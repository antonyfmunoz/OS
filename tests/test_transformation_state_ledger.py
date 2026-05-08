"""Tests for Transformation State Ledger -- Phase 96.8V.

Validates state creation, validation rules, lineage reconstruction,
rollback traversal, governance enforcement, transition validation,
deterministic trace replay, and forbidden field detection.
"""

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, "/opt/OS")

from core.state.transformation_state_ledger import (
    GOVERNANCE_REQUIRED_STAGES,
    MUTATION_BLOCKED_STAGES,
    VALID_TRANSITIONS,
    StateArtifactReference,
    StateLedgerRecord,
    TransformationStage,
    TransformationStateLedger,
    compute_hash,
    make_state_id,
    make_trace_id,
)

LEDGER_EXAMPLE_DIR = Path("/opt/OS/data/runtime/transformation_ledger")


def _make_record(
    stage: TransformationStage,
    parent_state_id: str = "",
    trace_id: str = "TRACE-TEST-001",
    governance_reference: str = "",
    rollback_reference: str = "",
    input_hash: str = "aaa",
    output_hash: str = "bbb",
    state_id: str = "",
    allowed_next: list[str] | None = None,
    blocked_next: list[str] | None = None,
) -> StateLedgerRecord:
    return StateLedgerRecord(
        state_id=state_id or make_state_id(),
        trace_id=trace_id,
        parent_state_id=parent_state_id,
        stage=stage,
        input_artifact_ref=StateArtifactReference("IN-001", "test"),
        output_artifact_ref=StateArtifactReference("OUT-001", "test"),
        transformer_name="test_transformer",
        transformer_version="v1",
        runtime_id="test_runtime",
        adapter_id="test_adapter",
        policy_envelope={"test": True},
        confidence="high",
        input_hash=input_hash,
        output_hash=output_hash,
        governance_reference=governance_reference,
        rollback_reference=rollback_reference,
        allowed_next_actions=allowed_next if allowed_next is not None else ["test_action"],
        blocked_next_actions=blocked_next if blocked_next is not None else [],
    )


class TestStateLedgerRecordCreation(unittest.TestCase):
    def test_creates_valid_record(self):
        r = _make_record(TransformationStage.EXTRACTION)
        self.assertTrue(r.state_id.startswith("STATE-"))
        self.assertEqual(r.stage, TransformationStage.EXTRACTION)

    def test_to_dict_has_all_fields(self):
        r = _make_record(TransformationStage.NORMALIZATION)
        d = r.to_dict()
        required_keys = [
            "state_id",
            "trace_id",
            "parent_state_id",
            "stage",
            "input_artifact_ref",
            "output_artifact_ref",
            "transformer_name",
            "transformer_version",
            "runtime_id",
            "adapter_id",
            "policy_envelope",
            "confidence",
            "input_hash",
            "output_hash",
            "timestamp",
            "allowed_next_actions",
            "blocked_next_actions",
            "rollback_reference",
            "governance_reference",
            "notes",
        ]
        for key in required_keys:
            self.assertIn(key, d, f"missing key: {key}")

    def test_timestamp_auto_populated(self):
        r = _make_record(TransformationStage.RAW_SOURCE)
        self.assertTrue(len(r.timestamp) > 0)


class TestStateLedgerValidation(unittest.TestCase):
    def setUp(self):
        self._tmpdir = TemporaryDirectory()
        self.ledger = TransformationStateLedger(Path(self._tmpdir.name))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_valid_record_passes(self):
        r = _make_record(TransformationStage.EXTRACTION)
        errors = self.ledger.validate_record(r)
        self.assertEqual(errors, [])

    def test_missing_input_hash_rejected(self):
        r = _make_record(TransformationStage.EXTRACTION, input_hash="")
        errors = self.ledger.validate_record(r)
        self.assertTrue(any("input_hash" in e for e in errors))

    def test_missing_output_hash_rejected(self):
        r = _make_record(TransformationStage.EXTRACTION, output_hash="")
        errors = self.ledger.validate_record(r)
        self.assertTrue(any("output_hash" in e for e in errors))

    def test_missing_actions_rejected(self):
        r = _make_record(
            TransformationStage.EXTRACTION,
            allowed_next=[],
            blocked_next=[],
        )
        errors = self.ledger.validate_record(r)
        self.assertTrue(
            any("allowed_next_actions" in e or "blocked_next_actions" in e for e in errors)
        )

    def test_canonical_memory_requires_governance(self):
        r = _make_record(
            TransformationStage.CANONICAL_MEMORY,
            governance_reference="",
        )
        errors = self.ledger.validate_record(r)
        self.assertTrue(any("governance_reference" in e for e in errors))

    def test_world_model_mutation_requires_governance(self):
        r = _make_record(
            TransformationStage.WORLD_MODEL_MUTATION,
            governance_reference="",
        )
        errors = self.ledger.validate_record(r)
        self.assertTrue(any("governance_reference" in e for e in errors))

    def test_canonical_memory_with_governance_passes(self):
        r = _make_record(
            TransformationStage.CANONICAL_MEMORY,
            governance_reference="GOV-001",
        )
        errors = self.ledger.validate_record(r)
        self.assertEqual(errors, [])

    def test_extraction_does_not_require_governance(self):
        r = _make_record(TransformationStage.EXTRACTION)
        errors = self.ledger.validate_record(r)
        self.assertEqual(errors, [])


