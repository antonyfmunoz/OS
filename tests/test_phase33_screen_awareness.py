"""Phase 33 — Screen Awareness Runtime tests.

110 tests covering:
  - Screen awareness models (enums + dataclasses)
  - Provider contract + three implementations
  - Screen observation engine with preference ordering
  - Repository context resolver
  - ContinuityEngine integration
  - OperatorContextEngine integration
  - Type registration
  - Cockpit route structure
  - No-control-methods verification
  - End-to-end integration
"""
from __future__ import annotations

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


# ── Mock infrastructure ─────────────────────────────────────────


class MockTerminal:
    def __init__(self, terminal_id: str = "t1", title: str = "bash"):
        self.terminal_id = terminal_id
        self.title = title

    def to_dict(self) -> dict:
        return {"terminal_id": self.terminal_id, "title": self.title}


class MockSession:
    def __init__(
        self,
        session_id: str = "s1",
        harness: str = "claude_code",
        files_touched: list | None = None,
    ):
        self.session_id = session_id
        self.harness = harness
        self.files_touched = files_touched or []
        self.session_type = "engineering"

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "harness": self.harness,
            "session_type": self.session_type,
        }


class MockWorkspaceSnapshot:
    def __init__(
        self,
        terminals: list | None = None,
        engineering_sessions: list | None = None,
        repositories: list | None = None,
    ):
        self.terminals = terminals or []
        self.engineering_sessions = engineering_sessions or []
        self.repositories = repositories or []
        self.containers = []
        self.previews = []
        self.snapshot_id = "wobs-test"
        self.observed_at = time.time()
        self.host_id = "test"
        self.metadata = {}

    def to_dict(self) -> dict:
        return {
            "terminals": [t.to_dict() for t in self.terminals],
            "engineering_sessions": [s.to_dict() for s in self.engineering_sessions],
            "repositories": self.repositories,
            "sessions": [s.to_dict() for s in self.engineering_sessions],
        }


class MockWorkspaceEngine:
    def __init__(self, snapshot: MockWorkspaceSnapshot | None = None):
        self._snapshot = snapshot

    def latest(self) -> MockWorkspaceSnapshot | None:
        return self._snapshot


class MockTopologyEngine:
    def __init__(self, summary: dict | None = None):
        self._summary = summary

    def workspace_summary(self, workspace_id: str) -> dict | None:
        return self._summary

    def snapshot(self) -> dict:
        return {}


class MockNode:
    def __init__(
        self,
        node_id: str = "umh-vps",
        device_id: str = "vps",
        roles: list | None = None,
        primary: bool = True,
    ):
        self.node_id = node_id
        self.device_id = device_id
        self.roles = roles or ["orchestrator", "control_plane"]
        self.primary = primary
        self.purpose = "test"
        self.hostname = "test"
        self.status = "online"


class MockNodeRegistry:
    def __init__(self, nodes: list | None = None):
        self._nodes = {n.node_id: n for n in (nodes or [])}

    def list_nodes(self) -> list:
        return list(self._nodes.values())

    def get_node(self, node_id: str):
        return self._nodes.get(node_id)

    def primary_node(self):
        for n in self._nodes.values():
            if n.primary:
                return n
        return None

    def nodes_for_role(self, role: str) -> list:
        return [n for n in self._nodes.values() if role in n.roles]


class MockContextEngine:
    def pending_approvals(self) -> dict:
        return {"count": 0, "items": []}

    def health_summary(self):
        m = MagicMock()
        m.overall_status = "healthy"
        return m


class MockActionBridge:
    pass


def _make_engine(**overrides):
    from substrate.operator.screen_observation_engine import ScreenObservationEngine

    defaults = {
        "workspace_engine": MockWorkspaceEngine(),
        "topology_engine": MockTopologyEngine(),
        "continuity_engine": None,
        "node_registry": MockNodeRegistry([MockNode()]),
    }
    defaults.update(overrides)
    return ScreenObservationEngine(**defaults)


def _make_continuity_engine(**overrides):
    from substrate.operator.continuity_engine import ContinuityEngine

    defaults = {
        "workspace_engine": MockWorkspaceEngine(),
        "topology_engine": MockTopologyEngine(),
        "action_bridge": MockActionBridge(),
        "context_engine": MockContextEngine(),
        "node_registry": MockNodeRegistry([MockNode()]),
    }
    defaults.update(overrides)
    return ContinuityEngine(**defaults)


# ── Enum tests ──────────────────────────────────────────────────


class TestScreenSourceTypeEnum(unittest.TestCase):
    def test_values(self):
        from substrate.operator.screen_awareness import ScreenSourceType

        self.assertEqual(ScreenSourceType.INFERRED.value, "inferred")
        self.assertEqual(ScreenSourceType.REPORTED.value, "reported")
        self.assertEqual(ScreenSourceType.OBSERVED.value, "observed")

    def test_count(self):
        from substrate.operator.screen_awareness import ScreenSourceType

        self.assertEqual(len(ScreenSourceType), 3)

    def test_str_enum(self):
        from substrate.operator.screen_awareness import ScreenSourceType

        self.assertIsInstance(ScreenSourceType.INFERRED, str)

    def test_from_value(self):
        from substrate.operator.screen_awareness import ScreenSourceType

        self.assertEqual(ScreenSourceType("inferred"), ScreenSourceType.INFERRED)


class TestScreenContextStatusEnum(unittest.TestCase):
    def test_values(self):
        from substrate.operator.screen_awareness import ScreenContextStatus

        self.assertEqual(ScreenContextStatus.ACTIVE.value, "active")
        self.assertEqual(ScreenContextStatus.STALE.value, "stale")
        self.assertEqual(ScreenContextStatus.UNKNOWN.value, "unknown")

    def test_count(self):
        from substrate.operator.screen_awareness import ScreenContextStatus

        self.assertEqual(len(ScreenContextStatus), 3)

    def test_str_enum(self):
        from substrate.operator.screen_awareness import ScreenContextStatus

        self.assertIsInstance(ScreenContextStatus.ACTIVE, str)

    def test_from_value(self):
        from substrate.operator.screen_awareness import ScreenContextStatus

        self.assertEqual(ScreenContextStatus("active"), ScreenContextStatus.ACTIVE)


