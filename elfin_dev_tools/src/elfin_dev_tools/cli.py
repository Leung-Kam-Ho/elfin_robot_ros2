"""Command-line interface for the Elfin robot.

Runs on the host (for example macOS) and talks only to the HTTP API, so it does
not need ROS, Docker, or rclpy.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

from . import __version__
from .api import (
    DEFAULT_API_URL,
    DEFAULT_TIMEOUT_SEC,
    ElfinApiError,
    ElfinClient,
)


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive finite number")
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--url",
        default=os.environ.get("ELFIN_API_URL", DEFAULT_API_URL),
        help="API base URL (env: ELFIN_API_URL, default: %(default)s)",
    )
    common.add_argument(
        "--timeout",
        type=_positive_float,
        default=DEFAULT_TIMEOUT_SEC,
        help="request timeout in seconds (default: %(default)s)",
    )

    parser = argparse.ArgumentParser(
        prog="elfin",
        description="Host-side tools for the Elfin robot (no ROS required)",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s {}".format(__version__)
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    joint_state = subparsers.add_parser(
        "joint-state",
        parents=[common],
        help="read the current joint state",
        description="Read the latest joint state from /api/joint-state.",
    )
    joint_state.add_argument(
        "--json", action="store_true", help="print the raw API response as JSON"
    )
    joint_state.add_argument(
        "--watch",
        action="store_true",
        help="poll continuously; one line per sample, or JSON Lines with --json",
    )
    joint_state.add_argument(
        "--interval",
        type=_positive_float,
        default=0.5,
        help="seconds between samples with --watch (default: %(default)s)",
    )
    joint_state.add_argument(
        "--allow-stale",
        action="store_true",
        help="print the API's last-known sample even when it is stale",
    )

    health = subparsers.add_parser(
        "health",
        parents=[common],
        help="check whether fresh joint state is available",
        description="Call /healthz. Exits non-zero when state is stale or missing.",
    )
    health.add_argument(
        "--json", action="store_true", help="print the raw health response as JSON"
    )

    return parser


def _stamp_text(stamp: dict[str, Any] | None) -> str:
    if not stamp:
        return "n/a"
    seconds = int(stamp.get("sec", 0))
    nanoseconds = int(stamp.get("nanosec", 0))
    if seconds == 0 and nanoseconds == 0:
        return "n/a"
    moment = datetime.fromtimestamp(seconds + nanoseconds / 1e9, tz=timezone.utc)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _age_text(age_sec: Any) -> str:
    if age_sec is None:
        return "n/a"
    return "{:.3f}s".format(float(age_sec))


def _format_table(payload: dict[str, Any]) -> str:
    names = list(payload.get("names") or [])
    positions = list(payload.get("positions") or [])
    positions_deg = list(payload.get("positions_deg") or [])

    heading = "Elfin joint state   age {}   stamp {}".format(
        _age_text(payload.get("age_sec")), _stamp_text(payload.get("stamp"))
    )
    if payload.get("stale"):
        heading += "   [STALE]"

    if not names:
        return heading + "\n\nNo joints reported."

    name_width = max([len("joint")] + [len(str(name)) for name in names])
    lines = [
        heading,
        "",
        "{:>2}  {:<{width}}  {:>10}  {:>10}".format(
            "#", "joint", "rad", "deg", width=name_width
        ),
    ]

    for index, name in enumerate(names):
        if index < len(positions_deg):
            degrees = float(positions_deg[index])
        elif index < len(positions):
            degrees = math.degrees(float(positions[index]))
        else:
            degrees = float("nan")
        radians = (
            float(positions[index])
            if index < len(positions)
            else math.radians(degrees)
        )
        lines.append(
            "{:>2}  {:<{width}}  {:>10.5f}  {:>10.3f}".format(
                index + 1, str(name), radians, degrees, width=name_width
            )
        )
    return "\n".join(lines)


def _format_compact(payload: dict[str, Any]) -> str:
    degrees = list(payload.get("positions_deg") or [])
    prefix = "stale " if payload.get("stale") else ""
    joints = " ".join(
        "j{}={:.2f}".format(index + 1, float(value))
        for index, value in enumerate(degrees)
    )
    return "{}age={} {}".format(prefix, _age_text(payload.get("age_sec")), joints)


def _print_joint_state(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(_format_table(payload))


def _run_joint_state(args: argparse.Namespace, client: ElfinClient) -> int:
    if not args.watch:
        _print_joint_state(
            client.joint_state(allow_stale=args.allow_stale), as_json=args.json
        )
        return 0

    while True:
        try:
            payload = client.joint_state(allow_stale=args.allow_stale)
        except ElfinApiError as exc:
            print("waiting: {}".format(exc), file=sys.stderr, flush=True)
        else:
            if args.json:
                print(json.dumps(payload, separators=(",", ":")), flush=True)
            else:
                print(_format_compact(payload), flush=True)
        time.sleep(args.interval)


def _run_health(args: argparse.Namespace, client: ElfinClient) -> int:
    payload = client.health()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            "{} topic={} available={} stale={} age={}".format(
                payload.get("status", "unknown"),
                payload.get("topic", "?"),
                payload.get("joint_state_available", False),
                payload.get("stale", True),
                _age_text(payload.get("age_sec")),
            )
        )
    healthy = bool(payload.get("joint_state_available")) and not bool(
        payload.get("stale", True)
    )
    return 0 if healthy else 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        with ElfinClient(args.url, args.timeout) as client:
            if args.command == "health":
                return _run_health(args, client)
            return _run_joint_state(args, client)
    except ElfinApiError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
