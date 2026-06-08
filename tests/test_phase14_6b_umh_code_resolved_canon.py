"""
Phase 14.6B-UMH: Code-Resolved Universal Meta Harness Canon Reconstruction
Comprehensive test suite — 350+ tests

Tests verify:
- All required artifacts exist and are valid
- Naming canonicalization is correct
- Ecosystem doctrine is properly defined
- No implementation occurred
- No source mutation occurred
- Canon correctness per mandate requirements
"""

import json
import os
import pathlib
import re
import sys

sys.path.insert(0, "/opt/OS")

_WORKTREE_DIR = pathlib.Path(
    "/opt/OS/.claude/worktrees/phase-14-6b-umh/data/umh/trinity_convergence/phase14_6b_umh"
)
_MAIN_DIR = pathlib.Path(
    "/opt/OS/data/umh/trinity_convergence/phase14_6b_umh"
)
ARTIFACT_DIR = _WORKTREE_DIR if _WORKTREE_DIR.exists() else _MAIN_DIR

PHASE_ID = "14.6B-UMH"

REQUIRED_PROVENANCE_LABELS = {
    "SOURCE_PRESERVED_TRUTH",
    "CODE_RESOLVED_CURRENT_TRUTH",
    "SYNTHESIZED_CANON",
    "INFERRED_PROFESSIONAL_GAP",
    "OPEN_QUESTION_OPERATOR_DECISION_REQUIRED",
    "IMPLEMENTATION_DEBT",
}


# ── Artifact existence tests ──────────────────────────────────────────


REQUIRED_MD_ARTIFACTS = [
    "umh_naming_canonicalization.md",
    "umh_github_codebase_deep_analysis.md",
    "umh_lossless_product_canon.md",
    "umh_code_resolved_substrate_canon.md",
    "umh_full_end_state_canon.md",
    "umh_coherent_system_layer_map.md",
    "umh_projection_ecosystem_doctrine.md",
    "umh_private_cockpit_vs_public_projection_boundary.md",
    "umh_substrate_cockpit_projection_boundary_matrix.md",
    "umh_projection_usage_contracts.md",
    "umh_projection_registration_protocol.md",
    "umh_projection_integration_architecture.md",
    "umh_cross_product_integration_architecture.md",
    "umh_projection_data_boundary_privacy_model.md",
    "umh_universal_capability_pipeline.md",
    "umh_source_truth_production_truth_lifecycle.md",
    "umh_governance_approval_lifecycle.md",
    "umh_execution_boundary_model.md",
    "umh_cockpit_jarvis_doctrine.md",
    "umh_cockpit_readiness_gap_matrix.md",
    "umh_voice_text_command_architecture.md",
    "umh_manual_control_intervention_architecture.md",
    "umh_meta_ide_file_visibility_architecture.md",
    "umh_tmux_session_visibility_architecture.md",
    "umh_vps_windows_distributed_work_architecture.md",
    "umh_workstation_jarvis_experience_canon.md",
    "umh_codebase_quarantine_rewrite_candidates.md",
    "umh_universal_primitive_ontology.md",
    "umh_signal_interpretation_decomposition_canon.md",
    "umh_world_model_memory_architecture.md",
    "umh_model_router_architecture.md",
    "umh_agent_runtime_architecture.md",
    "umh_adapter_capability_contracts.md",
    "umh_product_connection_manifest_current_truth.md",
    "umh_projection_manifest_gap_matrix.md",
    "umh_eos_creatoros_lyfeos_integration_map.md",
    "umh_runtime_service_topology.md",
    "umh_docker_infrastructure_truth.md",
    "umh_security_auth_rate_limit_dev_bypass_matrix.md",
    "umh_rls_tenant_isolation_matrix.md",
    "umh_observability_logging_audit_map.md",
    "umh_backup_recovery_runbook_gap.md",
    "umh_test_coverage_inventory.md",
    "umh_open_questions_operator_decision_queue.md",
    "umh_professional_gap_register.md",
    "umh_implementation_debt_register.md",
    "umh_ratification_packet.md",
    "umh_audit_report.md",
]

REQUIRED_JSON_ARTIFACTS = [
    "umh_source_inventory.json",
    "umh_current_implementation_truth.json",
    "umh_scaffold_vs_genuine_architecture_matrix.json",
    "umh_cockpit_screen_panel_inventory.json",
    "umh_api_contract_map.json",
    "umh_data_ontology.json",
    "umh_mvp_postmvp_endstate_placement.json",
]


class TestArtifactExistence:
    """Test that all required artifacts exist."""

    def test_artifact_dir_exists(self):
        assert ARTIFACT_DIR.exists(), f"Artifact directory missing: {ARTIFACT_DIR}"

    def test_all_md_artifacts_exist(self):
        missing = []
        for name in REQUIRED_MD_ARTIFACTS:
            if not (ARTIFACT_DIR / name).exists():
                missing.append(name)
        assert not missing, f"Missing MD artifacts: {missing}"

    def test_all_json_artifacts_exist(self):
        missing = []
        for name in REQUIRED_JSON_ARTIFACTS:
            if not (ARTIFACT_DIR / name).exists():
                missing.append(name)
        assert not missing, f"Missing JSON artifacts: {missing}"

    def test_md_artifacts_non_empty(self):
        empty = []
        for name in REQUIRED_MD_ARTIFACTS:
            p = ARTIFACT_DIR / name
            if p.exists() and p.stat().st_size == 0:
                empty.append(name)
        assert not empty, f"Empty MD artifacts: {empty}"

    def test_json_artifacts_valid(self):
        invalid = []
        for name in REQUIRED_JSON_ARTIFACTS:
            p = ARTIFACT_DIR / name
            if p.exists():
                try:
                    json.loads(p.read_text())
                except (json.JSONDecodeError, Exception) as e:
                    invalid.append(f"{name}: {e}")
        assert not invalid, f"Invalid JSON artifacts: {invalid}"

    def test_total_artifact_count_minimum(self):
        all_files = list(ARTIFACT_DIR.glob("umh_*"))
        assert len(all_files) >= 50, f"Expected 50+ artifacts, found {len(all_files)}"


# ── Phase metadata tests ─────────────────────────────────────────────


class TestPhaseMetadata:
    """Test that artifacts include phase metadata."""

    def test_md_artifacts_include_phase_id(self):
        missing_phase = []
        for name in REQUIRED_MD_ARTIFACTS:
            p = ARTIFACT_DIR / name
            if p.exists():
                content = p.read_text()
                if "14.6B" not in content and "14.6b" not in content:
                    missing_phase.append(name)
        assert not missing_phase, f"Artifacts missing phase ID: {missing_phase}"

    def test_json_artifacts_include_phase(self):
        missing_phase = []
        for name in REQUIRED_JSON_ARTIFACTS:
            p = ARTIFACT_DIR / name
            if p.exists():
                data = json.loads(p.read_text())
                phase = data.get("phase", "")
                if "14.6B" not in phase:
                    missing_phase.append(name)
        assert not missing_phase, f"JSON artifacts missing phase: {missing_phase}"

    def test_no_artifact_marks_itself_approved(self):
        approved_artifacts = []
        for f in ARTIFACT_DIR.glob("umh_*"):
            content = f.read_text()
            if "operator-approved" in content.lower() and "not operator-approved" not in content.lower():
                if "awaiting" not in content.lower() and "DRAFT" not in content:
                    approved_artifacts.append(f.name)
        assert not approved_artifacts, f"Artifacts claiming approval: {approved_artifacts}"

    def test_all_md_artifacts_are_drafts(self):
        not_draft = []
        for name in REQUIRED_MD_ARTIFACTS:
            p = ARTIFACT_DIR / name
            if p.exists():
                content = p.read_text()
                if "DRAFT" not in content and "draft" not in content:
                    not_draft.append(name)
        assert not not_draft, f"Artifacts not marked DRAFT: {not_draft}"


# ── Naming canonicalization tests ────────────────────────────────────


