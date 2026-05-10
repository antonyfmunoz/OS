"""Tests for Phase 96.0 Google Docs backend parity matrix."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.extraction_backend_contracts import (
    ExtractionBackendType,
    ExtractionCapability,
    ExtractionCoverageStatus,
)
from eos_ai.substrate.google_docs_backend_parity_matrix import (
    build_google_docs_backend_matrix,
    mark_api_capabilities,
    mark_cli_capabilities,
    mark_computer_use_capabilities,
    recommend_next_backend_hardening_step,
    evaluate_backend_against_contract,
    build_google_docs_contract,
)


def test_api_tab_aware_marks_all_tabs_supported():
    """API with tab-aware flag marks DOCUMENT_TABS as COMPLETE."""
    caps = mark_api_capabilities(tab_aware=True)
    tab_cap = next(c for c in caps if c.capability == ExtractionCapability.DOCUMENT_TABS)
    assert tab_cap.status == ExtractionCoverageStatus.COMPLETE


def test_api_without_tabs_marks_partial():
    """API without includeTabsContent marks tabs as PARTIAL."""
    caps = mark_api_capabilities(tab_aware=False)
    tab_cap = next(c for c in caps if c.capability == ExtractionCapability.DOCUMENT_TABS)
    assert tab_cap.status == ExtractionCoverageStatus.PARTIAL


def test_cli_marks_capability_based_on_wrapper():
    """CLI marks tabs COMPLETE only when wrapping tab-aware API."""
    caps_yes = mark_cli_capabilities(wraps_tab_aware_api=True)
    caps_no = mark_cli_capabilities(wraps_tab_aware_api=False)
    tab_yes = next(c for c in caps_yes if c.capability == ExtractionCapability.DOCUMENT_TABS)
    tab_no = next(c for c in caps_no if c.capability == ExtractionCapability.DOCUMENT_TABS)
    assert tab_yes.status == ExtractionCoverageStatus.COMPLETE
    assert tab_no.status == ExtractionCoverageStatus.PARTIAL


def test_cu_marks_tab_detection_partial():
    """CU marks tab detection as PARTIAL (detection proven, navigation not)."""
    caps = mark_computer_use_capabilities()
    tab_cap = next(c for c in caps if c.capability == ExtractionCapability.DOCUMENT_TABS)
    assert tab_cap.status == ExtractionCoverageStatus.PARTIAL


def test_cu_marks_body_blocked():
    """CU marks document body as BLOCKED due to foreground issue."""
    caps = mark_computer_use_capabilities()
    body_cap = next(c for c in caps if c.capability == ExtractionCapability.DOCUMENT_BODY)
    assert body_cap.status == ExtractionCoverageStatus.BLOCKED


def test_cu_accessibility_tree_complete():
    """CU marks accessibility tree extraction as COMPLETE."""
    caps = mark_computer_use_capabilities()
    at_cap = next(
        c for c in caps if c.capability == ExtractionCapability.ACCESSIBILITY_TREE_EXTRACTION
    )
    assert at_cap.status == ExtractionCoverageStatus.COMPLETE


def test_recommendation_when_api_incomplete():
    """Recommends running tab-aware API when API is not complete."""
    contract = build_google_docs_contract("test", ExtractionBackendType.API)
    api_caps = mark_api_capabilities(tab_aware=False)
    api_report = evaluate_backend_against_contract(contract, api_caps)

    cli_contract = build_google_docs_contract("test", ExtractionBackendType.CLI)
    cli_caps = mark_cli_capabilities(wraps_tab_aware_api=True)
    cli_report = evaluate_backend_against_contract(cli_contract, cli_caps)

    cu_contract = build_google_docs_contract("test", ExtractionBackendType.COMPUTER_USE)
    cu_caps = mark_computer_use_capabilities()
    cu_report = evaluate_backend_against_contract(cu_contract, cu_caps)

    rec = recommend_next_backend_hardening_step(api_report, cli_report, cu_report)
    assert rec == "RUN_TAB_AWARE_API_EXTRACTION"


def test_recommendation_chooses_cu_hardening():
    """Recommends CU doc reader hardening when parity is needed."""
    contract = build_google_docs_contract("test", ExtractionBackendType.API)
    api_caps = mark_api_capabilities(tab_aware=True)
    api_report = evaluate_backend_against_contract(contract, api_caps)

    cli_contract = build_google_docs_contract("test", ExtractionBackendType.CLI)
    cli_caps = mark_cli_capabilities(wraps_tab_aware_api=True)
    cli_report = evaluate_backend_against_contract(cli_contract, cli_caps)

    cu_contract = build_google_docs_contract("test", ExtractionBackendType.COMPUTER_USE)
    cu_caps = mark_computer_use_capabilities()
    cu_report = evaluate_backend_against_contract(cu_contract, cu_caps)

    rec = recommend_next_backend_hardening_step(api_report, cli_report, cu_report)
    assert "HARDEN_CU_DOCUMENT_READER" in rec


def test_full_matrix_builds_successfully():
    """Full matrix builds without errors and has all entries."""
    matrix = build_google_docs_backend_matrix()
    assert matrix.api_entry is not None
    assert matrix.cli_entry is not None
    assert matrix.cu_entry is not None
    assert matrix.api_entry.overall_status == "complete"
    assert matrix.cu_entry.overall_status != "complete"


def test_matrix_serialization():
    """Matrix serializes to dict correctly."""
    matrix = build_google_docs_backend_matrix()
    d = matrix.to_dict()
    assert d["api"]["backend_type"] == "api"
    assert d["cli"]["backend_type"] == "cli"
    assert d["computer_use"]["backend_type"] == "computer_use"
    assert d["recommended_action"] != ""
