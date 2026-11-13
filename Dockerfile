FROM ghcr.io/tiryoh/ros2-desktop-vnc:foxy
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV ROS_DISTRO=foxy \
    DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

RUN sed -i 's/^# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen en_US.UTF-8

# Foxy matches the Ubuntu 20.04 environment currently documented by this repo.
# Include the simulation, MoveIt, ros2_control, and Elfin desktop API dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libboost-system-dev \
        libboost-thread-dev \
        libpcap-dev \
        python3-wxgtk4.0 \
        ros-foxy-controller-manager \
        ros-foxy-gazebo-ros2-control \
        ros-foxy-joint-state-controller \
        ros-foxy-joint-trajectory-controller \
        ros-foxy-moveit \
        ros-foxy-position-controllers \
        ros-foxy-ros2-control \
        ros-foxy-robot-state-publisher \
        ros-foxy-xacro \
    && rm -rf /var/lib/apt/lists/*

RUN uv pip install --system --no-cache transforms3d

# Launch the TCP-backed MoveIt session from the container entrypoint's
# supervisord configuration. The program is opt-in through Compose env vars.
COPY docker/elfin_tcp_autostart.sh /usr/local/bin/elfin_tcp_autostart.sh
COPY docker/elfin_tcp_tui_autostart.sh /usr/local/bin/elfin_tcp_tui_autostart.sh
COPY docker/elfin_tcp_tui.sh /usr/local/bin/elfin_tcp_tui.sh
RUN chmod 755 \
        /usr/local/bin/elfin_tcp_autostart.sh \
        /usr/local/bin/elfin_tcp_tui_autostart.sh \
        /usr/local/bin/elfin_tcp_tui.sh

# Add the optional ROS process after the upstream entrypoint creates the VNC
# and noVNC supervisor programs. Keep the upstream desktop initialization intact.
RUN python3 - <<'PY'
from pathlib import Path

entrypoint = Path("/entrypoint.sh")
text = entrypoint.read_text()
marker = "# clearup\nPASSWORD="
program = '''# Optional Elfin TCP MoveIt autostart, after the VNC programs.
if [[ "${ELFIN_TCP_AUTOSTART:-false}" == "true" ]]; then
cat << EOF >> "$CONF_PATH"
[program:elfin_tcp_moveit]
command=/usr/local/bin/elfin_tcp_autostart.sh
user=$USER
environment=HOME="$HOME",DISPLAY=":$VNC_DISPLAY",XAUTHORITY="$HOME/.Xauthority"
autostart=true
autorestart=false
priority=1000
startsecs=0
[program:elfin_tcp_tui]
command=/usr/local/bin/elfin_tcp_tui_autostart.sh
user=$USER
environment=HOME="$HOME",DISPLAY=":$VNC_DISPLAY",XAUTHORITY="$HOME/.Xauthority"
autostart=true
autorestart=false
priority=1001
startsecs=0
EOF
fi

'''
if text.count(marker) != 1:
    raise SystemExit("Could not find the expected insertion point in /entrypoint.sh")
entrypoint.write_text(text.replace(marker, program + marker, 1))
PY

# The upstream entrypoint hardcodes VNC display :1 (RFB 5901) and noVNC on port
# 80. With host networking those collide with a host VNC server on :1 and with
# the host's unprivileged port range (port 80 is privileged there), so make both
# configurable while keeping the upstream defaults.
RUN sed -i \
        -e '1a VNC_DISPLAY=${VNC_DISPLAY:-1}\nNOVNC_PORT=${NOVNC_PORT:-80}\nVNC_RFB_PORT=$((5900 + VNC_DISPLAY))' \
        -e 's|\.X1-lock|.X$VNC_DISPLAY-lock|g' \
        -e 's|\.X11-unix/X1|.X11-unix/X$VNC_DISPLAY|g' \
        -e 's|vncserver :1|vncserver :$VNC_DISPLAY|g' \
        -e 's|websockify --web=/usr/lib/novnc 80 localhost:5901|websockify --web=/usr/lib/novnc $NOVNC_PORT localhost:$VNC_RFB_PORT|g' \
        /entrypoint.sh

WORKDIR /app
COPY . .

RUN source /opt/ros/${ROS_DISTRO}/setup.bash && \
    colcon build --merge-install --symlink-install --packages-select \
        elfin_description \
        elfin_robot_msgs \
        soem_ros2 \
        elfin_ethercat_driver \
        elfin_ros_control \
        elfin_robot_bringup \
        elfin5_ros2_gazebo \
        elfin5_ros2_moveit2 \
        elfin_tcp_driver \
        elfin_basic_api \
        --cmake-args -DBUILD_TESTING=OFF

# The upstream image creates its desktop user at container startup, so add
# workspace sourcing to the skeleton bashrc used for that account.
RUN echo 'source /app/install/setup.bash' >> /etc/skel/.bashrc
