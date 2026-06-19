"""Tests for ScreenAwarenessRuntime — Campaign 21.0."""

from __future__ import annotations

import os
import sys
import time
import unittest
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Mock helpers ──────────────────────────────────────────────────────────


@dataclass
class MockScreenSnapshot:
    source_type: str = "inferred"
    status: str = "active"
    device_id: str = "dev-1"
    source_device_id: str = "dev-1"
    source_device_role: str = "workstation"
    source_confidence: float = 0.85
    active_application: Any = None
    active_window: Any = None
    repository_context: Any = None
    file_context: Any = None
    browser_context: Any = None
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "status": self.status,
            "device_id": self.device_id,
            "source_device_id": self.source_device_id,
            "source_device_role": self.source_device_role,
            "source_confidence": self.source_confidence,
            "active_application": self.active_application,
            "active_window": self.active_window,
            "repository_context": self.repository_context,
            "file_context": self.file_context,
            "browser_context": self.browser_context,
            "generated_at": self.generated_at,
        }


class MockEngine:
    def __init__(self, snapshot: MockScreenSnapshot | None = None) -> None:
        self._snap = snapshot or MockScreenSnapshot()
        self._history: list[MockScreenSnapshot] = [self._snap]

    def current_snapshot(self) -> MockScreenSnapshot:
        return self._snap

    def provider_status(self) -> dict[str, Any]:
        return {
            "inferred": {"available": True},
            "observed": {"available": False},
            "reported": {"available": False},
        }

    def history(self, limit: int = 20) -> list[MockScreenSnapshot]:
        return self._history[:limit]


@dataclass
class MockWorkspaceSnapshot:
    device: str = "dev-1"
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


class MockWorkspaceAwareness:
    def detect_active_workspace(self) -> MockWorkspaceSnapshot:
        return MockWorkspaceSnapshot()


@dataclass
class MockPresenceSnapshot:
    operator_present: bool = True
    active_device: str = "dev-1"
    active_session: str = "sess-1"

    def to_dict(self) -> dict[str, Any]:
        return {"operator_present": self.operator_present, "active_device": self.active_device}


class MockPresence:
    def capture_snapshot(self) -> MockPresenceSnapshot:
        return MockPresenceSnapshot()

    def get_online_devices(self) -> list[dict[str, Any]]:
        return [{"id": "dev-1", "role": "workstation"}]


# ── Tests ─────────────────────────────────────────────────────────────────

from substrate.workstation.screen_awareness_runtime import (
    DeviceScreenBinding,
    ScreenAwarenessHealth,
    ScreenAwarenessRuntime,
    ScreenAwarenessSnapshot,
)


class TestTypes(unittest.TestCase):
    def test_health_enum_values(self) -> None:
        self.assertEqual(ScreenAwarenessHealth.ACTIVE.value, "active")
        self.assertEqual(ScreenAwarenessHealth.STALE.value, "stale")
        self.assertEqual(ScreenAwarenessHealth.DEGRADED.value, "degraded")
        self.assertEqual(ScreenAwarenessHealth.OFFLINE.value, "offline")

    def test_device_binding_defaults(self) -> None:
        b = DeviceScreenBinding()
        self.assertEqual(b.device_id, "")
        self.assertEqual(b.confidence, 0.0)

    def test_device_binding_to_dict(self) -> None:
        b = DeviceScreenBinding(device_id="d1", confidence=0.9)
        d = b.to_dict()
        self.assertEqual(d["device_id"], "d1")
        self.assertEqual(d["confidence"], 0.9)

    def test_snapshot_defaults(self) -> None:
        s = ScreenAwarenessSnapshot()
        self.assertEqual(s.health, "offline")
        self.assertEqual(s.current_screen, {})

    def test_snapshot_to_dict(self) -> None:
        s = ScreenAwarenessSnapshot(health="active", history_count=5, generated_at=100.0)
        d = s.to_dict()
        self.assertEqual(d["health"], "active")
        self.assertEqual(d["history_count"], 5)
        self.assertEqual(d["generated_at"], 100.0)


