#!/usr/bin/env python3
"""
Bounded operator CLI for the voice session substrate.

Subcommands:
  start   --node NODE --role ROLE          Start a new voice session.
  say     --session SID --text TEXT        Submit an utterance to a session.
  switch  --session SID --role ROLE        Switch the active role.
  end     --session SID [--reason TEXT]    Mark a session ended.
  report  [--node NODE] [--limit N]        Print recent voice session activity.
  list    [--node NODE] [--limit N]        Alias for report.

This CLI is intentionally tiny. It is the operator-facing seam over the
VoiceSessionRuntime + VoiceSessionStore — nothing more. Output is JSON
for everything except `report`, which prints a compact human summary.
"""

from __future__ import annotations

import argparse
import json
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.voice_session import (  # noqa: E402
    VoiceSessionRuntime,
    voice_session_report,
)


def _maybe_install_eos_responder() -> None:
    """Best-effort install of the EOS-backed responder.

    Imported lazily so the CLI still works if voice_eos_responder or
    model_router has an import-time issue. Falls back silently to the
    substrate stub if anything goes wrong.
    """
    try:
        from eos_ai.substrate.voice_eos_responder import (
            install_default_eos_voice_responder,
        )

        install_default_eos_voice_responder()
    except Exception as e:  # noqa: BLE001
        print(
            json.dumps({"warning": f"eos responder not installed: {e}"}),
            file=sys.stderr,
        )


def _print_session(session) -> int:
    if session is None:
        print(json.dumps({"error": "session not found"}))
        return 1
    print(json.dumps(session.as_dict(), indent=2, default=str))
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    if getattr(args, "eos", False):
        _maybe_install_eos_responder()
    rt = VoiceSessionRuntime()
    session = rt.start_session(args.node, role_slug=args.role)
    return _print_session(session)


def cmd_say(args: argparse.Namespace) -> int:
    rt = VoiceSessionRuntime()
    session = rt.submit_utterance(args.session, args.text)
    return _print_session(session)


def cmd_switch(args: argparse.Namespace) -> int:
    rt = VoiceSessionRuntime()
    session = rt.switch_role(args.session, args.role)
    return _print_session(session)


def cmd_end(args: argparse.Namespace) -> int:
    rt = VoiceSessionRuntime()
    session = rt.end_session(args.session, reason=args.reason)
    return _print_session(session)


def cmd_report(args: argparse.Namespace) -> int:
    report = voice_session_report(node_id=args.node, limit=args.limit)
    # Surface responder mode at the top level so operators can see it without
    # crawling per-session metadata.
    try:
        from eos_ai.substrate.voice_eos_responder import (
            is_eos_voice_responder_installed,
        )

        report["responder_mode"] = (
            "eos" if is_eos_voice_responder_installed() else "stub"
        )
    except Exception:  # noqa: BLE001
        report["responder_mode"] = "stub"
    print(json.dumps(report, indent=2, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="substrate_voice_session_cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start", help="Start a new voice session")
    s.add_argument("--node", required=True)
    s.add_argument("--role", default="ea_orchestrator")
    s.add_argument(
        "--eos",
        action="store_true",
        help="Install the EOS-backed responder (otherwise the substrate stub is used)",
    )
    s.set_defaults(func=cmd_start)

    s = sub.add_parser("say", help="Submit an utterance to a session")
    s.add_argument("--session", required=True)
    s.add_argument("--text", required=True)
    s.set_defaults(func=cmd_say)

    s = sub.add_parser("switch", help="Switch the active role of a session")
    s.add_argument("--session", required=True)
    s.add_argument("--role", required=True)
    s.set_defaults(func=cmd_switch)

    s = sub.add_parser("end", help="End a voice session")
    s.add_argument("--session", required=True)
    s.add_argument("--reason", default=None)
    s.set_defaults(func=cmd_end)

    for name in ("report", "list"):
        s = sub.add_parser(name, help="Recent voice session activity")
        s.add_argument("--node", default=None)
        s.add_argument("--limit", type=int, default=5)
        s.set_defaults(func=cmd_report)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
