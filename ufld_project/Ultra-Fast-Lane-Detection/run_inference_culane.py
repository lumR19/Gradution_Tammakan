import torch
import cv2
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
import sys
import time
import os
import warnings
 
# I'm suppressing the deprecation warnings from older torchvision API calls
# inside the UFLD repo itself — they don't affect anything, just noise
warnings.filterwarnings("ignore")
 
sys.path.insert(0, '.')
from model.model import parsingNet
 
 
# =============================================================================
# UFLD Lane Detection — CULane Pretrained Model
# This script runs inference on any video using the CULane trained weights.
# No training here — we're just using what the model already learned.
#
# The only thing you need to change between videos is VIDEO_IN below.
# Everything else figures itself out automatically.
# =============================================================================
 
 
# --- the only 2 things you need to change per video -------------------------
WEIGHTS  = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\culane_18.pth'
VIDEO_IN = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\2video_test_night.mp4'
# -----------------------------------------------------------------------------
 
# the output file is named automatically after the input — no need to touch this
OUTPUT_DIR = r'C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection\test_output_Culane'
os.makedirs(OUTPUT_DIR, exist_ok=True)
VIDEO_OUT  = os.path.join(OUTPUT_DIR, os.path.splitext(os.path.basename(VIDEO_IN))[0] + '_culane_output.mp4')
 
 
# --- model architecture settings — these come from the original paper --------
# the CULane model was trained with these exact numbers, so we can't change them
# without retraining from scratch (which we're not doing)
BACKBONE     = '18'       # ResNet-18 — lighter and faster than ResNet-34/50
IMG_W        = 800        # width the model expects — hardcoded in the architecture
IMG_H        = 288        # height the model expects — same reason
GRID_W       = 200        # how many horizontal positions the model checks per row
 
# these are the 18 horizontal "scan lines" where the model looks for lane points
# I scaled them to fit within our 288px image height after resizing
# originally they were 260-430 for a 590px image — I had to recalculate them
CULANE_ROW_ANCHORS = [
    80,  93, 106, 119, 132, 145, 158, 171, 184,
    197, 210, 223, 236, 249, 262, 275, 275, 280
]
 
# the model was trained on 1640px wide images but we use 800px
# so I scale the x-coordinates proportionally to avoid a horizontal offset
# this was one of the bugs I had to fix — without this the lanes were shifted
col_sample = np.linspace(0, 1640 - 1, GRID_W) * (IMG_W / 1640)
 
# 4 lanes, 4 colors — easy to tell apart on screen
COLORS = [
    ( 80,  80, 255),   # lane 0 — blue
    ( 80, 255,  80),   # lane 1 — green
    (255, 150,  80),   # lane 2 — orange
    ( 80, 220, 255),   # lane 3 — cyan
]
 
 
# --- adaptive confidence settings --------------------------------------------
# this is something I added on top of the original model — it wasn't in the paper
# the idea: at night, lane markings are faint so the model's confidence is lower
# if I use the same strict threshold for night and day, I miss lanes at night
# so the script checks brightness each frame and adjusts the threshold automatically
 
BASE_CONFIDENCE = 0.15   # used for daytime — strict enough to avoid false lanes
DARK_CONFIDENCE = 0.08   # used for night/tunnel — relaxed so we catch faint markings
DARK_THRESHOLD  = 80     # if average brightness < 80 out of 255, we treat it as dark
 
# ROI = Region of Interest — the area of the image we actually care about
# the top part is sky (useless), the bottom part is the car hood (also useless)
# I define these as percentages so they work regardless of video resolution
ROI_TOP_FRAC    = 0.35   # ignore the top 35% of the frame (sky / signs / overhead)
ROI_BOTTOM_FRAC = 0.92   # ignore the bottom 8% (car hood)
 
# a lane needs at least this many detected points to be counted as a real lane
# if we require too few, we get ghost lanes from road texture or shadows
MIN_POINTS   = 4
 
