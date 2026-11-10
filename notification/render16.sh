#!/usr/bin/env bash
# Render the 16:9 photoreal notification motion.
# Needs plate_clean.jpg, matte.png, plate.js next to scene16.html: run key.py on the plate (up.png) first.
# Usage: ./render16.sh OUTPUT.mp4
set -euo pipefail
OUT=${1:-notification_16x9.mp4}
DIR=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
NODE_PATH=${NODE_PATH:-$(npm root -g)} node "$DIR/render16.js" "$TMP" 25
python3 "$DIR/sfx16.py" "$TMP/sfx.wav" 7.0
ffmpeg -hide_banner -v error -y -framerate 25 -i "$TMP/f_%04d.png" -i "$TMP/sfx.wav" \
  -vf "noise=alls=4:allf=t,format=yuv420p" -c:v libx264 -preset slow -crf 17 \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart -shortest "$OUT"
echo "wrote $OUT"
