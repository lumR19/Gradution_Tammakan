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


# quick usage:
#   detector = LaneDetector(weights_path='culane_18.pth')
#   lanes    = detector.update(bgr_frame)
#   canvas   = visualize(bgr_frame, lanes)


# these are locked to the CULane training setup and cannot be changed
# without retraining. the pool layer inside the model expects exactly 800x288.
IMG_W  = 800
IMG_H  = 288
GRID_W = 200

# 18 horizontal positions where the model looks for lane points.
# I recalculated these from the original CULane values (260-530px for 590px images)
# to fit our 288px height. the last value was a duplicate 275 which I fixed to 288.
CULANE_ROW_ANCHORS = [
    80,  93, 106, 119, 132, 145, 158, 171, 184,
    197, 210, 223, 236, 249, 262, 275, 280, 288
]

# CULane training used 1640px wide images. we resize to 800px.
# without this scaling the lanes appear shifted left/right from where they actually are.
COL_SAMPLE = np.linspace(0, 1640 - 1, GRID_W) * (IMG_W / 1640)

# ROI — top 45% is sky/signs, bottom 8% is car hood. no lanes live there.
# using fractions so the values adapt automatically to any image height.
ROI_TOP_FRAC    = 0.45
ROI_BOTTOM_FRAC = 0.92
ROI_TOP         = int(IMG_H * ROI_TOP_FRAC)
ROI_BOTTOM      = int(IMG_H * ROI_BOTTOM_FRAC)

# at night the model sees faint lane markings and gives lower confidence scores.
# if we use the same threshold for night and day, most night lanes get filtered out.
# so we check brightness per frame and switch automatically.
BASE_CONFIDENCE = 0.15
DARK_CONFIDENCE = 0.08
DARK_THRESHOLD  = 80

# raised from 4 to 5 to reduce false lanes from road texture and barriers
MIN_POINTS = 5

# tightened from 40 to 20 to stop the polynomial from swinging wide on noisy frames
CURVE_MARGIN = 20

LANE_COLORS = [
    ( 80,  80, 255),
    ( 80, 255,  80),
    (255, 150,  80),
    ( 80, 220, 255),
]


class LaneDetector:
    """
    The whole inference pipeline wrapped in one object.
    Give it a BGR frame, get back a list of lane dicts.

    Each lane dict contains:
        poly_coeffs   ndarray (3,)   coefficients for x = a*y^2 + b*y + c
        x_at_bottom   float          x position at the bottom of the road zone
        side          str            'left' or 'right' relative to image center
        confidence    float          normalized model confidence 0.0 to 1.0
        points_xy     list           raw (x, y) detections before curve fitting
    """

    def __init__(self, weights_path, backbone='18', device=None):
        # auto-pick GPU if one exists, otherwise fall back to CPU silently.
        # on your laptop this will say 'cpu'. on a Jetson it will say 'cuda'.
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        print(f"  Device: {self.device}")
        if self.device.type == 'cuda':
            print(f"  GPU: {torch.cuda.get_device_name(0)}")

        # build the empty model structure first, then fill it with pretrained weights
        self.net = parsingNet(
            pretrained=False,
            backbone=backbone,
            cls_dim=(GRID_W + 1, len(CULANE_ROW_ANCHORS), 4),
            use_aux=False
        )

        state_dict = torch.load(weights_path, map_location=self.device)
        if 'model' in state_dict:
            state_dict = state_dict['model']

        # CULane weights were saved from multi-GPU training which adds 'module.'
        # to every key. stripping it lets the keys match our single-GPU model.
        clean = {}
        for k, v in state_dict.items():
            clean[k[7:] if k.startswith('module.') else k] = v

        self.net.load_state_dict(clean, strict=False)
        self.net = self.net.to(self.device)
        self.net.eval()

        # ResNet-18 was pretrained on ImageNet so it needs inputs normalized
        # with these exact mean and std values. skipping this gives garbage output.
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225)
            )
        ])

        print("  Model ready.\n")


    def _get_confidence_threshold(self, frame_bgr):
        gray       = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray[ROI_TOP:ROI_BOTTOM, :]))
        if brightness < DARK_THRESHOLD:
            return DARK_CONFIDENCE, brightness
        return BASE_CONFIDENCE, brightness


    def _preprocess(self, frame_bgr):
        """
        Input:  BGR frame, any resolution
        Output: torch tensor (1, 3, 288, 800), normalized with ImageNet mean/std,
                moved to the same device as the model (GPU or CPU)
        """
        # resize to the exact size the model's pool layer was built for
        resized = cv2.resize(frame_bgr, (IMG_W, IMG_H))

        # OpenCV loads BGR but PyTorch expects RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # ToTensor converts 0-255 to 0.0-1.0, unsqueeze adds the batch dimension
        # final shape: (1, 3, 288, 800)
        tensor = self.transform(Image.fromarray(rgb)).unsqueeze(0)
        return tensor.to(self.device), resized


    def _decode_output(self, output, confidence):
        # output[0] removes the batch dimension
        # we drop the last column because that's the "no lane" class
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

        # we fit x = f(y) rather than y = f(x) because each y maps to one x
        # but one x could have multiple y values. the math is more stable this way.
        # use degree 2 only when we have enough points for a stable parabola fit.
        degree      = 2 if len(xs) >= 7 else 1
        poly_coeffs = np.polyfit(ys_arr, xs_arr, deg=degree)

        x_at_bottom = float(np.polyval(poly_coeffs, ROI_BOTTOM))
        side        = 'left' if x_at_bottom < IMG_W / 2 else 'right'

        # divide by 20 to normalize the raw model scores to roughly 0.0-1.0
        # the raw scores accumulate across anchor points so they exceed 1.0 by default
        normalized_conf = float(min(np.mean(confs) / 20.0, 1.0))

        return {
            'poly_coeffs' : poly_coeffs,
            'x_at_bottom' : x_at_bottom,
            'side'        : side,
            'confidence'  : normalized_conf,
            'points_xy'   : list(zip(xs, ys)),
        }


    def update(self, bgr_frame):
        """
        Call once per frame.

        Input:  bgr_frame — numpy array, any resolution, BGR (standard OpenCV format)
        Output: list of lane dicts (empty list if nothing detected)
        """
        resized_for_check       = cv2.resize(bgr_frame, (IMG_W, IMG_H))
        confidence, _           = self._get_confidence_threshold(resized_for_check)
        input_tensor, _         = self._preprocess(bgr_frame)

        # no_grad tells PyTorch not to build a computation graph — we don't need
        # gradients at inference time and skipping them saves memory and time
        with torch.no_grad():
            output = self.net(input_tensor)

        raw_lanes = self._decode_output(output, confidence)

        result = []
        for xs, ys, confs in raw_lanes:
            try:
                result.append(self._fit_lane(xs, ys, confs))
            except Exception:
                # polyfit can fail if all points share the same x — just skip that lane
                pass

        return result


