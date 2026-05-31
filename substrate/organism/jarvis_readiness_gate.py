"""JarvisReadinessGate — Phase 13.4 readiness assessment.

Phase 13.4M correction: standard mode is blocked only when NO capable
governed runtime path exists — not merely when cloud API quota is exhausted.
Claude Code CLI, Codex, OpenCode, Hermes, Windows Beast, and other
subscription/CLI runtimes are all valid governed runtime paths that do not
require cloud API credits.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
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
    standard_ready: bool = False
    deterministic_only_ready: bool = False
    blocking_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    degraded_modes: list[str] = field(default_factory=list)
    required_operator_actions: list[str] = field(default_factory=list)
    capable_runtimes: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "standard_ready": self.standard_ready,
            "deterministic_only_ready": self.deterministic_only_ready,
            "blocking_issues": self.blocking_issues,
            "warnings": self.warnings,
            "degraded_modes": self.degraded_modes,
            "required_operator_actions": self.required_operator_actions,
            "capable_runtimes": self.capable_runtimes,
            "evidence": self.evidence,
        }


def _detect_cli_runtime(name: str) -> dict[str, Any]:
    """Check if a CLI runtime tool is installed and reachable."""
    binary = shutil.which(name)
    if binary:
        return {"installed": True, "path": binary}
    return {"installed": False, "path": ""}


def _detect_runtime_fleet(root: Path) -> list[dict[str, Any]]:
    """Detect available governed runtime paths on this host."""
    runtimes: list[dict[str, Any]] = []

    cc = _detect_cli_runtime("claude")
    runtimes.append({
        "provider": "claude_code",
        "installed": cc["installed"],
        "capable": cc["installed"],
        "cost_model": "subscription",
        "evidence": cc,
    })

    try:
        import importlib
        mod = importlib.import_module("substrate.organism.shell_runtime_adapter")
        adapter = mod.ShellRuntimeAdapter()
        shell_ok = adapter.is_available()
    except Exception:
        shell_ok = False
    runtimes.append({
        "provider": "shell",
        "installed": True,
        "capable": shell_ok,
        "cost_model": "free",
        "evidence": {"available": shell_ok},
    })

    for tool in ("codex", "opencode", "hermes"):
        info = _detect_cli_runtime(tool)
        runtimes.append({
            "provider": tool,
            "installed": info["installed"],
            "capable": info["installed"],
            "cost_model": "subscription" if tool == "codex" else "unknown",
            "evidence": info,
        })

    ollama = _detect_cli_runtime("ollama")
    runtimes.append({
        "provider": "ollama",
        "installed": ollama["installed"],
        "capable": ollama["installed"],
        "cost_model": "free",
        "evidence": ollama,
    })

    has_cloud_llm = False
    try:
        from substrate.organism.operational_truth import collect_snapshot as _cs
        snap = _cs(str(root))
        for p in snap.llm_provider_state:
            if p.available:
                has_cloud_llm = True
                break
    except Exception:
        pass
    runtimes.append({
        "provider": "cloud_api",
        "installed": True,
        "capable": has_cloud_llm,
        "cost_model": "per_token",
        "evidence": {"any_cloud_llm_available": has_cloud_llm},
    })

    return runtimes


def assess_readiness(
    snapshot: OperationalTruthSnapshot | None = None,
    repo_root: str | None = None,
    deterministic_only: bool = False,
) -> JarvisReadinessReport:
    """Assess whether Phase 13.4 can proceed.

    Phase 13.4M correction: standard mode is ready when ANY capable
    governed runtime path exists (Claude Code, Codex, shell, etc.).
    Cloud API exhaustion alone does NOT block standard mode.
    """
    root = Path(repo_root or os.environ.get("UMH_ROOT", "/opt/OS"))
    if snapshot is None:
        snapshot = collect_snapshot(str(root))

    report = JarvisReadinessReport()
    report.evidence["snapshot_id"] = snapshot.snapshot_id
    report.evidence["created_at"] = snapshot.created_at

    fleet = _detect_runtime_fleet(root)
    report.evidence["runtime_fleet"] = fleet

    capable = [r for r in fleet if r["capable"]]
    report.capable_runtimes = [r["provider"] for r in capable]
    has_capable_runtime = len(capable) > 0
    report.evidence["capable_runtime_count"] = len(capable)
    report.evidence["capable_runtime_providers"] = report.capable_runtimes

    has_cloud_llm = any(
        r["provider"] == "cloud_api" and r["capable"] for r in fleet
    )
    report.evidence["llm_cloud_available"] = has_cloud_llm

    if not has_cloud_llm:
        non_cloud_capable = [r["provider"] for r in capable if r["provider"] != "cloud_api"]
        if non_cloud_capable:
            report.warnings.append(
                f"Cloud API quota exhausted — using subscription/CLI runtimes: "
                f"{', '.join(non_cloud_capable)}"
            )
        else:
            report.warnings.append("No cloud API provider available")

    if not has_capable_runtime and not deterministic_only:
        report.blocking_issues.append(
            "No capable governed runtime path available. Install or authenticate "
            "Claude Code, Codex, OpenCode, Hermes, or restore a cloud provider."
        )
    elif not has_capable_runtime and deterministic_only:
        report.degraded_modes.append(
            "Deterministic-only mode — no governed runtime path available"
        )

    report.evidence["deterministic_only"] = deterministic_only

    journal_path = root / "data" / "umh" / "organism" / "execution_journal.jsonl"
    journal_has_entries = False
    if journal_path.exists():
        try:
            journal_has_entries = journal_path.stat().st_size > 0
        except OSError:
            pass
    if not journal_has_entries:
        report.blocking_issues.append(
            "execution_journal.jsonl has 0 entries — trace recording broken"
        )
    report.evidence["journal_has_entries"] = journal_has_entries

    git_dir = root / ".git"
    if git_dir.is_file():
        try:
            gitdir_line = git_dir.read_text().strip()
            if gitdir_line.startswith("gitdir:"):
                real_git = Path(gitdir_line.split(":", 1)[1].strip())
                if not real_git.is_absolute():
                    real_git = root / real_git
                hook_dir = real_git.parent.parent / "hooks"
            else:
                hook_dir = git_dir / "hooks"
        except OSError:
            hook_dir = git_dir / "hooks"
    else:
        hook_dir = git_dir / "hooks"
    hook_path = hook_dir / "pre-commit"
    gates_wired = 0
    if hook_path.exists():
        try:
            content = hook_path.read_text()
            for gate in [
                "check_type_divergence", "check_instance_leak",
                "check_projection_leak", "check_dependency_direction",
            ]:
                if gate in content:
                    gates_wired += 1
        except OSError:
            pass
    if gates_wired < 4:
        report.blocking_issues.append(
            f"Only {gates_wired}/4 pre-commit gates wired"
        )
    report.evidence["precommit_gates_wired"] = gates_wired

    eventbus_resolved = (
        "resolved" in snapshot.eventbus_state.lower()
        or "handled" in snapshot.eventbus_state.lower()
        or "classified" in snapshot.eventbus_state.lower()
        or "diagnostic" in snapshot.eventbus_state.lower()
    )
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
                report.warnings.append(
                    f"Knowledge graph is {age_hours:.0f}h stale"
                )
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
        report.warnings.append(
            f"Disk usage at {snapshot.disk_usage_percent}% — approaching danger"
        )
    report.evidence["disk_usage_percent"] = snapshot.disk_usage_percent

    cockpit_ok = (
        "accessible" in snapshot.cockpit_state.lower()
        or "healthy" in snapshot.cockpit_state.lower()
    )
    if not cockpit_ok and snapshot.cockpit_state:
        report.warnings.append(f"Cockpit: {snapshot.cockpit_state}")
    report.evidence["cockpit_state"] = snapshot.cockpit_state

    report.evidence["readiness_verdict"] = snapshot.readiness_verdict.value

    report.standard_ready = (
        len(report.blocking_issues) == 0 and has_capable_runtime
    )
    report.deterministic_only_ready = len(report.blocking_issues) == 0
    report.ready = report.standard_ready or (
        report.deterministic_only_ready and deterministic_only
    )
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
