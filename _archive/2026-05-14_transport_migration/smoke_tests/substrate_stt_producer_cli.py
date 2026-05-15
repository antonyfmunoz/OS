#!/usr/bin/env python3
"""
STT producer CLI — bounded operator interface to the local STT capture layer.

Subcommands:
  report              Show stt_runtime_status + capture snapshot + recent.
  capture             Perform one bounded capture on a node.
                      Modes: simulated | manual | push_to_talk
  inject              Shortcut: manual text capture → inject_transcript.
  recent              Show last N capture events (JSON).

This is intentionally small. It is NOT a daemon, not an always-on loop,
not a workstation controller. Every action is one explicit bounded call.

Usage examples:
    python3 scripts/substrate_stt_producer_cli.py report
    python3 scripts/substrate_stt_producer_cli.py report --node antony-workstation

    python3 scripts/substrate_stt_producer_cli.py capture \\
        --node antony-workstation \\
        --mode simulated \\
        --text "tell me the pending tasks"

    python3 scripts/substrate_stt_producer_cli.py capture \\
        --node antony-workstation \\
        --mode push_to_talk \\
        --duration 4.0

    python3 scripts/substrate_stt_producer_cli.py inject \\
        --node antony-workstation \\
        --text "status check"

    python3 scripts/substrate_stt_producer_cli.py recent --limit 10
"""

from __future__ import annotations

import argparse
import json
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def cmd_report(args: argparse.Namespace) -> int:
    from runtime.transport.stt_producer import (
        recent_stt_captures,
        stt_capture_snapshot,
        stt_runtime_status,
    )

    payload = {
        "runtime_status": stt_runtime_status(),
        "snapshot": stt_capture_snapshot(node_id=args.node),
        "recent": recent_stt_captures(limit=args.limit, node_id=args.node),
    }
    _print_json(payload)
    return 0


def cmd_readiness(args: argparse.Namespace) -> int:
    """Workstation-facing readiness probe.

    Exits 0 if the workstation can do REAL push-to-talk right now,
    1 otherwise. The JSON payload always includes actionable next steps.
    """
    from runtime.transport.stt_producer import stt_workstation_readiness

    payload = stt_workstation_readiness()
    _print_json(payload)
    return 0 if payload.get("classification") == "real_ready" else 1


def cmd_devices(args: argparse.Namespace) -> int:
    """List enumerable input audio devices (lazy sounddevice import)."""
    from runtime.transport.stt_producer import _enumerate_input_devices  # noqa: WPS450

    devices = _enumerate_input_devices()
    _print_json({"count": len(devices), "devices": devices})
    return 0 if devices else 1


def cmd_capture(args: argparse.Namespace) -> int:
    from runtime.transport.stt_producer import get_local_stt_runtime

    rt = get_local_stt_runtime()
    event = rt.capture_once(
        args.node,
        mode=args.mode,
        duration_s=args.duration,
        simulated_text=args.text if args.mode == "simulated" else None,
        manual_text=args.text if args.mode == "manual" else None,
        role_slug=args.role,
        start_if_missing=not args.no_start,
        device=args.device,
        metadata={"issued_by": "stt_producer_cli"},
    )
    _print_json(event.as_dict())
    return 0 if event.status.value in ("injected", "degraded") else 1


def cmd_inject(args: argparse.Namespace) -> int:
    from runtime.transport.stt_producer import get_local_stt_runtime

    rt = get_local_stt_runtime()
    event = rt.capture_once(
        args.node,
        mode="manual",
        manual_text=args.text,
        role_slug=args.role,
        start_if_missing=not args.no_start,
        metadata={"issued_by": "stt_producer_cli", "via": "inject"},
    )
    _print_json(event.as_dict())
    return 0 if event.status.value == "injected" else 1


def cmd_recent(args: argparse.Namespace) -> int:
    from runtime.transport.stt_producer import recent_stt_captures

    _print_json(recent_stt_captures(limit=args.limit, node_id=args.node))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("report", help="show runtime status + snapshot + recent")
    r.add_argument("--node", default=None)
    r.add_argument("--limit", type=int, default=10)
    r.set_defaults(func=cmd_report)

    c = sub.add_parser("capture", help="perform one bounded capture")
    c.add_argument("--node", required=True)
    c.add_argument(
        "--mode",
        choices=["simulated", "manual", "push_to_talk"],
        default="push_to_talk",
    )
    c.add_argument("--text", default=None, help="text for simulated/manual modes")
    c.add_argument("--duration", type=float, default=4.0)
    c.add_argument("--role", default="ea_orchestrator")
    c.add_argument(
        "--no-start", action="store_true", help="do not start a session if missing"
    )
    c.add_argument(
        "--device",
        type=int,
        default=None,
        help="sounddevice input device index (see `devices` subcommand)",
    )
    c.set_defaults(func=cmd_capture)

    rd = sub.add_parser(
        "readiness",
        help="workstation-facing PTT readiness probe (exit 0 if real_ready)",
    )
    rd.set_defaults(func=cmd_readiness)

    dv = sub.add_parser("devices", help="list input audio devices")
    dv.set_defaults(func=cmd_devices)

    i = sub.add_parser("inject", help="manual-text shortcut capture")
    i.add_argument("--node", required=True)
    i.add_argument("--text", required=True)
    i.add_argument("--role", default="ea_orchestrator")
    i.add_argument("--no-start", action="store_true")
    i.set_defaults(func=cmd_inject)

    rec = sub.add_parser("recent", help="show recent capture events (JSON)")
    rec.add_argument("--node", default=None)
    rec.add_argument("--limit", type=int, default=10)
    rec.set_defaults(func=cmd_recent)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
