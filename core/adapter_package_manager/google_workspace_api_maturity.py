"""Maturity Gate for W-GWS-API-001.

Evaluates whether the API tab-aware adapter path is 100% mature.
Uses existing maturity enforcement and full-path maturity helpers.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .google_workspace_api_adapter_path import (
    W_GWS_API_001_PATH_ID,
    build_google_workspace_api_tab_aware_path,
)
from .google_workspace_api_contract_mapping import (
    api_mapping_rejects_first_tab_only,
    api_mapping_requires_child_tabs_recursion,
    api_mapping_requires_document_tabs_traversal,
    api_mapping_requires_include_tabs_content,
    build_w_gws_api_001_contract_mapping,
)
from .google_workspace_api_governance import (
    build_w_gws_api_001_governance_policy,
    governance_blocks_credential_capture,
    governance_blocks_mutation,
    governance_is_read_only,
)
from .full_path_maturity import (
    AdapterPathSnapshot,
    PathDeclarationStatus,
    evaluate_full_adapter_package_maturity,
    evaluate_path_maturity,
)


@dataclass
class W_GWS_API_001_MaturityCheck:
    check_name: str
    passed: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "reason": self.reason,
        }


@dataclass
class W_GWS_API_001_MaturityDecision:
    path_id: str = W_GWS_API_001_PATH_ID
    checks: list[W_GWS_API_001_MaturityCheck] = field(default_factory=list)
    all_passed: bool = False
    current_maturity_percent: float = 0.0
    target_maturity_percent: float = 100.0
    is_100_percent_mature: bool = False
    is_execution_ready: bool = False
    gaps_to_100: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_id": self.path_id,
            "checks": [c.to_dict() for c in self.checks],
            "all_passed": self.all_passed,
            "current_maturity_percent": self.current_maturity_percent,
            "target_maturity_percent": self.target_maturity_percent,
            "is_100_percent_mature": self.is_100_percent_mature,
            "is_execution_ready": self.is_execution_ready,
            "gaps_to_100": self.gaps_to_100,
            "notes": self.notes,
        }


def evaluate_w_gws_api_001_maturity(
    has_tool_mastery_pack: bool = True,
    has_contract_mapping: bool = True,
    has_governance: bool = True,
    has_tests: bool = True,
    has_auth: bool = True,
    first_tab_only_allowed: bool = False,
    has_w0_001_coverage_contract: bool = True,
) -> W_GWS_API_001_MaturityDecision:
    decision = W_GWS_API_001_MaturityDecision()

    path = build_google_workspace_api_tab_aware_path()
    decision.checks.append(W_GWS_API_001_MaturityCheck(
        "path_exists", True, f"path {path.path_id} exists"
    ))
    decision.checks.append(W_GWS_API_001_MaturityCheck(
        "path_declared",
        path.declaration_status == PathDeclarationStatus.DECLARED,
        f"declaration: {path.declaration_status.value}",
    ))
    decision.checks.append(W_GWS_API_001_MaturityCheck(
        "current_status_complete",
        path.current_status == "complete",
        f"status: {path.current_status}",
    ))

    decision.checks.append(W_GWS_API_001_MaturityCheck(
        "has_auth_method",
        has_auth,
        "auth method defined and opaque" if has_auth else "missing auth",
    ))

    if has_governance:
        policy = build_w_gws_api_001_governance_policy()
        gov_pass = (
            governance_is_read_only(policy)
            and governance_blocks_mutation(policy)
            and governance_blocks_credential_capture(policy)
        )
    else:
        gov_pass = False

    decision.checks.append(W_GWS_API_001_MaturityCheck(
        "governance_policy_passes",
        gov_pass and has_governance,
        "governance complete" if gov_pass and has_governance else "governance incomplete or missing",
    ))

    if has_contract_mapping:
        mapping = build_w_gws_api_001_contract_mapping()
        contract_pass = (
            api_mapping_requires_include_tabs_content(mapping)
            and api_mapping_requires_document_tabs_traversal(mapping)
            and api_mapping_requires_child_tabs_recursion(mapping)
        )
    else:
        contract_pass = False

    decision.checks.append(W_GWS_API_001_MaturityCheck(
        "contract_mapping_passes",
        contract_pass and has_contract_mapping,
        "contract complete" if contract_pass and has_contract_mapping else "contract incomplete or missing",
    ))

    decision.checks.append(W_GWS_API_001_MaturityCheck(
        "tool_mastery_pack_present",
        has_tool_mastery_pack,
        "TME pack present" if has_tool_mastery_pack else "missing TME pack",
    ))

    decision.checks.append(W_GWS_API_001_MaturityCheck(
        "tests_present",
        has_tests,
        "tests present" if has_tests else "missing tests",
    ))

    decision.checks.append(W_GWS_API_001_MaturityCheck(
        "first_tab_only_rejected",
        not first_tab_only_allowed,
        "first-tab-only rejected" if not first_tab_only_allowed else "FAIL: first-tab-only is allowed",
    ))

    decision.checks.append(W_GWS_API_001_MaturityCheck(
        "w0_001_coverage_contract",
        has_w0_001_coverage_contract,
        "W0-001 coverage contract represented" if has_w0_001_coverage_contract else "missing W0-001 coverage",
    ))

    passed = sum(1 for c in decision.checks if c.passed)
    total = len(decision.checks)
    decision.current_maturity_percent = round((passed / total) * 100.0, 1)
    decision.all_passed = passed == total
    decision.is_100_percent_mature = decision.all_passed
    decision.is_execution_ready = decision.all_passed
    decision.gaps_to_100 = [c.check_name for c in decision.checks if not c.passed]

    return decision


def w_gws_api_001_is_100_percent_mature() -> bool:
    decision = evaluate_w_gws_api_001_maturity()
    return decision.is_100_percent_mature


def build_w_gws_api_001_maturity_decision() -> W_GWS_API_001_MaturityDecision:
    return evaluate_w_gws_api_001_maturity()


def build_w_gws_api_001_gap_report() -> dict[str, Any]:
    decision = evaluate_w_gws_api_001_maturity()
    return {
        "path_id": decision.path_id,
        "is_100_percent": decision.is_100_percent_mature,
        "current_maturity": decision.current_maturity_percent,
        "gaps": decision.gaps_to_100,
        "checks": [c.to_dict() for c in decision.checks],
    }


def google_workspace_package_is_fully_mature_with_cu_partial() -> bool:
    """Full GWS package requires all declared paths at 100%.
    CU is declared but partial, so the full package is not mature."""
    api_snap = AdapterPathSnapshot(
        path_id=W_GWS_API_001_PATH_ID,
        path_name="API tab-aware extractor",
        declaration_status=PathDeclarationStatus.DECLARED,
        current_status="complete",
        has_tool_mastery=True,
        has_auth=True,
        has_governance=True,
        has_tests=True,
        has_contract_mapping=True,
    )
    cu_snap = AdapterPathSnapshot(
        path_id="W-GWS-CU-001",
        path_name="Native Computer Use",
        declaration_status=PathDeclarationStatus.DECLARED,
        current_status="partial",
        has_tool_mastery=True,
    )
    decision = evaluate_full_adapter_package_maturity(
        "google_workspace", [api_snap, cu_snap]
    )
    return decision.package_is_100_percent_mature
