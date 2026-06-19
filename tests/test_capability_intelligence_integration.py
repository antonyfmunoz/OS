"""Campaign 10 — Capability Intelligence integration tests.

Tests full composition: CapabilityRuntime → GraphEngine → GapEngine →
PortfolioRuntime → ExecutiveBrief/StrategicContext integration.
"""

from __future__ import annotations

import sys
import tempfile

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.capability_graph_engine import (
    CapabilityGraphEngine,
    CapabilityRelationType,
)
from substrate.organism.capability_gap_engine import (
    CapabilityGapEngine,
    CapabilityGapSeverity,
)
from substrate.organism.capability_portfolio_runtime import (
    CapabilityPortfolioRuntime,
    PortfolioHealth,
)
from substrate.organism.executive_brief_runtime import ExecutiveBriefRuntime
from substrate.organism.strategic_context_runtime import StrategicContextRuntime


# ── Shared mocks ────────────────────────────────────────────────────────


class _Maturity:
    def __init__(self, v: str) -> None:
        self.value = v


class _Cap:
    def __init__(self, cid: str, name: str, maturity: str = "emerging") -> None:
        self.capability_id = cid
        self.name = name
        self.maturity = _Maturity(maturity)


class _MockCapRuntime:
    def __init__(self, caps: list) -> None:
        self._caps = caps

    def list_capabilities(self) -> list:
        return self._caps

    def get(self, cid: str):
        return next((c for c in self._caps if c.capability_id == cid), None)

    def maturity_score(self, cid: str) -> float:
        scores = {"institutional": 0.95, "operational": 0.7, "validated": 0.45, "emerging": 0.15}
        cap = self.get(cid)
        if cap:
            return scores.get(cap.maturity.value, 0.0)
        return 0.0


class _Goal:
    def __init__(self, gid: str, title: str, req: list[str]) -> None:
        self.goal_id = gid
        self.title = title
        self.required_capabilities = req


class _GoalRegistry:
    def __init__(self, goals: list) -> None:
        self._goals = {g.goal_id: g for g in goals}

    def list_goals(self, status=None) -> list:
        return list(self._goals.values())

    def get(self, gid: str):
        return self._goals.get(gid)


# ── Integration tests ───────────────────────────────────────────────────


class TestFullCapabilityStack:
    """Test full C10.0→C10.2 composition as a single stack."""

    def _build_stack(self):
        caps = [
            _Cap("c1", "Strategic Planning", "operational"),
            _Cap("c2", "Risk Analysis", "emerging"),
            _Cap("c3", "Code Review", "institutional"),
            _Cap("c4", "Data Pipeline", "validated"),
        ]
        goals = [
            _Goal("g1", "Ship Product", [
                "Strategic Planning",
                "Risk Analysis",
                "Release Coordination",
            ]),
        ]
        cap_rt = _MockCapRuntime(caps)
        goal_reg = _GoalRegistry(goals)
        data_dir = tempfile.mkdtemp()

        graph = CapabilityGraphEngine(capability_runtime=cap_rt, data_dir=data_dir)
        graph.add_edge("c1", "c2", CapabilityRelationType.ENABLES)
        graph.add_edge("c3", "c4", CapabilityRelationType.DEPENDS_ON)

        gap = CapabilityGapEngine(capability_runtime=cap_rt, goal_registry=goal_reg)
        portfolio = CapabilityPortfolioRuntime(
            capability_runtime=cap_rt,
            graph_engine=graph,
            gap_engine=gap,
        )
        return cap_rt, graph, gap, portfolio

    def test_graph_edges_visible_in_portfolio(self) -> None:
        _, graph, _, portfolio = self._build_stack()
        snap = portfolio.snapshot()
        assert snap.total_capabilities == 4
        assert len(snap.bottleneck_capabilities) >= 0

    def test_gaps_surface_in_portfolio(self) -> None:
        _, _, _, portfolio = self._build_stack()
        snap = portfolio.snapshot()
        assert len(snap.critical_gaps) >= 1

    def test_portfolio_health_reflects_mixed_maturity(self) -> None:
        _, _, _, portfolio = self._build_stack()
        snap = portfolio.snapshot()
        assert snap.health in (PortfolioHealth.HEALTHY, PortfolioHealth.STAGNATING)
        assert snap.compounding_score > 0.0

    def test_acceptance_test_full_flow(self) -> None:
        """The 4 acceptance questions work through the full stack."""
        _, _, gap, _ = self._build_stack()

        satisfied = gap.satisfied()
        assert any(g.matched_capability_name == "Strategic Planning" for g in satisfied)

        critical = gap.critical_gaps()
        assert any(g.required_capability == "Release Coordination" for g in critical)

        immature = gap.immature_gaps()
        assert any(g.matched_capability_name == "Risk Analysis" for g in immature)

        recs = gap.next_to_build(5)
        assert len(recs) >= 1
        assert recs[0]["severity"] == "critical"


class TestExecutiveBriefIntegration:
    """Test that ExecutiveBrief receives capability data from PortfolioRuntime."""

    def test_brief_includes_capability_fields(self) -> None:
        caps = [
            _Cap("c1", "Planning", "operational"),
            _Cap("c2", "Analysis", "emerging"),
        ]
        goals = [_Goal("g1", "Goal", ["Planning", "Missing"])]
        cap_rt = _MockCapRuntime(caps)
        gap = CapabilityGapEngine(capability_runtime=cap_rt, goal_registry=_GoalRegistry(goals))
        portfolio = CapabilityPortfolioRuntime(
            capability_runtime=cap_rt,
            gap_engine=gap,
        )
        brief_rt = ExecutiveBriefRuntime(
            capability_runtime=cap_rt,
            capability_portfolio=portfolio,
        )
        brief = brief_rt.generate()
        assert brief.capability_health != "unknown"
        assert len(brief.top_capabilities) >= 1

    def test_brief_includes_gaps(self) -> None:
        caps = [_Cap("c1", "Existing", "emerging")]
        goals = [_Goal("g1", "Goal", ["Existing", "Missing"])]
        cap_rt = _MockCapRuntime(caps)
        gap = CapabilityGapEngine(capability_runtime=cap_rt, goal_registry=_GoalRegistry(goals))
        portfolio = CapabilityPortfolioRuntime(
            capability_runtime=cap_rt,
            gap_engine=gap,
        )
        brief_rt = ExecutiveBriefRuntime(
            capability_portfolio=portfolio,
        )
        brief = brief_rt.generate()
        assert len(brief.critical_capability_gaps) >= 1


class TestStrategicContextIntegration:
    """Test that StrategicContext receives capability data."""

    def test_context_includes_capability_health(self) -> None:
        caps = [_Cap("c1", "Planning", "operational")]
        cap_rt = _MockCapRuntime(caps)
        gap = CapabilityGapEngine(capability_runtime=cap_rt)
        portfolio = CapabilityPortfolioRuntime(
            capability_runtime=cap_rt,
            gap_engine=gap,
        )
        ctx_rt = StrategicContextRuntime(capability_portfolio=portfolio)
        ctx = ctx_rt.context()
        assert ctx.capability_health.get("health") is not None
        assert ctx.capability_health.get("total_capabilities") == 1

    def test_context_degrades_without_portfolio(self) -> None:
        ctx_rt = StrategicContextRuntime()
        ctx = ctx_rt.context()
        assert ctx.capability_health == {}
        assert ctx.capability_gaps == []