class TestNoDeps(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = ScreenAwarenessRuntime()

    def test_health_offline(self) -> None:
        h = self.runtime.health()
        self.assertEqual(h, ScreenAwarenessHealth.OFFLINE)

    def test_current_screen_returns_data(self) -> None:
        screen = self.runtime.current_screen()
        self.assertIsInstance(screen, dict)
        self.assertIn("source_type", screen)

    def test_application_empty(self) -> None:
        self.assertEqual(self.runtime.application(), {})

    def test_repository_empty(self) -> None:
        self.assertEqual(self.runtime.repository(), {})

    def test_snapshot_offline(self) -> None:
        snap = self.runtime.snapshot()
        self.assertEqual(snap.health, "offline")

    def test_summary_offline(self) -> None:
        s = self.runtime.summary()
        self.assertEqual(s["health"], "offline")


class TestWithMocks(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = MockEngine(
            MockScreenSnapshot(
                active_application={"app_name": "VS Code", "category": "ide"},
                repository_context={"repo_name": "OS", "branch": "main"},
                file_context={"file_path": "/opt/OS/substrate/types.py", "file_name": "types.py"},
            )
        )
        cls.runtime = ScreenAwarenessRuntime(
            screen_observation_engine=cls.engine,
            workspace_awareness_runtime=MockWorkspaceAwareness(),
            presence_runtime=MockPresence(),
        )

    def test_health_active(self) -> None:
        h = self.runtime.health()
        self.assertIn(h, (ScreenAwarenessHealth.ACTIVE, ScreenAwarenessHealth.DEGRADED))

    def test_current_screen(self) -> None:
        screen = self.runtime.current_screen()
        self.assertNotIn("error", screen)
        self.assertEqual(screen["source_device_id"], "dev-1")

    def test_device_binding(self) -> None:
        b = self.runtime.device_binding()
        self.assertEqual(b.device_id, "dev-1")
        self.assertEqual(b.device_role, "workstation")
        self.assertGreater(b.confidence, 0)

    def test_application(self) -> None:
        app = self.runtime.application()
        self.assertEqual(app["app_name"], "VS Code")

    def test_repository(self) -> None:
        repo = self.runtime.repository()
        self.assertEqual(repo["repo_name"], "OS")

    def test_file_context(self) -> None:
        fc = self.runtime.file_context()
        self.assertEqual(fc["file_name"], "types.py")

    def test_snapshot_composition(self) -> None:
        snap = self.runtime.snapshot()
        self.assertNotEqual(snap.current_screen, {})
        self.assertNotEqual(snap.device_binding, {})
        self.assertNotEqual(snap.workspace_context, {})
        self.assertGreater(snap.generated_at, 0)

    def test_summary(self) -> None:
        s = self.runtime.summary()
        self.assertEqual(s["application"], "VS Code")
        self.assertEqual(s["repository"], "OS")


class TestHealthDerivation(unittest.TestCase):
    def test_stale_snapshot(self) -> None:
        stale = MockScreenSnapshot(generated_at=time.time() - 300)
        engine = MockEngine(stale)
        rt = ScreenAwarenessRuntime(screen_observation_engine=engine)
        self.assertEqual(rt.health(), ScreenAwarenessHealth.STALE)

    def test_no_engine(self) -> None:
        rt = ScreenAwarenessRuntime()
        self.assertEqual(rt.health(), ScreenAwarenessHealth.OFFLINE)

    def test_unknown_status(self) -> None:
        unknown = MockScreenSnapshot(status="unknown")
        engine = MockEngine(unknown)
        rt = ScreenAwarenessRuntime(screen_observation_engine=engine)
        self.assertEqual(rt.health(), ScreenAwarenessHealth.OFFLINE)


if __name__ == "__main__":
    unittest.main()
