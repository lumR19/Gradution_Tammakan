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


WEIGHTS   = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\culane_18.pth'
VIDEO_IN  = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\dataset_input_forTEST\3NewDataset_Test.mp4'

OUTPUT_DIR = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\test_output_Culane'
os.makedirs(OUTPUT_DIR, exist_ok=True)
VIDEO_OUT  = os.path.join(OUTPUT_DIR, os.path.splitext(os.path.basename(VIDEO_IN))[0] + '_culane_output.mp4')


BACKBONE     = '18'
IMG_W, IMG_H = 800, 288
GRID_W       = 200

CULANE_ROW_ANCHORS = [
    80,  93, 106, 119, 132, 145, 158, 171, 184,
    197, 210, 223, 236, 249, 262, 275, 280, 288
]

col_sample = np.linspace(0, 1640 - 1, GRID_W) * (IMG_W / 1640)

COLORS = [
    ( 80,  80, 255),
    ( 80, 255,  80),
    (255, 150,  80),
    ( 80, 220, 255),
]

# we keep the full frame resize (no cropping) because this version
# produced more stable results than the cropped version in testing.
# the model sees sky and hood too but handles it better than expected.

# single confidence value — no day/night switching.
# 0.25 is strict enough to kill most false lanes while still catching real ones.
CONFIDENCE = 0.25

ROI_TOP_FRAC    = 0.45
ROI_BOTTOM_FRAC = 0.92

# raised from 5 — needs 7 consistent anchor hits to count as a real lane
MIN_POINTS = 7

CURVE_MARGIN = 20

# the gap between the best column score and the column average.
# a guessing model spreads scores evenly — tiny gap.
# a confident model spikes one column — big gap.
SCORE_GAP_THRESHOLD = 0.02

# a real lane must span at least 35% of the ROI height vertically.
# barriers and road texture usually only fire on a short strip.
MIN_LANE_HEIGHT_FRACTION = 0.35

# how many past frames we average to stabilize the drawn lines.
# 5 frames smooths out jitter without making the lines feel laggy.
# raise it to 8 if lines still jump, lower to 3 if they feel too sluggish.
SMOOTHING_WINDOW = 5


# this class holds the memory between frames.
# instead of drawing whatever the model said this exact frame,
# we average the polynomial coefficients from the last N frames.
# frame-to-frame noise cancels out in the average.
# real lane movement accumulates and still shows up correctly.
class LaneSmoother:

    def __init__(self, window=SMOOTHING_WINDOW):
        self.window  = window
        # one history buffer per lane slot (max 4 lanes)
        self.history = [deque(maxlen=window) for _ in range(4)]

    def update(self, lanes_this_frame):
        # sort lanes left to right by x position at the bottom of the frame.
        # this gives consistent ordering even when the model swaps lane indices
        # between frames, which would otherwise confuse the smoothing buffers.
        sorted_lanes = sorted(lanes_this_frame, key=lambda l: l['x_bottom'])

        smoothed = []
        for slot, lane in enumerate(sorted_lanes):
            if slot >= 4:
                break
            self.history[slot].append(lane['coeffs'].copy())
            # average all stored coefficients for this slot
            avg_coeffs = np.mean(self.history[slot], axis=0)
            smoothed.append({
                'coeffs'    : avg_coeffs,
                'xs'        : lane['xs'],
                'ys'        : lane['ys'],
                'x_bottom'  : lane['x_bottom'],
                'color_idx' : slot,
            })

        # clear history for slots that had no lane this frame
        # so dead lanes don't bleed into future detections
        for slot in range(len(sorted_lanes), 4):
            self.history[slot].clear()

        return smoothed


smoother = LaneSmoother()


print("=" * 60)
print("  UFLD  CULane  General Purpose Inference")
print("=" * 60)
print("\nLoading model...")

net = parsingNet(
    pretrained=False,
    backbone=BACKBONE,
    cls_dim=(GRID_W + 1, len(CULANE_ROW_ANCHORS), 4),
    use_aux=False
)

state_dict = torch.load(WEIGHTS, map_location='cpu')
if 'model' in state_dict:
    state_dict = state_dict['model']

compatible_state_dict = {}
for k, v in state_dict.items():
    compatible_state_dict[k[7:] if 'module.' in k else k] = v

net.load_state_dict(compatible_state_dict, strict=False)
net.eval()
print("Model loaded!\n")


transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=(0.485, 0.456, 0.406),
                         std=(0.229, 0.224, 0.225))
])


cap = cv2.VideoCapture(VIDEO_IN)
if not cap.isOpened():
    raise FileNotFoundError(f"Could not open video: {VIDEO_IN}")

total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps          = cap.get(cv2.CAP_PROP_FPS)
orig_w       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
orig_h       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

