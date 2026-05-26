"""Action risk categories — semantic classification of side-effect types.

Each category describes WHAT KIND of side-effect an action has
(read-only, financial, external communication, etc.) and maps to
a canonical RiskClass level for governance decisions.

The canonical RiskClass enum lives in substrate/types.py.
"""

from __future__ import annotations

from enum import Enum

from substrate.types import RiskClass


class ActionRiskCategory(str, Enum):
    """Semantic classification of an action's side-effect type.

    Maps to a canonical RiskClass (NEGLIGIBLE → CRITICAL) for governance.
    """

    READ_ONLY = "read_only"
    SAFE_WRITE = "safe_write"
    REVERSIBLE_WRITE = "reversible_write"
    IRREVERSIBLE_WRITE = "irreversible_write"
    EXTERNAL_COMMUNICATION = "external_communication"
    FINANCIAL = "financial"
    SECURITY_SENSITIVE = "security_sensitive"
    PHYSICAL_WORLD = "physical_world"

    def to_risk_class(self) -> RiskClass:
        return _CATEGORY_TO_CLASS[self]

    to_risk_level = to_risk_class

    @property
    def is_blocking(self) -> bool:
        """Whether this category should block by default without explicit approval."""
        return self in _BLOCKING_CATEGORIES


_CATEGORY_TO_CLASS: dict[ActionRiskCategory, RiskClass] = {
    ActionRiskCategory.READ_ONLY: RiskClass.NEGLIGIBLE,
    ActionRiskCategory.SAFE_WRITE: RiskClass.LOW,
    ActionRiskCategory.REVERSIBLE_WRITE: RiskClass.MEDIUM,
    ActionRiskCategory.IRREVERSIBLE_WRITE: RiskClass.HIGH,
    ActionRiskCategory.EXTERNAL_COMMUNICATION: RiskClass.HIGH,
    ActionRiskCategory.FINANCIAL: RiskClass.CRITICAL,
    ActionRiskCategory.SECURITY_SENSITIVE: RiskClass.CRITICAL,
    ActionRiskCategory.PHYSICAL_WORLD: RiskClass.CRITICAL,
}

_BLOCKING_CATEGORIES: frozenset[ActionRiskCategory] = frozenset(
    {
        ActionRiskCategory.IRREVERSIBLE_WRITE,
        ActionRiskCategory.EXTERNAL_COMMUNICATION,
        ActionRiskCategory.FINANCIAL,
        ActionRiskCategory.SECURITY_SENSITIVE,
        ActionRiskCategory.PHYSICAL_WORLD,
    }
)

# Backward compatibility — 31 files import RiskClass from here.
# New code should use ActionRiskCategory directly.
RiskClass = ActionRiskCategory  # type: ignore[assignment]
