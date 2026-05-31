"""Jarvis acceptance mode — standard multi-runtime vs deterministic-only vs blocked.

Phase 13.4M corrects Phase 13.4D: standard mode is blocked only when no
capable governed runtime path exists, not merely when cloud API quota is
exhausted. Claude Code / Codex / OpenCode / Hermes / Beast are all valid
runtime paths that do not require cloud API credits.

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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DETERMINISTIC_ALLOWED: list[str] = [
    "deterministic_intent_classification",
    "work_packet_creation",
    "context_lookup",
    "reconciliation_proposal_generation",
    "permission_request_generation",
    "propagation_preview",
    "sandboxed_low_risk_runtime_execution",
    "artifact_report_generation",
    "api_cockpit_proof",
]

_DETERMINISTIC_BLOCKED: list[str] = [
    "full_ai_reasoning",
    "medium_risk_execution",
    "external_writes",
    "production_mutation",
    "auto_merge",
    "autonomous_cadence_execution",
    "external_account_crawling",
]

_DETERMINISTIC_PROVES: list[str] = [
    "full Jarvis plumbing: operator→AI→WorkPacket→context→permission→propagation→runtime→artifact→review",
    "sandboxed runtime execution with event streaming",
    "policy enforcement blocks unsafe actions",
    "API/cockpit expose acceptance state",
]

_DETERMINISTIC_DOES_NOT_PROVE: list[str] = [
    "full AI intelligence quality",
    "LLM-backed intent interpretation",
    "multi-provider model routing under load",
    "production-grade autonomous reasoning",
]

_STANDARD_ALLOWED: list[str] = [
    "deterministic_intent_classification",
    "ai_backed_intent_classification",
    "work_packet_creation",
    "context_lookup",
    "reconciliation_proposal_generation",
    "permission_request_generation",
    "propagation_preview",
    "sandboxed_low_risk_runtime_execution",
    "artifact_report_generation",
    "api_cockpit_proof",
    "ai_reasoning_via_governed_runtime",
    "multi_runtime_selection",
]

_STANDARD_BLOCKED: list[str] = [
    "medium_risk_execution",
    "external_writes",
    "production_mutation",
    "auto_merge",
    "autonomous_cadence_execution",
    "external_account_crawling",
]

_STANDARD_PROVES: list[str] = [
    "full Jarvis plumbing: operator→AI→WorkPacket→context→permission→propagation→runtime→artifact→review",
    "sandboxed runtime execution with event streaming",
    "policy enforcement blocks unsafe actions",
    "API/cockpit expose acceptance state",
    "multi-runtime fleet selection and placement",
    "governed AI reasoning via subscription/CLI runtime",
]

_STANDARD_DOES_NOT_PROVE: list[str] = [
    "medium-risk production execution",
    "full autonomous cadence",
    "multi-provider cloud API routing under load",
]

_DEFAULT_PERSIST_DIR: str = os.path.join(
    os.environ.get("UMH_ROOT", "/opt/OS"),
    "data",
    "umh",
    "jarvis_acceptance",
)

_DECISIONS_FILENAME: str = "mode_decisions.jsonl"


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------


class JarvisAcceptanceMode(str, Enum):
    """Which acceptance mode the harness runs under."""

    STANDARD_MULTI_RUNTIME = "standard_multi_runtime"
    DETERMINISTIC_ONLY = "deterministic_only"
    BLOCKED = "blocked"


# ---------------------------------------------------------------------------
# Decision dataclass
# ---------------------------------------------------------------------------


@dataclass
class JarvisAcceptanceModeDecision:
    """Captures the mode selection for a single acceptance run."""

    decision_id: str  # "jamd-<8hex>"
    mode: JarvisAcceptanceMode
    accepted_by_operator: bool
    capable_runtime_path_exists: bool
    selected_runtime: str  # provider name or "" if none
    selected_device: str  # device node name or "" if none
    llm_cloud_provider_available: bool
    degraded: bool
    what_this_proves: list[str]
    what_this_does_not_prove: list[str]
    allowed_capabilities: list[str]
    blocked_capabilities: list[str]
    readiness_report_id: str
    timestamp: str  # ISO format
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "decision_id": self.decision_id,
            "mode": self.mode.value if isinstance(self.mode, Enum) else self.mode,
            "accepted_by_operator": self.accepted_by_operator,
            "capable_runtime_path_exists": self.capable_runtime_path_exists,
            "selected_runtime": self.selected_runtime,
            "selected_device": self.selected_device,
            "llm_cloud_provider_available": self.llm_cloud_provider_available,
            "degraded": self.degraded,
            "what_this_proves": list(self.what_this_proves),
            "what_this_does_not_prove": list(self.what_this_does_not_prove),
            "allowed_capabilities": list(self.allowed_capabilities),
            "blocked_capabilities": list(self.blocked_capabilities),
            "readiness_report_id": self.readiness_report_id,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def to_dict(decision: JarvisAcceptanceModeDecision) -> dict[str, Any]:
    """Module-level convenience — delegates to the dataclass method."""
    return decision.to_dict()


def from_dict(data: dict[str, Any]) -> JarvisAcceptanceModeDecision:
    """Reconstruct a decision from a plain dictionary."""
    mode_raw = data["mode"]
    if mode_raw == "standard":
        mode_raw = "standard_multi_runtime"
    return JarvisAcceptanceModeDecision(
        decision_id=data["decision_id"],
        mode=JarvisAcceptanceMode(mode_raw),
        accepted_by_operator=data["accepted_by_operator"],
        capable_runtime_path_exists=data.get("capable_runtime_path_exists", False),
        selected_runtime=data.get("selected_runtime", ""),
        selected_device=data.get("selected_device", ""),
        llm_cloud_provider_available=data.get("llm_cloud_provider_available",
                                               data.get("llm_provider_available", False)),
        degraded=data["degraded"],
        what_this_proves=list(data["what_this_proves"]),
        what_this_does_not_prove=list(data["what_this_does_not_prove"]),
        allowed_capabilities=list(data["allowed_capabilities"]),
        blocked_capabilities=list(data["blocked_capabilities"]),
        readiness_report_id=data["readiness_report_id"],
        timestamp=data["timestamp"],
        metadata=dict(data.get("metadata", {})),
    )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_standard_mode_decision(
    readiness_report_id: str,
    selected_runtime: str,
    selected_device: str,
    llm_cloud_available: bool = False,
    operator_accepted: bool = True,
) -> JarvisAcceptanceModeDecision:
    """Build a standard multi-runtime mode decision.

    Standard mode is available when at least one capable governed runtime
    path exists (Claude Code, Codex, OpenCode, Hermes, Beast, etc.).
    Cloud API exhaustion alone does NOT block standard mode.
    """
    return JarvisAcceptanceModeDecision(
        decision_id=f"jamd-{uuid4().hex[:8]}",
        mode=JarvisAcceptanceMode.STANDARD_MULTI_RUNTIME,
        accepted_by_operator=operator_accepted,
        capable_runtime_path_exists=True,
        selected_runtime=selected_runtime,
        selected_device=selected_device,
        llm_cloud_provider_available=llm_cloud_available,
        degraded=False,
        what_this_proves=list(_STANDARD_PROVES),
        what_this_does_not_prove=list(_STANDARD_DOES_NOT_PROVE),
        allowed_capabilities=list(_STANDARD_ALLOWED),
        blocked_capabilities=list(_STANDARD_BLOCKED),
        readiness_report_id=readiness_report_id,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


def create_deterministic_mode_decision(
    readiness_report_id: str,
    operator_accepted: bool = True,
) -> JarvisAcceptanceModeDecision:
    """Build a deterministic-only mode decision.

    Deterministic-only is a FALLBACK used only when no capable governed
    runtime path exists and the operator explicitly accepts degraded mode.
    """
    return JarvisAcceptanceModeDecision(
        decision_id=f"jamd-{uuid4().hex[:8]}",
        mode=JarvisAcceptanceMode.DETERMINISTIC_ONLY,
        accepted_by_operator=operator_accepted,
        capable_runtime_path_exists=False,
        selected_runtime="",
        selected_device="",
        llm_cloud_provider_available=False,
        degraded=True,
        what_this_proves=list(_DETERMINISTIC_PROVES),
        what_this_does_not_prove=list(_DETERMINISTIC_DOES_NOT_PROVE),
        allowed_capabilities=list(_DETERMINISTIC_ALLOWED),
        blocked_capabilities=list(_DETERMINISTIC_BLOCKED),
        readiness_report_id=readiness_report_id,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


def select_acceptance_mode(
    capable_runtime_exists: bool,
    selected_runtime: str,
    selected_device: str,
    llm_cloud_available: bool,
    readiness_report_id: str,
    operator_accepts_degraded: bool = False,
) -> JarvisAcceptanceModeDecision:
    """Select the correct acceptance mode based on runtime fleet state.

    Decision logic:
    1. If a capable governed runtime path exists → standard_multi_runtime.
    2. If no runtime but operator explicitly accepts degraded → deterministic_only.
    3. Otherwise → blocked.
    """
    if capable_runtime_exists:
        return create_standard_mode_decision(
            readiness_report_id=readiness_report_id,
            selected_runtime=selected_runtime,
            selected_device=selected_device,
            llm_cloud_available=llm_cloud_available,
        )

    if operator_accepts_degraded:
        return create_deterministic_mode_decision(
            readiness_report_id=readiness_report_id,
            operator_accepted=True,
        )

    return JarvisAcceptanceModeDecision(
        decision_id=f"jamd-{uuid4().hex[:8]}",
        mode=JarvisAcceptanceMode.BLOCKED,
        accepted_by_operator=False,
        capable_runtime_path_exists=False,
        selected_runtime="",
        selected_device="",
        llm_cloud_provider_available=llm_cloud_available,
        degraded=True,
        what_this_proves=[],
        what_this_does_not_prove=[
            "anything — no capable governed runtime path exists",
        ],
        allowed_capabilities=[],
        blocked_capabilities=list(_STANDARD_BLOCKED) + ["all_runtime_execution"],
        readiness_report_id=readiness_report_id,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def persist_mode_decision(
    decision: JarvisAcceptanceModeDecision,
    persist_dir: str | None = None,
) -> Path:
    """Append a decision to the JSONL ledger.

    Args:
        decision: The mode decision to persist.
        persist_dir: Override directory (defaults to data/umh/jarvis_acceptance/).

    Returns:
        Path to the JSONL file written to.
    """
    target_dir = Path(persist_dir or _DEFAULT_PERSIST_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / _DECISIONS_FILENAME

    line = json.dumps(decision.to_dict(), separators=(",", ":"))
    with open(target_file, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")

    logger.info("Persisted mode decision %s → %s", decision.decision_id, target_file)
    return target_file


def load_mode_decisions(
    persist_dir: str | None = None,
) -> list[JarvisAcceptanceModeDecision]:
    """Load all persisted mode decisions from the JSONL ledger.

    Args:
        persist_dir: Override directory (defaults to data/umh/jarvis_acceptance/).

    Returns:
        List of decisions in chronological order.
    """
    target_file = Path(persist_dir or _DEFAULT_PERSIST_DIR) / _DECISIONS_FILENAME
    if not target_file.exists():
        return []

    decisions: list[JarvisAcceptanceModeDecision] = []
    with open(target_file, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                decisions.append(from_dict(json.loads(raw)))
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning(
                    "Skipping malformed line %d in %s: %s", lineno, target_file, exc
                )
    return decisions