class TestStateLedgerTransitionValidation(unittest.TestCase):
    def setUp(self):
        self._tmpdir = TemporaryDirectory()
        self.ledger = TransformationStateLedger(Path(self._tmpdir.name))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_valid_transition_accepted(self):
        parent = _make_record(TransformationStage.RAW_SOURCE, state_id="STATE-parent01")
        self.ledger.append(parent)
        child = _make_record(
            TransformationStage.EXTRACTION,
            parent_state_id="STATE-parent01",
        )
        errors = self.ledger.validate_record(child)
        self.assertEqual(errors, [])

    def test_invalid_transition_rejected(self):
        parent = _make_record(TransformationStage.RAW_SOURCE, state_id="STATE-parent02")
        self.ledger.append(parent)
        child = _make_record(
            TransformationStage.CANONICAL_MEMORY,
            parent_state_id="STATE-parent02",
            governance_reference="GOV-X",
        )
        errors = self.ledger.validate_record(child)
        self.assertTrue(any("invalid transition" in e for e in errors))

    def test_extraction_cannot_jump_to_canonical(self):
        parent = _make_record(TransformationStage.EXTRACTION, state_id="STATE-ext99")
        self.ledger.append(parent)
        child = _make_record(
            TransformationStage.CANONICAL_MEMORY,
            parent_state_id="STATE-ext99",
            governance_reference="GOV-X",
        )
        errors = self.ledger.validate_record(child)
        self.assertTrue(any("invalid transition" in e for e in errors))

    def test_interpretation_cannot_directly_mutate_canonical(self):
        parent = _make_record(TransformationStage.INTERPRETATION, state_id="STATE-interp99")
        self.ledger.append(parent)
        child = _make_record(
            TransformationStage.CANONICAL_MEMORY,
            parent_state_id="STATE-interp99",
            governance_reference="GOV-X",
        )
        errors = self.ledger.validate_record(child)
        self.assertTrue(any("invalid transition" in e for e in errors))


class TestLineageReconstruction(unittest.TestCase):
    def setUp(self):
        self._tmpdir = TemporaryDirectory()
        self.ledger = TransformationStateLedger(Path(self._tmpdir.name))
        self.trace_id = "TRACE-LINEAGE-TEST"

    def tearDown(self):
        self._tmpdir.cleanup()

    def _build_chain(self) -> str:
        ids = ["STATE-r", "STATE-e", "STATE-n", "STATE-i", "STATE-m", "STATE-g", "STATE-c"]
        stages = [
            TransformationStage.RAW_SOURCE,
            TransformationStage.EXTRACTION,
            TransformationStage.NORMALIZATION,
            TransformationStage.INGESTION_CANDIDATE,
            TransformationStage.MEMORY_CANDIDATE,
            TransformationStage.GOVERNANCE_REVIEW,
            TransformationStage.CANONICAL_MEMORY,
        ]
        for i, (sid, stage) in enumerate(zip(ids, stages)):
            parent = ids[i - 1] if i > 0 else ""
            gov = "GOV-TEST" if stage in GOVERNANCE_REQUIRED_STAGES else ""
            r = _make_record(
                stage,
                parent_state_id=parent,
                trace_id=self.trace_id,
                governance_reference=gov,
                state_id=sid,
            )
            errors = self.ledger.append(r)
            self.assertEqual(errors, [], f"append failed for {sid}: {errors}")
        return ids[-1]

    def test_full_lineage_reconstruction(self):
        final_id = self._build_chain()
        lineage = self.ledger.reconstruct_lineage(final_id)
        self.assertEqual(len(lineage), 7)

    def test_lineage_order_is_root_to_leaf(self):
        final_id = self._build_chain()
        lineage = self.ledger.reconstruct_lineage(final_id)
        self.assertEqual(lineage[0].stage, TransformationStage.RAW_SOURCE)
        self.assertEqual(lineage[-1].stage, TransformationStage.CANONICAL_MEMORY)

    def test_trace_replay_returns_all_records(self):
        self._build_chain()
        trace = self.ledger.get_trace(self.trace_id)
        self.assertEqual(len(trace), 7)

    def test_deterministic_trace_reconstruction(self):
        self._build_chain()
        trace1 = self.ledger.get_trace(self.trace_id)
        trace2 = self.ledger.get_trace(self.trace_id)
        self.assertEqual(
            [r.state_id for r in trace1],
            [r.state_id for r in trace2],
        )


