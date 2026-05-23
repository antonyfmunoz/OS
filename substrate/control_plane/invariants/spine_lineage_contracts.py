"""Canonical Spine Lineage Contracts.

Typed contracts for the 15-stage UMH canonical spine.
Every executable work packet must prove it descended from
the full spine or an explicitly governed MVP stub lineage.

A work packet is a downstream artifact — not the source of truth.
The source of truth is the spine lineage that produced it.

Stages:
  1. signal              — external trigger or request
  2. interpretation      — what the signal means
  3. decomposition       — breaking into actionable units
  4. primitive_mapping   — mapping to UMH primitives
  5. domain_mapping      — mapping to domain context
  6. state_context       — world/memory/profile context
  7. composition         — assembling execution plan
  8. capability_selection — selecting required capabilities
  9. adapter_selection   — selecting execution adapters
 10. execution_binding   — binding all 6 execution layers
 11. mastery_check       — verifying tool mastery
 12. governance_decision — authority/risk/approval decision
 13. work_packet         — generating governed work packet
 14. proof_contract      — defining required proof
 15. trace_path          — end-to-end trace identifier

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpineStage(str, Enum):
    SIGNAL = "signal"
    INTERPRETATION = "interpretation"
    DECOMPOSITION = "decomposition"
    PRIMITIVE_MAPPING = "primitive_mapping"
    DOMAIN_MAPPING = "domain_mapping"
    STATE_CONTEXT = "state_context"
    COMPOSITION = "composition"
    CAPABILITY_SELECTION = "capability_selection"
    ADAPTER_SELECTION = "adapter_selection"
    EXECUTION_BINDING = "execution_binding"
    MASTERY_CHECK = "mastery_check"
    GOVERNANCE_DECISION = "governance_decision"
    WORK_PACKET = "work_packet"
    PROOF_CONTRACT = "proof_contract"
    TRACE_PATH = "trace_path"


REQUIRED_STAGES = list(SpineStage)
REQUIRED_STAGE_NAMES = frozenset(s.value for s in SpineStage)

CANONICAL_STAGE_ORDER = {stage: i for i, stage in enumerate(SpineStage)}


class SpineStageStatus(str, Enum):
    COMPLETE = "complete"
    MVP_STUB = "mvp_stub"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    SKIPPED = "skipped"


class CoherenceStatus(str, Enum):
    COHERENT = "coherent"
    COHERENT_WITH_MVP_STUBS = "coherent_with_mvp_stubs"
    INCOMPLETE_CANONICAL_SPINE = "incomplete_canonical_spine"
    INVALID_STAGE_ORDER = "invalid_stage_order"
    INVALID_STAGE_ARTIFACT = "invalid_stage_artifact"
    GOVERNANCE_LINEAGE_MISSING = "governance_lineage_missing"
    MASTERY_LINEAGE_MISSING = "mastery_lineage_missing"
    EXECUTION_BINDING_LINEAGE_MISSING = "execution_binding_lineage_missing"
    PROOF_CONTRACT_LINEAGE_MISSING = "proof_contract_lineage_missing"
    TRACE_PATH_LINEAGE_MISSING = "trace_path_lineage_missing"


class CoherenceFailureReason(str, Enum):
    MISSING_STAGE = "missing_stage"
    DUPLICATE_STAGE = "duplicate_stage"
    INVALID_ORDER = "invalid_order"
    MISSING_ARTIFACT_ID = "missing_artifact_id"
    MISSING_TRACE_ID = "missing_trace_id"
    MISSING_SCHEMA_VERSION = "missing_schema_version"
    MISSING_STATUS = "missing_status"
    MVP_STUB_NOT_ALLOWED = "mvp_stub_not_allowed"
    MVP_STUB_MISSING_REASON = "mvp_stub_missing_reason"
    GOVERNANCE_BEFORE_WORK_PACKET = "governance_before_work_packet"
    MASTERY_BEFORE_GOVERNANCE = "mastery_before_governance"
    PROOF_CONTRACT_BEFORE_EXECUTION = "proof_contract_before_execution"


@dataclass
class SpineStageArtifact:
    stage_name: str = ""
    artifact_id: str = ""
    artifact_type: str = ""
    source: str = ""
    timestamp: str = ""
    status: str = ""
    confidence: float = 0.0
    validation_status: str = ""
    trace_id: str = ""
    schema_version: str = ""
    reason: str = ""
    allowed_for: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "source": self.source,
            "timestamp": self.timestamp,
            "status": self.status,
            "confidence": self.confidence,
            "validation_status": self.validation_status,
            "trace_id": self.trace_id,
            "schema_version": self.schema_version,
            "reason": self.reason,
            "allowed_for": self.allowed_for,
        }


@dataclass
class SpineLineage:
    stages: list[SpineStageArtifact] = field(default_factory=list)
    mvp_stub_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "stages": [s.to_dict() for s in self.stages],
            "mvp_stub_allowed": self.mvp_stub_allowed,
        }

    def stage_names(self) -> list[str]:
        return [s.stage_name for s in self.stages]

    def get_stage(self, name: str) -> SpineStageArtifact | None:
        for s in self.stages:
            if s.stage_name == name:
                return s
        return None


@dataclass
class CoherenceEnvelope:
    lineage: SpineLineage = field(default_factory=SpineLineage)
    coherence_status: str = ""
    trace_id: str = ""
    schema_version: str = "1.0"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage": self.lineage.to_dict(),
            "coherence_status": self.coherence_status,
            "trace_id": self.trace_id,
            "schema_version": self.schema_version,
            "notes": self.notes,
        }


@dataclass
class CoherenceValidationResult:
    status: str = CoherenceStatus.INCOMPLETE_CANONICAL_SPINE.value
    coherent: bool = False
    has_mvp_stubs: bool = False
    mvp_stub_allowed: bool = False
    errors: list[str] = field(default_factory=list)
    failure_reasons: list[str] = field(default_factory=list)
    missing_stages: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "coherent": self.coherent,
            "has_mvp_stubs": self.has_mvp_stubs,
            "mvp_stub_allowed": self.mvp_stub_allowed,
            "errors": self.errors,
            "failure_reasons": self.failure_reasons,
            "missing_stages": self.missing_stages,
            "notes": self.notes,
        }
