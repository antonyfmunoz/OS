"""Google Workspace Adapter Family.

Google Workspace is an Adapter Family — a suite-level grouping
of service adapter packages. NOT a monolithic Adapter Package.

Declared for W0-001: Core, Google Drive, Google Docs.
Future candidates: Gmail, Sheets, Slides, Calendar, Forms, Meet, Admin.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from .adapter_family_contracts import (
    AdapterFamily,
    AdapterFamilyStatus,
    ServiceAdapterPackageRef,
    ServicePackageStatus,
    build_adapter_family,
)

GWS_FAMILY_ID = "google_workspace"
GWS_FAMILY_NAME = "Google Workspace Adapter Family"
GWS_CORE_PACKAGE_ID = "W-GWS-CORE-001"

_SHARED_AUTH_MODELS = [
    "OAUTH_USER_CONSENT_OPAQUE_TOKEN_CACHE",
    "BROWSER_PROFILE_SESSION_AUTH_CANDIDATE",
    "SERVICE_ACCOUNT_DOMAIN_WIDE_DELEGATION_FUTURE",
]

_SHARED_GOVERNANCE = [
    "read_only_default",
    "no_credential_capture",
    "no_token_cookie_reading",
    "no_account_switching_unless_approved",
    "instance_scope_preservation",
    "export_requires_approval",
    "mutation_requires_approval",
    "no_memory_promotion",
]

_SHARED_TOOL_MASTERY = [
    "google_workspace_tool_mastery_pack",
    "google_docs_tool_mastery_pack",
    "google_drive_tool_mastery_pack",
]

_W0_001_DECLARED_SERVICES = [
    ServiceAdapterPackageRef(
        package_id="W-GDRIVE-API-001",
        service_name="Google Drive",
        service_type="api",
        declaration_status=ServicePackageStatus.DECLARED,
        current_maturity_percent=100.0,
        declared_for_current_test=True,
        blocks_current_test=True,
    ),
    ServiceAdapterPackageRef(
        package_id="W-GDOCS-API-001",
        service_name="Google Docs",
        service_type="api",
        declaration_status=ServicePackageStatus.DECLARED,
        current_maturity_percent=100.0,
        declared_for_current_test=True,
        blocks_current_test=True,
    ),
    ServiceAdapterPackageRef(
        package_id="W-GDRIVE-CU-001",
        service_name="Google Drive",
        service_type="computer_use",
        declaration_status=ServicePackageStatus.DECLARED,
        current_maturity_percent=0.0,
        declared_for_current_test=True,
        blocks_current_test=True,
        notes=["CU infrastructure not yet proven"],
    ),
    ServiceAdapterPackageRef(
        package_id="W-GDOCS-CU-001",
        service_name="Google Docs",
        service_type="computer_use",
        declaration_status=ServicePackageStatus.DECLARED,
        current_maturity_percent=0.0,
        declared_for_current_test=True,
        blocks_current_test=True,
        notes=["CU infrastructure not yet proven"],
    ),
]

_FUTURE_SERVICE_CANDIDATES = [
    ServiceAdapterPackageRef(
        package_id="W-GMAIL-001",
        service_name="Gmail",
        service_type="api",
        declaration_status=ServicePackageStatus.FUTURE_CANDIDATE,
        declared_for_current_test=False,
        blocks_current_test=False,
    ),
    ServiceAdapterPackageRef(
        package_id="W-GSHEETS-001",
        service_name="Google Sheets",
        service_type="api",
        declaration_status=ServicePackageStatus.FUTURE_CANDIDATE,
        declared_for_current_test=False,
        blocks_current_test=False,
    ),
    ServiceAdapterPackageRef(
        package_id="W-GSLIDES-001",
        service_name="Google Slides",
        service_type="api",
        declaration_status=ServicePackageStatus.FUTURE_CANDIDATE,
        declared_for_current_test=False,
        blocks_current_test=False,
    ),
    ServiceAdapterPackageRef(
        package_id="W-GCALENDAR-001",
        service_name="Google Calendar",
        service_type="api",
        declaration_status=ServicePackageStatus.FUTURE_CANDIDATE,
        declared_for_current_test=False,
        blocks_current_test=False,
    ),
    ServiceAdapterPackageRef(
        package_id="W-GFORMS-001",
        service_name="Google Forms",
        service_type="api",
        declaration_status=ServicePackageStatus.FUTURE_CANDIDATE,
        declared_for_current_test=False,
        blocks_current_test=False,
    ),
    ServiceAdapterPackageRef(
        package_id="W-GMEET-001",
        service_name="Google Meet",
        service_type="api",
        declaration_status=ServicePackageStatus.FUTURE_CANDIDATE,
        declared_for_current_test=False,
        blocks_current_test=False,
    ),
    ServiceAdapterPackageRef(
        package_id="W-GADMIN-001",
        service_name="Google Admin / Workspace Identity",
        service_type="api",
        declaration_status=ServicePackageStatus.FUTURE_CANDIDATE,
        declared_for_current_test=False,
        blocks_current_test=False,
    ),
]


def build_google_workspace_adapter_family() -> AdapterFamily:
    return build_adapter_family(
        family_id=GWS_FAMILY_ID,
        family_name=GWS_FAMILY_NAME,
        core_package_id=GWS_CORE_PACKAGE_ID,
        service_packages=list(_W0_001_DECLARED_SERVICES),
        future_service_candidates=list(_FUTURE_SERVICE_CANDIDATES),
        shared_auth_models=list(_SHARED_AUTH_MODELS),
        shared_governance=list(_SHARED_GOVERNANCE),
        shared_tool_mastery=list(_SHARED_TOOL_MASTERY),
        status=AdapterFamilyStatus.PARTIAL,
    )
