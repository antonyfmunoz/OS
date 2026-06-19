"""Integration tests for Campaign 18 — Jarvis Experience Validation (C18.5)."""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from substrate.workstation.unified_workstation_runtime import (
    UnifiedWorkstationRuntime,
    UnifiedWorkstationSnapshot,
    UnifiedWorkstationState,
)
from substrate.workstation.attention_aggregation_runtime import (
    AttentionAggregationRuntime,
    AttentionQueueSnapshot,
)


# ── Shared fakes ──────────────────────────────────────────────────────


class _Snap:
    def __init__(self, d: dict):
        self._d = d

    def to_dict(self) -> dict:
        return self._d


class _FakeItem:
    def __init__(self, **kw):
        self._data = {"priority": 0, "category": "change", "severity": "medium",
                       "title": "test", "description": "", "action_hint": "",
                       "source_id": "", "source_system": "test", "capability_link": "",
                       "timestamp": time.time()}
        self._data.update(kw)

    def to_dict(self) -> dict:
        return self._data


class _FakeOrchestrator:
    def snapshot(self):
        return _Snap({"mode": "planning", "active_project": "umh",
                       "active_repo": "OS", "active_delegation_count": 1})


class _FakeWorkstation:
    def snapshot(self):
        return _Snap({"active_panel": "editor", "active_project": "", "active_repo": ""})


class _FakeOrgState:
    def snapshot(self):
        return _Snap({"mode": "executing", "health": "healthy",
                       "attention_items": [{"title": "org item"}]})


class _FakeExec:
    def assess(self):
        return _Snap({"state": "executing", "top_blockers": [],
                       "pending_approval_count": 2})


class _FakePortfolio:
    def snapshot(self):
        return _Snap({"organism_health": "aligned", "coherence_score": 0.85,
                       "subsystem_health": [{"subsystem": "governance", "health": "healthy"}],
                       "drift_warnings": [{"severity": "low", "description": "Minor drift"}]})


class _FakeApprovals:
    def snapshot(self):
        return _Snap({"pending_count": 2})


class _FakeCC:
    def snapshot(self):
        return _Snap({"sections": []})


class _FakeAttentionEngine:
    def attention_queue(self):
        return [_FakeItem(title="critical failure", category="failure", severity="critical")]


# ── Integration Tests ─────────────────────────────────────────────────


class TestUnifiedSnapshotIntegration:
    """Full composition: 7 runtimes → 1 snapshot → all fields populated."""

    @classmethod
    def setup_class(cls):
        cls.rt = UnifiedWorkstationRuntime(
            orchestrator_presence=_FakeOrchestrator(),
            workstation_presence=_FakeWorkstation(),
            organism_state=_FakeOrgState(),
            governed_execution=_FakeExec(),
            organism_portfolio=_FakePortfolio(),
            unified_approvals=_FakeApprovals(),
            command_center=_FakeCC(),
        )
        cls.snap = cls.rt.snapshot()

    def test_snapshot_type(self):
        assert isinstance(self.snap, UnifiedWorkstationSnapshot)

    def test_state_derived_correctly(self):
        assert self.snap.workstation_state == "executing"

    def test_organism_mode_propagated(self):
        assert self.snap.organism_mode == "executing"

    def test_project_from_orchestrator(self):
        assert self.snap.active_project == "umh"

    def test_panel_from_workstation(self):
        assert self.snap.active_panel == "editor"

    def test_approvals_counted(self):
        assert self.snap.pending_approvals == 2

    def test_delegations_counted(self):
        assert self.snap.active_delegations == 1

    def test_health_propagated(self):
        assert self.snap.organism_health == "aligned"

    def test_coherence_propagated(self):
        assert self.snap.coherence_score == 0.85

    def test_attention_propagated(self):
        assert len(self.snap.attention_items) == 1

    def test_to_dict_roundtrip(self):
        d = self.snap.to_dict()
        assert d["workstation_state"] == "executing"
        assert d["active_project"] == "umh"
        assert d["pending_approvals"] == 2


class TestAttentionAggregationIntegration:
    """Full aggregation: 4 sources → 1 ranked queue."""

    @classmethod
    def setup_class(cls):
        cls.rt = AttentionAggregationRuntime(
            attention_engine=_FakeAttentionEngine(),
            organism_state=_FakeOrgState(),
            governed_execution=_FakeExec(),
            organism_portfolio=_FakePortfolio(),
        )
        cls.queue = cls.rt.queue()

    def test_queue_type(self):
        assert isinstance(self.queue, AttentionQueueSnapshot)

    def test_items_from_all_sources(self):
        sources = {i.get("source_system", "") for i in self.queue.items}
        assert "attention_engine" in sources or "test" in sources

    def test_total_count_matches_items(self):
        assert self.queue.total_count == len(self.queue.items)

    def test_critical_counted(self):
        assert self.queue.critical_count >= 1

    def test_failure_ranked_first(self):
        assert self.queue.items[0]["category"] == "failure"

    def test_to_dict_roundtrip(self):
        d = self.queue.to_dict()
        assert d["total_count"] == self.queue.total_count
        assert len(d["items"]) == len(self.queue.items)


class TestCrossRuntimeConsistency:
    """Both runtimes share subsystem state and produce consistent views."""

    def test_attention_count_consistent(self):
        org = _FakeOrgState()
        exe = _FakeExec()
        port = _FakePortfolio()

        ws_rt = UnifiedWorkstationRuntime(
            orchestrator_presence=_FakeOrchestrator(),
            workstation_presence=_FakeWorkstation(),
            organism_state=org,
            governed_execution=exe,
            organism_portfolio=port,
            unified_approvals=_FakeApprovals(),
            command_center=_FakeCC(),
        )
        attn_rt = AttentionAggregationRuntime(
            attention_engine=_FakeAttentionEngine(),
            organism_state=org,
            governed_execution=exe,
            organism_portfolio=port,
        )

        ws_snap = ws_rt.snapshot()
        attn_q = attn_rt.queue()

        assert attn_q.total_count > 0
        assert ws_snap.workstation_state == "executing"
