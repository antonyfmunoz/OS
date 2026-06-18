"""Campaign 10.2 — Capability Portfolio Runtime tests.

Tests portfolio snapshot, health classification, compounding score,
maturity velocity, top/weakest/bottleneck aggregation, graceful degradation.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.capability_portfolio_runtime import (
    CapabilityPortfolioRuntime,
    CapabilityPortfolioSnapshot,
    PortfolioHealth,
)


# ── Lightweight mocks ────────────────────────────────────────────────


class _MockMaturity:
    def __init__(self, value: str = "emerging") -> None:
        self.value = value


class _MockCap:
    def __init__(self, capability_id: str = "", name: str = "", maturity: str = "emerging") -> None:
        self.capability_id = capability_id
        self.name = name
        self.maturity = _MockMaturity(maturity)


class _MockCapabilityRuntime:
    def __init__(self, caps: list | None = None) -> None:
        self._caps = caps or []

    def list_capabilities(self) -> list:
        return self._caps

    def maturity_score(self, capability_id: str) -> float:
        for c in self._caps:
            if c.capability_id == capability_id:
                scores = {"institutional": 0.95, "operational": 0.7, "validated": 0.45, "emerging": 0.15}
                return scores.get(c.maturity.value, 0.0)
        return 0.0


class _MockGraphEngine:
    def __init__(self, bottlenecks: list | None = None) -> None:
        self._bottlenecks = bottlenecks or []

    def bottlenecks(self, limit: int = 5) -> list:
        return self._bottlenecks[:limit]


class _MockGap:
    def __init__(self, required: str = "", severity: str = "critical") -> None:
        self.required_capability = required
        self.severity = severity

    def to_dict(self) -> dict:
        return {"required_capability": self.required_capability, "severity": self.severity}


class _MockGapEngine:
    def __init__(self, gaps: list | None = None) -> None:
        self._gaps = gaps or []

    def critical_gaps(self) -> list:
        return self._gaps


class _MockAgentModel:
    def summary(self) -> dict:
        return {"agent_count": 3, "total_capabilities": 10}


def _make_runtime(**kwargs) -> CapabilityPortfolioRuntime:
    return CapabilityPortfolioRuntime(**kwargs)


# ── CapabilityPortfolioSnapshot tests ────────────────────────────────


class TestCapabilityPortfolioSnapshot:
    def test_defaults(self) -> None:
        s = CapabilityPortfolioSnapshot()
        assert s.total_capabilities == 0
        assert s.health == PortfolioHealth.HEALTHY

    def test_to_dict_keys(self) -> None:
        s = CapabilityPortfolioSnapshot()
        d = s.to_dict()
        expected = {
            "total_capabilities", "by_maturity", "compounding_score",
            "maturity_velocity", "health", "top_capabilities",
            "weakest_capabilities", "bottleneck_capabilities",
            "critical_gaps", "agent_coverage", "generated_at",
        }
        assert set(d.keys()) == expected


class TestPortfolioHealth:
    def test_values(self) -> None:
        assert PortfolioHealth.THRIVING.value == "thriving"
        assert PortfolioHealth.HEALTHY.value == "healthy"
        assert PortfolioHealth.STAGNATING.value == "stagnating"
        assert PortfolioHealth.DECAYING.value == "decaying"


# ── Health classification tests ──────────────────────────────────────


class TestHealthClassification:
    def test_thriving(self) -> None:
        caps = [
            _MockCap("c1", "A", "institutional"),
            _MockCap("c2", "B", "operational"),
            _MockCap("c3", "C", "operational"),
        ]
        rt = _make_runtime(capability_runtime=_MockCapabilityRuntime(caps))
        snap = rt.snapshot()
        assert snap.health == PortfolioHealth.THRIVING

    def test_healthy(self) -> None:
        caps = [
            _MockCap("c1", "A", "operational"),
            _MockCap("c2", "B", "validated"),
            _MockCap("c3", "C", "emerging"),
            _MockCap("c4", "D", "emerging"),
        ]
        rt = _make_runtime(capability_runtime=_MockCapabilityRuntime(caps))
        snap = rt.snapshot()
        assert snap.health in (PortfolioHealth.HEALTHY, PortfolioHealth.STAGNATING)

    def test_stagnating_empty(self) -> None:
        rt = _make_runtime(capability_runtime=_MockCapabilityRuntime([]))
        snap = rt.snapshot()
        assert snap.health == PortfolioHealth.STAGNATING

    def test_decaying(self) -> None:
        caps = [
            _MockCap("c1", "A", "emerging"),
            _MockCap("c2", "B", "emerging"),
            _MockCap("c3", "C", "emerging"),
            _MockCap("c4", "D", "emerging"),
            _MockCap("c5", "E", "emerging"),
        ]
        rt = _make_runtime(capability_runtime=_MockCapabilityRuntime(caps))
        snap = rt.snapshot()
        assert snap.health == PortfolioHealth.DECAYING


# ── Compounding score tests ──────────────────────────────────────────


class TestCompoundingScore:
    def test_all_institutional(self) -> None:
        caps = [_MockCap(f"c{i}", f"Cap{i}", "institutional") for i in range(5)]
        rt = _make_runtime(capability_runtime=_MockCapabilityRuntime(caps))
        assert rt.compounding_score() == 1.0

    def test_all_emerging(self) -> None:
        caps = [_MockCap(f"c{i}", f"Cap{i}", "emerging") for i in range(5)]
        rt = _make_runtime(capability_runtime=_MockCapabilityRuntime(caps))
        assert rt.compounding_score() == 0.25

    def test_mixed(self) -> None:
        caps = [
            _MockCap("c1", "A", "institutional"),
            _MockCap("c2", "B", "emerging"),
        ]
        rt = _make_runtime(capability_runtime=_MockCapabilityRuntime(caps))
        score = rt.compounding_score()
        assert 0.5 < score < 0.7

    def test_empty(self) -> None:
        rt = _make_runtime(capability_runtime=_MockCapabilityRuntime([]))
        assert rt.compounding_score() == 0.0

    def test_no_runtime(self) -> None:
        rt = _make_runtime()
        assert rt.compounding_score() == 0.0


# ── Snapshot composition tests ───────────────────────────────────────


class TestSnapshotComposition:
    def test_full_composition(self) -> None:
        caps = [
            _MockCap("c1", "Planning", "operational"),
            _MockCap("c2", "Analysis", "emerging"),
        ]
        rt = _make_runtime(
            capability_runtime=_MockCapabilityRuntime(caps),
            graph_engine=_MockGraphEngine([{"capability_id": "c1", "dependent_count": 3}]),
            gap_engine=_MockGapEngine([_MockGap("Missing Cap")]),
            agent_model=_MockAgentModel(),
        )
        snap = rt.snapshot()
        assert snap.total_capabilities == 2
        assert len(snap.bottleneck_capabilities) == 1
        assert len(snap.critical_gaps) == 1
        assert snap.agent_coverage.get("agent_count") == 3

    def test_top_and_weakest(self) -> None:
        caps = [
            _MockCap("c1", "Strong", "institutional"),
            _MockCap("c2", "Weak", "emerging"),
        ]
        rt = _make_runtime(capability_runtime=_MockCapabilityRuntime(caps))
        snap = rt.snapshot()
        assert len(snap.top_capabilities) >= 1
        assert snap.top_capabilities[0]["name"] == "Strong"
        assert len(snap.weakest_capabilities) >= 1


# ── Summary tests ────────────────────────────────────────────────────


class TestSummary:
    def test_summary_keys(self) -> None:
        rt = _make_runtime()
        s = rt.summary()
        expected = {
            "total_capabilities", "health", "compounding_score",
            "maturity_velocity", "critical_gap_count", "by_maturity",
            "generated_at",
        }
        assert set(s.keys()) == expected


# ── Graceful degradation ─────────────────────────────────────────────


class TestGracefulDegradation:
    def test_no_engines(self) -> None:
        rt = _make_runtime()
        snap = rt.snapshot()
        assert snap.total_capabilities == 0
        assert snap.top_capabilities == []
        assert snap.critical_gaps == []

    def test_broken_gap_engine(self) -> None:
        class _Broken:
            def critical_gaps(self):
                raise RuntimeError("down")

        rt = _make_runtime(
            capability_runtime=_MockCapabilityRuntime([_MockCap("c1", "A", "operational")]),
            gap_engine=_Broken(),
        )
        snap = rt.snapshot()
        assert snap.total_capabilities == 1
        assert snap.critical_gaps == []

    def test_broken_graph_engine(self) -> None:
        class _Broken:
            def bottlenecks(self, limit=5):
                raise RuntimeError("down")

        rt = _make_runtime(
            capability_runtime=_MockCapabilityRuntime([_MockCap("c1", "A", "operational")]),
            graph_engine=_Broken(),
        )
        snap = rt.snapshot()
        assert snap.total_capabilities == 1
        assert snap.bottleneck_capabilities == []
