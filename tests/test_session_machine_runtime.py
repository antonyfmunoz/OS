"""Tests for SessionMachineRuntime — Campaign 19.2."""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.workstation.session_machine_runtime import (
    MachineSessionBinding,
    SessionMachineRuntime,
    SessionMachineSnapshot,
)


# ── Mock helpers ──────────────────────────────────────────────────────


@dataclass
class MockDevice:
    device_id: str = "srv1500858"
    display_name: str = "VPS"
    device_type: str = "vps"
    online: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "display_name": self.display_name,
            "device_type": self.device_type,
            "online": self.online,
        }


@dataclass
class MockSession:
    session_id: str = "sess-1"
    session_type: str = "desktop"
    status: str = "active"
    authority: str = "primary"
    device_id: str = "srv1500858"
    workspace: dict[str, str] = field(default_factory=lambda: {"repo": "OS", "branch": "main", "directory": "/opt/OS"})

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_type": self.session_type,
            "status": self.status,
            "authority": self.authority,
            "device_id": self.device_id,
            "workspace": self.workspace,
        }


@dataclass
class MockWorkspace:
    device: str = "srv1500858"
    repo: str = "OS"
    branch: str = "main"
    directory: str = "/opt/OS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "device": self.device,
            "repo": self.repo,
            "branch": self.branch,
            "directory": self.directory,
        }


@dataclass
class MockHandoff:
    handoff_id: str = "ho-1"
    source_session: str = "sess-1"
    target_session: str = "sess-2"
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "handoff_id": self.handoff_id,
            "source_session": self.source_session,
            "target_session": self.target_session,
            "status": self.status,
        }


def _empty_sessions() -> MagicMock:
    m = MagicMock()
    m.list_all_sessions.return_value = []
    m.list_active_sessions.return_value = []
    m.pending_handoffs.return_value = []
    m.list_pending_handoffs.return_value = []
    return m


def _empty_presence() -> MagicMock:
    m = MagicMock()
    m.list_devices.return_value = []
    m.online_devices.return_value = []
    return m


def _empty_workspace() -> MagicMock:
    m = MagicMock()
    m.detect_active_workspace.return_value = None
    return m


def _empty_continuity() -> MagicMock:
    m = MagicMock()
    m.recent_handoffs.return_value = []
    m.get_work_lineage.return_value = []
    return m


def _make_runtime(**kwargs: Any) -> SessionMachineRuntime:
    return SessionMachineRuntime(**kwargs)


def _make_empty_runtime(**kwargs: Any) -> SessionMachineRuntime:
    """Runtime with all deps mocked to return empty state."""
    defaults: dict[str, Any] = {
        "session_runtime": _empty_sessions(),
        "presence_runtime": _empty_presence(),
        "workspace_awareness": _empty_workspace(),
        "continuity_runtime": _empty_continuity(),
    }
    defaults.update(kwargs)
    return SessionMachineRuntime(**defaults)


# ── Snapshot ──────────────────────────────────────────────────────────


class TestSnapshot:
    def test_snapshot_empty_deps(self) -> None:
        rt = _make_empty_runtime()
        snap = rt.snapshot()
        assert isinstance(snap, SessionMachineSnapshot)
        assert snap.total_devices == 0
        assert snap.generated_at > 0

    def test_snapshot_to_dict_keys(self) -> None:
        rt = _make_empty_runtime()
        d = rt.snapshot().to_dict()
        expected = {
            "bindings", "total_devices", "online_devices",
            "total_sessions", "active_sessions",
            "primary_session", "active_workspaces",
            "pending_handoffs", "continuity_links", "generated_at",
        }
        assert set(d.keys()) == expected

    def test_snapshot_with_devices_and_sessions(self) -> None:
        presence = MagicMock()
        presence.list_devices.return_value = [MockDevice()]
        sessions = MagicMock()
        sessions.list_all_sessions.return_value = [MockSession()]
        sessions.pending_handoffs.return_value = []
        rt = _make_runtime(presence_runtime=presence, session_runtime=sessions)
        snap = rt.snapshot()
        assert snap.total_devices == 1
        assert snap.online_devices == 1
        assert snap.total_sessions == 1
        assert snap.active_sessions == 1
        assert snap.primary_session is not None


# ── Bindings ──────────────────────────────────────────────────────────


