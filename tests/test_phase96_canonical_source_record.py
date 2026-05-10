"""Tests for Phase 96.0 canonical source record."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.canonical_source_record import (
    DocumentSourceRecord,
    ProvenanceRecord,
    TabSourceRecord,
    build_api_source_record,
    build_cli_source_record,
    build_cu_source_record,
)
from eos_ai.substrate.extraction_backend_contracts import (
    ExtractionBackendType,
    ExtractionCoverageStatus,
)


def _make_tabs(count: int = 3, words_per_tab: int = 100) -> list[TabSourceRecord]:
    """Helper to create test tab records."""
    tabs = []
    for i in range(count):
        content = " ".join(f"word{j}" for j in range(words_per_tab))
        tabs.append(
            TabSourceRecord(
                tab_id=f"tab_{i}",
                tab_title=f"Tab {i}",
                tab_path=f"Tab {i}",
                tab_order=i,
                is_empty=False,
                text_content=content,
                word_count=words_per_tab,
                character_count=len(content),
                extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
            )
        )
    return tabs


def test_canonical_record_accepts_all_backend_types():
    """CanonicalSourceRecord accepts backend_type without schema change."""
    for bt in ExtractionBackendType:
        record = DocumentSourceRecord(
            file_id="test",
            title="Test Doc",
            backend_type=bt,
            extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
        )
        assert record.backend_type == bt
        d = record.to_dict()
        assert d["backend_type"] == bt.value


def test_api_source_record_builder():
    """build_api_source_record produces correct record."""
    tabs = _make_tabs(3, 100)
    record = build_api_source_record("file_abc", "My Doc", tabs)
    assert record.backend_type == ExtractionBackendType.API
    assert record.total_tabs == 3
    assert record.total_words == 300
    assert record.extraction_coverage_status == ExtractionCoverageStatus.COMPLETE
    assert record.provenance is not None
    assert record.provenance.content_came_from_api is True


def test_cli_source_record_builder():
    """build_cli_source_record produces correct record."""
    tabs = _make_tabs(2, 50)
    record = build_cli_source_record("file_xyz", "CLI Doc", tabs, cli_tool="gws")
    assert record.backend_type == ExtractionBackendType.CLI
    assert record.extraction_method == "gws_docs_get_include_tabs"
    assert record.provenance.content_came_from_cli is True


def test_cu_source_record_builder():
    """build_cu_source_record produces correct record."""
    tabs = _make_tabs(1, 0)
    tabs[0].word_count = 0
    tabs[0].is_empty = True
    tabs[0].extraction_coverage_status = ExtractionCoverageStatus.BLOCKED
    record = build_cu_source_record(
        "file_cu",
        "CU Doc",
        tabs,
        any_inaccessible=True,
        inaccessible_reason="foreground_ownership_blocked",
    )
    assert record.backend_type == ExtractionBackendType.COMPUTER_USE
    assert record.extraction_coverage_status == ExtractionCoverageStatus.PARTIAL
    assert record.provenance.content_came_from_visible_ui is True
    assert record.provenance.any_content_inaccessible is True


def test_completeness_validation_passes_for_valid_record():
    """Completeness validation passes when all fields populated."""
    tabs = _make_tabs(2, 50)
    record = build_api_source_record("file_ok", "Valid Doc", tabs)
    is_complete, issues = record.validate_completeness()
    assert is_complete is True
    assert issues == []


def test_completeness_validation_fails_missing_tabs():
    """Completeness validation fails when no tabs extracted."""
    record = DocumentSourceRecord(
        file_id="file_empty",
        title="Empty",
        extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
        provenance=ProvenanceRecord(
            backend_type=ExtractionBackendType.API,
            extraction_method="test",
            source_observed_from="test",
        ),
    )
    is_complete, issues = record.validate_completeness()
    assert is_complete is False
    assert "no tabs extracted" in issues


def test_completeness_validation_catches_zero_word_complete_tab():
    """A tab claiming COMPLETE with 0 words is flagged."""
    tab = TabSourceRecord(
        tab_id="t1",
        tab_title="Bad Tab",
        tab_path="Bad Tab",
        is_empty=False,
        word_count=0,
        extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
    )
    record = DocumentSourceRecord(
        file_id="file_bad",
        title="Bad Doc",
        extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
        tabs=[tab],
        provenance=ProvenanceRecord(
            backend_type=ExtractionBackendType.API,
            extraction_method="test",
            source_observed_from="test",
        ),
    )
    is_complete, issues = record.validate_completeness()
    assert is_complete is False
    assert any("Bad Tab" in i and "0 words" in i for i in issues)


def test_empty_tab_with_zero_words_not_flagged():
    """An explicitly empty tab with 0 words is NOT flagged."""
    tab = TabSourceRecord(
        tab_id="t1",
        tab_title="Empty Tab",
        tab_path="Empty Tab",
        is_empty=True,
        word_count=0,
        extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
    )
    record = DocumentSourceRecord(
        file_id="file_ok",
        title="OK Doc",
        extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
        tabs=[tab],
        provenance=ProvenanceRecord(
            backend_type=ExtractionBackendType.API,
            extraction_method="test",
            source_observed_from="test",
        ),
    )
    is_complete, issues = record.validate_completeness()
    assert is_complete is True


def test_cli_wrapping_api_produces_cli_backend_record():
    """CLI wrapping API still produces CLI backend record."""
    tabs = _make_tabs(4, 200)
    record = build_cli_source_record("file_wrap", "Wrapped", tabs, cli_tool="gws")
    assert record.backend_type == ExtractionBackendType.CLI
    assert record.provenance.backend_type == ExtractionBackendType.CLI
    assert record.provenance.content_came_from_cli is True
    assert record.provenance.content_came_from_api is False


def test_record_serialization_roundtrip():
    """Record serializes and includes all expected keys."""
    tabs = _make_tabs(1, 10)
    record = build_api_source_record("file_ser", "Serialized", tabs)
    d = record.to_dict()
    assert d["file_id"] == "file_ser"
    assert d["total_tabs"] == 1
    assert d["total_words"] == 10
    assert d["provenance"]["backend_type"] == "api"
    assert len(d["tabs"]) == 1
