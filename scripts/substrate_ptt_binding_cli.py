#!/usr/bin/env python3
"""
Workstation push-to-talk binding CLI.

Subcommands:
  readiness   Show stt_workstation_readiness() (exit 0 if real_ready).
  devices     List enumerable input audio devices.
  validate    Run one bounded REAL_READY proof attempt and report it.
  report      Show recent validation history + current readiness.

This is intentionally small. It is NOT a daemon, not an always-on loop.
Every action is one explicit bounded call onto the bounded seam:

    capture_once(mode="push_to_talk")
    → inject_transcript(source="push_to_talk")
    → voice session → responder → SPEAK_TEXT

Usage examples:
    python3 scripts/substrate_ptt_binding_cli.py readiness

    python3 scripts/substrate_ptt_binding_cli.py validate \\
        --node antony-workstation --duration 4.0

    python3 scripts/substrate_ptt_binding_cli.py validate \\
        --node antony-workstation --simulated-fallback "test ptt path"

    python3 scripts/substrate_ptt_binding_cli.py report \\
        --node antony-workstation --limit 10
"""

from __future__ import annotations

import argparse
import json
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def cmd_readiness(args: argparse.Namespace) -> int:
    from runtime.substrate.stt_producer import stt_workstation_readiness

    payload = stt_workstation_readiness()
    _print_json(payload)
    return 0 if payload.get("classification") == "real_ready" else 1


def cmd_devices(args: argparse.Namespace) -> int:
    from runtime.substrate.stt_producer import _enumerate_input_devices  # noqa: WPS450

    devices = _enumerate_input_devices()
    _print_json({"count": len(devices), "devices": devices})
    return 0 if devices else 1


def cmd_validate(args: argparse.Namespace) -> int:
    from runtime.substrate.ptt_binding import validate_real_capture

    result = validate_real_capture(
        args.node,
        duration_s=args.duration,
        device=args.device,
        role_slug=args.role,
        simulated_fallback_text=args.simulated_fallback,
        metadata={"issued_by": "ptt_binding_cli"},
    )
    _print_json(result)
    cls = (result.get("classification") or "").lower()
    return 0 if cls in ("real_ready", "simulated_only") and result.get("injected") else 1


def cmd_report(args: argparse.Namespace) -> int:
    from runtime.substrate.ptt_binding import real_capture_report

    _print_json(real_capture_report(node_id=args.node, limit=args.limit))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    sub = p.add_subparsers(dest="cmd", required=True)

    rd = sub.add_parser("readiness", help="workstation PTT readiness probe")
    rd.set_defaults(func=cmd_readiness)

    dv = sub.add_parser("devices", help="list input audio devices")
    dv.set_defaults(func=cmd_devices)

    v = sub.add_parser("validate", help="run one REAL_READY proof attempt")
    v.add_argument("--node", required=True)
    v.add_argument("--duration", type=float, default=4.0)
    v.add_argument("--role", default="ea_orchestrator")
    v.add_argument("--device", type=int, default=None)
    v.add_argument(
        "--simulated-fallback",
        default=None,
        help="text to inject as a simulated capture if real capture is unsupported",
    )
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("report", help="recent validation history + readiness")
    r.add_argument("--node", default=None)
    r.add_argument("--limit", type=int, default=10)
    r.set_defaults(func=cmd_report)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