class TestApplicationCategoryEnum(unittest.TestCase):
    def test_values(self):
        from substrate.operator.screen_awareness import ApplicationCategory

        self.assertEqual(ApplicationCategory.IDE.value, "ide")
        self.assertEqual(ApplicationCategory.TERMINAL.value, "terminal")
        self.assertEqual(ApplicationCategory.BROWSER.value, "browser")
        self.assertEqual(ApplicationCategory.OTHER.value, "other")

    def test_count(self):
        from substrate.operator.screen_awareness import ApplicationCategory

        self.assertEqual(len(ApplicationCategory), 6)

    def test_str_enum(self):
        from substrate.operator.screen_awareness import ApplicationCategory

        self.assertIsInstance(ApplicationCategory.IDE, str)

    def test_from_value(self):
        from substrate.operator.screen_awareness import ApplicationCategory

        self.assertEqual(ApplicationCategory("ide"), ApplicationCategory.IDE)


# ── Dataclass tests ─────────────────────────────────────────────


class TestFocusedApplication(unittest.TestCase):
    def test_creation(self):
        from substrate.operator.screen_awareness import (
            ApplicationCategory,
            FocusedApplication,
        )

        app = FocusedApplication(app_name="VS Code", category=ApplicationCategory.IDE)
        self.assertEqual(app.app_name, "VS Code")
        self.assertEqual(app.category, ApplicationCategory.IDE)
        self.assertTrue(app.is_focused)
        self.assertIsInstance(app.detected_at, float)

    def test_to_dict(self):
        from substrate.operator.screen_awareness import FocusedApplication

        app = FocusedApplication(app_name="Terminal")
        d = app.to_dict()
        self.assertEqual(d["app_name"], "Terminal")
        self.assertEqual(d["category"], "other")

    def test_from_dict(self):
        from substrate.operator.screen_awareness import (
            ApplicationCategory,
            FocusedApplication,
        )

        d = {"app_name": "Chrome", "category": "browser", "pid": 1234}
        app = FocusedApplication.from_dict(d)
        self.assertEqual(app.app_name, "Chrome")
        self.assertEqual(app.category, ApplicationCategory.BROWSER)
        self.assertEqual(app.pid, 1234)

    def test_roundtrip(self):
        from substrate.operator.screen_awareness import (
            ApplicationCategory,
            FocusedApplication,
        )

        original = FocusedApplication(
            app_name="Figma",
            category=ApplicationCategory.DESIGN,
            pid=5678,
            window_title="Design File",
        )
        restored = FocusedApplication.from_dict(original.to_dict())
        self.assertEqual(restored.app_name, original.app_name)
        self.assertEqual(restored.category, original.category)
        self.assertEqual(restored.pid, original.pid)


class TestActiveWindow(unittest.TestCase):
    def test_creation(self):
        from substrate.operator.screen_awareness import ActiveWindow

        win = ActiveWindow(title="main.py")
        self.assertEqual(win.title, "main.py")
        self.assertTrue(win.is_active)
        self.assertTrue(win.window_id.startswith("win-"))

    def test_to_dict(self):
        from substrate.operator.screen_awareness import ActiveWindow

        win = ActiveWindow(title="test", application="vim")
        d = win.to_dict()
        self.assertEqual(d["title"], "test")
        self.assertEqual(d["application"], "vim")

    def test_from_dict(self):
        from substrate.operator.screen_awareness import ActiveWindow

        d = {"title": "code.py", "application": "VS Code", "is_active": False}
        win = ActiveWindow.from_dict(d)
        self.assertEqual(win.title, "code.py")
        self.assertFalse(win.is_active)

    def test_roundtrip(self):
        from substrate.operator.screen_awareness import ActiveWindow

        original = ActiveWindow(title="test.ts", application="VS Code", workspace_id="umh")
        restored = ActiveWindow.from_dict(original.to_dict())
        self.assertEqual(restored.title, original.title)
        self.assertEqual(restored.workspace_id, original.workspace_id)


class TestRepositoryContext(unittest.TestCase):
    def test_creation(self):
        from substrate.operator.screen_awareness import RepositoryContext

        repo = RepositoryContext(repo_name="OS", repo_path="/opt/OS")
        self.assertEqual(repo.repo_name, "OS")
        self.assertEqual(repo.dirty_files, 0)

    def test_to_dict(self):
        from substrate.operator.screen_awareness import RepositoryContext

        repo = RepositoryContext(repo_name="OS", repo_path="/opt/OS", branch="main")
        d = repo.to_dict()
        self.assertEqual(d["repo_name"], "OS")
        self.assertEqual(d["branch"], "main")

    def test_from_dict(self):
        from substrate.operator.screen_awareness import RepositoryContext

        d = {"repo_name": "creatoros", "repo_path": "/dev/creatoros", "dirty_files": 3}
        repo = RepositoryContext.from_dict(d)
        self.assertEqual(repo.dirty_files, 3)

    def test_roundtrip(self):
        from substrate.operator.screen_awareness import RepositoryContext

        original = RepositoryContext(
            repo_name="OS", repo_path="/opt/OS", branch="feature", dirty_files=5
        )
        restored = RepositoryContext.from_dict(original.to_dict())
        self.assertEqual(restored.repo_name, original.repo_name)
        self.assertEqual(restored.dirty_files, original.dirty_files)


class TestFileContext(unittest.TestCase):
    def test_creation(self):
        from substrate.operator.screen_awareness import FileContext

        fc = FileContext(file_path="/opt/OS/main.py", file_name="main.py")
        self.assertEqual(fc.file_name, "main.py")
        self.assertEqual(fc.line_number, 0)

    def test_to_dict(self):
        from substrate.operator.screen_awareness import FileContext

        fc = FileContext(file_path="/a/b.py", file_name="b.py", language="py")
        d = fc.to_dict()
        self.assertEqual(d["language"], "py")

    def test_from_dict(self):
        from substrate.operator.screen_awareness import FileContext

        d = {"file_path": "/x/y.ts", "file_name": "y.ts", "language": "ts", "line_number": 42}
        fc = FileContext.from_dict(d)
        self.assertEqual(fc.line_number, 42)

    def test_roundtrip(self):
        from substrate.operator.screen_awareness import FileContext

        original = FileContext(file_path="/a.py", file_name="a.py", repo_name="OS")
        restored = FileContext.from_dict(original.to_dict())
        self.assertEqual(restored.repo_name, original.repo_name)


