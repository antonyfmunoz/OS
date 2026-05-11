"""
Extraction parity comparator for Phase 96.0.

Compares extraction outputs across backends (API, CLI, Computer Use)
to measure parity: same tabs, same text, same coverage.

Initial parity thresholds:
- Metadata parity: 100%
- Tab discovery parity: 100%
- Text extraction recall: 95%+ for CU MVP, 99%+ for production
- False positive content: near 0%
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from eos_ai.transport.canonical_source_record import DocumentSourceRecord, TabSourceRecord
from eos_ai.transport.extraction_backend_contracts import (
    ExtractionBackendType,
    ExtractionCoverageStatus,
)


PARITY_THRESHOLD_TAB_DISCOVERY = 1.0
PARITY_THRESHOLD_TEXT_RECALL_MVP = 0.95
PARITY_THRESHOLD_TEXT_RECALL_PRODUCTION = 0.99
PARITY_THRESHOLD_FALSE_POSITIVE = 0.01


@dataclass
class TabParityResult:
    """Parity comparison for tab discovery."""

    reference_tab_count: int
    candidate_tab_count: int
    matched_tabs: int
    missing_tabs: list[str] = field(default_factory=list)
    extra_tabs: list[str] = field(default_factory=list)
    tab_recall: float = 0.0
    tab_precision: float = 0.0
    parity_pass: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_tab_count": self.reference_tab_count,
            "candidate_tab_count": self.candidate_tab_count,
            "matched_tabs": self.matched_tabs,
            "missing_tabs": self.missing_tabs,
            "extra_tabs": self.extra_tabs,
            "tab_recall": self.tab_recall,
            "tab_precision": self.tab_precision,
            "parity_pass": self.parity_pass,
        }


@dataclass
class TextParityResult:
    """Parity comparison for text content."""

    reference_word_count: int
    candidate_word_count: int
    word_recall: float = 0.0
    word_precision: float = 0.0
    phrase_recall: float = 0.0
    missing_text_sections: list[str] = field(default_factory=list)
    parity_pass: bool = False
    threshold_used: float = PARITY_THRESHOLD_TEXT_RECALL_MVP

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_word_count": self.reference_word_count,
            "candidate_word_count": self.candidate_word_count,
            "word_recall": self.word_recall,
            "word_precision": self.word_precision,
            "phrase_recall": self.phrase_recall,
            "missing_text_sections": self.missing_text_sections,
            "parity_pass": self.parity_pass,
            "threshold_used": self.threshold_used,
        }


@dataclass
class ParityReport:
    """Full parity report between two backend extraction records."""

    reference_backend: ExtractionBackendType
    candidate_backend: ExtractionBackendType
    document_count_match: bool = False
    tab_parity: TabParityResult | None = None
    text_parity: TextParityResult | None = None
    overall_parity_pass: bool = False
    parity_grade: str = "FAIL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_backend": self.reference_backend.value,
            "candidate_backend": self.candidate_backend.value,
            "document_count_match": self.document_count_match,
            "tab_parity": self.tab_parity.to_dict() if self.tab_parity else None,
            "text_parity": self.text_parity.to_dict() if self.text_parity else None,
            "overall_parity_pass": self.overall_parity_pass,
            "parity_grade": self.parity_grade,
        }


def _normalize(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def compare_tab_coverage(
    reference: DocumentSourceRecord,
    candidate: DocumentSourceRecord,
) -> TabParityResult:
    """Compare tab discovery between two records."""
    ref_tabs = {t.tab_id: t.tab_title for t in reference.tabs}
    cand_tabs = {t.tab_id: t.tab_title for t in candidate.tabs}

    ref_ids = set(ref_tabs.keys())
    cand_ids = set(cand_tabs.keys())

    matched = ref_ids & cand_ids
    missing = ref_ids - cand_ids
    extra = cand_ids - ref_ids

    ref_count = len(ref_ids)
    recall = len(matched) / ref_count if ref_count > 0 else 1.0
    precision = len(matched) / len(cand_ids) if cand_ids else 1.0

    return TabParityResult(
        reference_tab_count=ref_count,
        candidate_tab_count=len(cand_ids),
        matched_tabs=len(matched),
        missing_tabs=[ref_tabs[tid] for tid in missing],
        extra_tabs=[cand_tabs[tid] for tid in extra],
        tab_recall=round(recall, 4),
        tab_precision=round(precision, 4),
        parity_pass=recall >= PARITY_THRESHOLD_TAB_DISCOVERY,
    )


def compare_text_coverage(
    reference: DocumentSourceRecord,
    candidate: DocumentSourceRecord,
    threshold: float = PARITY_THRESHOLD_TEXT_RECALL_MVP,
) -> TextParityResult:
    """Compare text content coverage between two records."""
    ref_words = reference.total_words
    cand_words = candidate.total_words

    word_recall = cand_words / ref_words if ref_words > 0 else 1.0
    word_precision = min(ref_words, cand_words) / cand_words if cand_words > 0 else 1.0

    ref_text = " ".join(t.text_content for t in reference.tabs)
    cand_text = " ".join(t.text_content for t in candidate.tabs)
    phrase_recall = compute_word_recall(ref_text, cand_text)

    missing_sections: list[str] = []
    for ref_tab in reference.tabs:
        cand_tab = next((t for t in candidate.tabs if t.tab_id == ref_tab.tab_id), None)
        if cand_tab is None:
            missing_sections.append(f"tab:{ref_tab.tab_title}")
        elif cand_tab.word_count == 0 and ref_tab.word_count > 0:
            missing_sections.append(f"content:{ref_tab.tab_title} ({ref_tab.word_count} words)")

    return TextParityResult(
        reference_word_count=ref_words,
        candidate_word_count=cand_words,
        word_recall=round(word_recall, 4),
        word_precision=round(word_precision, 4),
        phrase_recall=round(phrase_recall, 4),
        missing_text_sections=missing_sections,
        parity_pass=word_recall >= threshold and phrase_recall >= threshold,
        threshold_used=threshold,
    )


def compute_word_recall(reference_text: str, candidate_text: str) -> float:
    """Compute word-level recall of candidate against reference."""
    ref_normalized = _normalize(reference_text)
    cand_normalized = _normalize(candidate_text)

    if not ref_normalized:
        return 1.0

    ref_words = set(ref_normalized.split())
    cand_words = set(cand_normalized.split())

    if not ref_words:
        return 1.0

    found = ref_words & cand_words
    return len(found) / len(ref_words)


def compute_tab_recall(
    reference_tabs: list[TabSourceRecord],
    candidate_tabs: list[TabSourceRecord],
) -> float:
    """Compute tab-level recall."""
    if not reference_tabs:
        return 1.0
    ref_ids = {t.tab_id for t in reference_tabs}
    cand_ids = {t.tab_id for t in candidate_tabs}
    found = ref_ids & cand_ids
    return len(found) / len(ref_ids)


def compute_precision(
    reference_tabs: list[TabSourceRecord],
    candidate_tabs: list[TabSourceRecord],
) -> float:
    """Compute tab-level precision (no false positives)."""
    if not candidate_tabs:
        return 1.0
    ref_ids = {t.tab_id for t in reference_tabs}
    cand_ids = {t.tab_id for t in candidate_tabs}
    correct = ref_ids & cand_ids
    return len(correct) / len(cand_ids)


def identify_missing_tabs(
    reference: DocumentSourceRecord,
    candidate: DocumentSourceRecord,
) -> list[str]:
    """Identify tabs present in reference but missing from candidate."""
    ref_ids = {t.tab_id for t in reference.tabs}
    cand_ids = {t.tab_id for t in candidate.tabs}
    missing_ids = ref_ids - cand_ids
    return [t.tab_title for t in reference.tabs if t.tab_id in missing_ids]


def identify_missing_text_sections(
    reference: DocumentSourceRecord,
    candidate: DocumentSourceRecord,
) -> list[str]:
    """Identify tabs where candidate has significantly less text."""
    missing: list[str] = []
    for ref_tab in reference.tabs:
        cand_tab = next((t for t in candidate.tabs if t.tab_id == ref_tab.tab_id), None)
        if cand_tab is None:
            missing.append(f"{ref_tab.tab_title} (entire tab missing)")
        elif ref_tab.word_count > 0:
            ratio = cand_tab.word_count / ref_tab.word_count
            if ratio < 0.5:
                missing.append(
                    f"{ref_tab.tab_title} (ref={ref_tab.word_count}w, cand={cand_tab.word_count}w, {ratio:.0%})"
                )
    return missing


def compare_document_records(
    api_record: DocumentSourceRecord,
    cu_record: DocumentSourceRecord,
) -> ParityReport:
    """Full parity comparison between two extraction records."""
    tab_parity = compare_tab_coverage(api_record, cu_record)
    text_parity = compare_text_coverage(api_record, cu_record)

    overall = tab_parity.parity_pass and text_parity.parity_pass

    if overall:
        grade = "PASS"
    elif tab_parity.parity_pass and text_parity.word_recall >= 0.8:
        grade = "NEAR_PARITY"
    elif tab_parity.parity_pass:
        grade = "TAB_PARITY_ONLY"
    else:
        grade = "FAIL"

    return ParityReport(
        reference_backend=api_record.backend_type,
        candidate_backend=cu_record.backend_type,
        document_count_match=True,
        tab_parity=tab_parity,
        text_parity=text_parity,
        overall_parity_pass=overall,
        parity_grade=grade,
    )


def build_parity_report(
    reference_backend: ExtractionBackendType,
    candidate_backend: ExtractionBackendType,
    reference_records: list[DocumentSourceRecord],
    candidate_records: list[DocumentSourceRecord],
) -> dict[str, Any]:
    """Build a multi-document parity report between two backends."""
    ref_by_id = {r.file_id: r for r in reference_records}
    cand_by_id = {r.file_id: r for r in candidate_records}

    doc_count_match = len(reference_records) == len(candidate_records)
    matched_ids = set(ref_by_id.keys()) & set(cand_by_id.keys())

    per_doc_results: list[dict[str, Any]] = []
    for fid in matched_ids:
        report = compare_document_records(ref_by_id[fid], cand_by_id[fid])
        per_doc_results.append(
            {
                "file_id": fid,
                "title": ref_by_id[fid].title,
                "parity": report.to_dict(),
            }
        )

    pass_count = sum(1 for r in per_doc_results if r["parity"]["overall_parity_pass"])

    return {
        "reference_backend": reference_backend.value,
        "candidate_backend": candidate_backend.value,
        "total_reference_docs": len(reference_records),
        "total_candidate_docs": len(candidate_records),
        "document_count_match": doc_count_match,
        "matched_documents": len(matched_ids),
        "parity_pass_count": pass_count,
        "parity_fail_count": len(matched_ids) - pass_count,
        "overall_parity_rate": round(pass_count / len(matched_ids), 3) if matched_ids else 0.0,
        "per_document_results": per_doc_results,
    }
