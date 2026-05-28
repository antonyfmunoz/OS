"""Real Workload Runner — governed execution of operational jobs.

Executes real infrastructure maintenance jobs through the organism's
governed execution pipeline:
  - repo health scan
  - stale branch/worktree cleanup scan
  - test run orchestration
  - docker health scan
  - disk/memory pressure scan
  - log rotation scan
  - knowledge duplication/staleness scan

Every job:
  - goes through ExecutionModeManager
  - emits EventSpine events
  - records LeverageMetrics
  - feeds BottleneckEngine
  - updates OperatorCompression
  - produces an outcome record

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from substrate.organism.action_envelope import (
    ActionEnvelope,
    ActionType,
    BlastRadius,
    ExecutionConstraints,
    ReversibilityClass,
)
from substrate.organism.event_spine import EventDomain, EventPriority, EventSpine
from substrate.organism.execution_modes import ExecutionDecision, ExecutionMode, ExecutionModeManager
from substrate.organism.leverage_metrics import LeverageMetrics, TaskRecord
from substrate.organism.operator_compression import OperatorCompression

logger = logging.getLogger(__name__)

_PROBE_TIMEOUT = 30


def _run(cmd: list[str], timeout: int = _PROBE_TIMEOUT) -> tuple[str, int]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip(), result.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.debug("workload command failed: %s — %s", cmd, exc)
        return str(exc), 1


class WorkloadType(str, Enum):
    REPO_HEALTH = "repo_health"
    STALE_BRANCH_SCAN = "stale_branch_scan"
    TEST_RUN = "test_run"
    DOCKER_HEALTH = "docker_health"
    DISK_PRESSURE = "disk_pressure"
    MEMORY_PRESSURE = "memory_pressure"
    LOG_ROTATION = "log_rotation"
    KNOWLEDGE_STALENESS = "knowledge_staleness"
    RUNTIME_RECONCILIATION = "runtime_reconciliation"


class WorkloadRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


_WORKLOAD_RISK: dict[WorkloadType, WorkloadRisk] = {
    WorkloadType.REPO_HEALTH: WorkloadRisk.LOW,
    WorkloadType.STALE_BRANCH_SCAN: WorkloadRisk.LOW,
    WorkloadType.TEST_RUN: WorkloadRisk.LOW,
    WorkloadType.DOCKER_HEALTH: WorkloadRisk.LOW,
    WorkloadType.DISK_PRESSURE: WorkloadRisk.LOW,
    WorkloadType.MEMORY_PRESSURE: WorkloadRisk.LOW,
    WorkloadType.LOG_ROTATION: WorkloadRisk.MEDIUM,
    WorkloadType.KNOWLEDGE_STALENESS: WorkloadRisk.LOW,
    WorkloadType.RUNTIME_RECONCILIATION: WorkloadRisk.MEDIUM,
}

_ESTIMATED_MANUAL_SECONDS: dict[WorkloadType, float] = {
    WorkloadType.REPO_HEALTH: 120.0,
    WorkloadType.STALE_BRANCH_SCAN: 60.0,
    WorkloadType.TEST_RUN: 180.0,
    WorkloadType.DOCKER_HEALTH: 60.0,
    WorkloadType.DISK_PRESSURE: 30.0,
    WorkloadType.MEMORY_PRESSURE: 30.0,
    WorkloadType.LOG_ROTATION: 120.0,
    WorkloadType.KNOWLEDGE_STALENESS: 300.0,
    WorkloadType.RUNTIME_RECONCILIATION: 90.0,
}


@dataclass
class WorkloadOutcome:
    workload_type: WorkloadType
    success: bool
    duration_seconds: float
    findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    timestamp: float = field(default_factory=time.time)
    execution_decision: ExecutionDecision | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workload_type": self.workload_type.value,
            "success": self.success,
            "duration_seconds": round(self.duration_seconds, 2),
            "findings": self.findings[:20],
            "recommendations": self.recommendations[:10],
            "metrics": self.metrics,
            "error": self.error[:500] if self.error else "",
            "timestamp": self.timestamp,
            "decision": self.execution_decision.to_dict() if self.execution_decision else None,
        }


_MAX_OUTCOMES = 500


class WorkloadRunner:
    """Governed execution of real operational workloads.

    All workloads pass through the ExecutionModeManager, emit
    events through the EventSpine, and record LeverageMetrics.
    """

    def __init__(
        self,
        event_spine: EventSpine,
        execution_mode: ExecutionModeManager,
        leverage_metrics: LeverageMetrics,
        operator_compression: OperatorCompression,
        repo_root: str | None = None,
    ) -> None:
        self._spine = event_spine
        self._mode = execution_mode
        self._leverage = leverage_metrics
        self._compression = operator_compression
        self._repo_root = repo_root or os.environ.get("UMH_ROOT", "/opt/OS")
        self._outcomes: list[WorkloadOutcome] = []
        self._total_runs: int = 0
        self._total_successes: int = 0
        self._total_failures: int = 0
        self._governed_spine: Any = None
        self._autonomous_gateway: Any = None

    def set_governed_spine(self, spine: Any) -> None:
        self._governed_spine = spine

    def set_autonomous_gateway(self, gateway: Any) -> None:
        self._autonomous_gateway = gateway

    def create_envelope(self, workload_type: WorkloadType) -> ActionEnvelope:
        """Create an ActionEnvelope for a workload — for spine-routed execution."""
        risk = _WORKLOAD_RISK.get(workload_type, WorkloadRisk.LOW)
        handler = _WORKLOAD_HANDLERS.get(workload_type)

        risk_map = {
            WorkloadRisk.LOW: "low",
            WorkloadRisk.MEDIUM: "medium",
            WorkloadRisk.HIGH: "high",
        }
        reversibility_map = {
            WorkloadRisk.LOW: ReversibilityClass.FULLY_REVERSIBLE,
            WorkloadRisk.MEDIUM: ReversibilityClass.PARTIALLY_REVERSIBLE,
            WorkloadRisk.HIGH: ReversibilityClass.IRREVERSIBLE,
        }

        repo_root = self._repo_root

        def _execute() -> tuple[str, bool]:
            if handler is None:
                return f"No handler for {workload_type.value}", False
            outcome = handler(repo_root)
            return "; ".join(outcome.findings[:5]), outcome.success

        return ActionEnvelope(
            intent=f"Run {workload_type.value} workload",
            action_type=ActionType.STATE,
            source="workload_runner",
            execute_fn=_execute,
            risk_level=risk_map.get(risk, "low"),
            blast_radius=BlastRadius.LOCAL_RUNTIME,
            reversibility=reversibility_map.get(risk, ReversibilityClass.FULLY_REVERSIBLE),
            estimated_manual_seconds=_ESTIMATED_MANUAL_SECONDS.get(workload_type, 60.0),
            constraints=ExecutionConstraints(
                timeout_seconds=120.0,
                require_approval=(risk != WorkloadRisk.LOW),
            ),
            metadata={"mutation_name": workload_type.value, "workload_type": workload_type.value},
        )

    def run_workload_via_gateway(self, workload_type: WorkloadType) -> WorkloadOutcome:
        """Route a mutation-capable workload through the autonomous gateway.

        Creates an ActionEnvelope and submits it via the gateway, which
        enforces autonomous policy before the spine sees it.
        """
        if self._autonomous_gateway is None:
            return self.run_workload(workload_type)

        envelope = self.create_envelope(workload_type)
        result_envelope = self._autonomous_gateway.submit_envelope(envelope)

        success = result_envelope.result_success
        return WorkloadOutcome(
            workload_type=workload_type,
            success=success,
            duration_seconds=max(result_envelope.completed_at - result_envelope.started_at, 0)
            if result_envelope.started_at > 0 else 0.0,
            findings=[result_envelope.result_output[:500]] if result_envelope.result_output else [],
            metrics={"envelope_id": result_envelope.envelope_id, "status": result_envelope.status.value},
        )

    def run_workload(
        self,
        workload_type: WorkloadType,
        force: bool = False,
    ) -> WorkloadOutcome:
        """Execute a single workload through the governance pipeline."""
        self._total_runs += 1
        risk = _WORKLOAD_RISK.get(workload_type, WorkloadRisk.LOW)

        required_mode = ExecutionMode.OBSERVE
        if risk == WorkloadRisk.MEDIUM:
            required_mode = ExecutionMode.ASSISTED
        elif risk == WorkloadRisk.HIGH:
            required_mode = ExecutionMode.AUTONOMOUS

        decision = self._mode.propose_action(
            task_id=f"workload-{workload_type.value}-{int(time.time())}",
            action_description=f"Run {workload_type.value} workload",
            required_mode=required_mode,
            reversible=(risk != WorkloadRisk.HIGH),
        )

        if not decision.approved and not force and risk != WorkloadRisk.LOW:
            outcome = WorkloadOutcome(
                workload_type=workload_type,
                success=False,
                duration_seconds=0.0,
                error=f"Blocked by execution mode: current={self._mode.current_mode.value}, required={required_mode.value}",
                execution_decision=decision,
            )
            self._spine.emit(
                EventDomain.EXECUTION,
                "workload_blocked",
                "workload_runner",
                {"workload": workload_type.value, "mode": self._mode.current_mode.value},
            )
            self._outcomes.append(outcome)
            return outcome

        start = time.monotonic()
        self._spine.emit(
            EventDomain.EXECUTION,
            "workload_started",
            "workload_runner",
            {"workload": workload_type.value, "risk": risk.value},
        )

        handler = _WORKLOAD_HANDLERS.get(workload_type)
        if handler is None:
            outcome = WorkloadOutcome(
                workload_type=workload_type,
                success=False,
                duration_seconds=0.0,
                error=f"No handler for workload type: {workload_type.value}",
                execution_decision=decision,
            )
            self._outcomes.append(outcome)
            return outcome

        try:
            outcome = handler(self._repo_root)
            outcome.execution_decision = decision
        except Exception as exc:
            outcome = WorkloadOutcome(
                workload_type=workload_type,
                success=False,
                duration_seconds=time.monotonic() - start,
                error=str(exc),
                execution_decision=decision,
            )

        outcome.duration_seconds = time.monotonic() - start

        if outcome.success:
            self._total_successes += 1
        else:
            self._total_failures += 1

        self._mode.record_outcome(
            decision.task_id,
            outcome.success,
            result="; ".join(outcome.findings[:3]),
        )

        self._leverage.record_task(TaskRecord(
            task_id=decision.task_id,
            started_at=time.time() - outcome.duration_seconds,
            completed_at=time.time(),
            autonomous=decision.approved,
            required_approval=(not decision.approved and risk != WorkloadRisk.LOW),
            success=outcome.success,
            estimated_manual_seconds=_ESTIMATED_MANUAL_SECONDS.get(workload_type, 60.0),
            actual_seconds=outcome.duration_seconds,
        ))

        self._compression.record_autonomous()

        self._spine.emit(
            EventDomain.EXECUTION,
            "workload_completed",
            "workload_runner",
            {
                "workload": workload_type.value,
                "success": outcome.success,
                "duration_s": round(outcome.duration_seconds, 2),
                "findings": len(outcome.findings),
                "recommendations": len(outcome.recommendations),
            },
            priority=EventPriority.HIGH if not outcome.success else EventPriority.NORMAL,
        )

        if len(self._outcomes) >= _MAX_OUTCOMES:
            self._outcomes = self._outcomes[-(_MAX_OUTCOMES // 2):]
        self._outcomes.append(outcome)

        return outcome

    def run_all_observe(self) -> list[WorkloadOutcome]:
        """Run all OBSERVE-safe workloads (read-only scans)."""
        observe_types = [
            WorkloadType.REPO_HEALTH,
            WorkloadType.STALE_BRANCH_SCAN,
            WorkloadType.DOCKER_HEALTH,
            WorkloadType.DISK_PRESSURE,
            WorkloadType.MEMORY_PRESSURE,
            WorkloadType.KNOWLEDGE_STALENESS,
        ]
        results = []
        for wt in observe_types:
            results.append(self.run_workload(wt))
        return results

    def recent_outcomes(self, limit: int = 20) -> list[dict[str, Any]]:
        return [o.to_dict() for o in self._outcomes[-limit:]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_runs": self._total_runs,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "success_rate": round(
                self._total_successes / max(self._total_runs, 1), 4
            ),
            "recent_outcomes": self.recent_outcomes(5),
        }


def _scan_repo_health(repo_root: str) -> WorkloadOutcome:
    findings: list[str] = []
    recommendations: list[str] = []
    metrics: dict[str, Any] = {}

    status_out, rc = _run(["git", "-C", repo_root, "status", "--porcelain", "-u"])
    uncommitted = len(status_out.splitlines()) if status_out else 0
    metrics["uncommitted_files"] = uncommitted
    if uncommitted > 20:
        findings.append(f"{uncommitted} uncommitted files")
        recommendations.append("Review and commit or gitignore outstanding files")

    branch, _ = _run(["git", "-C", repo_root, "branch", "--show-current"])
    metrics["current_branch"] = branch

    log_out, _ = _run(["git", "-C", repo_root, "log", "--oneline", "-5"])
    metrics["recent_commits"] = log_out.splitlines() if log_out else []

    diff_stat, _ = _run(["git", "-C", repo_root, "diff", "--stat", "HEAD"])
    if diff_stat:
        metrics["unstaged_changes"] = len(diff_stat.splitlines())
        findings.append(f"{len(diff_stat.splitlines())} files with unstaged changes")

    findings.append(f"Branch: {branch}, {uncommitted} uncommitted files")

    return WorkloadOutcome(
        workload_type=WorkloadType.REPO_HEALTH,
        success=True,
        duration_seconds=0.0,
        findings=findings,
        recommendations=recommendations,
        metrics=metrics,
    )


def _scan_stale_branches(repo_root: str) -> WorkloadOutcome:
    findings: list[str] = []
    recommendations: list[str] = []
    metrics: dict[str, Any] = {}

    branches_raw, _ = _run(["git", "-C", repo_root, "branch", "--format", "%(refname:short)"])
    all_branches = [b.strip() for b in branches_raw.splitlines() if b.strip()] if branches_raw else []
    current, _ = _run(["git", "-C", repo_root, "branch", "--show-current"])

    stale = [b for b in all_branches if b not in ("main", current.strip())]
    metrics["total_branches"] = len(all_branches)
    metrics["stale_branches"] = stale

    if stale:
        findings.append(f"{len(stale)} non-main branches: {', '.join(stale[:10])}")
        recommendations.append("Delete merged branches to keep repo clean")

    worktree_raw, _ = _run(["git", "-C", repo_root, "worktree", "list", "--porcelain"])
    worktrees: list[str] = []
    if worktree_raw:
        for line in worktree_raw.splitlines():
            if line.startswith("worktree ") and ".claude/worktrees" in line:
                worktrees.append(line.replace("worktree ", "").strip())

    metrics["worktrees"] = worktrees
    if worktrees:
        findings.append(f"{len(worktrees)} active worktrees")

    return WorkloadOutcome(
        workload_type=WorkloadType.STALE_BRANCH_SCAN,
        success=True,
        duration_seconds=0.0,
        findings=findings,
        recommendations=recommendations,
        metrics=metrics,
    )


def _scan_docker_health(repo_root: str) -> WorkloadOutcome:
    findings: list[str] = []
    recommendations: list[str] = []
    metrics: dict[str, Any] = {}

    output, rc = _run(["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}"])
    if rc != 0:
        return WorkloadOutcome(
            workload_type=WorkloadType.DOCKER_HEALTH,
            success=False,
            duration_seconds=0.0,
            error="docker ps failed",
        )

    running = 0
    stopped = 0
    unhealthy = 0
    containers: list[dict[str, str]] = []

    for line in (output or "").splitlines():
        parts = line.strip().split("|", 1)
        if len(parts) != 2:
            continue
        name, status = parts
        containers.append({"name": name, "status": status})
        status_lower = status.lower()
        if "up" in status_lower:
            running += 1
            if "unhealthy" in status_lower:
                unhealthy += 1
                findings.append(f"Container {name} is unhealthy")
                recommendations.append(f"Investigate and restart {name}")
        else:
            stopped += 1
            findings.append(f"Container {name} is stopped: {status}")

    metrics["running"] = running
    metrics["stopped"] = stopped
    metrics["unhealthy"] = unhealthy
    metrics["containers"] = containers

    findings.insert(0, f"Docker: {running} running, {stopped} stopped, {unhealthy} unhealthy")

    return WorkloadOutcome(
        workload_type=WorkloadType.DOCKER_HEALTH,
        success=True,
        duration_seconds=0.0,
        findings=findings,
        recommendations=recommendations,
        metrics=metrics,
    )


def _scan_disk_pressure(repo_root: str) -> WorkloadOutcome:
    import shutil

    findings: list[str] = []
    recommendations: list[str] = []
    metrics: dict[str, Any] = {}

    try:
        usage = shutil.disk_usage(repo_root)
        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        pct = (usage.used / usage.total) * 100 if usage.total > 0 else 0

        metrics["total_gb"] = round(total_gb, 2)
        metrics["used_gb"] = round(used_gb, 2)
        metrics["free_gb"] = round(free_gb, 2)
        metrics["usage_percent"] = round(pct, 1)

        pressure = "normal"
        if pct > 90:
            pressure = "critical"
            recommendations.append("Disk critically full — clean up immediately")
        elif pct > 80:
            pressure = "high"
            recommendations.append("Disk pressure high — consider cleanup")
        elif pct > 70:
            pressure = "elevated"

        metrics["pressure"] = pressure
        findings.append(f"Disk: {used_gb:.1f}/{total_gb:.1f} GB ({pct:.1f}%), pressure={pressure}")
    except OSError as exc:
        return WorkloadOutcome(
            workload_type=WorkloadType.DISK_PRESSURE,
            success=False,
            duration_seconds=0.0,
            error=str(exc),
        )

    large_logs_out, _ = _run([
        "find", repo_root, "-name", "*.log", "-size", "+10M",
        "-not", "-path", "*/.git/*",
    ])
    if large_logs_out:
        large_logs = large_logs_out.splitlines()
        metrics["large_logs"] = large_logs[:10]
        findings.append(f"{len(large_logs)} log files >10MB")
        recommendations.append("Rotate large log files")

    return WorkloadOutcome(
        workload_type=WorkloadType.DISK_PRESSURE,
        success=True,
        duration_seconds=0.0,
        findings=findings,
        recommendations=recommendations,
        metrics=metrics,
    )


def _scan_memory_pressure(repo_root: str) -> WorkloadOutcome:
    findings: list[str] = []
    metrics: dict[str, Any] = {}

    meminfo_path = Path("/proc/meminfo")
    if not meminfo_path.exists():
        return WorkloadOutcome(
            workload_type=WorkloadType.MEMORY_PRESSURE,
            success=True,
            duration_seconds=0.0,
            findings=["No /proc/meminfo — likely not Linux"],
            metrics={},
        )

    try:
        text = meminfo_path.read_text()
        values: dict[str, float] = {}
        for line in text.splitlines():
            parts = line.split(":")
            if len(parts) == 2:
                key = parts[0].strip()
                val_parts = parts[1].strip().split()
                if val_parts:
                    try:
                        values[key] = float(val_parts[0])
                    except ValueError:
                        pass

        total_kb = values.get("MemTotal", 0)
        avail_kb = values.get("MemAvailable", 0)
        total_mb = total_kb / 1024
        avail_mb = avail_kb / 1024
        pct = ((total_kb - avail_kb) / total_kb) * 100 if total_kb > 0 else 0

        pressure = "normal"
        if pct > 90:
            pressure = "critical"
        elif pct > 80:
            pressure = "high"
        elif pct > 70:
            pressure = "elevated"

        metrics["total_mb"] = round(total_mb, 1)
        metrics["available_mb"] = round(avail_mb, 1)
        metrics["usage_percent"] = round(pct, 1)
        metrics["pressure"] = pressure
        findings.append(f"Memory: {avail_mb:.0f}/{total_mb:.0f} MB available ({pct:.1f}% used), pressure={pressure}")

    except OSError as exc:
        return WorkloadOutcome(
            workload_type=WorkloadType.MEMORY_PRESSURE,
            success=False,
            duration_seconds=0.0,
            error=str(exc),
        )

    return WorkloadOutcome(
        workload_type=WorkloadType.MEMORY_PRESSURE,
        success=True,
        duration_seconds=0.0,
        findings=findings,
        metrics=metrics,
    )


def _scan_log_rotation(repo_root: str) -> WorkloadOutcome:
    findings: list[str] = []
    recommendations: list[str] = []
    metrics: dict[str, Any] = {}

    large_files_out, _ = _run([
        "find", repo_root, "-type", "f",
        "(",
        "-name", "*.log", "-o",
        "-name", "*.jsonl", "-o",
        "-name", "*.jsonl.old",
        ")",
        "-size", "+5M",
        "-not", "-path", "*/.git/*",
        "-not", "-path", "*/node_modules/*",
    ])

    large_files: list[dict[str, Any]] = []
    if large_files_out:
        for f in large_files_out.splitlines():
            f = f.strip()
            if not f:
                continue
            try:
                size = Path(f).stat().st_size
                large_files.append({
                    "path": f.replace(repo_root, ""),
                    "size_mb": round(size / (1024 * 1024), 2),
                })
            except OSError:
                pass

    metrics["large_files_count"] = len(large_files)
    metrics["large_files"] = large_files[:20]

    total_mb = sum(lf["size_mb"] for lf in large_files)
    metrics["total_large_mb"] = round(total_mb, 2)

    findings.append(f"{len(large_files)} files >5MB totaling {total_mb:.1f} MB")
    if large_files:
        recommendations.append("Rotate or compress large log/data files")

    return WorkloadOutcome(
        workload_type=WorkloadType.LOG_ROTATION,
        success=True,
        duration_seconds=0.0,
        findings=findings,
        recommendations=recommendations,
        metrics=metrics,
    )


def _scan_knowledge_staleness(repo_root: str) -> WorkloadOutcome:
    findings: list[str] = []
    recommendations: list[str] = []
    metrics: dict[str, Any] = {}

    knowledge_dir = Path(repo_root) / "knowledge"
    if not knowledge_dir.exists():
        return WorkloadOutcome(
            workload_type=WorkloadType.KNOWLEDGE_STALENESS,
            success=True,
            duration_seconds=0.0,
            findings=["No knowledge/ directory"],
        )

    md_files = list(knowledge_dir.rglob("*.md"))
    metrics["total_knowledge_files"] = len(md_files)

    now = time.time()
    stale_threshold = 30 * 86400
    stale_files: list[str] = []
    for f in md_files:
        try:
            mtime = f.stat().st_mtime
            if (now - mtime) > stale_threshold:
                stale_files.append(str(f).replace(repo_root, ""))
        except OSError:
            pass

    metrics["stale_files"] = stale_files[:20]
    metrics["stale_count"] = len(stale_files)

    findings.append(f"{len(md_files)} knowledge files, {len(stale_files)} stale (>30 days)")
    if stale_files:
        recommendations.append("Review and update stale knowledge files")

    return WorkloadOutcome(
        workload_type=WorkloadType.KNOWLEDGE_STALENESS,
        success=True,
        duration_seconds=0.0,
        findings=findings,
        recommendations=recommendations,
        metrics=metrics,
    )


def _scan_test_run(repo_root: str) -> WorkloadOutcome:
    findings: list[str] = []
    metrics: dict[str, Any] = {}

    out, rc = _run(
        ["python3", "-m", "pytest", "substrate/organism/tests/", "-x", "-q", "--tb=line"],
        timeout=120,
    )

    metrics["exit_code"] = rc
    metrics["output_lines"] = len(out.splitlines()) if out else 0

    last_lines = out.splitlines()[-5:] if out else []
    findings.extend(last_lines)

    return WorkloadOutcome(
        workload_type=WorkloadType.TEST_RUN,
        success=(rc == 0),
        duration_seconds=0.0,
        findings=findings,
        metrics=metrics,
        error="" if rc == 0 else f"Tests failed with exit code {rc}",
    )


def _scan_runtime_reconciliation(repo_root: str) -> WorkloadOutcome:
    findings: list[str] = []
    metrics: dict[str, Any] = {}

    docker_out, _ = _run(["docker", "ps", "--format", "{{.Names}}|{{.Status}}"])
    tmux_out, _ = _run(["tmux", "list-sessions", "-F", "#{session_name}"])
    ps_out, _ = _run(["ps", "aux"])

    running_containers = 0
    if docker_out:
        for line in docker_out.splitlines():
            if "|" in line and "Up" in line:
                running_containers += 1

    tmux_sessions = tmux_out.splitlines() if tmux_out else []
    python_procs = sum(1 for line in (ps_out or "").splitlines() if "python" in line.lower())

    metrics["running_containers"] = running_containers
    metrics["tmux_sessions"] = tmux_sessions
    metrics["python_processes"] = python_procs

    findings.append(
        f"Runtimes: {running_containers} containers, "
        f"{len(tmux_sessions)} tmux sessions, "
        f"{python_procs} python processes"
    )

    return WorkloadOutcome(
        workload_type=WorkloadType.RUNTIME_RECONCILIATION,
        success=True,
        duration_seconds=0.0,
        findings=findings,
        metrics=metrics,
    )


_WORKLOAD_HANDLERS: dict[WorkloadType, Any] = {
    WorkloadType.REPO_HEALTH: _scan_repo_health,
    WorkloadType.STALE_BRANCH_SCAN: _scan_stale_branches,
    WorkloadType.TEST_RUN: _scan_test_run,
    WorkloadType.DOCKER_HEALTH: _scan_docker_health,
    WorkloadType.DISK_PRESSURE: _scan_disk_pressure,
    WorkloadType.MEMORY_PRESSURE: _scan_memory_pressure,
    WorkloadType.LOG_ROTATION: _scan_log_rotation,
    WorkloadType.KNOWLEDGE_STALENESS: _scan_knowledge_staleness,
    WorkloadType.RUNTIME_RECONCILIATION: _scan_runtime_reconciliation,
}
