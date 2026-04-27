import cv2
import torch
import numpy as np
from transformers import AutoImageProcessor, AutoModelForDepthEstimation


class DepthEstimator:
    def __init__(self, model_name="LiheYoung/depth-anything-small-hf", device="cpu"):
        """
        Initialize model and processor
        """
        self.device = torch.device(device)

        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModelForDepthEstimation.from_pretrained(model_name).to(self.device)
        self.model.eval()

        self.frame_count = 0
        self.cached_depth = None

    def _predict(self, frame):
        """
        Run depth estimation on a single frame
        """
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
        Run inference every 4 frames only (caching)
        """
        self.frame_count += 1

        if self.frame_count % 4 == 0 or self.cached_depth is None:
            self.cached_depth = self._predict(frame)

        return self.cached_depth


# ===============================
# Threshold Calibration Function
# ===============================
def calibrate_threshold(estimator, close_video, far_video, num_frames=30):
    """
    Compute threshold based on close and far videos
    """

    def get_avg_depth(video_path):
        cap = cv2.VideoCapture(video_path)
        values = []

        count = 0
        while count < num_frames:
            ret, frame = cap.read()
            if not ret:
                break

            depth = estimator.update(frame)
            values.append(np.mean(depth))
            count += 1

        cap.release()
        return np.mean(values)

    close_avg = get_avg_depth(close_video)
    far_avg = get_avg_depth(far_video)

    threshold = (close_avg + far_avg) / 2

    print("Close avg depth:", close_avg)
    print("Far avg depth:", far_avg)
    print("Calibrated threshold:", threshold)

    return threshold


# ===============================
# Video Processing
# ===============================
def process_video(input_path, output_path, estimator, threshold=None):
    """
    Apply depth estimation on video and save output
    """

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

        # convert to color
        colored = cv2.applyColorMap(depth_map, cv2.COLORMAP_INFERNO)

        # optional: tailgating detection
        if threshold is not None:
            if np.mean(depth_map) > threshold:
                cv2.putText(colored, "WARNING: TOO CLOSE!", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        out.write(colored)

        cv2.imshow("Depth Output", colored)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()

    print("Saved to:", output_path)


# ===============================
# ONNX Export for TensorRT
# ===============================
def export_to_onnx(model, save_path="depth_model.onnx"):
    """
    Export PyTorch model to ONNX
    """

    dummy_input = torch.randn(1, 3, 384, 384)

    torch.onnx.export(
        model,
        dummy_input,
        save_path,
        input_names=["input"],
        output_names=["output"],
        opset_version=11
    )

    print("Model exported to:", save_path)


# ===============================
# MAIN (Example Usage)
# ===============================
if __name__ == "__main__":

    # initialize estimator (CPU forced)
    estimator = DepthEstimator(device="cpu")

    # ===== Step 1: Calibrate 
    
    threshold = calibrate_threshold(estimator, "close.mp4", "far.mp4")

    

    # ===== Step 2: Process Video =====
    process_video(
        input_path="input.mp4",
        output_path="output_depth.mp4",
        estimator=estimator,
        threshold=threshold
    )

    # ===== Step 3: Export to ONNX =====
    export_to_onnx(estimator.model)
