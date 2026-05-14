"""Tests for World Model Candidate v1 — Phase 96.8X.

Validates the world-model candidate system: entity modeling,
relationship graphs, causal links, deterministic assembly,
governance enforcement, boundary validation, ledger integration,
and uncertainty tracking.
"""

import json
import sys
import unittest
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from core.interpretation.interpretation_engine_v1 import (
    InterpretationEngineV1,
    InterpretationInput,
)
from core.state.transformation_state_ledger import (
    MUTATION_BLOCKED_STAGES,
    VALID_TRANSITIONS,
    TransformationStage,
    compute_hash,
)
from core.world_model.entity_resolution_v1 import (
    CandidateEntity,
    CandidateRelationship,
    CandidateRelationshipType,
    EntityAlias,
    EntityReference,
    RelationshipReference,
    ResolutionConfidence,
)
from core.world_model.world_model_candidate_v1 import (
    FORBIDDEN_CANDIDATE_ACTIONS,
    CandidateBoundary,
    CandidateCausalLink,
    CandidateConfidenceEnvelope,
    CandidateConstraint,
    CandidateObservation,
    CandidateStatus,
    WorldModelCandidate,
    WorldModelCandidateAssembler,
    _DeterministicIdGenerator,
)

EXAMPLE_DIR = Path(_ROOT) / "data" / "runtime" / "world_model_candidates"


def _make_interpretation():
    content = (
        "UMH test document. Goal: validate world model candidates. "
        "Constraint: no canonical mutation. Resource: test harness."
    )
    inp = InterpretationInput(
        input_id="INPUT-WMC-TEST",
        source_content=content,
        source_content_hash=compute_hash(content),
        source_trace_id="TRACE-WMC-TEST",
        source_state_id="STATE-NORM-TEST",
    )
    engine = InterpretationEngineV1()
    return engine.interpret(inp)


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
        trace_id="TRACE-WMC-TEST",
        extraction_lineage="STATE-EXT-TEST",
        normalization_lineage="STATE-NORM-TEST",
    )


class TestDeterministicAssembly(unittest.TestCase):
    def setUp(self):
        self.interp = _make_interpretation()

    def test_same_input_same_output_hash(self):
        wmc1 = _make_candidate(self.interp)
        wmc2 = _make_candidate(self.interp)
        self.assertEqual(wmc1.output_hash, wmc2.output_hash)

    def test_same_candidate_id(self):
        wmc1 = _make_candidate(self.interp)
        wmc2 = _make_candidate(self.interp)
        self.assertEqual(wmc1.candidate_id, wmc2.candidate_id)

    def test_same_entity_ids(self):
        wmc1 = _make_candidate(self.interp)
        wmc2 = _make_candidate(self.interp)
        ids1 = [e.entity_id for e in wmc1.entities]
        ids2 = [e.entity_id for e in wmc2.entities]
        self.assertEqual(ids1, ids2)

    def test_same_relationship_ids(self):
        wmc1 = _make_candidate(self.interp)
        wmc2 = _make_candidate(self.interp)
        ids1 = [r.relationship_id for r in wmc1.relationships]
        ids2 = [r.relationship_id for r in wmc2.relationships]
        self.assertEqual(ids1, ids2)

    def test_same_causal_link_ids(self):
        wmc1 = _make_candidate(self.interp)
        wmc2 = _make_candidate(self.interp)
        ids1 = [c.link_id for c in wmc1.causal_links]
        ids2 = [c.link_id for c in wmc2.causal_links]
        self.assertEqual(ids1, ids2)

    def test_different_interpretation_different_hash(self):
        content2 = "Entirely different content for second interpretation."
        inp2 = InterpretationInput(
            input_id="INPUT-WMC-TEST-2",
            source_content=content2,
            source_content_hash=compute_hash(content2),
            source_trace_id="TRACE-WMC-TEST-2",
            source_state_id="STATE-NORM-TEST-2",
        )
        interp2 = InterpretationEngineV1().interpret(inp2)
        wmc1 = _make_candidate(self.interp)
        wmc2 = _make_candidate(interp2)
        self.assertNotEqual(wmc1.output_hash, wmc2.output_hash)

    def test_output_hash_is_64_chars(self):
        wmc = _make_candidate(self.interp)
        self.assertEqual(len(wmc.output_hash), 64)


class TestDeterministicIdGenerator(unittest.TestCase):
    def test_same_seed_same_sequence(self):
        g1 = _DeterministicIdGenerator("seed-wmc")
        g2 = _DeterministicIdGenerator("seed-wmc")
        for _ in range(5):
            self.assertEqual(g1.next_id("ENT"), g2.next_id("ENT"))

    def test_different_seed_different_ids(self):
        g1 = _DeterministicIdGenerator("seed-a")
        g2 = _DeterministicIdGenerator("seed-b")
        self.assertNotEqual(g1.next_id("ENT"), g2.next_id("ENT"))


