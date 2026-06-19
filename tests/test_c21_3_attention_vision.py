"""Tests for AttentionVisionRuntime — Campaign 21.3."""

from __future__ import annotations

import os
import sys
import unittest
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.workstation.attention_vision_runtime import (
    AttentionVisionRuntime,
    AttentionVisionSnapshot,
    VisualAttentionSignal,
    VisualSignalSeverity,
    VisualSignalType,
)


# ── Mock helpers ──────────────────────────────────────────────────────


class MockScreenAwareness:
    def __init__(self, screen: dict[str, Any] | None = None) -> None:
        self._screen = screen or {}

    def current_screen(self) -> dict[str, Any]:
        return self._screen

    def health(self) -> str:
        return "active"


@dataclass
class MockQueueSnapshot:
    items: list[dict[str, Any]] = field(default_factory=list)
    total_count: int = 0
    critical_count: int = 0


class MockAttentionAggregation:
    def __init__(self, items: list[dict[str, Any]] | None = None) -> None:
        self._items = items or []

    def queue(self) -> MockQueueSnapshot:
        return MockQueueSnapshot(
            items=self._items,
            total_count=len(self._items),
            critical_count=0,
        )


class MockEnvironmentAwareness:
    def active_surfaces(self) -> list[Any]:
        return []


# ── Screens ───────────────────────────────────────────────────────────

CLEAN_SCREEN: dict[str, Any] = {
    "device_id": "dev-1",
    "focused_application": {
        "app_name": "VS Code",
        "window_title": "main.py — OS",
        "category": "ide",
    },
    "active_windows": [
        {"title": "VS Code — main.py"},
        {"title": "Terminal — bash"},
    ],
    "file_context": {"file_path": "/opt/OS/substrate/types.py"},
}

ERROR_SCREEN: dict[str, Any] = {
    "device_id": "dev-1",
    "focused_application": {
        "app_name": "Terminal",
        "window_title": "npm run test — 3 FAILED",
        "category": "terminal",
    },
    "active_windows": [
        {"title": "Terminal — FAILED tests=3"},
    ],
    "file_context": {},
}

STACK_TRACE_SCREEN: dict[str, Any] = {
    "device_id": "dev-1",
    "focused_application": {
        "app_name": "Terminal",
        "window_title": "Traceback (most recent call last)",
        "category": "terminal",
    },
    "active_windows": [],
    "file_context": {},
}

BUILD_FAIL_SCREEN: dict[str, Any] = {
    "device_id": "dev-1",
    "focused_application": {
        "app_name": "Terminal",
        "window_title": "build failed: compilation error in module X",
        "category": "terminal",
    },
    "active_windows": [],
    "file_context": {},
}

LINT_SCREEN: dict[str, Any] = {
    "device_id": "dev-1",
    "focused_application": {
        "app_name": "Terminal",
        "window_title": "ruff check — 5 warnings found",
        "category": "terminal",
    },
    "active_windows": [],
    "file_context": {},
}


# ── Type tests ────────────────────────────────────────────────────────


class TestTypes(unittest.TestCase):
    def test_signal_type_values(self) -> None:
        self.assertEqual(VisualSignalType.ERROR_BANNER.value, "error_banner")
        self.assertEqual(VisualSignalType.FAILING_TEST.value, "failing_test")
        self.assertEqual(VisualSignalType.STACK_TRACE.value, "stack_trace")
        self.assertEqual(VisualSignalType.BUILD_FAILURE.value, "build_failure")
        self.assertEqual(VisualSignalType.BLOCKED_EXECUTION.value, "blocked_execution")
        self.assertEqual(VisualSignalType.LINT_WARNING.value, "lint_warning")
        self.assertEqual(VisualSignalType.NOTIFICATION.value, "notification")

    def test_severity_values(self) -> None:
        self.assertEqual(VisualSignalSeverity.CRITICAL.value, "critical")
        self.assertEqual(VisualSignalSeverity.WARNING.value, "warning")
        self.assertEqual(VisualSignalSeverity.INFO.value, "info")

    def test_signal_defaults(self) -> None:
        sig = VisualAttentionSignal()
        self.assertEqual(sig.signal_type, "notification")
        self.assertEqual(sig.severity, "info")
        self.assertEqual(sig.confidence, 0.0)

    def test_signal_to_dict(self) -> None:
        sig = VisualAttentionSignal(
            signal_type="error_banner",
            severity="critical",
            source_surface="dev-1",
            description="Error detected",
            detected_from="test window",
            confidence=0.9,
        )
        d = sig.to_dict()
        self.assertEqual(d["signal_type"], "error_banner")
        self.assertEqual(d["severity"], "critical")
        self.assertEqual(d["source_surface"], "dev-1")

    def test_snapshot_defaults(self) -> None:
        snap = AttentionVisionSnapshot()
        self.assertEqual(snap.visual_signals, [])
        self.assertEqual(snap.critical_count, 0)
        self.assertEqual(snap.warning_count, 0)
        self.assertEqual(snap.info_count, 0)
        self.assertEqual(snap.total_attention_count, 0)

    def test_snapshot_to_dict(self) -> None:
        snap = AttentionVisionSnapshot(critical_count=2, warning_count=1)
        d = snap.to_dict()
        self.assertEqual(d["critical_count"], 2)
        self.assertEqual(d["warning_count"], 1)


