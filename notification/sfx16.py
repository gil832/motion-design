"""Procedural SFX for the notification motion (no samples, royalty-free).

Usage: python3 sfx.py OUT.wav DURATION_SECONDS
Cues match the timeline in scene.html.
"""
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
rng = np.random.default_rng(3)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)


def place(buf, sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    n = min(len(sig), buf.shape[0] - i)
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + n, 0] += sig[:n] * gain * l
    buf[i:i + n, 1] += sig[:n] * gain * r


def whoosh(dur, f0, f1):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    for k in range(8):  # stepped band sweep
        s, e = k * n // 8, (k + 1) * n // 8
        fc = f0 * (f1 / f0) ** (k / 7)
        out[s:e] = bp(x, fc * 0.6, min(fc * 1.6, SR / 2 - 100))[s:e]
    env = np.sin(np.pi * t / dur) ** 2
    return out * env


def chime(freq, dur=1.4):
    t = np.arange(int(dur * SR)) / SR
    env = np.minimum(t / 0.004, 1) * np.exp(-t / 0.35)
    tone = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2.01 * t) * np.exp(-t / 0.12)
            + 0.15 * np.sin(2 * np.pi * freq * 3 * t) * np.exp(-t / 0.06))
    return tone * env


def buzz(dur=0.32):
    t = np.arange(int(dur * SR)) / SR
    env = np.minimum(t / 0.01, 1) * np.minimum((dur - t) / 0.05, 1)
    return np.sin(2 * np.pi * 150 * t) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 150 * t))) * env


def pop(freq=900):
    t = np.arange(int(0.08 * SR)) / SR
    return np.sin(2 * np.pi * freq * t * (1 - t * 3)) * np.exp(-t / 0.015)


def main(out, dur):
    buf = np.zeros((int(dur * SR), 2))
    place(buf, whoosh(1.2, 150, 1800), 0.0, 0.25)            # camera settle
    place(buf, buzz(), 1.30, 0.25)                            # haptic
    place(buf, chime(1318.5), 1.32, 0.32, -0.15)              # notification chime E6
    place(buf, chime(1975.5), 1.45, 0.26, 0.15)               # B6
    for i in range(4):                                        # headline words
        place(buf, pop(1400 + 120 * i), 1.70 + i * 0.09, 0.05)
    for i in range(3):                                        # "Now for Less."
        place(buf, pop(700 + 90 * i), 2.30 + i * 0.14, 0.12)
    place(buf, whoosh(0.9, 3000, 9000), 3.3, 0.08, 0.3)       # sheen
    # Low pad under the push-in
    t = np.arange(buf.shape[0]) / SR
    pad = (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82.4 * t)) * 0.06
    pad *= np.clip((t - 1.25) / 1.5, 0, 1) * np.clip((dur - t) / 0.8, 0, 1)
    buf += pad[:, None]
    buf /= max(np.abs(buf).max(), 1e-9) / 0.9
    wavfile.write(out, SR, (buf * 32767).astype(np.int16))


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]))
