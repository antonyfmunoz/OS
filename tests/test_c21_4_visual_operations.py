"""Tests for VisualOperationsRuntime — Campaign 21.4."""

from __future__ import annotations

import os
import sys
import time
import unittest
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Sentinel to suppress lazy imports ─────────────────────────────────


class _NoRuntime:
    """Sentinel that is not None (so lazy import won't fire) but fails health check."""

    def health(self) -> "_NoRuntimeHealth":
        return _NoRuntimeHealth()


class _NoRuntimeHealth:
    value = "offline"


# ── Mock helpers ──────────────────────────────────────────────────────


@dataclass
class _MockScreenSnapshot:
    health: str = "active"
    current_screen: dict[str, Any] = field(
        default_factory=lambda: {
            "active_application": {"app_name": "VS Code", "category": "ide"},
            "repository_context": {"repo_name": "OS", "branch": "main"},
        }
    )
    device_binding: dict[str, Any] = field(default_factory=dict)
    workspace_context: dict[str, Any] = field(default_factory=dict)
    provider_status: dict[str, Any] = field(default_factory=dict)
    history_count: int = 5
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "health": self.health,
            "current_screen": self.current_screen,
            "device_binding": self.device_binding,
            "workspace_context": self.workspace_context,
            "provider_status": self.provider_status,
            "history_count": self.history_count,
            "generated_at": self.generated_at,
        }


class _MockScreenHealth:
    def __init__(self, value: str = "active"):
        self.value = value


class MockScreenAwareness:
    def snapshot(self) -> _MockScreenSnapshot:
        return _MockScreenSnapshot()

    def health(self) -> _MockScreenHealth:
        return _MockScreenHealth("active")

    def current_screen(self) -> dict[str, Any]:
        return _MockScreenSnapshot().current_screen


@dataclass
class _MockEnvSnapshot:
    surfaces: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {"surface_type": "desktop", "status": "active"},
            {"surface_type": "cockpit", "status": "active"},
        ]
    )
    active_count: int = 2
    device_count: int = 1
    primary_surface: dict[str, Any] = field(
        default_factory=lambda: {
            "surface_type": "desktop",
        }
    )
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "surfaces": self.surfaces,
            "active_count": self.active_count,
            "device_count": self.device_count,
            "primary_surface": self.primary_surface,
            "generated_at": self.generated_at,
        }


class _MockObservedSurface:
    def __init__(self, surface_type: str = "desktop", status: str = "active"):
        self.surface_type = surface_type
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        return {"surface_type": self.surface_type, "status": self.status}


class MockEnvironment:
    def snapshot(self) -> _MockEnvSnapshot:
        return _MockEnvSnapshot()

    def surfaces(self) -> list[_MockObservedSurface]:
        return [
            _MockObservedSurface("desktop"),
            _MockObservedSurface("cockpit"),
            _MockObservedSurface("terminal"),
        ]

    def health(self) -> _MockScreenHealth:
        return _MockScreenHealth("active")


@dataclass
class _MockContextBinding:
    depth: str = "work"
    screen_summary: str = "VS Code"
    application: str = "VS Code"
    repository: str = "OS"
    branch: str = "main"
    file_path: str = "substrate/workstation/visual_operations_runtime.py"
    campaign: str = "C21"
    goals: list[str] = field(default_factory=lambda: ["Visual awareness"])
    decisions: list[str] = field(default_factory=list)
    confidence: float = 0.9

    def to_dict(self) -> dict[str, Any]:
        return {
            "depth": self.depth,
            "screen_summary": self.screen_summary,
            "application": self.application,
            "repository": self.repository,
            "branch": self.branch,
            "file_path": self.file_path,
            "campaign": self.campaign,
            "goals": self.goals,
            "decisions": self.decisions,
            "confidence": self.confidence,
        }


class MockVisualContext:
    def resolve_context(self) -> _MockContextBinding:
        return _MockContextBinding()

    def continue_work(self) -> dict[str, Any]:
        return {
            "action": "continue",
            "binding": _MockContextBinding().to_dict(),
            "suggestion": "Continue working on C21 Visual Awareness",
        }

    def health(self) -> _MockScreenHealth:
        return _MockScreenHealth("active")


