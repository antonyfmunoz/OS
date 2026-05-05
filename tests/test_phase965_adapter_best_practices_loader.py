"""Tests for Phase 96.5 adapter best practices loader."""

import sys

sys.path.insert(0, "/opt/OS")

import os
import tempfile
import unittest

from eos_ai.substrate.adapter_best_practices_loader import (
    AdapterBestPracticesPolicy,
    build_adapter_policy_from_skill,
    build_tool_mastery_pack_from_skill,
    extract_adapter_relevant_rules,
    load_best_practices_skill,
    locate_claude_code_best_practices_skill,
    merge_skill_policy_with_adapter_quality_gate,
)


_MOCK_SKILL_CONTENT = """\
# Claude Code Best Practices

## Before any change
- Read the module you are changing
- Check if what you are building exists
- Understand where it fits architecturally

## Before declaring done
- Import check passes
- Relevant test passes
- Deployment command provided

## Never do
- Never hardcode API keys or secrets
- Never skip Neon registration for agents
- Never deploy without import verification

## Risk classes for code changes
- LOW: Adding new files, new methods
- MEDIUM: Modifying existing methods
- HIGH: Changing core infrastructure
- CRITICAL: Schema migrations, dropping tables
"""


class TestLocateSkill(unittest.TestCase):
    """Tests for locate_claude_code_best_practices_skill."""

    def test_finds_mock_skill_file(self) -> None:
        tmpdir = tempfile.mkdtemp()
        try:
            skill_path = os.path.join(tmpdir, "claude-code-best-practices.md")
            with open(skill_path, "w") as f:
                f.write(_MOCK_SKILL_CONTENT)
            result = locate_claude_code_best_practices_skill(search_roots=[tmpdir])
            self.assertIsNotNone(result)
            self.assertEqual(result, skill_path)
        finally:
            os.unlink(skill_path)
            os.rmdir(tmpdir)

    def test_returns_none_when_empty_dirs(self) -> None:
        tmpdir = tempfile.mkdtemp()
        try:
            result = locate_claude_code_best_practices_skill(search_roots=[tmpdir])
            self.assertIsNone(result)
        finally:
            os.rmdir(tmpdir)


class TestLoadBestPracticesSkill(unittest.TestCase):
    """Tests for load_best_practices_skill."""

    def test_loads_file_content(self) -> None:
        tmpdir = tempfile.mkdtemp()
        try:
            skill_path = os.path.join(tmpdir, "test-skill.md")
            with open(skill_path, "w") as f:
                f.write(_MOCK_SKILL_CONTENT)
            content = load_best_practices_skill(skill_path)
            self.assertIn("Claude Code Best Practices", content)
            self.assertIn("Before any change", content)
        finally:
            os.unlink(skill_path)
            os.rmdir(tmpdir)


class TestExtractAdapterRelevantRules(unittest.TestCase):
    """Tests for extract_adapter_relevant_rules."""

    def test_extracts_matching_lines(self) -> None:
        rules = extract_adapter_relevant_rules(_MOCK_SKILL_CONTENT)
        self.assertGreater(len(rules), 0)
        lower_rules = [r.lower() for r in rules]
        has_keyword = any(
            kw in rule
            for rule in lower_rules
            for kw in [
                "before any change",
                "never do",
                "hardcode",
                "secret",
                "import check",
                "test pass",
                "risk class",
                "neon registration",
            ]
        )
        self.assertTrue(has_keyword)


class TestBuildAdapterPolicyFromSkill(unittest.TestCase):
    """Tests for build_adapter_policy_from_skill."""

    def test_produces_policy(self) -> None:
        policy = build_adapter_policy_from_skill(_MOCK_SKILL_CONTENT)
        self.assertIsInstance(policy, AdapterBestPracticesPolicy)
        self.assertGreater(len(policy.rules), 0)

    def test_populates_sections(self) -> None:
        policy = build_adapter_policy_from_skill(_MOCK_SKILL_CONTENT)
        self.assertGreater(len(policy.pre_change_checks), 0)
        self.assertGreater(len(policy.pre_done_checks), 0)
        self.assertGreater(len(policy.never_do), 0)
        self.assertGreater(len(policy.risk_classes), 0)


class TestMergeSkillPolicy(unittest.TestCase):
    """Tests for merge_skill_policy_with_adapter_quality_gate."""

    def test_merges_correctly(self) -> None:
        policy = build_adapter_policy_from_skill(_MOCK_SKILL_CONTENT)
        merged = merge_skill_policy_with_adapter_quality_gate(policy)
        self.assertGreater(len(merged.merged_rules), 0)
        self.assertGreater(len(merged.skill_rules), 0)
        self.assertGreater(len(merged.default_rules), 0)
        # merged contains all skill + default rules (deduplicated)
        self.assertGreaterEqual(
            len(merged.merged_rules),
            max(len(merged.skill_rules), len(merged.default_rules)),
        )


class TestBuildToolMasteryPackFromSkill(unittest.TestCase):
    """Tests for build_tool_mastery_pack_from_skill."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.skill_path = os.path.join(self.tmpdir, "test-skill.md")
        with open(self.skill_path, "w") as f:
            f.write(_MOCK_SKILL_CONTENT)

    def tearDown(self) -> None:
        os.unlink(self.skill_path)
        os.rmdir(self.tmpdir)

    def test_returns_tool_mastery_pack(self) -> None:
        from eos_ai.substrate.adapter_engine_contracts import ToolMasteryPack

        pack = build_tool_mastery_pack_from_skill(
            adapter_id="claude_code",
            tool_name="Claude Code CLI",
            skill_path=self.skill_path,
        )
        self.assertIsInstance(pack, ToolMasteryPack)

    def test_correct_adapter_id_and_tool_name(self) -> None:
        pack = build_tool_mastery_pack_from_skill(
            adapter_id="claude_code",
            tool_name="Claude Code CLI",
            skill_path=self.skill_path,
        )
        self.assertEqual(pack.adapter_id, "claude_code")
        self.assertEqual(pack.tool_name, "Claude Code CLI")

    def test_populates_best_practices(self) -> None:
        pack = build_tool_mastery_pack_from_skill(
            adapter_id="claude_code",
            tool_name="Claude Code CLI",
            skill_path=self.skill_path,
        )
        self.assertGreater(len(pack.best_practices), 0)

    def test_populates_workflows(self) -> None:
        pack = build_tool_mastery_pack_from_skill(
            adapter_id="claude_code",
            tool_name="Claude Code CLI",
            skill_path=self.skill_path,
        )
        self.assertGreater(len(pack.common_workflows), 0)

    def test_populates_failure_modes(self) -> None:
        pack = build_tool_mastery_pack_from_skill(
            adapter_id="claude_code",
            tool_name="Claude Code CLI",
            skill_path=self.skill_path,
        )
        self.assertGreater(len(pack.failure_modes), 0)


if __name__ == "__main__":
    unittest.main()
