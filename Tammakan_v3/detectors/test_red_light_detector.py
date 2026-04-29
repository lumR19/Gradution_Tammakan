"""
test_red_light_detector.py
Quick test for RedLightDetector using a real video file.
Prints events to terminal + draws colored boxes on output video.
"""

import cv2
import sys
import os

# so it can find tamakkan_tracker and light_classifier
sys.path.insert(0, r"C:\Users\Admin\Gradution_Tammakan\Tammakan_v3\BytetTrack")

from tamakkan_tracker import TamakkanTracker
from red_light_detector import RedLightDetector, EventType

# ── EDIT THESE ────────────────────────────────────────────────────────────────
WEIGHTS      = r"C:\Users\Admin\Desktop\Grad_Project\Code\Yolov11s_training_Results\tamakkan_v2_hires\weights\best.pt"
TRACKER_CFG  = r"C:\Users\Admin\Gradution_Tammakan\Tammakan_v3\BytetTrack\bytetrack_tamakkan.yaml"
INPUT_VIDEO  = r"C:\Users\Admin\Desktop\Grad_Project\Code\Datasets\final-test-data\WIN_20260428_19_01_31_Pro.mp4"   # ← change this
OUTPUT_VIDEO = r"C:\Users\Admin\Desktop\Grad_Project\Code\Light_detector_result\output2_redlight.mp4"   # ← change this
# ─────────────────────────────────────────────────────────────────────────────

tracker  = TamakkanTracker(weights=WEIGHTS, tracker_config=TRACKER_CFG,
                            conf=0.25, imgsz=1280, device="cuda:0", half=True)
detector = RedLightDetector(confirm_frames=3)

cap    = cv2.VideoCapture(INPUT_VIDEO)
fps    = cap.get(cv2.CAP_PROP_FPS)
w      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
out    = cv2.VideoWriter(OUTPUT_VIDEO, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

all_events = []

while True:
    ret, frame = cap.read()
    if not ret:
        break

    tracks = tracker.update(frame)
    events = detector.update(tracks, frame)

    for e in events:
        all_events.append(e)
        # print immediately so you see it in terminal in real time
        if e.type == EventType.RED_LIGHT_AHEAD:
            print(f"[Frame {e.frame_idx}] ⚠️  RED LIGHT AHEAD  | track={e.track_id} conf={e.confidence:.2f}")
        else:
            print(f"[Frame {e.frame_idx}] 🚨 RED LIGHT RAN    | track={e.track_id}")

    # draw tracks on frame
    for t in tracks:
        x1,y1,x2,y2 = map(int, t.bbox)
        color = (0,0,255) if t.class_id == 4 else (200,200,200)
        cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
        cv2.putText(frame, f"ID:{t.track_id} {t.class_name}",
                    (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # draw active events on frame
    for e in events:
        if e.type == EventType.RED_LIGHT_AHEAD:
            cv2.putText(frame, "⚠ RED LIGHT AHEAD", (30, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,255), 3)
        elif e.type == EventType.RED_LIGHT_RAN:
            cv2.putText(frame, "!!! RED LIGHT VIOLATION !!!", (30, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,180), 3)

    out.write(frame)

cap.release()
out.release()

# ── Summary ───────────────────────────────────────────────────────────────────
ahead_count = sum(1 for e in all_events if e.type == EventType.RED_LIGHT_AHEAD)
ran_count   = sum(1 for e in all_events if e.type == EventType.RED_LIGHT_RAN)
print(f"\n{'='*50}")
print(f"Total RED_LIGHT_AHEAD events : {ahead_count}")
print(f"Total RED_LIGHT_RAN events   : {ran_count}")
print(f"Output saved to: {OUTPUT_VIDEO}")