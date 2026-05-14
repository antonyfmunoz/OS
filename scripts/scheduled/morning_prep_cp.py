#!/usr/bin/env python3
"""morning_prep_cp.py — Control Plane wrapper for morning_prep.sh.

This is the Control Plane migration of the morning_prep workflow.
Cron (or the operator) calls this Python entry instead of the raw
bash script, and the underlying .sh runs as a `run_script` action:
validated, risk-classified, and logged with a full lifecycle trail.

Why medium risk:
    morning_prep.sh mutates ritual state, consumes CC budget
    (up to $0.30), and touches the LLM provider health gate.
    It's not destructive, but it's also not free. Medium risk
    makes cron approvals explicit and visible in the deferred
    queue when auto-approval is disabled.

Usage:
    # Cron-style invocation (auto-approves — operator has pre-authorized):
    python3 /opt/OS/scripts/scheduled/morning_prep_cp.py --approve

    # Manual dry invocation (defers, operator resumes via scripts/deferred.py):
    python3 /opt/OS/scripts/scheduled/morning_prep_cp.py

Cron migration:
    # OLD:
    # 30 5 * * * bash /opt/OS/scripts/scheduled/morning_prep.sh
    # NEW:
    # 30 5 * * * python3 /opt/OS/scripts/scheduled/morning_prep_cp.py --approve \
    #           >> /opt/OS/logs/morning_prep_cp.log 2>&1
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from control_plane.runtime.orchestrator.steps import ScriptWorkflowSpec, run_script_workflow

SCRIPT_PATH = f"{_ROOT}/scripts/scheduled/morning_prep.sh"
IDEMPOTENCY_TTL_SECONDS = 23 * 3600  # 23h — never collides with tomorrow's run


def main() -> int:
    p = argparse.ArgumentParser(description="Control Plane wrapper for morning_prep")
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
    args = p.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    spec = ScriptWorkflowSpec(
        name="morning_prep",
        script_path=SCRIPT_PATH,
        description="scheduled morning prep (containers, keys, Neon, GWS, CC brief)",
        expected_output=(
            "SYSTEM READY line or issue list in logs/morning_YYYYMMDD.log"
        ),
        idempotency_key=f"morning_prep:{today}",
        idempotency_ttl_seconds=IDEMPOTENCY_TTL_SECONDS,
        risk_level=args.risk,
        timeout=600,
        reasoning=(
            "Route the morning prep through the Control Plane so the "
            "daily ritual has a full lifecycle record and can be deferred "
            "when the operator has not pre-approved the CC budget spend."
        ),
    )
    return run_script_workflow(spec, approve=args.approve)


if __name__ == "__main__":
    sys.exit(main())
