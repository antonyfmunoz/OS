"""Tests for spine lineage contracts — Phase 96.8G.

Verifies the 15-stage canonical spine model, enums, dataclasses,
and serialization.
"""

import sys

sys.path.insert(0, "/opt/OS")

import unittest

from core.coherence.spine_lineage_contracts import (
    CANONICAL_STAGE_ORDER,
    REQUIRED_STAGE_NAMES,
    REQUIRED_STAGES,
    CoherenceEnvelope,
    CoherenceFailureReason,
    CoherenceStatus,
    CoherenceValidationResult,
    SpineLineage,
    SpineStage,
    SpineStageArtifact,
    SpineStageStatus,
)


class TestSpineStageEnum(unittest.TestCase):
    def test_has_15_stages(self):
        self.assertEqual(len(SpineStage), 15)

    def test_required_stages_match_enum(self):
        self.assertEqual(len(REQUIRED_STAGES), 15)
        for stage in REQUIRED_STAGES:
            self.assertIn(stage.value, REQUIRED_STAGE_NAMES)

    def test_canonical_order_covers_all(self):
        self.assertEqual(len(CANONICAL_STAGE_ORDER), 15)
        for stage in SpineStage:
            self.assertIn(stage, CANONICAL_STAGE_ORDER)

    def test_stage_order_is_sequential(self):
        for i, stage in enumerate(SpineStage):
            self.assertEqual(CANONICAL_STAGE_ORDER[stage], i)


class TestSpineStageStatus(unittest.TestCase):
    def test_has_expected_values(self):
        self.assertEqual(SpineStageStatus.COMPLETE.value, "complete")
        self.assertEqual(SpineStageStatus.MVP_STUB.value, "mvp_stub")
        self.assertEqual(SpineStageStatus.FAILED.value, "failed")


class TestCoherenceStatus(unittest.TestCase):
    def test_has_all_statuses(self):
        self.assertEqual(CoherenceStatus.COHERENT.value, "coherent")
        self.assertEqual(
            CoherenceStatus.COHERENT_WITH_MVP_STUBS.value,
            "coherent_with_mvp_stubs",
        )
        self.assertEqual(
            CoherenceStatus.INCOMPLETE_CANONICAL_SPINE.value,
            "incomplete_canonical_spine",
        )
        self.assertEqual(
            CoherenceStatus.GOVERNANCE_LINEAGE_MISSING.value,
            "governance_lineage_missing",
        )


class TestSpineStageArtifact(unittest.TestCase):
    def test_fields(self):
        artifact = SpineStageArtifact(
            stage_name="signal",
            artifact_id="SIG-001",
            artifact_type="signal_record",
            source="test",
            timestamp="2026-05-06T00:00:00Z",
            status="complete",
            trace_id="TR-001",
            schema_version="1.0",
        )
        self.assertEqual(artifact.stage_name, "signal")
        self.assertEqual(artifact.artifact_id, "SIG-001")

    def test_to_dict(self):
        artifact = SpineStageArtifact(
            stage_name="signal",
            artifact_id="SIG-001",
            status="complete",
            trace_id="TR-001",
            schema_version="1.0",
        )
        d = artifact.to_dict()
        self.assertEqual(d["stage_name"], "signal")
        self.assertIn("artifact_id", d)
        self.assertIn("trace_id", d)
        self.assertIn("schema_version", d)

    def test_mvp_stub_fields(self):
        artifact = SpineStageArtifact(
            stage_name="decomposition",
            artifact_id="DEC-MVP-001",
            status="mvp_stub",
            reason="subsystem_not_implemented",
            allowed_for="W0 coherence validation only",
            trace_id="TR-001",
            schema_version="1.0",
        )
        d = artifact.to_dict()
        self.assertEqual(d["status"], "mvp_stub")
        self.assertEqual(d["reason"], "subsystem_not_implemented")
        self.assertEqual(d["allowed_for"], "W0 coherence validation only")


class TestSpineLineage(unittest.TestCase):
    def test_empty_lineage(self):
        lineage = SpineLineage()
        self.assertEqual(lineage.stages, [])
        self.assertFalse(lineage.mvp_stub_allowed)

    def test_stage_names(self):
        lineage = SpineLineage(
            stages=[
                SpineStageArtifact(stage_name="signal"),
                SpineStageArtifact(stage_name="interpretation"),
            ]
        )
        self.assertEqual(lineage.stage_names(), ["signal", "interpretation"])

    def test_get_stage(self):
        lineage = SpineLineage(
            stages=[
                SpineStageArtifact(stage_name="signal", artifact_id="S1"),
                SpineStageArtifact(stage_name="interpretation", artifact_id="I1"),
            ]
        )
        s = lineage.get_stage("signal")
        self.assertIsNotNone(s)
        self.assertEqual(s.artifact_id, "S1")
        self.assertIsNone(lineage.get_stage("nonexistent"))

    def test_to_dict(self):
        lineage = SpineLineage(
            stages=[SpineStageArtifact(stage_name="signal")],
            mvp_stub_allowed=True,
        )
        d = lineage.to_dict()
        self.assertTrue(d["mvp_stub_allowed"])
        self.assertEqual(len(d["stages"]), 1)


class TestCoherenceEnvelope(unittest.TestCase):
    def test_to_dict(self):
        envelope = CoherenceEnvelope(
            trace_id="TR-001",
            coherence_status="coherent",
            schema_version="1.0",
        )
        d = envelope.to_dict()
        self.assertEqual(d["trace_id"], "TR-001")
        self.assertEqual(d["coherence_status"], "coherent")
        self.assertIn("lineage", d)


class TestCoherenceValidationResult(unittest.TestCase):
    def test_default_not_coherent(self):
        result = CoherenceValidationResult()
        self.assertFalse(result.coherent)
        self.assertEqual(
            result.status,
            CoherenceStatus.INCOMPLETE_CANONICAL_SPINE.value,
        )

    def test_to_dict(self):
        result = CoherenceValidationResult(status="coherent", coherent=True)
        d = result.to_dict()
        self.assertTrue(d["coherent"])


if __name__ == "__main__":
    unittest.main()
