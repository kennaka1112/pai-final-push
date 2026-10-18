#!/usr/bin/env python3
"""CRANE+ V2 で「机の上の赤いブロックを目標エリアまで押す」動作を生成する。

軌道は関節空間で作り、physicalai_teleop の teleop_keyboard と同じトピック・
同じ20Hzで送る。したがって、この軌道を rosbag に録れば、手でテレオペして
集めたデータとまったく同じ形式になる（= 既存の変換・学習がそのまま使える）。

アームの平面2リンクIK（joint2, joint3）で手先(joint4軸)を極座標に置き、
joint4で手先の向きを真下に固定、joint1(旋回)でブロックを円弧状に押す。
"""
import math

# physicalai_teleop/teleop_keyboard.py と同じ定義
ARM_JOINT_NAMES = ['crane_plus_joint1', 'crane_plus_joint2',
                   'crane_plus_joint4', 'crane_plus_joint3']
GRIPPER_JOINT_NAME = 'crane_plus_joint_hand'
RATE_HZ = 20.0

# URDFから読んだリンク長（crane_plus.xacro）
L_UPPER = 0.083    # joint2 -> joint3
L_FORE = 0.0935    # joint3 -> joint4(手先原点)
H_SHOULDER = 0.0714  # base_link -> joint2

# 手先の高さ[m]（base_link基準）。グリッパを真下に向けたとき
#   0.131 付近で指先が天板に接触する（実測）
H_PUSH = 0.142     # 押すとき: 指先が天板すれすれ
H_OVER = 0.190     # ブロックをまたいで移動するとき
H_LIFT = 0.205     # 押し終わって持ち上げるとき
R_WORK = 0.140     # 作業半径[m]

GRIPPER_CLOSED = 0.0
UPRIGHT = [0.0, 0.0, 0.0, 0.0]


def ik_planar(radius, height):
    """手先(joint4軸)を 半径radius・高さheight に置く (joint2, joint3)。"""
    z = height - H_SHOULDER
    cos_d = (radius * radius + z * z - L_UPPER ** 2 - L_FORE ** 2) / (2 * L_UPPER * L_FORE)
    cos_d = max(-1.0, min(1.0, cos_d))
    d = math.acos(cos_d)
    phi = math.atan2(radius, z)
    j2 = phi - math.atan2(L_FORE * math.sin(d), L_UPPER + L_FORE * math.cos(d))
    j3 = -d
    return j2, j3


def arm_pose(yaw, radius, height, hand_dir=math.pi):
    """ARM_JOINT_NAMES の並び [joint1, joint2, joint4, joint3] で姿勢を返す。
       hand_dir=pi はグリッパを真下に向ける。"""
    j2, j3 = ik_planar(radius, height)
    j4 = (j2 - j3) - hand_dir
    return [yaw, j2, j4, j3]


def smoothstep(x):
    x = min(max(x, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def _interp(a, b, t):
    s = smoothstep(t)
    return [ai + (bi - ai) * s for ai, bi in zip(a, b)]


def push_trajectory(yaw_start=-0.60, yaw_goal=0.46, radius=R_WORK,
                    h_push=H_PUSH, sweep_sec=3.0, speed=1.0):
    """1エピソード分の [arm_pos, ...] を 20Hz で返す。

    yaw_start : 押し始めの旋回角[rad]（ブロックの手前側）
    yaw_goal  : 押し終わりの旋回角[rad]（目標エリア側）
    sweep_sec : 押している時間[s]。長いほどゆっくり押す
    speed     : 全体の速さ倍率（1.0が標準）
    """
    approach = arm_pose(yaw_start, radius, H_OVER)
    down = arm_pose(yaw_start, radius, h_push)
    sweep = arm_pose(yaw_goal, radius, h_push)
    lift = arm_pose(yaw_goal, radius, H_LIFT)

    # 軌道の開始姿勢(直立)と終了姿勢(目標上空で停止)をあえて別のものにしている。
    # 両端を直立にすると、関節状態だけを観測する方策からは
    # 「これから押す」のか「押し終わった」のかが区別できず、直立のまま止まってしまう。
    phases = [
        (UPRIGHT, UPRIGHT, 0.5),       # 直立で静止（エピソードの開始合図）
        (UPRIGHT, approach, 2.2),      # ブロック手前の上空へ
        (approach, down, 1.2),         # 天板すれすれまで下ろす
        (down, sweep, sweep_sec),      # 円弧状に押す
        (sweep, lift, 1.0),            # 持ち上げる
        (lift, lift, 1.5),             # 目標エリアの上空で静止（エピソード終了）
    ]

    out = []
    for a, b, sec in phases:
        sec = max(sec / speed, 0.05)
        steps = max(int(sec * RATE_HZ), 1)
        for i in range(steps):
            out.append(_interp(a, b, (i + 1) / steps))
    return out
