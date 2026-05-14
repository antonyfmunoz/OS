"""Tests for Phase 96.8AG — Full Live Ingestion Completion.

Verifies the complete governed ingestion chain:
  Discord !ingest-safe-doc → control plane → node sync → authority
  → gate → dispatch → supervisor → Drive/Docs adapter → extraction
  → normalization → primitive decomposition → ingestion candidate
  → memory candidate → ledger → replay → Discord result

Tests cover:
  - Command registration and routing
  - Safe doc targeting enforcement
  - Arbitrary URL / broad Drive blocking
  - Mutation blocking
  - Node sync requirement
  - Authority requirement
  - WorkPacket gate requirement
  - Identity refs preserved throughout
  - Adapter instance refs preserved
  - Extraction bounded
  - Normalization deterministic
  - Primitive decomposition created
  - Ingestion candidate created
  - Memory candidate created
  - Ledger state chain valid
  - Replay deterministic and immutable
  - No auto-promotion
  - No world-model mutation

UMH substrate subsystem. Phase 96.8AG.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

import pytest

from adapters.adapter_engine.google_docs_adapter_v1 import (
    ExtractionPath,
    GoogleDocsAdapterV1,
    NormalizedExtraction,
    normalize_text,
)
from adapters.adapter_engine.google_drive_adapter_v1 import GoogleDriveAdapterV1
from adapters.adapter_engine.live_drive_docs_ingestion_pipeline_v1 import (
    IngestionCandidate,
    MemoryCandidate,
    PIPELINE_FORBIDDEN_ACTIONS,
)
from control_plane.router.router_contracts import (
    ALLOWED_ACTION_TYPES,
    CapabilityType,
)
from control_plane.router.control_plane_router_v1 import (
    ACTION_CAPABILITY_MAP,
)
from execution.environments.windows_desktop_request_builder import (
    build_w0_full_live_ingestion_request,
)
from core.runtime.full_live_ingestion_spine_v1 import (
    FullLiveIngestionSpine,
    IdentityScopedMetadata,
    IngestionLedgerState,
    IngestionProof,
    IngestionSpineResult,
    INGESTION_FORBIDDEN_ACTIONS,
)
from state.transformation_state_ledger import (
    TransformationStage,
    TransformationStateLedger,
    compute_hash,
)
from runtime.interfaces.discord_interface_adapter_v1 import (
    COMMAND_ACTION_MAP,
    COMMAND_CONTRACT,
    SPINE_ROUTED_COMMANDS,
    SUPPORTED_COMMANDS,
    build_work_packet_for_router,
)
from runtime.interfaces.discord_spine_integration_v1 import (
    SpineExecutionConfig,
    build_spine_infrastructure,
    execute_spine_command,
    format_spine_result,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAFE_DOC_TITLE = "EOS W0 Test Document"
SAFE_DOC_URL = "https://docs.google.com/document/d/EOS-W0-SAFE-TEST-DOC/edit"
SAFE_DRIVE_URL = "https://drive.google.com/drive/my-drive"
GOOGLE_ACCOUNT = "antonyfm@empyreanstudios.co"
ADAPTER_INSTANCE = "gws-empyrean-primary-001"

SAMPLE_DOC_CONTENT = (
    "EntrepreneurOS is a production AI business operating system. "
    "It automates business operations through governed agents, "
    "structured memory, and deterministic execution pipelines. "
    "This is a safe test document for proving the ingestion lane."
)


def _make_config(**overrides: object) -> dict:
    config = {
        "safe_doc_title": SAFE_DOC_TITLE,
        "safe_doc_url_or_id": SAFE_DOC_URL,
        "safe_drive_url": SAFE_DRIVE_URL,
        "google_account_identity": GOOGLE_ACCOUNT,
        "adapter_instance_id": ADAPTER_INSTANCE,
        "allow_cu_path": False,
        "allow_api_path": True,
        "cu_enabled": False,
        "api_enabled": True,
        "require_parity": False,
        "preview_char_limit": 500,
        "max_extract_chars": 50000,
        "autostart_workers": True,
        "require_node_sync": True,
        "governance_required_for_promotion": True,
        "forbidden_actions": list(INGESTION_FORBIDDEN_ACTIONS),
    }
    config.update(overrides)
    return config


def _make_ledger(tmp_path: Path) -> TransformationStateLedger:
    return TransformationStateLedger(tmp_path / "ledger")


def _make_spine(tmp_path: Path, **config_overrides: object) -> FullLiveIngestionSpine:
    config = _make_config(**config_overrides)
    ledger = _make_ledger(tmp_path)
    proof_dir = tmp_path / "proofs"
    return FullLiveIngestionSpine(config, ledger, proof_dir)


# ===================================================================
# 1. Command Registration
# ===================================================================


class TestCommandRegistration:
    def test_ingest_safe_doc_in_supported_commands(self):
        assert "!ingest-safe-doc" in SUPPORTED_COMMANDS

    def test_ingest_safe_doc_in_action_map(self):
        assert COMMAND_ACTION_MAP["!ingest-safe-doc"] == "ingest_safe_doc"

    def test_ingest_safe_doc_is_spine_routed(self):
        assert "!ingest-safe-doc" in SPINE_ROUTED_COMMANDS

    def test_ingest_safe_doc_in_command_contract(self):
        contract = COMMAND_CONTRACT["!ingest-safe-doc"]
        assert contract["proof_required"] is True
        assert contract["mutation_allowed"] is False
        assert contract["capability"] == "DOCUMENT_EXTRACTION"

    def test_ingest_safe_doc_in_allowed_action_types(self):
        assert "ingest_safe_doc" in ALLOWED_ACTION_TYPES

    def test_ingest_safe_doc_in_capability_map(self):
        cap = ACTION_CAPABILITY_MAP["ingest_safe_doc"]
        assert cap.capability_type == CapabilityType.DOCUMENT_EXTRACTION
        assert cap.requires_gui is True

    def test_existing_commands_unaffected(self):
        for cmd in ["!ping", "!chrome", "!doc", "!extract", "!ingest-candidate"]:
            assert cmd in SUPPORTED_COMMANDS


# ===================================================================
# 2. Safe Doc Targeting
# ===================================================================


class TestSafeDocTargeting:
    def test_safe_doc_targeting_enforced(self, tmp_path):
        spine = _make_spine(tmp_path)
        errors = spine.validate_safe_doc_target()
        assert len(errors) == 0

    def test_missing_doc_url_blocked(self, tmp_path):
        spine = _make_spine(tmp_path, safe_doc_url_or_id="")
        errors = spine.validate_safe_doc_target()
        assert "safe_doc_url_or_id_not_configured" in errors

    def test_missing_doc_title_blocked(self, tmp_path):
        spine = _make_spine(tmp_path, safe_doc_title="")
        errors = spine.validate_safe_doc_target()
        assert "safe_doc_title_not_configured" in errors

    def test_missing_account_identity_blocked(self, tmp_path):
        spine = _make_spine(tmp_path, google_account_identity="")
        errors = spine.validate_safe_doc_target()
        assert "google_account_identity_not_configured" in errors

    def test_missing_adapter_instance_blocked(self, tmp_path):
        spine = _make_spine(tmp_path, adapter_instance_id="")
        errors = spine.validate_safe_doc_target()
        assert "adapter_instance_id_not_configured" in errors


# ===================================================================
# 3. Arbitrary URL Blocking
# ===================================================================


class TestArbitraryURLBlocking:
    def test_arbitrary_url_blocked(self, tmp_path):
        spine = _make_spine(tmp_path)
        errors = spine.validate_url_is_safe("https://evil.com/phish")
        assert "arbitrary_url_blocked" in errors

    def test_safe_url_allowed(self, tmp_path):
        spine = _make_spine(tmp_path)
        errors = spine.validate_url_is_safe(SAFE_DOC_URL)
        assert len(errors) == 0

    def test_empty_url_blocked(self, tmp_path):
        spine = _make_spine(tmp_path)
        errors = spine.validate_url_is_safe("")
        assert "url_empty" in errors


# ===================================================================
# 4. Broad Drive Search Blocking
# ===================================================================


class TestBroadDriveBlocking:
    def test_broad_drive_in_forbidden(self, tmp_path):
        spine = _make_spine(tmp_path)
        assert "broad_drive_ingestion" in spine.forbidden_actions

    def test_recursive_ingest_in_forbidden(self, tmp_path):
        spine = _make_spine(tmp_path)
        assert "recursively_ingest" in spine.forbidden_actions


# ===================================================================
# 5. Mutation Blocking
# ===================================================================


class TestMutationBlocking:
    def test_drive_mutation_blocked(self, tmp_path):
        spine = _make_spine(tmp_path)
        assert "mutate_drive" in spine.forbidden_actions

    def test_docs_mutation_blocked(self, tmp_path):
        spine = _make_spine(tmp_path)
        assert "mutate_docs" in spine.forbidden_actions

    def test_world_model_mutation_blocked(self, tmp_path):
        spine = _make_spine(tmp_path)
        assert "mutate_world_model" in spine.forbidden_actions


# ===================================================================
# 6. Node Sync Requirement
# ===================================================================


class TestNodeSyncRequirement:
    def test_spine_routed_commands_include_ingest(self):
        assert "!ingest-safe-doc" in SPINE_ROUTED_COMMANDS

    def test_spine_infrastructure_builds_with_sync_gate(self, tmp_path):
        config = SpineExecutionConfig(
            queue_dir=Path("data/runtime/test_spine_queue"),
            ledger_dir=Path("data/runtime/test_spine_ledger"),
            proof_dir=Path("data/runtime/test_spine_proofs"),
            gate_proof_dir=Path("data/runtime/test_spine_gate_proofs"),
        )
        spine = build_spine_infrastructure(config, Path(_ROOT))
        assert spine._sync_gate is not None


# ===================================================================
# 7. Authority Requirement
# ===================================================================


class TestAuthorityRequirement:
    def test_contract_requires_founder_approval(self):
        contract = COMMAND_CONTRACT["!ingest-safe-doc"]
        assert contract["authority_required"] == "FOUNDER_APPROVAL"

    def test_ingest_safe_doc_not_in_spine_forbidden(self):
        from core.runtime.live_local_runtime_execution_v1 import SPINE_FORBIDDEN_ACTIONS

        assert "ingest_safe_doc" not in SPINE_FORBIDDEN_ACTIONS


# ===================================================================
# 8. WorkPacket Gate Requirement
# ===================================================================


class TestWorkPacketGateRequirement:
    def test_work_packet_builds_for_ingest(self):
        wp = build_work_packet_for_router("!ingest-safe-doc")
        assert wp is not None
        assert wp.action_type == "ingest_safe_doc"

    def test_work_packet_has_trace_id(self):
        wp = build_work_packet_for_router("!ingest-safe-doc")
        assert wp.trace_id


# ===================================================================
# 9. Identity Refs Preserved
# ===================================================================


class TestIdentityRefsPreserved:
    def test_identity_metadata_creation(self):
        meta = IdentityScopedMetadata(
            source_account_id=GOOGLE_ACCOUNT,
            adapter_instance_id=ADAPTER_INSTANCE,
            document_id=SAFE_DOC_URL,
            document_title=SAFE_DOC_TITLE,
        )
        d = meta.to_dict()
        assert d["source_account_id"] == GOOGLE_ACCOUNT
        assert d["adapter_instance_id"] == ADAPTER_INSTANCE
        assert d["source_system"] == "google_workspace"
        assert d["permission_scope"] == "read_only"

    def test_identity_in_full_result(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.succeeded
        assert result.ingestion_proof.identity.source_account_id == GOOGLE_ACCOUNT
        assert result.ingestion_proof.identity.adapter_instance_id == ADAPTER_INSTANCE

    def test_identity_in_ingestion_candidate(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.ingestion_candidate["identity"]["source_account_id"] == GOOGLE_ACCOUNT

    def test_identity_in_memory_candidate(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.memory_candidate["identity"]["adapter_instance_id"] == ADAPTER_INSTANCE


# ===================================================================
# 10. Adapter Instance Refs Preserved
# ===================================================================


class TestAdapterInstanceRefs:
    def test_adapter_instance_in_ledger_states(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        for state in result.ledger_states:
            assert state["adapter_instance_id"] == ADAPTER_INSTANCE

    def test_source_identity_in_ledger_states(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        for state in result.ledger_states:
            assert state["source_identity_ref"] == GOOGLE_ACCOUNT


# ===================================================================
# 11. Extraction Bounded
# ===================================================================


class TestExtractionBounded:
    def test_extraction_respects_max_chars(self, tmp_path):
        long_content = "x" * 100000
        spine = _make_spine(tmp_path, max_extract_chars=1000)
        result = spine.execute_full_ingestion(long_content)
        assert result.succeeded
        assert result.extraction_result["char_count"] <= 1000

    def test_extraction_preserves_short_content(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.extraction_result["char_count"] == len(SAMPLE_DOC_CONTENT)


# ===================================================================
# 12. Normalization Deterministic
# ===================================================================


class TestNormalizationDeterministic:
    def test_normalization_produces_same_hash(self, tmp_path):
        spine1 = _make_spine(tmp_path)
        result1 = spine1.execute_full_ingestion(SAMPLE_DOC_CONTENT)

        spine2 = _make_spine(tmp_path)
        result2 = spine2.execute_full_ingestion(SAMPLE_DOC_CONTENT)

        assert (
            result1.normalized_extraction["normalized_hash"]
            == result2.normalized_extraction["normalized_hash"]
        )

    def test_normalization_strips_whitespace(self):
        raw = "  hello   world  \n   foo   bar  "
        normalized = normalize_text(raw)
        assert normalized == "hello world\nfoo bar"


# ===================================================================
# 13. Primitive Decomposition Created
# ===================================================================


class TestPrimitiveDecomposition:
    def test_decomposition_created(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.primitive_decomposition is not None
        assert result.primitive_decomposition["decomposition_type"] == "text_primitive"

    def test_decomposition_has_identity(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.primitive_decomposition["identity"]["source_account_id"] == GOOGLE_ACCOUNT


# ===================================================================
# 14. Ingestion Candidate Created
# ===================================================================


class TestIngestionCandidate:
    def test_candidate_created(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.ingestion_candidate is not None
        assert result.ingestion_candidate["candidate_id"].startswith("ING-CAND-")

    def test_candidate_not_promoted(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.ingestion_candidate["promoted"] is False

    def test_candidate_governance_state(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.ingestion_candidate["governance_state"] == "candidate"

    def test_candidate_has_doc_info(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.ingestion_candidate["doc_title"] == SAFE_DOC_TITLE
        assert result.ingestion_candidate["doc_url_or_id"] == SAFE_DOC_URL


# ===================================================================
# 15. Memory Candidate Created
# ===================================================================


class TestMemoryCandidate:
    def test_candidate_created(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.memory_candidate is not None
        assert result.memory_candidate["candidate_id"].startswith("MEM-CAND-")

    def test_candidate_awaiting_governance(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.memory_candidate["governance_state"] == "awaiting_governance"

    def test_candidate_not_promoted(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.memory_candidate["promoted"] is False

    def test_candidate_references_ingestion(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert (
            result.memory_candidate["ingestion_candidate_id"]
            == result.ingestion_candidate["candidate_id"]
        )


# ===================================================================
# 16. Ledger State Chain Valid
# ===================================================================


class TestLedgerStateChain:
    def test_ledger_has_states(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert len(result.ledger_states) >= 6

    def test_ledger_chain_linked(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        states = result.ledger_states
        for i in range(1, len(states)):
            assert states[i]["parent_state_id"] == states[i - 1]["state_id"]

    def test_ledger_stages_ordered(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        stage_names = [s["stage"] for s in result.ledger_states]
        expected_stages = [
            "drive_docs_opened",
            "document_extracted",
            "extraction_normalized",
            "primitives_decomposed",
            "ingestion_candidate_created",
            "memory_candidate_created",
            "replay_validated",
        ]
        assert stage_names == expected_stages

    def test_ledger_has_hashes(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        for state in result.ledger_states:
            assert state["input_hash"]
            assert state["output_hash"]

    def test_ledger_trace_consistent(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        trace_ids = {s["trace_id"] for s in result.ledger_states}
        assert len(trace_ids) == 1


# ===================================================================
# 17. Replay Deterministic
# ===================================================================


class TestReplayDeterministic:
    def test_replay_is_deterministic(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.replay_result["deterministic"] is True

    def test_replay_has_states(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.replay_result["total_states"] >= 5

    def test_replay_lineage_valid(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.replay_result["lineage_valid"] is True


# ===================================================================
# 18. Replay Immutable
# ===================================================================


class TestReplayImmutable:
    def test_replay_hashes_immutable(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.replay_result["hashes_immutable"] is True

    def test_replay_reconstruction_has_hashes(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        for entry in result.replay_result["reconstruction"]:
            assert "input_hash" in entry
            assert "output_hash" in entry


# ===================================================================
# 19. No Auto-Promotion
# ===================================================================


class TestNoAutoPromotion:
    def test_auto_promote_forbidden(self, tmp_path):
        spine = _make_spine(tmp_path)
        assert "auto_promote_canonical_truth" in spine.forbidden_actions

    def test_ingestion_proof_not_promoted(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.ingestion_proof.promoted is False
        assert result.ingestion_proof.governance_state == "candidate_only"


# ===================================================================
# 20. No World-Model Mutation
# ===================================================================


class TestNoWorldModelMutation:
    def test_world_model_mutation_forbidden(self, tmp_path):
        spine = _make_spine(tmp_path)
        assert "mutate_world_model" in spine.forbidden_actions

    def test_execution_planning_forbidden(self, tmp_path):
        spine = _make_spine(tmp_path)
        assert "invoke_execution_planning" in spine.forbidden_actions


# ===================================================================
# 21. End-to-End Full Ingestion
# ===================================================================


class TestEndToEndIngestion:
    def test_full_ingestion_succeeds(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.succeeded is True

    def test_full_ingestion_proof_complete(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        proof = result.ingestion_proof
        assert proof.ingestion_candidate_id.startswith("ING-CAND-")
        assert proof.memory_candidate_id.startswith("MEM-CAND-")
        assert proof.extraction_hash
        assert proof.normalized_hash
        assert proof.replay_deterministic is True

    def test_full_ingestion_all_artifacts_present(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.drive_open_proof is not None
        assert result.extraction_result is not None
        assert result.normalized_extraction is not None
        assert result.primitive_decomposition is not None
        assert result.ingestion_candidate is not None
        assert result.memory_candidate is not None
        assert result.replay_result is not None
        assert result.ingestion_proof is not None

    def test_full_ingestion_stages_completed(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        stages = result.ingestion_proof.stages_completed
        assert "drive_docs_opened" in stages
        assert "document_extracted" in stages
        assert "extraction_normalized" in stages
        assert "primitives_decomposed" in stages
        assert "ingestion_candidate_created" in stages
        assert "memory_candidate_created" in stages
        assert "replay_validated" in stages
        assert "ingestion_completed" in stages

    def test_full_ingestion_proof_persisted(self, tmp_path):
        spine = _make_spine(tmp_path)
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        proof_files = list((tmp_path / "proofs").glob("ING-PROOF-*.json"))
        assert len(proof_files) == 1
        data = json.loads(proof_files[0].read_text())
        assert data["proof_id"] == result.ingestion_proof.proof_id


# ===================================================================
# 22. Ingestion Fails Without Config
# ===================================================================


class TestIngestionFailsWithoutConfig:
    def test_fails_without_safe_doc_url(self, tmp_path):
        spine = _make_spine(tmp_path, safe_doc_url_or_id="")
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.succeeded is False
        assert "safe_doc_url_or_id_not_configured" in result.denial_reasons

    def test_fails_without_google_account(self, tmp_path):
        spine = _make_spine(tmp_path, google_account_identity="")
        result = spine.execute_full_ingestion(SAMPLE_DOC_CONTENT)
        assert result.succeeded is False
        assert "google_account_identity_not_configured" in result.denial_reasons


# ===================================================================
# 23. Request Builder
# ===================================================================


class TestRequestBuilder:
    def test_request_builds(self):
        req = build_w0_full_live_ingestion_request()
        d = req.to_dict()
        assert d["action_type"] == "ingest_safe_doc"
        assert d["no_mutation"] is True
        assert d["no_secret_capture"] is True

    def test_request_has_identity_notes(self):
        req = build_w0_full_live_ingestion_request(
            google_account_identity=GOOGLE_ACCOUNT,
            adapter_instance_id=ADAPTER_INSTANCE,
        )
        d = req.to_dict()
        notes = d["notes"]
        identity_notes = [n for n in notes if "Google account" in n or "Adapter instance" in n]
        assert len(identity_notes) == 2


# ===================================================================
# 24. Spine Integration
# ===================================================================


class TestSpineIntegration:
    def test_execute_spine_command_for_ingest(self, tmp_path):
        config = SpineExecutionConfig(
            queue_dir=Path("data/runtime/test_spine_queue"),
            ledger_dir=Path("data/runtime/test_spine_ledger"),
            proof_dir=Path("data/runtime/test_spine_proofs"),
            gate_proof_dir=Path("data/runtime/test_spine_gate_proofs"),
        )
        spine = build_spine_infrastructure(config, Path(_ROOT))
        result = execute_spine_command(spine, "!ingest-safe-doc")
        assert result.command == "!ingest-safe-doc"
        assert result.spine_result is not None

    def test_format_spine_result_for_ingest(self, tmp_path):
        config = SpineExecutionConfig(
            queue_dir=Path("data/runtime/test_spine_queue"),
            ledger_dir=Path("data/runtime/test_spine_ledger"),
            proof_dir=Path("data/runtime/test_spine_proofs"),
            gate_proof_dir=Path("data/runtime/test_spine_gate_proofs"),
        )
        spine = build_spine_infrastructure(config, Path(_ROOT))
        result = execute_spine_command(spine, "!ingest-safe-doc")
        formatted = format_spine_result(result)
        assert "!ingest-safe-doc" in formatted


# ===================================================================
# 25. Dataclass Contracts
# ===================================================================


class TestDataclassContracts:
    def test_identity_to_dict(self):
        meta = IdentityScopedMetadata(
            source_account_id="test@test.com",
            adapter_instance_id="test-001",
        )
        d = meta.to_dict()
        assert d["source_account_id"] == "test@test.com"
        assert d["governance_scope"] == "governed_ingestion"

    def test_ingestion_ledger_state_auto_id(self):
        state = IngestionLedgerState(
            state_id="",
            trace_id="test",
            parent_state_id="",
            stage="test_stage",
            input_hash="abc",
            output_hash="def",
        )
        assert state.state_id.startswith("STATE-")

    def test_ingestion_proof_auto_id(self):
        proof = IngestionProof(
            proof_id="",
            trace_id="test",
            identity=IdentityScopedMetadata(source_account_id="x", adapter_instance_id="y"),
        )
        assert proof.proof_id.startswith("ING-PROOF-")

    def test_ingestion_spine_result_auto_id(self):
        result = IngestionSpineResult(result_id="", trace_id="test")
        assert result.result_id.startswith("ING-RESULT-")

    def test_ingestion_spine_result_to_dict(self):
        result = IngestionSpineResult(result_id="", trace_id="test", succeeded=True)
        d = result.to_dict()
        assert d["succeeded"] is True
        assert d["trace_id"] == "test"

    def test_ingestion_proof_to_dict(self):
        meta = IdentityScopedMetadata(source_account_id="a@b.com", adapter_instance_id="inst-1")
        proof = IngestionProof(
            proof_id="",
            trace_id="t1",
            identity=meta,
            ingestion_candidate_id="ING-CAND-abc",
            memory_candidate_id="MEM-CAND-def",
        )
        d = proof.to_dict()
        assert d["ingestion_candidate_id"] == "ING-CAND-abc"
        assert d["identity"]["source_account_id"] == "a@b.com"


# ===================================================================
# 26. Regression — Existing Commands Unaffected
# ===================================================================


class TestRegressionExistingCommands:
    def test_ping_still_works(self):
        wp = build_work_packet_for_router("!ping")
        assert wp is not None
        assert wp.action_type == "ping"

    def test_chrome_still_works(self):
        wp = build_work_packet_for_router("!chrome")
        assert wp is not None
        assert wp.action_type == "open_application_url"

    def test_ingest_candidate_still_works(self):
        wp = build_work_packet_for_router("!ingest-candidate")
        assert wp is not None
        assert wp.action_type == "doc_ingestion_candidate_safe_test_doc"

    def test_chrome_open_google_drive_still_spine_routed(self):
        assert "!chrome-open-google-drive" in SPINE_ROUTED_COMMANDS

    def test_unknown_command_rejected(self):
        wp = build_work_packet_for_router("!nonexistent")
        assert wp is None
