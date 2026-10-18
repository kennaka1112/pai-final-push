#!/bin/bash
# 提出動画の素材を撮影する。
#   clip1: 自動デモによるデータ収集（2エピソード）
#   clip2: 学習済みACT方策による実行（3サイクルを連結）
# 出力: /workspace/video/raw/collect.mp4, policy.mp4
set -e
source /opt/ros/humble/setup.bash
source ~/airobot_ws/install/setup.bash
export DISPLAY=:0
HERE="$(cd "$(dirname "$0")" && pwd)"
RAW=/workspace/video/raw
mkdir -p "$RAW" "$RAW/parts"
bash "$HERE/prepare_display.sh" >/dev/null

echo "=== clip1: データ収集 ==="
pkill -f "scripts/infer.py" >/dev/null 2>&1 || true
python3 "$HERE/goto_upright.py" 3
bash "$HERE/reset_block.sh"
sleep 1
nohup python3 "$HERE/auto_demo_push.py" -n 2 --task video_demo --seed 3 > /tmp/collect_clip.log 2>&1 &
sleep 3
bash "$HERE/record_screen.sh" "$RAW/collect.mp4" 38
wait || true

echo "=== clip2: 方策の実行（3サイクル） ==="
rm -f "$RAW"/parts/policy_*.mp4
for i in 1 2 3; do
  pkill -f "scripts/infer.py" >/dev/null 2>&1 || true
  sleep 1
  python3 "$HERE/goto_upright.py" 4
  bash "$HERE/reset_block.sh"
  python3 "$HERE/goto_upright.py" 2
  : > /tmp/infer.log
  nohup bash "$HERE/push-infer" > /tmp/infer.log 2>&1 &
  # 方策が指令を出し始めるまで待ってから録画（モデル読み込みの待ち時間を映さない）
  for _ in $(seq 1 180); do
    grep -q '^action:' /tmp/infer.log && break
    sleep 0.5
  done
  bash "$HERE/record_screen.sh" "$RAW/parts/policy_$i.mp4" 16
  pkill -f "scripts/infer.py" >/dev/null 2>&1 || true
  echo "  cycle $i: $(bash "$HERE/block_pose.sh")"
done
: > "$RAW/parts/list.txt"
for i in 1 2 3; do echo "file '$RAW/parts/policy_$i.mp4'" >> "$RAW/parts/list.txt"; done
ffmpeg -loglevel error -y -f concat -safe 0 -i "$RAW/parts/list.txt" -c copy "$RAW/policy.mp4"
echo "done:"
ls -la "$RAW"
