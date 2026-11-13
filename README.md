Elfin Robot
======


Chinese version of the README -> please [click here](./README_cn.md)


<p align="center">
  <img src="docs/images/elfin.png" />
</p>

This repository provides ROS2 support for the Elfin Robot. The recommend operating environment is on Ubuntu 20.04 with ROS Foxy. So far These packages haven't been tested in other environment.

### Installation

#### Ubuntu 20.04 + ROS Foxy

**Install some important dependent software packages:**
```sh
sudo apt-get install ros-foxy-joint-trajectory-controller
sudo apt-get install ros-foxy-controller-manager
sudo apt-get install ros-foxy-trajectory-msgs
sudo apt-get install ros-foxy-gazebo-ros2-control*
sudo apt-get install ros-foxy-joint-state-controller
sudo apt-get install ros-foxy-position-controllers
```

**Install related software packages:**
```sh
sudo apt-get install build-essential libgtk-3-dev
sudo pip3 install wxpython
sudo pip3 install transforms3d
```

**Install or upgrade MoveIt!.** 

If you have installed MoveIt!, please make sure that it's been upgraded to the latest version.

Install/Upgrade MoveIt!:

```sh
sudo apt-get update
sudo apt-get install ros-foxy-moveit
```


**Install this repository from Source**

First set up a catkin workspace (see [this tutorials](http://wiki.ros.org/catkin/Tutorials)).  
Then clone the repository into the src/ folder. It should look like /path/to/your/catkin_workspace/src/elfin_robot.  
Make sure to source the correct setup file according to your workspace hierarchy, then use catkin_make to compile.  

Assuming your catkin workspace folder is ~/catkin_ws, you should use the following commands:
```sh
cd ~/catkin_ws/src
git clone -b foxy_ethercat https://github.com/huayan-robotics/elfin_robot_ros2.git
cd ..
colcon build
source install/setup.bash
```


---

### Usage with Gazebo Simulation

***There are launch files available to bringup a simulated robot - either Elfin3, Elfin5 or Elfin10.  
In the following the commands for Elfin3 are given. For Elfin5 or Elfin10, simply replace the prefix accordingly.***

Bring up the simulated robot in Gazebo and Start up RViz with a configuration including the MoveIt!:
```sh
ros2 launch elfin3_ros2_moveit2 elfin3.launch.py
```

Start up elfin basic api and "Elfin Control Panel" interface:
```sh
ros2 launch elfin3_ros2_moveit2 elfin3_basic_api.launch.py
ros2 launch elfin_basic_api fake_elfin_gui.launch.py
```

> Tutorial about how to use MoveIt! RViz plugin: [docs/moveit_plugin_tutorial_english.md](docs/moveit_plugin_tutorial_english.md)  
Tips:
Every time you want to plan a trajectory, you should set the start state to current first.


---

###  Usage with real Hardware

***There are launch files available to bringup a real robot - either Elfin3, Elfin5 or Elfin10.  
In the following the commands for Elfin3 are given. For Elfin5 or Elfin10, simply replace the prefix accordingly.***

Put the file *elfin_drivers.yaml*, that you got from the vendor, into the folder elfin_robot_bringup/config/.Then copy the parameters in this file to the elfin_robot_bringup/config/elfin_arm_control.yaml

Connect Elfin to the computer with a LAN cable. Then confirm the ethernet interface name of the connection with `ifconfig`. The default ethernet name is eth0. If the ethernet name is not eth0, you should correct the following line in the file *elfin_robot_bringup/config/elfin_arm_control.yaml* 

> **Which "LAN" port?** This cable must go to the arm's EtherCAT port. Control-box models have a separate cabinet LAN port that speaks Han's TCP/IP API (default TCP 10003); the joint drives sit behind that cabinet's own EtherCAT master, so this repository's SOEM driver cannot see them through it. See step 2 under [Docker](#docker) for the adapter/wiring details.

```
elfin_ethernet_name: eth0
```

Bring up the hardware of Elfin. Before bringing up the hardware, you should setup Linux with PREEMPT_RT properly. There is a [tutorial](https://wiki.linuxfoundation.org/realtime/documentation/howto/applications/preemptrt_setup). There are two versions of elfin EtherCAT slaves. Please bring up the hardware accordingly.

```sh
sudo chrt 10 bash
ros2 launch elfin3_ros2_moveit2 elfin3_moveit.launch.py
```

Start up RViz with a configuration including the MoveIt! Motion Planning plugin:
```sh
sudo su
ros2 launch elfin3_ros2_moveit2 elfin3_moveit_rviz.launch.py
```
Start up elfin basic api:
```sh
sudo su
ros2 launch elfin3_ros2_moveit2 elfin3_basic_api.launch.py
```
Start up "Elfin Control Panel" interface:
```sh
sudo su
ros2 launch elfin_basic_api elfin_gui.launch.py
```

Enable the servos of Elfin with "Elfin Control Panel" interface: if there is no "Warning", just press the "Servo On" button to enable the robot. If there is "Warning", press the "Clear Fault" button first and then press the "Servo On" button.

Tutorial about how to use MoveIt! RViz plugin: [docs/moveit_plugin_tutorial_english.md](docs/moveit_plugin_tutorial_english.md)  
Tips:
Every time you want to plan a trajectory, you should set the start state to current first.

Before turning the robot off, you should press the "Servo Off" button to disable the robot.

For more information about API, see [docs/API_description_english.md](docs/API_description_english.md)

---

### Elfin5 Docker desktop

The Docker image uses the [Tiryoh ROS 2 Desktop VNC](https://github.com/Tiryoh/docker-ros2-desktop-vnc) Foxy image for its browser-based Ubuntu desktop. Foxy is used because this repository documents Ubuntu 20.04 + ROS Foxy as its tested setup; Foxy is end-of-life, so this image is intended to reproduce the repository's existing environment rather than provide a current ROS distribution.

Build and start the desktop from the repository root:

```sh
docker compose up --build -d
```

Open <http://localhost:6080/>. The default VNC password is `ubuntu`; set `VNC_PASSWORD` before starting to change it. By default the image builds for your host architecture, because the upstream base image provides both amd64 and arm64 variants. To force a different platform (for example, `linux/amd64` under emulation on Apple Silicon), set `DOCKER_PLATFORM=linux/amd64` when building and running.


### TCP protocol adapter (Mac/Linux)

The repository's original real-hardware ROS driver uses EtherCAT. The `elfin_tcp_driver` package is a separate adapter for the HansRobot ASCII TCP protocol. It connects as a TCP client to the robot's configured server and exposes the MoveIt `FollowJointTrajectory` action expected by the Elfin5 MoveIt configuration. TCP is ordinary IP networking, so this path does not use `compose.hardware.yaml` or require raw Ethernet access. The Docker host/container must still be able to route to the controller IP. Close any interactive `nc` session before launching the adapter; the controller may accept only one client at a time.

Rebuild the image, start the normal desktop container, and in a desktop terminal launch the TCP-backed MoveIt setup in **read-only mode** first:

```sh
docker compose build
docker compose up -d
```

```sh
ros2 launch elfin_tcp_driver elfin5_tcp_moveit.launch.py \
  robot_ip:=192.168.1.63 robot_port:=10003
```

Verify that actual joint states are arriving before enabling motion:

```sh
ros2 topic echo /joint_states
```

The adapter polls actual joint positions at 20 Hz, including while a trajectory is running. State reads and motion requests share the protocol's single serialized TCP connection, so feedback traffic can add some waypoint latency.

The adapter does not power the arm or enable servos. Confirm the controller reports normal status and enable the servos through the teach pendant using your site's safety procedure. Only then, after clearing the work area and verifying the emergency stop, explicitly enable trajectory execution by restarting the launch with:

```sh
ros2 launch elfin_tcp_driver elfin5_tcp_moveit.launch.py \
  robot_ip:=192.168.1.63 robot_port:=10003 allow_motion:=true
```

The adapter maps trajectory waypoints to the protocol's `MoveBJ` endpoint-update command and waits for the controller's motion state. TCP execution is **not hard real-time**, and it does not reproduce the EtherCAT driver's timing/servo behavior; validate at low speed and do not use it for high-rate servoing or safety-critical motion. The existing Elfin Control Panel's EtherCAT servo-control path is not replaced by this adapter.

#### TCP Robotiq gripper control

The adapter uses the controller's Robotiq TCP commands: `SetRobotiq`, `ReadRobotiqPosition`, `RobotiqStatus`, and `RobotIQReset`. Position is in degrees and clamped to `0–140`; speed is clamped to `30–250`; force is clamped to `10–125`. The Elfin5 MoveIt model currently represents the gripper as a fixed dummy link, so this is a direct ROS service, not a gripper joint planned by MoveIt.

Gripper control is disabled by default. To enable **only** the gripper, leaving arm trajectory motion disabled, launch:

```sh
ros2 launch elfin_tcp_driver elfin5_tcp_moveit.launch.py \
  robot_ip:=192.168.1.63 robot_port:=10003 allow_gripper:=true
```

To enable both arm trajectory motion and gripper control, use both explicit gates:

```sh
ros2 launch elfin_tcp_driver elfin5_tcp_moveit.launch.py \
  robot_ip:=192.168.1.63 robot_port:=10003 \
  allow_motion:=true allow_gripper:=true
```

The gripper command service is `/elfin_gripper/move`. It accepts a target position in degrees, speed, and force; non-positive speed and force values use the defaults (250 and 10). The defaults can be changed at launch with `gripper_speed:=<30-250>` and `gripper_default_force:=<10-125>`.

```sh
# Move to 70 degrees, using force 25
ros2 service call /elfin_gripper/move elfin_robot_msgs/srv/SetRobotiq \
  "{position: 70.0, speed: 250.0, force: 25.0}"

# Read current position
ros2 service call /elfin_gripper/read_position std_srvs/srv/Trigger "{}"

# Reset the gripper
ros2 service call /elfin_gripper/reset std_srvs/srv/Trigger "{}"
```

The adapter checks DCS and arm state before gripper motion. The move service waits for the gripper to stop and returns its measured position, whether it reached the target, and whether it stopped early (for example, on an object). The supplied protocol commands do not include a gripper stop command; a timeout reports failure but cannot guarantee the gripper stopped. Verify the Robotiq interface, direction (which endpoint is open), and force behavior at low speed with the work area clear before use. Physical gripper behavior has not been tested here.

#### Terminal UI

With the TCP MoveIt launch running, start the curses-based dashboard in a separate terminal. Both UI command gates default to disabled; the adapter's own `allow_motion` and `allow_gripper` gates must also be enabled for commands to succeed.

```sh
ros2 run elfin_tcp_driver elfin5_robot_tui --ros-args \
  -p enable_arm_commands:=true -p enable_gripper_commands:=true
```

The dashboard displays actual arm joint positions and polls the gripper position. Press `j` to enter six target joint angles; pressing Enter submits them to MoveIt for planning and execution at 10% velocity/acceleration scaling. Press `g` to enter gripper angle, speed, and force; Enter submits the command. A blank entry cancels either prompt. Press `r` to reset the gripper immediately, `s` to cancel an active arm goal, and `q` to quit. The UI validates Elfin5 joint limits; gripper position must be 0–140°, speed 30–250, and force 10–125. Gripper movement cannot be canceled through the supplied TCP commands. Use a terminal large enough for the dashboard and keep the physical E-stop accessible.

This feature adds a ROS service interface and a console executable, so rebuild/recreate the image once before first use:

```sh
docker compose build
docker compose up -d
```

#### Auto-start MoveIt with the desktop

The Docker image adds an optional TCP MoveIt program to the upstream entrypoint's supervisor configuration. It starts after the VNC display is available and is **off by default**. To enable it, add these values to the Compose `.env` file:

```dotenv
ELFIN_TCP_AUTOSTART=true
ELFIN_TCP_ALLOW_MOTION=true
ELFIN_TCP_ALLOW_GRIPPER=true
```

The robot address and port default to `192.168.1.63:10003`; override them with `ELFIN_TCP_ROBOT_IP` and `ELFIN_TCP_ROBOT_PORT` if needed. Then run:

```sh
docker compose up -d --build
```

When the container starts, its entrypoint launches TCP MoveIt and RViz once the VNC display socket is ready. Output is written to `~/.ros/elfin_tcp_moveit.log` inside the container. Apply changes to `.env` with `docker compose up -d --build --force-recreate`. `ELFIN_TCP_AUTOSTART=true` does not power on the arm or enable servos, but the motion/gripper gates make commands available to ROS clients on the configured ROS domain. Only enable them on a trusted network and when that behavior is intended. To disable autostart or either command gate, set the corresponding `.env` value to `false` and recreate the container.

The Docker image uses `colcon build --symlink-install`, and Compose mounts the repository source read-only into the container. Edits to Python and launch files on the host are visible in the running container; restart the affected ROS process to load them. C++ changes still need recompilation. The workspace is root-owned in the image, so rebuild it from a desktop terminal with `sudo`:

```sh
sudo bash -lc 'cd /opt/elfin_ws && source /opt/ros/foxy/setup.bash && colcon build --merge-install --symlink-install --packages-select elfin_description elfin_robot_msgs soem_ros2 elfin_ethercat_driver elfin_ros_control elfin_robot_bringup elfin5_ros2_gazebo elfin5_ros2_moveit2 elfin_tcp_driver elfin_basic_api --cmake-args -DBUILD_TESTING=OFF'
```

If Gazebo or another GUI application opens blank, the upstream image documents `seccomp=unconfined` as a workaround for some Docker environments. This weakens container isolation; apply it only to a trusted local image and only if needed.
