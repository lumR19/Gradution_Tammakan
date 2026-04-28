import torch
import cv2
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
import sys
import os
import warnings
import time

warnings.filterwarnings("ignore")

sys.path.insert(0, '.')
from model.model import parsingNet


# Quick usage reminder:
#   detector = LaneDetector(weights_path='culane_18.pth')
#   lanes    = detector.update(bgr_frame)
#   canvas   = visualize(bgr_frame, lanes)


# These numbers are locked to how the model was trained on CULane.
# If you change IMG_W or IMG_H the pool layer inside the model
# will throw a shape error because it expects exactly 800x288.
IMG_W  = 800
IMG_H  = 288
GRID_W = 200

# The model scans the image at 18 fixed horizontal positions looking for lane points.
# I recalculated these from the original CULane values (which were for 590px height)
# to work within our 288px resized image. They cover the road from far (y=80) to near (y=280).
CULANE_ROW_ANCHORS = [
    80,  93, 106, 119, 132, 145, 158, 171, 184,
    197, 210, 223, 236, 249, 262, 275, 275, 280
]

# CULane training used 1640px wide images. We resize to 800px.
# Without this scaling the detected lanes appear shifted horizontally
# because the column indices don't map to the right pixel positions.
COL_SAMPLE = np.linspace(0, 1640 - 1, GRID_W) * (IMG_W / 1640)

# We only care about the road area. The top 35% is usually sky or highway signs,
# the bottom 8% is the car hood. Keeping detections inside this band avoids
# a lot of false positives that come from those regions.
ROI_TOP_FRAC    = 0.35
ROI_BOTTOM_FRAC = 0.92
ROI_TOP         = int(IMG_H * ROI_TOP_FRAC)
ROI_BOTTOM      = int(IMG_H * ROI_BOTTOM_FRAC)

# Lane markings look much fainter to the model at night because there's less
# reflected light. If we use the same confidence cutoff for night and day,
# most night lanes get filtered out. So we check brightness per frame
# and switch between these two values automatically.
BASE_CONFIDENCE = 0.15
DARK_CONFIDENCE = 0.08
DARK_THRESHOLD  = 80

# A lane needs at least 6 detected points before we treat it as real.
# Fewer than that is usually noise from road texture or shadows.
MIN_POINTS   = 6
CURVE_MARGIN = 40

LANE_COLORS = [
    ( 80,  80, 255),
    ( 80, 255,  80),
    (255, 150,  80),
    ( 80, 220, 255),
]


