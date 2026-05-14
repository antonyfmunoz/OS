"""Policy bridge between the Control Plane and `runtime.authority_engine`.

Two governance systems coexist in EOS and they speak different dialects:

- `runtime/authority_engine.py` governs *business* actions (`send_dm`,
  `publish_content`, `execute_payment`) in uppercase risk classes
  (`LOW/MEDIUM/HIGH/CRITICAL`) and persists approvals to Neon.
- `core/action_system/` governs *runtime* actions (`run_script`,
  `shell_command`, `write_file`, `call_api`) in lowercase risk levels
  (`low/medium/high`) and persists deferrals to disk.

Collapsing them into one module would create a circular dependency
(authority_engine imports `runtime.db`, which is a heavy dependency we
do not want to drag into the Control Plane's hot path) and would
conflate two *different* governance domains. Instead, this module is
the smallest correct adapter:

    - one canonical vocabulary (lowercase `low/medium/high/critical`)
    - pure functions, no DB access, no imports from `runtime.*` at module load
    - authority_engine is consulted *lazily* via `authority_classify()`,
      which catches ImportError and returns None so runtime governance
      never blocks on the business layer being importable

Integration contract:

    Control Plane is the source of truth for runtime actions
    (`run_script`, `shell_command`, `write_file`, `call_api`).

    AuthorityEngine is the source of truth for business actions
    (`send_dm`, `publish_content`, `execute_payment`, ...).

    When a runtime action carries business-layer semantics (e.g. an
    outreach agent running a script that dispatches DMs), callers can
    pass `business_action_type=...` and the policy bridge will upgrade
    the risk level to match the business classification.

See docs/system/control_plane.md for the full integration model.
"""

from __future__ import annotations

from typing import Literal, Optional

# Canonical Control Plane risk vocabulary. `critical` is accepted from
# authority_engine upgrades — validator still rejects anything not in
# (low, medium, high) for backwards compatibility, and `critical` is
# surfaced via `requires_approval` + `blocked_auto_execute` flags.
RiskLevel = Literal["low", "medium", "high", "critical"]

_CP_RISK_VALUES: tuple[str, ...] = ("low", "medium", "high", "critical")

# Map authority_engine uppercase classes → Control Plane lowercase.
_AUTHORITY_TO_CP: dict[str, RiskLevel] = {
    "LOW": "low",
    "MEDIUM": "medium",
    "HIGH": "high",
    "CRITICAL": "critical",
}

# Reverse — Control Plane → authority_engine vocabulary.
_CP_TO_AUTHORITY: dict[str, str] = {
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
    "critical": "CRITICAL",
}

# Minimum autonomy level required to auto-execute at each risk level.
# Mirrors authority_engine.MIN_LEVEL_TO_EXECUTE but lives here so the
# Control Plane can enforce it without importing the business layer.
MIN_AUTONOMY_LEVEL: dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 3,
    "critical": 999,  # never auto-execute
}


def normalize_risk(value: str | None) -> RiskLevel:
    """Coerce any caller-provided risk string into the canonical vocabulary.

    Accepts both control-plane (`low`) and authority-engine (`LOW`)
    forms. Unknown or empty → `low` (safest default for a runtime
    action; callers that need strict validation use `validate_action`).
    """
    if not value:
        return "low"
    v = value.strip().lower()
    if v in _CP_RISK_VALUES:
        return v  # type: ignore[return-value]
    return "low"


def map_to_authority_class(risk: str) -> str:
    """Translate a Control Plane risk level to authority_engine vocabulary."""
    return _CP_TO_AUTHORITY.get(normalize_risk(risk), "LOW")


def required_autonomy_level(risk: str) -> int:
    """Minimum org/workflow autonomy level required to auto-execute."""
    return MIN_AUTONOMY_LEVEL[normalize_risk(risk)]


def requires_explicit_approval(risk: str) -> bool:
    """Whether the Control Plane will defer this action absent explicit approval."""
    return normalize_risk(risk) in ("medium", "high", "critical")


def blocks_auto_execute(risk: str) -> bool:
    """Whether the action must never auto-execute regardless of approval context."""
    return normalize_risk(risk) == "critical"


def authority_classify(business_action_type: str) -> Optional[RiskLevel]:
    """Lazy, failure-tolerant lookup into `authority_engine.RISK_CLASSES`.

    Returns the canonical Control Plane risk for a business action type
    (`send_dm`, `publish_content`, ...) if the authority engine is
    importable and knows about it. Returns None on any failure — the
    Control Plane must never crash because the business layer is
    unavailable.
    """
    try:
        from governance.policy.authority_engine import RISK_CLASSES  # lazy import
    except Exception:
        return None
    for upper_class, actions in RISK_CLASSES.items():
        if business_action_type in actions:
            return _AUTHORITY_TO_CP.get(upper_class)
    return None


def resolve_effective_risk(
    declared_risk: str,
    business_action_type: str | None = None,
) -> RiskLevel:
    """Return the stricter of the declared Control Plane risk and any
    business-layer classification.

    Rationale: a runtime action (e.g. `run_script`) that *also* represents
    a business action (e.g. `publish_content`) should never execute at a
    lower risk than the business layer demands. The stricter wins.
    """
    declared = normalize_risk(declared_risk)
    if not business_action_type:
        return declared
    upgraded = authority_classify(business_action_type)
    if not upgraded:
        return declared
    # Ordering: critical > high > medium > low
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    return declared if order[declared] >= order[upgraded] else upgraded


__all__ = [
    "RiskLevel",
    "normalize_risk",
    "map_to_authority_class",
    "required_autonomy_level",
    "requires_explicit_approval",
    "blocks_auto_execute",
    "authority_classify",
    "resolve_effective_risk",
]
