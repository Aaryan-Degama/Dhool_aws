#!/usr/bin/env bash
# The film's sound design, made from noise with FFmpeg (nothing sampled, nothing licensed): a soft whoosh at each
# scene change, rain under the rain scene, wind under the dust scene. 70 s, 48 kHz mono.
#   bash video/audio/make-sound-design.sh        (writes video/public/audio/sound-design.wav)
set -eu
cd "$(dirname "$0")/.."
whoosh() { echo "anoisesrc=d=0.9:c=pink:a=0.5:seed=$1,bandpass=f=900:w=700,afade=t=in:d=0.4,afade=t=out:st=0.4:d=0.5,volume=0.5,adelay=$2:all=1[w$1]"; }
times=(5800 12800 20900 30800 37900 43900 50900 58900 65800); filters=""; mix=""
for i in "${!times[@]}"; do filters+="$(whoosh "$i" "${times[$i]}");"; mix+="[w$i]"; done
ffmpeg -v error -y -f lavfi -i "anullsrc=r=48000:cl=mono:d=70" -filter_complex "
  ${filters}
  anoisesrc=d=6.2:c=white:a=0.5:seed=41,highpass=f=2400,lowpass=f=9000,afade=t=in:d=1.2,afade=t=out:st=4.8:d=1.4,volume=0.11,adelay=25800:all=1[rain];
  anoisesrc=d=8:c=brown:a=0.9:seed=42,lowpass=f=420,tremolo=f=0.35:d=0.6,afade=t=in:d=1.5,afade=t=out:st=6:d=2,volume=0.55,adelay=30600:all=1[wind];
  [0:a]${mix}[rain][wind]amix=inputs=12:normalize=0:duration=first,alimiter=limit=0.7,afade=t=out:st=68:d=2[out]" \
  -map "[out]" -ar 48000 -ac 1 -c:a pcm_s16le public/audio/sound-design.wav
