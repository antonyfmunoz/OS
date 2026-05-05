"""Adapter Family Contracts.

Defines the Adapter Family, Service Adapter Package, and related
taxonomy for suite-level ecosystems like Google Workspace.

An Adapter Family is NOT a monolithic Adapter Package.
It is a suite-level grouping of service adapter packages that share
auth, governance, identity, rate limits, and ecosystem-level mastery.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AdapterFamilyStatus(str, Enum):
    DRAFT = "draft"
    PARTIAL = "partial"
    ACTIVE = "active"
    FULLY_MATURE = "fully_mature"
    BLOCKED = "blocked"
    DEPRECATED = "deprecated"


class ServicePackageStatus(str, Enum):
    DECLARED = "declared"
    FUTURE_CANDIDATE = "future_candidate"
    BLOCKED = "blocked"
    DEPRECATED = "deprecated"
    EXCLUDED_FROM_SCOPE = "excluded_from_scope"


@dataclass
class ServiceAdapterPackageRef:
    package_id: str
    service_name: str
    service_type: str = "api"
    declaration_status: ServicePackageStatus = ServicePackageStatus.DECLARED
    current_maturity_percent: float = 0.0
    target_maturity_percent: float = 100.0
    declared_for_current_test: bool = False
    blocks_current_test: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "service_name": self.service_name,
            "service_type": self.service_type,
            "declaration_status": self.declaration_status.value,
            "current_maturity_percent": self.current_maturity_percent,
            "target_maturity_percent": self.target_maturity_percent,
            "declared_for_current_test": self.declared_for_current_test,
            "blocks_current_test": self.blocks_current_test,
            "notes": self.notes,
        }


@dataclass
class AdapterFamily:
    family_id: str
    family_name: str
    core_package_id: str
    service_packages: list[ServiceAdapterPackageRef] = field(
        default_factory=list
    )
    future_service_candidates: list[ServiceAdapterPackageRef] = field(
        default_factory=list
    )
    shared_auth_models: list[str] = field(default_factory=list)
    shared_governance: list[str] = field(default_factory=list)
    shared_tool_mastery: list[str] = field(default_factory=list)
    status: AdapterFamilyStatus = AdapterFamilyStatus.DRAFT
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "family_name": self.family_name,
            "core_package_id": self.core_package_id,
            "service_packages": [s.to_dict() for s in self.service_packages],
            "future_service_candidates": [
                s.to_dict() for s in self.future_service_candidates
            ],
            "shared_auth_models": self.shared_auth_models,
            "shared_governance": self.shared_governance,
            "shared_tool_mastery": self.shared_tool_mastery,
            "status": self.status.value,
            "notes": self.notes,
        }


def build_adapter_family(
    family_id: str,
    family_name: str,
    core_package_id: str,
    service_packages: list[ServiceAdapterPackageRef] | None = None,
    future_service_candidates: list[ServiceAdapterPackageRef] | None = None,
    shared_auth_models: list[str] | None = None,
    shared_governance: list[str] | None = None,
    shared_tool_mastery: list[str] | None = None,
    status: AdapterFamilyStatus = AdapterFamilyStatus.DRAFT,
) -> AdapterFamily:
    return AdapterFamily(
        family_id=family_id,
        family_name=family_name,
        core_package_id=core_package_id,
        service_packages=service_packages or [],
        future_service_candidates=future_service_candidates or [],
        shared_auth_models=shared_auth_models or [],
        shared_governance=shared_governance or [],
        shared_tool_mastery=shared_tool_mastery or [],
        status=status,
    )


def adapter_family_is_monolithic(family: AdapterFamily) -> bool:
    """An Adapter Family is never monolithic. Returns False by design."""
    return False


def service_blocks_current_test(service_ref: ServiceAdapterPackageRef) -> bool:
    return service_ref.blocks_current_test


def family_can_be_fully_mature(family: AdapterFamily) -> bool:
    if not family.service_packages:
        return False
    return all(
        s.current_maturity_percent >= 100.0
        for s in family.service_packages
        if s.declaration_status == ServicePackageStatus.DECLARED
    )


def list_declared_services(
    family: AdapterFamily,
) -> list[ServiceAdapterPackageRef]:
    return [
        s
        for s in family.service_packages
        if s.declaration_status == ServicePackageStatus.DECLARED
    ]


def list_future_candidate_services(
    family: AdapterFamily,
) -> list[ServiceAdapterPackageRef]:
    return list(family.future_service_candidates)