class TestBindings:
    def test_bindings_maps_sessions_to_devices(self) -> None:
        presence = MagicMock()
        presence.list_devices.return_value = [MockDevice()]
        sessions = MagicMock()
        sessions.list_all_sessions.return_value = [
            MockSession(),
            MockSession(session_id="sess-2", status="background", authority="secondary"),
        ]
        rt = _make_runtime(presence_runtime=presence, session_runtime=sessions)
        bindings = rt.bindings()
        assert len(bindings) == 1
        assert isinstance(bindings[0], MachineSessionBinding)
        assert bindings[0].total_sessions == 2
        assert bindings[0].active_sessions == 1
        assert bindings[0].device_display_name == "VPS"

    def test_bindings_creates_unknown_device_for_orphan_sessions(self) -> None:
        presence = MagicMock()
        presence.list_devices.return_value = []
        sessions = MagicMock()
        sessions.list_all_sessions.return_value = [MockSession(device_id="unknown-device")]
        rt = _make_runtime(presence_runtime=presence, session_runtime=sessions)
        bindings = rt.bindings()
        assert len(bindings) == 1
        assert bindings[0].device_id == "unknown-device"
        assert bindings[0].device_type == "unknown"

    def test_multi_device_bindings(self) -> None:
        presence = MagicMock()
        presence.list_devices.return_value = [
            MockDevice(),
            MockDevice(device_id="beast", display_name="Beast PC", device_type="windows"),
        ]
        sessions = MagicMock()
        sessions.list_all_sessions.return_value = [
            MockSession(),
            MockSession(session_id="s2", device_id="beast"),
        ]
        rt = _make_runtime(presence_runtime=presence, session_runtime=sessions)
        bindings = rt.bindings()
        assert len(bindings) == 2


# ── Primary session ──────────────────────────────────────────────────


class TestPrimarySession:
    def test_identifies_primary(self) -> None:
        sessions = MagicMock()
        sessions.list_all_sessions.return_value = [
            MockSession(authority="secondary", session_id="s1"),
            MockSession(authority="primary", session_id="s2"),
        ]
        rt = _make_runtime(session_runtime=sessions)
        primary = rt.primary_session()
        assert primary is not None
        assert primary["session_id"] == "s2"

    def test_falls_back_to_first_active(self) -> None:
        sessions = MagicMock()
        sessions.list_all_sessions.return_value = [
            MockSession(authority="secondary", status="active"),
        ]
        rt = _make_runtime(session_runtime=sessions)
        primary = rt.primary_session()
        assert primary is not None

    def test_none_when_no_sessions(self) -> None:
        rt = _make_empty_runtime()
        assert rt.primary_session() is None


# ── Workspaces ────────────────────────────────────────────────────────


class TestWorkspaces:
    def test_active_workspaces_from_sessions(self) -> None:
        sessions = MagicMock()
        sessions.list_all_sessions.return_value = [MockSession()]
        rt = _make_runtime(session_runtime=sessions)
        ws = rt.active_workspaces()
        assert len(ws) >= 1
        assert ws[0].get("repo") or ws[0].get("directory")

    def test_workspace_from_awareness(self) -> None:
        workspace = MagicMock()
        workspace.detect_active_workspace.return_value = MockWorkspace()
        rt = _make_runtime(workspace_awareness=workspace)
        ws = rt.active_workspaces()
        assert len(ws) == 1
        assert ws[0]["repo"] == "OS"


# ── Handoffs ──────────────────────────────────────────────────────────


class TestHandoffs:
    def test_pending_handoffs(self) -> None:
        sessions = MagicMock()
        sessions.pending_handoffs.return_value = [MockHandoff()]
        sessions.list_all_sessions.return_value = []
        rt = _make_runtime(session_runtime=sessions)
        handoffs = rt.pending_handoffs()
        assert len(handoffs) == 1

    def test_empty_when_no_handoffs(self) -> None:
        rt = _make_empty_runtime()
        assert rt.pending_handoffs() == []


# ── Device utilization ────────────────────────────────────────────────


class TestDeviceUtilization:
    def test_utilization_map(self) -> None:
        presence = MagicMock()
        presence.list_devices.return_value = [MockDevice()]
        sessions = MagicMock()
        sessions.list_all_sessions.return_value = [MockSession(), MockSession(session_id="s2", status="background")]
        rt = _make_runtime(presence_runtime=presence, session_runtime=sessions)
        util = rt.device_utilization()
        assert "srv1500858" in util
        assert util["srv1500858"]["total_sessions"] == 2


# ── Summary ──────────────────────────────────────────────────────────


class TestSummary:
    def test_summary_keys(self) -> None:
        rt = _make_empty_runtime()
        s = rt.summary()
        assert s["ok"] is True
        assert "total_devices" in s
        assert "active_sessions" in s
        assert "has_primary" in s


# ── Graceful degradation ─────────────────────────────────────────────


class TestGracefulDegradation:
    def test_empty_deps_produce_empty(self) -> None:
        rt = _make_empty_runtime()
        snap = rt.snapshot()
        assert snap.bindings == []
        assert snap.active_workspaces == []
        assert snap.pending_handoffs == []

    def test_exception_in_presence(self) -> None:
        presence = MagicMock()
        presence.list_devices.side_effect = RuntimeError("boom")
        rt = _make_runtime(presence_runtime=presence)
        snap = rt.snapshot()
        assert snap.total_devices == 0


# ── Type registration ─────────────────────────────────────────────────


class TestTypeRegistration:
    def test_types_registered(self) -> None:
        from substrate.canonical_types import lookup
        assert lookup("MachineSessionBinding") is not None
        assert lookup("SessionMachineSnapshot") is not None
        assert lookup("SessionMachineRuntime") is not None
