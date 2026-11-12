"""MoveIt FollowJointTrajectory action adapter for the Elfin TCP protocol.

This is not a hard-real-time servo interface. It maps trajectory waypoints to
the protocol's MoveBJ command and must only be enabled after validating the
robot configuration and TCP mode on the physical system.
"""

import math
import threading
import time

import rclpy
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState

from elfin_tcp_driver.protocol import HansRobotTcpClient, ProtocolError


JOINT_NAMES = [
    "elfin_joint1",
    "elfin_joint2",
    "elfin_joint3",
    "elfin_joint4",
    "elfin_joint5",
    "elfin_joint6",
]

# These are the software limits in the Elfin5 xacro, represented in degrees.
JOINT_LIMITS_DEG = [
    (-180.0, 180.0),
    (-134.6, 134.6),
    (-149.5, 149.5),
    (-180.0, 180.0),
    (-146.7, 146.7),
    (-180.0, 180.0),
]


class ElfinTcpAdapter(Node):
    def __init__(self):
        super().__init__("elfin_tcp_adapter")
        self.declare_parameter("robot_ip", "192.168.1.63")
        self.declare_parameter("robot_port", 10003)
        self.declare_parameter("robot_id", 0)
        self.declare_parameter("allow_motion", False)
        self.declare_parameter("connect_timeout_sec", 3.0)
        self.declare_parameter("response_timeout_sec", 2.0)
        self.declare_parameter("state_publish_rate_hz", 5.0)
        self.declare_parameter("motion_timeout_sec", 120.0)
        self.declare_parameter("max_waypoint_lateness_sec", 0.5)
        self.declare_parameter("move_state_poll_period_sec", 0.1)

        self.robot_id = int(self.get_parameter("robot_id").value)
        self.allow_motion = bool(self.get_parameter("allow_motion").value)
        self.motion_timeout_sec = float(
            self.get_parameter("motion_timeout_sec").value
        )
        self.max_waypoint_lateness_sec = float(
            self.get_parameter("max_waypoint_lateness_sec").value
        )
        self.move_state_poll_period_sec = float(
            self.get_parameter("move_state_poll_period_sec").value
        )
        self.client = HansRobotTcpClient(
            self.get_parameter("robot_ip").value,
            self.get_parameter("robot_port").value,
            connect_timeout=self.get_parameter("connect_timeout_sec").value,
            response_timeout=self.get_parameter("response_timeout_sec").value,
        )

        self._action_group = ReentrantCallbackGroup()
        self._active_goal_lock = threading.Lock()
        self._active_goal = False
        self._motion_active = threading.Event()
        self._last_state_error = None
        self.joint_state_pub = self.create_publisher(JointState, "/joint_states", 10)
        self._action_server = ActionServer(
            self,
            FollowJointTrajectory,
            "elfin_arm_controller/follow_joint_trajectory",
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self._action_group,
        )

        state_rate = max(
            0.2, float(self.get_parameter("state_publish_rate_hz").value)
        )
        self._state_timer = self.create_timer(1.0 / state_rate, self.publish_state)

        if self.allow_motion:
            self.get_logger().warning(
                "TCP motion is ENABLED. No servo/power-on command is sent by this node."
            )
        else:
            self.get_logger().warning(
                "Read-only mode: FollowJointTrajectory goals are rejected. "
                "Set allow_motion:=true only after validating the setup."
            )
        self.get_logger().info(
            "Elfin TCP adapter targeting "
            f"{self.get_parameter('robot_ip').value}:"
            f"{self.get_parameter('robot_port').value}"
        )

    def destroy_node(self):
        self.client.close()
        return super().destroy_node()

    def goal_callback(self, goal_request):
        if not self.allow_motion:
            self.get_logger().error("Rejecting motion goal: allow_motion is false")
            return GoalResponse.REJECT
        try:
            self._validate_trajectory(goal_request.trajectory)
        except ValueError as exc:
            self.get_logger().error(f"Rejecting invalid trajectory: {exc}")
            return GoalResponse.REJECT
        with self._active_goal_lock:
            if self._active_goal:
                self.get_logger().warning("Rejecting goal: another trajectory is active")
                return GoalResponse.REJECT
            self._active_goal = True
        return GoalResponse.ACCEPT

    def cancel_callback(self, _goal_handle):
        return CancelResponse.ACCEPT

    def _validate_trajectory(self, trajectory):
        if not trajectory.points:
            raise ValueError("trajectory contains no points")
        if len(trajectory.joint_names) != len(JOINT_NAMES):
            raise ValueError("trajectory must contain exactly the six Elfin5 joints")
        if set(trajectory.joint_names) != set(JOINT_NAMES):
            raise ValueError("trajectory joint names do not match the Elfin5 joints")

        joint_index = {name: index for index, name in enumerate(trajectory.joint_names)}
        previous_time = -1.0
        for point_number, point in enumerate(trajectory.points):
            if len(point.positions) != len(JOINT_NAMES):
                raise ValueError(f"point {point_number} must have six positions")
            point_time = point.time_from_start.sec + point.time_from_start.nanosec * 1e-9
            if not math.isfinite(point_time) or point_time < previous_time:
                raise ValueError("trajectory point times must be finite and ordered")
            previous_time = point_time
            for joint_number, joint_name in enumerate(JOINT_NAMES):
                position = point.positions[joint_index[joint_name]]
                if not math.isfinite(position):
                    raise ValueError(f"point {point_number} contains a non-finite position")
                position_deg = math.degrees(position)
                lower, upper = JOINT_LIMITS_DEG[joint_number]
                if position_deg < lower or position_deg > upper:
                    raise ValueError(
                        f"point {point_number} exceeds the {joint_name} software limits"
                    )

    def _joint_positions_deg(self, trajectory, point):
        joint_index = {name: index for index, name in enumerate(trajectory.joint_names)}
        return [
            math.degrees(point.positions[joint_index[name]]) for name in JOINT_NAMES
        ]

    def _check_robot_ready(self):
        dcs = self.client.request("ReadDCSStatus,;")
        if len(dcs) != 1 or int(dcs[0]) != 10:
            raise ProtocolError(f"DCS is not normal (ReadDCSStatus={dcs})")

        state = self.client.request(f"ReadRobotState,{self.robot_id},;")
        if len(state) < 8:
            raise ProtocolError(f"Malformed ReadRobotState response: {state}")
        moving_state = int(state[0])
        power_state = int(state[1])
        error_state = int(state[2])
        if moving_state != 0:
            raise ProtocolError("Robot is already moving; refusing a new trajectory")
        if power_state != 1:
            raise ProtocolError(
                "Robot servos are not enabled; enable them using the teach pendant "
                "after completing the safety checks"
            )
        if error_state != 0:
            raise ProtocolError(f"Robot reports an error (ReadRobotState={state})")

    def execute_callback(self, goal_handle):
        result = FollowJointTrajectory.Result()
        trajectory = goal_handle.request.trajectory
        motion_started = False
        self._motion_active.set()
        try:
            self._check_robot_ready()
            actual_deg = self.client.request(
                f"ReadAcsActualPos,{self.robot_id},;"
            )
            if len(actual_deg) != len(JOINT_NAMES):
                raise ProtocolError(
                    f"Expected six joint positions, received {actual_deg}"
                )
            actual_deg = [float(value) for value in actual_deg]
            start_time = time.monotonic()
            command_number = 0

            for point in trajectory.points:
                target_time = point.time_from_start.sec + point.time_from_start.nanosec * 1e-9
                while True:
                    if goal_handle.is_cancel_requested:
                        if motion_started:
                            self._best_effort_stop()
                        goal_handle.canceled()
                        result.error_code = FollowJointTrajectory.Result.INVALID_GOAL
                        result.error_string = "Trajectory cancelled"
                        return result
                    remaining = start_time + target_time - time.monotonic()
                    if remaining <= 0:
                        break
                    time.sleep(min(remaining, 0.02))
                lateness = time.monotonic() - (start_time + target_time)
                if lateness > self.max_waypoint_lateness_sec:
                    raise ProtocolError(
                        "TCP adapter fell behind the trajectory by "
                        f"{lateness:.3f}s; aborting rather than sending stale waypoints"
                    )

                joints_deg = self._joint_positions_deg(trajectory, point)
                if command_number == 0 and max(
                    abs(target - current)
                    for target, current in zip(joints_deg, actual_deg)
                ) < 0.1:
                    # MoveIt commonly includes the measured start state as its
                    # first point. Skip that no-op so the first real target can
                    # start a MoveJ; following points retarget it with MoveBJ.
                    continue

                command_name = "MoveJ" if command_number == 0 else "MoveBJ"
                command = "{},{},{},{},{},{},{},{},;".format(
                    command_name,
                    self.robot_id,
                    *[f"{position:.6f}" for position in joints_deg]
                )
                self.client.request(command)
                motion_started = True
                command_number += 1

            if not motion_started:
                self.publish_state()
                goal_handle.succeed()
                result.error_code = FollowJointTrajectory.Result.SUCCESSFUL
                result.error_string = "Trajectory already at the requested position"
                return result

            deadline = time.monotonic() + self.motion_timeout_sec
            while time.monotonic() < deadline:
                if goal_handle.is_cancel_requested:
                    if motion_started:
                        self._best_effort_stop()
                    goal_handle.canceled()
                    result.error_code = FollowJointTrajectory.Result.INVALID_GOAL
                    result.error_string = "Trajectory cancelled"
                    return result
                move_state = self.client.request(
                    f"ReadMoveState,{self.robot_id},;"
                )
                if not move_state:
                    raise ProtocolError("ReadMoveState returned no state")
                state_value = int(move_state[0])
                if state_value == 0:
                    self._motion_active.clear()
                    self.publish_state()
                    goal_handle.succeed()
                    result.error_code = FollowJointTrajectory.Result.SUCCESSFUL
                    result.error_string = ""
                    return result
                if state_value not in (1009, 1013):
                    raise ProtocolError(f"Robot entered motion state {state_value}")
                time.sleep(self.move_state_poll_period_sec)

            raise ProtocolError("Timed out waiting for robot motion to complete")
        except (ProtocolError, OSError, ValueError) as exc:
            if motion_started:
                self._best_effort_stop()
            self.get_logger().error(f"Trajectory failed: {exc}")
            goal_handle.abort()
            result.error_code = FollowJointTrajectory.Result.INVALID_GOAL
            result.error_string = str(exc)
            return result
        finally:
            self._motion_active.clear()
            with self._active_goal_lock:
                self._active_goal = False

    def _best_effort_stop(self):
        try:
            self.client.request(f"GrpStop,{self.robot_id},;")
        except ProtocolError as exc:
            self.get_logger().error(f"Could not send TCP stop command: {exc}")

    def publish_state(self):
        if self._motion_active.is_set():
            return
        try:
            positions_deg = self.client.request(
                f"ReadAcsActualPos,{self.robot_id},;"
            )
            if len(positions_deg) != len(JOINT_NAMES):
                raise ProtocolError(
                    f"Expected six joint positions, received {positions_deg}"
                )
            message = JointState()
            message.header.stamp = self.get_clock().now().to_msg()
            message.name = list(JOINT_NAMES)
            message.position = [math.radians(float(value)) for value in positions_deg]
            self.joint_state_pub.publish(message)
            self._last_state_error = None
        except (ProtocolError, OSError, ValueError) as exc:
            error = str(exc)
            if error != self._last_state_error:
                self.get_logger().warning(f"TCP state read failed: {error}")
                self._last_state_error = error


def main(args=None):
    rclpy.init(args=args)
    node = ElfinTcpAdapter()
    executor = MultiThreadedExecutor(num_threads=3)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
