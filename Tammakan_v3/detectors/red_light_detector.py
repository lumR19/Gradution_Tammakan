"""
red_light_detector.py
═══════════════════════════════════════════════════════════════════════════════
Detects red light violations and upcoming red light warnings.

V2 — fixes false RED_LIGHT_RAN events:
- A track disappearing high in the frame = went out of view at distance
  (NOT a violation — car never reached it)
- A track disappearing low in the frame = car passed under/past it
  (real violation)
- Once a track is marked "warned", it stays warned even through brief
  classification flickers — no more re-firing AHEAD on the same light
- A small disappearance grace period (5 frames) before declaring the
  track gone, so brief occlusion doesn't trigger anything

Two event types:
    RED_LIGHT_AHEAD   — a red light is visible and stable
    RED_LIGHT_RAN     — a confirmed red light track passed below the
                        violation line at the bottom of the frame
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from light_classifier import LightClassifier
from tamakkan_tracker import Track


class EventType(str, Enum):
    RED_LIGHT_AHEAD = "RED_LIGHT_AHEAD"
    RED_LIGHT_RAN   = "RED_LIGHT_RAN"


@dataclass
class RedLightEvent:
    type:       EventType
    track_id:   int
    timestamp:  float
    confidence: float
    bbox:       tuple
    frame_idx:  int


@dataclass
class _TrackState:
    consecutive_red:    int   = 0
    confirmed:          bool  = False     # passed AHEAD threshold at least once
    warned:             bool  = False     # AHEAD already fired for this track
    last_confidence:    float = 0.0
    last_bbox:          tuple = field(default_factory=tuple)
    last_seen_frame:    int   = 0
    max_y_seen:         float = 0.0       # how low in frame this light has reached
    violation_fired:    bool  = False     # RAN already fired — don't fire again


class RedLightDetector:
    """
    Detects red light events. Stateful — create once, call update() per frame.
    """

    TRAFFIC_LIGHT_CLASS_ID = 4

    def __init__(
        self,
        confirm_frames:        int   = 3,
        disappear_grace:       int   = 5,
        violation_y_fraction:  float = 0.55,
    ):
        """
        Args:
            confirm_frames: consecutive red frames before firing AHEAD (default 3)
            disappear_grace: frames a track can be missing before being declared
                             gone — protects against brief occlusion (default 5)
            violation_y_fraction: a red light track must reach below this
                                  fraction of frame height before disappearing
                                  to count as a violation. 0.55 = lower half.
                                  Lights that disappear from the upper half are
                                  ignored (car never reached them).
        """
        self.confirm_frames       = confirm_frames
        self.disappear_grace      = disappear_grace
        self.violation_y_fraction = violation_y_fraction

        self.classifier = LightClassifier()
        self.frame_idx  = 0
        self._states: dict[int, _TrackState] = {}

    def update(self, tracks: List[Track], frame) -> List[RedLightEvent]:
        self.frame_idx += 1
        events: List[RedLightEvent] = []
        frame_h = frame.shape[0]
        violation_y = frame_h * self.violation_y_fraction

        seen_ids: set[int] = set()

        for track in tracks:
            if track.class_id != self.TRAFFIC_LIGHT_CLASS_ID:
                continue

            seen_ids.add(track.track_id)
            crop = self._crop(frame, track.bbox)
            if crop is None:
                continue

            result = self.classifier.classify(crop)
            state  = self._states.setdefault(track.track_id, _TrackState())

            state.last_bbox       = track.bbox
            state.last_confidence = result["confidence"]
            state.last_seen_frame = self.frame_idx

            # track the lowest point in frame this light has reached.
            # used later to decide if a disappearance is a real violation.
            y_bottom = track.bbox[3]
            if y_bottom > state.max_y_seen:
                state.max_y_seen = y_bottom

            if result["color"] == "red":
                state.consecutive_red += 1
            else:
                # once warned, ignore brief misclassification — the light
                # is the same physical object, ByteTrack confirms the ID.
                if not state.warned:
                    state.consecutive_red = max(0, state.consecutive_red - 2)

            if state.consecutive_red >= self.confirm_frames:
                state.confirmed = True

                if not state.warned:
                    state.warned = True
                    events.append(RedLightEvent(
                        type       = EventType.RED_LIGHT_AHEAD,
                        track_id   = track.track_id,
                        timestamp  = time.time(),
                        confidence = state.last_confidence,
                        bbox       = track.bbox,
                        frame_idx  = self.frame_idx,
                    ))

        # ── Disappearance check with grace period and geometric gate ──────────
        # A track is considered "really gone" if it hasn't been seen for
        # `disappear_grace` frames. THEN we check if it counts as a violation.
        to_delete = []
        for tid, state in self._states.items():
            if tid in seen_ids:
                continue

            frames_missing = self.frame_idx - state.last_seen_frame
            if frames_missing < self.disappear_grace:
                continue

            # track is really gone — decide what it means
            if (state.confirmed
                and not state.violation_fired
                and state.max_y_seen >= violation_y):
                # car physically passed the light → real violation
                state.violation_fired = True
                events.append(RedLightEvent(
                    type       = EventType.RED_LIGHT_RAN,
                    track_id   = tid,
                    timestamp  = time.time(),
                    confidence = state.last_confidence,
                    bbox       = state.last_bbox,
                    frame_idx  = self.frame_idx,
                ))

            to_delete.append(tid)

        for tid in to_delete:
            self._states.pop(tid, None)

        return events

    def reset(self):
        self._states.clear()
        self.frame_idx = 0

    @staticmethod
    def _crop(frame, bbox: tuple):
        x1, y1, x2, y2 = map(int, bbox)
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return None
        return frame[y1:y2, x1:x2]