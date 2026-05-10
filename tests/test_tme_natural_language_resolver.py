"""Tests for the TME Natural Language Tool Mastery Resolver.

Validates tool detection, capability detection, runtime detection,
mastery pack inference, and full resolution from natural language.
"""

import sys
import unittest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.tool_mastery_manager.tool_mastery_resolver import (
    ResolvedCapabilityMention,
    ResolvedMasteryPack,
    ResolvedToolMention,
    ToolMasteryResolution,
    detect_capability_mentions,
    detect_tool_mentions,
    explain_mastery_resolution,
    infer_required_mastery_packs,
    resolve_mastery_for_task,
    should_reuse_active_tool_context,
)


class TestDetectToolMentions(unittest.TestCase):
    def test_single_tool(self):
        results = detect_tool_mentions("I need to use discord for notifications")
        names = [r.normalized_tool_name for r in results]
        self.assertIn("discord", names)

    def test_multiple_tools(self):
        results = detect_tool_mentions("Use github and slack for the project")
        names = [r.normalized_tool_name for r in results]
        self.assertIn("github", names)
        self.assertIn("slack", names)

    def test_alias_detection(self):
        results = detect_tool_mentions("Open the gdocs file")
        names = [r.normalized_tool_name for r in results]
        self.assertIn("google_docs", names)

    def test_alias_cc(self):
        results = detect_tool_mentions("Use cc to fix the code")
        names = [r.normalized_tool_name for r in results]
        self.assertIn("claude_code", names)

    def test_no_tools(self):
        results = detect_tool_mentions("Make me a sandwich")
        self.assertEqual(results, [])

    def test_case_insensitive(self):
        results = detect_tool_mentions("I love DISCORD")
        names = [r.normalized_tool_name for r in results]
        self.assertIn("discord", names)

    def test_confidence(self):
        results = detect_tool_mentions("use docker")
        self.assertGreater(results[0].confidence, 0.5)

    def test_no_duplicate_slugs(self):
        results = detect_tool_mentions("neon postgres neon_postgres pg")
        slugs = [r.normalized_tool_name for r in results]
        self.assertEqual(slugs.count("neon_postgres"), 1)

    def test_custom_known_tools(self):
        custom = {"my_tool": ["mytool", "mt"]}
        results = detect_tool_mentions("use mytool here", custom)
        names = [r.normalized_tool_name for r in results]
        self.assertIn("my_tool", names)

    def test_longer_alias_wins(self):
        results = detect_tool_mentions("use google workspace for email")
        names = [r.normalized_tool_name for r in results]
        self.assertIn("google_workspace", names)


class TestDetectCapabilityMentions(unittest.TestCase):
    def test_software_engineering(self):
        results = detect_capability_mentions("I need to edit code in the frontend")
        names = [r.capability_name for r in results]
        self.assertIn("software_engineering", names)

    def test_deployment(self):
        results = detect_capability_mentions("Deploy the service to production")
        names = [r.capability_name for r in results]
        self.assertIn("deployment", names)

    def test_document_ingestion(self):
        results = detect_capability_mentions("Ingest documents from the drive")
        names = [r.capability_name for r in results]
        self.assertIn("document_ingestion", names)

    def test_no_capability(self):
        results = detect_capability_mentions("What time is it?")
        self.assertEqual(results, [])

    def test_tab_aware_extraction(self):
        results = detect_capability_mentions("Extract google docs tabs")
        names = [r.capability_name for r in results]
        self.assertIn("google_docs_tab_aware_extraction", names)


class TestInferRequiredMasteryPacks(unittest.TestCase):
    def test_tool_pack(self):
        packs = infer_required_mastery_packs("Use discord for messaging")
        tool_packs = [p for p in packs if p.scope == "tool"]
        self.assertTrue(any(p.tool_name == "discord" for p in tool_packs))

    def test_capability_pack(self):
        packs = infer_required_mastery_packs("Deploy the service")
        cap_packs = [p for p in packs if p.scope == "capability"]
        self.assertTrue(any(p.tool_name == "deployment" for p in cap_packs))

    def test_pack_path_format(self):
        packs = infer_required_mastery_packs("Use discord")
        tool_packs = [p for p in packs if p.scope == "tool"]
        self.assertTrue(tool_packs[0].pack_path.endswith("/SKILL.md"))

    def test_no_duplicates(self):
        packs = infer_required_mastery_packs("Use discord discord discord")
        tool_ids = [p.pack_id for p in packs if p.scope == "tool"]
        self.assertEqual(len(tool_ids), len(set(tool_ids)))


class TestResolveMasteryForTask(unittest.TestCase):
    def test_full_resolution(self):
        r = resolve_mastery_for_task("Use docker to deploy the service on the vps")
        self.assertGreater(len(r.detected_tools), 0)
        self.assertGreater(len(r.detected_capabilities), 0)
        self.assertGreater(len(r.detected_runtimes), 0)
        self.assertGreater(r.confidence, 0)
        self.assertFalse(r.needs_clarification)

    def test_no_detection_needs_clarification(self):
        r = resolve_mastery_for_task("Do the thing")
        self.assertTrue(r.needs_clarification)
        self.assertEqual(r.confidence, 0.0)

    def test_tools_only(self):
        r = resolve_mastery_for_task("Check the github repo")
        self.assertGreater(len(r.detected_tools), 0)
        self.assertFalse(r.needs_clarification)

    def test_serialization(self):
        r = resolve_mastery_for_task("Use stripe for payments")
        d = r.to_dict()
        self.assertIn("user_intent", d)
        self.assertIn("detected_tools", d)
        self.assertIn("detected_capabilities", d)
        self.assertIn("confidence", d)
        self.assertIn("needs_clarification", d)


class TestShouldReuseActiveToolContext(unittest.TestCase):
    def test_no_context_returns_false(self):
        self.assertFalse(should_reuse_active_tool_context("anything", None))

    def test_no_new_tools_returns_true(self):

        class FakeCtx:
            active_tools = ["discord"]

        self.assertTrue(should_reuse_active_tool_context("do the thing", FakeCtx()))

    def test_subset_returns_true(self):

        class FakeCtx:
            active_tools = ["discord", "github"]

        self.assertTrue(
            should_reuse_active_tool_context("check discord again", FakeCtx())
        )

    def test_new_tool_returns_false(self):

        class FakeCtx:
            active_tools = ["discord"]

        self.assertFalse(
            should_reuse_active_tool_context("now use stripe", FakeCtx())
        )


class TestExplainMasteryResolution(unittest.TestCase):
    def test_explain_with_tools(self):
        r = resolve_mastery_for_task("Use discord and docker on the vps")
        explanation = explain_mastery_resolution(r)
        self.assertIn("Tools detected", explanation)
        self.assertIn("Runtimes", explanation)

    def test_explain_empty(self):
        r = ToolMasteryResolution(user_intent="nothing")
        self.assertIn("No resolution", explain_mastery_resolution(r))

    def test_explain_needs_clarification(self):
        r = resolve_mastery_for_task("do something")
        explanation = explain_mastery_resolution(r)
        self.assertIn("clarification needed", explanation)


if __name__ == "__main__":
    unittest.main()
