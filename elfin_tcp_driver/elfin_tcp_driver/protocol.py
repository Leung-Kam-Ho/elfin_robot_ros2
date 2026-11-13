"""Small synchronous client for the HansRobot ASCII TCP protocol."""

import math
import socket
import threading
import time


class ProtocolError(RuntimeError):
    """Raised when the robot returns an invalid or failed protocol reply."""


def clamp(value, minimum, maximum):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Robotiq command values must be finite")
    return max(min(float(maximum), value), float(minimum))


def format_robotiq_command(position, speed=250, force=10):
    """Clamp values and format a HansRobot SetRobotiq command."""
    position = clamp(position, 0, 140)
    speed = int(round(clamp(speed, 30, 250)))
    force = int(round(clamp(force, 10, 125)))
    position_text = f"{position:.3f}".rstrip("0").rstrip(".")
    return f"SetRobotiq,{position_text},{speed},{force},;"


def parse_robotiq_moving(fields):
    """Return the moving state encoded by RobotiqStatus."""
    try:
        values = [int(value) for value in fields]
    except (TypeError, ValueError) as exc:
        raise ProtocolError(f"Invalid RobotiqStatus response: {fields}") from exc

    moving_state = (0, 3, 1, 1)
    stopped_states = ((3, 3, 1, 1), (2, 3, 1, 1))
    windows = [tuple(values[index:index + 4]) for index in range(len(values) - 3)]
    if moving_state in windows:
        return True
    if any(state in windows for state in stopped_states):
        return False
    raise ProtocolError(f"Unexpected RobotiqStatus response: {fields}")


class HansRobotTcpClient:
    """Keep one serialized TCP session and read complete semicolon messages."""

    def __init__(self, host, port, connect_timeout=3.0, response_timeout=2.0):
        self.host = str(host)
        self.port = int(port)
        self.connect_timeout = float(connect_timeout)
        self.response_timeout = float(response_timeout)
        self._socket = None
        self._receive_buffer = bytearray()
        self._lock = threading.Lock()

    def close(self):
        with self._lock:
            self._close_unlocked()

    def _close_unlocked(self):
        if self._socket is not None:
            try:
                self._socket.close()
            finally:
                self._socket = None
                self._receive_buffer.clear()

    def _connect_unlocked(self):
        if self._socket is not None:
            return
        self._socket = socket.create_connection(
            (self.host, self.port), timeout=self.connect_timeout
        )
        self._socket.settimeout(self.response_timeout)
        self._receive_buffer.clear()

    def request(self, message):
        """Send one complete protocol message and return comma-separated fields."""
        command = str(message).strip()
        if not command.endswith(";"):
            command += ";"
        try:
            encoded = command.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ProtocolError("Protocol messages must contain ASCII only") from exc

        with self._lock:
            try:
                self._connect_unlocked()
                self._socket.sendall(encoded)
                response = self._receive_message_unlocked()
            except (OSError, socket.timeout) as exc:
                self._close_unlocked()
                raise ProtocolError(f"TCP request failed: {exc}") from exc

        fields = [field.strip() for field in response[:-1].split(",")]
        while fields and not fields[-1]:
            fields.pop()
        if len(fields) < 2:
            raise ProtocolError(f"Malformed protocol response: {response!r}")
        if fields[1] == "Fail":
            code = fields[2] if len(fields) > 2 else "unknown"
            raise ProtocolError(f"Robot returned error {code} for {fields[0]}")
        if fields[1] != "OK":
            raise ProtocolError(f"Unexpected protocol response: {response!r}")
        return fields[2:]

    def _receive_message_unlocked(self):
        deadline = time.monotonic() + self.response_timeout
        while True:
            delimiter = self._receive_buffer.find(b";")
            if delimiter >= 0:
                raw = bytes(self._receive_buffer[: delimiter + 1])
                del self._receive_buffer[: delimiter + 1]
                try:
                    return raw.decode("ascii")
                except UnicodeDecodeError as exc:
                    raise ProtocolError("Robot response is not ASCII") from exc

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise socket.timeout("timed out waiting for ';' response terminator")
            self._socket.settimeout(remaining)
            chunk = self._socket.recv(4096)
            if not chunk:
                raise OSError("robot closed the TCP connection")
            self._receive_buffer.extend(chunk)
            if len(self._receive_buffer) > 65536:
                raise ProtocolError("Robot response exceeded 64 KiB")
