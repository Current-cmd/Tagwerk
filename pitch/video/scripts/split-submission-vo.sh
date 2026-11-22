#!/bin/sh
# Cuts the ElevenLabs read (vo-src/james.mp3) into public/vo/sub-<id>.wav at its pauses (silencedetect -40 dB, 0.3 s).
# Then: node scripts/make-submission-vo.mjs --measure-only && npm run render:submission
set -e
cut() { npx remotion ffmpeg -v error -y -ss "$2" -to "$3" -i vo-src/james.mp3 -af "loudnorm=I=-16:TP=-1.5:LRA=11" -ar 44100 -ac 1 -c:a pcm_s16le "public/vo/sub-$1.wav"; }
cut P1  0.00   6.21
cut P2  6.61  18.60
cut P3 18.92  24.06
cut D1 24.26  31.54
cut D2 31.74  38.18
cut D3 38.37  47.63
cut D4 47.90  55.94
cut D5 56.25  66.97
cut D6 67.27  74.75
cut D7 74.94  81.66
cut D8 81.89  90.41
cut D9 90.60  94.47
cut T1 94.75 104.36
