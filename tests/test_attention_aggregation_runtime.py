"""Tests for AttentionAggregationRuntime — Campaign 18.2."""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from substrate.workstation.attention_aggregation_runtime import (
    AttentionAggregationRuntime,
    AttentionQueueSnapshot,
)


# ── Fakes ──────────────────────────────────────────────────────────────


class _Snapshot:
    def __init__(self, d: dict):
        self._d = d

    def to_dict(self) -> dict:
        return self._d


class _FakeItem:
    def __init__(self, **kw):
        self._data = {
            "priority": 0,
            "category": "change",
            "severity": "medium",
            "title": "test",
            "description": "",
            "action_hint": "",
            "source_id": "",
            "source_system": "test",
            "capability_link": "",
            "timestamp": time.time(),
        }
        self._data.update(kw)

    def to_dict(self) -> dict:
        return self._data


class _FakeAttentionEngine:
    def __init__(self, items: list | None = None):
        self._items = items or []

    def attention_queue(self):
        return self._items


class _FakeOrganismState:
    def __init__(self, items: list | None = None):
        self._items = items or []

    def snapshot(self):
        return _Snapshot({"attention_items": self._items})


class _FakeGovernedExecution:
    def __init__(self, blockers: list | None = None, pending: int = 0):
        self._blockers = blockers or []
        self._pending = pending

    def assess(self):
        return _Snapshot({
            "top_blockers": self._blockers,
            "pending_approval_count": self._pending,
        })


class _FakeOrganismPortfolio:
    def __init__(self, warnings: list | None = None):
        self._warnings = warnings or []

    def snapshot(self):
        return _Snapshot({"drift_warnings": self._warnings})


def _runtime(**overrides) -> AttentionAggregationRuntime:
    defaults = {
        "attention_engine": _FakeAttentionEngine(),
        "organism_state": _FakeOrganismState(),
        "governed_execution": _FakeGovernedExecution(),
        "organism_portfolio": _FakeOrganismPortfolio(),
    }
    defaults.update(overrides)
    return AttentionAggregationRuntime(**defaults)


# ── Snapshot Type Tests ────────────────────────────────────────────


class TestAttentionQueueSnapshot:
    def test_to_dict_fields(self):
        snap = AttentionQueueSnapshot()
        d = snap.to_dict()
        expected = {"items", "total_count", "critical_count", "top_category", "generated_at"}
        assert expected.issubset(set(d.keys()))

    def test_defaults(self):
        snap = AttentionQueueSnapshot()
        assert snap.total_count == 0
        assert snap.critical_count == 0
        assert snap.items == []


# ── Collection Tests ────────────────────────────────────────────────


class TestCollection:
    def test_empty_sources_produce_empty_queue(self):
        rt = _runtime()
        q = rt.queue()
        assert q.total_count == 0

    def test_attention_engine_items_collected(self):
        items = [_FakeItem(title="engine item")]
        rt = _runtime(attention_engine=_FakeAttentionEngine(items=items))
        q = rt.queue()
        assert q.total_count == 1
        assert q.items[0]["title"] == "engine item"

    def test_organism_state_items_collected(self):
        items = [{"title": "org item", "category": "drift"}]
        rt = _runtime(organism_state=_FakeOrganismState(items=items))
        q = rt.queue()
        assert q.total_count == 1

    def test_governed_execution_blockers_collected(self):
        blockers = [{"blocker": "Missing dep", "detail": "No executor"}]
        rt = _runtime(governed_execution=_FakeGovernedExecution(blockers=blockers))
        q = rt.queue()
        assert any(i["category"] == "blocked" for i in q.items)

    def test_governed_execution_pending_approvals(self):
        rt = _runtime(governed_execution=_FakeGovernedExecution(pending=3))
        q = rt.queue()
        assert any(i["category"] == "approval" for i in q.items)

    def test_portfolio_drift_warnings_collected(self):
        warnings = [{"severity": "high", "description": "Governance drift"}]
        rt = _runtime(organism_portfolio=_FakeOrganismPortfolio(warnings=warnings))
        q = rt.queue()
        assert any(i["category"] == "drift" for i in q.items)


# ── Ranking Tests ──────────────────────────────────────────────────


class TestRanking:
    def test_failure_before_change(self):
        items = [
            _FakeItem(title="change", category="change"),
            _FakeItem(title="failure", category="failure"),
        ]
        rt = _runtime(attention_engine=_FakeAttentionEngine(items=items))
        q = rt.queue()
        assert q.items[0]["title"] == "failure"

    def test_critical_before_low(self):
        items = [
            _FakeItem(title="low", category="drift", severity="low"),
            _FakeItem(title="critical", category="drift", severity="critical"),
        ]
        rt = _runtime(attention_engine=_FakeAttentionEngine(items=items))
        q = rt.queue()
        assert q.items[0]["title"] == "critical"

    def test_critical_count_accurate(self):
        items = [
            _FakeItem(severity="critical"),
            _FakeItem(severity="critical"),
            _FakeItem(severity="medium"),
        ]
        rt = _runtime(attention_engine=_FakeAttentionEngine(items=items))
        q = rt.queue()
        assert q.critical_count == 2

    def test_top_category_is_highest_priority(self):
        items = [
            _FakeItem(category="change"),
            _FakeItem(category="failure"),
        ]
        rt = _runtime(attention_engine=_FakeAttentionEngine(items=items))
        q = rt.queue()
        assert q.top_category == "failure"


# ── Count API Tests ─────────────────────────────────────────────────


class TestCountAPI:
    def test_count_returns_dict(self):
        rt = _runtime()
        c = rt.count()
        assert "total" in c
        assert "critical" in c

    def test_count_matches_queue(self):
        items = [_FakeItem(severity="critical"), _FakeItem(severity="low")]
        rt = _runtime(attention_engine=_FakeAttentionEngine(items=items))
        c = rt.count()
        assert c["total"] == 2
        assert c["critical"] == 1


# ── Graceful Degradation Tests ──────────────────────────────────────


class _BrokenSubsystem:
    """Subsystem that always raises — simulates unavailable dep."""

    def attention_queue(self):
        raise RuntimeError("offline")

    def snapshot(self):
        raise RuntimeError("offline")

    def assess(self):
        raise RuntimeError("offline")


class TestGracefulDegradation:
    def test_broken_deps_produce_empty_queue(self):
        broken = _BrokenSubsystem()
        rt = AttentionAggregationRuntime(
            attention_engine=broken,
            organism_state=broken,
            governed_execution=broken,
            organism_portfolio=broken,
        )
        q = rt.queue()
        assert q.total_count == 0
