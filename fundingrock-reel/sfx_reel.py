"""Procedural SFX + light music bed for the FundingRock reel (reel.py timeline).

Reuses the synth voices from ../sfx.py. Writes a 48 kHz stereo WAV.
Usage: python3 sfx_reel.py OUT.wav DURATION_SECONDS
"""
import os
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sfx import (SR, ambience, boom, bp, click, ding, env_ad, hp, impact, lp,  # noqa: E402
                 norm, pop, reverb_ir, riser, rng, slash, stereo, t_axis, tick,
                 whoosh)

BPM = 104


def kick(dur=0.35):
    t = t_axis(dur)
    f = 45 + 90 * np.exp(-t / 0.03)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)
    return stereo(norm(x))


def hat(dur=0.05):
    n = int(dur * SR)
    return stereo(norm(hp(rng.standard_normal(n), 7000) * env_ad(n, 0.001, 0.015)))


def music(total):
    """Minimal pulse: four-on-the-floor kick, offbeat hats, sub-bass pad."""
    n = int(total * SR)
    out = np.zeros((n + SR, 2))
    beat = 60 / BPM
    k, h = kick(), hat()
    t = 0.0
    i = 0
    while t < total - 2.4:
        s = int(t * SR)
        out[s:s + len(k)] += k * 0.55
        sh = int((t + beat / 2) * SR)
        out[sh:sh + len(h)] += h * 0.18
        t += beat
        i += 1
    tt = t_axis(total)
    roots = [55.0, 55.0, 49.0, 41.2]  # A A G E, one per bar
    bar = 4 * beat
    f = np.array([roots[int(x / bar) % 4] for x in tt])
    bass = np.sin(2 * np.pi * np.cumsum(f) / SR)
    bass = lp(np.tanh(bass * 2), 300) * (0.55 + 0.45 * np.cos(2 * np.pi * tt / beat) ** 2)
    out[:n] += stereo(norm(bass)) * 0.35
    fade = np.clip(tt / 0.8, 0, 1) * np.clip((total - 0.5 - tt) / 1.6, 0, 1)
    return out[:n] * fade[:, None]


def build(total):
    W = lambda *a: whoosh(*a)  # noqa: E731
    cues = [
        # A: hook bubbles
        (0.08, pop(1100, 600, 0.1), -12, 0.25),
        (1.43, pop(1300, 700, 0.1), -12, 0.25),
        # B: drop to dark mode, grid
        (2.95, W(0.3, 3000, 600, 0.4, -0.4, 0.4), -18, 0.2),
        (3.80, W(0.6, 200, 2500, -0.6, 0.6, 0.7), -10, 0.3),
        (4.30, impact(110, 40, 0.8, 0.8), -9, 0.35),
        (4.48, pop(900, 520), -15, 0.2), (4.56, pop(1000, 580), -15, 0.2),
        (4.64, pop(1120, 640), -15, 0.2), (4.72, pop(1250, 700), -15, 0.2),
        (6.40, click(), -10, 0.1), (6.42, ding(1760, 0.6), -20, 0.4),
        # C: classic route
        (7.15, W(0.45, 2500, 300, 0.5, -0.5, 0.3), -13, 0.2),
        (7.45, pop(800, 450, 0.12), -13, 0.25),
        (8.25, pop(1500, 800), -13, 0.2), (8.95, pop(1700, 900), -13, 0.2),
        (8.70, tick(3200), -20, 0.1), (9.65, tick(3600), -20, 0.1),
        # D: evaluation crossed out, 0, Instant
        (10.62, pop(800, 450, 0.12), -13, 0.25),
        (11.15, slash(0.3, -0.6, 0.6), -11, 0.3), (11.38, slash(0.3, 0.6, -0.6), -12, 0.3),
        (11.80, W(0.35, 300, 4000, -0.4, 0.4, 0.8), -12, 0.2),
        (12.07, impact(140, 38, 1.0, 1.0), -6, 0.45),
        (13.10, W(0.35, 3000, 400, 0.4, -0.4, 0.2), -15, 0.2),
        (13.27, pop(900, 500, 0.12), -11, 0.25), (13.27, ding(2093, 0.6), -21, 0.4),
        (13.55, pop(1300, 720), -14, 0.2),
        # E: which route -- highlight cycling
        (15.40, W(0.5, 200, 2500, -0.5, 0.5, 0.7), -12, 0.3),
        (15.62, pop(950, 540), -16, 0.2), (15.70, pop(1050, 600), -16, 0.2),
        (15.78, pop(1150, 650), -16, 0.2), (15.86, pop(1250, 700), -16, 0.2),
        (15.90, tick(3000), -16, 0.1), (16.20, tick(3300), -16, 0.1),
        (16.50, tick(3600), -16, 0.1), (16.80, tick(3900), -16, 0.1),
        # F: pay after you pass
        (17.05, W(0.45, 2500, 300, 0.5, -0.5, 0.3), -13, 0.2),
        (17.45, pop(1500, 800), -12, 0.2), (17.65, pop(800, 450, 0.12), -13, 0.25),
        (18.60, click(), -13, 0.1), (19.99, click(), -13, 0.1), (21.10, click(), -13, 0.1),
        (20.30, riser(0.95), -17, 0.1),
        (21.25, impact(130, 40, 0.7, 0.6), -10, 0.35), (21.25, ding(1760, 0.9), -15, 0.45),
        # G: traders
        (22.15, pop(1100, 600, 0.1), -13, 0.25), (22.70, pop(1300, 700, 0.1), -13, 0.25),
        (23.60, impact(120, 45, 0.6, 0.5), -11, 0.3),
        # H: route. + end card
        (24.75, W(0.6, 200, 2500, -0.6, 0.6, 0.7), -10, 0.3),
        (25.07, impact(140, 38, 1.0, 1.0), -6, 0.45),
        (26.45, riser(0.95), -13, 0.1),
        (27.35, boom(), -7, 0.45),
        (27.40, W(0.5, 400, 4000, -0.3, 0.3, 0.6), -15, 0.3),
    ]
    n = int(total * SR) + SR
    dry = np.zeros((n, 2))
    wet = np.zeros((n, 2))
    for at, snd, gain_db, send in cues:
        s = int(at * SR)
        seg = snd[: n - s] * 10 ** (gain_db / 20)
        dry[s:s + len(seg)] += seg
        wet[s:s + len(seg)] += seg * send
    ir = reverb_ir()
    rev = np.stack([fftconvolve(wet[:, c], ir[:, c])[:n] for c in range(2)], axis=1)
    mix = dry + 0.5 * rev
    mix = mix[: int(total * SR)]
    mix += music(total) * 10 ** (-17 / 20)
    amb = ambience(total)
    mix[: len(amb)] += amb * 10 ** (-32 / 20)
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    return norm(mix, 0.89)


if __name__ == "__main__":
    out, total = sys.argv[1], float(sys.argv[2])
    wavfile.write(out, SR, (build(total) * 32767).astype(np.int16))
    print(f"wrote {out} ({total:.2f}s)")
