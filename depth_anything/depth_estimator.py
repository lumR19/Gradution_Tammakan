import cv2
import torch
import numpy as np
from collections import deque

# Official Depth Anything V2 repo (not HuggingFace transformers).
# Setup: git clone https://github.com/DepthAnything/Depth-Anything-V2
#        set PYTHONPATH to point at that clone
# Weights: depth_anything_v2_vits.pth (~99MB) from HuggingFace model page
from depth_anything_v2.dpt import DepthAnythingV2

# YOLO import removed — detection is TamakkanTracker's job.
# Bounding boxes are passed in to TailgatingDetector, not computed here.


# Model config for ViT-S (small = fastest, good for Jetson)
_VITS_CONFIG = {"encoder": "vits", "features": 64, "out_channels": [48, 96, 192, 384]}

# ===============================
# Depth Estimator (Requirement 1)
# ===============================
class DepthEstimator:
    def __init__(self, weights_path="depth_anything_v2_vits.pth", device="cpu"):
        self.device = torch.device(device)

        # Official V2 repo model — same weights, cleaner ONNX export path
        # than the HuggingFace transformers wrapper.
        self.model = DepthAnythingV2(**_VITS_CONFIG).to(self.device)
        self.model.load_state_dict(torch.load(weights_path, map_location=self.device))
        self.model.eval()

        # cached_depth kept so callers that want to skip frames can reuse it.
        # Frame-skip logic itself is REMOVED from here — AlertEngine decides
        # when to call predict_raw(), not this class.
        self.cached_depth = None

    def predict_raw(self, frame):
        """
        Run one depth inference pass. Always executes — no skip logic here.
        AlertEngine (or the main loop) decides how often to call this.

        Returns float32 depth map (H, W), values in [0, 255].
        Higher value = closer to camera.
        """
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # DINOv2 patch size is 14 — input dimensions must be multiples of 14.
        # Snap to nearest multiple, feed model, then resize output back to original.
        model_h = (h // 14) * 14
        model_w = (w // 14) * 14
        resized = cv2.resize(rgb, (model_w, model_h))

        tensor = (
            torch.from_numpy(resized)
            .permute(2, 0, 1)
            .unsqueeze(0)
            .float()
            .div(255.0)
            .to(self.device)
        )

        with torch.no_grad():
            depth = self.model(tensor)

        depth = depth.squeeze().cpu().numpy()
        depth = cv2.resize(depth, (w, h))          # back to original frame size
        depth_norm = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX)
        self.cached_depth = depth_norm.astype(np.float32)
        return self.cached_depth

    def colorize(self, depth_map):
        """Turn a float32 depth map into a BGR uint8 heatmap for encoding/WebSocket."""
        return cv2.applyColorMap(depth_map.astype(np.uint8), cv2.COLORMAP_INFERNO)


# ===============================
# Tailgating Detector
# ===============================
class TailgatingDetector:
    def __init__(self, estimator, n_calibration_frames=50, fallback_threshold=120.0):
        self.estimator = estimator
        self.threshold = None
        self.n_calibration_frames = n_calibration_frames
        self.fallback_threshold = fallback_threshold
        self._calib_buffer = deque(maxlen=n_calibration_frames)

        # YOLO removed — bboxes come from TamakkanTracker, not from here.
        # Running a second YOLO inside this class was a 2× speed hit for nothing.

    # ------------------------------------------------------------------
    # Internal helper — shared by calibration and inference
    # ------------------------------------------------------------------
    def _depth_for_bboxes(self, depth_map, bboxes):
        """
        bboxes: list of (x1, y1, x2, y2, label) from TamakkanTracker.
        Returns mean depth across all vehicle boxes, or None if none found.
        """
        vehicle_labels = {"car", "bus", "truck"}
        depths = []
        for (x1, y1, x2, y2, label) in bboxes:
            if label not in vehicle_labels:
                continue
            roi = depth_map[y1:y2, x1:x2]
            if roi.size > 0:
                depths.append(float(np.mean(roi)))
        return float(np.mean(depths)) if depths else None

    # ------------------------------------------------------------------
    # Calibration — rolling buffer, works on live stream
    # ------------------------------------------------------------------
    @property
    def is_calibrated(self):
        return self.threshold is not None

    def feed_calibration_frame(self, depth_map, bboxes):
        """
        Call this instead of check_tailgating() for the first ~50 frames.
        Replaces calibrate_from_video() which required a finished video file —
        that can't work with a live USB camera on the Jetson.

        The main loop pattern:
            depth_map = estimator.predict_raw(frame)
            bboxes    = tracker.get_vehicle_bboxes(frame)
            if not detector.is_calibrated:
                detector.feed_calibration_frame(depth_map, bboxes)
            else:
                result = detector.check_tailgating(depth_map, bboxes)
        """
        if self.is_calibrated:
            return
        depth_val = self._depth_for_bboxes(depth_map, bboxes)
        if depth_val is not None:
            self._calib_buffer.append(depth_val)
        if len(self._calib_buffer) >= self.n_calibration_frames:
            self.finalize_calibration()

    def finalize_calibration(self):
        """Force calibration to finish early (e.g. user skips warmup)."""
        if len(self._calib_buffer) == 0:
            print("No vehicles detected during calibration → using default threshold")
            self.threshold = self.fallback_threshold
        else:
            self.threshold = float(np.mean(self._calib_buffer)) * 1.2
        print("Threshold:", self.threshold)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def check_tailgating(self, depth_map, bboxes):
        """
        depth_map : float32 (H, W) from estimator.predict_raw()
        bboxes    : list of (x1, y1, x2, y2, label) from TamakkanTracker

        Returns True if tailgating detected.
        Must call finalize_calibration() first (or let feed_calibration_frame
        do it automatically).
        """
        if not self.is_calibrated:
            raise RuntimeError("check_tailgating() called before calibration is complete.")
        depth_val = self._depth_for_bboxes(depth_map, bboxes)
        if depth_val is None:
            return False
        return depth_val > self.threshold


# ===============================
# Video Processing
# ===============================
def process_video(input_path, output_path, estimator, detector, skip_frames=4):
    """
    Minimal reference loop — shows correct call order for the new API.

    imshow REMOVED: there is no display on the Jetson over SSH.
    Display goes to the phone via WebSocket (pipeline orchestrator's job).

    skip_frames: run depth inference every N frames; AlertEngine will own
    this in the full pipeline, but it's a parameter here for testing.
    """
    cap = cv2.VideoCapture(input_path)

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = int(cap.get(cv2.CAP_PROP_FPS))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height), True)

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # AlertEngine owns skip logic in prod; here we do it simply by index.
        if frame_idx % skip_frames == 0 or estimator.cached_depth is None:
            depth_map = estimator.predict_raw(frame)
        else:
            depth_map = estimator.cached_depth

        colored = estimator.colorize(depth_map)

        # In the full pipeline, bboxes come from TamakkanTracker.
        # Here we pass an empty list so the file runs standalone without YOLO.
        bboxes = []  # replace with tracker.get_vehicle_bboxes(frame) in pipeline

        if detector.is_calibrated:
            if detector.check_tailgating(depth_map, bboxes):
                cv2.putText(colored, "TAILGATING WARNING!", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            detector.feed_calibration_frame(depth_map, bboxes)

        out.write(colored)
        frame_idx += 1

    cap.release()
    out.release()
    # cv2.destroyAllWindows() — removed, no display on Jetson over SSH

    print("Saved to:", output_path)


# ===============================
# ONNX Export (Requirement 3)
# ===============================
def export_to_onnx(estimator, save_path="depth_anything_v2.onnx"):
    """
    Export model to ONNX for TensorRT FP16 on Jetson.

    After this, on the Jetson:
        trtexec --onnx=depth_anything_v2.onnx \
                --saveEngine=depth_anything_v2.trt \
                --fp16
    """
    s = 518  # 518 = 37 × 14, valid multiple of DINOv2 patch size
    dummy_input = torch.randn(1, 3, s, s, device=estimator.device)

    torch.onnx.export(
        estimator.model,
        dummy_input,
        save_path,
        input_names=["image"],
        output_names=["depth"],
        opset_version=18,
        do_constant_folding=True,
    )

    print("ONNX model saved at:", save_path)
    print("Next step (Jetson): trtexec --onnx=%s --saveEngine=depth.trt --fp16" % save_path)


# ===============================
# MAIN
# ===============================
if __name__ == "__main__":

    video_path = input("Enter full video path: ").strip()

    estimator = DepthEstimator(weights_path="depth_anything_v2_vits.pth", device="cpu")
    detector  = TailgatingDetector(estimator)

    # No calibrate_from_video() — calibration now happens inside process_video()
    # on the first 50 frames that contain vehicles, same as it would on a live camera.
    process_video(
        input_path=video_path,
        output_path="output_depth.mp4",
        estimator=estimator,
        detector=detector,
    )

    # Export for TensorRT (uncomment if onnx is installed)
    export_to_onnx(estimator)