class TestRollbackChain(unittest.TestCase):
    def setUp(self):
        self._tmpdir = TemporaryDirectory()
        self.ledger = TransformationStateLedger(Path(self._tmpdir.name))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_rollback_chain_includes_references(self):
        r1 = _make_record(
            TransformationStage.GOVERNANCE_REVIEW, state_id="STATE-g1", rollback_reference=""
        )
        self.ledger.append(r1)
        r2 = _make_record(
            TransformationStage.CANONICAL_MEMORY,
            parent_state_id="STATE-g1",
            state_id="STATE-c1",
            rollback_reference="ROLLBACK-TEST-001",
            governance_reference="GOV-TEST",
        )
        self.ledger.append(r2)
        chain = self.ledger.get_rollback_chain("STATE-c1")
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0]["rollback_reference"], "ROLLBACK-TEST-001")

    def test_empty_rollback_excluded(self):
        r = _make_record(TransformationStage.EXTRACTION, state_id="STATE-nrb")
        self.ledger.append(r)
        chain = self.ledger.get_rollback_chain("STATE-nrb")
        self.assertEqual(len(chain), 0)


class TestLedgerPersistence(unittest.TestCase):
    def setUp(self):
        self._tmpdir = TemporaryDirectory()
        self.ledger_dir = Path(self._tmpdir.name)
        self.ledger = TransformationStateLedger(self.ledger_dir)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_records_persisted_to_disk(self):
        r = _make_record(TransformationStage.EXTRACTION, state_id="STATE-persist01")
        self.ledger.append(r)
        path = self.ledger_dir / "STATE-persist01.json"
        self.assertTrue(path.exists())

    def test_persisted_json_valid(self):
        r = _make_record(TransformationStage.NORMALIZATION, state_id="STATE-persist02")
        self.ledger.append(r)
        path = self.ledger_dir / "STATE-persist02.json"
        data = json.loads(path.read_text())
        self.assertEqual(data["state_id"], "STATE-persist02")
        self.assertEqual(data["stage"], "normalization")


class TestLedgerExampleArtifacts(unittest.TestCase):
    def test_extraction_example_exists(self):
        path = LEDGER_EXAMPLE_DIR / "extraction_state_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["stage"], "extraction")
        self.assertTrue(len(data["input_hash"]) > 0)
        self.assertTrue(len(data["output_hash"]) > 0)

    def test_normalization_example_exists(self):
        path = LEDGER_EXAMPLE_DIR / "normalization_state_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["stage"], "normalization")

    def test_memory_candidate_example_exists(self):
        path = LEDGER_EXAMPLE_DIR / "memory_candidate_state_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["stage"], "memory_candidate")

    def test_canonical_memory_example_exists(self):
        path = LEDGER_EXAMPLE_DIR / "canonical_memory_state_example.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["stage"], "canonical_memory")
        self.assertTrue(len(data["governance_reference"]) > 0)

    def test_canonical_example_has_rollback(self):
        path = LEDGER_EXAMPLE_DIR / "canonical_memory_state_example.json"
        data = json.loads(path.read_text())
        self.assertTrue(len(data["rollback_reference"]) > 0)

    def test_no_secrets_in_examples(self):
        for name in [
            "extraction_state_example.json",
            "normalization_state_example.json",
            "memory_candidate_state_example.json",
            "canonical_memory_state_example.json",
        ]:
            raw = (LEDGER_EXAMPLE_DIR / name).read_text().lower()
            for keyword in ["password", "api_key", "secret_key", "bearer", "token_value"]:
                self.assertNotIn(keyword, raw, f"secret keyword '{keyword}' in {name}")


class TestTransformationStages(unittest.TestCase):
    def test_all_stages_in_valid_transitions(self):
        for stage in TransformationStage:
            self.assertIn(stage, VALID_TRANSITIONS)

    def test_governance_required_stages(self):
        self.assertIn(TransformationStage.CANONICAL_MEMORY, GOVERNANCE_REQUIRED_STAGES)
        self.assertIn(TransformationStage.WORLD_MODEL_MUTATION, GOVERNANCE_REQUIRED_STAGES)

    def test_mutation_blocked_stages(self):
        for stage in MUTATION_BLOCKED_STAGES:
            self.assertNotIn(stage, GOVERNANCE_REQUIRED_STAGES)

    def test_extraction_cannot_reach_canonical_directly(self):
        valid_from_extraction = VALID_TRANSITIONS[TransformationStage.EXTRACTION]
        self.assertNotIn(TransformationStage.CANONICAL_MEMORY, valid_from_extraction)

    def test_interpretation_cannot_reach_canonical_directly(self):
        valid_from_interp = VALID_TRANSITIONS[TransformationStage.INTERPRETATION]
        self.assertNotIn(TransformationStage.CANONICAL_MEMORY, valid_from_interp)


class TestDeterministicHash(unittest.TestCase):
    def test_same_content_same_hash(self):
        h1 = compute_hash("test content")
        h2 = compute_hash("test content")
        self.assertEqual(h1, h2)

    def test_different_content_different_hash(self):
        h1 = compute_hash("content A")
        h2 = compute_hash("content B")
        self.assertNotEqual(h1, h2)

    def test_hash_is_64_chars(self):
        h = compute_hash("any content")
        self.assertEqual(len(h), 64)


if __name__ == "__main__":
    unittest.main()
