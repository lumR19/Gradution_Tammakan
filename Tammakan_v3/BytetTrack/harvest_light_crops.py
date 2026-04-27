"""
harvest_light_crops.py
═══════════════════════════════════════════════════════════════════════════════
Run YOLO across MULTIPLE videos, harvest traffic_light crops, save to disk.

Filenames are prefixed with the video name so crops from different videos
never collide — your existing sorted crops/red/ and crops/green/ stay intact.

Output structure:
    crops/unsorted/
        clip01_frame_00042_box_0.jpg
        clip01_frame_00103_box_1.jpg
        clip02_frame_00021_box_0.jpg
        ...

Then YOU sort these into:
    crops/red/
    crops/green/
    crops/yellow/

Run with:
    python harvest_light_crops.py
"""

import cv2
from pathlib import Path
from ultralytics import YOLO

# ── EDIT THESE ─────────────────────────────────────────────────────────────────
WEIGHTS = r"C:\Users\Admin\Desktop\Grad_Project\Code\Yolov11s_training_Results\tamakkan_v2_hires\weights\best.pt"

# Point this at the FOLDER containing your dashcam clips
# The script will process every .mp4 in this folder
VIDEO_FOLDER = r"C:\Users\Admin\Desktop\Grad_Project\Code\Datasets\Dashcam_clips"

# Output folder (relative to where you run the script)
OUTPUT_DIR = Path("crops/unsorted")

# ── SETTINGS ──────────────────────────────────────────────────────────────────
TRAFFIC_LIGHT_CLASS_ID = 4   # 4 = traffic_light from your YOLO data.yaml
CONF_THRESHOLD = 0.35        # only confident detections
MIN_CROP_HEIGHT = 15         # skip tiny far-away lights — too pixelated to test
SAMPLE_EVERY_N_FRAMES = 8    # don't save every frame — bumped up for variety
MAX_CROPS_PER_VIDEO = 60     # cap per video so one long red doesn't dominate

# Skip videos you've ALREADY harvested from (manual list of filenames)
ALREADY_DONE = [
    # "20260218184427_0060.mp4",   # uncomment when you want to skip a video
]

VIDEO_EXTENSIONS = [".mp4", ".avi", ".mov", ".mkv"]


def process_video(video_path, model, output_dir, prefix):
    """Process one video, save crops with the given prefix on filenames."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"  ⚠ Could not open: {video_path.name}")
        return 0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"  Frames: {total_frames}")

    frame_idx = 0
    saved_count = 0

    while saved_count < MAX_CROPS_PER_VIDEO:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % SAMPLE_EVERY_N_FRAMES != 0:
            frame_idx += 1
            continue

        results = model.predict(frame, conf=CONF_THRESHOLD, verbose=False)
        result = results[0]

        if result.boxes is None or len(result.boxes) == 0:
            frame_idx += 1
            continue

        for box_idx, box in enumerate(result.boxes):
            cls_id = int(box.cls[0])
            if cls_id != TRAFFIC_LIGHT_CLASS_ID:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            crop = frame[y1:y2, x1:x2]

            if crop.shape[0] < MIN_CROP_HEIGHT:
                continue

            filename = output_dir / f"{prefix}_frame_{frame_idx:05d}_box_{box_idx}.jpg"
            cv2.imwrite(str(filename), crop)
            saved_count += 1

            if saved_count >= MAX_CROPS_PER_VIDEO:
                break

        frame_idx += 1

    cap.release()
    return saved_count


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading YOLO model...")
    model = YOLO(WEIGHTS)
    print("✅ Model loaded\n")

    # Find all videos in the folder
    folder = Path(VIDEO_FOLDER)
    videos = []
    for ext in VIDEO_EXTENSIONS:
        videos.extend(folder.glob(f"*{ext}"))

    # Filter out already-done videos
    videos = [v for v in videos if v.name not in ALREADY_DONE]

    if not videos:
        print(f"No videos found in {VIDEO_FOLDER}")
        return

    print(f"Found {len(videos)} video(s) to process\n")
    print(f"Settings:")
    print(f"  Sample every {SAMPLE_EVERY_N_FRAMES} frames")
    print(f"  Max {MAX_CROPS_PER_VIDEO} crops per video")
    print(f"  Min crop height: {MIN_CROP_HEIGHT}px")
    print()

    total_saved = 0
    for i, video_path in enumerate(videos, 1):
        # Use video filename (without extension) as prefix
        prefix = video_path.stem.replace(" ", "_")
        print(f"[{i}/{len(videos)}] Processing: {video_path.name}")

        count = process_video(video_path, model, OUTPUT_DIR, prefix)
        total_saved += count
        print(f"  ✅ Saved {count} crops\n")

    print(f"{'='*60}")
    print(f"✅ Done. Total crops saved: {total_saved}")
    print(f"   Folder: {OUTPUT_DIR.absolute()}")
    print(f"{'='*60}")
    print("\nNext: open the unsorted folder and copy crops into:")
    print("  crops/red/")
    print("  crops/green/")
    print("  crops/yellow/")
    print("(Hold Ctrl while dragging to copy, not move.)")


if __name__ == "__main__":
    main()
