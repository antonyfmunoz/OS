"""Tests for Interpretation Engine v1 — Phase 96.8W.

Validates the 5-stage pipeline, deterministic replay, governance
boundaries, primitive decomposition, hypothesis generation,
confidence envelopes, uncertainty tracking, forbidden actions,
and state ledger integration.
"""

import json
import sys
import unittest
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from substrate.understanding.interpretation.interpretation_engine_v1 import (
    FORBIDDEN_INTERPRETATION_ACTIONS,
    INTERPRETATION_STAGE_ORDER,
    ConfidenceEnvelope,
    InterpretationBoundary,
    InterpretationEngineV1,
    InterpretationHypothesis,
    InterpretationInput,
    InterpretationResult,
    InterpretationStage,
    _DeterministicIdGenerator,
)
from substrate.understanding.ontology.primitive_decomposition_v1 import (
    REQUIRED_PRIMITIVE_TYPES,
    DecompositionResult,
    PrimitiveObservation,
    PrimitiveRelationship,
    PrimitiveType,
    RelationshipType,
)
from state.transformation_state_ledger import (
    VALID_TRANSITIONS,
    TransformationStage,
    compute_hash,
)

EXAMPLE_DIR = Path(_ROOT) / "data" / "runtime" / "interpretation_states"


def _make_input(
    content: str = "UMH test document. Goal: validation. Constraint: safe. Resource: available.",
    input_id: str = "INPUT-TEST-001",
) -> InterpretationInput:
    return InterpretationInput(
        input_id=input_id,
        source_content=content,
        source_content_hash=compute_hash(content),
        source_trace_id="TRACE-TEST-001",
        source_state_id="STATE-TEST-001",
    )


def _run_engine(inp: InterpretationInput | None = None) -> InterpretationResult:
    engine = InterpretationEngineV1()
    return engine.interpret(inp or _make_input())


class TestPipelineCompleteness(unittest.TestCase):
    def test_all_5_stages_complete(self):
        result = _run_engine()
        expected = [s.value for s in INTERPRETATION_STAGE_ORDER]
        self.assertEqual(result.stages_completed, expected)

    def test_stage_order_is_correct(self):
        expected = [
            "observation",
            "pattern_detection",
            "primitive_mapping",
            "hypothesis_generation",
            "uncertainty_analysis",
        ]
        actual = [s.value for s in INTERPRETATION_STAGE_ORDER]
        self.assertEqual(actual, expected)


class TestDeterministicReplay(unittest.TestCase):
    def setUp(self):
        self.inp = _make_input()
        self.engine = InterpretationEngineV1()

    def test_same_input_same_output_hash(self):
        r1 = self.engine.interpret(self.inp)
        r2 = self.engine.interpret(self.inp)
        self.assertEqual(r1.output_hash, r2.output_hash)

    def test_same_result_id(self):
        r1 = self.engine.interpret(self.inp)
        r2 = self.engine.interpret(self.inp)
        self.assertEqual(r1.result_id, r2.result_id)

    def test_same_observation_ids(self):
        r1 = self.engine.interpret(self.inp)
        r2 = self.engine.interpret(self.inp)
        ids1 = [o.observation_id for o in r1.observations]
        ids2 = [o.observation_id for o in r2.observations]
        self.assertEqual(ids1, ids2)

    def test_same_hypothesis_ids(self):
        r1 = self.engine.interpret(self.inp)
        r2 = self.engine.interpret(self.inp)
        ids1 = [h.hypothesis_id for h in r1.hypotheses]
        ids2 = [h.hypothesis_id for h in r2.hypotheses]
        self.assertEqual(ids1, ids2)

    def test_same_decomposition_id(self):
        r1 = self.engine.interpret(self.inp)
        r2 = self.engine.interpret(self.inp)
        self.assertEqual(r1.decomposition.decomposition_id, r2.decomposition.decomposition_id)

    def test_different_content_different_hash(self):
        inp2 = _make_input(content="Completely different content for testing variation.")
        r1 = self.engine.interpret(self.inp)
        r2 = self.engine.interpret(inp2)
        self.assertNotEqual(r1.output_hash, r2.output_hash)

    def test_hash_is_64_chars(self):
        result = self.engine.interpret(self.inp)
        self.assertEqual(len(result.output_hash), 64)
        self.assertEqual(len(result.input_content_hash), 64)


