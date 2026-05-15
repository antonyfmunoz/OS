#!/usr/bin/env python3
"""
Claude Code Session Bridge CLI.

Operator-facing wrapper over runtime.substrate.claude_session_bridge. Provides
explicit, bounded control over persistent Claude Code tmux sessions on either
the VPS node or the local node.

Subcommands:
  detect    Print tmux + claude CLI availability and default target (JSON).
  list      List dex_* tmux sessions visible on this node.
  status    Report status of a single named session.
  ensure    Create session (idempotent); optionally launch claude inside.
  send      Inject text into a session's pane.
  capture   Capture bounded tail of pane output.
  ask       ensure → send → bounded poll → capture → extract reply.

Usage examples:
  python3 scripts/substrate_claude_session_cli.py detect
  python3 scripts/substrate_claude_session_cli.py list --target vps
  python3 scripts/substrate_claude_session_cli.py ensure \\
      --target vps --session dex_main --working-dir /opt/OS
  python3 scripts/substrate_claude_session_cli.py send \\
      --target vps --session dex_main --text "hello"
  python3 scripts/substrate_claude_session_cli.py ask \\
      --target vps --session dex_main --text "what is 2+2?"
"""

from __future__ import annotations

import argparse
import json
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from execution.transport import claude_session_bridge as csb  # noqa: E402


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def cmd_detect(_args: argparse.Namespace) -> int:
    _print_json(
        {
            "tmux": csb.detect_tmux_available(),
            "claude_cli": csb.detect_claude_cli_available(),
            "default_target": csb.default_session_target(),
            "layer": csb.LAYER_NAME,
            "version": csb.LAYER_VERSION,
        }
    )
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    _print_json(csb.list_sessions(target=args.target))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    res = csb.session_status(args.target, args.session)
    _print_json(res)
    return 0 if res.get("ok") else 1


def cmd_ensure(args: argparse.Namespace) -> int:
    res = csb.ensure_session(
        args.target,
        args.session,
        working_dir=args.working_dir,
        launch_claude=not args.no_launch,
    )
    _print_json(res)
    return 0 if res.get("ok") else 1


def cmd_send(args: argparse.Namespace) -> int:
    res = csb.send_message(args.target, args.session, args.text)
    _print_json(res)
    return 0 if res.get("ok") else 1


def cmd_capture(args: argparse.Namespace) -> int:
    res = csb.capture_output(args.target, args.session, tail_lines=args.tail_lines)
    _print_json(res)
    return 0 if res.get("ok") else 1


def cmd_ask(args: argparse.Namespace) -> int:
    res = csb.ask_session(
        args.target,
        args.session,
        args.text,
        ensure=not args.no_ensure,
        working_dir=args.working_dir,
        poll_interval_s=args.poll_interval,
        max_polls=args.max_polls,
        settle_lines=args.tail_lines,
    )
    _print_json(res)
    return 0 if res.get("ok") else 1


def _add_target(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--target",
        choices=list(csb.VALID_TARGETS),
        default=csb.default_session_target(),
        help="Session target node (vps|local). Defaults by EOS_NODE_ROLE/hostname.",
    )


def _add_session(p: argparse.ArgumentParser) -> None:
    p.add_argument("--session", required=True, help="tmux session name (e.g. dex_main)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Claude Code Session Bridge CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("detect", help="Print environment detection")
    p.set_defaults(func=cmd_detect)

    p = sub.add_parser("list", help="List dex_* tmux sessions on this node")
    _add_target(p)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("status", help="Status of a named session")
    _add_target(p)
    _add_session(p)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("ensure", help="Ensure session exists (optionally launch claude)")
    _add_target(p)
    _add_session(p)
    p.add_argument("--working-dir", default=None)
    p.add_argument("--no-launch", action="store_true", help="Do not auto-launch claude")
    p.set_defaults(func=cmd_ensure)

    p = sub.add_parser("send", help="Inject text into a session")
    _add_target(p)
    _add_session(p)
    p.add_argument("--text", required=True)
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("capture", help="Capture bounded pane output")
    _add_target(p)
    _add_session(p)
    p.add_argument("--tail-lines", type=int, default=200)
    p.set_defaults(func=cmd_capture)

    p = sub.add_parser("ask", help="Ensure+send+poll+capture a reply")
    _add_target(p)
    _add_session(p)
    p.add_argument("--text", required=True)
    p.add_argument("--working-dir", default=None)
    p.add_argument("--no-ensure", action="store_true")
    p.add_argument("--poll-interval", type=float, default=0.5)
    p.add_argument("--max-polls", type=int, default=12)
    p.add_argument("--tail-lines", type=int, default=200)
    p.set_defaults(func=cmd_ask)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
