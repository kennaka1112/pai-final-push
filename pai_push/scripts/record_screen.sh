#!/bin/bash
# Gazeboの3Dビュー領域を画面録画する
#   使い方: record_screen.sh 出力ファイル 秒数
set -e
OUT="${1:?output file}"
SEC="${2:-30}"
# Gazeboウィンドウ(1600x900)の3Dビュー部分だけを切り出す
X=0; Y=112; W=1600; H=848
ffmpeg -loglevel error -y \
  -f x11grab -draw_mouse 0 -framerate 30 -video_size ${W}x${H} -i :0+${X},${Y} \
  -t "$SEC" -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p "$OUT"
echo "saved: $OUT"
