"""Runtime fleet model — tracks available runtime providers and selection decisions.

Phase 13.4M. UMH substrate subsystem. Instance-agnostic.
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


# ── Enums ────────────────────────────────────────────────────────────────────


class RuntimeProvider(str, Enum):
    """Available runtime execution providers."""

    CLAUDE_CODE = "claude_code"
    CLAUDE_SDK = "claude_sdk"
    CODEX = "codex"
    OPENCODE = "opencode"
    HERMES = "hermes"
    OLLAMA = "ollama"
    SHELL = "shell"
    BROWSER = "browser"
    COMPUTER_USE = "computer_use"
    HUMAN = "human"
    CLOUD_API = "cloud_api"


class RuntimeCostModel(str, Enum):
    """Cost model classification for runtime providers."""

    SUBSCRIPTION = "subscription"
    FREE = "free"
    PER_TOKEN = "per_token"
    PER_MINUTE = "per_minute"
    UNKNOWN = "unknown"


class RuntimeReadiness(str, Enum):
    """Readiness state of a runtime fleet member."""

    READY = "ready"
    AVAILABLE_NOT_TESTED = "available_not_tested"
    INSTALLED_NOT_CONFIGURED = "installed_not_configured"
    NOT_INSTALLED = "not_installed"
    ERROR = "error"
    DEGRADED = "degraded"
    OFFLINE = "offline"


# ── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class RuntimeFleetMember:
    """A single runtime provider instance within the fleet."""

    runtime_id: str  # "rfm-<8hex>"
    provider: RuntimeProvider
    device_node_id: str
    status: RuntimeReadiness
    capabilities: list[str] = field(default_factory=list)
    cost_model: RuntimeCostModel = RuntimeCostModel.UNKNOWN
    context_window_class: str = ""  # "small", "medium", "large", "unlimited"
    latency_class: str = ""  # "low", "medium", "high"
    reliability_score: float = 0.0  # 0.0-1.0
    allowed_risk: str = "low"  # "low", "medium"
    allowed_workload_types: list[str] = field(default_factory=list)
    blocked_workload_types: list[str] = field(default_factory=list)
    sandbox_required: bool = True
    auth_state: str = ""  # "authenticated", "unauthenticated", "unknown", "subscription"
    last_health_check: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "runtime_id": self.runtime_id,
            "provider": self.provider.value,
            "device_node_id": self.device_node_id,
            "status": self.status.value,
            "capabilities": list(self.capabilities),
            "cost_model": self.cost_model.value,
            "context_window_class": self.context_window_class,
            "latency_class": self.latency_class,
            "reliability_score": self.reliability_score,
            "allowed_risk": self.allowed_risk,
            "allowed_workload_types": list(self.allowed_workload_types),
            "blocked_workload_types": list(self.blocked_workload_types),
            "sandbox_required": self.sandbox_required,
            "auth_state": self.auth_state,
            "last_health_check": self.last_health_check,
            "metadata": dict(self.metadata),
        }


@dataclass
class RuntimeSelection:
    """A recorded decision about which runtime was selected for a work packet."""

    selection_id: str  # "rts-<8hex>"
    work_packet_id: str
    workcell_id: str
    selected_runtime: str  # runtime_id
    selected_device: str  # device_node_id
    reason: str
    alternatives: list[str] = field(default_factory=list)
    rejected_options: list[dict[str, str]] = field(default_factory=list)
    risk_class: str = "low"
    expected_cost: str = "subscription"
    expected_latency: str = "medium"
    expected_quality: str = "high"
    confidence: float = 0.8
    requires_operator_approval: bool = False
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "selection_id": self.selection_id,
            "work_packet_id": self.work_packet_id,
            "workcell_id": self.workcell_id,
            "selected_runtime": self.selected_runtime,
            "selected_device": self.selected_device,
            "reason": self.reason,
            "alternatives": list(self.alternatives),
            "rejected_options": [dict(r) for r in self.rejected_options],
            "risk_class": self.risk_class,
            "expected_cost": self.expected_cost,
            "expected_latency": self.expected_latency,
            "expected_quality": self.expected_quality,
            "confidence": self.confidence,
            "requires_operator_approval": self.requires_operator_approval,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


# ── Factory Functions ────────────────────────────────────────────────────────


def create_fleet_member(
    provider: RuntimeProvider,
    device_node_id: str,
    status: RuntimeReadiness,
    *,
    capabilities: list[str] | None = None,
    cost_model: RuntimeCostModel = RuntimeCostModel.UNKNOWN,
    context_window_class: str = "",
    latency_class: str = "",
    reliability_score: float = 0.0,
    allowed_risk: str = "low",
    allowed_workload_types: list[str] | None = None,
    blocked_workload_types: list[str] | None = None,
    sandbox_required: bool = True,
    auth_state: str = "",
    metadata: dict[str, Any] | None = None,
) -> RuntimeFleetMember:
    """Create a new RuntimeFleetMember with a generated ID and health-check timestamp."""
    return RuntimeFleetMember(
        runtime_id=f"rfm-{uuid4().hex[:8]}",
        provider=provider,
        device_node_id=device_node_id,
        status=status,
        capabilities=capabilities or [],
        cost_model=cost_model,
        context_window_class=context_window_class,
        latency_class=latency_class,
        reliability_score=reliability_score,
        allowed_risk=allowed_risk,
        allowed_workload_types=allowed_workload_types or [],
        blocked_workload_types=blocked_workload_types or [],
        sandbox_required=sandbox_required,
        auth_state=auth_state,
        last_health_check=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        metadata=metadata or {},
    )


def create_selection(
    work_packet_id: str,
    workcell_id: str,
    selected_runtime: str,
    selected_device: str,
    reason: str,
    *,
    alternatives: list[str] | None = None,
    rejected_options: list[dict[str, str]] | None = None,
    risk_class: str = "low",
    expected_cost: str = "subscription",
    expected_latency: str = "medium",
    expected_quality: str = "high",
    confidence: float = 0.8,
    requires_operator_approval: bool = False,
    metadata: dict[str, Any] | None = None,
) -> RuntimeSelection:
    """Create a new RuntimeSelection with a generated ID and timestamp."""
    return RuntimeSelection(
        selection_id=f"rts-{uuid4().hex[:8]}",
        work_packet_id=work_packet_id,
        workcell_id=workcell_id,
        selected_runtime=selected_runtime,
        selected_device=selected_device,
        reason=reason,
        alternatives=alternatives or [],
        rejected_options=rejected_options or [],
        risk_class=risk_class,
        expected_cost=expected_cost,
        expected_latency=expected_latency,
        expected_quality=expected_quality,
        confidence=confidence,
        requires_operator_approval=requires_operator_approval,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        metadata=metadata or {},
    )


# ── Deserialization ──────────────────────────────────────────────────────────


def member_from_dict(data: dict[str, Any]) -> RuntimeFleetMember:
    """Reconstruct a RuntimeFleetMember from a plain dictionary."""
    return RuntimeFleetMember(
        runtime_id=data["runtime_id"],
        provider=RuntimeProvider(data["provider"]),
        device_node_id=data["device_node_id"],
        status=RuntimeReadiness(data["status"]),
        capabilities=data.get("capabilities", []),
        cost_model=RuntimeCostModel(data.get("cost_model", "unknown")),
        context_window_class=data.get("context_window_class", ""),
        latency_class=data.get("latency_class", ""),
        reliability_score=data.get("reliability_score", 0.0),
        allowed_risk=data.get("allowed_risk", "low"),
        allowed_workload_types=data.get("allowed_workload_types", []),
        blocked_workload_types=data.get("blocked_workload_types", []),
        sandbox_required=data.get("sandbox_required", True),
        auth_state=data.get("auth_state", ""),
        last_health_check=data.get("last_health_check", ""),
        metadata=data.get("metadata", {}),
    )


def selection_from_dict(data: dict[str, Any]) -> RuntimeSelection:
    """Reconstruct a RuntimeSelection from a plain dictionary."""
    return RuntimeSelection(
        selection_id=data["selection_id"],
        work_packet_id=data["work_packet_id"],
        workcell_id=data["workcell_id"],
        selected_runtime=data["selected_runtime"],
        selected_device=data["selected_device"],
        reason=data["reason"],
        alternatives=data.get("alternatives", []),
        rejected_options=data.get("rejected_options", []),
        risk_class=data.get("risk_class", "low"),
        expected_cost=data.get("expected_cost", "subscription"),
        expected_latency=data.get("expected_latency", "medium"),
        expected_quality=data.get("expected_quality", "high"),
        confidence=data.get("confidence", 0.8),
        requires_operator_approval=data.get("requires_operator_approval", False),
        timestamp=data.get("timestamp", ""),
        metadata=data.get("metadata", {}),
    )


# ── Persistence ──────────────────────────────────────────────────────────────


def _fleet_path(persist_dir: str | None = None) -> Path:
    """Resolve the fleet JSONL file path."""
    if persist_dir:
        return Path(persist_dir) / "runtime_fleet.jsonl"
    return Path(_REPO_ROOT) / "data" / "umh" / "operational_truth" / "runtime_fleet.jsonl"


def _selections_path(persist_dir: str | None = None) -> Path:
    """Resolve the selections JSONL file path."""
    if persist_dir:
        return Path(persist_dir) / "runtime_selections.jsonl"
    return Path(_REPO_ROOT) / "data" / "umh" / "operational_truth" / "runtime_selections.jsonl"


def persist_fleet(members: list[RuntimeFleetMember], persist_dir: str | None = None) -> Path:
    """Write the full fleet to a JSONL file (overwrites existing)."""
    path = _fleet_path(persist_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for member in members:
            f.write(json.dumps(member.to_dict()) + "\n")
    logger.info("Persisted %d fleet members to %s", len(members), path)
    return path


def persist_selection(selection: RuntimeSelection, persist_dir: str | None = None) -> Path:
    """Append a single selection record to the selections JSONL file."""
    path = _selections_path(persist_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(selection.to_dict()) + "\n")
    logger.info("Persisted selection %s to %s", selection.selection_id, path)
    return path


def load_fleet(persist_dir: str | None = None) -> list[RuntimeFleetMember]:
    """Load fleet members from the JSONL file. Returns empty list if file missing."""
    path = _fleet_path(persist_dir)
    if not path.exists():
        return []
    members: list[RuntimeFleetMember] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                members.append(member_from_dict(json.loads(line)))
    return members


def load_selections(persist_dir: str | None = None) -> list[RuntimeSelection]:
    """Load selection records from the JSONL file. Returns empty list if file missing."""
    path = _selections_path(persist_dir)
    if not path.exists():
        return []
    selections: list[RuntimeSelection] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                selections.append(selection_from_dict(json.loads(line)))
    return selections


# ── Query Functions ──────────────────────────────────────────────────────────


def get_capable_runtimes(fleet: list[RuntimeFleetMember]) -> list[RuntimeFleetMember]:
    """Return fleet members with status READY or AVAILABLE_NOT_TESTED."""
    return [
        m
        for m in fleet
        if m.status in (RuntimeReadiness.READY, RuntimeReadiness.AVAILABLE_NOT_TESTED)
    ]


def has_capable_runtime(fleet: list[RuntimeFleetMember]) -> bool:
    """Return True if at least one fleet member is capable."""
    return len(get_capable_runtimes(fleet)) > 0
