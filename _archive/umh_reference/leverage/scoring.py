"""Phase 87 leverage scoring — deterministic scoring of leverage opportunities.

All scores bounded [0, 1]. High dependency risk lowers overall. Low
reversibility lowers overall if risk is high. High compounding raises overall.
Short time-to-impact raises tactical score. Strategic alignment raises
strategic score.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.leverage.contracts import (
    LeverageConfidence,
    LeverageOpportunity,
    LeverageRiskLevel,
    LeverageTimeHorizon,
    _lev_id,
    clamp_score,
)


# ─── Individual Scoring Functions ───────────────────────────────────


_RISK_PENALTY: dict[LeverageRiskLevel, float] = {
    LeverageRiskLevel.NONE: 0.0,
    LeverageRiskLevel.LOW: 0.1,
    LeverageRiskLevel.MEDIUM: 0.25,
    LeverageRiskLevel.HIGH: 0.45,
    LeverageRiskLevel.CRITICAL: 0.7,
    LeverageRiskLevel.UNKNOWN: 0.3,
}

_CONFIDENCE_WEIGHT: dict[LeverageConfidence, float] = {
    LeverageConfidence.VERY_LOW: 0.2,
    LeverageConfidence.LOW: 0.4,
    LeverageConfidence.MEDIUM: 0.6,
    LeverageConfidence.HIGH: 0.8,
    LeverageConfidence.VERY_HIGH: 1.0,
    LeverageConfidence.UNKNOWN: 0.3,
}

_TIME_HORIZON_TACTICAL: dict[str, float] = {
    "today": 1.0,
    "week": 0.9,
    "month": 0.7,
    "quarter": 0.5,
    "year": 0.3,
    "three_year": 0.15,
    "ten_year": 0.08,
    "thirty_year": 0.04,
    "century": 0.02,
    "unknown": 0.3,
}

_REVERSIBILITY_SCORE: dict[str, float] = {
    "reversible": 1.0,
    "mostly_reversible": 0.8,
    "partially_reversible": 0.5,
    "irreversible": 0.1,
}


def score_multiplier(opp: LeverageOpportunity) -> float:
    raw = opp.expected_multiplier
    if raw <= 1.0:
        return 0.0
    return clamp_score(min(raw / 20.0, 1.0))


def score_time_to_impact(opp: LeverageOpportunity) -> float:
    tti = opp.time_to_impact.lower().strip() if opp.time_to_impact else "unknown"
    return clamp_score(_TIME_HORIZON_TACTICAL.get(tti, 0.3))


def score_cost_efficiency(opp: LeverageOpportunity) -> float:
    cost_str = opp.cost.lower().strip() if opp.cost else ""
    if not cost_str or cost_str in ("none", "free", "$0", "zero"):
        return 1.0
    if cost_str in ("low", "minimal", "cheap"):
        return 0.85
    if cost_str in ("medium", "moderate"):
        return 0.6
    if cost_str in ("high", "expensive"):
        return 0.3
    if cost_str in ("very high", "extreme"):
        return 0.1
    return 0.5


def score_risk_adjusted_value(opp: LeverageOpportunity) -> float:
    base = score_multiplier(opp)
    penalty = _RISK_PENALTY.get(opp.risk_level, 0.3)
    conf = _CONFIDENCE_WEIGHT.get(opp.confidence, 0.3)
    return clamp_score(base * (1.0 - penalty) * conf)


def score_reversibility(opp: LeverageOpportunity) -> float:
    rev = opp.reversibility.lower().strip() if opp.reversibility else "reversible"
    return clamp_score(_REVERSIBILITY_SCORE.get(rev, 0.5))


def score_compounding_potential(opp: LeverageOpportunity) -> float:
    return clamp_score(opp.compounding_potential)


def score_strategic_alignment(opp: LeverageOpportunity) -> float:
    return clamp_score(opp.strategic_alignment)


def score_attention_efficiency(opp: LeverageOpportunity) -> float:
    attn = opp.attention_required.lower().strip() if opp.attention_required else ""
    if not attn or attn in ("none", "zero", "minimal"):
        return 1.0
    if attn in ("low"):
        return 0.85
    if attn in ("medium", "moderate"):
        return 0.6
    if attn in ("high"):
        return 0.35
    if attn in ("very high", "extreme", "full"):
        return 0.15
    return 0.5


def score_dependency_risk(opp: LeverageOpportunity) -> float:
    meta_dep = str(opp.metadata.get("dependency_risk", "")).lower()
    if meta_dep in ("none", "low"):
        return 0.9
    if meta_dep in ("medium", "moderate"):
        return 0.6
    if meta_dep in ("high"):
        return 0.3
    if meta_dep in ("critical"):
        return 0.1
    return 0.6


def score_overall_leverage(opp: LeverageOpportunity) -> float:
    mult = score_multiplier(opp)
    tti = score_time_to_impact(opp)
    cost = score_cost_efficiency(opp)
    risk_adj = score_risk_adjusted_value(opp)
    rev = score_reversibility(opp)
    compound = score_compounding_potential(opp)
    strategic = score_strategic_alignment(opp)
    attn = score_attention_efficiency(opp)
    dep = score_dependency_risk(opp)

    # Weighted composite
    raw = (
        mult * 0.15
        + tti * 0.10
        + cost * 0.10
        + risk_adj * 0.15
        + rev * 0.05
        + compound * 0.15
        + strategic * 0.15
        + attn * 0.10
        + dep * 0.05
    )

    # Penalties
    if dep < 0.4:
        raw *= 0.8
    if rev < 0.3 and opp.risk_level in (LeverageRiskLevel.HIGH, LeverageRiskLevel.CRITICAL):
        raw *= 0.7

    # Bonuses
    if compound > 0.7:
        raw = min(raw * 1.15, 1.0)

    return clamp_score(raw)


# ─── Scorecard ──────────────────────────────────────────────────────


@dataclass
class LeverageScorecard:
    scorecard_id: str = ""
    opportunity_id: str = ""
    multiplier_score: float = 0.0
    time_to_impact_score: float = 0.0
    cost_efficiency_score: float = 0.0
    risk_adjusted_score: float = 0.0
    reversibility_score: float = 0.0
    compounding_score: float = 0.0
    strategic_alignment_score: float = 0.0
    attention_efficiency_score: float = 0.0
    dependency_risk_score: float = 0.0
    overall_score: float = 0.0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scorecard_id": self.scorecard_id,
            "opportunity_id": self.opportunity_id,
            "multiplier_score": round(self.multiplier_score, 4),
            "time_to_impact_score": round(self.time_to_impact_score, 4),
            "cost_efficiency_score": round(self.cost_efficiency_score, 4),
            "risk_adjusted_score": round(self.risk_adjusted_score, 4),
            "reversibility_score": round(self.reversibility_score, 4),
            "compounding_score": round(self.compounding_score, 4),
            "strategic_alignment_score": round(self.strategic_alignment_score, 4),
            "attention_efficiency_score": round(self.attention_efficiency_score, 4),
            "dependency_risk_score": round(self.dependency_risk_score, 4),
            "overall_score": round(self.overall_score, 4),
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


def build_leverage_scorecard(opp: LeverageOpportunity) -> LeverageScorecard:
    warnings: list[str] = []

    dep = score_dependency_risk(opp)
    if dep < 0.4:
        warnings.append("High dependency risk — overall score reduced")

    rev = score_reversibility(opp)
    if rev < 0.3 and opp.risk_level in (LeverageRiskLevel.HIGH, LeverageRiskLevel.CRITICAL):
        warnings.append("Low reversibility + high risk — overall score reduced")

    if opp.confidence in (LeverageConfidence.VERY_LOW, LeverageConfidence.LOW):
        warnings.append("Low confidence — consider RESEARCH before committing")

    return LeverageScorecard(
        scorecard_id=_lev_id("sc"),
        opportunity_id=opp.opportunity_id,
        multiplier_score=score_multiplier(opp),
        time_to_impact_score=score_time_to_impact(opp),
        cost_efficiency_score=score_cost_efficiency(opp),
        risk_adjusted_score=score_risk_adjusted_value(opp),
        reversibility_score=rev,
        compounding_score=score_compounding_potential(opp),
        strategic_alignment_score=score_strategic_alignment(opp),
        attention_efficiency_score=score_attention_efficiency(opp),
        dependency_risk_score=dep,
        overall_score=score_overall_leverage(opp),
        warnings=warnings,
    )


def rank_leverage_opportunities(
    opportunities: list[LeverageOpportunity],
) -> list[tuple[LeverageOpportunity, LeverageScorecard]]:
    scored = [(opp, build_leverage_scorecard(opp)) for opp in opportunities]
    scored.sort(key=lambda x: x[1].overall_score, reverse=True)
    return scored


def leverage_scorecard_to_dict(sc: LeverageScorecard) -> dict[str, Any]:
    return sc.to_dict()
