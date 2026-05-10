#!/usr/bin/env python3
"""Session Orchestration CLI — operator visibility into session topology.

Usage:
    python3 scripts/substrate_session_orchestration_cli.py status
    python3 scripts/substrate_session_orchestration_cli.py health
    python3 scripts/substrate_session_orchestration_cli.py ensure
    python3 scripts/substrate_session_orchestration_cli.py recover --session dex_builder_main
    python3 scripts/substrate_session_orchestration_cli.py reconcile
    python3 scripts/substrate_session_orchestration_cli.py expected
    python3 scripts/substrate_session_orchestration_cli.py actual
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

try:
    from eos_ai.substrate.session_orchestration import (
        actual_sessions,
        ensure_expected_sessions,
        expected_sessions,
        reconcile_sessions,
        recover_session,
        session_readiness_report,
    )
except ImportError as exc:
    print(f"ERROR: cannot import session_orchestration: {exc}", file=sys.stderr)
    sys.exit(1)


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


# ── subcommands ──────────────────────────────────────────────


def cmd_status(_args: argparse.Namespace) -> int:
    report = session_readiness_report()
    _print_json(report)
    return 0


def cmd_health(_args: argparse.Namespace) -> int:
    report = session_readiness_report()
    sessions = report.get("sessions", [])

    # Build mode lookup from expected sessions for display
    exp = expected_sessions()
    mode_map = {es.session_name: es.mode for es in exp}

    print("Session Orchestration Health Report")
    print("═" * 50)
    for s in sessions:
        name = s.get("session_name", "?")
        target = s.get("target", "?")
        mode = mode_map.get(name, "?")
        health = s.get("health", "UNKNOWN")
        print(f"  {name:<24}{target:<8}{mode:<14}{health}")
    print("─" * 50)

    healthy = report.get("healthy_count", 0)
    degraded = report.get("degraded_count", 0)
    missing = report.get("missing_count", 0)
    overall = report.get("overall", "unknown")
    print(
        f"Overall: {overall}  "
        f"({healthy} healthy, {degraded} degraded, {missing} missing)"
    )
    return 0


def cmd_ensure(_args: argparse.Namespace) -> int:
    result = ensure_expected_sessions()
    _print_json(result)
    return 0


def cmd_recover(args: argparse.Namespace) -> int:
    result = recover_session(
        target=args.target,
        session_name=args.session,
        strategy=args.strategy,
    )
    _print_json(result)
    return 0


def cmd_reconcile(_args: argparse.Namespace) -> int:
    result = reconcile_sessions()
    _print_json(result)
    return 0


def cmd_expected(_args: argparse.Namespace) -> int:
    sessions = expected_sessions()
    _print_json([dataclasses.asdict(s) for s in sessions])
    return 0


def cmd_actual(args: argparse.Namespace) -> int:
    sessions = actual_sessions(target=args.target)
    _print_json(sessions)
    return 0


# ── argparse ─────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Session Orchestration CLI — operator visibility into session topology.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Print session readiness report as JSON")
    sub.add_parser("health", help="Human-readable health table")
    sub.add_parser("ensure", help="Ensure all expected sessions exist")

    p_recover = sub.add_parser("recover", help="Recover a specific session")
    p_recover.add_argument("--session", required=True, help="Session name to recover")
    p_recover.add_argument("--target", default="vps", help="Target (default: vps)")
    p_recover.add_argument(
        "--strategy", default="recreate", help="Recovery strategy (default: recreate)"
    )

    sub.add_parser("reconcile", help="Reconcile expected vs actual sessions")
    sub.add_parser("expected", help="List expected sessions as JSON")

    p_actual = sub.add_parser("actual", help="List actual sessions as JSON")
    p_actual.add_argument("--target", default="vps", help="Target (default: vps)")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "status": cmd_status,
        "health": cmd_health,
        "ensure": cmd_ensure,
        "recover": cmd_recover,
        "reconcile": cmd_reconcile,
        "expected": cmd_expected,
        "actual": cmd_actual,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
