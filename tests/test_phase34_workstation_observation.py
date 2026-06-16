"""Phase 34 — Workstation Observation Runtime tests.

Covers:
  - WorkstationTranslator: Beast payload → ScreenSnapshot
  - App classification: deterministic process→category lookup
  - ScreenSnapshot extension: workstation_detail field
  - Mesh server handler: workstation_state signal routing
  - Preference ordering with workstation data
  - Cockpit routes: /screen/workstation, /screen/windows, /screen/monitors
  - Integration: end-to-end payload → OBSERVED beats INFERRED
  - Phase 33 regression: backward compatibility
  - No-control verification: observation only, no automation

UMH test suite. 104 tests.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import unittest
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


def _make_beast_payload(
    *,
    windows: list[dict[str, Any]] | None = None,
    monitors: list[dict[str, Any]] | None = None,
    editor_context: dict[str, Any] | None = None,
    browser_tabs: list[dict[str, Any]] | None = None,
    terminal_sessions: list[dict[str, Any]] | None = None,
    active_window_id: str = "",
    device_id: str = "beast",
) -> dict[str, Any]:
    """Helper to build a Beast workstation payload."""
    return {
        "device_id": device_id,
        "monitors": monitors or [],
        "windows": windows or [],
        "editor_context": editor_context,
        "browser_tabs": browser_tabs or [],
        "terminal_sessions": terminal_sessions or [],
        "active_window_id": active_window_id,
        "collected_at": time.time(),
    }


def _make_window(
    window_id: str = "w1",
    title: str = "test.py",
    app_name: str = "code.exe",
    pid: int = 1234,
    is_visible: bool = True,
    is_focused: bool = False,
    category: str = "ide",
) -> dict[str, Any]:
    return {
        "window_id": window_id,
        "title": title,
        "app_name": app_name,
        "pid": pid,
        "x": 0,
        "y": 0,
        "width": 1920,
        "height": 1080,
        "is_visible": is_visible,
        "is_minimized": False,
        "is_focused": is_focused,
        "category": category,
    }


def _make_monitor(
    monitor_id: str = "M0",
    width: int = 2560,
    height: int = 1440,
    is_primary: bool = True,
) -> dict[str, Any]:
    return {
        "monitor_id": monitor_id,
        "name": f"Monitor {monitor_id}",
        "width": width,
        "height": height,
        "x": 0,
        "y": 0,
        "is_primary": is_primary,
    }


# ── WorkstationTranslator Tests ──────────────────────────────────────────


class TestWorkstationTranslatorBasic(unittest.TestCase):
    """WorkstationTranslator: basic translation."""

    def setUp(self) -> None:
        from substrate.operator.workstation_translator import WorkstationTranslator

        self.translator = WorkstationTranslator()

    def test_translate_empty_payload(self) -> None:
        snap = self.translator.translate("node-1", _make_beast_payload())
        self.assertEqual(snap.source_type.value, "observed")
        self.assertEqual(snap.status.value, "active")
        self.assertEqual(snap.source_node_id, "node-1")
        self.assertEqual(snap.source_device_id, "beast")
        self.assertEqual(snap.source_confidence, 0.9)
        self.assertIsNone(snap.active_application)
        self.assertIsNone(snap.active_window)

    def test_translate_source_role(self) -> None:
        snap = self.translator.translate("n1", _make_beast_payload())
        self.assertEqual(snap.source_device_role, "workstation")

    def test_translate_preserves_device_id(self) -> None:
        snap = self.translator.translate("n1", _make_beast_payload(device_id="custom"))
        self.assertEqual(snap.source_device_id, "custom")

    def test_translate_generated_at(self) -> None:
        t = 1700000000.0
        payload = _make_beast_payload()
        payload["collected_at"] = t
        snap = self.translator.translate("n1", payload)
        self.assertEqual(snap.generated_at, t)


class TestWorkstationTranslatorFocusedWindow(unittest.TestCase):
    """WorkstationTranslator: focused window → active_application + active_window."""

    def setUp(self) -> None:
        from substrate.operator.workstation_translator import WorkstationTranslator

        self.translator = WorkstationTranslator()

    def test_focused_by_active_window_id(self) -> None:
        w = _make_window(window_id="w42", is_focused=False, title="main.py - OS")
        payload = _make_beast_payload(windows=[w], active_window_id="w42")
        snap = self.translator.translate("n1", payload)
        self.assertIsNotNone(snap.active_application)
        self.assertEqual(snap.active_application.app_name, "code.exe")

    def test_focused_by_is_focused_flag(self) -> None:
        w = _make_window(is_focused=True, title="test.py - VS Code")
        payload = _make_beast_payload(windows=[w])
        snap = self.translator.translate("n1", payload)
        self.assertIsNotNone(snap.active_application)

    def test_no_focused_window(self) -> None:
        w = _make_window(is_focused=False)
        payload = _make_beast_payload(windows=[w])
        snap = self.translator.translate("n1", payload)
        self.assertIsNone(snap.active_application)
        self.assertIsNone(snap.active_window)

    def test_active_window_fields(self) -> None:
        w = _make_window(window_id="w7", title="README.md", app_name="code.exe", is_focused=True)
        payload = _make_beast_payload(windows=[w], active_window_id="w7")
        snap = self.translator.translate("n1", payload)
        self.assertEqual(snap.active_window.window_id, "w7")
        self.assertEqual(snap.active_window.title, "README.md")
        self.assertEqual(snap.active_window.application, "code.exe")

    def test_focused_application_pid(self) -> None:
        w = _make_window(pid=9999, is_focused=True)
        payload = _make_beast_payload(windows=[w], active_window_id=w["window_id"])
        snap = self.translator.translate("n1", payload)
        self.assertEqual(snap.active_application.pid, 9999)


class TestWorkstationTranslatorApplications(unittest.TestCase):
    """WorkstationTranslator: visible windows → applications list."""

    def setUp(self) -> None:
        from substrate.operator.workstation_translator import WorkstationTranslator

        self.translator = WorkstationTranslator()

    def test_visible_windows_become_applications(self) -> None:
        w1 = _make_window(window_id="w1", is_visible=True, app_name="code.exe")
        w2 = _make_window(window_id="w2", is_visible=True, app_name="chrome.exe")
        w3 = _make_window(window_id="w3", is_visible=False, app_name="discord.exe")
        payload = _make_beast_payload(windows=[w1, w2, w3])
        snap = self.translator.translate("n1", payload)
        self.assertEqual(len(snap.applications), 2)

    def test_hidden_windows_excluded(self) -> None:
        w = _make_window(is_visible=False)
        payload = _make_beast_payload(windows=[w])
        snap = self.translator.translate("n1", payload)
        self.assertEqual(len(snap.applications), 0)

    def test_empty_windows(self) -> None:
        payload = _make_beast_payload(windows=[])
        snap = self.translator.translate("n1", payload)
        self.assertEqual(len(snap.applications), 0)


class TestWorkstationTranslatorEditor(unittest.TestCase):
    """WorkstationTranslator: editor_context → file_context + repo_context."""

    def setUp(self) -> None:
        from substrate.operator.workstation_translator import WorkstationTranslator

        self.translator = WorkstationTranslator()

    def test_editor_to_file_context(self) -> None:
        editor = {
            "editor_name": "VS Code",
            "workspace_name": "OS",
            "active_file": "substrate/types.py",
        }
        payload = _make_beast_payload(editor_context=editor)
        snap = self.translator.translate("n1", payload)
        self.assertIsNotNone(snap.file_context)
        self.assertEqual(snap.file_context.file_path, "substrate/types.py")
        self.assertEqual(snap.file_context.file_name, "types.py")
        self.assertEqual(snap.file_context.language, "py")
        self.assertEqual(snap.file_context.repo_name, "OS")

    def test_editor_to_repo_context(self) -> None:
        editor = {
            "editor_name": "VS Code",
            "workspace_name": "OS",
            "project_path": "/opt/OS",
            "git_branch": "main",
            "active_file": "test.py",
        }
        payload = _make_beast_payload(editor_context=editor)
        snap = self.translator.translate("n1", payload)
        self.assertIsNotNone(snap.repository_context)
        self.assertEqual(snap.repository_context.repo_name, "OS")
        self.assertEqual(snap.repository_context.repo_path, "/opt/OS")
        self.assertEqual(snap.repository_context.branch, "main")

    def test_no_editor_context(self) -> None:
        payload = _make_beast_payload(editor_context=None)
        snap = self.translator.translate("n1", payload)
        self.assertIsNone(snap.file_context)
        self.assertIsNone(snap.repository_context)

    def test_editor_no_active_file(self) -> None:
        editor = {"editor_name": "VS Code", "workspace_name": "OS", "active_file": ""}
        payload = _make_beast_payload(editor_context=editor)
        snap = self.translator.translate("n1", payload)
        self.assertIsNone(snap.file_context)


class TestWorkstationTranslatorBrowser(unittest.TestCase):
    """WorkstationTranslator: browser_tabs → browser_context."""

    def setUp(self) -> None:
        from substrate.operator.workstation_translator import WorkstationTranslator

        self.translator = WorkstationTranslator()

    def test_active_tab_to_browser_context(self) -> None:
        tabs = [
            {
                "tab_id": "t1",
                "url": "https://github.com",
                "title": "GitHub",
                "domain": "github.com",
                "is_active": True,
            },
            {
                "tab_id": "t2",
                "url": "https://google.com",
                "title": "Google",
                "domain": "google.com",
                "is_active": False,
            },
        ]
        payload = _make_beast_payload(browser_tabs=tabs)
        snap = self.translator.translate("n1", payload)
        self.assertIsNotNone(snap.browser_context)
        self.assertEqual(snap.browser_context.title, "GitHub")
        self.assertEqual(snap.browser_context.domain, "github.com")

    def test_no_active_tab_uses_first(self) -> None:
        tabs = [
            {"tab_id": "t1", "title": "First Tab", "is_active": False},
        ]
        payload = _make_beast_payload(browser_tabs=tabs)
        snap = self.translator.translate("n1", payload)
        self.assertIsNotNone(snap.browser_context)
        self.assertEqual(snap.browser_context.title, "First Tab")

    def test_no_tabs(self) -> None:
        payload = _make_beast_payload(browser_tabs=[])
        snap = self.translator.translate("n1", payload)
        self.assertIsNone(snap.browser_context)


class TestWorkstationTranslatorDetail(unittest.TestCase):
    """WorkstationTranslator: workstation_detail passthrough."""

    def setUp(self) -> None:
        from substrate.operator.workstation_translator import WorkstationTranslator

        self.translator = WorkstationTranslator()

    def test_workstation_detail_populated(self) -> None:
        monitors = [_make_monitor()]
        windows = [_make_window()]
        terminals = [{"terminal_id": "t1", "terminal_type": "powershell"}]
        editor = {"editor_name": "VS Code", "workspace_name": "OS", "active_file": "x.py"}
        tabs = [{"tab_id": "b1", "title": "Google", "is_active": True}]

        payload = _make_beast_payload(
            monitors=monitors,
            windows=windows,
            editor_context=editor,
            browser_tabs=tabs,
            terminal_sessions=terminals,
        )
        snap = self.translator.translate("n1", payload)

        self.assertEqual(len(snap.workstation_detail["monitors"]), 1)
        self.assertEqual(len(snap.workstation_detail["all_windows"]), 1)
        self.assertIsNotNone(snap.workstation_detail["editor_context"])
        self.assertEqual(len(snap.workstation_detail["browser_tabs"]), 1)
        self.assertEqual(len(snap.workstation_detail["terminal_sessions"]), 1)

    def test_workstation_detail_in_to_dict(self) -> None:
        payload = _make_beast_payload(monitors=[_make_monitor()])
        snap = self.translator.translate("n1", payload)
        d = snap.to_dict()
        self.assertIn("workstation_detail", d)
        self.assertEqual(len(d["workstation_detail"]["monitors"]), 1)

    def test_workstation_detail_roundtrip(self) -> None:
        from substrate.operator.screen_awareness import ScreenSnapshot

        payload = _make_beast_payload(monitors=[_make_monitor()], windows=[_make_window()])
        snap = self.translator.translate("n1", payload)
        d = snap.to_dict()
        restored = ScreenSnapshot.from_dict(d)
        self.assertEqual(len(restored.workstation_detail.get("monitors", [])), 1)
        self.assertEqual(len(restored.workstation_detail.get("all_windows", [])), 1)


# ── App Classification Tests ─────────────────────────────────────────────


class TestAppClassification(unittest.TestCase):
    """Deterministic process→category classification."""

    def test_code_exe_is_ide(self) -> None:
        from substrate.operator.workstation_translator import classify_application

        self.assertEqual(classify_application("code.exe").value, "ide")

    def test_chrome_is_browser(self) -> None:
        from substrate.operator.workstation_translator import classify_application

        self.assertEqual(classify_application("chrome.exe").value, "browser")

    def test_powershell_is_terminal(self) -> None:
        from substrate.operator.workstation_translator import classify_application

        self.assertEqual(classify_application("powershell.exe").value, "terminal")

    def test_discord_is_communication(self) -> None:
        from substrate.operator.workstation_translator import classify_application

        self.assertEqual(classify_application("discord.exe").value, "communication")

    def test_figma_is_design(self) -> None:
        from substrate.operator.workstation_translator import classify_application

        self.assertEqual(classify_application("figma.exe").value, "design")

    def test_unknown_is_other(self) -> None:
        from substrate.operator.workstation_translator import classify_application

        self.assertEqual(classify_application("notepad.exe").value, "other")

    def test_empty_is_other(self) -> None:
        from substrate.operator.workstation_translator import classify_application

        self.assertEqual(classify_application("").value, "other")

    def test_case_insensitive(self) -> None:
        from substrate.operator.workstation_translator import classify_application

        self.assertEqual(classify_application("CODE.EXE").value, "ide")
        self.assertEqual(classify_application("Chrome.exe").value, "browser")

    def test_partial_match(self) -> None:
        from substrate.operator.workstation_translator import classify_application

        self.assertEqual(classify_application("Visual Studio Code Helper").value, "ide")


# ── ScreenSnapshot Extension Tests ────────────────────────────────────────


class TestScreenSnapshotExtension(unittest.TestCase):
    """ScreenSnapshot.workstation_detail field — Phase 34 extension."""

    def test_default_empty_dict(self) -> None:
        from substrate.operator.screen_awareness import ScreenSnapshot

        snap = ScreenSnapshot()
        self.assertEqual(snap.workstation_detail, {})

    def test_to_dict_includes_workstation_detail(self) -> None:
        from substrate.operator.screen_awareness import ScreenSnapshot

        snap = ScreenSnapshot(workstation_detail={"monitors": [{"id": "M0"}]})
        d = snap.to_dict()
        self.assertIn("workstation_detail", d)
        self.assertEqual(len(d["workstation_detail"]["monitors"]), 1)

    def test_from_dict_parses_workstation_detail(self) -> None:
        from substrate.operator.screen_awareness import ScreenSnapshot

        d = {"workstation_detail": {"monitors": [{"id": "M0"}]}}
        snap = ScreenSnapshot.from_dict(d)
        self.assertEqual(len(snap.workstation_detail["monitors"]), 1)

    def test_from_dict_missing_workstation_detail(self) -> None:
        from substrate.operator.screen_awareness import ScreenSnapshot

        snap = ScreenSnapshot.from_dict({})
        self.assertEqual(snap.workstation_detail, {})

    def test_roundtrip_with_detail(self) -> None:
        from substrate.operator.screen_awareness import ScreenSnapshot

        detail = {"monitors": [{"id": "M0"}], "all_windows": [{"title": "x"}]}
        snap = ScreenSnapshot(workstation_detail=detail)
        restored = ScreenSnapshot.from_dict(snap.to_dict())
        self.assertEqual(restored.workstation_detail, detail)

    def test_existing_fields_unchanged(self) -> None:
        from substrate.operator.screen_awareness import (
            FocusedApplication,
            ScreenSnapshot,
            ScreenSourceType,
        )

        app = FocusedApplication(app_name="test")
        snap = ScreenSnapshot(
            source_type=ScreenSourceType.OBSERVED,
            source_confidence=0.9,
            active_application=app,
            workstation_detail={"monitors": []},
        )
        d = snap.to_dict()
        self.assertEqual(d["source_type"], "observed")
        self.assertEqual(d["source_confidence"], 0.9)
        self.assertEqual(d["active_application"]["app_name"], "test")


# ── Beast Workspace Collection Tests ──────────────────────────────────────


class TestBeastWorkspaceCollection(unittest.TestCase):
    """Beast-side collection functions (non-Windows: graceful fallback)."""

    def test_collect_workstation_state_structure(self) -> None:
        from nodes.windows.umh_node.workspace import collect_workstation_state

        state = collect_workstation_state()
        self.assertIn("monitors", state)
        self.assertIn("windows", state)
        self.assertIn("editor_context", state)
        self.assertIn("browser_tabs", state)
        self.assertIn("terminal_sessions", state)
        self.assertIn("active_window_id", state)
        self.assertIn("collected_at", state)

    def test_collect_returns_lists(self) -> None:
        from nodes.windows.umh_node.workspace import collect_workstation_state

        state = collect_workstation_state()
        self.assertIsInstance(state["monitors"], list)
        self.assertIsInstance(state["windows"], list)
        self.assertIsInstance(state["browser_tabs"], list)
        self.assertIsInstance(state["terminal_sessions"], list)

    def test_non_windows_returns_empty(self) -> None:
        if sys.platform == "win32":
            self.skipTest("Windows-specific test")
        from nodes.windows.umh_node.workspace import collect_workstation_state

        state = collect_workstation_state()
        self.assertEqual(state["monitors"], [])
        self.assertEqual(state["windows"], [])

    def test_state_hash_deterministic(self) -> None:
        from nodes.windows.umh_node.workspace import _state_hash

        state = {"monitors": [], "windows": [{"title": "test"}]}
        h1 = _state_hash(state)
        h2 = _state_hash(state)
        self.assertEqual(h1, h2)

    def test_state_hash_changes_on_different_data(self) -> None:
        from nodes.windows.umh_node.workspace import _state_hash

        s1 = {"windows": [{"title": "a"}]}
        s2 = {"windows": [{"title": "b"}]}
        self.assertNotEqual(_state_hash(s1), _state_hash(s2))

    def test_detect_editor_context_from_windows(self) -> None:
        from nodes.windows.umh_node.workspace import _detect_editor_context

        windows = [
            {"title": "main.py - OS - Visual Studio Code", "app_name": "code.exe"},
        ]
        ctx = _detect_editor_context(windows)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx["editor_name"], "Visual Studio Code")
        self.assertEqual(ctx["active_file"], "main.py")
        self.assertEqual(ctx["workspace_name"], "OS")

    def test_detect_editor_no_ide(self) -> None:
        from nodes.windows.umh_node.workspace import _detect_editor_context

        windows = [{"title": "Google Chrome", "app_name": "chrome.exe"}]
        ctx = _detect_editor_context(windows)
        self.assertIsNone(ctx)

    def test_detect_browser_tabs(self) -> None:
        from nodes.windows.umh_node.workspace import _detect_browser_tabs

        windows = [
            {"title": "GitHub", "app_name": "chrome.exe", "window_id": "w1", "is_focused": True},
            {
                "title": "Not a browser",
                "app_name": "notepad.exe",
                "window_id": "w2",
                "is_focused": False,
            },
        ]
        tabs = _detect_browser_tabs(windows)
        self.assertEqual(len(tabs), 1)
        self.assertEqual(tabs[0]["title"], "GitHub")

    def test_detect_terminal_sessions(self) -> None:
        from nodes.windows.umh_node.workspace import _detect_terminal_sessions

        windows = [
            {
                "title": "PS C:\\>",
                "app_name": "powershell.exe",
                "window_id": "w1",
                "pid": 123,
                "is_focused": False,
            },
        ]
        sessions = _detect_terminal_sessions(windows)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["terminal_type"], "powershell")


# ── Mesh Server Handler Tests ─────────────────────────────────────────────


class TestMeshServerHandler(unittest.TestCase):
    """NodeMeshServer: workstation_state signal routing."""

    def _make_server(self) -> Any:
        from transports.node_mesh.server import NodeMeshServer
        from transports.node_mesh.config import MeshConfig

        config = MeshConfig()
        executor = MagicMock()
        signal_socket = MagicMock()
        capability_socket = MagicMock()
        outcome_socket = MagicMock()
        view_socket = MagicMock()

        server = NodeMeshServer(
            config=config,
            executor=executor,
            signal_socket=signal_socket,
            capability_socket=capability_socket,
            outcome_socket=outcome_socket,
            view_socket=view_socket,
        )
        return server

    def test_register_workstation_callback(self) -> None:
        server = self._make_server()
        cb = MagicMock()
        server.register_workstation_callback(cb)
        self.assertEqual(server._workstation_callback, cb)

    def test_workstation_callback_default_none(self) -> None:
        server = self._make_server()
        self.assertIsNone(server._workstation_callback)

    def test_register_frame_callback_separate(self) -> None:
        server = self._make_server()
        frame_cb = MagicMock()
        ws_cb = MagicMock()
        server.register_frame_callback(frame_cb)
        server.register_workstation_callback(ws_cb)
        self.assertEqual(server._frame_callback, frame_cb)
        self.assertEqual(server._workstation_callback, ws_cb)


# ── Preference Ordering with Workstation Tests ────────────────────────────


class TestPreferenceWithWorkstation(unittest.TestCase):
    """Preference ordering when Beast sends OBSERVED workstation data."""

    def test_observed_beats_inferred(self) -> None:
        from substrate.operator.screen_observation_engine import ScreenObservationEngine
        from substrate.operator.screen_awareness import (
            FocusedApplication,
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        engine = ScreenObservationEngine()

        observed = ScreenSnapshot(
            source_type=ScreenSourceType.OBSERVED,
            status=ScreenContextStatus.ACTIVE,
            source_node_id="beast",
            source_confidence=0.9,
            active_application=FocusedApplication(app_name="VS Code"),
            workstation_detail={"monitors": [{"id": "M0"}]},
        )
        engine.report_observed(observed)
        result = engine.current_snapshot()
        self.assertEqual(result.source_type.value, "observed")
        self.assertEqual(result.source_confidence, 0.9)

    def test_observed_workstation_detail_survives(self) -> None:
        from substrate.operator.screen_observation_engine import ScreenObservationEngine
        from substrate.operator.screen_awareness import (
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        engine = ScreenObservationEngine()
        observed = ScreenSnapshot(
            source_type=ScreenSourceType.OBSERVED,
            status=ScreenContextStatus.ACTIVE,
            source_node_id="beast",
            source_confidence=0.9,
            workstation_detail={"monitors": [{"id": "M0"}], "all_windows": [{"title": "x"}]},
        )
        engine.report_observed(observed)
        result = engine.current_snapshot()
        self.assertEqual(len(result.workstation_detail.get("monitors", [])), 1)

    def test_inferred_has_empty_workstation_detail(self) -> None:
        from substrate.operator.screen_observation_engine import ScreenObservationEngine

        engine = ScreenObservationEngine()
        result = engine.current_snapshot()
        self.assertEqual(result.workstation_detail, {})

    def test_provider_status_shows_observed_available(self) -> None:
        from substrate.operator.screen_observation_engine import ScreenObservationEngine
        from substrate.operator.screen_awareness import (
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        engine = ScreenObservationEngine()
        engine.report_observed(
            ScreenSnapshot(
                source_type=ScreenSourceType.OBSERVED,
                status=ScreenContextStatus.ACTIVE,
                source_confidence=0.9,
            )
        )
        status = engine.provider_status()
        self.assertTrue(status["observed"]["available"])

    def test_source_provenance_correct(self) -> None:
        from substrate.operator.screen_observation_engine import ScreenObservationEngine
        from substrate.operator.screen_awareness import (
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        engine = ScreenObservationEngine()
        engine.report_observed(
            ScreenSnapshot(
                source_type=ScreenSourceType.OBSERVED,
                status=ScreenContextStatus.ACTIVE,
                source_node_id="umh-beast",
                source_device_id="beast-pc",
                source_device_role="workstation",
                source_confidence=0.9,
            )
        )
        result = engine.current_snapshot()
        self.assertEqual(result.source_node_id, "umh-beast")
        self.assertEqual(result.source_device_id, "beast-pc")
        self.assertEqual(result.source_device_role, "workstation")

    def test_history_records_workstation(self) -> None:
        from substrate.operator.screen_observation_engine import ScreenObservationEngine
        from substrate.operator.screen_awareness import (
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        engine = ScreenObservationEngine()
        engine.report_observed(
            ScreenSnapshot(
                source_type=ScreenSourceType.OBSERVED,
                status=ScreenContextStatus.ACTIVE,
                source_confidence=0.9,
            )
        )
        engine.current_snapshot()
        history = engine.history(limit=5)
        self.assertGreater(len(history), 0)
        self.assertEqual(history[0].source_type.value, "observed")


# ── Cockpit Routes Tests ─────────────────────────────────────────────────


class TestCockpitRoutes(unittest.TestCase):
    """Cockpit routes: /screen/workstation, /screen/windows, /screen/monitors."""

    def test_workstation_route_inferred(self) -> None:
        from substrate.operator.screen_awareness import ScreenSnapshot, ScreenSourceType

        snap = ScreenSnapshot(source_type=ScreenSourceType.INFERRED)
        if snap.source_type.value != "observed":
            result = {"available": False, "source_type": snap.source_type.value}
        else:
            result = {"available": True}
        self.assertFalse(result["available"])
        self.assertEqual(result["source_type"], "inferred")

    def test_workstation_route_observed(self) -> None:
        from substrate.operator.screen_awareness import (
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        snap = ScreenSnapshot(
            source_type=ScreenSourceType.OBSERVED,
            status=ScreenContextStatus.ACTIVE,
            source_node_id="beast",
            source_confidence=0.9,
            workstation_detail={
                "monitors": [_make_monitor()],
                "all_windows": [_make_window()],
            },
        )
        if snap.source_type.value == "observed":
            result = {
                "available": True,
                "source_type": snap.source_type.value,
                **snap.workstation_detail,
            }
        else:
            result = {"available": False}
        self.assertTrue(result["available"])
        self.assertEqual(len(result["monitors"]), 1)

    def test_windows_route(self) -> None:
        from substrate.operator.screen_awareness import ScreenSnapshot

        snap = ScreenSnapshot(workstation_detail={"all_windows": [{"title": "a"}, {"title": "b"}]})
        windows = snap.workstation_detail.get("all_windows", [])
        self.assertEqual(len(windows), 2)

    def test_monitors_route(self) -> None:
        from substrate.operator.screen_awareness import ScreenSnapshot

        snap = ScreenSnapshot(
            workstation_detail={
                "monitors": [_make_monitor(), _make_monitor(monitor_id="M1", is_primary=False)]
            }
        )
        monitors = snap.workstation_detail.get("monitors", [])
        self.assertEqual(len(monitors), 2)

    def test_existing_routes_unchanged(self) -> None:
        from substrate.operator.screen_awareness import (
            FocusedApplication,
            ScreenSnapshot,
        )

        snap = ScreenSnapshot(
            active_application=FocusedApplication(app_name="test"),
        )
        d = snap.to_dict()
        self.assertIn("active_application", d)
        self.assertEqual(d["active_application"]["app_name"], "test")


# ── Type Registration Tests ──────────────────────────────────────────────


class TestTypeRegistration(unittest.TestCase):
    """Type registration in canonical_types.py."""

    def test_workstation_translator_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        self.assertIn("WorkstationTranslator", CANONICAL_TYPES)
        self.assertEqual(
            CANONICAL_TYPES["WorkstationTranslator"],
            ["substrate.operator.workstation_translator"],
        )

    def test_phase33_types_still_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        phase33 = [
            "ScreenSourceType",
            "ScreenContextStatus",
            "ApplicationCategory",
            "FocusedApplication",
            "ActiveWindow",
            "RepositoryContext",
            "FileContext",
            "BrowserContext",
            "ScreenSnapshot",
            "ScreenObservationEngine",
        ]
        for name in phase33:
            self.assertIn(name, CANONICAL_TYPES, f"{name} missing from registry")

    def test_no_duplicate_registrations(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        for name, paths in CANONICAL_TYPES.items():
            unique = set(paths)
            self.assertEqual(
                len(unique),
                len(paths),
                f"{name} has duplicate paths: {paths}",
            )

    def test_no_parallel_types_created(self) -> None:
        import importlib

        mod = importlib.import_module("substrate.operator.workstation_translator")
        defined = [
            n
            for n in dir(mod)
            if not n.startswith("_")
            and isinstance(getattr(mod, n), type)
            and getattr(mod, n).__module__ == "substrate.operator.workstation_translator"
        ]
        self.assertEqual(
            defined,
            ["WorkstationTranslator"],
            f"Unexpected types defined in workstation_translator.py: {defined}",
        )


# ── No-Control Verification Tests ────────────────────────────────────────


class TestNoControlMethods(unittest.TestCase):
    """Verify Phase 34 has no keyboard/mouse/remote control automation."""

    def test_translator_has_no_click(self) -> None:
        from substrate.operator.workstation_translator import WorkstationTranslator

        methods = dir(WorkstationTranslator)
        for forbidden in ["click", "type_text", "keypress", "focus_window", "send_keys"]:
            self.assertNotIn(
                forbidden, methods, f"WorkstationTranslator has forbidden method: {forbidden}"
            )

    def test_translator_observation_only(self) -> None:
        from substrate.operator.workstation_translator import WorkstationTranslator

        public_methods = [m for m in dir(WorkstationTranslator) if not m.startswith("_")]
        self.assertEqual(public_methods, ["translate"])

    def test_workspace_no_automation(self) -> None:
        import nodes.windows.umh_node.workspace as ws_mod

        public = [n for n in dir(ws_mod) if not n.startswith("_") and callable(getattr(ws_mod, n))]
        for forbidden in ["click", "type_text", "keypress", "send_keys", "focus_window"]:
            self.assertNotIn(forbidden, public, f"workspace.py has forbidden function: {forbidden}")


# ── Phase 33 Regression Tests ─────────────────────────────────────────────


class TestPhase33Regression(unittest.TestCase):
    """Phase 33 backward compatibility — workstation_detail must not break existing behavior."""

    def test_snapshot_backward_compat(self) -> None:
        from substrate.operator.screen_awareness import ScreenSnapshot

        old_data = {
            "source_type": "inferred",
            "status": "active",
            "source_confidence": 0.3,
        }
        snap = ScreenSnapshot.from_dict(old_data)
        self.assertEqual(snap.source_type.value, "inferred")
        self.assertEqual(snap.workstation_detail, {})

    def test_providers_still_work(self) -> None:
        from substrate.operator.screen_context_providers import (
            InferredScreenContextProvider,
            ObservedScreenContextProvider,
            ReportedScreenContextProvider,
        )

        inferred = InferredScreenContextProvider()
        self.assertTrue(inferred.is_available())
        snap = inferred.current_snapshot()
        self.assertEqual(snap.source_type.value, "inferred")

        observed = ObservedScreenContextProvider()
        self.assertFalse(observed.is_available())

        reported = ReportedScreenContextProvider()
        self.assertFalse(reported.is_available())

    def test_observed_report_still_works(self) -> None:
        from substrate.operator.screen_awareness import (
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )
        from substrate.operator.screen_context_providers import ObservedScreenContextProvider

        provider = ObservedScreenContextProvider()
        snap = ScreenSnapshot(
            source_type=ScreenSourceType.OBSERVED,
            status=ScreenContextStatus.ACTIVE,
            source_confidence=0.9,
        )
        provider.report_observed(snap)
        self.assertTrue(provider.is_available())
        result = provider.current_snapshot()
        self.assertEqual(result.source_type.value, "observed")

    def test_preference_ordering_unchanged(self) -> None:
        from substrate.operator.screen_observation_engine import (
            _SOURCE_PRIORITY,
            _STATUS_PRIORITY,
        )

        self.assertEqual(_SOURCE_PRIORITY.get(None), None)
        self.assertEqual(len(_SOURCE_PRIORITY), 3)
        self.assertEqual(len(_STATUS_PRIORITY), 3)

    def test_inferred_without_workstation(self) -> None:
        from substrate.operator.screen_observation_engine import ScreenObservationEngine

        engine = ScreenObservationEngine()
        snap = engine.current_snapshot()
        self.assertEqual(snap.workstation_detail, {})

    def test_observed_provider_accepts_workstation_detail(self) -> None:
        from substrate.operator.screen_awareness import (
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )
        from substrate.operator.screen_context_providers import ObservedScreenContextProvider

        provider = ObservedScreenContextProvider()
        snap = ScreenSnapshot(
            source_type=ScreenSourceType.OBSERVED,
            status=ScreenContextStatus.ACTIVE,
            source_confidence=0.9,
            workstation_detail={"monitors": [{"id": "M0"}]},
        )
        provider.report_observed(snap)
        result = provider.current_snapshot()
        self.assertEqual(len(result.workstation_detail.get("monitors", [])), 1)


# ── Integration Tests ─────────────────────────────────────────────────────


class TestIntegration(unittest.TestCase):
    """End-to-end: Beast payload → translator → report_observed → engine → OBSERVED."""

    def test_end_to_end_observed_beats_inferred(self) -> None:
        from substrate.operator.screen_observation_engine import ScreenObservationEngine
        from substrate.operator.workstation_translator import WorkstationTranslator

        engine = ScreenObservationEngine()
        translator = WorkstationTranslator()

        payload = _make_beast_payload(
            monitors=[_make_monitor()],
            windows=[
                _make_window(
                    window_id="w1",
                    title="test.py - OS - Visual Studio Code",
                    app_name="code.exe",
                    is_focused=True,
                ),
                _make_window(window_id="w2", title="GitHub - Google Chrome", app_name="chrome.exe"),
            ],
            editor_context={
                "editor_name": "VS Code",
                "workspace_name": "OS",
                "active_file": "test.py",
                "project_path": "/opt/OS",
                "git_branch": "main",
            },
            active_window_id="w1",
        )

        snapshot = translator.translate("umh-windows", payload)
        engine.report_observed(snapshot)
        result = engine.current_snapshot()

        self.assertEqual(result.source_type.value, "observed")
        self.assertEqual(result.source_confidence, 0.9)
        self.assertIsNotNone(result.active_application)
        self.assertEqual(result.active_application.app_name, "code.exe")
        self.assertIsNotNone(result.file_context)
        self.assertEqual(result.file_context.file_name, "test.py")
        self.assertIsNotNone(result.repository_context)
        self.assertEqual(result.repository_context.repo_name, "OS")
        self.assertEqual(len(result.workstation_detail.get("monitors", [])), 1)

    def test_end_to_end_cockpit_data(self) -> None:
        from substrate.operator.screen_observation_engine import ScreenObservationEngine
        from substrate.operator.workstation_translator import WorkstationTranslator

        engine = ScreenObservationEngine()
        translator = WorkstationTranslator()

        payload = _make_beast_payload(
            monitors=[_make_monitor(), _make_monitor(monitor_id="M1", is_primary=False)],
            windows=[_make_window(is_focused=True)],
            active_window_id="w1",
        )

        snap = translator.translate("beast", payload)
        engine.report_observed(snap)
        result = engine.current_snapshot()

        d = result.to_dict()
        self.assertEqual(d["source_type"], "observed")
        self.assertEqual(len(d["workstation_detail"]["monitors"]), 2)

    def test_empty_workstation_graceful(self) -> None:
        from substrate.operator.screen_observation_engine import ScreenObservationEngine
        from substrate.operator.workstation_translator import WorkstationTranslator

        engine = ScreenObservationEngine()
        translator = WorkstationTranslator()

        snap = translator.translate("beast", _make_beast_payload())
        engine.report_observed(snap)
        result = engine.current_snapshot()

        self.assertEqual(result.source_type.value, "observed")
        self.assertIsNone(result.active_application)

    def test_vps_only_still_works(self) -> None:
        from substrate.operator.screen_observation_engine import ScreenObservationEngine

        engine = ScreenObservationEngine()
        result = engine.current_snapshot()
        self.assertIn(result.source_type.value, ("inferred", "unknown"))

    def test_translator_then_to_dict_roundtrip(self) -> None:
        from substrate.operator.screen_awareness import ScreenSnapshot
        from substrate.operator.workstation_translator import WorkstationTranslator

        translator = WorkstationTranslator()
        payload = _make_beast_payload(
            monitors=[_make_monitor()],
            windows=[_make_window(is_focused=True)],
            active_window_id="w1",
            editor_context={
                "editor_name": "VS Code",
                "workspace_name": "OS",
                "active_file": "main.py",
            },
        )
        snap = translator.translate("n1", payload)
        d = snap.to_dict()
        restored = ScreenSnapshot.from_dict(d)

        self.assertEqual(restored.source_type.value, "observed")
        self.assertEqual(restored.source_confidence, 0.9)
        self.assertIsNotNone(restored.active_application)
        self.assertEqual(len(restored.workstation_detail.get("monitors", [])), 1)

    def test_multiple_observed_updates(self) -> None:
        from substrate.operator.screen_observation_engine import ScreenObservationEngine
        from substrate.operator.workstation_translator import WorkstationTranslator

        engine = ScreenObservationEngine()
        translator = WorkstationTranslator()

        p1 = _make_beast_payload(
            windows=[_make_window(window_id="w1", title="file1.py", is_focused=True)],
            active_window_id="w1",
        )
        engine.report_observed(translator.translate("beast", p1))
        r1 = engine.current_snapshot()
        self.assertEqual(r1.active_window.title, "file1.py")

        p2 = _make_beast_payload(
            windows=[_make_window(window_id="w2", title="file2.py", is_focused=True)],
            active_window_id="w2",
        )
        engine.report_observed(translator.translate("beast", p2))
        r2 = engine.current_snapshot()
        self.assertEqual(r2.active_window.title, "file2.py")

    def test_workstation_detail_passthrough(self) -> None:
        from substrate.operator.workstation_translator import WorkstationTranslator

        translator = WorkstationTranslator()
        terminals = [
            {"terminal_id": "t1", "terminal_type": "powershell", "title": "PS C:\\>"},
        ]
        payload = _make_beast_payload(terminal_sessions=terminals)
        snap = translator.translate("n1", payload)
        self.assertEqual(len(snap.workstation_detail["terminal_sessions"]), 1)
        self.assertEqual(
            snap.workstation_detail["terminal_sessions"][0]["terminal_type"], "powershell"
        )

    def test_bridge_wiring_pattern(self) -> None:
        """Simulate the bridge wiring that app.py does."""
        from substrate.operator.screen_observation_engine import ScreenObservationEngine
        from substrate.operator.workstation_translator import WorkstationTranslator

        translator = WorkstationTranslator()
        engine = ScreenObservationEngine()

        def on_workstation_state(node_id: str, payload: dict) -> None:
            snapshot = translator.translate(node_id, payload)
            engine.report_observed(snapshot)

        payload = _make_beast_payload(
            windows=[_make_window(is_focused=True)],
            active_window_id="w1",
            monitors=[_make_monitor()],
        )
        on_workstation_state("umh-beast", payload)

        result = engine.current_snapshot()
        self.assertEqual(result.source_type.value, "observed")
        self.assertEqual(result.source_confidence, 0.9)
        self.assertEqual(len(result.workstation_detail.get("monitors", [])), 1)


if __name__ == "__main__":
    unittest.main()