# ── No-deps tests ────────────────────────────────────────────────────


class TestNoDeps(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = AttentionVisionRuntime()

    def test_detect_empty(self) -> None:
        signals = self.runtime.detect_visual_signals()
        self.assertEqual(signals, [])

    def test_critical_empty(self) -> None:
        self.assertEqual(self.runtime.critical_signals(), [])

    def test_snapshot_offline(self) -> None:
        snap = self.runtime.snapshot()
        self.assertEqual(snap.critical_count, 0)
        self.assertEqual(snap.total_attention_count, 0)

    def test_summary_zeroes(self) -> None:
        s = self.runtime.summary()
        self.assertEqual(s["critical_count"], 0)
        self.assertEqual(s["signal_count"], 0)


# ── Detection tests ──────────────────────────────────────────────────


class TestErrorDetection(unittest.TestCase):
    def test_failing_test_detected(self) -> None:
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(ERROR_SCREEN),
        )
        signals = rt.detect_visual_signals()
        types = {s.signal_type for s in signals}
        self.assertIn("failing_test", types)

    def test_failing_test_is_critical(self) -> None:
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(ERROR_SCREEN),
        )
        signals = rt.detect_visual_signals()
        for s in signals:
            if s.signal_type == "failing_test":
                self.assertEqual(s.severity, "critical")

    def test_stack_trace_detected(self) -> None:
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(STACK_TRACE_SCREEN),
        )
        signals = rt.detect_visual_signals()
        types = {s.signal_type for s in signals}
        self.assertIn("stack_trace", types)

    def test_build_failure_detected(self) -> None:
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(BUILD_FAIL_SCREEN),
        )
        signals = rt.detect_visual_signals()
        types = {s.signal_type for s in signals}
        self.assertIn("build_failure", types)

    def test_lint_warning_detected(self) -> None:
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(LINT_SCREEN),
        )
        signals = rt.detect_visual_signals()
        types = {s.signal_type for s in signals}
        self.assertIn("lint_warning", types)

    def test_lint_is_warning_severity(self) -> None:
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(LINT_SCREEN),
        )
        signals = rt.detect_visual_signals()
        for s in signals:
            if s.signal_type == "lint_warning":
                self.assertEqual(s.severity, "warning")

    def test_clean_screen_no_signals(self) -> None:
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(CLEAN_SCREEN),
        )
        signals = rt.detect_visual_signals()
        critical = [s for s in signals if s.severity == "critical"]
        self.assertEqual(critical, [])


# ── Critical filtering ───────────────────────────────────────────────


class TestCriticalFiltering(unittest.TestCase):
    def test_critical_only(self) -> None:
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(ERROR_SCREEN),
        )
        critical = rt.critical_signals()
        for s in critical:
            self.assertEqual(s.severity, "critical")

    def test_warning_only(self) -> None:
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(LINT_SCREEN),
        )
        warnings = rt.warning_signals()
        for s in warnings:
            self.assertEqual(s.severity, "warning")


# ── Merged attention ─────────────────────────────────────────────────


class TestMergedAttention(unittest.TestCase):
    def test_merge_visual_and_existing(self) -> None:
        existing_items = [
            {
                "priority": 1,
                "category": "approval",
                "severity": "high",
                "title": "Pending approval",
                "timestamp": 100.0,
            },
        ]
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(ERROR_SCREEN),
            attention_aggregation_runtime=MockAttentionAggregation(existing_items),
        )
        merged = rt.merged_attention()
        self.assertGreater(len(merged), 1)
        categories = {i.get("category") for i in merged}
        self.assertIn("visual", categories)
        self.assertIn("approval", categories)

    def test_merge_sorted_by_priority(self) -> None:
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(ERROR_SCREEN),
            attention_aggregation_runtime=MockAttentionAggregation(
                [
                    {"priority": 5, "category": "drift", "severity": "low", "timestamp": 100.0},
                ]
            ),
        )
        merged = rt.merged_attention()
        priorities = [i.get("priority", 9) for i in merged]
        self.assertEqual(priorities, sorted(priorities))

    def test_merge_without_aggregation(self) -> None:
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(ERROR_SCREEN),
        )
        merged = rt.merged_attention()
        self.assertGreater(len(merged), 0)
        for item in merged:
            self.assertEqual(item["source_system"], "attention_vision")


# ── Snapshot composition ─────────────────────────────────────────────


class TestSnapshot(unittest.TestCase):
    def test_full_snapshot(self) -> None:
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(ERROR_SCREEN),
            attention_aggregation_runtime=MockAttentionAggregation(),
            environment_awareness_runtime=MockEnvironmentAwareness(),
        )
        snap = rt.snapshot()
        self.assertGreater(snap.critical_count, 0)
        self.assertGreater(snap.generated_at, 0)
        d = snap.to_dict()
        self.assertIn("visual_signals", d)
        self.assertIn("attention_items", d)

    def test_snapshot_counts_match(self) -> None:
        rt = AttentionVisionRuntime(
            screen_awareness_runtime=MockScreenAwareness(LINT_SCREEN),
        )
        snap = rt.snapshot()
        self.assertGreater(snap.warning_count, 0)
        self.assertEqual(snap.critical_count, 0)


if __name__ == "__main__":
    unittest.main()
