#!/bin/bash
# 赤いブロックの現在位置 [x y z] を1行で表示する
source /opt/ros/humble/setup.bash
export DISPLAY=:0
ign model -m target_block -p 2>&1 | grep -E '^\s+\[' | head -1
