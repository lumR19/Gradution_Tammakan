"""
depth_estimator.py  —  Tammakan Pipeline · Depth & Tailgating Module
=====================================================================
Responsibilities of THIS file
──────────────────────────────
  1. Load Depth Anything V2 (official repo, not HuggingFace transformers).
  2. Run depth inference on demand and return a raw float32 depth map.
  3. Given bounding boxes that arrive FROM TamakkanTracker (no YOLO here),
     compute per-vehicle depth and decide whether tailgating is occurring.
  4. Support live-stream calibration on a rolling buffer — no video file needed.
  5. Export the model to ONNX for downstream TensorRT FP16 conversion on Jetson.

What was REMOVED and why
─────────────────────────
  ✗  YOLO / Ultralytics import  →  detection lives in TamakkanTracker; running
     it twice per frame was a 2× speed penalty for zero gain.

  ✗  calibrate_from_video(video_path)  →  opens a VideoCapture, which requires
     a finished file.  On a live USB camera there is no finished file.
     Replaced by feed_calibration_frame() + finalize_calibration(), which work
     on whatever frames the main loop has already decoded.

  ✗  process_video() with cv2.imshow  →  imshow blocks and requires a local
     display; over SSH on the Jetson there is none.  Display is the phone's job
     via WebSocket.  Video I/O belongs in the pipeline orchestrator, not here.

  ✗  Hardcoded frame-skip (frame_count % 4)  →  the skip cadence should be
     decided by AlertEngine, which knows the load of all other models.  This
     file now exposes predict_raw() (always runs) and the caller decides when
     to call it.

Model choice
─────────────
  Using the OFFICIAL Depth Anything V2 repo (DepthAnythingV2 class) rather than
  the HuggingFace transformers wrapper.  Both load the same weights but the
  official repo gives direct access to the encoder/decoder graph needed for a
  clean ONNX trace.  Install with:
      pip install git+https://github.com/DepthAnything/Depth-Anything-V2.git

ONNX → TensorRT path (Jetson)
──────────────────────────────
  1. python depth_estimator.py --export          # produces depth_anything_v2.onnx
  2. trtexec --onnx=depth_anything_v2.onnx \
             --saveEngine=depth_anything_v2.trt \
             --fp16                              # run on Jetson, ~2× faster
"""

from __future__ import annotations

import argparse
import logging
from collections import deque
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import torch

# ---------------------------------------------------------------------------
# Official Depth Anything V2 import.
# If you haven't cloned the repo yet:
#   git clone https://github.com/DepthAnything/Depth-Anything-V2
#   pip install -e Depth-Anything-V2
# ---------------------------------------------------------------------------
try:
    from depth_anything_v2.dpt import DepthAnythingV2 as _DepthAnythingV2
    _OFFICIAL_REPO_AVAILABLE = True
except ImportError:  # graceful fallback so the file is at least importable
    _OFFICIAL_REPO_AVAILABLE = False
    logging.warning(
        "depth_anything_v2 package not found. "
        "Clone https://github.com/DepthAnything/Depth-Anything-V2 and pip install it. "
        "DepthEstimator will raise at __init__ time if you try to instantiate it."
    )

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model configs (encoder → (channels, features)) as defined by the V2 repo
# ---------------------------------------------------------------------------
_MODEL_CONFIGS = {
    "vits": {"encoder": "vits", "features": 64,  "out_channels": [48,  96,  192, 384]},
    "vitb": {"encoder": "vitb", "features": 128, "out_channels": [96,  192, 384, 768]},
    "vitl": {"encoder": "vitl", "features": 256, "out_channels": [256, 512, 1024, 1024]},
}

# Safe default threshold (depth-normalised 0-255 scale).
# Used when calibration finds no vehicles in the first N frames.
_FALLBACK_THRESHOLD = 120.0


