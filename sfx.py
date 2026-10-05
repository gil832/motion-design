"""Synthesize a sound-effects track timed to the motion-design edit.

All sounds are generated procedurally (no samples), so the output is
royalty-free. Writes a 48 kHz stereo WAV.

Usage: python3 sfx.py OUT.wav DURATION_SECONDS
"""
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, lfilter, sosfilt

SR = 48000
rng = np.random.default_rng(7)


def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def env_ad(n, attack, decay_tau):
    """Linear attack then exponential decay envelope."""
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    d = np.exp(-np.maximum(t - attack, 0) / decay_tau)
    return a * d


def bp(x, lo, hi, order=2):
    sos = butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, btype="high", fs=SR, output="sos"), x)


def sweep_filter(x, f0, f1, q=1.2, block=256):
    """Band-pass with a centre frequency sweeping exponentially f0 -> f1."""
    out = np.zeros_like(x)
    zi = np.zeros(2)
    n = len(x)
    for s in range(0, n, block):
        frac = s / max(n - 1, 1)
        fc = f0 * (f1 / f0) ** frac
        w = 2 * np.pi * fc / SR
        alpha = np.sin(w) / (2 * q)
        b = np.array([alpha, 0, -alpha]) / (1 + alpha)
        a = np.array([1, -2 * np.cos(w) / (1 + alpha), (1 - alpha) / (1 + alpha)])
        out[s:s + block], zi = lfilter(b, a, x[s:s + block], zi=zi)
    return out


def stereo(mono, pan=0.0):
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    return np.stack([mono * l, mono * r], axis=1)


def pan_sweep(mono, p0, p1):
    p = np.linspace(p0, p1, len(mono))
    l = np.cos((p + 1) * np.pi / 4)
    r = np.sin((p + 1) * np.pi / 4)
    return np.stack([mono * l, mono * r], axis=1)


def norm(x, peak=1.0):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


# ---------------------------------------------------------------- sounds

def whoosh(dur=0.45, f0=300, f1=3000, p0=-0.6, p1=0.6, peak_at=0.6):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    e = np.where(t < peak_at, (t / peak_at) ** 2, ((1 - t) / (1 - peak_at)) ** 1.5)
    x = sweep_filter(rng.standard_normal(n), f0, f1, q=1.4)
    # airy top layer
    x += 0.3 * hp(rng.standard_normal(n), 5000) * e
    return pan_sweep(norm(x * e), p0, p1)


def impact(sub_f0=110, sub_f1=38, dur=0.9, body=1.0):
    n = int(dur * SR)
    t = t_axis(dur)
    f = sub_f1 + (sub_f0 - sub_f1) * np.exp(-t / 0.05)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.002, 0.28)
    crack = lp(rng.standard_normal(n), 2500) * env_ad(n, 0.0005, 0.035)
    click = hp(rng.standard_normal(n), 3000) * env_ad(n, 0.0002, 0.006)
    x = sub * 1.0 + crack * 0.6 * body + click * 0.35
    x = np.tanh(2.2 * x)  # saturate for weight
    return stereo(norm(x))


def boom(dur=2.2):
    """Deep cinematic hit with a long tail."""
    n = int(dur * SR)
    t = t_axis(dur)
    f = 30 + 70 * np.exp(-t / 0.08)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.003, 0.6)
    rumble = lp(rng.standard_normal(n), 180, order=4) * env_ad(n, 0.01, 0.5)
    crack = bp(rng.standard_normal(n), 200, 4000) * env_ad(n, 0.0005, 0.05)
    x = np.tanh(1.8 * (sub + 0.8 * rumble + 0.5 * crack))
    return stereo(norm(x))


def pop(f0=1400, f1=700, dur=0.09):
    n = int(dur * SR)
    t = t_axis(dur)
    f = f1 + (f0 - f1) * np.exp(-t / 0.012)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.001, 0.022)
    return stereo(norm(x))


def tick(freq=3200, dur=0.03, pan=0.0):
    n = int(dur * SR)
    t = t_axis(dur)
    x = np.sin(2 * np.pi * freq * t) * env_ad(n, 0.0003, 0.005)
    x += 0.5 * hp(rng.standard_normal(n), 4000) * env_ad(n, 0.0001, 0.003)
    return stereo(norm(x), pan)


