"""Operator acceptance run model — end-to-end acceptance test tracking.

Phase 13.4. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class AcceptanceRunStatus(str, Enum):
    DRAFTED = "drafted"
    RUNNING = "running"
    WAITING_FOR_PERMISSION = "waiting_for_permission"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    RUNTIME_RUNNING = "runtime_running"
    ARTIFACT_READY = "artifact_ready"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class OperatorAcceptanceRun:
    """A single end-to-end acceptance test run."""

    run_id: str  # "oar-<8hex>"
    acceptance_mode: str  # "standard", "deterministic_only", "blocked"
    operator_session_id: str
    input_text: str
    input_mode: str  # "text", "voice", "api"
    status: AcceptanceRunStatus = AcceptanceRunStatus.DRAFTED
    started_at: str = ""
    completed_at: str = ""
    dex_intent_id: str = ""
    work_packet_id: str = ""
    reconciliation_session_id: str = ""
    diagnostic_report_id: str = ""
    permission_request_ids: list[str] = field(default_factory=list)
    propagation_plan_id: str = ""
    runtime_session_id: str = ""
    selected_runtime: str = ""
    selected_device: str = ""
    placement_decision_id: str = ""
    artifact_paths: list[str] = field(default_factory=list)
    approval_required: bool = False
    human_required: bool = False
    execution_occurred: bool = False
    production_mutation_occurred: bool = False
    external_write_occurred: bool = False
    deterministic_only: bool = True
    degraded_reason: str = ""
    success_criteria: list[str] = field(default_factory=list)
    failure_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON."""
        return {
            "run_id": self.run_id,
            "acceptance_mode": self.acceptance_mode,
            "operator_session_id": self.operator_session_id,
            "input_text": self.input_text,
            "input_mode": self.input_mode,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "dex_intent_id": self.dex_intent_id,
            "work_packet_id": self.work_packet_id,
            "reconciliation_session_id": self.reconciliation_session_id,
            "diagnostic_report_id": self.diagnostic_report_id,
            "permission_request_ids": list(self.permission_request_ids),
            "propagation_plan_id": self.propagation_plan_id,
            "runtime_session_id": self.runtime_session_id,
            "selected_runtime": self.selected_runtime,
            "selected_device": self.selected_device,
            "placement_decision_id": self.placement_decision_id,
            "artifact_paths": list(self.artifact_paths),
            "approval_required": self.approval_required,
            "human_required": self.human_required,
            "execution_occurred": self.execution_occurred,
            "production_mutation_occurred": self.production_mutation_occurred,
            "external_write_occurred": self.external_write_occurred,
            "deterministic_only": self.deterministic_only,
            "degraded_reason": self.degraded_reason,
            "success_criteria": list(self.success_criteria),
            "failure_reason": self.failure_reason,
            "metadata": dict(self.metadata),
        }


