"""Canonical Contract Mapping for W-GWS-API-001.

Maps Google Docs/Drive API output into CanonicalSourceRecord fields.
Encodes the tab-aware extraction requirements as verifiable constraints.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApiContractRequirement:
    requirement_id: str
    description: str
    required: bool = True
    verifiable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "description": self.description,
            "required": self.required,
            "verifiable": self.verifiable,
        }


@dataclass
class W0001ExpectedCoverageContract:
    expected_docs: int = 28
    expected_tabs: int = 321
    expected_child_tabs: int = 134
    expected_words: int = 283831
    instance_id: str = "antony_empyrean"
    global_canon_allowed_by_default: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_docs": self.expected_docs,
            "expected_tabs": self.expected_tabs,
            "expected_child_tabs": self.expected_child_tabs,
            "expected_words": self.expected_words,
            "instance_id": self.instance_id,
            "global_canon_allowed_by_default": self.global_canon_allowed_by_default,
        }


@dataclass
class GoogleWorkspaceApiContractMapping:
    mapping_id: str = "w_gws_api_001_canonical_contract_mapping"
    api_requirements: list[ApiContractRequirement] = field(default_factory=list)
    canonical_field_mappings: dict[str, str] = field(default_factory=dict)
    extraction_constraints: list[str] = field(default_factory=list)
    coverage_contract: W0001ExpectedCoverageContract | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "api_requirements": [r.to_dict() for r in self.api_requirements],
            "canonical_field_mappings": self.canonical_field_mappings,
            "extraction_constraints": self.extraction_constraints,
            "coverage_contract": (
                self.coverage_contract.to_dict() if self.coverage_contract else None
            ),
        }


_API_REQUIREMENTS = [
    ApiContractRequirement(
        "include_tabs_content",
        "includeTabsContent=true must be set on documents.get",
    ),
    ApiContractRequirement(
        "document_tabs_traversal",
        "traverse document.tabs array for all top-level tabs",
    ),
    ApiContractRequirement(
        "child_tabs_recursion",
        "recurse childTabs for all nested/child tabs",
    ),
    ApiContractRequirement(
        "per_tab_body_extraction",
        "collect body/content per tab via tab.documentTab.body",
    ),
    ApiContractRequirement(
        "empty_tab_marking",
        "mark tabs with no text content as empty",
    ),
    ApiContractRequirement(
        "inaccessible_tab_marking",
        "mark inaccessible content with reason",
    ),
    ApiContractRequirement(
        "file_id_preservation",
        "preserve file_id/document_id from Drive/Docs API",
    ),
    ApiContractRequirement(
        "tab_id_preservation",
        "preserve tab_id, title, and computed tab_path",
    ),
    ApiContractRequirement(
        "backend_identity_preservation",
        "preserve backend/access path identity in provenance",
    ),
    ApiContractRequirement(
        "source_account_preservation",
        "preserve source account/instance scope",
    ),
    ApiContractRequirement(
        "canonical_source_record_emission",
        "emit CanonicalSourceRecord per document",
    ),
    ApiContractRequirement(
        "coverage_validation",
        "validate coverage against expected doc/tab/child-tab/word counts",
    ),
]

_CANONICAL_FIELD_MAPPINGS = {
    "file_id": "Drive API file.id → CanonicalSourceRecord.file_id",
    "title": "Drive API file.name → CanonicalSourceRecord.title",
    "tab_id": "Docs API tab.tabProperties.tabId → TabSourceRecord.tab_id",
    "tab_title": "Docs API tab.tabProperties.title → TabSourceRecord.tab_title",
    "tab_path": "computed from nesting depth → TabSourceRecord.tab_path",
    "parent_tab_id": "tab.tabProperties.parentTabId → TabSourceRecord.parent_tab_id",
    "is_empty": "len(text_content) == 0 → TabSourceRecord.is_empty",
    "text_content": "tab.documentTab.body → TabSourceRecord.text_content",
    "word_count": "len(text_content.split()) → TabSourceRecord.word_count",
    "backend_type": "'api' → ProvenanceRecord.backend_type",
    "extraction_method": "'tab_aware_api' → ProvenanceRecord.extraction_method",
    "content_came_from_api": "True → ProvenanceRecord.content_came_from_api",
}

_EXTRACTION_CONSTRAINTS = [
    "includeTabsContent=true is non-negotiable",
    "first-tab-only extraction is rejected as silent data loss",
    "document.body without tabs traversal is rejected",
    "tabs without childTabs recursion is incomplete",
    "empty tabs must be explicitly marked, not silently dropped",
    "inaccessible content must carry a reason, not be silently ignored",
    "word count must be computed per tab for parity validation",
    "extraction timestamp must be recorded",
]


def build_w_gws_api_001_contract_mapping() -> GoogleWorkspaceApiContractMapping:
    return GoogleWorkspaceApiContractMapping(
        api_requirements=list(_API_REQUIREMENTS),
        canonical_field_mappings=dict(_CANONICAL_FIELD_MAPPINGS),
        extraction_constraints=list(_EXTRACTION_CONSTRAINTS),
        coverage_contract=W0001ExpectedCoverageContract(),
    )


def api_mapping_requires_include_tabs_content(
    mapping: GoogleWorkspaceApiContractMapping,
) -> bool:
    return any(
        r.requirement_id == "include_tabs_content" and r.required
        for r in mapping.api_requirements
    )


def api_mapping_requires_document_tabs_traversal(
    mapping: GoogleWorkspaceApiContractMapping,
) -> bool:
    return any(
        r.requirement_id == "document_tabs_traversal" and r.required
        for r in mapping.api_requirements
    )


def api_mapping_requires_child_tabs_recursion(
    mapping: GoogleWorkspaceApiContractMapping,
) -> bool:
    return any(
        r.requirement_id == "child_tabs_recursion" and r.required
        for r in mapping.api_requirements
    )


def api_mapping_preserves_per_tab_provenance(
    mapping: GoogleWorkspaceApiContractMapping,
) -> bool:
    return (
        "tab_id" in mapping.canonical_field_mappings
        and "tab_title" in mapping.canonical_field_mappings
        and "tab_path" in mapping.canonical_field_mappings
        and "parent_tab_id" in mapping.canonical_field_mappings
    )


def api_mapping_rejects_first_tab_only(
    mapping: GoogleWorkspaceApiContractMapping,
) -> bool:
    return any(
        "first-tab-only" in c.lower() and "rejected" in c.lower()
        for c in mapping.extraction_constraints
    )


def build_w0_001_expected_coverage_contract() -> W0001ExpectedCoverageContract:
    return W0001ExpectedCoverageContract()
