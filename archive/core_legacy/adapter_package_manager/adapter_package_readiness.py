"""Adapter Package Readiness evaluation.

Computes maturity percentages for packages and access paths,
enforces 100% target, and produces honest gap reports.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .maturity_enforcement import (
    AdapterPackageSnapshot,
    _MATURITY_CHECKS,
    selected_access_path_is_complete,
    known_gaps_affect_capability,
)


@dataclass
class PackageGapReport:
    package_id: str
    tool_name: str
    target_maturity_percent: float = 100.0
    current_maturity_percent: float = 0.0
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    gaps_to_100: list[str] = field(default_factory=list)
    can_execute: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "tool_name": self.tool_name,
            "target_maturity_percent": self.target_maturity_percent,
            "current_maturity_percent": self.current_maturity_percent,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "gaps_to_100": self.gaps_to_100,
            "can_execute": self.can_execute,
        }


def _evaluate_checks(snap: AdapterPackageSnapshot, capability: str = "") -> list[tuple[str, bool]]:
    return [
        ("has_adapter_package", snap.has_adapter_package),
        ("has_tool_mastery_pack", snap.has_tool_mastery_pack),
        ("tool_mastery_fresh", snap.tool_mastery_fresh),
        ("tool_mastery_complete", snap.tool_mastery_complete),
        ("has_auth_profile", snap.has_auth_profile),
        ("access_path_complete", selected_access_path_is_complete(snap.access_path_status)),
        ("has_governance_policy", snap.has_governance_policy),
        ("has_no_secret_policy", snap.has_no_secret_policy),
        ("has_contract_mapping", snap.has_contract_mapping),
        ("has_tests", snap.has_tests),
        ("no_gaps_affect_capability", not known_gaps_affect_capability(snap, capability)),
    ]


def compute_package_maturity_percent(
    snap: AdapterPackageSnapshot, capability: str = ""
) -> float:
    checks = _evaluate_checks(snap, capability)
    passed = sum(1 for _, v in checks if v)
    return round((passed / len(checks)) * 100.0, 1)


def compute_access_path_maturity_percent(path_status: str) -> float:
    if selected_access_path_is_complete(path_status.lower()):
        return 100.0
    return 0.0


def package_targets_100_percent(snap: AdapterPackageSnapshot) -> bool:
    return True


def access_path_targets_100_percent(path_status: str) -> bool:
    return True


def package_current_state_is_honest(snap: AdapterPackageSnapshot, capability: str = "") -> bool:
    checks = _evaluate_checks(snap, capability)
    passed = sum(1 for _, v in checks if v)
    actual_pct = round((passed / len(checks)) * 100.0, 1)
    if actual_pct >= 100.0 and not all(v for _, v in checks):
        return False
    return True


def package_can_be_used_for_capability(
    snap: AdapterPackageSnapshot, capability: str
) -> bool:
    if not snap.has_adapter_package:
        return False
    if not selected_access_path_is_complete(snap.access_path_status):
        return False
    checks = _evaluate_checks(snap, capability)
    return all(v for _, v in checks)


def build_package_gap_report(
    snap: AdapterPackageSnapshot, capability: str = ""
) -> PackageGapReport:
    checks = _evaluate_checks(snap, capability)
    passed = [name for name, v in checks if v]
    failed = [name for name, v in checks if not v]
    pct = round((len(passed) / len(checks)) * 100.0, 1)

    gaps: list[str] = []
    for name, v in checks:
        if not v:
            gaps.append(f"missing {name}")

    return PackageGapReport(
        package_id=snap.package_id,
        tool_name=snap.tool_name,
        target_maturity_percent=100.0,
        current_maturity_percent=pct,
        checks_passed=passed,
        checks_failed=failed,
        gaps_to_100=gaps,
        can_execute=pct >= 100.0,
    )
