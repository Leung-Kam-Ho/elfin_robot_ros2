#!/usr/bin/env bash
set -eo pipefail

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-1}"
source "/opt/ros/${ROS_DISTRO:-foxy}/setup.bash"
source /app/install/setup.bash

exec ros2 run elfin_tcp_driver elfin5_robot_tui --ros-args \
    -p "enable_arm_commands:=${ELFIN_TCP_ALLOW_MOTION:-false}" \
    -p "enable_gripper_commands:=${ELFIN_TCP_ALLOW_GRIPPER:-false}"