class TestDeterministicIdGenerator(unittest.TestCase):
    def test_same_seed_same_sequence(self):
        g1 = _DeterministicIdGenerator("seed-abc")
        g2 = _DeterministicIdGenerator("seed-abc")
        for _ in range(5):
            self.assertEqual(g1.next_id("OBS"), g2.next_id("OBS"))

    def test_different_seed_different_ids(self):
        g1 = _DeterministicIdGenerator("seed-1")
        g2 = _DeterministicIdGenerator("seed-2")
        self.assertNotEqual(g1.next_id("OBS"), g2.next_id("OBS"))

    def test_different_prefix_different_ids(self):
        g = _DeterministicIdGenerator("seed-x")
        id1 = g.next_id("OBS")
        g2 = _DeterministicIdGenerator("seed-x")
        id2 = g2.next_id("HYP")
        self.assertNotEqual(id1, id2)

    def test_id_has_prefix(self):
        g = _DeterministicIdGenerator("seed")
        self.assertTrue(g.next_id("OBS").startswith("OBS-"))
        self.assertTrue(g.next_id("HYP").startswith("HYP-"))
        self.assertTrue(g.next_id("DECOMP").startswith("DECOMP-"))

    def test_counter_increments(self):
        g = _DeterministicIdGenerator("seed")
        ids = [g.next_id("X") for _ in range(10)]
        self.assertEqual(len(set(ids)), 10)


class TestObservations(unittest.TestCase):
    def test_observations_nonempty(self):
        result = _run_engine()
        self.assertGreater(len(result.observations), 0)

    def test_observations_have_valid_types(self):
        result = _run_engine()
        for obs in result.observations:
            self.assertIsInstance(obs.primitive_type, PrimitiveType)

    def test_observations_have_confidence(self):
        result = _run_engine()
        for obs in result.observations:
            self.assertGreater(obs.confidence, 0.0)
            self.assertLessEqual(obs.confidence, 1.0)

    def test_observations_have_ids(self):
        result = _run_engine()
        ids = [o.observation_id for o in result.observations]
        self.assertTrue(all(id_.startswith("OBS-") for id_ in ids))

    def test_observations_have_labels(self):
        result = _run_engine()
        for obs in result.observations:
            self.assertTrue(len(obs.label) > 0)


class TestRelationships(unittest.TestCase):
    def test_relationships_nonempty(self):
        result = _run_engine()
        self.assertGreater(len(result.relationships), 0)

    def test_relationships_reference_valid_observations(self):
        result = _run_engine()
        obs_ids = {o.observation_id for o in result.observations}
        for rel in result.relationships:
            self.assertIn(rel.from_observation_id, obs_ids)
            self.assertIn(rel.to_observation_id, obs_ids)

    def test_relationships_have_valid_types(self):
        result = _run_engine()
        for rel in result.relationships:
            self.assertIsInstance(rel.relationship_type, RelationshipType)


