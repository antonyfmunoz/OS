"""Adapter Package Manager — maturity enforcement and path inventory.

Enforces 100% maturity for selected tool/access path execution,
evaluates full adapter package maturity across all declared paths,
and inventories all paths with hardening plans.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from .maturity_enforcement import (
    AdapterExecutionMaturityStatus,
    AdapterExecutionReadinessDecision,
    AdapterPackageSnapshot,
    adapter_execution_blocks,
    adapter_package_has_required_components,
    build_adapter_execution_readiness_report,
    evaluate_adapter_package_execution_readiness,
    known_gaps_affect_capability,
    require_100_percent_maturity,
    selected_access_path_is_complete,
)

from .test_tool_preflight import (
    TestToolPreflightReport,
    TestToolPreflightStatus,
    TestToolRequirement,
    build_w0_001_required_tool_inventory,
    detect_required_tools_for_task,
    preflight_blocks_execution,
    run_test_tool_preflight,
    summarize_test_tool_preflight,
)

from .adapter_package_readiness import (
    PackageGapReport,
    build_package_gap_report,
    compute_access_path_maturity_percent,
    compute_package_maturity_percent,
    package_can_be_used_for_capability,
    package_current_state_is_honest,
    package_targets_100_percent,
)

from .full_path_maturity import (
    AdapterPathMaturityDecision,
    AdapterPathSnapshot,
    FullAdapterPackageMaturityDecision,
    FullPathMaturityStatus,
    PathDeclarationStatus,
    build_full_path_maturity_report,
    evaluate_full_adapter_package_maturity,
    evaluate_path_maturity,
    path_blocks_full_package_maturity,
    path_counts_toward_package_maturity,
    reject_fake_complete_path,
)

from .adapter_path_inventory import (
    AdapterPathInventoryItem,
    build_adapter_path_inventory_report,
    classify_declared_vs_candidate_paths,
    inventory_claude_code_paths,
    inventory_google_workspace_paths,
    inventory_w0_001_operational_tools,
)

from .path_hardening_plan import (
    PathHardeningWorkOrder,
    build_path_hardening_plan_report,
    create_hardening_plan_for_package,
    create_hardening_work_order,
    prioritize_hardening_work_orders,
)

from .google_workspace_api_adapter_path import (
    GoogleWorkspaceApiAdapterPath,
    W_GWS_API_001_PACKAGE_ID,
    W_GWS_API_001_PATH_ID,
    W_GWS_API_001_PATH_NAME,
    build_google_workspace_api_tab_aware_path,
)

from .google_workspace_api_contract_mapping import (
    ApiContractRequirement,
    GoogleWorkspaceApiContractMapping,
    W0001ExpectedCoverageContract,
    api_mapping_preserves_per_tab_provenance,
    api_mapping_rejects_first_tab_only,
    api_mapping_requires_child_tabs_recursion,
    api_mapping_requires_document_tabs_traversal,
    api_mapping_requires_include_tabs_content,
    build_w0_001_expected_coverage_contract,
    build_w_gws_api_001_contract_mapping,
)

from .google_workspace_api_governance import (
    GovernancePolicy,
    build_w_gws_api_001_governance_policy,
    governance_blocks_credential_capture,
    governance_blocks_memory_promotion,
    governance_blocks_mutation,
    governance_blocks_permission_changes,
    governance_is_read_only,
    governance_preserves_instance_scope,
    governance_requires_export_approval,
)

from .google_workspace_api_maturity import (
    W_GWS_API_001_MaturityCheck,
    W_GWS_API_001_MaturityDecision,
    build_w_gws_api_001_gap_report,
    build_w_gws_api_001_maturity_decision,
    evaluate_w_gws_api_001_maturity,
    google_workspace_package_is_fully_mature_with_cu_partial,
    w_gws_api_001_is_100_percent_mature,
)

__all__ = [
    "AdapterExecutionMaturityStatus",
    "AdapterExecutionReadinessDecision",
    "AdapterPackageSnapshot",
    "AdapterPathInventoryItem",
    "AdapterPathMaturityDecision",
    "AdapterPathSnapshot",
    "FullAdapterPackageMaturityDecision",
    "FullPathMaturityStatus",
    "PackageGapReport",
    "PathDeclarationStatus",
    "PathHardeningWorkOrder",
    "TestToolPreflightReport",
    "TestToolPreflightStatus",
    "TestToolRequirement",
    "adapter_execution_blocks",
    "adapter_package_has_required_components",
    "build_adapter_execution_readiness_report",
    "build_adapter_path_inventory_report",
    "build_full_path_maturity_report",
    "build_package_gap_report",
    "build_path_hardening_plan_report",
    "build_w0_001_required_tool_inventory",
    "classify_declared_vs_candidate_paths",
    "compute_access_path_maturity_percent",
    "compute_package_maturity_percent",
    "create_hardening_plan_for_package",
    "create_hardening_work_order",
    "detect_required_tools_for_task",
    "evaluate_adapter_package_execution_readiness",
    "evaluate_full_adapter_package_maturity",
    "evaluate_path_maturity",
    "inventory_claude_code_paths",
    "inventory_google_workspace_paths",
    "inventory_w0_001_operational_tools",
    "known_gaps_affect_capability",
    "package_can_be_used_for_capability",
    "package_current_state_is_honest",
    "package_targets_100_percent",
    "path_blocks_full_package_maturity",
    "path_counts_toward_package_maturity",
    "preflight_blocks_execution",
    "prioritize_hardening_work_orders",
    "reject_fake_complete_path",
    "require_100_percent_maturity",
    "run_test_tool_preflight",
    "selected_access_path_is_complete",
    "summarize_test_tool_preflight",
    "ApiContractRequirement",
    "GovernancePolicy",
    "GoogleWorkspaceApiAdapterPath",
    "GoogleWorkspaceApiContractMapping",
    "W0001ExpectedCoverageContract",
    "W_GWS_API_001_MaturityCheck",
    "W_GWS_API_001_MaturityDecision",
    "W_GWS_API_001_PACKAGE_ID",
    "W_GWS_API_001_PATH_ID",
    "W_GWS_API_001_PATH_NAME",
    "api_mapping_preserves_per_tab_provenance",
    "api_mapping_rejects_first_tab_only",
    "api_mapping_requires_child_tabs_recursion",
    "api_mapping_requires_document_tabs_traversal",
    "api_mapping_requires_include_tabs_content",
    "build_google_workspace_api_tab_aware_path",
    "build_w0_001_expected_coverage_contract",
    "build_w_gws_api_001_contract_mapping",
    "build_w_gws_api_001_gap_report",
    "build_w_gws_api_001_governance_policy",
    "build_w_gws_api_001_maturity_decision",
    "evaluate_w_gws_api_001_maturity",
    "google_workspace_package_is_fully_mature_with_cu_partial",
    "governance_blocks_credential_capture",
    "governance_blocks_memory_promotion",
    "governance_blocks_mutation",
    "governance_blocks_permission_changes",
    "governance_is_read_only",
    "governance_preserves_instance_scope",
    "governance_requires_export_approval",
    "w_gws_api_001_is_100_percent_mature",
]