# when drawing the smooth curve, how far can it extend beyond the detected points
# too large = wild arcs when points are noisy, too small = curve gets cut short
CURVE_MARGIN = 40
 
 
# --- load the model ----------------------------------------------------------
print("=" * 60)
print("  UFLD — CULane pretrained  |  General purpose inference")
print("=" * 60)
print("\nBuilding model architecture and loading weights...")
 
# build the model structure — at this point it has random weights
net = parsingNet(
    pretrained=False,                              # don't download ImageNet weights
    backbone=BACKBONE,
    cls_dim=(GRID_W + 1, len(CULANE_ROW_ANCHORS), 4),  # (201, 18, 4) — must match the checkpoint
    use_aux=False                                  # auxiliary branch is only used during training
)
 
# load the pretrained weights from the .pth file
# map_location='cpu' is critical — the weights were saved on a GPU machine
# without this it would crash on our CPU-only setup
state_dict = torch.load(WEIGHTS, map_location='cpu')
if 'model' in state_dict:
    state_dict = state_dict['model']
 
# the CULane weights were saved from multi-GPU training
# that adds a 'module.' prefix to every key — we strip it here so the keys match
compatible_state_dict = {}
for k, v in state_dict.items():
    compatible_state_dict[k[7:] if 'module.' in k else k] = v
 
# strict=False means if a key doesn't match perfectly, skip it instead of crashing
net.load_state_dict(compatible_state_dict, strict=False)
 
# eval mode disables dropout and batchnorm randomness
# always do this for inference — training mode would give different results each run
net.eval()
print("Weights loaded successfully!\n")
 
 
# --- image preprocessing pipeline -------------------------------------------
# every frame goes through this before hitting the model
# the normalization values (mean/std) are the ImageNet standard ones
# the model's backbone (ResNet-18) was pretrained on ImageNet so it expects these
transform = transforms.Compose([
    transforms.ToTensor(),       # converts pixel values from 0-255 to 0.0-1.0
    transforms.Normalize(
        mean=(0.485, 0.456, 0.406),
        std=(0.229, 0.224, 0.225)
    )
])
 
 
# --- open the input video ----------------------------------------------------
cap = cv2.VideoCapture(VIDEO_IN)
if not cap.isOpened():
    raise FileNotFoundError(f"Could not find or open: {VIDEO_IN}")
 
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps          = cap.get(cv2.CAP_PROP_FPS)
orig_w       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
orig_h       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
 
# convert ROI fractions to actual pixel values for this video
ROI_TOP    = int(IMG_H * ROI_TOP_FRAC)
ROI_BOTTOM = int(IMG_H * ROI_BOTTOM_FRAC)
 
print(f"Video        : {os.path.basename(VIDEO_IN)}")
print(f"Frames       : {total_frames}  |  {fps} FPS  |  original size {orig_w}x{orig_h}")
print(f"Model input  : {IMG_W}x{IMG_H}  (every frame gets resized to this)")
print(f"ROI zone     : rows {ROI_TOP} to {ROI_BOTTOM}  (road-only detection area)")
print(f"Output       : {os.path.basename(VIDEO_OUT)}\n")
 
# set up the output video writer — same FPS as input so playback speed is correct
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out    = cv2.VideoWriter(VIDEO_OUT, fourcc, fps, (IMG_W, IMG_H))
 
 
# --- storage for metrics we'll report at the end ----------------------------
frame_times       = []   # how long each frame took to process (ms)
lanes_per_frame   = []   # how many lanes were found in each frame
confidence_scores = []   # average model confidence per detected lane
points_per_lane   = []   # how many row anchors each lane hit
brightness_values = []   # average brightness per frame (to track day vs night)
 
 
# =============================================================================
# HELPER FUNCTION 1 — adaptive confidence based on scene brightness
# =============================================================================
def get_adaptive_confidence(frame):
    # convert frame to grayscale so we can measure brightness easily
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
 
    # only measure brightness in the road zone — sky and hood would skew the result
    road_region = gray[ROI_TOP:ROI_BOTTOM, :]
    brightness  = float(np.mean(road_region))
    brightness_values.append(brightness)
 
    # dark scene = use lower threshold so we don't miss faint night lanes
    # bright scene = use higher threshold so we don't get false detections
    if brightness < DARK_THRESHOLD:
        return DARK_CONFIDENCE
    else:
        return BASE_CONFIDENCE
 
 
