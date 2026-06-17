"""Campaign 7.4 — Drift Detection Engine tests.

Tests unified drift detection: tick-loop mapping, documentation drift,
execution drift, strategic drift, severity ranking, graceful degradation.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.organism.drift_detection_engine import (
    DriftDetectionEngine,
    DriftType,
    UnifiedDriftWarning,
)


# ── Lightweight mocks ────────────────────────────────────────────────


class _MockTickLoop:
    def __init__(self, drift: list | None = None) -> None:
        self._drift = drift or []

    def get_strategic_state(self) -> dict:
        return {"drift_warnings": self._drift}


class _MockDocEntry:
    def __init__(self, name: str = "") -> None:
        self.name = name


class _MockDocAwareness:
    def __init__(self, stale: list | None = None) -> None:
        self._stale = stale or []

    def find_stale_docs(self) -> list:
        return self._stale


class _MockRuntimeAwareness:
    def __init__(
        self,
        active: list | None = None,
        blocked: list | None = None,
    ) -> None:
        self._active = active or []
        self._blocked = blocked or []

    def active_work(self) -> list:
        return self._active

    def blocked_work(self) -> list:
        return self._blocked


class _MockPrioritizedItem:
    def __init__(self, title: str = "", entity_refs: list | None = None) -> None:
        self.title = title
        self.entity_refs = entity_refs or []


class _MockPriorityEngine:
    def __init__(self, priorities: list | None = None) -> None:
        self._priorities = priorities or []

    def top(self, limit: int = 3) -> list:
        return self._priorities[:limit]


def _make_engine(**kwargs) -> DriftDetectionEngine:
    return DriftDetectionEngine(**kwargs)


# ── UnifiedDriftWarning tests ────────────────────────────────────────


class TestUnifiedDriftWarning:
    def test_default_values(self) -> None:
        w = UnifiedDriftWarning()
        assert w.drift_id.startswith("drift-")
        assert w.drift_type == "strategic"
        assert w.severity == "warning"

    def test_to_dict_keys(self) -> None:
        w = UnifiedDriftWarning(title="test")
        d = w.to_dict()
        expected = {
            "drift_id", "drift_type", "severity", "title",
            "description", "entity_refs", "detected_at", "days_stagnant",
        }
        assert set(d.keys()) == expected


class TestDriftType:
    def test_values(self) -> None:
        assert DriftType.DOCUMENTATION.value == "documentation"
        assert DriftType.EXECUTION.value == "execution"
        assert DriftType.REALITY.value == "reality"
        assert DriftType.STRATEGIC.value == "strategic"
        assert DriftType.GOVERNANCE.value == "governance"
        assert len(DriftType) == 5


# ── Tick-loop drift mapping tests ────────────────────────────────────


class TestTickLoopDrift:
    def test_maps_tick_drift(self) -> None:
        drift = [{"severity": "alert", "goal_title": "Auth goal", "days_stagnant": 14, "goal_id": "g-1"}]
        engine = _make_engine(tick_loop=_MockTickLoop(drift=drift))
        result = engine.detect_drift()
        assert len(result) == 1
        assert result[0].drift_type == "strategic"
        assert result[0].severity == "alert"
        assert result[0].days_stagnant == 14

    def test_maps_multiple_drift(self) -> None:
        drift = [
            {"severity": "warning", "goal_title": "d-1"},
            {"severity": "critical", "goal_title": "d-2"},
        ]
        engine = _make_engine(tick_loop=_MockTickLoop(drift=drift))
        result = engine.detect_drift()
        assert len(result) == 2

    def test_empty_drift(self) -> None:
        engine = _make_engine(tick_loop=_MockTickLoop(drift=[]))
        assert engine.detect_drift() == []


# ── Documentation drift tests ───────────────────────────────────────


class TestDocumentationDrift:
    def test_stale_docs_create_drift(self) -> None:
        stale = [_MockDocEntry("readme.md"), _MockDocEntry("arch.md")]
        engine = _make_engine(documentation_awareness=_MockDocAwareness(stale=stale))
        result = engine.detect_drift()
        assert len(result) == 1
        assert result[0].drift_type == "documentation"
        assert result[0].severity == "warning"

    def test_many_stale_docs_alert(self) -> None:
        stale = [_MockDocEntry(f"doc-{i}.md") for i in range(6)]
        engine = _make_engine(documentation_awareness=_MockDocAwareness(stale=stale))
        result = engine.detect_drift()
        assert result[0].severity == "alert"

    def test_no_stale_no_drift(self) -> None:
        engine = _make_engine(documentation_awareness=_MockDocAwareness(stale=[]))
        assert engine.detect_drift() == []


# ── Execution drift tests ───────────────────────────────────────────


class TestExecutionDrift:
    def test_approved_old_work_drifts(self) -> None:
        five_days_ago = time.time() - 5 * 86400
        active = [{"status": "approved", "title": "auth work", "created_at": five_days_ago}]
        engine = _make_engine(
            runtime_awareness=_MockRuntimeAwareness(active=active),
        )
        result = engine.detect_drift()
        assert len(result) == 1
        assert result[0].drift_type == "execution"
        assert result[0].days_stagnant >= 4

    def test_recently_approved_no_drift(self) -> None:
        recent = time.time() - 1 * 86400
        active = [{"status": "approved", "title": "new work", "created_at": recent}]
        engine = _make_engine(
            runtime_awareness=_MockRuntimeAwareness(active=active),
        )
        assert engine.detect_drift() == []

    def test_executing_work_no_drift(self) -> None:
        old = time.time() - 10 * 86400
        active = [{"status": "executing", "title": "running", "created_at": old}]
        engine = _make_engine(
            runtime_awareness=_MockRuntimeAwareness(active=active),
        )
        assert engine.detect_drift() == []

    def test_week_old_approval_alert(self) -> None:
        eight_days_ago = time.time() - 8 * 86400
        active = [{"status": "approved", "title": "old", "created_at": eight_days_ago}]
        engine = _make_engine(
            runtime_awareness=_MockRuntimeAwareness(active=active),
        )
        result = engine.detect_drift()
        assert result[0].severity == "alert"


# ── Strategic drift tests ───────────────────────────────────────────


class TestStrategicDrift:
    def test_priority_without_active_work(self) -> None:
        priorities = [_MockPrioritizedItem("auth migration")]
        engine = _make_engine(
            priority_engine=_MockPriorityEngine(priorities=priorities),
            runtime_awareness=_MockRuntimeAwareness(active=[]),
        )
        result = engine.detect_drift()
        assert len(result) == 1
        assert result[0].drift_type == "strategic"
        assert "auth migration" in result[0].title

    def test_priority_with_matching_work_no_drift(self) -> None:
        priorities = [_MockPrioritizedItem("auth migration")]
        active = [{"title": "auth migration implementation"}]
        engine = _make_engine(
            priority_engine=_MockPriorityEngine(priorities=priorities),
            runtime_awareness=_MockRuntimeAwareness(active=active),
        )
        result = engine.detect_drift()
        strategic = [d for d in result if d.drift_type == "strategic"]
        assert len(strategic) == 0

    def test_multiple_priorities_some_drift(self) -> None:
        priorities = [
            _MockPrioritizedItem("auth migration"),
            _MockPrioritizedItem("deploy infra"),
        ]
        active = [{"title": "auth migration work"}]
        engine = _make_engine(
            priority_engine=_MockPriorityEngine(priorities=priorities),
            runtime_awareness=_MockRuntimeAwareness(active=active),
        )
        result = engine.detect_drift()
        strategic = [d for d in result if d.drift_type == "strategic"]
        assert len(strategic) == 1
        assert "deploy infra" in strategic[0].title

    def test_needs_both_engines(self) -> None:
        priorities = [_MockPrioritizedItem("x")]
        engine = _make_engine(priority_engine=_MockPriorityEngine(priorities=priorities))
        assert engine.detect_drift() == []


# ── Filtering tests ─────────────────────────────────────────────────


class TestFiltering:
    def test_high_drift(self) -> None:
        drift = [
            {"severity": "warning", "goal_title": "low"},
            {"severity": "critical", "goal_title": "high"},
        ]
        engine = _make_engine(tick_loop=_MockTickLoop(drift=drift))
        engine.detect_drift()
        high = engine.high_drift()
        assert all(h.severity in ("alert", "critical") for h in high)
        assert len(high) == 1

    def test_by_type(self) -> None:
        stale = [_MockDocEntry("d1")]
        drift = [{"severity": "warning", "goal_title": "g1"}]
        engine = _make_engine(
            tick_loop=_MockTickLoop(drift=drift),
            documentation_awareness=_MockDocAwareness(stale=stale),
        )
        engine.detect_drift()
        doc_drift = engine.by_type("documentation")
        strategic_drift = engine.by_type("strategic")
        assert len(doc_drift) == 1
        assert len(strategic_drift) == 1


# ── Sorting tests ───────────────────────────────────────────────────


class TestSorting:
    def test_sorted_by_severity(self) -> None:
        drift = [
            {"severity": "warning", "goal_title": "low"},
            {"severity": "critical", "goal_title": "high"},
            {"severity": "alert", "goal_title": "mid"},
        ]
        engine = _make_engine(tick_loop=_MockTickLoop(drift=drift))
        result = engine.detect_drift()
        severities = [w.severity for w in result]
        assert severities[0] == "critical"


# ── Graceful degradation ───────────────────────────────────────────


class TestGracefulDegradation:
    def test_no_engines(self) -> None:
        engine = _make_engine()
        assert engine.detect_drift() == []

    def test_broken_tick_loop(self) -> None:
        class _Broken:
            def get_strategic_state(self):
                raise RuntimeError("down")
        engine = _make_engine(tick_loop=_Broken())
        assert engine.detect_drift() == []

    def test_broken_doc_awareness(self) -> None:
        class _Broken:
            def find_stale_docs(self):
                raise RuntimeError("down")
        engine = _make_engine(documentation_awareness=_Broken())
        assert engine.detect_drift() == []

    def test_mixed_working_and_broken(self) -> None:
        class _BrokenDoc:
            def find_stale_docs(self):
                raise RuntimeError("down")

        drift = [{"severity": "warning", "goal_title": "works"}]
        engine = _make_engine(
            tick_loop=_MockTickLoop(drift=drift),
            documentation_awareness=_BrokenDoc(),
        )
        result = engine.detect_drift()
        assert len(result) == 1
