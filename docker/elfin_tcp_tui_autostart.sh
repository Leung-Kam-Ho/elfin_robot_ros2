#!/usr/bin/env bash
set -eo pipefail

display_number="${VNC_DISPLAY:-1}"
display_socket="/tmp/.X11-unix/X${display_number}"
for _ in $(seq 1 60); do
    [[ -S "$display_socket" ]] && break
    sleep 1
done
if [[ ! -S "$display_socket" ]]; then
    echo "VNC display socket $display_socket did not appear; refusing to start the TUI"
    exit 1
fi
sleep 5

export DISPLAY=":${display_number}"
export XAUTHORITY="${HOME}/.Xauthority"
source "/opt/ros/${ROS_DISTRO:-foxy}/setup.bash"
source /app/install/setup.bash

exec /usr/bin/terminator --no-dbus --title="Elfin Robot Console" \
    --execute /usr/local/bin/elfin_tcp_tui.sh
