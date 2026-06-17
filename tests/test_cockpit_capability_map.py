"""Tests for CockpitCapabilityMap — Campaign 3.1.

Covers: registry integrity, coverage classification, duplication detection,
MVP gap identification, surface filtering, summary aggregation, route responses.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.workstation.cockpit_capability_map import (
    CockpitCapabilityMap,
    CockpitCapabilitySnapshot,
    CockpitSurface,
    CoverageStatus,
    DuplicationFinding,
    MVPStatus,
    SurfaceCategory,
    _PANEL_REGISTRY,
    _ROUTE_REGISTRY,
    _STORE_REGISTRY,
    _MVP_REQUIRED_PANELS,
    _REDIRECT_PANELS,
    _classify_coverage,
)


# ── Registry Integrity ─────────────────────────────────────────────────────

class TestRegistryIntegrity:
    def test_route_registry_not_empty(self) -> None:
        assert len(_ROUTE_REGISTRY) >= 50

    def test_panel_registry_not_empty(self) -> None:
        assert len(_PANEL_REGISTRY) >= 50

    def test_store_registry_not_empty(self) -> None:
        assert len(_STORE_REGISTRY) >= 25

    def test_all_route_entries_have_required_keys(self) -> None:
        for name, meta in _ROUTE_REGISTRY.items():
            assert "subsystem" in meta, f"{name} missing subsystem"
            assert "panel_link" in meta, f"{name} missing panel_link"
            assert "mvp_status" in meta, f"{name} missing mvp_status"

    def test_all_panel_entries_have_required_keys(self) -> None:
        for name, meta in _PANEL_REGISTRY.items():
            assert "subsystem" in meta, f"{name} missing subsystem"
            assert "route_module" in meta, f"{name} missing route_module"
            assert "mvp_status" in meta, f"{name} missing mvp_status"

    def test_mvp_required_panels_exist_in_registry(self) -> None:
        for panel_id in _MVP_REQUIRED_PANELS:
            assert panel_id in _PANEL_REGISTRY, f"MVP required panel '{panel_id}' not in registry"


# ── Coverage Classification ────────────────────────────────────────────────

class TestCoverageClassification:
    def test_covered_has_route_and_subsystem(self) -> None:
        result = _classify_coverage("agents", {"route_module": "cockpit_agent_routes", "subsystem": "agent_fleet"})
        assert result == CoverageStatus.COVERED

    def test_missing_backend_no_route(self) -> None:
        result = _classify_coverage("analytics", {"route_module": "", "subsystem": "analytics"})
        assert result == CoverageStatus.MISSING_BACKEND

    def test_orphan_redirect_panel(self) -> None:
        result = _classify_coverage("dashboard", {"route_module": "some_route", "subsystem": "x"})
        assert result == CoverageStatus.ORPHAN

    def test_orphan_no_route_no_subsystem(self) -> None:
        result = _classify_coverage("unknown", {"route_module": "", "subsystem": ""})
        assert result == CoverageStatus.ORPHAN

    def test_partial_has_route_no_subsystem(self) -> None:
        result = _classify_coverage("test", {"route_module": "some_route", "subsystem": ""})
        assert result == CoverageStatus.PARTIAL

    def test_redirect_panels_always_orphan(self) -> None:
        for panel_id in _REDIRECT_PANELS:
            meta = _PANEL_REGISTRY.get(panel_id, {"route_module": "x", "subsystem": "x"})
            result = _classify_coverage(panel_id, meta)
            assert result == CoverageStatus.ORPHAN, f"{panel_id} should be ORPHAN"


# ── Duplication Detection ──────────────────────────────────────────────────

class TestDuplicationDetection:
    def test_duplications_returns_list(self) -> None:
        cap = CockpitCapabilityMap()
        dups = cap.duplications()
        assert isinstance(dups, list)

    def test_duplication_finding_has_required_fields(self) -> None:
        d = DuplicationFinding(
            surface_a="panel:a",
            surface_b="panel:b",
            overlap_type="same_data_source",
            recommendation="merge them",
        )
        result = d.to_dict()
        assert result["surface_a"] == "panel:a"
        assert result["overlap_type"] == "same_data_source"

    def test_no_self_duplications(self) -> None:
        cap = CockpitCapabilityMap()
        for d in cap.duplications():
            assert d.surface_a != d.surface_b

    def test_duplications_detect_shared_subsystem(self) -> None:
        cap = CockpitCapabilityMap()
        dups = cap.duplications()
        subsystems_with_dups = {d.overlap_type for d in dups}
        assert "same_data_source" in subsystems_with_dups or len(dups) == 0


# ── MVP Gap Identification ─────────────────────────────────────────────────

class TestMVPGaps:
    def test_mvp_gaps_returns_list(self) -> None:
        cap = CockpitCapabilityMap()
        gaps = cap.mvp_gaps()
        assert isinstance(gaps, list)

    def test_all_gaps_are_required_status(self) -> None:
        cap = CockpitCapabilityMap()
        for g in cap.mvp_gaps():
            assert g.mvp_status == MVPStatus.REQUIRED

    def test_no_covered_surfaces_in_gaps(self) -> None:
        cap = CockpitCapabilityMap()
        for g in cap.mvp_gaps():
            assert g.coverage != CoverageStatus.COVERED

    def test_gap_surfaces_have_surface_id(self) -> None:
        cap = CockpitCapabilityMap()
        for g in cap.mvp_gaps():
            assert g.surface_id.startswith("panel:") or g.surface_id.startswith("route:")

    def test_commandcenter_is_covered_not_gap(self) -> None:
        cap = CockpitCapabilityMap()
        gaps = cap.mvp_gaps()
        gap_names = {g.name for g in gaps}
        assert "commandcenter" not in gap_names

    def test_agents_is_covered_not_gap(self) -> None:
        cap = CockpitCapabilityMap()
        gaps = cap.mvp_gaps()
        gap_names = {g.name for g in gaps}
        assert "agents" not in gap_names


# ── Surface Filtering ──────────────────────────────────────────────────────

class TestSurfaceFiltering:
    def test_filter_by_category_panel(self) -> None:
        cap = CockpitCapabilityMap()
        panels = cap.surfaces(category="panel")
        assert all(s.category == SurfaceCategory.PANEL for s in panels)

    def test_filter_by_mvp_status_required(self) -> None:
        cap = CockpitCapabilityMap()
        required = cap.surfaces(mvp_status="required")
        assert all(s.mvp_status == MVPStatus.REQUIRED for s in required)

    def test_filter_combined(self) -> None:
        cap = CockpitCapabilityMap()
        result = cap.surfaces(category="panel", mvp_status="required")
        assert all(
            s.category == SurfaceCategory.PANEL and s.mvp_status == MVPStatus.REQUIRED
            for s in result
        )

    def test_no_filter_returns_all(self) -> None:
        cap = CockpitCapabilityMap()
        all_surfaces = cap.surfaces()
        assert len(all_surfaces) >= len(_PANEL_REGISTRY)


# ── Summary Aggregation ────────────────────────────────────────────────────

class TestSummaryAggregation:
    def test_summary_has_required_keys(self) -> None:
        cap = CockpitCapabilityMap()
        s = cap.summary()
        assert "total_routes" in s
        assert "total_panels" in s
        assert "total_stores" in s
        assert "total_surfaces" in s
        assert "mvp_gap_count" in s
        assert "duplication_count" in s

    def test_summary_counts_match_registries(self) -> None:
        cap = CockpitCapabilityMap()
        s = cap.summary()
        assert s["total_routes"] == len(_ROUTE_REGISTRY)
        assert s["total_panels"] == len(_PANEL_REGISTRY)
        assert s["total_stores"] == len(_STORE_REGISTRY)

    def test_snapshot_has_generated_at(self) -> None:
        cap = CockpitCapabilityMap()
        snap = cap.snapshot()
        assert snap.generated_at > 0

    def test_snapshot_to_dict_serializable(self) -> None:
        cap = CockpitCapabilityMap()
        snap = cap.snapshot()
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert isinstance(d["surfaces"], list)


# ── Type Serialization ─────────────────────────────────────────────────────

class TestTypeSerialization:
    def test_cockpit_surface_to_dict(self) -> None:
        s = CockpitSurface(
            surface_id="panel:test",
            category=SurfaceCategory.PANEL,
            name="test",
            subsystem="test_sub",
            panel_link="test",
            route_path="/test",
            mvp_status=MVPStatus.REQUIRED,
            coverage=CoverageStatus.COVERED,
        )
        d = s.to_dict()
        assert d["surface_id"] == "panel:test"
        assert d["category"] == "panel"
        assert d["mvp_status"] == "required"

    def test_duplication_finding_to_dict(self) -> None:
        d = DuplicationFinding("a", "b", "same_data_source", "merge").to_dict()
        assert d["surface_a"] == "a"

    def test_snapshot_to_dict_structure(self) -> None:
        snap = CockpitCapabilitySnapshot(
            total_routes=1,
            total_panels=1,
            total_stores=1,
            surfaces=[],
            duplications=[],
            mvp_coverage={},
            coverage_distribution={},
            mvp_gaps=[],
        )
        d = snap.to_dict()
        assert d["total_routes"] == 1
        assert d["surfaces"] == []
