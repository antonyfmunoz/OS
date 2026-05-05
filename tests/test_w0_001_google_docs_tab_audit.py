"""Tests for W0-001R Google Docs tab audit module."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.google_docs_tab_audit import (
    DocTabAuditResult,
    TabCoverageStatus,
    TabInfo,
    build_tab_audit_result,
    classify_prior_coverage,
    compute_audit_summary,
    count_body_words,
    extract_tabs_from_doc_json,
    extract_text_from_body,
)


SINGLE_TAB_DOC = {
    "tabs": [
        {
            "tabProperties": {"tabId": "t.abc", "title": "Main"},
            "documentTab": {
                "body": {
                    "content": [
                        {
                            "paragraph": {
                                "elements": [
                                    {"textRun": {"content": "Hello world\n"}}
                                ]
                            }
                        }
                    ]
                }
            },
            "childTabs": [],
        }
    ]
}

MULTI_TAB_DOC = {
    "tabs": [
        {
            "tabProperties": {"tabId": "t.tab1", "title": "Overview"},
            "documentTab": {
                "body": {
                    "content": [
                        {
                            "paragraph": {
                                "elements": [
                                    {"textRun": {"content": "Tab one content here\n"}}
                                ]
                            }
                        }
                    ]
                }
            },
            "childTabs": [
                {
                    "tabProperties": {"tabId": "t.child1", "title": "Details"},
                    "documentTab": {
                        "body": {
                            "content": [
                                {
                                    "paragraph": {
                                        "elements": [
                                            {"textRun": {"content": "Child tab content with more words\n"}}
                                        ]
                                    }
                                }
                            ]
                        }
                    },
                    "childTabs": [],
                }
            ],
        },
        {
            "tabProperties": {"tabId": "t.tab2", "title": "Notes"},
            "documentTab": {
                "body": {
                    "content": [
                        {
                            "paragraph": {
                                "elements": [
                                    {"textRun": {"content": "Second tab notes\n"}}
                                ]
                            }
                        }
                    ]
                }
            },
            "childTabs": [],
        },
    ]
}


class TestClassifyPriorCoverage:
    def test_single_tab_is_complete(self) -> None:
        assert classify_prior_coverage(1) == TabCoverageStatus.COMPLETE_SINGLE_TAB

    def test_multi_tab_is_first_only(self) -> None:
        assert classify_prior_coverage(3) == TabCoverageStatus.FIRST_TAB_ONLY

    def test_zero_tabs(self) -> None:
        assert classify_prior_coverage(0) == TabCoverageStatus.COMPLETE_SINGLE_TAB


class TestExtractTextFromBody:
    def test_extracts_paragraph_text(self) -> None:
        body = {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Hello world\n"}}
                        ]
                    }
                }
            ]
        }
        assert extract_text_from_body(body) == "Hello world\n"

    def test_extracts_table_text(self) -> None:
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
                                                    "elements": [
                                                        {"textRun": {"content": "cell1\n"}}
                                                    ]
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
        assert "cell1" in extract_text_from_body(body)

    def test_empty_body(self) -> None:
        assert extract_text_from_body({}) == ""
        assert extract_text_from_body({"content": []}) == ""


class TestCountBodyWords:
    def test_counts_words(self) -> None:
        body = {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "one two three four\n"}}
                        ]
                    }
                }
            ]
        }
        assert count_body_words(body) == 4

    def test_empty_is_zero(self) -> None:
        assert count_body_words({}) == 0


class TestExtractTabsFromDocJson:
    def test_single_tab(self) -> None:
        tabs = extract_tabs_from_doc_json(SINGLE_TAB_DOC)
        assert len(tabs) == 1
        assert tabs[0].title == "Main"
        assert tabs[0].tab_id == "t.abc"
        assert tabs[0].word_count == 2

    def test_multi_tab_with_children(self) -> None:
        tabs = extract_tabs_from_doc_json(MULTI_TAB_DOC)
        assert len(tabs) == 3
        assert tabs[0].title == "Overview"
        assert tabs[1].title == "Details"
        assert tabs[1].depth == 1
        assert tabs[2].title == "Notes"
        assert tabs[2].depth == 0

    def test_no_tabs_field(self) -> None:
        tabs = extract_tabs_from_doc_json({"body": {}})
        assert tabs == []


class TestBuildTabAuditResult:
    def test_single_tab_result(self) -> None:
        result = build_tab_audit_result("id1", "Test Doc", SINGLE_TAB_DOC)
        assert result.total_tabs == 1
        assert result.is_multi_tab is False
        assert result.prior_coverage == TabCoverageStatus.COMPLETE_SINGLE_TAB

    def test_multi_tab_result(self) -> None:
        result = build_tab_audit_result("id2", "Multi Doc", MULTI_TAB_DOC)
        assert result.total_tabs == 3
        assert result.is_multi_tab is True
        assert result.prior_coverage == TabCoverageStatus.FIRST_TAB_ONLY
        assert result.first_tab_words == 4
        assert result.total_words_all_tabs > result.first_tab_words

    def test_to_dict(self) -> None:
        result = build_tab_audit_result("id1", "Test", SINGLE_TAB_DOC)
        d = result.to_dict()
        assert d["file_id"] == "id1"
        assert d["prior_coverage"] == "complete_single_tab"


class TestComputeAuditSummary:
    def test_summary_with_mixed_docs(self) -> None:
        r1 = build_tab_audit_result("id1", "Single", SINGLE_TAB_DOC)
        r2 = build_tab_audit_result("id2", "Multi", MULTI_TAB_DOC)
        summary = compute_audit_summary([r1, r2])
        assert summary["total_docs"] == 2
        assert summary["multi_tab_docs"] == 1
        assert summary["single_tab_docs"] == 1
        assert summary["first_tab_only_risk"] == 1
        assert summary["prior_coverage_pct"] < 100.0

    def test_empty_list(self) -> None:
        summary = compute_audit_summary([])
        assert summary["total_docs"] == 0
        assert summary["prior_coverage_pct"] == 100.0