class TestPrimitiveDecomposition(unittest.TestCase):
    def test_decomposition_present(self):
        result = _run_engine()
        self.assertIsNotNone(result.decomposition)

    def test_decomposition_has_id(self):
        result = _run_engine()
        self.assertTrue(result.decomposition.decomposition_id.startswith("DECOMP-"))

    def test_decomposition_has_coverage(self):
        result = _run_engine()
        coverage = result.decomposition.primitive_type_coverage
        self.assertGreater(len(coverage), 0)

    def test_decomposition_confidence(self):
        result = _run_engine()
        self.assertGreater(result.decomposition.decomposition_confidence, 0.0)
        self.assertLessEqual(result.decomposition.decomposition_confidence, 1.0)

    def test_ontology_has_10_types(self):
        self.assertEqual(len(REQUIRED_PRIMITIVE_TYPES), 10)

    def test_all_primitive_types_exist(self):
        expected = {
            "state",
            "change",
            "constraint",
            "resource",
            "signal",
            "action",
            "outcome",
            "feedback",
            "goal",
            "time",
        }
        actual = {pt.value for pt in PrimitiveType}
        self.assertEqual(actual, expected)

    def test_all_relationship_types_exist(self):
        expected = {
            "causes",
            "constrains",
            "enables",
            "requires",
            "precedes",
            "follows",
            "produces",
            "consumes",
            "measures",
            "conflicts_with",
        }
        actual = {rt.value for rt in RelationshipType}
        self.assertEqual(actual, expected)

    def test_decomposition_to_dict(self):
        result = _run_engine()
        d = result.decomposition.to_dict()
        self.assertIn("decomposition_id", d)
        self.assertIn("observations", d)
        self.assertIn("relationships", d)
        self.assertIn("primitive_type_coverage", d)


class TestHypotheses(unittest.TestCase):
    def test_hypotheses_produced(self):
        result = _run_engine()
        self.assertGreater(len(result.hypotheses), 0)

    def test_hypotheses_require_governance(self):
        result = _run_engine()
        for hyp in result.hypotheses:
            self.assertTrue(hyp.requires_governance_review)

    def test_hypotheses_are_hypothesis_only(self):
        result = _run_engine()
        for hyp in result.hypotheses:
            self.assertEqual(hyp.promotion_status, "hypothesis_only")

    def test_hypotheses_have_supporting_observations(self):
        result = _run_engine()
        for hyp in result.hypotheses:
            self.assertGreater(len(hyp.supporting_observations), 0)

    def test_hypothesis_ids_have_prefix(self):
        result = _run_engine()
        for hyp in result.hypotheses:
            self.assertTrue(hyp.hypothesis_id.startswith("HYP-"))

    def test_hypothesis_to_dict(self):
        result = _run_engine()
        d = result.hypotheses[0].to_dict()
        self.assertIn("hypothesis_id", d)
        self.assertIn("statement", d)
        self.assertIn("confidence", d)
        self.assertIn("requires_governance_review", d)
        self.assertIn("promotion_status", d)


class TestConfidenceEnvelope(unittest.TestCase):
    def test_envelope_present(self):
        result = _run_engine()
        self.assertIsNotNone(result.confidence_envelope)

    def test_overall_confidence_positive(self):
        result = _run_engine()
        self.assertGreater(result.confidence_envelope.overall_confidence, 0.0)

    def test_uncertainty_score_present(self):
        result = _run_engine()
        self.assertGreater(result.confidence_envelope.uncertainty_score, 0.0)

    def test_confidence_dimensions_present(self):
        result = _run_engine()
        c = result.confidence_envelope
        self.assertGreater(c.observation_confidence, 0.0)
        self.assertGreater(c.pattern_confidence, 0.0)
        self.assertGreater(c.decomposition_confidence, 0.0)
        self.assertGreater(c.hypothesis_confidence, 0.0)

    def test_envelope_to_dict(self):
        result = _run_engine()
        d = result.confidence_envelope.to_dict()
        required_keys = [
            "overall_confidence",
            "uncertainty_score",
            "observation_confidence",
            "pattern_confidence",
            "decomposition_confidence",
            "hypothesis_confidence",
            "completeness_ratio",
            "assumptions_count",
            "unknowns_count",
        ]
        for key in required_keys:
            self.assertIn(key, d)


class TestUncertaintyTracking(unittest.TestCase):
    def test_unsupported_assumptions_present(self):
        result = _run_engine()
        self.assertGreater(len(result.unsupported_assumptions), 0)

    def test_explicit_unknowns_present(self):
        result = _run_engine()
        self.assertGreater(len(result.explicit_unknowns), 0)

    def test_missing_information_present(self):
        result = _run_engine()
        self.assertGreater(len(result.missing_information), 0)


