#!/usr/bin/env python3
"""weekly_review_cp.py — Control Plane wrapper for weekly_review.sh.

Third workflow routed through `core.action_system.run_action`.
Mirrors `morning_prep_cp.py` and `nightly_consolidation_cp.py` — the
third instance is the one that proves the migration pattern is boring.

Why LOW risk (departure from the first two wrappers):
    weekly_review.sh is read-heavy. It runs import checks, `docker ps`,
    skill counts, and a log summary, then calls `claude -p` with an
    already-capped `--max-budget-usd 1.00` and posts a report to
    Discord. It does NOT mutate wiki state, substrate ritual state,
    or any persisted data. Blast radius = one Discord message and
    up to $1 of CC spend (already hard-capped inside the .sh).
    Per the Phase 4 design (§4.2) this is a correct `low` classification.

Idempotency:
    Key = `weekly_review:<ISO-week>`. TTL = 6 days (604800s, strictly
    less than one week, so next Sunday is never blocked by this week).
    A re-run inside the same week becomes a no-op at the Control Plane
    level — the second call returns `skipped_duplicate` with the
    original action_id.

Usage:
    # Cron-style — low risk auto-approves, --approve is redundant but
    # retained for consistency with the other wrappers.
    python3 /opt/OS/scripts/scheduled/weekly_review_cp.py --approve

    # Manual (also auto-approves because risk=low):
    python3 /opt/OS/scripts/scheduled/weekly_review_cp.py

    # Force a deferred run (operator wants to review before execute):
    python3 /opt/OS/scripts/scheduled/weekly_review_cp.py --risk medium

Cron migration (documented — NOT applied in Phase 4):
    # OLD:
    # 0 6 * * 0 bash /opt/OS/scripts/scheduled/weekly_review.sh
    # NEW:
    # 0 6 * * 0 python3 /opt/OS/scripts/scheduled/weekly_review_cp.py --approve \
    #          >> /opt/OS/logs/weekly_review_cp.log 2>&1
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.orchestrator.steps import ScriptWorkflowSpec, run_script_workflow

SCRIPT_PATH = "/opt/OS/scripts/scheduled/weekly_review.sh"
IDEMPOTENCY_TTL_SECONDS = 6 * 24 * 3600  # 6 days — < 1 week


def _idempotency_key(now: datetime | None = None) -> str:
    ref = now or datetime.now(timezone.utc)
    year, week, _ = ref.isocalendar()
    return f"weekly_review:{year}-W{week:02d}"


def main() -> int:
    p = argparse.ArgumentParser(description="Control Plane wrapper for weekly_review")
    p.add_argument(
        "--approve",
        action="store_true",
        help="Grant explicit approval (redundant at low risk; kept for consistency)",
    )
    p.add_argument(
        "--risk",
        default="low",
        choices=("low", "medium", "high"),
        help="Override risk classification (default: low, per Phase 4 design)",
    )
    p.add_argument(
        "--no-idempotency",
        action="store_true",
        help="Disable the weekly idempotency key (for debugging only)",
    )
    args = p.parse_args()

    key = None if args.no_idempotency else _idempotency_key()
    spec = ScriptWorkflowSpec(
        name="weekly_review",
        script_path=SCRIPT_PATH,
        description=("weekly health review (imports, docker, skills, logs, CC brief)"),
        expected_output=(
            "Weekly review posted to Discord; exit 0 in logs/weekly_review.log"
        ),
        idempotency_key=key,
        idempotency_ttl_seconds=IDEMPOTENCY_TTL_SECONDS,
        risk_level=args.risk,
        timeout=1800,
        reasoning=(
            "Route the weekly review through the Control Plane so the "
            "health audit has a full lifecycle record and an idempotency "
            "guard prevents duplicate weekly reports inside the same ISO "
            "week."
        ),
    )
    return run_script_workflow(spec, approve=args.approve)


if __name__ == "__main__":
    sys.exit(main())