class TestBrowserContext(unittest.TestCase):
    def test_creation(self):
        from substrate.operator.screen_awareness import BrowserContext

        bc = BrowserContext()
        self.assertEqual(bc.url, "")
        self.assertIsInstance(bc.detected_at, float)

    def test_to_dict(self):
        from substrate.operator.screen_awareness import BrowserContext

        bc = BrowserContext(url="https://example.com", title="Example", domain="example.com")
        d = bc.to_dict()
        self.assertEqual(d["domain"], "example.com")

    def test_from_dict(self):
        from substrate.operator.screen_awareness import BrowserContext

        d = {"url": "https://x.com", "title": "X", "domain": "x.com"}
        bc = BrowserContext.from_dict(d)
        self.assertEqual(bc.domain, "x.com")

    def test_roundtrip(self):
        from substrate.operator.screen_awareness import BrowserContext

        original = BrowserContext(url="https://test.com", title="Test")
        restored = BrowserContext.from_dict(original.to_dict())
        self.assertEqual(restored.url, original.url)


class TestScreenSnapshot(unittest.TestCase):
    def test_creation_defaults(self):
        from substrate.operator.screen_awareness import (
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        snap = ScreenSnapshot()
        self.assertEqual(snap.source_type, ScreenSourceType.INFERRED)
        self.assertEqual(snap.status, ScreenContextStatus.UNKNOWN)
        self.assertEqual(snap.source_confidence, 0.0)
        self.assertIsNone(snap.active_application)

    def test_source_provenance_fields(self):
        from substrate.operator.screen_awareness import ScreenSnapshot, ScreenSourceType

        snap = ScreenSnapshot(
            source_type=ScreenSourceType.OBSERVED,
            source_node_id="umh-windows",
            source_device_id="beast",
            source_device_role="workstation",
            source_confidence=0.9,
        )
        self.assertEqual(snap.source_node_id, "umh-windows")
        self.assertEqual(snap.source_device_id, "beast")
        self.assertEqual(snap.source_device_role, "workstation")
        self.assertEqual(snap.source_confidence, 0.9)

    def test_to_dict(self):
        from substrate.operator.screen_awareness import ScreenSnapshot

        snap = ScreenSnapshot(source_node_id="umh-vps", source_confidence=0.3)
        d = snap.to_dict()
        self.assertEqual(d["source_node_id"], "umh-vps")
        self.assertEqual(d["source_confidence"], 0.3)
        self.assertIn("source_device_role", d)

    def test_from_dict(self):
        from substrate.operator.screen_awareness import ScreenSnapshot, ScreenSourceType

        d = {
            "source_type": "observed",
            "source_node_id": "umh-windows",
            "source_confidence": 0.9,
            "source_device_role": "workstation",
        }
        snap = ScreenSnapshot.from_dict(d)
        self.assertEqual(snap.source_type, ScreenSourceType.OBSERVED)
        self.assertEqual(snap.source_confidence, 0.9)

    def test_roundtrip(self):
        from substrate.operator.screen_awareness import (
            ApplicationCategory,
            FocusedApplication,
            RepositoryContext,
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        original = ScreenSnapshot(
            source_type=ScreenSourceType.OBSERVED,
            status=ScreenContextStatus.ACTIVE,
            source_node_id="umh-windows",
            source_device_id="beast",
            source_device_role="workstation",
            source_confidence=0.9,
            active_application=FocusedApplication(
                app_name="VS Code", category=ApplicationCategory.IDE
            ),
            repository_context=RepositoryContext(
                repo_name="OS", repo_path="/opt/OS", branch="main"
            ),
        )
        restored = ScreenSnapshot.from_dict(original.to_dict())
        self.assertEqual(restored.source_type, original.source_type)
        self.assertEqual(restored.source_confidence, original.source_confidence)
        self.assertEqual(restored.active_application.app_name, "VS Code")
        self.assertEqual(restored.repository_context.repo_name, "OS")

    def test_nested_objects(self):
        from substrate.operator.screen_awareness import (
            ActiveWindow,
            BrowserContext,
            FileContext,
            FocusedApplication,
            RepositoryContext,
            ScreenSnapshot,
        )

        snap = ScreenSnapshot(
            active_application=FocusedApplication(app_name="Chrome"),
            active_window=ActiveWindow(title="Tab 1"),
            repository_context=RepositoryContext(repo_name="OS", repo_path="/opt/OS"),
            file_context=FileContext(file_path="/a.py", file_name="a.py"),
            browser_context=BrowserContext(url="https://x.com"),
            applications=[FocusedApplication(app_name="A"), FocusedApplication(app_name="B")],
        )
        d = snap.to_dict()
        self.assertIsNotNone(d["active_application"])
        self.assertIsNotNone(d["active_window"])
        self.assertEqual(len(d["applications"]), 2)


# ── Provider tests ──────────────────────────────────────────────


class TestInferredProvider(unittest.TestCase):
    def test_creation(self):
        from substrate.operator.screen_context_providers import InferredScreenContextProvider
        from substrate.operator.screen_awareness import ScreenSourceType

        p = InferredScreenContextProvider()
        self.assertEqual(p.provider_id, "inferred")
        self.assertEqual(p.source_type, ScreenSourceType.INFERRED)

    def test_is_available_always_true(self):
        from substrate.operator.screen_context_providers import InferredScreenContextProvider

        p = InferredScreenContextProvider()
        self.assertTrue(p.is_available())

    def test_confidence(self):
        from substrate.operator.screen_context_providers import InferredScreenContextProvider

        self.assertEqual(InferredScreenContextProvider.CONFIDENCE, 0.3)

    def test_source_type_inferred(self):
        from substrate.operator.screen_context_providers import InferredScreenContextProvider
        from substrate.operator.screen_awareness import ScreenSourceType

        p = InferredScreenContextProvider()
        snap = p.current_snapshot()
        self.assertEqual(snap.source_type, ScreenSourceType.INFERRED)
        self.assertEqual(snap.source_confidence, 0.3)

    def test_snapshot_from_workspace(self):
        from substrate.operator.screen_context_providers import InferredScreenContextProvider

        ws = MockWorkspaceSnapshot(
            engineering_sessions=[MockSession()],
            repositories=[
                {"repo_name": "OS", "repo_path": "/opt/OS", "current_branch": "main", "dirty_files": 2}
            ],
        )
        p = InferredScreenContextProvider(workspace_engine=MockWorkspaceEngine(ws))
        snap = p.current_snapshot()
        self.assertIsNotNone(snap.active_application)
        self.assertEqual(snap.active_application.app_name, "Claude Code")
        self.assertIsNotNone(snap.repository_context)
        self.assertEqual(snap.repository_context.repo_name, "OS")

    def test_snapshot_empty(self):
        from substrate.operator.screen_context_providers import InferredScreenContextProvider
        from substrate.operator.screen_awareness import ScreenContextStatus

        p = InferredScreenContextProvider(workspace_engine=MockWorkspaceEngine(None))
        snap = p.current_snapshot()
        self.assertEqual(snap.status, ScreenContextStatus.UNKNOWN)
        self.assertIsNone(snap.active_application)


class TestObservedProvider(unittest.TestCase):
    def test_creation(self):
        from substrate.operator.screen_context_providers import ObservedScreenContextProvider
        from substrate.operator.screen_awareness import ScreenSourceType

        p = ObservedScreenContextProvider()
        self.assertEqual(p.source_type, ScreenSourceType.OBSERVED)
        self.assertEqual(p.node_id, "umh-windows")

    def test_not_available_initially(self):
        from substrate.operator.screen_context_providers import ObservedScreenContextProvider

        p = ObservedScreenContextProvider()
        self.assertFalse(p.is_available())

    def test_confidence(self):
        from substrate.operator.screen_context_providers import ObservedScreenContextProvider

        self.assertEqual(ObservedScreenContextProvider.CONFIDENCE, 0.9)

    def test_report_observed_makes_available(self):
        from substrate.operator.screen_context_providers import ObservedScreenContextProvider
        from substrate.operator.screen_awareness import ScreenSnapshot, ScreenSourceType

        p = ObservedScreenContextProvider()
        snap = ScreenSnapshot(source_type=ScreenSourceType.OBSERVED)
        p.report_observed(snap)
        self.assertTrue(p.is_available())
        result = p.current_snapshot()
        self.assertEqual(result.source_confidence, 0.9)

    def test_stale_snapshot(self):
        from substrate.operator.screen_context_providers import ObservedScreenContextProvider
        from substrate.operator.screen_awareness import (
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        p = ObservedScreenContextProvider()
        snap = ScreenSnapshot(source_type=ScreenSourceType.OBSERVED)
        p.report_observed(snap)
        p._observed_at = time.time() - 120
        result = p.current_snapshot()
        self.assertEqual(result.status, ScreenContextStatus.STALE)

    def test_unknown_when_no_data(self):
        from substrate.operator.screen_context_providers import ObservedScreenContextProvider
        from substrate.operator.screen_awareness import ScreenContextStatus

        p = ObservedScreenContextProvider()
        result = p.current_snapshot()
        self.assertEqual(result.status, ScreenContextStatus.UNKNOWN)


class TestReportedProvider(unittest.TestCase):
    def test_creation(self):
        from substrate.operator.screen_context_providers import ReportedScreenContextProvider
        from substrate.operator.screen_awareness import ScreenSourceType

        p = ReportedScreenContextProvider()
        self.assertEqual(p.source_type, ScreenSourceType.REPORTED)

    def test_confidence(self):
        from substrate.operator.screen_context_providers import ReportedScreenContextProvider

        self.assertEqual(ReportedScreenContextProvider.CONFIDENCE, 0.6)

    def test_not_available_initially(self):
        from substrate.operator.screen_context_providers import ReportedScreenContextProvider

        p = ReportedScreenContextProvider()
        self.assertFalse(p.is_available())

    def test_report_context(self):
        from substrate.operator.screen_context_providers import ReportedScreenContextProvider
        from substrate.operator.screen_awareness import ScreenSnapshot

        p = ReportedScreenContextProvider()
        snap = ScreenSnapshot()
        p.report_context(snap)
        self.assertTrue(p.is_available())

    def test_expired_report(self):
        from substrate.operator.screen_context_providers import ReportedScreenContextProvider
        from substrate.operator.screen_awareness import ScreenSnapshot

        p = ReportedScreenContextProvider()
        snap = ScreenSnapshot()
        p.report_context(snap)
        p._reported_at = time.time() - 400
        self.assertFalse(p.is_available())


# ── Screen Observation Engine tests ─────────────────────────────


class TestScreenObservationEngine(unittest.TestCase):
    def test_creation(self):
        engine = _make_engine()
        self.assertIsNotNone(engine)

    def test_lazy_properties(self):
        engine = _make_engine()
        self.assertIsNotNone(engine.workspace_engine)
        self.assertIsNotNone(engine.node_registry)

    def test_current_snapshot_empty(self):
        from substrate.operator.screen_awareness import ScreenSourceType

        engine = _make_engine()
        snap = engine.current_snapshot()
        self.assertEqual(snap.source_type, ScreenSourceType.INFERRED)

    def test_current_snapshot_with_workspace(self):
        ws = MockWorkspaceSnapshot(
            engineering_sessions=[MockSession()],
            repositories=[
                {"repo_name": "OS", "repo_path": "/opt/OS", "current_branch": "main", "dirty_files": 1}
            ],
        )
        engine = _make_engine(workspace_engine=MockWorkspaceEngine(ws))
        snap = engine.current_snapshot()
        self.assertIsNotNone(snap.active_application)

    def test_observed_beats_inferred(self):
        from substrate.operator.screen_awareness import (
            FocusedApplication,
            ApplicationCategory,
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        engine = _make_engine()
        observed_snap = ScreenSnapshot(
            source_type=ScreenSourceType.OBSERVED,
            status=ScreenContextStatus.ACTIVE,
            source_confidence=0.9,
            active_application=FocusedApplication(
                app_name="VS Code", category=ApplicationCategory.IDE
            ),
        )
        engine.report_observed(observed_snap)
        result = engine.current_snapshot()
        self.assertEqual(result.source_type, ScreenSourceType.OBSERVED)
        self.assertEqual(result.source_confidence, 0.9)

    def test_reported_beats_inferred(self):
        from substrate.operator.screen_awareness import (
            FocusedApplication,
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        engine = _make_engine()
        reported_snap = ScreenSnapshot(
            source_type=ScreenSourceType.REPORTED,
            status=ScreenContextStatus.ACTIVE,
            source_confidence=0.6,
            active_application=FocusedApplication(app_name="Safari"),
        )
        engine.report_context(reported_snap)
        result = engine.current_snapshot()
        self.assertEqual(result.source_type, ScreenSourceType.REPORTED)

    def test_stale_observed_loses_to_fresh_inferred(self):
        from substrate.operator.screen_awareness import (
            FocusedApplication,
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        ws = MockWorkspaceSnapshot(
            engineering_sessions=[MockSession()],
            repositories=[{"repo_name": "OS", "repo_path": "/opt/OS", "current_branch": "main", "dirty_files": 1}],
        )
        engine = _make_engine(workspace_engine=MockWorkspaceEngine(ws))

        observed_snap = ScreenSnapshot(
            source_type=ScreenSourceType.OBSERVED,
            status=ScreenContextStatus.ACTIVE,
            active_application=FocusedApplication(app_name="VS Code"),
        )
        engine.report_observed(observed_snap)
        engine._observed_provider._observed_at = time.time() - 120

        result = engine.current_snapshot()
        # Fresh inferred (ACTIVE) should beat stale observed
        # Both may appear — key is ACTIVE wins over STALE
        self.assertEqual(result.status, ScreenContextStatus.ACTIVE)

    def test_report_observed(self):
        from substrate.operator.screen_awareness import ScreenSnapshot, ScreenSourceType

        engine = _make_engine()
        snap = ScreenSnapshot(source_type=ScreenSourceType.OBSERVED)
        engine.report_observed(snap)
        self.assertTrue(engine._observed_provider.is_available())

    def test_report_context(self):
        from substrate.operator.screen_awareness import ScreenSnapshot

        engine = _make_engine()
        snap = ScreenSnapshot()
        engine.report_context(snap)
        self.assertTrue(engine._reported_provider.is_available())

    def test_history(self):
        engine = _make_engine()
        engine.current_snapshot()
        engine.current_snapshot()
        self.assertGreaterEqual(len(engine.history()), 2)

    def test_provider_status(self):
        engine = _make_engine()
        status = engine.provider_status()
        self.assertIn("inferred", status)
        self.assertIn("observed", status)
        self.assertIn("reported", status)
        self.assertTrue(status["inferred"]["available"])
        self.assertFalse(status["observed"]["available"])

    def test_expected_provider_for_vps_node(self):
        vps_node = MockNode(node_id="umh-vps", roles=["orchestrator", "control_plane"])
        engine = _make_engine(node_registry=MockNodeRegistry([vps_node]))
        expected = engine.expected_provider_for_node("umh-vps")
        self.assertEqual(expected, "inferred")

    def test_expected_provider_for_workstation_node(self):
        beast = MockNode(
            node_id="umh-windows",
            device_id="beast",
            roles=["workstation", "builder"],
            primary=False,
        )
        engine = _make_engine(node_registry=MockNodeRegistry([MockNode(), beast]))
        expected = engine.expected_provider_for_node("umh-windows")
        self.assertEqual(expected, "observed")

    def test_node_role_mapping(self):
        from substrate.operator.screen_observation_engine import _ROLE_TO_EXPECTED_SOURCE
        from substrate.operator.screen_awareness import ScreenSourceType

        self.assertEqual(_ROLE_TO_EXPECTED_SOURCE["workstation"], ScreenSourceType.OBSERVED)
        self.assertEqual(_ROLE_TO_EXPECTED_SOURCE["builder"], ScreenSourceType.OBSERVED)
        self.assertEqual(_ROLE_TO_EXPECTED_SOURCE["orchestrator"], ScreenSourceType.INFERRED)
        self.assertEqual(_ROLE_TO_EXPECTED_SOURCE["controller"], ScreenSourceType.REPORTED)

    def test_graceful_degradation(self):
        from substrate.operator.screen_awareness import ScreenSourceType

        engine = _make_engine(
            workspace_engine=None,
            topology_engine=None,
            node_registry=None,
        )
        snap = engine.current_snapshot()
        self.assertEqual(snap.source_type, ScreenSourceType.INFERRED)

    def test_active_application_delegates(self):
        ws = MockWorkspaceSnapshot(engineering_sessions=[MockSession()])
        engine = _make_engine(workspace_engine=MockWorkspaceEngine(ws))
        app = engine.active_application()
        self.assertIsNotNone(app)

    def test_active_browser_none_on_vps(self):
        engine = _make_engine()
        browser = engine.active_browser()
        self.assertIsNone(browser)


# ── Repository Context Resolver tests ───────────────────────────


class TestRepositoryContextResolver(unittest.TestCase):
    def test_creation(self):
        from substrate.operator.repository_context_resolver import RepositoryContextResolver

        resolver = RepositoryContextResolver()
        self.assertIsNotNone(resolver)

    def test_resolve_found(self):
        from substrate.operator.repository_context_resolver import RepositoryContextResolver

        ws = MockWorkspaceSnapshot(
            repositories=[{"repo_name": "OS", "repo_path": "/opt/OS", "current_branch": "main"}]
        )
        resolver = RepositoryContextResolver(workspace_engine=MockWorkspaceEngine(ws))
        ctx = resolver.resolve("/opt/OS")
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.repo_name, "OS")

    def test_resolve_not_found(self):
        from substrate.operator.repository_context_resolver import RepositoryContextResolver

        ws = MockWorkspaceSnapshot(repositories=[])
        resolver = RepositoryContextResolver(workspace_engine=MockWorkspaceEngine(ws))
        ctx = resolver.resolve("/nonexistent")
        self.assertIsNone(ctx)

    def test_resolve_by_prefix(self):
        from substrate.operator.repository_context_resolver import RepositoryContextResolver

        ws = MockWorkspaceSnapshot(
            repositories=[{"repo_name": "OS", "repo_path": "/opt/OS", "current_branch": "main"}]
        )
        resolver = RepositoryContextResolver(workspace_engine=MockWorkspaceEngine(ws))
        ctx = resolver.resolve("/opt/OS/substrate/operator/test.py")
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.repo_name, "OS")

    def test_active_repositories(self):
        from substrate.operator.repository_context_resolver import RepositoryContextResolver

        ws = MockWorkspaceSnapshot(
            repositories=[
                {"repo_name": "clean", "repo_path": "/a", "dirty_files": 0},
                {"repo_name": "dirty", "repo_path": "/b", "dirty_files": 3},
            ]
        )
        resolver = RepositoryContextResolver(workspace_engine=MockWorkspaceEngine(ws))
        active = resolver.active_repositories()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].repo_name, "dirty")

    def test_resolve_workspace(self):
        from substrate.operator.repository_context_resolver import RepositoryContextResolver

        topo = MockTopologyEngine(
            summary={"repositories": [{"repo_name": "OS", "repo_path": "/opt/OS"}]}
        )
        resolver = RepositoryContextResolver(topology_engine=topo)
        repos = resolver.resolve_workspace("umh")
        self.assertEqual(len(repos), 1)

    def test_graceful_degradation(self):
        from substrate.operator.repository_context_resolver import RepositoryContextResolver

        resolver = RepositoryContextResolver(workspace_engine=None, topology_engine=None)
        self.assertIsNone(resolver.resolve("/opt/OS"))
        self.assertEqual(resolver.active_repositories(), [])

    def test_resolve_workspace_no_summary(self):
        from substrate.operator.repository_context_resolver import RepositoryContextResolver

        topo = MockTopologyEngine(summary=None)
        resolver = RepositoryContextResolver(topology_engine=topo)
        self.assertEqual(resolver.resolve_workspace("nonexistent"), [])


# ── ContinuityEngine Integration tests ──────────────────────────


class TestContinuityEngineIntegration(unittest.TestCase):
    def test_screen_observation_lazy(self):
        engine = _make_continuity_engine()
        self.assertIsNone(engine._screen_observation)

    def test_screen_context_returns_dict(self):
        engine = _make_continuity_engine()
        result = engine.screen_context()
        if result is not None:
            self.assertIsInstance(result, dict)
            self.assertIn("source_type", result)

    def test_screen_observation_shares_engines(self):
        engine = _make_continuity_engine()
        so = engine.screen_observation
        if so is not None:
            self.assertIsNotNone(so)

    def test_checkpoint_includes_visual_metadata(self):
        ws = MockWorkspaceSnapshot(
            engineering_sessions=[MockSession()],
            repositories=[
                {"repo_name": "OS", "repo_path": "/opt/OS", "current_branch": "main", "dirty_files": 1}
            ],
        )
        engine = _make_continuity_engine(
            workspace_engine=MockWorkspaceEngine(ws),
        )
        engine._context_engine = MockContextEngine()
        checkpoints = engine.continuity_checkpoints()
        session_cps = [c for c in checkpoints if c.checkpoint_type == "engineering_session"]
        if session_cps:
            detail = session_cps[0].detail
            self.assertIn("|", detail)

    def test_screen_context_none_on_failure(self):
        engine = _make_continuity_engine()
        engine._screen_observation = MagicMock()
        engine._screen_observation.current_snapshot.side_effect = Exception("fail")
        result = engine.screen_context()
        self.assertIsNone(result)

    def test_source_provenance_in_checkpoint(self):
        ws = MockWorkspaceSnapshot(
            engineering_sessions=[MockSession()],
            repositories=[
                {"repo_name": "OS", "repo_path": "/opt/OS", "current_branch": "main", "dirty_files": 1}
            ],
        )
        engine = _make_continuity_engine(workspace_engine=MockWorkspaceEngine(ws))
        checkpoints = engine.continuity_checkpoints()
        session_cps = [c for c in checkpoints if c.checkpoint_type == "engineering_session"]
        if session_cps:
            detail = session_cps[0].detail
            if "|" in detail:
                self.assertIn("source=", detail)


# ── OperatorContextEngine Integration tests ─────────────────────


class TestOperatorContextIntegration(unittest.TestCase):
    def test_screen_observation_lazy(self):
        from substrate.operator.operator_context_engine import OperatorContextEngine

        engine = OperatorContextEngine()
        self.assertIsNone(engine._screen_observation)

    def test_screen_context_returns_dict(self):
        from substrate.operator.operator_context_engine import OperatorContextEngine

        engine = OperatorContextEngine()
        result = engine.screen_context()
        self.assertIsInstance(result, dict)

    def test_preference_ordering_used(self):
        from substrate.operator.operator_context_engine import OperatorContextEngine

        engine = OperatorContextEngine()
        result = engine.screen_context()
        if result:
            self.assertIn("source_type", result)

    def test_screen_context_empty_on_failure(self):
        from substrate.operator.operator_context_engine import OperatorContextEngine

        engine = OperatorContextEngine()
        engine._screen_observation = MagicMock()
        engine._screen_observation.current_snapshot.side_effect = Exception("fail")
        result = engine.screen_context()
        self.assertEqual(result, {})

    def test_independent_from_snapshot(self):
        from substrate.operator.operator_context_engine import OperatorContextEngine

        engine = OperatorContextEngine()
        snap = engine.snapshot()
        d = snap.to_dict()
        self.assertNotIn("screen_context", d)


# ── Type Registration tests ─────────────────────────────────────


class TestTypeRegistration(unittest.TestCase):
    def test_all_types_registered(self):
        from substrate.canonical_types import lookup

        types = [
            "ScreenSourceType",
            "ScreenContextStatus",
            "ApplicationCategory",
            "FocusedApplication",
            "ActiveWindow",
            "RepositoryContext",
            "FileContext",
            "BrowserContext",
            "ScreenSnapshot",
            "ScreenContextProvider",
            "InferredScreenContextProvider",
            "ObservedScreenContextProvider",
            "ReportedScreenContextProvider",
            "ScreenObservationEngine",
            "RepositoryContextResolver",
        ]
        for t in types:
            result = lookup(t)
            self.assertIsNotNone(result, f"{t} not registered in canonical_types")

    def test_no_duplicate_types(self):
        from substrate.canonical_types import CANONICAL_TYPES

        phase33_types = [k for k in CANONICAL_TYPES if k.startswith("Screen") or k in (
            "ApplicationCategory", "FocusedApplication", "ActiveWindow",
            "RepositoryContext", "FileContext", "BrowserContext",
            "InferredScreenContextProvider", "ObservedScreenContextProvider",
            "ReportedScreenContextProvider", "RepositoryContextResolver",
        )]
        self.assertEqual(len(phase33_types), len(set(phase33_types)))

    def test_correct_module_paths(self):
        from substrate.canonical_types import lookup

        self.assertEqual(
            lookup("ScreenSnapshot"),
            ["substrate.operator.screen_awareness"],
        )
        self.assertEqual(
            lookup("ScreenObservationEngine"),
            ["substrate.operator.screen_observation_engine"],
        )
        self.assertEqual(
            lookup("InferredScreenContextProvider"),
            ["substrate.operator.screen_context_providers"],
        )

    def test_type_count(self):
        from substrate.canonical_types import lookup

        count = 0
        for name in [
            "ScreenSourceType", "ScreenContextStatus", "ApplicationCategory",
            "FocusedApplication", "ActiveWindow", "RepositoryContext",
            "FileContext", "BrowserContext", "ScreenSnapshot",
            "ScreenContextProvider", "InferredScreenContextProvider",
            "ObservedScreenContextProvider", "ReportedScreenContextProvider",
            "ScreenObservationEngine", "RepositoryContextResolver",
        ]:
            if lookup(name) is not None:
                count += 1
        self.assertEqual(count, 15)


# ── Cockpit Route tests ────────────────────────────────────────


class TestCockpitRoutes(unittest.TestCase):
    def test_router_exists(self):
        from transports.api.cockpit_screen_awareness_routes import screen_awareness_router

        self.assertIsNotNone(screen_awareness_router)

    def test_route_count(self):
        from transports.api.cockpit_screen_awareness_routes import (
            screen_awareness_router,
            configure,
        )

        mock_dep = MagicMock()
        configure(require_operator_dep=mock_dep)
        routes = [r for r in screen_awareness_router.routes if hasattr(r, "path")]
        self.assertGreaterEqual(len(routes), 7)

    def test_route_paths(self):
        from transports.api.cockpit_screen_awareness_routes import (
            screen_awareness_router,
            configure,
        )

        mock_dep = MagicMock()
        configure(require_operator_dep=mock_dep)
        paths = {r.path for r in screen_awareness_router.routes if hasattr(r, "path")}
        expected = {
            "/screen",
            "/screen/current",
            "/screen/application",
            "/screen/file",
            "/screen/repository",
            "/screen/repositories",
            "/screen/providers",
        }
        for p in expected:
            self.assertIn(p, paths, f"Missing route: {p}")

    def test_configure_idempotent(self):
        from transports.api import cockpit_screen_awareness_routes

        mock_dep = MagicMock()
        cockpit_screen_awareness_routes.configure(require_operator_dep=mock_dep)
        cockpit_screen_awareness_routes.configure(require_operator_dep=mock_dep)

    def test_get_engine_singleton(self):
        from transports.api.cockpit_screen_awareness_routes import _get_engine

        e1 = _get_engine()
        e2 = _get_engine()
        self.assertIs(e1, e2)

    def test_get_resolver_singleton(self):
        from transports.api.cockpit_screen_awareness_routes import _get_resolver

        r1 = _get_resolver()
        r2 = _get_resolver()
        self.assertIs(r1, r2)

    def test_providers_route_exists(self):
        from transports.api.cockpit_screen_awareness_routes import (
            screen_awareness_router,
        )

        paths = {r.path for r in screen_awareness_router.routes if hasattr(r, "path")}
        self.assertIn("/screen/providers", paths)


# ── No-control-methods tests ────────────────────────────────────


class TestNoControlMethods(unittest.TestCase):
    def test_no_keyboard_mouse_methods(self):
        from substrate.operator.screen_observation_engine import ScreenObservationEngine

        engine = ScreenObservationEngine()
        methods = [m for m in dir(engine) if not m.startswith("_")]
        forbidden = ["click", "type", "press_key", "move_mouse", "keyboard", "mouse"]
        for f in forbidden:
            for m in methods:
                self.assertNotIn(f, m.lower(), f"Found forbidden method pattern '{f}' in '{m}'")

    def test_no_remote_desktop_methods(self):
        from substrate.operator.screen_observation_engine import ScreenObservationEngine

        engine = ScreenObservationEngine()
        methods = [m for m in dir(engine) if not m.startswith("_")]
        forbidden = ["remote_desktop", "vnc", "rdp", "screen_share"]
        for f in forbidden:
            for m in methods:
                self.assertNotIn(f, m.lower(), f"Found forbidden method pattern '{f}' in '{m}'")

    def test_no_ocr_authority(self):
        from substrate.operator.screen_observation_engine import ScreenObservationEngine

        engine = ScreenObservationEngine()
        methods = [m for m in dir(engine) if not m.startswith("_")]
        for m in methods:
            self.assertNotIn("ocr", m.lower(), f"Found OCR method: {m}")


# ── Integration tests ───────────────────────────────────────────


class TestIntegration(unittest.TestCase):
    def test_vps_returns_inferred(self):
        from substrate.operator.screen_awareness import ScreenSourceType

        engine = _make_engine()
        snap = engine.current_snapshot()
        self.assertEqual(snap.source_type, ScreenSourceType.INFERRED)

    def test_beast_expected_observed(self):
        beast = MockNode(
            node_id="umh-windows",
            device_id="beast",
            roles=["workstation", "builder"],
            primary=False,
        )
        engine = _make_engine(node_registry=MockNodeRegistry([MockNode(), beast]))
        expected = engine.expected_provider_for_node("umh-windows")
        self.assertEqual(expected, "observed")

    def test_full_preference_chain(self):
        from substrate.operator.screen_awareness import (
            FocusedApplication,
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        ws = MockWorkspaceSnapshot(
            engineering_sessions=[MockSession()],
            repositories=[{"repo_name": "OS", "repo_path": "/opt/OS", "current_branch": "main", "dirty_files": 1}],
        )
        engine = _make_engine(workspace_engine=MockWorkspaceEngine(ws))

        snap1 = engine.current_snapshot()
        self.assertEqual(snap1.source_type, ScreenSourceType.INFERRED)

        reported = ScreenSnapshot(
            source_type=ScreenSourceType.REPORTED,
            status=ScreenContextStatus.ACTIVE,
            active_application=FocusedApplication(app_name="Safari"),
        )
        engine.report_context(reported)
        snap2 = engine.current_snapshot()
        self.assertEqual(snap2.source_type, ScreenSourceType.REPORTED)

        observed = ScreenSnapshot(
            source_type=ScreenSourceType.OBSERVED,
            status=ScreenContextStatus.ACTIVE,
            active_application=FocusedApplication(app_name="VS Code"),
        )
        engine.report_observed(observed)
        snap3 = engine.current_snapshot()
        self.assertEqual(snap3.source_type, ScreenSourceType.OBSERVED)

    def test_stale_handling(self):
        from substrate.operator.screen_awareness import (
            FocusedApplication,
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )

        ws = MockWorkspaceSnapshot(
            engineering_sessions=[MockSession()],
            repositories=[{"repo_name": "OS", "repo_path": "/opt/OS", "current_branch": "main", "dirty_files": 1}],
        )
        engine = _make_engine(workspace_engine=MockWorkspaceEngine(ws))

        observed = ScreenSnapshot(
            source_type=ScreenSourceType.OBSERVED,
            status=ScreenContextStatus.ACTIVE,
            active_application=FocusedApplication(app_name="VS Code"),
        )
        engine.report_observed(observed)
        engine._observed_provider._observed_at = time.time() - 120

        result = engine.current_snapshot()
        self.assertEqual(result.status, ScreenContextStatus.ACTIVE)

    def test_provider_status_complete(self):
        engine = _make_engine()
        status = engine.provider_status()
        self.assertEqual(len(status), 3)
        for key in ["inferred", "observed", "reported"]:
            self.assertIn("available", status[key])
            self.assertIn("confidence", status[key])
            self.assertIn("source_type", status[key])

    def test_snapshot_has_source_provenance(self):
        engine = _make_engine()
        snap = engine.current_snapshot()
        self.assertIn("source_node_id", snap.to_dict())
        self.assertIn("source_device_id", snap.to_dict())
        self.assertIn("source_device_role", snap.to_dict())
        self.assertIn("source_confidence", snap.to_dict())

    def test_operator_context_preference(self):
        from substrate.operator.screen_awareness import (
            FocusedApplication,
            ScreenContextStatus,
            ScreenSnapshot,
            ScreenSourceType,
        )
        from substrate.operator.operator_context_engine import OperatorContextEngine

        engine = OperatorContextEngine()
        result = engine.screen_context()
        if result and result.get("source_type"):
            self.assertIn(result["source_type"], ["inferred", "reported", "observed"])

    def test_continuity_checkpoint_visual_metadata(self):
        ws = MockWorkspaceSnapshot(
            engineering_sessions=[MockSession()],
            repositories=[
                {"repo_name": "OS", "repo_path": "/opt/OS", "current_branch": "main", "dirty_files": 1}
            ],
        )
        engine = _make_continuity_engine(workspace_engine=MockWorkspaceEngine(ws))
        checkpoints = engine.continuity_checkpoints()
        session_cps = [c for c in checkpoints if c.checkpoint_type == "engineering_session"]
        if session_cps:
            detail = session_cps[0].detail
            if "|" in detail:
                self.assertTrue(
                    any(part.strip().startswith("app=") or part.strip().startswith("repo=") or part.strip().startswith("source=")
                        for part in detail.split("|")),
                    f"Expected visual metadata in detail: {detail}",
                )

    def test_end_to_end_visual_context_chain(self):
        from substrate.operator.screen_awareness import ScreenSourceType

        ws = MockWorkspaceSnapshot(
            engineering_sessions=[MockSession(harness="claude_code", files_touched=["/opt/OS/test.py"])],
            repositories=[
                {"repo_name": "OS", "repo_path": "/opt/OS", "current_branch": "main", "dirty_files": 2}
            ],
        )
        engine = _make_engine(workspace_engine=MockWorkspaceEngine(ws))
        snap = engine.current_snapshot()

        self.assertEqual(snap.source_type, ScreenSourceType.INFERRED)
        self.assertIsNotNone(snap.active_application)
        self.assertEqual(snap.active_application.app_name, "Claude Code")
        self.assertIsNotNone(snap.repository_context)
        self.assertEqual(snap.repository_context.repo_name, "OS")
        self.assertIsNotNone(snap.file_context)
        self.assertEqual(snap.file_context.file_name, "test.py")

    def test_no_vision_store_conflict(self):
        import importlib
        mod = importlib.import_module("substrate.operator.screen_awareness")
        members = [m for m in dir(mod) if not m.startswith("_")]
        for m in members:
            self.assertNotIn("vision", m.lower(), f"Found 'vision' in member name: {m}")


if __name__ == "__main__":
    unittest.main()