@dataclass
class OperatorAcceptanceArtifact:
    """An artifact produced by an operator acceptance run."""

    artifact_id: str  # "oaa-<8hex>"
    run_id: str
    artifact_type: str  # "implementation_plan", "roadmap_status", "reconciliation_report", etc.
    title: str
    path: str
    summary: str
    source_session_id: str = ""
    source_runtime_id: str = ""
    selected_runtime: str = ""
    selected_device: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    deterministic_only: bool = True
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON."""
        return {
            "artifact_id": self.artifact_id,
            "run_id": self.run_id,
            "artifact_type": self.artifact_type,
            "title": self.title,
            "path": self.path,
            "summary": self.summary,
            "source_session_id": self.source_session_id,
            "source_runtime_id": self.source_runtime_id,
            "selected_runtime": self.selected_runtime,
            "selected_device": self.selected_device,
            "evidence": dict(self.evidence),
            "deterministic_only": self.deterministic_only,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def create_run(
    input_text: str,
    input_mode: str,
    acceptance_mode: str,
    operator_session_id: str,
    deterministic_only: bool = True,
    degraded_reason: str = "",
) -> OperatorAcceptanceRun:
    """Create a new acceptance run with a unique ID and timestamp."""
    return OperatorAcceptanceRun(
        run_id=f"oar-{uuid4().hex[:8]}",
        acceptance_mode=acceptance_mode,
        operator_session_id=operator_session_id,
        input_text=input_text,
        input_mode=input_mode,
        status=AcceptanceRunStatus.DRAFTED,
        started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        deterministic_only=deterministic_only,
        degraded_reason=degraded_reason,
    )


def create_artifact(
    run_id: str,
    artifact_type: str,
    title: str,
    path: str,
    summary: str,
    source_session_id: str = "",
    source_runtime_id: str = "",
    evidence: dict[str, Any] | None = None,
    deterministic_only: bool = True,
) -> OperatorAcceptanceArtifact:
    """Create a new acceptance artifact with a unique ID and timestamp."""
    return OperatorAcceptanceArtifact(
        artifact_id=f"oaa-{uuid4().hex[:8]}",
        run_id=run_id,
        artifact_type=artifact_type,
        title=title,
        path=path,
        summary=summary,
        source_session_id=source_session_id,
        source_runtime_id=source_runtime_id,
        evidence=evidence if evidence is not None else {},
        deterministic_only=deterministic_only,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def run_from_dict(data: dict[str, Any]) -> OperatorAcceptanceRun:
    """Reconstruct an *OperatorAcceptanceRun* from a plain dict."""
    d = dict(data)
    d["status"] = AcceptanceRunStatus(d.get("status", "drafted"))
    # Accept legacy "jar-" prefix IDs
    if "run_id" in d and d["run_id"].startswith("jar-"):
        pass  # keep the original ID for continuity
    return OperatorAcceptanceRun(**d)


def artifact_from_dict(data: dict[str, Any]) -> OperatorAcceptanceArtifact:
    """Reconstruct an *OperatorAcceptanceArtifact* from a plain dict."""
    return OperatorAcceptanceArtifact(**data)


# ---------------------------------------------------------------------------
# Persistence (JSONL append-only)
# ---------------------------------------------------------------------------


def _default_persist_dir() -> Path:
    return Path(os.path.join(_REPO_ROOT, "data", "umh", "operator_acceptance"))


def persist_run(
    run: OperatorAcceptanceRun,
    persist_dir: Path | str | None = None,
) -> Path:
    """Append *run* as a single JSON line to ``runs.jsonl``."""
    d = Path(persist_dir) if persist_dir is not None else _default_persist_dir()
    d.mkdir(parents=True, exist_ok=True)
    out = d / "runs.jsonl"
    with open(out, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(run.to_dict(), separators=(",", ":")) + "\n")
    logger.debug("persisted run %s -> %s", run.run_id, out)
    return out


def persist_artifact(
    artifact: OperatorAcceptanceArtifact,
    persist_dir: Path | str | None = None,
) -> Path:
    """Append *artifact* as a single JSON line to ``artifacts.jsonl``."""
    d = Path(persist_dir) if persist_dir is not None else _default_persist_dir()
    d.mkdir(parents=True, exist_ok=True)
    out = d / "artifacts.jsonl"
    with open(out, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(artifact.to_dict(), separators=(",", ":")) + "\n")
    logger.debug("persisted artifact %s -> %s", artifact.artifact_id, out)
    return out


def load_runs(persist_dir: Path | str | None = None) -> list[OperatorAcceptanceRun]:
    """Load all runs from ``runs.jsonl``. Returns empty list if file missing."""
    d = Path(persist_dir) if persist_dir is not None else _default_persist_dir()
    path = d / "runs.jsonl"
    if not path.exists():
        return []
    runs: list[OperatorAcceptanceRun] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            runs.append(run_from_dict(json.loads(line)))
        except Exception:
            logger.warning("skipping malformed run at %s:%d", path, lineno)
    return runs


def load_artifacts(
    persist_dir: Path | str | None = None,
) -> list[OperatorAcceptanceArtifact]:
    """Load all artifacts from ``artifacts.jsonl``. Returns empty list if file missing."""
    d = Path(persist_dir) if persist_dir is not None else _default_persist_dir()
    path = d / "artifacts.jsonl"
    if not path.exists():
        return []
    artifacts: list[OperatorAcceptanceArtifact] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            artifacts.append(artifact_from_dict(json.loads(line)))
        except Exception:
            logger.warning("skipping malformed artifact at %s:%d", path, lineno)
    return artifacts


def get_run(
    run_id: str,
    persist_dir: Path | str | None = None,
) -> OperatorAcceptanceRun | None:
    """Return the run matching *run_id*, or ``None`` if not found."""
    for run in load_runs(persist_dir):
        if run.run_id == run_id:
            return run
    return None
