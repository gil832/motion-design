#!/usr/bin/env bash
# Render the FundingRock notification motion to MP4.
# Usage: ./render.sh OUTPUT.mp4
set -euo pipefail
OUT=${1:-notification.mp4}
DIR=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
FPS=25
DUR=6.4

node "$DIR/render.js" "$TMP" "$FPS"
python3 "$DIR/sfx.py" "$TMP/sfx.wav" "$DUR"
ffmpeg -hide_banner -v error -y -framerate "$FPS" -i "$TMP/f_%04d.png" -i "$TMP/sfx.wav" \
  -vf "noise=alls=3:allf=t,format=yuv420p" -c:v libx264 -preset slow -crf 18 \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart -shortest "$OUT"
echo "wrote $OUT"
