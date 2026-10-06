#!/usr/bin/env python3
"""Cut the FundingRock Instant UGC compilation into a <60s short.

Usage: python3 cut.py INPUT.mp4 OUTPUT.mp4

Straight cuts only: no added text, no transitions, original frame and
burned-in captions kept as is.
"""
import subprocess, sys
import numpy as np

IN, OUT = sys.argv[1], sys.argv[2]
SR = 16000

# (start, end) in source seconds; boundaries are snapped to the quietest
# point within +-SNAP so cuts land between words.
SEGMENTS = [
    (128.40, 130.95),  # Wait, so you can actually skip the whole challenge part?
    (0.00,   3.45),    # Tired of proving yourself through another evaluation?
    (47.95,  54.68),   # Instant revamped: $25,000 account for just $200
    (134.45, 140.60),  # No evaluation phase, no profit target...
    (98.25,  102.60),  # If you really trust your trading skills...
    (102.60, 106.60),  # Forget grinding through profit targets...
    (106.60, 116.40),  # Skip the challenge entirely, $5k to $100k
    (142.60, 146.90),  # 4% daily loss limit, up to 95% reward share
    (146.90, 149.90),  # Pick your account. Start trading. That's it.
    (119.05, 122.90),  # Stop wasting months trying to pass another evaluation
    (150.04, 155.55),  # If you'd rather skip the evaluation... check it out
]
END_CARD = (155.70, 157.40)
SNAP = 0.08

def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True)

pcm = run(["ffmpeg", "-v", "error", "-i", IN, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]).stdout
audio = np.frombuffer(pcm, np.float32)
hop = SR // 100
rms = np.sqrt(np.convolve(audio**2, np.ones(hop * 4) / (hop * 4), "same")[::hop])

def snap(t):
    if t <= 0:
        return 0.0
    lo, hi = int((t - SNAP) * 100), int((t + SNAP) * 100)
    return (lo + int(np.argmin(rms[lo:hi]))) / 100

def lufs(a, b):
    err = run(["ffmpeg", "-v", "info", "-ss", str(a), "-to", str(b), "-i", IN,
               "-af", "ebur128", "-f", "null", "-"]).stderr.decode()
    return float(err.rsplit("I:", 1)[1].split("LUFS")[0])

parts, total = [], 0.0
for i, (a, b) in enumerate(SEGMENTS):
    a, b = snap(a), snap(b)
    gain = -16 - lufs(a, b)  # even out loudness between creators
    d = b - a; total += d
    parts.append(
        f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}];"
        f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,volume={gain:.2f}dB,"
        f"afade=t=in:d=0.01,afade=t=out:st={d-0.015:.3f}:d=0.015[a{i}];")
    print(f"{i:2d} {a:7.2f}-{b:7.2f} ({d:4.2f}s) gain {gain:+.1f}dB")

a, b = END_CARD; n = len(SEGMENTS); total += b - a
parts.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{n}];"
             f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[a{n}];")
n += 1
print(f"total {total:.2f}s")

graph = "".join(parts) + "".join(f"[v{i}][a{i}]" for i in range(n)) + \
    f"concat=n={n}:v=1:a=1[v][a0];[a0]loudnorm=I=-14:TP=-1:LRA=9,aresample=48000[a]"
run(["ffmpeg", "-v", "error", "-y", "-i", IN, "-filter_complex", graph,
     "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", OUT])
print("wrote", OUT)
