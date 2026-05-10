"""Phase 85/85B council views — UI-safe read models for council data.

Includes Phase 85 advisory/health views and Phase 85B enhanced advisory view.
No sensitive data exposed. No execution. No mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


@dataclass
class CouncilAdvisoryView:
    advisory_id: str = ""
    request_id: str = ""
    status: str = ""
    primary_recommendation: str = ""
    confidence: str = ""
    is_actionable: bool = False
    perspective_count: int = 0
    consensus_strength: float = 0.0
    coverage_score: float = 0.0
    gap_count: int = 0
    disagreement_count: int = 0
    warning_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "advisory_id": self.advisory_id,
            "request_id": self.request_id,
            "status": self.status,
            "primary_recommendation": self.primary_recommendation,
            "confidence": self.confidence,
            "is_actionable": self.is_actionable,
            "perspective_count": self.perspective_count,
            "consensus_strength": round(self.consensus_strength, 3),
            "coverage_score": round(self.coverage_score, 3),
            "gap_count": self.gap_count,
            "disagreement_count": self.disagreement_count,
            "warning_count": self.warning_count,
            "metadata": self.metadata,
        }


@dataclass
class CouncilHealthView:
    generated_at: str = ""
    council_available: bool = False
    role_count: int = 0
    default_roles_present: bool = False
    ontology_bridge_ready: bool = False
    polarity_integration_ready: bool = False
    archetype_count: int = 0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "council_available": self.council_available,
            "role_count": self.role_count,
            "default_roles_present": self.default_roles_present,
            "ontology_bridge_ready": self.ontology_bridge_ready,
            "polarity_integration_ready": self.polarity_integration_ready,
            "archetype_count": self.archetype_count,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def advisory_to_view(advisory: Any) -> CouncilAdvisoryView:
    rec = getattr(advisory, "recommendation", None)
    status = getattr(advisory, "status", None)
    conf = getattr(advisory, "overall_confidence", None)
    gap_summary = getattr(advisory, "gap_summary", {}) or {}
    disagr_summary = getattr(advisory, "disagreement_summary", {}) or {}

    primary_rec = ""
    consensus_strength = 0.0
    coverage_score = 0.0
    if rec:
        primary_rec = getattr(rec, "primary_recommendation", "")
        consensus_strength = getattr(rec, "consensus_strength", 0.0)
        coverage_score = getattr(rec, "coverage_score", 0.0)

    return CouncilAdvisoryView(
        advisory_id=getattr(advisory, "advisory_id", ""),
        request_id=getattr(advisory, "request_id", ""),
        status=status.value if hasattr(status, "value") else str(status or ""),
        primary_recommendation=primary_rec,
        confidence=conf.value if hasattr(conf, "value") else str(conf or ""),
        is_actionable=getattr(advisory, "is_actionable", False),
        perspective_count=getattr(advisory, "perspective_count", 0),
        consensus_strength=consensus_strength,
        coverage_score=coverage_score,
        gap_count=gap_summary.get("gap_count", 0),
        disagreement_count=disagr_summary.get("total", 0),
        warning_count=len(getattr(advisory, "warnings", [])),
    )


@dataclass
class EnhancedAdvisoryView:
    """Phase 85B — UI-safe read model for enhanced council advisory."""

    enhanced_id: str = ""
    base_advisory_id: str = ""
    base_status: str = ""
    primary_recommendation: str = ""
    is_actionable: bool = False
    dissent_preserved: bool = False
    minority_count: int = 0
    false_consensus_risk: float = 0.0
    consensus_quality: str = ""
    red_team_risk_level: str = ""
    blue_team_guardrail_count: int = 0
    guardrails: list[str] = field(default_factory=list)
    non_actions: list[str] = field(default_factory=list)
    residual_uncertainty_count: int = 0
    what_would_change_count: int = 0
    overall_safe: bool = True
    warning_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enhanced_id": self.enhanced_id,
            "base_advisory_id": self.base_advisory_id,
            "base_status": self.base_status,
            "primary_recommendation": self.primary_recommendation,
            "is_actionable": self.is_actionable,
            "dissent_preserved": self.dissent_preserved,
            "minority_count": self.minority_count,
            "false_consensus_risk": round(self.false_consensus_risk, 3),
            "consensus_quality": self.consensus_quality,
            "red_team_risk_level": self.red_team_risk_level,
            "blue_team_guardrail_count": self.blue_team_guardrail_count,
            "guardrails": self.guardrails,
            "non_actions": self.non_actions,
            "residual_uncertainty_count": self.residual_uncertainty_count,
            "what_would_change_count": self.what_would_change_count,
            "overall_safe": self.overall_safe,
            "warning_count": self.warning_count,
            "metadata": self.metadata,
        }


def enhanced_advisory_to_view(enhanced: Any) -> EnhancedAdvisoryView:
    """Convert an EnhancedCouncilAdvisory to a UI-safe view."""
    base = getattr(enhanced, "base_advisory", None)
    base_id = getattr(base, "advisory_id", "") if base else ""
    base_status_obj = getattr(base, "status", None) if base else None
    base_status = (
        base_status_obj.value if hasattr(base_status_obj, "value") else str(base_status_obj or "")
    )
    base_rec = getattr(base, "recommendation", None) if base else None
    primary_rec = getattr(base_rec, "primary_recommendation", "") if base_rec else ""
    is_actionable = getattr(base, "is_actionable", False) if base else False

    minority = getattr(enhanced, "minority", None)
    consensus = getattr(enhanced, "consensus", None)
    red_team = getattr(enhanced, "red_team", None)
    blue_team = getattr(enhanced, "blue_team", None)

    consensus_quality = ""
    if consensus:
        cq = getattr(consensus, "quality", None)
        consensus_quality = cq.value if hasattr(cq, "value") else str(cq or "")

    return EnhancedAdvisoryView(
        enhanced_id=getattr(enhanced, "enhanced_id", ""),
        base_advisory_id=base_id,
        base_status=base_status,
        primary_recommendation=primary_rec,
        is_actionable=is_actionable,
        dissent_preserved=getattr(enhanced, "dissent_preserved", False),
        minority_count=getattr(minority, "minority_count", 0) if minority else 0,
        false_consensus_risk=getattr(enhanced, "false_consensus_risk", 0.0),
        consensus_quality=consensus_quality,
        red_team_risk_level=getattr(red_team, "overall_risk_level", "") if red_team else "",
        blue_team_guardrail_count=getattr(blue_team, "guardrail_count", 0) if blue_team else 0,
        guardrails=getattr(enhanced, "guardrails", []),
        non_actions=getattr(enhanced, "non_actions", []),
        residual_uncertainty_count=len(getattr(enhanced, "residual_uncertainty", [])),
        what_would_change_count=len(getattr(enhanced, "what_would_change", [])),
        overall_safe=getattr(enhanced, "overall_safe", True),
        warning_count=len(getattr(enhanced, "warnings", [])),
    )


def build_council_health_view() -> CouncilHealthView:
    warnings: list[str] = []
    council_available = False
    role_count = 0
    default_present = False
    bridge_ready = False
    polarity_ready = False

    try:
        from umh.council.roles import get_default_council_roles

        roles = get_default_council_roles()
        role_count = len(roles)
        default_present = role_count >= 5
        council_available = True
    except ImportError:
        warnings.append("Council roles module not available")

    try:
        from umh.council.ontology_bridge import resolve_ontology_context  # noqa: F401

        bridge_ready = True
    except ImportError:
        warnings.append("Ontology bridge not available")

    archetype_count = 0
    try:
        from umh.council.archetypes import get_all_thinker_profiles

        archetype_count = len(get_all_thinker_profiles())
    except ImportError:
        warnings.append("Thinker archetypes not available")

    try:
        from umh.ontology.polarity_synthesis import PolaritySynthesisStatus  # noqa: F401

        polarity_ready = True
    except ImportError:
        warnings.append("Polarity synthesis not available")

    return CouncilHealthView(
        generated_at=_iso_now(),
        council_available=council_available,
        role_count=role_count,
        default_roles_present=default_present,
        ontology_bridge_ready=bridge_ready,
        polarity_integration_ready=polarity_ready,
        archetype_count=archetype_count,
        warnings=warnings,
    )
