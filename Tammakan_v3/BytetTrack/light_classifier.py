"""
light_classifier.py
═══════════════════════════════════════════════════════════════════════════════
Traffic-light color classifier using HSV color space.

Input  : BGR cropped traffic_light bbox from YOLO (any size)
Output : {"color": "red" | "yellow" | "green" | "unknown", "confidence": float}

V2 — tuned for real LED traffic lights.
Key insight: LED bulbs have a bright white CORE (low saturation) and a
colored HALO around it (high saturation). The original v1 only counted
the halo and missed most lit lights.
"""

import cv2
import numpy as np


class LightClassifier:
    """Classify a traffic_light crop as red / yellow / green / unknown."""

    # ── HSV thresholds (OpenCV: H in [0,180], S/V in [0,255]) ────────────────
    HUE_RED_LOW = (0, 12)
    HUE_RED_HIGH = (165, 180)
    HUE_YELLOW = (13, 35)
    HUE_GREEN = (40, 95)

    # Lowered from v1: real traffic-light pixels can be less saturated than
    # synthetic test colors due to LED bloom and JPEG compression.
    SAT_MIN = 40
    VAL_MIN = 60

    # NEW in v2: a separate "bright pixel" check that catches the white-ish
    # bulb cores. Anything brighter than this counts as evidence even if its
    # saturation is too low to pass SAT_MIN.
    BRIGHT_VAL_MIN = 200      # very bright pixels (lit bulb core)
    BRIGHT_SAT_MIN = 15       # but with at least *some* color tint

    # Lowered from 10% to 3% — bulbs occupy a small fraction of the crop.
    MIN_PIXEL_PCT = 0.03

    # If the winning color is barely beating the runner-up, fall back to unknown.
    # Prevents flip-flopping between "almost red" and "almost yellow."
    MARGIN_PCT = 0.5          # winner must be at least 1.5x the runner-up

    def classify(self, bgr_crop):
        if bgr_crop is None or bgr_crop.size == 0:
            return self._unknown(0.0)
        if bgr_crop.shape[0] < 5 or bgr_crop.shape[1] < 5:
            return self._unknown(0.0)

        hsv = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2HSV)
        h = hsv[:, :, 0]
        s = hsv[:, :, 1]
        v = hsv[:, :, 2]

        # Two ways a pixel can "count":
        #   1. Standard: saturated AND not too dark
        #   2. Bright bulb core: very bright AND faintly tinted
        valid_standard = (s >= self.SAT_MIN) & (v >= self.VAL_MIN)
        valid_bright = (v >= self.BRIGHT_VAL_MIN) & (s >= self.BRIGHT_SAT_MIN)
        valid = valid_standard | valid_bright

        red_mask = (
            ((h >= self.HUE_RED_LOW[0])  & (h <= self.HUE_RED_LOW[1])) |
            ((h >= self.HUE_RED_HIGH[0]) & (h <= self.HUE_RED_HIGH[1]))
        )
        yellow_mask = (h >= self.HUE_YELLOW[0]) & (h <= self.HUE_YELLOW[1])
        green_mask  = (h >= self.HUE_GREEN[0])  & (h <= self.HUE_GREEN[1])

        total = bgr_crop.shape[0] * bgr_crop.shape[1]
        red_pct = float(np.sum(valid & red_mask)) / total
        yellow_pct = float(np.sum(valid & yellow_mask)) / total
        green_pct = float(np.sum(valid & green_mask)) / total

        scores = {"red": red_pct, "yellow": yellow_pct, "green": green_pct}
        winner = max(scores, key=scores.get)
        winner_pct = scores[winner]

        # Sorted to find the runner-up
        sorted_pcts = sorted(scores.values(), reverse=True)
        runner_up_pct = sorted_pcts[1]

        debug = {
            "red_pct": round(red_pct, 4),
            "yellow_pct": round(yellow_pct, 4),
            "green_pct": round(green_pct, 4),
        }

        # Below absolute minimum → no clear signal at all
        if winner_pct < self.MIN_PIXEL_PCT:
            return {"color": "unknown", "confidence": float(winner_pct), "debug": debug}

        # Winner not clearly ahead of runner-up → ambiguous
        if runner_up_pct > 0 and (winner_pct - runner_up_pct) / winner_pct < self.MARGIN_PCT:
            return {"color": "unknown", "confidence": float(winner_pct), "debug": debug}

        return {"color": winner, "confidence": float(winner_pct), "debug": debug}

    @staticmethod
    def _unknown(conf):
        return {"color": "unknown", "confidence": float(conf), "debug": {}}


# ── Sanity test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    classifier = LightClassifier()

    red_img = np.zeros((40, 40, 3), dtype=np.uint8); red_img[:, :] = (0, 0, 255)
    print("Solid red:   ", classifier.classify(red_img))

    green_img = np.zeros((40, 40, 3), dtype=np.uint8); green_img[:, :] = (0, 255, 0)
    print("Solid green: ", classifier.classify(green_img))

    yellow_img = np.zeros((40, 40, 3), dtype=np.uint8); yellow_img[:, :] = (0, 255, 255)
    print("Solid yellow:", classifier.classify(yellow_img))

    gray_img = np.full((40, 40, 3), 128, dtype=np.uint8)
    print("Solid gray:  ", classifier.classify(gray_img))
