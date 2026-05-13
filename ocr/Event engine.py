"""
event_engine.py
---------------
Overspeed detection engine for Tamakkan.

Responsibilities
----------------
- Track the current speed limit derived from OCR reads.
- Compare ego speed (from phone GPS or manual override) against the limit.
- Fire an OVERSPEED Event dict when the threshold is exceeded.

Usage
-----
    engine = EventEngine()

    # Call once per frame after OCR:
    event = engine.process_frame(ocr_reads=["80"], ego_speed_kmh=95)
    if event:
        print(event)  # {'type': 'OVERSPEED', 'severity': 'medium', ...}
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

# ── Constants ──────────────────────────────────────────────────────────────────

# Only these values are accepted as authoritative limit reads.
VALID_LIMITS = {40, 60, 80, 100, 120}

# km/h buffer above the posted limit before firing the event.
OVERSPEED_TOLERANCE_KMH = 10

# Minimum OCR confidence to accept a limit update.
# (Pass conf per read when available; defaults to 1.0 if not.)
MIN_LIMIT_CONF = 0.75

# Minimum consecutive confirming reads before we switch to a new limit.
# Prevents flickering when OCR mis-reads a sign momentarily.
CONFIRMATION_FRAMES = 2


# ── Event schema ───────────────────────────────────────────────────────────────

@dataclass
class OverspeedEvent:
    type: str = "OVERSPEED"
    severity: str = "medium"
    current_speed: float = 0.0
    limit: int = 0
    excess_kmh: float = 0.0
    timestamp: float = field(default_factory=time.time)
    message_ar: str = ""
    message_en: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def _build_messages(speed: float, limit: int, excess: float):
        en = (
            f"Overspeed detected! You are travelling at {speed:.0f} km/h "
            f"in a {limit} km/h zone — {excess:.0f} km/h over the limit."
        )
        ar = (
            f"تم رصد تجاوز للسرعة! سرعتك الحالية {speed:.0f} كم/ساعة "
            f"في منطقة محدودة بـ {limit} كم/ساعة — تجاوز {excess:.0f} كم/ساعة."
        )
        return ar, en


# ── Engine ────────────────────────────────────────────────────────────────────

class EventEngine:
    """
    Stateful engine that maintains the current speed limit and detects overspeed.

    Parameters
    ----------
    overspeed_tolerance : int
        How many km/h above the limit before firing an event (default 10).
    confirmation_frames : int
        How many consecutive agreeing OCR reads before accepting a new limit.
    """

    def __init__(
        self,
        overspeed_tolerance: int = OVERSPEED_TOLERANCE_KMH,
        confirmation_frames: int = CONFIRMATION_FRAMES,
    ) -> None:
        # Public state — readable by FastAPI / WebSocket layer
        self.current_limit: Optional[int] = None
        self.ego_speed_kmh: float = 0.0          # updated externally by GPS/override
        self.last_event: Optional[Dict[str, Any]] = None

        # Internal
        self._tolerance = overspeed_tolerance
        self._confirm_target: Optional[int] = None
        self._confirm_count: int = 0
        self._confirmation_frames = confirmation_frames

    # ── Public API ─────────────────────────────────────────────────────────────

    def update_ego_speed(self, speed_kmh: float) -> None:
        """Call this whenever a new GPS or manual speed arrives."""
        self.ego_speed_kmh = max(0.0, float(speed_kmh))

    def process_frame(
        self,
        ocr_reads: List[str],
        ego_speed_kmh: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Process OCR reads from a single frame.

        Parameters
        ----------
        ocr_reads   : list of speed strings e.g. ["80"] or []
        ego_speed_kmh : override ego speed for this frame (or use self.ego_speed_kmh)

        Returns
        -------
        Event dict if overspeed, else None.
        """
        if ego_speed_kmh is not None:
            self.update_ego_speed(ego_speed_kmh)

        self._ingest_ocr_reads(ocr_reads)
        return self._check_overspeed()

    # ── Limit tracking ─────────────────────────────────────────────────────────

    def _ingest_ocr_reads(self, ocr_reads: List[str]) -> None:
        """
        Parse OCR strings and update self.current_limit after confirmation.

        Only values in VALID_LIMITS are considered. We require
        `_confirmation_frames` consecutive reads of the same candidate before
        switching, to avoid noise-induced flickering.
        """
        candidate = self._best_candidate(ocr_reads)

        if candidate is None:
            # No valid read this frame — reset confirmation streak
            self._confirm_count = 0
            self._confirm_target = None
            return

        if candidate == self._confirm_target:
            self._confirm_count += 1
        else:
            # New candidate — start fresh streak
            self._confirm_target = candidate
            self._confirm_count = 1

        if self._confirm_count >= self._confirmation_frames:
            if candidate != self.current_limit:
                print(
                    f"[EventEngine] Speed limit updated: "
                    f"{self.current_limit} → {candidate} km/h"
                )
            self.current_limit = candidate

    def _best_candidate(self, ocr_reads: List[str]) -> Optional[int]:
        """Return the highest-confidence valid limit found in ocr_reads."""
        for text in ocr_reads:
            cleaned = text.strip().replace(" ", "")
            if cleaned.isdigit():
                val = int(cleaned)
                if val in VALID_LIMITS:
                    return val
        return None

    # ── Overspeed check ────────────────────────────────────────────────────────

    def _check_overspeed(self) -> Optional[Dict[str, Any]]:
        """
        Compare ego_speed against current_limit + tolerance.

        Returns
        -------
        Optional[Event dict]  — None if no violation or no limit known yet.
        """
        if self.current_limit is None:
            return None
        if self.ego_speed_kmh <= 0:
            return None

        threshold = self.current_limit + self._tolerance
        if self.ego_speed_kmh > threshold:
            excess = self.ego_speed_kmh - self.current_limit
            ar, en = OverspeedEvent._build_messages(
                self.ego_speed_kmh, self.current_limit, excess
            )
            event = OverspeedEvent(
                severity=self._severity(excess),
                current_speed=round(self.ego_speed_kmh, 1),
                limit=self.current_limit,
                excess_kmh=round(excess, 1),
                message_ar=ar,
                message_en=en,
            ).to_dict()
            self.last_event = event
            return event

        return None

    @staticmethod
    def _severity(excess_kmh: float) -> str:
        """Classify severity based on how far over the limit the driver is."""
        if excess_kmh <= 20:
            return "medium"
        elif excess_kmh <= 40:
            return "high"
        return "critical"