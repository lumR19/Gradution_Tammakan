"""
EventEngine detectors — Tasks 1.2 & 1.3
Author : Lina
Tasks  : Tailgating detector + Near-miss detector
Models : YOLO + ByteTrack + UFLD + Depth
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Shared data structures
# ---------------------------------------------------------------------------

@dataclass
class Track:
    track_id: int
    class_id: int          # 0=car, 1=truck, 2=bus, 3=motorcycle, 4=person, …
    bbox: Tuple[float, float, float, float]   # x1, y1, x2, y2  (pixel coords)
    frame_idx: int


@dataclass
class Event:
    type: str              # 'TAILGATING' | 'NEAR_MISS'
    severity: str          # 'high' | 'critical'
    track_id: int
    depth_value: Optional[float] = None
    approach_rate: Optional[float] = None
    class_name: Optional[str] = None
    message_ar: str = ""
    message_en: str = ""
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VEHICLE_CLASS_IDS   = {0, 1, 2}          # car, truck, bus
VRU_CLASS_IDS       = {3, 4, 5}          # motorcycle, person, cyclist (adjust to your label map)
TRACKED_CLASS_IDS   = VEHICLE_CLASS_IDS | VRU_CLASS_IDS

CLASS_NAMES: Dict[int, str] = {
    0: "car", 1: "truck", 2: "bus",
    3: "motorcycle", 4: "person", 5: "cyclist",
}


# ---------------------------------------------------------------------------
# Task 1.2 — Tailgating detector
# ---------------------------------------------------------------------------

class TailgatingDetector:
    """
    Detects when the ego-vehicle is following another vehicle too closely.

    Algorithm
    ---------
    1. Filter tracks to vehicles (class_id in {0,1,2}).
    2. Use UFLD lane data to find ego-lane boundaries (left/right x at bottom).
    3. Identify the *lead car*: bbox center_x inside lane bounds AND largest y2.
    4. Sample depth_map at lead car's bbox centre → depth_value.
    5. Maintain a deque of the last HISTORY_LEN depth values per track_id.
    6. If ALL values in the deque exceed DEPTH_THRESHOLD → fire TAILGATING event.

    Depth convention: higher relative depth value ≈ closer object.
    Threshold default: 0.7  (calibrate against real footage in Phase 2.6)
    """

    HISTORY_LEN     = 10
    DEPTH_THRESHOLD = 0.7   # relative depth; higher = closer

    def __init__(
        self,
        depth_threshold: float = DEPTH_THRESHOLD,
        history_len: int = HISTORY_LEN,
    ) -> None:
        self.depth_threshold = depth_threshold
        self.history_len     = history_len
        # track_id → deque of recent depth values
        self._depth_history: Dict[int, deque] = defaultdict(
            lambda: deque(maxlen=self.history_len)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _check_tailgating(
        self,
        tracks: List[Track],
        lanes: Dict,          # raw UFLD lane output
        depth_map: np.ndarray,
    ) -> Optional[Event]:
        """
        Called every frame.

        Parameters
        ----------
        tracks    : list of Track objects for the current frame
        lanes     : UFLD output dict; expected to contain ego-lane polylines
        depth_map : H×W float32 array of *relative* depth values (0–1)

        Returns
        -------
        An Event dict if tailgating is detected, else None.
        """
        # 1. Keep only vehicles
        vehicles = [t for t in tracks if t.class_id in VEHICLE_CLASS_IDS]
        if not vehicles:
            return None

        # 2. Extract ego-lane bounds from UFLD output
        lane_left_x, lane_right_x = self._get_ego_lane_bounds(lanes, depth_map.shape[1])
        if lane_left_x is None or lane_right_x is None:
            # Lane detection failed — skip this frame
            return None

        # 3. Find lead car
        lead = self._find_lead_car(vehicles, lane_left_x, lane_right_x)
        if lead is None:
            return None

        # 4. Sample depth at lead car's bbox centre
        cx, cy = self._bbox_centre(lead.bbox)
        depth_value = self._sample_depth(depth_map, cx, cy)

        # 5. Update history
        self._depth_history[lead.track_id].append(depth_value)

        # Prune stale track histories (optional housekeeping)
        active_ids = {t.track_id for t in tracks}
        self._prune_stale_tracks(active_ids)

        # 6. Fire event if all last N samples exceed threshold
        history = self._depth_history[lead.track_id]
        if len(history) == self.history_len and all(d > self.depth_threshold for d in history):
            return Event(
                type        = "TAILGATING",
                severity    = "high",
                track_id    = lead.track_id,
                depth_value = float(depth_value),
                message_ar  = "تحذير: مسافة أمان غير كافية — ابتعد عن السيارة الأمامية",
                message_en  = "Warning: Unsafe following distance — increase gap to lead vehicle",
            )

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_ego_lane_bounds(
        self, lanes: Dict, frame_width: int
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Parse UFLD lane output to get the ego-lane left/right x-coordinates
        at the bottom of the image.

        UFLD typically returns a list of lane polylines ordered left-to-right.
        Ego lane = lanes[1] (left boundary) and lanes[2] (right boundary) in
        a 4-lane model, but this depends on your UFLD config.

        Adjust indexing to match your specific UFLD variant.
        """
        try:
            # `lanes` is expected to be a list of polylines, each a list of (x, y) tuples
            # sorted by y descending (bottom of image first).
            polylines: List[List[Tuple[float, float]]] = lanes.get("lanes", [])

            if len(polylines) < 2:
                return None, None

            # Ego-lane: index 1 = left boundary, index 2 = right boundary
            # (assumes UFLD output is ordered left→right across full width)
            left_polyline  = polylines[1]
            right_polyline = polylines[2]

            # Take the bottommost point (largest y)
            left_x  = max(left_polyline,  key=lambda p: p[1])[0]
            right_x = max(right_polyline, key=lambda p: p[1])[0]

            return float(left_x), float(right_x)

        except (KeyError, IndexError, ValueError):
            return None, None

    def _find_lead_car(
        self,
        vehicles: List[Track],
        lane_left_x: float,
        lane_right_x: float,
    ) -> Optional[Track]:
        """
        Return the vehicle whose bbox centre_x is within ego-lane bounds
        AND has the largest y2 (closest to the camera at the bottom of frame).
        """
        candidates = []
        for v in vehicles:
            x1, y1, x2, y2 = v.bbox
            centre_x = (x1 + x2) / 2.0
            if lane_left_x <= centre_x <= lane_right_x:
                candidates.append(v)

        if not candidates:
            return None

        # Largest y2 = lowest in frame = closest ahead
        return max(candidates, key=lambda v: v.bbox[3])

    @staticmethod
    def _bbox_centre(bbox: Tuple[float, float, float, float]) -> Tuple[int, int]:
        x1, y1, x2, y2 = bbox
        return int((x1 + x2) / 2), int((y1 + y2) / 2)

    @staticmethod
    def _sample_depth(depth_map: np.ndarray, cx: int, cy: int) -> float:
        h, w = depth_map.shape[:2]
        cy = max(0, min(cy, h - 1))
        cx = max(0, min(cx, w - 1))
        return float(depth_map[cy, cx])

    def _prune_stale_tracks(self, active_ids: set) -> None:
        stale = [tid for tid in self._depth_history if tid not in active_ids]
        for tid in stale:
            del self._depth_history[tid]


