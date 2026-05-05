"""Phase 87C storage model — file classification and cleanup policy.

Advisory/planning only. No real scanning. No file access. No deletion.
"""

from __future__ import annotations

from typing import Any

from umh.workstation_optimization.contracts import (
    FileClassification,
    OptimizationActionType,
    OptimizationApprovalRequirement,
    OptimizationRiskLevel,
    normalize_file_classification,
)


_FILE_ACTION_MAP: dict[
    FileClassification,
    tuple[OptimizationActionType, OptimizationApprovalRequirement, OptimizationRiskLevel],
] = {
    FileClassification.SYSTEM_CRITICAL: (
        OptimizationActionType.PRESERVE,
        OptimizationApprovalRequirement.DISABLED,
        OptimizationRiskLevel.CRITICAL,
    ),
    FileClassification.CREDENTIAL_OR_SECRET: (
        OptimizationActionType.PRESERVE,
        OptimizationApprovalRequirement.DISABLED,
        OptimizationRiskLevel.CRITICAL,
    ),
    FileClassification.BUSINESS_CRITICAL: (
        OptimizationActionType.PRESERVE,
        OptimizationApprovalRequirement.EXPERT_REVIEW_REQUIRED,
        OptimizationRiskLevel.HIGH,
    ),
    FileClassification.LEGAL_FINANCIAL: (
        OptimizationActionType.PRESERVE,
        OptimizationApprovalRequirement.EXPERT_REVIEW_REQUIRED,
        OptimizationRiskLevel.HIGH,
    ),
    FileClassification.USER_CREATED: (
        OptimizationActionType.RECOMMEND,
        OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
        OptimizationRiskLevel.MEDIUM,
    ),
    FileClassification.CLOUD_SYNCED: (
        OptimizationActionType.RECOMMEND,
        OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
        OptimizationRiskLevel.MEDIUM,
    ),
    FileClassification.MEDIA_ARCHIVE: (
        OptimizationActionType.RECOMMEND,
        OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
        OptimizationRiskLevel.MEDIUM,
    ),
    FileClassification.GENERATED_CACHE: (
        OptimizationActionType.CLEAR_CACHE,
        OptimizationApprovalRequirement.BATCH_APPROVAL_ALLOWED,
        OptimizationRiskLevel.LOW,
    ),
    FileClassification.TEMPORARY: (
        OptimizationActionType.CLEAR_CACHE,
        OptimizationApprovalRequirement.BATCH_APPROVAL_ALLOWED,
        OptimizationRiskLevel.LOW,
    ),
    FileClassification.DUPLICATE_CANDIDATE: (
        OptimizationActionType.RECOMMEND,
        OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
        OptimizationRiskLevel.MEDIUM,
    ),
    FileClassification.LARGE_FILE_CANDIDATE: (
        OptimizationActionType.RECOMMEND,
        OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
        OptimizationRiskLevel.MEDIUM,
    ),
    FileClassification.DEVELOPER_ARTIFACT: (
        OptimizationActionType.CLEAR_CACHE,
        OptimizationApprovalRequirement.BATCH_APPROVAL_ALLOWED,
        OptimizationRiskLevel.LOW,
    ),
    FileClassification.UNKNOWN: (
        OptimizationActionType.PRESERVE,
        OptimizationApprovalRequirement.DISABLED,
        OptimizationRiskLevel.MEDIUM,
    ),
}


def classify_file_candidate(
    path_hint: str | None = None,
    name: str | None = None,
    context: str | None = None,
) -> FileClassification:
    hints = " ".join(filter(None, [path_hint, name, context])).lower()
    if not hints:
        return FileClassification.UNKNOWN
    if any(
        k in hints
        for k in ("password", "secret", "credential", "api_key", "token", ".pem", ".key", "id_rsa")
    ):
        return FileClassification.CREDENTIAL_OR_SECRET
    if any(k in hints for k in ("system32", "/system/", "/boot/", "kernel", "initrd")):
        return FileClassification.SYSTEM_CRITICAL
    if any(k in hints for k in ("invoice", "tax", "contract", "legal", "financial")):
        return FileClassification.LEGAL_FINANCIAL
    if any(
        k in hints
        for k in ("node_modules", "__pycache__", ".cache", "build/", "dist/", ".tox", ".mypy_cache")
    ):
        return FileClassification.DEVELOPER_ARTIFACT
    if any(k in hints for k in ("/tmp/", "temp", ".tmp", ".log")):
        return FileClassification.TEMPORARY
    if any(k in hints for k in ("cache", "thumbnail", ".thumbnails")):
        return FileClassification.GENERATED_CACHE
    if any(k in hints for k in ("dropbox", "icloud", "google drive", "onedrive")):
        return FileClassification.CLOUD_SYNCED
    if any(
        k in hints
        for k in (
            ".mp4",
            ".mov",
            ".mp3",
            ".wav",
            ".jpg",
            ".png",
            ".raw",
            "photos",
            "videos",
            "music",
        )
    ):
        return FileClassification.MEDIA_ARCHIVE
    return FileClassification.UNKNOWN


def recommend_file_action(
    file_classification: FileClassification | str,
    sensitivity: str | None = None,
) -> dict[str, Any]:
    fc = (
        normalize_file_classification(file_classification)
        if isinstance(file_classification, str)
        else file_classification
    )
    action, approval, risk = _FILE_ACTION_MAP.get(
        fc,
        (
            OptimizationActionType.PRESERVE,
            OptimizationApprovalRequirement.DISABLED,
            OptimizationRiskLevel.MEDIUM,
        ),
    )
    return {
        "classification": fc.value,
        "recommended_action": action.value,
        "approval_required": approval.value,
        "risk_level": risk.value,
    }


def build_storage_cleanup_policy() -> dict[str, Any]:
    return {
        "policy_name": "Default Storage Cleanup Policy",
        "rules": [
            {
                "classification": fc.value,
                "action": action.value,
                "approval": approval.value,
                "risk": risk.value,
            }
            for fc, (action, approval, risk) in _FILE_ACTION_MAP.items()
        ],
        "core_rule": "Unknown = preserve. Sensitive = preserve. System-critical = preserve. Credential-related = preserve. User-created = review. Generated/cache/temp = cleanup candidate.",
    }


def explain_storage_cleanup_policy() -> str:
    return (
        "Storage cleanup policy: system-critical and credential files are always preserved. "
        "Business-critical and legal/financial files require expert review. User-created and "
        "cloud-synced files require explicit approval. Generated caches, temporary files, and "
        "developer artifacts are cleanup candidates with batch approval. Unknown files are "
        "preserved by default."
    )
