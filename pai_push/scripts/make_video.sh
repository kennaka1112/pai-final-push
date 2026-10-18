#!/bin/bash
# 提出用の動画を組み立てる。
#   前提: /workspace/video/raw/ に以下の素材があること
#     collect.mp4 … 自動デモでデータ収集している様子
#     policy.mp4  … 学習済みACT方策で押している様子
#     loss.png    … 学習の損失曲線（任意）
#   出力: /workspace/video/PAI_final.mp4  (1280x720 / 30fps)
set -e
RAW=/workspace/video/raw
WORK=/workspace/video/work
OUT="${1:-/workspace/video/PAI_final.mp4}"
F=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
FB=/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc
BG=0x14213d
mkdir -p "$WORK"
rm -f "$WORK"/*.mp4 "$WORK"/list.txt

enc() { echo "-c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -r 30 -an"; }

# タイトルカード: card 出力 秒数 大見出し 小見出し
card() {
  local out="$1" sec="$2" big="$3" small="$4"
  ffmpeg -loglevel error -y -f lavfi -i "color=c=$BG:s=1280x720:d=$sec" \
    -vf "drawtext=fontfile=$FB:text='$big':fontcolor=white:fontsize=52:x=(w-tw)/2:y=300,\
drawtext=fontfile=$F:text='$small':fontcolor=0x9bb1d4:fontsize=30:x=(w-tw)/2:y=390" \
    $(enc) "$out"
}

# 画像カード: imgcard 出力 秒数 画像 キャプション
imgcard() {
  local out="$1" sec="$2" img="$3" cap="$4"
  ffmpeg -loglevel error -y -loop 1 -t "$sec" -i "$img" -f lavfi -t "$sec" -i "color=c=$BG:s=1280x720" \
    -filter_complex "[0:v]scale=1120:-1:force_original_aspect_ratio=decrease[im];\
[1:v][im]overlay=(W-w)/2:60:shortest=1[bg];\
[bg]drawtext=fontfile=$F:text='$cap':fontcolor=white:fontsize=30:x=(w-tw)/2:y=h-70" \
    $(enc) "$out"
}

# 映像クリップに字幕帯を載せる: clip 出力 入力 キャプション [開始秒] [長さ]
clip() {
  local out="$1" src="$2" cap="$3" ss="${4:-0}" dur="${5:-}"
  local t=""; [ -n "$dur" ] && t="-t $dur"
  ffmpeg -loglevel error -y -ss "$ss" $t -i "$src" \
    -vf "crop=1120:630:270:85,scale=1280:720,\
drawbox=x=0:y=640:w=1280:h=80:color=black@0.55:t=fill,\
drawtext=fontfile=$F:text='$cap':fontcolor=white:fontsize=30:x=36:y=668" \
    $(enc) "$out"
}

card "$WORK/01_title.mp4" 6 "机の上のブロックを目標エリアへ押す" "CRANE+ V2 / Gazebo / ACT 模倣学習"
card "$WORK/02_sec1.mp4" 4 "1. デモデータの自動収集" "スクリプトで押し動作を生成し rosbag2 に記録"
clip "$WORK/03_collect.mp4" "$RAW/collect.mp4" "自動デモ：毎回ブロックを初期位置へ戻し、角度と速さを変えて20エピソード記録" 0 24
card "$WORK/04_sec2.mp4" 4 "2. ACT 方策の学習" "LeRobot / RTX 3060 / 6000 step"
if [ -f "$RAW/loss.png" ]; then
  imgcard "$WORK/05_loss.mp4" 8 "$RAW/loss.png" "学習の損失（6000 step）"
fi
card "$WORK/06_sec3.mp4" 4 "3. 学習した方策で実行" "関節状態のみを入力に、方策が押し動作を再現"
clip "$WORK/07_policy.mp4" "$RAW/policy.mp4" "ACT方策による実行：教示していない制御則をデータから獲得" 0 46
card "$WORK/08_end.mp4" 8 "結果：10試行すべて成功" "目標エリア中心からの平均誤差 2.15 cm"

for f in "$WORK"/*.mp4; do echo "file '$f'" >> "$WORK/list.txt"; done
ffmpeg -loglevel error -y -f concat -safe 0 -i "$WORK/list.txt" -c copy "$OUT"
echo "saved: $OUT"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT"