def click():
    """Mouse click: down + up."""
    a = tick(2400, 0.04)
    b = tick(3400, 0.04) * 0.6
    out = np.zeros((int(0.12 * SR), 2))
    out[:len(a)] += a
    o = int(0.055 * SR)
    out[o:o + len(b)] += b
    return out


def ding(f=1760, dur=0.9):
    n = int(dur * SR)
    t = t_axis(dur)
    x = (np.sin(2 * np.pi * f * t)
         + 0.4 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.1)
         + 0.25 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t / 0.06))
    return stereo(norm(x * env_ad(n, 0.002, 0.22)))


def slash(dur=0.35, p0=-0.7, p1=0.7):
    """Blade swipe with a metallic shing."""
    n = int(dur * SR)
    t = t_axis(dur)
    sw = sweep_filter(rng.standard_normal(n), 1500, 9000, q=2.0)
    e = np.sin(np.pi * np.clip(t / 0.12, 0, 1)) ** 2 * (t < 0.12)
    ring = sum(np.sin(2 * np.pi * fr * t) * a
               for fr, a in [(3150, 1), (4420, .7), (5870, .5), (7710, .3)])
    ring *= env_ad(n, 0.06, 0.08) * (t > 0.05)
    x = sw * e + 0.25 * ring
    return pan_sweep(norm(x), p0, p1)


def riser(dur=0.9):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    e = t ** 2.5
    x = sweep_filter(rng.standard_normal(n), 400, 7000, q=3.0)
    f = 180 * (6 ** t)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
    return pan_sweep(norm((x + tone) * e), -0.3, 0.3)


def glitch(dur=0.16):
    n = int(dur * SR)
    t = t_axis(dur)
    sq = np.sign(np.sin(2 * np.pi * 220 * t * (1 + 3 * (t * 40 % 1))))
    gate = (np.floor(t * 70) % 2 == 0).astype(float)
    x = (0.5 * sq + bp(rng.standard_normal(n), 800, 6000)) * gate
    return stereo(norm(x * env_ad(n, 0.001, 0.08)) * 0.8)


def tail_swoosh(dur=1.2):
    """Soft reversed-feel whoosh for the fade out."""
    w = whoosh(dur, 2500, 200, 0.3, -0.3, peak_at=0.25)
    return w


def ambience(dur):
    n = int(dur * SR)
    t = t_axis(dur)
    pad = (np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82.4 * t)
           + 0.3 * np.sin(2 * np.pi * 110.3 * t))
    pad *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.25 * t)
    air = lp(rng.standard_normal(n), 600, order=4)
    x = norm(pad) * 0.7 + norm(air) * 0.3
    fade = np.clip(t / 1.0, 0, 1) * np.clip((dur - t) / 0.8, 0, 1)
    l = x * fade
    r = np.roll(x, 300) * fade  # small offset for width
    return np.stack([l, r], axis=1)


def reverb_ir(dur=1.4, tau=0.35):
    n = int(dur * SR)
    t = t_axis(dur)
    ir = rng.standard_normal((n, 2)) * np.exp(-t / tau)[:, None]
    ir[:, 0] = lp(ir[:, 0], 6000)
    ir[:, 1] = lp(ir[:, 1], 6000)
    return ir / np.sqrt((ir ** 2).sum(axis=0))


# ---------------------------------------------------------------- timeline

