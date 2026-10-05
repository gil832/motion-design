#!/usr/bin/env bash
# Re-edit main.mp4 and add synthesized SFX.
# Usage: ./render.sh INPUT.mp4 OUTPUT.mp4
set -euo pipefail
IN=${1:?input}
OUT=${2:?output}
DIR=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Total length: the original end card freezes from 14.44s to 20.8s with a
# choppy hard-cut outro. Keep ~1.5s of hold, then fade to black.
TOTAL=16.6
FADE_ST=15.95

# Punch-in zooms on impact beats: A*exp(-(t-ti)/tau) once t >= ti.
p() { echo "$2*exp(-(t-$1)/0.16)*gte(t,$1)"; }
Z="1+$(p 2.00 0.045)+$(p 2.96 0.03)+$(p 3.90 0.03)+$(p 5.50 0.03)+$(p 10.42 0.03)+$(p 13.28 0.02)+$(p 13.72 0.06)"
# Slow push-in across the end-card hold so it never sits dead.
Z="$Z+0.015*clip((t-14.4)/($TOTAL-14.4),0,1)"

python3 "$DIR/sfx.py" "$TMP/sfx.wav" "$TOTAL"

ffmpeg -hide_banner -v error -y -i "$IN" -i "$TMP/sfx.wav" -filter_complex "
  [0:v]trim=0:$TOTAL,setpts=PTS-STARTPTS,
       scale=w='2*trunc(1080*($Z)/2)':h='2*trunc(1920*($Z)/2)':eval=frame:flags=lanczos,
       crop=1080:1920,
       eq=contrast=1.04:saturation=1.10,
       noise=alls=3:allf=t,
       fade=t=out:st=$FADE_ST:d=0.6,
       format=yuv420p[v]" \
  -map "[v]" -map 1:a -c:v libx264 -preset slow -crf 18 -r 25 \
  -c:a aac -b:a 256k -af "loudnorm=I=-14:TP=-1:LRA=9" -ar 48000 \
  -movflags +faststart -shortest "$OUT"

echo "wrote $OUT"