# ===========================================================================
# 1.  DepthEstimator
# ===========================================================================
class DepthEstimator:
    """
    Wraps Depth Anything V2 (official repo).

    Usage in the main pipeline
    ──────────────────────────
        estimator = DepthEstimator(encoder="vits", device="cuda")

        # AlertEngine decides the skip cadence, not this class:
        if alert_engine.should_run_depth(frame_idx):
            depth_map = estimator.predict_raw(frame)   # H×W float32
            alert_engine.on_depth_ready(depth_map)

    The caller is also free to call predict_raw() on every frame — there is no
    hidden skip logic inside here anymore.
    """

    def __init__(
        self,
        encoder: str = "vits",
        weights_path: Optional[str] = None,
        device: str = "cpu",
        input_size: int = 384,
    ):
        """
        Parameters
        ----------
        encoder      : "vits" | "vitb" | "vitl"  (small → large, speed vs quality)
        weights_path : path to the .pth file downloaded from the official repo.
                       If None, the model is constructed but weights are NOT loaded
                       (useful for ONNX export tests without the real checkpoint).
        device       : "cpu" | "cuda" | "cuda:0" …
        input_size   : inference resolution fed to the model (square).
        """
        if not _OFFICIAL_REPO_AVAILABLE:
            raise ImportError(
                "Install the official Depth Anything V2 package first — "
                "see the module docstring."
            )

        if encoder not in _MODEL_CONFIGS:
            raise ValueError(f"encoder must be one of {list(_MODEL_CONFIGS)}; got '{encoder}'")

        self.device = torch.device(device)
        self.input_size = input_size

        cfg = _MODEL_CONFIGS[encoder]
        self.model = _DepthAnythingV2(**cfg).to(self.device)
        self.model.eval()

        if weights_path is not None:
            ckpt = torch.load(weights_path, map_location=self.device)
            self.model.load_state_dict(ckpt)
            log.info("Loaded weights from %s", weights_path)
        else:
            log.warning("No weights_path given — model has random weights.")

    # ------------------------------------------------------------------
    def predict_raw(self, frame: np.ndarray) -> np.ndarray:
        """
        Run one depth inference pass.

        Parameters
        ----------
        frame : BGR uint8 image (H, W, 3) — straight from cv2.VideoCapture

        Returns
        -------
        depth_norm : float32 array (H, W), values in [0, 255].
                     Higher values = closer to camera (the model outputs
                     inverse depth; we normalise to 0-255 for downstream use).
        """
        h, w = frame.shape[:2]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (self.input_size, self.input_size))

        tensor = (
            torch.from_numpy(resized)
            .permute(2, 0, 1)           # (3, H, W)
            .unsqueeze(0)               # (1, 3, H, W)
            .float()
            .div(255.0)
            .to(self.device)
        )

        with torch.no_grad():
            depth = self.model(tensor)  # (1, H, W) or (1, 1, H, W) depending on version

        depth = depth.squeeze().cpu().numpy()                   # (H_model, W_model)
        depth = cv2.resize(depth, (w, h))                       # back to original size
        depth_norm = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX)
        return depth_norm.astype(np.float32)

    # ------------------------------------------------------------------
    def colorize(self, depth_norm: np.ndarray) -> np.ndarray:
        """
        Convenience: turn a float32 depth map into a BGR uint8 heatmap for
        encoding / sending over WebSocket.  Not called during inference.
        """
        gray = depth_norm.astype(np.uint8)
        return cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)