class LaneDetector:
    """
    Wraps model loading and inference into one object you can reuse across frames.

    Give it a BGR frame, get back a list of lane dicts. That's the whole interface.

    Each lane dict contains:
        poly_coeffs  ndarray (3,)  coefficients for x = a*y^2 + b*y + c
        x_at_bottom  float         where the lane sits at the bottom of the road zone
        side         str           'left' or 'right' relative to image center
        confidence   float         average model score across the detected points
        points_xy    list          raw (x, y) detection points before smoothing
    """

    def __init__(self, weights_path, backbone='18', device=None):
        # pick GPU if one is available, otherwise fall back to CPU quietly
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        print(f"  Running on: {self.device}")
        if self.device.type == 'cuda':
            print(f"  GPU: {torch.cuda.get_device_name(0)}")

        # build the model structure first, then fill it with the pretrained weights
        self.net = parsingNet(
            pretrained=False,
            backbone=backbone,
            cls_dim=(GRID_W + 1, len(CULANE_ROW_ANCHORS), 4),
            use_aux=False
        )

        state_dict = torch.load(weights_path, map_location=self.device)
        if 'model' in state_dict:
            state_dict = state_dict['model']

        # the CULane weights were saved from a multi-GPU training run which adds
        # 'module.' in front of every key. we strip it so the keys match our model.
        clean_state = {}
        for k, v in state_dict.items():
            clean_state[k[7:] if k.startswith('module.') else k] = v

        self.net.load_state_dict(clean_state, strict=False)
        self.net = self.net.to(self.device)
        self.net.eval()

        # ResNet-18 was pretrained on ImageNet so it expects inputs normalized
        # with these specific mean and std values. skipping this step gives garbage output.
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225)
            )
        ])

        print("  Model ready.\n")


    def _get_confidence_threshold(self, frame_bgr):
        gray        = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        road_region = gray[ROI_TOP:ROI_BOTTOM, :]
        brightness  = float(np.mean(road_region))
        if brightness < DARK_THRESHOLD:
            return DARK_CONFIDENCE, brightness
        return BASE_CONFIDENCE, brightness


    def _preprocess(self, frame_bgr):
        # resize to 800x288 — the model's pool layer is built for exactly this size
        resized = cv2.resize(frame_bgr, (IMG_W, IMG_H))

        # OpenCV loads images in BGR order but PyTorch expects RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # normalize and add a batch dimension: (3, 288, 800) becomes (1, 3, 288, 800)
        tensor = self.transform(Image.fromarray(rgb)).unsqueeze(0)
        return tensor.to(self.device), resized


    def _decode_output(self, output, confidence):
        # output[0] removes the batch dimension
        # we only take the first GRID_W columns and drop the last one
        # because the last column is the "no lane here" class
        scores_np   = output[0].cpu().numpy()[:GRID_W, :, :]
        lane_points = np.argmax(scores_np, axis=0)
        max_scores  = np.max(scores_np, axis=0)
        exist_flags = max_scores > confidence

        lanes = []
        for lane_idx in range(4):
            xs, ys, confs = [], [], []
            for row_idx, row_anchor in enumerate(CULANE_ROW_ANCHORS):
                if not (ROI_TOP <= int(row_anchor) <= ROI_BOTTOM):
                    continue
                if exist_flags[row_idx, lane_idx]:
                    x = float(COL_SAMPLE[lane_points[row_idx, lane_idx]])
                    y = float(row_anchor)
                    xs.append(x)
                    ys.append(y)
                    confs.append(float(max_scores[row_idx, lane_idx]))

            if len(xs) > MIN_POINTS:
                lanes.append((xs, ys, confs))

        return lanes


    def _fit_lane(self, xs, ys, confs):
        xs_arr = np.array(xs, dtype=np.float64)
        ys_arr = np.array(ys, dtype=np.float64)

        # we fit x = f(y) rather than y = f(x) because lanes run top to bottom
        # and a single y value maps to exactly one x — the math is more stable this way
        poly_coeffs = np.polyfit(ys_arr, xs_arr, deg=2)

        x_at_bottom = float(np.polyval(poly_coeffs, ROI_BOTTOM))
        side        = 'left' if x_at_bottom < IMG_W / 2 else 'right'

        return {
            'poly_coeffs' : poly_coeffs,
            'x_at_bottom' : x_at_bottom,
            'side'        : side,
            'confidence' : float(min(np.mean(confs) / 20.0, 1.0)),
            'points_xy'   : list(zip(xs, ys)),
        }


    def update(self, bgr_frame):
        """
        Call this once per frame. Give it any BGR frame from OpenCV,
        get back a list of lane dicts (empty list if nothing was detected).
        """
        resized_for_brightness = cv2.resize(bgr_frame, (IMG_W, IMG_H))
        confidence, _          = self._get_confidence_threshold(resized_for_brightness)

        input_tensor, _ = self._preprocess(bgr_frame)

        with torch.no_grad():
            output = self.net(input_tensor)

        raw_lanes = self._decode_output(output, confidence)

        result = []
        for xs, ys, confs in raw_lanes:
            try:
                result.append(self._fit_lane(xs, ys, confs))
            except Exception:
                # polyfit can fail if points are all at the same x — just skip that lane
                pass

        return result


