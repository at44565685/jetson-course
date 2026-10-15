# Copyright 2026. Licensed under the Apache License, Version 2.0.
#
# TurtleBot3 Burger simulation on Gazebo Fortress (ROS 2 Humble).
# Starts Gazebo, robot_state_publisher, the ROS <-> Gazebo bridge and spawns
# the robot.  Arguments:
#   world:=turtlebot3_world | empty_world   (default turtlebot3_world)
#   x_pose / y_pose                          (default -2.0 / -0.5)
#   gui:=true | false   false runs the Gazebo server only (lighter)
#   rviz:=true | false  open RViz with the robot, TF, odometry and scan

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess, OpaqueFunction,
                            SetEnvironmentVariable, Shutdown)
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

PKG = 'turtlebot3_fortress'


def launch_gazebo(context, *args, **kwargs):
    share = get_package_share_directory(PKG)
    world = LaunchConfiguration('world').perform(context)
    gui = LaunchConfiguration('gui').perform(context).lower() == 'true'
    world_file = os.path.join(share, 'worlds', world + '.sdf')
    if not os.path.isfile(world_file):
        raise RuntimeError('Unknown world "%s" (expected turtlebot3_world or empty_world)' % world)

    cmd = ['ign', 'gazebo', '-r', '-v', '2', '--force-version', '6']
    if not gui:
        cmd.append('-s')
    cmd.append(world_file)

    model_sdf = os.path.join(share, 'models', 'turtlebot3_burger', 'model.sdf')
    return [
        ExecuteProcess(cmd=cmd, output='screen', on_exit=Shutdown()),
        Node(
            package='ros_gz_sim', executable='create', output='screen',
            arguments=['-world', world, '-name', 'burger', '-file', model_sdf,
                       '-x', LaunchConfiguration('x_pose').perform(context),
                       '-y', LaunchConfiguration('y_pose').perform(context),
                       '-z', '0.01']),
    ]


def generate_launch_description():
    share = get_package_share_directory(PKG)
    models = os.path.join(share, 'models')
    resource_path = os.pathsep.join(
        p for p in [models, os.environ.get('IGN_GAZEBO_RESOURCE_PATH', '')] if p)

    with open(os.path.join(share, 'urdf', 'turtlebot3_burger.urdf'), 'r') as f:
        robot_description = f.read()

    use_sim_time = {'use_sim_time': True}

    bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge', output='screen',
        parameters=[use_sim_time],
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
            '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan',
            '/imu@sensor_msgs/msg/Imu[ignition.msgs.IMU',
            '/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
            '/joint_states@sensor_msgs/msg/JointState[ignition.msgs.Model',
            '/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
        ])

    robot_state_publisher = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        output='screen',
        parameters=[{'use_sim_time': True, 'robot_description': robot_description}])

    rviz = Node(
        package='rviz2', executable='rviz2', output='screen',
        arguments=['-d', os.path.join(share, 'rviz', 'tb3_gazebo.rviz')],
        parameters=[use_sim_time],
        condition=IfCondition(LaunchConfiguration('rviz')))

    return LaunchDescription([
        DeclareLaunchArgument('world', default_value='turtlebot3_world',
                              description='turtlebot3_world or empty_world'),
        DeclareLaunchArgument('x_pose', default_value='-2.0'),
        DeclareLaunchArgument('y_pose', default_value='-0.5'),
        DeclareLaunchArgument('gui', default_value='true',
                              description='false: run the Gazebo server without its window'),
        DeclareLaunchArgument('rviz', default_value='false'),
        SetEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', resource_path),
        OpaqueFunction(function=launch_gazebo),
        robot_state_publisher,
        bridge,
        rviz,
    ])
