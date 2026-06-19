"""Tests for EnvironmentAwarenessRuntime — Campaign 21.1."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.workstation.environment_awareness_runtime import (
    EnvironmentAwarenessRuntime,
    EnvironmentAwarenessSnapshot,
    ObservedSurface,
    SurfaceHealth,
    SurfaceType,
)


# ── Mock helpers ──────────────────────────────────────────────────────


class MockPresenceRuntime:
    def get_online_devices(self) -> list[dict]:
        return [
            {
                "id": "srv1500858",
                "type": "vps",
                "role": "orchestrator",
                "online": True,
                "name": "VPS",
            },
            {
                "id": "desktop-lvguiq9",
                "type": "workstation",
                "role": "builder",
                "online": True,
                "name": "Beast",
            },
        ]

    def get_active_sessions(self) -> list[dict]:
        return [
            {
                "session_id": "s1",
                "client_type": "cockpit",
                "device_id": "desktop-lvguiq9",
                "last_active": 9999999999.0,
            },
            {
                "session_id": "s2",
                "client_type": "terminal",
                "device_id": "srv1500858",
                "last_active": 9999999999.0,
            },
        ]


class MockSessionMachineRuntime:
    def bindings(self) -> list[dict]:
        return [{"device_id": "srv1500858", "sessions": ["s2"]}]

    def active_workspaces(self) -> list[dict]:
        return [{"device": "srv1500858", "repo": "OS", "branch": "main"}]


class MockScreenAwarenessRuntime:
    def current_screen(self) -> dict:
        return {
            "application": {"app_name": "VS Code", "category": "ide"},
            "repository": {"repo_name": "OS", "branch": "main"},
        }

    def health(self) -> str:
        return "active"


# ── Type tests ────────────────────────────────────────────────────────


class TestTypes(unittest.TestCase):
    def test_surface_type_values(self) -> None:
        self.assertEqual(SurfaceType.DESKTOP.value, "desktop")
        self.assertEqual(SurfaceType.COCKPIT.value, "cockpit")
        self.assertEqual(SurfaceType.TERMINAL.value, "terminal")
        self.assertEqual(SurfaceType.CONTAINER.value, "container")
        self.assertEqual(SurfaceType.MOBILE.value, "mobile")

    def test_surface_health_values(self) -> None:
        self.assertEqual(SurfaceHealth.ACTIVE.value, "active")
        self.assertEqual(SurfaceHealth.OFFLINE.value, "offline")

    def test_observed_surface_defaults(self) -> None:
        s = ObservedSurface()
        self.assertEqual(s.surface_type, "desktop")
        self.assertEqual(s.status, "offline")
        self.assertEqual(s.device_id, "")

    def test_observed_surface_to_dict(self) -> None:
        s = ObservedSurface(surface_type="terminal", device_id="srv1")
        d = s.to_dict()
        self.assertEqual(d["surface_type"], "terminal")
        self.assertEqual(d["device_id"], "srv1")

    def test_snapshot_defaults(self) -> None:
        snap = EnvironmentAwarenessSnapshot()
        self.assertEqual(snap.surfaces, [])
        self.assertEqual(snap.active_count, 0)
        self.assertFalse(snap.camera_available)

    def test_snapshot_to_dict(self) -> None:
        snap = EnvironmentAwarenessSnapshot(active_count=2, device_count=1)
        d = snap.to_dict()
        self.assertEqual(d["active_count"], 2)
        self.assertEqual(d["device_count"], 1)


# ── No-deps graceful degradation ─────────────────────────────────────


class TestNoDeps(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = EnvironmentAwarenessRuntime()

    def test_surfaces_empty(self) -> None:
        result = self.runtime.surfaces()
        self.assertIsInstance(result, list)

    def test_active_surfaces_empty(self) -> None:
        result = self.runtime.active_surfaces()
        self.assertIsInstance(result, list)

    def test_primary_surface_graceful(self) -> None:
        result = self.runtime.primary_surface()
        # May resolve via lazy screen awareness or be None
        if result is not None:
            self.assertIsInstance(result, ObservedSurface)

    def test_device_count_zero(self) -> None:
        self.assertEqual(self.runtime.device_count(), 0)

    def test_snapshot_graceful(self) -> None:
        snap = self.runtime.snapshot()
        self.assertIsInstance(snap, EnvironmentAwarenessSnapshot)
        self.assertIsInstance(snap.active_count, int)

    def test_summary_works(self) -> None:
        s = self.runtime.summary()
        self.assertIn("active_surfaces", s)


# ── With mocks ────────────────────────────────────────────────────────


class TestWithMocks(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = EnvironmentAwarenessRuntime(
            presence_runtime=MockPresenceRuntime(),
            session_machine_runtime=MockSessionMachineRuntime(),
            screen_awareness_runtime=MockScreenAwarenessRuntime(),
        )

    def test_surfaces_populated(self) -> None:
        surfaces = self.runtime.surfaces()
        self.assertGreater(len(surfaces), 0)

    def test_surfaces_contain_device_types(self) -> None:
        types = {s.surface_type for s in self.runtime.surfaces()}
        self.assertIn("terminal", types)

    def test_active_surfaces_nonempty(self) -> None:
        active = self.runtime.active_surfaces()
        self.assertGreater(len(active), 0)

    def test_device_count(self) -> None:
        self.assertEqual(self.runtime.device_count(), 2)

    def test_snapshot_populated(self) -> None:
        snap = self.runtime.snapshot()
        self.assertGreater(snap.active_count, 0)
        self.assertGreater(snap.device_count, 0)
        self.assertTrue(snap.screen_available)

    def test_summary_keys(self) -> None:
        s = self.runtime.summary()
        self.assertIn("active_surfaces", s)
        self.assertIn("devices", s)
        self.assertIn("primary", s)


# ── Surface mapping ──────────────────────────────────────────────────


class TestSurfaceMapping(unittest.TestCase):
    def test_workstation_maps_to_desktop(self) -> None:
        rt = EnvironmentAwarenessRuntime(
            presence_runtime=MockPresenceRuntime(),
        )
        surfaces = rt.surfaces()
        types = {s.surface_type for s in surfaces}
        self.assertIn("desktop", types)

    def test_vps_maps_to_terminal(self) -> None:
        rt = EnvironmentAwarenessRuntime(
            presence_runtime=MockPresenceRuntime(),
        )
        surfaces = rt.surfaces()
        types = {s.surface_type for s in surfaces}
        self.assertIn("terminal", types)


# ── Primary surface ──────────────────────────────────────────────────


class TestPrimarySurface(unittest.TestCase):
    def test_primary_from_screen(self) -> None:
        rt = EnvironmentAwarenessRuntime(
            screen_awareness_runtime=MockScreenAwarenessRuntime(),
        )
        primary = rt.primary_surface()
        self.assertIsNotNone(primary)
        self.assertEqual(primary.surface_type, "ide")
        self.assertEqual(primary.status, "active")

    def test_primary_fallback_to_first_active(self) -> None:
        rt = EnvironmentAwarenessRuntime(
            presence_runtime=MockPresenceRuntime(),
        )
        primary = rt.primary_surface()
        self.assertIsNotNone(primary)


if __name__ == "__main__":
    unittest.main()
