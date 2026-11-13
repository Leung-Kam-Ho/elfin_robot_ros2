# elfin_tools

Host-side CLI tools for the Elfin robot. This project **does not import ROS**; it
reads state from the `elfin_web_api` Flask server over HTTP. It is intended to
run on a laptop (macOS, Linux, or Windows) while the robot stack runs in the
Docker container.

The first command is `elfin joint-state`. The HTTP client in
`src/elfin_tools/api.py` is the intended base for future AI/automation tooling.

## Setup

Run these commands from the **repository root**. The root `pyproject.toml`
defines this host-side tool; it does not include the ROS packages or the
container-side Flask API.

```sh
uv sync
uv run elfin --help
```

Install it as a standalone command:

```sh
uv tool install .
elfin joint-state
```

## Commands

### Read joint state

```sh
uv run elfin joint-state
```

```text
Elfin joint state   age 0.031s   stamp 2026-11-13T08:45:32.293Z

 #  joint          rad         deg
 1  elfin_joint1   -1.57010   -89.960
 2  elfin_joint2   -0.79308   -45.440
...
```

Raw API response:

```sh
uv run elfin joint-state --json
```

Poll continuously (compact, one sample per line):

```sh
uv run elfin joint-state --watch --interval 0.2
```

Machine-readable JSON Lines, suitable for logging or feeding another process:

```sh
uv run elfin joint-state --watch --json
```

Show the last known state even if it is stale:

```sh
uv run elfin joint-state --allow-stale
```

### Check freshness

```sh
uv run elfin health
```

Exits `0` only when joint state is available and fresh. Exits `1` otherwise, so
it can be used in scripts or shell conditions.

## Configuration

| Option | Environment | Default |
| --- | --- | --- |
| `--url` | `ELFIN_API_URL` | `http://localhost:5001` |
| `--timeout` | — | `3.0` seconds |
| `--interval` | — | `0.5` seconds (`--watch`) |

Point it at another host or port:

```sh
ELFIN_API_URL=http://192.168.1.10:5001 uv run elfin joint-state
```

The API must be running first. In the repository's Docker setup, either enable
`ELFIN_JOINT_API_AUTOSTART=true` or start it manually:

```sh
docker compose exec elfin5 /usr/local/bin/elfin_web_api.sh
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success (for `health`: state available and fresh) |
| `1` | API unreachable, stale/missing state, or unexpected response |
| `130` | Interrupted with Ctrl+C |

## Using the client from Python

```python
from elfin_tools import ElfinClient

with ElfinClient("http://localhost:5001") as client:
    state = client.joint_state()
    print(state["positions_deg"])
```

## Development

```sh
uv run pytest
```

## Why this is a root uv project

The repository root is the uv project for **host-side tooling**. Its only
Python package is `elfin_tools`, so `uv run elfin ...` works without changing
directories, while `uv sync` never touches ROS or colcon.

`elfin_web_api` remains a separate project because it runs inside ROS Foxy on
Python 3.8 and needs rclpy from the system interpreter. Mixing it into the root
project would tie host tooling to the container's Python version. A uv
workspace can be added later if multiple host packages need a shared lockfile.