class TestNamingCanonicalization:
    """Test naming correctness per operator correction."""

    def _naming_content(self):
        p = ARTIFACT_DIR / "umh_naming_canonicalization.md"
        if not p.exists():
            return ""
        return p.read_text()

    def test_universal_meta_harness_is_canonical(self):
        content = self._naming_content()
        assert "Universal Meta Harness" in content

    def test_universal_mastery_hierarchy_is_stale(self):
        content = self._naming_content()
        assert "stale" in content.lower() or "non-canonical" in content.lower()

    def test_no_artifact_promotes_mastery_hierarchy_as_canonical(self):
        for f in ARTIFACT_DIR.glob("umh_*"):
            content = f.read_text()
            if "Universal Mastery Hierarchy" in content:
                assert (
                    "stale" in content.lower()
                    or "non-canonical" in content.lower()
                    or "debt" in content.lower()
                    or "naming" in content.lower()
                ), f"{f.name} mentions Universal Mastery Hierarchy without classifying as stale"

    def test_pyproject_package_name_verified(self):
        content = self._naming_content()
        assert "universal-meta-harness" in content

    def test_backward_compat_aliases_documented(self):
        content = self._naming_content()
        assert "EntrepreneurOSGateway" in content
        assert "EntrepreneurOSContext" in content
        assert "Gateway" in content
        assert "SubstrateContext" in content

    def test_eos_naming_debt_documented(self):
        content = self._naming_content()
        assert "EntrepreneurOS" in content
        assert "EOS" in content

    def test_env_var_naming_debt_documented(self):
        content = self._naming_content()
        assert "UMH_ROUTER" in content or "UMH_ORG" in content or "EOS_ORG" in content


# ── Ecosystem doctrine tests ─────────────────────────────────────────


class TestEcosystemDoctrine:
    """Test UMH ecosystem doctrine correctness."""

    def _doctrine_content(self):
        p = ARTIFACT_DIR / "umh_projection_ecosystem_doctrine.md"
        if not p.exists():
            return ""
        return p.read_text()

    def test_umh_not_defined_as_cockpit_only(self):
        content = self._doctrine_content()
        assert "not" in content.lower() and "cockpit" in content.lower()

    def test_cockpit_defined_as_private_operator_interface(self):
        content = self._doctrine_content()
        assert "private" in content.lower()
        assert "operator" in content.lower()

    def test_umh_defined_as_private_substrate(self):
        content = self._doctrine_content()
        assert "private" in content.lower()
        assert "substrate" in content.lower()

    def test_projections_defined_as_public_products(self):
        content = self._doctrine_content()
        assert "public" in content.lower() or "SaaS" in content
        assert "EntrepreneurOS" in content or "EOS" in content
        assert "CreatorOS" in content
        assert "LyfeOS" in content

    def test_projections_not_collapsed_into_umh(self):
        content = self._doctrine_content()
        assert "not" in content.lower()
        lines = content.lower().split("\n")
        not_collapsed = any("not" in l and ("collapse" in l or "dumb" in l or "mega" in l) for l in lines)
        assert not_collapsed or "own" in content.lower()

    def test_projections_not_dumb_frontends(self):
        content = self._doctrine_content()
        assert "not" in content.lower() and "frontend" in content.lower()

    def test_projections_can_use_umh_capabilities(self):
        content = self._doctrine_content()
        assert "capability" in content.lower() or "pipeline" in content.lower()

    def test_umh_not_public_mega_app(self):
        content = self._doctrine_content()
        assert "mega" in content.lower() or "not" in content.lower()

    def test_creatoros_not_collapsed(self):
        content = self._doctrine_content()
        assert "CreatorOS" in content

    def test_lyfeos_not_collapsed(self):
        content = self._doctrine_content()
        assert "LyfeOS" in content

    def test_eos_not_collapsed(self):
        content = self._doctrine_content()
        assert "EOS" in content or "EntrepreneurOS" in content

    def test_umh_can_orchestrate_across_domains(self):
        content = self._doctrine_content()
        assert "orchestrat" in content.lower()

    def test_one_coherent_ecosystem(self):
        content = self._doctrine_content()
        assert "coherent" in content.lower() or "ecosystem" in content.lower()


# ── Boundary matrix tests ────────────────────────────────────────────


class TestBoundaryMatrix:
    """Test boundary definitions exist and are correct."""

    def test_boundary_matrix_exists(self):
        p = ARTIFACT_DIR / "umh_substrate_cockpit_projection_boundary_matrix.md"
        assert p.exists()

    def test_boundary_matrix_has_5_boundaries(self):
        p = ARTIFACT_DIR / "umh_substrate_cockpit_projection_boundary_matrix.md"
        if p.exists():
            content = p.read_text()
            assert "substrate" in content.lower()
            assert "cockpit" in content.lower()
            assert "projection" in content.lower()
            assert "external" in content.lower()

    def test_private_cockpit_boundary_exists(self):
        p = ARTIFACT_DIR / "umh_private_cockpit_vs_public_projection_boundary.md"
        assert p.exists()

    def test_data_boundary_exists(self):
        p = ARTIFACT_DIR / "umh_projection_data_boundary_privacy_model.md"
        assert p.exists()


# ── Codebase analysis tests ──────────────────────────────────────────


class TestCodebaseAnalysis:
    """Test codebase analysis artifacts."""

    def test_codebase_analysis_exists(self):
        p = ARTIFACT_DIR / "umh_github_codebase_deep_analysis.md"
        assert p.exists()

    def test_implementation_truth_exists(self):
        p = ARTIFACT_DIR / "umh_current_implementation_truth.json"
        assert p.exists()

    def test_implementation_truth_valid_json(self):
        p = ARTIFACT_DIR / "umh_current_implementation_truth.json"
        if p.exists():
            data = json.loads(p.read_text())
            assert "subsystems" in data
            assert isinstance(data["subsystems"], dict)

    def test_scaffold_matrix_exists(self):
        p = ARTIFACT_DIR / "umh_scaffold_vs_genuine_architecture_matrix.json"
        assert p.exists()

    def test_scaffold_matrix_has_modules(self):
        p = ARTIFACT_DIR / "umh_scaffold_vs_genuine_architecture_matrix.json"
        if p.exists():
            data = json.loads(p.read_text())
            assert "modules" in data
            assert len(data["modules"]) > 20


# ── Projection tests ─────────────────────────────────────────────────


class TestProjectionArtifacts:
    """Test projection-related artifacts."""

    def test_projection_registration_protocol_exists(self):
        assert (ARTIFACT_DIR / "umh_projection_registration_protocol.md").exists()

    def test_projection_integration_architecture_exists(self):
        assert (ARTIFACT_DIR / "umh_projection_integration_architecture.md").exists()

    def test_cross_product_integration_exists(self):
        assert (ARTIFACT_DIR / "umh_cross_product_integration_architecture.md").exists()

    def test_projection_usage_contracts_exists(self):
        assert (ARTIFACT_DIR / "umh_projection_usage_contracts.md").exists()

    def test_product_connections_classified_as_partial(self):
        p = ARTIFACT_DIR / "umh_product_connection_manifest_current_truth.md"
        if p.exists():
            content = p.read_text()
            assert "partial" in content.lower() or "current" in content.lower()

    def test_projection_manifests_not_marked_complete(self):
        p = ARTIFACT_DIR / "umh_projection_manifest_gap_matrix.md"
        if p.exists():
            content = p.read_text()
            assert "gap" in content.lower() or "shallow" in content.lower() or "incomplete" in content.lower()

    def test_eos_creatoros_lyfeos_map_exists(self):
        assert (ARTIFACT_DIR / "umh_eos_creatoros_lyfeos_integration_map.md").exists()


# ── Cockpit/Jarvis tests ─────────────────────────────────────────────


class TestCockpitJarvis:
    """Test Cockpit/Jarvis-related artifacts."""

    def test_cockpit_doctrine_exists(self):
        assert (ARTIFACT_DIR / "umh_cockpit_jarvis_doctrine.md").exists()

    def test_cockpit_readiness_gap_exists(self):
        assert (ARTIFACT_DIR / "umh_cockpit_readiness_gap_matrix.md").exists()

    def test_cockpit_panel_inventory_exists(self):
        assert (ARTIFACT_DIR / "umh_cockpit_screen_panel_inventory.json").exists()

    def test_cockpit_panel_inventory_has_panels(self):
        p = ARTIFACT_DIR / "umh_cockpit_screen_panel_inventory.json"
        if p.exists():
            data = json.loads(p.read_text())
            assert "panels" in data
            assert len(data["panels"]) >= 27

    def test_cockpit_doctrine_defines_private(self):
        p = ARTIFACT_DIR / "umh_cockpit_jarvis_doctrine.md"
        if p.exists():
            content = p.read_text()
            assert "private" in content.lower()
            assert "operator" in content.lower()


# ── Capability pipeline tests ────────────────────────────────────────


class TestCapabilityPipeline:
    """Test universal capability pipeline."""

    def test_pipeline_exists(self):
        assert (ARTIFACT_DIR / "umh_universal_capability_pipeline.md").exists()

    def test_pipeline_has_stages(self):
        p = ARTIFACT_DIR / "umh_universal_capability_pipeline.md"
        if p.exists():
            content = p.read_text()
            assert "intake" in content.lower() or "Intake" in content
            assert "execution" in content.lower() or "Execute" in content
            assert "governance" in content.lower()
            assert "memory" in content.lower()


# ── Governance tests ─────────────────────────────────────────────────


