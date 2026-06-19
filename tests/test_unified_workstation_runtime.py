"""Tests for UnifiedWorkstationRuntime — Campaign 18.0."""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from substrate.workstation.unified_workstation_runtime import (
    UnifiedWorkstationRuntime,
    UnifiedWorkstationSnapshot,
    UnifiedWorkstationState,
)


# ── Fakes ──────────────────────────────────────────────────────────────


class _Snapshot:
    def __init__(self, d: dict):
        self._d = d

    def to_dict(self) -> dict:
        return self._d


class _FakeOrchestratorPresence:
    def __init__(self, **kw):
        self._data = {
            "mode": "listening",
            "active_project": "umh",
            "active_repo": "OS",
            "active_delegation_count": 0,
        }
        self._data.update(kw)

    def snapshot(self):
        return _Snapshot(self._data)


class _FakeWorkstationPresence:
    def __init__(self, **kw):
        self._data = {
            "active_panel": "commandcenter",
            "active_project": "",
            "active_repo": "",
        }
        self._data.update(kw)

    def snapshot(self):
        return _Snapshot(self._data)


class _FakeOrganismState:
    def __init__(self, mode: str = "idle", attention_items: list | None = None):
        self._mode = mode
        self._items = attention_items or []

    def snapshot(self):
        return _Snapshot({
            "mode": self._mode,
            "health": "healthy",
            "attention_items": self._items,
        })


class _FakeGovernedExecution:
    def __init__(self, state: str = "idle", blockers: list | None = None, pending: int = 0):
        self._state = state
        self._blockers = blockers or []
        self._pending = pending

    def assess(self):
        return _Snapshot({
            "state": self._state,
            "top_blockers": self._blockers,
            "pending_approval_count": self._pending,
        })


class _FakeOrganismPortfolio:
    def __init__(self, health: str = "aligned", score: float = 0.8):
        self._health = health
        self._score = score

    def snapshot(self):
        return _Snapshot({
            "organism_health": self._health,
            "coherence_score": self._score,
            "subsystem_health": [{"subsystem": "governance", "health": "healthy"}],
        })


class _FakeUnifiedApprovals:
    def __init__(self, pending: int = 0):
        self._pending = pending

    def snapshot(self):
        return _Snapshot({"pending_count": self._pending})


class _FakeCommandCenter:
    def snapshot(self):
        return _Snapshot({"sections": []})


def _runtime(**overrides) -> UnifiedWorkstationRuntime:
    defaults = {
        "orchestrator_presence": _FakeOrchestratorPresence(),
        "workstation_presence": _FakeWorkstationPresence(),
        "organism_state": _FakeOrganismState(),
        "governed_execution": _FakeGovernedExecution(),
        "organism_portfolio": _FakeOrganismPortfolio(),
        "unified_approvals": _FakeUnifiedApprovals(),
        "command_center": _FakeCommandCenter(),
    }
    defaults.update(overrides)
    return UnifiedWorkstationRuntime(**defaults)


# ── Enum Tests ──────────────────────────────────────────────────────


class TestUnifiedWorkstationStateEnum:
    def test_values(self):
        assert UnifiedWorkstationState.IDLE.value == "idle"
        assert UnifiedWorkstationState.BUILDING.value == "building"
        assert UnifiedWorkstationState.GOVERNING.value == "governing"
        assert UnifiedWorkstationState.EXECUTING.value == "executing"
        assert UnifiedWorkstationState.MONITORING.value == "monitoring"
        assert UnifiedWorkstationState.DEGRADED.value == "degraded"

    def test_count(self):
        assert len(UnifiedWorkstationState) == 6


# ── Snapshot Tests ──────────────────────────────────────────────────


class TestUnifiedWorkstationSnapshot:
    def test_to_dict_fields(self):
        snap = UnifiedWorkstationSnapshot()
        d = snap.to_dict()
        expected = {
            "workstation_state", "organism_mode", "execution_state",
            "presence_mode", "active_project", "active_repo", "active_panel",
            "pending_approvals", "active_delegations", "active_risks",
            "attention_items", "subsystem_health", "organism_health",
            "coherence_score", "generated_at",
        }
        assert expected.issubset(set(d.keys()))

    def test_defaults(self):
        snap = UnifiedWorkstationSnapshot()
        assert snap.workstation_state == "idle"
        assert snap.organism_mode == "idle"
        assert snap.pending_approvals == 0


# ── State Derivation Tests ──────────────────────────────────────────


