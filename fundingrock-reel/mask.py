"""Per-frame person matte for the talking-head clip, using the MediaPipe
selfie-multiclass (256x256) TFLite model through LiteRT. Writes a lossless
grayscale FFV1 video at 540x960 / 30 fps.

Usage: python3 mask.py INPUT.mp4 selfie_multiclass_256x256.tflite OUT.mkv
"""
import subprocess
import sys

import numpy as np
from ai_edge_litert.interpreter import Interpreter
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

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


# Soft cut-out over the floor lamp (shade + pole), never where the presenter is.
_lc = Image.new("L", (W, H), 255)
ImageDraw.Draw(_lc).rectangle((0, 0, 120, 470), fill=0)
ImageDraw.Draw(_lc).rectangle((0, 470, 62, 900), fill=0)
LAMP_CUT = np.asarray(_lc.filter(ImageFilter.GaussianBlur(6)), np.float32) / 255.0


def cleanup(m):
    """Drop the lamp and other islands, keep the presenter, fill holes."""
    m = m * LAMP_CUT
    b = m > 0.5
    lab, n = ndimage.label(b)
    if n > 1:
        sizes = ndimage.sum(b, lab, range(1, n + 1))
        b = lab == (1 + int(np.argmax(sizes)))
    b = ndimage.binary_fill_holes(b)
    near = ndimage.binary_dilation(b, iterations=8)
    return np.where(b, np.maximum(m, 0.9), m * near)


def guided_filter(I, p, r, eps):
    box = lambda x: ndimage.uniform_filter(x, 2 * r + 1, mode="nearest")  # noqa: E731
    mI, mp = box(I), box(p)
    a = (box(I * p) - mI * mp) / (box(I * I) - mI * mI + eps)
    b = mp - a * mI
    return box(a) * I + box(b)


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
    rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    m = matte(rgb)
    # Light temporal smoothing on the coarse matte to stop edge shimmer.
    prev = m if prev is None else 0.6 * m + 0.4 * prev
    m = cleanup(prev)
    # Snap the blobby 256px matte to real image edges.
    m = guided_filter(rgb.mean(-1) / 255.0, m, 6, 2e-3)
    m = np.clip((m - 0.3) / 0.4, 0, 1)
    m = m * m * (3 - 2 * m)
    enc.stdin.write((m * 255).astype(np.uint8).tobytes())
    n += 1
enc.stdin.close()
enc.wait()
print(f"{n} frames -> {out}")
