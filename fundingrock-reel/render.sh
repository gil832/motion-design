#!/usr/bin/env bash
# FundingRock talking-head reel: person matte -> motion graphics -> SFX/music mix.
# Usage: ./render.sh INPUT.mp4 OUTPUT.mp4
# Needs: ffmpeg, python3 with numpy scipy pillow ai-edge-litert, and the
# MediaPipe selfie_multiclass_256x256.tflite model (downloaded if missing).
set -euo pipefail
IN=${1:?input}
OUT=${2:?output}
DIR=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
TOTAL=30.0
MODEL="$DIR/assets/selfie_multiclass_256x256.tflite"
[ -f "$MODEL" ] || curl -sSfo "$MODEL" \
  https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite

python3 "$DIR/mask.py" "$IN" "$MODEL" "$TMP/mask.mkv"
python3 "$DIR/reel.py" "$IN" "$TMP/mask.mkv" "$TMP/video.mp4"
python3 "$DIR/sfx_reel.py" "$TMP/sfx.wav" "$TOTAL"

# Voice: clean + level it; SFX/music bed sits underneath.
ffmpeg -hide_banner -v error -y -i "$TMP/video.mp4" -i "$IN" -i "$TMP/sfx.wav" -filter_complex "
  [1:a]atrim=0:27.6,asetpts=PTS-STARTPTS,highpass=f=70,
       acompressor=threshold=-20dB:ratio=3:attack=5:release=120,
       loudnorm=I=-16:TP=-2:LRA=7,aresample=48000,apad=whole_dur=$TOTAL[v];
  [2:a]volume=0.42[s];
  [v][s]amix=inputs=2:normalize=0:duration=first,
       loudnorm=I=-14:TP=-1:LRA=9,aresample=48000[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 256k -movflags +faststart -t $TOTAL "$OUT"
echo "wrote $OUT"
