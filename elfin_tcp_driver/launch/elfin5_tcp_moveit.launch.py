#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import xacro
import yaml


def _load_yaml(package, relative_path):
    path = os.path.join(get_package_share_directory(package), relative_path)
    with open(path, "r") as stream:
        return yaml.safe_load(stream)


def generate_launch_description():
    robot_ip = LaunchConfiguration("robot_ip")
    robot_port = LaunchConfiguration("robot_port")
    allow_motion = LaunchConfiguration("allow_motion")
    allow_gripper = LaunchConfiguration("allow_gripper")
    gripper_speed = LaunchConfiguration("gripper_speed")
    gripper_default_force = LaunchConfiguration("gripper_default_force")
    gripper_motion_timeout_sec = LaunchConfiguration("gripper_motion_timeout_sec")
    gripper_position_tolerance_deg = LaunchConfiguration(
        "gripper_position_tolerance_deg"
    )
    rviz = LaunchConfiguration("rviz")

    xacro_path = os.path.join(
        get_package_share_directory("elfin5_ros2_gazebo"),
        "urdf",
        "elfin5.urdf.xacro",
    )
    robot_description = {
        "robot_description": Command(
            [
                FindExecutable(name="xacro"),
                " ",
                xacro_path,
                " use_real_hardware:=false use_fake_hardware:=true",
            ]
        )
    }
    semantic_path = os.path.join(
        get_package_share_directory("elfin5_ros2_moveit2"),
        "config",
        "elfin5.srdf",
    )
    with open(semantic_path, "r") as stream:
        robot_description_semantic = {"robot_description_semantic": stream.read()}

    kinematics = _load_yaml("elfin5_ros2_moveit2", "config/kinematics.yaml")
    ompl = _load_yaml("elfin5_ros2_moveit2", "config/ompl_planning.yaml")
    controller_config = _load_yaml(
        "elfin5_ros2_moveit2", "config/elfin_controllers.yaml"
    )

    planning_pipeline = {
        "planning_plugin": "ompl_interface/OMPLPlanner",
        "request_adapters": (
            "default_planner_request_adapters/AddTimeOptimalParameterization "
            "default_planner_request_adapters/FixWorkspaceBounds "
            "default_planner_request_adapters/FixStartStateBounds "
            "default_planner_request_adapters/FixStartStateCollision "
            "default_planner_request_adapters/FixStartStatePathConstraints"
        ),
        "start_state_max_bounds_error": 0.1,
    }
    planning_pipeline.update(ompl)
    move_group_parameters = {
        **robot_description,
        **robot_description_semantic,
        "robot_description_kinematics": kinematics,
        "move_group": planning_pipeline,
        "moveit_simple_controller_manager": controller_config,
        "moveit_controller_manager": (
            "moveit_simple_controller_manager/MoveItSimpleControllerManager"
        ),
        "moveit_manage_controllers": False,
        "trajectory_execution.allowed_execution_duration_scaling": 2.0,
        "trajectory_execution.allowed_goal_duration_margin": 5.0,
        "trajectory_execution.allowed_start_tolerance": 0.05,
        "publish_planning_scene": True,
        "publish_geometry_updates": True,
        "publish_state_updates": True,
        "publish_transforms_updates": True,
    }

    rviz_path = os.path.join(
        get_package_share_directory("elfin5_ros2_moveit2"),
        "launch",
        "elfin5_moveit2.rviz",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("robot_ip", default_value="192.168.1.63"),
            DeclareLaunchArgument("robot_port", default_value="10003"),
            DeclareLaunchArgument(
                "allow_motion",
                default_value="false",
                description="Explicitly enable TCP motion action execution",
            ),
            DeclareLaunchArgument(
                "allow_gripper",
                default_value="false",
                description="Explicitly enable TCP Robotiq gripper commands",
            ),
            DeclareLaunchArgument("gripper_speed", default_value="250"),
            DeclareLaunchArgument("gripper_default_force", default_value="10"),
            DeclareLaunchArgument("gripper_motion_timeout_sec", default_value="15.0"),
            DeclareLaunchArgument(
                "gripper_position_tolerance_deg", default_value="1.0"
            ),
            DeclareLaunchArgument("rviz", default_value="true"),
            Node(
                package="elfin_tcp_driver",
                executable="elfin_tcp_adapter",
                name="elfin_tcp_adapter",
                output="screen",
                parameters=[
                    {
                        "robot_ip": robot_ip,
                        "robot_port": robot_port,
                        "allow_motion": ParameterValue(allow_motion, value_type=bool),
                        "allow_gripper": ParameterValue(
                            allow_gripper, value_type=bool
                        ),
                        "gripper_speed": ParameterValue(
                            gripper_speed, value_type=float
                        ),
                        "gripper_default_force": ParameterValue(
                            gripper_default_force, value_type=float
                        ),
                        "gripper_motion_timeout_sec": ParameterValue(
                            gripper_motion_timeout_sec, value_type=float
                        ),
                        "gripper_position_tolerance_deg": ParameterValue(
                            gripper_position_tolerance_deg, value_type=float
                        ),
                    }
                ],
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                output="screen",
                parameters=[robot_description],
            ),
            Node(
                package="moveit_ros_move_group",
                executable="move_group",
                output="screen",
                parameters=[move_group_parameters],
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                output="screen",
                arguments=["-d", rviz_path],
                parameters=[
                    robot_description,
                    robot_description_semantic,
                    {"robot_description_kinematics": kinematics},
                    {"move_group": planning_pipeline},
                ],
                condition=IfCondition(rviz),
            ),
        ]
    )
