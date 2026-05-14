"""Tests for Phase 95.0 — Visible Drive UI Inventory."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.local_gui_control_contracts import (
    GUIInventoryItem,
    GUIObservationMethod,
)
from runtime.substrate.visible_drive_ui_inventory import (
    build_inventory_result,
    build_scroll_plan,
    dedupe_inventory_items,
    detect_end_of_drive_list,
    extract_file_name_from_visible_row,
    extract_modified_date_from_visible_row,
    infer_file_type_from_visible_row,
    normalize_visible_drive_row,
    parse_ui_automation_output,
    validate_inventory_scope,
)


class TestNormalize:
    def test_strips_whitespace(self) -> None:
        assert normalize_visible_drive_row("  hello  ") == "hello"

    def test_collapses_spaces(self) -> None:
        assert normalize_visible_drive_row("file   name   here") == "file name here"

    def test_removes_control_chars(self) -> None:
        assert normalize_visible_drive_row("file\x00name") == "filename"


class TestExtractFileName:
    def test_tab_separated(self) -> None:
        row = "UMH\tGoogle Docs\tMay 4, 2026\tme"
        assert extract_file_name_from_visible_row(row) == "UMH"

    def test_double_space_separated(self) -> None:
        row = "EntrepreneurOS  Google Docs  Apr 6, 2026"
        assert extract_file_name_from_visible_row(row) == "EntrepreneurOS"

    def test_plain_text(self) -> None:
        row = "AI Tools"
        assert extract_file_name_from_visible_row(row) == "AI Tools"

    def test_empty(self) -> None:
        assert extract_file_name_from_visible_row("") == ""

    def test_dash_separated(self) -> None:
        row = "AI Tools — Google Docs"
        assert extract_file_name_from_visible_row(row) == "AI Tools"


class TestExtractDate:
    def test_full_date(self) -> None:
        row = "UMH  Google Docs  May 4, 2026"
        assert extract_modified_date_from_visible_row(row) == "May 4, 2026"

    def test_iso_date(self) -> None:
        row = "file\t2026-05-04\tme"
        assert extract_modified_date_from_visible_row(row) == "2026-05-04"

    def test_slash_date(self) -> None:
        row = "file  5/4/2026"
        assert extract_modified_date_from_visible_row(row) == "5/4/2026"

    def test_relative_date(self) -> None:
        row = "file  today"
        assert extract_modified_date_from_visible_row(row).lower() == "today"

    def test_no_date(self) -> None:
        assert extract_modified_date_from_visible_row("just a filename") == ""


class TestInferFileType:
    def test_google_docs(self) -> None:
        row = "UMH  Google Docs  May 4"
        mime = infer_file_type_from_visible_row(row)
        assert mime == "application/vnd.google-apps.document"

    def test_folder(self) -> None:
        row = "Projects  Folder"
        mime = infer_file_type_from_visible_row(row)
        assert mime == "application/vnd.google-apps.folder"

    def test_docx_extension(self) -> None:
        row = "LYFEOS_Product_Development_Roadmap.docx"
        mime = infer_file_type_from_visible_row(row)
        assert "wordprocessing" in mime

    def test_sheets(self) -> None:
        row = "Budget  Google Sheets  Jan 2026"
        mime = infer_file_type_from_visible_row(row)
        assert "spreadsheet" in mime

    def test_default_to_doc(self) -> None:
        row = "Untitled document"
        mime = infer_file_type_from_visible_row(row)
        assert "document" in mime


class TestDedupe:
    def test_removes_duplicates(self) -> None:
        items = [
            GUIInventoryItem(name="UMH", row_index=0),
            GUIInventoryItem(name="UMH", row_index=5),
            GUIInventoryItem(name="AI Tools", row_index=1),
        ]
        result = dedupe_inventory_items(items)
        assert len(result) == 2

    def test_case_insensitive(self) -> None:
        items = [
            GUIInventoryItem(name="UMH", row_index=0),
            GUIInventoryItem(name="umh", row_index=1),
        ]
        result = dedupe_inventory_items(items)
        assert len(result) == 1

    def test_empty_names_skipped(self) -> None:
        items = [
            GUIInventoryItem(name="", row_index=0),
            GUIInventoryItem(name="UMH", row_index=1),
        ]
        result = dedupe_inventory_items(items)
        assert len(result) == 1
        assert result[0].name == "UMH"


class TestEndOfList:
    def test_detects_stable_observations(self) -> None:
        history = [
            ["file1", "file2"],
            ["file3", "file4"],
            ["file3", "file4"],
            ["file3", "file4"],
        ]
        assert detect_end_of_drive_list(history) is True

    def test_not_stable_yet(self) -> None:
        history = [
            ["file1", "file2"],
            ["file3", "file4"],
        ]
        assert detect_end_of_drive_list(history) is False

    def test_changing_content(self) -> None:
        history = [
            ["file1"],
            ["file2"],
            ["file3"],
            ["file4"],
        ]
        assert detect_end_of_drive_list(history) is False


class TestScrollPlan:
    def test_builds_plan(self) -> None:
        plan = build_scroll_plan(max_scrolls=3)
        assert plan[0]["action"] == "observe"
        assert any(s["action"] == "scroll_down" for s in plan)
        assert len(plan) == 7  # 1 initial + 3*(scroll+observe)

    def test_respects_max(self) -> None:
        plan = build_scroll_plan(max_scrolls=1)
        scroll_steps = [s for s in plan if s["action"] == "scroll_down"]
        assert len(scroll_steps) == 1


class TestValidateScope:
    def test_drive_allowed(self) -> None:
        assert validate_inventory_scope("Google Drive - My Drive") == []

    def test_gmail_blocked(self) -> None:
        errors = validate_inventory_scope("Gmail inbox")
        assert len(errors) > 0

    def test_document_body_blocked(self) -> None:
        errors = validate_inventory_scope("document_body reading")
        assert len(errors) > 0

    def test_non_drive_rejected(self) -> None:
        errors = validate_inventory_scope("random page")
        assert any("drive" in e.lower() for e in errors)


class TestInventoryResult:
    def test_builds_result(self) -> None:
        items = [
            GUIInventoryItem(name="UMH", item_type="doc", row_index=0),
            GUIInventoryItem(name="AI Tools", item_type="doc", row_index=1),
        ]
        result = build_inventory_result(items, GUIObservationMethod.WINDOWS_UI_AUTOMATION)
        assert result["total_items"] == 2
        assert result["method"] == "COMPUTER_USE_ONLY"
        assert result["api_used"] is False
        assert result["playwright_used"] is False
        assert result["cdp_used"] is False

    def test_dedupes_in_result(self) -> None:
        items = [
            GUIInventoryItem(name="UMH", row_index=0),
            GUIInventoryItem(name="UMH", row_index=5),
        ]
        result = build_inventory_result(items, GUIObservationMethod.WINDOWS_UI_AUTOMATION)
        assert result["total_items"] == 1
