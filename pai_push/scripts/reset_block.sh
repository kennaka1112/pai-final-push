#!/bin/bash
# 赤いブロックを開始位置（半径0.14m, 方位-20deg）へ戻す。
#   使い方: reset_block.sh [y_offset]   省略時は既定の開始位置
set -e
source /opt/ros/humble/setup.bash
export DISPLAY=:0
X="${1:-0.1316}"
Y="${2:--0.0479}"
YAW="${3:--0.3491}"
QZ=$(python3 -c "import math,sys; print(math.sin(float(sys.argv[1])/2))" "$YAW")
QW=$(python3 -c "import math,sys; print(math.cos(float(sys.argv[1])/2))" "$YAW")
ign service -s /world/default/set_pose \
  --reqtype ignition.msgs.Pose --reptype ignition.msgs.Boolean --timeout 3000 \
  --req "name: \"target_block\", position: {x: $X, y: $Y, z: 1.0351}, orientation: {x: 0, y: 0, z: $QZ, w: $QW}" \
  > /dev/null
