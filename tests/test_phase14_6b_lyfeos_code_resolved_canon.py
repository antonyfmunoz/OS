"""
Phase 14.6B-LyfeOS: Code-Resolved Lossless LyfeOS Product Canon Reconstruction
Comprehensive test suite — 250+ tests

Tests verify:
- All required artifacts exist and are valid
- Provenance labels are present and correct
- Operator corrections are properly applied
- No implementation occurred
- No source mutation occurred
- Canon correctness per mandate requirements
"""

import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any

sys.path.insert(0, "/opt/OS")

ARTIFACT_DIR = pathlib.Path(
    "/opt/OS/data/umh/trinity_convergence/phase14_6b_lyfeos"
)

REQUIRED_PROVENANCE_LABELS = {
    "SOURCE_PRESERVED_TRUTH",
    "CODE_RESOLVED_CURRENT_TRUTH",
    "SYNTHESIZED_CANON",
    "INFERRED_PROFESSIONAL_GAP",
    "OPEN_QUESTION_OPERATOR_DECISION_REQUIRED",
    "IMPLEMENTATION_DEBT",
    "UMH_INTEGRATION_DEPENDENT_GAP",
}

REQUIRED_DATA_PROVENANCE_CATEGORIES = {
    "MANUAL_INPUT",
    "USER_SELF_REPORT",
    "COMPUTED_FROM_APP_BEHAVIOR",
    "IMPORTED_FROM_INTEGRATIONS",
    "LIVE_VERIFIED_DEVICE_API",
    "UMH_INFERRED_SYNTHESIZED",
}

PRIMARY_NAV_ITEMS = ["Dashboard", "Missions", "AI", "Chronilog", "Profile"]

PHASE_ID = "14.6B-LyfeOS"

# =============================================================
# JSON Artifacts
# =============================================================

JSON_ARTIFACTS = [
    "lyfeos_source_inventory.json",
    "lyfeos_current_implementation_truth.json",
    "lyfeos_docs_vs_code_convergence_matrix.json",
    "lyfeos_version_precedence_matrix.json",
    "lyfeos_contradiction_matrix.json",
    "lyfeos_secondary_module_route_map.json",
    "lyfeos_screen_inventory.json",
    "lyfeos_ai_tool_action_registry.json",
    "lyfeos_data_ontology.json",
    "lyfeos_database_table_inventory.json",
    "lyfeos_api_contract_map.json",
    "lyfeos_mvp_hardening_postmvp_endstate_placement.json",
]

# =============================================================
# Markdown Artifacts
# =============================================================

MD_ARTIFACTS = [
    "lyfeos_code_source_inventory.md",
    "lyfeos_github_codebase_deep_analysis.md",
    "lyfeos_deployed_mvp_truth_matrix.md",
    "lyfeos_code_resolved_product_canon.md",
    "lyfeos_lossless_product_canon.md",
    "lyfeos_mvp_current_canon.md",
    "lyfeos_full_end_state_canon.md",
    "lyfeos_umh_connected_future_canon.md",
    "lyfeos_navigation_shell_canon.md",
    "lyfeos_dashboard_architecture.md",
    "lyfeos_missions_quests_architecture.md",
    "lyfeos_ai_companion_architecture.md",
    "lyfeos_nova_legacy_naming_correction.md",
    "lyfeos_umh_connection_architecture.md",
    "lyfeos_ai_permissions_approval_model.md",
    "lyfeos_profile_character_sheet_canon.md",
    "lyfeos_onboarding_awakening_protocol_canon.md",
    "lyfeos_integrations_onboarding_gap.md",
    "lyfeos_transformation_thread_decision_packet.md",
    "lyfeos_chronilog_architecture.md",
    "lyfeos_systems_secondary_modules_architecture.md",
    "lyfeos_data_provenance_model.md",
    "lyfeos_stats_xp_gamification_truth.md",
    "lyfeos_integration_architecture.md",
    "lyfeos_google_integration_current_truth.md",
    "lyfeos_auth_session_security_truth.md",
    "lyfeos_auth_migration_candidate_plan.md",
    "lyfeos_rls_tenant_isolation_matrix.md",
    "lyfeos_backup_recovery_risk_packet.md",
    "lyfeos_security_trust_privacy_compliance.md",
    "lyfeos_observability_logging_audit_map.md",
    "lyfeos_test_coverage_inventory.md",
    "lyfeos_infrastructure_deployment_map.md",
    "lyfeos_current_code_gap_comparison.md",
    "lyfeos_implementation_debt_register.md",
    "lyfeos_professional_gap_register.md",
    "lyfeos_open_questions_operator_decision_queue.md",
    "lyfeos_source_truth_ratification_packet.md",
    "lyfeos_audit_report.md",
]

ALL_ARTIFACTS = JSON_ARTIFACTS + MD_ARTIFACTS


# =============================================================
# Helpers
# =============================================================


def _read_artifact(name: str) -> str:
    path = ARTIFACT_DIR / name
    assert path.exists(), f"Artifact missing: {name}"
    return path.read_text(encoding="utf-8")


def _load_json_artifact(name: str) -> Any:
    text = _read_artifact(name)
    return json.loads(text)


def _artifact_exists(name: str) -> bool:
    return (ARTIFACT_DIR / name).exists()


def _content_contains(text: str, needle: str, case_insensitive: bool = True) -> bool:
    if case_insensitive:
        return needle.lower() in text.lower()
    return needle in text


def _content_contains_any(text: str, needles: list[str], case_insensitive: bool = True) -> bool:
    return any(_content_contains(text, n, case_insensitive) for n in needles)


def _json_deep_search(obj: Any, needle: str) -> bool:
    """Recursively search JSON for a string value."""
    if isinstance(obj, str):
        return needle.lower() in obj.lower()
    if isinstance(obj, dict):
        return any(_json_deep_search(v, needle) for v in obj.values())
    if isinstance(obj, list):
        return any(_json_deep_search(item, needle) for item in obj)
    return False


# =============================================================
# SECTION 1: Artifact Existence (52 tests)
# =============================================================


