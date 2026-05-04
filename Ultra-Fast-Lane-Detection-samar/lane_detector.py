import torch
import cv2
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
import sys
import time
import os
import warnings
from collections import deque
warnings.filterwarnings("ignore")

sys.path.insert(0, '.')
from model.model import parsingNet


# to use this in another script:
#
#   from lane_detector import LaneDetector, visualize
#   detector = LaneDetector('culane_18.pth')
#
#   lanes  = detector.update(bgr_frame)   # call this every frame
#   canvas = visualize(bgr_frame, lanes)  # draw the results
#
# each lane you get back looks like this:
#   {
#     'poly_coeffs' : ndarray (3,)   the curve equation coefficients
#     'x_at_bottom' : float          where the lane sits at the bottom of the frame
#     'side'        : 'left'/'right' which side of center it's on
#     'confidence'  : float          how sure the model was, 0.0 to 1.0
#     'points_xy'   : list           the raw anchor detections before smoothing
#   }


IMG_W  = 800
IMG_H  = 288
GRID_W = 200

# these 18 y positions are where the model scans horizontally for lane markings.
# i recalculated them from the original CULane values which were for 590px tall images.
# they now fit our 288px height while still covering the road from near to far.
CULANE_ROW_ANCHORS = [
    80,  93, 106, 119, 132, 145, 158, 171, 184,
    197, 210, 223, 236, 249, 262, 275, 280, 288
]

# CULane training used 1640px wide images but we resize to 800px.
# without this scaling the detected lanes appear shifted left or right
# from where they actually are on the road.
COL_SAMPLE = np.linspace(0, 1640 - 1, GRID_W) * (IMG_W / 1640)

# we only care about the road area. the top 45% is usually sky, signs, or
# buildings, and the bottom 8% is the car hood. detections in those areas
# are almost never real lane markings so we just ignore them.
ROI_TOP_FRAC    = 0.45
ROI_BOTTOM_FRAC = 0.92
ROI_TOP         = int(IMG_H * ROI_TOP_FRAC)
ROI_BOTTOM      = int(IMG_H * ROI_BOTTOM_FRAC)

# how confident the model needs to be before we accept a detection.
# 0.25 worked well in testing — strict enough to cut noise but not so
# strict that it misses real lanes at night.
CONFIDENCE = 0.25

# a lane needs at least 7 anchor hits to count as real.
# fewer than that usually means the model caught some road texture or a shadow.
MIN_POINTS = 7

# after fitting a polynomial through the detected points, we don't let the
# drawn curve extend more than 20px beyond where the model actually fired.
# without this the curve sometimes swings wildly past the real lane markings.
CURVE_MARGIN = 20

# if the model is genuinely seeing a lane marking, one column will score
# much higher than all the others. if the scores are spread evenly across
# columns the model is basically guessing — we skip those points.
SCORE_GAP_THRESHOLD = 0.02

# real lanes run from near the car all the way to the horizon.
# something that only shows up in a tiny vertical strip (like a barrier
# or a road texture patch) gets filtered out by this check.
MIN_LANE_HEIGHT_FRAC = 0.35

# how many past frames we average to stop the lines from jumping around.
# 5 frames smooths out jitter without making the lines feel too slow to react.
SMOOTHING_WINDOW = 5

LANE_COLORS = [
    ( 80,  80, 255),
    ( 80, 255,  80),
    (255, 150,  80),
    ( 80, 220, 255),
]


class LaneSmoother:

    def __init__(self, window=SMOOTHING_WINDOW):
        self.window  = window
        # one history buffer per lane slot, max 4 lanes
        self.history = [deque(maxlen=window) for _ in range(4)]

    def update(self, raw_lanes):
        # sort left to right before updating the history buffers.
        # the model sometimes swaps which slot it uses for each physical lane
        # between frames — sorting by position keeps the right history
        # attached to the right lane no matter what the model does internally.
        sorted_lanes = sorted(raw_lanes, key=lambda l: l['x_at_bottom'])

        smoothed = []
        for slot, lane in enumerate(sorted_lanes):
            if slot >= 4:
                break
            self.history[slot].append(lane['poly_coeffs'].copy())
            avg_coeffs = np.mean(self.history[slot], axis=0)
            smoothed_lane = lane.copy()
            smoothed_lane['poly_coeffs'] = avg_coeffs
            smoothed.append(smoothed_lane)

        # if a lane disappears this frame we clear its history buffer
        # so it doesn't quietly bleed into detections in future frames
        for slot in range(len(sorted_lanes), 4):
            self.history[slot].clear()

        return smoothed


