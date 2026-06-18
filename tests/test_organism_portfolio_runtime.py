"""Tests for OrganismPortfolioRuntime — Campaign 15.3."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from substrate.organism.organism_portfolio_runtime import (
    OrganismDriftType,
    OrganismDriftWarning,
    OrganismHealth,
    OrganismPortfolioRuntime,
    OrganismPortfolioSnapshot,
    SubsystemHealthEntry,
    _SUBSYSTEM_WEIGHTS,
)


# ── Fake subsystems ──────────────────────────────────────────────────


class FakeHealthy:
    """Subsystem that reports healthy with no drift."""
    def __init__(self, health_val: str = "coherent") -> None:
        self._health_val = health_val

    def health(self):
        return type("H", (), {"value": self._health_val})()

    def drift_warnings(self) -> list:
        return []


class FakeDrifting:
    """Subsystem with drift warnings."""
    def __init__(self, health_val: str = "strained", drift_count: int = 2) -> None:
        self._health_val = health_val
        self._drift_count = drift_count

    def health(self):
        return type("H", (), {"value": self._health_val})()

    def drift_warnings(self) -> list:
        return [
            type("D", (), {
                "severity": "medium",
                "description": f"drift {i}",
                "affected_ids": [],
            })()
            for i in range(self._drift_count)
        ]


class FakeCritical:
    """Subsystem in critical state."""
    def health(self):
        return type("H", (), {"value": "critical"})()

    def drift_warnings(self) -> list:
        return [
            type("D", (), {
                "severity": "critical",
                "description": "critical drift",
                "affected_ids": ["x"],
            })(),
        ]


# ── Type tests ───────────────────────────────────────────────────────


class TestOrganismHealthEnum:
    def test_values(self) -> None:
        assert OrganismHealth.COHERENT.value == "coherent"
        assert OrganismHealth.ALIGNED.value == "aligned"
        assert OrganismHealth.STRAINED.value == "strained"
        assert OrganismHealth.FRAGMENTED.value == "fragmented"
        assert OrganismHealth.CRITICAL.value == "critical"

    def test_count(self) -> None:
        assert len(OrganismHealth) == 5


class TestOrganismDriftTypeEnum:
    def test_values(self) -> None:
        assert OrganismDriftType.GOVERNANCE_DRIFT.value == "governance_drift"
        assert OrganismDriftType.COORDINATION_DRIFT.value == "coordination_drift"
        assert OrganismDriftType.INSTITUTIONAL_MEMORY_DRIFT.value == "institutional_memory_drift"
        assert OrganismDriftType.EXECUTIVE_DRIFT.value == "executive_drift"
        assert OrganismDriftType.PREDICTION_DRIFT.value == "prediction_drift"
        assert OrganismDriftType.LEARNING_DRIFT.value == "learning_drift"
        assert OrganismDriftType.WORK_DRIFT.value == "work_drift"
        assert OrganismDriftType.CAPABILITY_DRIFT.value == "capability_drift"

    def test_count(self) -> None:
        assert len(OrganismDriftType) == 8


class TestOrganismDriftWarning:
    def test_defaults(self) -> None:
        w = OrganismDriftWarning()
        assert w.drift_type == OrganismDriftType.GOVERNANCE_DRIFT.value
        assert w.severity == "low"

    def test_to_dict(self) -> None:
        w = OrganismDriftWarning(
            drift_type=OrganismDriftType.WORK_DRIFT.value,
            severity="high",
            description="work drifting",
        )
        d = w.to_dict()
        assert d["drift_type"] == "work_drift"
        assert d["severity"] == "high"
        assert "affected_ids" in d


class TestSubsystemHealthEntry:
    def test_defaults(self) -> None:
        e = SubsystemHealthEntry()
        assert e.subsystem == ""
        assert e.health == "unknown"
        assert e.drift_count == 0
        assert e.score == 0.5

    def test_to_dict(self) -> None:
        e = SubsystemHealthEntry(subsystem="work", health="healthy", drift_count=1, score=0.7)
        d = e.to_dict()
        assert d["subsystem"] == "work"
        assert d["health"] == "healthy"
        assert d["drift_count"] == 1
        assert d["score"] == 0.7


class TestOrganismPortfolioSnapshot:
    def test_defaults(self) -> None:
        s = OrganismPortfolioSnapshot()
        assert s.organism_health == OrganismHealth.ALIGNED.value
        assert s.coherence_score == 0.5
        assert s.total_drift_count == 0

    def test_to_dict(self) -> None:
        s = OrganismPortfolioSnapshot(
            organism_health="coherent",
            coherence_score=0.95,
            governance_health="coherent",
        )
        d = s.to_dict()
        assert d["organism_health"] == "coherent"
        assert d["coherence_score"] == 0.95
        assert "subsystem_health" in d
        assert "drift_warnings" in d
        assert "generated_at" in d

    def test_has_all_subsystem_health_fields(self) -> None:
        s = OrganismPortfolioSnapshot()
        d = s.to_dict()
        for field_name in [
            "governance_health", "coordination_health", "institutional_memory_health",
            "executive_health", "prediction_health", "learning_health",
            "work_health", "capability_health",
        ]:
            assert field_name in d


# ── Runtime tests ────────────────────────────────────────────────────


class TestNoDeps:
    def test_coherence_score_returns_float(self) -> None:
        rt = OrganismPortfolioRuntime()
        score = rt.coherence_score()
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_subsystem_health_returns_list(self) -> None:
        rt = OrganismPortfolioRuntime()
        entries = rt.subsystem_health()
        assert isinstance(entries, list)
        assert len(entries) == 8

    def test_drift_warnings_returns_list(self) -> None:
        rt = OrganismPortfolioRuntime()
        warnings = rt.drift_warnings()
        assert isinstance(warnings, list)

    def test_health_returns_enum(self) -> None:
        rt = OrganismPortfolioRuntime()
        h = rt.health()
        assert isinstance(h, OrganismHealth)

    def test_snapshot_returns_snapshot(self) -> None:
        rt = OrganismPortfolioRuntime()
        s = rt.snapshot()
        assert isinstance(s, OrganismPortfolioSnapshot)
        assert s.generated_at > 0

    def test_summary_has_keys(self) -> None:
        rt = OrganismPortfolioRuntime()
        s = rt.summary()
        assert "organism_health" in s
        assert "coherence_score" in s
        assert "total_drift_count" in s
        assert "subsystem_count" in s


class TestWithFakes:
    def test_all_healthy_coherent(self) -> None:
        healthy = FakeHealthy("coherent")
        rt = OrganismPortfolioRuntime(
            governance_runtime=healthy,
            coordination_engine=healthy,
            institutional_memory=healthy,
            executive_portfolio=healthy,
            prediction_portfolio=healthy,
            work_portfolio=healthy,
            learning_portfolio=healthy,
            capability_portfolio=healthy,
        )
        assert rt.health() == OrganismHealth.COHERENT
        assert rt.coherence_score() >= 0.85

    def test_all_critical(self) -> None:
        critical = FakeCritical()
        rt = OrganismPortfolioRuntime(
            governance_runtime=critical,
            coordination_engine=critical,
            institutional_memory=critical,
            executive_portfolio=critical,
            prediction_portfolio=critical,
            work_portfolio=critical,
            learning_portfolio=critical,
            capability_portfolio=critical,
        )
        assert rt.health() == OrganismHealth.CRITICAL
        assert rt.coherence_score() < 0.3

    def test_some_drift_aligned(self) -> None:
        healthy = FakeHealthy("aligned")
        drifting = FakeDrifting("strained", drift_count=1)
        rt = OrganismPortfolioRuntime(
            governance_runtime=healthy,
            coordination_engine=healthy,
            institutional_memory=healthy,
            executive_portfolio=healthy,
            prediction_portfolio=healthy,
            work_portfolio=drifting,
            learning_portfolio=healthy,
            capability_portfolio=healthy,
        )
        h = rt.health()
        assert h in (OrganismHealth.ALIGNED, OrganismHealth.STRAINED)

    def test_many_drift_fragmented(self) -> None:
        drifting = FakeDrifting("fragmented", drift_count=3)
        rt = OrganismPortfolioRuntime(
            governance_runtime=drifting,
            coordination_engine=drifting,
            institutional_memory=drifting,
            executive_portfolio=drifting,
            prediction_portfolio=drifting,
            work_portfolio=drifting,
            learning_portfolio=drifting,
            capability_portfolio=drifting,
        )
        h = rt.health()
        assert h in (OrganismHealth.FRAGMENTED, OrganismHealth.CRITICAL)

    def test_total_drift_count_matches(self) -> None:
        drifting = FakeDrifting("strained", drift_count=2)
        healthy = FakeHealthy("coherent")
        rt = OrganismPortfolioRuntime(
            governance_runtime=healthy,
            coordination_engine=healthy,
            institutional_memory=healthy,
            executive_portfolio=healthy,
            prediction_portfolio=healthy,
            work_portfolio=drifting,
            learning_portfolio=healthy,
            capability_portfolio=healthy,
        )
        snap = rt.snapshot()
        assert snap.total_drift_count == len(snap.drift_warnings)

    def test_governance_coordination_weighted_higher(self) -> None:
        assert _SUBSYSTEM_WEIGHTS["governance"] == 1.5
        assert _SUBSYSTEM_WEIGHTS["coordination"] == 1.5
        assert _SUBSYSTEM_WEIGHTS["work"] == 1.0
        assert _SUBSYSTEM_WEIGHTS["executive"] == 1.0