ROI_TOP    = int(IMG_H * ROI_TOP_FRAC)
ROI_BOTTOM = int(IMG_H * ROI_BOTTOM_FRAC)

print(f"Video        {os.path.basename(VIDEO_IN)}")
print(f"Frames       {total_frames}  {fps} FPS  {orig_w}x{orig_h}")
print(f"Model input  {IMG_W}x{IMG_H}  full frame resize  no crop")
print(f"ROI          y={ROI_TOP} to y={ROI_BOTTOM}")
print(f"Smoothing    {SMOOTHING_WINDOW} frame window")
print(f"Output       {os.path.basename(VIDEO_OUT)}\n")

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out    = cv2.VideoWriter(VIDEO_OUT, fourcc, fps, (IMG_W, IMG_H))

frame_times       = []
lanes_per_frame   = []
confidence_scores = []
points_per_lane   = []


def draw_smooth_lane(canvas, lane):
    xs     = lane['xs']
    ys     = lane['ys']
    coeffs = lane['coeffs']
    color  = COLORS[lane['color_idx']]

    xs_arr = np.array(xs, dtype=np.float32)
    ys_arr = np.array(ys, dtype=np.float32)

    try:
        # generate one point per pixel from the top of the detection
        # to the bottom of the ROI so the line is fully continuous with no gaps
        y_smooth = np.arange(
            max(ROI_TOP + 15, int(np.min(ys_arr))),
            ROI_BOTTOM,
            1
        ).astype(np.float32)

        if len(y_smooth) < 2:
            return

        x_smooth = np.polyval(coeffs, y_smooth)

        # stop the curve from extending beyond where the model actually detected points
        x_min    = np.min(xs_arr) - CURVE_MARGIN
        x_max    = np.max(xs_arr) + CURVE_MARGIN
        valid    = (x_smooth >= x_min) & (x_smooth <= x_max)
        x_smooth = np.clip(x_smooth[valid], 0, IMG_W - 1).astype(np.int32)
        y_smooth = y_smooth[valid].astype(np.int32)

        if len(y_smooth) < 2:
            return

        pts = np.stack([x_smooth, y_smooth], axis=1).reshape(-1, 1, 2)
        cv2.polylines(canvas, [pts], isClosed=False, color=color, thickness=4)

    except Exception:
        pts = np.array(list(zip([int(x) for x in xs], [int(y) for y in ys])), dtype=np.int32)
        cv2.polylines(canvas, [pts.reshape(-1, 1, 2)], False, color, 3)