class TestInterpretationBoundary(unittest.TestCase):
    def test_default_boundary_valid(self):
        b = InterpretationBoundary()
        self.assertEqual(b.validate(), [])

    def test_mutation_forbidden(self):
        b = InterpretationBoundary(may_mutate_canonical_memory=True)
        errors = b.validate()
        self.assertTrue(any("canonical memory" in e for e in errors))

    def test_world_model_update_forbidden(self):
        b = InterpretationBoundary(may_update_world_model=True)
        errors = b.validate()
        self.assertTrue(any("world model" in e for e in errors))

    def test_embedding_generation_forbidden(self):
        b = InterpretationBoundary(may_generate_embeddings=True)
        errors = b.validate()
        self.assertTrue(any("embedding" in e for e in errors))

    def test_knowledge_promotion_forbidden(self):
        b = InterpretationBoundary(may_promote_knowledge=True)
        errors = b.validate()
        self.assertTrue(any("promote" in e for e in errors))

    def test_execution_trigger_forbidden(self):
        b = InterpretationBoundary(may_trigger_execution=True)
        errors = b.validate()
        self.assertTrue(any("execution" in e for e in errors))

    def test_self_expansion_forbidden(self):
        b = InterpretationBoundary(may_self_expand=True)
        errors = b.validate()
        self.assertTrue(any("self-expand" in e for e in errors))

    def test_allowed_capabilities(self):
        b = InterpretationBoundary()
        self.assertTrue(b.may_infer)
        self.assertTrue(b.may_decompose)
        self.assertTrue(b.may_classify)
        self.assertTrue(b.may_identify_patterns)
        self.assertTrue(b.may_generate_hypotheses)

    def test_boundary_to_dict(self):
        b = InterpretationBoundary()
        d = b.to_dict()
        self.assertIn("may_infer", d)
        self.assertIn("may_mutate_canonical_memory", d)
        self.assertEqual(len(d), 11)


class TestForbiddenActions(unittest.TestCase):
    def test_forbidden_actions_count(self):
        self.assertEqual(len(FORBIDDEN_INTERPRETATION_ACTIONS), 10)

    def test_result_blocks_all_forbidden(self):
        result = _run_engine()
        blocked = set(result.blocked_actions)
        forbidden = set(FORBIDDEN_INTERPRETATION_ACTIONS)
        self.assertTrue(forbidden.issubset(blocked))

    def test_allowed_actions_nonempty(self):
        result = _run_engine()
        self.assertGreater(len(result.allowed_actions), 0)

    def test_no_overlap_allowed_blocked(self):
        result = _run_engine()
        allowed = set(result.allowed_actions)
        blocked = set(result.blocked_actions)
        self.assertEqual(len(allowed & blocked), 0)


class TestStateLedgerIntegration(unittest.TestCase):
    def test_interpretation_stage_exists(self):
        self.assertIn(TransformationStage.INTERPRETATION, VALID_TRANSITIONS)

    def test_primitive_decomposition_stage_exists(self):
        self.assertIn(TransformationStage.PRIMITIVE_DECOMPOSITION, VALID_TRANSITIONS)

    def test_interpretation_to_primitive_decomposition(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.INTERPRETATION]
        self.assertIn(TransformationStage.PRIMITIVE_DECOMPOSITION, valid_next)

    def test_interpretation_cannot_reach_canonical(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.INTERPRETATION]
        self.assertNotIn(TransformationStage.CANONICAL_MEMORY, valid_next)

    def test_interpretation_cannot_reach_world_model(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.INTERPRETATION]
        self.assertNotIn(TransformationStage.WORLD_MODEL_MUTATION, valid_next)

    def test_normalization_to_interpretation(self):
        valid_next = VALID_TRANSITIONS[TransformationStage.NORMALIZATION]
        self.assertIn(TransformationStage.INTERPRETATION, valid_next)


