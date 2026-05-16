"""
speed_reader_video_only.py
--------------------------
Tamakkan Speed Limit Detector 
Detects speed limit signs (20-120 km/h) from video using YOLO + EasyOCR.
Output: annotated video with speed alert overlay.
"""
 
import cv2
import re
from pathlib import Path
from ultralytics import YOLO
import easyocr
 
# ═══════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════
MODEL_PATH    = r"D:\Gradution_Tammakan\best.pt"
VIDEO_FOLDER  = r"D:\tamakkan"
OUTPUT_FOLDER = r"D:\tamakken"
 
SIGN_CLASS_ID  = 5      # YOLO class index for speed limit signs
CONF_THRESHOLD = 0.50   # YOLO detection confidence threshold
OCR_EVERY_N    = 5      # Run OCR once every N frames (performance)
MIN_BOX_HEIGHT = 50     # Ignore detections smaller than this (pixels)
CACHE_FRAMES   = 30     # Reuse cached OCR result for this many frames
 
VALID_SPEEDS = {"20","30","40","50","60","70","80","90","100","110","120"}
 
 
# ═══════════════════════════════════════════════════════
# IMAGE PREPROCESSING FOR OCR
# ═══════════════════════════════════════════════════════
def preprocess(crop):
    """
    Returns multiple processed versions of the crop.
    Tries Otsu, inverted Otsu, and raw grayscale.
    Stops at the first one that yields a valid speed.
    """
    scale = 3.0 if crop.shape[0] < 80 else 2.0
    big   = cv2.resize(crop, None, fx=scale, fy=scale,
                       interpolation=cv2.INTER_CUBIC)
    gray  = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 0, 255,
                          cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return [th, cv2.bitwise_not(th), gray]
 
 
# ═══════════════════════════════════════════════════════
# OCR SPEED READER
# ═══════════════════════════════════════════════════════
def read_speed(crop, reader):
    """
    Reads a speed value from a cropped sign image.
    Returns the speed string (e.g. "80") or empty string if not found.
    """
    for img in preprocess(crop):
        results = reader.readtext(img, detail=0)
        text    = re.sub(r'[^0-9]', '', " ".join(results))
        if text in VALID_SPEEDS:
            return text
    return ""
 
 
# ═══════════════════════════════════════════════════════
# DRAW ALERT OVERLAY ON FRAME
# ═══════════════════════════════════════════════════════
def draw_alert(frame, speed, x1, y1, x2, y2):
    """Draws a green bounding box and a banner alert on the frame."""
    # Green box around the sign
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 80), 3)
 
    # Green banner at the top of the frame
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 75), (0, 120, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
 
    cv2.putText(frame, f"Speed Limit: {speed} km/h", (15, 32),
                cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, "Speed Limit Detected - Drive Safely", (15, 62),
                cv2.FONT_HERSHEY_DUPLEX, 0.65, (200, 255, 200), 1, cv2.LINE_AA)
 
    # Speed label above the bounding box
    cv2.putText(frame, f"{speed} km/h", (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 200, 80), 2, cv2.LINE_AA)
 
 
# ═══════════════════════════════════════════════════════
# MAIN VIDEO PROCESSOR
# ═══════════════════════════════════════════════════════
def process_video(video_path, model, reader):
    video_path    = Path(video_path)
    output_folder = Path(OUTPUT_FOLDER)
    output_folder.mkdir(parents=True, exist_ok=True)
 
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"[ERROR] Cannot open: {video_path}")
        return
 
    fps    = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
 
    out_video = output_folder / f"{video_path.stem}_speed_alert.mp4"
 
    writer = cv2.VideoWriter(
        str(out_video),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps, (width, height),
    )
 
    cache        = {}    # region_key -> {speed, last_seen}
    frame_idx    = 0
    last_printed = None  # Only print when speed changes
    detections   = 0
 
    print(f"\nProcessing: {video_path.name}")
 
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
 
        results = model.predict(frame, conf=CONF_THRESHOLD,
                                device="cpu", verbose=False)
 
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                if int(box.cls[0]) != SIGN_CLASS_ID:
                    continue
 
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                h_f, w_f        = frame.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w_f, x2), min(h_f, y2)
 
                crop = frame[y1:y2, x1:x2]
                if crop.size == 0:
                    continue
 
                bbox_h     = y2 - y1
                region_key = f"{x1//20}_{y1//20}_{x2//20}_{y2//20}"
                speed      = ""
 
                # Use cached result if still fresh
                cached = cache.get(region_key)
                if cached and (frame_idx - cached["last_seen"] <= CACHE_FRAMES):
                    speed = cached["speed"]
 
                # Run OCR every N frames on large-enough boxes
                if frame_idx % OCR_EVERY_N == 0 and bbox_h >= MIN_BOX_HEIGHT:
                    new_speed = read_speed(crop, reader)
                    if new_speed:
                        speed = new_speed
                        cache[region_key] = {"speed": new_speed,
                                             "last_seen": frame_idx}
 
                if not speed:
                    continue
 
                # Refresh cache timestamp
                if region_key in cache:
                    cache[region_key]["last_seen"] = frame_idx
 
                # Draw alert on frame
                draw_alert(frame, speed, x1, y1, x2, y2)
                detections += 1
 
                # Print only when speed changes
                if speed != last_printed:
                    print(f"  Frame {frame_idx:05d} -> Speed Limit: {speed} km/h")
                    last_printed = speed
 
        writer.write(frame)
        frame_idx += 1
 
    cap.release()
    writer.release()
 
    print(f"  Done | {frame_idx} frames | {detections} detections")
    print(f"  Video -> {out_video}")
 
 
# ═══════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════
def main():
    print("Loading YOLO model...")
    model = YOLO(MODEL_PATH)
 
    print("Loading EasyOCR...")
    reader = easyocr.Reader(['en'], gpu=True)
 
    exts   = {".mp4", ".avi", ".mov", ".mkv"}
    videos = [p for p in Path(VIDEO_FOLDER).iterdir()
              if p.suffix.lower() in exts]
 
    if not videos:
        print(f"No videos found in: {VIDEO_FOLDER}")
        return
 
    print(f"Found {len(videos)} video(s).\n")
    for v in videos:
        process_video(v, model, reader)
 
    print("\nAll videos processed.")
 
if __name__ == "__main__":
    main()
 