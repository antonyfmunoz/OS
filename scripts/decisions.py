#!/usr/bin/env python3
"""decisions.py — operator CLI for the Control Plane decision log.

Reads `logs/decisions/YYYY-MM-DD-decisions.jsonl` files append-only.
This tool is READ-ONLY and imports nothing from `core.action_system` —
if the Control Plane is broken, this tool still works. Matching the
discipline of `scripts/workers/discord_approval_worker.py`.

Commands:
    list                              recent decisions across days
    show <decision_id>                print one full record
    for-action <action_id>            every decision for one action

Filters on `list`:
    --limit N             default 20
    --agent NAME          substring match on source_agent
    --context SUBSTR      substring match on context
    --since YYYY-MM-DD    lower bound (default: 7 days ago)
    --today               restrict to UTC today
    --json                emit JSON array instead of table

Examples:
    python3 /opt/OS/scripts/decisions.py list
    python3 /opt/OS/scripts/decisions.py list --agent cron --limit 50
    python3 /opt/OS/scripts/decisions.py list --context morning_prep
    python3 /opt/OS/scripts/decisions.py show 25c42826-...-...
    python3 /opt/OS/scripts/decisions.py for-action 4f3e9d01-...-...
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

DECISION_LOG_DIR = "/opt/OS/logs/decisions"


def _iter_log_files(since: datetime) -> list[str]:
    if not os.path.isdir(DECISION_LOG_DIR):
        return []
    start = since.date()
    out: list[str] = []
    for name in sorted(os.listdir(DECISION_LOG_DIR)):
        if not name.endswith("-decisions.jsonl"):
            continue
        # Format: YYYY-MM-DD-decisions.jsonl
        try:
            day = datetime.strptime(name[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if day >= start:
            out.append(os.path.join(DECISION_LOG_DIR, name))
    return out


def _iter_records(paths: Iterable[str]) -> Iterable[dict[str, Any]]:
    for path in paths:
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue


def _short(s: str | None, n: int = 8) -> str:
    if not s:
        return "-"
    return s[:n]


def _truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def cmd_list(args: argparse.Namespace) -> int:
    if args.today:
        since = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif args.since:
        try:
            since = datetime.strptime(args.since, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            print(
                f"invalid --since {args.since!r}; expected YYYY-MM-DD",
                file=sys.stderr,
            )
            return 2
    else:
        since = datetime.now(timezone.utc) - timedelta(days=7)

    records: list[dict[str, Any]] = []
    for rec in _iter_records(_iter_log_files(since)):
        if args.agent and args.agent not in (rec.get("source_agent") or ""):
            continue
        if args.context and args.context not in (rec.get("context") or ""):
            continue
        records.append(rec)

    records.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
    records = records[: args.limit]

    if args.json:
        print(json.dumps(records, indent=2, default=str))
        return 0

    if not records:
        print("No decisions match filter.")
        return 0

    print(
        f"{'TIMESTAMP':<27}{'AGENT':<20}{'CONTEXT':<42}{'ACTION':<10}DECISION"
    )
    for r in records:
        print(
            f"{(r.get('timestamp') or '-')[:26]:<27}"
            f"{_truncate(r.get('source_agent') or '-', 19):<20}"
            f"{_truncate(r.get('context') or '-', 41):<42}"
            f"{_short(r.get('related_action_id')):<10}"
            f"{_short(r.get('decision_id'))}"
        )
    print(f"\n{len(records)} decision(s).")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=90)
    for rec in _iter_records(_iter_log_files(since)):
        if rec.get("decision_id") == args.decision_id:
            print(json.dumps(rec, indent=2, default=str))
            return 0
    print(f"No decision with id {args.decision_id!r}", file=sys.stderr)
    return 2


def cmd_for_action(args: argparse.Namespace) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=90)
    hits = [
        rec
        for rec in _iter_records(_iter_log_files(since))
        if rec.get("related_action_id") == args.action_id
    ]
    hits.sort(key=lambda r: r.get("timestamp") or "")
    if not hits:
        print(f"No decisions for action {args.action_id!r}")
        return 0
    if args.json:
        print(json.dumps(hits, indent=2, default=str))
        return 0
    for rec in hits:
        print(
            f"[{rec.get('timestamp')}] {rec.get('source_agent')} "
            f"— {rec.get('chosen_option')}: {rec.get('reasoning')}"
        )
    print(f"\n{len(hits)} decision(s) for action {args.action_id}.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    ls = sub.add_parser("list", help="List recent decisions")
    ls.add_argument("--limit", type=int, default=20)
    ls.add_argument("--agent", default=None, help="Filter by source_agent substring")
    ls.add_argument("--context", default=None, help="Filter by context substring")
    ls.add_argument("--since", default=None, help="Lower bound YYYY-MM-DD")
    ls.add_argument("--today", action="store_true", help="Restrict to UTC today")
    ls.add_argument("--json", action="store_true", help="Emit JSON array")
    ls.set_defaults(func=cmd_list)

    sh = sub.add_parser("show", help="Show a decision record by decision_id")
    sh.add_argument("decision_id")
    sh.set_defaults(func=cmd_show)

    fa = sub.add_parser("for-action", help="Show every decision for one action_id")
    fa.add_argument("action_id")
    fa.add_argument("--json", action="store_true")
    fa.set_defaults(func=cmd_for_action)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