# ===========================================================================
# 2.  TailgatingDetector
# ===========================================================================
class TailgatingDetector:
    """
    Decides whether any tracked vehicle is tailgating.

    Key design change
    ─────────────────
    This class NO LONGER runs YOLO.  Bounding boxes come in from TamakkanTracker,
    which already ran detection.  This class only samples the depth map inside
    each box and compares to the calibrated threshold.

    Calibration
    ───────────
    Instead of opening a video file (impossible on a live camera), calibration
    works on a rolling buffer populated by the main loop:

        detector = TailgatingDetector(estimator, n_calibration_frames=50)

        # Inside the capture loop:
        depth_map = estimator.predict_raw(frame)
        bboxes    = tracker.get_vehicle_bboxes(frame)   # from TamakkanTracker

        if not detector.is_calibrated:
            detector.feed_calibration_frame(depth_map, bboxes)
        else:
            is_tailgating = detector.check_tailgating(depth_map, bboxes)
    """

    def __init__(
        self,
        estimator: DepthEstimator,
        n_calibration_frames: int = 50,
        threshold_multiplier: float = 1.2,
        fallback_threshold: float = _FALLBACK_THRESHOLD,
        vehicle_labels: Optional[List[str]] = None,
    ):
        """
        Parameters
        ----------
        estimator             : DepthEstimator instance (used only for colorize;
                                depth maps are passed in, not computed here)
        n_calibration_frames  : how many frames with at least one vehicle to
                                collect before locking in the threshold
        threshold_multiplier  : threshold = mean_depth × this value
        fallback_threshold    : used if no vehicles appear during calibration
        vehicle_labels        : class names to treat as vehicles.
                                Must match whatever TamakkanTracker uses.
                                Defaults to ["car", "bus", "truck"].
        """
        self.estimator = estimator
        self.n_calibration_frames = n_calibration_frames
        self.threshold_multiplier = threshold_multiplier
        self.fallback_threshold = fallback_threshold
        self.vehicle_labels = vehicle_labels or ["car", "bus", "truck"]

        self.threshold: Optional[float] = None
        self._calibration_buffer: deque = deque(maxlen=n_calibration_frames)

    # ------------------------------------------------------------------
    @property
    def is_calibrated(self) -> bool:
        return self.threshold is not None

    # ------------------------------------------------------------------
    def _depth_for_bboxes(
        self,
        depth_map: np.ndarray,
        bboxes: List[Tuple[int, int, int, int, str]],
    ) -> Optional[float]:
        """
        Sample mean depth inside each vehicle bounding box and return the
        average across all vehicles in the frame.

        Parameters
        ----------
        depth_map : float32 (H, W) from DepthEstimator.predict_raw()
        bboxes    : list of (x1, y1, x2, y2, label) tuples from TamakkanTracker.
                    Labels that are not in self.vehicle_labels are skipped.

        Returns
        -------
        Mean depth value (float) or None if no eligible vehicles were found.
        """
        depths = []
        for (x1, y1, x2, y2, label) in bboxes:
            if label not in self.vehicle_labels:
                continue
            roi = depth_map[y1:y2, x1:x2]
            if roi.size > 0:
                depths.append(float(np.mean(roi)))

        return float(np.mean(depths)) if depths else None

    # ------------------------------------------------------------------
    def feed_calibration_frame(
        self,
        depth_map: np.ndarray,
        bboxes: List[Tuple[int, int, int, int, str]],
    ) -> None:
        """
        Add one frame to the calibration buffer.
        Call this during the first ~N frames of the live stream instead of
        check_tailgating().  When enough frames have been collected,
        finalize_calibration() is called automatically.

        Parameters are the same as check_tailgating().
        """
        if self.is_calibrated:
            return  # already done, ignore extra calls

        depth_val = self._depth_for_bboxes(depth_map, bboxes)
        if depth_val is not None:
            self._calibration_buffer.append(depth_val)
            log.debug(
                "Calibration frame %d/%d  depth=%.1f",
                len(self._calibration_buffer),
                self.n_calibration_frames,
                depth_val,
            )

        # Auto-finalize once buffer is full
        if len(self._calibration_buffer) >= self.n_calibration_frames:
            self.finalize_calibration()

    # ------------------------------------------------------------------
    def finalize_calibration(self) -> float:
        """
        Lock in the threshold from whatever calibration frames were collected
        so far.  Safe to call early (e.g. user skips straight into live mode).

        Returns the computed threshold.
        """
        if len(self._calibration_buffer) == 0:
            log.warning(
                "No vehicles detected during calibration — "
                "falling back to threshold=%.1f",
                self.fallback_threshold,
            )
            self.threshold = self.fallback_threshold
        else:
            self.threshold = float(np.mean(self._calibration_buffer)) * self.threshold_multiplier
            log.info(
                "Calibration complete: %d frames, threshold=%.1f",
                len(self._calibration_buffer),
                self.threshold,
            )
        return self.threshold

    # ------------------------------------------------------------------
    def check_tailgating(
        self,
        depth_map: np.ndarray,
        bboxes: List[Tuple[int, int, int, int, str]],
    ) -> bool:
        """
        Return True if any tracked vehicle is closer than the calibrated
        threshold (i.e. tailgating).

        Must call finalize_calibration() (or let feed_calibration_frame()
        do it automatically) before calling this.

        Parameters
        ----------
        depth_map : float32 (H, W) — latest output of DepthEstimator.predict_raw()
        bboxes    : list of (x1, y1, x2, y2, label) from TamakkanTracker

        Returns
        -------
        bool
        """
        if not self.is_calibrated:
            raise RuntimeError(
                "TailgatingDetector.check_tailgating() called before calibration. "
                "Feed at least one calibration frame or call finalize_calibration()."
            )

        depth_val = self._depth_for_bboxes(depth_map, bboxes)
        if depth_val is None:
            return False  # no vehicles visible → no tailgating

        return depth_val > self.threshold


