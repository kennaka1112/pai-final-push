#!/bin/bash
# 録画前の画面準備：スクリーンセーバー（MATEのfloaters）が録画に写り込むのを防ぐ
export DISPLAY=:0
gsettings set org.mate.screensaver idle-activation-enabled false 2>/dev/null || true
gsettings set org.mate.screensaver lock-enabled false 2>/dev/null || true
pkill -f mate-screensaver 2>/dev/null || true
xset s off 2>/dev/null || true
xset s noblank 2>/dev/null || true
echo "display prepared"
