"""
Google Docs tab coverage audit for W0-001R.

Audits whether a Google Docs API extraction captured all document tabs
or only the first/default tab. Google Docs supports multiple tabs per
document (introduced 2024), and the default API call without
includeTabsContent=true only returns the first tab's body.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TabCoverageStatus(Enum):
    COMPLETE_SINGLE_TAB = "complete_single_tab"
    COMPLETE_ALL_TABS = "complete_all_tabs"
    FIRST_TAB_ONLY = "first_tab_only"
    UNKNOWN = "unknown"


@dataclass
class TabInfo:
    tab_id: str
    title: str
    depth: int = 0
    word_count: int = 0
    child_tab_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tab_id": self.tab_id,
            "title": self.title,
            "depth": self.depth,
            "word_count": self.word_count,
            "child_tab_count": self.child_tab_count,
        }


@dataclass
class DocTabAuditResult:
    file_id: str
    title: str
    top_level_tab_count: int = 1
    total_tabs: int = 1
    total_child_tabs: int = 0
    total_words_all_tabs: int = 0
    first_tab_words: int = 0
    is_multi_tab: bool = False
    prior_coverage: TabCoverageStatus = TabCoverageStatus.UNKNOWN
    tabs: list[TabInfo] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "title": self.title,
            "top_level_tab_count": self.top_level_tab_count,
            "total_tabs": self.total_tabs,
            "total_child_tabs": self.total_child_tabs,
            "total_words_all_tabs": self.total_words_all_tabs,
            "first_tab_words": self.first_tab_words,
            "is_multi_tab": self.is_multi_tab,
            "prior_coverage": self.prior_coverage.value,
            "tabs": [t.to_dict() for t in self.tabs],
        }


def classify_prior_coverage(total_tabs: int) -> TabCoverageStatus:
    """Classify whether prior extraction covered all tabs."""
    if total_tabs <= 1:
        return TabCoverageStatus.COMPLETE_SINGLE_TAB
    return TabCoverageStatus.FIRST_TAB_ONLY


def extract_tabs_from_doc_json(doc_json: dict[str, Any]) -> list[TabInfo]:
    """Recursively extract tab metadata from a tab-aware doc response."""
    tabs = doc_json.get("tabs", [])
    if not tabs:
        return []
    return _process_tabs_recursive(tabs, depth=0)


def _process_tabs_recursive(tabs_list: list[dict], depth: int) -> list[TabInfo]:
    """Recursively process tabs and childTabs."""
    results: list[TabInfo] = []
    for tab in tabs_list:
        tp = tab.get("tabProperties", {})
        dt = tab.get("documentTab", {})
        body = dt.get("body", {})
        child_tabs = tab.get("childTabs", [])

        word_count = count_body_words(body)

        info = TabInfo(
            tab_id=tp.get("tabId", ""),
            title=tp.get("title", ""),
            depth=depth,
            word_count=word_count,
            child_tab_count=len(child_tabs),
        )
        results.append(info)

        if child_tabs:
            results.extend(_process_tabs_recursive(child_tabs, depth + 1))

    return results


def count_body_words(body: dict[str, Any]) -> int:
    """Count words in a Google Docs body content structure."""
    text = extract_text_from_body(body)
    return len(text.split())


def extract_text_from_body(body: dict[str, Any]) -> str:
    """Extract plain text from a Google Docs body."""
    parts: list[str] = []
    for elem in body.get("content", []):
        if "paragraph" in elem:
            for pe in elem["paragraph"].get("elements", []):
                if "textRun" in pe:
                    parts.append(pe["textRun"]["content"])
        elif "table" in elem:
            for row in elem["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    for cc in cell.get("content", []):
                        if "paragraph" in cc:
                            for pe in cc["paragraph"].get("elements", []):
                                if "textRun" in pe:
                                    parts.append(pe["textRun"]["content"])
    return "".join(parts)


def build_tab_audit_result(
    file_id: str,
    title: str,
    doc_json: dict[str, Any],
) -> DocTabAuditResult:
    """Build a complete tab audit result from a tab-aware API response."""
    tabs = extract_tabs_from_doc_json(doc_json)
    total_words = sum(t.word_count for t in tabs)
    total_child = sum(t.child_tab_count for t in tabs)
    top_level = len(doc_json.get("tabs", []))

    return DocTabAuditResult(
        file_id=file_id,
        title=title,
        top_level_tab_count=top_level,
        total_tabs=len(tabs),
        total_child_tabs=total_child,
        total_words_all_tabs=total_words,
        first_tab_words=tabs[0].word_count if tabs else 0,
        is_multi_tab=len(tabs) > 1,
        prior_coverage=classify_prior_coverage(len(tabs)),
        tabs=tabs,
    )


def compute_audit_summary(results: list[DocTabAuditResult]) -> dict[str, Any]:
    """Compute summary statistics from a list of audit results."""
    multi_tab = [r for r in results if r.is_multi_tab]
    single_tab = [r for r in results if not r.is_multi_tab]
    first_tab_only = [r for r in results if r.prior_coverage == TabCoverageStatus.FIRST_TAB_ONLY]

    total_first_tab_words = sum(r.first_tab_words for r in results)
    total_all_tab_words = sum(r.total_words_all_tabs for r in results)

    return {
        "total_docs": len(results),
        "multi_tab_docs": len(multi_tab),
        "single_tab_docs": len(single_tab),
        "first_tab_only_risk": len(first_tab_only),
        "total_first_tab_words": total_first_tab_words,
        "total_all_tab_words": total_all_tab_words,
        "missing_words": total_all_tab_words - total_first_tab_words,
        "prior_coverage_pct": round(total_first_tab_words / total_all_tab_words * 100, 1) if total_all_tab_words > 0 else 100.0,
    }
