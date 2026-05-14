#!/usr/bin/env python3
"""
Wake producer CLI — simulate wake-word / clap events and view history.

Bounded. No audio frameworks. No freeform commands. Mirrors the
substrate_voice_session_cli.py idiom. Never raises — errors are printed
as JSON with an "error" key.
"""

from __future__ import annotations

import argparse
import json
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.transport.wake_producer import (  # noqa: E402
    get_wake_producer_runtime,
)


def _emit(obj) -> None:
    print(json.dumps(obj, default=str, indent=2))


def cmd_simulate_wake_word(args: argparse.Namespace) -> int:
    rt = get_wake_producer_runtime()
    event = rt.simulate_wake_word(
        node_id=args.node,
        phrase=args.phrase,
        confidence=args.confidence,
        issued_by=args.issued_by,
    )
    _emit(event.as_dict())
    return 0


def cmd_simulate_clap(args: argparse.Namespace) -> int:
    rt = get_wake_producer_runtime()
    event = rt.simulate_clap(
        node_id=args.node,
        confidence=args.confidence,
        issued_by=args.issued_by,
    )
    _emit(event.as_dict())
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    rt = get_wake_producer_runtime()
    _emit(rt.report(node_id=args.node, limit=args.limit))
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    rt = get_wake_producer_runtime()
    _emit(
        {
            "runtime_mode": rt.runtime_mode,
            "report": rt.report(limit=5),
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="substrate_wake_producer_cli",
        description="Simulate wake producer events and inspect history.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sw = sub.add_parser("simulate-wake-word", help="Simulate a wake-word event")
    sw.add_argument("--node", required=True)
    sw.add_argument("--phrase", default=None)
    sw.add_argument("--confidence", type=float, default=None)
    sw.add_argument("--issued-by", default="wake_producer_cli")
    sw.set_defaults(func=cmd_simulate_wake_word)

    sc = sub.add_parser("simulate-clap", help="Simulate a clap-detected event")
    sc.add_argument("--node", required=True)
    sc.add_argument("--confidence", type=float, default=None)
    sc.add_argument("--issued-by", default="wake_producer_cli")
    sc.set_defaults(func=cmd_simulate_clap)

    rp = sub.add_parser("report", help="Report recent wake producer events")
    rp.add_argument("--node", default=None)
    rp.add_argument("--limit", type=int, default=5)
    rp.set_defaults(func=cmd_report)

    st = sub.add_parser("status", help="Runtime mode + short report")
    st.set_defaults(func=cmd_status)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:  # noqa: BLE001
        _emit({"error": str(e)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
