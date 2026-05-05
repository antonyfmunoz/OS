"""Phase 81 universal primitive contracts.

Extends the L0 primitives (umh.primitives.ontological) with scope, abstraction
level, evidence basis, confidence, and projection/instance layering.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PrimitiveType(str, Enum):
    ENTITY = "entity"
    STATE = "state"
    RELATIONSHIP = "relationship"
    CHANGE = "change"
    TIME = "time"
    SPACE = "space"
    ENVIRONMENT = "environment"
    CONSTRAINT = "constraint"
    RESOURCE = "resource"
    ENERGY = "energy"
    EFFORT = "effort"
    INFORMATION = "information"
    SIGNAL = "signal"
    ACTION = "action"
    FEEDBACK = "feedback"
    GOAL = "goal"
    ATTRACTOR = "attractor"
    OUTCOME = "outcome"
    UNCERTAINTY = "uncertainty"
    UNKNOWN = "unknown"


def normalize_primitive_type(value: str) -> PrimitiveType:
    v = value.strip().lower()
    for m in PrimitiveType:
        if m.value == v:
            return m
    return PrimitiveType.UNKNOWN


class PrimitiveScope(str, Enum):
    UNIVERSAL = "universal"
    DOMAIN_PROJECTION = "domain_projection"
    CONTEXTUAL_INSTANCE = "contextual_instance"
    SYSTEM_INTERNAL = "system_internal"
    UNKNOWN = "unknown"


def normalize_primitive_scope(value: str) -> PrimitiveScope:
    v = value.strip().lower()
    for m in PrimitiveScope:
        if m.value == v:
            return m
    return PrimitiveScope.UNKNOWN


class PrimitiveAbstractionLevel(str, Enum):
    UNIVERSAL = "universal"
    DOMAIN = "domain"
    SYSTEM = "system"
    WORKFLOW = "workflow"
    TOOL = "tool"
    HUMAN = "human"
    INSTANCE = "instance"
    META_SYSTEM = "meta_system"
    UNKNOWN = "unknown"


def normalize_abstraction_level(value: str) -> PrimitiveAbstractionLevel:
    v = value.strip().lower()
    for m in PrimitiveAbstractionLevel:
        if m.value == v:
            return m
    return PrimitiveAbstractionLevel.UNKNOWN


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))


def _prim_id() -> str:
    return f"prim_{uuid.uuid4().hex[:10]}"


@dataclass
class UniversalPrimitive:
    primitive_id: str
    name: str = ""
    primitive_type: PrimitiveType = PrimitiveType.UNKNOWN
    definition: str = ""
    abstraction_level: PrimitiveAbstractionLevel = PrimitiveAbstractionLevel.UNIVERSAL
    scope: PrimitiveScope = PrimitiveScope.UNIVERSAL
    relationships: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    evidence_basis: str = ""
    confidence: float = 0.8
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive_id": self.primitive_id,
            "name": self.name,
            "primitive_type": self.primitive_type.value,
            "definition": self.definition,
            "abstraction_level": self.abstraction_level.value,
            "scope": self.scope.value,
            "relationships": self.relationships,
            "examples": self.examples,
            "evidence_basis": self.evidence_basis,
            "confidence": self.confidence,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UniversalPrimitive:
        return cls(
            primitive_id=data.get("primitive_id", _prim_id()),
            name=data.get("name", ""),
            primitive_type=normalize_primitive_type(data.get("primitive_type", "unknown")),
            definition=data.get("definition", ""),
            abstraction_level=normalize_abstraction_level(
                data.get("abstraction_level", "universal")
            ),
            scope=normalize_primitive_scope(data.get("scope", "universal")),
            relationships=data.get("relationships", []),
            examples=data.get("examples", []),
            evidence_basis=data.get("evidence_basis", ""),
            confidence=clamp_confidence(data.get("confidence", 0.8)),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PrimitiveProjection:
    projection_id: str
    universal_primitive_id: str = ""
    domain: str = ""
    local_name: str = ""
    local_definition: str = ""
    local_constraints: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    evidence_basis: str = ""
    confidence: float = 0.7
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "universal_primitive_id": self.universal_primitive_id,
            "domain": self.domain,
            "local_name": self.local_name,
            "local_definition": self.local_definition,
            "local_constraints": self.local_constraints,
            "examples": self.examples,
            "evidence_basis": self.evidence_basis,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PrimitiveProjection:
        return cls(
            projection_id=data.get("projection_id", f"proj_{uuid.uuid4().hex[:10]}"),
            universal_primitive_id=data.get("universal_primitive_id", ""),
            domain=data.get("domain", ""),
            local_name=data.get("local_name", ""),
            local_definition=data.get("local_definition", ""),
            local_constraints=data.get("local_constraints", []),
            examples=data.get("examples", []),
            evidence_basis=data.get("evidence_basis", ""),
            confidence=clamp_confidence(data.get("confidence", 0.7)),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PrimitiveInstance:
    instance_id: str
    universal_primitive_id: str = ""
    projection_id: str = ""
    domain: str = ""
    context: str = ""
    local_value: str = ""
    source: str = ""
    confidence: float = 0.5
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "universal_primitive_id": self.universal_primitive_id,
            "projection_id": self.projection_id,
            "domain": self.domain,
            "context": self.context,
            "local_value": self.local_value,
            "source": self.source,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


def create_universal_primitive(
    name: str,
    primitive_type: str,
    definition: str,
    relationships: list[str] | None = None,
    examples: list[str] | None = None,
    evidence_basis: str = "cross-domain abstraction",
    confidence: float = 0.8,
    tags: list[str] | None = None,
) -> UniversalPrimitive:
    return UniversalPrimitive(
        primitive_id=f"prim_{name}",
        name=name,
        primitive_type=normalize_primitive_type(primitive_type),
        definition=definition,
        abstraction_level=PrimitiveAbstractionLevel.UNIVERSAL,
        scope=PrimitiveScope.UNIVERSAL,
        relationships=relationships or [],
        examples=examples or [],
        evidence_basis=evidence_basis,
        confidence=clamp_confidence(confidence),
        tags=tags or ["universal"],
    )


def get_default_universal_primitives() -> list[UniversalPrimitive]:
    return [
        create_universal_primitive(
            "entity",
            "entity",
            "A distinct thing that can be identified and referred to.",
            relationships=["state", "relationship"],
            examples=["a person", "a company", "a file", "a neuron", "a server"],
            evidence_basis="formal modeling",
        ),
        create_universal_primitive(
            "state",
            "state",
            "A snapshot of an entity's properties at a point in time.",
            relationships=["entity", "change", "time", "outcome"],
            examples=["account balance", "runtime config", "emotional state", "market price"],
            evidence_basis="systems theory",
        ),
        create_universal_primitive(
            "relationship",
            "relationship",
            "A connection or dependency between entities.",
            relationships=["entity", "constraint"],
            examples=["parent-child", "API caller-callee", "employer-employee", "cause-effect"],
            evidence_basis="graph theory / relational modeling",
        ),
        create_universal_primitive(
            "change",
            "change",
            "A transition from one state to another.",
            relationships=["state", "action", "time"],
            examples=["database migration", "price movement", "mood shift", "code commit"],
            evidence_basis="systems theory",
        ),
        create_universal_primitive(
            "time",
            "time",
            "A temporal coordinate or duration that bounds when things happen.",
            relationships=["state", "change", "action", "constraint"],
            examples=["deadline", "event timestamp", "session duration", "business quarter"],
            evidence_basis="physical reality",
        ),
        create_universal_primitive(
            "space_environment",
            "environment",
            "A context or medium in which entities exist and interact.",
            relationships=["entity", "constraint", "resource"],
            examples=["production server", "marketplace", "classroom", "filesystem"],
            evidence_basis="physical reality / systems theory",
        ),
        create_universal_primitive(
            "constraint",
            "constraint",
            "A boundary that limits what actions or states are valid.",
            relationships=["state", "action", "resource", "environment"],
            examples=["API rate limit", "budget cap", "physics law", "governance rule"],
            evidence_basis="formal modeling / optimization theory",
        ),
        create_universal_primitive(
            "resource",
            "resource",
            "Anything consumed, allocated, or required to perform an action.",
            relationships=["action", "constraint", "time", "entity"],
            examples=["money", "compute", "attention", "energy", "team capacity"],
            evidence_basis="economics / thermodynamics",
        ),
        create_universal_primitive(
            "energy_effort",
            "energy",
            "Capacity to do work or produce change.",
            relationships=["resource", "action", "change"],
            examples=["willpower", "CPU cycles", "caloric energy", "electrical power"],
            evidence_basis="thermodynamics / systems theory",
        ),
        create_universal_primitive(
            "information",
            "information",
            "Structured data that reduces uncertainty about state.",
            relationships=["signal", "state", "uncertainty"],
            examples=["database record", "research finding", "sensor reading", "log entry"],
            evidence_basis="information theory",
        ),
        create_universal_primitive(
            "signal",
            "signal",
            "An observable event that carries information about state or change.",
            relationships=["information", "state", "change", "feedback"],
            examples=["notification", "price tick", "error log", "user click", "heartbeat"],
            evidence_basis="information theory / cybernetics",
        ),
        create_universal_primitive(
            "action",
            "action",
            "An operation performed by an agent that may change state.",
            relationships=["state", "change", "resource", "goal", "constraint"],
            examples=["API call", "hiring decision", "exercise session", "code deployment"],
            evidence_basis="systems theory / agency",
        ),
        create_universal_primitive(
            "feedback",
            "feedback",
            "Information about the effect of a prior action, used to adjust future behavior.",
            relationships=["action", "outcome", "signal", "goal"],
            examples=["customer review", "test result", "habit reinforcement", "market response"],
            evidence_basis="cybernetics / control theory",
        ),
        create_universal_primitive(
            "goal_attractor",
            "goal",
            "A desired future state that motivates action.",
            relationships=["state", "action", "outcome", "constraint"],
            examples=["revenue target", "fitness goal", "product launch date", "system uptime"],
            evidence_basis="teleology / optimization theory",
        ),
        create_universal_primitive(
            "outcome",
            "outcome",
            "The measurable result of an action, compared against the goal.",
            relationships=["action", "goal", "state", "feedback"],
            examples=["sale closed", "test passed", "deployment succeeded", "habit formed"],
            evidence_basis="systems theory",
        ),
        create_universal_primitive(
            "uncertainty",
            "uncertainty",
            "The degree to which state, outcome, or relationship is unknown.",
            relationships=["information", "state", "outcome"],
            examples=["market risk", "prediction error", "measurement noise", "unknown dependency"],
            evidence_basis="information theory / probability theory",
        ),
    ]


_DEFAULT_PRIMITIVES: list[UniversalPrimitive] | None = None


def get_primitives() -> list[UniversalPrimitive]:
    global _DEFAULT_PRIMITIVES
    if _DEFAULT_PRIMITIVES is None:
        _DEFAULT_PRIMITIVES = get_default_universal_primitives()
    return list(_DEFAULT_PRIMITIVES)


def get_primitive_by_id(primitive_id: str) -> UniversalPrimitive | None:
    for p in get_primitives():
        if p.primitive_id == primitive_id:
            return p
    return None


def get_primitive_by_name(name: str) -> UniversalPrimitive | None:
    nl = name.lower()
    for p in get_primitives():
        if p.name.lower() == nl:
            return p
    return None


def export_storage_descriptors() -> list[Any]:
    from umh.storage.contracts import (
        StorageBackendType,
        StorageMutability,
        StorageRecordDescriptor,
        StorageRecordType,
        StorageScope,
        StorageSource,
    )

    descriptors: list[StorageRecordDescriptor] = []
    for p in get_primitives():
        descriptors.append(
            StorageRecordDescriptor(
                record_id=p.primitive_id,
                record_type=StorageRecordType.ONTOLOGY_PRIMITIVE,
                scope=StorageScope.SYSTEM,
                mutability=StorageMutability.IMMUTABLE,
                source=StorageSource.ONTOLOGY,
                backend_type=StorageBackendType.MEMORY,
            )
        )
    return descriptors
