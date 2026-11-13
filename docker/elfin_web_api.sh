#!/usr/bin/env bash
set -eo pipefail

source "/opt/ros/${ROS_DISTRO:-foxy}/setup.bash"
source /app/install/setup.bash

cd /app/elfin_web_api
export ELFIN_JOINT_API_HOST="${ELFIN_JOINT_API_HOST:-0.0.0.0}"
export ELFIN_JOINT_API_PORT="${ELFIN_JOINT_API_PORT:-5001}"

exec ./.venv/bin/python app.py
