"""
Scenario Intelligence Engine — Campaign 13.1

Generates deterministic future-state scenarios via rule-based branching.
Not simulation. Not generative reasoning. Deterministic rule application
against trajectory data, decision health, and risk profiles.

Operator questions answered:
  - What is the best realistic outcome from here?
  - What should we expect if current trends hold?
  - What happens if things go wrong?
  - What disruptions could cascade?

Composes:
  - TrajectoryIntelligenceRuntime (C13.0) — trajectory forecasts
  - DecisionValidityEngine (C9) — decision health
  - WorkPortfolioRuntime (C11.2) — work velocity + at-risk
  - CapabilityPortfolioRuntime (C10.2) — capability health
  - LearningPortfolioRuntime (C12.3) — learning compounding
  - StrategicPlanningEngine (C8.3) — goal roadmap
  - RiskEngine (C7.2) — unified risk register

Forecast artifacts only. No mutation authority. Does not modify goals,
work, decisions, capabilities, or delegation state.
Deterministic. Zero LLM calls.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ScenarioType(str, Enum):
    """Deterministic scenario classification."""
    BEST_CASE = "best_case"
    EXPECTED = "expected"
    WORST_CASE = "worst_case"
    DISRUPTION = "disruption"


@dataclass
class FutureScenario:
    """A deterministic future-state scenario.

    Explainability contract: every scenario carries assumptions (what
    must hold), projected_outcomes, probability, contributing risks
    and opportunities, and affected_goals so the operator can trace
    exactly why this scenario was generated.
    """
    scenario_id: str = ""
    scenario_type: str = ScenarioType.EXPECTED.value
    title: str = ""
    assumptions: list[str] = field(default_factory=list)
    projected_outcomes: dict[str, Any] = field(default_factory=dict)
    probability: float = 0.0
    risks: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    affected_goals: list[str] = field(default_factory=list)
    source_signals: list[str] = field(default_factory=list)
    contributing_factors: list[str] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["probability"] = round(self.probability, 4)
        return d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ScenarioIntelligenceEngine:
    """Deterministic future-state scenario generation.

    Each scenario type has a rule-based generation algorithm that composes
    trajectory data, decision health, risk profile, and portfolio state
    into a probabilistic future-state description.
    """

    def __init__(
        self,
        trajectory_runtime: Any | None = None,
        decision_validity: Any | None = None,
        work_portfolio: Any | None = None,
        capability_portfolio: Any | None = None,
        learning_portfolio: Any | None = None,
        strategic_planning: Any | None = None,
        risk_engine: Any | None = None,
    ) -> None:
        self._trajectory_runtime = trajectory_runtime
        self._decision_validity = decision_validity
        self._work_portfolio = work_portfolio
        self._capability_portfolio = capability_portfolio
        self._learning_portfolio = learning_portfolio
        self._strategic_planning = strategic_planning
        self._risk_engine = risk_engine

    # ── Lazy subsystem access ────────────────────────────────────────────

    @property
    def trajectory_runtime(self) -> Any | None:
        if self._trajectory_runtime is None:
            try:
                from substrate.organism.trajectory_intelligence_runtime import TrajectoryIntelligenceRuntime
                self._trajectory_runtime = TrajectoryIntelligenceRuntime()
            except Exception:
                logger.debug("TrajectoryIntelligenceRuntime unavailable")
        return self._trajectory_runtime

    @property
    def decision_validity(self) -> Any | None:
        if self._decision_validity is None:
            try:
                from substrate.organism.decision_validity_engine import DecisionValidityEngine
                self._decision_validity = DecisionValidityEngine()
            except Exception:
                logger.debug("DecisionValidityEngine unavailable")
        return self._decision_validity

    @property
    def work_portfolio(self) -> Any | None:
        if self._work_portfolio is None:
            try:
                from substrate.organism.work_portfolio_runtime import WorkPortfolioRuntime
                self._work_portfolio = WorkPortfolioRuntime()
            except Exception:
                logger.debug("WorkPortfolioRuntime unavailable")
        return self._work_portfolio

    @property
    def capability_portfolio(self) -> Any | None:
        if self._capability_portfolio is None:
            try:
                from substrate.organism.capability_portfolio_runtime import CapabilityPortfolioRuntime
                self._capability_portfolio = CapabilityPortfolioRuntime()
            except Exception:
                logger.debug("CapabilityPortfolioRuntime unavailable")
        return self._capability_portfolio

    @property
    def learning_portfolio(self) -> Any | None:
        if self._learning_portfolio is None:
            try:
                from substrate.organism.learning_portfolio_runtime import LearningPortfolioRuntime
                self._learning_portfolio = LearningPortfolioRuntime()
            except Exception:
                logger.debug("LearningPortfolioRuntime unavailable")
        return self._learning_portfolio

    @property
    def strategic_planning(self) -> Any | None:
        if self._strategic_planning is None:
            try:
                from substrate.organism.strategic_planning_engine import StrategicPlanningEngine
                self._strategic_planning = StrategicPlanningEngine()
            except Exception:
                logger.debug("StrategicPlanningEngine unavailable")
        return self._strategic_planning

    @property
    def risk_engine(self) -> Any | None:
        if self._risk_engine is None:
            try:
                from substrate.organism.risk_engine import RiskEngine
                self._risk_engine = RiskEngine()
            except Exception:
                logger.debug("RiskEngine unavailable")
        return self._risk_engine

    # ── Signal collection ────────────────────────────────────────────────

    def _collect_trajectory_data(self) -> dict[str, Any]:
        """Collect all trajectory forecasts."""
        data: dict[str, Any] = {
            "forecasts": [],
            "at_risk": [],
            "summary": {},
            "health": "unknown",
        }
        tr = self.trajectory_runtime
        if tr is None:
            return data
        try:
            forecasts = tr.forecast_all()
            data["forecasts"] = forecasts
            data["at_risk"] = [
                f for f in forecasts
                if _get_attr(f, "status", "") in ("slowing", "stalled", "declining")
            ]
            data["summary"] = tr.trajectory_summary()
            data["health"] = tr.health()
        except Exception:
            logger.debug("Failed to collect trajectory data", exc_info=True)
        return data

    def _collect_risk_data(self) -> dict[str, Any]:
        """Collect risk profile."""
        data: dict[str, Any] = {"all_risks": [], "high_risks": []}
        re = self.risk_engine
        if re is None:
            return data
        try:
            data["all_risks"] = re.detect_risks() or []
            data["high_risks"] = re.high_risks() or []
        except Exception:
            logger.debug("Failed to collect risk data", exc_info=True)
        return data

    def _collect_decision_data(self) -> dict[str, Any]:
        """Collect decision validity data."""
        data: dict[str, Any] = {"at_risk": [], "invalid": []}
        dv = self.decision_validity
        if dv is None:
            return data
        try:
            data["at_risk"] = dv.at_risk() or []
            data["invalid"] = dv.invalid() or []
        except Exception:
            logger.debug("Failed to collect decision data", exc_info=True)
        return data

    def _collect_portfolio_data(self) -> dict[str, Any]:
        """Collect portfolio health signals."""
        data: dict[str, Any] = {
            "work_health": "unknown",
            "work_velocity": 0.0,
            "work_at_risk": 0,
            "capability_health": "unknown",
            "learning_compounding": 0.0,
            "learning_health": "unknown",
        }
        wp = self.work_portfolio
        if wp is not None:
            try:
                h = wp.health()
                data["work_health"] = h.value if hasattr(h, "value") else str(h)
                data["work_velocity"] = wp.completions_per_day()
                ar = wp.at_risk_work()
                data["work_at_risk"] = len(ar) if ar else 0
            except Exception:
                logger.debug("Failed to collect work portfolio data")
        cp = self.capability_portfolio
        if cp is not None:
            try:
                h = cp.health()
                data["capability_health"] = h.value if hasattr(h, "value") else str(h)
            except Exception:
                logger.debug("Failed to collect capability portfolio data")
        lp = self.learning_portfolio
        if lp is not None:
            try:
                data["learning_compounding"] = lp.compounding_score()
                h = lp.health()
                data["learning_health"] = h.value if hasattr(h, "value") else str(h)
            except Exception:
                logger.debug("Failed to collect learning portfolio data")
        return data

    def _collect_goal_ids(self) -> list[str]:
        """Collect affected goal IDs from strategic planning."""
        sp = self.strategic_planning
        if sp is None:
            return []
        try:
            roadmap = sp.roadmap()
            if isinstance(roadmap, dict):
                return list(roadmap.keys())[:20]
        except Exception:
            logger.debug("Failed to collect goal IDs")
        return []

    def _count_signals(self) -> tuple[int, list[str]]:
        """Count available signal sources."""
        count = 0
        sources: list[str] = []
        for name, prop in [
            ("trajectory_runtime", self.trajectory_runtime),
            ("decision_validity", self.decision_validity),
            ("work_portfolio", self.work_portfolio),
            ("capability_portfolio", self.capability_portfolio),
            ("learning_portfolio", self.learning_portfolio),
            ("strategic_planning", self.strategic_planning),
            ("risk_engine", self.risk_engine),
        ]:
            if prop is not None:
                count += 1
                sources.append(name)
        return count, sources

    # ── Scenario generation ──────────────────────────────────────────────

    def best_case(self) -> FutureScenario:
        """Generate best-case scenario.

        Rule: all accelerating/stable trajectories hold, at-risk decisions
        resolve positively, learning compounding above threshold, no high
        risks materialize.
        """
        now = time.time()
        traj = self._collect_trajectory_data()
        risk = self._collect_risk_data()
        dec = self._collect_decision_data()
        port = self._collect_portfolio_data()
        goals = self._collect_goal_ids()
        signal_count, source_signals = self._count_signals()

        forecasts = traj["forecasts"]
        avg_conf = traj["summary"].get("average_confidence", 0.5) if traj["summary"] else 0.5

        good_count = sum(
            1 for f in forecasts
            if _get_attr(f, "status", "") in ("accelerating", "stable")
        )
        good_ratio = good_count / len(forecasts) if forecasts else 0.5

        high_risk_count = len(risk["high_risks"])
        total_risk = len(risk["all_risks"]) or 1
        risk_factor = 1.0 - (high_risk_count / total_risk)

        cap_factor = 1.0 if port["capability_health"] in ("healthy", "thriving") else 0.8
        learn_factor = min(1.0, 0.5 + port["learning_compounding"])

        probability = max(0.0, min(1.0,
            avg_conf * good_ratio * risk_factor * cap_factor * learn_factor
        ))

        assumptions = [
            "All accelerating/stable trajectories maintain direction",
            "At-risk decisions resolve positively",
            f"No high-severity risks materialize ({high_risk_count} currently high)",
            f"Learning compounding holds at {port['learning_compounding']:.2f}",
        ]
        if port["work_velocity"] > 0:
            assumptions.append(f"Work velocity sustains at {port['work_velocity']:.2f}/day")

        factors = [
            f"trajectory health: {traj['health']}",
            f"good trajectory ratio: {good_ratio:.1%}",
            f"risk factor: {risk_factor:.2f}",
            f"capability health: {port['capability_health']}",
        ]

        opportunities = []
        if good_ratio > 0.7:
            opportunities.append("Strong trajectory momentum enables acceleration")
        if port["learning_compounding"] > 0.5:
            opportunities.append("High learning compounding may accelerate capability growth")
        if high_risk_count == 0:
            opportunities.append("Clean risk profile allows aggressive execution")

        return FutureScenario(
            scenario_id=str(uuid.uuid4())[:12],
            scenario_type=ScenarioType.BEST_CASE.value,
            title="Best Case: Trajectories Hold, Risks Clear",
            assumptions=assumptions,
            projected_outcomes={
                "trajectory_health": "healthy",
                "expected_good_ratio": min(1.0, good_ratio + 0.1),
                "risk_materialization": 0,
                "velocity_trend": "increasing",
            },
            probability=round(probability, 4),
            risks=[],
            opportunities=opportunities,
            affected_goals=goals[:10],
            source_signals=source_signals,
            contributing_factors=factors,
            generated_at=now,
        )

    def expected_case(self) -> FutureScenario:
        """Generate expected-case scenario.

        Rule: trajectories hold current status, at-risk decisions have
        50% resolution, current velocity maintained.
        """
        now = time.time()
        traj = self._collect_trajectory_data()
        risk = self._collect_risk_data()
        dec = self._collect_decision_data()
        port = self._collect_portfolio_data()
        goals = self._collect_goal_ids()
        signal_count, source_signals = self._count_signals()

        avg_conf = traj["summary"].get("average_confidence", 0.5) if traj["summary"] else 0.5
        probability = max(0.0, min(1.0, avg_conf))

        at_risk_decisions = len(dec["at_risk"])
        high_risk_count = len(risk["high_risks"])

        assumptions = [
            "Current trajectory statuses persist unchanged",
            f"50% of at-risk decisions resolve ({at_risk_decisions} at risk)",
            f"Work velocity holds at {port['work_velocity']:.2f}/day",
            f"Some high risks may materialize ({high_risk_count} currently high)",
        ]

        risks_list = []
        if high_risk_count > 0:
            risks_list.append(f"{high_risk_count} high-severity risks may partially materialize")
        if at_risk_decisions > 0:
            risks_list.append(f"{at_risk_decisions // 2 + 1} at-risk decisions may fail")

        opportunities_list = []
        if port["learning_compounding"] > 0.3:
            opportunities_list.append("Ongoing learning compounding provides gradual improvement")

        factors = [
            f"average confidence: {avg_conf:.2f}",
            f"at-risk decisions: {at_risk_decisions}",
            f"high risks: {high_risk_count}",
            f"work velocity: {port['work_velocity']:.2f}/day",
        ]

        return FutureScenario(
            scenario_id=str(uuid.uuid4())[:12],
            scenario_type=ScenarioType.EXPECTED.value,
            title="Expected Case: Current Trends Continue",
            assumptions=assumptions,
            projected_outcomes={
                "trajectory_health": traj["health"],
                "decision_resolution_rate": 0.5,
                "velocity_trend": "steady",
                "risk_materialization_partial": True,
            },
            probability=round(probability, 4),
            risks=risks_list,
            opportunities=opportunities_list,
            affected_goals=goals[:10],
            source_signals=source_signals,
            contributing_factors=factors,
            generated_at=now,
        )

    def worst_case(self) -> FutureScenario:
        """Generate worst-case scenario.

        Rule: all declining trajectories worsen, at-risk decisions fail,
        high risks materialize, work velocity drops.
        """
        now = time.time()
        traj = self._collect_trajectory_data()
        risk = self._collect_risk_data()
        dec = self._collect_decision_data()
        port = self._collect_portfolio_data()
        goals = self._collect_goal_ids()
        signal_count, source_signals = self._count_signals()

        avg_conf = traj["summary"].get("average_confidence", 0.5) if traj["summary"] else 0.5
        at_risk_count = len(traj["at_risk"])
        total = len(traj["forecasts"]) or 1
        risk_ratio = at_risk_count / total
        high_risk_count = len(risk["high_risks"])

        probability = max(0.0, min(1.0,
            risk_ratio * (1.0 - avg_conf) * (1.0 + high_risk_count * 0.1)
        ))

        invalid_count = len(dec["invalid"])
        at_risk_dec = len(dec["at_risk"])

        assumptions = [
            f"All declining/stalled trajectories worsen ({at_risk_count} at risk)",
            f"At-risk decisions fail ({at_risk_dec} at risk)",
            f"High-severity risks materialize ({high_risk_count} high)",
            "Work velocity drops significantly",
        ]
        if invalid_count > 0:
            assumptions.append(f"Invalid decisions compound ({invalid_count} invalid)")

        risks_list = [
            f"{at_risk_count} trajectories degrade further",
            f"{high_risk_count} high-severity risks materialize",
        ]
        if at_risk_dec > 0:
            risks_list.append(f"{at_risk_dec} at-risk decisions fail")
        if port["work_at_risk"] > 0:
            risks_list.append(f"{port['work_at_risk']} work items fail or block")

        factors = [
            f"at-risk trajectory ratio: {risk_ratio:.1%}",
            f"average confidence: {avg_conf:.2f}",
            f"high risk count: {high_risk_count}",
            f"invalid decisions: {invalid_count}",
        ]

        return FutureScenario(
            scenario_id=str(uuid.uuid4())[:12],
            scenario_type=ScenarioType.WORST_CASE.value,
            title="Worst Case: Risks Materialize, Trajectories Degrade",
            assumptions=assumptions,
            projected_outcomes={
                "trajectory_health": "critical",
                "decision_failure_rate": 1.0,
                "velocity_trend": "declining",
                "risk_materialization": high_risk_count,
            },
            probability=round(probability, 4),
            risks=risks_list,
            opportunities=[],
            affected_goals=goals[:10],
            source_signals=source_signals,
            contributing_factors=factors,
            generated_at=now,
        )

    def disruption_case(self) -> FutureScenario:
        """Generate disruption scenario.

        Rule: invalid decisions cascade, multiple high risks co-occur,
        capability gaps widen. Low probability, high impact.
        """
        now = time.time()
        traj = self._collect_trajectory_data()
        risk = self._collect_risk_data()
        dec = self._collect_decision_data()
        port = self._collect_portfolio_data()
        goals = self._collect_goal_ids()
        signal_count, source_signals = self._count_signals()

        invalid_count = len(dec["invalid"])
        high_risk_count = len(risk["high_risks"])

        # Disruption probability is the product of individual failure
        # probabilities — intentionally low
        base = 0.05
        if invalid_count > 0:
            base *= (1.0 + invalid_count * 0.3)
        if high_risk_count > 1:
            base *= (1.0 + (high_risk_count - 1) * 0.2)

        probability = max(0.0, min(0.5, base))

        assumptions = [
            "Multiple high-severity risks co-occur simultaneously",
            f"Invalid decisions cascade ({invalid_count} invalid)",
            "Capability gaps prevent recovery",
            "External disruptions compound internal weaknesses",
        ]

        risks_list = [
            "Cascading decision failures across goal hierarchy",
            f"Simultaneous materialization of {high_risk_count} high risks",
        ]
        if port["capability_health"] in ("degraded", "critical"):
            risks_list.append("Capability weakness prevents adaptive response")
        if port["learning_health"] in ("declining", "critical"):
            risks_list.append("Degraded learning ability slows recovery")

        factors = [
            f"invalid decisions: {invalid_count}",
            f"high risks: {high_risk_count}",
            f"capability health: {port['capability_health']}",
            f"learning health: {port['learning_health']}",
        ]

        return FutureScenario(
            scenario_id=str(uuid.uuid4())[:12],
            scenario_type=ScenarioType.DISRUPTION.value,
            title="Disruption: Cascading Failures",
            assumptions=assumptions,
            projected_outcomes={
                "trajectory_health": "critical",
                "cascade_depth": invalid_count + high_risk_count,
                "recovery_time_days": max(30, (invalid_count + high_risk_count) * 14),
                "velocity_trend": "collapsed",
            },
            probability=round(probability, 4),
            risks=risks_list,
            opportunities=["Crisis reveals hidden structural weaknesses for repair"],
            affected_goals=goals,
            source_signals=source_signals,
            contributing_factors=factors,
            generated_at=now,
        )

    def generate(self) -> list[FutureScenario]:
        """Generate all four scenario types."""
        scenarios: list[FutureScenario] = []
        for method in (self.best_case, self.expected_case, self.worst_case, self.disruption_case):
            try:
                scenarios.append(method())
            except Exception as exc:
                logger.debug("Scenario generation failed for %s: %s", method.__name__, exc)
        return scenarios

    def compare(self) -> dict[str, Any]:
        """Side-by-side comparison of all scenarios."""
        scenarios = self.generate()
        if not scenarios:
            return {"scenarios": [], "probability_range": [0.0, 0.0], "generated_at": time.time()}

        probs = [s.probability for s in scenarios]
        return {
            "scenarios": [s.to_dict() for s in scenarios],
            "probability_range": [round(min(probs), 4), round(max(probs), 4)],
            "scenario_count": len(scenarios),
            "best_probability": round(max(probs), 4),
            "worst_probability": round(
                min(s.probability for s in scenarios if s.scenario_type != ScenarioType.DISRUPTION.value)
                if any(s.scenario_type != ScenarioType.DISRUPTION.value for s in scenarios)
                else min(probs),
                4,
            ),
            "spread": round(max(probs) - min(probs), 4),
            "generated_at": time.time(),
        }

    def summary(self) -> dict[str, Any]:
        """Compact scenario summary for API."""
        scenarios = self.generate()
        if not scenarios:
            return {
                "scenario_count": 0,
                "types": [],
                "probability_range": [0.0, 0.0],
                "top_risks": [],
                "top_opportunities": [],
                "generated_at": time.time(),
            }

        probs = [s.probability for s in scenarios]
        all_risks: list[str] = []
        all_opps: list[str] = []
        for s in scenarios:
            all_risks.extend(s.risks)
            all_opps.extend(s.opportunities)

        return {
            "scenario_count": len(scenarios),
            "types": [s.scenario_type for s in scenarios],
            "probability_range": [round(min(probs), 4), round(max(probs), 4)],
            "top_risks": list(dict.fromkeys(all_risks))[:5],
            "top_opportunities": list(dict.fromkeys(all_opps))[:5],
            "generated_at": time.time(),
        }


# ── Module helpers ───────────────────────────────────────────────────────


def _get_attr(obj: Any, name: str, default: Any = None) -> Any:
    """Safely get attribute from object or dict."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)
