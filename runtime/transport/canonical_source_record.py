"""
Canonical source record for Phase 96.0.

Shared output schema used by ALL extraction backends (API, CLI, Computer Use).
Every backend must normalize its output into this format regardless of mechanism.

Hard rule: No backend-specific schema drift.
API/CLI/CU outputs must normalize into this same record format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from eos_ai.transport.extraction_backend_contracts import (
    ExtractionBackendType,
    ExtractionCoverageStatus,
)


@dataclass
class TabSourceRecord:
    """Canonical record for a single document tab."""

    tab_id: str
    tab_title: str
    tab_path: str
    parent_tab_id: str | None = None
    tab_order: int = 0
    is_empty: bool = False
    text_content: str = ""
    word_count: int = 0
    character_count: int = 0
    extraction_coverage_status: ExtractionCoverageStatus = ExtractionCoverageStatus.UNKNOWN
    extraction_notes: str = ""

    def to_dict(self, include_text: bool = True) -> dict[str, Any]:
        d: dict[str, Any] = {
            "tab_id": self.tab_id,
            "tab_title": self.tab_title,
            "tab_path": self.tab_path,
            "parent_tab_id": self.parent_tab_id,
            "tab_order": self.tab_order,
            "is_empty": self.is_empty,
            "word_count": self.word_count,
            "character_count": self.character_count,
            "extraction_coverage_status": self.extraction_coverage_status.value,
            "extraction_notes": self.extraction_notes,
        }
        if include_text:
            d["text_content"] = self.text_content
        return d


@dataclass
class ProvenanceRecord:
    """Records HOW content was extracted."""

    backend_type: ExtractionBackendType
    extraction_method: str
    source_observed_from: str
    content_came_from_api: bool = False
    content_came_from_cli: bool = False
    content_came_from_visible_ui: bool = False
    any_content_inaccessible: bool = False
    inaccessible_reason: str = ""
    fallback_used: bool = False
    fallback_backend: ExtractionBackendType | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "backend_type": self.backend_type.value,
            "extraction_method": self.extraction_method,
            "source_observed_from": self.source_observed_from,
            "content_came_from_api": self.content_came_from_api,
            "content_came_from_cli": self.content_came_from_cli,
            "content_came_from_visible_ui": self.content_came_from_visible_ui,
            "any_content_inaccessible": self.any_content_inaccessible,
        }
        if self.inaccessible_reason:
            d["inaccessible_reason"] = self.inaccessible_reason
        if self.fallback_used:
            d["fallback_used"] = True
            d["fallback_backend"] = self.fallback_backend.value if self.fallback_backend else None
        return d


@dataclass
class DocumentSourceRecord:
    """Canonical record for a fully-extracted document."""

    file_id: str
    title: str
    mime_type: str = "application/vnd.google-apps.document"
    source_account: str = ""
    web_view_link: str = ""
    modified_time: str = ""
    created_time: str = ""
    owner_metadata: dict[str, str] = field(default_factory=dict)
    parent_metadata: dict[str, str] = field(default_factory=dict)
    backend_type: ExtractionBackendType = ExtractionBackendType.API
    extraction_timestamp: str = ""
    extraction_method: str = ""
    extraction_coverage_status: ExtractionCoverageStatus = ExtractionCoverageStatus.UNKNOWN
    tabs: list[TabSourceRecord] = field(default_factory=list)
    provenance: ProvenanceRecord | None = None

    def __post_init__(self) -> None:
        if not self.extraction_timestamp:
            self.extraction_timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def total_tabs(self) -> int:
        return len(self.tabs)

    @property
    def total_words(self) -> int:
        return sum(t.word_count for t in self.tabs)

    @property
    def total_characters(self) -> int:
        return sum(t.character_count for t in self.tabs)

    @property
    def empty_tab_count(self) -> int:
        return sum(1 for t in self.tabs if t.is_empty)

    @property
    def has_incomplete_tabs(self) -> bool:
        return any(
            t.extraction_coverage_status != ExtractionCoverageStatus.COMPLETE for t in self.tabs
        )

    def validate_completeness(self) -> tuple[bool, list[str]]:
        """Validate that this record meets the completeness contract."""
        issues: list[str] = []

        if not self.file_id:
            issues.append("missing file_id")
        if not self.title:
            issues.append("missing title")
        if not self.tabs:
            issues.append("no tabs extracted")
        if self.extraction_coverage_status == ExtractionCoverageStatus.UNKNOWN:
            issues.append("coverage status not set")
        if not self.provenance:
            issues.append("missing provenance record")

        for tab in self.tabs:
            if tab.extraction_coverage_status == ExtractionCoverageStatus.UNKNOWN:
                issues.append(f"tab '{tab.tab_title}' has unknown coverage status")
            if (
                not tab.is_empty
                and tab.word_count == 0
                and tab.extraction_coverage_status == ExtractionCoverageStatus.COMPLETE
            ):
                issues.append(f"tab '{tab.tab_title}' claims complete but has 0 words")

        is_complete = len(issues) == 0
        return is_complete, issues

    def to_dict(self, include_text: bool = True) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "title": self.title,
            "mime_type": self.mime_type,
            "source_account": self.source_account,
            "web_view_link": self.web_view_link,
            "modified_time": self.modified_time,
            "created_time": self.created_time,
            "owner_metadata": self.owner_metadata,
            "parent_metadata": self.parent_metadata,
            "backend_type": self.backend_type.value,
            "extraction_timestamp": self.extraction_timestamp,
            "extraction_method": self.extraction_method,
            "extraction_coverage_status": self.extraction_coverage_status.value,
            "total_tabs": self.total_tabs,
            "total_words": self.total_words,
            "total_characters": self.total_characters,
            "empty_tab_count": self.empty_tab_count,
            "tabs": [t.to_dict(include_text=include_text) for t in self.tabs],
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }


def build_api_source_record(
    file_id: str,
    title: str,
    tabs: list[TabSourceRecord],
    source_account: str = "",
) -> DocumentSourceRecord:
    """Build a DocumentSourceRecord from an API extraction."""
    all_complete = all(
        t.extraction_coverage_status == ExtractionCoverageStatus.COMPLETE for t in tabs
    )
    coverage = (
        ExtractionCoverageStatus.COMPLETE if all_complete else ExtractionCoverageStatus.PARTIAL
    )

    return DocumentSourceRecord(
        file_id=file_id,
        title=title,
        source_account=source_account,
        backend_type=ExtractionBackendType.API,
        extraction_method="google_docs_api_include_tabs_content",
        extraction_coverage_status=coverage,
        tabs=tabs,
        provenance=ProvenanceRecord(
            backend_type=ExtractionBackendType.API,
            extraction_method="google_docs_api_include_tabs_content",
            source_observed_from="Google Docs API v1",
            content_came_from_api=True,
        ),
    )


def build_cli_source_record(
    file_id: str,
    title: str,
    tabs: list[TabSourceRecord],
    cli_tool: str = "gws",
    source_account: str = "",
) -> DocumentSourceRecord:
    """Build a DocumentSourceRecord from a CLI extraction."""
    all_complete = all(
        t.extraction_coverage_status == ExtractionCoverageStatus.COMPLETE for t in tabs
    )
    coverage = (
        ExtractionCoverageStatus.COMPLETE if all_complete else ExtractionCoverageStatus.PARTIAL
    )

    return DocumentSourceRecord(
        file_id=file_id,
        title=title,
        source_account=source_account,
        backend_type=ExtractionBackendType.CLI,
        extraction_method=f"{cli_tool}_docs_get_include_tabs",
        extraction_coverage_status=coverage,
        tabs=tabs,
        provenance=ProvenanceRecord(
            backend_type=ExtractionBackendType.CLI,
            extraction_method=f"{cli_tool}_docs_get_include_tabs",
            source_observed_from=f"{cli_tool} CLI tool",
            content_came_from_cli=True,
        ),
    )


def build_cu_source_record(
    file_id: str,
    title: str,
    tabs: list[TabSourceRecord],
    extraction_method: str = "accessibility_tree_clipboard",
    any_inaccessible: bool = False,
    inaccessible_reason: str = "",
) -> DocumentSourceRecord:
    """Build a DocumentSourceRecord from a Computer Use extraction."""
    all_complete = all(
        t.extraction_coverage_status == ExtractionCoverageStatus.COMPLETE for t in tabs
    )
    if not tabs:
        coverage = ExtractionCoverageStatus.FAILED
    elif all_complete and not any_inaccessible:
        coverage = ExtractionCoverageStatus.COMPLETE
    else:
        coverage = ExtractionCoverageStatus.PARTIAL

    return DocumentSourceRecord(
        file_id=file_id,
        title=title,
        backend_type=ExtractionBackendType.COMPUTER_USE,
        extraction_method=extraction_method,
        extraction_coverage_status=coverage,
        tabs=tabs,
        provenance=ProvenanceRecord(
            backend_type=ExtractionBackendType.COMPUTER_USE,
            extraction_method=extraction_method,
            source_observed_from="Chrome Profile 5 + Windows UI Automation",
            content_came_from_visible_ui=True,
            any_content_inaccessible=any_inaccessible,
            inaccessible_reason=inaccessible_reason,
        ),
    )
