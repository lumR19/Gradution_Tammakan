# How to Run lane_detector.py

This file tells you everything you need to run the lane detection script, export it for Jetson, and use it inside another project.

---

## Before you start — make sure you have these

1. Python 3.8 or higher
2. The virtual environment we created (`venv`)
3. The weights file `culane_18.pth` inside the `Ultra-Fast-Lane-Detection` folder
4. Your test video somewhere on your machine

If you haven't installed the dependencies yet, activate the venv and run:

```
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install opencv-python Pillow numpy
```

---

## Running on a video (the normal way)

Open a terminal inside `Ultra-Fast-Lane-Detection` and activate your venv:

```
cd C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection
venv\Scripts\activate
```

Open `lane_detector.py` and change these two lines at the bottom of the file to point to your weights and your video:

```python
WEIGHTS  = r'C:\path\to\culane_18.pth'
VIDEO_IN = r'C:\path\to\your_video.mp4'
```

Then run:

```
python lane_detector.py
```

The output video will be saved automatically inside `test_output_Culane` with `_culane_output.mp4` added to the filename. You don't need to create that folder manually — the script creates it if it doesn't exist.

---

## Switching between CPU and GPU

By default the script picks GPU if one is available and falls back to CPU if not. You don't need to change anything.

If you want to force one or the other, find this line in the `if __name__ == '__main__'` block at the bottom:

```python
run_on_video(WEIGHTS, VIDEO_IN, OUTPUT_DIR)
```

And change it to:

```python
run_on_video(WEIGHTS, VIDEO_IN, OUTPUT_DIR, device='cpu')   # force CPU
run_on_video(WEIGHTS, VIDEO_IN, OUTPUT_DIR, device='cuda')  # force GPU
```

---

## Using LaneDetector inside another script

If you want to plug the detector into another project, import it like this:

```python
import cv2
from lane_detector import LaneDetector, visualize

detector = LaneDetector(weights_path='culane_18.pth')

cap = cv2.VideoCapture('your_video.mp4')
while True:
    ret, frame = cap.read()
    if not ret:
        break

    lanes = detector.update(frame)

    for lane in lanes:
        print(lane['side'], lane['confidence'], lane['x_at_bottom'])

    canvas = visualize(frame, lanes)
    cv2.imshow('lanes', canvas)
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
```

Each lane you get back looks like this:

```
{
    'poly_coeffs'  : array([a, b, c])   x = a*y^2 + b*y + c
    'x_at_bottom'  : 423.5              x position at bottom of the road zone
    'side'         : 'left'             or 'right' — relative to image center
    'confidence'   : 0.84               average model score across detected points
    'points_xy'    : [(x1,y1), ...]     the raw anchor detections before smoothing
}
```

To get the x position of a lane at any y position use:

```python
import numpy as np
y = 200
x = np.polyval(lane['poly_coeffs'], y)
```

---

## Exporting to ONNX for Jetson TensorRT

This is a two step process. Step one runs on your laptop, step two runs on the Jetson.

**Step one — export on your laptop**

Find this line at the bottom of `lane_detector.py`:

```python
# export_to_onnx(WEIGHTS, output_path='culane_18.onnx')
```

Remove the `#` to uncomment it and run the script once. It will create `culane_18.onnx` in the same folder.

```
python lane_detector.py
```

**Step two — convert on the Jetson**

Copy `culane_18.onnx` to your Jetson board, then open a terminal there and run:

```
trtexec --onnx=culane_18.onnx --saveEngine=culane_fp16.engine --fp16
```

This creates `culane_fp16.engine` which is the optimized model that runs at full Jetson GPU speed. `--fp16` means it uses half precision numbers — twice as fast as the default, half the memory usage, and almost no accuracy difference.

`trtexec` comes pre-installed on Jetson with JetPack. If it's not found, it's usually at `/usr/src/tensorrt/bin/trtexec`.

---

## What the terminal output means while it runs

```
Frame   50/387  |    310 ms  |  Lanes: 4  |  Scene: Night/Tunnel   |  ETA: 1m 42s
```

Frame 50/387 — which frame we're on out of the total  
310 ms — how long that frame took to process  
Lanes: 4 — how many lanes were detected in that frame  
Scene — whether the script decided this frame is night or daytime based on brightness  
ETA — estimated time until the whole video is done  

---

## What the final report numbers mean

**Avg inference per frame** — average time in milliseconds to process one frame. On CPU expect 250-400ms. On a Jetson GPU expect under 10ms.

**Avg processing speed** — frames per second we achieved. The video is 25 FPS so if this is below 25 we can't do it in real time, which is expected on CPU.

**Avg lanes per frame** — how many lanes the model found on average. A normal highway should give 3-4.

**Frames with 0 lanes** — how many frames the model found nothing. A high number here (above 20%) means the video conditions are challenging for the model.

**F1 Score night 66.3%** — this is the official score from the original paper measured on the CULane nighttime test set. It's the most relevant benchmark for our nighttime Saudi footage. We cite this number directly in the paper since we don't have ground truth labels for our own video.

---

## Common errors and how to fix them

`FileNotFoundError: culane_18.pth` — the weights path is wrong. Double check the WEIGHTS variable at the bottom of the file.

`ModuleNotFoundError: model.model` — you're not running from inside the Ultra-Fast-Lane-Detection folder. Make sure your terminal is in that directory.

`RuntimeError: shape mismatch` — something changed in cls_dim. It must stay as (201, 18, 4) to match the CULane weights.

`CUDA out of memory` — only happens if you force `device='cuda'` on a GPU with very little VRAM. Switch back to CPU or reduce batch size.

`Output video is corrupted / won't open` — this happens when the script is interrupted before `out.release()` runs. Let the script finish normally and it won't happen.
