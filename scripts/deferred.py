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
from core.action_system import idempotency
from core.action_system.deferred_status import (
    DEFAULT_STALE_HOURS,
    VALID_STATUSES,
    clear_status,
    list_overdue_snoozed,
    mark_stale_over_threshold,
    read_status,
    wake_due_snoozed,
    write_status,
)


def cmd_list(args: argparse.Namespace) -> int:
    rows = list_deferred()
    if getattr(args, "overdue_snoozed", False):
        overdue = set(list_overdue_snoozed())
        rows = [r for r in rows if (r.get("id") or "") in overdue]
    if not rows:
        print("No deferred actions.")
        return 0
    print(f"{'STATUS':<13}{'RISK':<10}{'TYPE':<16}{'AGENT':<20}{'ID':<38}DESCRIPTION")
    for r in rows:
        st = read_status(r["id"] or "").status
        print(
            f"{st:<13}"
            f"{(r['risk_level'] or '-'):<10}"
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
    clear_status(args.action_id)
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
    clear_status(args.action_id)
    print("removed" if removed else f"no deferred action with id {args.action_id!r}")
    return 0 if removed else 2


def cmd_status(args: argparse.Namespace) -> int:
    """Set or read the sidecar status for a deferred action."""
    if args.set:
        try:
            rec = write_status(
                args.action_id, args.set, note=args.note or "", snoozed_until=args.until
            )
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        print(json.dumps(rec.to_dict(), indent=2))
        return 0
    rec = read_status(args.action_id)
    print(json.dumps(rec.to_dict(), indent=2))
    return 0


def cmd_stale_check(args: argparse.Namespace) -> int:
    """Scan the queue and mark every pending action older than threshold as stale."""
    marked = mark_stale_over_threshold(threshold_hours=args.older_than)
    print(
        json.dumps(
            {"threshold_hours": args.older_than, "marked_stale": marked},
            indent=2,
        )
    )
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    """Delete deferred actions that are marked stale (or past threshold).

    Two modes:
      --marked-only (default): only prunes actions whose sidecar says `stale`
      --auto-mark: first runs stale-check with --older-than, then prunes
    """
    if args.auto_mark:
        mark_stale_over_threshold(threshold_hours=args.older_than)

    rows = list_deferred()
    pruned: list[str] = []
    for r in rows:
        action_id = r.get("id") or ""
        if not action_id:
            continue
        if read_status(action_id).status != "stale":
            continue
        if args.dry_run:
            pruned.append(action_id)
            continue
        delete_deferred(action_id)
        clear_status(action_id)
        pruned.append(action_id)

    print(
        json.dumps(
            {
                "dry_run": args.dry_run,
                "older_than_hours": args.older_than,
                "pruned_count": len(pruned),
                "pruned_ids": pruned,
            },
            indent=2,
        )
    )
    return 0


def cmd_wake(args: argparse.Namespace) -> int:
    """Promote snoozed deferred actions whose wake time has passed."""
    if args.dry_run:
        due = list_overdue_snoozed()
        print(
            json.dumps(
                {"dry_run": True, "would_wake": due, "count": len(due)},
                indent=2,
            )
        )
        return 0
    woken = wake_due_snoozed()
    print(json.dumps({"woken": woken, "count": len(woken)}, indent=2))
    return 0


def _render_sentinel(s: idempotency.Sentinel) -> dict:
    return {
        "key": s.key,
        "sha": s.key and __import__("hashlib").sha1(s.key.encode()).hexdigest(),
        "action_id": s.action_id,
        "status": s.status,
        "created_at": s.created_at,
        "completed_at": s.completed_at,
        "ttl_seconds": s.ttl_seconds,
        "expired": s.is_expired(),
    }


def cmd_idem_list(args: argparse.Namespace) -> int:
    rows = idempotency.list_all()
    if args.expired:
        rows = [s for s in rows if s.is_expired()]
    if not rows:
        print("No idempotency sentinels.")
        return 0
    print(f"{'STATUS':<11}{'TTL':<8}{'EXPIRED':<9}{'ACTION_ID':<38}KEY")
    for s in rows:
        print(
            f"{s.status:<11}"
            f"{str(s.ttl_seconds):<8}"
            f"{('yes' if s.is_expired() else 'no'):<9}"
            f"{(s.action_id or '-'):<38}"
            f"{s.key}"
        )
    print(f"\n{len(rows)} sentinel(s).")
    return 0


def cmd_idem_show(args: argparse.Namespace) -> int:
    s = idempotency.find(args.key)
    if s is None:
        print(f"No sentinel for {args.key!r}", file=sys.stderr)
        return 2
    print(json.dumps(_render_sentinel(s), indent=2))
    return 0


def cmd_idem_clear(args: argparse.Namespace) -> int:
    s = idempotency.find(args.key)
    if s is None:
        print(f"No sentinel for {args.key!r}", file=sys.stderr)
        return 2
    removed = idempotency.clear(s.key)
    print(json.dumps({"cleared": removed, "key": s.key}, indent=2))
    return 0 if removed else 2


def cmd_idem_prune(_args: argparse.Namespace) -> int:
    cleared = idempotency.prune_expired()
    print(json.dumps({"pruned_count": len(cleared), "keys": cleared}, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    ls = sub.add_parser("list", help="List deferred actions")
    ls.add_argument(
        "--overdue-snoozed",
        action="store_true",
        dest="overdue_snoozed",
        help="Only show snoozed actions whose snoozed_until has passed",
    )
    ls.set_defaults(func=cmd_list)

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

    st = sub.add_parser("status", help="Read or set the sidecar status of an action")
    st.add_argument("action_id")
    st.add_argument(
        "--set",
        choices=VALID_STATUSES,
        help="Set the status (pending|acknowledged|snoozed|stale)",
    )
    st.add_argument("--note", default="", help="Optional note to attach")
    st.add_argument("--until", default=None, help="ISO timestamp for snoozed_until")
    st.set_defaults(func=cmd_status)

    sc = sub.add_parser(
        "stale-check",
        help="Mark every pending deferred action older than N hours as stale",
    )
    sc.add_argument(
        "--older-than",
        type=int,
        default=DEFAULT_STALE_HOURS,
        help=f"Threshold in hours (default {DEFAULT_STALE_HOURS})",
    )
    sc.set_defaults(func=cmd_stale_check)

    pr = sub.add_parser("prune", help="Delete deferred actions marked stale")
    pr.add_argument(
        "--older-than",
        type=int,
        default=DEFAULT_STALE_HOURS,
        help="Threshold for --auto-mark (default 72)",
    )
    pr.add_argument(
        "--auto-mark",
        action="store_true",
        help="Run stale-check before pruning",
    )
    pr.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be pruned without deleting",
    )
    pr.set_defaults(func=cmd_prune)

    wk = sub.add_parser(
        "wake",
        help="Promote snoozed actions whose snoozed_until has passed to pending",
    )
    wk.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be woken without mutating sidecars",
    )
    wk.set_defaults(func=cmd_wake)

    ip = sub.add_parser("idempotency", help="Operator commands for the idempotency store")
    ipsub = ip.add_subparsers(dest="idem_cmd", required=True)

    ipl = ipsub.add_parser("list", help="List sentinels")
    ipl.add_argument("--expired", action="store_true", help="Only expired sentinels")
    ipl.set_defaults(func=cmd_idem_list)

    ips = ipsub.add_parser("show", help="Show one sentinel by key or sha prefix")
    ips.add_argument("key")
    ips.set_defaults(func=cmd_idem_show)

    ipc = ipsub.add_parser("clear", help="Delete a sentinel by key or sha prefix")
    ipc.add_argument("key")
    ipc.set_defaults(func=cmd_idem_clear)

    ipp = ipsub.add_parser("prune", help="Delete every expired sentinel")
    ipp.set_defaults(func=cmd_idem_prune)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
