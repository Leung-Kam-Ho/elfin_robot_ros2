#!/usr/bin/env bash
set -eo pipefail

mkdir -p "${HOME}/.ros"
exec > >(tee -a "${HOME}/.ros/elfin_tcp_moveit.log") 2>&1

source "/opt/ros/${ROS_DISTRO:-foxy}/setup.bash"
source /app/install/setup.bash

echo "Starting Elfin TCP MoveIt with motion=${ELFIN_TCP_ALLOW_MOTION:-false}, gripper=${ELFIN_TCP_ALLOW_GRIPPER:-false}"
exec ros2 launch elfin_tcp_driver elfin5_tcp_moveit.launch.py \
    "robot_ip:=${ELFIN_TCP_ROBOT_IP:-192.168.1.63}" \
    "robot_port:=${ELFIN_TCP_ROBOT_PORT:-10003}" \
    "allow_motion:=${ELFIN_TCP_ALLOW_MOTION:-false}" \
    "allow_gripper:=${ELFIN_TCP_ALLOW_GRIPPER:-false}"
