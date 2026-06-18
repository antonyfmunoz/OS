"""Tests for Campaign 9.4 — Strategic Memory Engine."""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.organism.strategic_memory_engine import (
    MemorySnapshot,
    StrategicMemory,
    StrategicMemoryEngine,
)


# ── Mock helpers ──────────────────────────────────────────────────────────


@dataclass
class MockDecision:
    decision_id: str = "sd-mock"
    title: str = "Mock Decision"
    status: str = "active"
    goal_refs: list[str] = field(default_factory=list)
    created_at: float = 1000.0
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "title": self.title,
            "status": self.status,
            "goal_refs": self.goal_refs,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class MockDecisionRegistry:
    def __init__(self, decisions: list[MockDecision] | None = None) -> None:
        self._decisions = decisions or []

    def list_decisions(self) -> list[MockDecision]:
        return list(self._decisions)

    def active_decisions(self) -> list[MockDecision]:
        return [d for d in self._decisions if d.status == "active"]


@dataclass
class MockGoal:
    goal_id: str = "g-mock"
    title: str = "Mock Goal"
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        return {"goal_id": self.goal_id, "title": self.title, "status": self.status}


class MockGoalRegistry:
    def __init__(self, goals: list[MockGoal] | None = None) -> None:
        self._goals = goals or []

    def active_goals(self) -> list[MockGoal]:
        return [g for g in self._goals if g.status == "active"]


@dataclass
class MockAssumption:
    assumption_id: str = "asm-mock"
    statement: str = "Mock assumption"
    status: str = "active"
    updated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "statement": self.statement,
            "status": self.status,
            "updated_at": self.updated_at,
        }


class MockAssumptionTracking:
    def __init__(self, assumptions: list[MockAssumption] | None = None) -> None:
        self._assumptions = assumptions or []

    def list_assumptions(self) -> list[MockAssumption]:
        return list(self._assumptions)

    def invalidated(self) -> list[MockAssumption]:
        return [a for a in self._assumptions if a.status == "invalidated"]


@dataclass
class MockValidity:
    decision_id: str = "sd-mock"
    validity: str = "valid"

    def to_dict(self) -> dict[str, Any]:
        return {"decision_id": self.decision_id, "validity": self.validity}


class MockValidityEngine:
    def __init__(self, results: list[MockValidity] | None = None) -> None:
        self._results = results or []

    def evaluate_all(self) -> list[MockValidity]:
        return list(self._results)


# ── MemorySnapshot ────────────────────────────────────────────────────────


class TestMemorySnapshot:
    def test_defaults(self) -> None:
        s = MemorySnapshot()
        assert s.snapshot_id.startswith("snap-")
        assert s.timestamp == 0.0
        assert s.decisions_snapshot == []
        assert s.goals_snapshot == []
        assert s.assumptions_snapshot == []
        assert s.validity_snapshot == []
        assert s.risks_snapshot == []
        assert s.health_summary == {}

    def test_to_dict_keys(self) -> None:
        s = MemorySnapshot()
        keys = set(s.to_dict().keys())
        expected = {
            "snapshot_id", "timestamp", "decisions_snapshot",
            "goals_snapshot", "assumptions_snapshot", "validity_snapshot",
            "risks_snapshot", "health_summary", "created_at",
        }
        assert keys == expected

    def test_from_dict_round_trip(self) -> None:
        original = MemorySnapshot(
            timestamp=123.0,
            decisions_snapshot=[{"decision_id": "sd-1"}],
            goals_snapshot=[{"goal_id": "g-1"}],
            assumptions_snapshot=[{"assumption_id": "asm-1"}],
            validity_snapshot=[{"validity": "valid"}],
            risks_snapshot=[{"risk": "high"}],
            health_summary={"overall": "healthy"},
        )
        restored = MemorySnapshot.from_dict(original.to_dict())
        assert restored.snapshot_id == original.snapshot_id
        assert restored.timestamp == 123.0
        assert restored.decisions_snapshot == [{"decision_id": "sd-1"}]
        assert restored.health_summary == {"overall": "healthy"}

    def test_from_dict_defaults(self) -> None:
        s = MemorySnapshot.from_dict({})
        assert s.timestamp == 0.0
        assert s.decisions_snapshot == []
        assert s.health_summary == {}

    def test_unique_ids(self) -> None:
        s1 = MemorySnapshot()
        s2 = MemorySnapshot()
        assert s1.snapshot_id != s2.snapshot_id

    def test_to_dict_immutability(self) -> None:
        s = MemorySnapshot(decisions_snapshot=[{"id": "1"}])
        out = s.to_dict()
        out["decisions_snapshot"].append({"id": "2"})
        assert len(s.decisions_snapshot) == 1


