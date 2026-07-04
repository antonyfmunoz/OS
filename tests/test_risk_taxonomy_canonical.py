"""WP-P2-002 — canonical risk vocabulary + fail-closed coercion tests.

Proves the canonical two-axis risk spine (SeverityClass x ActionRiskCategory)
coerces every vocabulary into the canonical severity, that unknown values FAIL
CLOSED (never downgrade to LOW), that the stricter-of-two rule holds, and that
the two hard-gate fail-open sites (agent_registry.can_handle_risk,
orchestrator/decisions._risk) now fail closed. The remaining scoring/planning
default sites are documented follow-on and are not covered here.
"""

from __future__ import annotations

from substrate.canonical_types import CANONICAL_TYPES
from substrate.governance.risk_classes import (
    ActionRiskCategory,
    SeverityClass,
    coerce_risk_class,
    severity_rank,
    stricter_of,
)

# ── canonical registration ───────────────────────────────────────────────────


def test_action_risk_category_registered():
    assert CANONICAL_TYPES.get("ActionRiskCategory") == ["substrate.governance.risk_classes"]


def test_risk_class_still_registered():
    assert CANONICAL_TYPES.get("RiskClass") == ["substrate.types"]


# ── coercion: known values map correctly ─────────────────────────────────────


def test_known_severity_names_map():
    assert coerce_risk_class("critical") == SeverityClass.CRITICAL
    assert coerce_risk_class("high") == SeverityClass.HIGH
    assert coerce_risk_class("medium") == SeverityClass.MEDIUM
    assert coerce_risk_class("low") == SeverityClass.LOW
    assert coerce_risk_class("negligible") == SeverityClass.NEGLIGIBLE
    assert coerce_risk_class("forbidden") == SeverityClass.FORBIDDEN


def test_category_maps_via_bridge():
    assert coerce_risk_class(ActionRiskCategory.FINANCIAL) == SeverityClass.CRITICAL
    assert coerce_risk_class(ActionRiskCategory.READ_ONLY) == SeverityClass.NEGLIGIBLE
    assert coerce_risk_class(ActionRiskCategory.IRREVERSIBLE_WRITE) == SeverityClass.HIGH


def test_severity_class_passthrough():
    assert coerce_risk_class(SeverityClass.MEDIUM) == SeverityClass.MEDIUM


# ── coercion: unknown FAILS CLOSED (never low) ───────────────────────────────


def test_unknown_fails_closed_to_high():
    assert coerce_risk_class("bogus") == SeverityClass.HIGH
    assert coerce_risk_class("") == SeverityClass.HIGH
    assert coerce_risk_class(None) == SeverityClass.HIGH
    assert coerce_risk_class(12345) == SeverityClass.HIGH


def test_unknown_never_downgrades_to_low_or_negligible():
    for junk in ("xyz", "", None, "unspecified", "n/a"):
        result = coerce_risk_class(junk)
        assert result not in (SeverityClass.LOW, SeverityClass.NEGLIGIBLE), (
            f"unknown risk {junk!r} downgraded to {result} — must fail closed"
        )


# ── stricter-of-two (disagreement resolution) ────────────────────────────────


def test_stricter_of_picks_higher_severity():
    assert stricter_of("low", "critical") == SeverityClass.CRITICAL
    assert stricter_of("critical", "low") == SeverityClass.CRITICAL
    assert stricter_of("medium", "high") == SeverityClass.HIGH


def test_stricter_of_unknown_can_only_raise():
    # An unknown value coerces to HIGH, so it can only raise the result.
    assert stricter_of("bogus", "low") == SeverityClass.HIGH
    assert stricter_of("negligible", "bogus") == SeverityClass.HIGH


def test_severity_rank_monotonic():
    assert (
        severity_rank("negligible")
        < severity_rank("low")
        < severity_rank("medium")
        < severity_rank("high")
        < severity_rank("critical")
        < severity_rank("forbidden")
    )
    # unknown ranks as HIGH
    assert severity_rank("bogus") == severity_rank("high")


# ── the two hard-gate fail-open sites now fail closed ─────────────────────────


def test_agent_registry_fails_closed_on_unknown_risk():
    from substrate.organism.agent_registry import AgentType

    agent = AgentType(agent_type_id="t", label="t", description="d", max_risk_class="low")
    assert agent.can_handle_risk("low") is True
    assert agent.can_handle_risk("critical") is False
    # unknown REQUEST risk must be rejected (was silently allowed as "low")
    assert agent.can_handle_risk("bogus") is False


def test_agent_registry_unknown_ceiling_is_restrictive():
    from substrate.organism.agent_registry import AgentType

    agent = AgentType(agent_type_id="t", label="t", description="d", max_risk_class="mystery")
    # a misconfigured/unknown ceiling must permit almost nothing, not everything
    assert agent.can_handle_risk("low") is False


def test_orchestrator_missing_risk_escalates():
    from substrate.control_plane.runtime.orchestrator import decisions

    # missing risk_level must escalate (was silently "low" -> not escalated)
    assert decisions._risk({}) == "high"
    assert decisions._risk({}) in decisions.ALWAYS_ESCALATE_RISK
    assert decisions._risk({"risk_level": "garbage"}) == "high"
    assert decisions._risk({"risk_level": "low"}) == "low"


# ── approval authority uses canonical severity (P1-007 preserved) ────────────


def test_approval_authority_coerce_still_fail_closed():
    from substrate.organism.approval_authority import _coerce_risk
    from substrate.types import RiskClass

    assert _coerce_risk("bogus") == RiskClass.HIGH
    assert _coerce_risk("low") == RiskClass.LOW


# ── role/permission canonicals verified + registered (WP-P2-002) ─────────────
# WP-P2-002 VERIFIES (does not rebuild) the existing role/permission canonicals.
# The unknown→READ permission-envelope fail-open in required_tier_for_action is
# tracked follow-on (see test_permission_tiers.test_unknown_defaults_to_read):
# fixing it couples into the authority engine's risk classification, which is
# out of this packet's mandate ("no new risk taxonomy").


def test_role_permission_canonicals_registered():
    from substrate.canonical_types import CANONICAL_TYPES

    assert "PermissionTier" in CANONICAL_TYPES
    assert "AutonomyLevel" in CANONICAL_TYPES
    assert "AgentRole" in CANONICAL_TYPES
