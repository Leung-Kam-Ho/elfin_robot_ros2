FROM ghcr.io/tiryoh/ros2-desktop-vnc:foxy
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV ROS_DISTRO=foxy \
    DEBIAN_FRONTEND=noninteractive

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

WORKDIR /opt/elfin_ws
COPY . /opt/elfin_ws/src/elfin_robot_ros2

RUN source /opt/ros/${ROS_DISTRO}/setup.bash && \
    colcon build --merge-install --packages-select \
        elfin_description \
        elfin_robot_msgs \
        soem_ros2 \
        elfin_ethercat_driver \
        elfin_ros_control \
        elfin_robot_bringup \
        elfin5_ros2_gazebo \
        elfin5_ros2_moveit2 \
        elfin_basic_api \
        --cmake-args -DBUILD_TESTING=OFF

# The upstream image creates its desktop user at container startup, so add
# workspace sourcing to the skeleton bashrc used for that account.
RUN echo 'source /opt/elfin_ws/install/setup.bash' >> /etc/skel/.bashrc