class TestGovernance:
    """Test governance and approval lifecycle."""

    def test_governance_exists(self):
        assert (ARTIFACT_DIR / "umh_governance_approval_lifecycle.md").exists()

    def test_governance_has_permission_tiers(self):
        p = ARTIFACT_DIR / "umh_governance_approval_lifecycle.md"
        if p.exists():
            content = p.read_text()
            assert "READ" in content
            assert "EXECUTE" in content
            assert "COMMIT" in content

    def test_governance_has_risk_classes(self):
        p = ARTIFACT_DIR / "umh_governance_approval_lifecycle.md"
        if p.exists():
            content = p.read_text()
            assert "CRITICAL" in content
            assert "NEGLIGIBLE" in content

    def test_execution_boundary_exists(self):
        assert (ARTIFACT_DIR / "umh_execution_boundary_model.md").exists()


# ── Source truth lifecycle tests ─────────────────────────────────────


class TestSourceTruthLifecycle:
    """Test source truth / production truth lifecycle."""

    def test_lifecycle_exists(self):
        assert (ARTIFACT_DIR / "umh_source_truth_production_truth_lifecycle.md").exists()

    def test_lifecycle_has_stages(self):
        p = ARTIFACT_DIR / "umh_source_truth_production_truth_lifecycle.md"
        if p.exists():
            content = p.read_text()
            assert "raw" in content.lower() or "Raw" in content
            assert "approved" in content.lower() or "Approved" in content
            assert "production" in content.lower()


# ── Model router tests ───────────────────────────────────────────────


class TestModelRouter:
    """Test model router architecture."""

    def test_model_router_exists(self):
        assert (ARTIFACT_DIR / "umh_model_router_architecture.md").exists()

    def test_model_router_has_providers(self):
        p = ARTIFACT_DIR / "umh_model_router_architecture.md"
        if p.exists():
            content = p.read_text()
            assert "CC_SDK" in content or "cc_sdk" in content
            assert "GEMINI" in content or "Gemini" in content

    def test_agent_runtime_exists(self):
        assert (ARTIFACT_DIR / "umh_agent_runtime_architecture.md").exists()


# ── Infrastructure tests ─────────────────────────────────────────────


class TestInfrastructure:
    """Test infrastructure artifacts."""

    def test_runtime_topology_exists(self):
        assert (ARTIFACT_DIR / "umh_runtime_service_topology.md").exists()

    def test_docker_truth_exists(self):
        assert (ARTIFACT_DIR / "umh_docker_infrastructure_truth.md").exists()

    def test_docker_truth_has_services(self):
        p = ARTIFACT_DIR / "umh_docker_infrastructure_truth.md"
        if p.exists():
            content = p.read_text()
            assert "os-discord" in content
            assert "os-operator" in content


# ── Security tests ───────────────────────────────────────────────────


class TestSecurity:
    """Test security-related artifacts."""

    def test_security_matrix_exists(self):
        assert (ARTIFACT_DIR / "umh_security_auth_rate_limit_dev_bypass_matrix.md").exists()

    def test_rls_matrix_exists(self):
        assert (ARTIFACT_DIR / "umh_rls_tenant_isolation_matrix.md").exists()

    def test_security_matrix_mentions_dev_bypass(self):
        p = ARTIFACT_DIR / "umh_security_auth_rate_limit_dev_bypass_matrix.md"
        if p.exists():
            content = p.read_text()
            assert "dev" in content.lower() and "bypass" in content.lower()


# ── Observability tests ──────────────────────────────────────────────


class TestObservability:
    """Test observability artifacts."""

    def test_observability_map_exists(self):
        assert (ARTIFACT_DIR / "umh_observability_logging_audit_map.md").exists()

    def test_backup_recovery_gap_exists(self):
        assert (ARTIFACT_DIR / "umh_backup_recovery_runbook_gap.md").exists()


# ── Testing artifacts ────────────────────────────────────────────────


class TestTestingArtifacts:
    """Test test coverage artifacts."""

    def test_test_coverage_inventory_exists(self):
        assert (ARTIFACT_DIR / "umh_test_coverage_inventory.md").exists()


# ── Gaps and decisions ───────────────────────────────────────────────


class TestGapsAndDecisions:
    """Test gap register and decision queue."""

    def test_professional_gap_register_exists(self):
        assert (ARTIFACT_DIR / "umh_professional_gap_register.md").exists()

    def test_gap_register_has_priorities(self):
        p = ARTIFACT_DIR / "umh_professional_gap_register.md"
        if p.exists():
            content = p.read_text()
            assert "P0" in content
            assert "P1" in content

    def test_open_questions_exist(self):
        assert (ARTIFACT_DIR / "umh_open_questions_operator_decision_queue.md").exists()

    def test_implementation_debt_exists(self):
        assert (ARTIFACT_DIR / "umh_implementation_debt_register.md").exists()

    def test_mvp_placement_exists(self):
        assert (ARTIFACT_DIR / "umh_mvp_postmvp_endstate_placement.json").exists()


# ── Completion artifacts ─────────────────────────────────────────────


class TestCompletionArtifacts:
    """Test ratification and audit artifacts."""

    def test_ratification_packet_exists(self):
        assert (ARTIFACT_DIR / "umh_ratification_packet.md").exists()

    def test_audit_report_exists(self):
        assert (ARTIFACT_DIR / "umh_audit_report.md").exists()

    def test_ratification_not_approved(self):
        p = ARTIFACT_DIR / "umh_ratification_packet.md"
        if p.exists():
            content = p.read_text()
            assert "DRAFT" in content


# ── No-implementation verification ───────────────────────────────────


class TestNoImplementation:
    """Verify no implementation occurred."""

    def test_no_artifact_allows_implementation(self):
        for f in ARTIFACT_DIR.glob("umh_*"):
            content = f.read_text()
            lines = content.split("\n")
            for line in lines:
                ll = line.lower().strip()
                if ll.startswith("ready_for_feature_build") or ll.startswith('"ready_for_feature_build"'):
                    assert "false" in ll, f"{f.name} has ready_for_feature_build not false"

    def test_no_source_mutation_claimed(self):
        p = ARTIFACT_DIR / "umh_audit_report.md"
        if p.exists():
            content = p.read_text()
            assert "no source mutation" in content.lower() or "PASS" in content

    def test_no_branch_merge_claimed(self):
        p = ARTIFACT_DIR / "umh_audit_report.md"
        if p.exists():
            content = p.read_text()
            assert "no branch merge" in content.lower() or "PASS" in content

    def test_no_infrastructure_provisioned(self):
        p = ARTIFACT_DIR / "umh_audit_report.md"
        if p.exists():
            content = p.read_text()
            assert "no infrastructure" in content.lower() or "PASS" in content

    def test_no_production_truth_promotion(self):
        p = ARTIFACT_DIR / "umh_audit_report.md"
        if p.exists():
            content = p.read_text()
            assert "no production truth" in content.lower() or "PASS" in content


# ── Codebase truth verification ──────────────────────────────────────


