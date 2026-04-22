import cv2
import os
import csv
from pathlib import Path
from ultralytics import YOLO
from ocr_handler import TamakkanOCR

# =========================================================
# SETTINGS
# =========================================================
MODEL_PATH = r"D:\Gradution_Tammakan\best.pt"
VIDEO_FOLDER = r"D:\tamakkan"
OUTPUT_FOLDER = r"D:\tamakken"

TRAFFIC_SIGN_ID = 5
CONF_THRESHOLD = 0.50
OCR_EVERY_N_FRAMES = 3   # 1 = كل فريم، 3 أخف وأنسب غالبًا

# =========================================================
# PROCESS ONE VIDEO
# =========================================================
def process_video(video_path, model, ocr_manager, output_folder):
    video_path = Path(video_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Could not open video: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 20.0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_video_path = output_folder / f"{video_path.stem}_speed_output.mp4"
    output_csv_path = output_folder / f"{video_path.stem}_speed_results.csv"

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))

    frame_idx = 0
    last_speeds = {}

    with open(output_csv_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "speed", "confidence", "x1", "y1", "x2", "y2"])

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            results = model.predict(frame, conf=CONF_THRESHOLD, device="cpu", verbose=False)

            for r in results:
                if r.boxes is None:
                    continue

                for box in r.boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    # فقط لوحات المرور
                    if cls != TRAFFIC_SIGN_ID:
                        continue

                    h, w = frame.shape[:2]
                    x1 = max(0, x1)
                    y1 = max(0, y1)
                    x2 = min(w, x2)
                    y2 = min(h, y2)

                    cropped_sign = frame[y1:y2, x1:x2]
                    if cropped_sign.size == 0:
                        continue

                    region_key = f"{x1//20}_{y1//20}_{x2//20}_{y2//20}"
                    speed = ""

                    # OCR كل كم فريم لتخفيف الحمل
                    if frame_idx % OCR_EVERY_N_FRAMES == 0:
                        speed = ocr_manager.read_speed_sign(cropped_sign)
                        if speed:
                            last_speeds[region_key] = speed
                    else:
                        speed = last_speeds.get(region_key, "")

                    # إذا ما اكتشف رقم سرعة صحيح، تجاهل
                    if not speed:
                        continue

                    print(f"[{video_path.name}] Frame {frame_idx}: Detected Speed = {speed}")

                    # رسم البوكس والسرعة
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    label = f"Speed: {speed}"
                    cv2.putText(
                        frame,
                        label,
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 255),
                        2
                    )

                    writer.writerow([frame_idx, speed, round(conf, 4), x1, y1, x2, y2])

            out.write(frame)
            frame_idx += 1

    cap.release()
    out.release()

    print(f"Done: {video_path.name}")
    print(f"Saved video -> {output_video_path}")
    print(f"Saved csv   -> {output_csv_path}")
    print("-" * 60)

# =========================================================
# MAIN
# =========================================================
def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    print("Loading YOLO model...")
    model = YOLO(MODEL_PATH)

    print("Loading EasyOCR...")
    ocr_manager = TamakkanOCR(use_gpu=False)

    video_extensions = [".mp4", ".avi", ".mov", ".mkv"]
    videos = []

    for ext in video_extensions:
        videos.extend(Path(VIDEO_FOLDER).glob(f"*{ext}"))

    if not videos:
        print("No videos found in:", VIDEO_FOLDER)
        return

    print(f"Found {len(videos)} video(s).\n")

    for video_path in videos:
        process_video(video_path, model, ocr_manager, OUTPUT_FOLDER)

    print("All videos processed successfully.")

if __name__ == "__main__":
    main()