# ===========================================================================
# 3.  ONNX Export
# ===========================================================================
def export_to_onnx(
    estimator: DepthEstimator,
    save_path: str = "depth_anything_v2.onnx",
) -> None:
    """
    Trace the depth model to ONNX with a fixed input size.

    After this, on the Jetson:
        trtexec --onnx=depth_anything_v2.onnx \
                --saveEngine=depth_anything_v2.trt \
                --fp16

    The FP16 engine gives roughly 2× the throughput on Jetson AGX Orin
    compared to FP32 PyTorch inference.

    Parameters
    ----------
    estimator : an already-loaded DepthEstimator
    save_path : output .onnx filename
    """
    s = estimator.input_size
    dummy = torch.randn(1, 3, s, s, device=estimator.device)

    torch.onnx.export(
        estimator.model,
        dummy,
        save_path,
        input_names=["image"],
        output_names=["depth"],
        dynamic_axes={
            # Allow variable batch size in case you want to batch frames later
            "image": {0: "batch"},
            "depth": {0: "batch"},
        },
        opset_version=17,   # 17 works reliably with TensorRT 8.6+; use 18 only if needed
        do_constant_folding=True,
    )
    log.info("ONNX model saved: %s", save_path)
    log.info("Next step on Jetson: trtexec --onnx=%s --saveEngine=depth.trt --fp16", save_path)
    print(f"✓  Saved ONNX model → {save_path}")


# ===========================================================================
# CLI  (for standalone testing and ONNX export — not the pipeline entry point)
# ===========================================================================
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Depth Anything V2 — standalone test / ONNX export")
    p.add_argument("--weights",  required=False, help="Path to .pth weights file")
    p.add_argument("--encoder",  default="vits", choices=list(_MODEL_CONFIGS))
    p.add_argument("--device",   default="cpu")
    p.add_argument("--export",   action="store_true", help="Export to ONNX and exit")
    p.add_argument("--onnx-out", default="depth_anything_v2.onnx")
    return p.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args()

    estimator = DepthEstimator(
        encoder=args.encoder,
        weights_path=args.weights,
        device=args.device,
    )

    if args.export:
        export_to_onnx(estimator, save_path=args.onnx_out)
    else:
        # Quick smoke-test on a single camera frame
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            print("Could not read from camera — pass --export for ONNX export only.")
        else:
            depth = estimator.predict_raw(frame)
            colored = estimator.colorize(depth)
            # Write to file instead of imshow (no display on Jetson over SSH)
            cv2.imwrite("depth_smoke_test.jpg", colored)
            print("Smoke test done — see depth_smoke_test.jpg")
