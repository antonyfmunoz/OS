#!/usr/bin/env python3
"""Orchestrator loop runner.

Usage:
    python3 scripts/orchestrator_loop.py              # one cycle, print JSON report
    python3 scripts/orchestrator_loop.py --cycles 3   # run N cycles with sleep
    python3 scripts/orchestrator_loop.py --forever    # run until killed
    python3 scripts/orchestrator_loop.py --interval 60

The loop itself is deterministic: signals → stale deferred → failures.
No infinite retries. No mutation without going through run_action().
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "/opt/OS")

from core.orchestrator.loop import LoopConfig, run_cycle, run_forever  # noqa: E402
from core.orchestrator.orchestrator import default_orchestrator  # noqa: E402
from core.orchestrator.workflows import register_default_workflows  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="EOS Orchestrator loop")
    parser.add_argument(
        "--forever",
        action="store_true",
        help="Run until killed (dev use only — prefer cron/systemd).",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=1,
        help="Number of cycles to run when not using --forever (default: 1).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Sleep between cycles in seconds (default: 300).",
    )
    parser.add_argument(
        "--stale-deferred-seconds",
        type=int,
        default=6 * 3600,
        help="Threshold for marking a deferred action as stale.",
    )
    args = parser.parse_args()

    orch = default_orchestrator()
    register_default_workflows(orch)

    config = LoopConfig(
        stale_deferred_seconds=args.stale_deferred_seconds,
        interval_seconds=args.interval,
    )

    if args.forever:
        run_forever(orch=orch, config=config)
        return 0

    for _ in range(max(1, args.cycles)):
        report = run_cycle(orch=orch, config=config)
        print(json.dumps(report.to_dict(), default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