# ── StrategicMemory ───────────────────────────────────────────────────────


class TestStrategicMemory:
    def test_defaults(self) -> None:
        m = StrategicMemory()
        assert m.current is None
        assert m.history == []
        assert m.decision_timeline == []
        assert m.pattern_observations == []
        assert m.generated_at == 0.0

    def test_to_dict_keys(self) -> None:
        m = StrategicMemory()
        keys = set(m.to_dict().keys())
        expected = {
            "current", "history", "decision_timeline",
            "pattern_observations", "generated_at",
        }
        assert keys == expected

    def test_to_dict_values(self) -> None:
        m = StrategicMemory(
            current={"snapshot_id": "snap-1"},
            history=[{"snapshot_id": "snap-1"}],
            decision_timeline=[{"action": "created"}],
            pattern_observations=["pattern A"],
            generated_at=99.0,
        )
        d = m.to_dict()
        assert d["current"] == {"snapshot_id": "snap-1"}
        assert len(d["history"]) == 1
        assert d["pattern_observations"] == ["pattern A"]
        assert d["generated_at"] == 99.0


# ── StrategicMemoryEngine ────────────────────────────────────────────────


class TestStrategicMemoryEngine:
    @pytest.fixture()
    def tmp_dir(self, tmp_path: str) -> str:
        return str(tmp_path)

    def test_capture_no_deps(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        snap = engine.capture()
        assert snap.snapshot_id.startswith("snap-")
        assert snap.decisions_snapshot == []
        assert snap.goals_snapshot == []
        assert snap.assumptions_snapshot == []
        assert snap.health_summary["overall"] == "empty"

    def test_capture_with_decision_registry(self, tmp_dir: str) -> None:
        reg = MockDecisionRegistry([MockDecision(decision_id="sd-1", title="D1")])
        engine = StrategicMemoryEngine(decision_registry=reg, data_dir=tmp_dir)
        snap = engine.capture()
        assert len(snap.decisions_snapshot) == 1
        assert snap.decisions_snapshot[0]["decision_id"] == "sd-1"

    def test_capture_with_goal_registry(self, tmp_dir: str) -> None:
        goals = MockGoalRegistry([MockGoal(goal_id="g-1")])
        engine = StrategicMemoryEngine(goal_registry=goals, data_dir=tmp_dir)
        snap = engine.capture()
        assert len(snap.goals_snapshot) == 1
        assert snap.goals_snapshot[0]["goal_id"] == "g-1"

    def test_capture_with_assumption_tracking(self, tmp_dir: str) -> None:
        asm = MockAssumptionTracking([MockAssumption(assumption_id="asm-1")])
        engine = StrategicMemoryEngine(assumption_tracking=asm, data_dir=tmp_dir)
        snap = engine.capture()
        assert len(snap.assumptions_snapshot) == 1
        assert snap.assumptions_snapshot[0]["assumption_id"] == "asm-1"

    def test_capture_with_validity_engine(self, tmp_dir: str) -> None:
        ve = MockValidityEngine([MockValidity(decision_id="sd-1", validity="at_risk")])
        reg = MockDecisionRegistry([MockDecision(decision_id="sd-1")])
        engine = StrategicMemoryEngine(
            decision_registry=reg, validity_engine=ve, data_dir=tmp_dir
        )
        snap = engine.capture()
        assert len(snap.validity_snapshot) == 1
        assert snap.validity_snapshot[0]["validity"] == "at_risk"

    def test_get_current_none(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        assert engine.get_current() is None

    def test_get_current_returns_latest(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        engine.capture()
        engine.capture()
        current = engine.get_current()
        assert current is not None
        history = engine.get_history()
        assert current.timestamp == history[0].timestamp

    def test_get_history_sorted(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        engine.capture()
        engine.capture()
        engine.capture()
        history = engine.get_history()
        assert len(history) == 3
        for i in range(len(history) - 1):
            assert history[i].timestamp >= history[i + 1].timestamp

    def test_get_history_limit(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        for _ in range(5):
            engine.capture()
        history = engine.get_history(limit=2)
        assert len(history) == 2

    def test_decision_timeline_no_registry(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        assert engine.decision_timeline() == []

    def test_decision_timeline_with_registry(self, tmp_dir: str) -> None:
        decisions = [
            MockDecision(decision_id="sd-1", title="D1", created_at=100.0),
            MockDecision(decision_id="sd-2", title="D2", created_at=200.0),
        ]
        reg = MockDecisionRegistry(decisions)
        engine = StrategicMemoryEngine(decision_registry=reg, data_dir=tmp_dir)
        tl = engine.decision_timeline()
        assert len(tl) == 2
        assert tl[0]["timestamp"] >= tl[1]["timestamp"]

    def test_decision_timeline_includes_updates(self, tmp_dir: str) -> None:
        decisions = [
            MockDecision(decision_id="sd-1", created_at=100.0, updated_at=150.0),
        ]
        reg = MockDecisionRegistry(decisions)
        engine = StrategicMemoryEngine(decision_registry=reg, data_dir=tmp_dir)
        tl = engine.decision_timeline()
        assert len(tl) == 2
        actions = {e["action"] for e in tl}
        assert "created" in actions
        assert "updated" in actions

    def test_decision_timeline_since_filter(self, tmp_dir: str) -> None:
        decisions = [
            MockDecision(decision_id="sd-1", created_at=100.0),
            MockDecision(decision_id="sd-2", created_at=200.0),
        ]
        reg = MockDecisionRegistry(decisions)
        engine = StrategicMemoryEngine(decision_registry=reg, data_dir=tmp_dir)
        tl = engine.decision_timeline(since=150.0)
        assert len(tl) == 1
        assert tl[0]["decision_id"] == "sd-2"

    def test_synthesize(self, tmp_dir: str) -> None:
        reg = MockDecisionRegistry([MockDecision()])
        engine = StrategicMemoryEngine(decision_registry=reg, data_dir=tmp_dir)
        engine.capture()
        mem = engine.synthesize()
        assert mem.current is not None
        assert len(mem.history) >= 1
        assert mem.generated_at > 0

    def test_synthesize_no_snapshots(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        mem = engine.synthesize()
        assert mem.current is None
        assert mem.history == []

    def test_diff_added_decisions(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        snap_a = MemorySnapshot(
            snapshot_id="snap-a",
            timestamp=1.0,
            decisions_snapshot=[{"decision_id": "sd-1", "status": "active"}],
        )
        snap_b = MemorySnapshot(
            snapshot_id="snap-b",
            timestamp=2.0,
            decisions_snapshot=[
                {"decision_id": "sd-1", "status": "active"},
                {"decision_id": "sd-2", "status": "active"},
            ],
        )
        engine._snapshots = [snap_a, snap_b]
        result = engine.diff("snap-a", "snap-b")
        assert "sd-2" in result["added_decisions"]
        assert result["removed_decisions"] == []

    def test_diff_removed_decisions(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        snap_a = MemorySnapshot(
            snapshot_id="snap-a",
            timestamp=1.0,
            decisions_snapshot=[
                {"decision_id": "sd-1", "status": "active"},
                {"decision_id": "sd-2", "status": "active"},
            ],
        )
        snap_b = MemorySnapshot(
            snapshot_id="snap-b",
            timestamp=2.0,
            decisions_snapshot=[{"decision_id": "sd-1", "status": "active"}],
        )
        engine._snapshots = [snap_a, snap_b]
        result = engine.diff("snap-a", "snap-b")
        assert "sd-2" in result["removed_decisions"]

    def test_diff_status_changes(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        snap_a = MemorySnapshot(
            snapshot_id="snap-a",
            timestamp=1.0,
            decisions_snapshot=[{"decision_id": "sd-1", "status": "active"}],
        )
        snap_b = MemorySnapshot(
            snapshot_id="snap-b",
            timestamp=2.0,
            decisions_snapshot=[{"decision_id": "sd-1", "status": "superseded"}],
        )
        engine._snapshots = [snap_a, snap_b]
        result = engine.diff("snap-a", "snap-b")
        assert len(result["status_changes"]) == 1
        assert result["status_changes"][0]["old_status"] == "active"
        assert result["status_changes"][0]["new_status"] == "superseded"

    def test_diff_goal_changes(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        snap_a = MemorySnapshot(
            snapshot_id="snap-a",
            timestamp=1.0,
            goals_snapshot=[{"goal_id": "g-1"}],
        )
        snap_b = MemorySnapshot(
            snapshot_id="snap-b",
            timestamp=2.0,
            goals_snapshot=[{"goal_id": "g-1"}, {"goal_id": "g-2"}],
        )
        engine._snapshots = [snap_a, snap_b]
        result = engine.diff("snap-a", "snap-b")
        assert "g-2" in result["added_goals"]

    def test_diff_assumption_changes(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        snap_a = MemorySnapshot(
            snapshot_id="snap-a",
            timestamp=1.0,
            assumptions_snapshot=[{"assumption_id": "asm-1"}, {"assumption_id": "asm-2"}],
        )
        snap_b = MemorySnapshot(
            snapshot_id="snap-b",
            timestamp=2.0,
            assumptions_snapshot=[{"assumption_id": "asm-1"}],
        )
        engine._snapshots = [snap_a, snap_b]
        result = engine.diff("snap-a", "snap-b")
        assert "asm-2" in result["removed_assumptions"]

    def test_diff_missing_snapshot(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        result = engine.diff("nonexistent-a", "nonexistent-b")
        assert "error" in result

    def test_detect_patterns_empty(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        assert engine.detect_patterns() == []

    def test_detect_patterns_no_decisions(self, tmp_dir: str) -> None:
        reg = MockDecisionRegistry([])
        engine = StrategicMemoryEngine(decision_registry=reg, data_dir=tmp_dir)
        assert engine.detect_patterns() == []

    def test_detect_patterns_superseded(self, tmp_dir: str) -> None:
        now = time.time()
        decisions = [
            MockDecision(decision_id=f"sd-{i}", status="superseded", updated_at=now)
            for i in range(3)
        ]
        reg = MockDecisionRegistry(decisions)
        engine = StrategicMemoryEngine(decision_registry=reg, data_dir=tmp_dir)
        patterns = engine.detect_patterns()
        assert any("superseded" in p for p in patterns)

    def test_detect_patterns_unlinked_goals(self, tmp_dir: str) -> None:
        decisions = [
            MockDecision(decision_id="sd-1", status="active", goal_refs=[]),
        ]
        reg = MockDecisionRegistry(decisions)
        engine = StrategicMemoryEngine(decision_registry=reg, data_dir=tmp_dir)
        patterns = engine.detect_patterns()
        assert any("not linked" in p for p in patterns)

    def test_detect_patterns_invalidated_assumptions(self, tmp_dir: str) -> None:
        now = time.time()
        decisions = [MockDecision(decision_id="sd-1", status="active", goal_refs=["g-1"])]
        reg = MockDecisionRegistry(decisions)
        asms = [
            MockAssumption(assumption_id=f"asm-{i}", status="invalidated", updated_at=now)
            for i in range(3)
        ]
        asm_tracker = MockAssumptionTracking(asms)
        engine = StrategicMemoryEngine(
            decision_registry=reg, assumption_tracking=asm_tracker, data_dir=tmp_dir
        )
        patterns = engine.detect_patterns()
        assert any("invalidated" in p for p in patterns)

    def test_persistence_round_trip(self, tmp_dir: str) -> None:
        reg = MockDecisionRegistry([MockDecision()])
        e1 = StrategicMemoryEngine(decision_registry=reg, data_dir=tmp_dir)
        snap = e1.capture()

        e2 = StrategicMemoryEngine(data_dir=tmp_dir)
        loaded = e2.get_current()
        assert loaded is not None
        assert loaded.snapshot_id == snap.snapshot_id

    def test_persistence_file_created(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        engine.capture()
        assert os.path.exists(os.path.join(tmp_dir, "snapshots.jsonl"))

    def test_summary_keys(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        s = engine.summary()
        expected = {"snapshot_count", "current_health", "pattern_count", "patterns", "generated_at"}
        assert set(s.keys()) == expected

    def test_summary_snapshot_count(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        engine.capture()
        engine.capture()
        s = engine.summary()
        assert s["snapshot_count"] == 2

    def test_health_empty(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        snap = engine.capture()
        assert snap.health_summary["overall"] == "empty"

    def test_health_healthy(self, tmp_dir: str) -> None:
        reg = MockDecisionRegistry([MockDecision()])
        engine = StrategicMemoryEngine(decision_registry=reg, data_dir=tmp_dir)
        snap = engine.capture()
        assert snap.health_summary["overall"] == "healthy"

    def test_health_degraded(self, tmp_dir: str) -> None:
        reg = MockDecisionRegistry([MockDecision()])
        ve = MockValidityEngine([MockValidity(validity="at_risk")])
        engine = StrategicMemoryEngine(
            decision_registry=reg, validity_engine=ve, data_dir=tmp_dir
        )
        snap = engine.capture()
        assert snap.health_summary["overall"] == "degraded"

    def test_health_watch(self, tmp_dir: str) -> None:
        reg = MockDecisionRegistry([MockDecision()])
        asms = MockAssumptionTracking([
            MockAssumption(assumption_id="asm-1", status="active"),
            MockAssumption(assumption_id="asm-2", status="invalidated"),
            MockAssumption(assumption_id="asm-3", status="invalidated"),
        ])
        engine = StrategicMemoryEngine(
            decision_registry=reg, assumption_tracking=asms, data_dir=tmp_dir
        )
        snap = engine.capture()
        assert snap.health_summary["overall"] == "watch"

    def test_health_summary_keys(self, tmp_dir: str) -> None:
        engine = StrategicMemoryEngine(data_dir=tmp_dir)
        snap = engine.capture()
        expected = {
            "overall", "total_decisions", "total_assumptions",
            "invalidated_assumptions", "at_risk_decisions",
        }
        assert set(snap.health_summary.keys()) == expected
