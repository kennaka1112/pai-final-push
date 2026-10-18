#!/usr/bin/env python3
"""押しタスクのデモを自動生成して rosbag2 に記録する。

講義の pai-auto-demo（お辞儀デモ）と同じ構成・同じトピック・同じ20Hzで動かすので、
出力される rosbag はテレオペで手集めしたものと同じ形式になる。
エピソードごとに押し始めの角度・押す速さ・手先の高さを少しずつ変え、
毎回ブロックを開始位置へ戻してから記録する。

  使い方: auto_demo_push.py [-n 20] [--task push_block] [--seed 0]
  前提  : 別ターミナルで push_task.launch.py が起動していること
"""
import argparse
import os
import random
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from push_motion import (ARM_JOINT_NAMES, GRIPPER_JOINT_NAME, GRIPPER_CLOSED,
                         RATE_HZ, UPRIGHT, push_trajectory)

TOPICS = ['/joint_states',
          '/crane_plus_arm_controller/joint_trajectory',
          '/crane_plus_gripper_controller/joint_trajectory']
HERE = os.path.dirname(os.path.abspath(__file__))


class DemoPublisher(Node):
    def __init__(self):
        super().__init__('pai_auto_demo_push')
        self.set_parameters([Parameter('use_sim_time', Parameter.Type.BOOL, True)])
        self.arm_pub = self.create_publisher(
            JointTrajectory, '/crane_plus_arm_controller/joint_trajectory', 10)
        self.gripper_pub = self.create_publisher(
            JointTrajectory, '/crane_plus_gripper_controller/joint_trajectory', 10)

    def send(self, arm_pos, gripper_pos=GRIPPER_CLOSED):
        for pub, names, pos in ((self.arm_pub, ARM_JOINT_NAMES, arm_pos),
                                (self.gripper_pub, [GRIPPER_JOINT_NAME], [gripper_pos])):
            jt = JointTrajectory()
            jt.joint_names = names
            pt = JointTrajectoryPoint()
            pt.positions = [float(p) for p in pos]
            pt.time_from_start.nanosec = int(0.1 * 1e9)
            jt.points.append(pt)
            pub.publish(jt)

    def hold(self, arm_pos, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.send(arm_pos)
            time.sleep(1.0 / RATE_HZ)


def reset_block():
    subprocess.run(['bash', os.path.join(HERE, 'reset_block.sh')],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def block_xy():
    r = subprocess.run(['bash', os.path.join(HERE, 'block_pose.sh')],
                       capture_output=True, text=True, check=False)
    try:
        v = r.stdout.strip().strip('[]').split()
        return float(v[0]), float(v[1])
    except Exception:
        return float('nan'), float('nan')


def next_episode_dir(base):
    n = 1
    while os.path.exists(os.path.join(base, f'ep{n}')):
        n += 1
    return os.path.join(base, f'ep{n}')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('-n', '--episodes', type=int, default=20)
    ap.add_argument('--task', default='push_block')
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    base = os.path.expanduser(f'~/dataset/rosbags/{args.task}')
    os.makedirs(base, exist_ok=True)

    rclpy.init()
    node = DemoPublisher()
    ok = 0
    try:
        for ep in range(args.episodes):
            node.hold(UPRIGHT, 1.5)          # 直立に戻してから
            reset_block()                    # ブロックを開始位置へ
            node.hold(UPRIGHT, 1.5)          # 物理が落ち着くのを待つ

            params = dict(
                yaw_start=rng.uniform(-0.64, -0.56),
                yaw_goal=rng.uniform(0.42, 0.50),
                h_push=rng.uniform(0.140, 0.145),
                sweep_sec=rng.uniform(2.6, 3.4),
            )
            traj = push_trajectory(**params)

            out_dir = next_episode_dir(base)
            rec = subprocess.Popen(['ros2', 'bag', 'record', '-o', out_dir, *TOPICS],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5)                  # recorder の購読開始待ち
            for pos in traj:
                node.send(pos)
                time.sleep(1.0 / RATE_HZ)
            rec.send_signal(signal.SIGINT)
            rec.wait(timeout=20)

            x, y = block_xy()
            # 目標エリア中心 (0.1289, 0.0547) から4cm以内なら成功とみなす
            dist = ((x - 0.1289) ** 2 + (y - 0.0547) ** 2) ** 0.5
            hit = dist < 0.04
            ok += int(hit)
            print(f'[{ep + 1}/{args.episodes}] {os.path.basename(out_dir)}  '
                  f'block=({x:+.4f},{y:+.4f})  goal_dist={dist * 100:.1f}cm  '
                  f'{"OK" if hit else "MISS"}', flush=True)
        print(f'\n成功 {ok}/{args.episodes} エピソード  保存先: {base}')
    finally:
        node.destroy_node()
        rclpy.shutdown()


main()
