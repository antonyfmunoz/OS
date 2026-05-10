"""Tests for Phase 96.0 extraction backend contracts."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.extraction_backend_contracts import (
    BackendCapabilityReport,
    CanonicalExtractionContract,
    CapabilityDeclaration,
    ExtractionBackendType,
    ExtractionCapability,
    ExtractionCoverageStatus,
    ExtractionFailureReason,
    build_google_docs_contract,
    evaluate_backend_against_contract,
)


def test_all_backend_types_declared():
    """API, CLI, CU can all declare the same required capabilities."""
    for bt in [
        ExtractionBackendType.API,
        ExtractionBackendType.CLI,
        ExtractionBackendType.COMPUTER_USE,
    ]:
        contract = build_google_docs_contract("test_id", bt)
        assert contract.backend_type == bt
        assert ExtractionCapability.DOCUMENT_TABS in contract.required_capabilities
        assert ExtractionCapability.CHILD_TABS in contract.required_capabilities
        assert ExtractionCapability.DOCUMENT_BODY in contract.required_capabilities


def test_contract_requires_all_core_capabilities():
    """Contract requires inventory, metadata, body, tabs, child_tabs, provenance, validation."""
    contract = build_google_docs_contract("file123", ExtractionBackendType.API)
    assert len(contract.required_capabilities) == 7
    assert ExtractionCapability.SOURCE_INVENTORY in contract.required_capabilities
    assert ExtractionCapability.COMPLETENESS_VALIDATION in contract.required_capabilities


def test_contract_has_blocked_actions():
    """Contract blocks destructive and credential-leaking actions."""
    contract = build_google_docs_contract("file123", ExtractionBackendType.API)
    assert "edit_document" in contract.blocked_actions
    assert "open_gmail" in contract.blocked_actions
    assert "capture_credentials" in contract.blocked_actions


def test_complete_backend_passes_evaluation():
    """A backend with all COMPLETE capabilities passes evaluation."""
    contract = build_google_docs_contract("file123", ExtractionBackendType.API)
    caps = [
        CapabilityDeclaration(c, ExtractionCoverageStatus.COMPLETE)
        for c in contract.required_capabilities
    ]
    report = evaluate_backend_against_contract(contract, caps)
    assert report.overall_status == ExtractionCoverageStatus.COMPLETE
    assert report.missing_capabilities == []
    assert report.blocked_capabilities == []


def test_missing_tabs_fail_completeness():
    """Missing DOCUMENT_TABS capability fails completeness."""
    contract = build_google_docs_contract("file123", ExtractionBackendType.COMPUTER_USE)
    caps = [
        CapabilityDeclaration(c, ExtractionCoverageStatus.COMPLETE)
        for c in contract.required_capabilities
        if c != ExtractionCapability.DOCUMENT_TABS
    ]
    report = evaluate_backend_against_contract(contract, caps)
    assert report.overall_status != ExtractionCoverageStatus.COMPLETE
    assert ExtractionCapability.DOCUMENT_TABS in report.missing_capabilities


def test_missing_body_fails_completeness():
    """Missing DOCUMENT_BODY capability fails completeness."""
    contract = build_google_docs_contract("file123", ExtractionBackendType.COMPUTER_USE)
    caps = [
        CapabilityDeclaration(c, ExtractionCoverageStatus.COMPLETE)
        for c in contract.required_capabilities
        if c != ExtractionCapability.DOCUMENT_BODY
    ]
    report = evaluate_backend_against_contract(contract, caps)
    assert ExtractionCapability.DOCUMENT_BODY in report.missing_capabilities


def test_partial_backend_cannot_claim_complete():
    """A backend with BLOCKED capabilities cannot be COMPLETE."""
    contract = build_google_docs_contract("file123", ExtractionBackendType.COMPUTER_USE)
    caps = []
    for c in contract.required_capabilities:
        if c == ExtractionCapability.DOCUMENT_BODY:
            caps.append(
                CapabilityDeclaration(
                    c,
                    ExtractionCoverageStatus.BLOCKED,
                    failure_reason=ExtractionFailureReason.FOREGROUND_OWNERSHIP_BLOCKED,
                )
            )
        else:
            caps.append(CapabilityDeclaration(c, ExtractionCoverageStatus.COMPLETE))

    report = evaluate_backend_against_contract(contract, caps)
    assert report.overall_status != ExtractionCoverageStatus.COMPLETE
    assert ExtractionCapability.DOCUMENT_BODY in report.blocked_capabilities


def test_failed_capability_counts_as_missing():
    """A FAILED capability is treated as missing."""
    contract = build_google_docs_contract("file123", ExtractionBackendType.CLI)
    caps = []
    for c in contract.required_capabilities:
        if c == ExtractionCapability.CHILD_TABS:
            caps.append(CapabilityDeclaration(c, ExtractionCoverageStatus.FAILED))
        else:
            caps.append(CapabilityDeclaration(c, ExtractionCoverageStatus.COMPLETE))

    report = evaluate_backend_against_contract(contract, caps)
    assert ExtractionCapability.CHILD_TABS in report.missing_capabilities


def test_contract_serialization():
    """Contract serializes to dict correctly."""
    contract = build_google_docs_contract("abc123", ExtractionBackendType.API)
    d = contract.to_dict()
    assert d["source_id"] == "abc123"
    assert d["backend_type"] == "api"
    assert "document_tabs" in d["required_capabilities"]


def test_capability_report_serialization():
    """BackendCapabilityReport serializes to dict."""
    report = BackendCapabilityReport(
        backend_type=ExtractionBackendType.COMPUTER_USE,
        overall_status=ExtractionCoverageStatus.PARTIAL,
        missing_capabilities=[ExtractionCapability.DOCUMENT_BODY],
    )
    d = report.to_dict()
    assert d["backend_type"] == "computer_use"
    assert d["overall_status"] == "partial"
    assert "document_body" in d["missing_capabilities"]
