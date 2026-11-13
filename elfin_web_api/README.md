# Elfin joint-state HTTP API

A small Flask service that exposes the robot's latest `sensor_msgs/JointState`
message as JSON. It subscribes to `/joint_states` with rclpy in a background
thread, so it sees the same state as the TCP adapter, the TUI, and RViz.

## Requirements

`rclpy` ships with ROS 2 rather than PyPI. Run the service inside a sourced
ROS 2 environment (the repository's Docker image already provides this) and
create the uv environment with access to the system interpreter:

```sh
source /opt/ros/foxy/setup.bash
cd /path/to/elfin_robot_ros2
uv venv --system-site-packages elfin_web_api/.venv
UV_PROJECT_ENVIRONMENT=elfin_web_api/.venv \
  uv sync --no-dev --no-install-project
elfin_web_api/.venv/bin/python elfin_web_api/app.py
```

The root `pyproject.toml` and `uv.lock` are the repository's only uv project
metadata. The API uses the same locked Flask dependency in a dedicated
environment so it can access ROS's system-provided rclpy. Do not run a plain
`uv sync` without `--system-site-packages` for this service; the environment
would install Flask but could not import rclpy.

## Running in Docker

The image builds the uv environment during `docker compose build`. Start the
service manually in a container terminal:

```sh
docker compose exec elfin5 /usr/local/bin/elfin_web_api.sh
```

Or enable it with the desktop session by setting `ELFIN_JOINT_API_AUTOSTART=true`
in `.env` (the container port is published to `127.0.0.1` on the host).

## Endpoints

### `GET /api/joint-state`

Returns the newest message with positions in radians and degrees. Responds with
HTTP 503 if nothing has been received yet, or if the newest message is older
than `ELFIN_JOINT_STATE_MAX_AGE` seconds (default `2.0`).

```sh
curl -s http://localhost:5001/api/joint-state | python3 -m json.tool
```

```json
{
  "stale": false,
  "age_sec": 0.031,
  "frame_id": "",
  "stamp": { "sec": 1762980000, "nanosec": 123456789 },
  "received_at": "2026-11-13T08:40:00.123456+00:00",
  "names": ["elfin_joint1", "elfin_joint2", "elfin_joint3",
            "elfin_joint4", "elfin_joint5", "elfin_joint6"],
  "positions": [0.0, -0.5236, 0.0, 0.0, 0.0, 0.0],
  "positions_deg": [0.0, -30.0, 0.0, 0.0, 0.0, 0.0],
  "velocities": [],
  "efforts": [],
  "joints": [
    {
      "name": "elfin_joint1",
      "position_rad": 0.0,
      "position_deg": 0.0
    }
  ]
}
```

`joints` mirrors `names` and includes `velocity`/`effort` only when the
publisher provides those arrays.

### `GET /healthz`

Always returns HTTP 200 with liveness and freshness information:

```json
{
  "status": "ok",
  "topic": "/joint_states",
  "joint_state_available": true,
  "stale": false,
  "age_sec": 0.031
}
```

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `ELFIN_JOINT_API_HOST` | `127.0.0.1` (`0.0.0.0` in Docker) | Bind address |
| `ELFIN_JOINT_API_PORT` | `5001` | HTTP port (host and container) |
| `ELFIN_JOINT_STATE_TOPIC` | `/joint_states` | Topic to subscribe to |
| `ELFIN_JOINT_STATE_MAX_AGE` | `2.0` | Seconds before data is considered stale |

Flask's development server is used intentionally: this is a local read-only
bridge for dashboards and scripts, not an internet-facing service. Keep the
Docker port bound to `127.0.0.1`, as the Compose file does.
