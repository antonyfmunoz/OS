"""Tests for the TME Active Tool Context.

Validates context creation, updating, continuation/switch decisions,
and serialization.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.tool_mastery_manager.active_tool_context import (
    ActiveToolContext,
    create_active_tool_context,
    should_continue_context,
    should_switch_context,
    summarize_active_tool_context,
    update_active_tool_context,
)
from core.tool_mastery_manager.tool_mastery_resolver import (
    ResolvedCapabilityMention,
    ResolvedMasteryPack,
    ResolvedToolMention,
    ToolMasteryResolution,
)


def _make_resolution(
    tools: list[str] | None = None,
    capabilities: list[str] | None = None,
    runtimes: list[str] | None = None,
    packs: list[str] | None = None,
) -> ToolMasteryResolution:
    return ToolMasteryResolution(
        user_intent="test",
        detected_tools=[
            ResolvedToolMention(raw_mention=t, normalized_tool_name=t)
            for t in (tools or [])
        ],
        detected_capabilities=[
            ResolvedCapabilityMention(capability_name=c)
            for c in (capabilities or [])
        ],
        detected_runtimes=runtimes or [],
        required_mastery_packs=[
            ResolvedMasteryPack(pack_id=f"pack:{p}", tool_name=p)
            for p in (packs or [])
        ],
    )


class TestCreateActiveToolContext(unittest.TestCase):
    def test_basic_creation(self):
        resolution = _make_resolution(
            tools=["discord"],
            capabilities=["message_sending"],
            runtimes=["vps"],
            packs=["discord"],
        )
        ctx = create_active_tool_context("Send a message", resolution, task_id="t1")
        self.assertEqual(ctx.task_id, "t1")
        self.assertEqual(ctx.task_summary, "Send a message")
        self.assertIn("discord", ctx.active_tools)
        self.assertIn("message_sending", ctx.active_capabilities)
        self.assertIn("vps", ctx.active_runtimes)
        self.assertIn("pack:discord", ctx.active_mastery_packs)
        self.assertTrue(ctx.started_at)
        self.assertTrue(ctx.last_updated_at)

    def test_empty_resolution(self):
        resolution = _make_resolution()
        ctx = create_active_tool_context("Do nothing", resolution)
        self.assertEqual(ctx.active_tools, [])
        self.assertEqual(ctx.active_capabilities, [])


class TestUpdateActiveToolContext(unittest.TestCase):
    def test_adds_new_tools(self):
        resolution1 = _make_resolution(tools=["discord"])
        ctx = create_active_tool_context("task", resolution1)
        self.assertEqual(ctx.active_tools, ["discord"])

        resolution2 = _make_resolution(tools=["github"])
        ctx = update_active_tool_context(ctx, resolution2)
        self.assertIn("discord", ctx.active_tools)
        self.assertIn("github", ctx.active_tools)

    def test_no_duplicates(self):
        resolution1 = _make_resolution(tools=["discord"])
        ctx = create_active_tool_context("task", resolution1)

        resolution2 = _make_resolution(tools=["discord"])
        ctx = update_active_tool_context(ctx, resolution2)
        self.assertEqual(ctx.active_tools.count("discord"), 1)

    def test_updates_timestamp(self):
        resolution = _make_resolution(tools=["discord"])
        ctx = create_active_tool_context("task", resolution)
        original_time = ctx.last_updated_at

        resolution2 = _make_resolution(tools=["github"])
        ctx = update_active_tool_context(ctx, resolution2)
        self.assertNotEqual(ctx.last_updated_at, original_time)


class TestShouldContinueContext(unittest.TestCase):
    def test_no_active_tools_returns_false(self):
        ctx = ActiveToolContext()
        self.assertFalse(should_continue_context(ctx, "anything"))

    def test_no_new_tools_returns_true(self):
        ctx = ActiveToolContext(active_tools=["discord"])
        self.assertTrue(should_continue_context(ctx, "send another message"))

    def test_subset_tools_returns_true(self):
        ctx = ActiveToolContext(active_tools=["discord", "github"])
        self.assertTrue(should_continue_context(ctx, "check discord"))

    def test_new_tool_returns_false(self):
        ctx = ActiveToolContext(active_tools=["discord"])
        self.assertFalse(should_continue_context(ctx, "now use stripe"))


class TestShouldSwitchContext(unittest.TestCase):
    def test_no_new_tools_returns_false(self):
        ctx = ActiveToolContext(active_tools=["discord"])
        resolution = _make_resolution()
        self.assertFalse(should_switch_context(ctx, resolution))

    def test_disjoint_tools_returns_true(self):
        ctx = ActiveToolContext(active_tools=["discord"])
        resolution = _make_resolution(tools=["stripe"])
        self.assertTrue(should_switch_context(ctx, resolution))

    def test_overlapping_tools_returns_false(self):
        ctx = ActiveToolContext(active_tools=["discord", "github"])
        resolution = _make_resolution(tools=["discord"])
        self.assertFalse(should_switch_context(ctx, resolution))

    def test_disjoint_capabilities_returns_true(self):
        ctx = ActiveToolContext(
            active_tools=["discord"],
            active_capabilities=["message_sending"],
        )
        resolution = _make_resolution(
            tools=["discord"], capabilities=["deployment"]
        )
        self.assertTrue(should_switch_context(ctx, resolution))


class TestSummarize(unittest.TestCase):
    def test_full_summary(self):
        ctx = ActiveToolContext(
            task_summary="Deploy service",
            active_tools=["docker"],
            active_capabilities=["deployment"],
            active_mastery_packs=["pack:docker"],
            active_runtimes=["vps"],
            active_governance_constraints=["no-prod-write"],
        )
        summary = summarize_active_tool_context(ctx)
        self.assertIn("Deploy service", summary)
        self.assertIn("docker", summary)
        self.assertIn("deployment", summary)
        self.assertIn("vps", summary)
        self.assertIn("no-prod-write", summary)

    def test_empty_context(self):
        ctx = ActiveToolContext()
        self.assertEqual(summarize_active_tool_context(ctx), "No active context")


class TestSerialization(unittest.TestCase):
    def test_to_dict(self):
        resolution = _make_resolution(tools=["discord"], runtimes=["vps"])
        ctx = create_active_tool_context("task", resolution, task_id="t1")
        d = ctx.to_dict()
        self.assertEqual(d["task_id"], "t1")
        self.assertIn("discord", d["active_tools"])
        self.assertIn("vps", d["active_runtimes"])
        self.assertIn("started_at", d)
        self.assertIn("last_updated_at", d)
        self.assertEqual(d["reuse_until_condition"], "task_change_or_tool_switch")


if __name__ == "__main__":
    unittest.main()
