#!/usr/bin/env python3
"""Tool Mastery Manager — CLI.

Thin wrapper over the `core.tool_mastery_manager` package. The package
is the source of truth; this file is deliberately shallow so changing
Manager behaviour never requires CLI surgery.

Commands
--------
    ensure <tool>           Discover → classify → scaffold-if-missing →
                            queue research/refresh/repair via Control Plane.
    status <tool>           Print coverage report for one tool.
    scan                    Print coverage for every discovered tool.
    backlog                 Write + print the prioritised worklist of
                            non-READY tools.
    bootstrap               Run `backlog` then ensure_mastery on each
                            non-READY tool. Use --dry-run first.
    refresh-stale           Queue refresh actions for all STALE tools.

Exit codes
----------
    0   success / nothing to do
    1   at least one tool needed work and was queued
    2   bad invocation

All commands accept `--json` for machine-readable output.

Examples
--------
    python3 scripts/tool_mastery_manager.py status notion
    python3 scripts/tool_mastery_manager.py scan --json
    python3 scripts/tool_mastery_manager.py ensure slack
    python3 scripts/tool_mastery_manager.py backlog
    python3 scripts/tool_mastery_manager.py bootstrap --dry-run
    python3 scripts/tool_mastery_manager.py refresh-stale --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from substrate.composition.mastery.management.backlog import backlog_report, bootstrap  # noqa: E402
from substrate.composition.mastery.management.coverage import evaluate_coverage  # noqa: E402
from substrate.composition.mastery.management.ensure import ensure_mastery  # noqa: E402
from substrate.composition.mastery.management.maintenance import (  # noqa: E402
    audit_all,
    refresh_stale,
)
from substrate.composition.mastery.management.models import CoverageStatus  # noqa: E402


def _emit(payload: dict | list, as_json: bool, fallback_lines: list[str]) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        for line in fallback_lines:
            print(line)


def cmd_ensure(args: argparse.Namespace) -> int:
    res = ensure_mastery(args.tool, dry_run=args.dry_run)
    payload = res.to_dict()
    lines = [
        f"tool:           {res.slug}",
        f"initial_status: {res.initial_status.value}",
        f"final_status:   {res.final_status.value}",
        f"scaffolded:     {res.scaffolded}",
        f"action_id:      {res.action_id or '—'}",
        f"action_status:  {res.action_status or '—'}",
    ]
    if res.plan:
        lines.append(f"planned:        {res.plan.work_type} via {res.plan.script_path}")
    for n in res.notes:
        lines.append(f"note:           {n}")
    _emit(payload, args.json, lines)
    return 0 if res.final_status is CoverageStatus.READY else 1


def cmd_status(args: argparse.Namespace) -> int:
    report = evaluate_coverage(args.tool)
    lines = [
        f"tool:            {report.slug}",
        f"status:          {report.status.value}",
        f"exists_on_disk:  {report.exists_on_disk}",
        f"staleness:       {report.staleness_status or '—'}",
        f"age_days:        {report.age_days if report.age_days is not None else '—'}",
        f"last_researched: {report.last_researched or '—'}",
        f"speed_category:  {report.speed_category or '—'}",
    ]
    if report.reasons:
        lines.append("reasons:")
        for r in report.reasons:
            lines.append(f"  - {r}")
    if report.verifier_failures:
        lines.append(f"verifier_failures ({len(report.verifier_failures)}):")
        for f in report.verifier_failures[:10]:
            lines.append(f"  - {f}")
    if report.verifier_warnings:
        lines.append(f"verifier_warnings ({len(report.verifier_warnings)}):")
        for w in report.verifier_warnings[:10]:
            lines.append(f"  ~ {w}")
    _emit(report.to_dict(), args.json, lines)
    return 0 if report.status is CoverageStatus.READY else 1


def cmd_scan(args: argparse.Namespace) -> int:
    snap = audit_all()
    lines = [
        f"total discovered: {snap['total']}",
        "counts: " + ", ".join(f"{k}={v}" for k, v in sorted(snap["counts"].items())),
    ]
    # Show only non-ready in text mode to stay readable
    for entry in snap["reports"]:
        if entry["coverage"]["status"] == "ready":
            continue
        sources = ",".join(entry["tool"]["sources"])
        lines.append(
            f"  [{entry['coverage']['status']:7s}] {entry['tool']['slug']:30s} "
            f"sources={sources}"
        )
    _emit(snap, args.json, lines)
    needs_work = sum(v for k, v in snap["counts"].items() if k != "ready")
    return 0 if needs_work == 0 else 1


def cmd_backlog(args: argparse.Namespace) -> int:
    report = backlog_report(write_artifacts=not args.no_write)
    lines = [
        f"backlog size: {report['total']}",
        "counts: " + ", ".join(f"{k}={v}" for k, v in sorted(report["counts"].items())),
    ]
    for entry in report["entries"]:
        sources = ",".join(entry["tool"]["sources"])
        reason = entry["coverage"]["reasons"][0] if entry["coverage"]["reasons"] else ""
        lines.append(
            f"  [{entry['coverage']['status']:7s}] {entry['tool']['slug']:30s} "
            f"sources={sources}  {reason[:60]}"
        )
    if report["artifacts"]:
        lines.append(f"artifacts: md={report['artifacts']['md']}")
        lines.append(f"           json={report['artifacts']['json']}")
    _emit(report, args.json, lines)
    return 0 if report["total"] == 0 else 1


def cmd_bootstrap(args: argparse.Namespace) -> int:
    result = bootstrap(dry_run=args.dry_run)
    lines = [
        f"considered: {result['total_considered']}",
        f"dry_run:    {result['dry_run']}",
        f"queued:     {result['queued']}",
        f"scaffolded: {result['scaffolded']}",
        f"artifact:   {result['artifact']}",
    ]
    for r in result["results"][:20]:
        lines.append(
            f"  {r['slug']:30s} {r['initial_status']:8s} → {r['final_status']:8s} "
            f"action={r['action_status'] or '—'}"
        )
    if len(result["results"]) > 20:
        lines.append(f"  ... +{len(result['results']) - 20} more")
    _emit(result, args.json, lines)
    return 0 if result["total_considered"] == 0 else 1


def cmd_refresh_stale(args: argparse.Namespace) -> int:
    results = refresh_stale(dry_run=args.dry_run)
    lines = [f"refreshed: {len(results)}"]
    for r in results:
        lines.append(
            f"  {r['slug']:30s} → action={r['action_status'] or '—'}"
        )
    _emit(results, args.json, lines)
    return 0 if not results else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", action="store_true", help="emit JSON output")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ensure", help="ensure mastery for a tool")
    p.add_argument("tool")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_ensure)

    p = sub.add_parser("status", help="coverage report for one tool")
    p.add_argument("tool")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("scan", help="coverage report for every discovered tool")
    p.set_defaults(fn=cmd_scan)

    p = sub.add_parser("backlog", help="prioritised worklist of non-ready tools")
    p.add_argument("--no-write", action="store_true", help="skip artifact write")
    p.set_defaults(fn=cmd_backlog)

    p = sub.add_parser("bootstrap", help="run backlog + ensure_mastery on each")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_bootstrap)

    p = sub.add_parser("refresh-stale", help="queue refresh action for stale tools")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_refresh_stale)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
