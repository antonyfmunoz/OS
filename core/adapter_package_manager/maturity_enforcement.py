"""Adapter Package Maturity Enforcement.

Selected-tool / access-path 100% maturity gate. No external tool,
SaaS, API, CLI, MCP server, browser tool, computer-use path, file
parser, runtime, or environment may be used by UMH unless the
selected Adapter Package / access path is 100% mature for the
capability being executed.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AdapterExecutionMaturityStatus(str, Enum):
    EXECUTION_READY = "execution_ready"
    MISSING_ADAPTER_PACKAGE = "missing_adapter_package"
    MISSING_TOOL_MASTERY_PACK = "missing_tool_mastery_pack"
    STALE_TOOL_MASTERY_PACK = "stale_tool_mastery_pack"
    INCOMPLETE_TOOL_MASTERY_PACK = "incomplete_tool_mastery_pack"
    MISSING_AUTH_PROFILE = "missing_auth_profile"
    MISSING_ACCESS_PATH = "missing_access_path"
    ACCESS_PATH_PARTIAL = "access_path_partial"
    ACCESS_PATH_BLOCKED = "access_path_blocked"
    ACCESS_PATH_NOT_IMPLEMENTED = "access_path_not_implemented"
    ACCESS_PATH_UNKNOWN = "access_path_unknown"
    MISSING_GOVERNANCE_POLICY = "missing_governance_policy"
    MISSING_NO_SECRET_POLICY = "missing_no_secret_policy"
    MISSING_CONTRACT_MAPPING = "missing_contract_mapping"
    MISSING_TESTS = "missing_tests"
    KNOWN_GAPS_AFFECT_EXECUTION = "known_gaps_affect_execution"
    REQUIRES_APPROVAL = "requires_approval"
    WAIVED_BY_FOUNDER = "waived_by_founder"
    BLOCKED = "blocked"


@dataclass
class AdapterExecutionReadinessDecision:
    tool_name: str
    adapter_package_id: str = ""
    capability: str = ""
    selected_access_path: str = ""
    maturity_status: AdapterExecutionMaturityStatus = (
        AdapterExecutionMaturityStatus.BLOCKED
    )
    target_maturity_percent: float = 100.0
    current_maturity_percent: float = 0.0
    can_execute: bool = False
    block_reasons: list[str] = field(default_factory=list)
    required_fixes: list[str] = field(default_factory=list)
    waiver_status: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "adapter_package_id": self.adapter_package_id,
            "capability": self.capability,
            "selected_access_path": self.selected_access_path,
            "maturity_status": self.maturity_status.value,
            "target_maturity_percent": self.target_maturity_percent,
            "current_maturity_percent": self.current_maturity_percent,
            "can_execute": self.can_execute,
            "block_reasons": self.block_reasons,
            "required_fixes": self.required_fixes,
            "waiver_status": self.waiver_status,
            "notes": self.notes,
        }


@dataclass
class AdapterPackageSnapshot:
    """Lightweight view of an adapter package for maturity evaluation.

    Callers construct this from whatever storage layer they use.
    The enforcement module is pure — no I/O.
    """

    package_id: str = ""
    tool_name: str = ""
    has_adapter_package: bool = False
    has_tool_mastery_pack: bool = False
    tool_mastery_fresh: bool = False
    tool_mastery_complete: bool = False
    has_auth_profile: bool = False
    has_governance_policy: bool = False
    has_no_secret_policy: bool = False
    has_contract_mapping: bool = False
    has_tests: bool = False
    access_path_id: str = ""
    access_path_status: str = ""
    known_gaps: list[str] = field(default_factory=list)
    gaps_affecting_capability: list[str] = field(default_factory=list)
    requires_approval: bool = False
    founder_waiver: bool = False


_MATURITY_CHECKS = [
    "has_adapter_package",
    "has_tool_mastery_pack",
    "tool_mastery_fresh",
    "tool_mastery_complete",
    "has_auth_profile",
    "access_path_complete",
    "has_governance_policy",
    "has_no_secret_policy",
    "has_contract_mapping",
    "has_tests",
    "no_gaps_affect_capability",
]


def selected_access_path_is_complete(path_status: str) -> bool:
    return path_status == "complete"


def adapter_package_has_required_components(snap: AdapterPackageSnapshot) -> bool:
    return all([
        snap.has_adapter_package,
        snap.has_tool_mastery_pack,
        snap.tool_mastery_fresh,
        snap.tool_mastery_complete,
        snap.has_auth_profile,
        snap.has_governance_policy,
        snap.has_no_secret_policy,
        snap.has_contract_mapping,
        snap.has_tests,
    ])


def known_gaps_affect_capability(
    snap: AdapterPackageSnapshot, capability: str
) -> bool:
    return len(snap.gaps_affecting_capability) > 0


def evaluate_adapter_package_execution_readiness(
    snap: AdapterPackageSnapshot,
    capability: str,
    access_path_id: str | None = None,
) -> AdapterExecutionReadinessDecision:
    decision = AdapterExecutionReadinessDecision(
        tool_name=snap.tool_name,
        adapter_package_id=snap.package_id,
        capability=capability,
        selected_access_path=access_path_id or snap.access_path_id,
        target_maturity_percent=100.0,
    )

    if snap.founder_waiver:
        checks_passed = _count_passed_checks(snap, capability)
        decision.maturity_status = AdapterExecutionMaturityStatus.WAIVED_BY_FOUNDER
        decision.can_execute = True
        decision.waiver_status = "waived_by_founder"
        decision.current_maturity_percent = round(
            (checks_passed / len(_MATURITY_CHECKS)) * 100.0, 1
        )
        decision.notes.append("founder waiver — execution allowed but maturity incomplete")
        return decision

    if not snap.has_adapter_package:
        decision.maturity_status = AdapterExecutionMaturityStatus.MISSING_ADAPTER_PACKAGE
        decision.block_reasons.append("no adapter package exists")
        decision.required_fixes.append("create adapter package")
        return decision

    if not snap.has_tool_mastery_pack:
        decision.maturity_status = AdapterExecutionMaturityStatus.MISSING_TOOL_MASTERY_PACK
        decision.block_reasons.append("no Tool Mastery Pack")
        decision.required_fixes.append("create Tool Mastery Pack")
        return decision

    if not snap.tool_mastery_fresh:
        decision.maturity_status = AdapterExecutionMaturityStatus.STALE_TOOL_MASTERY_PACK
        decision.block_reasons.append("Tool Mastery Pack is stale")
        decision.required_fixes.append("re-research Tool Mastery Pack")
        return decision

    if not snap.tool_mastery_complete:
        decision.maturity_status = AdapterExecutionMaturityStatus.INCOMPLETE_TOOL_MASTERY_PACK
        decision.block_reasons.append("Tool Mastery Pack is incomplete")
        decision.required_fixes.append("complete Tool Mastery Pack")
        return decision

    if not snap.has_auth_profile:
        decision.maturity_status = AdapterExecutionMaturityStatus.MISSING_AUTH_PROFILE
        decision.block_reasons.append("no auth profile defined")
        decision.required_fixes.append("define auth profile")
        return decision

    path_status = snap.access_path_status.lower()
    if not path_status or path_status == "":
        decision.maturity_status = AdapterExecutionMaturityStatus.MISSING_ACCESS_PATH
        decision.block_reasons.append("no access path selected")
        decision.required_fixes.append("select access path")
        return decision

    status_map = {
        "partial": AdapterExecutionMaturityStatus.ACCESS_PATH_PARTIAL,
        "blocked": AdapterExecutionMaturityStatus.ACCESS_PATH_BLOCKED,
        "not_implemented": AdapterExecutionMaturityStatus.ACCESS_PATH_NOT_IMPLEMENTED,
        "unknown": AdapterExecutionMaturityStatus.ACCESS_PATH_UNKNOWN,
    }
    if path_status in status_map:
        decision.maturity_status = status_map[path_status]
        decision.block_reasons.append(f"access path is {path_status}")
        decision.required_fixes.append(f"mature access path to complete")
        return decision

    if not snap.has_governance_policy:
        decision.maturity_status = AdapterExecutionMaturityStatus.MISSING_GOVERNANCE_POLICY
        decision.block_reasons.append("no governance policy")
        decision.required_fixes.append("define governance policy")
        return decision

    if not snap.has_no_secret_policy:
        decision.maturity_status = AdapterExecutionMaturityStatus.MISSING_NO_SECRET_POLICY
        decision.block_reasons.append("no no-secret policy")
        decision.required_fixes.append("define no-secret policy")
        return decision

    if not snap.has_contract_mapping:
        decision.maturity_status = AdapterExecutionMaturityStatus.MISSING_CONTRACT_MAPPING
        decision.block_reasons.append("no contract mapping")
        decision.required_fixes.append("create contract mapping")
        return decision

    if not snap.has_tests:
        decision.maturity_status = AdapterExecutionMaturityStatus.MISSING_TESTS
        decision.block_reasons.append("no tests")
        decision.required_fixes.append("create validation tests")
        return decision

    if known_gaps_affect_capability(snap, capability):
        decision.maturity_status = (
            AdapterExecutionMaturityStatus.KNOWN_GAPS_AFFECT_EXECUTION
        )
        decision.block_reasons.extend(snap.gaps_affecting_capability)
        decision.required_fixes.append("resolve gaps affecting capability")
        return decision

    if snap.requires_approval:
        decision.maturity_status = AdapterExecutionMaturityStatus.REQUIRES_APPROVAL
        decision.block_reasons.append("requires approval before execution")
        decision.required_fixes.append("obtain approval")
        return decision

    decision.maturity_status = AdapterExecutionMaturityStatus.EXECUTION_READY
    decision.can_execute = True
    decision.current_maturity_percent = 100.0
    return decision


def _count_passed_checks(snap: AdapterPackageSnapshot, capability: str) -> int:
    checks = [
        snap.has_adapter_package,
        snap.has_tool_mastery_pack,
        snap.tool_mastery_fresh,
        snap.tool_mastery_complete,
        snap.has_auth_profile,
        selected_access_path_is_complete(snap.access_path_status),
        snap.has_governance_policy,
        snap.has_no_secret_policy,
        snap.has_contract_mapping,
        snap.has_tests,
        not known_gaps_affect_capability(snap, capability),
    ]
    return sum(1 for c in checks if c)


def adapter_execution_blocks(decision: AdapterExecutionReadinessDecision) -> bool:
    return not decision.can_execute


def require_100_percent_maturity(
    decision: AdapterExecutionReadinessDecision,
) -> bool:
    return decision.current_maturity_percent >= 100.0


def build_adapter_execution_readiness_report(
    decisions: list[AdapterExecutionReadinessDecision],
) -> dict[str, Any]:
    blocked = [d for d in decisions if not d.can_execute]
    ready = [d for d in decisions if d.can_execute]
    return {
        "total": len(decisions),
        "ready_count": len(ready),
        "blocked_count": len(blocked),
        "ready_tools": [d.tool_name for d in ready],
        "blocked_tools": [
            {"tool": d.tool_name, "status": d.maturity_status.value, "reasons": d.block_reasons}
            for d in blocked
        ],
        "all_ready": len(blocked) == 0,
    }
