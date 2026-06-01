"""OperationalTruthSnapshot — scoreboard for UMH operational reality.

Captures the truthful state of UMH's runtime infrastructure at a point
in time. Used by OperatorReadinessGate and the cockpit to display whether
the system is actually operational vs. what documentation claims.

Persistence: JSONL append to data/umh/operational_truth/snapshots.jsonl

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
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class OperationalReadinessStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    CRITICAL = "critical"


class IssuePriority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    P5 = "P5"
    P6 = "P6"


class IssueStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    WONT_FIX = "wont_fix"
    DEFERRED = "deferred"


class FixEffort(str, Enum):
    TRIVIAL = "trivial"
    HOUR = "hour"
    DAY = "day"
    MULTI_DAY = "multi_day"
    WEEK = "week"


@dataclass
class OperationalIssue:
    issue_id: str = field(default_factory=lambda: f"oi-{uuid4().hex[:8]}")
    priority: IssuePriority = IssuePriority.P3
    title: str = ""
    description: str = ""
    impact: str = ""
    fix_effort: FixEffort = FixEffort.DAY
    affected_files: list[str] = field(default_factory=list)
    affected_subsystems: list[str] = field(default_factory=list)
    status: IssueStatus = IssueStatus.OPEN
    evidence: str = ""
    recommended_fix: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "impact": self.impact,
            "fix_effort": self.fix_effort.value,
            "affected_files": self.affected_files,
            "affected_subsystems": self.affected_subsystems,
            "status": self.status.value,
            "evidence": self.evidence,
            "recommended_fix": self.recommended_fix,
            "created_at": self.created_at,
        }


@dataclass
class ContainerState:
    name: str = ""
    status: str = ""
    uptime: str = ""
    port: str = ""
    healthy: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "uptime": self.uptime,
            "port": self.port,
            "healthy": self.healthy,
        }


@dataclass
class ServiceState:
    name: str = ""
    status: str = ""
    active: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "active": self.active,
        }


@dataclass
class LLMProviderState:
    name: str = ""
    configured: bool = False
    available: bool = False
    quota_exhausted: bool = False
    auth_error: bool = False
    last_error_category: str = ""
    recommended_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "configured": self.configured,
            "available": self.available,
            "quota_exhausted": self.quota_exhausted,
            "auth_error": self.auth_error,
            "last_error_category": self.last_error_category,
            "recommended_action": self.recommended_action,
        }


@dataclass
class OperationalTruthSnapshot:
    snapshot_id: str = field(default_factory=lambda: f"ots-{uuid4().hex[:8]}")
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    repo_file_count: int = 0
    active_python_files: int = 0
    active_ts_files: int = 0
    disk_usage_percent: float = 0.0
    ram_usage_percent: float = 0.0
    containers: list[ContainerState] = field(default_factory=list)
    services: list[ServiceState] = field(default_factory=list)
    cron_jobs: int = 0
    llm_provider_state: list[LLMProviderState] = field(default_factory=list)
    cockpit_state: str = ""
    organism_state: str = ""
    execution_journal_state: str = ""
    eventbus_state: str = ""
    precommit_gate_state: str = ""
    knowledge_graph_state: str = ""
    data_hygiene_state: str = ""
    critical_issues: list[OperationalIssue] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    readiness_verdict: OperationalReadinessStatus = OperationalReadinessStatus.DEGRADED

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "repo_file_count": self.repo_file_count,
            "active_python_files": self.active_python_files,
            "active_ts_files": self.active_ts_files,
            "disk_usage_percent": self.disk_usage_percent,
            "ram_usage_percent": self.ram_usage_percent,
            "containers": [c.to_dict() for c in self.containers],
            "services": [s.to_dict() for s in self.services],
            "cron_jobs": self.cron_jobs,
            "llm_provider_state": [p.to_dict() for p in self.llm_provider_state],
            "cockpit_state": self.cockpit_state,
            "organism_state": self.organism_state,
            "execution_journal_state": self.execution_journal_state,
            "eventbus_state": self.eventbus_state,
            "precommit_gate_state": self.precommit_gate_state,
            "knowledge_graph_state": self.knowledge_graph_state,
            "data_hygiene_state": self.data_hygiene_state,
            "critical_issues": [i.to_dict() for i in self.critical_issues],
            "recommended_actions": self.recommended_actions,
            "readiness_verdict": self.readiness_verdict.value,
        }


def collect_snapshot(repo_root: str | None = None) -> OperationalTruthSnapshot:
    """Collect a live operational truth snapshot from the system."""
    root = Path(repo_root or os.environ.get("UMH_ROOT", "/opt/OS"))
    snap = OperationalTruthSnapshot()

    try:
        result = subprocess.run(
            [
                "find", str(root), "-type", "f",
                "-not", "-path", "*/.git/*",
                "-not", "-path", "*/node_modules/*",
                "-not", "-path", "*/__pycache__/*",
                "-not", "-path", "*/.mypy_cache/*",
                "-not", "-path", "*/.ruff_cache/*",
                "-not", "-path", "*/.pytest_cache/*",
            ],
            capture_output=True, text=True, timeout=30,
        )
        snap.repo_file_count = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
    except Exception as exc:
        logger.warning("file count failed: %s", exc)

    try:
        result = subprocess.run(
            ["find", str(root), "-name", "*.py", "-not", "-path", "*/__pycache__/*",
             "-not", "-path", "*/.git/*", "-not", "-path", "*/node_modules/*"],
            capture_output=True, text=True, timeout=30,
        )
        snap.active_python_files = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["find", str(root), "-name", "*.ts", "-o", "-name", "*.tsx",
             "-not", "-path", "*/.git/*", "-not", "-path", "*/node_modules/*"],
            capture_output=True, text=True, timeout=30,
        )
        snap.active_ts_files = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
    except Exception:
        pass

    try:
        usage = shutil.disk_usage("/")
        snap.disk_usage_percent = round((usage.used / usage.total) * 100, 1)
    except Exception:
        pass

    try:
        with open("/proc/meminfo") as f:
            meminfo = f.read()
        total = int([l for l in meminfo.split("\n") if "MemTotal" in l][0].split()[1])
        available = int([l for l in meminfo.split("\n") if "MemAvailable" in l][0].split()[1])
        snap.ram_usage_percent = round(((total - available) / total) * 100, 1)
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Status}}|{{.Ports}}"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|")
            name = parts[0] if len(parts) > 0 else ""
            status = parts[1] if len(parts) > 1 else ""
            port = parts[2] if len(parts) > 2 else ""
            snap.containers.append(ContainerState(
                name=name, status=status, port=port,
                healthy="Up" in status,
            ))
    except Exception:
        pass

    journal_path = root / "data" / "umh" / "organism" / "execution_journal.jsonl"
    if journal_path.exists():
        try:
            lines = sum(1 for _ in open(journal_path))
            snap.execution_journal_state = f"{lines} entries"
        except Exception:
            snap.execution_journal_state = "error reading"
    else:
        snap.execution_journal_state = "file missing"

    hook_path = root / ".git" / "hooks" / "pre-commit"
    if hook_path.exists():
        try:
            content = hook_path.read_text()
            gates = []
            if "check_type_divergence" in content:
                gates.append("type_divergence")
            if "check_instance_leak" in content:
                gates.append("instance_leak")
            if "check_projection_leak" in content:
                gates.append("projection_leak")
            if "check_dependency_direction" in content:
                gates.append("dependency_direction")
            snap.precommit_gate_state = f"{len(gates)}/4 wired: {', '.join(gates)}"
        except Exception:
            snap.precommit_gate_state = "error reading hook"
    else:
        snap.precommit_gate_state = "no pre-commit hook"

    graph_path = root / "data" / "codebase_graph.json"
    if graph_path.exists():
        try:
            mtime = graph_path.stat().st_mtime
            age_hours = (time.time() - mtime) / 3600
            snap.knowledge_graph_state = f"{age_hours:.0f}h old"
        except Exception:
            snap.knowledge_graph_state = "error checking"
    else:
        snap.knowledge_graph_state = "missing"

    metrics_path = root / "data" / "umh" / "mesh" / "metrics.jsonl"
    if metrics_path.exists():
        try:
            size_mb = metrics_path.stat().st_size / (1024 * 1024)
            snap.data_hygiene_state = f"metrics.jsonl: {size_mb:.0f}MB"
        except Exception:
            snap.data_hygiene_state = "error checking"
    else:
        snap.data_hygiene_state = "no metrics file"

    return snap


def persist_snapshot(
    snapshot: OperationalTruthSnapshot,
    persist_dir: str | None = None,
) -> Path:
    """Append snapshot to snapshots.jsonl and return the path."""
    base = Path(persist_dir or os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "umh", "operational_truth",
    ))
    base.mkdir(parents=True, exist_ok=True)
    path = base / "snapshots.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(snapshot.to_dict(), default=str) + "\n")
    return path


def persist_issues(
    issues: list[OperationalIssue],
    persist_dir: str | None = None,
) -> Path:
    """Append issues to issues.jsonl and return the path."""
    base = Path(persist_dir or os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "umh", "operational_truth",
    ))
    base.mkdir(parents=True, exist_ok=True)
    path = base / "issues.jsonl"
    with open(path, "a") as f:
        for issue in issues:
            f.write(json.dumps(issue.to_dict(), default=str) + "\n")
    return path
