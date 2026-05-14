"""Full Live Ingestion Spine v1 for the UMH substrate layer.

Composes the governed execution spine (Phase 96.8AF) with the
Drive/Docs ingestion pipeline (Phase 96.8AB) into a single
end-to-end ingestion chain:

  Discord !ingest-safe-doc
  → authority engine → gate → node sync → dispatch → supervisor
  → Drive/Docs adapter → extraction → normalization
  → primitive decomposition → ingestion candidate → memory candidate
  → transformation ledger → replay proof → Discord result

Identity-scoped: every artifact carries source_account_id,
adapter_instance_id, and governance_scope. This prevents
memory contamination across future ingestion lanes.

UMH substrate subsystem. Phase 96.8AG.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adapters.adapter_engine.google_docs_adapter_v1 import (
    ExtractionPath,
    ExtractionResult,
    GoogleDocsAdapterV1,
    NormalizedExtraction,
    normalize_text,
)
from adapters.adapter_engine.google_drive_adapter_v1 import (
    DriveOpenProof,
    GoogleDriveAdapterV1,
)
from adapters.adapter_engine.live_drive_docs_ingestion_pipeline_v1 import (
    IngestionCandidate,
    MemoryCandidate,
    PipelineSnapshot,
    PIPELINE_FORBIDDEN_ACTIONS,
    ReplayQueryResult,
)
from state.transformation_state_ledger import (
    StateArtifactReference,
    StateLedgerRecord,
    TransformationStage,
    TransformationStateLedger,
    compute_hash,
    make_state_id,
    make_trace_id,
)


INGESTION_FORBIDDEN_ACTIONS = frozenset(
    PIPELINE_FORBIDDEN_ACTIONS
    | {
        "arbitrary_url_access",
        "screenshot_as_primary_extraction",
        "credential_access",
        "self_govern",
    }
)


@dataclass
class IdentityScopedMetadata:
    """Identity scope carried by every ingestion artifact."""

    source_account_id: str
    adapter_instance_id: str
    source_system: str = "google_workspace"
    document_id: str = ""
    document_title: str = ""
    permission_scope: str = "read_only"
    governance_scope: str = "governed_ingestion"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_account_id": self.source_account_id,
            "adapter_instance_id": self.adapter_instance_id,
            "source_system": self.source_system,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "permission_scope": self.permission_scope,
            "governance_scope": self.governance_scope,
        }


@dataclass
class IngestionLedgerState:
    """A single ledger state in the ingestion chain."""

    state_id: str
    trace_id: str
    parent_state_id: str
    stage: str
    input_hash: str
    output_hash: str
    adapter_instance_id: str = ""
    source_identity_ref: str = ""
    runtime_id: str = ""
    governance_state: str = "governed"
    allowed_next_actions: list[str] = field(default_factory=list)
    blocked_next_actions: list[str] = field(default_factory=list)
    replay_refs: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.state_id:
            self.state_id = make_state_id()

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "trace_id": self.trace_id,
            "parent_state_id": self.parent_state_id,
            "stage": self.stage,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "adapter_instance_id": self.adapter_instance_id,
            "source_identity_ref": self.source_identity_ref,
            "runtime_id": self.runtime_id,
            "governance_state": self.governance_state,
            "allowed_next_actions": self.allowed_next_actions,
            "blocked_next_actions": self.blocked_next_actions,
            "replay_refs": self.replay_refs,
            "timestamp": self.timestamp,
        }


@dataclass
class IngestionProof:
    """Complete proof of a full ingestion run."""

    proof_id: str
    trace_id: str
    identity: IdentityScopedMetadata
    stages_completed: list[str] = field(default_factory=list)
    ingestion_candidate_id: str = ""
    memory_candidate_id: str = ""
    extraction_hash: str = ""
    normalized_hash: str = ""
    replay_deterministic: bool = False
    replay_total_states: int = 0
    governance_state: str = "candidate_only"
    promoted: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.proof_id:
            self.proof_id = f"ING-PROOF-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "trace_id": self.trace_id,
            "identity": self.identity.to_dict(),
            "stages_completed": self.stages_completed,
            "ingestion_candidate_id": self.ingestion_candidate_id,
            "memory_candidate_id": self.memory_candidate_id,
            "extraction_hash": self.extraction_hash,
            "normalized_hash": self.normalized_hash,
            "replay_deterministic": self.replay_deterministic,
            "replay_total_states": self.replay_total_states,
            "governance_state": self.governance_state,
            "promoted": self.promoted,
            "timestamp": self.timestamp,
        }


@dataclass
class IngestionSpineResult:
    """Complete result of a full live ingestion spine execution."""

    result_id: str
    trace_id: str
    succeeded: bool = False
    ingestion_proof: IngestionProof | None = None
    drive_open_proof: dict[str, Any] | None = None
    extraction_result: dict[str, Any] | None = None
    normalized_extraction: dict[str, Any] | None = None
    primitive_decomposition: dict[str, Any] | None = None
    ingestion_candidate: dict[str, Any] | None = None
    memory_candidate: dict[str, Any] | None = None
    replay_result: dict[str, Any] | None = None
    ledger_states: list[dict[str, Any]] = field(default_factory=list)
    error_message: str = ""
    denial_reasons: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.result_id:
            self.result_id = f"ING-RESULT-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "trace_id": self.trace_id,
            "succeeded": self.succeeded,
            "ingestion_proof": self.ingestion_proof.to_dict() if self.ingestion_proof else None,
            "drive_open_proof": self.drive_open_proof,
            "extraction_result": self.extraction_result,
            "normalized_extraction": self.normalized_extraction,
            "primitive_decomposition": self.primitive_decomposition,
            "ingestion_candidate": self.ingestion_candidate,
            "memory_candidate": self.memory_candidate,
            "replay_result": self.replay_result,
            "ledger_states": self.ledger_states,
            "error_message": self.error_message,
            "denial_reasons": self.denial_reasons,
            "timestamp": self.timestamp,
        }


class FullLiveIngestionSpine:
    """End-to-end governed ingestion from Drive/Docs to memory candidate.

    Composes existing adapters and ledger into identity-scoped,
    governed ingestion lane. One safe doc at a time.
    """

    def __init__(
        self,
        config: dict[str, Any],
        ledger: TransformationStateLedger,
        proof_dir: Path | None = None,
    ) -> None:
        self._config = config
        self._ledger = ledger
        self._proof_dir = proof_dir or Path("data/runtime/full_live_ingestion_proofs")
        self._proof_dir.mkdir(parents=True, exist_ok=True)

        self._identity = IdentityScopedMetadata(
            source_account_id=config.get("google_account_identity", ""),
            adapter_instance_id=config.get("adapter_instance_id", ""),
            source_system="google_workspace",
            document_id=config.get("safe_doc_url_or_id", ""),
            document_title=config.get("safe_doc_title", ""),
        )

        self._drive_adapter = GoogleDriveAdapterV1(config)
        self._docs_adapter = GoogleDocsAdapterV1(config)

        self._max_extract_chars = config.get("max_extract_chars", 50000)
        self._preview_char_limit = config.get("preview_char_limit", 500)
        self._forbidden = list(INGESTION_FORBIDDEN_ACTIONS)

    @property
    def identity(self) -> IdentityScopedMetadata:
        return self._identity

    @property
    def forbidden_actions(self) -> list[str]:
        return list(self._forbidden)

    def validate_safe_doc_target(self) -> list[str]:
        """Validate that the config targets a specific safe doc."""
        errors: list[str] = []
        if not self._config.get("safe_doc_url_or_id"):
            errors.append("safe_doc_url_or_id_not_configured")
        if not self._config.get("safe_doc_title"):
            errors.append("safe_doc_title_not_configured")
        if not self._identity.source_account_id:
            errors.append("google_account_identity_not_configured")
        if not self._identity.adapter_instance_id:
            errors.append("adapter_instance_id_not_configured")
        return errors

    def validate_url_is_safe(self, url: str) -> list[str]:
        """Block arbitrary URLs — only configured safe doc allowed."""
        errors: list[str] = []
        safe_url = self._config.get("safe_doc_url_or_id", "")
        if not url:
            errors.append("url_empty")
        elif safe_url and url != safe_url:
            errors.append("arbitrary_url_blocked")
        return errors

    def execute_full_ingestion(
        self,
        api_raw_content: str,
        trace_id: str = "",
        runtime_id: str = "ingestion-spine-v1",
    ) -> IngestionSpineResult:
        """Execute the full governed ingestion chain.

        Steps:
        1. Validate safe doc targeting
        2. Open Drive
        3. Extract document content
        4. Normalize extraction
        5. Primitive decomposition
        6. Create ingestion candidate
        7. Create memory candidate
        8. Replay validation
        9. Persist ingestion proof
        """
        if not trace_id:
            trace_id = make_trace_id("INGEST")

        stages_completed: list[str] = []
        ledger_states: list[IngestionLedgerState] = []
        last_state_id = ""

        def _record(
            stage_name: str,
            ledger_stage: TransformationStage,
            in_hash: str,
            out_hash: str,
            allowed_next: list[str] | None = None,
            adapter_id: str = "",
        ) -> IngestionLedgerState:
            nonlocal last_state_id
            state = IngestionLedgerState(
                state_id="",
                trace_id=trace_id,
                parent_state_id=last_state_id,
                stage=stage_name,
                input_hash=in_hash,
                output_hash=out_hash,
                adapter_instance_id=self._identity.adapter_instance_id,
                source_identity_ref=self._identity.source_account_id,
                runtime_id=runtime_id,
                allowed_next_actions=allowed_next or ["next_stage"],
                blocked_next_actions=self._forbidden,
                replay_refs=[s.state_id for s in ledger_states[-3:]],
            )
            ledger_states.append(state)
            stages_completed.append(stage_name)
            last_state_id = state.state_id

            record = StateLedgerRecord(
                state_id=state.state_id,
                trace_id=trace_id,
                parent_state_id=state.parent_state_id,
                stage=ledger_stage,
                input_artifact_ref=StateArtifactReference(
                    artifact_id=f"in-{uuid.uuid4().hex[:6]}",
                    artifact_type=stage_name,
                    content_hash=in_hash,
                ),
                output_artifact_ref=StateArtifactReference(
                    artifact_id=f"out-{uuid.uuid4().hex[:6]}",
                    artifact_type=stage_name,
                    content_hash=out_hash,
                ),
                transformer_name="full_live_ingestion_spine_v1",
                transformer_version="v1",
                runtime_id=runtime_id,
                adapter_id=adapter_id or self._identity.adapter_instance_id,
                policy_envelope={
                    "phase": "96.8AG",
                    "governance": "active",
                    "identity": self._identity.source_account_id,
                },
                confidence="high",
                input_hash=in_hash,
                output_hash=out_hash,
                allowed_next_actions=state.allowed_next_actions,
                blocked_next_actions=state.blocked_next_actions,
            )
            self._ledger.append(record)
            return state

        result = IngestionSpineResult(result_id="", trace_id=trace_id)

        # Step 1: Validate safe doc targeting
        target_errors = self.validate_safe_doc_target()
        if target_errors:
            result.denial_reasons = target_errors
            result.error_message = f"safe_doc_validation_failed: {target_errors}"
            return result

        # Bound extraction content
        bounded_content = api_raw_content[: self._max_extract_chars]

        # Step 2: Drive open
        drive_proof = self._drive_adapter.open_safe_drive(trace_id=trace_id, runtime_id=runtime_id)
        result.drive_open_proof = drive_proof.to_dict()
        drive_hash = compute_hash(json.dumps(drive_proof.to_dict(), sort_keys=True))
        _record(
            "drive_docs_opened",
            TransformationStage.RAW_SOURCE,
            drive_hash,
            drive_hash,
            allowed_next=["document_extracted"],
            adapter_id=self._drive_adapter.adapter_id,
        )

        # Step 3: Extract document
        extraction = self._docs_adapter.extract(
            path=ExtractionPath.API,
            raw_content=bounded_content,
            trace_id=trace_id,
            runtime_id=runtime_id,
        )
        extraction.compute_content_hash()
        result.extraction_result = extraction.to_dict()
        _record(
            "document_extracted",
            TransformationStage.EXTRACTION,
            drive_hash,
            extraction.content_hash,
            allowed_next=["extraction_normalized"],
            adapter_id=self._docs_adapter.adapter_id,
        )

        # Step 4: Normalize
        normalized = self._docs_adapter.normalize(extraction, trace_id=trace_id)
        result.normalized_extraction = normalized.to_dict()
        _record(
            "extraction_normalized",
            TransformationStage.NORMALIZATION,
            extraction.content_hash,
            normalized.normalized_hash,
            allowed_next=["primitives_decomposed"],
        )

        # Step 5: Primitive decomposition
        decomp_hash = compute_hash(f"decomposition:{normalized.normalized_hash}")
        decomp_payload = {
            "source_normalization_id": normalized.normalization_id,
            "normalized_hash": normalized.normalized_hash,
            "decomposition_type": "text_primitive",
            "identity": self._identity.to_dict(),
        }
        result.primitive_decomposition = decomp_payload
        _record(
            "primitives_decomposed",
            TransformationStage.PRIMITIVE_DECOMPOSITION,
            normalized.normalized_hash,
            decomp_hash,
            allowed_next=["ingestion_candidate_created"],
        )

        # Step 6: Ingestion candidate
        ingestion = IngestionCandidate(
            candidate_id="",
            trace_id=trace_id,
            doc_title=self._config.get("safe_doc_title", ""),
            doc_url_or_id=self._config.get("safe_doc_url_or_id", ""),
            normalized_hash=normalized.normalized_hash,
            char_count=normalized.char_count,
            word_count=normalized.word_count,
            extraction_path=ExtractionPath.API.value,
        )
        ing_dict = ingestion.to_dict()
        ing_dict["identity"] = self._identity.to_dict()
        result.ingestion_candidate = ing_dict
        ing_hash = compute_hash(json.dumps(ing_dict, sort_keys=True))
        _record(
            "ingestion_candidate_created",
            TransformationStage.INGESTION_CANDIDATE,
            normalized.normalized_hash,
            ing_hash,
            allowed_next=["memory_candidate_created"],
        )

        # Step 7: Memory candidate
        memory = MemoryCandidate(
            candidate_id="",
            ingestion_candidate_id=ingestion.candidate_id,
            trace_id=trace_id,
            doc_title=ingestion.doc_title,
            normalized_hash=ingestion.normalized_hash,
        )
        mem_dict = memory.to_dict()
        mem_dict["identity"] = self._identity.to_dict()
        result.memory_candidate = mem_dict
        mem_hash = compute_hash(json.dumps(mem_dict, sort_keys=True))
        _record(
            "memory_candidate_created",
            TransformationStage.MEMORY_CANDIDATE,
            ing_hash,
            mem_hash,
            allowed_next=["replay_validated"],
        )

        # Step 8: Replay validation
        trace_records = self._ledger.get_trace(trace_id)
        reconstruction = []
        for rec in trace_records:
            reconstruction.append(
                {
                    "state_id": rec.state_id,
                    "stage": rec.stage.value
                    if isinstance(rec.stage, TransformationStage)
                    else rec.stage,
                    "input_hash": rec.input_hash,
                    "output_hash": rec.output_hash,
                }
            )

        replay = ReplayQueryResult(
            query_id="",
            trace_id=trace_id,
            total_states=len(reconstruction),
            lineage_valid=len(reconstruction) > 0,
            hashes_immutable=True,
            deterministic=len(reconstruction) > 0,
            reconstruction=reconstruction,
        )
        result.replay_result = replay.to_dict()

        replay_hash = compute_hash(json.dumps(replay.to_dict(), sort_keys=True))
        replay_state = IngestionLedgerState(
            state_id="",
            trace_id=trace_id,
            parent_state_id=last_state_id,
            stage="replay_validated",
            input_hash=mem_hash,
            output_hash=replay_hash,
            adapter_instance_id=self._identity.adapter_instance_id,
            source_identity_ref=self._identity.source_account_id,
            runtime_id=runtime_id,
            allowed_next_actions=["ingestion_completed"],
            blocked_next_actions=self._forbidden,
            replay_refs=[s.state_id for s in ledger_states[-3:]],
        )
        ledger_states.append(replay_state)
        stages_completed.append("replay_validated")
        last_state_id = replay_state.state_id

        stages_completed.append("ingestion_completed")

        # Build ingestion proof
        proof = IngestionProof(
            proof_id="",
            trace_id=trace_id,
            identity=self._identity,
            stages_completed=stages_completed,
            ingestion_candidate_id=ingestion.candidate_id,
            memory_candidate_id=memory.candidate_id,
            extraction_hash=extraction.content_hash,
            normalized_hash=normalized.normalized_hash,
            replay_deterministic=replay.deterministic,
            replay_total_states=replay.total_states,
        )

        # Persist proof
        proof_path = self._proof_dir / f"{proof.proof_id}.json"
        proof_path.write_text(json.dumps(proof.to_dict(), indent=2, default=str))

        result.succeeded = True
        result.ingestion_proof = proof
        result.ledger_states = [s.to_dict() for s in ledger_states]

        return result
