"""
Document CU vs API comparator for W0-001R.

Compares text extracted via computer-use (accessibility tree / scrolling)
against the tab-aware API extraction for coverage assessment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class DocComparisonResult:
    file_id: str
    title: str
    api_total_words: int
    api_total_tabs: int
    cu_total_words: int
    cu_tabs_read: int
    word_recall: float
    tab_coverage: float
    unique_api_phrases_found_in_cu: int
    total_api_phrases_checked: int
    phrase_recall: float
    confidence: str
    method_separation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "title": self.title,
            "api_total_words": self.api_total_words,
            "api_total_tabs": self.api_total_tabs,
            "cu_total_words": self.cu_total_words,
            "cu_tabs_read": self.cu_tabs_read,
            "word_recall": self.word_recall,
            "tab_coverage": self.tab_coverage,
            "unique_api_phrases_found_in_cu": self.unique_api_phrases_found_in_cu,
            "total_api_phrases_checked": self.total_api_phrases_checked,
            "phrase_recall": self.phrase_recall,
            "confidence": self.confidence,
            "method_separation": self.method_separation,
        }


def normalize_text(text: str) -> str:
    """Normalize text for comparison (lowercase, collapse whitespace)."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def extract_unique_phrases(text: str, phrase_length: int = 5) -> list[str]:
    """Extract unique N-word phrases for content matching."""
    words = normalize_text(text).split()
    if len(words) < phrase_length:
        return [" ".join(words)] if words else []

    phrases: list[str] = []
    seen: set[str] = set()
    step = max(1, phrase_length)

    for i in range(0, len(words) - phrase_length + 1, step):
        phrase = " ".join(words[i:i + phrase_length])
        if phrase not in seen:
            seen.add(phrase)
            phrases.append(phrase)

    return phrases


def compute_phrase_recall(
    api_text: str,
    cu_text: str,
    phrase_length: int = 5,
    max_phrases: int = 200,
) -> tuple[int, int]:
    """Check how many API phrases appear in CU text.

    Returns (found_count, total_checked).
    """
    api_phrases = extract_unique_phrases(api_text, phrase_length)
    if len(api_phrases) > max_phrases:
        step = len(api_phrases) // max_phrases
        api_phrases = api_phrases[::step][:max_phrases]

    cu_normalized = normalize_text(cu_text)
    found = sum(1 for p in api_phrases if p in cu_normalized)

    return found, len(api_phrases)


def compare_doc_extraction(
    file_id: str,
    title: str,
    api_text: str,
    api_total_tabs: int,
    cu_text: str,
    cu_tabs_read: int,
) -> DocComparisonResult:
    """Compare CU extraction against API extraction."""
    api_words = len(api_text.split())
    cu_words = len(cu_text.split())

    word_recall = round(cu_words / api_words, 3) if api_words > 0 else 0.0
    tab_coverage = round(cu_tabs_read / api_total_tabs, 3) if api_total_tabs > 0 else 0.0

    found, total = compute_phrase_recall(api_text, cu_text)
    phrase_recall = round(found / total, 3) if total > 0 else 0.0

    if phrase_recall >= 0.8 and word_recall >= 0.7:
        confidence = "HIGH"
    elif phrase_recall >= 0.5 or word_recall >= 0.5:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return DocComparisonResult(
        file_id=file_id,
        title=title,
        api_total_words=api_words,
        api_total_tabs=api_total_tabs,
        cu_total_words=cu_words,
        cu_tabs_read=cu_tabs_read,
        word_recall=word_recall,
        tab_coverage=tab_coverage,
        unique_api_phrases_found_in_cu=found,
        total_api_phrases_checked=total,
        phrase_recall=phrase_recall,
        confidence=confidence,
        method_separation="API=tab-aware-docs-get | CU=accessibility-tree-scroll",
    )


METHOD_SEPARATION_STATEMENT = """
PRODUCTION INGESTION vs COMPUTER-USE FALLBACK

Production method (preferred):
  - Google Docs API with includeTabsContent=true
  - Recursive tab traversal
  - Structured JSON response
  - Complete coverage guaranteed
  - Fast, reliable, scalable

Computer-use fallback (worst-case):
  - Chrome with --force-renderer-accessibility
  - Windows UI Automation / accessibility tree
  - Task Scheduler /IT for interactive session
  - Mouse/keyboard/scrolling
  - Variable coverage depending on document complexity
  - Slow, fragile, single-document-at-a-time
  - Proves system is not helpless without API

These are SEPARATE capabilities:
  - API ingestion is production-preferred
  - CU is emergency fallback
  - Both are proven
  - Neither replaces the other
"""
