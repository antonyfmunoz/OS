"""Governing laws — enacted constraints that govern UMH like physics governs reality.

Each law is a Pydantic model with a check() method. Laws are not descriptions —
they are executable validators called during governance classification.

Source mapping:
- services/umh/foundation/laws.py → Law model, LawCategory, Severity, 6 foundation laws
- Spec Section 22 → 8 invariant assertions
- Spec Section 10 → 12 invariant laws (canonical)
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class LawCategory(str, Enum):
    ONTOLOGICAL = "ontological"
    EPISTEMIC = "epistemic"
    GOVERNANCE = "governance"
    CAUSAL = "causal"
    BOUNDARY = "boundary"
    CONTROL = "control"
    EXECUTION = "execution"


class Severity(str, Enum):
    HARD_BLOCK = "hard_block"
    SOFT_BLOCK = "soft_block"
    WARNING = "warning"
    LOG_ONLY = "log_only"


class Law(BaseModel):
    """An enacted constraint on the substrate. check() returns None if satisfied, violation string if not."""

    id: UUID = Field(default_factory=uuid4)
    category: LawCategory
    name: str = Field(max_length=120)
    statement: str = Field(max_length=500)
    severity: Severity = Severity.HARD_BLOCK
    context_key: str = Field(default="", max_length=120)
    expected_value: Any = True

    def check(self, context: dict[str, Any]) -> str | None:
        """Check if this law is satisfied. Returns None if ok, violation message if not."""
        if not self.context_key:
            return None
        actual = context.get(self.context_key)
        if actual == self.expected_value:
            return None
        return (
            f"Law '{self.name}' violated: {self.statement} "
            f"(expected {self.context_key}={self.expected_value}, got {actual})"
        )


# ─── The 14 substrate laws (merged foundation + spec invariants) ──────────────

_ALL_LAWS: list[Law] = [
    Law(
        category=LawCategory.CONTROL,
        name="control_plane_exclusivity",
        statement="All signals pass through the Control Plane",
        context_key="routed_through_control_plane",
        expected_value=True,
    ),
    Law(
        category=LawCategory.EXECUTION,
        name="single_execution_spine",
        statement="One canonical runtime path for all execution",
        context_key="executed_through_spine",
        expected_value=True,
    ),
    Law(
        category=LawCategory.GOVERNANCE,
        name="governance_before_action",
        statement="No execution without governance classification",
        context_key="has_governance_verdict",
        expected_value=True,
    ),
    Law(
        category=LawCategory.CONTROL,
        name="typed_contracts_only",
        statement="All inter-module communication uses explicit schemas",
        context_key="uses_typed_contract",
        expected_value=True,
    ),
    Law(
        category=LawCategory.ONTOLOGICAL,
        name="memory_discipline",
        statement="All durable state writes through Memory/Storage subsystem",
        context_key="writes_through_memory_system",
        expected_value=True,
    ),
    Law(
        category=LawCategory.EXECUTION,
        name="environment_explicitness",
        statement="Every action declares target environment",
        context_key="has_environment_declaration",
        expected_value=True,
    ),
    Law(
        category=LawCategory.EPISTEMIC,
        name="trace_completeness",
        statement="Every execution produces an inspectable trace",
        context_key="has_trace",
        expected_value=True,
    ),
    Law(
        category=LawCategory.CONTROL,
        name="deterministic_plus_ai",
        statement="Intelligence is subordinate to control",
        context_key="has_deterministic_fallback",
        expected_value=True,
    ),
    Law(
        category=LawCategory.BOUNDARY,
        name="external_boundary",
        statement="No external system accessed directly — all through adapters",
        context_key="uses_adapter_boundary",
        expected_value=True,
    ),
    Law(
        category=LawCategory.EXECUTION,
        name="action_execution_separation",
        statement="Action, capability, adapter, environment, worker, actuation, work packet, proof are distinct",
        context_key="entities_separated",
        expected_value=True,
    ),
    Law(
        category=LawCategory.GOVERNANCE,
        name="mastery_law",
        statement="Verify competence before execution",
        context_key="mastery_verified",
        expected_value=True,
        severity=Severity.SOFT_BLOCK,
    ),
    Law(
        category=LawCategory.ONTOLOGICAL,
        name="reality_mimicry",
        statement="Model after effective real-world patterns when technically useful",
        severity=Severity.LOG_ONLY,
    ),
    Law(
        category=LawCategory.BOUNDARY,
        name="signal_intake",
        statement="All external input enters through signal intake pathway",
        context_key="entered_through_signal",
        expected_value=True,
    ),
    Law(
        category=LawCategory.EPISTEMIC,
        name="epistemic_humility",
        statement="Track confidence and uncertainty",
        context_key="has_confidence_score",
        expected_value=True,
        severity=Severity.SOFT_BLOCK,
    ),
]


class LawRegistry:
    """Registry of all substrate laws. Instantiate once at boot."""

    def __init__(self) -> None:
        self._laws: dict[str, Law] = {law.name: law for law in _ALL_LAWS}

    def all(self) -> list[Law]:
        """Return all registered laws."""
        return list(self._laws.values())

    def get(self, name: str) -> Law | None:
        """Return law by name, or None if not found."""
        return self._laws.get(name)

    def check_all(self, context: dict[str, Any]) -> list[str]:
        """Check all laws. Returns list of violation messages (empty = all pass)."""
        violations = []
        for law in self._laws.values():
            result = law.check(context)
            if result and law.severity in (Severity.HARD_BLOCK, Severity.SOFT_BLOCK):
                violations.append(result)
        return violations

    def hard_violations(self, context: dict[str, Any]) -> list[str]:
        """Check only HARD_BLOCK laws."""
        violations = []
        for law in self._laws.values():
            if law.severity != Severity.HARD_BLOCK:
                continue
            result = law.check(context)
            if result:
                violations.append(result)
        return violations
