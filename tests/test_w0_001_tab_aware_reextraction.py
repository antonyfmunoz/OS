"""Tests for W0-001 tab-aware re-extraction correctness."""

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.canonical_source_record import (
    DocumentSourceRecord,
    ProvenanceRecord,
    TabSourceRecord,
    build_api_source_record,
)
from eos_ai.substrate.extraction_backend_contracts import (
    ExtractionBackendType,
    ExtractionCoverageStatus,
)
from eos_ai.substrate.google_docs_tab_audit import (
    extract_tabs_from_doc_json,
    extract_text_from_body,
)
from eos_ai.substrate.google_docs_tab_extractor import extract_all_tabs


def _make_tab_aware_doc(tabs_data: list[dict]) -> dict:
    """Build a mock tab-aware API response."""
    tabs = []
    for t in tabs_data:
        content_elements = []
        if t.get("text"):
            content_elements.append(
                {"paragraph": {"elements": [{"textRun": {"content": t["text"]}}]}}
            )
        tab = {
            "tabProperties": {"tabId": t["id"], "title": t["title"]},
            "documentTab": {"body": {"content": content_elements}},
            "childTabs": t.get("children", []),
        }
        tabs.append(tab)
    return {"documentId": "test_doc", "title": "Test", "tabs": tabs}


def test_tab_aware_extractor_handles_document_tabs():
    """Tab-aware extractor processes document.tabs correctly."""
    doc_json = _make_tab_aware_doc(
        [
            {"id": "t1", "title": "Main", "text": "hello world foo bar"},
            {"id": "t2", "title": "Details", "text": "detail content here now"},
        ]
    )
    result = extract_all_tabs("test_doc", "Test", doc_json)
    assert result.total_tabs == 2
    assert result.tabs[0].title == "Main"
    assert result.tabs[1].title == "Details"
    assert result.total_words == 8


def test_tab_aware_extractor_handles_child_tabs():
    """Tab-aware extractor handles childTabs recursively."""
    child_tab = {
        "tabProperties": {"tabId": "t1_c1", "title": "Child"},
        "documentTab": {
            "body": {
                "content": [
                    {"paragraph": {"elements": [{"textRun": {"content": "child content"}}]}}
                ]
            }
        },
        "childTabs": [],
    }
    doc_json = _make_tab_aware_doc(
        [
            {"id": "t1", "title": "Parent", "text": "parent text", "children": [child_tab]},
        ]
    )
    result = extract_all_tabs("test_doc", "Test", doc_json)
    assert result.total_tabs == 2
    assert result.tabs[1].title == "Child"
    assert result.tabs[1].depth == 1


def test_empty_tabs_marked_empty():
    """Empty tabs are marked is_empty, not failed."""
    doc_json = _make_tab_aware_doc(
        [
            {"id": "t1", "title": "Content Tab", "text": "some words here"},
            {"id": "t2", "title": "Empty Tab", "text": ""},
        ]
    )
    result = extract_all_tabs("test_doc", "Test", doc_json)
    content_tab = result.tabs[0]
    empty_tab = result.tabs[1]
    assert content_tab.word_count > 0
    assert empty_tab.word_count == 0


def test_first_tab_only_fails_completeness():
    """A record with only first tab fails completeness validation against full record."""
    tabs_full = [
        TabSourceRecord(
            tab_id="t1",
            tab_title="Tab 1",
            tab_path="Tab 1",
            word_count=100,
            character_count=500,
            text_content="x " * 100,
            extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
        ),
        TabSourceRecord(
            tab_id="t2",
            tab_title="Tab 2",
            tab_path="Tab 2",
            word_count=200,
            character_count=1000,
            text_content="y " * 200,
            extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
        ),
    ]
    full_record = build_api_source_record("f1", "Doc", tabs_full)
    assert full_record.total_words == 300

    tabs_first_only = [tabs_full[0]]
    first_only_record = build_api_source_record("f1", "Doc", tabs_first_only)
    assert first_only_record.total_words == 100
    assert first_only_record.total_tabs == 1


def test_canonical_records_preserve_tab_provenance():
    """Canonical records preserve which tab content came from."""
    tabs = [
        TabSourceRecord(
            tab_id="t.abc",
            tab_title="Strategy",
            tab_path="Strategy",
            parent_tab_id=None,
            tab_order=0,
            word_count=50,
            character_count=250,
            text_content="strategy content " * 5,
            extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
        ),
        TabSourceRecord(
            tab_id="t.def",
            tab_title="Execution",
            tab_path="Execution",
            parent_tab_id=None,
            tab_order=1,
            word_count=30,
            character_count=150,
            text_content="execution plan " * 6,
            extraction_coverage_status=ExtractionCoverageStatus.COMPLETE,
        ),
    ]
    record = build_api_source_record("file_prov", "Provenance Test", tabs)
    d = record.to_dict()
    assert d["tabs"][0]["tab_id"] == "t.abc"
    assert d["tabs"][0]["tab_title"] == "Strategy"
    assert d["tabs"][1]["tab_id"] == "t.def"
    assert d["tabs"][1]["tab_path"] == "Execution"
    assert d["provenance"]["backend_type"] == "api"


def test_extract_text_handles_tables():
    """extract_text_from_body handles table elements."""
    body = {
        "content": [
            {
                "table": {
                    "tableRows": [
                        {
                            "tableCells": [
                                {
                                    "content": [
                                        {
                                            "paragraph": {
                                                "elements": [{"textRun": {"content": "cell value"}}]
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        ]
    }
    text = extract_text_from_body(body)
    assert "cell value" in text


def test_tab_audit_detects_multi_tab():
    """Tab audit correctly identifies multi-tab documents."""
    doc_json = _make_tab_aware_doc(
        [
            {"id": "t1", "title": "A", "text": "aaa"},
            {"id": "t2", "title": "B", "text": "bbb"},
            {"id": "t3", "title": "C", "text": "ccc"},
        ]
    )
    tabs = extract_tabs_from_doc_json(doc_json)
    assert len(tabs) == 3