def visualize(bgr_frame, lanes, show_roi=True):
    """
    Draws smooth polynomial curves on the frame for each detected lane.
    Works on a copy so the original frame is never touched.

    Kept as a standalone function instead of inside the class so you can
    run detection without drawing (useful if you only need the lane data)
    or swap in a different drawing style without touching the detection code.
    """
    canvas = cv2.resize(bgr_frame, (IMG_W, IMG_H)).copy()

    if show_roi:
        cv2.line(canvas, (0, ROI_TOP),    (IMG_W, ROI_TOP),    (50, 50, 50), 1)
        cv2.line(canvas, (0, ROI_BOTTOM), (IMG_W, ROI_BOTTOM), (50, 50, 50), 1)

    for i, lane in enumerate(lanes):
        color       = LANE_COLORS[i % len(LANE_COLORS)]
        poly_coeffs = lane['poly_coeffs']
        points_xy   = lane['points_xy']

        xs_arr = np.array([p[0] for p in points_xy], dtype=np.float32)
        ys_arr = np.array([p[1] for p in points_xy], dtype=np.float32)

        if len(xs_arr) < 2:
            continue

        y_smooth = np.arange(
            max(ROI_TOP,    int(np.min(ys_arr))),
            min(ROI_BOTTOM, int(np.max(ys_arr)) + 1),
            2
        ).astype(np.float32)

        if len(y_smooth) < 2:
            continue

        x_smooth = np.polyval(poly_coeffs, y_smooth)

        # stop the curve from shooting past the actual detected region
        x_min    = np.min(xs_arr) - CURVE_MARGIN
        x_max    = np.max(xs_arr) + CURVE_MARGIN
        valid    = (x_smooth >= x_min) & (x_smooth <= x_max)
        x_smooth = np.clip(x_smooth[valid], 0, IMG_W - 1).astype(np.int32)
        y_smooth = y_smooth[valid].astype(np.int32)

        if len(y_smooth) < 2:
            continue

        pts = np.stack([x_smooth, y_smooth], axis=1).reshape(-1, 1, 2)
        cv2.polylines(canvas, [pts], isClosed=False, color=color, thickness=4)

        for x, y in points_xy:
            cv2.circle(canvas, (int(x), int(y)), 3, color, -1)

        if len(points_xy) > 0:
            mid     = len(points_xy) // 2
            label_x = int(points_xy[mid][0])
            label_y = int(points_xy[mid][1])
            cv2.putText(canvas,
                        f"{lane['side']} {lane['confidence']:.2f}",
                        (label_x + 5, label_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    return canvas


def export_to_onnx(weights_path, output_path='culane_18.onnx'):
    """
    Converts the PyTorch model to ONNX format so it can be picked up by TensorRT.

    Run this once on any machine (doesn't need Jetson).
    Then copy the .onnx file to the Jetson and run:
        trtexec --onnx=culane_18.onnx --saveEngine=culane_fp16.engine --fp16

    The resulting .engine file is what the Jetson actually runs at full GPU speed.
    FP16 means half precision — twice the throughput, half the memory, almost no accuracy loss.
    """
    print("Loading model for ONNX export...")

    net = parsingNet(
        pretrained=False,
        backbone='18',
        cls_dim=(GRID_W + 1, len(CULANE_ROW_ANCHORS), 4),
        use_aux=False
    )

    state_dict = torch.load(weights_path, map_location='cpu')
    if 'model' in state_dict:
        state_dict = state_dict['model']

    clean = {(k[7:] if k.startswith('module.') else k): v for k, v in state_dict.items()}
    net.load_state_dict(clean, strict=False)
    net.eval()

    # ONNX export works by tracing — it runs the model once on this dummy input
    # and records every operation. the shape must match the real input exactly.
    dummy_input = torch.zeros(1, 3, IMG_H, IMG_W)

    print(f"Exporting to {output_path} ...")
    torch.onnx.export(
        net,
        dummy_input,
        output_path,
        opset_version=11,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input':  {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
    )
    print(f"Saved to: {output_path}")
    print(f"\nNext step on Jetson:")
    print(f"  trtexec --onnx={output_path} --saveEngine=culane_fp16.engine --fp16")
    return output_path


def run_on_video(weights_path, video_in, output_dir, device=None):
    os.makedirs(output_dir, exist_ok=True)
    VIDEO_OUT = os.path.join(
        output_dir,
        os.path.splitext(os.path.basename(video_in))[0] + '_culane_output.mp4'
    )

    print("=" * 60)
    print("  UFLD Lane Detection — CULane Model")
    print("=" * 60)

    detector = LaneDetector(weights_path=weights_path, device=device)

    cap = cv2.VideoCapture(video_in)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open: {video_in}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS)
    orig_w       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Video        : {os.path.basename(video_in)}")
    print(f"Resolution   : {orig_w}x{orig_h} -> {IMG_W}x{IMG_H}")
    print(f"Frames       : {total_frames} at {fps} FPS")
    print(f"Output       : {os.path.basename(VIDEO_OUT)}\n")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out    = cv2.VideoWriter(VIDEO_OUT, fourcc, fps, (IMG_W, IMG_H))

    frame_times       = []
    lanes_per_frame   = []
    brightness_values = []

    video_start = time.time()
    frame_idx   = 0

    print("Processing — hang tight, CPU takes a few minutes per video\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Reached end of video.")
            break

        frame_idx += 1

        resized    = cv2.resize(frame, (IMG_W, IMG_H))
        gray       = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray[ROI_TOP:ROI_BOTTOM, :]))
        brightness_values.append(brightness)
        scene_label = "Night/Tunnel" if brightness < DARK_THRESHOLD else "Daytime"

        t0           = time.time()
        lanes        = detector.update(frame)
        inference_ms = (time.time() - t0) * 1000
        frame_times.append(inference_ms)
        lanes_per_frame.append(len(lanes))

        canvas  = visualize(frame, lanes, show_roi=True)
        elapsed = time.time() - video_start
        avg_fps = frame_idx / elapsed if elapsed > 0 else 0
        eta     = (total_frames - frame_idx) / avg_fps if avg_fps > 0 else 0

        overlay = [
            f"Frame: {frame_idx}/{total_frames}",
            f"Inference: {inference_ms:.0f} ms  ({1000/inference_ms:.1f} FPS)",
            f"Avg FPS: {avg_fps:.2f}",
            f"ETA: {int(eta//60)}m {int(eta%60)}s",
            f"Lanes: {len(lanes)} | Scene: {scene_label}",
            f"Brightness: {brightness:.0f}/255",
        ]
        for i, txt in enumerate(overlay):
            cv2.putText(canvas, txt, (10, 22 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 3)
            cv2.putText(canvas, txt, (10, 22 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)

        out.write(canvas)

        if frame_idx % 25 == 0:
            print(f"  Frame {frame_idx:>4}/{total_frames}  |  "
                  f"{inference_ms:>5.0f} ms  |  "
                  f"Lanes: {len(lanes)}  |  "
                  f"Scene: {scene_label:<13}  |  "
                  f"ETA: {int(eta//60)}m {int(eta%60)}s")

    cap.release()
    out.release()
    total_time = time.time() - video_start

    no_lane    = lanes_per_frame.count(0)
    three_plus = sum(1 for x in lanes_per_frame if x >= 3)
    night_cnt  = sum(1 for b in brightness_values if b < DARK_THRESHOLD)

    print("\n" + "=" * 60)
    print("        EVALUATION REPORT — UFLD CULane")
    print("=" * 60)
    print(f"\n  [Video Info]")
    print(f"  File                     : {os.path.basename(video_in)}")
    print(f"  Duration                 : {total_frames/fps:.1f} sec")
    print(f"  Device used              : {detector.device}")
    print(f"  Night/Tunnel frames      : {night_cnt} ({100*night_cnt/total_frames:.1f}%)")
    print(f"  Daytime frames           : {total_frames-night_cnt} ({100*(total_frames-night_cnt)/total_frames:.1f}%)")
    print(f"  Avg brightness           : {np.mean(brightness_values):.1f}/255")
    print(f"\n  [Speed Metrics]")
    print(f"  Total processing time    : {total_time:.1f} sec ({total_time/60:.1f} min)")
    print(f"  Avg inference per frame  : {np.mean(frame_times):.1f} ms")
    print(f"  Min / Max inference      : {np.min(frame_times):.1f} / {np.max(frame_times):.1f} ms")
    print(f"  Avg processing speed     : {total_frames/total_time:.2f} FPS")
    print(f"  Real-time capable        : {'YES' if total_frames/total_time >= fps else 'NO — GPU needed for real-time'}")
    print(f"\n  [Detection Metrics]")
    print(f"  Total frames processed   : {total_frames}")
    print(f"  Avg lanes per frame      : {np.mean(lanes_per_frame):.2f}")
    print(f"  Frames with 0 lanes      : {no_lane} ({100*no_lane/total_frames:.1f}%)")
    print(f"  Frames with 3+ lanes     : {three_plus} ({100*three_plus/total_frames:.1f}%)")
    print(f"\n  [Published Benchmark — CULane, from UFLD paper]")
    print(f"  F1 Score overall         : 68.4%")
    print(f"  F1 Score night           : 66.3%  <- most relevant to our test")
    print(f"  Speed on GPU             : 322 FPS  <- vs our {total_frames/total_time:.1f} FPS on CPU")
    print("=" * 60)
    print(f"\n  Output saved to: {VIDEO_OUT}")

    return VIDEO_OUT


if __name__ == '__main__':

    WEIGHTS    = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\culane_18.pth'
    VIDEO_IN   = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\dataset_input_forTEST\2video_test_night.mp4'
    OUTPUT_DIR = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\test_output_Culane'

    run_on_video(WEIGHTS, VIDEO_IN, OUTPUT_DIR)

    # uncomment this when you're ready to export for Jetson
    # export_to_onnx(WEIGHTS, output_path='culane_18.onnx')
