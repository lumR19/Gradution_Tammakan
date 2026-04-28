import cv2
import torch
import numpy as np
from transformers import AutoImageProcessor, AutoModelForDepthEstimation
from ultralytics import YOLO


# ===============================
# Depth Estimator (Requirement 1)
# ===============================
class DepthEstimator:
    def __init__(self, model_name="LiheYoung/depth-anything-small-hf", device="cpu"):
        self.device = torch.device(device)

        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModelForDepthEstimation.from_pretrained(model_name).to(self.device)
        self.model.eval()

        self.frame_count = 0
        self.cached_depth = None

    def _predict(self, frame):
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            depth = outputs.predicted_depth

        depth = depth.squeeze().cpu().numpy()
        depth = cv2.resize(depth, (frame.shape[1], frame.shape[0]))

        depth_norm = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX)
        return depth_norm.astype(np.uint8)

    def update(self, frame):
        """
        Run inference every 4 frames (caching)
        """
        self.frame_count += 1

        if self.frame_count % 4 == 0 or self.cached_depth is None:
            self.cached_depth = self._predict(frame)

        return self.cached_depth


# ===============================
# Tailgating Detector (Auto Calibration)
# ===============================
class TailgatingDetector:
    def __init__(self, estimator):
        self.estimator = estimator
        self.yolo = YOLO("yolov8n.pt")
        self.threshold = None

    def detect_vehicle_depth(self, frame):
        results = self.yolo(frame, verbose=False)[0]
        vehicle_depths = []

        for box in results.boxes:
            cls = int(box.cls[0])

            # car=2, bus=5, truck=7
            if cls in [2, 5, 7]:
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                depth_map = self.estimator.update(frame)
                roi = depth_map[y1:y2, x1:x2]

                if roi.size > 0:
                    vehicle_depths.append(np.mean(roi))

        if len(vehicle_depths) > 0:
            return np.mean(vehicle_depths)

        return None

    def calibrate_from_video(self, video_path, num_frames=50):
        """
        Auto calibration (UNCHANGED as requested)
        """
        cap = cv2.VideoCapture(video_path)
        values = []

        count = 0
        while count < num_frames:
            ret, frame = cap.read()
            if not ret:
                break

            depth_val = self.detect_vehicle_depth(frame)

            if depth_val is not None:
                values.append(depth_val)
                count += 1

        cap.release()

        if len(values) == 0:
            print("No vehicles detected → using default threshold")
            self.threshold = 120
        else:
            self.threshold = np.mean(values) * 1.2

        print("Threshold:", self.threshold)

    def check_tailgating(self, frame):
        depth_val = self.detect_vehicle_depth(frame)

        if depth_val is None:
            return False

        return depth_val > self.threshold


# ===============================
# Video Processing
# ===============================
def process_video(input_path, output_path, estimator, detector):

    cap = cv2.VideoCapture(input_path)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height), True)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        depth_map = estimator.update(frame)
        colored = cv2.applyColorMap(depth_map, cv2.COLORMAP_INFERNO)

        if detector.check_tailgating(frame):
            cv2.putText(colored, "TAILGATING WARNING!", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        out.write(colored)

        cv2.imshow("Output", colored)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()

    print("Saved to:", output_path)


# ===============================
# ONNX Export (Requirement 3)
# ===============================
def export_to_onnx(model, save_path="depth_model.onnx"):
    """
    Export model to ONNX (for TensorRT FP16 later)
    """

    dummy_input = torch.randn(1, 3, 384, 384)

    torch.onnx.export(
        model,
        dummy_input,
        save_path,
        input_names=["input"],
        output_names=["output"],
        opset_version=18
    )

    print("ONNX model saved at:", save_path)
    print("Next step (Jetson): convert to TensorRT FP16 using trtexec")


# ===============================
# MAIN
# ===============================
if __name__ == "__main__":

    video_path = input("Enter full video path: ").strip()

    estimator = DepthEstimator(device="cpu")
    detector = TailgatingDetector(estimator)

    detector.calibrate_from_video(video_path)

    process_video(
        input_path=video_path,
        output_path="output_depth.mp4",
        estimator=estimator,
        detector=detector
    )


    # (3) Export for TensorRT
    # ⚠️ Uncomment if you installed ONNX dependencies
    export_to_onnx(estimator.model)