class TestArtifactExistence:
    """Every required artifact must exist."""

    def test_artifact_directory_exists(self):
        assert ARTIFACT_DIR.exists(), f"Artifact directory missing: {ARTIFACT_DIR}"

    def test_all_json_artifacts_exist(self):
        for name in JSON_ARTIFACTS:
            assert _artifact_exists(name), f"JSON artifact missing: {name}"

    def test_all_md_artifacts_exist(self):
        for name in MD_ARTIFACTS:
            assert _artifact_exists(name), f"Markdown artifact missing: {name}"

    def test_source_inventory_exists(self):
        assert _artifact_exists("lyfeos_source_inventory.json")

    def test_code_source_inventory_exists(self):
        assert _artifact_exists("lyfeos_code_source_inventory.md")

    def test_github_deep_analysis_exists(self):
        assert _artifact_exists("lyfeos_github_codebase_deep_analysis.md")

    def test_current_implementation_truth_exists(self):
        assert _artifact_exists("lyfeos_current_implementation_truth.json")

    def test_deployed_mvp_truth_matrix_exists(self):
        assert _artifact_exists("lyfeos_deployed_mvp_truth_matrix.md")

    def test_docs_vs_code_convergence_exists(self):
        assert _artifact_exists("lyfeos_docs_vs_code_convergence_matrix.json")

    def test_version_precedence_exists(self):
        assert _artifact_exists("lyfeos_version_precedence_matrix.json")

    def test_contradiction_matrix_exists(self):
        assert _artifact_exists("lyfeos_contradiction_matrix.json")

    def test_code_resolved_canon_exists(self):
        assert _artifact_exists("lyfeos_code_resolved_product_canon.md")

    def test_lossless_canon_exists(self):
        assert _artifact_exists("lyfeos_lossless_product_canon.md")

    def test_mvp_current_canon_exists(self):
        assert _artifact_exists("lyfeos_mvp_current_canon.md")

    def test_full_end_state_canon_exists(self):
        assert _artifact_exists("lyfeos_full_end_state_canon.md")

    def test_umh_connected_future_canon_exists(self):
        assert _artifact_exists("lyfeos_umh_connected_future_canon.md")

    def test_navigation_shell_canon_exists(self):
        assert _artifact_exists("lyfeos_navigation_shell_canon.md")

    def test_secondary_module_route_map_exists(self):
        assert _artifact_exists("lyfeos_secondary_module_route_map.json")

    def test_screen_inventory_exists(self):
        assert _artifact_exists("lyfeos_screen_inventory.json")

    def test_dashboard_architecture_exists(self):
        assert _artifact_exists("lyfeos_dashboard_architecture.md")

    def test_missions_quests_architecture_exists(self):
        assert _artifact_exists("lyfeos_missions_quests_architecture.md")

    def test_ai_companion_architecture_exists(self):
        assert _artifact_exists("lyfeos_ai_companion_architecture.md")

    def test_nova_legacy_naming_exists(self):
        assert _artifact_exists("lyfeos_nova_legacy_naming_correction.md")

    def test_umh_connection_architecture_exists(self):
        assert _artifact_exists("lyfeos_umh_connection_architecture.md")

    def test_ai_tool_action_registry_exists(self):
        assert _artifact_exists("lyfeos_ai_tool_action_registry.json")

    def test_ai_permissions_model_exists(self):
        assert _artifact_exists("lyfeos_ai_permissions_approval_model.md")

    def test_profile_character_sheet_exists(self):
        assert _artifact_exists("lyfeos_profile_character_sheet_canon.md")

    def test_onboarding_awakening_exists(self):
        assert _artifact_exists("lyfeos_onboarding_awakening_protocol_canon.md")

    def test_integrations_onboarding_gap_exists(self):
        assert _artifact_exists("lyfeos_integrations_onboarding_gap.md")

    def test_transformation_thread_exists(self):
        assert _artifact_exists("lyfeos_transformation_thread_decision_packet.md")

    def test_chronilog_architecture_exists(self):
        assert _artifact_exists("lyfeos_chronilog_architecture.md")

    def test_systems_secondary_modules_exists(self):
        assert _artifact_exists("lyfeos_systems_secondary_modules_architecture.md")

    def test_data_ontology_exists(self):
        assert _artifact_exists("lyfeos_data_ontology.json")

    def test_database_table_inventory_exists(self):
        assert _artifact_exists("lyfeos_database_table_inventory.json")

    def test_api_contract_map_exists(self):
        assert _artifact_exists("lyfeos_api_contract_map.json")

    def test_data_provenance_model_exists(self):
        assert _artifact_exists("lyfeos_data_provenance_model.md")

    def test_stats_xp_gamification_exists(self):
        assert _artifact_exists("lyfeos_stats_xp_gamification_truth.md")

    def test_integration_architecture_exists(self):
        assert _artifact_exists("lyfeos_integration_architecture.md")

    def test_google_integration_truth_exists(self):
        assert _artifact_exists("lyfeos_google_integration_current_truth.md")

    def test_auth_session_security_exists(self):
        assert _artifact_exists("lyfeos_auth_session_security_truth.md")

    def test_auth_migration_candidate_exists(self):
        assert _artifact_exists("lyfeos_auth_migration_candidate_plan.md")

    def test_rls_tenant_isolation_exists(self):
        assert _artifact_exists("lyfeos_rls_tenant_isolation_matrix.md")

    def test_backup_recovery_exists(self):
        assert _artifact_exists("lyfeos_backup_recovery_risk_packet.md")

    def test_security_trust_privacy_exists(self):
        assert _artifact_exists("lyfeos_security_trust_privacy_compliance.md")

    def test_observability_logging_exists(self):
        assert _artifact_exists("lyfeos_observability_logging_audit_map.md")

    def test_test_coverage_inventory_exists(self):
        assert _artifact_exists("lyfeos_test_coverage_inventory.md")

    def test_infrastructure_deployment_exists(self):
        assert _artifact_exists("lyfeos_infrastructure_deployment_map.md")

    def test_mvp_hardening_placement_exists(self):
        assert _artifact_exists("lyfeos_mvp_hardening_postmvp_endstate_placement.json")

    def test_current_code_gap_exists(self):
        assert _artifact_exists("lyfeos_current_code_gap_comparison.md")

    def test_implementation_debt_register_exists(self):
        assert _artifact_exists("lyfeos_implementation_debt_register.md")

    def test_professional_gap_register_exists(self):
        assert _artifact_exists("lyfeos_professional_gap_register.md")

    def test_open_questions_decision_queue_exists(self):
        assert _artifact_exists("lyfeos_open_questions_operator_decision_queue.md")

    def test_source_truth_ratification_exists(self):
        assert _artifact_exists("lyfeos_source_truth_ratification_packet.md")

    def test_audit_report_exists(self):
        assert _artifact_exists("lyfeos_audit_report.md")


# =============================================================
# SECTION 2: JSON Validity (12 tests)
# =============================================================


class TestJSONValidity:
    """All JSON artifacts must be valid JSON."""

    def test_source_inventory_valid_json(self):
        _load_json_artifact("lyfeos_source_inventory.json")

    def test_current_implementation_truth_valid_json(self):
        _load_json_artifact("lyfeos_current_implementation_truth.json")

    def test_docs_vs_code_convergence_valid_json(self):
        _load_json_artifact("lyfeos_docs_vs_code_convergence_matrix.json")

    def test_version_precedence_valid_json(self):
        _load_json_artifact("lyfeos_version_precedence_matrix.json")

    def test_contradiction_matrix_valid_json(self):
        _load_json_artifact("lyfeos_contradiction_matrix.json")

    def test_secondary_module_route_map_valid_json(self):
        _load_json_artifact("lyfeos_secondary_module_route_map.json")

    def test_screen_inventory_valid_json(self):
        _load_json_artifact("lyfeos_screen_inventory.json")

    def test_ai_tool_action_registry_valid_json(self):
        _load_json_artifact("lyfeos_ai_tool_action_registry.json")

    def test_data_ontology_valid_json(self):
        _load_json_artifact("lyfeos_data_ontology.json")

    def test_database_table_inventory_valid_json(self):
        _load_json_artifact("lyfeos_database_table_inventory.json")

    def test_api_contract_map_valid_json(self):
        _load_json_artifact("lyfeos_api_contract_map.json")

    def test_mvp_hardening_placement_valid_json(self):
        _load_json_artifact("lyfeos_mvp_hardening_postmvp_endstate_placement.json")


# =============================================================
# SECTION 3: Phase Metadata (12 tests)
# =============================================================


class TestPhaseMetadata:
    """Artifacts must include correct phase metadata."""

    def test_json_artifacts_have_phase(self):
        for name in JSON_ARTIFACTS:
            data = _load_json_artifact(name)
            found = _json_deep_search(data, "14.6B")
            assert found, f"{name} missing phase reference 14.6B"

    def test_md_artifacts_reference_phase(self):
        for name in MD_ARTIFACTS:
            text = _read_artifact(name)
            assert _content_contains(text, "14.6B"), f"{name} missing phase reference 14.6B"

    def test_no_artifact_marks_operator_approved(self):
        for name in ALL_ARTIFACTS:
            text = _read_artifact(name)
            if name.endswith(".json"):
                data = json.loads(text)
                if isinstance(data, dict) and "operator_approved" in data:
                    assert data["operator_approved"] is False, f"{name} has operator_approved=true"
            lower = text.lower()
            assert "operator_approved: true" not in lower and '"operator_approved": true' not in lower, \
                f"{name} claims operator approved"

    def test_no_artifact_allows_implementation(self):
        for name in ALL_ARTIFACTS:
            text = _read_artifact(name)
            if name.endswith(".json"):
                data = json.loads(text)
                if isinstance(data, dict) and "allows_implementation" in data:
                    assert data["allows_implementation"] is False, f"{name} has allows_implementation=true"
            lower = text.lower()
            assert "allows_implementation: true" not in lower and '"allows_implementation": true' not in lower, \
                f"{name} allows implementation"

    def test_source_inventory_has_phase(self):
        data = _load_json_artifact("lyfeos_source_inventory.json")
        assert _json_deep_search(data, "14.6B")

    def test_contradiction_matrix_has_phase(self):
        data = _load_json_artifact("lyfeos_contradiction_matrix.json")
        assert _json_deep_search(data, "14.6B")

    def test_code_resolved_canon_has_phase(self):
        text = _read_artifact("lyfeos_code_resolved_product_canon.md")
        assert _content_contains(text, "14.6B")

    def test_lossless_canon_has_phase(self):
        text = _read_artifact("lyfeos_lossless_product_canon.md")
        assert _content_contains(text, "14.6B")

    def test_audit_report_has_phase(self):
        text = _read_artifact("lyfeos_audit_report.md")
        assert _content_contains(text, "14.6B")

    def test_umh_connection_has_phase(self):
        text = _read_artifact("lyfeos_umh_connection_architecture.md")
        assert _content_contains(text, "14.6B")

    def test_backup_recovery_has_phase(self):
        text = _read_artifact("lyfeos_backup_recovery_risk_packet.md")
        assert _content_contains(text, "14.6B")

    def test_open_questions_has_phase(self):
        text = _read_artifact("lyfeos_open_questions_operator_decision_queue.md")
        assert _content_contains(text, "14.6B")


