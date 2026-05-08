import cv2
import time
import os
import numpy as np
from lane_detector import LaneDetector, visualize, IMG_W, IMG_H, ROI_TOP, ROI_BOTTOM, LANE_COLORS
from event_engine import EventEngine


WEIGHTS    = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\culane_18.pth'
VIDEO_IN   = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\dataset_input_forTEST\12ArduCam.mp4'
OUTPUT_DIR = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\test_output_Culane'

os.makedirs(OUTPUT_DIR, exist_ok=True)
VIDEO_OUT = os.path.join(
    OUTPUT_DIR,
    os.path.splitext(os.path.basename(VIDEO_IN))[0] + '_with_events.mp4'
)

detector = LaneDetector(weights_path=WEIGHTS)
engine   = EventEngine(
    threshold_px      = 80,
    frames_to_confirm = 15,
    cooldown_seconds  = 3.0,
    image_width       = IMG_W,
)

cap = cv2.VideoCapture(VIDEO_IN)
# for live camera replace the line above with:
# cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise FileNotFoundError(f"could not open: {VIDEO_IN}")

total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps          = cap.get(cv2.CAP_PROP_FPS)
orig_w       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
orig_h       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
writer = cv2.VideoWriter(VIDEO_OUT, fourcc, fps, (IMG_W, IMG_H))

frame_idx   = 0
event_log   = []
video_start = time.time()

print(f"processing {os.path.basename(VIDEO_IN)}\n")


