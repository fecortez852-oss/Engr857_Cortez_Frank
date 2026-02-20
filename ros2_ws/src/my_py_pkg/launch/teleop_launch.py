
# teleop_launch.py
# ENGR 857 - Assignment 3.5
# Launches QBot driver + joystick + custom teleop node

import subprocess

from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler, OpaqueFunction, TimerAction
from launch.event_handlers import OnProcessStart, OnProcessExit
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def exit_driver_cb(context):
    subprocess.run(
        'quarc_run -q -t tcpip://localhost:17000 qbot_platform_driver_physical',
        shell=True,
        capture_output=True
    )


def generate_launch_description():

    driver_model_rt_executable = PathJoinSubstitution(
        [FindPackageShare('qbot_platform'),
         'rt_models',
         'qbot_platform_driver_physical.rt-linux_qbot_platform']
    )

    rt_model_start = ExecuteProcess(
        cmd=[
            'quarc_run',
            '-r -t tcpip://localhost:17000',
            driver_model_rt_executable,
            '-d %d -uri tcpip://%m:17001'
        ],
        shell=True
    )

    qbot_driver_node = Node(
        package='qbot_platform',
        executable='qbot_platform_driver_interface',
        name='QBotPlatformDriver',
        parameters=[{'arm_robot': True}],
    )

    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node'
    )

    teleop_node = Node(
        package='teleop',
        executable='teleop_node',  # must match setup.py
        name='TeleopNode',
        output='screen'
    )

    return LaunchDescription([

        rt_model_start,

        joy_node,

        teleop_node,

        RegisterEventHandler(
            OnProcessStart(
                target_action=rt_model_start,
                on_start=[
                    TimerAction(
                        period=2.0,
                        actions=[qbot_driver_node]
                    )
                ]
            )
        ),

        RegisterEventHandler(
            OnProcessExit(
                target_action=qbot_driver_node,
                on_exit=[
                    OpaqueFunction(function=exit_driver_cb)
                ]
            )
        )
    ])
