"""Action risk categories — semantic classification of side-effect types.

Each category describes WHAT KIND of side-effect an action has
(read-only, financial, external communication, etc.) and maps to
a canonical RiskClass level for governance decisions.

The canonical RiskClass enum lives in substrate/types.py.
"""

from __future__ import annotations

from enum import Enum

from substrate.types import RiskClass as SeverityClass

# `SeverityClass` is the canonical 6-member severity enum (substrate.types.RiskClass:
# CRITICAL/HIGH/MEDIUM/LOW/NEGLIGIBLE/FORBIDDEN). It is aliased here under an
# UNAMBIGUOUS name because this module also rebinds `RiskClass` to the 8-member
# `ActionRiskCategory` for backward compatibility (see bottom of file). New code
# that needs the severity axis should import `SeverityClass` (or import RiskClass
# directly from substrate.types); code that needs the side-effect category axis
# should use `ActionRiskCategory`.
RiskClass = SeverityClass  # keep the real severity enum importable pre-rebind


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

# ── Canonical fail-closed risk coercion (WP-P2-002) ──────────────────────────
# Single canonical entry point for turning any risk string/enum into a canonical
# SeverityClass. FAIL-CLOSED: an unknown/missing value maps to HIGH (the
# strictest reasonable non-FORBIDDEN severity), NEVER to LOW/NEGLIGIBLE. This is
# the one helper every consumer should use so no site silently downgrades an
# unrecognized risk into a permissive band.

_SEVERITY_ALIASES: dict[str, SeverityClass] = {
    # canonical names
    "critical": SeverityClass.CRITICAL,
    "high": SeverityClass.HIGH,
    "medium": SeverityClass.MEDIUM,
    "low": SeverityClass.LOW,
    "negligible": SeverityClass.NEGLIGIBLE,
    "forbidden": SeverityClass.FORBIDDEN,
    # common alias vocab seen across the codebase (severity axis)
    "none": SeverityClass.NEGLIGIBLE,
    "trivial": SeverityClass.NEGLIGIBLE,
    "safe": SeverityClass.LOW,
    "blocked": SeverityClass.FORBIDDEN,
    "blocker": SeverityClass.CRITICAL,
    "severe": SeverityClass.CRITICAL,
}

# Ordering for "which is stricter" — higher index = stricter. FORBIDDEN is the
# absolute ceiling (never executable).
_SEVERITY_ORDER: dict[SeverityClass, int] = {
    SeverityClass.NEGLIGIBLE: 0,
    SeverityClass.LOW: 1,
    SeverityClass.MEDIUM: 2,
    SeverityClass.HIGH: 3,
    SeverityClass.CRITICAL: 4,
    SeverityClass.FORBIDDEN: 5,
}


# The set of strings coerce_risk_class recognizes (for callers that must
# distinguish "known value" from "unknown → apply the strict default").
_KNOWN_RISK_NAMES: frozenset[str] = frozenset(_SEVERITY_ALIASES.keys())


def coerce_risk_class(value: object) -> SeverityClass:
    """Canonical, deterministic, FAIL-CLOSED coercion to a SeverityClass.

    Accepts a SeverityClass, an ActionRiskCategory (mapped via to_risk_class),
    or any string. Unknown / empty / unrecognized input → HIGH (fail-closed):
    an unrecognized risk must never read as LOW or NEGLIGIBLE.
    """
    if isinstance(value, SeverityClass):
        return value
    if isinstance(value, ActionRiskCategory):
        return value.to_risk_class()
    text = str(value or "").strip().lower()
    if not text:
        return SeverityClass.HIGH
    return _SEVERITY_ALIASES.get(text, SeverityClass.HIGH)


def severity_rank(value: object) -> int:
    """Fail-closed strictness rank of any risk value (unknown → HIGH's rank)."""
    return _SEVERITY_ORDER[coerce_risk_class(value)]


def stricter_of(a: object, b: object) -> SeverityClass:
    """Return the stricter (higher-severity) of two risk values.

    Used when two taxonomies disagree: choose the stricter interpretation. Both
    operands are coerced fail-closed first, so an unknown value can only raise
    the result, never lower it.
    """
    ca, cb = coerce_risk_class(a), coerce_risk_class(b)
    return ca if _SEVERITY_ORDER[ca] >= _SEVERITY_ORDER[cb] else cb


# Backward compatibility — 31 files import RiskClass from here.
# New code should use ActionRiskCategory directly, or SeverityClass /
# coerce_risk_class for the severity axis.
RiskClass = ActionRiskCategory  # type: ignore[assignment]
