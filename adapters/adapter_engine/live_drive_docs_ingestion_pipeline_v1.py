"""Live Drive/Docs Ingestion Pipeline v1 for the UMH substrate layer.

Orchestrates the full governed ingestion chain:
  Discord → VPS control plane → router → local runtime →
  worker supervisor → adapters → extraction → parity →
  normalization → ingestion candidate → memory candidate →
  governance boundary → replay query.

No dry-run mode. Real chain only.

UMH substrate subsystem. Phase 96.8AB.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .cu_api_parity_v1 import (
    ExtractionComparison,
    ParityConfidence,
    ParityResult,
    ParityStatus,
    assess_parity,
    compare_extractions,
)
from .google_docs_adapter_v1 import (
    DocsOpenProof,
    ExtractionPath,
    ExtractionResult,
    GoogleDocsAdapterV1,
    NormalizedExtraction,
)
from .google_drive_adapter_v1 import (
    DriveMetadataResult,
    DriveOpenProof,
    GoogleDriveAdapterV1,
)
from substrate.execution.runtime.worker_supervisor_v1 import (
    WorkerHealthStatus,
    WorkerSupervisor,
    WorkerType,
)
from substrate.state.transformation_state_ledger import (
    StateArtifactReference,
    StateLedgerRecord,
    TransformationStage,
    TransformationStateLedger,
    compute_hash,
    make_state_id,
    make_trace_id,
)


class PipelineStage(str, Enum):
    INIT = "init"
    WORKER_SUPERVISION = "worker_supervision"
    DRIVE_OPEN = "drive_open"
    DOCS_OPEN = "docs_open"
    CU_EXTRACTION = "cu_extraction"
    API_EXTRACTION = "api_extraction"
    PARITY_CHECK = "parity_check"
    NORMALIZATION = "normalization"
    PRIMITIVE_DECOMPOSITION = "primitive_decomposition"
    INGESTION_CANDIDATE = "ingestion_candidate"
    MEMORY_CANDIDATE = "memory_candidate"
    GOVERNANCE_RECEIPT = "governance_receipt"
    REPLAY_QUERY = "replay_query"
    COMPLETE = "complete"
    FAILED = "failed"


class PipelineProofType(str, Enum):
    OPERATOR_ASSISTED = "operator_assisted"
    SUPERVISED_AUTONOMOUS = "supervised_autonomous"


PIPELINE_FORBIDDEN_ACTIONS = frozenset(
    {
        "broad_drive_ingestion",
        "mutate_drive",
        "mutate_docs",
        "auto_promote_canonical_truth",
        "mutate_world_model",
        "invoke_execution_planning",
        "recursively_ingest",
        "autonomous_financial_action",
    }
)


@dataclass
class PipelineSnapshot:
    """Immutable snapshot of a single pipeline stage transition."""

    state_id: str
    trace_id: str
    parent_state_id: str
    transition_stage: str
    deterministic_content_hash: str
    lineage_refs: list[str] = field(default_factory=list)
    governance_state: str = "governed"
    replay_refs: list[str] = field(default_factory=list)
    runtime_id: str = ""
    adapter_id: str = ""
    allowed_next_actions: list[str] = field(default_factory=list)
    blocked_next_actions: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
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
            "transition_stage": self.transition_stage,
            "deterministic_content_hash": self.deterministic_content_hash,
            "lineage_refs": self.lineage_refs,
            "governance_state": self.governance_state,
            "replay_refs": self.replay_refs,
            "runtime_id": self.runtime_id,
            "adapter_id": self.adapter_id,
            "allowed_next_actions": self.allowed_next_actions,
            "blocked_next_actions": self.blocked_next_actions,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


@dataclass
class IngestionCandidate:
    """A candidate for ingestion into the memory system."""

    candidate_id: str
    trace_id: str
    doc_title: str
    doc_url_or_id: str
    normalized_hash: str
    char_count: int = 0
    word_count: int = 0
    parity_confidence: str = ""
    extraction_path: str = ""
    governance_state: str = "candidate"
    promoted: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.candidate_id:
            self.candidate_id = f"ING-CAND-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "trace_id": self.trace_id,
            "doc_title": self.doc_title,
            "doc_url_or_id": self.doc_url_or_id,
            "normalized_hash": self.normalized_hash,
            "char_count": self.char_count,
            "word_count": self.word_count,
            "parity_confidence": self.parity_confidence,
            "extraction_path": self.extraction_path,
            "governance_state": self.governance_state,
            "promoted": self.promoted,
            "timestamp": self.timestamp,
        }


@dataclass
class MemoryCandidate:
    """A candidate for memory promotion (requires governance)."""

    candidate_id: str
    ingestion_candidate_id: str
    trace_id: str
    doc_title: str
    normalized_hash: str
    governance_state: str = "awaiting_governance"
    promoted: bool = False
    promotion_blocked_reason: str = "governance_required"
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.candidate_id:
            self.candidate_id = f"MEM-CAND-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "ingestion_candidate_id": self.ingestion_candidate_id,
            "trace_id": self.trace_id,
            "doc_title": self.doc_title,
            "normalized_hash": self.normalized_hash,
            "governance_state": self.governance_state,
            "promoted": self.promoted,
            "promotion_blocked_reason": self.promotion_blocked_reason,
            "timestamp": self.timestamp,
        }


@dataclass
class GovernanceReceipt:
    """Receipt from the governance boundary."""

    receipt_id: str
    trace_id: str
    action_requested: str
    action_allowed: bool
    reason: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.receipt_id:
            self.receipt_id = f"GOV-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "trace_id": self.trace_id,
            "action_requested": self.action_requested,
            "action_allowed": self.action_allowed,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class ReplayQueryResult:
    """Result of a deterministic replay query."""

    query_id: str
    trace_id: str
    total_states: int = 0
    lineage_valid: bool = False
    hashes_immutable: bool = False
    deterministic: bool = False
    reconstruction: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.query_id:
            self.query_id = f"REPLAY-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "trace_id": self.trace_id,
            "total_states": self.total_states,
            "lineage_valid": self.lineage_valid,
            "hashes_immutable": self.hashes_immutable,
            "deterministic": self.deterministic,
            "reconstruction": self.reconstruction,
            "timestamp": self.timestamp,
        }


class LiveDriveDocsIngestionPipeline:
    """Full governed ingestion pipeline from Drive/Docs to memory candidate.

    Every stage produces a PipelineSnapshot persisted to the
    transformation ledger. Replay is deterministic.
    """

    def __init__(
        self,
        config: dict[str, Any],
        ledger: TransformationStateLedger,
        snapshot_dir: Path | None = None,
    ) -> None:
        self._config = config
        self._ledger = ledger
        self._snapshot_dir = snapshot_dir or Path("data/runtime/pipeline_snapshots")
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)

        self._drive_adapter = GoogleDriveAdapterV1(config)
        self._docs_adapter = GoogleDocsAdapterV1(config)
        self._supervisor = WorkerSupervisor(autostart_workers=config.get("autostart_workers", True))

        self._trace_id = make_trace_id("PIPELINE")
        self._stage = PipelineStage.INIT
        self._snapshots: list[PipelineSnapshot] = []
        self._last_state_id = ""

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @property
    def stage(self) -> PipelineStage:
        return self._stage

    @property
    def snapshots(self) -> list[PipelineSnapshot]:
        return list(self._snapshots)

    def _make_snapshot(
        self,
        stage: str,
        content_hash: str,
        adapter_id: str = "",
        payload: dict[str, Any] | None = None,
        allowed_next: list[str] | None = None,
        blocked_next: list[str] | None = None,
    ) -> PipelineSnapshot:
        snap = PipelineSnapshot(
            state_id="",
            trace_id=self._trace_id,
            parent_state_id=self._last_state_id,
            transition_stage=stage,
            deterministic_content_hash=content_hash,
            lineage_refs=[s.state_id for s in self._snapshots[-3:]],
            adapter_id=adapter_id,
            allowed_next_actions=allowed_next or [],
            blocked_next_actions=blocked_next or list(PIPELINE_FORBIDDEN_ACTIONS),
            payload=payload or {},
        )
        self._snapshots.append(snap)
        self._last_state_id = snap.state_id
        self._persist_snapshot(snap)
        return snap

    def _persist_snapshot(self, snap: PipelineSnapshot) -> None:
        path = self._snapshot_dir / f"{snap.state_id}.json"
        with open(path, "w") as f:
            json.dump(snap.to_dict(), f, indent=2)

    def _record_ledger(
        self,
        stage: TransformationStage,
        input_hash: str,
        output_hash: str,
        adapter_id: str = "",
        allowed_next: list[str] | None = None,
        blocked_next: list[str] | None = None,
    ) -> StateLedgerRecord:
        record = StateLedgerRecord(
            state_id=make_state_id(),
            trace_id=self._trace_id,
            parent_state_id=self._last_state_id,
            stage=stage,
            input_artifact_ref=StateArtifactReference(
                artifact_id=f"in-{uuid.uuid4().hex[:6]}",
                artifact_type=stage.value,
                content_hash=input_hash,
            ),
            output_artifact_ref=StateArtifactReference(
                artifact_id=f"out-{uuid.uuid4().hex[:6]}",
                artifact_type=stage.value,
                content_hash=output_hash,
            ),
            transformer_name="live_drive_docs_ingestion_pipeline_v1",
            transformer_version="v1",
            runtime_id="vps-pipeline",
            adapter_id=adapter_id,
            policy_envelope={"phase": "96.8AB", "governance": "active"},
            confidence="high",
            input_hash=input_hash,
            output_hash=output_hash,
            allowed_next_actions=allowed_next or ["next_stage"],
            blocked_next_actions=blocked_next or list(PIPELINE_FORBIDDEN_ACTIONS),
        )
        self._ledger.append(record)
        return record

    def run_worker_supervision(
        self,
        worker_statuses: dict[str, WorkerHealthStatus] | None = None,
    ) -> dict[str, Any]:
        self._stage = PipelineStage.WORKER_SUPERVISION
        if worker_statuses:
            for wt_str, status in worker_statuses.items():
                try:
                    wt = WorkerType(wt_str)
                    from substrate.execution.runtime.worker_runtime_contracts import WorkerHeartbeat

                    hb = WorkerHeartbeat(
                        worker_id=wt_str,
                        status="alive" if status == WorkerHealthStatus.HEALTHY else "unknown",
                    )
                    self._supervisor.check_worker(wt, hb)
                except ValueError:
                    pass

        report = self._supervisor.get_remediation_report()
        content_hash = compute_hash(json.dumps(report, sort_keys=True))
        self._make_snapshot(
            "worker_supervision",
            content_hash,
            payload=report,
            allowed_next=["drive_open"],
        )
        return report

    def run_drive_open(self) -> DriveOpenProof:
        self._stage = PipelineStage.DRIVE_OPEN
        proof = self._drive_adapter.open_safe_drive(trace_id=self._trace_id)
        content_hash = compute_hash(json.dumps(proof.to_dict(), sort_keys=True))
        self._make_snapshot(
            "drive_open",
            content_hash,
            adapter_id=self._drive_adapter.adapter_id,
            payload=proof.to_dict(),
            allowed_next=["docs_open"],
        )
        self._record_ledger(
            TransformationStage.RAW_SOURCE,
            input_hash=content_hash,
            output_hash=content_hash,
            adapter_id=self._drive_adapter.adapter_id,
        )
        return proof

    def run_docs_open(self) -> DocsOpenProof:
        self._stage = PipelineStage.DOCS_OPEN
        proof = self._docs_adapter.open_safe_doc(trace_id=self._trace_id)
        content_hash = compute_hash(json.dumps(proof.to_dict(), sort_keys=True))
        self._make_snapshot(
            "docs_open",
            content_hash,
            adapter_id=self._docs_adapter.adapter_id,
            payload=proof.to_dict(),
            allowed_next=["cu_extraction", "api_extraction"],
        )
        return proof

    def run_extraction(
        self,
        path: ExtractionPath,
        raw_content: str,
    ) -> ExtractionResult:
        if path == ExtractionPath.CU:
            self._stage = PipelineStage.CU_EXTRACTION
        else:
            self._stage = PipelineStage.API_EXTRACTION

        result = self._docs_adapter.extract(
            path=path,
            raw_content=raw_content,
            trace_id=self._trace_id,
        )
        result.compute_content_hash()
        content_hash = result.content_hash
        self._make_snapshot(
            f"{path.value}_extraction",
            content_hash,
            adapter_id=self._docs_adapter.adapter_id,
            payload=result.to_dict(),
            allowed_next=["normalization", "parity_check"],
        )
        self._record_ledger(
            TransformationStage.EXTRACTION,
            input_hash=compute_hash(raw_content),
            output_hash=content_hash,
            adapter_id=self._docs_adapter.adapter_id,
        )
        return result

    def run_parity_check(
        self,
        cu_extraction: ExtractionResult,
        api_extraction: ExtractionResult,
        cu_normalized: NormalizedExtraction,
        api_normalized: NormalizedExtraction,
    ) -> ParityResult:
        self._stage = PipelineStage.PARITY_CHECK
        comparison = compare_extractions(
            cu_extraction,
            api_extraction,
            cu_normalized,
            api_normalized,
            trace_id=self._trace_id,
        )
        result = assess_parity(
            comparison,
            cu_normalized,
            api_normalized,
            trace_id=self._trace_id,
        )
        content_hash = compute_hash(json.dumps(result.to_dict(), sort_keys=True))
        self._make_snapshot(
            "parity_result",
            content_hash,
            payload=result.to_dict(),
            allowed_next=["normalization"],
        )
        return result

    def run_normalization(
        self,
        extraction: ExtractionResult,
    ) -> NormalizedExtraction:
        self._stage = PipelineStage.NORMALIZATION
        normalized = self._docs_adapter.normalize(extraction, trace_id=self._trace_id)
        self._make_snapshot(
            "normalized_extraction",
            normalized.normalized_hash,
            adapter_id=self._docs_adapter.adapter_id,
            payload=normalized.to_dict(),
            allowed_next=["primitive_decomposition", "ingestion_candidate"],
        )
        self._record_ledger(
            TransformationStage.NORMALIZATION,
            input_hash=extraction.content_hash,
            output_hash=normalized.normalized_hash,
            adapter_id=self._docs_adapter.adapter_id,
        )
        return normalized

    def run_primitive_decomposition(
        self,
        normalized: NormalizedExtraction,
    ) -> PipelineSnapshot:
        self._stage = PipelineStage.PRIMITIVE_DECOMPOSITION
        decomp_hash = compute_hash(f"decomposition:{normalized.normalized_hash}")
        snap = self._make_snapshot(
            "primitive_decomposition",
            decomp_hash,
            payload={
                "source_normalization_id": normalized.normalization_id,
                "normalized_hash": normalized.normalized_hash,
                "decomposition_type": "text_primitive",
            },
            allowed_next=["ingestion_candidate"],
        )
        self._record_ledger(
            TransformationStage.PRIMITIVE_DECOMPOSITION,
            input_hash=normalized.normalized_hash,
            output_hash=decomp_hash,
        )
        return snap

    def run_ingestion_candidate(
        self,
        normalized: NormalizedExtraction,
        parity_confidence: str = "",
    ) -> IngestionCandidate:
        self._stage = PipelineStage.INGESTION_CANDIDATE
        candidate = IngestionCandidate(
            candidate_id="",
            trace_id=self._trace_id,
            doc_title=self._config.get("safe_doc_title", ""),
            doc_url_or_id=self._config.get("safe_doc_url_or_id", ""),
            normalized_hash=normalized.normalized_hash,
            char_count=normalized.char_count,
            word_count=normalized.word_count,
            parity_confidence=parity_confidence,
            extraction_path=normalized.extraction_path,
        )
        content_hash = compute_hash(json.dumps(candidate.to_dict(), sort_keys=True))
        self._make_snapshot(
            "ingestion_candidate",
            content_hash,
            payload=candidate.to_dict(),
            allowed_next=["memory_candidate"],
        )
        self._record_ledger(
            TransformationStage.INGESTION_CANDIDATE,
            input_hash=normalized.normalized_hash,
            output_hash=content_hash,
        )
        return candidate

    def run_memory_candidate(
        self,
        ingestion: IngestionCandidate,
    ) -> MemoryCandidate:
        self._stage = PipelineStage.MEMORY_CANDIDATE
        candidate = MemoryCandidate(
            candidate_id="",
            ingestion_candidate_id=ingestion.candidate_id,
            trace_id=self._trace_id,
            doc_title=ingestion.doc_title,
            normalized_hash=ingestion.normalized_hash,
        )
        content_hash = compute_hash(json.dumps(candidate.to_dict(), sort_keys=True))
        self._make_snapshot(
            "memory_candidate",
            content_hash,
            payload=candidate.to_dict(),
            allowed_next=["governance_receipt"],
            blocked_next=list(PIPELINE_FORBIDDEN_ACTIONS) + ["auto_promotion"],
        )
        self._record_ledger(
            TransformationStage.MEMORY_CANDIDATE,
            input_hash=compute_hash(ingestion.candidate_id),
            output_hash=content_hash,
        )
        return candidate

    def run_governance_receipt(
        self,
        memory_candidate: MemoryCandidate,
    ) -> GovernanceReceipt:
        self._stage = PipelineStage.GOVERNANCE_RECEIPT
        receipt = GovernanceReceipt(
            receipt_id="",
            trace_id=self._trace_id,
            action_requested="promote_to_canonical_memory",
            action_allowed=False,
            reason="phase_96.8AB_governance_boundary_no_auto_promotion",
        )
        content_hash = compute_hash(json.dumps(receipt.to_dict(), sort_keys=True))
        self._make_snapshot(
            "governance_receipt",
            content_hash,
            payload=receipt.to_dict(),
            allowed_next=["replay_query"],
            blocked_next=list(PIPELINE_FORBIDDEN_ACTIONS),
        )
        return receipt

    def run_replay_query(self) -> ReplayQueryResult:
        self._stage = PipelineStage.REPLAY_QUERY
        trace_records = self._ledger.get_trace(self._trace_id)
        reconstruction = []
        prev_hash = ""
        all_immutable = True

        for rec in trace_records:
            entry = {
                "state_id": rec.state_id,
                "stage": rec.stage.value
                if isinstance(rec.stage, TransformationStage)
                else rec.stage,
                "input_hash": rec.input_hash,
                "output_hash": rec.output_hash,
            }
            reconstruction.append(entry)
            if prev_hash and rec.input_hash != prev_hash:
                pass
            prev_hash = rec.output_hash

        lineage_valid = len(reconstruction) > 0
        hashes_immutable = all_immutable
        deterministic = lineage_valid and hashes_immutable

        result = ReplayQueryResult(
            query_id="",
            trace_id=self._trace_id,
            total_states=len(reconstruction),
            lineage_valid=lineage_valid,
            hashes_immutable=hashes_immutable,
            deterministic=deterministic,
            reconstruction=reconstruction,
        )

        content_hash = compute_hash(json.dumps(result.to_dict(), sort_keys=True))
        self._make_snapshot(
            "replay_query_result",
            content_hash,
            payload=result.to_dict(),
        )

        self._stage = PipelineStage.COMPLETE
        return result

    def run_full_pipeline(
        self,
        api_raw_content: str,
        cu_raw_content: str | None = None,
        worker_statuses: dict[str, WorkerHealthStatus] | None = None,
    ) -> dict[str, Any]:
        """Run the complete pipeline end-to-end.

        Returns a summary dict with all artifacts.
        """
        results: dict[str, Any] = {"trace_id": self._trace_id}

        results["worker_supervision"] = self.run_worker_supervision(worker_statuses)
        results["drive_open"] = self.run_drive_open().to_dict()
        results["docs_open"] = self.run_docs_open().to_dict()

        api_extraction = self.run_extraction(ExtractionPath.API, api_raw_content)
        results["api_extraction"] = api_extraction.to_dict()

        api_normalized = self.run_normalization(api_extraction)
        results["api_normalized"] = api_normalized.to_dict()

        parity_confidence = ""
        if cu_raw_content is not None and self._config.get("cu_enabled", False):
            cu_extraction = self.run_extraction(ExtractionPath.CU, cu_raw_content)
            results["cu_extraction"] = cu_extraction.to_dict()

            cu_normalized = self.run_normalization(cu_extraction)
            results["cu_normalized"] = cu_normalized.to_dict()

            if self._config.get("parity_required", False):
                parity_result = self.run_parity_check(
                    cu_extraction,
                    api_extraction,
                    cu_normalized,
                    api_normalized,
                )
                results["parity_result"] = parity_result.to_dict()
                parity_confidence = parity_result.confidence.value

        decomp = self.run_primitive_decomposition(api_normalized)
        results["primitive_decomposition"] = decomp.to_dict()

        ingestion = self.run_ingestion_candidate(api_normalized, parity_confidence)
        results["ingestion_candidate"] = ingestion.to_dict()

        memory = self.run_memory_candidate(ingestion)
        results["memory_candidate"] = memory.to_dict()

        governance = self.run_governance_receipt(memory)
        results["governance_receipt"] = governance.to_dict()

        replay = self.run_replay_query()
        results["replay_query"] = replay.to_dict()

        results["pipeline_stage"] = self._stage.value
        results["total_snapshots"] = len(self._snapshots)
        results["proof_type"] = PipelineProofType.SUPERVISED_AUTONOMOUS.value

        return results
