#!/usr/bin/env python3
"""Loop runner CLI — start, stop, and query persistent loops.

Usage:
    python3 scripts/loop_runner.py status           # show all loop states
    python3 scripts/loop_runner.py start             # start all loops
    python3 scripts/loop_runner.py start business_ops # start one loop
    python3 scripts/loop_runner.py stop              # stop all loops
    python3 scripts/loop_runner.py run-once research # run single cycle
    python3 scripts/loop_runner.py run-forever       # start all, block
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from substrate.execution.loop.persistent_loop import get_registry  # noqa: E402


def cmd_status(args: argparse.Namespace) -> int:
    registry = get_registry()
    registry.register_defaults()
    status = registry.status()
    print(json.dumps(status, indent=2, default=str))
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    registry = get_registry()
    registry.register_defaults()
    if args.loop_name:
        ok = registry.start(args.loop_name)
        if not ok:
            print(f"Unknown loop: {args.loop_name}")
            print(f"Available: {registry.list_loops()}")
            return 1
        print(f"Started: {args.loop_name}")
    else:
        started = registry.start_all()
        print(f"Started: {started}")
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    registry = get_registry()
    registry.register_defaults()
    if args.loop_name:
        registry.stop(args.loop_name)
        print(f"Stopped: {args.loop_name}")
    else:
        stopped = registry.stop_all()
        print(f"Stopped: {stopped}")
    return 0


def cmd_run_once(args: argparse.Namespace) -> int:
    registry = get_registry()
    registry.register_defaults()
    loop = registry.get(args.loop_name)
    if not loop:
        print(f"Unknown loop: {args.loop_name}")
        print(f"Available: {registry.list_loops()}")
        return 1
    report = loop.run_once()
    print(json.dumps(report.to_dict(), indent=2, default=str))
    return 0


def cmd_run_forever(args: argparse.Namespace) -> int:
    registry = get_registry()
    registry.register_defaults()
    started = registry.start_all()
    print(f"Started all loops: {started}")
    print("Press Ctrl+C to stop.")

    stop = False

    def handle_signal(sig, frame):
        nonlocal stop
        stop = True
        print("\nStopping all loops...")
        registry.stop_all()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while not stop:
        time.sleep(10)
        status = registry.status()
        running = sum(1 for s in status.values() if s["state"] == "running")
        if running == 0:
            print("All loops stopped.")
            break

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="UMH Persistent Loop Runner")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show all loop states")

    p_start = sub.add_parser("start", help="Start loop(s)")
    p_start.add_argument("loop_name", nargs="?", help="Loop name (omit for all)")

    p_stop = sub.add_parser("stop", help="Stop loop(s)")
    p_stop.add_argument("loop_name", nargs="?", help="Loop name (omit for all)")

    p_once = sub.add_parser("run-once", help="Run one cycle of a loop")
    p_once.add_argument("loop_name", help="Loop name")

    sub.add_parser("run-forever", help="Start all loops and block")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    handlers = {
        "status": cmd_status,
        "start": cmd_start,
        "stop": cmd_stop,
        "run-once": cmd_run_once,
        "run-forever": cmd_run_forever,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