@dataclass
class _MockAttentionSignal:
    signal_type: str = "error_banner"
    severity: str = "critical"
    description: str = "Build failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type,
            "severity": self.severity,
            "description": self.description,
        }


@dataclass
class _MockAttentionSnapshot:
    visual_signals: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {"signal_type": "error_banner", "severity": "critical"},
        ]
    )
    critical_count: int = 1
    warning_count: int = 0
    info_count: int = 0
    attention_items: list[dict[str, Any]] = field(default_factory=list)
    total_attention_count: int = 0
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "visual_signals": self.visual_signals,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
        }


class MockAttentionVision:
    def snapshot(self) -> _MockAttentionSnapshot:
        return _MockAttentionSnapshot()

    def detect_visual_signals(self) -> list[_MockAttentionSignal]:
        return [_MockAttentionSignal()]

    def critical_signals(self) -> list[_MockAttentionSignal]:
        return [_MockAttentionSignal()]

    def health(self) -> _MockScreenHealth:
        return _MockScreenHealth("active")


# ── Type tests ────────────────────────────────────────────────────────


class TestTypes(unittest.TestCase):
    def test_health_enum_values(self) -> None:
        from substrate.workstation.visual_operations_runtime import (
            VisualOperationsHealth,
        )

        self.assertEqual(VisualOperationsHealth.OPTIMAL.value, "optimal")
        self.assertEqual(VisualOperationsHealth.ACTIVE.value, "active")
        self.assertEqual(VisualOperationsHealth.DEGRADED.value, "degraded")
        self.assertEqual(VisualOperationsHealth.OFFLINE.value, "offline")

    def test_capability_status_defaults(self) -> None:
        from substrate.workstation.visual_operations_runtime import (
            VisualCapabilityStatus,
        )

        caps = VisualCapabilityStatus()
        self.assertFalse(caps.screen_awareness)
        self.assertFalse(caps.environment_awareness)
        d = caps.to_dict()
        self.assertIn("screen_awareness", d)

    def test_snapshot_defaults(self) -> None:
        from substrate.workstation.visual_operations_runtime import (
            VisualOperationsSnapshot,
        )

        snap = VisualOperationsSnapshot()
        self.assertEqual(snap.health, "offline")
        self.assertEqual(snap.critical_count, 0)
        d = snap.to_dict()
        self.assertIn("health", d)
        self.assertIn("capabilities", d)


# ── No-deps tests ────────────────────────────────────────────────────


