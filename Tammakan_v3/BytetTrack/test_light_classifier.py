"""
test_light_classifier.py
═══════════════════════════════════════════════════════════════════════════════
Test LightClassifier accuracy against real sorted dashcam crops.

Reads from:
    crops/red/      → expects classifier to return "red"
    crops/green/    → expects classifier to return "green"
    crops/yellow/   → expects classifier to return "yellow"   (skipped if empty)
    crops/unknown/  → expects classifier to return "unknown"

Outputs:
    - Per-class accuracy printed to terminal
    - A confusion matrix (what got predicted as what)
    - crops/wrong/<expected>_as_<predicted>/  ← misclassified crops copied here
      so you can visually inspect where the classifier is failing.

Run with:
python test_light_classifier.py
    
"""

import shutil
from pathlib import Path
from collections import defaultdict
import cv2

from light_classifier import LightClassifier


# ── PATHS ─────────────────────────────────────────────────────────────────────
CROPS_ROOT = Path("crops")
WRONG_DIR = Path("crops/wrong")

# Expected-color folders to test
CLASSES = ["red", "green", "unknown"]


def main():
    classifier = LightClassifier()

    # Wipe and recreate the wrong/ folder so we don't mix runs
    if WRONG_DIR.exists():
        shutil.rmtree(WRONG_DIR)
    WRONG_DIR.mkdir(parents=True)

    # Stats: confusion[expected][predicted] = count
    confusion = defaultdict(lambda: defaultdict(int))
    per_class_total = defaultdict(int)
    per_class_correct = defaultdict(int)
    overall_total = 0
    overall_correct = 0

    print("═" * 60)
    print("Testing LightClassifier on real crops")
    print("═" * 60)

    for expected in CLASSES:
        folder = CROPS_ROOT / expected
        if not folder.exists():
            print(f"\n[{expected}] folder does not exist — skipping")
            continue

        crops = list(folder.glob("*.jpg")) + list(folder.glob("*.png"))
        if not crops:
            print(f"\n[{expected}] folder is empty — skipping")
            continue

        print(f"\n[{expected}] testing {len(crops)} crops...")

        for crop_path in crops:
            img = cv2.imread(str(crop_path))
            if img is None:
                print(f"  ⚠ Could not read: {crop_path.name}")
                continue

            result = classifier.classify(img)
            predicted = result["color"]

            # Track stats
            confusion[expected][predicted] += 1
            per_class_total[expected] += 1
            overall_total += 1

            if predicted == expected:
                per_class_correct[expected] += 1
                overall_correct += 1
            else:
                # Save misclassified crop for inspection
                wrong_subdir = WRONG_DIR / f"{expected}_as_{predicted}"
                wrong_subdir.mkdir(parents=True, exist_ok=True)
                shutil.copy(crop_path, wrong_subdir / crop_path.name)

    # ── Print results ────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("RESULTS")
    print("═" * 60)

    print("\nPer-class accuracy:")
    for cls in CLASSES:
        if per_class_total[cls] == 0:
            continue
        correct = per_class_correct[cls]
        total = per_class_total[cls]
        pct = 100 * correct / total
        bar = "█" * int(pct / 5)  # visual bar
        print(f"  {cls:10s}  {correct:4d}/{total:4d}  ({pct:5.1f}%)  {bar}")

    if overall_total > 0:
        overall_pct = 100 * overall_correct / overall_total
        print(f"\n  {'OVERALL':10s}  {overall_correct:4d}/{overall_total:4d}  ({overall_pct:5.1f}%)")

    # ── Confusion matrix ─────────────────────────────────────────────────────
    print("\nConfusion matrix (rows = actual, columns = predicted):")
    all_predicted = ["red", "green", "unknown"]
    header = "  expected \\ predicted | " + " | ".join(f"{p:>8}" for p in all_predicted)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for expected in CLASSES:
        if per_class_total[expected] == 0:
            continue
        row = f"  {expected:20s} | "
        row += " | ".join(f"{confusion[expected][p]:>8}" for p in all_predicted)
        print(row)

    # ── Misclassification summary ────────────────────────────────────────────
    print("\nMisclassified crops saved to:")
    if any(WRONG_DIR.iterdir()):
        for subdir in sorted(WRONG_DIR.iterdir()):
            if subdir.is_dir():
                count = len(list(subdir.glob("*")))
                print(f"  {subdir}  ({count} crops)")
        print("\nOpen these folders to see where the classifier is failing.")
        print("Common patterns to look for:")
        print("  - red_as_unknown    → red lights too dim, lower SAT_MIN")
        print("  - green_as_unknown  → green LEDs not saturated enough")
        print("  - red_as_yellow     → orange/amber reds, narrow HUE_RED_LOW range")
        print("  - unknown_as_red    → off lights with red housing reflections")
    else:
        print("  (none — perfect classification!)")

    print("\n✅ Done")


if __name__ == "__main__":
    main()
