"""Risk classes — domain-specific action classifications that map to governance risk levels."""

from __future__ import annotations

from enum import Enum

from services.umh.protocols.governance import RiskLevel


class RiskClass(str, Enum):
    """Domain-specific risk classification for actions.

    Each class maps to a protocol-level RiskLevel but carries
    semantic meaning about what kind of side-effect the action has.
    """

    READ_ONLY = "read_only"
    SAFE_WRITE = "safe_write"
    REVERSIBLE_WRITE = "reversible_write"
    IRREVERSIBLE_WRITE = "irreversible_write"
    EXTERNAL_COMMUNICATION = "external_communication"
    FINANCIAL = "financial"
    SECURITY_SENSITIVE = "security_sensitive"
    PHYSICAL_WORLD = "physical_world"

    def to_risk_level(self) -> RiskLevel:
        return _CLASS_TO_LEVEL[self]

    @property
    def is_blocking(self) -> bool:
        """Whether this class should block by default without explicit approval."""
        return self in _BLOCKING_CLASSES


_CLASS_TO_LEVEL: dict[RiskClass, RiskLevel] = {
    RiskClass.READ_ONLY: RiskLevel.NEGLIGIBLE,
    RiskClass.SAFE_WRITE: RiskLevel.LOW,
    RiskClass.REVERSIBLE_WRITE: RiskLevel.MEDIUM,
    RiskClass.IRREVERSIBLE_WRITE: RiskLevel.HIGH,
    RiskClass.EXTERNAL_COMMUNICATION: RiskLevel.HIGH,
    RiskClass.FINANCIAL: RiskLevel.CRITICAL,
    RiskClass.SECURITY_SENSITIVE: RiskLevel.CRITICAL,
    RiskClass.PHYSICAL_WORLD: RiskLevel.CRITICAL,
}

_BLOCKING_CLASSES: frozenset[RiskClass] = frozenset({
    RiskClass.IRREVERSIBLE_WRITE,
    RiskClass.EXTERNAL_COMMUNICATION,
    RiskClass.FINANCIAL,
    RiskClass.SECURITY_SENSITIVE,
    RiskClass.PHYSICAL_WORLD,
})
