"""Phase 87B permission-first ingestion — no source ingested without explicit approval.

Every source must have user-approved: scope, access method, node location,
sensitivity classification, and review behavior before ingestion begins.

Advisory/planning only. No scraping. No API calls. No account connections.
No file reading. No memory promotion. No execution.
"""

from __future__ import annotations

from typing import Any

from umh.ingestion.contracts import (
    AccessMethod,
    IngestionSource,
    PermissionScope,
    SourceSensitivity,
    SourceStatus,
    _ingest_id,
)


def build_permission_request(
    source: IngestionSource,
) -> dict[str, Any]:
    return {
        "request_id": _ingest_id("perm"),
        "source_id": source.source_id,
        "source_name": source.name,
        "source_class": source.source_class.value,
        "platform": source.platform.value,
        "requested_scopes": [s.value for s in source.permission_scopes],
        "requested_access_methods": [a.value for a in source.access_methods],
        "sensitivity": source.sensitivity.value,
        "review_requirement": source.review_requirement.value,
        "promotion_policy": source.promotion_policy.value,
        "status": "pending_approval",
        "user_must_approve": [
            "Permission scope (what data EOS can read)",
            "Access method (how EOS connects)",
            "Node location (where ingestion runs)",
            "Sensitivity classification (how data is handled)",
            "Review behavior (how candidates are reviewed before promotion)",
        ],
    }


def validate_permission_grant(
    source: IngestionSource,
    granted_scopes: list[PermissionScope],
    granted_access: AccessMethod,
) -> dict[str, Any]:
    warnings: list[str] = []
    valid = True

    if not granted_scopes:
        valid = False
        warnings.append("No permission scopes granted")

    if granted_access == AccessMethod.UNKNOWN:
        valid = False
        warnings.append("Access method not specified")

    if source.sensitivity == SourceSensitivity.FINANCIAL:
        if PermissionScope.READ_WRITE in granted_scopes:
            warnings.append("READ_WRITE on financial source — requires extra caution")
        if granted_access == AccessMethod.BROWSER_SESSION:
            warnings.append("Browser session access to financial source — prefer official API")

    if source.sensitivity == SourceSensitivity.CREDENTIAL:
        valid = False
        warnings.append("Credential sources cannot be ingested — access only at runtime")

    if granted_access == AccessMethod.SCREEN_CAPTURE:
        warnings.append("Screen capture access — ensure user has opted in explicitly")

    if granted_access == AccessMethod.BROWSER_SESSION:
        if PermissionScope.READ_WRITE in granted_scopes:
            warnings.append("Browser session with READ_WRITE — risk of unintended mutations")

    return {
        "valid": valid,
        "warnings": warnings,
        "granted_scopes": [s.value for s in granted_scopes],
        "granted_access": granted_access.value,
    }


def check_source_ready_for_ingestion(source: IngestionSource) -> dict[str, Any]:
    ready = True
    blockers: list[str] = []
    warnings: list[str] = []

    if source.status not in (SourceStatus.APPROVED, SourceStatus.CONNECTED):
        ready = False
        blockers.append(f"Source status is {source.status.value} — must be approved or connected")

    if not source.permission_scopes:
        ready = False
        blockers.append("No permission scopes defined")

    if not source.access_methods:
        ready = False
        blockers.append("No access methods defined")

    if source.sensitivity == SourceSensitivity.CREDENTIAL:
        ready = False
        blockers.append("Credential sources cannot be ingested")

    if source.sensitivity == SourceSensitivity.FINANCIAL:
        warnings.append("Financial source — review requirement should be FULL_REVIEW or higher")

    return {
        "ready": ready,
        "blockers": blockers,
        "warnings": warnings,
        "source_id": source.source_id,
        "status": source.status.value,
    }


def classify_permission_risk(
    scope: PermissionScope,
    access: AccessMethod,
    sensitivity: SourceSensitivity,
) -> str:
    if sensitivity == SourceSensitivity.CREDENTIAL:
        return "blocked"
    if sensitivity == SourceSensitivity.FINANCIAL and scope == PermissionScope.READ_WRITE:
        return "critical"
    if sensitivity == SourceSensitivity.FINANCIAL:
        return "high"
    if access == AccessMethod.BROWSER_SESSION and scope == PermissionScope.READ_WRITE:
        return "high"
    if sensitivity == SourceSensitivity.CONFIDENTIAL:
        return "medium"
    if access == AccessMethod.SCREEN_CAPTURE:
        return "medium"
    if scope in (
        PermissionScope.READ_ONLY,
        PermissionScope.READ_METADATA,
        PermissionScope.EXPORT_ONLY,
    ):
        return "low"
    return "medium"
