"""Tests for C21.2 — Visual Context Runtime."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.workstation.visual_context_runtime import (
    ContextBinding,
    ContextBindingDepth,
    VisualContextRuntime,
    VisualContextSnapshot,
)


# ── Mock helpers ──────────────────────────────────────────────────────


class _MockIdeContext:
    """MetaIdeContextRuntime stand-in with goals and decisions."""

    class _Snap:
        def __init__(self) -> None:
            self.related_goals = [
                {"title": "Ship MVP", "label": "ship-mvp"},
                {"title": "Close first sale"},
            ]
            self.related_decisions = [
                {"title": "Use deterministic-first"},
            ]

        def to_dict(self) -> dict:
            return {
                "related_goals": self.related_goals,
                "related_decisions": self.related_decisions,
                "repo": "OS",
                "branch": "main",
            }

    def context(self):  # noqa: ANN201
        return self._Snap()


class _MockScreenAwareness:
    """ScreenAwarenessRuntime stand-in returning full screen state."""

    def __init__(
        self, *, include_app: bool = True, include_repo: bool = True, include_file: bool = True
    ) -> None:
        self._include_app = include_app
        self._include_repo = include_repo
        self._include_file = include_file

    def current_screen(self) -> dict:
        result: dict = {
            "active_window": {"title": "execution_fabric_runtime.py — VS Code"},
        }
        if self._include_app:
            result["focused_application"] = {
                "app_name": "VS Code",
                "category": "ide",
                "window_title": "execution_fabric_runtime.py — VS Code",
            }
        if self._include_repo:
            result["repository_context"] = {
                "repo_name": "OS",
                "branch": "main",
                "working_directory": "substrate/workstation",
            }
        if self._include_file:
            result["file_context"] = {
                "file_path": "substrate/workstation/execution_fabric_runtime.py",
            }
        return result


class _MockWorkspace:
    """WorkspaceAwarenessRuntime stand-in."""

    class _Snap:
        def to_dict(self) -> dict:
            return {
                "repo": "OS",
                "branch": "main",
                "directory": "substrate/workstation",
                "device": "srv1500858",
                "project": "UMH",
            }

    def detect_active_workspace(self):  # noqa: ANN201
        return self._Snap()


# ── Type tests ────────────────────────────────────────────────────────


class TestTypes(unittest.TestCase):
    def test_context_binding_depth_values(self) -> None:
        self.assertEqual(ContextBindingDepth.SCREEN.value, "screen")
        self.assertEqual(ContextBindingDepth.APPLICATION.value, "application")
        self.assertEqual(ContextBindingDepth.REPOSITORY.value, "repository")
        self.assertEqual(ContextBindingDepth.FILE.value, "file")
        self.assertEqual(ContextBindingDepth.WORK.value, "work")

    def test_context_binding_defaults(self) -> None:
        b = ContextBinding()
        self.assertEqual(b.depth, "screen")
        self.assertEqual(b.application, "")
        self.assertEqual(b.repository, "")
        self.assertEqual(b.goals, [])
        self.assertEqual(b.confidence, 0.0)

    def test_context_binding_to_dict(self) -> None:
        b = ContextBinding(application="VS Code", depth="application")
        d = b.to_dict()
        self.assertEqual(d["application"], "VS Code")
        self.assertEqual(d["depth"], "application")
        self.assertIn("goals", d)
        self.assertIn("decisions", d)

    def test_visual_context_snapshot_defaults(self) -> None:
        s = VisualContextSnapshot()
        self.assertEqual(s.binding_depth, "screen")
        self.assertEqual(s.binding, {})
        self.assertIsInstance(s.to_dict(), dict)


# ── No-deps tests ─────────────────────────────────────────────────────


class TestNoDeps(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = VisualContextRuntime()

    def test_resolve_context_graceful(self) -> None:
        binding = self.runtime.resolve_context()
        self.assertIsInstance(binding, ContextBinding)
        self.assertEqual(binding.depth, "screen")

    def test_binding_depth_graceful(self) -> None:
        depth = self.runtime.binding_depth()
        self.assertEqual(depth, ContextBindingDepth.SCREEN)

    def test_continue_work_graceful(self) -> None:
        result = self.runtime.continue_work()
        self.assertIn("action", result)
        self.assertEqual(result["action"], "continue")

    def test_snapshot_graceful(self) -> None:
        snap = self.runtime.snapshot()
        self.assertIsInstance(snap, VisualContextSnapshot)

    def test_summary_graceful(self) -> None:
        s = self.runtime.summary()
        self.assertIn("depth", s)


# ── Waterfall resolution tests ────────────────────────────────────────


class TestWaterfallResolution(unittest.TestCase):
    def test_full_depth_reaches_work(self) -> None:
        rt = VisualContextRuntime(
            screen_awareness_runtime=_MockScreenAwareness(),
            meta_ide_context_runtime=_MockIdeContext(),
            workspace_awareness_runtime=_MockWorkspace(),
        )
        binding = rt.resolve_context()
        self.assertEqual(binding.depth, "work")
        self.assertEqual(binding.application, "VS Code")
        self.assertEqual(binding.repository, "OS")
        self.assertEqual(binding.branch, "main")
        self.assertIn("execution_fabric_runtime.py", binding.file_path)
        self.assertTrue(len(binding.goals) > 0)
        self.assertGreaterEqual(binding.confidence, 0.9)

    def test_no_ide_stops_at_file(self) -> None:
        rt = VisualContextRuntime(
            screen_awareness_runtime=_MockScreenAwareness(),
            meta_ide_context_runtime=None,
            workspace_awareness_runtime=_MockWorkspace(),
        )
        binding = rt.resolve_context()
        self.assertEqual(binding.depth, "file")

    def test_no_file_stops_at_repository(self) -> None:
        rt = VisualContextRuntime(
            screen_awareness_runtime=_MockScreenAwareness(include_file=False),
            meta_ide_context_runtime=_MockIdeContext(),
            workspace_awareness_runtime=_MockWorkspace(),
        )
        binding = rt.resolve_context()
        # With repo and IDE context, should reach WORK depth
        self.assertIn(binding.depth, ["repository", "work"])
        self.assertEqual(binding.repository, "OS")

    def test_no_repo_stops_at_application(self) -> None:
        rt = VisualContextRuntime(
            screen_awareness_runtime=_MockScreenAwareness(include_repo=False, include_file=False),
            workspace_awareness_runtime=None,
        )
        binding = rt.resolve_context()
        self.assertEqual(binding.depth, "application")
        self.assertEqual(binding.application, "VS Code")

    def test_no_app_stays_at_screen(self) -> None:
        rt = VisualContextRuntime(
            screen_awareness_runtime=_MockScreenAwareness(
                include_app=False, include_repo=False, include_file=False
            ),
        )
        binding = rt.resolve_context()
        self.assertEqual(binding.depth, "screen")

    def test_workspace_fallback_for_repo(self) -> None:
        """When screen has no repo but workspace does, still reaches REPOSITORY."""
        rt = VisualContextRuntime(
            screen_awareness_runtime=_MockScreenAwareness(include_repo=False, include_file=False),
            workspace_awareness_runtime=_MockWorkspace(),
        )
        binding = rt.resolve_context()
        self.assertIn(binding.depth, ["repository", "work"])
        self.assertEqual(binding.repository, "OS")


# ── Continue work tests ───────────────────────────────────────────────


class TestContinueWork(unittest.TestCase):
    def test_full_binding_suggestion(self) -> None:
        rt = VisualContextRuntime(
            screen_awareness_runtime=_MockScreenAwareness(),
            meta_ide_context_runtime=_MockIdeContext(),
            workspace_awareness_runtime=_MockWorkspace(),
        )
        result = rt.continue_work()
        self.assertEqual(result["action"], "continue")
        self.assertIn("binding", result)
        self.assertIn("suggestion", result)
        self.assertIn("execution_fabric_runtime.py", result["suggestion"])

    def test_shallow_binding_suggestion(self) -> None:
        rt = VisualContextRuntime(
            screen_awareness_runtime=_MockScreenAwareness(
                include_app=False, include_repo=False, include_file=False
            ),
        )
        result = rt.continue_work()
        self.assertIn("Screen visible", result["suggestion"])


# ── Snapshot tests ────────────────────────────────────────────────────


class TestSnapshot(unittest.TestCase):
    def test_snapshot_with_mocks(self) -> None:
        rt = VisualContextRuntime(
            screen_awareness_runtime=_MockScreenAwareness(),
            meta_ide_context_runtime=_MockIdeContext(),
            workspace_awareness_runtime=_MockWorkspace(),
        )
        snap = rt.snapshot()
        d = snap.to_dict()
        self.assertEqual(d["binding_depth"], "work")
        self.assertIn("binding", d)
        self.assertIn("meta_ide_context", d)
        self.assertIn("screen_source", d)
        self.assertGreater(d["generated_at"], 0)


# ── Campaign inference tests ──────────────────────────────────────────


class TestCampaignInference(unittest.TestCase):
    def test_no_campaign_in_path(self) -> None:
        rt = VisualContextRuntime(
            screen_awareness_runtime=_MockScreenAwareness(),
        )
        binding = rt.resolve_context()
        # Standard path has no c-prefix pattern
        self.assertEqual(binding.campaign, "")

    def test_summary_includes_campaign(self) -> None:
        rt = VisualContextRuntime(
            screen_awareness_runtime=_MockScreenAwareness(),
            meta_ide_context_runtime=_MockIdeContext(),
            workspace_awareness_runtime=_MockWorkspace(),
        )
        s = rt.summary()
        self.assertIn("campaign", s)
        self.assertIn("depth", s)
        self.assertIn("confidence", s)


if __name__ == "__main__":
    unittest.main()
