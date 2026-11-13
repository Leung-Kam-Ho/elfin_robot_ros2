#!/usr/bin/env bash
set -eo pipefail

mkdir -p "${HOME}/.ros"
exec >> "${HOME}/.ros/elfin_tcp_moveit.log" 2>&1
echo "$(date --iso-8601=seconds) Elfin TCP desktop autostart invoked"

if [[ "${ELFIN_TCP_AUTOSTART:-false}" != "true" ]]; then
    echo "Autostart disabled (ELFIN_TCP_AUTOSTART is not true)"
    exit 0
fi

display_number="${VNC_DISPLAY:-1}"
display_socket="/tmp/.X11-unix/X${display_number}"
for _ in $(seq 1 60); do
    [[ -S "$display_socket" ]] && break
    sleep 1
done
if [[ ! -S "$display_socket" ]]; then
    echo "VNC display socket $display_socket did not appear; refusing to start RViz"
    exit 1
fi

export DISPLAY=":${display_number}"
export XAUTHORITY="${HOME}/.Xauthority"

source "/opt/ros/${ROS_DISTRO:-foxy}/setup.bash"
source /app/install/setup.bash

echo "Starting Elfin TCP MoveIt with motion=${ELFIN_TCP_ALLOW_MOTION:-false}, gripper=${ELFIN_TCP_ALLOW_GRIPPER:-false}"
exec ros2 launch elfin_tcp_driver elfin5_tcp_moveit.launch.py \
    "robot_ip:=${ELFIN_TCP_ROBOT_IP:-192.168.1.63}" \
    "robot_port:=${ELFIN_TCP_ROBOT_PORT:-10003}" \
    "allow_motion:=${ELFIN_TCP_ALLOW_MOTION:-false}" \
    "allow_gripper:=${ELFIN_TCP_ALLOW_GRIPPER:-false}"
