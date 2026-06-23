#!/usr/bin/env python3
"""C29 Harness Superiority Benchmark — CLI Runner.

Main CLI for the C29 Harness Superiority benchmark. Registers tasks, records
Track A (Legacy) and Track B (UMH) results, computes scores, generates the
certification report, and runs longitudinal continuity checkpoints and
multi-project pressure tests.

All scoring is deterministic and lives in harness_scorer.py — this module is
only the interactive recording / dashboard layer. Track B browser evidence is
collected on Beast via the SSH pattern shared with C28.

Usage:
  python3 tests/certification/c29_benchmark.py --register-task
  python3 tests/certification/c29_benchmark.py --record-legacy <task_id>
  python3 tests/certification/c29_benchmark.py --record-umh <task_id>
  python3 tests/certification/c29_benchmark.py --score
  python3 tests/certification/c29_benchmark.py --report
  python3 tests/certification/c29_benchmark.py --status
  python3 tests/certification/c29_benchmark.py --checkpoint
  python3 tests/certification/c29_benchmark.py --multi-project
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.organism.benchmarks.harness_superiority import (  # noqa: E402
    AwarenessSnapshot,
    BenchmarkCategory,
    BenchmarkTask,
    BrowserEvidence,
    CognitiveLoadResult,
    Complexity,
    ContinuityResult,
    EscapeEvent,
    EvidenceClass,
    GovernanceResult,
    InterruptionResult,
    LongitudinalCheckpoint,
    MetaIDEResult,
    OperatorTrustResult,
    Outcome,
    RealityDriftResult,
    ResourceCost,
    ResultStore,
    TaskRegistry,
    Track,
    TrackResult,
    WorkdayCoverage,
)
from substrate.organism.benchmarks.harness_scorer import (  # noqa: E402
    HarnessScorer,
    HTICalculator,
    MVPVerdictEngine,
    UMHMetricCalculator,
)

logger = logging.getLogger(__name__)

_COCKPIT_URL = "https://universalmetaharness.tech"
_BEAST_SSH = os.environ.get("UMH_BEAST_SSH", "")
_PROJECTS = ("UMH", "CreatorOS", "EntrepreneurOS", "LyfeOS")


def _umh_root() -> Path:
    return Path(os.environ.get("UMH_ROOT", "/opt/OS"))


def _c29_dir() -> Path:
    return _umh_root() / "data" / "certification" / "c29"


def _checkpoints_path() -> Path:
    return _c29_dir() / "checkpoints.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Interactive prompt helpers
# ---------------------------------------------------------------------------


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        raw = input(f"{label}{suffix}: ").strip()
    except EOFError:
        return default
    return raw if raw else default


def _prompt_optional(label: str) -> str | None:
    """Empty input -> None (skip)."""
    raw = _prompt(label)
    return raw if raw else None


def _prompt_int(label: str, default: int = 0) -> int:
    while True:
        raw = _prompt(label, str(default))
        try:
            return int(raw)
        except ValueError:
            print(f"  '{raw}' is not an integer. Try again.")


def _prompt_float(label: str, default: float = 0.0) -> float:
    while True:
        raw = _prompt(label, str(default))
        try:
            return float(raw)
        except ValueError:
            print(f"  '{raw}' is not a number. Try again.")


def _prompt_bool(label: str, default: bool = False) -> bool:
    default_str = "y" if default else "n"
    while True:
        raw = _prompt(f"{label} (y/n)", default_str).lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Please answer y/yes or n/no.")


def _prompt_choice(label: str, choices: tuple[str, ...], default: str = "") -> str:
    default = default or choices[0]
    options = "/".join(choices)
    while True:
        raw = _prompt(f"{label} ({options})", default).upper()
        for c in choices:
            if raw == c.upper():
                return c
        print(f"  Choose one of: {options}")


def _prompt_list(label: str) -> list[str]:
    raw = _prompt(f"{label} (comma-separated)")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_timestamp(label: str) -> str:
    """Prompt for an ISO timestamp; 'now' -> current UTC time."""
    raw = _prompt(f"{label} (ISO or 'now')", "now")
    if raw.lower() == "now" or not raw:
        return _now_iso()
    return raw


def _duration_between(started: str, completed: str) -> float | None:
    try:
        a = datetime.fromisoformat(started)
        b = datetime.fromisoformat(completed)
        return (b - a).total_seconds()
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Task registration
# ---------------------------------------------------------------------------


def register_task(quiet: bool = False) -> None:
    registry = TaskRegistry()

    if quiet:
        print("--register-task requires interactive input; --quiet not supported here.")
        return

    print("\n=== C29 Register Benchmark Task ===\n")

    task_id = _prompt("task_id (e.g. c29-001)")
    if not task_id:
        print("task_id required. Aborting.")
        return
    if registry.get(task_id) is not None:
        print(f"Task '{task_id}' already exists. Aborting.")
        return

    category = BenchmarkCategory(
        _prompt_choice("category", tuple(c.value for c in BenchmarkCategory))
    )
    project = _prompt_choice("project", _PROJECTS)
    title = _prompt("title")
    description = _prompt("description")
    complexity = Complexity(
        _prompt_choice("complexity", tuple(c.value for c in Complexity), "MEDIUM")
    )
    deliverables = _prompt_list("expected_deliverables")

    new_task = BenchmarkTask(
        task_id=task_id,
        category=category,
        project=project,
        title=title,
        description=description,
        complexity=complexity,
        expected_deliverables=deliverables,
        created_at=_now_iso(),
    )
    registry.register(new_task)
    print(f"\nRegistered task '{task_id}' ({category.value} / {project}).")


# ---------------------------------------------------------------------------
# Shared result recording
# ---------------------------------------------------------------------------


def _record_core_fields(task_id: str, track: Track) -> dict[str, Any]:
    """Prompt for the fields common to both tracks; returns a kwargs dict."""
    print(f"\n--- Core fields ({track.value}) ---")

    evidence_class = EvidenceClass(
        _prompt_choice(
            "evidence_class",
            tuple(ec.value for ec in EvidenceClass),
            EvidenceClass.A_PRODUCTION.value,
        )
    )

    started_at = _parse_timestamp("started_at")
    completed_at = _parse_timestamp("completed_at")

    auto_duration = _duration_between(started_at, completed_at)
    if auto_duration is not None and auto_duration >= 0:
        duration_seconds = _prompt_float("duration_seconds", round(auto_duration, 2))
    else:
        duration_seconds = _prompt_float("duration_seconds")

    outcome = Outcome(
        _prompt_choice("outcome", tuple(o.value for o in Outcome), Outcome.SUCCESS.value)
    )
    deliverables_met = _prompt_list("deliverables_met")
    quality_score = _prompt_float("quality_score (0-100)", 0.0)
    verification_method = _prompt("verification_method")
    verification_passed = _prompt_bool("verification_passed")

    recovery_needed = _prompt_bool("recovery_needed")
    recovery_successful = False
    recovery_time_seconds = 0.0
    if recovery_needed:
        recovery_successful = _prompt_bool("recovery_successful")
        recovery_time_seconds = _prompt_float("recovery_time_seconds")

    context_switches = _prompt_int("context_switches")
    manual_reconstructions = _prompt_int("manual_reconstructions")
    tools_used = _prompt_list("tools_used")
    notes = _prompt("notes")

    return {
        "task_id": task_id,
        "track": track,
        "evidence_class": evidence_class,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": duration_seconds,
        "outcome": outcome,
        "deliverables_met": deliverables_met,
        "quality_score": quality_score,
        "verification_method": verification_method,
        "verification_passed": verification_passed,
        "recovery_needed": recovery_needed,
        "recovery_successful": recovery_successful,
        "recovery_time_seconds": recovery_time_seconds,
        "context_switches": context_switches,
        "manual_reconstructions": manual_reconstructions,
        "tools_used": tools_used,
        "notes": notes,
    }


def _record_cognitive_load() -> CognitiveLoadResult | None:
    if not _prompt_bool("Record cognitive_load?", True):
        return None
    print("--- cognitive_load ---")
    return CognitiveLoadResult(
        reconstruction_steps=_prompt_int("reconstruction_steps"),
        clarification_questions=_prompt_int("clarification_questions"),
        context_searches=_prompt_int("context_searches"),
        panel_hops=_prompt_int("panel_hops"),
        memory_recovery_actions=_prompt_int("memory_recovery_actions"),
    )


def _record_interruption() -> InterruptionResult | None:
    if not _prompt_bool("Record interruption_test?", False):
        return None
    print("--- interruption_test ---")
    return InterruptionResult(
        interruption_type=_prompt_choice(
            "interruption_type",
            ("TASK_SWITCH", "MEETING", "EMERGENCY", "TIME_GAP"),
        ),
        interruption_from=_prompt("interruption_from"),
        interruption_to=_prompt("interruption_to", "away"),
        away_duration_seconds=_prompt_float("away_duration_seconds"),
        resume_time_seconds=_prompt_float("resume_time_seconds"),
        context_accuracy=_prompt_float("context_accuracy (0-1)"),
        decisions_recalled=_prompt_int("decisions_recalled"),
        decisions_total=_prompt_int("decisions_total"),
        work_recovery_complete=_prompt_bool("work_recovery_complete"),
    )


def _record_resource_cost(deliverables_met: int) -> ResourceCost | None:
    if not _prompt_bool("Record resource_cost?", True):
        return None
    print("--- resource_cost ---")
    operator_minutes = _prompt_float("operator_minutes")
    default_cpd = operator_minutes / max(deliverables_met, 1)
    cpd_in = _prompt_float("cost_per_deliverable", round(default_cpd, 4))
    return ResourceCost(
        tokens_used=_prompt_int("tokens_used"),
        compute_seconds=_prompt_float("compute_seconds"),
        operator_minutes=operator_minutes,
        clicks=_prompt_int("clicks"),
        panel_changes=_prompt_int("panel_changes"),
        commands_issued=_prompt_int("commands_issued"),
        cost_per_deliverable=cpd_in,
    )


def _record_continuity() -> ContinuityResult | None:
    if not _prompt_bool("Record continuity_test?", False):
        return None
    print("--- continuity_test ---")
    return ContinuityResult(
        interruption_duration_seconds=_prompt_float("interruption_duration_seconds"),
        context_preserved=_prompt_bool("context_preserved"),
        resume_time_seconds=_prompt_float("resume_time_seconds (TTRC)"),
        decisions_recalled=_prompt_int("decisions_recalled"),
        decisions_total=_prompt_int("decisions_total"),
        intent_preserved=_prompt_bool("intent_preserved"),
    )


def _record_governance() -> GovernanceResult | None:
    if not _prompt_bool("Record governance_test?", True):
        return None
    print("--- governance_test ---")
    return GovernanceResult(
        approvals_required=_prompt_int("approvals_required"),
        approvals_enforced=_prompt_int("approvals_enforced"),
        proof_generated=_prompt_bool("proof_generated"),
        verification_enforced=_prompt_bool("verification_enforced"),
        false_history_tested=_prompt_bool("false_history_tested"),
        false_history_blocked=_prompt_bool("false_history_blocked"),
    )


def _record_awareness() -> AwarenessSnapshot | None:
    if not _prompt_bool("Record awareness_snapshot?", True):
        return None
    print("--- awareness_snapshot (10 visibility checks) ---")
    return AwarenessSnapshot(
        repos_visible=_prompt_bool("repos_visible"),
        branches_visible=_prompt_bool("branches_visible"),
        builds_visible=_prompt_bool("builds_visible"),
        deployments_visible=_prompt_bool("deployments_visible"),
        containers_visible=_prompt_bool("containers_visible"),
        previews_visible=_prompt_bool("previews_visible"),
        sessions_visible=_prompt_bool("sessions_visible"),
        executions_visible=_prompt_bool("executions_visible"),
        agents_visible=_prompt_bool("agents_visible"),
        device_mesh_visible=_prompt_bool("device_mesh_visible"),
    )


def _record_meta_ide() -> MetaIDEResult | None:
    if not _prompt_bool("Record meta_ide_test?", True):
        return None
    print("--- meta_ide_test (7 awareness dimensions) ---")
    return MetaIDEResult(
        workspace_aware=_prompt_bool("workspace_aware"),
        repo_aware=_prompt_bool("repo_aware"),
        branch_aware=_prompt_bool("branch_aware"),
        execution_aware=_prompt_bool("execution_aware"),
        preview_aware=_prompt_bool("preview_aware"),
        proof_aware=_prompt_bool("proof_aware"),
        continuity_aware=_prompt_bool("continuity_aware"),
    )


def _record_operator_trust() -> OperatorTrustResult | None:
    if not _prompt_bool("Record operator_trust?", True):
        return None
    print("--- operator_trust ---")
    return OperatorTrustResult(
        confidence_before=_prompt_int("confidence_before (1-5)", 3),
        confidence_after=_prompt_int("confidence_after (1-5)", 3),
        verification_needed=_prompt_bool("verification_needed"),
        manual_double_checks=_prompt_int("manual_double_checks"),
    )


def _record_reality_drift() -> RealityDriftResult | None:
    if not _prompt_bool("Record reality_drift?", False):
        return None
    print("--- reality_drift ---")
    return RealityDriftResult(
        drift_type=_prompt_choice(
            "drift_type",
            (
                "STALE_BRANCH",
                "STALE_DEPLOY",
                "WRONG_ASSUMPTION",
                "FAILED_ROLLOUT",
                "MISSING_DEPENDENCY",
                "OUTDATED_PLAN",
            ),
        ),
        drift_present=_prompt_bool("drift_present", True),
        drift_detected=_prompt_bool("drift_detected"),
        detection_time_seconds=_prompt_float("detection_time_seconds"),
        false_positive=_prompt_bool("false_positive"),
        detection_method=_prompt_choice(
            "detection_method", ("automated", "manual", "not_detected")
        ),
    )


def _record_escapes() -> list[EscapeEvent]:
    escapes: list[EscapeEvent] = []
    print("--- escapes (enter 'done' for tool to stop) ---")
    while True:
        tool = _prompt("escape tool ('done' to stop)")
        if not tool or tool.lower() == "done":
            break
        reason = _prompt("  reason")
        could_handle = _prompt_bool("  could_cockpit_handle")
        escapes.append(
            EscapeEvent(
                timestamp=_now_iso(),
                tool=tool,
                reason=reason,
                could_cockpit_handle=could_handle,
            )
        )
    return escapes


# ---------------------------------------------------------------------------
# Track A (Legacy) recording
# ---------------------------------------------------------------------------


def record_legacy(task_id: str, quiet: bool = False) -> None:
    registry = TaskRegistry()
    store = ResultStore()

    task = registry.get(task_id)
    if task is None:
        print(f"Task '{task_id}' not found. Register it first.")
        return

    if quiet:
        print("--record-legacy requires interactive input; --quiet not supported.")
        return

    print(f"\n=== C29 Record Track A (Legacy) — {task_id} ===")
    print(f"  {task.title} ({task.category.value} / {task.project})")

    core = _record_core_fields(task_id, Track.A_LEGACY)

    cognitive_load = _record_cognitive_load()
    interruption_test = _record_interruption()
    resource_cost = _record_resource_cost(len(core["deliverables_met"]))

    result = TrackResult(
        **core,
        cognitive_load=cognitive_load,
        interruption_test=interruption_test,
        resource_cost=resource_cost,
    )
    store.record(result)
    print(f"\nRecorded Track A result for '{task_id}'.")


# ---------------------------------------------------------------------------
# Track B (UMH) recording
# ---------------------------------------------------------------------------


def record_umh(task_id: str, quiet: bool = False, collect_evidence: bool = True) -> None:
    registry = TaskRegistry()
    store = ResultStore()

    task = registry.get(task_id)
    if task is None:
        print(f"Task '{task_id}' not found. Register it first.")
        return

    if quiet:
        print("--record-umh requires interactive input; --quiet not supported.")
        return

    print(f"\n=== C29 Record Track B (UMH) — {task_id} ===")
    print(f"  {task.title} ({task.category.value} / {task.project})")

    core = _record_core_fields(task_id, Track.B_UMH)

    escapes = _record_escapes()
    cognitive_load = _record_cognitive_load()
    interruption_test = _record_interruption()
    continuity_test = _record_continuity()
    governance_test = _record_governance()
    awareness_snapshot = _record_awareness()
    meta_ide_test = _record_meta_ide()
    operator_trust = _record_operator_trust()
    reality_drift = _record_reality_drift()
    resource_cost = _record_resource_cost(len(core["deliverables_met"]))

    browser_evidence: BrowserEvidence | None = None
    if collect_evidence and _prompt_bool("Collect Beast browser evidence?", False):
        browser_evidence = _collect_browser_evidence(task_id, Track.B_UMH)

    result = TrackResult(
        **core,
        escapes=escapes,
        continuity_test=continuity_test,
        governance_test=governance_test,
        awareness_snapshot=awareness_snapshot,
        cognitive_load=cognitive_load,
        interruption_test=interruption_test,
        reality_drift=reality_drift,
        operator_trust=operator_trust,
        meta_ide_test=meta_ide_test,
        resource_cost=resource_cost,
        browser_evidence=browser_evidence,
    )
    store.record(result)
    print(f"\nRecorded Track B result for '{task_id}'.")


def _collect_browser_evidence(task_id: str, track: Track) -> BrowserEvidence | None:
    """Trigger Beast Playwright evidence collection (C28 SSH pattern)."""
    if not _BEAST_SSH:
        print("  UMH_BEAST_SSH not configured — skipping browser evidence.")
        return None

    from substrate.meta_ide.browser_evidence_collector import trigger_collection

    run_dir = _c29_dir() / "runs" / task_id / track.value
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Triggering Beast evidence collection -> {run_dir} ...")
    evidence = trigger_collection(_COCKPIT_URL, pass_count=1)

    if evidence.get("error"):
        print(f"  Evidence collection error: {evidence['error']}")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    artifact = run_dir / f"evidence_{stamp}.json"
    artifact.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")

    passes = evidence.get("passes", [])
    screenshots: list[str] = []
    console_errors: list[str] = []
    console_log: list[str] = []
    network_errors: list[str] = []
    network_traces: list[str] = []
    for p in passes:
        if not isinstance(p, dict):
            continue
        for vp in p.get("viewports", []):
            if vp.get("screenshot_path"):
                screenshots.append(vp["screenshot_path"])
            console_errors.extend(vp.get("console_errors", []))
            console_log.extend(vp.get("console_log", []))
            network_errors.extend(vp.get("network_errors", []))
            network_traces.extend(vp.get("network_traces", []))

    return BrowserEvidence(
        screenshots=screenshots,
        console_errors=console_errors,
        console_log=console_log,
        network_errors=network_errors,
        network_traces=network_traces,
        execution_traces=[str(artifact)],
        proof_package_id=evidence.get("proof_package_id", ""),
        verification_result="collected" if not evidence.get("error") else "error",
    )


# ---------------------------------------------------------------------------
# Workday coverage (aggregate across all runs)
# ---------------------------------------------------------------------------


def _compute_workday_coverage(results: list[TrackResult]) -> WorkdayCoverage:
    """Infer daily-driver coverage from the activities exercised across runs.

    Coverage is capability-positive: any successful UMH run on an activity flips
    its flag on. Maps benchmark categories + sub-results to the 10 activities.
    """
    registry = TaskRegistry()
    cov = {
        "coding": False,
        "debugging": False,
        "review": False,
        "deployment": False,
        "planning": False,
        "continuity": False,
        "documentation": False,
        "approvals": False,
        "knowledge_retrieval": False,
        "runtime_inspection": False,
    }

    cat_map = {
        BenchmarkCategory.FEATURE: "coding",
        BenchmarkCategory.REFACTOR: "coding",
        BenchmarkCategory.BUG_FIX: "debugging",
        BenchmarkCategory.DEPLOY: "deployment",
        BenchmarkCategory.RECOVERY: "debugging",
    }

    for r in results:
        if r.track != Track.B_UMH:
            continue
        if r.outcome == Outcome.FAILED:
            continue
        task = registry.get(r.task_id)
        if task is not None and task.category in cat_map:
            cov[cat_map[task.category]] = True
        if r.continuity_test is not None and r.continuity_test.context_preserved:
            cov["continuity"] = True
        if r.governance_test is not None and r.governance_test.approvals_enforced > 0:
            cov["approvals"] = True
        if r.awareness_snapshot is not None and (
            r.awareness_snapshot.executions_visible
            or r.awareness_snapshot.containers_visible
        ):
            cov["runtime_inspection"] = True
        if r.meta_ide_test is not None and r.meta_ide_test.proof_aware:
            cov["review"] = True
        if "docs" in (r.tools_used or []) or "documentation" in (r.deliverables_met or []):
            cov["documentation"] = True

    # Planning + knowledge_retrieval: exercised whenever any UMH run surfaced
    # awareness state for the operator to plan and retrieve from.
    if any(
        r.track == Track.B_UMH and r.awareness_snapshot is not None for r in results
    ):
        cov["planning"] = True
        cov["knowledge_retrieval"] = True

    return WorkdayCoverage(**cov)


def _split_tracks(
    results: list[TrackResult],
) -> tuple[list[TrackResult], list[TrackResult]]:
    legacy = [r for r in results if r.track == Track.A_LEGACY]
    umh = [r for r in results if r.track == Track.B_UMH]
    return legacy, umh


def _build_engines() -> tuple[
    HarnessScorer, HTICalculator, UMHMetricCalculator, MVPVerdictEngine, list[TrackResult]
]:
    store = ResultStore()
    results = store.list_all()
    legacy, umh = _split_tracks(results)
    workday = _compute_workday_coverage(results)

    scorer = HarnessScorer(legacy, umh)
    hti = HTICalculator(umh)
    metrics = UMHMetricCalculator(umh, workday)
    verdict_engine = MVPVerdictEngine(scorer, hti, metrics)
    return scorer, hti, metrics, verdict_engine, results


# ---------------------------------------------------------------------------
# --score
# ---------------------------------------------------------------------------


_DIM_LABELS = {
    "capability": "Capability",
    "execution": "Execution",
    "cognitive_load": "Cognitive Load",
    "interruption_resistance": "Interruption Resist.",
    "continuity": "Continuity",
    "governance": "Governance",
    "awareness": "Awareness",
    "recovery": "Recovery",
    "meta_ide": "Meta IDE",
    "cost_efficiency": "Cost Efficiency",
}


def show_score() -> None:
    scorer, hti, metrics, verdict_engine, results = _build_engines()

    print("\nC29 HARNESS SUPERIORITY — CURRENT SCORES")
    print("=" * 60)

    if not results:
        print("\nNo results recorded yet. Record Track A + Track B runs first.")
        return

    dims = scorer.compute_all()
    print("\nComparative Scores (10 dimensions):")
    for name, d in dims.items():
        label = _DIM_LABELS.get(name, name)
        pct = int(round(d["weight"] * 100))
        delta = d["delta"]
        sign = "+" if delta >= 0 else ""
        print(
            f"  {label:<22} ({pct:>2}%):  "
            f"Legacy {d['legacy']:.2f}  UMH {d['umh']:.2f}  "
            f"Δ {sign}{delta:.2f}"
        )

    print(f"\nHTI Score: {hti.hti_score():.2f} / 100")
    for name, val in hti.compute().items():
        weight = HTICalculator.COMPONENT_WEIGHTS[name]
        print(f"  {name:<24} ({int(round(weight * 100)):>2}%): {val:.3f}")

    print("\nUMH Metrics:")
    for name, m in metrics.pass_report().items():
        passed = "✓" if m["passed"] else "✗"
        target = m["target"]
        if name in UMHMetricCalculator.LOWER_IS_BETTER:
            target_str = f"target <{target}"
            value_str = f"{m['value']:.2f}"
        else:
            target_str = f"target >{target}"
            value_str = (
                f"{m['value'] * 100:.1f}%" if m["value"] <= 1.0 else f"{m['value']:.2f}"
            )
        print(f"  {name}: {value_str} ({m['confidence']}) {passed}  [{target_str}]")

    dist = ResultStore().evidence_distribution()
    print("\nEvidence Distribution:")
    print(
        f"  Class A: {dist['A_PRODUCTION']}  "
        f"Class B: {dist['B_CONTROLLED']}  "
        f"Class C: {dist['C_SYNTHETIC']}"
    )

    verdict = verdict_engine.derive_verdict()
    print(f"\nMVP Trust Verdict: {verdict.verdict}")
    print(f"  {verdict.evidence_summary}")


# ---------------------------------------------------------------------------
# --status
# ---------------------------------------------------------------------------


def show_status() -> None:
    registry = TaskRegistry()
    store = ResultStore()

    tasks = registry.list_all()
    results = store.list_all()

    print("\nC29 STATUS")
    print("=" * 30)

    cat_counts = {c.value: 0 for c in BenchmarkCategory}
    proj_counts = {p: 0 for p in _PROJECTS}
    for t in tasks:
        cat_counts[t.category.value] += 1
        proj_counts.setdefault(t.project, 0)
        proj_counts[t.project] += 1

    cat_str = ", ".join(f"{k}: {v}" for k, v in cat_counts.items())
    print(f"Tasks: {len(tasks)}  ({cat_str})")

    proj_str = ", ".join(f"{k}: {v}" for k, v in proj_counts.items())
    print(f"Projects: {proj_str}")

    legacy, umh = _split_tracks(results)
    print(f"Results: {len(results)} total  (Legacy: {len(legacy)}, UMH: {len(umh)})")

    dist = store.evidence_distribution()
    print(
        f"Evidence: A={dist['A_PRODUCTION']}, "
        f"B={dist['B_CONTROLLED']}, C={dist['C_SYNTHETIC']}"
    )

    completed_runs = len(results)
    next_checkpoint_at = ((completed_runs // 10) + 1) * 10
    runs_away = next_checkpoint_at - completed_runs
    print(
        f"Next checkpoint: Run {next_checkpoint_at} "
        f"({runs_away} run{'s' if runs_away != 1 else ''} away)"
    )


# ---------------------------------------------------------------------------
# --checkpoint (longitudinal continuity recall challenge)
# ---------------------------------------------------------------------------


def _generate_challenge_questions(results: list[TrackResult]) -> list[str]:
    """Generate up to 5 recall questions from recorded run data."""
    registry = TaskRegistry()
    questions: list[str] = []

    def _by_category(cat: BenchmarkCategory) -> list[TrackResult]:
        out = []
        for r in results:
            t = registry.get(r.task_id)
            if t is not None and t.category == cat:
                out.append(r)
        return out

    bug_fixes = _by_category(BenchmarkCategory.BUG_FIX)
    if bug_fixes:
        t = registry.get(bug_fixes[-1].task_id)
        questions.append(f"What was the last bug fix on {t.project}?")

    refactors = _by_category(BenchmarkCategory.REFACTOR)
    if refactors:
        t = registry.get(refactors[-1].task_id)
        questions.append(
            f"What branch was the {t.project} refactor ({refactors[-1].task_id}) on?"
        )

    failed = [r for r in results if r.outcome == Outcome.FAILED]
    if failed:
        questions.append(f"What failed in run {failed[-1].task_id}?")

    governed = [
        r
        for r in results
        if r.governance_test is not None and r.governance_test.approvals_required > 0
    ]
    if governed:
        questions.append(f"What was the governance decision on {governed[-1].task_id}?")

    deploys = _by_category(BenchmarkCategory.DEPLOY)
    if deploys:
        t = registry.get(deploys[-1].task_id)
        questions.append(
            f"What's the current deploy status of {t.project} ({deploys[-1].task_id})?"
        )

    generic = [
        "What was the most recent task completed?",
        "Which project had the most runs?",
        "What was the last task that required recovery?",
        "Which run had the highest cognitive load?",
        "What was the last interruption test scenario?",
    ]
    gi = 0
    while len(questions) < 5 and gi < len(generic):
        if generic[gi] not in questions:
            questions.append(generic[gi])
        gi += 1

    return questions[:5]


def run_checkpoint(quiet: bool = False) -> None:
    store = ResultStore()
    results = store.list_all()

    checkpoints_path = _checkpoints_path()
    checkpoints_path.parent.mkdir(parents=True, exist_ok=True)

    existing = 0
    if checkpoints_path.exists():
        existing = sum(
            1 for line in checkpoints_path.read_text().splitlines() if line.strip()
        )
    checkpoint_number = existing + 1

    questions = _generate_challenge_questions(results)

    print(f"\n=== C29 Longitudinal Checkpoint #{checkpoint_number} ===")
    print(f"Runs completed: {len(results)}")
    print(f"Recall challenge: {len(questions)} questions\n")

    if quiet:
        checkpoint = LongitudinalCheckpoint(
            checkpoint_number=checkpoint_number,
            runs_completed_at_checkpoint=len(results),
            challenge_tasks=questions,
            correct_answers=0,
            total_questions=len(questions),
            track_a_recall_score=0.0,
            track_b_recall_score=0.0,
            time_to_answer_seconds=0.0,
        )
        with checkpoints_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(checkpoint.to_dict()) + "\n")
        print(f"Recorded checkpoint scaffold #{checkpoint_number} (quiet mode).")
        return

    track_a_correct = 0
    track_b_correct = 0
    total_time = 0.0

    for i, q in enumerate(questions, 1):
        print(f"Q{i}: {q}")
        a_recall = _prompt_bool("  Track A (operator recall) — answered correctly?")
        b_recall = _prompt_bool("  Track B (cockpit surfaced answer)?", True)
        t = _prompt_float("  time_to_answer_seconds")
        track_a_correct += 1 if a_recall else 0
        track_b_correct += 1 if b_recall else 0
        total_time += t

    total_q = max(len(questions), 1)
    checkpoint = LongitudinalCheckpoint(
        checkpoint_number=checkpoint_number,
        runs_completed_at_checkpoint=len(results),
        challenge_tasks=questions,
        correct_answers=track_b_correct,
        total_questions=len(questions),
        track_a_recall_score=track_a_correct / total_q,
        track_b_recall_score=track_b_correct / total_q,
        time_to_answer_seconds=total_time / total_q,
    )

    with checkpoints_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(checkpoint.to_dict()) + "\n")

    print(f"\nCheckpoint #{checkpoint_number} recorded.")
    print(
        f"  Track A recall: {checkpoint.track_a_recall_score * 100:.0f}%  "
        f"Track B recall: {checkpoint.track_b_recall_score * 100:.0f}%  "
        f"Avg time: {checkpoint.time_to_answer_seconds:.1f}s"
    )


# ---------------------------------------------------------------------------
# --multi-project (Gap 3 pressure test)
# ---------------------------------------------------------------------------


def run_multi_project(quiet: bool = False) -> None:
    registry = TaskRegistry()
    store = ResultStore()

    print("\n=== C29 Multi-Project Pressure Test (Gap 3) ===")
    print("Sequence: Start A -> INTERRUPT -> B -> INTERRUPT -> C -> return to A")

    if quiet:
        print("--multi-project requires interactive input; --quiet not supported.")
        return

    track = Track(
        _prompt_choice(
            "Which track is this sequence?",
            (Track.A_LEGACY.value, Track.B_UMH.value),
        )
    )
    evidence_class = EvidenceClass(
        _prompt_choice(
            "evidence_class for all switches",
            tuple(ec.value for ec in EvidenceClass),
            EvidenceClass.B_CONTROLLED.value,
        )
    )

    steps = [
        ("Task A", "start"),
        ("Task B", "interrupt-to"),
        ("Task C", "interrupt-to"),
        ("Task A", "return"),
    ]
    print("\nFor each transition, record the switch as an InterruptionResult.")

    switch_records: list[tuple[str, InterruptionResult]] = []
    prev_label: str | None = None
    for label, kind in steps:
        if kind == "start":
            print(f"\n[1] Start {label}")
            prev_label = label
            continue

        verb = "Return to" if kind == "return" else "INTERRUPT -> switch to"
        print(f"\n[switch] {verb} {label} (from {prev_label})")
        host_task_id = _prompt("host task_id for this switch (e.g. c29-040)")
        if not host_task_id:
            print("  Skipping switch (no task_id).")
            prev_label = label
            continue

        interruption = InterruptionResult(
            interruption_type="TASK_SWITCH",
            interruption_from=prev_label or "",
            interruption_to=label,
            away_duration_seconds=_prompt_float("away_duration_seconds"),
            resume_time_seconds=_prompt_float("resume_time_seconds"),
            context_accuracy=_prompt_float("context_accuracy (0-1)"),
            decisions_recalled=_prompt_int("decisions_recalled"),
            decisions_total=_prompt_int("decisions_total"),
            work_recovery_complete=_prompt_bool("work_recovery_complete"),
        )
        switch_records.append((host_task_id, interruption))
        prev_label = label

    now = _now_iso()
    for host_task_id, interruption in switch_records:
        if registry.get(host_task_id) is None:
            print(f"  Warning: task '{host_task_id}' not registered — recording anyway.")
        result = TrackResult(
            task_id=host_task_id,
            track=track,
            evidence_class=evidence_class,
            started_at=now,
            completed_at=now,
            duration_seconds=interruption.away_duration_seconds
            + interruption.resume_time_seconds,
            outcome=Outcome.SUCCESS
            if interruption.work_recovery_complete
            else Outcome.PARTIAL,
            interruption_test=interruption,
            notes=(
                "Multi-project pressure switch: "
                f"{interruption.interruption_from} -> {interruption.interruption_to}"
            ),
        )
        store.record(result)

    print(
        f"\nRecorded {len(switch_records)} interruption switches for the pressure run."
    )


# ---------------------------------------------------------------------------
# --report
# ---------------------------------------------------------------------------


def run_report() -> None:
    """Generate the full certification report via c29_report if available."""
    try:
        from tests.certification import c29_report  # type: ignore
    except ImportError:
        print("c29_report.py not available yet — falling back to inline score summary.\n")
        show_score()
        return

    if hasattr(c29_report, "generate_report"):
        c29_report.generate_report()
    else:
        show_score()


# ---------------------------------------------------------------------------
# --next (task recommendation engine)
# ---------------------------------------------------------------------------


def show_next(count: int = 5) -> None:
    """Recommend the next tasks to run based on coverage gaps."""
    registry = TaskRegistry()
    store = ResultStore()
    tasks = registry.list_all()
    results = store.list_all()

    completed_ids: dict[str, set[str]] = {}
    for r in results:
        completed_ids.setdefault(r.task_id, set()).add(r.track.value)

    fully_done = {
        tid
        for tid, tracks in completed_ids.items()
        if Track.A_LEGACY.value in tracks and Track.B_UMH.value in tracks
    }
    partial = {
        tid
        for tid, tracks in completed_ids.items()
        if tid not in fully_done
    }

    cat_counts: dict[str, int] = {c.value: 0 for c in BenchmarkCategory}
    proj_counts: dict[str, int] = {p: 0 for p in _PROJECTS}
    for tid in fully_done:
        t = registry.get(tid)
        if t:
            cat_counts[t.category.value] = cat_counts.get(t.category.value, 0) + 1
            proj_counts[t.project] = proj_counts.get(t.project, 0) + 1

    evidence_dist = store.evidence_distribution()
    total_results = sum(evidence_dist.values())
    class_a_ratio = evidence_dist.get("A_PRODUCTION", 0) / max(total_results, 1)

    print("\nC29 NEXT TASKS — RECOMMENDED EXECUTION ORDER")
    print("=" * 55)

    print(f"\nProgress: {len(fully_done)} paired / {len(partial)} partial / "
          f"{len(tasks) - len(fully_done) - len(partial)} unstarted")

    if partial:
        print(f"\n--- Complete partial runs first ({len(partial)}) ---")
        for tid in sorted(partial):
            t = registry.get(tid)
            tracks_done = completed_ids[tid]
            missing = "Track A" if Track.A_LEGACY.value not in tracks_done else "Track B"
            if t:
                print(f"  {tid}: {t.title} — needs {missing}")

    weak_cats = sorted(cat_counts.items(), key=lambda x: x[1])[:2]
    weak_projs = sorted(proj_counts.items(), key=lambda x: x[1])[:2]

    not_started = [
        t for t in tasks
        if t.task_id not in completed_ids
    ]

    def _priority(task: BenchmarkTask) -> tuple[int, int, int]:
        cat_score = cat_counts.get(task.category.value, 0)
        proj_score = proj_counts.get(task.project, 0)
        is_multi = 1 if "[MULTI-PROJECT]" in task.title else 0
        is_drift = 1 if "[DRIFT]" in task.title else 0
        special_bonus = -(is_multi + is_drift)
        complexity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        return (cat_score + proj_score, special_bonus, complexity_order.get(task.complexity.value, 1))

    ranked = sorted(not_started, key=_priority)

    print(f"\n--- Next {min(count, len(ranked))} recommended tasks ---")
    print(f"  (weakest categories: {[c[0] for c in weak_cats]})")
    print(f"  (weakest projects:   {[p[0] for p in weak_projs]})")
    if class_a_ratio < 0.5 and total_results > 0:
        print(f"  Warning: Class A evidence only {class_a_ratio*100:.0f}% — prioritize production runs")
    print()

    for i, t in enumerate(ranked[:count], 1):
        tags = []
        if "[MULTI-PROJECT]" in t.title:
            tags.append("MULTI")
        if "[DRIFT]" in t.title:
            tags.append("DRIFT")
        tag_str = f" [{','.join(tags)}]" if tags else ""
        print(f"  {i}. {t.task_id}: {t.title}")
        print(f"     {t.category.value} / {t.project} / {t.complexity.value}{tag_str}")

    remaining_multi = sum(
        1 for t in not_started if "[MULTI-PROJECT]" in t.title
    )
    remaining_drift = sum(
        1 for t in not_started if "[DRIFT]" in t.title
    )
    print(f"\nRemaining: {len(not_started)} tasks "
          f"({remaining_multi} multi-project, {remaining_drift} drift)")

    completed_runs = len(results)
    next_checkpoint_at = ((completed_runs // 10) + 1) * 10
    if completed_runs > 0 and completed_runs >= next_checkpoint_at - 2:
        print(f"\n  Checkpoint due at run {next_checkpoint_at} "
              f"({next_checkpoint_at - completed_runs} runs away)")


# ---------------------------------------------------------------------------
# --list-tasks (browse corpus)
# ---------------------------------------------------------------------------


def list_tasks(
    filter_category: str | None = None,
    filter_project: str | None = None,
) -> None:
    """List all tasks in the corpus with optional filters."""
    registry = TaskRegistry()
    store = ResultStore()
    tasks = registry.list_all()
    results = store.list_all()

    completed_ids: dict[str, set[str]] = {}
    for r in results:
        completed_ids.setdefault(r.task_id, set()).add(r.track.value)

    if filter_category:
        tasks = [t for t in tasks if t.category.value == filter_category.upper()]
    if filter_project:
        tasks = [t for t in tasks if t.project == filter_project]

    print(f"\nC29 TASK CORPUS — {len(tasks)} tasks")
    if filter_category:
        print(f"  Filter: category={filter_category.upper()}")
    if filter_project:
        print(f"  Filter: project={filter_project}")
    print("=" * 70)

    for t in tasks:
        tracks_done = completed_ids.get(t.task_id, set())
        if Track.A_LEGACY.value in tracks_done and Track.B_UMH.value in tracks_done:
            status = "DONE"
        elif tracks_done:
            missing = "A" if Track.A_LEGACY.value not in tracks_done else "B"
            status = f"PART({missing})"
        else:
            status = "    "

        tags = ""
        if "[MULTI-PROJECT]" in t.title:
            tags = " [M]"
        elif "[DRIFT]" in t.title:
            tags = " [D]"

        clean_title = t.title.replace("[MULTI-PROJECT] ", "").replace("[DRIFT] ", "")
        print(
            f"  {status:6s}  {t.task_id}  {t.category.value:<10s}  "
            f"{t.project:<16s}  {t.complexity.value:<6s}  {clean_title[:40]}{tags}"
        )


# ---------------------------------------------------------------------------
# --dashboard (incremental progress)
# ---------------------------------------------------------------------------


def show_dashboard() -> None:
    """Show running dashboard with incremental scores and coverage gaps."""
    registry = TaskRegistry()
    store = ResultStore()
    results = store.list_all()
    tasks = registry.list_all()

    print("\nC29 HARNESS SUPERIORITY — DASHBOARD")
    print("=" * 60)

    if not results:
        print("\nNo results yet. Start with:")
        print("  python3 tests/certification/c29_benchmark.py --next")
        print("  python3 tests/certification/c29_benchmark.py --record-legacy <id>")
        print("  python3 tests/certification/c29_benchmark.py --record-umh <id>")
        return

    legacy, umh = _split_tracks(results)
    dist = store.evidence_distribution()

    print(f"\n--- Progress ---")
    print(f"Total runs:     {len(results)}  (Legacy: {len(legacy)}, UMH: {len(umh)})")
    print(f"Evidence:       A={dist['A_PRODUCTION']}  B={dist['B_CONTROLLED']}  "
          f"C={dist['C_SYNTHETIC']}")

    completed_ids: dict[str, set[str]] = {}
    for r in results:
        completed_ids.setdefault(r.task_id, set()).add(r.track.value)
    paired = sum(
        1 for tracks in completed_ids.values()
        if Track.A_LEGACY.value in tracks and Track.B_UMH.value in tracks
    )
    print(f"Paired runs:    {paired} / {len(tasks)}")

    cat_done: dict[str, int] = {c.value: 0 for c in BenchmarkCategory}
    proj_done: dict[str, int] = {p: 0 for p in _PROJECTS}
    for tid, tracks in completed_ids.items():
        if Track.A_LEGACY.value in tracks and Track.B_UMH.value in tracks:
            t = registry.get(tid)
            if t:
                cat_done[t.category.value] = cat_done.get(t.category.value, 0) + 1
                proj_done[t.project] = proj_done.get(t.project, 0) + 1

    print(f"\n--- Category Coverage ---")
    for cat in BenchmarkCategory:
        total = sum(1 for t in tasks if t.category == cat)
        done = cat_done.get(cat.value, 0)
        bar_len = 20
        filled = int(bar_len * done / max(total, 1))
        bar = "#" * filled + "." * (bar_len - filled)
        print(f"  {cat.value:<10s}  [{bar}]  {done}/{total}")

    print(f"\n--- Project Coverage ---")
    for proj in _PROJECTS:
        total = sum(1 for t in tasks if t.project == proj)
        done = proj_done.get(proj, 0)
        bar_len = 20
        filled = int(bar_len * done / max(total, 1))
        bar = "#" * filled + "." * (bar_len - filled)
        print(f"  {proj:<16s}  [{bar}]  {done}/{total}")

    if paired >= 1:
        print(f"\n--- Running Scores (from {paired} paired runs) ---")
        try:
            scorer, hti_calc, metrics, verdict_engine, _ = _build_engines()
            dims = scorer.compute_all()
            for name, d in dims.items():
                label = _DIM_LABELS.get(name, name)
                delta = d["delta"]
                sign = "+" if delta >= 0 else ""
                winner = "UMH" if delta > 0 else "Legacy" if delta < 0 else "Tie"
                print(f"  {label:<22s}: d {sign}{delta:.2f}  ({winner})")

            hti = hti_calc.hti_score()
            print(f"\n  HTI: {hti:.1f} / 100  (target >90)")

            pass_report = metrics.pass_report()
            passing = sum(1 for m in pass_report.values() if m["passed"])
            total_metrics = len(pass_report)
            print(f"  Metrics: {passing}/{total_metrics} passing")

            verdict = verdict_engine.derive_verdict()
            verdict_val = verdict.verdict
            if isinstance(verdict_val, MVPVerdictLevel):
                verdict_val = verdict_val.value
            print(f"  Verdict: {verdict_val}")
        except Exception as e:
            print(f"  (scoring error: {e})")

    ab_count = dist["A_PRODUCTION"] + dist["B_CONTROLLED"]
    ab_needed = 15 - ab_count
    print(f"\n--- Readiness ---")
    print(f"  Min 15 A+B runs: {ab_count}/15 "
          f"{'PASS' if ab_needed <= 0 else f'(need {ab_needed} more)'}")
    print(f"  Min 20 total runs: {len(results)}/20 "
          f"{'PASS' if len(results) >= 20 else f'(need {20 - len(results)} more)'}")

    next_checkpoint = ((len(results) // 10) + 1) * 10
    print(f"  Next checkpoint: run {next_checkpoint} "
          f"({next_checkpoint - len(results)} away)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="C29 Harness Superiority Benchmark Runner"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--register-task", action="store_true", help="Interactive task registration"
    )
    group.add_argument(
        "--record-legacy", metavar="TASK_ID", help="Record a Track A (Legacy) result"
    )
    group.add_argument(
        "--record-umh", metavar="TASK_ID", help="Record a Track B (UMH) result"
    )
    group.add_argument(
        "--score", action="store_true", help="Compute and display all scores"
    )
    group.add_argument(
        "--report", action="store_true", help="Generate full certification report"
    )
    group.add_argument("--status", action="store_true", help="Show registry status")
    group.add_argument(
        "--checkpoint",
        action="store_true",
        help="Run a longitudinal continuity checkpoint",
    )
    group.add_argument(
        "--multi-project",
        action="store_true",
        help="Run a multi-project pressure test",
    )
    group.add_argument(
        "--next",
        action="store_true",
        help="Recommend next tasks based on coverage gaps",
    )
    group.add_argument(
        "--list-tasks",
        action="store_true",
        help="List all tasks in the corpus",
    )
    group.add_argument(
        "--dashboard",
        action="store_true",
        help="Show running dashboard with incremental scores",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress interactive prompts (scripted use)",
    )
    parser.add_argument(
        "--no-evidence",
        action="store_true",
        help="Skip Beast browser evidence on Track B",
    )
    parser.add_argument(
        "--category",
        help="Filter --list-tasks by category",
    )
    parser.add_argument(
        "--project",
        help="Filter --list-tasks by project",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of tasks to show with --next (default: 5)",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        if args.register_task:
            register_task(quiet=args.quiet)
        elif args.record_legacy:
            record_legacy(args.record_legacy, quiet=args.quiet)
        elif args.record_umh:
            record_umh(
                args.record_umh, quiet=args.quiet, collect_evidence=not args.no_evidence
            )
        elif args.score:
            show_score()
        elif args.report:
            run_report()
        elif args.status:
            show_status()
        elif args.checkpoint:
            run_checkpoint(quiet=args.quiet)
        elif args.multi_project:
            run_multi_project(quiet=args.quiet)
        elif args.next:
            show_next(count=args.count)
        elif args.list_tasks:
            list_tasks(filter_category=args.category, filter_project=args.project)
        elif args.dashboard:
            show_dashboard()
    except KeyboardInterrupt:
        print("\nInterrupted. No partial record written for the current entry.")
        return 130

    return 0


if __name__ == "__main__":
    sys.exit(main())
