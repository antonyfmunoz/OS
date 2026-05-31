"""JarvisReadinessGate — Phase 13.4 readiness assessment.

Checks whether UMH operational truth meets the minimum bar for running
the True Jarvis End-to-End Acceptance Test. Produces a JarvisReadinessReport
with blocking issues, warnings, and required operator actions.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from substrate.organism.operational_truth import (
    OperationalReadinessStatus,
    OperationalTruthSnapshot,
    collect_snapshot,
)

logger = logging.getLogger(__name__)


@dataclass
class JarvisReadinessReport:
    ready: bool = False
    blocking_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    degraded_modes: list[str] = field(default_factory=list)
    required_operator_actions: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "blocking_issues": self.blocking_issues,
            "warnings": self.warnings,
            "degraded_modes": self.degraded_modes,
            "required_operator_actions": self.required_operator_actions,
            "evidence": self.evidence,
        }


def assess_readiness(
    snapshot: OperationalTruthSnapshot | None = None,
    repo_root: str | None = None,
    deterministic_only: bool = False,
) -> JarvisReadinessReport:
    """Assess whether Phase 13.4 can proceed.

    Args:
        snapshot: Pre-collected snapshot. If None, collects a live one.
        repo_root: Repository root path.
        deterministic_only: If True, skips the LLM provider requirement.
    """
    root = Path(repo_root or os.environ.get("UMH_ROOT", "/opt/OS"))
    if snapshot is None:
        snapshot = collect_snapshot(str(root))

    report = JarvisReadinessReport()
    report.evidence["snapshot_id"] = snapshot.snapshot_id
    report.evidence["created_at"] = snapshot.created_at

    has_llm = False
    for provider in snapshot.llm_provider_state:
        if provider.available:
            has_llm = True
            break
    if not has_llm and not deterministic_only:
        report.blocking_issues.append(
            "No capable LLM provider available. Either restore a provider "
            "or explicitly run in deterministic-only mode."
        )
    elif not has_llm and deterministic_only:
        report.degraded_modes.append("Running in deterministic-only mode — no LLM intelligence")
    report.evidence["llm_available"] = has_llm
    report.evidence["deterministic_only"] = deterministic_only

    journal_path = root / "data" / "umh" / "organism" / "execution_journal.jsonl"
    journal_has_entries = False
    if journal_path.exists():
        try:
            journal_has_entries = journal_path.stat().st_size > 0
        except OSError:
            pass
    if not journal_has_entries:
        report.blocking_issues.append("execution_journal.jsonl has 0 entries — trace recording broken")
    report.evidence["journal_has_entries"] = journal_has_entries

    hook_path = root / ".git" / "hooks" / "pre-commit"
    gates_wired = 0
    if hook_path.exists():
        try:
            content = hook_path.read_text()
            for gate in ["check_type_divergence", "check_instance_leak",
                         "check_projection_leak", "check_dependency_direction"]:
                if gate in content:
                    gates_wired += 1
        except OSError:
            pass
    if gates_wired < 4:
        report.blocking_issues.append(f"Only {gates_wired}/4 pre-commit gates wired")
    report.evidence["precommit_gates_wired"] = gates_wired

    eventbus_resolved = "resolved" in snapshot.eventbus_state.lower() or \
                        "handled" in snapshot.eventbus_state.lower() or \
                        "classified" in snapshot.eventbus_state.lower() or \
                        "diagnostic" in snapshot.eventbus_state.lower()
    if not eventbus_resolved and snapshot.eventbus_state:
        report.warnings.append(f"EventBus cadence issue: {snapshot.eventbus_state}")
    report.evidence["eventbus_state"] = snapshot.eventbus_state

    graph_path = root / "data" / "codebase_graph.json"
    graph_fresh = False
    if graph_path.exists():
        try:
            age_hours = (time.time() - graph_path.stat().st_mtime) / 3600
            graph_fresh = age_hours < 48
            if not graph_fresh:
                report.warnings.append(f"Knowledge graph is {age_hours:.0f}h stale")
        except OSError:
            pass
    else:
        report.warnings.append("Knowledge graph missing")
    report.evidence["graph_fresh"] = graph_fresh

    if snapshot.disk_usage_percent > 90:
        report.blocking_issues.append(
            f"Disk usage at {snapshot.disk_usage_percent}% — critical threshold"
        )
    elif snapshot.disk_usage_percent > 85:
        report.warnings.append(f"Disk usage at {snapshot.disk_usage_percent}% — approaching danger")
    report.evidence["disk_usage_percent"] = snapshot.disk_usage_percent

    cockpit_ok = "accessible" in snapshot.cockpit_state.lower() or \
                 "healthy" in snapshot.cockpit_state.lower()
    if not cockpit_ok and snapshot.cockpit_state:
        report.warnings.append(f"Cockpit: {snapshot.cockpit_state}")
    report.evidence["cockpit_state"] = snapshot.cockpit_state

    report.evidence["readiness_verdict"] = snapshot.readiness_verdict.value

    report.ready = len(report.blocking_issues) == 0
    return report


def persist_readiness_report(
    report: JarvisReadinessReport,
    persist_dir: str | None = None,
) -> Path:
    """Write readiness report to JSON file."""
    base = Path(persist_dir or os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "umh", "operational_truth",
    ))
    base.mkdir(parents=True, exist_ok=True)
    path = base / "phase13_3s_jarvis_readiness_report.json"
    with open(path, "w") as f:
        json.dump(report.to_dict(), f, indent=2, default=str)
    return path
