"""Workload placement policy — selects correct runtime + device for Work Packets.

Phase 13.4M. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WorkloadType(str, Enum):
    """Classification of workloads for placement decisions.

    Distinct from workload_runner.WorkloadType which classifies probe/health
    workloads. This enum classifies *execution* workloads for device+runtime
    placement.
    """

    GOVERNANCE = "governance"
    API_SERVING = "api_serving"
    SCHEDULING = "scheduling"
    LIGHTWEIGHT_PROBE = "lightweight_probe"
    AUDIT_PERSISTENCE = "audit_persistence"
    COORDINATION = "coordination"
    HEAVY_CODE_EXECUTION = "heavy_code_execution"
    LONG_RUNNING_CODING = "long_running_coding"
    BROWSER_AUTOMATION = "browser_automation"
    COMPUTER_USE = "computer_use"
    MEDIA_GENERATION = "media_generation"
    LOCAL_MODEL_INFERENCE = "local_model_inference"
    CONTAINERIZED_WORKLOAD = "containerized_workload"
    COCKPIT_RENDERING = "cockpit_rendering"
    OPERATOR_INTERACTION = "operator_interaction"
    DETERMINISTIC_CLASSIFICATION = "deterministic_classification"
    AI_REASONING = "ai_reasoning"
    CODE_REVIEW = "code_review"
    SANDBOX_RUNTIME = "sandbox_runtime"


# ---------------------------------------------------------------------------
# Decision dataclass
# ---------------------------------------------------------------------------


@dataclass
class WorkloadPlacementDecision:
    """Result of a workload placement evaluation."""

    decision_id: str  # "wpd-<8hex>"
    work_packet_id: str
    workload_type: WorkloadType
    selected_device: str  # device node_id or name
    selected_runtime: str  # runtime provider name
    reason: str
    governance_constraints: list[str] = field(default_factory=list)
    rejected_devices: list[dict[str, str]] = field(default_factory=list)
    rejected_runtimes: list[dict[str, str]] = field(default_factory=list)
    approval_required: bool = False
    degraded_mode: bool = False
    confidence: float = 0.8
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict for JSON persistence."""
        return {
            "decision_id": self.decision_id,
            "work_packet_id": self.work_packet_id,
            "workload_type": self.workload_type.value,
            "selected_device": self.selected_device,
            "selected_runtime": self.selected_runtime,
            "reason": self.reason,
            "governance_constraints": self.governance_constraints,
            "rejected_devices": self.rejected_devices,
            "rejected_runtimes": self.rejected_runtimes,
            "approval_required": self.approval_required,
            "degraded_mode": self.degraded_mode,
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Preference maps
# ---------------------------------------------------------------------------

_WORKLOAD_DEVICE_PREFERENCE: dict[WorkloadType, list[str]] = {
    WorkloadType.GOVERNANCE: ["vps"],
    WorkloadType.API_SERVING: ["vps"],
    WorkloadType.SCHEDULING: ["vps"],
    WorkloadType.LIGHTWEIGHT_PROBE: ["vps"],
    WorkloadType.AUDIT_PERSISTENCE: ["vps"],
    WorkloadType.COORDINATION: ["vps"],
    WorkloadType.HEAVY_CODE_EXECUTION: ["windows_beast", "vps"],
    WorkloadType.LONG_RUNNING_CODING: ["windows_beast", "vps"],
    WorkloadType.BROWSER_AUTOMATION: ["windows_beast"],
    WorkloadType.COMPUTER_USE: ["windows_beast"],
    WorkloadType.MEDIA_GENERATION: ["windows_beast"],
    WorkloadType.LOCAL_MODEL_INFERENCE: ["windows_beast"],
    WorkloadType.CONTAINERIZED_WORKLOAD: ["windows_beast", "vps"],
    WorkloadType.COCKPIT_RENDERING: ["fly_cockpit"],
    WorkloadType.OPERATOR_INTERACTION: ["fly_cockpit", "vps"],
    WorkloadType.DETERMINISTIC_CLASSIFICATION: ["vps"],
    WorkloadType.AI_REASONING: ["windows_beast", "vps"],
    WorkloadType.CODE_REVIEW: ["windows_beast", "vps"],
    WorkloadType.SANDBOX_RUNTIME: ["windows_beast", "vps"],
}

_WORKLOAD_RUNTIME_PREFERENCE: dict[WorkloadType, list[str]] = {
    WorkloadType.GOVERNANCE: ["shell"],
    WorkloadType.API_SERVING: ["shell"],
    WorkloadType.SCHEDULING: ["shell"],
    WorkloadType.LIGHTWEIGHT_PROBE: ["shell"],
    WorkloadType.AUDIT_PERSISTENCE: ["shell"],
    WorkloadType.COORDINATION: ["shell"],
    WorkloadType.HEAVY_CODE_EXECUTION: [
        "claude_code", "codex", "opencode", "hermes", "shell",
    ],
    WorkloadType.LONG_RUNNING_CODING: [
        "claude_code", "codex", "opencode", "hermes",
    ],
    WorkloadType.BROWSER_AUTOMATION: ["browser", "computer_use"],
    WorkloadType.COMPUTER_USE: ["computer_use", "browser"],
    WorkloadType.MEDIA_GENERATION: ["shell", "claude_code"],
    WorkloadType.LOCAL_MODEL_INFERENCE: ["ollama", "shell"],
    WorkloadType.CONTAINERIZED_WORKLOAD: ["shell"],
    WorkloadType.COCKPIT_RENDERING: [],
    WorkloadType.OPERATOR_INTERACTION: [],
    WorkloadType.DETERMINISTIC_CLASSIFICATION: ["shell"],
    WorkloadType.AI_REASONING: [
        "claude_code", "claude_sdk", "codex", "opencode",
        "hermes", "cloud_api", "ollama",
    ],
    WorkloadType.CODE_REVIEW: [
        "claude_code", "codex", "opencode", "hermes",
    ],
    WorkloadType.SANDBOX_RUNTIME: [
        "claude_code", "shell", "codex", "opencode", "hermes",
    ],
}

# Risk classes that require governance approval before execution.
_APPROVAL_RISK_CLASSES: frozenset[str] = frozenset({
    "medium", "high", "critical",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_decision_id() -> str:
    """Return a ``wpd-<8hex>`` identifier."""
    return f"wpd-{uuid.uuid4().hex[:8]}"


def _resolve_workload_type(raw: WorkloadType | str) -> WorkloadType:
    """Coerce a string to *WorkloadType*, raising ValueError on mismatch."""
    if isinstance(raw, WorkloadType):
        return raw
    try:
        return WorkloadType(raw)
    except ValueError:
        # Try upper-case member name as fallback.
        upper = raw.upper()
        if upper in WorkloadType.__members__:
            return WorkloadType[upper]
        raise


def _pick_best(
    preferred: list[str],
    available: list[str] | None,
) -> tuple[str | None, list[dict[str, str]]]:
    """Return the best option from *preferred* that is in *available*.

    Returns ``(selected, rejected_list)`` where *rejected_list* records
    every skipped option with a reason string.
    """
    rejected: list[dict[str, str]] = []
    if available is None:
        # No constraint — first preference wins.
        return (preferred[0] if preferred else None, rejected)

    available_set = set(available)
    for option in preferred:
        if option in available_set:
            # Record the ones we skipped before this match.
            return option, rejected
        rejected.append({"name": option, "reason": "not in available set"})

    # Nothing matched — try first available as degraded fallback.
    if available:
        return available[0], rejected
    return None, rejected


# ---------------------------------------------------------------------------
# Core placement function
# ---------------------------------------------------------------------------


def select_placement(
    work_packet_id: str,
    workload_type: WorkloadType | str,
    risk_class: str = "low",
    available_devices: list[str] | None = None,
    available_runtimes: list[str] | None = None,
) -> WorkloadPlacementDecision:
    """Select device + runtime for a work packet.

    Parameters
    ----------
    work_packet_id:
        Unique identifier of the work packet to place.
    workload_type:
        The kind of workload — accepts enum member or string value.
    risk_class:
        Risk classification (``"low"``, ``"medium"``, ``"high"``,
        ``"critical"``). Medium and above require approval.
    available_devices:
        If provided, restrict placement to these device node IDs.
    available_runtimes:
        If provided, restrict placement to these runtime providers.

    Returns
    -------
    WorkloadPlacementDecision
        Fully populated placement decision.
    """
    wtype = _resolve_workload_type(workload_type)
    device_prefs = _WORKLOAD_DEVICE_PREFERENCE.get(wtype, [])
    runtime_prefs = _WORKLOAD_RUNTIME_PREFERENCE.get(wtype, [])

    selected_device, rejected_devices = _pick_best(device_prefs, available_devices)
    selected_runtime, rejected_runtimes = _pick_best(runtime_prefs, available_runtimes)

    degraded_mode = False
    reason_parts: list[str] = []

    # Device resolution ---------------------------------------------------
    if selected_device is None:
        degraded_mode = True
        selected_device = "unknown"
        reason_parts.append("no suitable device found")
    elif selected_device not in device_prefs:
        degraded_mode = True
        reason_parts.append(
            f"preferred devices unavailable, fell back to {selected_device}"
        )
    else:
        reason_parts.append(f"device {selected_device} matched preference")

    # Runtime resolution ---------------------------------------------------
    if selected_runtime is None:
        if not runtime_prefs:
            # Workloads like COCKPIT_RENDERING have no runtime requirement.
            selected_runtime = "none"
            reason_parts.append("no runtime required for this workload type")
        else:
            degraded_mode = True
            selected_runtime = "unknown"
            reason_parts.append("no suitable runtime found")
    elif selected_runtime not in runtime_prefs:
        degraded_mode = True
        reason_parts.append(
            f"preferred runtimes unavailable, fell back to {selected_runtime}"
        )
    else:
        reason_parts.append(f"runtime {selected_runtime} matched preference")

    # Governance -----------------------------------------------------------
    governance_constraints: list[str] = []
    approval_required = risk_class.lower() in _APPROVAL_RISK_CLASSES
    if approval_required:
        governance_constraints.append(
            f"risk_class={risk_class} requires operator approval"
        )
    if degraded_mode:
        governance_constraints.append(
            "degraded placement — operator should review"
        )

    confidence = 0.95 if not degraded_mode else 0.5

    return WorkloadPlacementDecision(
        decision_id=_generate_decision_id(),
        work_packet_id=work_packet_id,
        workload_type=wtype,
        selected_device=selected_device,
        selected_runtime=selected_runtime,
        reason="; ".join(reason_parts),
        governance_constraints=governance_constraints,
        rejected_devices=rejected_devices,
        rejected_runtimes=rejected_runtimes,
        approval_required=approval_required,
        degraded_mode=degraded_mode,
        confidence=confidence,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

_DEFAULT_PERSIST_SUBPATH = "data/umh/operational_truth/workload_placement_decisions.jsonl"


def _resolve_persist_path(persist_dir: str | None) -> Path:
    """Return the JSONL file path for placement decisions."""
    if persist_dir is not None:
        return Path(persist_dir) / "workload_placement_decisions.jsonl"
    return Path(_REPO_ROOT) / _DEFAULT_PERSIST_SUBPATH


def persist_decision(
    decision: WorkloadPlacementDecision,
    persist_dir: str | None = None,
) -> Path:
    """Append *decision* to the placement decisions JSONL log.

    Returns the path written to.
    """
    path = _resolve_persist_path(persist_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(decision.to_dict(), separators=(",", ":")) + "\n")
    logger.debug("persisted placement decision %s → %s", decision.decision_id, path)
    return path


def decision_from_dict(data: dict[str, Any]) -> WorkloadPlacementDecision:
    """Reconstruct a *WorkloadPlacementDecision* from a plain dict."""
    return WorkloadPlacementDecision(
        decision_id=data["decision_id"],
        work_packet_id=data["work_packet_id"],
        workload_type=WorkloadType(data["workload_type"]),
        selected_device=data["selected_device"],
        selected_runtime=data["selected_runtime"],
        reason=data.get("reason", ""),
        governance_constraints=data.get("governance_constraints", []),
        rejected_devices=data.get("rejected_devices", []),
        rejected_runtimes=data.get("rejected_runtimes", []),
        approval_required=data.get("approval_required", False),
        degraded_mode=data.get("degraded_mode", False),
        confidence=data.get("confidence", 0.8),
        timestamp=data.get("timestamp", ""),
        metadata=data.get("metadata", {}),
    )


def load_decisions(
    persist_dir: str | None = None,
) -> list[WorkloadPlacementDecision]:
    """Load all persisted placement decisions from the JSONL log."""
    path = _resolve_persist_path(persist_dir)
    if not path.exists():
        return []
    decisions: list[WorkloadPlacementDecision] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                decisions.append(decision_from_dict(json.loads(line)))
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.warning(
                    "skipping malformed placement decision at line %d: %s",
                    lineno,
                    exc,
                )
    return decisions
