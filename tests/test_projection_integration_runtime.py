"""Tests for ProjectionIntegrationRuntime — Campaign 3.5.

Covers: alias normalization, location registration, availability probing,
audit, gaps, duplication, build readiness, snapshot aggregation.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, "/opt/OS")

from unittest.mock import MagicMock

import pytest

from substrate.organism.projection_integration_runtime import (
    IntegrationGapType,
    ProjectionAvailability,
    ProjectionBuildReadiness,
    ProjectionCodeLocation,
    ProjectionIntegrationGap,
    ProjectionIntegrationProfile,
    ProjectionIntegrationRuntime,
    ProjectionIntegrationSnapshot,
    ProjectionMachineType,
    ProjectionMaturityLevel,
    _KNOWN_PROJECTIONS,
    _normalize_projection_id,
)


# ── Alias Normalization ────────────────────────────────────────────────────

class TestAliasNormalization:
    def test_eos_normalizes(self) -> None:
        assert _normalize_projection_id("eos") == "entrepreneuros"

    def test_EOS_normalizes(self) -> None:
        assert _normalize_projection_id("EOS") == "entrepreneuros"

    def test_EntrepreneurOS_normalizes(self) -> None:
        assert _normalize_projection_id("EntrepreneurOS") == "entrepreneuros"

    def test_lyfeos_passthrough(self) -> None:
        assert _normalize_projection_id("lyfeos") == "lyfeos"

    def test_LyfeOS_normalizes(self) -> None:
        assert _normalize_projection_id("LyfeOS") == "lyfeos"

    def test_creatoros_passthrough(self) -> None:
        assert _normalize_projection_id("creatoros") == "creatoros"

    def test_unknown_passthrough(self) -> None:
        assert _normalize_projection_id("FutureOS") == "futureos"


# ── Location Registration ─────────────────────────────────────────────────

class TestLocationRegistration:
    def test_register_vps_location(self) -> None:
        rt = ProjectionIntegrationRuntime()
        loc = rt.register_projection_location(
            projection_id="lyfeos",
            machine="vps",
            root_path="projections/lyfeos",
        )
        assert isinstance(loc, ProjectionCodeLocation)
        assert loc.machine == ProjectionMachineType.VPS
        assert loc.projection_id == "lyfeos"

    def test_register_windows_location(self) -> None:
        rt = ProjectionIntegrationRuntime()
        loc = rt.register_projection_location(
            projection_id="eos",
            machine="windows",
            root_path="C:\\dev\\dev\\eos",
        )
        assert loc.machine == ProjectionMachineType.WINDOWS
        assert loc.projection_id == "entrepreneuros"
        assert loc.availability_status == ProjectionAvailability.UNKNOWN

    def test_register_unknown_machine(self) -> None:
        rt = ProjectionIntegrationRuntime()
        loc = rt.register_projection_location(
            projection_id="creatoros",
            machine="mars_server",
        )
        assert loc.machine == ProjectionMachineType.UNKNOWN

    def test_registered_location_appears_in_code_locations(self) -> None:
        rt = ProjectionIntegrationRuntime()
        rt.register_projection_location(
            projection_id="lyfeos",
            machine="windows",
            root_path="D:\\lyfeos",
        )
        locs = rt.code_locations("lyfeos")
        windows_locs = [l for l in locs if l.machine == ProjectionMachineType.WINDOWS]
        assert len(windows_locs) >= 1


# ── Availability Probing ──────────────────────────────────────────────────

class TestAvailabilityProbing:
    def test_vps_available_location(self) -> None:
        rt = ProjectionIntegrationRuntime()
        locs = rt.code_locations("lyfeos")
        vps_locs = [l for l in locs if l.machine == ProjectionMachineType.VPS]
        assert len(vps_locs) >= 1
        assert vps_locs[0].availability_status == ProjectionAvailability.AVAILABLE

    def test_vps_unavailable_location(self) -> None:
        rt = ProjectionIntegrationRuntime()
        loc = rt.register_projection_location(
            projection_id="lyfeos",
            machine="vps",
            root_path="projections/nonexistent_dir",
        )
        assert loc.availability_status == ProjectionAvailability.UNAVAILABLE

    def test_windows_always_unknown(self) -> None:
        rt = ProjectionIntegrationRuntime()
        loc = rt.register_projection_location(
            projection_id="eos",
            machine="windows",
            root_path="C:\\dev\\eos",
        )
        assert loc.availability_status == ProjectionAvailability.UNKNOWN


# ── Audit ──────────────────────────────────────────────────────────────────

class TestAudit:
    def test_audit_known_projection(self) -> None:
        rt = ProjectionIntegrationRuntime()
        profile = rt.audit_projection("lyfeos")
        assert isinstance(profile, ProjectionIntegrationProfile)
        assert profile.projection_id == "lyfeos"
        assert profile.maturity_level == ProjectionMaturityLevel.MATURE_PARTIAL
        assert profile.last_audited > 0

    def test_audit_with_alias(self) -> None:
        rt = ProjectionIntegrationRuntime()
        profile = rt.audit_projection("EOS")
        assert profile.projection_id == "entrepreneuros"

    def test_audit_unknown_projection(self) -> None:
        rt = ProjectionIntegrationRuntime()
        profile = rt.audit_projection("futureos")
        assert profile.projection_id == "futureos"
        assert profile.maturity_level == ProjectionMaturityLevel.UNKNOWN

    def test_audit_all_returns_all_known(self) -> None:
        rt = ProjectionIntegrationRuntime()
        snap = rt.audit_all()
        assert snap.total >= 3
        ids = {p.projection_id for p in snap.projections}
        assert "lyfeos" in ids
        assert "entrepreneuros" in ids
        assert "creatoros" in ids

    def test_audit_populates_cache(self) -> None:
        rt = ProjectionIntegrationRuntime()
        rt.audit_projection("lyfeos")
        profile = rt.projection_profile("lyfeos")
        assert profile.last_audited > 0


# ── Gap Detection ─────────────────────────────────────────────────────────

class TestGapDetection:
    def test_known_projection_has_no_location_gap(self) -> None:
        rt = ProjectionIntegrationRuntime()
        gaps = rt.integration_gaps("lyfeos")
        gap_types = {g.gap_type for g in gaps}
        assert IntegrationGapType.MISSING_CODE_LOCATION not in gap_types

    def test_unknown_projection_has_location_gap(self) -> None:
        rt = ProjectionIntegrationRuntime()
        gaps = rt.integration_gaps("futureos")
        gap_types = {g.gap_type for g in gaps}
        assert IntegrationGapType.MISSING_CODE_LOCATION in gap_types

    def test_gap_has_no_feature_completion(self) -> None:
        rt = ProjectionIntegrationRuntime()
        gaps = rt.integration_gaps("futureos")
        for g in gaps:
            assert g.does_not_require_feature_completion is True

    def test_missing_registration_gap(self) -> None:
        port = MagicMock()
        port.list_registrations.return_value = []
        rt = ProjectionIntegrationRuntime(projection_port=port)
        gaps = rt.integration_gaps("lyfeos")
        gap_types = {g.gap_type for g in gaps}
        assert IntegrationGapType.MISSING_REGISTRATION in gap_types

    def test_no_registration_gap_when_registered(self) -> None:
        reg = MagicMock()
        reg.projection_id = "lyfeos"
        port = MagicMock()
        port.list_registrations.return_value = [reg]
        rt = ProjectionIntegrationRuntime(projection_port=port)
        gaps = rt.integration_gaps("lyfeos")
        gap_types = {g.gap_type for g in gaps}
        assert IntegrationGapType.MISSING_REGISTRATION not in gap_types


# ── Duplication Detection ─────────────────────────────────────────────────

class TestDuplicationDetection:
    def test_no_duplications_without_reconciliation(self) -> None:
        rt = ProjectionIntegrationRuntime()
        result = rt.detect_duplicated_substrate_concerns("lyfeos")
        assert result == []

    def test_duplications_with_reconciliation(self) -> None:
        div = MagicMock()
        div.projection_id = "lyfeos"
        div.divergence_type = "duplicated_memory"
        recon = MagicMock()
        recon.list_divergences.return_value = [div]
        rt = ProjectionIntegrationRuntime(reconciliation_engine=recon)
        result = rt.detect_duplicated_substrate_concerns("lyfeos")
        assert "duplicated_memory" in result


# ── Build Readiness ───────────────────────────────────────────────────────

class TestBuildReadiness:
    def test_readiness_no_deps(self) -> None:
        rt = ProjectionIntegrationRuntime()
        br = rt.build_readiness("lyfeos")
        assert isinstance(br, ProjectionBuildReadiness)
        assert br.can_inspect_from_meta_ide is False
        assert br.readiness_score <= 1.0

    def test_readiness_with_meta_ide(self) -> None:
        meta_ide = MagicMock()
        rt = ProjectionIntegrationRuntime(meta_ide=meta_ide)
        br = rt.build_readiness("lyfeos")
        assert br.can_inspect_from_meta_ide is True

    def test_readiness_with_agent_fleet(self) -> None:
        fleet = MagicMock()
        rt = ProjectionIntegrationRuntime(agent_fleet=fleet)
        br = rt.build_readiness("lyfeos")
        assert br.can_route_work_via_agent_fleet is True

    def test_readiness_with_compute_fabric(self) -> None:
        cf = MagicMock()
        node = MagicMock()
        node.status = "online"
        node.available = True
        cf.nodes.return_value = [node]
        rt = ProjectionIntegrationRuntime(compute_fabric=cf)
        br = rt.build_readiness("lyfeos")
        assert br.can_select_compute_target is True

    def test_readiness_score_full(self) -> None:
        meta_ide = MagicMock()
        fleet = MagicMock()
        cf = MagicMock()
        node = MagicMock()
        node.status = "online"
        cf.nodes.return_value = [node]
        rt = ProjectionIntegrationRuntime(
            meta_ide=meta_ide, agent_fleet=fleet, compute_fabric=cf,
        )
        br = rt.build_readiness("lyfeos")
        assert br.readiness_score == 1.0
        assert br.missing_requirements == []

    def test_readiness_missing_requirements_listed(self) -> None:
        rt = ProjectionIntegrationRuntime()
        br = rt.build_readiness("lyfeos")
        assert len(br.missing_requirements) > 0

    def test_readiness_unknown_projection(self) -> None:
        rt = ProjectionIntegrationRuntime()
        br = rt.build_readiness("futureos")
        assert br.readiness_score == 0.0


# ── Snapshot Aggregation ──────────────────────────────────────────────────

class TestSnapshotAggregation:
    def test_snapshot_returns_all(self) -> None:
        rt = ProjectionIntegrationRuntime()
        snap = rt.snapshot()
        assert isinstance(snap, ProjectionIntegrationSnapshot)
        assert snap.total >= 3

    def test_snapshot_to_dict(self) -> None:
        rt = ProjectionIntegrationRuntime()
        d = rt.snapshot().to_dict()
        assert "projections" in d
        assert "total" in d
        assert "readiness_summary" in d

    def test_snapshot_counts_correct(self) -> None:
        rt = ProjectionIntegrationRuntime()
        snap = rt.snapshot()
        assert snap.total == snap.connected + snap.partially_connected + snap.unavailable


# ── Type Serialization ────────────────────────────────────────────────────

class TestTypeSerialization:
    def test_code_location_to_dict(self) -> None:
        loc = ProjectionCodeLocation(
            projection_id="test",
            machine=ProjectionMachineType.VPS,
            root_path="projections/test",
        )
        d = loc.to_dict()
        assert d["machine"] == "vps"
        assert "location_id" in d

    def test_integration_gap_to_dict(self) -> None:
        g = ProjectionIntegrationGap(
            projection_id="test",
            gap_type=IntegrationGapType.MISSING_REGISTRATION,
        )
        d = g.to_dict()
        assert d["gap_type"] == "missing_registration"
        assert d["does_not_require_feature_completion"] is True

    def test_profile_to_dict(self) -> None:
        p = ProjectionIntegrationProfile(projection_id="test", name="Test")
        d = p.to_dict()
        assert d["projection_id"] == "test"
        assert d["code_locations"] == []

    def test_build_readiness_to_dict(self) -> None:
        br = ProjectionBuildReadiness(projection_id="test", readiness_score=0.67)
        d = br.to_dict()
        assert d["readiness_score"] == 0.67

    def test_snapshot_to_dict_structure(self) -> None:
        snap = ProjectionIntegrationSnapshot()
        d = snap.to_dict()
        assert "projections" in d
        assert "generated_at" in d
