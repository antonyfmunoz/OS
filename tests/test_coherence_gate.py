"""Tests for coherence gate — Phase 96.8G.

Verifies the fail-closed coherence gate:
- Packets without coherence_envelope are blocked
- Packets with incomplete lineage are blocked
- Packets with valid lineage pass
- assert_coherent_or_block raises on failure
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from control_plane.invariants.coherence_gate import (
    CoherenceGateBlocked,
    assert_coherent_or_block,
    coherence_gate_allows_execution,
    evaluate_coherence_before_execution,
)
from control_plane.invariants.spine_lineage_contracts import (
    CoherenceEnvelope,
    CoherenceStatus,
    SpineLineage,
    SpineStage,
    SpineStageArtifact,
    SpineStageStatus,
)


def _complete_artifact(stage_name: str) -> SpineStageArtifact:
    return SpineStageArtifact(
        stage_name=stage_name,
        artifact_id=f"ART-{stage_name}",
        artifact_type=f"{stage_name}_contract",
        source="test",
        timestamp="2026-05-06T00:00:00Z",
        status="complete",
        confidence=1.0,
        validation_status="validated",
        trace_id="TR-GATE-001",
        schema_version="1.0",
    )


def _valid_packet() -> dict:
    envelope = CoherenceEnvelope(
        lineage=SpineLineage(
            stages=[_complete_artifact(s.value) for s in SpineStage],
            mvp_stub_allowed=False,
        ),
        coherence_status="coherent",
        trace_id="TR-GATE-001",
        schema_version="1.0",
    )
    return {"coherence_envelope": envelope.to_dict()}


class TestEvaluateCoherence(unittest.TestCase):
    def test_missing_envelope_fails(self):
        result = evaluate_coherence_before_execution({})
        self.assertFalse(result.coherent)
        self.assertTrue(any("MISSING_COHERENCE_ENVELOPE" in e for e in result.errors))

    def test_none_envelope_fails(self):
        result = evaluate_coherence_before_execution({"coherence_envelope": None})
        self.assertFalse(result.coherent)

    def test_empty_envelope_fails(self):
        result = evaluate_coherence_before_execution({"coherence_envelope": {}})
        self.assertFalse(result.coherent)

    def test_valid_envelope_passes(self):
        result = evaluate_coherence_before_execution(_valid_packet())
        self.assertTrue(result.coherent)


class TestAssertCoherentOrBlock(unittest.TestCase):
    def test_valid_packet_does_not_raise(self):
        assert_coherent_or_block(_valid_packet())

    def test_missing_envelope_raises(self):
        with self.assertRaises(CoherenceGateBlocked) as ctx:
            assert_coherent_or_block({})
        self.assertIn("BLOCK_EXECUTION", str(ctx.exception))

    def test_incomplete_lineage_raises(self):
        envelope = CoherenceEnvelope(
            lineage=SpineLineage(
                stages=[_complete_artifact("signal")],
                mvp_stub_allowed=False,
            ),
            trace_id="TR-001",
        )
        with self.assertRaises(CoherenceGateBlocked):
            assert_coherent_or_block({"coherence_envelope": envelope.to_dict()})


class TestCoherenceGateAllowsExecution(unittest.TestCase):
    def test_valid_returns_true(self):
        allowed, result = coherence_gate_allows_execution(_valid_packet())
        self.assertTrue(allowed)
        self.assertTrue(result.coherent)

    def test_missing_returns_false(self):
        allowed, result = coherence_gate_allows_execution({})
        self.assertFalse(allowed)
        self.assertFalse(result.coherent)


class TestCoherenceGateBlockedException(unittest.TestCase):
    def test_exception_has_result(self):
        try:
            assert_coherent_or_block({})
        except CoherenceGateBlocked as e:
            self.assertIsNotNone(e.result)
            self.assertFalse(e.result.coherent)
            self.assertEqual(
                e.result.status,
                CoherenceStatus.INCOMPLETE_CANONICAL_SPINE.value,
            )


if __name__ == "__main__":
    unittest.main()
