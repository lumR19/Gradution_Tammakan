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

VALID_LIMITS = {40, 60, 80, 100, 120}
OVERSPEED_TOLERANCE_KMH = 10
MIN_LIMIT_CONF = 0.75
CONFIRMATION_FRAMES = 1   # للديمو 1

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


class EventEngine:
    def __init__(
        self,
        overspeed_tolerance: int = OVERSPEED_TOLERANCE_KMH,
        confirmation_frames: int = CONFIRMATION_FRAMES,
    ) -> None:
        self.current_limit: Optional[int] = None
        self.ego_speed_kmh: float = 0.0
        self.last_event: Optional[Dict[str, Any]] = None

        self._tolerance = overspeed_tolerance
        self._confirm_target: Optional[int] = None
        self._confirm_count: int = 0
        self._confirmation_frames = confirmation_frames

        # جديد: يمنع تكرار نفس الحدث كل فريم
        self._overspeed_active = False

    def update_ego_speed(self, speed_kmh: float) -> None:
        self.ego_speed_kmh = max(0.0, float(speed_kmh))

    def process_frame(
        self,
        ocr_reads: List[str],
        ego_speed_kmh: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        if ego_speed_kmh is not None:
            self.update_ego_speed(ego_speed_kmh)

        self._ingest_ocr_reads(ocr_reads)
        return self._check_overspeed()

    def _ingest_ocr_reads(self, ocr_reads: List[str]) -> None:
        candidate = self._best_candidate(ocr_reads)

        if candidate is None:
            self._confirm_count = 0
            self._confirm_target = None
            return

        if candidate == self._confirm_target:
            self._confirm_count += 1
        else:
            self._confirm_target = candidate
            self._confirm_count = 1

        if self._confirm_count >= self._confirmation_frames:
            if candidate != self.current_limit:
                print(f"[EventEngine] Speed limit updated: {self.current_limit} → {candidate} km/h")
            self.current_limit = candidate

    def _best_candidate(self, ocr_reads: List[str]) -> Optional[int]:
        for text in ocr_reads:
            cleaned = text.strip().replace(" ", "")
            if cleaned.isdigit():
                val = int(cleaned)
                if val in VALID_LIMITS:
                    return val
        return None

    def _check_overspeed(self) -> Optional[Dict[str, Any]]:
        if self.current_limit is None:
            self._overspeed_active = False
            return None

        if self.ego_speed_kmh <= 0:
            self._overspeed_active = False
            return None

        threshold = self.current_limit + self._tolerance

        # إذا رجعت السرعة طبيعية، نصفر الحالة
        if self.ego_speed_kmh <= threshold:
            self._overspeed_active = False
            return None

        # إذا الحدث شغال بالفعل، لا تكرر
        if self._overspeed_active:
            return None

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
        self._overspeed_active = True
        return event

    @staticmethod
    def _severity(excess_kmh: float) -> str:
        if excess_kmh <= 20:
            return "medium"
        elif excess_kmh <= 40:
            return "high"
        return "critical"