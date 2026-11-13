"""Curses dashboard for MoveIt arm motion and the TCP Robotiq gripper."""

import curses
import math
import threading
import time

import rclpy
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_srvs.srv import Trigger

from elfin_robot_msgs.srv import SetRobotiq
from elfin_tcp_driver.adapter_node import JOINT_LIMITS_DEG, JOINT_NAMES


class ElfinRobotTui(Node):
    def __init__(self):
        super().__init__("elfin_robot_tui")
        self.declare_parameter("enable_arm_commands", False)
        self.declare_parameter("enable_gripper_commands", False)
        self.declare_parameter("planning_time_sec", 5.0)
        self.declare_parameter("planning_velocity_scaling", 0.1)
        self.declare_parameter("planning_acceleration_scaling", 0.1)

        self.enable_arm_commands = bool(
            self.get_parameter("enable_arm_commands").value
        )
        self.enable_gripper_commands = bool(
            self.get_parameter("enable_gripper_commands").value
        )
        self.planning_time_sec = float(self.get_parameter("planning_time_sec").value)
        self.velocity_scaling = float(
            self.get_parameter("planning_velocity_scaling").value
        )
        self.acceleration_scaling = float(
            self.get_parameter("planning_acceleration_scaling").value
        )
        if not math.isfinite(self.planning_time_sec) or self.planning_time_sec <= 0:
            raise ValueError("planning_time_sec must be positive and finite")
        if not 0 < self.velocity_scaling <= 1:
            raise ValueError("planning_velocity_scaling must be in (0, 1]")
        if not 0 < self.acceleration_scaling <= 1:
            raise ValueError("planning_acceleration_scaling must be in (0, 1]")

        self._callbacks = ReentrantCallbackGroup()
        self._lock = threading.Lock()
        self._joint_positions = {}
        self._gripper_commanded_position = None
        # The toggle is a UI-side target sequence, independent of encoder reads.
        # Begin by commanding 140 degrees on the first toggle press.
        self._next_gripper_toggle_target = 140.0
        self._pending_gripper_target = None
        self._message = "Waiting for robot state..."
        self._arm_pending = False
        self._active_arm_goal = None
        self._gripper_pending = False

        self._joint_state_sub = self.create_subscription(
            JointState, "/joint_states", self._joint_state_callback, 10
        )
        self._move_group_client = ActionClient(
            self,
            MoveGroup,
            "/move_action",
            callback_group=self._callbacks,
        )
        self._gripper_move_client = self.create_client(
            SetRobotiq,
            "/elfin_gripper/move",
            callback_group=self._callbacks,
        )
        self._gripper_reset_client = self.create_client(
            Trigger,
            "/elfin_gripper/reset",
            callback_group=self._callbacks,
        )

    def destroy_node(self):
        self._move_group_client.destroy()
        return super().destroy_node()

    def _joint_state_callback(self, message):
        with self._lock:
            for name, position in zip(message.name, message.position):
                if name in JOINT_NAMES:
                    self._joint_positions[name] = math.degrees(position)

    def _set_message(self, message):
        with self._lock:
            self._message = message

    def _snapshot(self):
        with self._lock:
            return (
                dict(self._joint_positions),
                self._gripper_commanded_position,
                self._message,
                self._arm_pending,
                self._gripper_pending,
            )

    def _read_joint_goal(self, screen):
        values = self._prompt(
            screen,
            "Enter J1..J6 target degrees separated by spaces, or leave blank to cancel:",
        )
        if not values:
            return
        try:
            joints = [float(value) for value in values.replace(",", " ").split()]
            if len(joints) != 6 or not all(math.isfinite(value) for value in joints):
                raise ValueError("Enter exactly six finite joint angles")
            for name, value, limits in zip(JOINT_NAMES, joints, JOINT_LIMITS_DEG):
                if value < limits[0] or value > limits[1]:
                    raise ValueError(
                        f"{name} target {value:g}° is outside {limits[0]:g}..{limits[1]:g}°"
                    )
        except ValueError as exc:
            self._set_message(str(exc))
            return
        self._send_joint_goal(joints)

    def _send_joint_goal(self, joints_deg):
        if not self.enable_arm_commands:
            self._set_message(
                "Arm commands disabled in TUI; restart with enable_arm_commands:=true"
            )
            return
        if not self._move_group_client.server_is_ready():
            self._set_message("MoveIt /move_action is not available")
            return
        with self._lock:
            if self._arm_pending or self._gripper_pending:
                self._message = "Another arm or gripper command is active"
                return
            self._arm_pending = True
            self._message = "Sending joint-space plan to MoveIt..."

        goal = MoveGroup.Goal()
        goal.request.group_name = "elfin_arm"
        goal.request.allowed_planning_time = self.planning_time_sec
        goal.request.num_planning_attempts = 5
        goal.request.max_velocity_scaling_factor = self.velocity_scaling
        goal.request.max_acceleration_scaling_factor = self.acceleration_scaling
        constraints = Constraints()
        for name, position_deg in zip(JOINT_NAMES, joints_deg):
            joint_constraint = JointConstraint()
            joint_constraint.joint_name = name
            joint_constraint.position = math.radians(position_deg)
            joint_constraint.tolerance_above = math.radians(1.0)
            joint_constraint.tolerance_below = math.radians(1.0)
            joint_constraint.weight = 1.0
            constraints.joint_constraints.append(joint_constraint)
        goal.request.goal_constraints = [constraints]
        goal.planning_options.plan_only = False
        goal.planning_options.look_around = False
        goal.planning_options.replan = False

        future = self._move_group_client.send_goal_async(goal)
        future.add_done_callback(self._arm_goal_response)

    def _arm_goal_response(self, future):
        try:
            goal_handle = future.result()
            if not goal_handle.accepted:
                self._set_message("MoveIt rejected the arm goal")
                with self._lock:
                    self._arm_pending = False
                return
            with self._lock:
                self._active_arm_goal = goal_handle
                self._message = "MoveIt accepted goal; planning/execution in progress..."
            goal_handle.get_result_async().add_done_callback(self._arm_result)
        except Exception as exc:  # noqa: BLE001 - report middleware/action errors in the TUI
            with self._lock:
                self._arm_pending = False
                self._active_arm_goal = None
                self._message = f"Arm goal failed: {exc}"

    def _arm_result(self, future):
        try:
            wrapped = future.result()
            error_code = wrapped.result.error_code.val
            if error_code == MoveItErrorCodes.SUCCESS:
                message = "MoveIt plan and execution succeeded"
            else:
                message = f"MoveIt failed with error code {error_code}"
        except Exception as exc:  # noqa: BLE001 - report middleware/action errors in the TUI
            message = f"Arm result failed: {exc}"
        with self._lock:
            self._arm_pending = False
            self._active_arm_goal = None
            self._message = message

    def _cancel_arm_goal(self):
        with self._lock:
            goal_handle = self._active_arm_goal
        if goal_handle is None:
            self._set_message("No active arm goal to cancel")
            return
        goal_handle.cancel_goal_async().add_done_callback(
            lambda _future: self._set_message(
                "Arm cancellation requested; verify the robot has stopped"
            )
        )

    def _read_gripper_command(self, screen):
        if not self.enable_gripper_commands:
            self._set_message(
                "Gripper commands disabled in TUI; restart with enable_gripper_commands:=true"
            )
            return
        values = self._prompt(
            screen,
            "Enter gripper angle [0-140], speed [30-250], force [10-125] (or blank to cancel):",
        )
        if not values:
            return
        try:
            command = [float(value) for value in values.replace(",", " ").split()]
            if len(command) not in (1, 3) or not all(
                math.isfinite(value) for value in command
            ):
                raise ValueError("Enter an angle, optionally followed by speed and force")
            position = command[0]
            speed = command[1] if len(command) == 3 else 250.0
            force = command[2] if len(command) == 3 else 10.0
            if position < 0 or position > 140:
                raise ValueError("Gripper angle must be between 0 and 140 degrees")
            if speed < 30 or speed > 250:
                raise ValueError("Gripper speed must be between 30 and 250")
            if force < 10 or force > 125:
                raise ValueError("Gripper force must be between 10 and 125")
        except ValueError as exc:
            self._set_message(str(exc))
            return
        self._send_gripper_goal(position, speed, force)

    def _send_gripper_goal(self, position, speed, force):
        if not self.enable_gripper_commands:
            self._set_message("Gripper commands are disabled in this TUI session")
            return
        if not self._gripper_move_client.service_is_ready():
            self._set_message("Gripper service is unavailable; is the TCP adapter running?")
            return
        with self._lock:
            if self._arm_pending or self._gripper_pending:
                self._message = "Another arm or gripper command is active"
                return
            self._gripper_pending = True
            self._message = f"Commanding gripper to {position:g} degrees..."
        request = SetRobotiq.Request()
        request.position = float(position)
        request.speed = float(speed)
        request.force = float(force)
        with self._lock:
            self._pending_gripper_target = float(position)
        self._gripper_move_client.call_async(request).add_done_callback(
            self._gripper_move_done
        )

    def _toggle_gripper(self):
        if not self.enable_gripper_commands:
            self._set_message(
                "Gripper commands disabled in TUI; enable_gripper_commands:=true"
            )
            return
        with self._lock:
            target_position = self._next_gripper_toggle_target
        # Zero speed/force asks the adapter to use its configured defaults.
        self._send_gripper_goal(target_position, 0.0, 0.0)

    def _gripper_move_done(self, future):
        try:
            response = future.result()
            message = response.message
            if response.success:
                with self._lock:
                    commanded_target = self._pending_gripper_target
                    self._gripper_commanded_position = commanded_target
                    if commanded_target is not None:
                        self._next_gripper_toggle_target = (
                            0.0 if commanded_target > 70.0 else 140.0
                        )
            else:
                message = f"Gripper command failed: {message}"
        except Exception as exc:  # noqa: BLE001 - report middleware/service errors in the TUI
            message = f"Gripper command failed: {exc}"
        with self._lock:
            self._gripper_pending = False
            self._pending_gripper_target = None
            self._message = message

    def _reset_gripper(self):
        if not self.enable_gripper_commands:
            self._set_message("Gripper commands are disabled in this TUI session")
            return
        if not self._gripper_reset_client.service_is_ready():
            self._set_message("Gripper reset service is unavailable")
            return
        with self._lock:
            if self._arm_pending or self._gripper_pending:
                self._message = "Another arm or gripper command is active"
                return
            self._gripper_pending = True
            self._message = "Sending Robotiq reset..."
        self._gripper_reset_client.call_async(Trigger.Request()).add_done_callback(
            self._gripper_reset_done
        )

    def _gripper_reset_done(self, future):
        try:
            response = future.result()
            message = response.message if response.success else f"Reset failed: {response.message}"
            if response.success:
                with self._lock:
                    self._gripper_commanded_position = None
                    self._next_gripper_toggle_target = 140.0
        except Exception as exc:  # noqa: BLE001 - report middleware/service errors in the TUI
            message = f"Reset failed: {exc}"
        with self._lock:
            self._gripper_pending = False
            self._message = message

    @staticmethod
    def _prompt(screen, label):
        height, width = screen.getmaxyx()
        if height < 3:
            return ""
        screen.addstr(height - 2, 0, label[: max(0, width - 1)])
        screen.clrtoeol()
        screen.addstr(height - 1, 0, " " * max(0, width - 1))
        screen.move(height - 1, 0)
        screen.refresh()
        screen.timeout(-1)
        curses.echo()
        try:
            return screen.getstr(height - 1, 0, max(1, width - 1)).decode("utf-8")
        finally:
            curses.noecho()
            screen.timeout(100)

    def run_tui(self, screen):
        screen.keypad(True)
        screen.timeout(100)
        while rclpy.ok():
            self._draw(screen)
            key = screen.getch()
            if key == ord("q"):
                break
            if key == ord("j"):
                self._read_joint_goal(screen)
            elif key == ord("g"):
                self._read_gripper_command(screen)
            elif key == ord("t"):
                self._toggle_gripper()
            elif key == ord("r"):
                self._reset_gripper()
            elif key in (ord("s"), 3):
                self._cancel_arm_goal()

    def _draw(self, screen):
        screen.erase()
        height, width = screen.getmaxyx()
        joints, gripper_position, message, arm_pending, gripper_pending = self._snapshot()
        rows = [
            "Elfin5 TCP Robot Console",
            "Read-only by default; physical E-stop is not replaced by this app.",
            f"Arm commands: {'ENABLED' if self.enable_arm_commands else 'disabled'}   "
            f"Gripper commands: {'ENABLED' if self.enable_gripper_commands else 'disabled'}",
            "",
            "Actual arm joints (degrees):",
        ]
        for index, name in enumerate(JOINT_NAMES, start=1):
            value = joints.get(name)
            rows.append(f"  J{index}  {value:8.2f}" if value is not None else f"  J{index}  waiting")
        rows.extend(
            [
                "",
                "Last gripper command: "
                + (
                    f"{gripper_position:.1f}° (not sensor feedback)"
                    if gripper_position is not None
                    else "unknown (position read disabled)"
                ),
                f"Command state: arm={'busy' if arm_pending else 'idle'}, "
                f"gripper={'busy' if gripper_pending else 'idle'}",
                "",
                "Keys: j=arm target   g=gripper angle   t=toggle gripper 0/140 degrees",
                "      r=reset gripper",
                "      s=cancel active arm goal     q=quit",
                "",
                f"Status: {message}",
            ]
        )
        for row, text in enumerate(rows[: max(0, height - 2)]):
            try:
                screen.addstr(row, 0, text[: max(0, width - 1)])
            except curses.error:
                pass
        screen.refresh()


def main(args=None):
    rclpy.init(args=args)
    node = ElfinRobotTui()
    executor = MultiThreadedExecutor(num_threads=3)
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    try:
        curses.wrapper(node.run_tui)
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown(timeout_sec=2.0)
        spin_thread.join(timeout=2.0)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
