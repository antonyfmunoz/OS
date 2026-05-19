"""Substrate laws — inviolable constraints that govern all operations."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class LawCategory(str, Enum):
    """Categories of substrate laws."""

    ONTOLOGICAL = "ontological"
    EPISTEMIC = "epistemic"
    GOVERNANCE = "governance"
    CAUSAL = "causal"
    BOUNDARY = "boundary"


class Severity(str, Enum):
    """What happens when a law is violated."""

    HARD_BLOCK = "hard_block"
    SOFT_BLOCK = "soft_block"
    WARNING = "warning"
    LOG_ONLY = "log_only"


class Law(BaseModel):
    """An inviolable constraint on the substrate."""

    id: UUID = Field(default_factory=uuid4)
    category: LawCategory
    name: str = Field(max_length=120)
    statement: str = Field(max_length=500)
    severity: Severity = Severity.HARD_BLOCK
    enforceable: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


# ─── The substrate's foundational laws ────────────────────────────────────────

SIGNAL_INTAKE_LAW = Law(
    category=LawCategory.BOUNDARY,
    name="signal_intake",
    statement="All external input enters the substrate exclusively through the signal intake pathway.",
    severity=Severity.HARD_BLOCK,
)

NO_DIRECT_EXECUTION_LAW = Law(
    category=LawCategory.GOVERNANCE,
    name="no_direct_execution",
    statement="No execution may occur without a governance decision. All execution requests must pass through governance.",
    severity=Severity.HARD_BLOCK,
)

ADAPTER_MEDIATION_LAW = Law(
    category=LawCategory.BOUNDARY,
    name="adapter_mediation",
    statement="All interaction with external systems must be mediated by the adapter protocol.",
    severity=Severity.HARD_BLOCK,
)

MEMORY_PATHWAY_LAW = Law(
    category=LawCategory.ONTOLOGICAL,
    name="memory_pathway",
    statement="All durable state writes must go through the memory candidate/update pathway.",
    severity=Severity.HARD_BLOCK,
)

TRACEABILITY_LAW = Law(
    category=LawCategory.EPISTEMIC,
    name="traceability",
    statement="Every execution must produce a trace. Untraceable operations are illegal.",
    severity=Severity.HARD_BLOCK,
)

EPISTEMIC_HUMILITY_LAW = Law(
    category=LawCategory.EPISTEMIC,
    name="epistemic_humility",
    statement="The substrate must track confidence and uncertainty. Assertions without epistemic grounding are prohibited.",
    severity=Severity.SOFT_BLOCK,
)

SUBSTRATE_LAWS: list[Law] = [
    SIGNAL_INTAKE_LAW,
    NO_DIRECT_EXECUTION_LAW,
    ADAPTER_MEDIATION_LAW,
    MEMORY_PATHWAY_LAW,
    TRACEABILITY_LAW,
    EPISTEMIC_HUMILITY_LAW,
]
