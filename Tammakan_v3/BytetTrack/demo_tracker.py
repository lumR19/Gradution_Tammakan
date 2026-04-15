"""
Tamakkan tracker demo — run TamakkanTracker on a video file.

Saves annotated video to disk with bounding boxes + persistent track IDs.
Use this to visually verify tracking quality before deploying.
"""

import cv2
import time
from pathlib import Path
from tamakkan_tracker import TamakkanTracker

# ── PATHS ─────────────────────────────────────────────────────────────────────
WEIGHTS = r"C:\Users\Admin\Desktop\Grad_Project\Code\Yolov11s_training_Results\tamakkan_v2_hires\weights\best.pt"
TRACKER_CONFIG = r"C:\Users\Admin\Gradution_Tammakan\Tammakan_v3\BytetTrack\bytetrack_tamakkan.yaml"
INPUT_VIDEO = r"C:\Users\Admin\Desktop\Grad_Project\Code\Datasets\Dashcam_clips\20260218184427_0060.mp4"  # ← change this
OUTPUT_VIDEO = r"C:\Users\Admin\Desktop\Grad_Project\Code\Bytetrack_Results_V3\dashcam6_tracked.mp4"  # ← change this

# ── COLOR PER CLASS (BGR for OpenCV) ──────────────────────────────────────────
# Distinct colors so different classes are easy to tell apart.
CLASS_COLORS = {
    0: (255, 100, 100),   # car           — light blue
    1: (255, 50,  200),   # truck         — magenta
    2: (200, 50,  255),   # bus           — purple
    3: (50,  255, 50),    # person        — green
    4: (50,  255, 255),   # traffic_light — yellow
    5: (50,  150, 255),   # traffic_sign  — orange
    6: (50,  50,  255),   # VRU           — red (highest visual priority)
}


def draw_track(frame, track, color):
    """Draw bounding box + ID label for one track."""
    x1, y1, x2, y2 = map(int, track.bbox)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    label = f"ID:{track.track_id} {track.class_name} {track.confidence:.2f}"
    
    # Label background for readability
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
    cv2.putText(frame, label, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)


def main():
    # ── Initialize tracker ────────────────────────────────────────────────────
    print("Loading TamakkanTracker...")
    tracker = TamakkanTracker(
        weights=WEIGHTS,
        tracker_config=TRACKER_CONFIG,
        conf=0.25,
        imgsz=1280,
        device="cuda:0",
        half=True,
    )
    print("✅ Tracker ready\n")

    # ── Open video ────────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(INPUT_VIDEO)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {INPUT_VIDEO}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Input: {width}x{height} @ {fps:.1f}fps, {total_frames} frames")

    # ── Setup output writer ───────────────────────────────────────────────────
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (width, height))

    # ── Process loop ──────────────────────────────────────────────────────────
    frame_idx = 0
    inference_times = []
    unique_ids = set()

    t_start = time.time()
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        t0 = time.time()
        tracks = tracker.update(frame)
        inference_times.append(time.time() - t0)

        # Track unique IDs seen across the whole video
        for t in tracks:
            unique_ids.add(t.track_id)
            color = CLASS_COLORS.get(t.class_id, (200, 200, 200))
            draw_track(frame, t, color)

        # Overlay frame info
        info = f"Frame {frame_idx+1}/{total_frames} | Active: {len(tracks)} | Total IDs: {len(unique_ids)}"
        cv2.putText(frame, info, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        out.write(frame)
        frame_idx += 1

        # Progress every 30 frames
        if frame_idx % 30 == 0:
            avg_ms = sum(inference_times[-30:]) / 30 * 1000
            print(f"  Frame {frame_idx}/{total_frames} | "
                  f"avg inference: {avg_ms:.1f}ms | "
                  f"active tracks: {len(tracks)}")

    # ── Cleanup ───────────────────────────────────────────────────────────────
    cap.release()
    out.release()

    elapsed = time.time() - t_start
    avg_ms = sum(inference_times) / len(inference_times) * 1000
    realtime_fps = frame_idx / elapsed

    print(f"\n{'='*60}")
    print(f"✅ Done. Output saved to: {OUTPUT_VIDEO}")
    print(f"{'='*60}")
    print(f"Total frames:        {frame_idx}")
    print(f"Total unique IDs:    {len(unique_ids)}")
    print(f"Avg inference time:  {avg_ms:.1f}ms")
    print(f"Effective FPS:       {realtime_fps:.1f}")
    print(f"Realtime capable:    {'YES ✅' if realtime_fps >= fps else 'NO ❌ (too slow)'}")


if __name__ == "__main__":
    main()