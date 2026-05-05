"""Governance Policy for W-GWS-API-001.

Defines what is allowed and blocked for the API tab-aware extraction
path. Read-only by default; no mutation, no credential capture.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GovernancePolicy:
    policy_id: str = "w_gws_api_001_governance_policy"
    read_only: bool = True
    allowed_actions: list[str] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)
    instance_scoped: bool = True
    global_canon_default: bool = False
    export_requires_approval: bool = True
    auth_token_opaque: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "read_only": self.read_only,
            "allowed_actions": self.allowed_actions,
            "blocked_actions": self.blocked_actions,
            "instance_scoped": self.instance_scoped,
            "global_canon_default": self.global_canon_default,
            "export_requires_approval": self.export_requires_approval,
            "auth_token_opaque": self.auth_token_opaque,
        }


_ALLOWED_ACTIONS = [
    "read_metadata",
    "read_document_content_through_authorized_api",
    "read_tabs_content_for_in_scope_docs",
    "emit_local_canonical_records",
    "validate_coverage",
    "generate_local_reports",
    "build_source_graph",
]

_BLOCKED_ACTIONS = [
    "edit_documents",
    "delete_documents",
    "move_documents",
    "share_documents",
    "change_permissions",
    "switch_accounts",
    "open_gmail",
    "capture_credentials",
    "capture_tokens",
    "capture_api_keys",
    "capture_cookies",
    "capture_secrets",
    "export_files_without_approval",
    "download_files_without_approval",
    "promote_memory",
    "write_global_canon",
    "mutate_source_files",
    "change_drive_permissions",
]


def build_w_gws_api_001_governance_policy() -> GovernancePolicy:
    return GovernancePolicy(
        allowed_actions=list(_ALLOWED_ACTIONS),
        blocked_actions=list(_BLOCKED_ACTIONS),
    )


def governance_is_read_only(policy: GovernancePolicy) -> bool:
    return policy.read_only


def governance_blocks_mutation(policy: GovernancePolicy) -> bool:
    mutation_actions = [
        "edit_documents",
        "delete_documents",
        "move_documents",
    ]
    return all(a in policy.blocked_actions for a in mutation_actions)


def governance_blocks_credential_capture(policy: GovernancePolicy) -> bool:
    capture_actions = [
        "capture_credentials",
        "capture_tokens",
        "capture_api_keys",
        "capture_cookies",
        "capture_secrets",
    ]
    return all(a in policy.blocked_actions for a in capture_actions)


def governance_blocks_permission_changes(policy: GovernancePolicy) -> bool:
    return (
        "change_permissions" in policy.blocked_actions
        and "share_documents" in policy.blocked_actions
    )


def governance_blocks_memory_promotion(policy: GovernancePolicy) -> bool:
    return "promote_memory" in policy.blocked_actions


def governance_requires_export_approval(policy: GovernancePolicy) -> bool:
    return policy.export_requires_approval


def governance_preserves_instance_scope(policy: GovernancePolicy) -> bool:
    return policy.instance_scoped and not policy.global_canon_default
