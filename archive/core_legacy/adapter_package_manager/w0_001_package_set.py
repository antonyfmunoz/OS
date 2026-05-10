"""W0-001 Adapter Package Set.

Composes Core + Drive API + Docs API + Drive CU + Docs CU into
the W0-001 operational test package set.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .package_set_contracts import (
    PackageSet,
    PackageSetMember,
    PackageSetStatus,
    build_package_set,
    package_set_all_required_members_mature,
    package_set_api_ready,
    package_set_cu_ready,
    summarize_package_set,
)

W0_001_PACKAGE_SET_ID = "W0-001"
W0_001_PACKAGE_SET_NAME = "W0-001 Google Workspace Triple-Test Package Set"
W0_001_FAMILY_ID = "google_workspace"

_EXCLUDED_FUTURE_CANDIDATES = [
    "Gmail",
    "Google Sheets",
    "Google Slides",
    "Google Calendar",
    "Google Forms",
    "Google Meet",
    "Google Admin",
]

_W0_001_CAPABILITIES = [
    "drive_inventory_via_api",
    "drive_metadata_via_api",
    "docs_tab_aware_extraction_via_api",
    "drive_inventory_via_cu",
    "docs_tab_aware_extraction_via_cu",
    "api_cu_parity_validation",
    "ingestion_coverage_validation",
    "canonical_source_record_emission",
]


def _build_w0_001_members() -> list[PackageSetMember]:
    return [
        PackageSetMember(
            package_id="W-GWS-CORE-001",
            role="core_foundation",
            service_name="Google Workspace Core",
            required_for_test=True,
            current_maturity_percent=100.0,
            target_maturity_percent=100.0,
            status="mature",
        ),
        PackageSetMember(
            package_id="W-GDRIVE-API-001",
            role="service_api",
            service_name="Google Drive",
            required_for_test=True,
            current_maturity_percent=100.0,
            target_maturity_percent=100.0,
            status="mature",
        ),
        PackageSetMember(
            package_id="W-GDOCS-API-001",
            role="service_api",
            service_name="Google Docs",
            required_for_test=True,
            current_maturity_percent=100.0,
            target_maturity_percent=100.0,
            status="mature",
        ),
        PackageSetMember(
            package_id="W-GDRIVE-CU-001",
            role="service_cu",
            service_name="Google Drive",
            required_for_test=True,
            current_maturity_percent=0.0,
            target_maturity_percent=100.0,
            status="partial_needs_hardening",
            blockers=["CU infrastructure not yet proven"],
        ),
        PackageSetMember(
            package_id="W-GDOCS-CU-001",
            role="service_cu",
            service_name="Google Docs",
            required_for_test=True,
            current_maturity_percent=0.0,
            target_maturity_percent=100.0,
            status="partial_needs_hardening",
            blockers=["CU infrastructure not yet proven"],
        ),
    ]


def build_w0_001_adapter_package_set() -> PackageSet:
    return build_package_set(
        package_set_id=W0_001_PACKAGE_SET_ID,
        package_set_name=W0_001_PACKAGE_SET_NAME,
        family_id=W0_001_FAMILY_ID,
        included_packages=_build_w0_001_members(),
        excluded_future_candidates=list(_EXCLUDED_FUTURE_CANDIDATES),
        declared_capabilities=list(_W0_001_CAPABILITIES),
    )


@dataclass
class W0001PackageSetReadiness:
    package_set_id: str = W0_001_PACKAGE_SET_ID
    api_slice_ready: bool = False
    cu_slice_ready: bool = False
    full_triple_test_ready: bool = False
    memory_activation_ready: bool = False
    current_status: str = "not_ready"
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_set_id": self.package_set_id,
            "api_slice_ready": self.api_slice_ready,
            "cu_slice_ready": self.cu_slice_ready,
            "full_triple_test_ready": self.full_triple_test_ready,
            "memory_activation_ready": self.memory_activation_ready,
            "current_status": self.current_status,
            "blockers": self.blockers,
            "notes": self.notes,
        }


def evaluate_w0_001_package_set_readiness() -> W0001PackageSetReadiness:
    ps = build_w0_001_adapter_package_set()
    readiness = W0001PackageSetReadiness()

    readiness.api_slice_ready = package_set_api_ready(ps)
    readiness.cu_slice_ready = package_set_cu_ready(ps)
    readiness.full_triple_test_ready = (
        readiness.api_slice_ready and readiness.cu_slice_ready
    )
    readiness.memory_activation_ready = False
    readiness.blockers = list(ps.blockers)

    if readiness.full_triple_test_ready:
        readiness.current_status = "ready"
    elif readiness.api_slice_ready:
        readiness.current_status = "api_ready"
    else:
        readiness.current_status = "not_ready"

    readiness.notes = [
        "Memory activation requires separate founder review",
        "Full triple-test requires API + CU slices both ready",
    ]
    return readiness


def w0_001_api_slice_is_ready() -> bool:
    ps = build_w0_001_adapter_package_set()
    return package_set_api_ready(ps)


def w0_001_cu_slice_is_ready() -> bool:
    ps = build_w0_001_adapter_package_set()
    return package_set_cu_ready(ps)


def w0_001_full_triple_test_ready() -> bool:
    readiness = evaluate_w0_001_package_set_readiness()
    return readiness.full_triple_test_ready


def build_w0_001_package_set_report() -> dict[str, Any]:
    ps = build_w0_001_adapter_package_set()
    readiness = evaluate_w0_001_package_set_readiness()
    return {
        "package_set": summarize_package_set(ps),
        "readiness": readiness.to_dict(),
    }
