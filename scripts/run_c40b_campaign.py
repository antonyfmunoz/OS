#!/usr/bin/env python3
"""C40B — Runtime Embodiment Campaign.

The last runtime convergence campaign. Proves the operator physically
inhabits the organism through real runtime execution.

5 phases: audit -> fix -> qualify -> stress -> certify.

Usage:
    python3 scripts/run_c40b_campaign.py [--skip-browser] [--phase N] [--skip-voice]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, "/opt/OS")
sys.path.insert(0, _REPO_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("c40b")

from scripts.c40b_phases.campaign_context import (
    CampaignContext,
    DATA_DIR,
    PhaseResult,
)


def _run_phase(
    ctx: CampaignContext,
    phase_num: int,
    phase_name: str,
    phase_fn,
    skip_if_browser: bool = False,
) -> PhaseResult:
    """Run a phase with logging and error handling."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("C40B PHASE %d: %s", phase_num, phase_name)
    logger.info("=" * 70)

    if skip_if_browser and ctx.skip_browser:
        logger.info("SKIPPED (--skip-browser)")
        pr = PhaseResult(
            phase=phase_num,
            name=phase_name,
            notes="Skipped: --skip-browser",
        )
        ctx.persist_phase(pr)
        return pr

    try:
        pr = phase_fn(ctx)
        if pr.gate_passed:
            logger.info("PHASE %d GATE: PASSED", phase_num)
        else:
            logger.warning("PHASE %d GATE: FAILED — %s", phase_num, pr.notes)
        return pr
    except Exception as exc:
        logger.error("PHASE %d ERROR: %s", phase_num, exc)
        logger.error(traceback.format_exc())
        pr = PhaseResult(
            phase=phase_num,
            name=phase_name,
            notes="Error: %s" % exc,
        )
        ctx.persist_phase(pr)
        return pr


def run_campaign(
    skip_browser: bool = False,
    phase_only: int | None = None,
    skip_voice: bool = False,
) -> None:
    """Run C40B campaign."""
    logger.info("=" * 70)
    logger.info("C40B — RUNTIME EMBODIMENT CAMPAIGN")
    logger.info("=" * 70)
    logger.info("skip_browser=%s phase_only=%s skip_voice=%s", skip_browser, phase_only, skip_voice)

    ctx = CampaignContext(skip_browser=skip_browser)
    t0 = time.time()

    from scripts.c40b_phases.phase1_runtime_audit import run_phase1
    from scripts.c40b_phases.phase2_runtime_fix import run_phase2
    from scripts.c40b_phases.phase3_operator_qualification import run_phase3
    from scripts.c40b_phases.phase4_embodied_stress import run_phase4
    from scripts.c40b_phases.phase5_runtime_certification import run_phase5
    from scripts.c40b_phases.report_generator import generate_report, dispatch_to_discord

    phases = [
        (1, "Runtime Boundary Audit", run_phase1, False),
        (2, "Runtime Defect Resolution", run_phase2, False),
        (3, "Operator Runtime Qualification", run_phase3, True),
        (4, "Embodied Stress", run_phase4, True),
        (5, "Runtime Certification", run_phase5, False),
    ]

    for phase_num, phase_name, phase_fn, needs_browser in phases:
        if phase_only is not None and phase_num != phase_only:
            continue
        _run_phase(ctx, phase_num, phase_name, phase_fn, skip_if_browser=needs_browser)

    # Generate report
    logger.info("")
    logger.info("=" * 70)
    logger.info("GENERATING REPORT")
    logger.info("=" * 70)

    try:
        report_path = generate_report(ctx)
        logger.info("Report: %s", report_path)
    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        report_path = ""

    # Dispatch to Discord
    if report_path:
        try:
            msg_id = dispatch_to_discord(report_path)
            if msg_id:
                logger.info("Discord message: %s", msg_id)
            else:
                logger.warning("Discord dispatch returned no message ID")
        except Exception as exc:
            logger.error("Discord dispatch failed: %s", exc)

    # Summary
    elapsed = time.time() - t0
    logger.info("")
    logger.info("=" * 70)
    logger.info("C40B CAMPAIGN COMPLETE")
    logger.info("=" * 70)
    logger.info("Elapsed: %.1fs", elapsed)
    logger.info("Phases: %d", len(ctx.phase_results))
    logger.info("Mutations: %d", len(ctx.results))
    logger.info("")

    for v_key in ("organism", "runtime", "projection", "operator"):
        v = ctx.verdicts.get(v_key)
        if v:
            logger.info("  %s: %s — %s", v.name, v.status, v.evidence)

    all_pass = all(v.status == "PASS" for v in ctx.verdicts.values())
    gate_path = DATA_DIR / "production_readiness.json"
    gate_met = False
    if gate_path.exists():
        try:
            gate = json.loads(gate_path.read_text())
            gate_met = gate.get("all_met", False)
        except (json.JSONDecodeError, OSError):
            pass

    overall = "PRODUCTION READY" if all_pass and gate_met else "NOT READY"
    logger.info("")
    logger.info("OVERALL: %s", overall)
    logger.info("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="C40B Runtime Embodiment Campaign")
    parser.add_argument(
        "--skip-browser",
        action="store_true",
        help="Skip phases requiring Beast/browser",
    )
    parser.add_argument(
        "--phase",
        type=int,
        default=None,
        help="Run only phase N",
    )
    parser.add_argument(
        "--skip-voice",
        action="store_true",
        help="Skip voice-related tests",
    )
    args = parser.parse_args()
    run_campaign(
        skip_browser=args.skip_browser,
        phase_only=args.phase,
        skip_voice=args.skip_voice,
    )


if __name__ == "__main__":
    main()
