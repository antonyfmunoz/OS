"""Tests for W0 coherence envelope integration — Phase 96.8G.

Verifies that:
- W0 packet builder emits coherence_envelope
- Coherence envelope has all 15 stages
- MVP stubs are explicitly labeled
- Packet validator rejects packets without coherence_envelope
- Local worker validates coherence before execution
- W0 path validates coherence before visible Chrome gate
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from core.environment_bridge.w0_packet_builder import build_w0_001_packet
from core.environment_bridge.packet_validator import (
    PacketValidationStatus,
    validate_w0_packet_dict,
)
from core.coherence.spine_coherence_validator import validate_coherence_envelope_dict
from core.coherence.coherence_gate import (
    coherence_gate_allows_execution,
    evaluate_coherence_before_execution,
)
from core.coherence.spine_lineage_contracts import (
    CoherenceStatus,
    SpineStage,
    SpineStageStatus,
)
from runtime.substrate.local_worker_auto_loop import (
    validate_wo_001_packet,
    validate_coherence_from_packet,
)


class TestW0PacketBuilderEmitsCoherence(unittest.TestCase):
    def test_packet_has_coherence_envelope(self):
        pkt = build_w0_001_packet()
        self.assertIn("coherence_envelope", pkt)
        self.assertIsInstance(pkt["coherence_envelope"], dict)

    def test_envelope_has_lineage(self):
        pkt = build_w0_001_packet()
        env = pkt["coherence_envelope"]
        self.assertIn("lineage", env)
        self.assertIn("stages", env["lineage"])

    def test_envelope_has_all_15_stages(self):
        pkt = build_w0_001_packet()
        stages = pkt["coherence_envelope"]["lineage"]["stages"]
        names = {s["stage_name"] for s in stages}
        for stage in SpineStage:
            self.assertIn(stage.value, names, f"Missing stage: {stage.value}")

    def test_envelope_has_trace_id(self):
        pkt = build_w0_001_packet()
        self.assertTrue(pkt["coherence_envelope"]["trace_id"])

    def test_envelope_has_schema_version(self):
        pkt = build_w0_001_packet()
        self.assertEqual(pkt["coherence_envelope"]["schema_version"], "1.0")

    def test_mvp_stubs_are_labeled(self):
        pkt = build_w0_001_packet()
        stages = pkt["coherence_envelope"]["lineage"]["stages"]
        for s in stages:
            if s["status"] == SpineStageStatus.MVP_STUB.value:
                self.assertTrue(s["reason"], f"MVP stub {s['stage_name']} has no reason")
                self.assertTrue(s["allowed_for"], f"MVP stub {s['stage_name']} has no allowed_for")

    def test_mvp_stub_allowed_is_true(self):
        pkt = build_w0_001_packet()
        self.assertTrue(pkt["coherence_envelope"]["lineage"]["mvp_stub_allowed"])

    def test_execution_binding_stage_is_complete(self):
        pkt = build_w0_001_packet()
        stages = pkt["coherence_envelope"]["lineage"]["stages"]
        eb = next(s for s in stages if s["stage_name"] == "execution_binding")
        self.assertEqual(eb["status"], "complete")

    def test_work_packet_stage_is_complete(self):
        pkt = build_w0_001_packet()
        stages = pkt["coherence_envelope"]["lineage"]["stages"]
        wp = next(s for s in stages if s["stage_name"] == "work_packet")
        self.assertEqual(wp["status"], "complete")

    def test_every_stage_has_artifact_id(self):
        pkt = build_w0_001_packet()
        for s in pkt["coherence_envelope"]["lineage"]["stages"]:
            self.assertTrue(s["artifact_id"], f"Stage {s['stage_name']} missing artifact_id")

    def test_every_stage_has_trace_id(self):
        pkt = build_w0_001_packet()
        for s in pkt["coherence_envelope"]["lineage"]["stages"]:
            self.assertTrue(s["trace_id"], f"Stage {s['stage_name']} missing trace_id")


class TestW0CoherenceValidation(unittest.TestCase):
    def test_w0_envelope_passes_validator(self):
        pkt = build_w0_001_packet()
        result = validate_coherence_envelope_dict(pkt["coherence_envelope"])
        self.assertTrue(result.coherent, f"Errors: {result.errors}")
        self.assertEqual(result.status, CoherenceStatus.COHERENT_WITH_MVP_STUBS.value)

    def test_w0_packet_passes_full_validation(self):
        pkt = build_w0_001_packet()
        result = validate_w0_packet_dict(pkt)
        self.assertTrue(result.can_execute, f"Errors: {result.validation_errors}")

    def test_w0_packet_passes_coherence_gate(self):
        pkt = build_w0_001_packet()
        allowed, result = coherence_gate_allows_execution(pkt)
        self.assertTrue(allowed, f"Errors: {result.errors}")


class TestPacketValidatorRejectsMissingCoherence(unittest.TestCase):
    def test_missing_coherence_envelope_fails(self):
        pkt = build_w0_001_packet()
        del pkt["coherence_envelope"]
        result = validate_w0_packet_dict(pkt)
        self.assertFalse(result.can_execute)
        self.assertEqual(result.status, PacketValidationStatus.INCOMPLETE_CANONICAL_SPINE)

    def test_empty_coherence_envelope_fails(self):
        pkt = build_w0_001_packet()
        pkt["coherence_envelope"] = {}
        result = validate_w0_packet_dict(pkt)
        self.assertFalse(result.can_execute)

    def test_incomplete_lineage_fails(self):
        pkt = build_w0_001_packet()
        pkt["coherence_envelope"]["lineage"]["stages"] = []
        result = validate_w0_packet_dict(pkt)
        self.assertFalse(result.can_execute)


class TestLocalWorkerValidatesCoherence(unittest.TestCase):
    def test_packet_with_coherence_passes(self):
        pkt = build_w0_001_packet()
        errors = validate_wo_001_packet(pkt)
        self.assertEqual(errors, [], f"Unexpected errors: {errors}")

    def test_packet_without_coherence_fails(self):
        pkt = build_w0_001_packet()
        del pkt["coherence_envelope"]
        errors = validate_wo_001_packet(pkt)
        self.assertTrue(any("coherence_envelope" in e for e in errors))

    def test_packet_with_empty_coherence_fails(self):
        pkt = build_w0_001_packet()
        pkt["coherence_envelope"] = {}
        errors = validate_wo_001_packet(pkt)
        self.assertTrue(len(errors) > 0)

    def test_coherence_from_packet_checks_stages(self):
        pkt = build_w0_001_packet()
        pkt["coherence_envelope"]["lineage"]["stages"] = [
            {"stage_name": "signal", "artifact_id": "S1", "trace_id": "T1", "status": "complete"}
        ]
        errors = validate_coherence_from_packet(pkt)
        self.assertTrue(any("missing stages" in e for e in errors))

    def test_coherence_checks_mvp_stub_allowed(self):
        pkt = build_w0_001_packet()
        pkt["coherence_envelope"]["lineage"]["mvp_stub_allowed"] = False
        errors = validate_coherence_from_packet(pkt)
        self.assertTrue(any("mvp_stub" in e for e in errors))


class TestW0CoherenceBeforeChromeGate(unittest.TestCase):
    """Coherence must be validated before any Chrome/GUI action."""

    def test_coherence_gate_runs_before_execution(self):
        pkt = build_w0_001_packet()
        result = evaluate_coherence_before_execution(pkt)
        self.assertTrue(result.coherent)

    def test_broken_coherence_blocks_before_chrome(self):
        pkt = build_w0_001_packet()
        del pkt["coherence_envelope"]
        result = evaluate_coherence_before_execution(pkt)
        self.assertFalse(result.coherent)
        self.assertEqual(
            result.status,
            CoherenceStatus.INCOMPLETE_CANONICAL_SPINE.value,
        )


if __name__ == "__main__":
    unittest.main()
