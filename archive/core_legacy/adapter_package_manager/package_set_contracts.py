"""Package Set Contracts.

A Package Set is a composed operational bundle used for a specific
test or workflow. It selects packages from an Adapter Family and
evaluates readiness for the specific test scope.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PackageSetStatus(str, Enum):
    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    API_READY = "api_ready"
    CU_BLOCKED = "cu_blocked"
    INGESTION_VALIDATED = "ingestion_validated"
    NOT_READY = "not_ready"


@dataclass
class PackageSetMember:
    package_id: str
    role: str
    service_name: str
    required_for_test: bool = True
    current_maturity_percent: float = 0.0
    target_maturity_percent: float = 100.0
    status: str = "not_ready"
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "role": self.role,
            "service_name": self.service_name,
            "required_for_test": self.required_for_test,
            "current_maturity_percent": self.current_maturity_percent,
            "target_maturity_percent": self.target_maturity_percent,
            "status": self.status,
            "blockers": self.blockers,
            "notes": self.notes,
        }


@dataclass
class PackageSet:
    package_set_id: str
    package_set_name: str
    family_id: str
    included_packages: list[PackageSetMember] = field(default_factory=list)
    excluded_future_candidates: list[str] = field(default_factory=list)
    declared_capabilities: list[str] = field(default_factory=list)
    current_status: PackageSetStatus = PackageSetStatus.NOT_READY
    maturity_summary: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_set_id": self.package_set_id,
            "package_set_name": self.package_set_name,
            "family_id": self.family_id,
            "included_packages": [p.to_dict() for p in self.included_packages],
            "excluded_future_candidates": self.excluded_future_candidates,
            "declared_capabilities": self.declared_capabilities,
            "current_status": self.current_status.value,
            "maturity_summary": self.maturity_summary,
            "blockers": self.blockers,
            "notes": self.notes,
        }


def build_package_set(
    package_set_id: str,
    package_set_name: str,
    family_id: str,
    included_packages: list[PackageSetMember] | None = None,
    excluded_future_candidates: list[str] | None = None,
    declared_capabilities: list[str] | None = None,
) -> PackageSet:
    ps = PackageSet(
        package_set_id=package_set_id,
        package_set_name=package_set_name,
        family_id=family_id,
        included_packages=included_packages or [],
        excluded_future_candidates=excluded_future_candidates or [],
        declared_capabilities=declared_capabilities or [],
    )
    ps.current_status = _compute_status(ps)
    ps.maturity_summary = _compute_maturity_summary(ps)
    ps.blockers = _compute_blockers(ps)
    return ps


def _compute_status(ps: PackageSet) -> PackageSetStatus:
    required = [m for m in ps.included_packages if m.required_for_test]
    if not required:
        return PackageSetStatus.NOT_READY
    all_mature = all(m.current_maturity_percent >= 100.0 for m in required)
    if all_mature:
        return PackageSetStatus.READY

    api_members = [m for m in required if "cu" not in m.package_id.lower()]
    cu_members = [m for m in required if "cu" in m.package_id.lower()]
    api_ready = all(m.current_maturity_percent >= 100.0 for m in api_members) if api_members else False
    cu_ready = all(m.current_maturity_percent >= 100.0 for m in cu_members) if cu_members else False

    if api_ready and not cu_ready:
        return PackageSetStatus.API_READY
    if cu_members and not cu_ready:
        return PackageSetStatus.CU_BLOCKED
    return PackageSetStatus.PARTIAL


def _compute_maturity_summary(ps: PackageSet) -> dict[str, Any]:
    required = [m for m in ps.included_packages if m.required_for_test]
    if not required:
        return {"total_members": 0, "mature_members": 0, "percent": 0.0}
    mature = sum(1 for m in required if m.current_maturity_percent >= 100.0)
    return {
        "total_members": len(required),
        "mature_members": mature,
        "percent": round((mature / len(required)) * 100.0, 1),
    }


def _compute_blockers(ps: PackageSet) -> list[str]:
    blockers = []
    for m in ps.included_packages:
        if m.required_for_test and m.current_maturity_percent < 100.0:
            blockers.append(f"{m.package_id} at {m.current_maturity_percent}%")
    return blockers


def package_set_all_required_members_mature(package_set: PackageSet) -> bool:
    required = [
        m for m in package_set.included_packages if m.required_for_test
    ]
    return all(m.current_maturity_percent >= 100.0 for m in required)


def package_set_api_ready(package_set: PackageSet) -> bool:
    api_members = [
        m
        for m in package_set.included_packages
        if m.required_for_test and "cu" not in m.package_id.lower()
    ]
    return bool(api_members) and all(
        m.current_maturity_percent >= 100.0 for m in api_members
    )


def package_set_cu_ready(package_set: PackageSet) -> bool:
    cu_members = [
        m
        for m in package_set.included_packages
        if m.required_for_test and "cu" in m.package_id.lower()
    ]
    return bool(cu_members) and all(
        m.current_maturity_percent >= 100.0 for m in cu_members
    )


def package_set_blocks_memory_review(package_set: PackageSet) -> bool:
    return not package_set_all_required_members_mature(package_set)


def summarize_package_set(package_set: PackageSet) -> dict[str, Any]:
    return {
        "package_set_id": package_set.package_set_id,
        "status": package_set.current_status.value,
        "api_ready": package_set_api_ready(package_set),
        "cu_ready": package_set_cu_ready(package_set),
        "all_ready": package_set_all_required_members_mature(package_set),
        "blockers": package_set.blockers,
        "maturity_summary": package_set.maturity_summary,
    }
