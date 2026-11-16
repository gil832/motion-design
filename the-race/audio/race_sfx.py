"""Procedural sound design for THE RACE, locked to the Premiere XML timeline.

Everything is synthesized (no samples): royalty-free. Reuses the primitives in
the repo's sfx.py and adds engine, pass-by, gear-shift, rain, room tone and UI
sounds. Writes a 48 kHz stereo mix plus four stems (engine, hits, ambience, ui)
so levels can be balanced in Premiere.

Usage: python3 race_sfx.py OUT_DIR
"""
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "the-race" / "premiere"))
import sfx  # noqa: E402
from sfx import (SR, boom, bp, click, ding, env_ad, glitch, hp, impact, lp,  # noqa: E402
                 norm, pan_sweep, reverb_ir, riser, stereo, sweep_filter, tick, whoosh)
import build_xml  # noqa: E402

rng = np.random.default_rng(21)
sfx.rng = rng


# ------------------------------------------------------------- new sounds
def engine(rpm, cyl=6, rough=0.25):
    """Additive V6 engine from a per-sample rpm curve."""
    f = rpm / 60 * cyl / 2  # firing frequency
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.zeros_like(f)
    for k in range(1, 14):
        x += np.sin(k * ph + k * 0.7) / k ** 0.9
    # combustion roughness locked to the firing rate
    x *= 1 + rough * lp(rng.standard_normal(len(f)), 900) * (0.5 + 0.5 * np.sin(ph))
    x = np.tanh(1.8 * x)
    x = bp(x, 70, 7000)
    return norm(x)


def rpm_curve(dur, segments):
    """segments: list of (t, rpm) keypoints, linear between."""
    t = np.arange(int(dur * SR)) / SR
    ts, rs = zip(*segments)
    return np.interp(t, ts, rs)


def onboard(dur, shifts):
    """Onboard engine: rpm climbs, drops ~18% at each upshift time."""
    keys, rpm, last = [(0, 9500)], 9500, 0
    for s in shifts:
        keys.append((s - 0.01, 12200))
        keys.append((s + 0.04, 10000))
        last = s
    keys.append((dur, min(12200, 10000 + (dur - last) * 2400)))
    return engine(rpm_curve(dur, keys))


def pass_by(dur=1.4, center=0.55, p0=-1.0, p1=1.0, rpm=11800):
    n = int(dur * SR)
    t = np.arange(n) / SR
    dop = 0.86 + 0.28 / (1 + np.exp((t - center) / 0.06))  # 1.14 -> 0.86
    x = engine(np.full(n, rpm) * dop, rough=0.35)
    amp = np.exp(-((t - center) / 0.32) ** 2) + 0.15 * np.exp(-((t - center) / 0.9) ** 2)
    spray = hp(rng.standard_normal(n), 1800) * np.exp(-((t - center - 0.05) / 0.25) ** 2) * 0.6
    return pan_sweep(norm((x + spray) * amp), p0, p1)


def shift_crack(dur=0.25):
    n = int(dur * SR)
    pop_ = bp(rng.standard_normal(n), 300, 5000) * env_ad(n, 0.0005, 0.02)
    thump = np.sin(2 * np.pi * 70 * np.arange(n) / SR) * env_ad(n, 0.001, 0.05)
    return stereo(norm(np.tanh(3 * (pop_ + 0.8 * thump))))


def rain(dur):
    n = int(dur * SR)
    hiss = hp(lp(rng.standard_normal((n, 2)), 9000, 4), 600) * 0.6
    drops = np.zeros((n, 2))
    for _ in range(int(dur * 70)):
        s = rng.integers(0, n - 800)
        d = hp(rng.standard_normal(600), 2500) * env_ad(600, 0.0002, 0.003)
        drops[s:s + 600, rng.integers(0, 2)] += d * rng.uniform(0.2, 1.0)
    return norm(hiss + drops)


def room_tone(dur, hum=50.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = 0.5 * np.sin(2 * np.pi * hum * t) + 0.2 * np.sin(2 * np.pi * hum * 3 * t)
    x += lp(rng.standard_normal(n), 300, 4) * 2.0
    return stereo(norm(x))


def actuator(dur=0.7, f0=180, f1=420):
    """Motion-platform servo whir."""
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    x = sweep_filter(rng.standard_normal(n), f0, f1, q=6.0)
    x += 0.4 * np.sin(2 * np.pi * np.cumsum(np.linspace(f0, f1, n)) / SR)
    return stereo(norm(x * np.sin(np.pi * t) ** 1.5), rng.uniform(-0.3, 0.3))


def shimmer(dur=1.0, p0=-0.9, p1=0.9):
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = sum(np.sin(2 * np.pi * f * t) * a for f, a in [(1318.5, 1), (1975.5, .6), (2637, .35)])
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    air = sweep_filter(rng.standard_normal(n), 800, 9000, q=2.5)
    return pan_sweep(norm((0.5 * tone + air) * e), p0, p1)


def chime():
    a, b = ding(1318.5, 0.9), ding(1975.5, 1.2)
    out = np.zeros((int(1.5 * SR), 2))
    out[:len(a)] += a * 0.8
    o = int(0.12 * SR)
    out[o:o + len(b)] += b
    return out


def muffle(x, f=700):
    return np.stack([lp(x[:, c], f, 4) for c in range(2)], axis=1)


def slowmo(x, factor=0.6, f=1800):
    """Pitch/time-stretch by resampling, then darken: slow-motion feel."""
    idx = np.arange(0, len(x) - 1, factor)
    y = np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1)
    return muffle(y, f)


