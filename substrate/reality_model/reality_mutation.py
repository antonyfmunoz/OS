"""Reality mutation contracts — governed observation writes.

A RealityMutation represents a validated observation from any source system
that should be recorded in the InstanceRealityModel. The contract carries
source attribution, confidence, evidence, and governance context.

CanonicalRealityWritePath.apply_mutation() is the single governed entry
point. It validates the mutation and delegates to InstanceRealityModel.record().

Phase 19. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MutationSource(str, Enum):
    EXECUTION = "execution"
    GOVERNANCE = "governance"
    CONVERSATION_MEMORY = "conversation_memory"
    OBSERVATION_API = "observation_api"
    SIMULATION = "simulation"
    META_IDE = "meta_ide"
    ENGINEERING = "engineering"


class MutationType(str, Enum):
    OBSERVATION_RECORDED = "observation_recorded"
    PATTERN_CONFIRMED = "pattern_confirmed"
    DECISION_RECORDED = "decision_recorded"
    INSIGHT_PROMOTED = "insight_promoted"


@dataclass
class RealityMutation:
    mutation_id: str
    source_system: MutationSource
    source_id: str
    mutation_type: MutationType
    content: str
    confidence: float
    domain: str
    timestamp: float = field(default_factory=time.time)
    evidence: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    governance_context: dict[str, str] | None = None


@dataclass
class RealityMutationReceipt:
    mutation_id: str
    observation_id: str | None
    accepted: bool
    reason: str
    timestamp: float = field(default_factory=time.time)
