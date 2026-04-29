"""
light_classifier.py
═══════════════════════════════════════════════════════════════════════════════
Traffic-light color classifier using HSV color space.

Input  : BGR cropped traffic_light bbox from YOLO (any size)
Output : {"color": "red" | "green" | "unknown", "confidence": float}

V4 changes:
- Added brightness gate: crops with no bright region → unknown immediately
- Tightened green hue range from (40,95) to (60,95) to exclude teal housings
- Unknown class now correctly rejects dark/off lights and non-bulb crops
"""

import cv2
import numpy as np


class LightClassifier:
    """Classify a traffic_light crop as red / green / unknown."""

    # ── HSV thresholds ────────────────────────────────────────────────────────
    HUE_RED_LOW  = (0,   35)   # pure red + amber/orange-red LEDs
    HUE_RED_HIGH = (165, 180)  # wraps around from magenta-red
    HUE_GREEN    = (60,  95)   # tightened: real traffic green LEDs only
                               # was (40,95) — 40-59 is olive/teal/housing color

    SAT_MIN = 40
    VAL_MIN = 60

    BRIGHT_VAL_MIN = 200
    BRIGHT_SAT_MIN = 15

    MIN_PIXEL_PCT = 0.015
    MARGIN_PCT    = 0.2

    # NEW V4: minimum fraction of crop pixels that must be "bright"
    # (V >= 180) for the crop to be considered a lit bulb at all.
    # If nothing is bright enough, the light is off or the crop is junk.
    # 1.5% is intentionally low — a tiny bulb in a large crop still passes.
    MIN_BRIGHT_FRACTION = 0.015
    BRIGHT_GATE_VAL     = 180

    def classify(self, bgr_crop):
        if bgr_crop is None or bgr_crop.size == 0:
            return self._unknown(0.0)
        if bgr_crop.shape[0] < 5 or bgr_crop.shape[1] < 5:
            return self._unknown(0.0)

        hsv = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2HSV)
        h = hsv[:, :, 0]
        s = hsv[:, :, 1]
        v = hsv[:, :, 2]

        # ── Brightness gate (V4) ──────────────────────────────────────────────
        # Reject crops where nothing is bright enough to be a lit bulb.
        # Catches: off lights, dark housings, night poles, junk crops.
        total = bgr_crop.shape[0] * bgr_crop.shape[1]
        bright_fraction = float(np.sum(v >= self.BRIGHT_GATE_VAL)) / total
        if bright_fraction < self.MIN_BRIGHT_FRACTION:
            return {"color": "unknown", "confidence": 0.0,
                    "debug": {"reason": "no_bright_region",
                              "bright_fraction": round(bright_fraction, 4)}}

        # ── Color scoring ─────────────────────────────────────────────────────
        valid_standard = (s >= self.SAT_MIN) & (v >= self.VAL_MIN)
        valid_bright   = (v >= self.BRIGHT_VAL_MIN) & (s >= self.BRIGHT_SAT_MIN)
        valid = valid_standard | valid_bright

        red_mask = (
            ((h >= self.HUE_RED_LOW[0])  & (h <= self.HUE_RED_LOW[1])) |
            ((h >= self.HUE_RED_HIGH[0]) & (h <= self.HUE_RED_HIGH[1]))
        )
        green_mask = (h >= self.HUE_GREEN[0]) & (h <= self.HUE_GREEN[1])

        red_pct   = float(np.sum(valid & red_mask))   / total
        green_pct = float(np.sum(valid & green_mask)) / total

        scores        = {"red": red_pct, "green": green_pct}
        winner        = max(scores, key=scores.get)
        winner_pct    = scores[winner]
        runner_up_pct = scores["green" if winner == "red" else "red"]

        debug = {
            "red_pct":        round(red_pct,        4),
            "green_pct":      round(green_pct,      4),
            "bright_fraction": round(bright_fraction, 4),
        }

        if winner_pct < self.MIN_PIXEL_PCT:
            return {"color": "unknown", "confidence": float(winner_pct),
                    "debug": debug}

        if runner_up_pct > 0 and \
           (winner_pct - runner_up_pct) / winner_pct < self.MARGIN_PCT:
            return {"color": "unknown", "confidence": float(winner_pct),
                    "debug": debug}

        return {"color": winner, "confidence": float(winner_pct), "debug": debug}

    @staticmethod
    def _unknown(conf):
        return {"color": "unknown", "confidence": float(conf), "debug": {}}


# ── Sanity test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    classifier = LightClassifier()

    red_img   = np.zeros((40, 40, 3), dtype=np.uint8); red_img[:]   = (0,   0,   255)
    amber_img = np.zeros((40, 40, 3), dtype=np.uint8); amber_img[:] = (0,   140, 255)
    green_img = np.zeros((40, 40, 3), dtype=np.uint8); green_img[:] = (0,   255, 0  )
    gray_img  = np.full((40, 40, 3), 128, dtype=np.uint8)
    dark_img  = np.full((40, 40, 3),  30, dtype=np.uint8)  # dark housing

    print("Solid red:        ", classifier.classify(red_img))
    print("Amber/orange-red: ", classifier.classify(amber_img))
    print("Solid green:      ", classifier.classify(green_img))
    print("Solid gray:       ", classifier.classify(gray_img))
    print("Dark housing:     ", classifier.classify(dark_img))