# ------------------------------------------------------------- timeline
def build():
    fps = build_xml.FPS
    v1 = build_xml.layout(build_xml.V1, build_xml.REC_START)
    total = v1[-1]["end"] / fps + 0.6
    occ = {}
    for ev in v1:
        occ.setdefault(ev["clip"], []).append(ev)

    def T(clip, k=0, edge="start"):
        return occ[clip][k][edge] / fps

    n = int(total * SR)
    stems = {k: np.zeros((n, 2)) for k in ("engine", "hits", "ambience", "ui")}
    sends = {k: np.zeros((n, 2)) for k in stems}

    def put(stem, at, snd, db, send=0.0):
        s = int(at * SR)
        if s >= n:
            return
        seg = snd[: n - s] * 10 ** (db / 20)
        stems[stem][s:s + len(seg)] += seg
        sends[stem][s:s + len(seg)] += seg * send

    def fade(x, fi=0.05, fo=0.05):
        m = len(x)
        e = np.ones(m)
        a, b = int(fi * SR), int(fo * SR)
        if a:
            e[:a] = np.linspace(0, 1, a)
        if b:
            e[-b:] = np.linspace(1, 0, b)
        return x * e[:, None]

    t_puddle = T("01_puddle_macro.mp4")
    t_race_end = T("07_finish_slowmo.mp4", edge="end")
    t_twist = T("T1_finish_into_screens.mp4")
    t_freeze = T("06_overtake.mp4", 1)
    t_resume = T("06_overtake.mp4", 2)
    t_finish = T("07_finish_slowmo.mp4")
    t_w1 = T("W1_sim_wide_back.mp4")
    t_m3 = T("M3_morph_lime_wipe.mp4")
    t_wipe = t_m3 + 30 / fps
    t_td = T("TD_trading_desk.mp4")
    t_reward = T("10_reward_screen.mp4")
    t_end = T("endcard.mov")

    # --- COLD OPEN: engine screaming in from the dark, pass-by on the puddle hit
    put("engine", 0.0, pass_by(1.6, center=t_puddle + 0.35, p0=-1, p1=1), -3, 0.15)
    put("hits", t_puddle, impact(120, 40, 0.8, 0.6), -8, 0.2)

    # --- RAIN bed for the whole race, hard cut at the twist
    put("ambience", t_puddle, fade(rain(t_twist - t_puddle), 0.2, 0.0), -20)

    # --- ONBOARD engine through the build-up and overtake (ducked under the freeze)
    t0, t1 = T("02_hairpin.mp4"), t_finish
    shifts = [s - t0 for s in np.arange(t0 + 0.55, t1, 0.85)]
    eng = stereo(onboard(t1 - t0, shifts))
    fz0, fz1 = int((t_freeze - t0) * SR), int((t_resume - t0) * SR)
    eng[fz0:fz1] *= 0.0  # time stops on the freeze
    eng[fz1:fz1 + int(0.08 * SR)] *= np.linspace(0, 1, int(0.08 * SR))[:, None]
    put("engine", t0, fade(eng, 0.15, 0.1), -9, 0.05)
    for s in shifts:
        put("hits", t0 + s, shift_crack(), -16, 0.1)

    # --- whooshes on the fast cuts + paddle clicks
    race_cuts = [ev["start"] / fps for ev in v1
                 if t0 < ev["start"] / fps < t_freeze]
    for i, c in enumerate(race_cuts):
        d = 0.32
        put("hits", c - d * 0.6, whoosh(d, 400, 4500, -0.7 if i % 2 else 0.7, 0.7 if i % 2 else -0.7, 0.6),
            -15, 0.15)
    for k in range(2):
        put("ui", T("04_paddle.mp4", k) + 0.05, click(), -12, 0.05)
        put("hits", T("04_paddle.mp4", k) + 0.06, shift_crack(), -9, 0.1)
    # lime flash frames
    for f in [T("02_hairpin.mp4"), T("04_paddle.mp4"), T("04_paddle.mp4", 1), T("06_overtake.mp4")]:
        put("hits", f, impact(150, 50, 0.4, 0.5), -16, 0.2)

    # --- SUBLIMINAL glimpse of the rig: engine drops out, glitch, room tone blip
    t_g = T("T3_chase_to_rig.mp4")
    g0, g1 = int((t_g - t0) * SR), int((T("T3_chase_to_rig.mp4", edge="end") - t0) * SR)
    stems["engine"][int(t_g * SR):int(T("T3_chase_to_rig.mp4", edge="end") * SR)] *= 0.12
    put("hits", t_g, glitch(0.42), -12, 0.1)
    put("ambience", t_g, fade(room_tone(0.42), 0.01, 0.05), -18)

    # --- OVERTAKE: riser into the freeze, boom + ticks on the telemetry, slam back
    put("hits", t_freeze - 0.9, riser(0.9), -10, 0.1)
    put("hits", t_freeze, boom(2.0), -4, 0.45)
    for k, dt in enumerate([0.1, 0.2, 0.28, 0.36, 0.45, 0.55]):
        put("ui", t_freeze + dt, tick(2600 + 220 * k, pan=-0.6 + 0.24 * k), -16, 0.1)
    put("hits", t_resume - 0.25, whoosh(0.3, 3000, 300, 0.6, -0.6, 0.85), -9, 0.2)
    put("hits", t_resume, impact(130, 40, 0.8, 1.0), -5, 0.3)

    # --- FINISH: slow-motion engine + rain swell
    fin = slowmo(stereo(engine(rpm_curve(1.6, [(0, 12000), (1.6, 11500)]))), 0.55)
    put("engine", t_finish, fade(fin[: int((t_twist - t_finish) * SR)], 0.05, 0.12), -8, 0.3)
    put("hits", t_finish, boom(2.2), -9, 0.5)

    # --- THE TWIST: total silence for ~1s (everything above stops at t_twist)
    for k in stems:
        stems[k][int(t_twist * SR):] *= 0.0
        sends[k][int(t_twist * SR):] *= 0.0
    t_room = t_twist + 1.0

    # --- SIM ROOM: room tone, muffled race from the screen speakers, platform servos
    put("ambience", t_room, fade(room_tone(t_wipe - t_room + 0.6), 1.2, 0.6), -22)
    screen = muffle(stereo(onboard(t_wipe - t_room, [0.6, 1.5, 2.4, 3.3, 4.2, 5.1, 6.0])), 600)
    put("engine", t_room, fade(screen, 1.5, 0.8), -24, 0.4)
    for at in np.arange(t_w1 - 0.6, t_wipe - 0.3, 0.9):
        put("ambience", at, actuator(0.7, rng.uniform(150, 220), rng.uniform(350, 500)), -20, 0.3)

    # --- LIME WIPE: sim room -> trading room
    put("ui", t_wipe - 0.5, riser(0.5), -16, 0.1)
    put("ui", t_wipe, shimmer(1.0), -9, 0.4)
    put("hits", t_wipe + 0.95, impact(90, 40, 0.8, 0.3), -12, 0.4)
    put("ambience", t_wipe + 0.6, fade(room_tone(t_end - t_wipe - 0.6, hum=60.0), 0.8, 0.4), -26)

    # --- TRADING DESK: soft chart ticks + one confident click
    for k in range(6):
        put("ui", t_td + 0.3 + 0.25 * k, tick(3000 + 150 * k, 0.03, pan=0.2), -26, 0.2)
    put("ui", t_td + 1.2, click(), -10, 0.1)

    # --- REWARD
    put("ui", t_reward + 0.35, chime(), -8, 0.5)

    # --- END CARD (frame offsets from make_graphics.end_card)
    f = lambda fr: t_end + fr / fps  # noqa: E731
    put("hits", f(2), impact(110, 38, 0.9, 0.8), -5, 0.4)
    for k in range(18):
        put("ui", f(22 + k * 16 / 18), tick(2800 + 90 * (k % 5), 0.025, pan=-0.6 + 1.2 * k / 17), -18, 0.1)
    put("hits", f(38), boom(2.0), -6, 0.5)
    put("hits", f(57), whoosh(0.4, 3000, 400, 0.0, 0.0, 0.3), -14, 0.3)
    put("ui", f(68), shimmer(0.8, -0.3, 0.3), -14, 0.5)
    put("hits", f(72), impact(80, 35, 1.2, 0.2), -10, 0.5)

    # --- reverb + mix
    ir = reverb_ir(1.8, 0.45)
    wet = sum(sends.values())
    rev = np.stack([fftconvolve(wet[:, c], ir[:, c])[:n] for c in range(2)], axis=1)
    rev[int(t_twist * SR):int((t_twist + 0.9) * SR)] *= np.linspace(1, 0, int(0.9 * SR))[:, None] ** 3
    stems["hits"] = stems["hits"] + 0.5 * rev
    mix = sum(stems.values())
    peak = np.max(np.abs(mix)) or 1
    scale = 0.89 / peak
    return {k: v * scale for k, v in stems.items()}, np.tanh(mix * scale * 1.1) / np.tanh(1.1), total


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    stems, mix, total = build()
    wavfile.write(out / "THE_RACE_sfx_mix.wav", SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
    for k, v in stems.items():
        wavfile.write(out / f"stem_{k}.wav", SR, (np.clip(v, -1, 1) * 32767).astype(np.int16))
    print(f"wrote mix + {len(stems)} stems, {total:.2f}s")
