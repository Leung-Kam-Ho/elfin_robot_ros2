Elfin Robot
======

Chinese version of the README -> [click here](./README%20_cn.md)

<p align="center">
  <img src="docs/images/elfin.png" />
</p>

ROS 2 support for the Elfin robot. The recommended environment in this repository
is Ubuntu 20.04 + ROS 2 Foxy, provided as a browser-accessible Docker desktop.
This README focuses on the Elfin5 TCP workflow: start the stack, read joint state
over HTTP, and use the host-side `elfin` CLI.

---

## Quick start

Requirements:

- Docker with Compose
- [uv](https://docs.astral.sh/uv/) on the host
- The Elfin controller reachable over TCP (default `192.168.1.63:10003`)
- macOS or Linux host for the CLI; the ROS stack stays in Docker

### 1. Configure

```sh
cp .env.example .env
```

The defaults are read-only: the TCP adapter and HTTP API start with the
container, but arm and gripper commands stay disabled.

```dotenv
ELFIN_TCP_AUTOSTART=true
ELFIN_TCP_ALLOW_MOTION=false
ELFIN_TCP_ALLOW_GRIPPER=false
ELFIN_TCP_ROBOT_IP=192.168.1.63
ELFIN_TCP_ROBOT_PORT=10003
ELFIN_JOINT_API_AUTOSTART=true
ELFIN_JOINT_API_PORT=5001
ELFIN_JOINT_STATE_MAX_AGE=2.0
```

Change `ELFIN_TCP_ROBOT_IP` if the controller uses a different address.
`ELFIN_TCP_ALLOW_MOTION` and `ELFIN_TCP_ALLOW_GRIPPER` are described in
[Enabling motion](#enabling-motion) and [Robotiq gripper](#robotiq-gripper).

### 2. Build and start

```sh
docker compose build
docker compose up -d
```

Open <http://localhost:6080/> for the desktop. The default VNC password is
`ubuntu`; set `VNC_PASSWORD` before starting to change it.

### 3. Read joint state from the host

Run these from the repository root:

```sh
uv sync
uv run elfin joint-state
uv run elfin joint-state --watch --interval 0.2
uv run elfin health
```

`joint-state` prints the latest positions in radians and degrees:

```text
Elfin joint state   age 0.031s   stamp 2026-11-13T08:53:36.445Z

 #  joint                rad         deg
 1  elfin_joint1    -1.57010     -89.960
 2  elfin_joint2    -0.79308     -45.440
 3  elfin_joint3    -2.39316    -137.118
 4  elfin_joint4    -0.00005      -0.003
 5  elfin_joint5    -1.55785     -89.258
 6  elfin_joint6     0.00005       0.003
```

`--watch` prints one compact sample per interval. `health` exits `0` only when
fresh joint state is available, so it works in scripts:

```sh
uv run elfin health || echo "robot state is not ready"
```

Use `--json` for the raw API response or `--json --watch` for JSON Lines. See
[elfin_dev_tools/README.md](elfin_dev_tools/README.md) for all CLI options.

### 4. Optional: call the API directly

```sh
curl -s http://localhost:5001/api/joint-state | python3 -m json.tool
curl -s http://localhost:5001/healthz
```

The API returns HTTP 503 until the first joint-state message arrives, or when
the newest message is older than `ELFIN_JOINT_STATE_MAX_AGE` seconds (default
`2.0`). The Compose port is controlled by `ELFIN_JOINT_API_PORT` (default
`5001`).

---

## Components

| Component | Runs where | Purpose |
| --- | --- | --- |
| `elfin_tcp_driver` | Docker | Talks to the controller over TCP; publishes `/joint_states`; exposes the MoveIt trajectory action, arm speed, and gripper services |
| `elfin_web_api` | Docker | Flask bridge from `/joint_states` to HTTP (default port `5001`) |
| `elfin_dev_tools` | Host | `uv`-managed CLI; no ROS or rclpy required |
| RViz / MoveIt / TUI | Docker | Visualization and interactive control through the VNC desktop |

The host CLI only needs `httpx` and talks to the API:

```sh
ELFIN_API_URL=http://192.168.1.10:5001 uv run elfin joint-state
```

### Python tooling

The repository root is the single `elfin-robot` uv project. It manages the
host CLI and Flask dependency used by the joint-state API:

| Python component | Purpose |
| --- | --- |
| `elfin-robot` (root) | Host-side `elfin` CLI (`elfin_dev_tools` package) and shared Python dependencies |
| `elfin_web_api` | API application code; its Flask dependency is locked at the root |

`uv sync` from the root creates the host environment, so `uv run elfin ...` and
`uv run pytest` work without changing directories. Docker uses the same root
`uv.lock` to install the API dependencies into a separate environment with
access to ROS's system `rclpy`. Install the CLI globally with `uv tool install .`.

The ROS 2 packages are built by colcon, not uv. In particular,
`elfin_tcp_driver` is an `ament_python` package that imports rclpy, which is
provided by ROS rather than PyPI, so colcon remains responsible for building
ROS packages.

---

## TCP protocol adapter

The original real-hardware driver uses EtherCAT. `elfin_tcp_driver` is a separate
adapter for the HansRobot ASCII TCP protocol. It connects as a TCP client to the
controller and exposes the MoveIt `FollowJointTrajectory` action expected by the
Elfin5 configuration. It does not use `compose.hardware.yaml` or require raw
Ethernet access, but the Docker host must be able to route to the controller IP.
Close any interactive `nc` session first; the controller may accept only one
client at a time.

The adapter polls actual joint positions at 20 Hz, including while a trajectory
is running. State reads and motion requests share the protocol's single
serialized TCP connection, so feedback traffic can add some waypoint latency.

By default the container's autostart starts the adapter in read-only mode. To
launch it manually instead, set `ELFIN_TCP_AUTOSTART=false`, recreate the
container, and run this in a desktop terminal:

```sh
ros2 launch elfin_tcp_driver elfin5_tcp_moveit.launch.py \
  robot_ip:=192.168.1.63 robot_port:=10003
```

Verify that state is arriving:

```sh
ros2 topic echo /joint_states
```

The adapter does **not** power the arm or enable servos. Confirm the controller
reports normal status and enable the servos through the teach pendant using your
site's safety procedure.

### Enabling motion

After clearing the work area and verifying the emergency stop, enable
trajectory execution in `.env` and recreate:

```dotenv
ELFIN_TCP_ALLOW_MOTION=true
```

```sh
docker compose up -d --force-recreate
```

The adapter maps trajectory waypoints to the protocol's `MoveBJ` endpoint-update
command and waits for the controller's motion state. TCP execution is **not hard
real-time** and does not reproduce the EtherCAT driver's timing/servo behavior;
validate at low speed and do not use it for high-rate servoing or
safety-critical motion. The existing Elfin Control Panel's EtherCAT
servo-control path is not replaced by this adapter.

Arm speed can be set while the robot is idle with `/elfin_arm/set_speed` (the
controller's `SetOverride` command). The value is a percentage from 1 to 100 and
requires `ELFIN_TCP_ALLOW_MOTION=true`; it does not power on the arm or enable
servos and is not applied automatically at startup.

```sh
ros2 service call /elfin_arm/set_speed elfin_robot_msgs/srv/SetFloat64 \
  "{data: 25.0}"
```

### Robotiq gripper

The adapter uses the controller's `SetRobotiq`, `RobotiqStatus`, and `RobotIQReset`
commands. For the Robotiq 2F-140, position is in millimeters and clamped to
`0–140`, speed to `30–250 mm/s`, and force to `10–125`. It does not query
`ReadRobotiqPosition`; the TUI displays the last commanded target, not measured
position. The Elfin5 MoveIt model represents the gripper as a fixed dummy link,
so this is a direct ROS service, not a gripper joint planned by MoveIt.

Gripper control is disabled by default. Enable it, and optionally motion, in
`.env` and recreate:

```dotenv
ELFIN_TCP_ALLOW_GRIPPER=true
ELFIN_TCP_ALLOW_MOTION=true
```

```sh
docker compose up -d --force-recreate
```

The command service is `/elfin_gripper/move`. It accepts a target position in
millimeters (0–140 for the 2F-140), speed in mm/s, and force. Set `speed` per
call to control that move; non-positive speed and force values use the configured
defaults (250 and 10). Change the default speed for TUI toggles and calls that
omit speed with `gripper_speed:=<30-250>` at launch; change the default force with
`gripper_default_force:=<10-125>`.

```sh
# Move to 70 mm at speed 100, using force 25
ros2 service call /elfin_gripper/move elfin_robot_msgs/srv/SetRobotiq \
  "{position: 70.0, speed: 100.0, force: 25.0}"

# Reset the gripper
ros2 service call /elfin_gripper/reset std_srvs/srv/Trigger "{}"
```

The gripper path does not check DCS, arm state, or actual gripper position. It
requires `ELFIN_TCP_ALLOW_GRIPPER=true` and rejects commands while this adapter
has an arm or gripper command active. The move service waits for `RobotiqStatus`
to report that motion stopped; the returned message identifies the commanded
target, not a measured position. The supplied protocol commands do not include a
gripper stop command; a timeout reports failure but cannot guarantee the gripper
stopped. Verify the Robotiq interface, direction (which endpoint is open), and
force behavior at low speed with the work area clear before use. Physical
gripper behavior has not been tested here.

### Terminal UI

With the TCP MoveIt launch running, start the curses dashboard in a separate
desktop terminal. Both UI command gates default to disabled; the adapter's
`ELFIN_TCP_ALLOW_MOTION` and `ELFIN_TCP_ALLOW_GRIPPER` gates must also be enabled
for commands to succeed.

```sh
ros2 run elfin_tcp_driver elfin5_robot_tui --ros-args \
  -p enable_arm_commands:=true -p enable_gripper_commands:=true
```

The dashboard displays actual arm joint positions and the last commanded gripper
target (not sensor feedback). Press `v` to set the robot speed override from
1–100%; this also sets MoveIt's velocity and acceleration scaling for subsequent
TUI arm moves. The change is sent to the TCP adapter and is rejected while a
command is active. The initial planning scaling is 10%; the TUI does not change
the controller override until `v` is used. Press `j` to enter six target joint
angles; Enter submits them to MoveIt. Press `g` and enter
`position [speed] [force]` in millimeters; for example, `70 100` commands 70 mm
at 100 mm/s using the configured default force, and `70 100 25` also sets force
to 25. Press `t` to toggle the internal target between 0 mm and 140 mm using the
configured defaults. The first `t` press targets 140 mm; after a successful move,
the next press targets the opposite endpoint. This toggle does not read the
gripper position. A blank entry cancels either prompt. Press `r` to reset the
gripper, `s` to cancel an active arm goal, and `q` to quit. The UI validates
Elfin5 joint limits; gripper position must be 0–140 mm, speed 30–250 mm/s, and
force 10–125. Gripper movement cannot be canceled through the supplied TCP
commands. Use a terminal large enough for the dashboard and keep the physical
E-stop accessible.

### Auto-start with the desktop

`ELFIN_TCP_AUTOSTART=true` adds MoveIt, RViz, and the TUI to the container
entrypoint's supervisor configuration. It starts after the VNC display is
available. MoveIt output is written to `~/.ros/elfin_tcp_moveit.log` inside the
container. Apply `.env` changes with:

```sh
docker compose up -d --force-recreate
```

`ELFIN_TCP_AUTOSTART=true` does not power on the arm or enable servos. The
motion/gripper gates only make commands available to ROS clients on the configured
ROS domain, so enable them only on a trusted network and when that behavior is
intended. To disable autostart or either gate, set the value to `false` and
recreate the container.

---

## Joint-state HTTP API

`elfin_web_api` runs inside the container so rclpy sees the same ROS graph as the
TCP adapter. It is managed with `uv` and Flask. Start it manually if autostart is
disabled:

```sh
docker compose exec elfin5 /usr/local/bin/elfin_web_api.sh
```

`GET /api/joint-state` returns joint names, positions in radians and degrees, and
the message timestamp. It returns HTTP 503 until the first message arrives or
when the newest message is older than `ELFIN_JOINT_STATE_MAX_AGE` seconds
(default `2.0`), so a stopped adapter or missing robot connection is visible
instead of serving stale data.

```json
{
  "stale": false,
  "age_sec": 0.031,
  "names": ["elfin_joint1", "elfin_joint2", "elfin_joint3",
            "elfin_joint4", "elfin_joint5", "elfin_joint6"],
  "positions_deg": [0.0, -30.0, 0.0, 0.0, 0.0, 0.0],
  "positions": [0.0, -0.5236, 0.0, 0.0, 0.0, 0.0]
}
```

`GET /healthz` reports whether fresh state is available. Override
`ELFIN_JOINT_API_PORT` or `ELFIN_JOINT_STATE_MAX_AGE` in `.env`, then recreate
with `docker compose up -d --force-recreate`. The API is read-only and uses
Flask's development server; restrict access to trusted networks. See
[elfin_web_api/README.md](elfin_web_api/README.md) for local, non-Docker usage.

The root `uv` project manages Python dependencies only; `uv sync` does not build
ROS packages. colcon remains the ROS build system, including the `ament_python`
TCP driver that depends on rclpy.

---

## Legacy: native ROS installation

The Docker workflow above is the recommended path. The original native setup
targets Ubuntu 20.04 + ROS Foxy.

### Install dependencies

```sh
sudo apt-get install ros-foxy-joint-trajectory-controller
sudo apt-get install ros-foxy-controller-manager
sudo apt-get install ros-foxy-trajectory-msgs
sudo apt-get install ros-foxy-gazebo-ros2-control*
sudo apt-get install ros-foxy-joint-state-controller
sudo apt-get install ros-foxy-position-controllers
sudo apt-get install build-essential libgtk-3-dev
sudo pip3 install wxpython transforms3d
sudo apt-get update
sudo apt-get install ros-foxy-moveit
```

### Build from source

```sh
cd ~/catkin_ws/src
git clone -b foxy_ethercat https://github.com/huayan-robotics/elfin_robot_ros2.git
cd ..
colcon build
source install/setup.bash
```

### Gazebo simulation

Launch files are available for Elfin3, Elfin5, and Elfin10. The examples below use
Elfin3; replace the prefix as needed.

```sh
ros2 launch elfin3_ros2_moveit2 elfin3.launch.py
ros2 launch elfin3_ros2_moveit2 elfin3_basic_api.launch.py
ros2 launch elfin_basic_api fake_elfin_gui.launch.py
```

Tutorial: [docs/moveit_plugin_tutorial_english.md](docs/moveit_plugin_tutorial_english.md).
When planning, set the start state to current first.

### EtherCAT real hardware

Put the vendor-provided `elfin_drivers.yaml` into `elfin_robot_bringup/config/`
and copy its parameters into `elfin_robot_bringup/config/elfin_arm_control.yaml`.

Connect the arm's EtherCAT port to the computer and confirm the interface name
with `ifconfig` (default `eth0`). If it differs, update
`elfin_ethernet_name` in `elfin_arm_control.yaml`.

> **Which "LAN" port?** This cable must go to the arm's EtherCAT port.
> Control-box models have a separate cabinet LAN port that speaks Han's TCP/IP API
> (default TCP 10003); the joint drives sit behind that cabinet's own EtherCAT
> master, so this repository's SOEM driver cannot see them through it. See the
> [TCP adapter](#tcp-protocol-adapter) section for that path.

Set up PREEMPT_RT first ([tutorial](https://wiki.linuxfoundation.org/realtime/documentation/howto/applications/preemptrt_setup)).
Then bring up the hardware:

```sh
sudo chrt 10 bash
ros2 launch elfin3_ros2_moveit2 elfin3_moveit.launch.py
```

Start RViz, the basic API, and the control panel:

```sh
sudo su
ros2 launch elfin3_ros2_moveit2 elfin3_moveit_rviz.launch.py
ros2 launch elfin3_ros2_moveit2 elfin3_basic_api.launch.py
ros2 launch elfin_basic_api elfin_gui.launch.py
```

Enable the servos in the "Elfin Control Panel": press **Servo On** if there is no
warning, or **Clear Fault** first. Before powering off, press **Servo Off**.

For more information, see [docs/API_description_english.md](docs/API_description_english.md).

---

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `elfin joint-state` returns connection refused | Container is running (`docker compose ps`) and the API is listening on `ELFIN_JOINT_API_PORT` (`docker compose logs elfin5`, or `docker compose exec elfin5 /usr/local/bin/elfin_web_api.sh`) |
| `elfin health` exits `1` or reports `stale` | TCP adapter is not connected or the controller is not publishing; check `~/.ros/elfin_tcp_moveit.log` inside the container and the robot IP |
| API port already in use | Set `ELFIN_JOINT_API_PORT` to another port in `.env` and run `docker compose up -d --force-recreate` |
| GUI is blank | See the upstream image's `seccomp=unconfined` workaround below |
| Source changes do not appear | The image is built from this repository into `/app`; re-run `docker compose build` and `docker compose up -d` |

The running container uses the code baked into the image at `/app`, not a live
mount. Rebuild after changing Python, launch, or C++ files. To rebuild the ROS
workspace inside the container instead, use:

```sh
sudo bash -lc 'cd /app && source /opt/ros/foxy/setup.bash && colcon build --merge-install --symlink-install --packages-select elfin_description elfin_robot_msgs soem_ros2 elfin_ethercat_driver elfin_ros_control elfin_robot_bringup elfin5_ros2_gazebo elfin5_ros2_moveit2 elfin_tcp_driver elfin_basic_api --cmake-args -DBUILD_TESTING=OFF'
```

If Gazebo or another GUI application opens blank, the upstream image documents
`seccomp=unconfined` as a workaround for some Docker environments. This weakens
container isolation; apply it only to a trusted local image and only if needed.