class TestNoDeps(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from substrate.workstation.visual_operations_runtime import (
            VisualOperationsRuntime,
        )

        _no = _NoRuntime()
        cls.runtime = VisualOperationsRuntime(
            screen_awareness_runtime=_no,
            environment_awareness_runtime=_no,
            visual_context_runtime=_no,
            attention_vision_runtime=_no,
        )

    def test_health_offline(self) -> None:
        h = self.runtime.health()
        self.assertEqual(h.value, "offline")

    def test_capabilities_all_false(self) -> None:
        caps = self.runtime.capabilities()
        self.assertFalse(caps.screen_awareness)
        self.assertFalse(caps.environment_awareness)
        self.assertFalse(caps.visual_context)
        self.assertFalse(caps.attention_vision)

    def test_snapshot_offline(self) -> None:
        snap = self.runtime.snapshot()
        self.assertEqual(snap.health, "offline")

    def test_what_am_i_looking_at_degraded(self) -> None:
        result = self.runtime.what_am_i_looking_at()
        self.assertIn("screen_error", result)

    def test_continue_this_work_error(self) -> None:
        result = self.runtime.continue_this_work()
        self.assertIn("error", result)

    def test_error_awareness_error(self) -> None:
        result = self.runtime.error_awareness()
        self.assertIn("error", result)

    def test_all_surfaces_empty(self) -> None:
        result = self.runtime.all_surfaces()
        self.assertEqual(result, [])

    def test_summary_offline(self) -> None:
        s = self.runtime.summary()
        self.assertEqual(s["health"], "offline")
        self.assertEqual(s["subsystems_up"], 0)


# ── With-mocks tests ─────────────────────────────────────────────────


class TestWithMocks(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from substrate.workstation.visual_operations_runtime import (
            VisualOperationsRuntime,
        )

        cls.runtime = VisualOperationsRuntime(
            screen_awareness_runtime=MockScreenAwareness(),
            environment_awareness_runtime=MockEnvironment(),
            visual_context_runtime=MockVisualContext(),
            attention_vision_runtime=MockAttentionVision(),
        )

    def test_health_optimal(self) -> None:
        h = self.runtime.health()
        self.assertEqual(h.value, "optimal")

    def test_capabilities_all_true(self) -> None:
        caps = self.runtime.capabilities()
        self.assertTrue(caps.screen_awareness)
        self.assertTrue(caps.environment_awareness)
        self.assertTrue(caps.visual_context)
        self.assertTrue(caps.attention_vision)

    def test_snapshot_full(self) -> None:
        snap = self.runtime.snapshot()
        self.assertEqual(snap.health, "optimal")
        self.assertIn("current_screen", snap.screen_state)
        self.assertIn("surfaces", snap.environment)
        self.assertIn("depth", snap.context_binding)
        self.assertEqual(snap.critical_count, 1)
        self.assertEqual(snap.surface_count, 2)

    def test_what_am_i_looking_at(self) -> None:
        result = self.runtime.what_am_i_looking_at()
        self.assertIn("screen", result)
        self.assertIn("context_binding", result)
        self.assertEqual(result["context_binding"]["repository"], "OS")

    def test_continue_this_work(self) -> None:
        result = self.runtime.continue_this_work()
        self.assertEqual(result["action"], "continue")
        self.assertIn("binding", result)

    def test_error_awareness(self) -> None:
        result = self.runtime.error_awareness()
        self.assertEqual(result["critical_count"], 1)
        self.assertIn("visual_signals", result)

    def test_all_surfaces(self) -> None:
        result = self.runtime.all_surfaces()
        self.assertEqual(len(result), 3)
        types = [s["surface_type"] for s in result]
        self.assertIn("desktop", types)
        self.assertIn("cockpit", types)

    def test_summary(self) -> None:
        s = self.runtime.summary()
        self.assertEqual(s["health"], "optimal")
        self.assertEqual(s["subsystems_up"], 4)


# ── Health derivation tests ───────────────────────────────────────────


class TestHealthDerivation(unittest.TestCase):
    def test_one_subsystem_degraded(self) -> None:
        from substrate.workstation.visual_operations_runtime import (
            VisualOperationsRuntime,
        )

        _no = _NoRuntime()
        rt = VisualOperationsRuntime(
            screen_awareness_runtime=MockScreenAwareness(),
            environment_awareness_runtime=MockEnvironment(),
            visual_context_runtime=_no,
            attention_vision_runtime=_no,
        )
        h = rt.health()
        self.assertEqual(h.value, "degraded")

    def test_three_subsystems_active(self) -> None:
        from substrate.workstation.visual_operations_runtime import (
            VisualOperationsRuntime,
        )

        _no = _NoRuntime()
        rt = VisualOperationsRuntime(
            screen_awareness_runtime=MockScreenAwareness(),
            environment_awareness_runtime=MockEnvironment(),
            visual_context_runtime=MockVisualContext(),
            attention_vision_runtime=_no,
        )
        h = rt.health()
        self.assertEqual(h.value, "active")


# ── Partial subsystem tests ───────────────────────────────────────────


class TestPartialSubsystems(unittest.TestCase):
    def test_screen_only(self) -> None:
        from substrate.workstation.visual_operations_runtime import (
            VisualOperationsRuntime,
        )

        _no = _NoRuntime()
        rt = VisualOperationsRuntime(
            screen_awareness_runtime=MockScreenAwareness(),
            environment_awareness_runtime=_no,
            visual_context_runtime=_no,
            attention_vision_runtime=_no,
        )
        result = rt.what_am_i_looking_at()
        self.assertIn("screen", result)
        self.assertIn("context_error", result)

    def test_no_attention_still_works(self) -> None:
        from substrate.workstation.visual_operations_runtime import (
            VisualOperationsRuntime,
        )

        _no = _NoRuntime()
        rt = VisualOperationsRuntime(
            screen_awareness_runtime=MockScreenAwareness(),
            visual_context_runtime=MockVisualContext(),
            environment_awareness_runtime=MockEnvironment(),
            attention_vision_runtime=_no,
        )
        result = rt.error_awareness()
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
