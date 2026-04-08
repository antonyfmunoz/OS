#!/usr/bin/env python3
"""deferred.py — operator CLI for the Control Plane deferred queue.

Commands:
    list                      show all currently deferred actions
    show <action_id>          print the full persisted action record
    approve <action_id>       approve + execute a deferred action (= resume)
    drop <action_id>          remove a deferred action without executing

Examples:
    python3 scripts/deferred.py list
    python3 scripts/deferred.py approve 0073bd45-...
    python3 scripts/deferred.py drop 0073bd45-...
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "/opt/OS")

from core.action_system.control_plane import (
    list_deferred,
    load_deferred,
    resume_action,
)
from core.action_system.deferred import delete_deferred


def cmd_list(_args: argparse.Namespace) -> int:
    rows = list_deferred()
    if not rows:
        print("No deferred actions.")
        return 0
    print(f"{'RISK':<7}{'TYPE':<16}{'AGENT':<20}{'ID':<38}DESCRIPTION")
    for r in rows:
        print(
            f"{(r['risk_level'] or '-'):<7}"
            f"{(r['type'] or '-'):<16}"
            f"{(r['source_agent'] or '-'):<20}"
            f"{(r['id'] or '-'):<38}"
            f"{r['description'] or ''}"
        )
    print(f"\n{len(rows)} deferred action(s).")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    try:
        action = load_deferred(args.action_id)
    except FileNotFoundError:
        print(f"No deferred action with id {args.action_id!r}", file=sys.stderr)
        return 2
    print(json.dumps(action.to_dict(), indent=2, default=str))
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    try:
        action = resume_action(args.action_id, consult_tme=args.consult_tme)
    except FileNotFoundError:
        print(f"No deferred action with id {args.action_id!r}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "id": action.id,
                "status": action.status,
                "result": action.result,
            },
            indent=2,
            default=str,
        )
    )
    return 0 if action.status == "executed" else 1


def cmd_drop(args: argparse.Namespace) -> int:
    removed = delete_deferred(args.action_id)
    print("removed" if removed else f"no deferred action with id {args.action_id!r}")
    return 0 if removed else 2


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List deferred actions").set_defaults(func=cmd_list)

    s = sub.add_parser("show", help="Show a deferred action's full record")
    s.add_argument("action_id")
    s.set_defaults(func=cmd_show)

    a = sub.add_parser("approve", help="Approve + execute a deferred action")
    a.add_argument("action_id")
    a.add_argument("--consult-tme", action="store_true")
    a.set_defaults(func=cmd_approve)

    d = sub.add_parser("drop", help="Remove a deferred action without executing")
    d.add_argument("action_id")
    d.set_defaults(func=cmd_drop)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