class TestEntityModeling(unittest.TestCase):
    def test_entities_created(self):
        wmc = _make_candidate()
        self.assertGreater(len(wmc.entities), 0)

    def test_entity_ids_have_prefix(self):
        wmc = _make_candidate()
        for ent in wmc.entities:
            self.assertTrue(ent.entity_id.startswith("ENT-"))

    def test_entities_have_types(self):
        wmc = _make_candidate()
        for ent in wmc.entities:
            self.assertTrue(len(ent.entity_type) > 0)

    def test_entities_have_labels(self):
        wmc = _make_candidate()
        for ent in wmc.entities:
            self.assertTrue(len(ent.label) > 0)

    def test_entities_have_confidence(self):
        wmc = _make_candidate()
        for ent in wmc.entities:
            self.assertGreater(ent.confidence, 0.0)
            self.assertLessEqual(ent.confidence, 1.0)

    def test_entities_have_trace_ids(self):
        wmc = _make_candidate()
        for ent in wmc.entities:
            self.assertGreater(len(ent.source_trace_ids), 0)

    def test_entities_have_observation_refs(self):
        wmc = _make_candidate()
        for ent in wmc.entities:
            self.assertGreater(len(ent.source_observation_ids), 0)

    def test_entity_to_dict(self):
        wmc = _make_candidate()
        d = wmc.entities[0].to_dict()
        self.assertIn("entity_id", d)
        self.assertIn("entity_type", d)
        self.assertIn("label", d)
        self.assertIn("source_observation_ids", d)
        self.assertIn("resolution_confidence", d)

    def test_no_duplicate_labels(self):
        wmc = _make_candidate()
        labels = [e.label for e in wmc.entities]
        self.assertEqual(len(labels), len(set(labels)))


class TestRelationshipModeling(unittest.TestCase):
    def test_relationships_created(self):
        wmc = _make_candidate()
        self.assertGreater(len(wmc.relationships), 0)

    def test_relationship_ids_have_prefix(self):
        wmc = _make_candidate()
        for rel in wmc.relationships:
            self.assertTrue(rel.relationship_id.startswith("REL-"))

    def test_relationships_reference_valid_entities(self):
        wmc = _make_candidate()
        entity_ids = {e.entity_id for e in wmc.entities}
        for rel in wmc.relationships:
            self.assertIn(rel.from_entity_id, entity_ids)
            self.assertIn(rel.to_entity_id, entity_ids)

    def test_relationships_have_evidence(self):
        wmc = _make_candidate()
        for rel in wmc.relationships:
            self.assertGreater(len(rel.evidence_observation_ids), 0)

    def test_relationship_to_dict(self):
        wmc = _make_candidate()
        d = wmc.relationships[0].to_dict()
        self.assertIn("relationship_id", d)
        self.assertIn("from_entity_id", d)
        self.assertIn("to_entity_id", d)
        self.assertIn("is_causal", d)
        self.assertIn("is_temporal", d)
        self.assertIn("is_constraint", d)


class TestCausalLinks(unittest.TestCase):
    def test_causal_links_created(self):
        wmc = _make_candidate()
        self.assertGreater(len(wmc.causal_links), 0)

    def test_causal_link_ids_have_prefix(self):
        wmc = _make_candidate()
        for link in wmc.causal_links:
            self.assertTrue(link.link_id.startswith("CAUSAL-"))

    def test_causal_links_reference_entities(self):
        wmc = _make_candidate()
        entity_ids = {e.entity_id for e in wmc.entities}
        for link in wmc.causal_links:
            self.assertIn(link.cause_entity_id, entity_ids)
            self.assertIn(link.effect_entity_id, entity_ids)

    def test_causal_links_have_evidence(self):
        wmc = _make_candidate()
        for link in wmc.causal_links:
            self.assertGreater(len(link.evidence_observation_ids), 0)

    def test_causal_links_have_confidence(self):
        wmc = _make_candidate()
        for link in wmc.causal_links:
            self.assertGreater(link.confidence, 0.0)

    def test_causal_link_to_dict(self):
        wmc = _make_candidate()
        d = wmc.causal_links[0].to_dict()
        self.assertIn("link_id", d)
        self.assertIn("cause_entity_id", d)
        self.assertIn("effect_entity_id", d)
        self.assertIn("causal_type", d)
        self.assertIn("temporal_ordering", d)


