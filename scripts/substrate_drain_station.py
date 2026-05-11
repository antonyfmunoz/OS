#!/usr/bin/env python3
"""
Operator entrypoint: drain one or more station inboxes once.

Runs the unified drain (events + results) and optionally reconciles recent
rituals so body_actions get their outcomes mirrored in-place.

Usage:
    python3 /opt/OS/scripts/substrate_drain_station.py --node antony-workstation
    python3 /opt/OS/scripts/substrate_drain_station.py --node a --node b
    python3 /opt/OS/scripts/substrate_drain_station.py --node a --reconcile
    python3 /opt/OS/scripts/substrate_drain_station.py --node a --reconcile-limit 10

Prints a JSON summary. Safe to run repeatedly. Intended for a lightweight
scheduler — this script does NOT loop. Exit code is non-zero only if an
ingestion error occurred (malformed entries do not count as errors).
"""

from __future__ import annotations

import argparse
import json
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.result_query import (  # noqa: E402
    latest_failed,
    node_health_summary,
    recent_open_close_summaries,
    ritual_outcomes_summary,
    station_readiness_report,
    stats as result_stats,
    unresolved_rituals,
)
from runtime.substrate.local_listener import listener_report  # noqa: E402
from runtime.substrate.ritual_reconciler import reconcile_recent  # noqa: E402
from runtime.substrate.station_drainer import drain_all  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Drain station inbox(es) once.")
    parser.add_argument(
        "--node",
        action="append",
        required=True,
        help="Node id to drain. Repeatable.",
    )
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="After draining, reconcile recent rituals against ingested results.",
    )
    parser.add_argument(
        "--reconcile-limit",
        type=int,
        default=20,
        help="How many recent rituals to reconcile when --reconcile is set.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Append a lightweight report (result store stats, recent failures, "
        "recent ritual outcomes) to the output.",
    )
    args = parser.parse_args()

    summary: dict = {"drains": [], "reconcile": None}
    exit_code = 0

    for node_id in args.node:
        stats = drain_all(node_id)
        summary["drains"].append(stats.as_dict())
        if stats.events.errors or stats.results.errors:
            exit_code = 1

    if args.reconcile:
        rs = reconcile_recent(limit=args.reconcile_limit)
        summary["reconcile"] = [s.as_dict() for s in rs]

    if args.report:
        summary["report"] = {
            "result_store": result_stats(),
            "latest_failed": latest_failed(limit=10),
            "ritual_outcomes": ritual_outcomes_summary(limit=5),
            "unresolved_rituals": unresolved_rituals(limit=10),
            "nodes": [node_health_summary(n) for n in args.node],
            # New: per-node readiness + recommended scene from the policy layer.
            "readiness": [station_readiness_report(n) for n in args.node],
            # New: most recent open_day/close_day rituals with summaries.
            "recent_rituals": recent_open_close_summaries(limit=5),
            # New: bounded local-listener activity (recent triggers + last activation).
            "local_listener": {
                n: listener_report(node_id=n, limit=5) for n in args.node
            },
        }

    print(json.dumps(summary, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
