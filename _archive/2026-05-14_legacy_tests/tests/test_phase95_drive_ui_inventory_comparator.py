"""Tests for Phase 95.0 — Drive UI Inventory Comparator."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.drive_ui_inventory_comparator import (
    build_comparison_report,
    compare_inventories,
    find_name_mismatches,
    normalize_name_for_comparison,
)
from runtime.substrate.local_gui_control_contracts import (
    GUIInventoryItem,
    GUIObservationMethod,
)


def _api_files(names: list[str]) -> list[dict]:
    return [{"name": n, "mimeType": "doc"} for n in names]


def _cu_items(names: list[str]) -> list[GUIInventoryItem]:
    return [GUIInventoryItem(name=n, row_index=i) for i, n in enumerate(names)]


class TestCompareInventories:
    def test_matching_inventories(self) -> None:
        names = ["UMH", "AI Tools", "EntrepreneurOS"]
        result = compare_inventories(_api_files(names), _cu_items(names))
        assert result["matching_count"] == 3
        assert result["missing_from_cu_count"] == 0
        assert result["extra_in_cu_count"] == 0
        assert result["confidence_score"] == 1.0
        assert result["confidence_rating"] == "HIGH"

    def test_missing_item_detected(self) -> None:
        api = _api_files(["UMH", "AI Tools", "LyfeOS"])
        cu = _cu_items(["UMH", "AI Tools"])
        result = compare_inventories(api, cu)
        assert result["missing_from_cu_count"] == 1
        assert "lyfeos" in result["missing_from_cu"]

    def test_extra_item_detected(self) -> None:
        api = _api_files(["UMH", "AI Tools"])
        cu = _cu_items(["UMH", "AI Tools", "New File"])
        result = compare_inventories(api, cu)
        assert result["extra_in_cu_count"] == 1
        assert "new file" in result["extra_in_cu"]

    def test_count_mismatch_detected(self) -> None:
        api = _api_files(["A", "B", "C", "D"])
        cu = _cu_items(["A", "B"])
        result = compare_inventories(api, cu)
        assert result["count_difference"] == -2
        assert result["api_baseline_count"] == 4
        assert result["cu_inventory_count"] == 2

    def test_confidence_score_computed(self) -> None:
        api = _api_files(["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"])
        cu = _cu_items(["A", "B", "C", "D", "E"])
        result = compare_inventories(api, cu)
        assert 0.0 < result["confidence_score"] < 1.0
        assert result["confidence_rating"] in ("LOW", "MEDIUM")

    def test_empty_both(self) -> None:
        result = compare_inventories([], [])
        assert result["confidence_score"] == 1.0

    def test_case_insensitive_matching(self) -> None:
        api = _api_files(["UMH", "AI Tools"])
        cu = _cu_items(["umh", "ai tools"])
        result = compare_inventories(api, cu)
        assert result["matching_count"] == 2


class TestNameMismatches:
    def test_finds_similar_names(self) -> None:
        api = _api_files(["EntrepreneurOS System"])
        cu = _cu_items(["EntrepreneurOS"])
        mismatches = find_name_mismatches(api, cu, threshold=0.7)
        assert len(mismatches) >= 1

    def test_no_mismatch_for_exact(self) -> None:
        api = _api_files(["UMH"])
        cu = _cu_items(["UMH"])
        mismatches = find_name_mismatches(api, cu)
        assert len(mismatches) == 0


class TestComparisonReport:
    def test_builds_report(self) -> None:
        comparison = compare_inventories(
            _api_files(["A", "B", "C"]),
            _cu_items(["A", "B"]),
        )
        mismatches = find_name_mismatches(
            _api_files(["A", "B", "C"]),
            _cu_items(["A", "B"]),
        )
        report = build_comparison_report(comparison, mismatches, "windows_ui_automation")
        assert report["work_order"] == "WO-LOCAL-PILOT-GDRIVE-GDOCS-001"
        assert report["observation_method"] == "windows_ui_automation"
        assert "proves" in report
        assert "does_not_prove" in report
