"""GWS Scanner Bridge v1 — translates existing scanner outputs into substrate ingestion contracts.

Takes canonical source records + raw API extractions already produced by gws_scanner.py
and emits normalized documents ready for primitive decomposition.

This is a translation layer only. It does NOT re-extract or re-scan.

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class NormalizedTab:
    """A single tab's extracted text with provenance."""

    tab_id: str
    tab_title: str
    tab_order: int
    text: str
    word_count: int
    character_count: int


@dataclass
class NormalizedDocument:
    """A fully normalized document ready for primitive decomposition."""

    document_id: str
    trace_id: str
    title: str
    file_id: str
    source_account: str
    extraction_method: str
    extraction_timestamp: str
    content_hash: str
    tabs: list[NormalizedTab] = field(default_factory=list)
    full_text: str = ""
    total_words: int = 0
    total_characters: int = 0
    provenance: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "trace_id": self.trace_id,
            "title": self.title,
            "file_id": self.file_id,
            "source_account": self.source_account,
            "extraction_method": self.extraction_method,
            "extraction_timestamp": self.extraction_timestamp,
            "content_hash": self.content_hash,
            "tabs": [
                {
                    "tab_id": t.tab_id,
                    "tab_title": t.tab_title,
                    "tab_order": t.tab_order,
                    "text": t.text,
                    "word_count": t.word_count,
                    "character_count": t.character_count,
                }
                for t in self.tabs
            ],
            "full_text": self.full_text,
            "total_words": self.total_words,
            "total_characters": self.total_characters,
            "provenance": self.provenance,
            "metadata": self.metadata,
        }


def _extract_text_from_google_doc_body(body: dict[str, Any]) -> str:
    """Extract plain text from Google Docs API body structure."""
    parts: list[str] = []
    for elem in body.get("content", []):
        if "paragraph" in elem:
            for pel in elem["paragraph"].get("elements", []):
                if "textRun" in pel:
                    parts.append(pel["textRun"]["content"])
        elif "table" in elem:
            for row in elem["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    cell_text = _extract_text_from_google_doc_body(cell)
                    if cell_text.strip():
                        parts.append(cell_text)
    return "".join(parts)


def _compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_from_scanner_outputs(
    canonical_record_path: str | Path,
    raw_extraction_path: str | Path,
) -> NormalizedDocument:
    """Bridge scanner outputs into a NormalizedDocument for substrate ingestion.

    Args:
        canonical_record_path: Path to canonical source record JSON
        raw_extraction_path: Path to raw Google Docs API extraction JSON

    Returns:
        NormalizedDocument ready for primitive decomposition
    """
    canonical_record_path = Path(canonical_record_path)
    raw_extraction_path = Path(raw_extraction_path)

    with open(canonical_record_path) as f:
        canonical = json.load(f)

    with open(raw_extraction_path) as f:
        raw = json.load(f)

    trace_id = f"trace-{uuid.uuid4().hex[:12]}"
    document_id = f"doc-{canonical['file_id'][:16]}"

    tabs: list[NormalizedTab] = []
    all_text_parts: list[str] = []

    for raw_tab in raw.get("tabs", []):
        tab_props = raw_tab.get("tabProperties", {})
        tab_id = tab_props.get("tabId", f"t.{len(tabs)}")
        tab_title = tab_props.get("title", f"Tab {len(tabs) + 1}")

        doc_tab = raw_tab.get("documentTab", {})
        body = doc_tab.get("body", {})
        text = _extract_text_from_google_doc_body(body)

        words = text.split()
        nt = NormalizedTab(
            tab_id=tab_id,
            tab_title=tab_title,
            tab_order=len(tabs),
            text=text,
            word_count=len(words),
            character_count=len(text),
        )
        tabs.append(nt)
        all_text_parts.append(f"[Tab: {tab_title}]\n{text}")

    full_text = "\n\n".join(all_text_parts)
    content_hash = _compute_content_hash(full_text)

    return NormalizedDocument(
        document_id=document_id,
        trace_id=trace_id,
        title=canonical.get("title", raw.get("title", "Untitled")),
        file_id=canonical["file_id"],
        source_account=canonical.get("source_account", ""),
        extraction_method=canonical.get("extraction_method", "unknown"),
        extraction_timestamp=canonical.get("extraction_timestamp", ""),
        content_hash=content_hash,
        tabs=tabs,
        full_text=full_text,
        total_words=sum(t.word_count for t in tabs),
        total_characters=sum(t.character_count for t in tabs),
        provenance=canonical.get("provenance", {}),
        metadata={
            "canonical_record_path": str(canonical_record_path),
            "raw_extraction_path": str(raw_extraction_path),
            "bridge_version": "gws_scanner_bridge_v1",
            "bridge_timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
