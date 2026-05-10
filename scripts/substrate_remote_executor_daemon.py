#!/usr/bin/env python3
"""
Control Layer v2 — Remote Executor Daemon CLI.

Subcommands:
    run       --node NODE_ID [--interval 1.0] [--batch 5]
    run-once  --node NODE_ID
    status    [--node NODE_ID]

JSON in, JSON out. Never raises — failures emit a JSON error envelope.
"""

from __future__ import annotations

import argparse
import json
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.remote_executor import RemoteExecutor  # noqa: E402
from eos_ai.substrate import remote_identity  # noqa: E402


def _emit(payload: dict) -> int:
    try:
        print(json.dumps(payload, default=str, indent=2))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "reason": f"emit_error:{type(e).__name__}"}))
        return 1
    return 0 if payload.get("ok") else 1


def _cmd_run(args) -> int:
    node = args.node or remote_identity.get_node_id()
    ex = RemoteExecutor()
    result = ex.run_loop(node, interval_s=args.interval, max_batch=args.batch)
    return _emit(result)


def _cmd_run_once(args) -> int:
    node = args.node or remote_identity.get_node_id()
    ex = RemoteExecutor()
    result = ex.poll_once(node)
    return _emit(result)


def _cmd_status(args) -> int:
    node = args.node or remote_identity.get_node_id()
    ex = RemoteExecutor()
    return _emit(ex.status(node))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="substrate_remote_executor_daemon",
        description="EOS Control Layer v2 — remote executor daemon (queue reader).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="poll-loop until interrupted")
    p_run.add_argument("--node", default=None)
    p_run.add_argument("--interval", type=float, default=1.0)
    p_run.add_argument("--batch", type=int, default=5)
    p_run.set_defaults(func=_cmd_run)

    p_once = sub.add_parser("run-once", help="single drain pass")
    p_once.add_argument("--node", default=None)
    p_once.set_defaults(func=_cmd_run_once)

    p_status = sub.add_parser("status", help="queue depth + last batch")
    p_status.add_argument("--node", default=None)
    p_status.set_defaults(func=_cmd_status)

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    try:
        return int(args.func(args) or 0)
    except Exception as e:  # noqa: BLE001
        print(
            json.dumps(
                {"ok": False, "reason": f"cli_error:{type(e).__name__}", "detail": str(e)}
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
