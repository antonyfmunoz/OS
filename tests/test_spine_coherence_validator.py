"""Tests for spine coherence validator — Phase 96.8G.

Verifies that:
1. Complete lineage passes.
2-10. Missing individual stages fail.
11. Invalid stage order fails.
12. Duplicate required stage fails.
13. MVP stub lineage passes when allowed.
14. MVP stub lineage fails when not allowed.
15. Missing artifact_id fails.
16. Missing trace_id fails.
17. Missing schema_version fails.
18. Missing status fails.
19. MVP stub without reason fails.
20. Governance must appear before work_packet.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from core.coherence.spine_lineage_contracts import (
    CoherenceEnvelope,
    CoherenceStatus,
    SpineLineage,
    SpineStage,
    SpineStageArtifact,
    SpineStageStatus,
)
from core.coherence.spine_coherence_validator import (
    validate_coherence_envelope,
)


def _complete_artifact(stage_name: str, status: str = "complete") -> SpineStageArtifact:
    return SpineStageArtifact(
        stage_name=stage_name,
        artifact_id=f"ART-{stage_name}",
        artifact_type=f"{stage_name}_contract",
        source="test",
        timestamp="2026-05-06T00:00:00Z",
        status=status,
        confidence=1.0,
        validation_status="validated",
        trace_id="TR-TEST-001",
        schema_version="1.0",
    )


def _mvp_stub_artifact(stage_name: str) -> SpineStageArtifact:
    return SpineStageArtifact(
        stage_name=stage_name,
        artifact_id=f"ART-{stage_name}-mvp",
        artifact_type=f"{stage_name}_mvp_stub",
        source="test",
        timestamp="2026-05-06T00:00:00Z",
        status=SpineStageStatus.MVP_STUB.value,
        confidence=0.0,
        validation_status="mvp_stub",
        trace_id="TR-TEST-001",
        schema_version="1.0",
        reason="subsystem_not_implemented",
        allowed_for="W0 coherence validation only",
    )


def _full_lineage(mvp_stub_allowed: bool = False) -> SpineLineage:
    return SpineLineage(
        stages=[_complete_artifact(s.value) for s in SpineStage],
        mvp_stub_allowed=mvp_stub_allowed,
    )


def _full_envelope(mvp_stub_allowed: bool = False) -> CoherenceEnvelope:
    return CoherenceEnvelope(
        lineage=_full_lineage(mvp_stub_allowed),
        coherence_status="",
        trace_id="TR-TEST-001",
        schema_version="1.0",
    )


def _mvp_envelope() -> CoherenceEnvelope:
    """Envelope with MVP stubs for all stages except execution_binding and work_packet."""
    complete = {SpineStage.EXECUTION_BINDING.value, SpineStage.WORK_PACKET.value}
    stages = []
    for s in SpineStage:
        if s.value in complete:
            stages.append(_complete_artifact(s.value))
        else:
            stages.append(_mvp_stub_artifact(s.value))
    return CoherenceEnvelope(
        lineage=SpineLineage(stages=stages, mvp_stub_allowed=True),
        coherence_status="",
        trace_id="TR-TEST-001",
        schema_version="1.0",
    )


class TestCompleteLineagePasses(unittest.TestCase):
    def test_all_stages_complete(self):
        result = validate_coherence_envelope(_full_envelope())
        self.assertTrue(result.coherent)
        self.assertEqual(result.status, CoherenceStatus.COHERENT.value)


class TestMissingStagesFail(unittest.TestCase):
    def _test_missing_stage(self, stage: SpineStage):
        envelope = _full_envelope()
        envelope.lineage.stages = [
            s for s in envelope.lineage.stages if s.stage_name != stage.value
        ]
        result = validate_coherence_envelope(envelope)
        self.assertFalse(result.coherent)
        self.assertIn(stage.value, result.missing_stages)

    def test_missing_signal(self):
        self._test_missing_stage(SpineStage.SIGNAL)

    def test_missing_interpretation(self):
        self._test_missing_stage(SpineStage.INTERPRETATION)

    def test_missing_decomposition(self):
        self._test_missing_stage(SpineStage.DECOMPOSITION)

    def test_missing_primitive_mapping(self):
        self._test_missing_stage(SpineStage.PRIMITIVE_MAPPING)

    def test_missing_domain_mapping(self):
        self._test_missing_stage(SpineStage.DOMAIN_MAPPING)

    def test_missing_state_context(self):
        self._test_missing_stage(SpineStage.STATE_CONTEXT)

    def test_missing_composition(self):
        self._test_missing_stage(SpineStage.COMPOSITION)

    def test_missing_capability_selection(self):
        self._test_missing_stage(SpineStage.CAPABILITY_SELECTION)

    def test_missing_execution_binding(self):
        self._test_missing_stage(SpineStage.EXECUTION_BINDING)

    def test_missing_mastery_check(self):
        self._test_missing_stage(SpineStage.MASTERY_CHECK)

    def test_missing_governance_decision(self):
        envelope = _full_envelope()
        envelope.lineage.stages = [
            s
            for s in envelope.lineage.stages
            if s.stage_name != SpineStage.GOVERNANCE_DECISION.value
        ]
        result = validate_coherence_envelope(envelope)
        self.assertFalse(result.coherent)
        self.assertEqual(result.status, CoherenceStatus.GOVERNANCE_LINEAGE_MISSING.value)

    def test_missing_proof_contract(self):
        self._test_missing_stage(SpineStage.PROOF_CONTRACT)

    def test_missing_trace_path(self):
        self._test_missing_stage(SpineStage.TRACE_PATH)


class TestInvalidStageOrder(unittest.TestCase):
    def test_reversed_order_fails(self):
        envelope = _full_envelope()
        envelope.lineage.stages = list(reversed(envelope.lineage.stages))
        result = validate_coherence_envelope(envelope)
        self.assertFalse(result.coherent)
        self.assertEqual(result.status, CoherenceStatus.INVALID_STAGE_ORDER.value)

    def test_swapped_adjacent_fails(self):
        envelope = _full_envelope()
        stages = envelope.lineage.stages
        stages[0], stages[1] = stages[1], stages[0]
        result = validate_coherence_envelope(envelope)
        self.assertFalse(result.coherent)


class TestDuplicateStage(unittest.TestCase):
    def test_duplicate_signal_fails(self):
        envelope = _full_envelope()
        envelope.lineage.stages.append(_complete_artifact("signal"))
        result = validate_coherence_envelope(envelope)
        self.assertFalse(result.coherent)
        self.assertTrue(any("DUPLICATE" in e for e in result.errors))


class TestMVPStubLineage(unittest.TestCase):
    def test_mvp_stubs_allowed_passes(self):
        result = validate_coherence_envelope(_mvp_envelope())
        self.assertTrue(result.coherent)
        self.assertTrue(result.has_mvp_stubs)
        self.assertTrue(result.mvp_stub_allowed)
        self.assertEqual(result.status, CoherenceStatus.COHERENT_WITH_MVP_STUBS.value)

    def test_mvp_stubs_not_allowed_fails(self):
        envelope = _mvp_envelope()
        envelope.lineage.mvp_stub_allowed = False
        result = validate_coherence_envelope(envelope)
        self.assertFalse(result.coherent)
        self.assertTrue(any("MVP_STUB_NOT_ALLOWED" in e for e in result.errors))


class TestMissingArtifactFields(unittest.TestCase):
    def test_missing_artifact_id_fails(self):
        envelope = _full_envelope()
        envelope.lineage.stages[0].artifact_id = ""
        result = validate_coherence_envelope(envelope)
        self.assertFalse(result.coherent)
        self.assertTrue(any("MISSING_ARTIFACT_ID" in e for e in result.errors))

    def test_missing_trace_id_fails(self):
        envelope = _full_envelope()
        envelope.lineage.stages[0].trace_id = ""
        result = validate_coherence_envelope(envelope)
        self.assertFalse(result.coherent)
        self.assertTrue(any("MISSING_TRACE_ID" in e for e in result.errors))

    def test_missing_schema_version_fails(self):
        envelope = _full_envelope()
        envelope.lineage.stages[0].schema_version = ""
        result = validate_coherence_envelope(envelope)
        self.assertFalse(result.coherent)

    def test_missing_status_fails(self):
        envelope = _full_envelope()
        envelope.lineage.stages[0].status = ""
        result = validate_coherence_envelope(envelope)
        self.assertFalse(result.coherent)


class TestMVPStubMissingReason(unittest.TestCase):
    def test_mvp_stub_without_reason_fails(self):
        envelope = _mvp_envelope()
        for s in envelope.lineage.stages:
            if s.status == SpineStageStatus.MVP_STUB.value:
                s.reason = ""
                break
        result = validate_coherence_envelope(envelope)
        self.assertFalse(result.coherent)
        self.assertTrue(any("MVP_STUB_MISSING_REASON" in e for e in result.errors))


class TestGovernanceBeforeWorkPacket(unittest.TestCase):
    def test_governance_after_work_packet_fails(self):
        envelope = _full_envelope()
        stages = envelope.lineage.stages
        gov_idx = next(
            i for i, s in enumerate(stages) if s.stage_name == SpineStage.GOVERNANCE_DECISION.value
        )
        wp_idx = next(
            i for i, s in enumerate(stages) if s.stage_name == SpineStage.WORK_PACKET.value
        )
        stages[gov_idx], stages[wp_idx] = stages[wp_idx], stages[gov_idx]
        result = validate_coherence_envelope(envelope)
        self.assertFalse(result.coherent)


if __name__ == "__main__":
    unittest.main()
