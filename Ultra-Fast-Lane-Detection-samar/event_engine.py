from typing import Optional
import time


COOLDOWN_SECONDS    = 3.0
FRAMES_TO_CONFIRM   = 15
DEPARTURE_THRESHOLD = 80
IMAGE_WIDTH         = 800


class EventEngine:
    """
    Watches the lane detector output frame by frame and fires a
    LANE_DEPARTURE event when the car has been drifting for long enough
    to be considered a real departure rather than a momentary wobble.

    Call update() every frame with the list from LaneDetector.update().
    Returns an Event dict when something fires, None when everything is fine.
    """

    def __init__(
        self,
        threshold_px:       int   = DEPARTURE_THRESHOLD,
        frames_to_confirm:  int   = FRAMES_TO_CONFIRM,
        cooldown_seconds:   float = COOLDOWN_SECONDS,
        image_width:        int   = IMAGE_WIDTH,
    ):
        self.threshold_px      = threshold_px
        self.frames_to_confirm = frames_to_confirm
        self.cooldown_seconds  = cooldown_seconds
        self.image_width       = image_width

        self._consecutive_frames = 0
        self._last_fired_at: Optional[float] = None
        self._offset_history: list = []


    def _pick_ego_lanes(self, lanes: list):
        """
        Picks the two lane boundaries the car is currently driving between.

        We only filter by max distance from center — no minimum distance.
        Removing the minimum means we don't accidentally discard a valid
        ego lane just because the car is close to it, which is exactly
        what happens during a real departure.

        We also don't require both lanes to exist. If only one boundary
        is visible we still return what we have so the caller can decide
        what to do with partial information.
        """
        car_center   = self.image_width / 2

        # anything more than 380px from center is almost certainly a barrier,
        # outer road edge, or sidewalk — not the lane the car is driving in
        max_distance = 380

        left_candidates = [
            l for l in lanes
            if l['x_at_bottom'] < car_center
            and (car_center - l['x_at_bottom']) <= max_distance
        ]

        right_candidates = [
            l for l in lanes
            if l['x_at_bottom'] >= car_center
            and (l['x_at_bottom'] - car_center) <= max_distance
        ]

        ego_left  = max(left_candidates,  key=lambda l: l['x_at_bottom']) if left_candidates  else None
        ego_right = min(right_candidates, key=lambda l: l['x_at_bottom']) if right_candidates else None

        return ego_left, ego_right


    def _calculate_offset(self, ego_left, ego_right) -> Optional[float]:
        """
        Calculates how far the car center is from the lane center.

        Works with both lanes, or just one if the other isn't visible.
        Returns None only when we have absolutely nothing to work with.

        Positive offset = car is to the right of lane center.
        Negative offset = car is to the left of lane center.
        """
        car_center = self.image_width / 2

        if ego_left is not None and ego_right is not None:
            # ideal case — both boundaries visible, use their midpoint
            lane_center = (ego_left['x_at_bottom'] + ego_right['x_at_bottom']) / 2
            return car_center - lane_center

        if ego_left is not None and ego_right is None:
            # only left boundary visible.
            # a normal driving position puts the left lane roughly 150-200px
            # from center. if it's much closer the car is drifting left.
            expected_left_distance = 180
            actual_left_distance   = car_center - ego_left['x_at_bottom']
            return expected_left_distance - actual_left_distance

        if ego_right is not None and ego_left is None:
            # only right boundary visible.
            # same logic mirrored for the right side.
            expected_right_distance = 180
            actual_right_distance   = ego_right['x_at_bottom'] - car_center
            return actual_right_distance - expected_right_distance

        return None


    def _check_lane_departure(self, lanes: list) -> Optional[dict]:
        ego_left, ego_right = self._pick_ego_lanes(lanes)
        offset              = self._calculate_offset(ego_left, ego_right)

        # no usable lane data at all this frame — skip it but don't reset.
        # a few frames of missing detection shouldn't cancel a real departure
        # that was already building up.
        if offset is None:
            return None

        if abs(offset) > self.threshold_px:
            self._consecutive_frames += 1
            self._offset_history.append(offset)
        else:
            # car is comfortably within lane — reset everything
            self._consecutive_frames = 0
            self._offset_history.clear()
            return None

        # haven't seen enough consecutive frames yet to call it a real departure
        if self._consecutive_frames < self.frames_to_confirm:
            return None

        # check cooldown so we don't spam the same alert repeatedly
        now = time.time()
        if self._last_fired_at is not None:
            if now - self._last_fired_at < self.cooldown_seconds:
                return None

        # confirmed departure — fire the event
        self._last_fired_at      = now
        self._consecutive_frames = 0

        avg_offset = sum(self._offset_history) / len(self._offset_history)
        self._offset_history.clear()

        side = 'right' if avg_offset > 0 else 'left'
        return self._build_event(avg_offset, side)


    def _build_event(self, offset_px: float, side: str) -> dict:
        if side == 'right':
            message_en = "Lane departure warning: vehicle drifting to the right"
            message_ar = "تحذير: السيارة تنحرف نحو اليمين"
        else:
            message_en = "Lane departure warning: vehicle drifting to the left"
            message_ar = "تحذير: السيارة تنحرف نحو اليسار"

        return {
            'type'       : 'LANE_DEPARTURE',
            'severity'   : 'medium',
            'side'       : side,
            'offset_px'  : round(offset_px, 1),
            'message_en' : message_en,
            'message_ar' : message_ar,
            'timestamp'  : time.time(),
        }


    def update(self, lanes: list) -> Optional[dict]:
        """
        Call this every frame with the output of LaneDetector.update().
        Returns an Event dict when a departure is confirmed, None otherwise.
        """
        return self._check_lane_departure(lanes)


    def reset(self):
        """
        Resets all state. Call this when starting a new session or
        after a long gap in processing.
        """
        self._consecutive_frames = 0
        self._last_fired_at      = None
        self._offset_history.clear()