class LaneDetector:

    def __init__(self, weights_path, backbone='18', device=None):
        # pick GPU automatically if one exists, otherwise fall back to CPU.
        # on the Jetson this will say cuda. on a regular laptop it says cpu.
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        print(f"running on {self.device}")
        if self.device.type == 'cuda':
            print(f"gpu: {torch.cuda.get_device_name(0)}")

        # build the model architecture first — at this point it has no knowledge,
        # just the right structure. the weights loaded below are what give it knowledge.
        self.net = parsingNet(
            pretrained=False,
            backbone=backbone,
            cls_dim=(GRID_W + 1, len(CULANE_ROW_ANCHORS), 4),
            use_aux=False
        )

        state_dict = torch.load(weights_path, map_location=self.device)
        if 'model' in state_dict:
            state_dict = state_dict['model']

        # the CULane weights were saved from multi-GPU training which adds
        # 'module.' in front of every key. we strip it here so the keys
        # match what our single-device model expects.
        clean = {}
        for k, v in state_dict.items():
            clean[k[7:] if k.startswith('module.') else k] = v

        self.net.load_state_dict(clean, strict=False)
        self.net = self.net.to(self.device)
        self.net.eval()

        # ResNet-18 was pretrained on ImageNet so it needs inputs normalized
        # with these specific values. skipping normalization gives garbage output
        # even if the model loaded correctly.
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(
                mean=(0.485, 0.456, 0.406),
                std=(0.229, 0.224, 0.225)
            )
        ])

        self.smoother = LaneSmoother(window=SMOOTHING_WINDOW)
        print("model ready\n")


    def _preprocess(self, bgr_frame):
        # resize to 800x288 — the model architecture is hardcoded for this size.
        # OpenCV reads images as BGR but PyTorch expects RGB so we convert.
        # unsqueeze adds the batch dimension: (3, 288, 800) becomes (1, 3, 288, 800).
        resized = cv2.resize(bgr_frame, (IMG_W, IMG_H))
        rgb     = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        tensor  = self.transform(Image.fromarray(rgb)).unsqueeze(0)
        return tensor.to(self.device)


    def _decode(self, output):
        # output shape is (1, 201, 18, 4) — for each of the 4 lanes and 18 rows,
        # the model gives a probability over 200 column positions plus 1 no-lane class.
        # argmax picks the column with the highest score = the predicted x position.
        scores_np   = output[0].cpu().numpy()[:GRID_W, :, :]
        lane_points = np.argmax(scores_np, axis=0)
        max_scores  = np.max(scores_np, axis=0)
        exist_flags = max_scores > CONFIDENCE

        lanes = []
        for lane_idx in range(4):
            xs, ys, confs = [], [], []

            for row_idx, row_anchor in enumerate(CULANE_ROW_ANCHORS):
                if not (ROI_TOP <= int(row_anchor) <= ROI_BOTTOM):
                    continue

                if exist_flags[row_idx, lane_idx]:
                    # check how spiky the score distribution is for this point.
                    # a real detection has one column that clearly beats the rest.
                    # a guess has scores spread out evenly — we skip those.
                    score_gap = (np.max(scores_np[:, row_idx, lane_idx]) -
                                 np.mean(scores_np[:, row_idx, lane_idx]))
                    if score_gap < SCORE_GAP_THRESHOLD:
                        continue

                    xs.append(int(COL_SAMPLE[lane_points[row_idx, lane_idx]]))
                    ys.append(int(row_anchor))
                    confs.append(float(max_scores[row_idx, lane_idx]))

            # if the surviving points only cover a short vertical strip,
            # it's almost certainly a barrier, a shadow, or road texture.
            # real lanes span the road from near the car to the horizon.
            lane_span = (max(ys) - min(ys)) if ys else 0
            if lane_span < (ROI_BOTTOM - ROI_TOP) * MIN_LANE_HEIGHT_FRAC:
                continue

            if len(xs) > MIN_POINTS:
                try:
                    xs_arr      = np.array(xs, dtype=np.float64)
                    ys_arr      = np.array(ys, dtype=np.float64)
                    # degree 2 gives a gentle curve for normal roads.
                    # we only use it when we have enough points for a stable fit.
                    degree      = 2 if len(xs) >= 7 else 1
                    poly_coeffs = np.polyfit(ys_arr, xs_arr, deg=degree)
                    x_at_bottom = float(np.polyval(poly_coeffs, ROI_BOTTOM))
                    side        = 'left' if x_at_bottom < IMG_W / 2 else 'right'
                    # raw scores accumulate across anchor points so they go above 1.0.
                    # dividing by 20 brings them back to a 0.0-1.0 range.
                    confidence  = float(min(np.mean(confs) / 20.0, 1.0))

                    lanes.append({
                        'poly_coeffs' : poly_coeffs,
                        'x_at_bottom' : x_at_bottom,
                        'side'        : side,
                        'confidence'  : confidence,
                        'points_xy'   : list(zip(xs, ys)),
                    })
                except Exception:
                    pass

        return lanes


    def update(self, bgr_frame):
        # this is the main method — call it once per frame.
        # give it any BGR frame from OpenCV, get back a list of lane dicts.
        # returns an empty list when nothing is detected confidently enough.
        input_tensor = self._preprocess(bgr_frame)

        with torch.no_grad():
            output = self.net(input_tensor)

        raw_lanes = self._decode(output)
        smoothed  = self.smoother.update(raw_lanes)
        return smoothed


