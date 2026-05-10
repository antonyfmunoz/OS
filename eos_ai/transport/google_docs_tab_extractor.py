"""
Google Docs tab-aware content extractor for W0-001R.

Extracts text from ALL tabs in a Google Doc, preserving tab provenance
(tab ID, title, hierarchy depth, parent path).

Requires: includeTabsContent=true in the API call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eos_ai.transport.google_docs_tab_audit import extract_text_from_body


@dataclass
class TabExtraction:
    tab_id: str
    title: str
    depth: int
    parent_path: str
    word_count: int
    char_count: int
    text_content: str

    def to_dict(self, include_text: bool = True) -> dict[str, Any]:
        d: dict[str, Any] = {
            "tab_id": self.tab_id,
            "title": self.title,
            "depth": self.depth,
            "parent_path": self.parent_path,
            "word_count": self.word_count,
            "char_count": self.char_count,
        }
        if include_text:
            d["text_content"] = self.text_content
        return d


@dataclass
class DocTabExtraction:
    file_id: str
    title: str
    total_tabs: int
    total_words: int
    total_chars: int
    tabs: list[TabExtraction] = field(default_factory=list)

    def to_dict(self, include_text: bool = True) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "title": self.title,
            "total_tabs": self.total_tabs,
            "total_words": self.total_words,
            "total_chars": self.total_chars,
            "tabs": [t.to_dict(include_text=include_text) for t in self.tabs],
        }

    def get_full_text(self) -> str:
        """Get concatenated text from all tabs."""
        parts: list[str] = []
        for tab in self.tabs:
            if tab.text_content.strip():
                parts.append(f"[TAB: {tab.title or tab.tab_id}]\n{tab.text_content}")
        return "\n\n".join(parts)


def extract_all_tabs(
    file_id: str,
    title: str,
    doc_json: dict[str, Any],
) -> DocTabExtraction:
    """Extract text from all tabs in a Google Doc.

    Args:
        file_id: The Google Drive file ID.
        title: Document title.
        doc_json: Full API response with includeTabsContent=true.

    Returns:
        DocTabExtraction with all tab content and provenance.
    """
    tabs = doc_json.get("tabs", [])
    extractions = _extract_tabs_recursive(tabs, parent_path="", depth=0)

    total_words = sum(e.word_count for e in extractions)
    total_chars = sum(e.char_count for e in extractions)

    return DocTabExtraction(
        file_id=file_id,
        title=title,
        total_tabs=len(extractions),
        total_words=total_words,
        total_chars=total_chars,
        tabs=extractions,
    )


def _extract_tabs_recursive(
    tabs_list: list[dict],
    parent_path: str,
    depth: int,
) -> list[TabExtraction]:
    """Recursively extract text from tabs and childTabs."""
    results: list[TabExtraction] = []

    for tab in tabs_list:
        tp = tab.get("tabProperties", {})
        dt = tab.get("documentTab", {})
        body = dt.get("body", {})
        child_tabs = tab.get("childTabs", [])

        tab_id = tp.get("tabId", "")
        tab_title = tp.get("title", "")
        current_path = f"{parent_path}/{tab_title}" if parent_path else tab_title

        text = extract_text_from_body(body)
        word_count = len(text.split())

        extraction = TabExtraction(
            tab_id=tab_id,
            title=tab_title,
            depth=depth,
            parent_path=current_path,
            word_count=word_count,
            char_count=len(text),
            text_content=text,
        )
        results.append(extraction)

        if child_tabs:
            results.extend(_extract_tabs_recursive(child_tabs, current_path, depth + 1))

    return results


def compare_first_tab_vs_all(extraction: DocTabExtraction) -> dict[str, Any]:
    """Compare first-tab-only extraction against full tab extraction."""
    if not extraction.tabs:
        return {
            "first_tab_words": 0,
            "all_tabs_words": 0,
            "coverage_pct": 100.0,
            "missing_tabs": 0,
            "gap": "NONE",
        }

    first_tab_words = extraction.tabs[0].word_count
    all_tabs_words = extraction.total_words
    coverage = round(first_tab_words / all_tabs_words * 100, 1) if all_tabs_words > 0 else 100.0

    missing_tabs = extraction.total_tabs - 1
    if missing_tabs == 0:
        gap = "NONE"
    elif coverage >= 90:
        gap = "MINOR"
    elif coverage >= 50:
        gap = "MODERATE"
    else:
        gap = "SEVERE"

    return {
        "first_tab_words": first_tab_words,
        "all_tabs_words": all_tabs_words,
        "coverage_pct": coverage,
        "missing_tabs": missing_tabs,
        "gap": gap,
    }
