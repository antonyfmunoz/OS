"""Tests for Phase 96.0 extraction parity comparator."""

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.canonical_source_record import (
    DocumentSourceRecord,
    ProvenanceRecord,
    TabSourceRecord,
    build_api_source_record,
    build_cu_source_record,
)
from eos_ai.substrate.extraction_backend_contracts import (
    ExtractionBackendType,
    ExtractionCoverageStatus,
)
from eos_ai.substrate.extraction_parity_comparator import (
    compare_document_records,
    compare_tab_coverage,
    compare_text_coverage,
    compute_precision,
    compute_tab_recall,
    compute_word_recall,
    identify_missing_tabs,
    identify_missing_text_sections,
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


def _make_record(
    backend: ExtractionBackendType,
    tabs: list[TabSourceRecord],
    file_id: str = "test_file",
) -> DocumentSourceRecord:
    return DocumentSourceRecord(
        file_id=file_id,
        title="Test Doc",
        backend_type=backend,
        extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
        tabs=tabs,
        provenance=ProvenanceRecord(
            backend_type=backend,
            extraction_method="test",
            source_observed_from="test",
        ),
    )


def test_identical_records_pass():
    """Identical records produce full parity pass."""
    tabs = [_make_tab("t1", "Tab 1", 100), _make_tab("t2", "Tab 2", 200)]
    ref = _make_record(ExtractionBackendType.API, tabs)
    cand = _make_record(ExtractionBackendType.CLI, tabs)
    report = compare_document_records(ref, cand)
    assert report.overall_parity_pass is True
    assert report.parity_grade == "PASS"


def test_missing_tab_detected():
    """Missing tab in candidate is detected."""
    ref_tabs = [_make_tab("t1", "Tab 1", 100), _make_tab("t2", "Tab 2", 200)]
    cand_tabs = [_make_tab("t1", "Tab 1", 100)]
    ref = _make_record(ExtractionBackendType.API, ref_tabs)
    cand = _make_record(ExtractionBackendType.COMPUTER_USE, cand_tabs)

    tab_result = compare_tab_coverage(ref, cand)
    assert tab_result.missing_tabs == ["Tab 2"]
    assert tab_result.parity_pass is False


def test_missing_child_tab_detected():
    """Child tab missing from candidate is detected via tab ID."""
    ref_tabs = [
        _make_tab("t1", "Parent", 100),
        TabSourceRecord(
            tab_id="t1_child",
            tab_title="Child Tab",
            tab_path="Parent/Child Tab",
            parent_tab_id="t1",
            word_count=50,
            character_count=200,
            text_content="child content " * 10,
            extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
        ),
    ]
    cand_tabs = [_make_tab("t1", "Parent", 100)]
    ref = _make_record(ExtractionBackendType.API, ref_tabs)
    cand = _make_record(ExtractionBackendType.COMPUTER_USE, cand_tabs)

    missing = identify_missing_tabs(ref, cand)
    assert "Child Tab" in missing


def test_missing_body_content_detected():
    """Tab with 0 words in candidate but content in reference is flagged."""
    ref_tabs = [_make_tab("t1", "Main", 500)]
    cand_tabs = [
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
    ref = _make_record(ExtractionBackendType.API, ref_tabs)
    cand = _make_record(ExtractionBackendType.COMPUTER_USE, cand_tabs)

    missing = identify_missing_text_sections(ref, cand)
    assert any("Main" in m for m in missing)


def test_word_recall_computed():
    """Word recall is computed correctly."""
    ref_text = "the quick brown fox jumps over the lazy dog"
    cand_text = "the quick brown fox"
    recall = compute_word_recall(ref_text, cand_text)
    assert recall > 0.0
    assert recall < 1.0


def test_word_recall_identical():
    """Identical text gives 1.0 recall."""
    text = "hello world foo bar baz"
    recall = compute_word_recall(text, text)
    assert recall == 1.0


def test_tab_recall_computed():
    """Tab recall is computed correctly."""
    ref = [_make_tab("t1", "A", 10), _make_tab("t2", "B", 10), _make_tab("t3", "C", 10)]
    cand = [_make_tab("t1", "A", 10), _make_tab("t2", "B", 10)]
    recall = compute_tab_recall(ref, cand)
    assert abs(recall - 2 / 3) < 0.01


def test_precision_computed():
    """Precision detects extra tabs in candidate."""
    ref = [_make_tab("t1", "A", 10)]
    cand = [_make_tab("t1", "A", 10), _make_tab("t2", "Extra", 5)]
    precision = compute_precision(ref, cand)
    assert abs(precision - 0.5) < 0.01


def test_cu_below_threshold_fails():
    """CU extraction below threshold fails parity."""
    ref_tabs = [_make_tab("t1", "Main", 1000)]
    cand_tabs = [
        TabSourceRecord(
            tab_id="t1",
            tab_title="Main",
            tab_path="Main",
            word_count=100,
            character_count=400,
            text_content=" ".join(f"word{i}" for i in range(100)),
            extraction_coverage_status=ExtractionCoverageStatus.PARTIAL,
        )
    ]
    ref = _make_record(ExtractionBackendType.API, ref_tabs)
    cand = _make_record(ExtractionBackendType.COMPUTER_USE, cand_tabs)

    text_result = compare_text_coverage(ref, cand, threshold=0.95)
    assert text_result.parity_pass is False
    assert text_result.word_recall < 0.95


def test_text_coverage_comparison():
    """Text coverage comparison produces expected structure."""
    tabs = [_make_tab("t1", "Tab", 50)]
    ref = _make_record(ExtractionBackendType.API, tabs)
    cand = _make_record(ExtractionBackendType.CLI, tabs)
    result = compare_text_coverage(ref, cand)
    assert result.reference_word_count == 50
    assert result.candidate_word_count == 50
    assert result.parity_pass is True


def test_parity_report_grade_fail():
    """Report grades FAIL when both tab and text parity fail."""
    ref_tabs = [_make_tab("t1", "A", 100), _make_tab("t2", "B", 200)]
    cand_tabs = []
    ref = _make_record(ExtractionBackendType.API, ref_tabs)
    cand = _make_record(ExtractionBackendType.COMPUTER_USE, cand_tabs)

    report = compare_document_records(ref, cand)
    assert report.parity_grade == "FAIL"
    assert report.overall_parity_pass is False
