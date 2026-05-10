"""Tests for Phase 96.5 adapter generation contracts."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from eos_ai.substrate.adapter_generation_contracts import (
    AdapterGenerationPlan,
    AdapterGenerationRequest,
    AdapterGenerationResult,
    AdapterGenerationStage,
)


class TestAdapterGenerationStage(unittest.TestCase):
    """Tests for AdapterGenerationStage enum."""

    def test_has_11_values(self) -> None:
        self.assertEqual(len(AdapterGenerationStage), 11)

    def test_expected_members(self) -> None:
        expected = {
            "DISCOVERY",
            "CLASSIFICATION",
            "CONTRACT_GENERATION",
            "CODE_GENERATION",
            "TOOL_MASTERY_GENERATION",
            "TEST_GENERATION",
            "SAFETY_POLICY_GENERATION",
            "DOCUMENTATION_GENERATION",
            "QUALITY_GATE",
            "REGISTRATION",
            "COMPLETE",
        }
        self.assertEqual(set(AdapterGenerationStage.__members__.keys()), expected)

    def test_tool_mastery_generation_value(self) -> None:
        self.assertEqual(
            AdapterGenerationStage.TOOL_MASTERY_GENERATION.value,
            "tool_mastery_generation",
        )

    def test_tool_mastery_after_code_before_test(self) -> None:
        stages = list(AdapterGenerationStage)
        code_idx = stages.index(AdapterGenerationStage.CODE_GENERATION)
        mastery_idx = stages.index(AdapterGenerationStage.TOOL_MASTERY_GENERATION)
        test_idx = stages.index(AdapterGenerationStage.TEST_GENERATION)
        self.assertGreater(mastery_idx, code_idx)
        self.assertLess(mastery_idx, test_idx)


class TestAdapterGenerationRequest(unittest.TestCase):
    """Tests for AdapterGenerationRequest serialization."""

    def test_serializes_correctly(self) -> None:
        req = AdapterGenerationRequest(
            source_system="Google Docs",
            adapter_type="api",
            target_contract="extraction",
            notes="test note",
        )
        d = req.to_dict()
        self.assertEqual(d["source_system"], "Google Docs")
        self.assertEqual(d["adapter_type"], "api")
        self.assertEqual(d["target_contract"], "extraction")
        self.assertEqual(d["notes"], "test note")
        self.assertIn("auth_requirements", d)
        self.assertIn("safety_requirements", d)


class TestAdapterGenerationPlan(unittest.TestCase):
    """Tests for AdapterGenerationPlan."""

    def test_stages_defaults_to_all(self) -> None:
        req = AdapterGenerationRequest(
            source_system="test",
            adapter_type="api",
        )
        plan = AdapterGenerationPlan(request=req)
        self.assertEqual(len(plan.stages), 11)
        self.assertEqual(plan.stages, list(AdapterGenerationStage))


class TestAdapterGenerationResult(unittest.TestCase):
    """Tests for AdapterGenerationResult."""

    def test_serializes_correctly(self) -> None:
        req = AdapterGenerationRequest(
            source_system="test",
            adapter_type="api",
        )
        result = AdapterGenerationResult(request=req)
        d = result.to_dict()
        self.assertIn("success", d)
        self.assertIn("quality_gate_passed", d)
        self.assertIn("artifacts", d)

    def test_defaults_to_failure(self) -> None:
        req = AdapterGenerationRequest(
            source_system="test",
            adapter_type="api",
        )
        result = AdapterGenerationResult(request=req)
        self.assertFalse(result.success)
        self.assertFalse(result.quality_gate_passed)


if __name__ == "__main__":
    unittest.main()
