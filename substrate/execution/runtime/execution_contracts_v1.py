"""Execution Contracts v1 for the canonical runtime spine.

Data shapes for the full governed execution lifecycle:
  signal → interpretation → capability resolution → adapter selection
  → environment selection → governance evaluation → execution envelope
  → observability record → spine execution result.

All contracts are immutable after creation. All carry provenance.
All serialize deterministically.

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:16]}"


def _deterministic_id(namespace: str, content: str) -> str:
    h = hashlib.sha256(f"{namespace}:{content}".encode("utf-8")).hexdigest()[:16]
    return f"{namespace}-{h}"


def _content_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SignalSource(str, Enum):
    DISCORD = "discord"
    SPINE = "spine"
    ORCHESTRATOR = "orchestrator"
    CRON = "cron"
    API = "api"
    MANUAL = "manual"


class IntentType(str, Enum):
    COMMAND = "command"
    QUERY = "query"
    REPORT = "report"
    INGESTION = "ingestion"
    ACTUATION = "actuation"
    GOVERNANCE = "governance"
    DIAGNOSTIC = "diagnostic"


class CapabilityDomain(str, Enum):
    SHELL_EXECUTION = "shell_execution"
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    GIT_INSPECTION = "git_inspection"
    MEMORY_QUERY = "memory_query"
    MEMORY_WRITE = "memory_write"
    REPORT_GENERATION = "report_generation"
    GUI_ACTUATION = "gui_actuation"
    DOCUMENT_INGESTION = "document_ingestion"


# NOTE: The canonical GovernanceVerdict is a Pydantic model in substrate.types.
# This is a runtime-scoped enum for the execution contracts pipeline.
# Import the canonical version for cross-reference:
from substrate.types import GovernanceVerdict as CanonicalGovernanceVerdict  # noqa: F401


class GovernanceVerdict(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    REQUIRES_APPROVAL = "requires_approval"
    STRUCTURALLY_FORBIDDEN = "structurally_forbidden"


from substrate.types import RiskClass


class SpineOutcome(str, Enum):
    SUCCESS = "success"
    GOVERNANCE_DENIED = "governance_denied"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    ADAPTER_UNAVAILABLE = "adapter_unavailable"
    ENVIRONMENT_UNAVAILABLE = "environment_unavailable"
    EXECUTION_FAILED = "execution_failed"
    TIMEOUT = "timeout"
    STRUCTURALLY_FORBIDDEN = "structurally_forbidden"


class ExecutionMode(str, Enum):
    SYNCHRONOUS = "synchronous"
    QUEUED = "queued"
    DEFERRED = "deferred"


# ---------------------------------------------------------------------------
# Contract 1: ExecutionSignal
# ---------------------------------------------------------------------------


@dataclass
class ExecutionSignal:
    """The raw incoming signal that triggers the execution spine."""

    signal_id: str = ""
    source: SignalSource = SignalSource.DISCORD
    raw_command: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    user_id: str = ""
    channel_id: str = ""
    correlation_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.signal_id:
            self.signal_id = _new_id("sig")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.correlation_id:
            self.correlation_id = _new_id("corr")

    def content_hash(self) -> str:
        return _content_hash(
            {"source": self.source.value, "raw_command": self.raw_command, "payload": self.payload}
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "source": self.source.value,
            "raw_command": self.raw_command,
            "payload": self.payload,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 2: InterpretedIntent
# ---------------------------------------------------------------------------


@dataclass
class InterpretedIntent:
    """The interpreted meaning of an execution signal."""

    intent_id: str = ""
    signal_id: str = ""
    intent_type: IntentType = IntentType.COMMAND
    command_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    required_capabilities: list[str] = field(default_factory=list)
    risk_class: RiskClass = RiskClass.NEGLIGIBLE
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.intent_id:
            self.intent_id = _deterministic_id("intent", f"{self.signal_id}:{self.command_name}")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "signal_id": self.signal_id,
            "intent_type": self.intent_type.value,
            "command_name": self.command_name,
            "arguments": self.arguments,
            "required_capabilities": self.required_capabilities,
            "risk_class": self.risk_class.value,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 3: CapabilityResolution
# ---------------------------------------------------------------------------


@dataclass
class CapabilityResolution:
    """Result of resolving what capabilities are needed and available."""

    resolution_id: str = ""
    intent_id: str = ""
    required_capabilities: list[str] = field(default_factory=list)
    available_capabilities: list[str] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    resolved: bool = False
    resolution_notes: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.resolution_id:
            self.resolution_id = _deterministic_id(
                "capres", f"{self.intent_id}:{','.join(sorted(self.required_capabilities))}"
            )
        if not self.timestamp:
            self.timestamp = _now_iso()
        self.missing_capabilities = [
            c for c in self.required_capabilities if c not in self.available_capabilities
        ]
        self.resolved = len(self.missing_capabilities) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolution_id": self.resolution_id,
            "intent_id": self.intent_id,
            "required_capabilities": self.required_capabilities,
            "available_capabilities": self.available_capabilities,
            "missing_capabilities": self.missing_capabilities,
            "resolved": self.resolved,
            "resolution_notes": self.resolution_notes,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 4: AdapterSelection
# ---------------------------------------------------------------------------


@dataclass
class AdapterSelection:
    """Which adapter was selected to fulfill the execution."""

    selection_id: str = ""
    intent_id: str = ""
    adapter_id: str = ""
    adapter_type: str = ""
    capability_matched: str = ""
    environment_type: str = ""
    selected: bool = False
    rejection_reason: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.selection_id:
            self.selection_id = _deterministic_id("adsel", f"{self.intent_id}:{self.adapter_id}")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_id": self.selection_id,
            "intent_id": self.intent_id,
            "adapter_id": self.adapter_id,
            "adapter_type": self.adapter_type,
            "capability_matched": self.capability_matched,
            "environment_type": self.environment_type,
            "selected": self.selected,
            "rejection_reason": self.rejection_reason,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 5: EnvironmentSelection
# ---------------------------------------------------------------------------


@dataclass
class EnvironmentSelection:
    """Which environment was selected for execution."""

    selection_id: str = ""
    intent_id: str = ""
    environment_id: str = ""
    environment_type: str = ""
    authority_domains: list[str] = field(default_factory=list)
    health_status: str = "healthy"
    selected: bool = False
    rejection_reason: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.selection_id:
            self.selection_id = _deterministic_id(
                "envsel", f"{self.intent_id}:{self.environment_id}"
            )
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_id": self.selection_id,
            "intent_id": self.intent_id,
            "environment_id": self.environment_id,
            "environment_type": self.environment_type,
            "authority_domains": self.authority_domains,
            "health_status": self.health_status,
            "selected": self.selected,
            "rejection_reason": self.rejection_reason,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 6: GovernanceEvaluation
# ---------------------------------------------------------------------------


@dataclass
class GovernanceEvaluation:
    """Result of pre-execution governance evaluation."""

    evaluation_id: str = ""
    intent_id: str = ""
    command_name: str = ""
    risk_class: RiskClass = RiskClass.NEGLIGIBLE
    verdict: GovernanceVerdict = GovernanceVerdict.APPROVED
    denial_reasons: list[str] = field(default_factory=list)
    governance_rules_applied: list[str] = field(default_factory=list)
    authority_class: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.evaluation_id:
            self.evaluation_id = _deterministic_id(
                "goveval", f"{self.intent_id}:{self.command_name}:{self.risk_class.value}"
            )
        if not self.timestamp:
            self.timestamp = _now_iso()

    @property
    def approved(self) -> bool:
        return self.verdict == GovernanceVerdict.APPROVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "intent_id": self.intent_id,
            "command_name": self.command_name,
            "risk_class": self.risk_class.value,
            "verdict": self.verdict.value,
            "approved": self.approved,
            "denial_reasons": self.denial_reasons,
            "governance_rules_applied": self.governance_rules_applied,
            "authority_class": self.authority_class,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 7: ExecutionEnvelope
# ---------------------------------------------------------------------------


@dataclass
class ExecutionEnvelope:
    """The complete execution package handed to the orchestrator."""

    envelope_id: str = ""
    signal: ExecutionSignal | None = None
    intent: InterpretedIntent | None = None
    capability_resolution: CapabilityResolution | None = None
    adapter_selection: AdapterSelection | None = None
    environment_selection: EnvironmentSelection | None = None
    governance_evaluation: GovernanceEvaluation | None = None
    execution_mode: ExecutionMode = ExecutionMode.SYNCHRONOUS
    correlation_id: str = ""
    session_id: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.envelope_id:
            self.envelope_id = _new_id("env")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.correlation_id and self.signal:
            self.correlation_id = self.signal.correlation_id

    def content_hash(self) -> str:
        return _content_hash(
            {
                "envelope_id": self.envelope_id,
                "command": self.intent.command_name if self.intent else "",
                "adapter": self.adapter_selection.adapter_id if self.adapter_selection else "",
                "environment": (
                    self.environment_selection.environment_id if self.environment_selection else ""
                ),
                "verdict": (
                    self.governance_evaluation.verdict.value if self.governance_evaluation else ""
                ),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "signal": self.signal.to_dict() if self.signal else None,
            "intent": self.intent.to_dict() if self.intent else None,
            "capability_resolution": (
                self.capability_resolution.to_dict() if self.capability_resolution else None
            ),
            "adapter_selection": (
                self.adapter_selection.to_dict() if self.adapter_selection else None
            ),
            "environment_selection": (
                self.environment_selection.to_dict() if self.environment_selection else None
            ),
            "governance_evaluation": (
                self.governance_evaluation.to_dict() if self.governance_evaluation else None
            ),
            "execution_mode": self.execution_mode.value,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "content_hash": self.content_hash(),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 8: ObservabilityRecord
# ---------------------------------------------------------------------------


@dataclass
class ObservabilityRecord:
    """Telemetry record for a single spine execution."""

    record_id: str = ""
    envelope_id: str = ""
    correlation_id: str = ""
    command_name: str = ""
    outcome: SpineOutcome = SpineOutcome.SUCCESS
    risk_class: RiskClass = RiskClass.NEGLIGIBLE
    governance_verdict: GovernanceVerdict = GovernanceVerdict.APPROVED
    adapter_id: str = ""
    environment_id: str = ""
    latency_ms: float = 0.0
    execution_started_at: str = ""
    execution_completed_at: str = ""
    proof_artifact_count: int = 0
    error_message: str = ""
    continuity_updated: bool = False
    memory_promoted: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.record_id:
            self.record_id = _new_id("obs")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash(
            {
                "envelope_id": self.envelope_id,
                "command_name": self.command_name,
                "outcome": self.outcome.value,
                "adapter_id": self.adapter_id,
                "environment_id": self.environment_id,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "envelope_id": self.envelope_id,
            "correlation_id": self.correlation_id,
            "command_name": self.command_name,
            "outcome": self.outcome.value,
            "risk_class": self.risk_class.value,
            "governance_verdict": self.governance_verdict.value,
            "adapter_id": self.adapter_id,
            "environment_id": self.environment_id,
            "latency_ms": self.latency_ms,
            "execution_started_at": self.execution_started_at,
            "execution_completed_at": self.execution_completed_at,
            "proof_artifact_count": self.proof_artifact_count,
            "error_message": self.error_message,
            "continuity_updated": self.continuity_updated,
            "memory_promoted": self.memory_promoted,
            "content_hash": self.content_hash(),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Contract 9: SpineExecutionResult
# ---------------------------------------------------------------------------


@dataclass
class SpineExecutionResult:
    """The complete result of a canonical runtime spine execution."""

    result_id: str = ""
    envelope_id: str = ""
    correlation_id: str = ""
    command_name: str = ""
    outcome: SpineOutcome = SpineOutcome.SUCCESS
    execution_envelope: ExecutionEnvelope | None = None
    observability_record: ObservabilityRecord | None = None
    result_payload: dict[str, Any] = field(default_factory=dict)
    artifacts_produced: list[str] = field(default_factory=list)
    error_message: str = ""
    duration_ms: float = 0.0
    continuity_snapshot_id: str = ""
    open_loops_created: list[str] = field(default_factory=list)
    memory_promotions: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.result_id:
            self.result_id = _new_id("spres")
        if not self.timestamp:
            self.timestamp = _now_iso()

    @property
    def succeeded(self) -> bool:
        return self.outcome == SpineOutcome.SUCCESS

    def content_hash(self) -> str:
        return _content_hash(
            {
                "result_id": self.result_id,
                "envelope_id": self.envelope_id,
                "command_name": self.command_name,
                "outcome": self.outcome.value,
                "artifacts": sorted(self.artifacts_produced),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "envelope_id": self.envelope_id,
            "correlation_id": self.correlation_id,
            "command_name": self.command_name,
            "outcome": self.outcome.value,
            "succeeded": self.succeeded,
            "execution_envelope": (
                self.execution_envelope.to_dict() if self.execution_envelope else None
            ),
            "observability_record": (
                self.observability_record.to_dict() if self.observability_record else None
            ),
            "result_payload": self.result_payload,
            "artifacts_produced": self.artifacts_produced,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "continuity_snapshot_id": self.continuity_snapshot_id,
            "open_loops_created": self.open_loops_created,
            "memory_promotions": self.memory_promotions,
            "content_hash": self.content_hash(),
            "timestamp": self.timestamp,
        }
