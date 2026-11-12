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

If Gazebo or another GUI application opens blank, the upstream image documents `seccomp=unconfined` as a workaround for some Docker environments. This weakens container isolation; apply it only to a trusted local image and only if needed.