# =============================================================================
# HELPER FUNCTION 2 — smooth lane drawing using polynomial curve fitting
# =============================================================================
def draw_smooth_lane(canvas, xs, ys, color):
    # if we only got 1 or 2 points, a curve doesn't make sense — just draw dots
    if len(xs) < 3:
        for x, y in zip(xs, ys):
            cv2.circle(canvas, (int(x), int(y)), 4, color, -1)
        return
 
    xs_arr = np.array(xs, dtype=np.float32)
    ys_arr = np.array(ys, dtype=np.float32)
 
    try:
        # fit x as a function of y — lanes are mostly vertical so this works well
        # degree 2 gives a gentle parabola which is realistic for road curves
        # degree 1 would give a straight line (too rigid for curves)
        # degree 3+ would overfit to noisy points (too wiggly)
        coeffs = np.polyfit(ys_arr, xs_arr, deg=2)
 
        # generate a smooth set of y values every 2 pixels within the detected range
        y_smooth = np.arange(
            max(ROI_TOP,    int(np.min(ys_arr))),
            min(ROI_BOTTOM, int(np.max(ys_arr)) + 1),
            2
        ).astype(np.float32)
 
        if len(y_smooth) < 2:
            return
 
        # evaluate the polynomial at each y to get the corresponding x
        x_smooth = np.polyval(coeffs, y_smooth)
 
        # clipping: don't let the curve wander more than CURVE_MARGIN pixels
        # beyond where the model actually detected points — prevents wild arcs
        x_min = np.min(xs_arr) - CURVE_MARGIN
        x_max = np.max(xs_arr) + CURVE_MARGIN
        valid    = (x_smooth >= x_min) & (x_smooth <= x_max)
        x_smooth = x_smooth[valid]
        y_smooth = y_smooth[valid]
 
        if len(y_smooth) < 2:
            return
 
        # make sure we don't draw outside the image boundaries
        x_smooth = np.clip(x_smooth, 0, IMG_W - 1).astype(np.int32)
        y_smooth = y_smooth.astype(np.int32)
 
        # draw the smooth curve through all the interpolated points
        pts = np.stack([x_smooth, y_smooth], axis=1).reshape(-1, 1, 2)
        cv2.polylines(canvas, [pts], isClosed=False, color=color, thickness=4)
 
        # also show the raw detection dots so we can see where the model actually fired
        for x, y in zip(xs, ys):
            cv2.circle(canvas, (int(x), int(y)), 3, color, -1)
 
    except Exception:
        # if the polynomial fit fails for any reason, fall back to a basic line
        pts = np.array(list(zip(xs, ys)), dtype=np.int32)
        cv2.polylines(canvas, [pts.reshape(-1, 1, 2)], False, color, 3)
 
 
# =============================================================================
# MAIN PROCESSING LOOP — go through every frame in the video
# =============================================================================
video_start = time.time()
frame_idx   = 0
print("Starting inference — this will take a while on CPU, hang tight\n")
 
