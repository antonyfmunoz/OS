"""Tests for CU/API Parity Validator v1.

Phase 96.8AB — parity validation.
"""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest

from core.adapters.cu_api_parity_v1 import (
    PARITY_FORBIDDEN_ACTIONS,
    ExtractionComparison,
    ParityCheck,
    ParityConfidence,
    ParityResult,
    ParityStatus,
    assess_parity,
    compare_extractions,
)
from core.adapters.google_docs_adapter_v1 import (
    ExtractionPath,
    ExtractionResult,
    GoogleDocsAdapterV1,
    NormalizedExtraction,
)


SAFE_CONFIG = {
    "safe_doc_url_or_id": "doc123",
    "safe_doc_title": "Test Doc",
    "cu_enabled": True,
    "api_enabled": True,
    "preview_char_limit": 500,
}


def _make_extraction(path: str, content: str) -> ExtractionResult:
    r = ExtractionResult(
        extraction_id=f"ext-{path}",
        adapter_id="test",
        doc_url_or_id="doc123",
        doc_title="Test Doc",
        extraction_path=path,
        raw_content=content,
    )
    r.compute_content_hash()
    return r


def _make_normalized(ext_id: str, path: str, content: str) -> NormalizedExtraction:
    return NormalizedExtraction(
        normalization_id=f"norm-{path}",
        source_extraction_id=ext_id,
        extraction_path=path,
        normalized_content=content,
    )


class TestParityCheck:
    def test_matching_fields(self) -> None:
        check = ParityCheck("title", "Test", "Test")
        assert check.match is True
        assert check.discrepancy == ""

    def test_mismatched_fields(self) -> None:
        check = ParityCheck("title", "Test A", "Test B")
        assert check.match is False
        assert "title" in check.discrepancy

    def test_to_dict(self) -> None:
        check = ParityCheck("count", "10", "11")
        d = check.to_dict()
        assert d["field_name"] == "count"
        assert d["match"] is False


class TestExtractionComparison:
    def test_all_matching(self) -> None:
        cu = _make_extraction("cu", "hello world")
        api = _make_extraction("api", "hello world")
        cu_n = _make_normalized("ext-cu", "cu", "hello world")
        api_n = _make_normalized("ext-api", "api", "hello world")
        comp = compare_extractions(cu, api, cu_n, api_n)
        assert comp.match_ratio == 1.0
        assert comp.failing_checks == 0

    def test_partial_match(self) -> None:
        cu = _make_extraction("cu", "hello world extra")
        api = _make_extraction("api", "hello world")
        cu_n = _make_normalized("ext-cu", "cu", "hello world extra")
        api_n = _make_normalized("ext-api", "api", "hello world")
        comp = compare_extractions(cu, api, cu_n, api_n)
        assert comp.match_ratio < 1.0
        assert comp.failing_checks > 0

    def test_to_dict(self) -> None:
        cu = _make_extraction("cu", "test")
        api = _make_extraction("api", "test")
        cu_n = _make_normalized("ext-cu", "cu", "test")
        api_n = _make_normalized("ext-api", "api", "test")
        comp = compare_extractions(cu, api, cu_n, api_n)
        d = comp.to_dict()
        assert "total_checks" in d
        assert "checks" in d


class TestParityResult:
    def test_exact_parity(self) -> None:
        cu = _make_extraction("cu", "hello world")
        api = _make_extraction("api", "hello world")
        cu_n = _make_normalized("ext-cu", "cu", "hello world")
        api_n = _make_normalized("ext-api", "api", "hello world")
        comp = compare_extractions(cu, api, cu_n, api_n)
        result = assess_parity(comp, cu_n, api_n)
        assert result.confidence == ParityConfidence.EXACT
        assert result.status == ParityStatus.PASSED
        assert result.normalized_hash_match is True

    def test_degraded_parity(self) -> None:
        cu = _make_extraction("cu", "completely different text here")
        api = _make_extraction("api", "hello world")
        cu_n = _make_normalized("ext-cu", "cu", "completely different text here")
        api_n = _make_normalized("ext-api", "api", "hello world")
        comp = compare_extractions(cu, api, cu_n, api_n)
        result = assess_parity(comp, cu_n, api_n)
        assert result.confidence in (
            ParityConfidence.LOW,
            ParityConfidence.NO_PARITY,
        )
        assert result.normalized_hash_match is False
        assert len(result.discrepancies) > 0

    def test_discrepancies_captured(self) -> None:
        cu = _make_extraction("cu", "abc")
        api = _make_extraction("api", "xyz")
        cu_n = _make_normalized("ext-cu", "cu", "abc")
        api_n = _make_normalized("ext-api", "api", "xyz")
        comp = compare_extractions(cu, api, cu_n, api_n)
        result = assess_parity(comp, cu_n, api_n)
        assert len(result.discrepancies) > 0

    def test_parity_schema_valid(self) -> None:
        result = ParityResult(
            result_id="",
            comparison_id="cmp-1",
            confidence=ParityConfidence.HIGH,
            status=ParityStatus.PASSED,
        )
        d = result.to_dict()
        assert d["confidence"] == "high"
        assert d["status"] == "passed"
        assert "result_id" in d
        assert "discrepancies" in d


class TestForbiddenActions:
    def test_arbitrary_doc_comparison_forbidden(self) -> None:
        assert "arbitrary_doc_comparison" in PARITY_FORBIDDEN_ACTIONS

    def test_drive_wide_scan_forbidden(self) -> None:
        assert "drive_wide_scan" in PARITY_FORBIDDEN_ACTIONS

    def test_silent_fallback_forbidden(self) -> None:
        assert "silent_fallback" in PARITY_FORBIDDEN_ACTIONS

    def test_mutation_forbidden(self) -> None:
        assert "mutation" in PARITY_FORBIDDEN_ACTIONS

    def test_ocr_identical_without_downgrade_forbidden(self) -> None:
        assert "ocr_as_identical_without_downgrade" in PARITY_FORBIDDEN_ACTIONS
