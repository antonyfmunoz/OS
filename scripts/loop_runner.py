#!/usr/bin/env python3
"""Loop runner CLI — start, stop, and query persistent loops.

Usage:
    python3 scripts/loop_runner.py status              # show all loop states
    python3 scripts/loop_runner.py start                # start all enabled loops
    python3 scripts/loop_runner.py start business_ops   # start one loop
    python3 scripts/loop_runner.py stop                 # stop all loops
    python3 scripts/loop_runner.py run-once research    # run single cycle
    python3 scripts/loop_runner.py run-forever          # start all, block
    python3 scripts/loop_runner.py add my_loop ops 60 signal_drain,actionable_scan
    python3 scripts/loop_runner.py remove my_loop
    python3 scripts/loop_runner.py stages               # list available stages

Loops are loaded from data/config/loop_definitions.jsonl.
Custom definitions can be added at runtime and persisted back.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from substrate.execution.loop import get_registry, STAGE_REGISTRY  # noqa: E402
from substrate.execution.loop.persistent_loop import LoopDefinition  # noqa: E402


def _init_registry():
    """Load definitions + ensure stages are registered."""
    registry = get_registry()
    if not registry.list_loops():
        registry.load_definitions()
    return registry


def cmd_status(args: argparse.Namespace) -> int:
    registry = _init_registry()
    status = registry.status()
    print(json.dumps(status, indent=2, default=str))
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    registry = _init_registry()
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
    registry = _init_registry()
    if args.loop_name:
        registry.stop(args.loop_name)
        print(f"Stopped: {args.loop_name}")
    else:
        stopped = registry.stop_all()
        print(f"Stopped: {stopped}")
    return 0


def cmd_run_once(args: argparse.Namespace) -> int:
    registry = _init_registry()
    loop = registry.get(args.loop_name)
    if not loop:
        print(f"Unknown loop: {args.loop_name}")
        print(f"Available: {registry.list_loops()}")
        return 1
    report = loop.run_once()
    print(json.dumps(report.to_dict(), indent=2, default=str))
    return 0


def cmd_run_forever(args: argparse.Namespace) -> int:
    registry = _init_registry()
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


def cmd_add(args: argparse.Namespace) -> int:
    registry = _init_registry()
    stages = [s.strip() for s in args.stages.split(",") if s.strip()]
    unknown = [s for s in stages if s not in STAGE_REGISTRY]
    if unknown:
        print(f"Unknown stages: {unknown}")
        print(f"Available: {sorted(STAGE_REGISTRY.keys())}")
        return 1

    defn = LoopDefinition(
        name=args.name,
        domain=args.domain,
        interval_seconds=args.interval,
        stages=stages,
        description=args.description or "",
    )
    registry.register_definition(defn)
    registry.save_definitions()
    print(f"Added and saved: {defn.name} (stages={stages}, interval={args.interval}s)")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    registry = _init_registry()
    ok = registry.remove(args.name)
    if not ok:
        print(f"Unknown loop: {args.name}")
        return 1
    registry.save_definitions()
    print(f"Removed and saved: {args.name}")
    return 0


def cmd_stages(args: argparse.Namespace) -> int:
    for name, func in sorted(STAGE_REGISTRY.items()):
        doc = (func.__doc__ or "").strip().split("\n")[0]
        print(f"  {name:30s} {doc}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="UMH Persistent Loop Runner")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show all loop states")
    sub.add_parser("stages", help="List available pipeline stages")

    p_start = sub.add_parser("start", help="Start loop(s)")
    p_start.add_argument("loop_name", nargs="?", help="Loop name (omit for all)")

    p_stop = sub.add_parser("stop", help="Stop loop(s)")
    p_stop.add_argument("loop_name", nargs="?", help="Loop name (omit for all)")

    p_once = sub.add_parser("run-once", help="Run one cycle of a loop")
    p_once.add_argument("loop_name", help="Loop name")

    sub.add_parser("run-forever", help="Start all enabled loops and block")

    p_add = sub.add_parser("add", help="Add a new loop definition")
    p_add.add_argument("name", help="Loop name")
    p_add.add_argument("domain", help="Domain (e.g. operations, intelligence)")
    p_add.add_argument("interval", type=int, help="Interval in seconds")
    p_add.add_argument("stages", help="Comma-separated stage names")
    p_add.add_argument("--description", default="", help="Loop description")

    p_rm = sub.add_parser("remove", help="Remove a loop definition")
    p_rm.add_argument("name", help="Loop name")

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
        "add": cmd_add,
        "remove": cmd_remove,
        "stages": cmd_stages,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
