"""Tests for CapabilityEvolutionEngine — Campaign 12.2."""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest
from substrate.organism.capability_evolution_engine import (
    CapabilityEvolutionEngine,
    CapabilityTrajectory,
    EvolutionEvent,
    EvolutionEventType,
    EvolutionSnapshot,
)


# ── Fixtures ──────────────────────────────────────────────────────────


class FakeCapabilityRuntime:
    _caps = {
        "cap-1": type("C", (), {"capability_id": "cap-1", "name": "Python", "maturity": "operational", "status": "active"})(),
        "cap-2": type("C", (), {"capability_id": "cap-2", "name": "Docker", "maturity": "emerging", "status": "active"})(),
        "cap-3": type("C", (), {"capability_id": "cap-3", "name": "Testing", "maturity": "validated", "status": "active"})(),
    }

    def list_capabilities(self) -> list:
        return list(self._caps.values())

    def get(self, capability_id: str):
        return self._caps.get(capability_id)

    def maturity_score(self, capability_id: str) -> float:
        scores = {"cap-1": 0.8, "cap-2": 0.3, "cap-3": 0.6}
        return scores.get(capability_id, 0.0)

    def evidence_for(self, capability_id: str) -> list:
        return [{"type": "outcome", "id": "out-1", "timestamp": time.time()}]

    def propose_from_patterns(self) -> list:
        return []


class FakeCapabilityPortfolio:
    def compounding_score(self) -> float:
        return 0.65

    def health(self) -> str:
        return "healthy"

    def snapshot(self) -> object:
        return type("S", (), {
            "total_capabilities": 3,
            "advancing_count": 1,
            "declining_count": 0,
            "stalled_count": 1,
            "compounding_score": 0.65,
            "health": "healthy",
            "to_dict": lambda self: {"total_capabilities": 3},
        })()


class FakePatternEngine:
    def patterns_for_capability(self, cap_id: str) -> list:
        return [type("P", (), {"id": "p-1", "pattern_type": "recurring_success", "occurrences": 4, "confidence": 0.8})()]

    def correlations(self) -> list:
        return []


class FakeLearningExtraction:
    def lessons_by_category(self, category: str) -> list:
        if category == "capability_gap":
            return [type("L", (), {"id": "l-1", "related_capability_ids": ["cap-2"], "title": "Docker gap"})()]
        return []


class FakeCompounding:
    def detect_insight_to_capability(self) -> list:
        return []

    def detect_capability_to_operationalization(self) -> list:
        return []


# ── Type tests ────────────────────────────────────────────────────────


class TestEvolutionEventType:
    def test_all_values(self) -> None:
        assert len(EvolutionEventType) == 7
        assert "maturity_advance" in [e.value for e in EvolutionEventType]


class TestEvolutionEvent:
    def test_defaults(self) -> None:
        ev = EvolutionEvent()
        assert ev.event_id == ""
        assert ev.capability_id == ""
        assert ev.timestamp == 0.0

    def test_to_dict(self) -> None:
        ev = EvolutionEvent(event_id="ev-1", capability_id="cap-1", event_type="maturity_advance")
        d = ev.to_dict()
        assert d["event_id"] == "ev-1"


class TestCapabilityTrajectory:
    def test_defaults(self) -> None:
        t = CapabilityTrajectory()
        assert t.capability_id == ""
        assert t.maturity_trend == 0.0
        assert t.events == []

    def test_to_dict(self) -> None:
        t = CapabilityTrajectory(
            capability_id="cap-1",
            capability_name="Python",
            current_maturity="operational",
            maturity_trend=0.5,
        )
        d = t.to_dict()
        assert d["capability_id"] == "cap-1"
        assert d["maturity_trend"] == 0.5


class TestEvolutionSnapshot:
    def test_defaults(self) -> None:
        snap = EvolutionSnapshot()
        assert snap.total_capabilities == 0
        assert snap.evolution_velocity == 0.0


# ── Runtime tests ─────────────────────────────────────────────────────


class TestCapabilityEvolutionEngine:
    def _make_engine(self) -> CapabilityEvolutionEngine:
        return CapabilityEvolutionEngine(
            capability_runtime=FakeCapabilityRuntime(),
            capability_portfolio=FakeCapabilityPortfolio(),
            outcome_patterns=FakePatternEngine(),
            learning_extraction=FakeLearningExtraction(),
            compounding_engine=FakeCompounding(),
        )

    def test_instantiation(self) -> None:
        engine = self._make_engine()
        assert engine is not None

    def test_trajectory(self) -> None:
        engine = self._make_engine()
        t = engine.trajectory("cap-1")
        assert t is not None
        assert isinstance(t, CapabilityTrajectory)
        assert t.capability_id == "cap-1"

    def test_all_trajectories(self) -> None:
        engine = self._make_engine()
        trajectories = engine.all_trajectories()
        assert isinstance(trajectories, list)
        assert len(trajectories) == 3

    def test_advancing(self) -> None:
        engine = self._make_engine()
        adv = engine.advancing()
        assert isinstance(adv, list)

    def test_declining(self) -> None:
        engine = self._make_engine()
        dec = engine.declining()
        assert isinstance(dec, list)

    def test_stalled(self) -> None:
        engine = self._make_engine()
        stalled = engine.stalled()
        assert isinstance(stalled, list)

    def test_evolution_recommendations(self) -> None:
        engine = self._make_engine()
        recs = engine.evolution_recommendations()
        assert isinstance(recs, list)

    def test_record_evolution(self) -> None:
        engine = self._make_engine()
        ev = engine.record_evolution(
            capability_id="cap-1",
            event_type=EvolutionEventType.NEW_EVIDENCE.value,
            description="New test evidence",
        )
        assert isinstance(ev, EvolutionEvent)
        assert ev.capability_id == "cap-1"

    def test_snapshot(self) -> None:
        engine = self._make_engine()
        snap = engine.snapshot()
        assert isinstance(snap, EvolutionSnapshot)
        assert snap.total_capabilities == 3

    def test_summary(self) -> None:
        engine = self._make_engine()
        s = engine.summary()
        assert isinstance(s, dict)
        assert "total_capabilities" in s

    def test_health(self) -> None:
        engine = self._make_engine()
        h = engine.health()
        assert h in ("evolving", "declining", "stalled", "stable", "dormant", "unknown")

    def test_no_deps_graceful(self) -> None:
        engine = CapabilityEvolutionEngine()
        snap = engine.snapshot()
        assert snap.total_capabilities == 0

    def test_trajectory_missing_capability(self) -> None:
        engine = self._make_engine()
        t = engine.trajectory("nonexistent")
        assert t is None or isinstance(t, CapabilityTrajectory)

    def test_maturity_levels_ordered(self) -> None:
        from substrate.organism.capability_evolution_engine import _MATURITY_LEVELS
        assert len(_MATURITY_LEVELS) == 4
        assert _MATURITY_LEVELS[0] == "emerging"
        assert _MATURITY_LEVELS[-1] == "institutional"
