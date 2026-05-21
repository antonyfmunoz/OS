#!/usr/bin/env python3
"""
Operator CLI for EOS substrate — Operator Interface Layer v1.

Human-driven query + controlled-command surface over linkage_snapshot.
Deterministic. Bounded. No automation.

Usage:
    substrate_operator_cli.py summary    --node NODE [--meeting-id MID]
    substrate_operator_cli.py actionable --node NODE [--meeting-id MID]
                                         [--ready-only] [--blocked-only]
                                         [--owner OWNER] [--priority P]
    substrate_operator_cli.py top        --node NODE [--meeting-id MID]
    substrate_operator_cli.py blocked    --node NODE [--meeting-id MID]
    substrate_operator_cli.py owners     --node NODE [--meeting-id MID]
    substrate_operator_cli.py refresh    --node NODE [--meeting-id MID]
    substrate_operator_cli.py mark-resolved --node NODE --meeting-id MID
                                            [--text-contains TXT]
                                            [--owner OWNER]
    substrate_operator_cli.py assign-owner  --node NODE --meeting-id MID
                                            --text-contains TXT --new-owner O
                                            [--owner-confidence high|low]
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.substrate import operator_interface as oi  # noqa: E402
from umh.runtime_engine.substrate import control_bridge as cb  # noqa: E402
from umh.runtime_engine.substrate import control_commands as cc  # noqa: E402
from umh.runtime_engine.substrate import local_executor as lx  # noqa: E402


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str, sort_keys=True))


def _add_common(p: argparse.ArgumentParser, *, require_meeting: bool = False) -> None:
    p.add_argument("--node", required=True, help="node_id")
    p.add_argument(
        "--meeting-id",
        required=require_meeting,
        default=None,
        help="meeting_id (required for commands that mutate state)",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="substrate_operator_cli",
        description="Operator Interface Layer v1 — query + controlled commands",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_sum = sub.add_parser("summary", help="high-level snapshot summary")
    _add_common(p_sum)

    p_act = sub.add_parser("actionable", help="list actionable items")
    _add_common(p_act)
    p_act.add_argument("--ready-only", action="store_true")
    p_act.add_argument("--blocked-only", action="store_true")
    p_act.add_argument("--owner", default=None)
    p_act.add_argument("--priority", choices=["low", "medium", "high"], default=None)

    p_top = sub.add_parser("top", help="highest-priority actionable")
    _add_common(p_top)

    p_blk = sub.add_parser("blocked", help="blocked actionable items")
    _add_common(p_blk)

    p_own = sub.add_parser("owners", help="owner distribution")
    _add_common(p_own)

    p_ref = sub.add_parser("refresh", help="re-run snapshot (no persistence)")
    _add_common(p_ref)

    p_mr = sub.add_parser("mark-resolved", help="resolve commitments (explicit)")
    _add_common(p_mr, require_meeting=True)
    p_mr.add_argument("--text-contains", default=None)
    p_mr.add_argument("--owner", default=None)

    p_ao = sub.add_parser("assign-owner", help="reassign owner on commitments")
    _add_common(p_ao, require_meeting=True)
    p_ao.add_argument("--text-contains", required=True)
    p_ao.add_argument("--new-owner", required=True)
    p_ao.add_argument(
        "--owner-confidence", choices=["low", "high"], default="high"
    )

    # ── Control Layer v1 commands ────────────────────────────────────────
    p_rs = sub.add_parser("run-shell", help="enqueue a whitelisted shell command")
    p_rs.add_argument("--node", default="local")
    p_rs.add_argument("--cmd", required=True, help='e.g. "echo hello"')
    p_rs.add_argument("--issued-by", default="operator")

    p_wf = sub.add_parser("write-file", help="enqueue a sandbox file write")
    p_wf.add_argument("--node", default="local")
    p_wf.add_argument("--path", required=True, help="path under sandbox/")
    p_wf.add_argument("--content", required=True)
    p_wf.add_argument("--issued-by", default="operator")

    p_rp = sub.add_parser("run-python", help="enqueue a sandboxed python snippet")
    p_rp.add_argument("--node", default="local")
    p_rp.add_argument("--code", required=True)
    p_rp.add_argument("--issued-by", default="operator")

    p_pl = sub.add_parser(
        "process-local", help="explicitly drain pending commands for a node"
    )
    p_pl.add_argument("--node", default="local")

    p_qd = sub.add_parser("queue-depth", help="inspect pending queue depth")
    p_qd.add_argument("--node", default="local")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    cmd = args.command

    if cmd == "summary":
        _print_json(oi.summarize(args.node, args.meeting_id))
        return 0

    if cmd == "actionable":
        if args.ready_only and args.blocked_only:
            print("error: --ready-only and --blocked-only are mutually exclusive",
                  file=sys.stderr)
            return 2
        if args.ready_only:
            items = oi.get_ready_items(args.node, args.meeting_id)
        elif args.blocked_only:
            items = oi.get_blocked_items(args.node, args.meeting_id)
        else:
            filters: dict = {}
            if args.owner is not None:
                filters["owner"] = args.owner
            if args.priority is not None:
                filters["priority"] = args.priority
            items = oi.get_actionable_items(
                args.node, args.meeting_id, filters=filters or None
            )
        # Apply owner/priority filters to ready/blocked lists too
        if args.ready_only or args.blocked_only:
            if args.owner is not None:
                items = [it for it in items if (it.get("owner") or "") == args.owner]
            if args.priority is not None:
                items = [it for it in items if it.get("priority") == args.priority]
        _print_json({"count": len(items), "items": items})
        return 0

    if cmd == "top":
        _print_json({"top": oi.get_top_actionable(args.node, args.meeting_id)})
        return 0

    if cmd == "blocked":
        items = oi.get_blocked_items(args.node, args.meeting_id)
        _print_json({"count": len(items), "items": items})
        return 0

    if cmd == "owners":
        _print_json(oi.get_owner_breakdown(args.node, args.meeting_id))
        return 0

    if cmd == "refresh":
        snap = oi.refresh(args.node, args.meeting_id)
        # Keep refresh output compact — just the operator summary projection
        _print_json(oi.summarize(args.node, args.meeting_id))
        return 0

    if cmd == "mark-resolved":
        result = oi.mark_resolved(
            args.node,
            args.meeting_id,
            text_contains=args.text_contains,
            owner=args.owner,
        )
        _print_json(result)
        return 0

    if cmd == "assign-owner":
        result = oi.assign_owner(
            args.node,
            args.meeting_id,
            text_contains=args.text_contains,
            new_owner=args.new_owner,
            owner_confidence=args.owner_confidence,
        )
        _print_json(result)
        return 0

    if cmd in ("run-shell", "write-file", "run-python"):
        action_map = {
            "run-shell": ("run_shell", lambda a: {"cmd": a.cmd}),
            "write-file": ("write_file", lambda a: {"path": a.path, "content": a.content}),
            "run-python": ("run_python", lambda a: {"code": a.code}),
        }
        action, build_payload = action_map[cmd]
        envelope = cc.make_command(
            action,
            build_payload(args),
            issued_by=args.issued_by,
            node_id=args.node,
        )
        result = cb.send_command(envelope)
        _print_json(result)
        return 0 if result.get("ok") else 1

    if cmd == "process-local":
        _print_json(lx.process_pending(args.node))
        return 0

    if cmd == "queue-depth":
        _print_json({"node_id": args.node, "depth": cb.queue_depth(args.node)})
        return 0

    print(f"error: unknown command {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