class TestStateDerivedCorrectly:
    def test_idle_when_nothing_happening(self):
        rt = _runtime()
        assert rt.mode() == "idle"

    def test_executing_when_execution_active(self):
        rt = _runtime(governed_execution=_FakeGovernedExecution(state="executing"))
        assert rt.mode() == "executing"

    def test_governing_when_organism_governing(self):
        rt = _runtime(organism_state=_FakeOrganismState(mode="governing"))
        assert rt.mode() == "governing"

    def test_building_when_assessing(self):
        rt = _runtime(governed_execution=_FakeGovernedExecution(state="assessing"))
        assert rt.mode() == "building"

    def test_building_when_governed(self):
        rt = _runtime(governed_execution=_FakeGovernedExecution(state="governed"))
        assert rt.mode() == "building"

    def test_monitoring_when_approvals_pending(self):
        rt = _runtime(unified_approvals=_FakeUnifiedApprovals(pending=3))
        assert rt.mode() == "monitoring"

    def test_monitoring_when_delegations_active(self):
        rt = _runtime(
            orchestrator_presence=_FakeOrchestratorPresence(active_delegation_count=2)
        )
        assert rt.mode() == "monitoring"

    def test_degraded_when_organism_degraded(self):
        rt = _runtime(organism_state=_FakeOrganismState(mode="degraded"))
        assert rt.mode() == "degraded"

    def test_degraded_when_health_critical(self):
        rt = _runtime(organism_portfolio=_FakeOrganismPortfolio(health="critical"))
        assert rt.mode() == "degraded"

    def test_degraded_when_health_fragmented(self):
        rt = _runtime(organism_portfolio=_FakeOrganismPortfolio(health="fragmented"))
        assert rt.mode() == "degraded"

    def test_executing_beats_governing(self):
        rt = _runtime(
            organism_state=_FakeOrganismState(mode="governing"),
            governed_execution=_FakeGovernedExecution(state="executing"),
        )
        assert rt.mode() == "executing"

    def test_degraded_beats_executing(self):
        rt = _runtime(
            organism_state=_FakeOrganismState(mode="degraded"),
            governed_execution=_FakeGovernedExecution(state="executing"),
        )
        assert rt.mode() == "degraded"


# ── Snapshot Composition Tests ──────────────────────────────────────


class TestSnapshotComposition:
    def test_snapshot_returns_snapshot_type(self):
        rt = _runtime()
        snap = rt.snapshot()
        assert isinstance(snap, UnifiedWorkstationSnapshot)

    def test_snapshot_includes_project(self):
        rt = _runtime(
            orchestrator_presence=_FakeOrchestratorPresence(active_project="umh")
        )
        snap = rt.snapshot()
        assert snap.active_project == "umh"

    def test_snapshot_includes_panel(self):
        rt = _runtime(
            workstation_presence=_FakeWorkstationPresence(active_panel="editor")
        )
        snap = rt.snapshot()
        assert snap.active_panel == "editor"

    def test_snapshot_includes_attention(self):
        items = [{"title": "test attention"}]
        rt = _runtime(organism_state=_FakeOrganismState(attention_items=items))
        snap = rt.snapshot()
        assert len(snap.attention_items) == 1

    def test_snapshot_includes_subsystem_health(self):
        rt = _runtime()
        snap = rt.snapshot()
        assert len(snap.subsystem_health) > 0

    def test_snapshot_generated_at_recent(self):
        rt = _runtime()
        snap = rt.snapshot()
        assert snap.generated_at > time.time() - 5


# ── API Tests ──────────────────────────────────────────────────────


class TestPublicAPI:
    def test_attention_returns_list(self):
        rt = _runtime()
        assert isinstance(rt.attention(), list)

    def test_risks_returns_list(self):
        rt = _runtime()
        assert isinstance(rt.risks(), list)

    def test_summary_returns_dict(self):
        rt = _runtime()
        s = rt.summary()
        assert "state" in s
        assert "organism_mode" in s
        assert "pending_approvals" in s


# ── Graceful Degradation Tests ──────────────────────────────────────


class _BrokenSubsystem:
    """Subsystem that always raises — simulates unavailable dep."""

    def snapshot(self):
        raise RuntimeError("subsystem offline")

    def assess(self):
        raise RuntimeError("subsystem offline")


class TestGracefulDegradation:
    def test_broken_deps_produce_idle_snapshot(self):
        broken = _BrokenSubsystem()
        rt = UnifiedWorkstationRuntime(
            orchestrator_presence=broken,
            workstation_presence=broken,
            organism_state=broken,
            governed_execution=broken,
            organism_portfolio=broken,
            unified_approvals=broken,
            command_center=broken,
        )
        snap = rt.snapshot()
        assert snap.workstation_state == "idle"

    def test_partial_deps_still_works(self):
        broken = _BrokenSubsystem()
        rt = UnifiedWorkstationRuntime(
            orchestrator_presence=_FakeOrchestratorPresence(),
            workstation_presence=broken,
            organism_state=broken,
            governed_execution=broken,
            organism_portfolio=broken,
            unified_approvals=broken,
            command_center=broken,
        )
        snap = rt.snapshot()
        assert snap.active_project == "umh"
