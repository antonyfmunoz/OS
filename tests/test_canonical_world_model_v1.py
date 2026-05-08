"""Tests for Canonical World Model v1 — Phase 96.8Y.

Validates governance-bound promotion, deterministic truth hashes,
rollback reconstruction, self-mutation blocking, recursive promotion
blocking, lineage replay, transition graph enforcement, canonical
truth immutability, and audit traversal.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from core.interpretation.interpretation_engine_v1 import (
    InterpretationEngineV1,
    InterpretationInput,
)
from core.state.transformation_state_ledger import (
    GOVERNANCE_REQUIRED_STAGES,
    MUTATION_BLOCKED_STAGES,
    VALID_TRANSITIONS,
    TransformationStage,
    compute_hash,
)
from core.world_model.canonical_world_model_v1 import (
    FORBIDDEN_CANONICAL_ACTIONS,
    CanonicalBoundary,
    CanonicalCausalGraph,
    CanonicalConstraint,
    CanonicalEntity,
    CanonicalGovernanceReceipt,
    CanonicalLineageReference,
    CanonicalRelationship,
    CanonicalTruthRecord,
    CanonicalWorldModel,
)
from core.world_model.world_model_candidate_v1 import WorldModelCandidateAssembler
from core.world_model.world_model_promotion_v1 import (
    GovernanceApproval,
    PromotionDecision,
    PromotionReceipt,
    PromotionRequest,
    PromotionReview,
    RollbackReceipt,
    WorldModelPromoter,
)

EXAMPLE_DIR = Path("/opt/OS/data/runtime/canonical_world_models")


def _make_interpretation():
    content = (
        "UMH test. Goal: canonical promotion. "
        "Constraint: governance required. Resource: test pipeline."
    )
    inp = InterpretationInput(
        input_id="INPUT-CWM-TEST",
        source_content=content,
        source_content_hash=compute_hash(content),
        source_trace_id="TRACE-CWM-TEST",
        source_state_id="STATE-NORM-TEST",
    )
    return InterpretationEngineV1().interpret(inp)


def _make_candidate(interp=None):
    if interp is None:
        interp = _make_interpretation()
    assembler = WorldModelCandidateAssembler()
    return assembler.assemble(
        interpretation_result_id=interp.result_id,
        interpretation_output_hash=interp.output_hash,
        observations=[o.to_dict() for o in interp.observations],
        relationships=[r.to_dict() for r in interp.relationships],
        hypotheses=[h.to_dict() for h in interp.hypotheses],
        trace_id="TRACE-CWM-TEST",
        extraction_lineage="STATE-EXT-TEST",
        normalization_lineage="STATE-NORM-TEST",
    )


def _make_approval(candidate):
    return GovernanceApproval(
        approval_id="GOV-TEST-001",
        review_id="REVIEW-TEST-001",
        request_id="REQ-TEST-001",
        candidate_id=candidate.candidate_id,
        candidate_hash=candidate.output_hash,
        approved_by="founder",
    )


def _make_canonical():
    candidate = _make_candidate()
    approval = _make_approval(candidate)
    promoter = WorldModelPromoter()
    return promoter.promote(candidate, approval)


class TestGovernanceRequired(unittest.TestCase):
    def test_promotion_requires_approval_id(self):
        candidate = _make_candidate()
        approval = GovernanceApproval(
            approval_id="",
            review_id="R",
            request_id="Q",
            candidate_id=candidate.candidate_id,
            candidate_hash=candidate.output_hash,
            approved_by="founder",
        )
        promoter = WorldModelPromoter()
        with self.assertRaises(ValueError) as ctx:
            promoter.promote(candidate, approval)
        self.assertIn("approval_id", str(ctx.exception))

    def test_promotion_requires_approved_by(self):
        candidate = _make_candidate()
        approval = GovernanceApproval(
            approval_id="GOV-1",
            review_id="R",
            request_id="Q",
            candidate_id=candidate.candidate_id,
            candidate_hash=candidate.output_hash,
            approved_by="",
        )
        promoter = WorldModelPromoter()
        with self.assertRaises(ValueError) as ctx:
            promoter.promote(candidate, approval)
        self.assertIn("approved_by", str(ctx.exception))

    def test_promotion_requires_candidate_id_match(self):
        candidate = _make_candidate()
        approval = GovernanceApproval(
            approval_id="GOV-1",
            review_id="R",
            request_id="Q",
            candidate_id="WRONG-ID",
            candidate_hash=candidate.output_hash,
            approved_by="founder",
        )
        promoter = WorldModelPromoter()
        with self.assertRaises(ValueError) as ctx:
            promoter.promote(candidate, approval)
        self.assertIn("mismatch", str(ctx.exception))

    def test_promotion_requires_candidate_hash_match(self):
        candidate = _make_candidate()
        approval = GovernanceApproval(
            approval_id="GOV-1",
            review_id="R",
            request_id="Q",
            candidate_id=candidate.candidate_id,
            candidate_hash="wrong_hash",
            approved_by="founder",
        )
        promoter = WorldModelPromoter()
        with self.assertRaises(ValueError) as ctx:
            promoter.promote(candidate, approval)
        self.assertIn("hash mismatch", str(ctx.exception))

    def test_truth_records_have_governance_receipt(self):
        model, _ = _make_canonical()
        for tr in model.truth_records:
            self.assertIsNotNone(tr.governance_receipt)
            self.assertTrue(len(tr.governance_receipt.receipt_id) > 0)

    def test_model_has_governance_receipts(self):
        model, _ = _make_canonical()
        self.assertGreater(len(model.governance_receipts), 0)


class TestDeterministicTruthHashes(unittest.TestCase):
    def setUp(self):
        self.candidate = _make_candidate()
        self.approval = _make_approval(self.candidate)

    def test_same_input_same_model_hash(self):
        promoter = WorldModelPromoter()
        m1, _ = promoter.promote(self.candidate, self.approval)
        m2, _ = promoter.promote(self.candidate, self.approval)
        self.assertEqual(m1.output_hash, m2.output_hash)

    def test_same_input_same_truth_hash(self):
        promoter = WorldModelPromoter()
        m1, _ = promoter.promote(self.candidate, self.approval)
        m2, _ = promoter.promote(self.candidate, self.approval)
        self.assertEqual(
            m1.truth_records[0].canonical_hash,
            m2.truth_records[0].canonical_hash,
        )

    def test_same_input_same_model_id(self):
        promoter = WorldModelPromoter()
        m1, _ = promoter.promote(self.candidate, self.approval)
        m2, _ = promoter.promote(self.candidate, self.approval)
        self.assertEqual(m1.model_id, m2.model_id)

    def test_same_input_same_receipt_hash(self):
        promoter = WorldModelPromoter()
        _, r1 = promoter.promote(self.candidate, self.approval)
        _, r2 = promoter.promote(self.candidate, self.approval)
        self.assertEqual(r1.canonical_hash, r2.canonical_hash)

    def test_different_candidate_different_hash(self):
        content2 = "Different content for different canonical result."
        inp2 = InterpretationInput(
            input_id="INPUT-2",
            source_content=content2,
            source_content_hash=compute_hash(content2),
            source_trace_id="TRACE-2",
            source_state_id="STATE-2",
        )
        interp2 = InterpretationEngineV1().interpret(inp2)
        candidate2 = _make_candidate(interp2)
        approval2 = _make_approval(candidate2)
        promoter = WorldModelPromoter()
        m1, _ = promoter.promote(self.candidate, self.approval)
        m2, _ = promoter.promote(candidate2, approval2)
        self.assertNotEqual(m1.output_hash, m2.output_hash)

    def test_output_hash_is_64_chars(self):
        model, _ = _make_canonical()
        self.assertEqual(len(model.output_hash), 64)

    def test_truth_hash_is_64_chars(self):
        model, _ = _make_canonical()
        self.assertEqual(len(model.truth_records[0].canonical_hash), 64)


class TestRollbackReconstruction(unittest.TestCase):
    def test_rollback_chain_present(self):
        model, _ = _make_canonical()
        self.assertGreater(len(model.rollback_chain), 0)

    def test_truth_record_has_rollback_reference(self):
        model, _ = _make_canonical()
        for tr in model.truth_records:
            self.assertTrue(len(tr.rollback_reference) > 0)

    def test_rollback_receipt_creation(self):
        model, _ = _make_canonical()
        promoter = WorldModelPromoter()
        rb = promoter.create_rollback_receipt(
            model,
            [model.truth_records[0].truth_id],
            "test rollback",
            "GOV-ROLLBACK-001",
        )
        self.assertTrue(rb.receipt_id.startswith("RBRECEIPT-"))
        self.assertEqual(rb.canonical_model_id, model.model_id)
        self.assertEqual(len(rb.rolled_back_truth_ids), 1)
        self.assertEqual(rb.prior_canonical_hash, model.output_hash)
        self.assertEqual(rb.governance_reference, "GOV-ROLLBACK-001")

    def test_rollback_receipt_to_dict(self):
        model, _ = _make_canonical()
        promoter = WorldModelPromoter()
        rb = promoter.create_rollback_receipt(
            model, [model.truth_records[0].truth_id], "test", "GOV-RB"
        )
        d = rb.to_dict()
        self.assertIn("receipt_id", d)
        self.assertIn("rolled_back_truth_ids", d)
        self.assertIn("prior_canonical_hash", d)
        self.assertIn("governance_reference", d)

    def test_rollback_preserves_prior_hash(self):
        model, _ = _make_canonical()
        promoter = WorldModelPromoter()
        rb = promoter.create_rollback_receipt(
            model, [model.truth_records[0].truth_id], "test", "GOV-RB"
        )
        self.assertEqual(rb.prior_canonical_hash, model.output_hash)


class TestSelfMutationBlocked(unittest.TestCase):
    def test_boundary_blocks_self_mutation(self):
        b = CanonicalBoundary(may_self_mutate=True)
        errors = b.validate()
        self.assertTrue(any("self-mutate" in e for e in errors))

    def test_boundary_blocks_recursive_rewrite(self):
        b = CanonicalBoundary(may_recursive_rewrite=True)
        errors = b.validate()
        self.assertTrue(any("recursively rewrite" in e for e in errors))

    def test_boundary_blocks_auto_promote(self):
        b = CanonicalBoundary(may_auto_promote=True)
        errors = b.validate()
        self.assertTrue(any("auto-promote" in e for e in errors))

    def test_boundary_blocks_execution(self):
        b = CanonicalBoundary(may_trigger_execution=True)
        errors = b.validate()
        self.assertTrue(any("execution" in e for e in errors))

    def test_boundary_blocks_reinterpretation(self):
        b = CanonicalBoundary(may_reinterpret_observations=True)
        errors = b.validate()
        self.assertTrue(any("reinterpret" in e for e in errors))

    def test_boundary_blocks_governance_bypass(self):
        b = CanonicalBoundary(may_bypass_governance=True)
        errors = b.validate()
        self.assertTrue(any("governance" in e for e in errors))

    def test_default_boundary_valid(self):
        b = CanonicalBoundary()
        self.assertEqual(b.validate(), [])

    def test_boundary_violation_raises(self):
        promoter = WorldModelPromoter()
        promoter.boundary = CanonicalBoundary(may_self_mutate=True)
        candidate = _make_candidate()
        approval = _make_approval(candidate)
        with self.assertRaises(ValueError):
            promoter.promote(candidate, approval)


class TestRecursivePromotionBlocked(unittest.TestCase):
    def test_forbidden_actions_include_self_reinforcing(self):
        self.assertIn("self_reinforcing_promotion", FORBIDDEN_CANONICAL_ACTIONS)

    def test_forbidden_actions_include_circular_truth(self):
        self.assertIn("circular_truth_reference", FORBIDDEN_CANONICAL_ACTIONS)

    def test_forbidden_actions_include_ungrounded_entity(self):
        self.assertIn("ungrounded_entity_generation", FORBIDDEN_CANONICAL_ACTIONS)

    def test_forbidden_actions_count(self):
        self.assertEqual(len(FORBIDDEN_CANONICAL_ACTIONS), 10)

    def test_model_blocks_all_forbidden(self):
        model, _ = _make_canonical()
        blocked = set(model.blocked_actions)
        forbidden = set(FORBIDDEN_CANONICAL_ACTIONS)
        self.assertTrue(forbidden.issubset(blocked))

    def test_truth_records_block_forbidden(self):
        model, _ = _make_canonical()
        for tr in model.truth_records:
            blocked = set(tr.blocked_next_actions)
            self.assertTrue(set(FORBIDDEN_CANONICAL_ACTIONS).issubset(blocked))


class TestLineageReplay(unittest.TestCase):
    def test_truth_record_has_lineage(self):
        model, _ = _make_canonical()
        tr = model.truth_records[0]
        self.assertTrue(len(tr.lineage.extraction_state_id) > 0)
        self.assertTrue(len(tr.lineage.normalization_state_id) > 0)
        self.assertTrue(len(tr.lineage.interpretation_state_id) > 0)
        self.assertTrue(len(tr.lineage.candidate_state_id) > 0)
        self.assertTrue(len(tr.lineage.governance_state_id) > 0)

    def test_truth_record_has_originating_ids(self):
        model, _ = _make_canonical()
        tr = model.truth_records[0]
        self.assertGreater(len(tr.originating_observation_ids), 0)
        self.assertTrue(len(tr.originating_interpretation_id) > 0)

    def test_truth_record_has_trace_id(self):
        model, _ = _make_canonical()
        tr = model.truth_records[0]
        self.assertTrue(len(tr.originating_trace_id) > 0)

    def test_lineage_to_dict(self):
        model, _ = _make_canonical()
        d = model.truth_records[0].lineage.to_dict()
        self.assertIn("extraction_state_id", d)
        self.assertIn("normalization_state_id", d)
        self.assertIn("interpretation_state_id", d)
        self.assertIn("candidate_state_id", d)
        self.assertIn("governance_state_id", d)
        self.assertIn("trace_id", d)

    def test_entities_have_source_candidate_refs(self):
        model, _ = _make_canonical()
        for ent in model.entities:
            self.assertTrue(len(ent.source_candidate_entity_id) > 0)

    def test_relationships_have_source_candidate_refs(self):
        model, _ = _make_canonical()
        for rel in model.relationships:
            self.assertTrue(len(rel.source_candidate_relationship_id) > 0)


class TestTransitionGraphEnforced(unittest.TestCase):
    def test_canonical_world_model_stage_exists(self):
        self.assertIn(TransformationStage.CANONICAL_WORLD_MODEL, VALID_TRANSITIONS)

    def test_governance_review_to_canonical_world_model(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.GOVERNANCE_REVIEW]
        self.assertIn(TransformationStage.CANONICAL_WORLD_MODEL, valid_next)

    def test_canonical_world_model_to_world_model_mutation(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.CANONICAL_WORLD_MODEL]
        self.assertIn(TransformationStage.WORLD_MODEL_MUTATION, valid_next)

    def test_canonical_world_model_cannot_reach_interpretation(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.CANONICAL_WORLD_MODEL]
        self.assertNotIn(TransformationStage.INTERPRETATION, valid_next)

    def test_world_model_candidate_cannot_reach_canonical_world_model(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.WORLD_MODEL_CANDIDATE]
        self.assertNotIn(TransformationStage.CANONICAL_WORLD_MODEL, valid_next)

    def test_canonical_world_model_requires_governance(self):
        self.assertIn(
            TransformationStage.CANONICAL_WORLD_MODEL,
            GOVERNANCE_REQUIRED_STAGES,
        )

    def test_world_model_candidate_is_mutation_blocked(self):
        self.assertIn(
            TransformationStage.WORLD_MODEL_CANDIDATE,
            MUTATION_BLOCKED_STAGES,
        )

    def test_all_stages_in_transitions(self):
        for stage in TransformationStage:
            self.assertIn(stage, VALID_TRANSITIONS)

    def test_governance_review_still_reaches_canonical_memory(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.GOVERNANCE_REVIEW]
        self.assertIn(TransformationStage.CANONICAL_MEMORY, valid_next)


class TestCanonicalTruthImmutable(unittest.TestCase):
    def test_truth_record_has_canonical_hash(self):
        model, _ = _make_canonical()
        for tr in model.truth_records:
            self.assertTrue(len(tr.canonical_hash) == 64)

    def test_truth_record_has_source_candidate_hash(self):
        model, _ = _make_canonical()
        for tr in model.truth_records:
            self.assertTrue(len(tr.source_candidate_hash) == 64)

    def test_truth_record_has_confidence(self):
        model, _ = _make_canonical()
        for tr in model.truth_records:
            self.assertGreater(tr.confidence, 0.0)

    def test_truth_record_has_uncertainty(self):
        model, _ = _make_canonical()
        for tr in model.truth_records:
            self.assertGreater(tr.uncertainty_score, 0.0)


class TestAuditTraversal(unittest.TestCase):
    def test_governance_audit(self):
        model, _ = _make_canonical()
        audit = model.get_governance_audit()
        self.assertGreater(len(audit), 0)
        self.assertIn("receipt_id", audit[0])
        self.assertIn("approved_by", audit[0])

    def test_truth_record_lookup(self):
        model, _ = _make_canonical()
        tr = model.truth_records[0]
        found = model.get_truth_record(tr.truth_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.truth_id, tr.truth_id)

    def test_truth_record_lookup_missing(self):
        model, _ = _make_canonical()
        found = model.get_truth_record("NONEXISTENT")
        self.assertIsNone(found)


class TestResultValidation(unittest.TestCase):
    def test_valid_model_passes(self):
        model, _ = _make_canonical()
        self.assertEqual(model.validate(), [])

    def test_model_to_dict(self):
        model, _ = _make_canonical()
        d = model.to_dict()
        required = [
            "model_id",
            "entities",
            "relationships",
            "constraints",
            "causal_graph",
            "truth_records",
            "boundary",
            "output_hash",
            "governance_receipts",
            "rollback_chain",
            "blocked_actions",
            "allowed_actions",
        ]
        for key in required:
            self.assertIn(key, d, f"missing key: {key}")

    def test_json_serializable(self):
        model, _ = _make_canonical()
        json_str = json.dumps(model.to_dict())
        self.assertGreater(len(json_str), 0)

    def test_promotion_receipt_to_dict(self):
        _, receipt = _make_canonical()
        d = receipt.to_dict()
        self.assertIn("receipt_id", d)
        self.assertIn("candidate_hash", d)
        self.assertIn("canonical_hash", d)
        self.assertIn("governance_approval_id", d)


class TestPromotionContracts(unittest.TestCase):
    def test_promotion_request(self):
        r = PromotionRequest(
            request_id="REQ-001",
            candidate_id="WMC-001",
            candidate_hash="abc123",
        )
        d = r.to_dict()
        self.assertEqual(d["request_id"], "REQ-001")

    def test_promotion_review(self):
        r = PromotionReview(
            review_id="REV-001",
            request_id="REQ-001",
            reviewer="founder",
            decision=PromotionDecision.APPROVED,
        )
        d = r.to_dict()
        self.assertEqual(d["decision"], "approved")

    def test_promotion_decision_values(self):
        expected = {"approved", "rejected", "deferred"}
        actual = {d.value for d in PromotionDecision}
        self.assertEqual(actual, expected)

    def test_boundary_to_dict(self):
        b = CanonicalBoundary()
        d = b.to_dict()
        self.assertEqual(len(d), 12)

    def test_allowed_capabilities(self):
        b = CanonicalBoundary()
        self.assertTrue(b.may_store_governed_truth)
        self.assertTrue(b.may_expose_retrieval)
        self.assertTrue(b.may_support_replay)
        self.assertTrue(b.may_support_rollback)
        self.assertTrue(b.may_support_lineage_traversal)
        self.assertTrue(b.may_support_governance_audit)


class TestEntityAndRelationshipPromotion(unittest.TestCase):
    def test_entities_promoted(self):
        model, _ = _make_canonical()
        self.assertGreater(len(model.entities), 0)

    def test_entity_ids_have_canonical_prefix(self):
        model, _ = _make_canonical()
        for ent in model.entities:
            self.assertTrue(ent.entity_id.startswith("CENT-"))

    def test_entities_have_governance_receipt(self):
        model, _ = _make_canonical()
        for ent in model.entities:
            self.assertTrue(len(ent.governance_receipt_id) > 0)

    def test_relationships_promoted(self):
        model, _ = _make_canonical()
        self.assertGreater(len(model.relationships), 0)

    def test_relationship_ids_have_canonical_prefix(self):
        model, _ = _make_canonical()
        for rel in model.relationships:
            self.assertTrue(rel.relationship_id.startswith("CREL-"))

    def test_relationships_reference_canonical_entities(self):
        model, _ = _make_canonical()
        entity_ids = {e.entity_id for e in model.entities}
        for rel in model.relationships:
            self.assertIn(rel.from_entity_id, entity_ids)
            self.assertIn(rel.to_entity_id, entity_ids)

    def test_causal_graph_promoted(self):
        model, _ = _make_canonical()
        self.assertIsNotNone(model.causal_graph)
        self.assertGreater(len(model.causal_graph.causal_links), 0)


class TestExampleArtifacts(unittest.TestCase):
    def test_canonical_entity_example_exists(self):
        path = EXAMPLE_DIR / "canonical_entity_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertIn("entity_id", data)
        self.assertIn("governance_receipt_id", data)

    def test_canonical_relationship_example_exists(self):
        path = EXAMPLE_DIR / "canonical_relationship_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertIn("relationship_id", data)

    def test_canonical_truth_record_example_exists(self):
        path = EXAMPLE_DIR / "canonical_truth_record_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertIn("truth_id", data)
        self.assertIn("governance_receipt", data)
        self.assertIn("lineage", data)

    def test_canonical_world_model_example_exists(self):
        path = EXAMPLE_DIR / "canonical_world_model_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertIn("model_id", data)
        self.assertIn("entities", data)
        self.assertIn("governance_receipts", data)

    def test_governance_receipt_example_exists(self):
        path = EXAMPLE_DIR / "governance_receipt_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertIn("receipt_id", data)
        self.assertIn("approved_by", data)

    def test_rollback_receipt_example_exists(self):
        path = EXAMPLE_DIR / "rollback_receipt_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertIn("receipt_id", data)
        self.assertIn("rolled_back_truth_ids", data)
        self.assertIn("governance_reference", data)

    def test_no_secrets_in_examples(self):
        for name in [
            "canonical_entity_example.json",
            "canonical_relationship_example.json",
            "canonical_truth_record_example.json",
            "canonical_world_model_example.json",
            "governance_receipt_example.json",
            "rollback_receipt_example.json",
        ]:
            raw = (EXAMPLE_DIR / name).read_text().lower()
            for keyword in ["password", "api_key", "secret_key", "bearer", "token_value"]:
                self.assertNotIn(keyword, raw, f"secret keyword '{keyword}' in {name}")


if __name__ == "__main__":
    unittest.main()