def build(total):
    # (time_s, sound, gain_db, reverb_send)
    cues = [
        (0.08, whoosh(0.4, 250, 2500, -0.5, 0.2), -14, 0.3),   # card enters
        (0.50, pop(1100, 650), -20, 0.2),                       # checklist items
        (0.70, pop(1250, 720), -20, 0.2),
        (0.92, pop(1400, 800), -20, 0.2),
        (1.60, whoosh(0.4, 400, 4000, -0.8, 0.0, 0.85), -12, 0.2),  # SKIP flies in
        (2.00, impact(130, 40), -6, 0.35),                      # SKIP slam
        (2.30, whoosh(0.45, 300, 3500, 0.6, -0.6, 0.8), -11, 0.2),  # card swap
        (2.96, impact(120, 45, 0.7, 0.7), -8, 0.3),             # NO
        (3.08, tick(3000, pan=-0.2), -22, 0.1),                 # E-V-A-L typing
        (3.16, tick(3300, pan=-0.1), -22, 0.1),
        (3.24, tick(3100, pan=0.0), -22, 0.1),
        (3.32, tick(3500, pan=0.1), -22, 0.1),
        (3.62, tick(3200, pan=0.1), -24, 0.1),
        (3.72, slash(0.3, -0.6, 0.6), -10, 0.3),                # X stroke 1
        (3.86, slash(0.3, 0.6, -0.6), -11, 0.3),                # X stroke 2
        (3.90, impact(100, 45, 0.6, 0.5), -12, 0.3),
        (4.88, whoosh(0.7, 200, 3000, -0.7, 0.7, 0.5), -9, 0.25),   # big transition
        (5.50, impact(120, 45, 0.7, 0.7), -9, 0.3),             # NO
        (6.02, slash(0.35, -0.5, 0.5), -10, 0.35),              # line through 10%
        (6.20, tick(3000, pan=0.2), -23, 0.1),                  # PROFIT TARGET
        (6.30, tick(3400, pan=0.25), -23, 0.1),
        (6.42, tick(3150, pan=0.3), -23, 0.1),
        (6.54, tick(3600, pan=0.35), -23, 0.1),
        (6.66, tick(3300, pan=0.4), -23, 0.1),
        (7.30, glitch(), -12, 0.15),                            # glitch cut
        (7.40, whoosh(0.35, 500, 3000, 0.0, 0.0, 0.3), -14, 0.2),
        (7.50, pop(900, 500), -16, 0.2),                        # account list
        (7.66, pop(1000, 560), -16, 0.2),
        (7.82, pop(1120, 630), -16, 0.2),
        (7.98, pop(1260, 700), -16, 0.2),
        (8.14, pop(1400, 790), -16, 0.2),
        (8.64, whoosh(0.8, 200, 1200, -0.3, 0.3, 0.5), -18, 0.2),   # card tilt
        (9.72, click(), -11, 0.1),                              # select $50,000
        (9.76, ding(1760), -17, 0.4),
        (10.10, riser(0.32), -14, 0.1),
        (10.38, whoosh(0.35, 3000, 400, 0.5, -0.5, 0.15), -10, 0.2),  # zoom cut
        (10.42, impact(90, 40, 0.6, 0.4), -12, 0.3),
        (11.00, pop(800, 420, 0.12), -13, 0.25),                # START TRADING
        (11.16, pop(1300, 750), -15, 0.2),                      # button
        (12.28, click(), -9, 0.1),                              # press Start Trading
        (12.30, ding(2093, 0.7), -20, 0.4),
        (12.40, riser(0.9), -10, 0.1),                          # build into cut
        (13.28, boom(), -6, 0.4),                               # cut to end card
        (13.52, whoosh(0.25, 400, 5000, -0.4, 0.2, 0.85), -12, 0.2),  # 95 flies in
        (13.72, impact(140, 38, 1.0, 1.0), -5, 0.45),           # 95 slam
        (14.00, pop(1600, 800), -14, 0.3),                      # %
        (14.12, whoosh(0.3, 800, 4000, -0.2, 0.2, 0.5), -20, 0.2),  # subline
        (total - 1.05, tail_swoosh(1.0), -16, 0.5),             # fade out
    ]

    n = int(total * SR) + SR
    dry = np.zeros((n, 2))
    wet = np.zeros((n, 2))
    for at, snd, gain_db, send in cues:
        s = int(at * SR)
        g = 10 ** (gain_db / 20)
        seg = snd[: n - s] * g
        dry[s:s + len(seg)] += seg
        wet[s:s + len(seg)] += seg * send

    ir = reverb_ir()
    rev = np.stack([fftconvolve(wet[:, c], ir[:, c])[:n] for c in range(2)], axis=1)
    amb = ambience(total)
    mix = dry + 0.5 * rev
    mix[: len(amb)] += amb * 10 ** (-30 / 20)
    mix = mix[: int(total * SR)]
    # gentle bus glue + safety limiting
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    return norm(mix, 0.89)


if __name__ == "__main__":
    out, total = sys.argv[1], float(sys.argv[2])
    mix = build(total)
    wavfile.write(out, SR, (mix * 32767).astype(np.int16))
    print(f"wrote {out} ({total:.2f}s)")
