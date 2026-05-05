"""Tests for Phase 96.5 adapter engine contracts."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest

from eos_ai.substrate.adapter_engine_contracts import (
    AdapterCapabilityMap,
    AdapterProfile,
    AdapterRegistryEntry,
    AdapterSafetyPolicy,
    AdapterStatus,
    AdapterType,
    ToolMasteryPack,
)


class TestAdapterType(unittest.TestCase):
    """Tests for AdapterType enum."""

    def test_has_16_values(self) -> None:
        self.assertEqual(len(AdapterType), 16)

    def test_expected_members(self) -> None:
        expected = {
            "API",
            "SDK",
            "CLI",
            "MCP",
            "COMPUTER_USE",
            "BROWSER_AUTOMATION",
            "BROWSER_EXTENSION",
            "RPA_DESKTOP_AUTOMATION",
            "LOCAL_SYNC",
            "LOCAL_EXPORT_ARCHIVE",
            "DATABASE_DIRECT",
            "WEBHOOK_EVENT_STREAM",
            "FILE_PARSER",
            "MOBILE_AUTOMATION",
            "MANUAL_HUMAN_ASSISTED",
            "HYBRID",
        }
        self.assertEqual(set(AdapterType.__members__.keys()), expected)


class TestAdapterStatus(unittest.TestCase):
    """Tests for AdapterStatus enum."""

    def test_has_9_values(self) -> None:
        self.assertEqual(len(AdapterStatus), 9)

    def test_expected_members(self) -> None:
        expected = {
            "DISCOVERED",
            "CANDIDATE",
            "GENERATED",
            "TESTED",
            "AVAILABLE",
            "PREFERRED",
            "FALLBACK",
            "DEPRECATED",
            "BLOCKED",
        }
        self.assertEqual(set(AdapterStatus.__members__.keys()), expected)


class TestAdapterProfile(unittest.TestCase):
    """Tests for AdapterProfile serialization."""

    def test_serializes_correctly(self) -> None:
        p = AdapterProfile(
            adapter_id="gws_api",
            adapter_type=AdapterType.API,
            source_system="Google Workspace",
        )
        d = p.to_dict()
        self.assertEqual(d["adapter_id"], "gws_api")
        self.assertEqual(d["adapter_type"], "api")
        self.assertEqual(d["source_system"], "Google Workspace")
        self.assertIn("capabilities", d)
        self.assertIn("current_status", d)


class TestAdapterCapabilityMap(unittest.TestCase):
    """Tests for AdapterCapabilityMap serialization."""

    def test_serializes_correctly(self) -> None:
        m = AdapterCapabilityMap(
            adapter_id="gws_api",
            can_read=True,
            can_write=False,
        )
        d = m.to_dict()
        self.assertEqual(d["adapter_id"], "gws_api")
        self.assertTrue(d["can_read"])
        self.assertFalse(d["can_write"])
        self.assertIn("mutation_risk", d)


class TestAdapterSafetyPolicy(unittest.TestCase):
    """Tests for AdapterSafetyPolicy serialization."""

    def test_serializes_correctly(self) -> None:
        s = AdapterSafetyPolicy(
            adapter_id="gws_api",
            read_only_enforced=True,
            no_secret_exposure=True,
        )
        d = s.to_dict()
        self.assertEqual(d["adapter_id"], "gws_api")
        self.assertTrue(d["read_only_enforced"])
        self.assertTrue(d["no_secret_exposure"])
        self.assertIn("blocked_actions", d)


class TestToolMasteryPack(unittest.TestCase):
    """Tests for ToolMasteryPack."""

    def test_exists_and_serializes(self) -> None:
        pack = ToolMasteryPack(
            adapter_id="claude_code",
            tool_name="Claude Code CLI",
            best_practices=["read before write", "verify imports"],
            common_workflows=["pre-change", "pre-done"],
            failure_modes=["never skip tests"],
            edge_cases=["large repos"],
            quality_standards=["100% import check"],
        )
        d = pack.to_dict()
        self.assertEqual(d["adapter_id"], "claude_code")
        self.assertEqual(d["tool_name"], "Claude Code CLI")
        self.assertEqual(d["best_practices_count"], 2)
        self.assertEqual(d["common_workflows_count"], 2)
        self.assertEqual(d["failure_modes_count"], 1)
        self.assertEqual(d["edge_cases_count"], 1)
        self.assertEqual(d["quality_standards_count"], 1)
        self.assertIn("operating_manual_ref", d)
        self.assertIn("skill_file_ref", d)
        self.assertIn("examples_count", d)
        self.assertIn("prompts_count", d)

    def test_has_expected_fields(self) -> None:
        pack = ToolMasteryPack(adapter_id="test")
        required_fields = {
            "adapter_id",
            "tool_name",
            "version_scope",
            "best_practices",
            "common_workflows",
            "anti_patterns",
            "failure_modes",
            "recovery_playbooks",
            "hidden_features",
            "api_defaults_and_traps",
            "completeness_requirements",
            "validation_checklist",
            "edge_cases",
            "quality_standards",
            "operating_manual_ref",
            "skill_file_ref",
            "examples",
            "prompts",
            "last_verified",
            "provenance_notes",
        }
        actual_fields = set(pack.__dataclass_fields__.keys())
        self.assertTrue(required_fields.issubset(actual_fields))


class TestAdapterRegistryEntry(unittest.TestCase):
    """Tests for AdapterRegistryEntry."""

    def _make_profile(self) -> AdapterProfile:
        return AdapterProfile(
            adapter_id="test_adapter",
            adapter_type=AdapterType.API,
        )

    def test_has_tool_mastery_field(self) -> None:
        entry = AdapterRegistryEntry(profile=self._make_profile())
        self.assertIsNone(entry.tool_mastery)

    def test_has_has_tool_mastery_field(self) -> None:
        entry = AdapterRegistryEntry(profile=self._make_profile())
        self.assertFalse(entry.has_tool_mastery)

    def test_to_dict_includes_tool_mastery(self) -> None:
        pack = ToolMasteryPack(adapter_id="test_adapter", tool_name="Test")
        entry = AdapterRegistryEntry(
            profile=self._make_profile(),
            tool_mastery=pack,
            has_tool_mastery=True,
        )
        d = entry.to_dict()
        self.assertIn("tool_mastery", d)
        self.assertIsNotNone(d["tool_mastery"])
        self.assertEqual(d["tool_mastery"]["adapter_id"], "test_adapter")
        self.assertTrue(d["has_tool_mastery"])

    def test_to_dict_tool_mastery_none(self) -> None:
        entry = AdapterRegistryEntry(profile=self._make_profile())
        d = entry.to_dict()
        self.assertIn("tool_mastery", d)
        self.assertIsNone(d["tool_mastery"])


if __name__ == "__main__":
    unittest.main()
