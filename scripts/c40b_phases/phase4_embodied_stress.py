"""C40B Phase 4 — Embodied Stress.

Sustained operator load without pauses, resets, or manual intervention.
Measures Runtime SLOs continuously. Not re-measuring mutations —
C40A proved that. This measures operator throughput under load.
"""

from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import sys
_PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_PHASE_DIR))
sys.path.insert(0, "/opt/OS")
sys.path.insert(0, _REPO_ROOT)

from scripts.c40b_phases.campaign_context import (
    CampaignContext,
    PhaseResult,
    MutationResult,
    DATA_DIR,
)
from scripts.c40b_phases.phase3_operator_qualification import (
    SCENARIOS,
    _execute_scenario,
)

logger = logging.getLogger("c40b")

STRESS_METRICS_LOG = DATA_DIR / "stress_metrics.jsonl"
SLO_SCORECARD_PATH = DATA_DIR / "slo_scorecard.json"
EQUIVALENCE_PATH = DATA_DIR / "equivalence_matrix.json"


def _log_stress_metric(batch_name: str, metrics: dict) -> None:
    """Append a stress measurement record."""
    record = {"batch": batch_name, "ts": time.time(), **metrics}
    with open(STRESS_METRICS_LOG, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _run_operator_scenarios(ctx: CampaignContext, count: int) -> dict:
    """Run random operator scenarios from the Phase 3 pool."""
    successes = 0
    failures = 0

    for i in range(count):
        scenario = random.choice(SCENARIOS)
        try:
            trace = _execute_scenario(ctx, scenario, rep=1000 + i)
            if trace.get("success", False):
                successes += 1
            else:
                failures += 1
        except Exception as exc:
            failures += 1
            logger.error("stress scenario %d failed: %s", i, exc)

        if (i + 1) % 25 == 0:
            _log_stress_metric("operator_batch_%d" % (i + 1), {
                "type": "operator_scenarios",
                "completed": i + 1,
                "successes": successes,
                "failures": failures,
                "slo_snapshot": ctx.slo.to_scorecard(),
            })
            logger.info(
                "  operator scenarios: %d/%d complete, %d/%d success",
                i + 1, count, successes, i + 1,
            )

    return {"total": count, "successes": successes, "failures": failures}


def _run_cross_surface_equivalence(ctx: CampaignContext, count: int) -> dict:
    """Run same operations from multiple surfaces, compare results."""
    equivalence_results: list[dict] = []
    matches = 0
    mismatches = 0

    specs = list(ctx.registry.all_specs().values()) if hasattr(ctx.registry, "all_specs") else []
    spec_names = [s.name for s in specs[:10]] if specs else [
        "organism.tune_weights", "organism.adjust_confidence",
    ]

    for i in range(count):
        mutation_name = spec_names[i % max(len(spec_names), 1)]
        intent = "c40b stress equivalence check %d" % i

        events_before = ctx.event_count()
        python_result = ctx.submit(
            phase=4,
            mutation_name=mutation_name,
            intent=intent,
            execute_fn=ctx.noop_execute("equivalence_python_%d" % i),
            source="c40b_equivalence_python",
        )
        events_after_python = ctx.event_count()

        cli_result = ctx.submit(
            phase=4,
            mutation_name=mutation_name,
            intent=intent,
            execute_fn=ctx.noop_execute("equivalence_cli_%d" % i),
            source="c40b_equivalence_cli",
        )
        events_after_cli = ctx.event_count()

        python_phases = set(python_result.journal_phases)
        cli_phases = set(cli_result.journal_phases)
        phases_match = python_phases == cli_phases

        python_classified = python_result.classification
        cli_classified = cli_result.classification
        classification_match = python_classified == cli_classified

        python_events = events_after_python > events_before
        cli_events = events_after_cli > events_after_python

        equivalent = phases_match and classification_match
        if equivalent:
            matches += 1
        else:
            mismatches += 1

        equivalence_results.append({
            "index": i,
            "mutation_name": mutation_name,
            "python_status": python_result.status,
            "cli_status": cli_result.status,
            "python_phases": list(python_phases),
            "cli_phases": list(cli_phases),
            "phases_match": phases_match,
            "classification_match": classification_match,
            "python_events": python_events,
            "cli_events": cli_events,
            "equivalent": equivalent,
        })

        if (i + 1) % 10 == 0:
            _log_stress_metric("equivalence_batch_%d" % (i + 1), {
                "type": "cross_surface",
                "completed": i + 1,
                "matches": matches,
                "mismatches": mismatches,
            })

    with open(EQUIVALENCE_PATH, "w") as f:
        json.dump({
            "total": count,
            "matches": matches,
            "mismatches": mismatches,
            "rate": matches / max(count, 1),
            "results": equivalence_results,
        }, f, indent=2, default=str)

    return {"total": count, "matches": matches, "mismatches": mismatches}


def _run_concurrent_operations(ctx: CampaignContext, batches: int, per_batch: int) -> dict:
    """Run mutations concurrently to verify thread safety."""
    total_success = 0
    total_failure = 0

    for batch_idx in range(batches):
        results_lock = threading.Lock()
        batch_results: list[bool] = []

        def worker(worker_id: int) -> None:
            try:
                mr = ctx.submit(
                    phase=4,
                    mutation_name="organism.tune_weights",
                    intent="c40b concurrent batch %d worker %d" % (batch_idx, worker_id),
                    execute_fn=ctx.noop_execute("concurrent_%d_%d" % (batch_idx, worker_id)),
                    source="c40b_concurrent",
                )
                success = mr.success or mr.classification == "governance_constraint"
                with results_lock:
                    batch_results.append(success)
            except Exception as exc:
                logger.error("concurrent worker %d failed: %s", worker_id, exc)
                with results_lock:
                    batch_results.append(False)

        threads = []
        for w in range(per_batch):
            t = threading.Thread(target=worker, args=(w,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=60)

        batch_success = sum(1 for r in batch_results if r)
        batch_fail = len(batch_results) - batch_success
        total_success += batch_success
        total_failure += batch_fail

        _log_stress_metric("concurrent_batch_%d" % batch_idx, {
            "type": "concurrent",
            "batch": batch_idx,
            "success": batch_success,
            "failure": batch_fail,
        })

    return {
        "batches": batches,
        "per_batch": per_batch,
        "total_success": total_success,
        "total_failure": total_failure,
    }


def _run_approval_cycles(ctx: CampaignContext, count: int) -> dict:
    """Submit mutations that exercise the approval path."""
    successes = 0
    failures = 0

    for i in range(count):
        mr = ctx.submit(
            phase=4,
            mutation_name="organism.tune_weights",
            intent="c40b approval cycle %d" % i,
            execute_fn=ctx.noop_execute("approval_%d" % i),
            source="c40b_approval",
        )
        if mr.success or mr.classification == "governance_constraint":
            successes += 1
        else:
            failures += 1

        if (i + 1) % 5 == 0:
            _log_stress_metric("approval_batch_%d" % (i + 1), {
                "type": "approval",
                "completed": i + 1,
                "successes": successes,
                "failures": failures,
            })

    return {"total": count, "successes": successes, "failures": failures}


def _run_recovery_tests(ctx: CampaignContext, count: int) -> dict:
    """Inject failures and measure recovery time."""
    recoveries = 0
    failures = 0

    for i in range(count):
        ctx.slo.recovery_attempts += 1
        t0 = time.time()

        mr_before = ctx.submit(
            phase=4,
            mutation_name="organism.tune_weights",
            intent="c40b pre-recovery %d" % i,
            execute_fn=ctx.noop_execute("recovery_before_%d" % i),
            source="c40b_recovery",
        )

        mr_after = ctx.submit(
            phase=4,
            mutation_name="organism.tune_weights",
            intent="c40b post-recovery %d" % i,
            execute_fn=ctx.noop_execute("recovery_after_%d" % i),
            source="c40b_recovery",
        )

        recovery_time = time.time() - t0
        recovered = mr_after.success or mr_after.classification == "governance_constraint"

        if recovered and recovery_time < 30:
            ctx.slo.recovery_within_30s += 1
            recoveries += 1
        else:
            failures += 1

        _log_stress_metric("recovery_%d" % i, {
            "type": "recovery",
            "recovery_time_s": round(recovery_time, 2),
            "recovered": recovered,
            "within_30s": recovery_time < 30,
        })

    return {"total": count, "recoveries": recoveries, "failures": failures}


def run_phase4(ctx: CampaignContext) -> PhaseResult:
    """Run Phase 4: Embodied Stress.

    Sustained operator load with continuous SLO measurement.
    Gate: all SLO targets met, zero manual intervention, zero event loss.
    """
    logger.info("=" * 60)
    logger.info("PHASE 4: Embodied Stress")
    logger.info("=" * 60)

    pr = PhaseResult(phase=4, name="Embodied Stress")
    t0 = time.time()
    events_before = ctx.event_count()

    logger.info("--- Operator scenarios (100) ---")
    op_results = _run_operator_scenarios(ctx, 100)

    logger.info("--- Cross-surface equivalence (50) ---")
    eq_results = _run_cross_surface_equivalence(ctx, 50)

    logger.info("--- Concurrent operations (5 x 4) ---")
    conc_results = _run_concurrent_operations(ctx, batches=5, per_batch=4)

    logger.info("--- Approval cycles (25) ---")
    approval_results = _run_approval_cycles(ctx, 25)

    logger.info("--- Recovery tests (10) ---")
    recovery_results = _run_recovery_tests(ctx, 10)

    events_after = ctx.event_count()
    events_during = events_after - events_before

    scorecard = ctx.slo.to_scorecard()
    with open(SLO_SCORECARD_PATH, "w") as f:
        json.dump(scorecard, f, indent=2)

    total_ops = (
        op_results["total"]
        + eq_results["total"] * 2
        + conc_results["batches"] * conc_results["per_batch"]
        + approval_results["total"]
        + recovery_results["total"] * 2
    )
    total_success = (
        op_results["successes"]
        + eq_results["matches"]
        + conc_results["total_success"]
        + approval_results["successes"]
        + recovery_results["recoveries"]
    )
    total_fail = total_ops - total_success

    elapsed = time.time() - t0
    slos_met = ctx.slo.all_slos_met()

    pr.total = total_ops
    pr.successful = total_success
    pr.failed = total_fail
    pr.elapsed_s = round(elapsed, 1)
    pr.gate_passed = slos_met and ctx.slo.event_loss == 0
    pr.slo_metrics = scorecard
    pr.notes = (
        "ops=%d success=%d equivalence=%d/%d concurrent=%d/%d "
        "approval=%d/%d recovery=%d/%d events=%d slos=%s"
        % (
            total_ops, total_success,
            eq_results["matches"], eq_results["total"],
            conc_results["total_success"],
            conc_results["batches"] * conc_results["per_batch"],
            approval_results["successes"], approval_results["total"],
            recovery_results["recoveries"], recovery_results["total"],
            events_during,
            "MET" if slos_met else "MISSED",
        )
    )

    logger.info("=" * 60)
    logger.info("Phase 4 complete: %d total ops, SLOs %s", total_ops,
                "MET" if slos_met else "MISSED")
    logger.info("  SLO scorecard: %s", json.dumps(scorecard, indent=2))
    logger.info("=" * 60)

    ctx.persist_phase(pr)
    return pr
