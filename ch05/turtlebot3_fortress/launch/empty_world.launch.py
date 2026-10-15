# Copyright 2026. Licensed under the Apache License, Version 2.0.
# Shortcut: TurtleBot3 Burger in empty_world (same arguments as simulation.launch.py).

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    sim = os.path.join(get_package_share_directory('turtlebot3_fortress'),
                       'launch', 'simulation.launch.py')
    args = [('x_pose', '0.0'), ('y_pose', '0.0'), ('gui', 'true'), ('rviz', 'false')]
    return LaunchDescription(
        [DeclareLaunchArgument(n, default_value=v) for n, v in args] + [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(sim),
                launch_arguments=[('world', 'empty_world')] +
                [(n, LaunchConfiguration(n)) for n, _ in args])])
