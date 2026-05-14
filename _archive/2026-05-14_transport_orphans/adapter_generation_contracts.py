"""
Adapter generation contracts for Phase 96.5.

Defines the lifecycle stages and artifacts for generating
new adapters through the Adapter Engine.

Includes Tool Mastery Pack generation — expert-level usage
knowledge is generated/loaded as part of the adapter lifecycle,
not separately.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AdapterGenerationStage(str, Enum):
    DISCOVERY = "discovery"
    CLASSIFICATION = "classification"
    CONTRACT_GENERATION = "contract_generation"
    CODE_GENERATION = "code_generation"
    TOOL_MASTERY_GENERATION = "tool_mastery_generation"
    TEST_GENERATION = "test_generation"
    SAFETY_POLICY_GENERATION = "safety_policy_generation"
    DOCUMENTATION_GENERATION = "documentation_generation"
    QUALITY_GATE = "quality_gate"
    REGISTRATION = "registration"
    COMPLETE = "complete"


@dataclass
class AdapterGenerationRequest:
    """Request to generate a new adapter."""

    source_system: str
    adapter_type: str
    target_contract: str = ""
    auth_requirements: list[str] = field(default_factory=list)
    safety_requirements: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_system": self.source_system,
            "adapter_type": self.adapter_type,
            "target_contract": self.target_contract,
            "auth_requirements": self.auth_requirements,
            "safety_requirements": self.safety_requirements,
            "notes": self.notes,
        }


@dataclass
class AdapterGenerationPlan:
    """Plan for generating an adapter through all stages."""

    request: AdapterGenerationRequest
    stages: list[AdapterGenerationStage] = field(
        default_factory=lambda: list(AdapterGenerationStage)
    )
    current_stage: AdapterGenerationStage = AdapterGenerationStage.DISCOVERY
    artifacts_planned: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "stages": [s.value for s in self.stages],
            "current_stage": self.current_stage.value,
            "artifacts_planned": self.artifacts_planned,
        }


@dataclass
class AdapterGeneratedArtifact:
    """An artifact produced during adapter generation."""

    artifact_type: str
    file_path: str = ""
    content_hash: str = ""
    stage: AdapterGenerationStage = AdapterGenerationStage.DISCOVERY
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": self.artifact_type,
            "file_path": self.file_path,
            "content_hash": self.content_hash,
            "stage": self.stage.value,
            "notes": self.notes,
        }


@dataclass
class AdapterGenerationResult:
    """Result of adapter generation."""

    request: AdapterGenerationRequest
    success: bool = False
    artifacts: list[AdapterGeneratedArtifact] = field(default_factory=list)
    quality_gate_passed: bool = False
    registered: bool = False
    failure_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "success": self.success,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "quality_gate_passed": self.quality_gate_passed,
            "registered": self.registered,
            "failure_reason": self.failure_reason,
        }
