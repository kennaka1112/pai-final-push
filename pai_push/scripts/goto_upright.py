#!/usr/bin/env python3
"""アームを直立姿勢へ戻す（試行の開始条件をそろえるため）。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from push_motion import (ARM_JOINT_NAMES, GRIPPER_JOINT_NAME, GRIPPER_CLOSED,
                         RATE_HZ, UPRIGHT)

SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0


class Upright(Node):
    def __init__(self):
        super().__init__('pai_goto_upright')
        self.set_parameters([Parameter('use_sim_time', Parameter.Type.BOOL, True)])
        self.arm = self.create_publisher(
            JointTrajectory, '/crane_plus_arm_controller/joint_trajectory', 10)
        self.grip = self.create_publisher(
            JointTrajectory, '/crane_plus_gripper_controller/joint_trajectory', 10)

    def send(self):
        for pub, names, pos in ((self.arm, ARM_JOINT_NAMES, UPRIGHT),
                                (self.grip, [GRIPPER_JOINT_NAME], [GRIPPER_CLOSED])):
            jt = JointTrajectory()
            jt.joint_names = names
            pt = JointTrajectoryPoint()
            pt.positions = [float(p) for p in pos]
            pt.time_from_start.nanosec = int(0.1 * 1e9)
            jt.points.append(pt)
            pub.publish(jt)


rclpy.init()
n = Upright()
end = time.monotonic() + SECONDS
while time.monotonic() < end:
    n.send()
    time.sleep(1.0 / RATE_HZ)
n.destroy_node()
rclpy.shutdown()
