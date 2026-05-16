"""
main.py  (updated)
------------------
Integrates EventEngine into the Tamakkan video processing pipeline.
EventEngine receives OCR reads each frame and fires OVERSPEED events.
"""

import cv2
import os
import csv
import time
from pathlib import Path
from ultralytics import YOLO
from ocr_handler import TamakkanOCR
from event_engine import EventEngine          # ← NEW

# =========================================================
# SETTINGS
# =========================================================
MODEL_PATH   = r"D:\Gradution_Tammakan\best.pt"
VIDEO_FOLDER = r"D:\tamakkan"
OUTPUT_FOLDER = r"D:\tamakken"

TRAFFIC_SIGN_ID  = 5
CONF_THRESHOLD   = 0.50
OCR_EVERY_N_FRAMES = 5

MIN_OCR_CONF  = 0.75
MIN_BBOX_HEIGHT = 60

CACHE_TTL_FRAMES = 30
USE_GPU_FOR_OCR  = False

# ── Demo: set a fixed ego speed for offline testing (set None to disable) ──────
DEMO_EGO_SPEED_KMH = 100.0   # e.g. 95.0 to test without a phone

# =========================================================
# PROCESS THE VIDEO
# =========================================================
def process_video(video_path, model, ocr_manager, output_folder,
                  ego_speed_kmh: float = 0.0):
    video_path    = Path(video_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Could not open video: {video_path}")
        return

    fps    = cap.get(cv2.CAP_PROP_FPS) or 20.0
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_video_path = output_folder / f"{video_path.stem}_speed_output.mp4"
    output_csv_path   = output_folder / f"{video_path.stem}_speed_results.csv"
    events_csv_path   = output_folder / f"{video_path.stem}_events.csv"   # ← NEW

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out    = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))

    # ── One EventEngine per video ──────────────────────────────────────────────
    engine = EventEngine()
    engine.update_ego_speed(ego_speed_kmh)

    frame_idx = 0
    last_speeds: dict = {}
    total_ocr_calls = 0
    total_ocr_time  = 0.0

    with (
        open(output_csv_path,  'w', newline='', encoding='utf-8') as f_det,
        open(events_csv_path,  'w', newline='', encoding='utf-8') as f_evt,
    ):
        det_writer = csv.writer(f_det)
        det_writer.writerow(["frame", "speed", "confidence", "bbox_height",
                              "x1", "y1", "x2", "y2"])

        evt_writer = csv.writer(f_evt)
        evt_writer.writerow(["frame", "type", "severity", "ego_speed",
                              "limit", "excess_kmh", "message_en"])

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            results = model.predict(frame, conf=CONF_THRESHOLD,
                                    device="cpu", verbose=False)
            frame_ocr_reads: list[str] = []   # collect OCR hits this frame

            for r in results:
                if r.boxes is None:
                    continue

                for box in r.boxes:
                    cls  = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    if cls != TRAFFIC_SIGN_ID:
                        continue

                    h, w = frame.shape[:2]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)

                    cropped_sign = frame[y1:y2, x1:x2]
                    if cropped_sign.size == 0:
                        continue

                    bbox_height = y2 - y1
                    region_key  = f"{x1//20}_{y1//20}_{x2//20}_{y2//20}"
                    speed       = ""

                    # Cache lookup
                    cached = last_speeds.get(region_key)
                    if cached and (frame_idx - cached["last_seen"] <= CACHE_TTL_FRAMES):
                        speed = cached["speed"]

                    # OCR gating
                    should_run_ocr = (
                        frame_idx % OCR_EVERY_N_FRAMES == 0 and
                        bbox_height >= MIN_BBOX_HEIGHT and
                        conf >= MIN_OCR_CONF
                    )

                    if should_run_ocr:
                        t0 = time.perf_counter()
                        detected_speed = ocr_manager.read_speed_sign(cropped_sign)
                        total_ocr_time += time.perf_counter() - t0
                        total_ocr_calls += 1

                        if detected_speed:
                            speed = detected_speed
                            last_speeds[region_key] = {
                                "speed": detected_speed,
                                "last_seen": frame_idx,
                            }

                    if not speed:
                        continue

                    if region_key in last_speeds:
                        last_speeds[region_key]["last_seen"] = frame_idx

                    frame_ocr_reads.append(speed)   # ← feed to engine

                    print(
                        f"[{video_path.name}] Frame {frame_idx}: "
                        f"Speed={speed} | conf={conf:.2f} | h={bbox_height}"
                    )

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        frame, f"Speed: {speed}",
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2,
                    )

                    det_writer.writerow([
                        frame_idx, speed, round(conf, 4),
                        bbox_height, x1, y1, x2, y2,
                    ])

            # ── EventEngine: update limit + check overspeed ────────────────────
            event = engine.process_frame(frame_ocr_reads)

            if event:
                print(
                    f"  ⚠  OVERSPEED | {event['current_speed']} km/h "
                    f"in {event['limit']} zone | {event['message_en']}"
                )
                evt_writer.writerow([
                    frame_idx,
                    event["type"],
                    event["severity"],
                    event["current_speed"],
                    event["limit"],
                    event["excess_kmh"],
                    event["message_en"],
                ])

                # Overlay warning on frame
                _draw_overspeed_overlay(frame, event)

            out.write(frame)
            frame_idx += 1

    cap.release()
    out.release()

    print(f"\nDone: {video_path.name}")
    print(f"  Video  → {output_video_path}")
    print(f"  CSV    → {output_csv_path}")
    print(f"  Events → {events_csv_path}")
    if total_ocr_calls:
        print(f"  OCR avg: {total_ocr_time/total_ocr_calls:.4f}s over "
              f"{total_ocr_calls} calls")
    print("-" * 60)


def _draw_overspeed_overlay(frame, event: dict):
    """Stamp a red warning banner onto the frame."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 80), (w, h), (0, 0, 200), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    msg = (
        f"OVERSPEED  {event['current_speed']:.0f} / {event['limit']} km/h  "
        f"[{event['severity'].upper()}]"
    )
    cv2.putText(
        frame, msg,
        (12, h - 25),
        cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2,
    )


# =========================================================
# MAIN
# =========================================================
def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    print("Loading YOLO model...")
    model = YOLO(MODEL_PATH)

    print("Loading EasyOCR...")
    ocr_manager = TamakkanOCR(use_gpu=USE_GPU_FOR_OCR)

    ego_speed = DEMO_EGO_SPEED_KMH or 0.0
    if ego_speed:
        print(f"[Demo mode] Ego speed fixed at {ego_speed} km/h")

    video_extensions = [".mp4", ".avi", ".mov", ".mkv"]
    videos = []
    for ext in video_extensions:
        videos.extend(Path(VIDEO_FOLDER).glob(f"*{ext}"))

    if not videos:
        print("No videos found in:", VIDEO_FOLDER)
        return

    print(f"Found {len(videos)} video(s).\n")

    for video_path in videos:
        process_video(video_path, model, ocr_manager, OUTPUT_FOLDER,
                      ego_speed_kmh=ego_speed)

    print("All videos processed successfully.")


if __name__ == "__main__":
    main()