class TestCandidateObservations(unittest.TestCase):
    def test_observations_created(self):
        wmc = _make_candidate()
        self.assertGreater(len(wmc.observations), 0)

    def test_observations_have_interpretation_ref(self):
        wmc = _make_candidate()
        for obs in wmc.observations:
            self.assertTrue(len(obs.source_interpretation_id) > 0)

    def test_observations_have_trace_ref(self):
        wmc = _make_candidate()
        for obs in wmc.observations:
            self.assertTrue(len(obs.source_trace_id) > 0)


class TestCandidateConstraints(unittest.TestCase):
    def test_constraints_extraction(self):
        content = "Test document. Constraint: no sensitive data allowed. Goal: prove safety."
        inp = InterpretationInput(
            input_id="INPUT-CSTR-TEST",
            source_content=content,
            source_content_hash=compute_hash(content),
            source_trace_id="TRACE-CSTR-TEST",
            source_state_id="STATE-NORM-CSTR",
        )
        interp = InterpretationEngineV1().interpret(inp)
        wmc = _make_candidate(interp)
        constraint_obs = [o for o in interp.observations if o.primitive_type.value == "constraint"]
        if constraint_obs:
            self.assertGreater(len(wmc.constraints), 0)


class TestConfidenceEnvelope(unittest.TestCase):
    def test_envelope_present(self):
        wmc = _make_candidate()
        self.assertIsNotNone(wmc.confidence_envelope)

    def test_overall_confidence_positive(self):
        wmc = _make_candidate()
        self.assertGreater(wmc.confidence_envelope.overall_confidence, 0.0)

    def test_uncertainty_score_present(self):
        wmc = _make_candidate()
        self.assertGreater(wmc.confidence_envelope.uncertainty_score, 0.0)

    def test_dimensions_present(self):
        wmc = _make_candidate()
        c = wmc.confidence_envelope
        self.assertGreaterEqual(c.entity_confidence, 0.0)
        self.assertGreaterEqual(c.relationship_confidence, 0.0)
        self.assertGreaterEqual(c.causal_confidence, 0.0)
        self.assertGreaterEqual(c.evidence_coverage, 0.0)

    def test_envelope_to_dict(self):
        wmc = _make_candidate()
        d = wmc.confidence_envelope.to_dict()
        required = [
            "overall_confidence",
            "entity_confidence",
            "relationship_confidence",
            "causal_confidence",
            "evidence_coverage",
            "uncertainty_score",
        ]
        for key in required:
            self.assertIn(key, d)


class TestUncertaintyTracking(unittest.TestCase):
    def test_unsupported_assumptions_present(self):
        wmc = _make_candidate()
        self.assertGreater(len(wmc.unsupported_assumptions), 0)

    def test_explicit_unknowns_present(self):
        wmc = _make_candidate()
        self.assertGreater(len(wmc.explicit_unknowns), 0)

    def test_missing_information_present(self):
        wmc = _make_candidate()
        self.assertGreater(len(wmc.missing_information), 0)


class TestGovernanceEnforcement(unittest.TestCase):
    def test_status_is_assembled(self):
        wmc = _make_candidate()
        self.assertEqual(wmc.status, CandidateStatus.ASSEMBLED)

    def test_governance_status_not_submitted(self):
        wmc = _make_candidate()
        self.assertEqual(wmc.governance_status, "not_submitted")

    def test_all_forbidden_actions_blocked(self):
        wmc = _make_candidate()
        blocked = set(wmc.blocked_actions)
        forbidden = set(FORBIDDEN_CANDIDATE_ACTIONS)
        self.assertTrue(forbidden.issubset(blocked))

    def test_forbidden_actions_count(self):
        self.assertEqual(len(FORBIDDEN_CANDIDATE_ACTIONS), 10)