video_start = time.time()
frame_idx   = 0
print("Processing  hang tight on CPU this takes a few minutes\n")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Video finished!")
        break

    frame_idx += 1
    frame_resized = cv2.resize(frame, (IMG_W, IMG_H))

    img_rgb      = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
    input_tensor = transform(Image.fromarray(img_rgb)).unsqueeze(0)

    t0 = time.time()
    with torch.no_grad():
        output = net(input_tensor)
    inference_ms = (time.time() - t0) * 1000
    frame_times.append(inference_ms)

    output_np   = output[0].numpy()
    scores_np   = output_np[:GRID_W, :, :]
    lane_points = np.argmax(scores_np, axis=0)
    max_scores  = np.max(scores_np, axis=0)
    exist_flags = max_scores > CONFIDENCE

    raw_lanes = []

    for lane_idx in range(4):
        xs, ys, confs = [], [], []

        for row_idx, row_anchor in enumerate(CULANE_ROW_ANCHORS):
            if not (ROI_TOP <= int(row_anchor) <= ROI_BOTTOM):
                continue

            if exist_flags[row_idx, lane_idx]:

                # score gap check — skip this point if the model is guessing.
                # a confident detection has one column that clearly beats the others.
                # if the scores are spread evenly across columns the model has no idea.
                score_gap = (np.max(scores_np[:, row_idx, lane_idx]) -
                             np.mean(scores_np[:, row_idx, lane_idx]))
                if score_gap < SCORE_GAP_THRESHOLD:
                    continue

                xs.append(int(col_sample[lane_points[row_idx, lane_idx]]))
                ys.append(int(row_anchor))
                confs.append(float(max_scores[row_idx, lane_idx]))

        # height span check — skip lanes that only fire on a short vertical strip.
        # real lanes span from near the car toward the horizon.
        # false positives from barriers and curbs are short patches.
        lane_span = (max(ys) - min(ys)) if ys else 0
        if lane_span < (ROI_BOTTOM - ROI_TOP) * MIN_LANE_HEIGHT_FRACTION:
            continue

        if len(xs) > MIN_POINTS:
            xs_arr = np.array(xs, dtype=np.float64)
            ys_arr = np.array(ys, dtype=np.float64)

            try:
                degree = 2 if len(xs) >= 7 else 1
                coeffs = np.polyfit(ys_arr, xs_arr, deg=degree)
                x_bottom = float(np.polyval(coeffs, ROI_BOTTOM))

                raw_lanes.append({
                    'coeffs'   : coeffs,
                    'xs'       : xs,
                    'ys'       : ys,
                    'x_bottom' : x_bottom,
                    'color_idx': lane_idx,
                })

                confidence_scores.append(np.mean(confs))
                points_per_lane.append(len(xs))

            except Exception:
                pass

    # pass through the smoother — this is what stops the dancing.
    # each drawn line is the average of this frame plus the last 4 frames.
    smoothed_lanes = smoother.update(raw_lanes)
    lanes_this_frame = len(smoothed_lanes)
    lanes_per_frame.append(lanes_this_frame)

    canvas  = frame_resized.copy()
    elapsed = time.time() - video_start
    avg_fps = frame_idx / elapsed if elapsed > 0 else 0
    eta     = (total_frames - frame_idx) / avg_fps if avg_fps > 0 else 0

    cv2.line(canvas, (0, ROI_TOP),    (IMG_W, ROI_TOP),    (50, 50, 50), 1)
    cv2.line(canvas, (0, ROI_BOTTOM), (IMG_W, ROI_BOTTOM), (50, 50, 50), 1)

    for lane in smoothed_lanes:
        draw_smooth_lane(canvas, lane)

    overlay = [
        f"Frame {frame_idx} of {total_frames}",
        f"Inference {inference_ms:.0f} ms   {1000/inference_ms:.1f} FPS",
        f"Average {avg_fps:.2f} FPS",
        f"ETA {int(eta//60)}m {int(eta%60)}s",
        f"Lanes detected {lanes_this_frame}",
    ]
    for i, txt in enumerate(overlay):
        cv2.putText(canvas, txt, (10, 22 + i * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 3)
        cv2.putText(canvas, txt, (10, 22 + i * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)

    out.write(canvas)

    if frame_idx % 25 == 0:
        print(f"  frame {frame_idx:>4} of {total_frames}   "
              f"{inference_ms:>5.0f} ms   "
              f"lanes {lanes_this_frame}   "
              f"eta {int(eta//60)}m {int(eta%60)}s")


cap.release()
out.release()
total_time = time.time() - video_start

no_lane    = lanes_per_frame.count(0)
one_lane   = sum(1 for x in lanes_per_frame if x == 1)
two_lane   = sum(1 for x in lanes_per_frame if x == 2)
three_plus = sum(1 for x in lanes_per_frame if x >= 3)

print("\n" + "=" * 60)
print("Evaluation Report  UFLD CULane")
print("=" * 60)

print("\nVideo info")
print(f"  file              {os.path.basename(VIDEO_IN)}")
print(f"  duration          {total_frames/fps:.1f} seconds")
print(f"  resize mode       full frame to 800x288  no sky crop")
print(f"  smoothing         {SMOOTHING_WINDOW} frame averaging window")

print("\nSpeed")
print(f"  total time        {total_time:.1f} sec  ({total_time/60:.1f} min)")
print(f"  avg per frame     {np.mean(frame_times):.1f} ms")
print(f"  fastest frame     {np.min(frame_times):.1f} ms")
print(f"  slowest frame     {np.max(frame_times):.1f} ms")
print(f"  avg speed         {total_frames/total_time:.2f} FPS")
print(f"  real time         {'yes' if total_frames/total_time >= fps else 'no  GPU needed for real time'}")

print("\nDetection")
print(f"  frames processed  {total_frames}")
print(f"  avg lanes         {np.mean(lanes_per_frame):.2f} per frame")
if confidence_scores:
    print(f"  avg confidence    {min(np.mean(confidence_scores)/20.0, 1.0):.4f}")
    print(f"  avg points        {np.mean(points_per_lane):.1f} per lane")
print(f"  0 lanes           {no_lane} frames  ({100*no_lane/total_frames:.1f}%)")
print(f"  1 lane            {one_lane} frames  ({100*one_lane/total_frames:.1f}%)")
print(f"  2 lanes           {two_lane} frames  ({100*two_lane/total_frames:.1f}%)")
print(f"  3 or more         {three_plus} frames  ({100*three_plus/total_frames:.1f}%)")

print("\nPublished benchmark  CULane dataset  from original paper")
print(f"  F1 overall        68.4%")
print(f"  F1 night          66.3%  most relevant to our footage")
print(f"  F1 crowded        69.7%")
print(f"  F1 no marking     41.7%")
print(f"  GPU speed         322 FPS  vs our {total_frames/total_time:.1f} FPS on CPU")

print("\n" + "=" * 60)
print(f"output saved to {VIDEO_OUT}")