"""Full-Path Adapter Package Maturity Contract.

For a full Adapter Package maturity test, every declared access path
must reach 100%. A package with API COMPLETE + CU PARTIAL is not
fully mature if both are declared package paths.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PathDeclarationStatus(str, Enum):
    DECLARED = "declared"
    FUTURE_CANDIDATE = "future_candidate"
    BLOCKED_DEPENDENCY = "blocked_dependency"
    REQUIRES_APPROVAL = "requires_approval"
    DEPRECATED = "deprecated"
    EXCLUDED_FROM_PACKAGE = "excluded_from_package"


class FullPathMaturityStatus(str, Enum):
    FULLY_MATURE = "fully_mature"
    NOT_MATURE = "not_mature"
    HAS_PARTIAL_DECLARED_PATHS = "has_partial_declared_paths"
    HAS_BLOCKED_DECLARED_PATHS = "has_blocked_declared_paths"
    HAS_UNKNOWN_DECLARED_PATHS = "has_unknown_declared_paths"
    HAS_NOT_IMPLEMENTED_DECLARED_PATHS = "has_not_implemented_declared_paths"
    HAS_REQUIRES_APPROVAL_DECLARED_PATHS = "has_requires_approval_declared_paths"
    INVALID_FAKE_COMPLETE = "invalid_fake_complete"


@dataclass
class AdapterPathSnapshot:
    """Lightweight view of a single access path for maturity evaluation."""

    path_id: str = ""
    path_name: str = ""
    declaration_status: PathDeclarationStatus = PathDeclarationStatus.FUTURE_CANDIDATE
    current_status: str = ""
    has_tool_mastery: bool = False
    has_auth: bool = False
    has_governance: bool = False
    has_tests: bool = False
    has_contract_mapping: bool = False
    known_gaps: list[str] = field(default_factory=list)
    requires_approval: bool = False


_PATH_MATURITY_CHECKS = [
    "current_status_complete",
    "has_tool_mastery",
    "has_auth",
    "has_governance",
    "has_tests",
    "has_contract_mapping",
    "no_known_gaps",
]


@dataclass
class AdapterPathMaturityDecision:
    package_id: str = ""
    path_id: str = ""
    path_name: str = ""
    declaration_status: PathDeclarationStatus = PathDeclarationStatus.FUTURE_CANDIDATE
    current_status: str = ""
    target_maturity_percent: float = 100.0
    current_maturity_percent: float = 0.0
    is_declared_package_path: bool = False
    can_count_toward_package_maturity: bool = False
    can_execute: bool = False
    gaps_to_100: list[str] = field(default_factory=list)
    hardening_required: bool = False
    hardening_work_order: str = ""
    blockers: list[str] = field(default_factory=list)
    required_approval: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "path_id": self.path_id,
            "path_name": self.path_name,
            "declaration_status": self.declaration_status.value,
            "current_status": self.current_status,
            "target_maturity_percent": self.target_maturity_percent,
            "current_maturity_percent": self.current_maturity_percent,
            "is_declared_package_path": self.is_declared_package_path,
            "can_count_toward_package_maturity": self.can_count_toward_package_maturity,
            "can_execute": self.can_execute,
            "gaps_to_100": self.gaps_to_100,
            "hardening_required": self.hardening_required,
            "hardening_work_order": self.hardening_work_order,
            "blockers": self.blockers,
            "required_approval": self.required_approval,
            "notes": self.notes,
        }


@dataclass
class FullAdapterPackageMaturityDecision:
    package_id: str = ""
    declared_paths: list[str] = field(default_factory=list)
    candidate_paths: list[str] = field(default_factory=list)
    excluded_paths: list[str] = field(default_factory=list)
    path_decisions: list[AdapterPathMaturityDecision] = field(default_factory=list)
    fully_mature_paths: list[str] = field(default_factory=list)
    immature_declared_paths: list[str] = field(default_factory=list)
    blocked_declared_paths: list[str] = field(default_factory=list)
    approval_required_paths: list[str] = field(default_factory=list)
    package_current_maturity_percent: float = 0.0
    package_target_maturity_percent: float = 100.0
    package_is_100_percent_mature: bool = False
    can_use_for_full_adapter_test: bool = False
    next_required_work_orders: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "declared_paths": self.declared_paths,
            "candidate_paths": self.candidate_paths,
            "excluded_paths": self.excluded_paths,
            "path_decisions": [d.to_dict() for d in self.path_decisions],
            "fully_mature_paths": self.fully_mature_paths,
            "immature_declared_paths": self.immature_declared_paths,
            "blocked_declared_paths": self.blocked_declared_paths,
            "approval_required_paths": self.approval_required_paths,
            "package_current_maturity_percent": self.package_current_maturity_percent,
            "package_target_maturity_percent": self.package_target_maturity_percent,
            "package_is_100_percent_mature": self.package_is_100_percent_mature,
            "can_use_for_full_adapter_test": self.can_use_for_full_adapter_test,
            "next_required_work_orders": self.next_required_work_orders,
            "notes": self.notes,
        }


def _compute_path_maturity(snap: AdapterPathSnapshot) -> tuple[float, list[str]]:
    checks = [
        ("current_status_complete", snap.current_status.lower() == "complete"),
        ("has_tool_mastery", snap.has_tool_mastery),
        ("has_auth", snap.has_auth),
        ("has_governance", snap.has_governance),
        ("has_tests", snap.has_tests),
        ("has_contract_mapping", snap.has_contract_mapping),
        ("no_known_gaps", len(snap.known_gaps) == 0),
    ]
    passed = sum(1 for _, v in checks if v)
    pct = round((passed / len(checks)) * 100.0, 1)
    gaps = [f"missing {name}" for name, v in checks if not v]
    return pct, gaps


def evaluate_path_maturity(
    snap: AdapterPathSnapshot, package_id: str = ""
) -> AdapterPathMaturityDecision:
    pct, gaps = _compute_path_maturity(snap)
    is_declared = snap.declaration_status == PathDeclarationStatus.DECLARED
    can_count = is_declared and pct >= 100.0

    decision = AdapterPathMaturityDecision(
        package_id=package_id,
        path_id=snap.path_id,
        path_name=snap.path_name,
        declaration_status=snap.declaration_status,
        current_status=snap.current_status,
        target_maturity_percent=100.0,
        current_maturity_percent=pct,
        is_declared_package_path=is_declared,
        can_count_toward_package_maturity=can_count,
        can_execute=pct >= 100.0,
        gaps_to_100=gaps,
        hardening_required=pct < 100.0 and is_declared,
    )

    if snap.requires_approval:
        decision.required_approval = "founder_or_security_approval"
        decision.blockers.append("requires approval")

    if snap.current_status.lower() == "blocked":
        decision.blockers.append("path is blocked")

    return decision


def path_counts_toward_package_maturity(
    decision: AdapterPathMaturityDecision,
) -> bool:
    return decision.can_count_toward_package_maturity


def path_blocks_full_package_maturity(
    decision: AdapterPathMaturityDecision,
) -> bool:
    if not decision.is_declared_package_path:
        return False
    return decision.current_maturity_percent < 100.0


def reject_fake_complete_path(snap: AdapterPathSnapshot) -> bool:
    if snap.current_status.lower() == "complete" and len(snap.known_gaps) > 0:
        return True
    if snap.current_status.lower() == "complete" and not snap.has_tool_mastery:
        return True
    if snap.current_status.lower() == "complete" and not snap.has_tests:
        return True
    return False


def evaluate_full_adapter_package_maturity(
    package_id: str,
    paths: list[AdapterPathSnapshot],
) -> FullAdapterPackageMaturityDecision:
    decision = FullAdapterPackageMaturityDecision(package_id=package_id)

    for snap in paths:
        path_decision = evaluate_path_maturity(snap, package_id)
        decision.path_decisions.append(path_decision)

        if snap.declaration_status == PathDeclarationStatus.DECLARED:
            decision.declared_paths.append(snap.path_id)
            if path_decision.current_maturity_percent >= 100.0:
                decision.fully_mature_paths.append(snap.path_id)
            else:
                decision.immature_declared_paths.append(snap.path_id)
                if path_decision.hardening_required:
                    decision.next_required_work_orders.append(
                        f"harden {snap.path_name} to 100%"
                    )
            if snap.current_status.lower() == "blocked":
                decision.blocked_declared_paths.append(snap.path_id)
            if snap.requires_approval:
                decision.approval_required_paths.append(snap.path_id)

        elif snap.declaration_status == PathDeclarationStatus.FUTURE_CANDIDATE:
            decision.candidate_paths.append(snap.path_id)

        elif snap.declaration_status == PathDeclarationStatus.EXCLUDED_FROM_PACKAGE:
            decision.excluded_paths.append(snap.path_id)

    declared_count = len(decision.declared_paths)
    if declared_count > 0:
        mature_count = len(decision.fully_mature_paths)
        decision.package_current_maturity_percent = round(
            (mature_count / declared_count) * 100.0, 1
        )
    else:
        decision.package_current_maturity_percent = 0.0

    decision.package_is_100_percent_mature = (
        declared_count > 0
        and len(decision.immature_declared_paths) == 0
        and len(decision.blocked_declared_paths) == 0
        and len(decision.approval_required_paths) == 0
    )

    decision.can_use_for_full_adapter_test = decision.package_is_100_percent_mature

    return decision


def build_full_path_maturity_report(
    decision: FullAdapterPackageMaturityDecision,
) -> str:
    parts: list[str] = []
    parts.append(f"Package: {decision.package_id}")
    parts.append(f"Maturity: {decision.package_current_maturity_percent}%")
    parts.append(f"Declared paths: {len(decision.declared_paths)}")
    parts.append(f"Fully mature: {len(decision.fully_mature_paths)}")
    parts.append(f"Immature declared: {len(decision.immature_declared_paths)}")
    parts.append(f"Blocked declared: {len(decision.blocked_declared_paths)}")
    parts.append(f"Approval required: {len(decision.approval_required_paths)}")
    parts.append(f"Candidate paths: {len(decision.candidate_paths)}")
    parts.append(f"100% mature: {decision.package_is_100_percent_mature}")
    parts.append(f"Full test ready: {decision.can_use_for_full_adapter_test}")
    if decision.next_required_work_orders:
        parts.append(f"Work orders: {'; '.join(decision.next_required_work_orders)}")
    return "\n".join(parts)