class TestCandidateBoundary(unittest.TestCase):
    def test_default_boundary_valid(self):
        b = CandidateBoundary()
        self.assertEqual(b.validate(), [])

    def test_canonical_mutation_forbidden(self):
        b = CandidateBoundary(may_mutate_canonical_world_model=True)
        errors = b.validate()
        self.assertTrue(any("canonical world model" in e for e in errors))

    def test_canonical_truth_forbidden(self):
        b = CandidateBoundary(may_create_canonical_truth=True)
        errors = b.validate()
        self.assertTrue(any("canonical truth" in e for e in errors))

    def test_auto_promote_forbidden(self):
        b = CandidateBoundary(may_auto_promote=True)
        errors = b.validate()
        self.assertTrue(any("auto-promote" in e for e in errors))

    def test_bypass_governance_forbidden(self):
        b = CandidateBoundary(may_bypass_governance=True)
        errors = b.validate()
        self.assertTrue(any("governance" in e for e in errors))

    def test_execution_forbidden(self):
        b = CandidateBoundary(may_trigger_execution=True)
        errors = b.validate()
        self.assertTrue(any("execution" in e for e in errors))

    def test_recursive_rewrite_forbidden(self):
        b = CandidateBoundary(may_recursive_rewrite=True)
        errors = b.validate()
        self.assertTrue(any("recursively rewrite" in e for e in errors))

    def test_allowed_capabilities(self):
        b = CandidateBoundary()
        self.assertTrue(b.may_aggregate_interpretations)
        self.assertTrue(b.may_connect_entities)
        self.assertTrue(b.may_establish_relationships)
        self.assertTrue(b.may_accumulate_evidence)
        self.assertTrue(b.may_track_uncertainty)
        self.assertTrue(b.may_form_causal_structures)

    def test_boundary_to_dict(self):
        b = CandidateBoundary()
        d = b.to_dict()
        self.assertEqual(len(d), 12)

    def test_boundary_violation_raises(self):
        assembler = WorldModelCandidateAssembler()
        assembler.boundary = CandidateBoundary(may_mutate_canonical_world_model=True)
        interp = _make_interpretation()
        with self.assertRaises(ValueError):
            assembler.assemble(
                interpretation_result_id=interp.result_id,
                interpretation_output_hash=interp.output_hash,
                observations=[o.to_dict() for o in interp.observations],
                relationships=[r.to_dict() for r in interp.relationships],
                hypotheses=[h.to_dict() for h in interp.hypotheses],
            )


class TestLineagePreservation(unittest.TestCase):
    def test_extraction_lineage_set(self):
        wmc = _make_candidate()
        self.assertEqual(wmc.extraction_lineage, "STATE-EXT-TEST")

    def test_normalization_lineage_set(self):
        wmc = _make_candidate()
        self.assertEqual(wmc.normalization_lineage, "STATE-NORM-TEST")

    def test_interpretation_lineage_set(self):
        wmc = _make_candidate()
        interp = _make_interpretation()
        self.assertEqual(wmc.interpretation_lineage, interp.result_id)

    def test_source_interpretation_ids(self):
        wmc = _make_candidate()
        self.assertGreater(len(wmc.source_interpretation_ids), 0)

    def test_source_trace_ids(self):
        wmc = _make_candidate()
        self.assertGreater(len(wmc.source_trace_ids), 0)


class TestValidTransitions(unittest.TestCase):
    def test_world_model_candidate_stage_exists(self):
        self.assertIn(TransformationStage.WORLD_MODEL_CANDIDATE, VALID_TRANSITIONS)

    def test_interpretation_to_world_model_candidate(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.INTERPRETATION]
        self.assertIn(TransformationStage.WORLD_MODEL_CANDIDATE, valid_next)

    def test_world_model_candidate_to_governance_review(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.WORLD_MODEL_CANDIDATE]
        self.assertIn(TransformationStage.GOVERNANCE_REVIEW, valid_next)

    def test_world_model_candidate_cannot_reach_canonical_memory(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.WORLD_MODEL_CANDIDATE]
        self.assertNotIn(TransformationStage.CANONICAL_MEMORY, valid_next)

    def test_world_model_candidate_cannot_reach_world_model_mutation(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.WORLD_MODEL_CANDIDATE]
        self.assertNotIn(TransformationStage.WORLD_MODEL_MUTATION, valid_next)

    def test_world_model_candidate_is_mutation_blocked(self):
        self.assertIn(TransformationStage.WORLD_MODEL_CANDIDATE, MUTATION_BLOCKED_STAGES)

    def test_interpretation_still_reaches_primitive_decomposition(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.INTERPRETATION]
        self.assertIn(TransformationStage.PRIMITIVE_DECOMPOSITION, valid_next)

    def test_all_stages_in_transitions(self):
        for stage in TransformationStage:
            self.assertIn(stage, VALID_TRANSITIONS)


class TestResultValidation(unittest.TestCase):
    def test_valid_candidate_passes(self):
        wmc = _make_candidate()
        self.assertEqual(wmc.validate(), [])

    def test_candidate_to_dict(self):
        wmc = _make_candidate()
        d = wmc.to_dict()
        required = [
            "candidate_id",
            "entities",
            "relationships",
            "causal_links",
            "constraints",
            "observations",
            "confidence_envelope",
            "boundary",
            "status",
            "output_hash",
            "extraction_lineage",
            "normalization_lineage",
            "interpretation_lineage",
            "governance_status",
            "unsupported_assumptions",
            "explicit_unknowns",
            "blocked_actions",
            "allowed_actions",
        ]
        for key in required:
            self.assertIn(key, d, f"missing key: {key}")

    def test_json_serializable(self):
        wmc = _make_candidate()
        d = wmc.to_dict()
        json_str = json.dumps(d)
        self.assertGreater(len(json_str), 0)


