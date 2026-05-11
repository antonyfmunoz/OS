"""Tests for W0-001 backend parity status after tab-aware re-extraction."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.canonical_source_record import (
    DocumentSourceRecord,
    ProvenanceRecord,
    TabSourceRecord,
    build_api_source_record,
    build_cu_source_record,
)
from runtime.substrate.extraction_backend_contracts import (
    ExtractionBackendType,
    ExtractionCapability,
    ExtractionCoverageStatus,
)
from runtime.substrate.extraction_parity_comparator import (
    compare_document_records,
    compare_tab_coverage,
    compare_text_coverage,
    identify_missing_tabs,
)
from runtime.substrate.google_docs_backend_parity_matrix import (
    build_google_docs_backend_matrix,
    mark_computer_use_capabilities,
    evaluate_backend_against_contract,
    build_google_docs_contract,
)
from runtime.substrate.cu_document_reader_hardening_plan import (
    build_hardening_plan,
    HardeningPhase,
    PhaseStatus,
)


def _make_tab(tab_id: str, title: str, words: int) -> TabSourceRecord:
    content = " ".join(f"word{i}" for i in range(words))
    return TabSourceRecord(
        tab_id=tab_id,
        tab_title=title,
        tab_path=title,
        word_count=words,
        character_count=len(content),
        text_content=content,
        extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
    )


def test_parity_comparator_detects_missing_tabs():
    """Parity comparator detects tabs present in API but missing from CU."""
    api_tabs = [_make_tab("t1", "A", 100), _make_tab("t2", "B", 200), _make_tab("t3", "C", 300)]
    cu_tabs = [_make_tab("t1", "A", 100)]

    api_record = DocumentSourceRecord(
        file_id="doc1",
        title="Test",
        backend_type=ExtractionBackendType.API,
        extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
        tabs=api_tabs,
        provenance=ProvenanceRecord(
            backend_type=ExtractionBackendType.API,
            extraction_method="test",
            source_observed_from="test",
        ),
    )
    cu_record = DocumentSourceRecord(
        file_id="doc1",
        title="Test",
        backend_type=ExtractionBackendType.COMPUTER_USE,
        extraction_coverage_status=ExtractionCoverageStatus.PARTIAL,
        tabs=cu_tabs,
        provenance=ProvenanceRecord(
            backend_type=ExtractionBackendType.COMPUTER_USE,
            extraction_method="test",
            source_observed_from="test",
        ),
    )

    missing = identify_missing_tabs(api_record, cu_record)
    assert "B" in missing
    assert "C" in missing


def test_parity_comparator_detects_missing_text():
    """Parity comparator detects missing body text in CU extraction."""
    api_tabs = [_make_tab("t1", "Main", 500)]
    cu_tabs = [
        TabSourceRecord(
            tab_id="t1",
            tab_title="Main",
            tab_path="Main",
            word_count=0,
            character_count=0,
            text_content="",
            extraction_coverage_status=ExtractionCoverageStatus.BLOCKED,
        )
    ]

    api_record = DocumentSourceRecord(
        file_id="doc1",
        title="Test",
        backend_type=ExtractionBackendType.API,
        extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
        tabs=api_tabs,
        provenance=ProvenanceRecord(
            backend_type=ExtractionBackendType.API,
            extraction_method="test",
            source_observed_from="test",
        ),
    )
    cu_record = DocumentSourceRecord(
        file_id="doc1",
        title="Test",
        backend_type=ExtractionBackendType.COMPUTER_USE,
        extraction_coverage_status=ExtractionCoverageStatus.PARTIAL,
        tabs=cu_tabs,
        provenance=ProvenanceRecord(
            backend_type=ExtractionBackendType.COMPUTER_USE,
            extraction_method="test",
            source_observed_from="test",
        ),
    )

    text_result = compare_text_coverage(api_record, cu_record)
    assert text_result.parity_pass is False
    assert text_result.word_recall == 0.0


def test_cu_backend_remains_partial():
    """CU backend correctly reports PARTIAL until content extraction works."""
    cu_caps = mark_computer_use_capabilities()
    cu_contract = build_google_docs_contract("test", ExtractionBackendType.COMPUTER_USE)
    report = evaluate_backend_against_contract(cu_contract, cu_caps)
    assert report.overall_status != ExtractionCoverageStatus.COMPLETE
    assert ExtractionCapability.DOCUMENT_BODY in report.blocked_capabilities


def test_api_backend_complete_after_reextraction():
    """API backend is COMPLETE when tab-aware extraction is used."""
    matrix = build_google_docs_backend_matrix(api_tab_aware=True)
    assert matrix.api_entry.overall_status == "complete"


def test_hardening_plan_starts_at_foreground():
    """Hardening plan starts at Phase A (foreground ownership)."""
    plan = build_hardening_plan()
    assert plan.current_phase == HardeningPhase.FOREGROUND_OWNERSHIP
    assert plan.overall_status == PhaseStatus.NOT_STARTED
    next_phase = plan.get_next_actionable_phase()
    assert next_phase is not None
    assert next_phase.phase == HardeningPhase.FOREGROUND_OWNERSHIP


def test_hardening_plan_phase_b_requires_phase_a():
    """Phase B (clipboard) requires Phase A (foreground) as prerequisite."""
    plan = build_hardening_plan()
    phase_b = next(p for p in plan.phases if p.phase == HardeningPhase.CLIPBOARD_EXTRACTION)
    assert HardeningPhase.FOREGROUND_OWNERSHIP in phase_b.prerequisites


def test_parity_report_grades_cu_fail():
    """CU with no content extraction produces FAIL parity grade."""
    api_tabs = [_make_tab("t1", "Main", 1000)]
    cu_tabs = []

    api_record = DocumentSourceRecord(
        file_id="doc1",
        title="Test",
        backend_type=ExtractionBackendType.API,
        extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
        tabs=api_tabs,
        provenance=ProvenanceRecord(
            backend_type=ExtractionBackendType.API,
            extraction_method="test",
            source_observed_from="test",
        ),
    )
    cu_record = DocumentSourceRecord(
        file_id="doc1",
        title="Test",
        backend_type=ExtractionBackendType.COMPUTER_USE,
        extraction_coverage_status=ExtractionCoverageStatus.PARTIAL,
        tabs=cu_tabs,
        provenance=ProvenanceRecord(
            backend_type=ExtractionBackendType.COMPUTER_USE,
            extraction_method="test",
            source_observed_from="test",
        ),
    )

    report = compare_document_records(api_record, cu_record)
    assert report.parity_grade == "FAIL"
    assert report.overall_parity_pass is False
