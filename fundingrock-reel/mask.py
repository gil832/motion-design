"""Per-frame person matte for the talking-head clip, using the MediaPipe
selfie-multiclass (256x256) TFLite model through LiteRT. Writes a lossless
grayscale FFV1 video at 540x960 / 30 fps.

Usage: python3 mask.py INPUT.mp4 selfie_multiclass_256x256.tflite OUT.mkv
"""
import subprocess
import sys

import numpy as np
from ai_edge_litert.interpreter import Interpreter
from PIL import Image, ImageFilter

W, H, FPS = 540, 960, 30
src, model, out = sys.argv[1:4]

it = Interpreter(model, num_threads=4)
it.allocate_tensors()
inp = it.get_input_details()[0]["index"]
outp = it.get_output_details()[0]["index"]


def matte(rgb):
    # The model wants a square input: squash the 9:16 frame in two halves
    # (top/bottom squares) so the person isn't distorted too much.
    m = np.zeros((H, W), np.float32)
    for y0 in (0, H - W):
        tile = Image.fromarray(rgb[y0:y0 + W]).resize((256, 256), Image.BILINEAR)
        x = np.asarray(tile, np.float32)[None] / 255.0
        it.set_tensor(inp, x)
        it.invoke()
        logits = it.get_tensor(outp)[0]
        e = np.exp(logits - logits.max(-1, keepdims=True))
        p = 1.0 - e[..., 0] / e.sum(-1)
        p = np.asarray(Image.fromarray(p).resize((W, W), Image.BILINEAR))
        m[y0:y0 + W] = np.maximum(m[y0:y0 + W], p)
    return m


dec = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={FPS},scale={W}:{H}",
     "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray",
     "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "ffv1", out],
    stdin=subprocess.PIPE)

prev = None
n = 0
while True:
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        break
    m = matte(np.frombuffer(buf, np.uint8).reshape(H, W, 3))
    m = np.clip((m - 0.3) / 0.4, 0, 1)
    # Light temporal smoothing to stop edge shimmer.
    prev = m if prev is None else 0.65 * m + 0.35 * prev
    img = Image.fromarray((prev * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))
    enc.stdin.write(img.tobytes())
    n += 1
enc.stdin.close()
enc.wait()
print(f"{n} frames -> {out}")