while True:
    ret, frame = cap.read()
    if not ret:
        # ret becomes False when we've read the last frame
        print("Done — reached end of video!")
        break
 
    frame_idx += 1
 
    # resize to model input size — the architecture requires exactly 800x288
    frame_resized = cv2.resize(frame, (IMG_W, IMG_H))
 
    # figure out what kind of scene this is and pick the right confidence level
    confidence = get_adaptive_confidence(frame_resized)
 
    # convert BGR to RGB — OpenCV reads as BGR but PyTorch expects RGB
    img_rgb      = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
    input_tensor = transform(Image.fromarray(img_rgb)).unsqueeze(0)  # add batch dimension
 
    # run the model — no_grad means we skip gradient tracking (saves memory + time)
    # we're only doing inference, not backpropagation, so we don't need gradients
    t0 = time.time()
    with torch.no_grad():
        output = net(input_tensor)
    inference_ms = (time.time() - t0) * 1000
    frame_times.append(inference_ms)
 
    # --- decode the model output ---------------------------------------------
    # output shape is (1, 201, 18, 4) — batch x columns x rows x lanes
    # for each lane and each row, the model gives a probability over 200 columns
    # argmax picks the column with the highest probability = predicted x position
    output_np   = output[0].numpy()
    scores_np   = output_np[:GRID_W, :, :]         # drop the "no lane" class
    lane_points = np.argmax(scores_np, axis=0)     # shape (18, 4) — best column per row per lane
    max_scores  = np.max(scores_np, axis=0)        # shape (18, 4) — confidence at that column
    exist_flags = max_scores > confidence          # True only if confident enough
 
    # --- draw the detected lanes on the frame --------------------------------
    canvas           = frame_resized.copy()
    lanes_this_frame = 0
    elapsed          = time.time() - video_start
    avg_fps          = frame_idx / elapsed if elapsed > 0 else 0
    eta              = (total_frames - frame_idx) / avg_fps if avg_fps > 0 else 0
 
    # draw thin lines to show where the ROI boundaries are
    cv2.line(canvas, (0, ROI_TOP),    (IMG_W, ROI_TOP),    (50, 50, 50), 1)
    cv2.line(canvas, (0, ROI_BOTTOM), (IMG_W, ROI_BOTTOM), (50, 50, 50), 1)
 
    for lane_idx in range(4):
        xs, ys, confs = [], [], []
 
        for row_idx, row_anchor in enumerate(CULANE_ROW_ANCHORS):
            # skip any row anchor that falls outside our road zone
            if not (ROI_TOP <= int(row_anchor) <= ROI_BOTTOM):
                continue
 
            if exist_flags[row_idx, lane_idx]:
                # convert grid column index back to actual pixel x coordinate
                x = int(col_sample[lane_points[row_idx, lane_idx]])
                y = int(row_anchor)
                xs.append(x)
                ys.append(y)
                confs.append(float(max_scores[row_idx, lane_idx]))
 
        # only draw if we have enough confident points — single points are unreliable
        if len(xs) > MIN_POINTS:
            lanes_this_frame += 1
            confidence_scores.append(np.mean(confs))
            points_per_lane.append(len(xs))
            draw_smooth_lane(canvas, xs, ys, COLORS[lane_idx])
 
    lanes_per_frame.append(lanes_this_frame)
 
    # figure out what to label the scene on screen
    brightness  = brightness_values[-1]
    scene_label = "Night/Tunnel" if brightness < DARK_THRESHOLD else "Daytime"
 
    # write live stats on the frame so we can see what's happening during playback
    overlay = [
        f"Frame: {frame_idx}/{total_frames}",
        f"Inference: {inference_ms:.0f} ms  ({1000/inference_ms:.1f} FPS)",
        f"Avg FPS: {avg_fps:.2f}",
        f"ETA: {int(eta//60)}m {int(eta%60)}s",
        f"Lanes: {lanes_this_frame} | Scene: {scene_label}",
        f"Brightness: {brightness:.0f}/255 | Conf threshold: {confidence:.2f}",
    ]
    for i, txt in enumerate(overlay):
        # draw text twice — once thick black for outline, once thin white on top
        # this makes it readable on any background color
        cv2.putText(canvas, txt, (10, 22 + i * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 3)
        cv2.putText(canvas, txt, (10, 22 + i * 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
 
    out.write(canvas)
 
    # print progress every 25 frames so we know it's still running
    if frame_idx % 25 == 0:
        print(f"  Frame {frame_idx:>4}/{total_frames}  |  "
              f"{inference_ms:>5.0f} ms  |  "
              f"Lanes: {lanes_this_frame}  |  "
              f"Scene: {scene_label:<13}  |  "
              f"ETA: {int(eta//60)}m {int(eta%60)}s")
 
 
# --- cleanup -----------------------------------------------------------------
cap.release()   # release the video file handle
out.release()   # this is important — without it the output file gets corrupted
total_time = time.time() - video_start
 
 
# =============================================================================
# FINAL EVALUATION REPORT
# these are the numbers we report in the paper and show to the supervisor
# =============================================================================
no_lane_frames    = lanes_per_frame.count(0)
one_lane_frames   = sum(1 for x in lanes_per_frame if x == 1)
two_lane_frames   = sum(1 for x in lanes_per_frame if x == 2)
three_lane_frames = sum(1 for x in lanes_per_frame if x >= 3)
night_frames      = sum(1 for b in brightness_values if b < DARK_THRESHOLD)
day_frames        = total_frames - night_frames
 
print("\n" + "=" * 60)
print("        EVALUATION REPORT — UFLD CULane")
print("=" * 60)
 
# video info — basic facts about the test clip
print(f"\n  [Video Info]")
print(f"  File                     : {os.path.basename(VIDEO_IN)}")
print(f"  Duration                 : {total_frames/fps:.1f} sec")
print(f"  Daytime frames           : {day_frames} ({100*day_frames/total_frames:.1f}%)")
print(f"  Night/Tunnel frames      : {night_frames} ({100*night_frames/total_frames:.1f}%)")
print(f"  Avg scene brightness     : {np.mean(brightness_values):.1f}/255")
 
# speed metrics — how fast did we process the video
# on CPU we can't do real-time but that's expected and explainable
print(f"\n  [Speed Metrics]")
print(f"  Total processing time    : {total_time:.1f} sec ({total_time/60:.1f} min)")
print(f"  Avg inference per frame  : {np.mean(frame_times):.1f} ms")
print(f"  Min inference time       : {np.min(frame_times):.1f} ms")
print(f"  Max inference time       : {np.max(frame_times):.1f} ms")
print(f"  Avg processing speed     : {total_frames/total_time:.2f} FPS")
print(f"  Real-time capable (CPU)  : {'YES' if total_frames/total_time >= fps else 'NO — expected on CPU, GPU needed for real-time'}")
 
# detection metrics — how well did the model actually find lanes
print(f"\n  [Detection Metrics]")
print(f"  Total frames processed   : {total_frames}")
print(f"  Avg lanes per frame      : {np.mean(lanes_per_frame):.2f}")
if confidence_scores:
    print(f"  Avg points per lane      : {np.mean(points_per_lane):.1f} out of {len(CULANE_ROW_ANCHORS)} anchors")
print(f"  Frames with 0 lanes      : {no_lane_frames} ({100*no_lane_frames/total_frames:.1f}%)")
print(f"  Frames with 1 lane       : {one_lane_frames} ({100*one_lane_frames/total_frames:.1f}%)")
print(f"  Frames with 2 lanes      : {two_lane_frames} ({100*two_lane_frames/total_frames:.1f}%)")
print(f"  Frames with 3+ lanes     : {three_lane_frames} ({100*three_lane_frames/total_frames:.1f}%)")
 
# published numbers from the original paper — we cite these directly
# they were measured on the official CULane test set with a GPU
print(f"\n  [Published Benchmark — from original UFLD paper, CULane dataset]")
print(f"  F1 Score (overall)       : 68.4%")
print(f"  F1 Score (night)         : 66.3%   <- most relevant to our nighttime test")
print(f"  F1 Score (crowded roads) : 69.7%")
print(f"  F1 Score (no line)       : 41.7%   <- hardest scenario")
print(f"  Speed on GPU             : 322 FPS  <- vs our {total_frames/total_time:.1f} FPS on CPU")
print("=" * 60)
print(f"\n  Output saved to: {VIDEO_OUT}")
 