class TestResultValidation(unittest.TestCase):
    def test_valid_result_passes(self):
        result = _run_engine()
        self.assertEqual(result.validate(), [])

    def test_result_to_dict(self):
        result = _run_engine()
        d = result.to_dict()
        required_keys = [
            "result_id",
            "input_id",
            "input_content_hash",
            "output_hash",
            "stages_completed",
            "observations",
            "relationships",
            "decomposition",
            "hypotheses",
            "confidence_envelope",
            "boundary",
            "unsupported_assumptions",
            "missing_information",
            "explicit_unknowns",
            "blocked_actions",
            "allowed_actions",
        ]
        for key in required_keys:
            self.assertIn(key, d, f"missing key: {key}")

    def test_result_json_serializable(self):
        result = _run_engine()
        d = result.to_dict()
        json_str = json.dumps(d)
        self.assertGreater(len(json_str), 0)


class TestInterpretationInput(unittest.TestCase):
    def test_input_has_required_fields(self):
        inp = _make_input()
        self.assertTrue(len(inp.input_id) > 0)
        self.assertTrue(len(inp.source_content) > 0)
        self.assertTrue(len(inp.source_content_hash) > 0)
        self.assertTrue(len(inp.source_trace_id) > 0)
        self.assertTrue(len(inp.source_state_id) > 0)

    def test_input_to_dict(self):
        inp = _make_input()
        d = inp.to_dict()
        self.assertIn("input_id", d)
        self.assertIn("source_content_hash", d)


class TestExampleArtifacts(unittest.TestCase):
    def test_interpretation_state_example_exists(self):
        path = EXAMPLE_DIR / "interpretation_state_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["stage"], "interpretation")

    def test_primitive_decomposition_example_exists(self):
        path = EXAMPLE_DIR / "primitive_decomposition_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["stage"], "primitive_decomposition")

    def test_uncertainty_analysis_example_exists(self):
        path = EXAMPLE_DIR / "uncertainty_analysis_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["stage"], "uncertainty_analysis")

    def test_interpretation_state_has_hashes(self):
        data = json.loads((EXAMPLE_DIR / "interpretation_state_example.json").read_text())
        self.assertTrue(len(data["input_hash"]) > 0)
        self.assertTrue(len(data["output_hash"]) > 0)

    def test_decomposition_has_coverage(self):
        data = json.loads((EXAMPLE_DIR / "primitive_decomposition_example.json").read_text())
        self.assertIn("decomposition", data)
        decomp = data["decomposition"]
        self.assertIn("primitive_type_coverage", decomp)

    def test_uncertainty_has_envelope(self):
        data = json.loads((EXAMPLE_DIR / "uncertainty_analysis_example.json").read_text())
        self.assertIn("confidence_envelope", data)
        self.assertIn("hypotheses", data)

    def test_no_secrets_in_examples(self):
        for name in [
            "interpretation_state_example.json",
            "primitive_decomposition_example.json",
            "uncertainty_analysis_example.json",
        ]:
            raw = (EXAMPLE_DIR / name).read_text().lower()
            for keyword in ["password", "api_key", "secret_key", "bearer", "token_value"]:
                self.assertNotIn(keyword, raw, f"secret keyword '{keyword}' in {name}")


class TestEngineEdgeCases(unittest.TestCase):
    def test_minimal_content(self):
        inp = _make_input(content="Hello.")
        result = _run_engine(inp)
        self.assertEqual(len(result.validate()), 0)

    def test_empty_content_still_produces_result(self):
        inp = _make_input(content="")
        result = _run_engine(inp)
        self.assertEqual(len(result.validate()), 0)

    def test_long_content(self):
        inp = _make_input(content="test " * 1000)
        result = _run_engine(inp)
        self.assertEqual(len(result.validate()), 0)

    def test_boundary_violation_raises(self):
        engine = InterpretationEngineV1()
        engine.boundary = InterpretationBoundary(may_mutate_canonical_memory=True)
        inp = _make_input()
        with self.assertRaises(ValueError):
            engine.interpret(inp)


if __name__ == "__main__":
    unittest.main()
