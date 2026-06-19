"""Integration tests for Campaign 21 — Visual Awareness.

Tests the full visual brain pipeline: C21.0→C21.1→C21.2→C21.3→C21.4.
Also tests voice→vision bridge via VoiceQueryEngine SCREEN domain.
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Shared mock infrastructure ────────────────────────────────────────


class _Health:
    def __init__(self, v: str = "active"):
        self.value = v


@dataclass
class _ScreenSnap:
    health: str = "active"
    current_screen: dict[str, Any] = field(
        default_factory=lambda: {
            "source_type": "inferred",
            "status": "active",
            "active_application": {
                "app_name": "VS Code",
                "category": "ide",
                "window_title": "visual_operations_runtime.py — OS",
            },
            "repository_context": {
                "repo_name": "OS",
                "branch": "worktree-c21-visual-awareness",
                "dirty_files": 3,
            },
            "file_context": {
                "file_path": "substrate/workstation/visual_operations_runtime.py",
                "file_name": "visual_operations_runtime.py",
                "language": "python",
            },
        }
    )
    device_binding: dict[str, Any] = field(default_factory=dict)
    workspace_context: dict[str, Any] = field(default_factory=dict)
    provider_status: dict[str, Any] = field(default_factory=dict)
    history_count: int = 0
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


class MockScreen:
    def snapshot(self) -> _ScreenSnap:
        return _ScreenSnap()

    def health(self) -> _Health:
        return _Health("active")

    def current_screen(self) -> dict[str, Any]:
        return _ScreenSnap().current_screen


class _Surface:
    def __init__(self, st: str, status: str = "active"):
        self.surface_type = st
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        return {"surface_type": self.surface_type, "status": self.status}


@dataclass
class _EnvSnap:
    surfaces: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {"surface_type": "desktop", "status": "active"},
        ]
    )
    active_count: int = 1
    device_count: int = 1
    primary_surface: dict[str, Any] = field(default_factory=lambda: {"surface_type": "desktop"})
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "surfaces": self.surfaces,
            "active_count": self.active_count,
            "device_count": self.device_count,
            "primary_surface": self.primary_surface,
            "generated_at": self.generated_at,
        }


class MockEnv:
    def snapshot(self) -> _EnvSnap:
        return _EnvSnap()

    def surfaces(self) -> list[_Surface]:
        return [_Surface("desktop"), _Surface("cockpit")]

    def health(self) -> _Health:
        return _Health("active")


@dataclass
class _Binding:
    depth: str = "work"
    screen_summary: str = "VS Code — visual_operations_runtime.py"
    application: str = "VS Code"
    repository: str = "OS"
    branch: str = "worktree-c21-visual-awareness"
    file_path: str = "substrate/workstation/visual_operations_runtime.py"
    campaign: str = "C21"
    goals: list[str] = field(default_factory=lambda: ["Visual awareness MVP"])
    decisions: list[str] = field(default_factory=list)
    confidence: float = 0.85

    def to_dict(self) -> dict[str, Any]:
        return {
            "depth": self.depth,
            "application": self.application,
            "repository": self.repository,
            "branch": self.branch,
            "file_path": self.file_path,
            "campaign": self.campaign,
            "goals": self.goals,
            "confidence": self.confidence,
        }


class MockContext:
    def resolve_context(self) -> _Binding:
        return _Binding()

    def continue_work(self) -> dict[str, Any]:
        return {"action": "continue", "binding": _Binding().to_dict()}

    def health(self) -> _Health:
        return _Health("active")


@dataclass
class _Signal:
    signal_type: str = "failing_test"
    severity: str = "critical"
    description: str = "3 tests failing in test_c21_integration.py"

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type,
            "severity": self.severity,
            "description": self.description,
        }


@dataclass
class _AttSnap:
    visual_signals: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {"signal_type": "failing_test", "severity": "critical"},
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


class MockAttention:
    def snapshot(self) -> _AttSnap:
        return _AttSnap()

    def critical_signals(self) -> list[_Signal]:
        return [_Signal()]

    def detect_visual_signals(self) -> list[_Signal]:
        return [_Signal()]

    def health(self) -> _Health:
        return _Health("active")


# ── Acceptance test 1: What am I looking at? ──────────────────────────


class TestAcceptance1_WhatAmILookingAt(unittest.TestCase):
    def test_full_pipeline(self) -> None:
        from substrate.workstation.visual_operations_runtime import VisualOperationsRuntime

        rt = VisualOperationsRuntime(
            screen_awareness_runtime=MockScreen(),
            environment_awareness_runtime=MockEnv(),
            visual_context_runtime=MockContext(),
            attention_vision_runtime=MockAttention(),
        )
        result = rt.what_am_i_looking_at()
        self.assertIn("screen", result)
        self.assertIn("context_binding", result)
        self.assertEqual(result["context_binding"]["application"], "VS Code")
        self.assertEqual(result["context_binding"]["repository"], "OS")
        self.assertEqual(result["context_binding"]["campaign"], "C21")


# ── Acceptance test 2: Continue this work ─────────────────────────────


class TestAcceptance2_ContinueWork(unittest.TestCase):
    def test_full_pipeline(self) -> None:
        from substrate.workstation.visual_operations_runtime import VisualOperationsRuntime

        rt = VisualOperationsRuntime(visual_context_runtime=MockContext())
        result = rt.continue_this_work()
        self.assertEqual(result["action"], "continue")
        self.assertIn("binding", result)
        self.assertEqual(result["binding"]["repository"], "OS")


# ── Acceptance test 3: Error awareness ────────────────────────────────


class TestAcceptance3_ErrorAwareness(unittest.TestCase):
    def test_full_pipeline(self) -> None:
        from substrate.workstation.visual_operations_runtime import VisualOperationsRuntime

        rt = VisualOperationsRuntime(attention_vision_runtime=MockAttention())
        result = rt.error_awareness()
        self.assertEqual(result["critical_count"], 1)


# ── Acceptance test 4: Multi-surface awareness ────────────────────────


class TestAcceptance4_AllSurfaces(unittest.TestCase):
    def test_full_pipeline(self) -> None:
        from substrate.workstation.visual_operations_runtime import VisualOperationsRuntime

        rt = VisualOperationsRuntime(environment_awareness_runtime=MockEnv())
        result = rt.all_surfaces()
        self.assertEqual(len(result), 2)
        types = [s["surface_type"] for s in result]
        self.assertIn("desktop", types)
        self.assertIn("cockpit", types)


# ── Acceptance test 5: Voice + Vision ─────────────────────────────────


class TestAcceptance5_VoiceVision(unittest.TestCase):
    def test_voice_query_engine_imports(self) -> None:
        from substrate.operator.voice_query_engine import VoiceQueryEngine, QueryDomain

        self.assertIn("SCREEN", [d.name for d in QueryDomain])

    def test_screen_domain_exists(self) -> None:
        from substrate.operator.voice_query_engine import QueryDomain

        self.assertEqual(QueryDomain.SCREEN.value, "screen")


# ── Full composition snapshot ─────────────────────────────────────────


class TestFullComposition(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from substrate.workstation.visual_operations_runtime import VisualOperationsRuntime

        cls.runtime = VisualOperationsRuntime(
            screen_awareness_runtime=MockScreen(),
            environment_awareness_runtime=MockEnv(),
            visual_context_runtime=MockContext(),
            attention_vision_runtime=MockAttention(),
        )

    def test_snapshot_complete(self) -> None:
        snap = self.runtime.snapshot()
        d = snap.to_dict()
        self.assertEqual(d["health"], "optimal")
        self.assertIn("screen_state", d)
        self.assertIn("environment", d)
        self.assertIn("context_binding", d)
        self.assertIn("visual_signals", d)
        self.assertIn("capabilities", d)
        self.assertTrue(d["capabilities"]["screen_awareness"])
        self.assertTrue(d["capabilities"]["visual_context"])

    def test_health_optimal(self) -> None:
        self.assertEqual(self.runtime.health().value, "optimal")

    def test_summary(self) -> None:
        s = self.runtime.summary()
        self.assertEqual(s["subsystems_up"], 4)


if __name__ == "__main__":
    unittest.main()