class TestEntityResolutionContracts(unittest.TestCase):
    def test_entity_alias(self):
        a = EntityAlias(alias="test_alias", source="interpretation", confidence=0.8)
        d = a.to_dict()
        self.assertEqual(d["alias"], "test_alias")

    def test_entity_reference(self):
        r = EntityReference(
            reference_id="REF-001",
            reference_type="observation",
            source_trace_id="TRACE-001",
        )
        d = r.to_dict()
        self.assertEqual(d["reference_id"], "REF-001")

    def test_relationship_reference(self):
        r = RelationshipReference(
            reference_id="RELREF-001",
            relationship_type="causal",
            source_observation_ids=["OBS-001"],
        )
        d = r.to_dict()
        self.assertEqual(d["reference_id"], "RELREF-001")

    def test_resolution_confidence_values(self):
        self.assertEqual(ResolutionConfidence.HIGH.value, "high")
        self.assertEqual(ResolutionConfidence.SPECULATIVE.value, "speculative")

    def test_candidate_relationship_types(self):
        expected = {
            "causal",
            "temporal",
            "constraint",
            "dependency",
            "association",
            "hierarchy",
            "conflict",
            "enables",
            "produces",
            "consumes",
        }
        actual = {rt.value for rt in CandidateRelationshipType}
        self.assertEqual(actual, expected)


class TestCandidateStatus(unittest.TestCase):
    def test_all_statuses(self):
        expected = {
            "draft",
            "assembled",
            "awaiting_governance",
            "governance_approved",
            "governance_rejected",
        }
        actual = {s.value for s in CandidateStatus}
        self.assertEqual(actual, expected)

    def test_assembled_status(self):
        wmc = _make_candidate()
        self.assertEqual(wmc.status, CandidateStatus.ASSEMBLED)


class TestExampleArtifacts(unittest.TestCase):
    def test_entity_example_exists(self):
        path = EXAMPLE_DIR / "candidate_entity_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertIn("entity_id", data)
        self.assertIn("entity_type", data)

    def test_relationship_example_exists(self):
        path = EXAMPLE_DIR / "candidate_relationship_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertIn("relationship_id", data)
        self.assertIn("from_entity_id", data)

    def test_causal_chain_example_exists(self):
        path = EXAMPLE_DIR / "candidate_causal_chain_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertIn("causal_chain", data)
        self.assertGreater(len(data["causal_chain"]), 0)

    def test_world_model_candidate_example_exists(self):
        path = EXAMPLE_DIR / "world_model_candidate_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertIn("candidate_id", data)
        self.assertIn("entities", data)
        self.assertIn("governance_status", data)

    def test_no_secrets_in_examples(self):
        for name in [
            "candidate_entity_example.json",
            "candidate_relationship_example.json",
            "candidate_causal_chain_example.json",
            "world_model_candidate_example.json",
        ]:
            raw = (EXAMPLE_DIR / name).read_text().lower()
            for keyword in ["password", "api_key", "secret_key", "bearer", "token_value"]:
                self.assertNotIn(keyword, raw, f"secret keyword '{keyword}' in {name}")


class TestEdgeCases(unittest.TestCase):
    def test_minimal_interpretation(self):
        content = "Hello."
        inp = InterpretationInput(
            input_id="INPUT-MINIMAL",
            source_content=content,
            source_content_hash=compute_hash(content),
            source_trace_id="TRACE-MINIMAL",
            source_state_id="STATE-MINIMAL",
        )
        interp = InterpretationEngineV1().interpret(inp)
        wmc = _make_candidate(interp)
        self.assertEqual(len(wmc.validate()), 0)

    def test_empty_hypotheses(self):
        interp = _make_interpretation()
        assembler = WorldModelCandidateAssembler()
        wmc = assembler.assemble(
            interpretation_result_id=interp.result_id,
            interpretation_output_hash=interp.output_hash,
            observations=[o.to_dict() for o in interp.observations],
            relationships=[r.to_dict() for r in interp.relationships],
            hypotheses=[],
            trace_id="TRACE-NOHYP",
        )
        self.assertEqual(len(wmc.validate()), 0)
        self.assertEqual(len(wmc.causal_links), 0)


if __name__ == "__main__":
    unittest.main()
