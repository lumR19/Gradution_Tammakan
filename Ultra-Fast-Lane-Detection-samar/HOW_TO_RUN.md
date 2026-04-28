# How to Run lane_detector.py

Everything you need to know to run the lane detection, switch between CPU and GPU,
use the detector inside another script, and export to Jetson.

---

## What you need before running

Make sure these exist on your machine:

- Python 3.8 or higher with the venv activated
- `culane_18.pth` inside the `Ultra-Fast-Lane-Detection` folder
- Your test video somewhere on disk
- Dependencies installed:

```
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install opencv-python Pillow numpy
```

If you have a GPU and want to use it, install the GPU version of PyTorch instead:

```
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

---

## Running on a video

Open a terminal, go into the project folder and activate the venv:

```
cd C:\Users\Lenovo\Desktop\Graduation_tammakan\ufld_project\Ultra-Fast-Lane-Detection
venv\Scripts\activate
```

Open `lane_detector.py` and change the two paths at the bottom of the file:

```python
WEIGHTS  = r'C:\path\to\culane_18.pth'
VIDEO_IN = r'C:\path\to\your_video.mp4'
```

Then run:

```
python lane_detector.py
```

The output video saves automatically to `test_output_Culane` with `_culane_output.mp4`
added to the original filename. The folder is created automatically if it doesn't exist.

---

## GPU vs CPU

The script picks GPU automatically if one is available and falls back to CPU if not.
You do not need to change anything for this to work.

If you want to force a specific device, find this line at the bottom of the file:

```python
run_on_video(WEIGHTS, VIDEO_IN, OUTPUT_DIR)
```

And change it to:

```python
run_on_video(WEIGHTS, VIDEO_IN, OUTPUT_DIR, device='cpu')    # force CPU
run_on_video(WEIGHTS, VIDEO_IN, OUTPUT_DIR, device='cuda')   # force GPU
```

On your current laptop the terminal will print `Device: cpu`.
On a machine with a GPU it will print the GPU name automatically.

---

## What the terminal output means while it runs

```
Frame   50/387  |   310 ms  |  Lanes: 4  |  Scene: Night/Tunnel  |  ETA: 1m 42s
```

- `Frame 50/387` — current frame out of total
- `310 ms` — how long that specific frame took
- `Lanes: 4` — how many lanes were found in that frame
- `Scene` — whether the brightness check decided this is night or daytime
- `ETA` — estimated minutes and seconds until the video finishes

---

## Using LaneDetector inside another script

Import the class and call `.update()` on each frame:

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
    cv2.imshow('result', canvas)
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
```

Each lane dict you get back looks like this:

```
poly_coeffs   array([a, b, c])    x = a*y^2 + b*y + c
x_at_bottom   423.5               x position at the bottom of the road zone
side          'left'              or 'right' — relative to image center
confidence    0.73                normalized 0.0 to 1.0
points_xy     [(x1,y1), ...]      raw detected anchor points before smoothing
```

To get the x position of a lane at any y coordinate:

```python
import numpy as np
y = 200
x = np.polyval(lane['poly_coeffs'], y)
```

---

## Exporting to ONNX for Jetson TensorRT

This is a two step process. Step one on your laptop, step two on the Jetson.

Step one — export on your laptop. Find this line at the bottom of `lane_detector.py`:

```python
# export_to_onnx(WEIGHTS, output_path='culane_18.onnx')
```

Remove the `#` and run the script once. You will get `culane_18.onnx` in the folder.

Step two — on the Jetson. Copy `culane_18.onnx` to the Jetson and open a terminal there:

```
trtexec --onnx=culane_18.onnx --saveEngine=culane_fp16.engine --fp16
```

This creates `culane_fp16.engine` which is the optimized model that runs at full Jetson
GPU speed. The `--fp16` flag tells it to use half precision numbers — twice the throughput,
half the memory, almost no accuracy drop compared to full precision.

`trtexec` is pre-installed on Jetson with JetPack. If it is not found, try:

```
/usr/src/tensorrt/bin/trtexec --onnx=culane_18.onnx --saveEngine=culane_fp16.engine --fp16
```

---

## What the modifications actually did

**Modification 1 — LaneDetector class with .update(frame)**

Before, the code was one long script that ran top to bottom. Now it is a class.
Other programs can import it and use it like a plug-in without copying the whole script.
The `.update()` method takes one frame and returns structured lane data.

**Modification 2 — visualize() as a separate function**

Detection and drawing used to be mixed together in the same loop.
Now detection is `.update()` and drawing is `visualize()`. You can run detection
without drawing if you only need the data, or change how lanes look on screen
without touching the detection code at all.

**Modification 3 — ONNX export for Jetson TensorRT FP16**

The `export_to_onnx()` function converts the PyTorch model to a universal format
that TensorRT on the Jetson can read and optimize. FP16 means half precision — the
model runs in 16-bit instead of 32-bit, which doubles throughput on Jetson hardware.

**Modification 4 — GPU support**

The model and all tensors now move to whatever device is available. On CPU nothing
changes. On a GPU the model loads onto the GPU and every frame tensor moves there
before inference, then the output comes back to CPU for drawing. The device switch
is automatic — no code changes needed between machines.

---

## Common errors

`FileNotFoundError: culane_18.pth` — the WEIGHTS path is wrong. Check the path at the bottom of the file.

`ModuleNotFoundError: model.model` — you are not running from inside the
Ultra-Fast-Lane-Detection folder. The terminal must be in that directory.

`RuntimeError: size mismatch` — cls_dim changed. It must stay as (201, 18, 4).
Do not change GRID_W or CULANE_ROW_ANCHORS length independently.

`Output video is empty or corrupted` — the script was interrupted before
`writer.release()` ran. Let the script finish normally.

`CUDA out of memory` — only happens when forcing `device='cuda'` on a low VRAM GPU.
Switch to CPU or use the Jetson export path instead.
