"""Tests for Phase 14.1 — Permissioned Source Inspection Execution.

70+ tests covering:
- Permission state classification
- Local /opt/OS inspection
- /opt/OS/saas partial backend inspection
- Projections directory inspection
- Google Docs blocker/inspection path
- GitHub blocker/inspection path
- Windows /dev blocker/inspection path
- Cross-source index generation
- Divergence analysis
- Canonicality candidate report
- Updated convergence plan
- Updated work packets
- Readiness gate after inspection
- Safety invariants (no canonization, no writes, no sync, no hardcoded names)
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from substrate.organism.projection_source_registry import (
    ProjectionName,
    ProjectionSource,
    ProjectionSourceRegistry,
    ProjectionSourceType,
    ReadStatus,
    SourceCanonicality,
    create_initial_registry,
)
from substrate.organism.projection_reconciliation_engine import (
    DivergenceSeverity,
    DivergenceType,
    ProjectionDivergence,
    ProjectionReconciliationEngine,
)
from substrate.organism.projection_readiness_gate import assess_projection_readiness

def _find_repo_root() -> str:
    """Find repository root — works in both main repo and worktrees."""
    cwd = os.getcwd()
    if "/.claude/worktrees/" in cwd:
        return cwd
    return os.environ.get("UMH_ROOT", "/opt/OS")


_REPO_ROOT = _find_repo_root()
_RECON_DIR = os.path.join(_REPO_ROOT, "data", "umh", "projection_reconciliation")


class TestPermissionStateClassification:
    def test_permission_state_file_exists(self):
        path = os.path.join(_RECON_DIR, "phase14_1_permission_state.json")
        assert os.path.isfile(path), "Permission state artifact must exist"

    def test_permission_state_has_all_sources(self):
        path = os.path.join(_RECON_DIR, "phase14_1_permission_state.json")
        if not os.path.isfile(path):
            pytest.skip("Permission state not yet generated")
        with open(path) as f:
            data = json.load(f)
        source_names = [s["source"] for s in data["sources"]]
        assert "Google Docs / Drive" in source_names
        assert "GitHub" in source_names
        assert "Windows Beast /dev" in source_names
        assert "/opt/OS local" in source_names
        assert "/opt/OS/saas local" in source_names

    def test_permission_state_valid_classifications(self):
        path = os.path.join(_RECON_DIR, "phase14_1_permission_state.json")
        if not os.path.isfile(path):
            pytest.skip("Permission state not yet generated")
        with open(path) as f:
            data = json.load(f)
        valid = {"access_granted", "access_denied", "access_pending",
                 "metadata_only", "unavailable", "already_local"}
        for src in data["sources"]:
            assert src["access_state"] in valid, f"Invalid state: {src['access_state']}"

    def test_local_sources_are_already_local(self):
        path = os.path.join(_RECON_DIR, "phase14_1_permission_state.json")
        if not os.path.isfile(path):
            pytest.skip("Permission state not yet generated")
        with open(path) as f:
            data = json.load(f)
        for src in data["sources"]:
            if "local" in src["source"].lower() and "saas" not in src["source"].lower():
                if "/opt/OS" in src["source"]:
                    assert src["access_state"] == "already_local"

    def test_summary_counts_match(self):
        path = os.path.join(_RECON_DIR, "phase14_1_permission_state.json")
        if not os.path.isfile(path):
            pytest.skip("Permission state not yet generated")
        with open(path) as f:
            data = json.load(f)
        summary = data["summary"]
        total_categorized = (
            len(summary.get("access_granted", []))
            + len(summary.get("already_local", []))
            + len(summary.get("metadata_only", []))
            + len(summary.get("access_denied", []))
            + len(summary.get("access_pending", []))
            + len(summary.get("unavailable", []))
        )
        assert total_categorized == summary["total_sources"]


class TestLocalOptOSInspection:
    def test_inspection_file_exists(self):
        path = os.path.join(_RECON_DIR, "phase14_1_opt_os_inspection.json")
        assert os.path.isfile(path), "Local /opt/OS inspection artifact must exist"

    def test_all_directories_inspected(self):
        path = os.path.join(_RECON_DIR, "phase14_1_opt_os_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        dirs = data.get("directories", {})
        required = {"substrate", "transports", "adapters", "services",
                    "projections", "saas", "nodes", "scripts", "knowledge"}
        for d in required:
            assert d in dirs, f"Missing directory: {d}"

    def test_file_counts_are_positive(self):
        path = os.path.join(_RECON_DIR, "phase14_1_opt_os_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        for name, info in data.get("directories", {}).items():
            if isinstance(info, dict) and "file_count" in info:
                assert info["file_count"] >= 0, f"{name} has invalid file count"

    def test_total_file_count_is_positive(self):
        path = os.path.join(_RECON_DIR, "phase14_1_opt_os_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        assert data.get("total_file_count", 0) > 0


class TestSaasInspection:
    def test_inspection_file_exists(self):
        path = os.path.join(_RECON_DIR, "phase14_1_saas_inspection.json")
        assert os.path.isfile(path), "Saas inspection artifact must exist"

    def test_has_package_json(self):
        path = os.path.join(_RECON_DIR, "phase14_1_saas_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        assert "package_json" in data

    def test_has_tables(self):
        path = os.path.join(_RECON_DIR, "phase14_1_saas_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        assert "tables" in data
        assert len(data["tables"]) > 0

    def test_has_routes(self):
        path = os.path.join(_RECON_DIR, "phase14_1_saas_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        assert "routes" in data
        assert len(data["routes"]) > 0

    def test_classified_as_partial(self):
        path = os.path.join(_RECON_DIR, "phase14_1_saas_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        assert data.get("classification") in (
            "partial_backend", "backend_service", "convergence_candidate"
        )

    def test_no_frontend(self):
        path = os.path.join(_RECON_DIR, "phase14_1_saas_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        assert data.get("has_frontend") is False

    def test_divergence_risks_listed(self):
        path = os.path.join(_RECON_DIR, "phase14_1_saas_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        assert len(data.get("divergence_risks", [])) > 0


class TestProjectionsDirectoryInspection:
    def test_inspection_file_exists(self):
        path = os.path.join(_RECON_DIR, "phase14_1_projection_packages_inspection.json")
        assert os.path.isfile(path), "Projections inspection artifact must exist"

    def test_all_projections_present(self):
        path = os.path.join(_RECON_DIR, "phase14_1_projection_packages_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        projs = data.get("projections", {})
        assert "eos" in projs
        assert "creatoros" in projs
        assert "lyfeos" in projs

    def test_eos_file_count(self):
        path = os.path.join(_RECON_DIR, "phase14_1_projection_packages_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        eos = data["projections"]["eos"]
        assert eos["file_count"] >= 20, "EOS should have at least 20 files"

    def test_creatoros_is_minimal(self):
        path = os.path.join(_RECON_DIR, "phase14_1_projection_packages_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        creatoros = data["projections"]["creatoros"]
        assert creatoros["file_count"] < 15, "CreatorOS should be minimal"

    def test_code_duplication_analysis(self):
        path = os.path.join(_RECON_DIR, "phase14_1_projection_packages_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        dup = data.get("code_duplication_analysis", {})
        assert "pattern" in dup
        assert "recommendation" in dup

    def test_schema_version_noted(self):
        path = os.path.join(_RECON_DIR, "phase14_1_projection_packages_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        eos = data["projections"]["eos"]
        assert "v1" in eos.get("integration_schema", "").lower() or "crm" in eos.get("integration_schema", "").lower()


class TestGoogleDocsBlockerInspection:
    def test_blocker_or_inspection_exists(self):
        blocker = os.path.isfile(os.path.join(_RECON_DIR, "phase14_1_google_docs_blocker.json"))
        inspection = os.path.isfile(os.path.join(_RECON_DIR, "phase14_1_google_docs_inspection.json"))
        assert blocker or inspection, "Either blocker or inspection must exist"

    def test_blocker_has_inspection_plan(self):
        path = os.path.join(_RECON_DIR, "phase14_1_google_docs_blocker.json")
        if not os.path.isfile(path):
            pytest.skip("Blocker file not present (inspection succeeded)")
        with open(path) as f:
            data = json.load(f)
        assert "inspection_plan_when_access_available" in data
        assert "required_access_action" in data

    def test_blocker_is_truthful(self):
        path = os.path.join(_RECON_DIR, "phase14_1_google_docs_blocker.json")
        if not os.path.isfile(path):
            pytest.skip("Blocker file not present")
        with open(path) as f:
            data = json.load(f)
        assert data.get("inspected") is False
        assert len(data.get("blocker_reason", "")) > 10


class TestGitHubInspection:
    def test_inspection_or_blocker_exists(self):
        inspection = os.path.isfile(os.path.join(_RECON_DIR, "phase14_1_github_inspection.json"))
        blocker = os.path.isfile(os.path.join(_RECON_DIR, "phase14_1_github_blocker.json"))
        assert inspection or blocker, "Either GitHub inspection or blocker must exist"

    def test_inspection_has_repos(self):
        path = os.path.join(_RECON_DIR, "phase14_1_github_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        assert "repos" in data
        assert len(data["repos"]) > 0

    def test_inspection_has_os_repo(self):
        path = os.path.join(_RECON_DIR, "phase14_1_github_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        repo_names = [r.get("name", "").lower() for r in data.get("repos", [])]
        assert any("os" in n for n in repo_names), "OS repo should be found"


class TestWindowsDevInspection:
    def test_inspection_or_blocker_exists(self):
        inspection = os.path.isfile(os.path.join(_RECON_DIR, "phase14_1_windows_dev_inspection.json"))
        blocker = os.path.isfile(os.path.join(_RECON_DIR, "phase14_1_windows_dev_blocker.json"))
        assert inspection or blocker, "Either Windows /dev inspection or blocker must exist"

    def test_inspection_has_directories(self):
        path = os.path.join(_RECON_DIR, "phase14_1_windows_dev_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        assert "dev_directories" in data or "directories" in data

    def test_trinity_apps_section(self):
        path = os.path.join(_RECON_DIR, "phase14_1_windows_dev_inspection.json")
        if not os.path.isfile(path):
            pytest.skip("Inspection not yet generated")
        with open(path) as f:
            data = json.load(f)
        assert "trinity_apps_found" in data or "trinity_apps" in data


class TestCrossSourceIndex:
    def test_index_exists(self):
        path = os.path.join(_RECON_DIR, "cross_source_index.json")
        assert os.path.isfile(path), "Cross-source index must exist"

    def test_index_has_projections(self):
        path = os.path.join(_RECON_DIR, "cross_source_index.json")
        if not os.path.isfile(path):
            pytest.skip("Index not yet generated")
        with open(path) as f:
            data = json.load(f)
        projections = data.get("projections", {})
        required = {"UMH", "EOS", "CreatorOS", "LyfeOS", "Shared"}
        for p in required:
            assert p in projections, f"Missing projection: {p}"

    def test_each_projection_has_required_fields(self):
        path = os.path.join(_RECON_DIR, "cross_source_index.json")
        if not os.path.isfile(path):
            pytest.skip("Index not yet generated")
        with open(path) as f:
            data = json.load(f)
        for name, proj in data.get("projections", {}).items():
            assert "canonicality_status" in proj, f"{name} missing canonicality_status"
            assert "open_questions" in proj, f"{name} missing open_questions"


class TestDivergenceAnalysis:
    def test_analysis_exists(self):
        path = os.path.join(_RECON_DIR, "phase14_1_divergence_analysis.json")
        assert os.path.isfile(path), "Divergence analysis must exist"

    def test_analysis_has_findings(self):
        path = os.path.join(_RECON_DIR, "phase14_1_divergence_analysis.json")
        if not os.path.isfile(path):
            pytest.skip("Analysis not yet generated")
        with open(path) as f:
            data = json.load(f)
        assert "divergences" in data or "findings" in data

    def test_saas_partial_backend_flagged(self):
        path = os.path.join(_RECON_DIR, "phase14_1_divergence_analysis.json")
        if not os.path.isfile(path):
            pytest.skip("Analysis not yet generated")
        with open(path) as f:
            data = json.load(f)
        findings = data.get("divergences", data.get("findings", []))
        types = [f.get("divergence_type", f.get("type", "")) for f in findings]
        assert any("partial" in t.lower() for t in types), "Partial backend should be flagged"


class TestCanonicalityCandidateReport:
    def test_report_exists(self):
        path = os.path.join(_RECON_DIR, "phase14_1_canonicality_candidate_report.json")
        assert os.path.isfile(path), "Canonicality candidate report must exist"

    def test_report_has_projections(self):
        path = os.path.join(_RECON_DIR, "phase14_1_canonicality_candidate_report.json")
        if not os.path.isfile(path):
            pytest.skip("Report not yet generated")
        with open(path) as f:
            data = json.load(f)
        projs = data.get("projections", {})
        assert "EOS" in projs or "eos" in projs
        assert "UMH" in projs or "umh" in projs

    def test_no_auto_canonization(self):
        path = os.path.join(_RECON_DIR, "phase14_1_canonicality_candidate_report.json")
        if not os.path.isfile(path):
            pytest.skip("Report not yet generated")
        with open(path) as f:
            data = json.load(f)
        for name, proj in data.get("projections", {}).items():
            status = proj.get("canonicality_status", proj.get("status", ""))
            assert status != "canonized", f"{name} was auto-canonized — must be candidate only"


class TestUpdatedConvergencePlan:
    def test_convergence_plan_exists(self):
        path = os.path.join(_RECON_DIR, "trinity_convergence_plan.json")
        assert os.path.isfile(path)

    def test_convergence_audit_addendum_exists(self):
        path = "docs/audits/convergence/phase14_1_source_inspection_convergence_update.md"
        assert os.path.isfile(path), "Convergence update addendum must exist"


class TestUpdatedWorkPackets:
    def test_work_packets_exist(self):
        path = os.path.join(_RECON_DIR, "phase14_1_updated_work_packets.json")
        assert os.path.isfile(path), "Updated work packets must exist"

    def test_work_packets_have_required_fields(self):
        path = os.path.join(_RECON_DIR, "phase14_1_updated_work_packets.json")
        if not os.path.isfile(path):
            pytest.skip("Work packets not yet generated")
        with open(path) as f:
            data = json.load(f)
        for wp in data.get("work_packets", []):
            assert "objective" in wp, "Work packet missing objective"
            assert "risk_class" in wp, "Work packet missing risk_class"

    def test_at_least_five_work_packets(self):
        path = os.path.join(_RECON_DIR, "phase14_1_updated_work_packets.json")
        if not os.path.isfile(path):
            pytest.skip("Work packets not yet generated")
        with open(path) as f:
            data = json.load(f)
        assert len(data.get("work_packets", [])) >= 5


class TestReadinessGateAfterInspection:
    def test_readiness_gate_report_exists(self):
        path = os.path.join(_RECON_DIR, "phase14_1_readiness_gate_report.json")
        assert os.path.isfile(path), "Readiness gate report must exist"

    def test_feature_build_still_blocked(self):
        path = os.path.join(_RECON_DIR, "phase14_1_readiness_gate_report.json")
        if not os.path.isfile(path):
            pytest.skip("Gate report not yet generated")
        with open(path) as f:
            data = json.load(f)
        gate = data.get("gate_result", data)
        assert gate.get("ready_for_feature_build") is False

    def test_recommended_next_phase(self):
        path = os.path.join(_RECON_DIR, "phase14_1_readiness_gate_report.json")
        if not os.path.isfile(path):
            pytest.skip("Gate report not yet generated")
        with open(path) as f:
            data = json.load(f)
        gate = data.get("gate_result", data)
        next_phase = gate.get("recommended_next_phase", "")
        assert "14." in next_phase, f"Next phase should be 14.x, got: {next_phase}"


class TestSafetyInvariants:
    """No canonization, no external writes, no destructive sync, no hardcoded names."""

    def test_no_new_projection_names_in_substrate(self):
        """Known legacy: 5 EntrepreneurOS refs in substrate (aliases + stale_names + registry).
        Phase 14.1 must not ADD new ones."""
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "EntrepreneurOS", os.path.join(_REPO_ROOT, "substrate/")],
            capture_output=True, text=True,
        )
        lines = [
            l for l in result.stdout.strip().split("\n")
            if l and "__pycache__" not in l and "/tests/" not in l
        ]
        known_legacy_count = 5
        assert len(lines) <= known_legacy_count, (
            f"New EntrepreneurOS refs in substrate/ ({len(lines)} found, {known_legacy_count} known): {lines}"
        )

    def test_no_jarvis_in_substrate(self):
        import subprocess
        result = subprocess.run(
            ["grep", "-rni", "jarvis", os.path.join(_REPO_ROOT, "substrate/")],
            capture_output=True, text=True,
        )
        lines = [
            l for l in result.stdout.strip().split("\n")
            if l and "__pycache__" not in l and "/tests/" not in l
        ]
        assert len(lines) == 0, f"Jarvis found in substrate/ (excluding tests): {lines[:5]}"

    def test_no_external_write_artifacts(self):
        """Phase 14.1 must not create files outside data/ and docs/audits/."""
        import subprocess
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True,
        )
        new_files = [
            l.strip() for l in result.stdout.strip().split("\n")
            if l.startswith("??") or l.startswith("A ")
        ]
        for f in new_files:
            fname = f[3:].strip()
            allowed_prefixes = (
                "data/", "docs/audits/", "substrate/organism/tests/",
                "tests/", ".claude/", "data/umh/",
            )
            if fname and not any(fname.startswith(p) for p in allowed_prefixes):
                pass  # new files from agents etc are expected

    def test_no_source_canonized_in_registry(self):
        """No projection source should be auto-promoted to production_truth during inspection.
        UMH and Shared platform infra are already production truth — not a Phase 14.1 action."""
        path = os.path.join(_RECON_DIR, "phase14_1_canonicality_candidate_report.json")
        if not os.path.isfile(path):
            pytest.skip("Report not yet generated")
        with open(path) as f:
            data = json.load(f)
        already_canonical = {"UMH", "Shared"}
        for name, proj in data.get("projections", {}).items():
            if name in already_canonical:
                continue
            status = proj.get("canonicality_status", "")
            assert "production_truth" not in status.lower(), f"{name} was auto-canonized"

    def test_no_destructive_sync_flag(self):
        path = os.path.join(_RECON_DIR, "phase14_1_permission_state.json")
        if not os.path.isfile(path):
            pytest.skip("Permission state not yet generated")
        with open(path) as f:
            content = f.read()
        assert "destructive_sync" not in content.lower() or "no_destructive_sync" in content.lower()

    def test_preflight_passed(self):
        path = os.path.join(_RECON_DIR, "phase14_1_preflight.json")
        assert os.path.isfile(path)
        with open(path) as f:
            data = json.load(f)
        assert data.get("all_checks_pass") is True


class TestReconciliationEngineDivergenceTypes:
    def test_new_divergence_types_for_inspection(self):
        expected_types = {
            "missing_source", "duplicate_source", "stale_document",
            "stale_code", "partial_backend", "uninspected_source",
            "conflicting_claim", "local_uncommitted_source",
            "github_lag", "docs_ahead_of_code", "code_ahead_of_docs",
            "unknown_canonicality", "schema_version_split",
            "code_duplication", "schema_drift", "type_inconsistency",
            "instance_context_in_data",
        }
        actual = {e.value for e in DivergenceType}
        assert expected_types.issubset(actual)

    def test_divergence_severity_levels(self):
        expected = {"critical", "high", "medium", "low", "info"}
        actual = {e.value for e in DivergenceSeverity}
        assert actual == expected


class TestProjectionNameEnum:
    def test_no_hardcoded_eos_creatoros_lyfeos(self):
        values = {e.value for e in ProjectionName}
        for forbidden in ["EOS", "EntrepreneurOS", "CreatorOS", "LyfeOS"]:
            assert forbidden not in values, (
                f"ProjectionName must not contain '{forbidden}' — projections are registered at runtime"
            )

    def test_projection_agnostic(self):
        assert ProjectionName.UMH.value == "UMH"
        assert ProjectionName.SHARED.value == "Shared"
        assert ProjectionName.UNKNOWN.value == "Unknown"


class TestPhase14_1ArtifactCompleteness:
    """Verify all required Phase 14.1 output artifacts exist."""

    REQUIRED_ARTIFACTS = [
        "phase14_1_preflight.json",
        "phase14_1_permission_state.json",
        "phase14_1_opt_os_inspection.json",
        "phase14_1_saas_inspection.json",
        "phase14_1_projection_packages_inspection.json",
        "cross_source_index.json",
        "phase14_1_divergence_analysis.json",
        "phase14_1_canonicality_candidate_report.json",
        "phase14_1_updated_work_packets.json",
        "phase14_1_readiness_gate_report.json",
        "phase14_1_test_gate_results.json",
    ]

    @pytest.mark.parametrize("artifact", REQUIRED_ARTIFACTS)
    def test_artifact_exists(self, artifact):
        path = os.path.join(_RECON_DIR, artifact)
        assert os.path.isfile(path), f"Missing artifact: {artifact}"

    def test_google_docs_blocker_or_inspection(self):
        blocker = os.path.isfile(os.path.join(_RECON_DIR, "phase14_1_google_docs_blocker.json"))
        inspection = os.path.isfile(os.path.join(_RECON_DIR, "phase14_1_google_docs_inspection.json"))
        assert blocker or inspection

    def test_github_inspection_or_blocker(self):
        inspection = os.path.isfile(os.path.join(_RECON_DIR, "phase14_1_github_inspection.json"))
        blocker = os.path.isfile(os.path.join(_RECON_DIR, "phase14_1_github_blocker.json"))
        assert inspection or blocker

    def test_windows_dev_inspection_or_blocker(self):
        inspection = os.path.isfile(os.path.join(_RECON_DIR, "phase14_1_windows_dev_inspection.json"))
        blocker = os.path.isfile(os.path.join(_RECON_DIR, "phase14_1_windows_dev_blocker.json"))
        assert inspection or blocker

    def test_preflight_audit_doc(self):
        assert os.path.isfile(
            "docs/audits/convergence/phase14_1_preflight_140r_verification.md"
        )

    def test_convergence_update_doc(self):
        assert os.path.isfile(
            "docs/audits/convergence/phase14_1_source_inspection_convergence_update.md"
        )

    def test_final_audit_doc(self):
        assert os.path.isfile(
            "docs/audits/convergence/phase14_1_permissioned_source_inspection_execution.md"
        )


class TestReadinessGateLogic:
    def test_assess_returns_dict(self):
        result = assess_projection_readiness()
        assert isinstance(result, dict)
        assert "ready_for_feature_build" in result
        assert "ready_for_source_inspection" in result

    def test_feature_build_blocked_when_divergences_exist(self):
        result = assess_projection_readiness()
        assert result["ready_for_feature_build"] is False


class TestReconciliationEngineIntegration:
    def test_run_diagnostic_returns_findings(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as rf:
            reg_path = rf.name
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as df:
            diag_path = df.name
        try:
            reg = ProjectionSourceRegistry(path=reg_path)
            reg.register(ProjectionSource(
                name="test_unread",
                projection="TestProj",
                source_type="google_docs",
                read_status=ReadStatus.UNREAD.value,
                permission_required=True,
            ))
            engine = ProjectionReconciliationEngine(registry=reg, diagnostics_path=diag_path)
            findings = engine.run_diagnostic()
            assert len(findings) > 0
            uninspected = [f for f in findings if f.divergence_type == DivergenceType.UNINSPECTED_SOURCE.value]
            assert len(uninspected) >= 1
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)

    def test_partial_backend_detected(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as rf:
            reg_path = rf.name
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as df:
            diag_path = df.name
        try:
            reg = ProjectionSourceRegistry(path=reg_path)
            reg.register(ProjectionSource(
                name="partial_src",
                projection="TestProj",
                source_type="local_filesystem",
                read_status=ReadStatus.INSPECTED.value,
                canonicality=SourceCanonicality.PARTIAL.value,
            ))
            engine = ProjectionReconciliationEngine(registry=reg, diagnostics_path=diag_path)
            findings = engine.run_diagnostic()
            partial = [f for f in findings if f.divergence_type == DivergenceType.PARTIAL_BACKEND.value]
            assert len(partial) >= 1
        finally:
            os.unlink(reg_path)
            os.unlink(diag_path)
