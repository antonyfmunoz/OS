"""Boot orchestrator — routes to first-boot or daily-boot."""

from __future__ import annotations

import logging
import os
import sys

from umh.daily import run_daily_boot
from umh.loop import run_interaction_loop
from umh.profile import ProfileManager

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


def run_boot(text_only: bool = False) -> int:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    pm = ProfileManager()
    if not pm.has_snapshot():
        return run_first_boot(text_only=text_only)

    mode_state, session_id = run_daily_boot(text_only=text_only)
    return run_interaction_loop(
        mode_state=mode_state,
        session_id=session_id,
        text_only=text_only,
    )


def run_first_boot(text_only: bool = False) -> int:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    print()
    print("═" * 50)
    print("  UMH Workstation — First Boot")
    print("═" * 50)
    print()
    print("No existing session found. Running first-boot setup.")
    print()

    from umh.diagnostics import run_diagnostics

    diag_result = run_diagnostics()
    if diag_result != 0:
        print("Fix diagnostic failures before continuing.")
        return diag_result

    print("First-boot onboarding flow is not yet implemented (Sprint 3).")
    print("Starting in text-only mode with default profile.\n")

    mode_state, session_id = run_daily_boot(text_only=True)
    return run_interaction_loop(
        mode_state=mode_state,
        session_id=session_id,
        text_only=True,
    )
