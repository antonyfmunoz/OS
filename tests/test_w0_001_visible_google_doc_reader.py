"""Tests for W0-001R visible Google Doc reader module."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.visible_google_doc_reader import (
    BLOCKED_DOC_ACTIONS,
    DocCUReadResult,
    DocReadMethod,
    DocReadStatus,
    DocTabCURead,
    build_cu_vs_api_coverage,
    build_doc_open_command,
    build_doc_scroll_read_script,
    build_doc_tab_detection_script,
    parse_doc_cu_output,
    validate_doc_read_scope,
)


class TestValidateDocReadScope:
    def test_valid_google_doc_url(self) -> None:
        url = "https://docs.google.com/document/d/1abc123/edit"
        assert validate_doc_read_scope(url) == []

    def test_rejects_non_doc_url(self) -> None:
        errors = validate_doc_read_scope("https://gmail.com/inbox")
        assert len(errors) >= 1

    def test_rejects_gmail(self) -> None:
        errors = validate_doc_read_scope("https://mail.google.com/mail/u/0/")
        assert any("Gmail" in e for e in errors)

    def test_rejects_random_url(self) -> None:
        errors = validate_doc_read_scope("https://example.com/page")
        assert len(errors) >= 1


class TestBuildDocOpenCommand:
    def test_includes_file_id(self) -> None:
        cmd = build_doc_open_command("abc123xyz")
        assert "abc123xyz" in cmd

    def test_includes_accessibility_flag(self) -> None:
        cmd = build_doc_open_command("id")
        assert "--force-renderer-accessibility" in cmd

    def test_includes_profile(self) -> None:
        cmd = build_doc_open_command("id", profile_directory="Profile 5")
        assert "Profile 5" in cmd

    def test_opens_edit_url(self) -> None:
        cmd = build_doc_open_command("abc")
        assert "docs.google.com/document/d/abc/edit" in cmd


class TestBuildScripts:
    def test_tab_detection_script_not_empty(self) -> None:
        script = build_doc_tab_detection_script()
        assert "UIAutomationClient" in script
        assert "TabItem" in script

    def test_scroll_read_script_not_empty(self) -> None:
        script = build_doc_scroll_read_script(max_scrolls=10)
        assert "PGDN" in script
        assert "CONTENT_START" in script

    def test_scroll_read_uses_max_scrolls(self) -> None:
        script = build_doc_scroll_read_script(max_scrolls=15)
        assert "15" in script


class TestParseDocCUOutput:
    def test_parses_complete_output(self) -> None:
        raw = """WINDOW: UMH - Google Docs - Google Chrome
TAB_COUNT: 8
INITIAL_TEXT_ELEMENTS: 50
INITIAL_WORD_COUNT: 200
SCROLL_1: 10 new elements
SCROLL_2: 5 new elements
SCROLL_3: 0 new elements (end of content)
TOTAL_SCROLLS: 3
TOTAL_TEXT_ELEMENTS: 65
TOTAL_WORD_COUNT: 350
---CONTENT_START---
Universal Meta Harness
This is the system definition.
More content here with multiple lines.
---CONTENT_END---"""
        result = parse_doc_cu_output(raw)
        assert "UMH" in result.title
        assert result.total_tabs_detected == 8
        assert result.total_words > 0
        assert result.status == DocReadStatus.COMPLETE
        assert len(result.tabs_read) == 1

    def test_parses_error_output(self) -> None:
        raw = "ERROR: No document window found"
        result = parse_doc_cu_output(raw)
        assert result.status == DocReadStatus.PARTIAL
        assert result.total_words == 0


class TestBuildCUvsAPICoverage:
    def test_high_coverage(self) -> None:
        result = build_cu_vs_api_coverage(900, 1000, 1, 1)
        assert result["word_recall"] == 0.9
        assert result["confidence"] == "HIGH"

    def test_low_coverage(self) -> None:
        result = build_cu_vs_api_coverage(100, 1000, 1, 8)
        assert result["word_recall"] == 0.1
        assert result["tab_coverage"] == 0.125
        assert result["confidence"] == "LOW"

    def test_zero_api_words(self) -> None:
        result = build_cu_vs_api_coverage(0, 0, 0, 0)
        assert result["word_recall"] == 0.0


class TestBlockedActions:
    def test_edit_blocked(self) -> None:
        assert "edit_document" in BLOCKED_DOC_ACTIONS

    def test_delete_blocked(self) -> None:
        assert "delete_document" in BLOCKED_DOC_ACTIONS

    def test_gmail_blocked(self) -> None:
        assert "open_gmail" in BLOCKED_DOC_ACTIONS

    def test_account_switch_blocked(self) -> None:
        assert "switch_account" in BLOCKED_DOC_ACTIONS
