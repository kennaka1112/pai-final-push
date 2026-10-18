# 押しタスク用の Gazebo 起動ファイル
#   crane_plus_gazebo/launch/no_moveit_crane_plus_with_table.launch.py をベースに、
#   ワールドファイルだけ本課題用の push_task.sdf に差し替えたもの（MoveIt/RVizは使わない）。
import os

from ament_index_python.packages import get_package_share_directory
from crane_plus_description.robot_description_loader import RobotDescriptionLoader
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node
from launch_ros.actions import SetParameter

WORLD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'worlds', 'push_task.sdf')


def generate_launch_description():
    env = {'IGN_GAZEBO_SYSTEM_PLUGIN_PATH': os.environ['LD_LIBRARY_PATH'],
           'IGN_GAZEBO_RESOURCE_PATH': os.path.dirname(
               get_package_share_directory('crane_plus_description'))}
    gui_config = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gui', 'push_gui.config')

    ign_gazebo = ExecuteProcess(
        cmd=['ign gazebo -r', WORLD, '--gui-config', gui_config],
        output='screen', additional_env=env, shell=True)

    gazebo_spawn_entity = Node(
        package='ros_gz_sim', executable='create', output='screen',
        arguments=['-topic', '/robot_description', '-name', 'crane_plus',
                   '-z', '1.015', '-allow_renaming', 'true'])

    loader = RobotDescriptionLoader()
    loader.use_gazebo = 'true'
    loader.use_ignition = 'true'
    loader.gz_control_config_package = 'crane_plus_control'
    loader.gz_control_config_file_path = 'config/crane_plus_controllers.yaml'
    description = loader.load()

    robot_state_publisher = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        name='robot_state_publisher', output='both',
        parameters=[{'robot_description': description}])

    def spawner(name):
        return ExecuteProcess(cmd=[f'ros2 run controller_manager spawner {name}'],
                              shell=True, output='screen')

    bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'],
        output='screen')

    return LaunchDescription([
        SetParameter(name='use_sim_time', value=True),
        ign_gazebo,
        robot_state_publisher,
        gazebo_spawn_entity,
        spawner('joint_state_broadcaster'),
        spawner('crane_plus_arm_controller'),
        spawner('crane_plus_gripper_controller'),
        bridge,
    ])
