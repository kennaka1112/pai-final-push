# 押しタスク用のデータセット定義
#   講義の configs/crane_features.py と同じ5次元（4関節＋グリッパ）構成。
#   タスク名とrepo_idだけ押しタスク用に変更している。
features = {
    "observation.state": {
        "dtype": "float32",
        "shape": (5,),
        "names": ["joint1", "joint2", "joint3", "joint4", "gripper"],
    },
    "observation.environment_state": {
        "dtype": "float32",
        "shape": (5,),
        "names": ["joint1", "joint2", "joint3", "joint4", "gripper"],
    },
    "action": {
        "dtype": "float32",
        "shape": (5,),
        "names": ["joint1", "joint2", "joint3", "joint4", "gripper"],
    },
}

robot_type = "crane_plus"
repo_id = "crane_plus_push"
root = "/home/ubuntu/dataset/lerobot_dataset/crane_plus_push"
task_name = "push_block_to_goal"