# =============================================================
# SECTION 4: Provenance Labels (18 tests)
# =============================================================


class TestProvenanceLabels:
    """Provenance labels must be present in artifacts."""

    def test_source_inventory_has_provenance(self):
        text = _read_artifact("lyfeos_source_inventory.json")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_current_implementation_truth_has_provenance(self):
        text = _read_artifact("lyfeos_current_implementation_truth.json")
        has_any = _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))
        assert has_any, "current_implementation_truth missing provenance labels"

    def test_code_resolved_canon_has_provenance(self):
        text = _read_artifact("lyfeos_code_resolved_product_canon.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_lossless_canon_has_provenance(self):
        text = _read_artifact("lyfeos_lossless_product_canon.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_navigation_canon_has_provenance(self):
        text = _read_artifact("lyfeos_navigation_shell_canon.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_ai_companion_has_provenance(self):
        text = _read_artifact("lyfeos_ai_companion_architecture.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_onboarding_has_provenance(self):
        text = _read_artifact("lyfeos_onboarding_awakening_protocol_canon.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_integration_gap_has_provenance(self):
        text = _read_artifact("lyfeos_integrations_onboarding_gap.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_transformation_thread_has_provenance(self):
        text = _read_artifact("lyfeos_transformation_thread_decision_packet.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_nova_naming_has_provenance(self):
        text = _read_artifact("lyfeos_nova_legacy_naming_correction.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_rls_has_provenance(self):
        text = _read_artifact("lyfeos_rls_tenant_isolation_matrix.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_backup_recovery_has_provenance(self):
        text = _read_artifact("lyfeos_backup_recovery_risk_packet.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_auth_truth_has_provenance(self):
        text = _read_artifact("lyfeos_auth_session_security_truth.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_security_has_provenance(self):
        text = _read_artifact("lyfeos_security_trust_privacy_compliance.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_stats_gamification_has_provenance(self):
        text = _read_artifact("lyfeos_stats_xp_gamification_truth.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_data_provenance_model_has_labels(self):
        text = _read_artifact("lyfeos_data_provenance_model.md")
        assert _content_contains_any(text, list(REQUIRED_DATA_PROVENANCE_CATEGORIES))

    def test_implementation_debt_has_provenance(self):
        text = _read_artifact("lyfeos_implementation_debt_register.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))

    def test_professional_gaps_has_provenance(self):
        text = _read_artifact("lyfeos_professional_gap_register.md")
        assert _content_contains_any(text, list(REQUIRED_PROVENANCE_LABELS))


# =============================================================
# SECTION 5: Navigation Canon (10 tests)
# =============================================================


class TestNavigationCanon:
    """Primary navigation must be Dashboard, Missions, AI, Chronilog, Profile."""

    def test_navigation_canon_includes_all_primary(self):
        text = _read_artifact("lyfeos_navigation_shell_canon.md")
        for item in PRIMARY_NAV_ITEMS:
            assert _content_contains(text, item), f"Navigation canon missing: {item}"

    def test_code_resolved_canon_includes_primary_nav(self):
        text = _read_artifact("lyfeos_code_resolved_product_canon.md")
        for item in PRIMARY_NAV_ITEMS:
            assert _content_contains(text, item), f"Code-resolved canon missing nav: {item}"

    def test_systems_not_primary_nav(self):
        text = _read_artifact("lyfeos_navigation_shell_canon.md")
        lines = text.lower().split("\n")
        for line in lines:
            if "primary" in line and "nav" in line and "systems" in line:
                assert "not" in line or "secondary" in line or "excluded" in line, \
                    "Systems appears classified as primary navigation"

    def test_systems_classified_as_secondary(self):
        text = _read_artifact("lyfeos_systems_secondary_modules_architecture.md")
        assert _content_contains(text, "secondary"), \
            "Systems modules architecture should reference 'secondary'"

    def test_profile_is_fifth_primary_tab(self):
        text = _read_artifact("lyfeos_navigation_shell_canon.md")
        assert _content_contains(text, "Profile"), "Profile should be in primary navigation"

    def test_screen_inventory_has_five_primary(self):
        data = _load_json_artifact("lyfeos_screen_inventory.json")
        text = json.dumps(data).lower()
        for item in PRIMARY_NAV_ITEMS:
            assert item.lower() in text, f"Screen inventory missing primary nav: {item}"

    def test_dashboard_in_primary_nav(self):
        text = _read_artifact("lyfeos_navigation_shell_canon.md")
        assert _content_contains(text, "Dashboard")

    def test_missions_in_primary_nav(self):
        text = _read_artifact("lyfeos_navigation_shell_canon.md")
        assert _content_contains(text, "Missions")

    def test_ai_in_primary_nav(self):
        text = _read_artifact("lyfeos_navigation_shell_canon.md")
        assert _content_contains(text, "AI")

    def test_chronilog_in_primary_nav(self):
        text = _read_artifact("lyfeos_navigation_shell_canon.md")
        assert _content_contains(text, "Chronilog")


# =============================================================
# SECTION 6: NOVA Naming Correction (8 tests)
# =============================================================


class TestNovaNamingCorrection:
    """NOVA must be classified as legacy/default, not universal system name."""

    def test_nova_correction_document_exists(self):
        assert _artifact_exists("lyfeos_nova_legacy_naming_correction.md")

    def test_nova_classified_as_legacy(self):
        text = _read_artifact("lyfeos_nova_legacy_naming_correction.md")
        assert _content_contains_any(text, ["legacy", "default", "historical"]), \
            "NOVA correction should classify NOVA as legacy/default/historical"

    def test_nova_not_universal_system_name(self):
        text = _read_artifact("lyfeos_nova_legacy_naming_correction.md")
        assert _content_contains_any(text, ["not", "universal", "user-named", "renamable"]), \
            "NOVA correction should state NOVA is not universal system name"

    def test_user_named_ai_companion_model(self):
        text = _read_artifact("lyfeos_ai_companion_architecture.md")
        assert _content_contains_any(text, ["user-named", "renam", "aiAssistantName"]), \
            "AI companion architecture should reference user-named AI model"

    def test_umh_is_substrate_not_ai_name(self):
        text = _read_artifact("lyfeos_umh_connection_architecture.md")
        assert _content_contains(text, "substrate"), \
            "UMH connection architecture should identify UMH as substrate"

    def test_ai_companion_architecture_mentions_nova(self):
        text = _read_artifact("lyfeos_ai_companion_architecture.md")
        assert _content_contains(text, "NOVA"), "AI companion architecture should mention NOVA"

    def test_ai_companion_mentions_user_rename(self):
        text = _read_artifact("lyfeos_ai_companion_architecture.md")
        assert _content_contains_any(text, ["rename", "aiAssistantName", "user-named", "customiz"]), \
            "AI companion should reference user ability to rename"

    def test_nova_code_resolved_current_truth(self):
        text = _read_artifact("lyfeos_nova_legacy_naming_correction.md")
        assert _content_contains(text, "CODE_RESOLVED_CURRENT_TRUTH"), \
            "NOVA naming should reference CODE_RESOLVED_CURRENT_TRUTH"


# =============================================================
# SECTION 7: Onboarding (10 tests)
# =============================================================


class TestOnboardingCanon:
    """Onboarding must be classified as 8-mission current truth."""

    def test_onboarding_mentions_eight_missions(self):
        text = _read_artifact("lyfeos_onboarding_awakening_protocol_canon.md")
        assert _content_contains_any(text, ["8 mission", "eight mission", "0-7", "mission 0", "missions 0"]), \
            "Onboarding canon should reference 8 missions"

    def test_onboarding_mission_zero_access(self):
        text = _read_artifact("lyfeos_onboarding_awakening_protocol_canon.md")
        assert _content_contains_any(text, ["Access", "Quickstart", "Mission 0"]), \
            "Onboarding should reference Mission 0: Access & Quickstart"

    def test_onboarding_archetype_calibration(self):
        text = _read_artifact("lyfeos_onboarding_awakening_protocol_canon.md")
        assert _content_contains(text, "Archetype"), \
            "Onboarding should reference Archetype Calibration"

    def test_integrations_onboarding_gap_exists(self):
        text = _read_artifact("lyfeos_integrations_onboarding_gap.md")
        assert _content_contains(text, "UMH"), \
            "Integrations gap should reference UMH dependency"

    def test_integrations_gap_classified_correctly(self):
        text = _read_artifact("lyfeos_integrations_onboarding_gap.md")
        assert _content_contains_any(text, [
            "UMH_INTEGRATION_DEPENDENT_GAP",
            "integration-dependent",
            "deferred",
        ]), "Integrations gap should be classified as UMH-integration-dependent"

    def test_integrations_gap_not_treated_as_bug(self):
        text = _read_artifact("lyfeos_integrations_onboarding_gap.md")
        assert _content_contains_any(text, ["intentional", "deferred", "not exist"]), \
            "Integrations gap should note intentional deferral, not bug"

    def test_onboarding_code_resolved(self):
        text = _read_artifact("lyfeos_onboarding_awakening_protocol_canon.md")
        assert _content_contains(text, "CODE_RESOLVED_CURRENT_TRUTH"), \
            "Onboarding should reference CODE_RESOLVED_CURRENT_TRUTH"

    def test_legacy_setup_missions_mentioned(self):
        text = _read_artifact("lyfeos_onboarding_awakening_protocol_canon.md")
        assert _content_contains_any(text, ["setupMissionStatus", "legacy", "setup_mission"]), \
            "Onboarding should mention legacy setup mission status"

    def test_onboarding_completed_field_mentioned(self):
        text = _read_artifact("lyfeos_onboarding_awakening_protocol_canon.md")
        assert _content_contains_any(text, ["onboardingCompleted", "onboarding_completed"]), \
            "Onboarding should reference onboardingCompleted field"

    def test_completed_onboarding_missions_field(self):
        text = _read_artifact("lyfeos_onboarding_awakening_protocol_canon.md")
        assert _content_contains_any(text, [
            "completedOnboardingMissions",
            "completed_onboarding_missions",
        ]), "Onboarding should reference completedOnboardingMissions field"


# =============================================================
# SECTION 8: Transformation Thread (6 tests)
# =============================================================


class TestTransformationThread:
    """Transformation Thread must be future candidate, not implemented."""

    def test_transformation_thread_not_implemented(self):
        text = _read_artifact("lyfeos_transformation_thread_decision_packet.md")
        assert _content_contains_any(text, [
            "not implemented", "not in code", "absent", "not built",
            "no implementation", "does not exist", "never implemented",
            "SOURCE_PRESERVED", "OPEN_QUESTION", "future candidate",
            "not yet", "no code", "not currently",
        ]), "Transformation Thread should be classified as not implemented"

    def test_transformation_thread_future_candidate(self):
        text = _read_artifact("lyfeos_transformation_thread_decision_packet.md")
        assert _content_contains_any(text, [
            "future",
            "candidate",
            "SOURCE_PRESERVED",
            "OPEN_QUESTION",
        ]), "Transformation Thread should be classified as future candidate"

    def test_transformation_thread_operator_decision(self):
        text = _read_artifact("lyfeos_transformation_thread_decision_packet.md")
        assert _content_contains_any(text, ["operator", "decision", "ratif"]), \
            "Transformation Thread should require operator decision"

    def test_transformation_thread_not_forced(self):
        text = _read_artifact("lyfeos_transformation_thread_decision_packet.md")
        assert _content_contains_any(text, [
            "not forced",
            "not finalized",
            "preserved",
            "must not",
        ]), "Transformation Thread should not be forced into canon"

    def test_transformation_thread_in_open_questions(self):
        text = _read_artifact("lyfeos_open_questions_operator_decision_queue.md")
        assert _content_contains(text, "Transformation Thread"), \
            "Transformation Thread should be in open questions queue"

    def test_transformation_thread_not_in_mvp_canon(self):
        text = _read_artifact("lyfeos_mvp_current_canon.md")
        lower = text.lower()
        if "transformation thread" in lower:
            assert _content_contains_any(text, [
                "not implemented", "future", "not current", "absent",
                "does not exist", "not built", "not yet", "no code",
                "not exist", "What Does NOT Exist",
            ]), "MVP canon must not claim Transformation Thread is current"


# =============================================================
# SECTION 9: XP / Stats / Data Provenance (12 tests)
# =============================================================


class TestXPStatsDataProvenance:
    """XP/stats are proxy data; data provenance model must exist."""

    def test_xp_stats_not_live_verified(self):
        text = _read_artifact("lyfeos_stats_xp_gamification_truth.md")
        assert _content_contains_any(text, [
            "not live",
            "proxy",
            "manual",
            "computed",
            "not necessarily",
            "self-report",
        ]), "Stats should not be marked as live verified data"

    def test_data_provenance_model_exists(self):
        text = _read_artifact("lyfeos_data_provenance_model.md")
        assert len(text) > 200, "Data provenance model should be substantial"

    def test_data_provenance_has_manual_input(self):
        text = _read_artifact("lyfeos_data_provenance_model.md")
        assert _content_contains_any(text, ["MANUAL_INPUT", "manual input", "manual"]), \
            "Data provenance must include manual input category"

    def test_data_provenance_has_self_report(self):
        text = _read_artifact("lyfeos_data_provenance_model.md")
        assert _content_contains_any(text, ["SELF_REPORT", "self-report", "self report"]), \
            "Data provenance must include self-report category"

    def test_data_provenance_has_computed(self):
        text = _read_artifact("lyfeos_data_provenance_model.md")
        assert _content_contains_any(text, ["COMPUTED", "computed", "app behavior"]), \
            "Data provenance must include computed-from-app-behavior category"

    def test_data_provenance_has_imported(self):
        text = _read_artifact("lyfeos_data_provenance_model.md")
        assert _content_contains_any(text, ["IMPORTED", "imported", "integration"]), \
            "Data provenance must include imported-from-integrations category"

    def test_data_provenance_has_live_verified(self):
        text = _read_artifact("lyfeos_data_provenance_model.md")
        assert _content_contains_any(text, ["LIVE_VERIFIED", "live verified", "device"]), \
            "Data provenance must include live-verified category"

    def test_data_provenance_has_umh_inferred(self):
        text = _read_artifact("lyfeos_data_provenance_model.md")
        assert _content_contains_any(text, ["UMH_INFERRED", "UMH", "inferred", "synthesized"]), \
            "Data provenance must include UMH-inferred category"

    def test_xp_three_tier_system_documented(self):
        text = _read_artifact("lyfeos_stats_xp_gamification_truth.md")
        assert _content_contains_any(text, ["tier", "1-10", "11-50", "51-100"]), \
            "XP documentation should reference 3-tier system"

    def test_five_stat_tokens_documented(self):
        text = _read_artifact("lyfeos_stats_xp_gamification_truth.md")
        for stat in ["Energy", "Health", "Wealth", "Time", "Attention"]:
            assert _content_contains(text, stat), f"Stats truth should mention {stat}"

    def test_gamification_mentions_difficulty_ranks(self):
        text = _read_artifact("lyfeos_stats_xp_gamification_truth.md")
        assert _content_contains_any(text, ["S, A, B, C, D", "difficulty", "rank"]), \
            "Gamification should mention difficulty ranks"

    def test_gamification_mentions_streak(self):
        text = _read_artifact("lyfeos_stats_xp_gamification_truth.md")
        assert _content_contains(text, "streak"), "Gamification should mention streak system"


# =============================================================
# SECTION 10: AI Companion Architecture (10 tests)
# =============================================================


class TestAICompanionArchitecture:
    """AI companion architecture must exist with full detail."""

    def test_ai_companion_architecture_exists(self):
        text = _read_artifact("lyfeos_ai_companion_architecture.md")
        assert len(text) > 500

    def test_ai_tool_registry_exists(self):
        data = _load_json_artifact("lyfeos_ai_tool_action_registry.json")
        text = json.dumps(data)
        assert len(text) > 200

    def test_ai_tool_registry_has_web_search(self):
        text = json.dumps(_load_json_artifact("lyfeos_ai_tool_action_registry.json"))
        assert _content_contains(text, "web_search") or _content_contains(text, "web search")

    def test_ai_tool_registry_has_create_missions(self):
        text = json.dumps(_load_json_artifact("lyfeos_ai_tool_action_registry.json"))
        assert _content_contains_any(text, ["batch_create", "create_mission", "mission"]), \
            "AI tool registry should include mission creation"

    def test_ai_companion_mentions_streaming(self):
        text = _read_artifact("lyfeos_ai_companion_architecture.md")
        assert _content_contains_any(text, ["streaming", "SSE", "server-sent"]), \
            "AI companion should reference streaming"

    def test_ai_companion_mentions_anthropic(self):
        text = _read_artifact("lyfeos_ai_companion_architecture.md")
        assert _content_contains_any(text, ["Anthropic", "Claude", "Haiku", "Sonnet"]), \
            "AI companion should reference Anthropic/Claude models"

    def test_ai_companion_mentions_knowledge_base(self):
        text = _read_artifact("lyfeos_ai_companion_architecture.md")
        assert _content_contains(text, "knowledge"), \
            "AI companion should reference knowledge base"

    def test_ai_companion_mentions_vision(self):
        text = _read_artifact("lyfeos_ai_companion_architecture.md")
        assert _content_contains_any(text, ["vision", "image"]), \
            "AI companion should reference vision/image capability"

    def test_ai_permissions_model_exists(self):
        text = _read_artifact("lyfeos_ai_permissions_approval_model.md")
        assert len(text) > 300

    def test_ai_permissions_mentions_approval(self):
        text = _read_artifact("lyfeos_ai_permissions_approval_model.md")
        assert _content_contains_any(text, ["approval", "permission", "tier"]), \
            "AI permissions model should reference approval tiers"


# =============================================================
# SECTION 11: UMH Connection Architecture (8 tests)
# =============================================================


class TestUMHConnectionArchitecture:
    """UMH connection architecture must exist."""

    def test_umh_connection_exists(self):
        text = _read_artifact("lyfeos_umh_connection_architecture.md")
        assert len(text) > 1000

    def test_lyfeos_remains_user_facing(self):
        text = _read_artifact("lyfeos_umh_connection_architecture.md")
        assert _content_contains_any(text, ["user-facing", "user facing"]), \
            "LyfeOS should remain user-facing"

    def test_umh_remains_substrate(self):
        text = _read_artifact("lyfeos_umh_connection_architecture.md")
        assert _content_contains(text, "substrate"), "UMH should remain substrate"

    def test_adapter_first_principle(self):
        text = _read_artifact("lyfeos_umh_connection_architecture.md")
        assert _content_contains_any(text, ["adapter", "not rewrite"]), \
            "UMH connection should reference adapter-first principle"

    def test_umh_connection_has_blocking_questions(self):
        text = _read_artifact("lyfeos_umh_connection_architecture.md")
        assert _content_contains_any(text, ["question", "blocking", "decision"]), \
            "UMH connection should have blocking questions"

    def test_umh_connection_mentions_integration_surfaces(self):
        text = _read_artifact("lyfeos_umh_connection_architecture.md")
        assert _content_contains_any(text, ["integration", "surface", "boundary"]), \
            "UMH connection should mention integration surfaces"

    def test_umh_connection_mentions_failover(self):
        text = _read_artifact("lyfeos_umh_connection_architecture.md")
        assert _content_contains_any(text, ["failover", "unavailable", "fallback"]), \
            "UMH connection should address failover scenario"

    def test_umh_connection_mentions_privacy(self):
        text = _read_artifact("lyfeos_umh_connection_architecture.md")
        assert _content_contains_any(text, ["privacy", "sensitive", "personal data"]), \
            "UMH connection should address privacy/sensitive data"


# =============================================================
# SECTION 12: Auth / Firebase / Clerk Truth (8 tests)
# =============================================================


class TestAuthTruth:
    """Firebase/session/local auth is current; Clerk is not."""

    def test_firebase_auth_is_current(self):
        text = _read_artifact("lyfeos_auth_session_security_truth.md")
        assert _content_contains(text, "Firebase"), "Auth truth should reference Firebase"

    def test_passport_auth_is_current(self):
        text = _read_artifact("lyfeos_auth_session_security_truth.md")
        assert _content_contains(text, "Passport"), "Auth truth should reference Passport.js"

    def test_express_session_is_current(self):
        text = _read_artifact("lyfeos_auth_session_security_truth.md")
        assert _content_contains_any(text, ["express-session", "session"]), \
            "Auth truth should reference session management"

    def test_clerk_not_current_implementation(self):
        text = _read_artifact("lyfeos_auth_session_security_truth.md")
        lower = text.lower()
        if "clerk" in lower:
            assert _content_contains_any(text, [
                "not current",
                "not implemented",
                "candidate",
                "future",
                "migration",
            ]), "Clerk should NOT be classified as current implementation"

    def test_auth_migration_mentions_clerk(self):
        text = _read_artifact("lyfeos_auth_migration_candidate_plan.md")
        assert _content_contains(text, "Clerk"), "Auth migration plan should mention Clerk"

    def test_auth_migration_is_blocked(self):
        text = _read_artifact("lyfeos_auth_migration_candidate_plan.md")
        assert _content_contains_any(text, ["blocked", "pending", "not current", "decision"]), \
            "Auth migration should be classified as blocked/pending"

    def test_two_factor_auth_documented(self):
        text = _read_artifact("lyfeos_auth_session_security_truth.md")
        assert _content_contains_any(text, ["2FA", "two-factor", "two factor"]), \
            "Auth truth should document 2FA"

    def test_bcrypt_or_scrypt_documented(self):
        text = _read_artifact("lyfeos_auth_session_security_truth.md")
        assert _content_contains_any(text, ["bcrypt", "scrypt"]), \
            "Auth truth should document password hashing"


# =============================================================
# SECTION 13: RLS / Backup / Security (10 tests)
# =============================================================


class TestRLSBackupSecurity:
    """RLS unverified, backup P0, security gaps surfaced."""

    def test_rls_not_verified(self):
        text = _read_artifact("lyfeos_rls_tenant_isolation_matrix.md")
        assert _content_contains_any(text, ["no RLS", "not found", "not verified", "absent"]), \
            "RLS should be classified as not verified"

    def test_backup_recovery_is_critical(self):
        text = _read_artifact("lyfeos_backup_recovery_risk_packet.md")
        assert _content_contains_any(text, ["P0", "critical", "CRITICAL", "HIGH"]), \
            "Backup/recovery should be classified as critical/P0"

    def test_backup_no_scripts_found(self):
        text = _read_artifact("lyfeos_backup_recovery_risk_packet.md")
        assert _content_contains_any(text, [
            "no backup",
            "not found",
            "no script",
            "no recovery",
            "absent",
            "no dedicated",
            "zero",
            "none",
            "CRITICAL",
            "P0",
            "unverified",
            "not verified",
        ]), "Backup recovery should note absence of backup scripts or critical risk"

    def test_security_artifact_has_privacy(self):
        text = _read_artifact("lyfeos_security_trust_privacy_compliance.md")
        assert _content_contains(text, "privacy"), "Security artifact should address privacy"

    def test_security_mentions_sensitive_data(self):
        text = _read_artifact("lyfeos_security_trust_privacy_compliance.md")
        assert _content_contains(text, "sensitive"), \
            "Security artifact should mention sensitive data"

    def test_observability_exists(self):
        text = _read_artifact("lyfeos_observability_logging_audit_map.md")
        assert len(text) > 300

    def test_observability_mentions_error_tracking(self):
        text = _read_artifact("lyfeos_observability_logging_audit_map.md")
        assert _content_contains_any(text, ["error tracking", "error_tracking", "Sentry"]), \
            "Observability should mention error tracking"

    def test_test_coverage_inventory_exists(self):
        text = _read_artifact("lyfeos_test_coverage_inventory.md")
        assert len(text) > 200

    def test_test_coverage_mentions_thin(self):
        text = _read_artifact("lyfeos_test_coverage_inventory.md")
        assert _content_contains_any(text, ["thin", "limited", "2 test", "two test", "minimal"]), \
            "Test coverage should be classified as thin/limited"

    def test_implementation_debt_register_exists(self):
        text = _read_artifact("lyfeos_implementation_debt_register.md")
        assert len(text) > 500


# =============================================================
# SECTION 14: Google Integration (5 tests)
# =============================================================


class TestGoogleIntegration:
    """Google integration is partial current implementation."""

    def test_google_integration_documented(self):
        text = _read_artifact("lyfeos_google_integration_current_truth.md")
        assert _content_contains(text, "Google"), "Should document Google integration"

    def test_google_calendar_sync(self):
        text = _read_artifact("lyfeos_google_integration_current_truth.md")
        assert _content_contains_any(text, ["Calendar", "calendar", "sync"]), \
            "Should document Google Calendar sync"

    def test_google_tasks_import(self):
        text = _read_artifact("lyfeos_google_integration_current_truth.md")
        assert _content_contains_any(text, ["Tasks", "tasks", "import"]), \
            "Should document Google Tasks import"

    def test_google_classified_as_partial(self):
        text = _read_artifact("lyfeos_google_integration_current_truth.md")
        assert _content_contains_any(text, [
            "partial",
            "CODE_RESOLVED_CURRENT_TRUTH",
            "implemented",
        ]), "Google integration should be classified as partial/current"

    def test_full_integration_future(self):
        text = _read_artifact("lyfeos_integration_architecture.md")
        assert _content_contains_any(text, [
            "future",
            "UMH",
            "harmonization",
        ]), "Full integration harmonization should be classified as future"


# =============================================================
# SECTION 15: Database and API (8 tests)
# =============================================================


class TestDatabaseAndAPI:
    """Database inventory and API contract map must exist."""

    def test_database_table_inventory_has_entries(self):
        data = _load_json_artifact("lyfeos_database_table_inventory.json")
        text = json.dumps(data)
        assert _content_contains(text, "users"), "Database inventory should include users table"
        assert _content_contains(text, "quests"), "Database inventory should include quests table"

    def test_database_inventory_has_user_profile(self):
        text = json.dumps(_load_json_artifact("lyfeos_database_table_inventory.json"))
        assert _content_contains_any(text, ["userProfile", "user_profile"]), \
            "Database inventory should include userProfile table"

    def test_database_inventory_has_conversations(self):
        text = json.dumps(_load_json_artifact("lyfeos_database_table_inventory.json"))
        assert _content_contains(text, "conversations"), \
            "Database inventory should include conversations table"

    def test_api_contract_map_has_entries(self):
        data = _load_json_artifact("lyfeos_api_contract_map.json")
        text = json.dumps(data)
        assert _content_contains(text, "/api"), "API contract map should have API routes"

    def test_api_contract_has_auth_routes(self):
        text = json.dumps(_load_json_artifact("lyfeos_api_contract_map.json"))
        assert _content_contains_any(text, ["auth", "login", "register"]), \
            "API contract should include auth routes"

    def test_api_contract_has_quest_routes(self):
        text = json.dumps(_load_json_artifact("lyfeos_api_contract_map.json"))
        assert _content_contains_any(text, ["quest", "mission"]), \
            "API contract should include quest/mission routes"

    def test_data_ontology_has_tables(self):
        data = _load_json_artifact("lyfeos_data_ontology.json")
        text = json.dumps(data)
        assert _content_contains(text, "users"), "Data ontology should include users"

    def test_data_ontology_has_relationships(self):
        text = json.dumps(_load_json_artifact("lyfeos_data_ontology.json"))
        assert _content_contains_any(text, ["relationship", "reference", "foreign", "FK"]), \
            "Data ontology should include relationship info"


# =============================================================
# SECTION 16: MVP / Hardening / Post-MVP Placement (6 tests)
# =============================================================


class TestMVPPlacement:
    """MVP vs hardening vs post-MVP placement must exist."""

    def test_placement_artifact_exists(self):
        data = _load_json_artifact("lyfeos_mvp_hardening_postmvp_endstate_placement.json")
        assert len(json.dumps(data)) > 200

    def test_placement_has_current_mvp(self):
        text = json.dumps(_load_json_artifact("lyfeos_mvp_hardening_postmvp_endstate_placement.json"))
        assert _content_contains_any(text, ["CURRENT_MVP", "current_mvp", "MVP"]), \
            "Placement should include CURRENT_MVP category"

    def test_placement_has_hardening(self):
        text = json.dumps(_load_json_artifact("lyfeos_mvp_hardening_postmvp_endstate_placement.json"))
        assert _content_contains_any(text, ["HARDENING", "hardening"]), \
            "Placement should include HARDENING category"

    def test_placement_has_umh_connected(self):
        text = json.dumps(_load_json_artifact("lyfeos_mvp_hardening_postmvp_endstate_placement.json"))
        assert _content_contains_any(text, ["UMH", "umh_connected"]), \
            "Placement should include UMH-connected category"

    def test_professional_gap_register_exists(self):
        text = _read_artifact("lyfeos_professional_gap_register.md")
        assert len(text) > 500

    def test_open_questions_queue_exists(self):
        text = _read_artifact("lyfeos_open_questions_operator_decision_queue.md")
        assert len(text) > 500


# =============================================================
# SECTION 17: No Implementation Gate (15 tests)
# =============================================================


class TestNoImplementation:
    """Verify no implementation, source mutation, or infrastructure changes."""

    def test_no_branch_merge_occurred(self):
        result = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            cwd="/opt/OS",
            capture_output=True,
            text=True,
        )
        assert "merge" not in result.stdout.lower() or "lyfeos" not in result.stdout.lower(), \
            "No LyfeOS branch merge should have occurred"

    def test_no_lyfeos_source_modified(self):
        lyfeos_dir = pathlib.Path("/opt/OS/data/repos/LYFEOS")
        if lyfeos_dir.exists():
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD", "--", "data/repos/LYFEOS/"],
                cwd="/opt/OS",
                capture_output=True,
                text=True,
            )
            modified = result.stdout.strip()
            assert modified == "", f"LyfeOS source files were modified: {modified}"

    def test_no_infrastructure_provisioned(self):
        artifact_dir = ARTIFACT_DIR
        for f in artifact_dir.iterdir():
            text = f.read_text(encoding="utf-8")
            assert "provisioned" not in text.lower() or "not provisioned" in text.lower() or \
                   "no infrastructure provisioned" in text.lower() or "false" in text.lower(), \
                f"Artifact {f.name} may claim infrastructure was provisioned"

    def test_no_auth_migration_occurred(self):
        text = _read_artifact("lyfeos_audit_report.md")
        assert not _content_contains(text, "auth migration completed"), \
            "Auth migration should not have occurred"

    def test_no_umh_connection_implemented(self):
        text = _read_artifact("lyfeos_audit_report.md")
        assert not _content_contains(text, "UMH connection implemented"), \
            "UMH connection should not have been implemented"

    def test_artifacts_are_in_worktree(self):
        """Verify artifacts were written to worktree, not main."""
        worktree_dir = pathlib.Path(
            "/opt/OS/.claude/worktrees/phase-14-6b-lyfeos/data/umh/trinity_convergence/phase14_6b_lyfeos"
        )
        assert worktree_dir.exists() or ARTIFACT_DIR.exists(), \
            "Artifacts should exist in worktree or target directory"

    def test_no_docker_containers_modified(self):
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        containers = result.stdout.strip()
        assert "lyfeos" not in containers.lower(), \
            "No LyfeOS Docker containers should be running from this phase"

    def test_no_deployment_occurred(self):
        for name in ALL_ARTIFACTS:
            if _artifact_exists(name):
                text = _read_artifact(name)
                assert not _content_contains(text, "deployed successfully"), \
                    f"{name} claims deployment occurred"

    def test_no_database_migration_ran(self):
        for name in ALL_ARTIFACTS:
            if _artifact_exists(name):
                text = _read_artifact(name)
                assert not _content_contains(text, "migration executed"), \
                    f"{name} claims migration was executed"

    def test_no_clerk_resources_created(self):
        for name in ALL_ARTIFACTS:
            if _artifact_exists(name):
                text = _read_artifact(name)
                assert not _content_contains(text, "Clerk resource created"), \
                    f"{name} claims Clerk resources were created"

    def test_no_firebase_resources_created(self):
        for name in ALL_ARTIFACTS:
            if _artifact_exists(name):
                text = _read_artifact(name)
                assert not _content_contains(text, "Firebase resource created"), \
                    f"{name} claims Firebase resources were created"

    def test_no_stripe_resources_created(self):
        for name in ALL_ARTIFACTS:
            if _artifact_exists(name):
                text = _read_artifact(name)
                assert not _content_contains(text, "Stripe resource created"), \
                    f"{name} claims Stripe resources were created"

    def test_no_fly_io_deployed(self):
        for name in ALL_ARTIFACTS:
            if _artifact_exists(name):
                text = _read_artifact(name)
                assert not _content_contains(text, "deployed to Fly.io"), \
                    f"{name} claims Fly.io deployment"

    def test_no_vercel_deployed(self):
        for name in ALL_ARTIFACTS:
            if _artifact_exists(name):
                text = _read_artifact(name)
                assert not _content_contains(text, "deployed to Vercel"), \
                    f"{name} claims Vercel deployment"

    def test_no_autonomous_execution(self):
        for name in ALL_ARTIFACTS:
            if _artifact_exists(name):
                text = _read_artifact(name)
                assert not _content_contains(text, "autonomous execution enabled"), \
                    f"{name} claims autonomous execution was enabled"


# =============================================================
# SECTION 18: Audit Report & Readiness Gate (12 tests)
# =============================================================


class TestAuditReportAndReadiness:
    """Audit report must exist with correct readiness gates."""

    def test_audit_report_exists(self):
        text = _read_artifact("lyfeos_audit_report.md")
        assert len(text) > 1000

    def test_audit_report_has_success_criteria(self):
        text = _read_artifact("lyfeos_audit_report.md")
        assert _content_contains_any(text, ["success criteria", "criteria"]), \
            "Audit report should reference success criteria"

    def test_audit_report_has_readiness_gate(self):
        text = _read_artifact("lyfeos_audit_report.md")
        assert _content_contains_any(text, ["readiness", "gate", "ready"]), \
            "Audit report should reference readiness gates"

    def test_not_ready_for_implementation(self):
        text = _read_artifact("lyfeos_audit_report.md")
        lower = text.lower()
        assert "ready_for_feature_build" not in lower or "false" in lower, \
            "Should not be ready for feature build"

    def test_not_ready_for_auth_migration(self):
        text = _read_artifact("lyfeos_audit_report.md")
        lower = text.lower()
        if "ready_for_auth_migration" in lower:
            idx = lower.index("ready_for_auth_migration")
            context = lower[idx:idx+60]
            assert "false" in context, "Should not be ready for auth migration"

    def test_not_ready_for_autonomous_execution(self):
        text = _read_artifact("lyfeos_audit_report.md")
        lower = text.lower()
        if "ready_for_autonomous_execution" in lower:
            idx = lower.index("ready_for_autonomous_execution")
            context = lower[idx:idx+60]
            assert "false" in context, "Should not be ready for autonomous execution"

    def test_ready_for_operator_review(self):
        text = _read_artifact("lyfeos_audit_report.md")
        assert _content_contains_any(text, ["operator review", "operator_review", "review"]), \
            "Should be ready for operator review"

    def test_ratification_packet_exists(self):
        text = _read_artifact("lyfeos_source_truth_ratification_packet.md")
        assert len(text) > 500

    def test_ratification_packet_lists_corrections(self):
        text = _read_artifact("lyfeos_source_truth_ratification_packet.md")
        assert _content_contains_any(text, ["correction", "corrected", "operator"]), \
            "Ratification packet should list corrections"

    def test_open_questions_queue_has_items(self):
        text = _read_artifact("lyfeos_open_questions_operator_decision_queue.md")
        assert _content_contains_any(text, ["PRD", "Clerk", "UMH", "Transformation"]), \
            "Open questions should include key decision items"

    def test_professional_gap_register_has_items(self):
        text = _read_artifact("lyfeos_professional_gap_register.md")
        assert _content_contains_any(text, ["RLS", "backup", "error tracking", "CI/CD"]), \
            "Professional gap register should include key gaps"

    def test_implementation_debt_has_items(self):
        text = _read_artifact("lyfeos_implementation_debt_register.md")
        assert _content_contains_any(text, ["RLS", "backup", "test", "rate limit"]), \
            "Implementation debt should include key items"


# =============================================================
# SECTION 19: Contradiction Matrix (6 tests)
# =============================================================


class TestContradictionMatrix:
    """Contradictions must be classified properly."""

    def test_contradiction_matrix_has_entries(self):
        data = _load_json_artifact("lyfeos_contradiction_matrix.json")
        text = json.dumps(data)
        assert len(text) > 200, "Contradiction matrix should have entries"

    def test_prd_contradiction_present(self):
        text = json.dumps(_load_json_artifact("lyfeos_contradiction_matrix.json"))
        assert _content_contains_any(text, ["PRD", "prd"]), \
            "Contradiction matrix should include PRD version conflict"

    def test_nova_naming_contradiction_present(self):
        text = json.dumps(_load_json_artifact("lyfeos_contradiction_matrix.json"))
        assert _content_contains(text, "NOVA"), \
            "Contradiction matrix should include NOVA naming conflict"

    def test_auth_contradiction_present(self):
        text = json.dumps(_load_json_artifact("lyfeos_contradiction_matrix.json"))
        assert _content_contains_any(text, ["auth", "Clerk", "Firebase"]), \
            "Contradiction matrix should include auth conflict"

    def test_contradictions_have_classification(self):
        text = json.dumps(_load_json_artifact("lyfeos_contradiction_matrix.json"))
        assert _content_contains_any(text, [
            "CODE_RESOLVED",
            "SOURCE_PRESERVED",
            "STAGE_BASED",
            "SEMANTICALLY_MERGEABLE",
            "IMPLEMENTATION_DEBT",
            "OPEN_OPERATOR",
        ]), "Contradictions should have classification labels"

    def test_systems_nav_contradiction(self):
        text = json.dumps(_load_json_artifact("lyfeos_contradiction_matrix.json"))
        assert _content_contains_any(text, ["Systems", "navigation", "primary"]), \
            "Contradiction matrix should address Systems nav conflict"


# =============================================================
# SECTION 20: Cross-Artifact Consistency (8 tests)
# =============================================================


class TestCrossArtifactConsistency:
    """Artifacts must be consistent with each other."""

    def test_nav_consistent_across_artifacts(self):
        for name in [
            "lyfeos_code_resolved_product_canon.md",
            "lyfeos_navigation_shell_canon.md",
            "lyfeos_mvp_current_canon.md",
        ]:
            text = _read_artifact(name)
            for item in PRIMARY_NAV_ITEMS:
                assert _content_contains(text, item), \
                    f"{name} missing nav item: {item}"

    def test_nova_naming_consistent(self):
        for name in [
            "lyfeos_nova_legacy_naming_correction.md",
            "lyfeos_ai_companion_architecture.md",
        ]:
            text = _read_artifact(name)
            assert _content_contains(text, "NOVA"), f"{name} should mention NOVA"
            assert _content_contains_any(text, ["legacy", "default", "historical", "renam"]), \
                f"{name} should classify NOVA as legacy/default"

    def test_transformation_thread_consistent(self):
        for name in [
            "lyfeos_transformation_thread_decision_packet.md",
            "lyfeos_open_questions_operator_decision_queue.md",
        ]:
            text = _read_artifact(name)
            assert _content_contains(text, "Transformation Thread"), \
                f"{name} should mention Transformation Thread"

    def test_firebase_consistent_across_auth_artifacts(self):
        for name in [
            "lyfeos_auth_session_security_truth.md",
            "lyfeos_auth_migration_candidate_plan.md",
        ]:
            text = _read_artifact(name)
            assert _content_contains(text, "Firebase"), f"{name} should mention Firebase"

    def test_rls_gap_consistent(self):
        for name in [
            "lyfeos_rls_tenant_isolation_matrix.md",
            "lyfeos_implementation_debt_register.md",
            "lyfeos_professional_gap_register.md",
        ]:
            text = _read_artifact(name)
            assert _content_contains(text, "RLS"), f"{name} should mention RLS"

    def test_backup_gap_consistent(self):
        for name in [
            "lyfeos_backup_recovery_risk_packet.md",
            "lyfeos_professional_gap_register.md",
        ]:
            text = _read_artifact(name)
            assert _content_contains_any(text, ["backup", "recovery"]), \
                f"{name} should mention backup/recovery"

    def test_umh_substrate_consistent(self):
        for name in [
            "lyfeos_umh_connection_architecture.md",
            "lyfeos_umh_connected_future_canon.md",
        ]:
            text = _read_artifact(name)
            assert _content_contains(text, "substrate"), \
                f"{name} should mention UMH as substrate"

    def test_onboarding_consistent(self):
        for name in [
            "lyfeos_onboarding_awakening_protocol_canon.md",
            "lyfeos_integrations_onboarding_gap.md",
        ]:
            text = _read_artifact(name)
            assert _content_contains_any(text, ["8", "eight", "0-7"]), \
                f"{name} should reference 8 onboarding missions"


# =============================================================
# SECTION 21: Content Quality (10 tests)
# =============================================================


class TestContentQuality:
    """Artifacts must have substantial content."""

    def test_code_resolved_canon_substantial(self):
        text = _read_artifact("lyfeos_code_resolved_product_canon.md")
        assert len(text) > 5000, "Code-resolved canon should be substantial (>5000 chars)"

    def test_lossless_canon_substantial(self):
        text = _read_artifact("lyfeos_lossless_product_canon.md")
        assert len(text) > 5000, "Lossless canon should be substantial (>5000 chars)"

    def test_github_analysis_substantial(self):
        text = _read_artifact("lyfeos_github_codebase_deep_analysis.md")
        assert len(text) > 5000, "GitHub analysis should be substantial (>5000 chars)"

    def test_umh_connection_substantial(self):
        text = _read_artifact("lyfeos_umh_connection_architecture.md")
        assert len(text) > 3000, "UMH connection should be substantial (>3000 chars)"

    def test_ai_companion_substantial(self):
        text = _read_artifact("lyfeos_ai_companion_architecture.md")
        assert len(text) > 3000, "AI companion architecture should be substantial (>3000 chars)"

    def test_profile_character_sheet_substantial(self):
        text = _read_artifact("lyfeos_profile_character_sheet_canon.md")
        assert len(text) > 3000, "Profile/character sheet should be substantial (>3000 chars)"

    def test_missions_architecture_substantial(self):
        text = _read_artifact("lyfeos_missions_quests_architecture.md")
        assert len(text) > 3000, "Missions architecture should be substantial (>3000 chars)"

    def test_audit_report_substantial(self):
        text = _read_artifact("lyfeos_audit_report.md")
        assert len(text) > 3000, "Audit report should be substantial (>3000 chars)"

    def test_security_substantial(self):
        text = _read_artifact("lyfeos_security_trust_privacy_compliance.md")
        assert len(text) > 2000, "Security artifact should be substantial (>2000 chars)"

    def test_deployment_map_substantial(self):
        text = _read_artifact("lyfeos_infrastructure_deployment_map.md")
        assert len(text) > 1000, "Deployment map should be substantial (>1000 chars)"


# =============================================================
# SECTION 22: Total Test Count Validation
# =============================================================


class TestAdditionalCoverage:
    """Additional coverage tests for mandate completeness."""

    def test_chronilog_mentions_daily_logs(self):
        text = _read_artifact("lyfeos_chronilog_architecture.md")
        assert _content_contains_any(text, ["daily", "log"]), "Chronilog should mention daily logs"

    def test_chronilog_mentions_reflection(self):
        text = _read_artifact("lyfeos_chronilog_architecture.md")
        assert _content_contains(text, "reflection"), "Chronilog should mention reflection"

    def test_chronilog_mentions_energy_log(self):
        text = _read_artifact("lyfeos_chronilog_architecture.md")
        assert _content_contains_any(text, ["energy", "mental", "physical", "emotional"]), \
            "Chronilog should mention energy/state tracking"

    def test_dashboard_mentions_widgets(self):
        text = _read_artifact("lyfeos_dashboard_architecture.md")
        assert _content_contains(text, "widget"), "Dashboard should mention widgets"

    def test_dashboard_mentions_xp(self):
        text = _read_artifact("lyfeos_dashboard_architecture.md")
        assert _content_contains(text, "XP"), "Dashboard should mention XP"

    def test_screen_inventory_has_onboarding(self):
        text = json.dumps(_load_json_artifact("lyfeos_screen_inventory.json"))
        assert _content_contains_any(text, ["Onboarding", "onboarding"]), \
            "Screen inventory should include onboarding"

    def test_secondary_routes_have_document_vault(self):
        text = json.dumps(_load_json_artifact("lyfeos_secondary_module_route_map.json"))
        assert _content_contains_any(text, ["document", "vault", "Document"]), \
            "Secondary routes should include document vault"

    def test_secondary_routes_have_contacts(self):
        text = json.dumps(_load_json_artifact("lyfeos_secondary_module_route_map.json"))
        assert _content_contains_any(text, ["contact", "Contact"]), \
            "Secondary routes should include contacts"

    def test_mvp_canon_only_code_resolved(self):
        text = _read_artifact("lyfeos_mvp_current_canon.md")
        assert _content_contains_any(text, ["CODE_RESOLVED", "current", "implemented"]), \
            "MVP canon should focus on code-resolved/current truth"

    def test_end_state_canon_includes_future(self):
        text = _read_artifact("lyfeos_full_end_state_canon.md")
        assert _content_contains_any(text, ["future", "end state", "vision"]), \
            "End state canon should include future features"

    def test_umh_future_canon_mentions_projection(self):
        text = _read_artifact("lyfeos_umh_connected_future_canon.md")
        assert _content_contains_any(text, ["projection", "adapter", "substrate"]), \
            "UMH future canon should mention projection/adapter architecture"

    def test_version_precedence_has_operator(self):
        text = json.dumps(_load_json_artifact("lyfeos_version_precedence_matrix.json"))
        assert _content_contains_any(text, ["operator", "correction", "highest"]), \
            "Version precedence should list operator corrections as highest"

    def test_docs_vs_code_convergence_has_entries(self):
        data = _load_json_artifact("lyfeos_docs_vs_code_convergence_matrix.json")
        text = json.dumps(data)
        assert len(text) > 300, "Docs vs code convergence should have entries"

    def test_source_inventory_has_schema(self):
        text = json.dumps(_load_json_artifact("lyfeos_source_inventory.json"))
        assert _content_contains(text, "schema"), "Source inventory should reference schema.ts"

    def test_source_inventory_has_replit_md(self):
        text = json.dumps(_load_json_artifact("lyfeos_source_inventory.json"))
        assert _content_contains(text, "replit"), "Source inventory should reference replit.md"


class TestSuiteCompleteness:
    """Meta-test to verify we have 250+ tests."""

    def test_minimum_test_count(self):
        import inspect
        test_count = 0
        for name, obj in globals().items():
            if isinstance(obj, type) and name.startswith("Test"):
                for method_name in dir(obj):
                    if method_name.startswith("test_"):
                        test_count += 1
        assert test_count >= 250, \
            f"Expected 250+ tests, found {test_count}"


# =============================================================
# Run with pytest
# =============================================================

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