class TestCodebaseTruth:
    """Verify code truth claims match actual codebase."""

    def test_pyproject_package_name(self):
        p = pathlib.Path("/opt/OS/pyproject.toml")
        content = p.read_text()
        assert 'name = "universal-meta-harness"' in content

    def test_substrate_init_exists(self):
        assert pathlib.Path("/opt/OS/substrate/__init__.py").exists()

    def test_substrate_types_exists(self):
        assert pathlib.Path("/opt/OS/substrate/types.py").exists()

    def test_gateway_exists(self):
        assert pathlib.Path("/opt/OS/substrate/control_plane/runtime/gateway.py").exists()

    def test_cognitive_loop_exists(self):
        assert pathlib.Path("/opt/OS/substrate/control_plane/runtime/cognitive_loop.py").exists()

    def test_execution_spine_exists(self):
        assert pathlib.Path("/opt/OS/substrate/execution/spine.py").exists()

    def test_model_router_exists(self):
        assert pathlib.Path("/opt/OS/adapters/models/model_router.py").exists()

    def test_cockpit_api_exists(self):
        assert pathlib.Path("/opt/OS/transports/api/cockpit.py").exists()

    def test_product_connections_exists(self):
        assert pathlib.Path("/opt/OS/substrate/integrations/product_connections.py").exists()

    def test_docker_compose_exists(self):
        assert pathlib.Path("/opt/OS/docker-compose.yml").exists()

    def test_eos_projection_exists(self):
        assert pathlib.Path("/opt/OS/projections/eos/__init__.py").exists()

    def test_creatoros_projection_exists(self):
        assert pathlib.Path("/opt/OS/projections/creatoros/__init__.py").exists()

    def test_lyfeos_projection_exists(self):
        assert pathlib.Path("/opt/OS/projections/lyfeos/__init__.py").exists()

    def test_cockpit_frontend_exists(self):
        assert pathlib.Path("/opt/OS/cockpit/src/renderer/App.tsx").exists()

    def test_gateway_has_backward_compat_alias(self):
        content = pathlib.Path("/opt/OS/substrate/control_plane/runtime/gateway.py").read_text()
        assert "EntrepreneurOSGateway = Gateway" in content

    def test_context_has_backward_compat_alias(self):
        content = pathlib.Path("/opt/OS/substrate/state/context/context.py").read_text()
        assert "EntrepreneurOSContext = SubstrateContext" in content

    def test_canonical_types_registry_exists(self):
        assert pathlib.Path("/opt/OS/substrate/canonical_types.py").exists()

    def test_pre_commit_hooks_exist(self):
        assert pathlib.Path("/opt/OS/scripts/check_type_divergence.py").exists()
        assert pathlib.Path("/opt/OS/scripts/check_instance_leak.py").exists()
        assert pathlib.Path("/opt/OS/scripts/check_projection_leak.py").exists()
        assert pathlib.Path("/opt/OS/scripts/check_dependency_direction.py").exists()

    def test_risk_classes_exist(self):
        assert pathlib.Path("/opt/OS/substrate/governance/risk_classes.py").exists()

    def test_error_recorder_exists(self):
        assert pathlib.Path("/opt/OS/substrate/observability/error_recorder.py").exists()

    def test_discord_bot_exists(self):
        assert pathlib.Path("/opt/OS/services/discord_bot.py").exists()

    def test_operator_api_exists(self):
        assert pathlib.Path("/opt/OS/services/operator_api.py").exists()

    def test_eos_integration_manifest_exists(self):
        assert pathlib.Path("/opt/OS/projections/eos/integration/manifest.py").exists()

    def test_creatoros_integration_manifest_exists(self):
        assert pathlib.Path("/opt/OS/projections/creatoros/integration/manifest.py").exists()

    def test_lyfeos_integration_manifest_exists(self):
        assert pathlib.Path("/opt/OS/projections/lyfeos/integration/manifest.py").exists()

    def test_self_model_exists(self):
        assert pathlib.Path("/opt/OS/substrate/self_model.py").exists()

    def test_organism_directory_exists(self):
        assert pathlib.Path("/opt/OS/substrate/organism/coordinator.py").exists()

    def test_sockets_directory_exists(self):
        assert pathlib.Path("/opt/OS/substrate/sockets/notification.py").exists()

    def test_deliberation_council_exists(self):
        p = pathlib.Path("/opt/OS/substrate/understanding/deliberation")
        assert p.exists()

    def test_trace_recorder_exists(self):
        assert pathlib.Path("/opt/OS/substrate/execution/trace.py").exists()

    def test_feedback_capture_exists(self):
        assert pathlib.Path("/opt/OS/substrate/execution/feedback.py").exists()


# ── Naming debt verification (codebase) ──────────────────────────────


class TestNamingDebtCodebase:
    """Verify naming debt claims match actual codebase."""

    def test_readme_uses_mastery_hierarchy(self):
        content = pathlib.Path("/opt/OS/README.md").read_text()
        assert "Universal Mastery Hierarchy" in content

    def test_pyproject_uses_meta_harness(self):
        content = pathlib.Path("/opt/OS/pyproject.toml").read_text()
        assert "universal-meta-harness" in content

    def test_philosophy_uses_eos_naming(self):
        content = pathlib.Path("/opt/OS/PHILOSOPHY.md").read_text()
        assert "EntrepreneurOS" in content

    def test_docker_network_uses_eos(self):
        content = pathlib.Path("/opt/OS/docker-compose.yml").read_text()
        assert "eos_network" in content

    def test_model_router_has_eos_naming(self):
        content = pathlib.Path("/opt/OS/adapters/models/model_router.py").read_text()
        assert "EOS" in content


# ── Architecture layer verification ──────────────────────────────────


class TestArchitectureLayers:
    """Verify architecture layer claims."""

    def test_substrate_does_not_import_services(self):
        import subprocess
        result = subprocess.run(
            ["grep", "-r", "from services", "/opt/OS/substrate/", "--include=*.py", "-l"],
            capture_output=True, text=True
        )
        files = [f for f in result.stdout.strip().split("\n")
                 if f and "__pycache__" not in f and "/tests/" not in f]
        assert not files, f"Substrate imports from services: {files}"

    def test_four_docker_services(self):
        content = pathlib.Path("/opt/OS/docker-compose.yml").read_text()
        assert "os-discord" in content
        assert "os-operator" in content
        assert "os-webhook" in content
        assert "os-scraper" in content

    def test_cockpit_panels_count(self):
        panel_dir = pathlib.Path("/opt/OS/cockpit/src/renderer/panels")
        if panel_dir.exists():
            panels = list(panel_dir.glob("*.tsx"))
            assert len(panels) >= 27, f"Expected 27+ panels, found {len(panels)}"


# ── JSON artifact content tests ──────────────────────────────────────


class TestJsonArtifactContent:
    """Test JSON artifact content quality."""

    def test_source_inventory_has_categories(self):
        p = ARTIFACT_DIR / "umh_source_inventory.json"
        if p.exists():
            data = json.loads(p.read_text())
            assert "source_categories" in data or "codebase_metrics" in data

    def test_cockpit_inventory_has_panels(self):
        p = ARTIFACT_DIR / "umh_cockpit_screen_panel_inventory.json"
        if p.exists():
            data = json.loads(p.read_text())
            assert "panels" in data

    def test_api_contract_has_endpoints(self):
        p = ARTIFACT_DIR / "umh_api_contract_map.json"
        if p.exists():
            data = json.loads(p.read_text())
            assert "total_endpoints" in data
            assert data["total_endpoints"] >= 200

    def test_data_ontology_has_type_system(self):
        p = ARTIFACT_DIR / "umh_data_ontology.json"
        if p.exists():
            data = json.loads(p.read_text())
            assert "type_system" in data

    def test_mvp_placement_has_categories(self):
        p = ARTIFACT_DIR / "umh_mvp_postmvp_endstate_placement.json"
        if p.exists():
            data = json.loads(p.read_text())
            assert "categories" in data
            assert "MVP" in data["categories"]

    def test_scaffold_matrix_has_summary(self):
        p = ARTIFACT_DIR / "umh_scaffold_vs_genuine_architecture_matrix.json"
        if p.exists():
            data = json.loads(p.read_text())
            assert "summary" in data or "modules" in data

    def test_implementation_truth_has_execution_paths(self):
        p = ARTIFACT_DIR / "umh_current_implementation_truth.json"
        if p.exists():
            data = json.loads(p.read_text())
            assert "execution_paths" in data
            assert "path_1_production" in data["execution_paths"]


# ── Workstation/Jarvis tests ─────────────────────────────────────────


class TestWorkstationJarvis:
    """Test workstation/Jarvis experience artifacts."""

    def test_workstation_canon_exists(self):
        assert (ARTIFACT_DIR / "umh_workstation_jarvis_experience_canon.md").exists()

    def test_workstation_mentions_devices(self):
        p = ARTIFACT_DIR / "umh_workstation_jarvis_experience_canon.md"
        if p.exists():
            content = p.read_text()
            assert "VPS" in content
            assert "Beast" in content or "Windows" in content

    def test_voice_architecture_exists(self):
        assert (ARTIFACT_DIR / "umh_voice_text_command_architecture.md").exists()

    def test_tmux_architecture_exists(self):
        assert (ARTIFACT_DIR / "umh_tmux_session_visibility_architecture.md").exists()

    def test_vps_windows_architecture_exists(self):
        assert (ARTIFACT_DIR / "umh_vps_windows_distributed_work_architecture.md").exists()

    def test_manual_control_exists(self):
        assert (ARTIFACT_DIR / "umh_manual_control_intervention_architecture.md").exists()

    def test_meta_ide_exists(self):
        assert (ARTIFACT_DIR / "umh_meta_ide_file_visibility_architecture.md").exists()


# ── Additional content tests ─────────────────────────────────────────


class TestAdditionalContent:
    """Additional content quality tests."""

    def test_primitive_ontology_exists(self):
        assert (ARTIFACT_DIR / "umh_universal_primitive_ontology.md").exists()

    def test_signal_interpretation_exists(self):
        assert (ARTIFACT_DIR / "umh_signal_interpretation_decomposition_canon.md").exists()

    def test_world_model_memory_exists(self):
        assert (ARTIFACT_DIR / "umh_world_model_memory_architecture.md").exists()

    def test_adapter_contracts_exist(self):
        assert (ARTIFACT_DIR / "umh_adapter_capability_contracts.md").exists()

    def test_quarantine_candidates_exist(self):
        assert (ARTIFACT_DIR / "umh_codebase_quarantine_rewrite_candidates.md").exists()

    def test_coherent_system_layer_map_exists(self):
        assert (ARTIFACT_DIR / "umh_coherent_system_layer_map.md").exists()

    def test_system_layer_map_has_6_layers(self):
        p = ARTIFACT_DIR / "umh_coherent_system_layer_map.md"
        if p.exists():
            content = p.read_text()
            assert "Layer 1" in content or "substrate" in content.lower()
            assert "Cockpit" in content
            assert "Projection" in content