def visualize(bgr_frame, lanes, show_roi=True):
    """
    Draws smooth polynomial curves on the frame for each detected lane.
    Works on a copy so the original frame is never modified.

    Kept as a standalone function (not inside LaneDetector) so you can:
    - run detection without drawing if you only need the lane data
    - swap in a different drawing style without touching the detection code
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
            max(ROI_TOP + 15, int(np.min(ys_arr))),
            min(ROI_BOTTOM,   int(np.max(ys_arr)) + 1),
            2
        ).astype(np.float32)

        if len(y_smooth) < 2:
            continue

        x_smooth = np.polyval(poly_coeffs, y_smooth)

        # stop the curve from wandering beyond where the model actually fired
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

        # label shows side and normalized confidence score
        if len(points_xy) > 0:
            mid = len(points_xy) // 2
            cv2.putText(canvas,
                        f"{lane['side']} {lane['confidence']:.2f}",
                        (int(points_xy[mid][0]) + 5, int(points_xy[mid][1])),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    return canvas


def export_to_onnx(weights_path, output_path='culane_18.onnx'):
    """
    Converts the PyTorch model to ONNX format.
    Run this once on any machine — doesn't need a Jetson.

    After you get the .onnx file, copy it to the Jetson and run:
        trtexec --onnx=culane_18.onnx --saveEngine=culane_fp16.engine --fp16

    fp16 = half precision. twice the throughput, half the memory,
    almost no accuracy difference. this is how you get 100+ FPS on a Jetson.
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

    # ONNX export traces the model by running it once on this dummy input.
    # the shape must match exactly what the real input looks like.
    dummy = torch.zeros(1, 3, IMG_H, IMG_W)

    print(f"Exporting to {output_path} ...")
    torch.onnx.export(
        net, dummy, output_path,
        opset_version=11,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input':  {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
    )
    print(f"Saved: {output_path}")
    print(f"\nOn the Jetson, run:")
    print(f"  trtexec --onnx={output_path} --saveEngine=culane_fp16.engine --fp16")
    return output_path


def run_on_video(weights_path, video_in, output_dir, device=None):
    """
    Processes a full video and prints the evaluation report at the end.
    Uses LaneDetector and visualize() separately so the logic stays clean.
    """
    os.makedirs(output_dir, exist_ok=True)
    video_out = os.path.join(
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
    print(f"Output       : {os.path.basename(video_out)}\n")
    print("Processing — hang tight, CPU takes a few minutes per video\n")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(video_out, fourcc, fps, (IMG_W, IMG_H))

    frame_times       = []
    lanes_per_frame   = []
    brightness_values = []

    video_start = time.time()
    frame_idx   = 0

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
            f"Brightness: {brightness:.0f}/255 | Conf: {'night' if brightness < DARK_THRESHOLD else 'day'}",
        ]
        for i, txt in enumerate(overlay):
            cv2.putText(canvas, txt, (10, 22 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 3)
            cv2.putText(canvas, txt, (10, 22 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)

        writer.write(canvas)

        if frame_idx % 25 == 0:
            print(f"  Frame {frame_idx:>4}/{total_frames}  |  "
                  f"{inference_ms:>5.0f} ms  |  "
                  f"Lanes: {len(lanes)}  |  "
                  f"Scene: {scene_label:<13}  |  "
                  f"ETA: {int(eta//60)}m {int(eta%60)}s")

    cap.release()
    writer.release()
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
    print(f"\n  Output saved to: {video_out}")
    return video_out


if __name__ == '__main__':

    WEIGHTS    = r"C:\Users\Admin\Desktop\Grad_Project\Code\UFLD\culane_18.pth"
    VIDEO_IN   = r"C:\Users\Admin\Desktop\Grad_Project\Code\Datasets\Dashcam_clips\20260421212545_0060.mp4"
    OUTPUT_DIR = r"C:\Users\Admin\Desktop\Grad_Project\Code\UFLD\OUTPUT"

    run_on_video(WEIGHTS, VIDEO_IN, OUTPUT_DIR)

    # uncomment when you're ready to export for Jetson
    # export_to_onnx(WEIGHTS, output_path='culane_18.onnx')
