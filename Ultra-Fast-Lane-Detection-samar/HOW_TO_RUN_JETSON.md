# Jetson Setup — Lane Detection
### Written for Samar

Hey Samar, this file walks you through everything you need to get the lane detection running on the Jetson. Read it top to bottom before doing anything — it's not long and it'll save you from running into issues halfway through.

---

## What you need before starting

- The Jetson board with JetPack installed (JetPack 5.x or higher)
- These two files copied onto the Jetson:
  - `culane_18.onnx` — the exported model (see the section below on how to get it)
  - `lane_detector.py` — the main detection script
- A camera connected to the Jetson (USB or CSI)
- An internet connection on the Jetson for the first-time package installs

---

## Step 1 — Get the ONNX file from the laptop

On the graduation project laptop, open `lane_detector.py` and scroll to the very bottom. You'll see this line commented out:

```python
# export_to_onnx(WEIGHTS, output_path='culane_18.onnx')
```

Remove the `#` at the start so it looks like this:

```python
export_to_onnx(WEIGHTS, output_path='culane_18.onnx')
```

Run the script once. It will create `culane_18.onnx` in the same folder as the script. Copy that file to the Jetson — USB drive or scp both work.

---

## Step 2 — Convert ONNX to TensorRT on the Jetson

This step only needs to happen once. Open a terminal on the Jetson and run:

```bash
trtexec --onnx=culane_18.onnx --saveEngine=culane_fp16.engine --fp16
```

If trtexec is not found, it's usually hiding here:

```bash
/usr/src/tensorrt/bin/trtexec --onnx=culane_18.onnx --saveEngine=culane_fp16.engine --fp16
```

This will take a few minutes. When it finishes you'll have a file called `culane_fp16.engine`. This is the optimized version of the model that runs at full Jetson GPU speed.

What `--fp16` means: the model runs in half precision instead of full precision. This doubles the speed and cuts memory usage in half with almost no difference in accuracy. You always want this on Jetson.

---

## Step 3 — Install Python dependencies on the Jetson

Run these in a terminal:

```bash
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip3 install opencv-python Pillow numpy
```

JetPack usually comes with PyTorch pre-installed. If the above command fails, check what version is already there first:

```bash
python3 -c "import torch; print(torch.__version__)"
```

If it prints something, you already have it and can skip the torch install line.

---

## Step 4 — Run on live camera

The `lane_detector.py` script reads from a video file by default. To switch to a live camera feed, open the file and find this line near the bottom:

```python
cap = cv2.VideoCapture(video_in)
```

Change `video_in` to `0` for a USB camera:

```python
cap = cv2.VideoCapture(0)
```

Or if you're using a CSI camera (the ribbon cable type):

```python
cap = cv2.VideoCapture("nvarguscamerasrc ! video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1 ! nvvidconv ! video/x-raw, format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink", cv2.CAP_GSTREAMER)
```

Then run:

```bash
python3 lane_detector.py
```

---

## Step 5 — Check it's actually using the GPU

When the script starts it prints which device it's running on. You should see:

```
running on cuda
gpu: NVIDIA Orin (or whatever your board is)
```

If it says `running on cpu` then CUDA isn't being picked up. Check that your PyTorch installation has CUDA support:

```bash
python3 -c "import torch; print(torch.cuda.is_available())"
```

If it prints `False`, you need to reinstall PyTorch with the CUDA-enabled version. Come back to Step 3 and try again with the right wheel URL for your JetPack version.

---

## Expected performance on Jetson

| Board | Expected FPS |
|---|---|
| Jetson Orin | 80-120 FPS |
| Jetson AGX Xavier | 50-80 FPS |
| Jetson Nano | 15-25 FPS |

With the TensorRT engine (Step 2) you'll get roughly double these numbers compared to running the raw PyTorch model.

---

## What the output shows

While running you'll see a window (or output video) with colored lines drawn on the road. Each line is a detected lane boundary. The overlay in the top left shows:

- **frame X of Y** — which frame you're on
- **ms per frame** — how long each frame takes to process
- **avg FPS** — average processing speed
- **lanes found** — how many lanes were detected this frame

---

## Common problems

**Camera not opening**
Try changing the camera index from `0` to `1` or `2`. Run `ls /dev/video*` to see what cameras are available on the system.

**CUDA not available**
Your PyTorch version doesn't have CUDA support. Reinstall using the JetPack-specific wheel — check the NVIDIA forums for the exact URL matching your JetPack version.

**trtexec not found**
Find it with: `find / -name trtexec 2>/dev/null`

**Model loads but output is all wrong**
Make sure the weights file is `culane_18.pth` and not the TuSimple version. The two are not interchangeable.

**Screen flickers or display issues**
If running headlessly (no monitor), remove the `cv2.imshow` line and just let it write to the output file.

---

## Files you need on the Jetson

```
lane_detector.py
culane_18.pth        (original PyTorch weights)
culane_18.onnx       (exported from laptop, needed for TensorRT conversion)
culane_fp16.engine   (generated by trtexec in Step 2)
model/               (the model folder from the repo)
```

The `model/` folder contains `model.py` and `backbone.py` which the script imports. Without them it crashes immediately.

---

Good luck Samar! If something isn't working ping the team and we'll figure it out.