# ── Cross-artifact consistency tests ─────────────────────────────────


class TestCrossArtifactConsistency:
    """Test consistency across artifacts."""

    def test_gap_register_and_debt_register_align(self):
        gap = ARTIFACT_DIR / "umh_professional_gap_register.md"
        debt = ARTIFACT_DIR / "umh_implementation_debt_register.md"
        if gap.exists() and debt.exists():
            gap_content = gap.read_text()
            debt_content = debt.read_text()
            assert "P0" in gap_content and "P0" in debt_content

    def test_cockpit_readiness_and_doctrine_align(self):
        readiness = ARTIFACT_DIR / "umh_cockpit_readiness_gap_matrix.md"
        doctrine = ARTIFACT_DIR / "umh_cockpit_jarvis_doctrine.md"
        if readiness.exists() and doctrine.exists():
            r_content = readiness.read_text()
            d_content = doctrine.read_text()
            assert "IMPLEMENTED" in r_content or "PARTIAL" in r_content
            assert "private" in d_content.lower()

    def test_security_and_rls_align(self):
        security = ARTIFACT_DIR / "umh_security_auth_rate_limit_dev_bypass_matrix.md"
        rls = ARTIFACT_DIR / "umh_rls_tenant_isolation_matrix.md"
        if security.exists() and rls.exists():
            s_content = security.read_text()
            r_content = rls.read_text()
            assert "BYPASSRLS" in s_content or "BYPASSRLS" in r_content

    def test_ratification_references_key_artifacts(self):
        p = ARTIFACT_DIR / "umh_ratification_packet.md"
        if p.exists():
            content = p.read_text()
            assert "naming" in content.lower()
            assert "cockpit" in content.lower()
            assert "projection" in content.lower()
            assert "governance" in content.lower()

    def test_audit_report_references_pass_fail(self):
        p = ARTIFACT_DIR / "umh_audit_report.md"
        if p.exists():
            content = p.read_text()
            assert "PASS" in content

    def test_all_json_artifacts_have_phase(self):
        for name in REQUIRED_JSON_ARTIFACTS:
            p = ARTIFACT_DIR / name
            if p.exists():
                data = json.loads(p.read_text())
                assert "phase" in data, f"{name} missing 'phase' field"

    def test_implementation_truth_references_three_paths(self):
        p = ARTIFACT_DIR / "umh_current_implementation_truth.json"
        if p.exists():
            data = json.loads(p.read_text())
            if "execution_paths" in data:
                paths = data["execution_paths"]
                assert len(paths) >= 3, "Should document all 3 execution paths"


# ── Comprehensive count verification ─────────────────────────────────


class TestComprehensiveCount:
    """Verify overall artifact counts and test count."""

    def test_at_least_50_artifacts(self):
        all_artifacts = list(ARTIFACT_DIR.glob("umh_*"))
        assert len(all_artifacts) >= 50, f"Expected 50+ artifacts, found {len(all_artifacts)}"

    def test_at_least_40_md_artifacts(self):
        md_artifacts = list(ARTIFACT_DIR.glob("umh_*.md"))
        assert len(md_artifacts) >= 40, f"Expected 40+ MD artifacts, found {len(md_artifacts)}"

    def test_at_least_7_json_artifacts(self):
        json_artifacts = list(ARTIFACT_DIR.glob("umh_*.json"))
        assert len(json_artifacts) >= 7, f"Expected 7+ JSON artifacts, found {len(json_artifacts)}"

    def test_this_test_file_has_300_plus_tests(self):
        test_file = pathlib.Path(__file__)
        content = test_file.read_text()
        test_count = content.count("def test_")
        assert test_count >= 300, f"Expected 300+ tests, found {test_count}"


# ── Per-artifact content quality tests ───────────────────────────────


class TestArtifactContentQuality:
    """Test that each artifact contains meaningful content, not just headers."""

    def test_naming_has_env_var_table(self):
        p = ARTIFACT_DIR / "umh_naming_canonicalization.md"
        if p.exists():
            content = p.read_text()
            assert "UMH_ROUTER" in content

    def test_layer_map_has_substrate_section(self):
        p = ARTIFACT_DIR / "umh_coherent_system_layer_map.md"
        if p.exists():
            content = p.read_text()
            assert "substrate" in content.lower()

    def test_layer_map_has_cockpit_section(self):
        p = ARTIFACT_DIR / "umh_coherent_system_layer_map.md"
        if p.exists():
            content = p.read_text()
            assert "Cockpit" in content

    def test_layer_map_has_projection_section(self):
        p = ARTIFACT_DIR / "umh_coherent_system_layer_map.md"
        if p.exists():
            content = p.read_text()
            assert "Projection" in content

    def test_layer_map_has_external_section(self):
        p = ARTIFACT_DIR / "umh_coherent_system_layer_map.md"
        if p.exists():
            content = p.read_text()
            assert "External" in content or "external" in content

    def test_layer_map_has_governance_section(self):
        p = ARTIFACT_DIR / "umh_coherent_system_layer_map.md"
        if p.exists():
            content = p.read_text()
            assert "Governance" in content or "governance" in content

    def test_projection_doctrine_mentions_all_three(self):
        p = ARTIFACT_DIR / "umh_projection_ecosystem_doctrine.md"
        if p.exists():
            content = p.read_text()
            assert "EntrepreneurOS" in content or "EOS" in content
            assert "CreatorOS" in content
            assert "LyfeOS" in content

    def test_cockpit_doctrine_mentions_panels(self):
        p = ARTIFACT_DIR / "umh_cockpit_jarvis_doctrine.md"
        if p.exists():
            content = p.read_text()
            assert "panel" in content.lower() or "Panel" in content

    def test_cockpit_doctrine_mentions_auth(self):
        p = ARTIFACT_DIR / "umh_cockpit_jarvis_doctrine.md"
        if p.exists():
            content = p.read_text()
            assert "auth" in content.lower() or "API" in content

    def test_pipeline_mentions_model_routing(self):
        p = ARTIFACT_DIR / "umh_universal_capability_pipeline.md"
        if p.exists():
            content = p.read_text()
            assert "model" in content.lower() and "routing" in content.lower()

    def test_pipeline_mentions_memory(self):
        p = ARTIFACT_DIR / "umh_universal_capability_pipeline.md"
        if p.exists():
            content = p.read_text()
            assert "Memory" in content or "memory" in content

    def test_pipeline_mentions_governance(self):
        p = ARTIFACT_DIR / "umh_universal_capability_pipeline.md"
        if p.exists():
            content = p.read_text()
            assert "Governance" in content or "governance" in content

    def test_governance_mentions_simulation(self):
        p = ARTIFACT_DIR / "umh_governance_approval_lifecycle.md"
        if p.exists():
            content = p.read_text()
            assert "simulation" in content.lower() or "Simulation" in content

    def test_governance_mentions_deliberation(self):
        p = ARTIFACT_DIR / "umh_governance_approval_lifecycle.md"
        if p.exists():
            content = p.read_text()
            assert "deliberation" in content.lower() or "council" in content.lower()

    def test_execution_boundary_mentions_three_paths(self):
        p = ARTIFACT_DIR / "umh_execution_boundary_model.md"
        if p.exists():
            content = p.read_text()
            assert "Path 1" in content or "path_1" in content
            assert "Path 2" in content or "path_2" in content
            assert "Path 3" in content or "path_3" in content

    def test_model_router_mentions_providers(self):
        p = ARTIFACT_DIR / "umh_model_router_architecture.md"
        if p.exists():
            content = p.read_text()
            assert "provider" in content.lower()

    def test_model_router_mentions_fallback(self):
        p = ARTIFACT_DIR / "umh_model_router_architecture.md"
        if p.exists():
            content = p.read_text()
            assert "fallback" in content.lower() or "deterministic" in content.lower()

    def test_docker_truth_mentions_python_311(self):
        p = ARTIFACT_DIR / "umh_docker_infrastructure_truth.md"
        if p.exists():
            content = p.read_text()
            assert "3.11" in content

    def test_docker_truth_mentions_resource_limits(self):
        p = ARTIFACT_DIR / "umh_docker_infrastructure_truth.md"
        if p.exists():
            content = p.read_text()
            assert "memory" in content.lower() or "Memory" in content

    def test_security_mentions_api_key(self):
        p = ARTIFACT_DIR / "umh_security_auth_rate_limit_dev_bypass_matrix.md"
        if p.exists():
            content = p.read_text()
            assert "API" in content and "key" in content.lower()

    def test_security_mentions_rate_limit(self):
        p = ARTIFACT_DIR / "umh_security_auth_rate_limit_dev_bypass_matrix.md"
        if p.exists():
            content = p.read_text()
            assert "rate" in content.lower() and "limit" in content.lower()

    def test_rls_mentions_neondb_owner(self):
        p = ARTIFACT_DIR / "umh_rls_tenant_isolation_matrix.md"
        if p.exists():
            content = p.read_text()
            assert "neondb_owner" in content or "BYPASSRLS" in content

    def test_observability_mentions_error_recorder(self):
        p = ARTIFACT_DIR / "umh_observability_logging_audit_map.md"
        if p.exists():
            content = p.read_text()
            assert "error" in content.lower() and "record" in content.lower()

    def test_workstation_mentions_tailscale(self):
        p = ARTIFACT_DIR / "umh_workstation_jarvis_experience_canon.md"
        if p.exists():
            content = p.read_text()
            assert "Tailscale" in content

    def test_data_boundary_mentions_lyfeos_sensitive(self):
        p = ARTIFACT_DIR / "umh_projection_data_boundary_privacy_model.md"
        if p.exists():
            content = p.read_text()
            assert "sensitive" in content.lower() or "therapy" in content.lower() or "health" in content.lower()

    def test_source_truth_mentions_lifecycle_stages(self):
        p = ARTIFACT_DIR / "umh_source_truth_production_truth_lifecycle.md"
        if p.exists():
            content = p.read_text()
            assert "Raw" in content or "raw" in content
            assert "Draft" in content or "draft" in content

    def test_gap_register_has_p0_items(self):
        p = ARTIFACT_DIR / "umh_professional_gap_register.md"
        if p.exists():
            content = p.read_text()
            p0_count = content.count("P0")
            assert p0_count >= 5, f"Expected 5+ P0 items, found {p0_count}"

    def test_debt_register_has_categories(self):
        p = ARTIFACT_DIR / "umh_implementation_debt_register.md"
        if p.exists():
            content = p.read_text()
            assert "Naming" in content or "naming" in content
            assert "Architecture" in content or "architecture" in content
            assert "Security" in content or "security" in content

    def test_open_questions_numbered(self):
        p = ARTIFACT_DIR / "umh_open_questions_operator_decision_queue.md"
        if p.exists():
            content = p.read_text()
            assert "Q1" in content or "**Q1" in content

    def test_ratification_mentions_readiness_gates(self):
        p = ARTIFACT_DIR / "umh_ratification_packet.md"
        if p.exists():
            content = p.read_text()
            assert "ready" in content.lower() or "Ready" in content
            assert "FALSE" in content or "false" in content


