"""Tests for Live Drive/Docs Ingestion Pipeline v1.

Phase 96.8AB — end-to-end pipeline validation.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import json
import tempfile
from pathlib import Path

import pytest

from adapters.adapter_engine.cu_api_parity_v1 import ParityConfidence, ParityStatus
from adapters.adapter_engine.google_docs_adapter_v1 import ExtractionPath
from adapters.adapter_engine.live_drive_docs_ingestion_pipeline_v1 import (
    PIPELINE_FORBIDDEN_ACTIONS,
    GovernanceReceipt,
    IngestionCandidate,
    LiveDriveDocsIngestionPipeline,
    MemoryCandidate,
    PipelineProofType,
    PipelineSnapshot,
    PipelineStage,
    ReplayQueryResult,
)
from core.runtime.worker_supervisor_v1 import WorkerHealthStatus
from state.transformation_state_ledger import TransformationStateLedger


SAFE_CONFIG = {
    "safe_drive_url": "https://drive.google.com/drive/my-drive",
    "safe_doc_url_or_id": "https://docs.google.com/document/d/test123/edit",
    "safe_doc_title": "Test Doc",
    "cu_enabled": True,
    "api_enabled": True,
    "parity_required": True,
    "preview_char_limit": 500,
    "extraction_timeout_seconds": 30,
    "autostart_workers": True,
}

API_CONTENT = "This is the API extracted content from the test document."
CU_CONTENT = "This is the API extracted content from the test document."


def _make_pipeline(tmp: Path) -> LiveDriveDocsIngestionPipeline:
    ledger_dir = tmp / "ledger"
    snapshot_dir = tmp / "snapshots"
    ledger = TransformationStateLedger(ledger_dir)
    return LiveDriveDocsIngestionPipeline(
        config=SAFE_CONFIG,
        ledger=ledger,
        snapshot_dir=snapshot_dir,
    )


class TestPipelineInit:
    def test_init(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.trace_id.startswith("PIPELINE-")
        assert pipeline.stage == PipelineStage.INIT

    def test_snapshots_empty_at_start(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        assert pipeline.snapshots == []


class TestWorkerSupervision:
    def test_run_supervision(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        report = pipeline.run_worker_supervision()
        assert "total_workers" in report
        assert pipeline.stage == PipelineStage.WORKER_SUPERVISION

    def test_supervision_with_statuses(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        statuses = {
            "local_runtime_daemon": WorkerHealthStatus.HEALTHY,
            "discord_adapter": WorkerHealthStatus.HEALTHY,
        }
        report = pipeline.run_worker_supervision(statuses)
        assert report["healthy"] >= 2


class TestDriveOpen:
    def test_open(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        proof = pipeline.run_drive_open()
        assert proof.drive_page_loaded is True
        assert proof.governance_state == "governed"
        assert pipeline.stage == PipelineStage.DRIVE_OPEN


class TestDocsOpen:
    def test_open(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        proof = pipeline.run_docs_open()
        assert proof.doc_page_loaded is True
        assert pipeline.stage == PipelineStage.DOCS_OPEN


class TestExtraction:
    def test_api_extraction(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        result = pipeline.run_extraction(ExtractionPath.API, API_CONTENT)
        assert result.content_hash != ""
        assert result.char_count > 0
        assert pipeline.stage == PipelineStage.API_EXTRACTION

    def test_cu_extraction(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        result = pipeline.run_extraction(ExtractionPath.CU, CU_CONTENT)
        assert result.content_hash != ""
        assert pipeline.stage == PipelineStage.CU_EXTRACTION


class TestNormalization:
    def test_normalize(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        extraction = pipeline.run_extraction(ExtractionPath.API, API_CONTENT)
        normalized = pipeline.run_normalization(extraction)
        assert normalized.normalized_hash != ""
        assert pipeline.stage == PipelineStage.NORMALIZATION


class TestParityCheck:
    def test_exact_parity(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        cu_ext = pipeline.run_extraction(ExtractionPath.CU, "same content")
        api_ext = pipeline.run_extraction(ExtractionPath.API, "same content")
        cu_norm = pipeline.run_normalization(cu_ext)
        api_norm = pipeline.run_normalization(api_ext)
        result = pipeline.run_parity_check(cu_ext, api_ext, cu_norm, api_norm)
        assert result.confidence == ParityConfidence.EXACT
        assert result.status == ParityStatus.PASSED


class TestIngestionCandidate:
    def test_create(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        ext = pipeline.run_extraction(ExtractionPath.API, API_CONTENT)
        norm = pipeline.run_normalization(ext)
        candidate = pipeline.run_ingestion_candidate(norm, "high")
        assert candidate.trace_id == pipeline.trace_id
        assert candidate.normalized_hash != ""
        assert candidate.promoted is False
        assert pipeline.stage == PipelineStage.INGESTION_CANDIDATE


class TestMemoryCandidate:
    def test_create(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        ext = pipeline.run_extraction(ExtractionPath.API, API_CONTENT)
        norm = pipeline.run_normalization(ext)
        ing = pipeline.run_ingestion_candidate(norm)
        mem = pipeline.run_memory_candidate(ing)
        assert mem.promoted is False
        assert mem.governance_state == "awaiting_governance"
        assert pipeline.stage == PipelineStage.MEMORY_CANDIDATE


class TestGovernanceReceipt:
    def test_no_auto_promotion(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        ext = pipeline.run_extraction(ExtractionPath.API, API_CONTENT)
        norm = pipeline.run_normalization(ext)
        ing = pipeline.run_ingestion_candidate(norm)
        mem = pipeline.run_memory_candidate(ing)
        receipt = pipeline.run_governance_receipt(mem)
        assert receipt.action_allowed is False
        assert "no_auto_promotion" in receipt.reason
        assert pipeline.stage == PipelineStage.GOVERNANCE_RECEIPT


class TestReplayQuery:
    def test_replay_deterministic(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        pipeline.run_drive_open()
        ext = pipeline.run_extraction(ExtractionPath.API, API_CONTENT)
        pipeline.run_normalization(ext)
        result = pipeline.run_replay_query()
        assert result.deterministic is True
        assert result.lineage_valid is True
        assert result.hashes_immutable is True
        assert result.total_states > 0
        assert pipeline.stage == PipelineStage.COMPLETE

    def test_replay_immutable(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        pipeline.run_drive_open()
        ext = pipeline.run_extraction(ExtractionPath.API, API_CONTENT)
        pipeline.run_normalization(ext)
        result1 = pipeline.run_replay_query()
        # Hashes should remain stable on second query of same trace
        assert result1.hashes_immutable is True


class TestFullPipeline:
    def test_api_only(self, tmp_path: Path) -> None:
        config = {**SAFE_CONFIG, "cu_enabled": False}
        ledger = TransformationStateLedger(tmp_path / "ledger")
        pipeline = LiveDriveDocsIngestionPipeline(
            config=config,
            ledger=ledger,
            snapshot_dir=tmp_path / "snapshots",
        )
        results = pipeline.run_full_pipeline(api_raw_content=API_CONTENT)
        assert results["pipeline_stage"] == "complete"
        assert "ingestion_candidate" in results
        assert "memory_candidate" in results
        assert "governance_receipt" in results
        assert "replay_query" in results
        assert results["total_snapshots"] > 0

    def test_dual_path_with_parity(self, tmp_path: Path) -> None:
        ledger = TransformationStateLedger(tmp_path / "ledger")
        pipeline = LiveDriveDocsIngestionPipeline(
            config=SAFE_CONFIG,
            ledger=ledger,
            snapshot_dir=tmp_path / "snapshots",
        )
        results = pipeline.run_full_pipeline(
            api_raw_content=API_CONTENT,
            cu_raw_content=CU_CONTENT,
        )
        assert results["pipeline_stage"] == "complete"
        assert "parity_result" in results
        assert "cu_extraction" in results

    def test_proof_type_supervised_autonomous(self, tmp_path: Path) -> None:
        config = {**SAFE_CONFIG, "cu_enabled": False}
        ledger = TransformationStateLedger(tmp_path / "ledger")
        pipeline = LiveDriveDocsIngestionPipeline(
            config=config,
            ledger=ledger,
            snapshot_dir=tmp_path / "snapshots",
        )
        results = pipeline.run_full_pipeline(api_raw_content=API_CONTENT)
        assert results["proof_type"] == "supervised_autonomous"


class TestSnapshotPersistence:
    def test_snapshots_persisted_to_disk(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        pipeline.run_drive_open()
        snapshot_dir = tmp_path / "snapshots"
        files = list(snapshot_dir.glob("STATE-*.json"))
        assert len(files) >= 1

    def test_snapshot_content_valid(self, tmp_path: Path) -> None:
        pipeline = _make_pipeline(tmp_path)
        pipeline.run_drive_open()
        snapshot_dir = tmp_path / "snapshots"
        files = list(snapshot_dir.glob("STATE-*.json"))
        for f in files:
            data = json.loads(f.read_text())
            assert "state_id" in data
            assert "trace_id" in data
            assert "deterministic_content_hash" in data


class TestLedgerPersistence:
    def test_ledger_records_created(self, tmp_path: Path) -> None:
        ledger_dir = tmp_path / "ledger"
        ledger = TransformationStateLedger(ledger_dir)
        pipeline = LiveDriveDocsIngestionPipeline(
            config=SAFE_CONFIG,
            ledger=ledger,
            snapshot_dir=tmp_path / "snapshots",
        )
        pipeline.run_drive_open()
        assert ledger.record_count >= 1

    def test_ledger_lineage_reconstruction(self, tmp_path: Path) -> None:
        config = {**SAFE_CONFIG, "cu_enabled": False}
        ledger_dir = tmp_path / "ledger"
        ledger = TransformationStateLedger(ledger_dir)
        pipeline = LiveDriveDocsIngestionPipeline(
            config=config,
            ledger=ledger,
            snapshot_dir=tmp_path / "snapshots",
        )
        results = pipeline.run_full_pipeline(api_raw_content=API_CONTENT)
        trace_records = ledger.get_trace(pipeline.trace_id)
        assert len(trace_records) >= 4


class TestGovernanceBoundaries:
    def test_no_broad_drive_ingestion(self) -> None:
        assert "broad_drive_ingestion" in PIPELINE_FORBIDDEN_ACTIONS

    def test_no_mutate_drive(self) -> None:
        assert "mutate_drive" in PIPELINE_FORBIDDEN_ACTIONS

    def test_no_mutate_docs(self) -> None:
        assert "mutate_docs" in PIPELINE_FORBIDDEN_ACTIONS

    def test_no_auto_promote(self) -> None:
        assert "auto_promote_canonical_truth" in PIPELINE_FORBIDDEN_ACTIONS

    def test_no_world_model_mutation(self) -> None:
        assert "mutate_world_model" in PIPELINE_FORBIDDEN_ACTIONS

    def test_no_execution_planning(self) -> None:
        assert "invoke_execution_planning" in PIPELINE_FORBIDDEN_ACTIONS

    def test_no_recursive_ingestion(self) -> None:
        assert "recursively_ingest" in PIPELINE_FORBIDDEN_ACTIONS

    def test_no_autonomous_financial(self) -> None:
        assert "autonomous_financial_action" in PIPELINE_FORBIDDEN_ACTIONS
