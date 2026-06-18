"""Tests for Campaign 17.0 — OrchestratorPresenceRuntime.

Mode classification, context delegation, snapshot serialization.
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from typing import Any
from unittest.mock import MagicMock

from substrate.workstation.orchestrator_presence_runtime import (
    OrchestratorPresenceRuntime,
    PresenceMode,
    OrchestratorPresenceSnapshot,
)


# ── Shared fakes ─────────────────────────────────────────────────────


class _FakeOrchestratorAwareness:
    def __init__(self, ctx: dict[str, Any] | None = None) -> None:
        self._ctx = ctx or {}

    def context(self) -> MagicMock:
        m = MagicMock()
        m.to_dict.return_value = self._ctx
        return m


class _FakeOrganismState:
    def __init__(self, mode: str = "idle", degraded: bool = False) -> None:
        self._mode = mode
        self._degraded = degraded

    def mode(self) -> MagicMock:
        m = MagicMock()
        m.value = self._mode
        return m

    def is_degraded(self) -> bool:
        return self._degraded


class _FakeGovernedExecution:
    def __init__(self, state: str = "idle") -> None:
        self._state = state

    def state(self) -> MagicMock:
        m = MagicMock()
        m.value = self._state
        return m


class _FakeContextResolution:
    def __init__(self, resolved: dict[str, Any] | None = None) -> None:
        self._resolved = resolved or {"project_name": "test-project"}

    def resolve(self, text: str) -> MagicMock:
        m = MagicMock()
        result = dict(self._resolved)
        result["query"] = text
        m.to_dict.return_value = result
        return m


class _FakeWorkspaceAwareness:
    def __init__(self, workspace: dict[str, Any] | None = None) -> None:
        self._workspace = workspace or {}

    def snapshot(self) -> dict[str, Any]:
        return self._workspace


class _FakeDeviceAwareness:
    def __init__(self, device: str = "srv1500858") -> None:
        self._device = device

    def detect_active_device(self) -> str:
        return self._device


class _FakeApprovals:
    def __init__(self, pending_count: int = 0) -> None:
        self._pending = [{"approval_id": f"a-{i}"} for i in range(pending_count)]

    def pending(self) -> list[dict]:
        return self._pending


class _FakeDelegation:
    def __init__(self, delegatable: int = 0) -> None:
        self._delegatable = delegatable

    def snapshot(self) -> MagicMock:
        m = MagicMock()
        m.to_dict.return_value = {
            "total_assessed": 10,
            "delegatable_count": self._delegatable,
        }
        return m


# ── Factory ──────────────────────────────────────────────────────────


def _opr(**overrides: Any) -> OrchestratorPresenceRuntime:
    defaults: dict[str, Any] = {
        "orchestrator_awareness": _FakeOrchestratorAwareness(),
        "organism_state": _FakeOrganismState(),
        "governed_execution": _FakeGovernedExecution(),
        "context_resolution": _FakeContextResolution(),
        "workspace_awareness": _FakeWorkspaceAwareness(),
        "device_awareness": _FakeDeviceAwareness(),
        "unified_approvals": _FakeApprovals(),
        "delegation_readiness": _FakeDelegation(),
    }
    defaults.update(overrides)
    return OrchestratorPresenceRuntime(**defaults)


# ── Mode classification tests ────────────────────────────────────────


class TestPresenceModeClassification:
    def test_idle_is_listening(self) -> None:
        rt = _opr()
        assert rt.mode() == PresenceMode.LISTENING

    def test_degraded_overrides_all(self) -> None:
        rt = _opr(organism_state=_FakeOrganismState(degraded=True))
        assert rt.mode() == PresenceMode.DEGRADED

    def test_executing_is_monitoring(self) -> None:
        rt = _opr(governed_execution=_FakeGovernedExecution(state="executing"))
        assert rt.mode() == PresenceMode.MONITORING

    def test_pending_approvals_is_waiting_approval(self) -> None:
        rt = _opr(unified_approvals=_FakeApprovals(pending_count=3))
        assert rt.mode() == PresenceMode.WAITING_APPROVAL

    def test_active_delegations_is_planning(self) -> None:
        rt = _opr(delegation_readiness=_FakeDelegation(delegatable=5))
        assert rt.mode() == PresenceMode.PLANNING

    def test_recent_resolution_is_clarifying(self) -> None:
        rt = _opr(context_resolution=_FakeContextResolution())
        rt.interpret("Use Clerk for auth")
        assert rt.mode() == PresenceMode.CLARIFYING

    def test_degraded_overrides_monitoring(self) -> None:
        rt = _opr(
            organism_state=_FakeOrganismState(degraded=True),
            governed_execution=_FakeGovernedExecution(state="executing"),
        )
        assert rt.mode() == PresenceMode.DEGRADED

    def test_monitoring_overrides_waiting_approval(self) -> None:
        rt = _opr(
            governed_execution=_FakeGovernedExecution(state="executing"),
            unified_approvals=_FakeApprovals(pending_count=2),
        )
        assert rt.mode() == PresenceMode.MONITORING


# ── Interpret tests ──────────────────────────────────────────────────


class TestInterpret:
    def test_interpret_delegates_to_context_resolution(self) -> None:
        rt = _opr(context_resolution=_FakeContextResolution({"project_name": "CreatorOS"}))
        result = rt.interpret("Use Clerk for CreatorOS auth")
        assert result["project_name"] == "CreatorOS"
        assert result["query"] == "Use Clerk for CreatorOS auth"

    def test_interpret_returns_dict(self) -> None:
        rt = _opr()
        result = rt.interpret("test query")
        assert isinstance(result, dict)


# ── Snapshot tests ───────────────────────────────────────────────────


class TestPresenceSnapshot:
    def test_snapshot_returns_all_fields(self) -> None:
        rt = _opr(device_awareness=_FakeDeviceAwareness("desktop-lvguiq9"))
        snap = rt.snapshot()
        assert isinstance(snap, OrchestratorPresenceSnapshot)
        d = snap.to_dict()
        expected = {
            "mode", "active_device", "active_panel", "active_project",
            "active_repo", "active_directory", "pending_approval_count",
            "active_delegation_count", "organism_mode", "execution_state",
            "context_summary", "generated_at",
        }
        assert expected.issubset(set(d.keys()))
        assert d["active_device"] == "desktop-lvguiq9"

    def test_snapshot_mode_reflects_state(self) -> None:
        rt = _opr(unified_approvals=_FakeApprovals(pending_count=2))
        snap = rt.snapshot()
        assert snap.mode == "waiting_approval"
        assert snap.pending_approval_count == 2


# ── Summary tests ────────────────────────────────────────────────────


class TestPresenceSummary:
    def test_summary_returns_dict(self) -> None:
        rt = _opr()
        s = rt.summary()
        assert isinstance(s, dict)
        assert s["mode"] == "listening"
        assert "active_device" in s


# ── API delegation tests ────────────────────────────────────────────


class TestAPIAccessors:
    def test_active_device(self) -> None:
        rt = _opr(device_awareness=_FakeDeviceAwareness("srv1500858"))
        assert rt.active_device() == "srv1500858"

    def test_pending_approvals_list(self) -> None:
        rt = _opr(unified_approvals=_FakeApprovals(pending_count=3))
        approvals = rt.pending_approvals()
        assert len(approvals) == 3
        assert all(isinstance(a, dict) for a in approvals)

    def test_context_delegates_to_awareness(self) -> None:
        ctx = {"active_project": "UMH", "active_repo": "OS"}
        rt = _opr(orchestrator_awareness=_FakeOrchestratorAwareness(ctx))
        result = rt.context()
        assert result["active_project"] == "UMH"
