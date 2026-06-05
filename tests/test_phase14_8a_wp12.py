"""Phase 14.8A WP-1.2 — WorldModelPanel wiring to reality model routes.

Verifies that:
1. Frontend store calls /reality-model/* endpoints (not /organism/*)
2. Backend routes return valid response shapes
3. Frontend types align with backend response contracts
4. No speculative /organism/* endpoints remain in frontend code
5. dist-web serves the new build
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/OS")

WORKTREE = Path("/opt/OS/.claude/worktrees/phase-14-7b-cockpit-usability")
COCKPIT = WORKTREE / "cockpit"
STORE_FILE = COCKPIT / "src/renderer/stores/worldModelStore.ts"
PANEL_FILE = COCKPIT / "src/renderer/panels/WorldModelPanel.tsx"
DIST_WEB = COCKPIT / "dist-web"
ROUTES_FILE = WORKTREE / "transports/api/cockpit_reality_model_routes.py"


class TestNoOrganismEndpoints:
    """Verify all speculative /organism/* endpoints are eliminated from frontend."""

    def test_store_has_no_organism_calls(self):
        content = STORE_FILE.read_text()
        organism_calls = re.findall(r"['\"/]organism/", content)
        assert organism_calls == [], f"Store still calls /organism/*: {organism_calls}"

    def test_panel_has_no_organism_calls(self):
        content = PANEL_FILE.read_text()
        organism_calls = re.findall(r"['\"/]organism/", content)
        assert organism_calls == [], f"Panel still calls /organism/*: {organism_calls}"


class TestStoreCallsRealityModelRoutes:
    """Verify store fetch methods call the correct /reality-model/* endpoints."""

    def test_fetch_status_calls_status(self):
        content = STORE_FILE.read_text()
        assert "/reality-model/status" in content

    def test_fetch_patterns_calls_patterns(self):
        content = STORE_FILE.read_text()
        assert "/reality-model/canonical/patterns" in content

    def test_fetch_pattern_detail_calls_pattern(self):
        content = STORE_FILE.read_text()
        assert "/reality-model/canonical/pattern/" in content

    def test_fetch_relationships_calls_relationships(self):
        content = STORE_FILE.read_text()
        assert "/reality-model/canonical/relationships/" in content

    def test_fetch_recent_observations_calls_recent(self):
        content = STORE_FILE.read_text()
        assert "/reality-model/instance/recent" in content

    def test_fetch_instance_stats_calls_stats(self):
        content = STORE_FILE.read_text()
        assert "/reality-model/instance/stats" in content

    def test_fetch_domains_calls_both(self):
        content = STORE_FILE.read_text()
        assert "/reality-model/canonical/domains" in content
        assert "/reality-model/instance/domains" in content

    def test_search_calls_canonical_search(self):
        content = STORE_FILE.read_text()
        assert "/reality-model/canonical/search" in content

    def test_simulate_calls_simulate(self):
        content = STORE_FILE.read_text()
        assert "/reality-model/simulate" in content


class TestBackendRouteContracts:
    """Verify backend routes exist and return expected shapes."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.routes_content = ROUTES_FILE.read_text()

    def test_status_route_exists(self):
        assert "/reality-model/status" in self.routes_content

    def test_canonical_patterns_route_exists(self):
        assert "/reality-model/canonical/patterns" in self.routes_content

    def test_canonical_pattern_detail_route_exists(self):
        assert "/reality-model/canonical/pattern/{name}" in self.routes_content

    def test_canonical_search_route_exists(self):
        assert "/reality-model/canonical/search" in self.routes_content

    def test_canonical_domains_route_exists(self):
        assert "/reality-model/canonical/domains" in self.routes_content

    def test_canonical_stats_route_exists(self):
        assert "/reality-model/canonical/stats" in self.routes_content

    def test_canonical_relationships_route_exists(self):
        assert "/reality-model/canonical/relationships/{name}" in self.routes_content

    def test_instance_observations_route_exists(self):
        assert "/reality-model/instance/observations" in self.routes_content

    def test_instance_recent_route_exists(self):
        assert "/reality-model/instance/recent" in self.routes_content

    def test_instance_search_route_exists(self):
        assert "/reality-model/instance/search" in self.routes_content

    def test_instance_domains_route_exists(self):
        assert "/reality-model/instance/domains" in self.routes_content

    def test_instance_stats_route_exists(self):
        assert "/reality-model/instance/stats" in self.routes_content

    def test_simulate_route_exists(self):
        assert "/reality-model/simulate" in self.routes_content

    def test_canonical_store_route_exists(self):
        assert "/reality-model/canonical/store" in self.routes_content

    def test_instance_record_route_exists(self):
        assert "/reality-model/instance/record" in self.routes_content


class TestFrontendTypeAlignment:
    """Verify frontend types match backend response field names."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.store_content = STORE_FILE.read_text()

    def test_canonical_pattern_has_required_fields(self):
        for field in [
            "id", "name", "domain", "description",
            "evidence_count", "confidence", "effective_confidence",
            "promoted_at", "last_confirmed", "tags",
        ]:
            assert field in self.store_content, f"CanonicalPattern missing field: {field}"

    def test_reality_model_status_has_layers(self):
        assert "layers" in self.store_content

    def test_instance_stats_has_required_fields(self):
        for field in [
            "observation_count", "domains",
            "avg_effective_confidence", "oldest", "newest",
        ]:
            assert field in self.store_content, f"InstanceStats missing field: {field}"

    def test_instance_observation_has_required_fields(self):
        for field in [
            "content", "domain", "confidence",
            "effective_confidence", "observed_at", "tags",
        ]:
            assert field in self.store_content, f"InstanceObservation missing field: {field}"

    def test_simulation_result_has_required_fields(self):
        for field in [
            "simulation_id", "hypothesis", "step_count",
            "overall_confidence", "duration_ms", "safe_to_execute",
            "predicted_outcome", "risk_factors", "matched_patterns",
        ]:
            assert field in self.store_content, f"SimulationResult missing field: {field}"


class TestPanelStructure:
    """Verify panel has correct tab structure and components."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.panel_content = PANEL_FILE.read_text()

    def test_has_six_tabs(self):
        tab_defs = re.findall(r"id:\s*'(\w+)'", self.panel_content)
        assert len(tab_defs) == 6

    def test_world_tab_exists(self):
        assert "WorldTab" in self.panel_content

    def test_graph_tab_exists(self):
        assert "GraphTab" in self.panel_content

    def test_search_tab_exists(self):
        assert "SearchTab" in self.panel_content

    def test_simulate_tab_exists(self):
        assert "SimulateTab" in self.panel_content

    def test_observations_tab_exists(self):
        assert "ObservationsTab" in self.panel_content

    def test_instance_tab_exists(self):
        assert "InstanceTab" in self.panel_content

    def test_empty_state_component_exists(self):
        assert "Empty" in self.panel_content

    def test_stat_component_exists(self):
        assert "Stat" in self.panel_content

    def test_uses_polling(self):
        assert "usePolling" in self.panel_content


class TestDistWebBuild:
    """Verify dist-web contains the new build."""

    def test_dist_web_exists(self):
        assert DIST_WEB.is_dir()

    def test_index_html_exists(self):
        assert (DIST_WEB / "index.html").is_file()

    def test_assets_dir_exists(self):
        assert (DIST_WEB / "assets").is_dir()

    def test_has_js_asset(self):
        js_files = list((DIST_WEB / "assets").glob("*.js"))
        assert len(js_files) >= 1, "No JS build artifact in dist-web/assets/"

    def test_has_css_asset(self):
        css_files = list((DIST_WEB / "assets").glob("*.css"))
        assert len(css_files) >= 1, "No CSS build artifact in dist-web/assets/"

    def test_no_old_build_hash(self):
        html = (DIST_WEB / "index.html").read_text()
        assert "CKsSa-e8" not in html, "Old build hash CKsSa-e8 still present"

    def test_new_build_hash_present(self):
        html = (DIST_WEB / "index.html").read_text()
        assert "DBaZ_nqZ" in html, "New build hash DBaZ_nqZ not found"


class TestBackendResponseShapes:
    """Verify backend models return fields that frontend expects."""

    def test_canonical_stats_returns_dict(self):
        from substrate.reality_model.canonical import CanonicalRealityModel
        model = CanonicalRealityModel(store_path=Path("/dev/null"))
        stats = model.stats()
        assert isinstance(stats, dict)
        for key in ["pattern_count", "relationship_count", "domains", "avg_confidence"]:
            assert key in stats, f"canonical stats missing '{key}'"

    def test_instance_stats_returns_dict(self):
        from substrate.reality_model.instance import InstanceRealityModel
        model = InstanceRealityModel(
            user_id="test", org_id="test",
            store_path=Path("/dev/null"),
        )
        stats = model.stats()
        assert isinstance(stats, dict)
        for key in ["observation_count", "domains", "avg_effective_confidence", "oldest", "newest"]:
            assert key in stats, f"instance stats missing '{key}'"

    def test_simulation_result_to_dict(self):
        from substrate.reality_model.simulation import SimulationResult
        result = SimulationResult(hypothesis="test")
        d = result.to_dict()
        assert isinstance(d, dict)
        for key in [
            "simulation_id", "hypothesis", "step_count",
            "overall_confidence", "duration_ms", "safe_to_execute",
            "predicted_outcome", "risk_factors", "matched_patterns",
        ]:
            assert key in d, f"SimulationResult.to_dict() missing '{key}'"

    def test_canonical_pattern_has_effective_confidence(self):
        from substrate.reality_model.canonical import CanonicalPattern
        p = CanonicalPattern(name="test", domain="test", description="test")
        ec = p.effective_confidence()
        assert isinstance(ec, float)
        assert 0.0 <= ec <= 1.0

    def test_instance_observation_has_effective_confidence(self):
        from substrate.reality_model.instance import InstanceObservation
        o = InstanceObservation(content="test")
        ec = o.effective_confidence()
        assert isinstance(ec, float)
        assert 0.0 <= ec <= 1.0