# ---------------------------------------------------------------------------
# Task 1.3 — Near-miss detector
# ---------------------------------------------------------------------------

class NearMissDetector:
    """
    Detects objects rapidly approaching the ego-vehicle.

    Algorithm
    ---------
    1. For every tracked object (car, truck, bus, VRU), maintain a rolling
       buffer of (depth_value, frame_idx) tuples.
    2. Compute Δdepth/Δframe over the last VELOCITY_WINDOW frames.
       Positive Δdepth means the object is getting closer (depth increasing).
    3. If the object is a vehicle or VRU AND approach_rate > velocity_threshold
       → fire NEAR_MISS event immediately (no cooldown).
    4. ByteTrack persistent IDs guarantee we track the *same* object across
       frames — no ID switches corrupt the velocity estimate.
    5. A velocity floor (MIN_APPROACH_RATE) prevents static/slow objects from
       triggering noise.
    """

    BUFFER_LEN        = 30    # frames of history per track
    VELOCITY_WINDOW   = 5     # frames used for Δdepth estimate
    VELOCITY_THRESHOLD = 0.015 # Δdepth per frame; tune on parking-lot tests
    MIN_APPROACH_RATE = 0.003  # velocity floor to suppress noise

    def __init__(
        self,
        velocity_threshold: float = VELOCITY_THRESHOLD,
        velocity_window: int = VELOCITY_WINDOW,
        buffer_len: int = BUFFER_LEN,
        min_approach_rate: float = MIN_APPROACH_RATE,
    ) -> None:
        self.velocity_threshold = velocity_threshold
        self.velocity_window    = velocity_window
        self.buffer_len         = buffer_len
        self.min_approach_rate  = min_approach_rate

        # track_id → deque of (depth_value, frame_idx)
        self._buffers: Dict[int, deque] = defaultdict(
            lambda: deque(maxlen=self.buffer_len)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _check_near_miss(
        self,
        tracks: List[Track],
        depth_map: np.ndarray,
    ) -> Optional[Event]:
        """
        Called every frame. Returns the *most critical* near-miss event
        (highest approach rate) if any, else None.

        Parameters
        ----------
        tracks    : list of Track objects from ByteTrack for the current frame
        depth_map : H×W float32 relative-depth array

        Returns
        -------
        Event or None — fires immediately, no cooldown.
        """
        events: List[Tuple[float, Event]] = []

        for track in tracks:
            if track.class_id not in TRACKED_CLASS_IDS:
                continue

            # 1. Sample depth at bbox centre
            cx, cy = self._bbox_centre(track.bbox)
            depth_val = self._sample_depth(depth_map, cx, cy)

            # 2. Push to rolling buffer
            self._buffers[track.track_id].append((depth_val, track.frame_idx))

            buf = self._buffers[track.track_id]
            if len(buf) < self.velocity_window:
                continue   # not enough history yet

            # 3. Compute approach rate over last VELOCITY_WINDOW samples
            approach_rate = self._compute_approach_rate(buf)

            # 4. Velocity floor + threshold check
            if approach_rate < self.min_approach_rate:
                continue

            if approach_rate > self.velocity_threshold:
                class_name = CLASS_NAMES.get(track.class_id, "unknown")
                evt = Event(
                    type         = "NEAR_MISS",
                    severity     = "critical",
                    track_id     = track.track_id,
                    depth_value  = float(depth_val),
                    approach_rate = float(approach_rate),
                    class_name   = class_name,
                    message_ar   = f"خطر: اقتراب مفاجئ — {self._ar_class(class_name)} يقترب بسرعة",
                    message_en   = f"Critical: Rapid approach detected — {class_name} closing fast",
                )
                events.append((approach_rate, evt))

        # Prune tracks that are no longer active
        active_ids = {t.track_id for t in tracks}
        self._prune_stale_tracks(active_ids)

        if not events:
            return None

        # Return the fastest-approaching object
        events.sort(key=lambda x: x[0], reverse=True)
        return events[0][1]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_approach_rate(self, buf: deque) -> float:
        """
        Δdepth / Δframe using the most recent VELOCITY_WINDOW entries.
        Returns a positive value if the object is approaching (depth rising).
        """
        recent = list(buf)[-self.velocity_window:]
        depths  = np.array([r[0] for r in recent], dtype=np.float32)
        frames  = np.array([r[1] for r in recent], dtype=np.float32)

        delta_frame = frames[-1] - frames[0]
        if delta_frame == 0:
            return 0.0

        delta_depth = depths[-1] - depths[0]
        return float(delta_depth / delta_frame)

    @staticmethod
    def _bbox_centre(bbox: Tuple[float, float, float, float]) -> Tuple[int, int]:
        x1, y1, x2, y2 = bbox
        return int((x1 + x2) / 2), int((y1 + y2) / 2)

    @staticmethod
    def _sample_depth(depth_map: np.ndarray, cx: int, cy: int) -> float:
        h, w = depth_map.shape[:2]
        cy = max(0, min(cy, h - 1))
        cx = max(0, min(cx, w - 1))
        return float(depth_map[cy, cx])

    def _prune_stale_tracks(self, active_ids: set) -> None:
        stale = [tid for tid in self._buffers if tid not in active_ids]
        for tid in stale:
            del self._buffers[tid]

    @staticmethod
    def _ar_class(en_name: str) -> str:
        ar = {"car": "سيارة", "truck": "شاحنة", "bus": "حافلة",
              "motorcycle": "دراجة نارية", "person": "شخص", "cyclist": "دراجة"}
        return ar.get(en_name, en_name)


# ---------------------------------------------------------------------------
# EventEngine — wires both detectors together
# ---------------------------------------------------------------------------

class EventEngine:
    """
    Top-level engine. Instantiate once; call process_frame() every frame.

    Usage
    -----
        engine = EventEngine()
        event  = engine.process_frame(tracks, lanes, depth_map, frame_idx)
        if event:
            dispatch(event)
    """

    def __init__(
        self,
        tailgating_threshold: float = TailgatingDetector.DEPTH_THRESHOLD,
        near_miss_threshold:  float = NearMissDetector.VELOCITY_THRESHOLD,
    ) -> None:
        self._tailgating = TailgatingDetector(depth_threshold=tailgating_threshold)
        self._near_miss  = NearMissDetector(velocity_threshold=near_miss_threshold)

    def process_frame(
        self,
        tracks:    List[Track],
        lanes:     Dict,
        depth_map: np.ndarray,
        frame_idx: int = 0,
    ) -> Optional[Event]:
        """
        Run both detectors; return the highest-priority event.

        Priority: NEAR_MISS (critical) > TAILGATING (high)
        """
        # Stamp frame_idx on tracks if not already set
        for t in tracks:
            if t.frame_idx == 0:
                t.frame_idx = frame_idx

        near_miss_event  = self._near_miss._check_near_miss(tracks, depth_map)
        tailgating_event = self._tailgating._check_tailgating(tracks, lanes, depth_map)

        # Near-miss is highest priority
        if near_miss_event is not None:
            return near_miss_event
        return tailgating_event


# ---------------------------------------------------------------------------
# Quick smoke-test  (run: python event_engine_detectors.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    rng = np.random.default_rng(42)

    H, W = 480, 640
    engine = EventEngine(tailgating_threshold=0.7, near_miss_threshold=0.015)

    # Simulate 15 frames
    for frame_idx in range(15):
        # Fake depth map — lead car zone gets high depth in later frames
        depth_map = rng.uniform(0.1, 0.4, (H, W)).astype(np.float32)
        depth_map[200:300, 280:360] = 0.5 + frame_idx * 0.03   # approaching object

        tracks = [
            Track(track_id=1, class_id=0,
                  bbox=(280.0, 100.0, 360.0, 310.0), frame_idx=frame_idx),
            Track(track_id=2, class_id=4,
                  bbox=(100.0, 200.0, 140.0, 280.0), frame_idx=frame_idx),
        ]

        lanes = {
            "lanes": [
                [(50,  479), (80,  350), (100, 200)],   # far-left lane boundary
                [(200, 479), (220, 350), (240, 200)],   # ego-lane LEFT boundary
                [(400, 479), (380, 350), (360, 200)],   # ego-lane RIGHT boundary
                [(550, 479), (530, 350), (510, 200)],   # far-right lane boundary
            ]
        }

        event = engine.process_frame(tracks, lanes, depth_map, frame_idx)
        status = f"[frame {frame_idx:02d}]"
        if event:
            print(f"{status} 🚨 {event.type} | severity={event.severity} | "
                  f"track={event.track_id} | {event.message_en}")
        else:
            print(f"{status} ✅ No event")
