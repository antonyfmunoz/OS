#!/usr/bin/env python3
"""
Bounded operator CLI for the local audio loop.

Subcommands:
  report                             Snapshot the audio loop across all nodes.
  report-node --node NODE            Snapshot one node + its transcript ring.
  inject-transcript --node NODE --text TEXT [--source SRC] [--role ROLE]
                                     Inject a transcript into the voice loop.
  prime --node NODE [--wake-event EID]
                                     Mark a node as PRIMED (no wake event).

Output: JSON for all responses. Never raises — errors are {"error": "..."}.
"""

from __future__ import annotations

import argparse
import json
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")


def _dumps(obj) -> str:
    return json.dumps(obj, indent=2, default=str)


def cmd_report(args: argparse.Namespace) -> int:
    try:
        from eos_ai.substrate.result_query import audio_loop_snapshot

        snap = audio_loop_snapshot(node_id=None)
        print(_dumps(snap))
        return 0
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


def cmd_report_node(args: argparse.Namespace) -> int:
    try:
        from eos_ai.substrate.result_query import (
            audio_loop_snapshot,
            recent_audio_loop_transcripts,
        )

        snap = audio_loop_snapshot(node_id=args.node)
        transcripts = recent_audio_loop_transcripts(args.node, limit=args.limit)
        out = {
            "snapshot": snap,
            "recent_transcripts": transcripts,
        }
        print(_dumps(out))
        return 0
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


def cmd_inject_transcript(args: argparse.Namespace) -> int:
    try:
        from eos_ai.substrate.transcript_inject import inject_transcript

        result = inject_transcript(
            args.node,
            args.text,
            source=args.source,
            start_if_missing=not args.no_start,
            role_slug=args.role,
        )
        print(_dumps(result))
        return 0 if result.get("status") == "ok" else 2
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


def cmd_prime(args: argparse.Namespace) -> int:
    try:
        from eos_ai.substrate.audio_loop import mark_primed

        state = mark_primed(
            args.node,
            wake_event_id=args.wake_event,
        )
        if state is None:
            print(json.dumps({"error": "mark_primed returned None"}), file=sys.stderr)
            return 1
        print(_dumps(state.as_dict()))
        return 0
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="substrate_audio_loop_cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("report", help="Snapshot audio loop across all nodes")
    s.set_defaults(func=cmd_report)

    s = sub.add_parser("report-node", help="Snapshot one node + transcript ring")
    s.add_argument("--node", required=True)
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_report_node)

    s = sub.add_parser("inject-transcript", help="Inject text into the voice loop")
    s.add_argument("--node", required=True)
    s.add_argument("--text", required=True)
    s.add_argument("--source", default="manual")
    s.add_argument("--role", default="ea_orchestrator")
    s.add_argument(
        "--no-start",
        action="store_true",
        help="Fail instead of starting a new session if none is active",
    )
    s.set_defaults(func=cmd_inject_transcript)

    s = sub.add_parser("prime", help="Mark a node as PRIMED (no wake event)")
    s.add_argument("--node", required=True)
    s.add_argument("--wake-event", default=None)
    s.set_defaults(func=cmd_prime)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