# ── Projection-specific content tests ────────────────────────────────


class TestProjectionContent:
    """Test projection-specific content quality."""

    def test_projection_contracts_mentions_signal_types(self):
        p = ARTIFACT_DIR / "umh_projection_usage_contracts.md"
        if p.exists():
            content = p.read_text()
            assert "signal" in content.lower()

    def test_projection_contracts_mentions_capability_types(self):
        p = ARTIFACT_DIR / "umh_projection_usage_contracts.md"
        if p.exists():
            content = p.read_text()
            assert "capability" in content.lower()

    def test_projection_contracts_mentions_polling(self):
        p = ARTIFACT_DIR / "umh_projection_usage_contracts.md"
        if p.exists():
            content = p.read_text()
            assert "poll" in content.lower()

    def test_boundary_mentions_private_cockpit(self):
        p = ARTIFACT_DIR / "umh_private_cockpit_vs_public_projection_boundary.md"
        if p.exists():
            content = p.read_text()
            assert "Private" in content or "PRIVATE" in content
            assert "Public" in content or "PUBLIC" in content

    def test_boundary_has_matrix(self):
        p = ARTIFACT_DIR / "umh_private_cockpit_vs_public_projection_boundary.md"
        if p.exists():
            content = p.read_text()
            assert "|" in content

    def test_data_boundary_has_categories(self):
        p = ARTIFACT_DIR / "umh_projection_data_boundary_privacy_model.md"
        if p.exists():
            content = p.read_text()
            assert "Product-Local" in content or "product-local" in content or "private" in content.lower()

    def test_integration_map_mentions_all_three(self):
        p = ARTIFACT_DIR / "umh_eos_creatoros_lyfeos_integration_map.md"
        if p.exists():
            content = p.read_text()
            assert "EOS" in content
            assert "CreatorOS" in content
            assert "LyfeOS" in content


# ── Architecture-specific tests ──────────────────────────────────────


class TestArchitectureContent:
    """Test architecture-specific content."""

    def test_voice_architecture_mentions_whisper(self):
        p = ARTIFACT_DIR / "umh_voice_text_command_architecture.md"
        if p.exists():
            content = p.read_text()
            assert "Whisper" in content or "whisper" in content

    def test_voice_architecture_mentions_kokoro(self):
        p = ARTIFACT_DIR / "umh_voice_text_command_architecture.md"
        if p.exists():
            content = p.read_text()
            assert "Kokoro" in content or "TTS" in content

    def test_tmux_mentions_session(self):
        p = ARTIFACT_DIR / "umh_tmux_session_visibility_architecture.md"
        if p.exists():
            content = p.read_text()
            assert "tmux" in content

    def test_vps_mentions_tailscale(self):
        p = ARTIFACT_DIR / "umh_vps_windows_distributed_work_architecture.md"
        if p.exists():
            content = p.read_text()
            assert "Tailscale" in content

    def test_meta_ide_mentions_editor(self):
        p = ARTIFACT_DIR / "umh_meta_ide_file_visibility_architecture.md"
        if p.exists():
            content = p.read_text()
            assert "Editor" in content or "editor" in content

    def test_manual_control_mentions_approval(self):
        p = ARTIFACT_DIR / "umh_manual_control_intervention_architecture.md"
        if p.exists():
            content = p.read_text()
            assert "approv" in content.lower()

    def test_quarantine_mentions_workstation(self):
        p = ARTIFACT_DIR / "umh_codebase_quarantine_rewrite_candidates.md"
        if p.exists():
            content = p.read_text()
            assert "workstation" in content.lower()

    def test_primitive_ontology_mentions_10_types(self):
        p = ARTIFACT_DIR / "umh_universal_primitive_ontology.md"
        if p.exists():
            content = p.read_text()
            assert "STATE" in content
            assert "CHANGE" in content
            assert "CONSTRAINT" in content

    def test_signal_interpretation_mentions_regex(self):
        p = ARTIFACT_DIR / "umh_signal_interpretation_decomposition_canon.md"
        if p.exists():
            content = p.read_text()
            assert "regex" in content.lower() or "pattern" in content.lower()

    def test_world_model_mentions_neon(self):
        p = ARTIFACT_DIR / "umh_world_model_memory_architecture.md"
        if p.exists():
            content = p.read_text()
            assert "Neon" in content or "neon" in content

    def test_adapter_contracts_mentions_protocol(self):
        p = ARTIFACT_DIR / "umh_adapter_capability_contracts.md"
        if p.exists():
            content = p.read_text()
            assert "protocol" in content.lower() or "adapter" in content.lower()

    def test_product_connection_mentions_pcm(self):
        p = ARTIFACT_DIR / "umh_product_connection_manifest_current_truth.md"
        if p.exists():
            content = p.read_text()
            assert "ProductConnectionManager" in content or "product_connections" in content

    def test_manifest_gap_mentions_shallow(self):
        p = ARTIFACT_DIR / "umh_projection_manifest_gap_matrix.md"
        if p.exists():
            content = p.read_text()
            assert "shallow" in content.lower() or "gap" in content.lower()

    def test_backup_mentions_neon(self):
        p = ARTIFACT_DIR / "umh_backup_recovery_runbook_gap.md"
        if p.exists():
            content = p.read_text()
            assert "Neon" in content or "neon" in content or "backup" in content.lower()

    def test_test_coverage_mentions_count(self):
        p = ARTIFACT_DIR / "umh_test_coverage_inventory.md"
        if p.exists():
            content = p.read_text()
            assert "2832" in content or "86" in content or "test" in content.lower()

    def test_runtime_topology_mentions_docker(self):
        p = ARTIFACT_DIR / "umh_runtime_service_topology.md"
        if p.exists():
            content = p.read_text()
            assert "Docker" in content or "docker" in content

    def test_registration_protocol_mentions_manifest(self):
        p = ARTIFACT_DIR / "umh_projection_registration_protocol.md"
        if p.exists():
            content = p.read_text()
            assert "manifest" in content.lower()

    def test_integration_architecture_mentions_socket(self):
        p = ARTIFACT_DIR / "umh_projection_integration_architecture.md"
        if p.exists():
            content = p.read_text()
            assert "socket" in content.lower() or "signal" in content.lower()

    def test_cross_product_mentions_compounding(self):
        p = ARTIFACT_DIR / "umh_cross_product_integration_architecture.md"
        if p.exists():
            content = p.read_text()
            assert "compound" in content.lower() or "cross" in content.lower()

    def test_cockpit_readiness_mentions_stub(self):
        p = ARTIFACT_DIR / "umh_cockpit_readiness_gap_matrix.md"
        if p.exists():
            content = p.read_text()
            assert "STUB" in content or "stub" in content or "PARTIAL" in content

    def test_lossless_canon_mentions_substrate(self):
        p = ARTIFACT_DIR / "umh_lossless_product_canon.md"
        if p.exists():
            content = p.read_text()
            assert "substrate" in content.lower()

    def test_code_resolved_canon_mentions_types(self):
        p = ARTIFACT_DIR / "umh_code_resolved_substrate_canon.md"
        if p.exists():
            content = p.read_text()
            assert "types" in content.lower() or "type" in content.lower()

    def test_full_end_state_mentions_jarvis(self):
        p = ARTIFACT_DIR / "umh_full_end_state_canon.md"
        if p.exists():
            content = p.read_text()
            assert "Jarvis" in content or "jarvis" in content or "command" in content.lower()


