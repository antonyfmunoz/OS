"""Phase 87C approval policy — destructive action safety and approval requirements.

Advisory/planning only. No execution. No deletion. No settings changes.
"""

from __future__ import annotations

from typing import Any

from umh.workstation_optimization.contracts import (
    OptimizationActionType,
    OptimizationApprovalRequirement,
    OptimizationCandidate,
    OptimizationRiskLevel,
    OptimizationReversibility,
)


_NO_APPROVAL_ACTIONS = frozenset(
    {
        OptimizationActionType.EXPLAIN,
        OptimizationActionType.RECOMMEND,
        OptimizationActionType.PRESERVE,
        OptimizationActionType.DEFER,
        OptimizationActionType.BACKUP,
    }
)

_APPROVAL_REQUIRED_ACTIONS = frozenset(
    {
        OptimizationActionType.ARCHIVE,
        OptimizationActionType.MOVE_FILES,
        OptimizationActionType.CLEAR_CACHE,
    }
)

_EXPLICIT_APPROVAL_ACTIONS = frozenset(
    {
        OptimizationActionType.DELETE,
        OptimizationActionType.UNINSTALL,
        OptimizationActionType.KILL_PROCESS,
        OptimizationActionType.CHANGE_SETTING,
        OptimizationActionType.DISABLE_STARTUP,
        OptimizationActionType.RESTORE,
    }
)

_HIGH_REVIEW_ACTIONS = frozenset(
    {
        OptimizationActionType.UPDATE_DRIVER,
        OptimizationActionType.CHANGE_POWER_PROFILE,
        OptimizationActionType.OVERCLOCK,
        OptimizationActionType.UNDERVOLT,
        OptimizationActionType.FAN_CURVE_CHANGE,
    }
)


def determine_approval_requirement(
    candidate: OptimizationCandidate,
) -> OptimizationApprovalRequirement:
    if candidate.action_type in _NO_APPROVAL_ACTIONS:
        return OptimizationApprovalRequirement.NONE
    if candidate.action_type in _HIGH_REVIEW_ACTIONS:
        return OptimizationApprovalRequirement.EXPERT_REVIEW_REQUIRED
    if candidate.action_type in _EXPLICIT_APPROVAL_ACTIONS:
        return OptimizationApprovalRequirement.EXPLICIT_APPROVAL
    if candidate.action_type in _APPROVAL_REQUIRED_ACTIONS:
        return OptimizationApprovalRequirement.EXPLICIT_APPROVAL
    return OptimizationApprovalRequirement.EXPLICIT_APPROVAL


def requires_rollback_plan(candidate: OptimizationCandidate) -> bool:
    if candidate.reversibility in (
        OptimizationReversibility.HARD_TO_REVERSE,
        OptimizationReversibility.IRREVERSIBLE,
    ):
        return True
    if candidate.action_type in _HIGH_REVIEW_ACTIONS:
        return True
    if candidate.action_type in (OptimizationActionType.DELETE, OptimizationActionType.UNINSTALL):
        return True
    return False


def requires_post_action_verification(candidate: OptimizationCandidate) -> bool:
    if candidate.action_type in _HIGH_REVIEW_ACTIONS:
        return True
    if candidate.action_type in (
        OptimizationActionType.DELETE,
        OptimizationActionType.UNINSTALL,
        OptimizationActionType.KILL_PROCESS,
    ):
        return True
    if candidate.action_type == OptimizationActionType.CHANGE_SETTING:
        return True
    return False


def validate_candidate_safe_for_recommendation(candidate: OptimizationCandidate) -> dict[str, Any]:
    warnings: list[str] = []
    safe = True

    if not candidate.target and candidate.action_type not in _NO_APPROVAL_ACTIONS:
        safe = False
        warnings.append("Cannot action a candidate with unknown target")

    if (
        candidate.action_type in _HIGH_REVIEW_ACTIONS
        and candidate.approval_required == OptimizationApprovalRequirement.NONE
    ):
        warnings.append(
            "High-review action should not have NONE approval — overriding to EXPERT_REVIEW_REQUIRED"
        )

    if (
        candidate.reversibility == OptimizationReversibility.IRREVERSIBLE
        and not candidate.rollback_plan_required
    ):
        warnings.append("Irreversible action should require rollback/backup plan")

    return {"safe": safe, "warnings": warnings}


def build_destructive_action_policy() -> dict[str, Any]:
    return {
        "policy_name": "Destructive Action Approval Policy",
        "classification_rules": {
            "unknown": "preserve",
            "sensitive": "preserve",
            "system_critical": "preserve",
            "credential_related": "preserve",
            "user_created": "review",
            "generated_cache_temp": "cleanup_candidate",
        },
        "action_approval_matrix": {
            "explain_recommend_preserve": "no_approval",
            "archive_move_clear_cache": "explicit_approval",
            "delete_uninstall_kill_process_change_setting": "explicit_approval",
            "driver_power_overclock_undervolt_bios_fan": "expert_review_or_one_by_one",
        },
        "irreversible_hard_to_reverse": "requires_rollback_backup_plan_or_block",
        "unknown_target": "cannot_be_actioned",
    }