def draw_debug_overlay(canvas, lanes, ego_left, ego_right, offset):
    """
    Draws a debug panel in the bottom-right corner showing exactly which
    lanes the engine picked as ego left and ego right this frame, and
    what the current offset is.

    This makes it clear during a demo whether the engine had enough
    information to make a decision or not.
    """
    panel_x = IMG_W - 220
    panel_y = IMG_H - 95
    panel_w = 215
    panel_h = 90

    # semi-transparent dark background for the panel
    overlay = canvas.copy()
    cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h),
                  (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.7, canvas, 0.3, 0, canvas)

    cv2.putText(canvas, "ego lane debug",
                (panel_x + 5, panel_y + 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1)

    # ego left status
    if ego_left is not None:
        left_txt   = f"left   x={ego_left['x_at_bottom']:.0f}  conf={ego_left['confidence']:.2f}"
        left_color = (80, 255, 80)   # green — found
    else:
        left_txt   = "left   not found"
        left_color = (80, 80, 255)   # red — missing

    cv2.putText(canvas, left_txt,
                (panel_x + 5, panel_y + 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, left_color, 1)

    # ego right status
    if ego_right is not None:
        right_txt   = f"right  x={ego_right['x_at_bottom']:.0f}  conf={ego_right['confidence']:.2f}"
        right_color = (80, 255, 80)
    else:
        right_txt   = "right  not found"
        right_color = (80, 80, 255)

    cv2.putText(canvas, right_txt,
                (panel_x + 5, panel_y + 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, right_color, 1)

    # offset value
    if offset is not None:
        offset_txt   = f"offset {offset:+.0f}px"
        offset_color = (0, 80, 220) if abs(offset) > 80 else (80, 220, 80)
    else:
        offset_txt   = "offset  unknown"
        offset_color = (120, 120, 120)

    cv2.putText(canvas, offset_txt,
                (panel_x + 5, panel_y + 64),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, offset_color, 1)

    # confirmation bar — shows how close we are to triggering an alarm
    conf_frames  = engine._consecutive_frames
    conf_max     = engine.frames_to_confirm
    bar_fill     = int((conf_frames / conf_max) * (panel_w - 10)) if conf_max > 0 else 0
    bar_fill     = min(bar_fill, panel_w - 10)
    bar_color    = (0, 80, 220) if conf_frames > conf_max * 0.7 else (0, 180, 80)

    cv2.rectangle(canvas,
                  (panel_x + 5, panel_y + 72),
                  (panel_x + 5 + panel_w - 10, panel_y + 82),
                  (60, 60, 60), -1)
    if bar_fill > 0:
        cv2.rectangle(canvas,
                      (panel_x + 5, panel_y + 72),
                      (panel_x + 5 + bar_fill, panel_y + 82),
                      bar_color, -1)

    cv2.putText(canvas, f"confirm {conf_frames}/{conf_max}",
                (panel_x + 5, panel_y + 88),
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, (160, 160, 160), 1)

    # draw markers on the actual lane lines to show which ones were picked
    if ego_left is not None:
        ex = int(ego_left['x_at_bottom'])
        cv2.circle(canvas, (ex, ROI_BOTTOM - 5), 8, (80, 255, 80), -1)
        cv2.putText(canvas, "EL", (ex - 10, ROI_BOTTOM - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 255, 80), 1)

    if ego_right is not None:
        ex = int(ego_right['x_at_bottom'])
        cv2.circle(canvas, (ex, ROI_BOTTOM - 5), 8, (80, 255, 80), -1)
        cv2.putText(canvas, "ER", (ex - 10, ROI_BOTTOM - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 255, 80), 1)

    # draw lane center marker
    if ego_left is not None and ego_right is not None:
        lc = int((ego_left['x_at_bottom'] + ego_right['x_at_bottom']) / 2)
        cv2.line(canvas, (lc, ROI_BOTTOM - 15), (lc, ROI_BOTTOM), (255, 255, 255), 2)

    # draw car center marker
    cv2.line(canvas, (IMG_W // 2, ROI_BOTTOM - 15),
             (IMG_W // 2, ROI_BOTTOM), (0, 200, 255), 2)


while True:
    ret, frame = cap.read()
    if not ret:
        print("reached end of video")
        break

    frame_idx += 1

    lanes = detector.update(frame)
    event = engine.update(lanes)

    if event:
        event_log.append(event)
        print(f"  frame {frame_idx}  {event['type']}  "
              f"side {event['side']}  "
              f"offset {event['offset_px']:+.0f}px  "
              f"{event['message_en']}")

    # get ego lane info for the debug overlay
    ego_left, ego_right = engine._pick_ego_lanes(lanes)
    offset              = engine._calculate_offset(ego_left, ego_right)

    canvas = visualize(frame, lanes, show_roi=True)

    # draw the debug overlay showing ego lane selection
    draw_debug_overlay(canvas, lanes, ego_left, ego_right, offset)

    # show departure alert when an event fired recently
    recent_event = next(
        (e for e in reversed(event_log)
         if time.time() - e['timestamp'] < 2.0),
        None
    )

    if recent_event:
        cv2.rectangle(canvas, (0, IMG_H - 40), (IMG_W, IMG_H), (0, 0, 200), -1)
        cv2.putText(canvas, recent_event['message_en'],
                    (10, IMG_H - 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        cv2.putText(canvas, recent_event['message_ar'],
                    (500, IMG_H - 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        side    = recent_event['side']
        arrow_x = 750 if side == 'right' else 50
        cv2.arrowedLine(canvas, (IMG_W // 2, IMG_H - 50),
                        (arrow_x, IMG_H - 50),
                        (255, 255, 255), 3, tipLength=0.4)
    else:
        cv2.rectangle(canvas, (0, IMG_H - 8), (IMG_W, IMG_H), (0, 140, 0), -1)

    elapsed = time.time() - video_start
    avg_fps = frame_idx / elapsed if elapsed > 0 else 0
    eta     = (total_frames - frame_idx) / avg_fps if avg_fps > 0 else 0

    overlay = [
        f"frame {frame_idx} of {total_frames}",
        f"{avg_fps:.1f} FPS avg",
        f"eta {int(eta//60)}m {int(eta%60)}s",
        f"lanes {len(lanes)}",
    ]
    for i, txt in enumerate(overlay):
        cv2.putText(canvas, txt, (10, 18 + i * 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
        cv2.putText(canvas, txt, (10, 18 + i * 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    writer.write(canvas)

    if frame_idx % 25 == 0:
        print(f"  frame {frame_idx:>4} of {total_frames}   "
              f"{avg_fps:.1f} FPS   "
              f"events {len(event_log)}   "
              f"ego L{'yes' if ego_left else 'no '} R{'yes' if ego_right else 'no '}   "
              f"offset {f'{offset:+.0f}px' if offset is not None else 'unknown'}")

cap.release()
writer.release()
total_time = time.time() - video_start

print(f"\ndone in {total_time:.1f} seconds")
print(f"departure events fired  {len(event_log)}")
for e in event_log:
    print(f"  {e['type']}  {e['side']}  offset {e['offset_px']:+.0f}px")
print(f"\noutput saved to {VIDEO_OUT}")