def visualize(bgr_frame, lanes, show_roi=True):
    # works on a copy so the original frame is never touched.
    # keeping drawing separate from detection means you can get lane data
    # without drawing anything, which is useful when speed matters.
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

        # one point per pixel gives a fully continuous line with no gaps
        y_smooth = np.arange(
            max(ROI_TOP + 15, int(np.min(ys_arr))),
            ROI_BOTTOM, 1
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

    return canvas


def export_to_onnx(weights_path, output_path='culane_18.onnx'):
    # converts the PyTorch model to ONNX format so TensorRT on the Jetson can use it.
    # run this once on any machine — it doesn't need to be the Jetson itself.
    # after you get the .onnx file, copy it to the Jetson and follow the
    # instructions in the HOW_TO_RUN_JETSON.md file.
    print("loading model for export...")

    net = parsingNet(
        pretrained=False, backbone='18',
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
    # the shape must exactly match what the model will actually receive.
    dummy = torch.zeros(1, 3, IMG_H, IMG_W)

    torch.onnx.export(
        net, dummy, output_path, opset_version=11,
        input_names=['input'], output_names=['output'],
        dynamic_axes={'input': {0: 'batch'}, 'output': {0: 'batch'}}
    )
    print(f"saved to {output_path}")
    print(f"next step on the Jetson:")
    print(f"  trtexec --onnx={output_path} --saveEngine=culane_fp16.engine --fp16")
    return output_path


def run_on_video(weights_path, video_in, output_dir, device=None):
    os.makedirs(output_dir, exist_ok=True)
    video_out = os.path.join(
        output_dir,
        os.path.splitext(os.path.basename(video_in))[0] + '_culane_output.mp4'
    )

    print("UFLD lane detection  CULane weights")
    print("=" * 50)

    detector = LaneDetector(weights_path=weights_path, device=device)

    cap = cv2.VideoCapture(video_in)
    if not cap.isOpened():
        raise FileNotFoundError(f"can't open: {video_in}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS)
    orig_w       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"video        {os.path.basename(video_in)}")
    print(f"size         {orig_w}x{orig_h}  resized to {IMG_W}x{IMG_H} internally")
    print(f"frames       {total_frames} at {fps} FPS")
    print(f"smoothing    last {SMOOTHING_WINDOW} frames averaged to keep lines stable")
    print(f"saving to    {os.path.basename(video_out)}\n")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(video_out, fourcc, fps, (IMG_W, IMG_H))

    frame_times     = []
    lanes_per_frame = []

    video_start = time.time()
    frame_idx   = 0

    print("processing frames...\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("reached the end of the video")
            break

        frame_idx += 1

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
            f"frame {frame_idx} of {total_frames}",
            f"{inference_ms:.0f} ms per frame   {1000/inference_ms:.1f} FPS",
            f"avg {avg_fps:.2f} FPS",
            f"done in about {int(eta//60)}m {int(eta%60)}s",
            f"lanes found {len(lanes)}",
        ]
        for i, txt in enumerate(overlay):
            cv2.putText(canvas, txt, (10, 22 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 3)
            cv2.putText(canvas, txt, (10, 22 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)

        writer.write(canvas)

        if frame_idx % 25 == 0:
            print(f"  frame {frame_idx:>4} of {total_frames}   "
                  f"{inference_ms:>5.0f} ms   "
                  f"lanes {len(lanes)}   "
                  f"eta {int(eta//60)}m {int(eta%60)}s")

    cap.release()
    writer.release()
    total_time = time.time() - video_start

    no_lane    = lanes_per_frame.count(0)
    one_lane   = sum(1 for x in lanes_per_frame if x == 1)
    two_lane   = sum(1 for x in lanes_per_frame if x == 2)
    three_plus = sum(1 for x in lanes_per_frame if x >= 3)

    print("\n" + "=" * 50)
    print("results")
    print("=" * 50)

    print("\nvideo")
    print(f"  file          {os.path.basename(video_in)}")
    print(f"  length        {total_frames/fps:.1f} seconds")
    print(f"  ran on        {detector.device}")

    print("\nspeed")
    print(f"  total time    {total_time:.1f} seconds  ({total_time/60:.1f} minutes)")
    print(f"  per frame     {np.mean(frame_times):.1f} ms on average")
    print(f"  fastest       {np.min(frame_times):.1f} ms")
    print(f"  slowest       {np.max(frame_times):.1f} ms")
    print(f"  overall       {total_frames/total_time:.2f} FPS")
    print(f"  real time     {'yes' if total_frames/total_time >= fps else 'no — needs a GPU for real time'}")

    print("\nlane detection")
    print(f"  total frames  {total_frames}")
    print(f"  avg per frame {np.mean(lanes_per_frame):.2f} lanes")
    print(f"  0 lanes       {no_lane} frames  ({100*no_lane/total_frames:.1f}%)")
    print(f"  1 lane        {one_lane} frames  ({100*one_lane/total_frames:.1f}%)")
    print(f"  2 lanes       {two_lane} frames  ({100*two_lane/total_frames:.1f}%)")
    print(f"  3 or more     {three_plus} frames  ({100*three_plus/total_frames:.1f}%)")

    print("\nbenchmark numbers from the original paper  CULane dataset")
    print(f"  overall F1    68.4%")
    print(f"  night F1      66.3%  this is the most relevant one for our videos")
    print(f"  crowded F1    69.7%")
    print(f"  no marking    41.7%  hardest case")
    print(f"  GPU speed     322 FPS  vs our {total_frames/total_time:.1f} FPS on CPU")

    print("\n" + "=" * 50)
    print(f"output video saved to {video_out}")
    return video_out


if __name__ == '__main__':

    WEIGHTS    = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\culane_18.pth'
    VIDEO_IN   = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\dataset_input_forTEST\10NewData_Test.mp4'
    OUTPUT_DIR = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\test_output_Culane'

    run_on_video(WEIGHTS, VIDEO_IN, OUTPUT_DIR)

    # when you're ready to export for Samar's Jetson setup, uncomment this:
    # export_to_onnx(WEIGHTS, output_path='culane_18.onnx')