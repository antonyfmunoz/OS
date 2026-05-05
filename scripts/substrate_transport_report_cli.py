#!/usr/bin/env python3
"""
Unified transport report CLI.

Subcommand:
  unified   Print the cross-transport unified report (JSON).

Joins:
  - workstation PTT readiness + recent real-capture validations
  - Discord voice transport status (transcript-only by default)
  - shared voice/audio/operator state for the focus node
  - per-source transcript counts across both transports

Usage examples:
    python3 scripts/substrate_transport_report_cli.py unified

    python3 scripts/substrate_transport_report_cli.py unified \\
        --node antony-workstation --limit 10

    python3 scripts/substrate_transport_report_cli.py unified \\
        --node antony-workstation \\
        --discord-guild 1234567890 --discord-channel 9876543210
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "/opt/OS")


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _print_summary(report: dict) -> None:
    """Print a human-readable operator summary after the JSON payload."""
    print("")
    print("=== operator summary ===")

    print("Attached meeting sources:")
    meeting = report.get("meeting_transport") or {}
    attached = meeting.get("attached_sources") if isinstance(meeting, dict) else None
    if attached:
        for src in attached:
            if not isinstance(src, dict):
                continue
            name = src.get("name", "?")
            provider = src.get("provider", "?")
            pump_count = src.get("pump_count", 0)
            last_status = src.get("last_status", "-")
            print(
                f"  - {name} ({provider}) pumped={pump_count} last_status={last_status}"
            )
    else:
        print("  (none)")

    print("Playback aggregates:")
    agg = None
    if isinstance(report, dict):
        agg = report.get("playback_aggregates")
    if not isinstance(agg, dict):
        print("  (none)")
        return

    by_status = agg.get("by_status")
    if by_status is None:
        print("  by_status: (none)")
    else:
        print(f"  by_status: {by_status}")

    by_transport = agg.get("by_transport") if isinstance(agg, dict) else None
    if not isinstance(by_transport, dict):
        by_transport = {}
    for label in ("discord", "meeting"):
        block = by_transport.get(label)
        if not isinstance(block, dict):
            print(f"  {label}: (none)")
            continue
        mode = block.get("mode")
        attached_f = block.get("attached")
        enabled = block.get("enabled")
        attempts = block.get("attempt_count", block.get("attempts"))
        print(
            f"  {label}: mode={mode} attached={attached_f} "
            f"enabled={enabled} attempts={attempts}"
        )


def cmd_unified(args: argparse.Namespace) -> int:
    from eos_ai.substrate.transport_report import unified_transport_report

    payload = unified_transport_report(
        node_id=args.node,
        transcript_limit=args.limit,
        discord_guild_id=args.discord_guild,
        discord_channel_id=args.discord_channel,
        meeting_platform=args.meeting_platform,
        meeting_id=args.meeting_id,
    )
    _print_json(payload)
    if getattr(args, "summary", False):
        _print_summary(payload if isinstance(payload, dict) else {})
    return 0


def _add_unified_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--node", default=None, help="focus node (workstation node id)")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--discord-guild", default=None)
    p.add_argument("--discord-channel", default=None)
    p.add_argument(
        "--meeting-platform",
        default=None,
        help="meeting platform (google_meet|zoom|teams|generic_meeting)",
    )
    p.add_argument("--meeting-id", default=None)
    p.add_argument(
        "--summary",
        action="store_true",
        help="print a human-readable operator summary after the JSON payload",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    # Top-level unified args so the CLI can be invoked without the
    # `unified` subcommand (backwards compatible — the subcommand still works).
    _add_unified_args(p)
    p.set_defaults(func=cmd_unified)
    sub = p.add_subparsers(dest="cmd", required=False)

    u = sub.add_parser("unified", help="print the cross-transport unified report")
    _add_unified_args(u)
    u.set_defaults(func=cmd_unified)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
