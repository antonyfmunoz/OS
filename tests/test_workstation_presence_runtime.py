"""Tests for Campaign 17.2 — WorkstationPresenceRuntime.

Operator footprint: device, panel, project, recent actions.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from typing import Any
from unittest.mock import MagicMock

from substrate.workstation.workstation_presence_runtime import (
    WorkstationPresenceRuntime,
    WorkstationPresenceSnapshot,
)


# ── Shared fakes ─────────────────────────────────────────────────────


class _FakeDeviceAwareness:
    def __init__(self, device: str = "srv1500858") -> None:
        self._device = device

    def detect_active_device(self) -> str:
        return self._device


class _FakeWorkspaceAwareness:
    def __init__(self, workspace: dict[str, Any] | None = None) -> None:
        self._workspace = workspace or {"repo": "OS", "project": "UMH"}

    def snapshot(self) -> dict[str, Any]:
        return self._workspace


class _FakeContinuityEngine:
    def __init__(self, state: str = "active", checkpoints: int = 3) -> None:
        self._state = state
        self._checkpoints = checkpoints

    def state(self) -> MagicMock:
        m = MagicMock()
        m.value = self._state
        return m

    def checkpoints(self) -> list[dict]:
        return [{"id": f"cp-{i}"} for i in range(self._checkpoints)]


class _FakeApprovals:
    def __init__(self, decisions: list[dict] | None = None) -> None:
        self._decisions = decisions or []

    def recent_decisions(self, limit: int = 1) -> list[dict]:
        return self._decisions[:limit]


class _FakeDevicePresence:
    def __init__(self, sessions: list[dict] | None = None) -> None:
        self._sessions = sessions or []

    def active_sessions(self) -> list[dict]:
        return self._sessions


# ── Factory ──────────────────────────────────────────────────────────


def _wpr(**overrides: Any) -> WorkstationPresenceRuntime:
    defaults: dict[str, Any] = {
        "device_awareness": _FakeDeviceAwareness(),
        "workspace_awareness": _FakeWorkspaceAwareness(),
        "continuity_engine": _FakeContinuityEngine(),
        "unified_approvals": _FakeApprovals(),
        "device_presence": _FakeDevicePresence(),
    }
    defaults.update(overrides)
    return WorkstationPresenceRuntime(**defaults)


# ── Snapshot tests ───────────────────────────────────────────────────


class TestWorkstationPresenceSnapshot:
    def test_snapshot_returns_all_fields(self) -> None:
        rt = _wpr()
        snap = rt.snapshot()
        assert isinstance(snap, WorkstationPresenceSnapshot)
        d = snap.to_dict()
        expected = {
            "active_device", "active_sessions", "active_panel", "active_project",
            "active_repo", "last_command", "last_approval", "continuity_state",
            "checkpoint_count", "generated_at",
        }
        assert expected.issubset(set(d.keys()))

    def test_snapshot_pulls_device(self) -> None:
        rt = _wpr(device_awareness=_FakeDeviceAwareness("desktop-lvguiq9"))
        snap = rt.snapshot()
        assert snap.active_device == "desktop-lvguiq9"

    def test_snapshot_pulls_continuity(self) -> None:
        rt = _wpr(continuity_engine=_FakeContinuityEngine("resuming", 5))
        snap = rt.snapshot()
        assert snap.continuity_state == "resuming"
        assert snap.checkpoint_count == 5


# ── Panel tracking tests ─────────────────────────────────────────────


class TestPanelTracking:
    def test_update_panel_persists(self) -> None:
        rt = _wpr()
        rt.update_panel("commandcenter")
        snap = rt.snapshot()
        assert snap.active_panel == "commandcenter"

    def test_panel_starts_empty(self) -> None:
        rt = _wpr()
        assert rt.snapshot().active_panel == ""


# ── Device override tests ────────────────────────────────────────────


class TestDeviceOverride:
    def test_update_device_overrides(self) -> None:
        rt = _wpr(device_awareness=_FakeDeviceAwareness("srv1500858"))
        rt.update_device("desktop-lvguiq9")
        assert rt.snapshot().active_device == "desktop-lvguiq9"


# ── Command tracking tests ───────────────────────────────────────────


class TestCommandTracking:
    def test_record_command_persists(self) -> None:
        rt = _wpr()
        rt.record_command({"type": "navigate", "target": "agents"})
        cmd = rt.last_command()
        assert cmd["type"] == "navigate"
        assert "recorded_at" in cmd

    def test_last_command_empty_initially(self) -> None:
        rt = _wpr()
        assert rt.last_command() == {}


# ── Approval tracking tests ──────────────────────────────────────────


class TestApprovalTracking:
    def test_last_approval_returns_recent(self) -> None:
        rt = _wpr(unified_approvals=_FakeApprovals(
            decisions=[{"approval_id": "a-1", "action": "approved"}]
        ))
        approval = rt.last_approval()
        assert approval["approval_id"] == "a-1"

    def test_last_approval_empty_when_none(self) -> None:
        rt = _wpr(unified_approvals=_FakeApprovals(decisions=[]))
        assert rt.last_approval() == {}


# ── Session tracking tests ───────────────────────────────────────────


class TestSessionTracking:
    def test_active_sessions_propagated(self) -> None:
        sessions = [
            {"session_id": "s-1", "device_id": "srv1500858"},
            {"session_id": "s-2", "device_id": "desktop-lvguiq9"},
        ]
        rt = _wpr(device_presence=_FakeDevicePresence(sessions))
        snap = rt.snapshot()
        assert len(snap.active_sessions) == 2


# ── Summary tests ────────────────────────────────────────────────────


class TestPresenceSummary:
    def test_summary_returns_dict(self) -> None:
        rt = _wpr()
        s = rt.summary()
        assert isinstance(s, dict)
        assert "active_device" in s
        assert "active_panel" in s
        assert "continuity_state" in s

    def test_summary_reflects_recent_command(self) -> None:
        rt = _wpr()
        assert s["has_recent_command"] is False if (s := rt.summary()) else True
        rt.record_command({"type": "test"})
        s2 = rt.summary()
        assert s2["has_recent_command"] is True


# ── Context update tests ─────────────────────────────────────────────


class TestContextUpdate:
    def test_update_context_affects_snapshot(self) -> None:
        rt = _wpr()
        rt.update_context({"project": "CreatorOS", "repo": "creator-os"})
        snap = rt.snapshot()
        assert snap.active_project == "CreatorOS"
        assert snap.active_repo == "creator-os"
