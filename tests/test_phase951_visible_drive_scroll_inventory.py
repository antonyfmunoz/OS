"""Tests for Phase 95.1 — Visible Drive Scroll Inventory."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.local_gui_control_contracts import (
    GUIInventoryItem,
    GUIObservationMethod,
)
from eos_ai.substrate.visible_drive_ui_inventory import (
    build_complete_cu_inventory,
    build_scroll_action,
    capture_visible_drive_rows_from_accessibility_tree,
    detect_new_items,
    extract_drive_item_from_row,
    mark_inventory_incomplete,
    should_continue_scrolling,
)


SAMPLE_ACCESSIBILITY_OUTPUT = """FILE: AI Agents Google Docs Modified Aug 26, 2025 me More actions (Alt+A)
FILE: AI Tools Google Docs Modified Mar 18 me More actions (Alt+A)
FILE: UMH Google Docs Modified May 3 me More actions (Alt+A)
FILE: LYFEOS_Product_Development_Roadmap.docx Microsoft Word Modified Feb 1 me More actions (Alt+A)
"""


class TestCaptureRows:
    def test_extracts_items_from_accessibility_output(self) -> None:
        rows = capture_visible_drive_rows_from_accessibility_tree(SAMPLE_ACCESSIBILITY_OUTPUT)
        assert len(rows) == 4

    def test_extracts_name(self) -> None:
        rows = capture_visible_drive_rows_from_accessibility_tree(SAMPLE_ACCESSIBILITY_OUTPUT)
        names = [r["name"] for r in rows]
        assert "AI Agents" in names
        assert "UMH" in names

    def test_extracts_type(self) -> None:
        rows = capture_visible_drive_rows_from_accessibility_tree(SAMPLE_ACCESSIBILITY_OUTPUT)
        types = [r["type_label"] for r in rows]
        assert "Google Docs" in types
        assert "Microsoft Word" in types

    def test_extracts_date(self) -> None:
        rows = capture_visible_drive_rows_from_accessibility_tree(SAMPLE_ACCESSIBILITY_OUTPUT)
        dates = [r["modified"] for r in rows]
        assert "Aug 26, 2025" in dates
        assert "Mar 18" in dates

    def test_handles_empty_input(self) -> None:
        rows = capture_visible_drive_rows_from_accessibility_tree("")
        assert rows == []


class TestExtractDriveItem:
    def test_creates_inventory_item(self) -> None:
        row = {"name": "UMH", "type_label": "Google Docs", "modified": "May 3"}
        item = extract_drive_item_from_row(row)
        assert item.name == "UMH"
        assert item.item_type == "application/vnd.google-apps.document"
        assert item.modified_date == "May 3"

    def test_word_doc_type(self) -> None:
        row = {"name": "Roadmap.docx", "type_label": "Microsoft Word", "modified": "Feb 1"}
        item = extract_drive_item_from_row(row)
        assert "wordprocessing" in item.item_type


class TestDetectNewItems:
    def test_finds_new_items(self) -> None:
        prev = [GUIInventoryItem(name="A", modified_date="Jan 1", row_index=0)]
        curr = [
            GUIInventoryItem(name="A", modified_date="Jan 1", row_index=0),
            GUIInventoryItem(name="B", modified_date="Feb 1", row_index=1),
        ]
        new = detect_new_items(prev, curr)
        assert len(new) == 1
        assert new[0].name == "B"

    def test_no_new_items(self) -> None:
        items = [GUIInventoryItem(name="A", modified_date="Jan 1", row_index=0)]
        new = detect_new_items(items, items)
        assert new == []

    def test_handles_same_name_different_date(self) -> None:
        prev = [GUIInventoryItem(name="Untitled", modified_date="Jan 1", row_index=0)]
        curr = [
            GUIInventoryItem(name="Untitled", modified_date="Jan 1", row_index=0),
            GUIInventoryItem(name="Untitled", modified_date="Feb 1", row_index=1),
        ]
        new = detect_new_items(prev, curr)
        assert len(new) == 1


class TestShouldContinueScrolling:
    def test_stops_after_max_scrolls(self) -> None:
        history = [1, 2, 1, 1, 1, 1, 1, 1, 1, 1]
        assert should_continue_scrolling(history, max_scrolls=10) is False

    def test_stops_after_no_new_items(self) -> None:
        history = [5, 3, 2, 0, 0, 0]
        assert should_continue_scrolling(history, no_new_item_limit=3) is False

    def test_continues_when_finding_items(self) -> None:
        history = [5, 3, 2, 1]
        assert should_continue_scrolling(history) is True

    def test_continues_when_just_started(self) -> None:
        history = [5]
        assert should_continue_scrolling(history) is True

    def test_continues_with_intermittent_zeros(self) -> None:
        history = [5, 0, 3, 0, 2]
        assert should_continue_scrolling(history, no_new_item_limit=3) is True


class TestBuildScrollAction:
    def test_default_down_page(self) -> None:
        action = build_scroll_action()
        assert action["direction"] == "down"
        assert action["amount"] == "page"

    def test_custom_direction(self) -> None:
        action = build_scroll_action(direction="up", amount="line")
        assert action["direction"] == "up"
        assert action["amount"] == "line"


class TestBuildCompleteInventory:
    def test_marks_complete_at_baseline(self) -> None:
        items = [GUIInventoryItem(name=f"file{i}", row_index=i) for i in range(29)]
        result = build_complete_cu_inventory(items, GUIObservationMethod.WINDOWS_UI_AUTOMATION, 3, baseline_count=29)
        assert result["completeness"] == "COMPLETE"
        assert result["recall_vs_baseline"] == 1.0

    def test_marks_partial_below_baseline(self) -> None:
        items = [GUIInventoryItem(name=f"file{i}", row_index=i) for i in range(20)]
        result = build_complete_cu_inventory(items, GUIObservationMethod.WINDOWS_UI_AUTOMATION, 5, baseline_count=29)
        assert result["completeness"] == "PARTIAL"
        assert result["recall_vs_baseline"] < 1.0

    def test_never_emits_document_open(self) -> None:
        items = [GUIInventoryItem(name="test", row_index=0)]
        result = build_complete_cu_inventory(items, GUIObservationMethod.WINDOWS_UI_AUTOMATION, 0)
        assert result["document_content_read"] is False
        assert result["api_used"] is False


class TestMarkIncomplete:
    def test_records_reason(self) -> None:
        result = mark_inventory_incomplete(26, 29, "3 items below scroll fold")
        assert result["status"] == "INCOMPLETE"
        assert result["current_count"] == 26
        assert result["baseline_count"] == 29
        assert "below scroll fold" in result["reason"]

    def test_computes_recall(self) -> None:
        result = mark_inventory_incomplete(26, 29, "test")
        assert 0.89 <= result["recall"] <= 0.90
