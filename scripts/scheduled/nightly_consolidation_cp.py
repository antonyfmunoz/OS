#!/usr/bin/env python3
"""nightly_consolidation_cp.py — Control Plane wrapper for nightly_consolidation.sh.

Second real workflow routed through `core.action_system.run_action`.
Mirrors the shape of `morning_prep_cp.py` — this is deliberate, since
part of Phase 3's goal is proving the migration pattern is boringly
repeatable.

Why medium risk:
    nightly_consolidation.sh runs the memory pipeline: summarises
    conversations via an LLM, promotes content into the wiki, and
    mutates substrate ritual state (close_day start/finish). It
    consumes provider budget and writes persistent knowledge. Not
    destructive, but high enough impact that operators should see
    deferred runs before approving.

Why this workflow (instead of weekly_review or nightly_maintenance):
    - bounded: single cron line, ~70 lines of bash
    - stateful: mutates wiki + substrate rituals (unlike the read-heavy
      weekly_review)
    - gated: already has a provider_health preflight, so failures are
      informative rather than catastrophic
    - reversible: the underlying .sh is untouched, so reverting the
      cron line restores the pre-migration behavior exactly

Usage:
    # Cron-style (auto-approves — operator has pre-authorized):
    python3 /opt/OS/scripts/scheduled/nightly_consolidation_cp.py --approve

    # Manual dry invocation (defers, operator resumes via scripts/deferred.py):
    python3 /opt/OS/scripts/scheduled/nightly_consolidation_cp.py

Cron migration:
    # OLD:
    # 0 2 * * * bash /opt/OS/scripts/scheduled/nightly_consolidation.sh
    # NEW:
    # 0 2 * * * python3 /opt/OS/scripts/scheduled/nightly_consolidation_cp.py --approve \
    #           >> /opt/OS/logs/nightly_consolidation_cp.log 2>&1
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "/opt/OS")

from core.action_system.control_plane import log_decision, run_action

SCRIPT_PATH = "/opt/OS/scripts/scheduled/nightly_consolidation.sh"


def main() -> int:
    p = argparse.ArgumentParser(
        description="Control Plane wrapper for nightly consolidation"
    )
    p.add_argument(
        "--approve",
        action="store_true",
        help="Grant explicit approval (for cron / trusted automation)",
    )
    p.add_argument(
        "--risk",
        default="medium",
        choices=("low", "medium", "high"),
        help="Override risk classification (default: medium)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Pass --dry-run through to the underlying .sh",
    )
    args = p.parse_args()

    log_decision(
        context="scheduled invocation of nightly_consolidation",
        options_considered=[
            "bash nightly_consolidation.sh direct",
            "python wrapper via Control Plane",
        ],
        chosen_option="python wrapper via Control Plane",
        reasoning=(
            "Route nightly consolidation through the Control Plane so the "
            "close_day ritual, wiki mutations, and LLM spend are captured "
            "with a full lifecycle trail and can be deferred when not "
            "pre-approved by the operator."
        ),
        source_agent="cron",
    )

    script_args = ["--dry-run"] if args.dry_run else []

    action = run_action(
        type="run_script",
        description=(
            "nightly memory consolidation (close_day ritual, wiki promotion, "
            "summarization)" + (" [dry-run]" if args.dry_run else "")
        ),
        inputs={"path": SCRIPT_PATH, "args": script_args, "timeout": 1800},
        risk_level=args.risk,
        source_agent="cron",
        explicit_approval=args.approve,
        expected_output=(
            "END: exit code 0 in logs/nightly_consolidation.log, close_day "
            "ritual finished"
        ),
    )

    print(
        json.dumps(
            {
                "id": action.id,
                "status": action.status,
                "validation": action.validation,
                "approval": action.approval,
                "result": {
                    k: v
                    for k, v in action.result.items()
                    if k
                    in ("ok", "returncode", "stderr", "deferred_path", "notification")
                },
            },
            indent=2,
            default=str,
        )
    )

    if action.status == "executed":
        return 0
    if action.status == "validated":
        # Deferred — a normal outcome when the operator has not pre-approved.
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
