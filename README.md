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

In a terminal inside the desktop, launch the Elfin5 Gazebo + MoveIt simulation:

```sh
ros2 launch elfin5_ros2_moveit2 elfin5.launch.py
```

To start the Elfin API and simulated control panel, open another terminal for each command:

```sh
ros2 launch elfin5_ros2_moveit2 elfin5_basic_api.launch.py
ros2 launch elfin_basic_api fake_elfin_gui.launch.py
```

The image also builds the EtherCAT and hardware-control packages. **The container only starts the desktop; it does not automatically connect to or move a real robot.** Direct EtherCAT access requires a Linux host; Docker Desktop on macOS cannot provide it.

Before starting the hardware connection:

1. Connect the robot to the Linux host and identify the host interface connected to the robot:

   ```sh
   ip -br link
   ```

2. EtherCAT reaches the joint drives directly, so the arm must be connected **without the vendor control box in the path**. Use the Han's Robot *Elfin cable adapter* (the "body/cabinet adapter" in their *ROS Control* manual) to break out the arm's EtherCAT interface and 48 V supply; the control box cuts power to the arm after a while without its watchdog messages, and two masters cannot share the same chain. A direct cable, or a gigabit switch between the arm and the host, both work. The power side is 42–54 V DC with at least 19 A peak (for example a Mean Well RSP-1000-48); adapter pins are 1 = +48 V, 2 = −48 V, 3 = GND, 4 = unused. **Add an emergency-stop switch in the 48 V line**, because bypassing the cabinet also bypasses its E-stop. No IP address is required on the EtherCAT NIC. `No slaves are found on <nic>` (or `wkc = -1`) means the drives are not visible: wrong NIC, the control box or a filtered/isolated switch port in the path, or the arm is not powered. A quick way to identify the control box: if the arm address answers TCP port 10003 (Han's remote API), the joint drives are behind that controller and SOEM will never enumerate through it. If the slaves enumerate but later drop, the vendor's fix is to enable Simulation mode on the pendant.

3. Put the vendor-provided `elfin_drivers.yaml` in `elfin_robot_bringup/config/`. Configure `elfin_robot_bringup/config/elfin_arm_control.yaml` with the correct NIC name and the robot-specific values supplied by the vendor. **The repository's checked-in YAML contains example values; do not assume they are correct for your arm.** Configure the host network and PREEMPT_RT as required by the vendor, and review the launch configuration before powering the robot.

Switch from the normal desktop container to the hardware network setup from the repository root on the host:

```sh
docker compose down
docker compose -f compose.yaml -f compose.hardware.yaml up --build -d
```

With host networking, open the desktop at <http://localhost:6080/>. Because the container shares the host network, it runs its VNC server on display `:2` (RFB 5902) and noVNC on port 6080 by default, avoiding a host VNC server on `:1`/5901 and the privileged port 80. Override with `VNC_DISPLAY` or `NOVNC_PORT` if those are also in use. In separate terminals inside the desktop, launch the hardware controller, MoveIt/RViz, API, and control panel in this order. Source the ROS and workspace setup in each terminal, and run the hardware processes as root because SOEM needs raw-socket access:

```sh
sudo bash -c 'source /opt/ros/foxy/setup.bash && source /opt/elfin_ws/install/setup.bash && ros2 launch elfin5_ros2_moveit2 elfin5_moveit.launch.py'
```

```sh
sudo bash -c 'source /opt/ros/foxy/setup.bash && source /opt/elfin_ws/install/setup.bash && ros2 launch elfin5_ros2_moveit2 elfin5_moveit_rviz.launch.py'
```

```sh
source /opt/ros/foxy/setup.bash
source /opt/elfin_ws/install/setup.bash
ros2 launch elfin5_ros2_moveit2 elfin5_basic_api.launch.py
```

```sh
source /opt/ros/foxy/setup.bash
source /opt/elfin_ws/install/setup.bash
ros2 launch elfin_basic_api elfin_gui.launch.py
```

Host networking exposes the desktop on host port 80 and grants raw-network and realtime scheduling capabilities. Use it only on a trusted, isolated host/network. Verify the robot is in a safe state and the area is clear before enabling servos; the container does not provide hard realtime guarantees. Follow the [real-hardware setup](#usage-with-real-hardware) for the vendor-specific setup and safety steps.

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

#### TCP gripper output control

The HansRobot TCP protocol exposes digital outputs rather than a dedicated gripper command. The adapter provides a `std_srvs/SetBool` service that switches a two-output gripper: `data: false` opens and `data: true` closes. This assumes the gripper is wired to two mutually exclusive digital outputs (one for open, one for close). The Elfin5 MoveIt model currently represents the gripper as a fixed dummy link, so this is a direct ROS service and is not a MoveIt gripper action or planned gripper joint.

First identify the correct output bank and indices from the controller configuration / gripper wiring. Do **not** copy the example indices blindly. Start the launch with gripper control explicitly enabled and the outputs configured; arm trajectory motion can remain disabled:

```sh
ros2 launch elfin_tcp_driver elfin5_tcp_moveit.launch.py \
  robot_ip:=192.168.1.63 robot_port:=10003 \
  allow_gripper:=true gripper_io_type:=robot \
  gripper_open_output:=0 gripper_close_output:=1
```

`gripper_io_type` selects `robot` (`SetOutIOState`, robot-specific output), `config` (`SetConfigDO`, functional serial-port output), or `serial` (`SetSerialDO`, common serial-port output). Replace indices `0` and `1` with the actual outputs. Active output levels default to high (`1`); set `gripper_open_active_state` and/or `gripper_close_active_state` to `0` if the corresponding hardware is active-low. Before a command, the node deactivates the opposite output, then activates the requested output. It does not initialize or energize gripper outputs on startup, and it rejects gripper requests while the arm is moving or reports an error. If a TCP/output command fails, it does not issue further output changes because that could release a held object; inspect the gripper state before retrying.

After confirming DCS is normal, the arm is stationary, and the work area is clear, call:

```sh
# Open
ros2 service call /elfin_gripper/set std_srvs/srv/SetBool "{data: false}"

# Close
ros2 service call /elfin_gripper/set std_srvs/srv/SetBool "{data: true}"
```

Gripper output control is separately gated by `allow_gripper:=true` (default `false`); it does not require `allow_motion:=true`. The output commands are not atomic and the adapter cannot confirm physical jaw position or grasp success. Verify the wiring and behavior at low force/speed under the gripper manufacturer's safety instructions before use.

The Docker image uses `colcon build --symlink-install`, and Compose mounts the repository source read-only into the container. Edits to Python and launch files on the host are visible in the running container; restart the affected ROS process to load them. C++ changes still need recompilation. The workspace is root-owned in the image, so rebuild it from a desktop terminal with `sudo`:

```sh
sudo bash -lc 'cd /opt/elfin_ws && source /opt/ros/foxy/setup.bash && colcon build --merge-install --symlink-install --packages-select elfin_description elfin_robot_msgs soem_ros2 elfin_ethercat_driver elfin_ros_control elfin_robot_bringup elfin5_ros2_gazebo elfin5_ros2_moveit2 elfin_tcp_driver elfin_basic_api --cmake-args -DBUILD_TESTING=OFF'
```

If Gazebo or another GUI application opens blank, the upstream image documents `seccomp=unconfined` as a workaround for some Docker environments. This weakens container isolation; apply it only to a trusted local image and only if needed.
