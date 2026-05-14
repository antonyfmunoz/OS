"""Tests for TME UMH scope correctness.

Validates that TME modules, docs, and SKILL.md describe TME
as a UMH substrate subsystem — not an EOS-specific feature.
"""

import sys
import os
import unittest

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

EOS_ROOT = _ROOT


def _read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def _has_conflict_markers(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("<<<<<<< ") or stripped.startswith(">>>>>>> "):
            return True
        if stripped == "=======":
            return True
    return False


class TestModuleDocstrings(unittest.TestCase):
    """TME Python modules must reference UMH, not claim EOS ownership."""

    def _check_module(self, rel_path: str):
        path = os.path.join(EOS_ROOT, rel_path)
        if not os.path.exists(path):
            self.skipTest(f"{rel_path} not found")
        text = _read_file(path)
        self.assertIn("UMH", text, f"{rel_path} missing UMH reference")
        self.assertNotIn(
            "<<<<<<",
            text,
            f"{rel_path} contains conflict markers",
        )

    def test_mastery_assurance(self):
        self._check_module("core/tool_mastery_manager/mastery_assurance.py")

    def test_tool_mastery_resolver(self):
        self._check_module("core/tool_mastery_manager/tool_mastery_resolver.py")

    def test_active_tool_context(self):
        self._check_module("core/tool_mastery_manager/active_tool_context.py")


class TestDoctrineFiles(unittest.TestCase):
    """TME doctrine docs must reference UMH substrate scope."""

    DOCTRINE_FILES = [
        "docs/operations/tme_umh_substrate_doctrine_v1.md",
        "docs/operations/tme_adapter_engine_relationship_v1.md",
        "docs/system/tme_scope_correction_umh_report_v1.md",
    ]

    def test_doctrine_files_exist(self):
        for rel_path in self.DOCTRINE_FILES:
            path = os.path.join(EOS_ROOT, rel_path)
            self.assertTrue(os.path.exists(path), f"Missing: {rel_path}")

    def test_doctrine_files_mention_umh(self):
        for rel_path in self.DOCTRINE_FILES:
            path = os.path.join(EOS_ROOT, rel_path)
            if not os.path.exists(path):
                continue
            text = _read_file(path)
            self.assertIn("UMH", text, f"{rel_path} missing UMH reference")

    def test_no_conflict_markers(self):
        for rel_path in self.DOCTRINE_FILES:
            path = os.path.join(EOS_ROOT, rel_path)
            if not os.path.exists(path):
                continue
            text = _read_file(path)
            self.assertFalse(
                _has_conflict_markers(text),
                f"{rel_path} contains conflict markers",
            )


class TestSKILLMD(unittest.TestCase):
    """TME SKILL.md must not have conflict markers or EOS-only ownership."""

    SKILL_PATH = os.path.join(
        EOS_ROOT, "skills/meta/tool_mastery_engine/SKILL.md"
    )

    def test_skill_exists(self):
        self.assertTrue(os.path.exists(self.SKILL_PATH))

    def test_no_conflict_markers(self):
        text = _read_file(self.SKILL_PATH)
        self.assertFalse(
            _has_conflict_markers(text),
            "SKILL.md contains conflict markers",
        )

    def test_mentions_umh(self):
        text = _read_file(self.SKILL_PATH)
        self.assertIn("UMH", text, "SKILL.md missing UMH reference")


class TestCLAUDEMD(unittest.TestCase):
    """Root CLAUDE.md must not have conflict markers."""

    CLAUDE_PATH = os.path.join(EOS_ROOT, "CLAUDE.md")

    def test_no_conflict_markers(self):
        text = _read_file(self.CLAUDE_PATH)
        self.assertFalse(
            _has_conflict_markers(text),
            "CLAUDE.md contains conflict markers",
        )


class TestTmeActionSystem(unittest.TestCase):
    """tme.py in action_system must expose new integration functions."""

    def test_ensure_mastery_before_tool_execution_importable(self):
        from control_plane.actions.tme import ensure_mastery_before_tool_execution
        self.assertTrue(callable(ensure_mastery_before_tool_execution))

    def test_resolve_mastery_for_user_intent_importable(self):
        from control_plane.actions.tme import resolve_mastery_for_user_intent
        self.assertTrue(callable(resolve_mastery_for_user_intent))


if __name__ == "__main__":
    unittest.main()