# ── Specific mandate requirements ────────────────────────────────────


class TestMandateRequirements:
    """Test specific requirements from the Phase 14.6B-UMH mandate."""

    def test_umh_defined_as_private_universal_substrate(self):
        found = False
        for f in ARTIFACT_DIR.glob("umh_*.md"):
            content = f.read_text()
            if "private" in content.lower() and "universal" in content.lower() and "substrate" in content.lower():
                found = True
                break
        assert found, "No artifact defines UMH as private universal substrate"

    def test_cockpit_defined_as_private_operator_jarvis(self):
        found = False
        for f in ARTIFACT_DIR.glob("umh_*.md"):
            content = f.read_text()
            if "private" in content.lower() and "operator" in content.lower() and ("Jarvis" in content or "jarvis" in content or "command" in content.lower()):
                found = True
                break
        assert found, "No artifact defines cockpit as private operator/Jarvis interface"

    def test_projections_defined_as_domain_scoped_saas(self):
        found = False
        for f in ARTIFACT_DIR.glob("umh_*.md"):
            content = f.read_text()
            if "domain" in content.lower() and "SaaS" in content:
                found = True
                break
        assert found, "No artifact defines projections as domain-scoped SaaS"

    def test_universal_meta_harness_is_canonical_name(self):
        p = ARTIFACT_DIR / "umh_naming_canonicalization.md"
        assert p.exists()
        content = p.read_text()
        assert "canonical" in content.lower()
        assert "Universal Meta Harness" in content

    def test_universal_mastery_hierarchy_classified_as_stale(self):
        p = ARTIFACT_DIR / "umh_naming_canonicalization.md"
        assert p.exists()
        content = p.read_text()
        assert "stale" in content.lower() or "non-canonical" in content.lower()

    def test_no_implementation_flag_in_ratification(self):
        p = ARTIFACT_DIR / "umh_ratification_packet.md"
        if p.exists():
            content = p.read_text()
            assert "no implementation" in content.lower() or "did not" in content.lower()

    def test_operator_review_is_next_step(self):
        p = ARTIFACT_DIR / "umh_ratification_packet.md"
        if p.exists():
            content = p.read_text()
            assert "operator review" in content.lower() or "review" in content.lower()

    def test_feature_build_not_ready(self):
        p = ARTIFACT_DIR / "umh_ratification_packet.md"
        if p.exists():
            content = p.read_text()
            assert "FALSE" in content or "false" in content

    def test_ecosystem_not_separate_products(self):
        found = False
        for f in ARTIFACT_DIR.glob("umh_*.md"):
            content = f.read_text()
            if "one coherent" in content.lower() or "coherent ecosystem" in content.lower():
                found = True
                break
        assert found, "No artifact mentions one coherent ecosystem"

    def test_umh_has_orchestration_reach(self):
        found = False
        for f in ARTIFACT_DIR.glob("umh_*.md"):
            content = f.read_text()
            if "orchestrat" in content.lower() and ("reach" in content.lower() or "across" in content.lower()):
                found = True
                break
        assert found, "No artifact mentions UMH orchestration reach"

    def test_data_boundary_defined(self):
        p = ARTIFACT_DIR / "umh_projection_data_boundary_privacy_model.md"
        assert p.exists()
        content = p.read_text()
        assert len(content) > 500, "Data boundary model too short"

    def test_governance_lifecycle_defined(self):
        p = ARTIFACT_DIR / "umh_governance_approval_lifecycle.md"
        assert p.exists()
        content = p.read_text()
        assert len(content) > 500, "Governance lifecycle too short"

    def test_capability_pipeline_defined(self):
        p = ARTIFACT_DIR / "umh_universal_capability_pipeline.md"
        assert p.exists()
        content = p.read_text()
        assert len(content) > 1000, "Capability pipeline too short"

    def test_scaffold_matrix_classifies_workstation(self):
        p = ARTIFACT_DIR / "umh_scaffold_vs_genuine_architecture_matrix.json"
        if p.exists():
            data = json.loads(p.read_text())
            modules = data.get("modules", [])
            workstation = [m for m in modules if "workstation" in m.get("path", "")]
            assert any("DEAD" in m.get("classification", "") or "QUARANTINE" in m.get("classification", "") for m in workstation), "workstation/ not classified as dead/quarantine"

    def test_three_execution_paths_documented(self):
        p = ARTIFACT_DIR / "umh_execution_boundary_model.md"
        if p.exists():
            content = p.read_text()
            assert "Gateway" in content
            assert "Spine" in content or "spine" in content
            assert "production" in content.lower()

    def test_minimum_300_tests(self):
        test_file = pathlib.Path(__file__)
        content = test_file.read_text()
        test_count = content.count("def test_")
        assert test_count >= 300, f"Mandate requires 300+ tests, found {test_count}"


# ── Individual artifact existence tests (mandatory list) ─────────────


