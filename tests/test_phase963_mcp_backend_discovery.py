"""Tests for eos_ai/substrate/mcp_backend_discovery.py (Phase 96.3)."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from eos_ai.substrate.extraction_backend_contracts import (
    BackendIndependenceLevel,
    MCPSubtype,
)
from eos_ai.substrate.mcp_backend_contracts import MCPToolProfile
from eos_ai.substrate.mcp_backend_discovery import (
    build_mcp_discovery_plan,
    build_mcp_discovery_report,
    classify_available_mcp_tool,
    parse_mcp_tool_manifest,
    register_mcp_candidate_backend,
)


class TestBuildMCPDiscoveryPlan(unittest.TestCase):
    def test_has_5_candidate_subtypes(self) -> None:
        plan = build_mcp_discovery_plan()
        self.assertEqual(len(plan.candidate_subtypes), 5)

    def test_has_10_discovery_steps(self) -> None:
        plan = build_mcp_discovery_plan()
        self.assertEqual(len(plan.discovery_steps), 10)

    def test_has_7_evaluation_criteria(self) -> None:
        plan = build_mcp_discovery_plan()
        self.assertEqual(len(plan.evaluation_criteria), 7)


class TestParseMCPToolManifest(unittest.TestCase):
    def test_parses_manifest_dict(self) -> None:
        manifest = {
            "name": "gdocs-reader",
            "server": "gdocs-mcp",
            "capabilities": ["read_metadata", "read_body"],
            "data_access_channel": "google_api",
            "requires_auth": True,
            "can_read_metadata": True,
            "can_read_body": True,
            "can_read_tabs": False,
            "can_read_child_tabs": False,
            "can_emit_canonical_records": False,
            "notes": "basic reader",
        }
        profile = parse_mcp_tool_manifest(manifest)
        self.assertEqual(profile.tool_name, "gdocs-reader")
        self.assertEqual(profile.server_name, "gdocs-mcp")
        self.assertEqual(profile.declared_capabilities, ["read_metadata", "read_body"])
        self.assertTrue(profile.requires_auth)
        self.assertTrue(profile.can_read_body)
        self.assertFalse(profile.can_read_tabs)


class TestClassifyAvailableMCPTool(unittest.TestCase):
    def test_classifies_from_manifest(self) -> None:
        manifest = {
            "name": "test-tool",
            "server": "test-server",
            "capabilities": ["read_metadata"],
            "notes": "internal extractor wrapper",
        }
        profile = classify_available_mcp_tool(manifest)
        self.assertIsInstance(profile, MCPToolProfile)
        self.assertEqual(profile.tool_name, "test-tool")


class TestRegisterMCPCandidateBackend(unittest.TestCase):
    def test_returns_candidate_registered(self) -> None:
        profile = MCPToolProfile(
            tool_name="test-candidate",
            server_name="test-server",
        )
        result = register_mcp_candidate_backend(profile)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "candidate_registered")
        self.assertEqual(result["tool_name"], "test-candidate")


class TestBuildMCPDiscoveryReport(unittest.TestCase):
    def test_counts_independent_interface_blocked(self) -> None:
        # Independent: API connector (level 1+)
        independent_profile = MCPToolProfile(
            tool_name="api-connector",
            server_name="s1",
            mcp_subtype=MCPSubtype.MCP_API_CONNECTOR,
            independence_level=BackendIndependenceLevel.LEVEL_1_DIFFERENT_IMPLEMENTATION_SAME_PROVIDER_API,
        )
        # Interface-only: MCP_AS_INTERFACE (level 0)
        interface_profile = MCPToolProfile(
            tool_name="interface-wrap",
            server_name="s2",
            mcp_subtype=MCPSubtype.MCP_AS_INTERFACE,
            independence_level=BackendIndependenceLevel.LEVEL_0_INTERFACE_WRAPPER,
        )
        # Blocked: browser automation
        blocked_profile = MCPToolProfile(
            tool_name="browser-auto",
            server_name="s3",
            mcp_subtype=MCPSubtype.MCP_BROWSER_AUTOMATION,
            independence_level=BackendIndependenceLevel.LEVEL_1_DIFFERENT_IMPLEMENTATION_SAME_PROVIDER_API,
        )
        report = build_mcp_discovery_report(
            [independent_profile, interface_profile, blocked_profile]
        )
        self.assertEqual(report.tools_classified, 3)
        self.assertEqual(report.independent_backends, 1)
        self.assertEqual(report.interface_only, 1)
        self.assertEqual(report.blocked, 1)


if __name__ == "__main__":
    unittest.main()
