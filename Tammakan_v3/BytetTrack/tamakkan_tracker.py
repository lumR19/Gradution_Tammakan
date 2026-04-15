"""
TamakkanTracker — production detection + tracking wrapper for Tamakkan v3.

Encapsulates YOLOv11s + ByteTrack as a single component.
The AlertEngine and FastAPI server only touch this class — they never
import ultralytics directly. This means we can swap the tracker
(BoT-SORT, OC-SORT, custom) without touching downstream code.

Usage:
    tracker = TamakkanTracker(weights="best.pt")
    for frame in video_stream:
        tracks = tracker.update(frame)
        for t in tracks:
            print(t.track_id, t.class_name, t.bbox, t.confidence)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import numpy as np
from ultralytics import YOLO


@dataclass
class Track:
    """
    Single tracked object at one frame.
    
    Attributes are intentionally minimal — depth, velocity, and alert state
    are computed by downstream modules (DepthEstimator, AlertEngine), NOT here.
    Tracker's only job: stable IDs + boxes per frame.
    """
    track_id: int           # persistent ID across frames
    class_id: int           # 0=car, 1=truck, 2=bus, 3=person, 4=traffic_light, 5=traffic_sign, 6=VRU
    class_name: str         # human-readable class name
    confidence: float       # detection confidence [0, 1]
    bbox: tuple             # (x1, y1, x2, y2) in pixel coordinates


class TamakkanTracker:
    """
    YOLOv11s + ByteTrack wrapper.

    Maintains internal track state across .update() calls — DO NOT create
    a new instance per frame, you'll lose all track IDs.
    Create once at startup, call update() per frame.
    """

    # Class ID → name mapping for Tamakkan's 7-class model.
    # Keep this in sync with your data.yaml.
    CLASS_NAMES = {
        0: "car",
        1: "truck",
        2: "bus",
        3: "person",
        4: "traffic_light",
        5: "traffic_sign",
        6: "vulnerable_road_user",
    }

    def __init__(
        self,
        weights: str,
        tracker_config: str = "bytetrack_tamakkan.yaml",
        conf: float = 0.25,
        iou: float = 0.7,
        imgsz: int = 1280,
        device: str = "cuda:0",
        half: bool = True,
    ):
        """
        Args:
            weights: path to YOLOv11s best.pt
            tracker_config: path to bytetrack yaml
            conf: detection confidence threshold (0.25 = your F1-optimal)
            iou: NMS IoU threshold (Ultralytics default)
            imgsz: inference resolution. 1280 = train resolution, best accuracy.
                   Drop to 960 or 640 for faster inference if needed.
            device: 'cuda:0' for GPU, 'cpu' for fallback
            half: FP16 inference. Faster on RTX 5080, free accuracy.
                  Set False if running on CPU or older GPU.
        """
        if not Path(weights).exists():
            raise FileNotFoundError(f"Weights not found: {weights}")
        if not Path(tracker_config).exists():
            raise FileNotFoundError(f"Tracker config not found: {tracker_config}")

        self.model = YOLO(weights)
        self.tracker_config = tracker_config
        self.conf = conf
        self.iou = iou
        self.imgsz = imgsz
        self.device = device
        self.half = half

        # Frame counter — useful for downstream velocity calculations
        self.frame_count = 0

    def update(self, frame: np.ndarray) -> List[Track]:
        """
        Process one frame, return active tracks.
        
        Args:
            frame: BGR numpy array (H, W, 3) — same format as cv2.imread / cv2 video capture
        
        Returns:
            List of Track objects for all currently-active tracks in this frame.
            Empty list if nothing detected.
        """
        # persist=True is the key flag — tells Ultralytics to maintain state
        # across calls. Without it, tracking resets every frame.
        results = self.model.track(
            source=frame,
            conf=self.conf,
            iou=self.iou,
            imgsz=self.imgsz,
            device=self.device,
            half=self.half,
            persist=True,
            tracker=self.tracker_config,
            verbose=False,
            stream=False,
        )

        self.frame_count += 1

        # Ultralytics returns a list (one element per input image).
        # We always pass one frame, so we take [0].
        result = results[0]

        # No detections this frame → empty list
        if result.boxes is None or result.boxes.id is None:
            return []

        # Extract tensors and move to CPU for downstream processing
        boxes = result.boxes.xyxy.cpu().numpy()       # (N, 4) — x1,y1,x2,y2
        track_ids = result.boxes.id.cpu().numpy().astype(int)  # (N,)
        class_ids = result.boxes.cls.cpu().numpy().astype(int) # (N,)
        confidences = result.boxes.conf.cpu().numpy()          # (N,)

        tracks = []
        for i in range(len(track_ids)):
            cid = int(class_ids[i])
            tracks.append(Track(
                track_id=int(track_ids[i]),
                class_id=cid,
                class_name=self.CLASS_NAMES.get(cid, f"unknown_{cid}"),
                confidence=float(confidences[i]),
                bbox=tuple(boxes[i].tolist()),
            ))

        return tracks

    def reset(self):
        """
        Clear all track state. Call between unrelated video clips.
        Do NOT call between frames of the same video.
        """
        # Ultralytics doesn't expose a clean reset, so we reload the model.
        # Cheap operation since weights are already in GPU memory.
        weights_path = self.model.ckpt_path
        self.model = YOLO(weights_path)
        self.frame_count = 0