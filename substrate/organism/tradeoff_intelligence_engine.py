"""C14.1 — Tradeoff Intelligence Engine.

Models executive tradeoffs. "If we do X, what do we NOT do?"
Deterministic displacement analysis.

No execution authority. No mutation authority. Analysis only.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ────────────────────────────────────────────────────────────


class TradeoffSeverity(str, Enum):
    NEGLIGIBLE = "negligible"
    MINOR = "minor"
    SIGNIFICANT = "significant"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class TradeoffOption:
    option_id: str = ""
    target_id: str = ""
    target_name: str = ""
    target_type: str = ""
    resource_cost: dict[str, float] = field(default_factory=dict)
    leverage_score: float = 0.0
    impact_score: float = 0.0
    risk_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "option_id": self.option_id,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "target_type": self.target_type,
            "resource_cost": {k: round(v, 4) for k, v in self.resource_cost.items()},
            "leverage_score": round(self.leverage_score, 4),
            "impact_score": round(self.impact_score, 4),
            "risk_score": round(self.risk_score, 4),
        }


@dataclass
class TradeoffAnalysis:
    analysis_id: str = ""
    chosen: dict[str, Any] = field(default_factory=dict)
    displaced: list[dict[str, Any]] = field(default_factory=list)
    leverage_delta: float = 0.0
    impact_delta: float = 0.0
    risk_delta: float = 0.0
    severity: str = TradeoffSeverity.NEGLIGIBLE.value
    recommendation: str = "proceed"
    rationale: str = ""
    source_signals: list[str] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "chosen": self.chosen,
            "displaced": self.displaced,
            "leverage_delta": round(self.leverage_delta, 4),
            "impact_delta": round(self.impact_delta, 4),
            "risk_delta": round(self.risk_delta, 4),
            "severity": self.severity,
            "recommendation": self.recommendation,
            "rationale": self.rationale,
            "source_signals": self.source_signals,
            "generated_at": self.generated_at,
        }


@dataclass
class TradeoffSnapshot:
    active_tradeoffs: list[dict[str, Any]] = field(default_factory=list)
    highest_cost_targets: list[dict[str, Any]] = field(default_factory=list)
    resource_contention: dict[str, list[str]] = field(default_factory=dict)
    overall_severity: str = TradeoffSeverity.NEGLIGIBLE.value
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_tradeoffs": self.active_tradeoffs,
            "highest_cost_targets": self.highest_cost_targets,
            "resource_contention": self.resource_contention,
            "overall_severity": self.overall_severity,
            "generated_at": self.generated_at,
        }


# ── Runtime ──────────────────────────────────────────────────────────


class TradeoffIntelligenceEngine:
    """Models executive tradeoffs and displacement analysis.

    Composes ResourceAllocationRuntime (C14.0) with 5 existing subsystems
    to compute what gets crowded out when resources are allocated.

    No execution authority. No mutation authority. Analysis only.
    """

    SEVERITY_THRESHOLDS = {
        "critical": 0.6,
        "major": 0.4,
        "significant": 0.25,
        "minor": 0.1,
    }

    def __init__(
        self,
        resource_allocation: Any | None = None,
        strategic_planning: Any | None = None,
        goal_alignment: Any | None = None,
        work_portfolio: Any | None = None,
        capability_gap: Any | None = None,
        prediction_portfolio: Any | None = None,
    ) -> None:
        self._resource_allocation = resource_allocation
        self._strategic_planning = strategic_planning
        self._goal_alignment = goal_alignment
        self._work_portfolio = work_portfolio
        self._capability_gap = capability_gap
        self._prediction_portfolio = prediction_portfolio

    # ── Lazy subsystem access ─────────────────────────────────────

    @property
    def _allocation(self) -> Any | None:
        if self._resource_allocation is None:
            try:
                from substrate.organism.resource_allocation_runtime import ResourceAllocationRuntime
                self._resource_allocation = ResourceAllocationRuntime()
            except Exception:
                logger.debug("tradeoff: could not lazy-load resource_allocation")
        return self._resource_allocation

    @property
    def _planning(self) -> Any | None:
        if self._strategic_planning is None:
            try:
                from substrate.organism.strategic_planning_engine import StrategicPlanningEngine
                self._strategic_planning = StrategicPlanningEngine()
            except Exception:
                logger.debug("tradeoff: could not lazy-load strategic_planning")
        return self._strategic_planning

    @property
    def _goals(self) -> Any | None:
        if self._goal_alignment is None:
            try:
                from substrate.organism.goal_alignment_engine import GoalAlignmentEngine
                self._goal_alignment = GoalAlignmentEngine()
            except Exception:
                logger.debug("tradeoff: could not lazy-load goal_alignment")
        return self._goal_alignment

    @property
    def _work(self) -> Any | None:
        if self._work_portfolio is None:
            try:
                from substrate.organism.work_portfolio_runtime import WorkPortfolioRuntime
                self._work_portfolio = WorkPortfolioRuntime()
            except Exception:
                logger.debug("tradeoff: could not lazy-load work_portfolio")
        return self._work_portfolio

    @property
    def _caps(self) -> Any | None:
        if self._capability_gap is None:
            try:
                from substrate.organism.capability_gap_engine import CapabilityGapEngine
                self._capability_gap = CapabilityGapEngine()
            except Exception:
                logger.debug("tradeoff: could not lazy-load capability_gap")
        return self._capability_gap

    @property
    def _prediction(self) -> Any | None:
        if self._prediction_portfolio is None:
            try:
                from substrate.organism.prediction_portfolio_runtime import PredictionPortfolioRuntime
                self._prediction_portfolio = PredictionPortfolioRuntime()
            except Exception:
                logger.debug("tradeoff: could not lazy-load prediction_portfolio")
        return self._prediction_portfolio

    # ── Signal extraction ─────────────────────────────────────────

    def _get_all_recommendations(self) -> list[Any]:
        try:
            if self._allocation is None:
                return []
            return list(self._allocation.recommend_all())
        except Exception:
            logger.debug("tradeoff: recommend_all failed")
            return []

    def _get_budgets(self) -> list[Any]:
        try:
            if self._allocation is None:
                return []
            return list(self._allocation.budgets())
        except Exception:
            logger.debug("tradeoff: budgets failed")
            return []

    def _get_roadmap(self) -> dict[str, Any]:
        try:
            if self._planning is None:
                return {}
            rm = self._planning.roadmap()
            return rm if isinstance(rm, dict) else {}
        except Exception:
            logger.debug("tradeoff: roadmap failed")
            return {}

    def _get_coverage(self) -> dict[str, int]:
        try:
            if self._goals is None:
                return {}
            return self._goals.coverage()
        except Exception:
            logger.debug("tradeoff: coverage failed")
            return {}

    def _get_velocity(self) -> dict[str, Any]:
        try:
            if self._work is None:
                return {}
            v = self._work.velocity()
            return v if isinstance(v, dict) else {"completions_per_day": float(v)}
        except Exception:
            logger.debug("tradeoff: velocity failed")
            return {}

    def _get_at_risk_work(self) -> list[Any]:
        try:
            if self._work is None:
                return []
            return list(self._work.at_risk_work())
        except Exception:
            logger.debug("tradeoff: at_risk_work failed")
            return []

    def _get_critical_gaps(self) -> list[Any]:
        try:
            if self._caps is None:
                return []
            return list(self._caps.critical_gaps())
        except Exception:
            logger.debug("tradeoff: critical_gaps failed")
            return []

    def _get_highest_risk_forecasts(self) -> list[Any]:
        try:
            if self._prediction is None:
                return []
            return list(self._prediction.highest_risk_forecasts(limit=10))
        except Exception:
            logger.debug("tradeoff: highest_risk_forecasts failed")
            return []

    # ── Option building ───────────────────────────────────────────

    def _build_option(self, rec: Any) -> TradeoffOption:
        target_id = getattr(rec, "target_id", "")
        target_name = getattr(rec, "target_name", target_id)
        target_type = getattr(rec, "target_type", "goal")
        leverage = getattr(rec, "leverage_score", 0.0)

        roadmap = self._get_roadmap()
        goal_data = roadmap.get(target_id, {})
        goal_count = max(len(roadmap), 1)

        time_cost = 1.0 / goal_count
        attention_cost = time_cost * 1.2 if target_id in [
            getattr(w, "id", str(w)) for w in self._get_at_risk_work()
        ] else time_cost
        cap_gaps = self._get_critical_gaps()
        cap_cost = 0.3 if cap_gaps else 0.1
        exec_cost = time_cost

        resource_cost = {
            "time": round(min(time_cost, 1.0), 4),
            "attention": round(min(attention_cost, 1.0), 4),
            "capital": 0.1,
            "capability_building": round(min(cap_cost, 1.0), 4),
            "execution_capacity": round(min(exec_cost, 1.0), 4),
        }

        risk_forecasts = self._get_highest_risk_forecasts()
        risk_ids = {getattr(f, "entity_id", "") for f in risk_forecasts}
        risk_score = 0.7 if target_id in risk_ids else 0.2

        impact_score = leverage * 0.8 + (0.2 if target_type == "goal" else 0.1)

        return TradeoffOption(
            option_id=str(uuid.uuid4())[:8],
            target_id=target_id,
            target_name=target_name,
            target_type=target_type,
            resource_cost=resource_cost,
            leverage_score=leverage,
            impact_score=round(min(impact_score, 1.0), 4),
            risk_score=round(risk_score, 4),
        )

    # ── Displacement logic ────────────────────────────────────────

    def _compute_displaced(
        self, chosen: TradeoffOption, all_options: list[TradeoffOption]
    ) -> list[TradeoffOption]:
        displaced: list[TradeoffOption] = []
        for opt in all_options:
            if opt.target_id == chosen.target_id:
                continue
            contention = sum(
                1 for rt in chosen.resource_cost
                if chosen.resource_cost.get(rt, 0) > 0.2
                and opt.resource_cost.get(rt, 0) > 0.2
            )
            if contention >= 2:
                displaced.append(opt)
        displaced.sort(key=lambda o: o.leverage_score, reverse=True)
        return displaced

    def _classify_severity(
        self, leverage_delta: float, risk_delta: float
    ) -> TradeoffSeverity:
        combined = abs(leverage_delta) + abs(risk_delta) * 0.5
        t = self.SEVERITY_THRESHOLDS
        if combined >= t["critical"]:
            return TradeoffSeverity.CRITICAL
        if combined >= t["major"]:
            return TradeoffSeverity.MAJOR
        if combined >= t["significant"]:
            return TradeoffSeverity.SIGNIFICANT
        if combined >= t["minor"]:
            return TradeoffSeverity.MINOR
        return TradeoffSeverity.NEGLIGIBLE

    def _classify_recommendation(
        self, severity: TradeoffSeverity, leverage_delta: float
    ) -> str:
        if severity in (TradeoffSeverity.CRITICAL, TradeoffSeverity.MAJOR):
            if leverage_delta < 0:
                return "defer"
            return "reconsider"
        if severity == TradeoffSeverity.SIGNIFICANT:
            return "reconsider"
        return "proceed"

    # ── Public API ────────────────────────────────────────────────

    def analyze(self, target_id: str) -> TradeoffAnalysis:
        recs = self._get_all_recommendations()
        options = [self._build_option(r) for r in recs]

        chosen_opt = None
        for opt in options:
            if opt.target_id == target_id:
                chosen_opt = opt
                break

        if chosen_opt is None:
            return TradeoffAnalysis(
                analysis_id=str(uuid.uuid4())[:8],
                rationale=f"target {target_id} not found in allocation recommendations",
                generated_at=time.time(),
            )

        displaced = self._compute_displaced(chosen_opt, options)

        max_displaced_leverage = max(
            (d.leverage_score for d in displaced), default=0.0
        )
        leverage_delta = chosen_opt.leverage_score - max_displaced_leverage

        max_displaced_risk = max(
            (d.risk_score for d in displaced), default=0.0
        )
        risk_delta = chosen_opt.risk_score - max_displaced_risk

        impact_delta = chosen_opt.impact_score - (
            max((d.impact_score for d in displaced), default=0.0)
        )

        severity = self._classify_severity(leverage_delta, risk_delta)
        recommendation = self._classify_recommendation(severity, leverage_delta)

        signals = [
            f"chosen_leverage={chosen_opt.leverage_score:.2f}",
            f"displaced_count={len(displaced)}",
            f"max_displaced_leverage={max_displaced_leverage:.2f}",
            f"severity={severity.value}",
        ]

        rationale_parts = []
        if displaced:
            top_displaced = displaced[0]
            rationale_parts.append(
                f"displaces {top_displaced.target_name} "
                f"(leverage={top_displaced.leverage_score:.2f})"
            )
        if leverage_delta > 0:
            rationale_parts.append(
                f"chosen has {leverage_delta:.2f} more leverage than top displaced"
            )
        elif leverage_delta < 0:
            rationale_parts.append(
                f"chosen has {abs(leverage_delta):.2f} LESS leverage than top displaced"
            )
        if not rationale_parts:
            rationale_parts.append("no competing targets displaced")

        return TradeoffAnalysis(
            analysis_id=str(uuid.uuid4())[:8],
            chosen=chosen_opt.to_dict(),
            displaced=[d.to_dict() for d in displaced],
            leverage_delta=round(leverage_delta, 4),
            impact_delta=round(impact_delta, 4),
            risk_delta=round(risk_delta, 4),
            severity=severity.value,
            recommendation=recommendation,
            rationale="; ".join(rationale_parts),
            source_signals=signals,
            generated_at=time.time(),
        )

    def analyze_pair(self, target_a: str, target_b: str) -> dict[str, Any]:
        analysis_a = self.analyze(target_a)
        analysis_b = self.analyze(target_b)

        a_leverage = analysis_a.chosen.get("leverage_score", 0.0) if analysis_a.chosen else 0.0
        b_leverage = analysis_b.chosen.get("leverage_score", 0.0) if analysis_b.chosen else 0.0
        a_risk = analysis_a.chosen.get("risk_score", 0.0) if analysis_a.chosen else 0.0
        b_risk = analysis_b.chosen.get("risk_score", 0.0) if analysis_b.chosen else 0.0

        if a_leverage > b_leverage:
            preferred = target_a
            reason = f"{target_a} has higher leverage ({a_leverage:.2f} vs {b_leverage:.2f})"
        elif b_leverage > a_leverage:
            preferred = target_b
            reason = f"{target_b} has higher leverage ({b_leverage:.2f} vs {a_leverage:.2f})"
        else:
            preferred = target_a if a_risk <= b_risk else target_b
            reason = "equal leverage; preferring lower risk"

        return {
            "target_a": analysis_a.to_dict(),
            "target_b": analysis_b.to_dict(),
            "preferred": preferred,
            "reason": reason,
            "leverage_delta": round(a_leverage - b_leverage, 4),
            "risk_delta": round(a_risk - b_risk, 4),
        }

    def contention_map(self) -> dict[str, list[str]]:
        recs = self._get_all_recommendations()
        options = [self._build_option(r) for r in recs]

        contention: dict[str, list[str]] = {}
        resource_types = ["time", "attention", "capital", "capability_building", "execution_capacity"]

        for rt in resource_types:
            competing: list[str] = []
            for opt in options:
                if opt.resource_cost.get(rt, 0) > 0.2:
                    competing.append(opt.target_id)
            if len(competing) >= 2:
                contention[rt] = competing

        return contention

    def highest_cost_targets(self, limit: int = 5) -> list[dict[str, Any]]:
        recs = self._get_all_recommendations()
        options = [self._build_option(r) for r in recs]

        for opt in options:
            opt._total_cost = sum(opt.resource_cost.values())
        options.sort(key=lambda o: o._total_cost, reverse=True)

        results: list[dict[str, Any]] = []
        for opt in options[:limit]:
            d = opt.to_dict()
            d["total_cost"] = round(opt._total_cost, 4)
            results.append(d)
        return results

    def lowest_cost_targets(self, limit: int = 5) -> list[dict[str, Any]]:
        recs = self._get_all_recommendations()
        options = [self._build_option(r) for r in recs]

        for opt in options:
            opt._total_cost = sum(opt.resource_cost.values())
        options.sort(key=lambda o: o._total_cost)

        results: list[dict[str, Any]] = []
        for opt in options[:limit]:
            d = opt.to_dict()
            d["total_cost"] = round(opt._total_cost, 4)
            results.append(d)
        return results

    def snapshot(self) -> TradeoffSnapshot:
        recs = self._get_all_recommendations()
        options = [self._build_option(r) for r in recs]

        analyses: list[dict[str, Any]] = []
        severities: list[str] = []
        for opt in options:
            analysis = self.analyze(opt.target_id)
            analyses.append(analysis.to_dict())
            severities.append(analysis.severity)

        severity_order = ["critical", "major", "significant", "minor", "negligible"]
        overall = "negligible"
        for s in severity_order:
            if s in severities:
                overall = s
                break

        return TradeoffSnapshot(
            active_tradeoffs=analyses,
            highest_cost_targets=self.highest_cost_targets(limit=5),
            resource_contention=self.contention_map(),
            overall_severity=overall,
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        contention = self.contention_map()
        recs = self._get_all_recommendations()

        contention_count = sum(len(v) for v in contention.values())
        max_contention_resource = max(
            contention.keys(), key=lambda k: len(contention[k]),
            default="none"
        ) if contention else "none"

        return {
            "total_targets": len(recs),
            "contention_resource_count": len(contention),
            "total_contention_entries": contention_count,
            "max_contention_resource": max_contention_resource,
            "highest_cost_target": (
                self.highest_cost_targets(limit=1)[0]["target_id"]
                if recs else "none"
            ),
        }