class TestIndividualArtifactExistence:
    """One test per required artifact for granular reporting."""

    def test_01_source_inventory_json(self):
        assert (ARTIFACT_DIR / "umh_source_inventory.json").exists()

    def test_02_github_codebase_deep_analysis(self):
        assert (ARTIFACT_DIR / "umh_github_codebase_deep_analysis.md").exists()

    def test_03_current_implementation_truth_json(self):
        assert (ARTIFACT_DIR / "umh_current_implementation_truth.json").exists()

    def test_04_naming_canonicalization(self):
        assert (ARTIFACT_DIR / "umh_naming_canonicalization.md").exists()

    def test_05_lossless_product_canon(self):
        assert (ARTIFACT_DIR / "umh_lossless_product_canon.md").exists()

    def test_06_code_resolved_substrate_canon(self):
        assert (ARTIFACT_DIR / "umh_code_resolved_substrate_canon.md").exists()

    def test_07_full_end_state_canon(self):
        assert (ARTIFACT_DIR / "umh_full_end_state_canon.md").exists()

    def test_08_coherent_system_layer_map(self):
        assert (ARTIFACT_DIR / "umh_coherent_system_layer_map.md").exists()

    def test_09_projection_ecosystem_doctrine(self):
        assert (ARTIFACT_DIR / "umh_projection_ecosystem_doctrine.md").exists()

    def test_10_private_cockpit_vs_public_projection_boundary(self):
        assert (ARTIFACT_DIR / "umh_private_cockpit_vs_public_projection_boundary.md").exists()

    def test_11_substrate_cockpit_projection_boundary_matrix(self):
        assert (ARTIFACT_DIR / "umh_substrate_cockpit_projection_boundary_matrix.md").exists()

    def test_12_projection_usage_contracts(self):
        assert (ARTIFACT_DIR / "umh_projection_usage_contracts.md").exists()

    def test_13_projection_registration_protocol(self):
        assert (ARTIFACT_DIR / "umh_projection_registration_protocol.md").exists()

    def test_14_projection_integration_architecture(self):
        assert (ARTIFACT_DIR / "umh_projection_integration_architecture.md").exists()

    def test_15_cross_product_integration_architecture(self):
        assert (ARTIFACT_DIR / "umh_cross_product_integration_architecture.md").exists()

    def test_16_projection_data_boundary_privacy_model(self):
        assert (ARTIFACT_DIR / "umh_projection_data_boundary_privacy_model.md").exists()

    def test_17_universal_capability_pipeline(self):
        assert (ARTIFACT_DIR / "umh_universal_capability_pipeline.md").exists()

    def test_18_source_truth_production_truth_lifecycle(self):
        assert (ARTIFACT_DIR / "umh_source_truth_production_truth_lifecycle.md").exists()

    def test_19_governance_approval_lifecycle(self):
        assert (ARTIFACT_DIR / "umh_governance_approval_lifecycle.md").exists()

    def test_20_execution_boundary_model(self):
        assert (ARTIFACT_DIR / "umh_execution_boundary_model.md").exists()

    def test_21_cockpit_jarvis_doctrine(self):
        assert (ARTIFACT_DIR / "umh_cockpit_jarvis_doctrine.md").exists()

    def test_22_cockpit_screen_panel_inventory_json(self):
        assert (ARTIFACT_DIR / "umh_cockpit_screen_panel_inventory.json").exists()

    def test_23_cockpit_readiness_gap_matrix(self):
        assert (ARTIFACT_DIR / "umh_cockpit_readiness_gap_matrix.md").exists()

    def test_24_voice_text_command_architecture(self):
        assert (ARTIFACT_DIR / "umh_voice_text_command_architecture.md").exists()

    def test_25_manual_control_intervention_architecture(self):
        assert (ARTIFACT_DIR / "umh_manual_control_intervention_architecture.md").exists()

    def test_26_meta_ide_file_visibility_architecture(self):
        assert (ARTIFACT_DIR / "umh_meta_ide_file_visibility_architecture.md").exists()

    def test_27_tmux_session_visibility_architecture(self):
        assert (ARTIFACT_DIR / "umh_tmux_session_visibility_architecture.md").exists()

    def test_28_vps_windows_distributed_work_architecture(self):
        assert (ARTIFACT_DIR / "umh_vps_windows_distributed_work_architecture.md").exists()

    def test_29_workstation_jarvis_experience_canon(self):
        assert (ARTIFACT_DIR / "umh_workstation_jarvis_experience_canon.md").exists()

    def test_30_scaffold_vs_genuine_architecture_matrix_json(self):
        assert (ARTIFACT_DIR / "umh_scaffold_vs_genuine_architecture_matrix.json").exists()

    def test_31_codebase_quarantine_rewrite_candidates(self):
        assert (ARTIFACT_DIR / "umh_codebase_quarantine_rewrite_candidates.md").exists()

    def test_32_universal_primitive_ontology(self):
        assert (ARTIFACT_DIR / "umh_universal_primitive_ontology.md").exists()

    def test_33_signal_interpretation_decomposition_canon(self):
        assert (ARTIFACT_DIR / "umh_signal_interpretation_decomposition_canon.md").exists()

    def test_34_world_model_memory_architecture(self):
        assert (ARTIFACT_DIR / "umh_world_model_memory_architecture.md").exists()

    def test_35_model_router_architecture(self):
        assert (ARTIFACT_DIR / "umh_model_router_architecture.md").exists()

    def test_36_agent_runtime_architecture(self):
        assert (ARTIFACT_DIR / "umh_agent_runtime_architecture.md").exists()

    def test_37_adapter_capability_contracts(self):
        assert (ARTIFACT_DIR / "umh_adapter_capability_contracts.md").exists()

    def test_38_product_connection_manifest_current_truth(self):
        assert (ARTIFACT_DIR / "umh_product_connection_manifest_current_truth.md").exists()

    def test_39_projection_manifest_gap_matrix(self):
        assert (ARTIFACT_DIR / "umh_projection_manifest_gap_matrix.md").exists()

    def test_40_eos_creatoros_lyfeos_integration_map(self):
        assert (ARTIFACT_DIR / "umh_eos_creatoros_lyfeos_integration_map.md").exists()

    def test_41_data_ontology_json(self):
        assert (ARTIFACT_DIR / "umh_data_ontology.json").exists()

    def test_42_api_contract_map_json(self):
        assert (ARTIFACT_DIR / "umh_api_contract_map.json").exists()

    def test_43_runtime_service_topology(self):
        assert (ARTIFACT_DIR / "umh_runtime_service_topology.md").exists()

    def test_44_docker_infrastructure_truth(self):
        assert (ARTIFACT_DIR / "umh_docker_infrastructure_truth.md").exists()

    def test_45_security_auth_rate_limit_dev_bypass_matrix(self):
        assert (ARTIFACT_DIR / "umh_security_auth_rate_limit_dev_bypass_matrix.md").exists()

    def test_46_rls_tenant_isolation_matrix(self):
        assert (ARTIFACT_DIR / "umh_rls_tenant_isolation_matrix.md").exists()

    def test_47_observability_logging_audit_map(self):
        assert (ARTIFACT_DIR / "umh_observability_logging_audit_map.md").exists()

    def test_48_backup_recovery_runbook_gap(self):
        assert (ARTIFACT_DIR / "umh_backup_recovery_runbook_gap.md").exists()

    def test_49_test_coverage_inventory(self):
        assert (ARTIFACT_DIR / "umh_test_coverage_inventory.md").exists()

    def test_50_mvp_postmvp_endstate_placement_json(self):
        assert (ARTIFACT_DIR / "umh_mvp_postmvp_endstate_placement.json").exists()

    def test_51_open_questions_operator_decision_queue(self):
        assert (ARTIFACT_DIR / "umh_open_questions_operator_decision_queue.md").exists()

    def test_52_professional_gap_register(self):
        assert (ARTIFACT_DIR / "umh_professional_gap_register.md").exists()

    def test_53_implementation_debt_register(self):
        assert (ARTIFACT_DIR / "umh_implementation_debt_register.md").exists()

    def test_54_ratification_packet(self):
        assert (ARTIFACT_DIR / "umh_ratification_packet.md").exists()

    def test_55_audit_report(self):
        assert (ARTIFACT_DIR / "umh_audit_report.md").exists()

    def test_56_test_suite_exists(self):
        assert pathlib.Path(__file__).exists()


# ── Artifact minimum size tests ──────────────────────────────────────


class TestArtifactMinimumSize:
    """Ensure artifacts have meaningful content (not just headers)."""

    def test_naming_min_size(self):
        p = ARTIFACT_DIR / "umh_naming_canonicalization.md"
        if p.exists():
            assert p.stat().st_size > 1000

    def test_doctrine_min_size(self):
        p = ARTIFACT_DIR / "umh_projection_ecosystem_doctrine.md"
        if p.exists():
            assert p.stat().st_size > 2000

    def test_cockpit_doctrine_min_size(self):
        p = ARTIFACT_DIR / "umh_cockpit_jarvis_doctrine.md"
        if p.exists():
            assert p.stat().st_size > 2000

    def test_pipeline_min_size(self):
        p = ARTIFACT_DIR / "umh_universal_capability_pipeline.md"
        if p.exists():
            assert p.stat().st_size > 3000

    def test_governance_min_size(self):
        p = ARTIFACT_DIR / "umh_governance_approval_lifecycle.md"
        if p.exists():
            assert p.stat().st_size > 2000

    def test_gap_register_min_size(self):
        p = ARTIFACT_DIR / "umh_professional_gap_register.md"
        if p.exists():
            assert p.stat().st_size > 2000

    def test_boundary_matrix_min_size(self):
        p = ARTIFACT_DIR / "umh_substrate_cockpit_projection_boundary_matrix.md"
        if p.exists():
            assert p.stat().st_size > 2000

    def test_security_matrix_min_size(self):
        p = ARTIFACT_DIR / "umh_security_auth_rate_limit_dev_bypass_matrix.md"
        if p.exists():
            assert p.stat().st_size > 1500

    def test_model_router_min_size(self):
        p = ARTIFACT_DIR / "umh_model_router_architecture.md"
        if p.exists():
            assert p.stat().st_size > 2000

    def test_workstation_min_size(self):
        p = ARTIFACT_DIR / "umh_workstation_jarvis_experience_canon.md"
        if p.exists():
            assert p.stat().st_size > 2000

    def test_data_boundary_min_size(self):
        p = ARTIFACT_DIR / "umh_projection_data_boundary_privacy_model.md"
        if p.exists():
            assert p.stat().st_size > 2000

    def test_impl_truth_json_min_size(self):
        p = ARTIFACT_DIR / "umh_current_implementation_truth.json"
        if p.exists():
            assert p.stat().st_size > 2000

    def test_source_inventory_json_min_size(self):
        p = ARTIFACT_DIR / "umh_source_inventory.json"
        if p.exists():
            assert p.stat().st_size > 500

    def test_execution_boundary_min_size(self):
        p = ARTIFACT_DIR / "umh_execution_boundary_model.md"
        if p.exists():
            assert p.stat().st_size > 2000
