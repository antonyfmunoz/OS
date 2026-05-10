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
import sys
from datetime import datetime, timezone

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.orchestrator.steps import ScriptWorkflowSpec, run_script_workflow

SCRIPT_PATH = "/opt/OS/scripts/scheduled/nightly_consolidation.sh"
IDEMPOTENCY_TTL_SECONDS = 23 * 3600  # 23h — never collides with tomorrow's run


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

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Dry-run invocations must not claim the real daily slot — they'd
    # lock out the real nightly consolidation. Key is distinct per mode.
    key_prefix = (
        "nightly_consolidation_dry" if args.dry_run else "nightly_consolidation"
    )
    spec = ScriptWorkflowSpec(
        name="nightly_consolidation",
        script_path=SCRIPT_PATH,
        description=(
            "nightly memory consolidation (close_day ritual, wiki promotion, "
            "summarization)" + (" [dry-run]" if args.dry_run else "")
        ),
        expected_output=(
            "END: exit code 0 in logs/nightly_consolidation.log, close_day "
            "ritual finished"
        ),
        idempotency_key=f"{key_prefix}:{today}",
        idempotency_ttl_seconds=IDEMPOTENCY_TTL_SECONDS,
        risk_level=args.risk,
        timeout=1800,
        script_args=["--dry-run"] if args.dry_run else [],
        reasoning=(
            "Route nightly consolidation through the Control Plane so the "
            "close_day ritual, wiki mutations, and LLM spend are captured "
            "with a full lifecycle trail and can be deferred when not "
            "pre-approved by the operator."
        ),
    )
    return run_script_workflow(spec, approve=args.approve)


if __name__ == "__main__":
    sys.exit(main())
