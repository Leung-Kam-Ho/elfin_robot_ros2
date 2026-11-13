"""Flask HTTP API for the Elfin robot's live joint state.

The process subscribes to ``/joint_states`` with rclpy and serves the most
recent message over HTTP. It must run inside a sourced ROS 2 environment
because rclpy is supplied by ROS, not by PyPI::

    source /opt/ros/foxy/setup.bash
    uv sync --system-site-packages
    .venv/bin/python app.py

Endpoints
---------
GET /api/joint-state
    Latest joint positions in radians and degrees, plus velocity and effort
    when the publisher provides them. Returns 503 until a message has been
    received, or when the newest message is older than
    ``ELFIN_JOINT_STATE_MAX_AGE`` seconds.
GET /healthz
    Liveness plus whether fresh joint-state data is currently available.
"""

import math
import os
import threading
import time
from datetime import datetime, timezone

import rclpy
from flask import Flask, jsonify
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState


def _env_float(name, default):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise SystemExit("{} must be a number, got {!r}".format(name, raw)) from exc
    if not math.isfinite(value) or value <= 0.0:
        raise SystemExit(
            "{} must be a positive finite number, got {!r}".format(name, raw)
        )
    return value


def _env_int(name, default):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit("{} must be an integer, got {!r}".format(name, raw)) from exc
    if not 1 <= value <= 65535:
        raise SystemExit("{} must be in 1..65535, got {!r}".format(name, raw))
    return value


class JointStateCache(Node):
    """Keep a thread-safe copy of the newest JointState message."""

    def __init__(self):
        super().__init__("elfin_joint_state_api")
        self.topic = os.environ.get("ELFIN_JOINT_STATE_TOPIC", "/joint_states")
        self._lock = threading.Lock()
        self._latest = None
        self._received_monotonic = None
        self.create_subscription(JointState, self.topic, self._on_joint_state, 10)
        self.get_logger().info("Subscribed to {}".format(self.topic))

    def _on_joint_state(self, message):
        positions = [float(value) for value in message.position]
        velocities = [float(value) for value in message.velocity]
        efforts = [float(value) for value in message.effort]

        joints = []
        for index, name in enumerate(message.name):
            joint = {"name": name}
            if index < len(positions):
                joint["position_rad"] = positions[index]
                joint["position_deg"] = math.degrees(positions[index])
            if index < len(velocities):
                joint["velocity"] = velocities[index]
            if index < len(efforts):
                joint["effort"] = efforts[index]
            joints.append(joint)

        snapshot = {
            "frame_id": message.header.frame_id,
            "stamp": {
                "sec": int(message.header.stamp.sec),
                "nanosec": int(message.header.stamp.nanosec),
            },
            "names": list(message.name),
            "positions": positions,
            "positions_deg": [math.degrees(value) for value in positions],
            "velocities": velocities,
            "efforts": efforts,
            "joints": joints,
        }
        snapshot["received_at"] = datetime.now(timezone.utc).isoformat()

        with self._lock:
            self._latest = snapshot
            self._received_monotonic = time.monotonic()

    def snapshot(self):
        """Return ``(snapshot, age_sec)`` or ``(None, None)`` if no data yet."""
        with self._lock:
            if self._latest is None:
                return None, None
            return self._latest, time.monotonic() - self._received_monotonic


def _json_body(snapshot, age_sec, stale):
    return {
        "stale": stale,
        "age_sec": round(age_sec, 3),
        "frame_id": snapshot["frame_id"],
        "stamp": snapshot["stamp"],
        "received_at": snapshot["received_at"],
        "names": snapshot["names"],
        "positions": snapshot["positions"],
        "positions_deg": snapshot["positions_deg"],
        "velocities": snapshot["velocities"],
        "efforts": snapshot["efforts"],
        "joints": snapshot["joints"],
    }


def create_app(cache, max_age_sec):
    app = Flask(__name__)
    app.json.sort_keys = False

    @app.get("/api/joint-state")
    def joint_state():
        snapshot, age_sec = cache.snapshot()
        if snapshot is None:
            return (
                jsonify(
                    {
                        "error": "no joint state received yet",
                        "topic": cache.topic,
                        "stale": True,
                    }
                ),
                503,
            )

        stale = age_sec > max_age_sec
        body = _json_body(snapshot, age_sec, stale)
        if stale:
            body["error"] = "joint state is stale"
        return jsonify(body), (503 if stale else 200)

    @app.get("/healthz")
    def healthz():
        snapshot, age_sec = cache.snapshot()
        stale = snapshot is None or age_sec > max_age_sec
        return jsonify(
            {
                "status": "ok",
                "topic": cache.topic,
                "joint_state_available": snapshot is not None,
                "stale": stale,
                "age_sec": None if age_sec is None else round(age_sec, 3),
            }
        )

    return app


def main():
    host = os.environ.get("ELFIN_JOINT_API_HOST", "0.0.0.0")
    port = _env_int("ELFIN_JOINT_API_PORT", 5001)
    max_age_sec = _env_float("ELFIN_JOINT_STATE_MAX_AGE", 2.0)

    rclpy.init()
    cache = JointStateCache()
    executor = SingleThreadedExecutor()
    executor.add_node(cache)

    spin_thread = threading.Thread(
        target=executor.spin, name="rclpy-spin", daemon=True
    )
    spin_thread.start()

    app = create_app(cache, max_age_sec)
    print(
        "Elfin joint-state API listening on http://{}:{}".format(host, port),
        flush=True,
    )

    try:
        app.run(host=host, port=port, threaded=True, use_reloader=False)
    finally:
        executor.shutdown()
        spin_thread.join(timeout=2.0)
        cache.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
