"""
Governance gate contracts for Phase 94D.4.

Every action passes through governance before execution.
Gates produce ALLOW, REQUIRE_ADVISOR_APPROVAL, BLOCK, or PAUSE_FOR_HUMAN.

No action bypasses governance. BLOCK is terminal for that action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GateDecision(str, Enum):
    ALLOW = "allow"
    REQUIRE_ADVISOR_APPROVAL = "require_advisor_approval"
    BLOCK = "block"
    PAUSE_FOR_HUMAN = "pause_for_human"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class GovernanceGate:
    action_type: str
    decision: GateDecision
    risk_level: RiskLevel
    reason: str
    evaluated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "decision": self.decision.value,
            "risk_level": self.risk_level.value,
            "reason": self.reason,
            "evaluated_at": self.evaluated_at,
        }


ALWAYS_BLOCKED_ACTIONS: frozenset[str] = frozenset(
    {
        "send_emails",
        "send_dms",
        "post_content",
        "edit_documents",
        "delete_files",
        "change_permissions",
        "change_account_settings",
        "capture_credentials",
        "process_payments",
        "subscribe_unsubscribe",
        "purchase",
        "install_software",
        "modify_system_settings",
        "autonomous_social_actions",
        "run_arbitrary_shell_commands",
    }
)

APPROVAL_REQUIRED_ACTIONS: frozenset[str] = frozenset(
    {
        "open_source_account",
        "open_folder",
        "read_document",
        "deep_read_content",
        "export_document",
        "download_file",
        "screenshot_capture",
        "follow_external_link",
        "switch_backend",
        "browser_automation_fallback",
    }
)

ALLOWED_SCOPED_ACTIONS: frozenset[str] = frozenset(
    {
        "inventory_files",
        "inventory_folders",
        "read_metadata",
        "classify_document",
        "write_result_report",
        "check_node_health",
        "check_backend_availability",
    }
)


@dataclass
class GovernancePolicy:
    blocked_actions: frozenset[str] = field(default_factory=lambda: ALWAYS_BLOCKED_ACTIONS)
    approval_required_actions: frozenset[str] = field(
        default_factory=lambda: APPROVAL_REQUIRED_ACTIONS
    )
    allowed_scoped_actions: frozenset[str] = field(default_factory=lambda: ALLOWED_SCOPED_ACTIONS)
    memory_promotion_requires_review: bool = True
    browser_automation_requires_approval: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "blocked_actions": sorted(self.blocked_actions),
            "approval_required_actions": sorted(self.approval_required_actions),
            "allowed_scoped_actions": sorted(self.allowed_scoped_actions),
            "memory_promotion_requires_review": self.memory_promotion_requires_review,
            "browser_automation_requires_approval": self.browser_automation_requires_approval,
        }


def evaluate_action_gate(action_type: str, policy: GovernancePolicy) -> GovernanceGate:
    """Evaluate governance gate for an action type."""
    if action_type in policy.blocked_actions:
        return GovernanceGate(
            action_type=action_type,
            decision=GateDecision.BLOCK,
            risk_level=RiskLevel.CRITICAL,
            reason=f"Action '{action_type}' is permanently blocked by governance policy",
        )

    if action_type == "promote_memory_without_governance":
        if policy.memory_promotion_requires_review:
            return GovernanceGate(
                action_type=action_type,
                decision=GateDecision.BLOCK,
                risk_level=RiskLevel.HIGH,
                reason="Memory promotion blocked without explicit review approval",
            )

    if action_type == "browser_automation_fallback":
        if policy.browser_automation_requires_approval:
            return GovernanceGate(
                action_type=action_type,
                decision=GateDecision.REQUIRE_ADVISOR_APPROVAL,
                risk_level=RiskLevel.MEDIUM,
                reason="Browser automation requires explicit founder approval when GUI computer-use is preferred",
            )

    if action_type in policy.approval_required_actions:
        return GovernanceGate(
            action_type=action_type,
            decision=GateDecision.REQUIRE_ADVISOR_APPROVAL,
            risk_level=RiskLevel.MEDIUM,
            reason=f"Action '{action_type}' requires advisor approval",
        )

    if action_type in policy.allowed_scoped_actions:
        return GovernanceGate(
            action_type=action_type,
            decision=GateDecision.ALLOW,
            risk_level=RiskLevel.LOW,
            reason=f"Action '{action_type}' allowed within scope",
        )

    return GovernanceGate(
        action_type=action_type,
        decision=GateDecision.REQUIRE_ADVISOR_APPROVAL,
        risk_level=RiskLevel.MEDIUM,
        reason=f"Unknown action '{action_type}' — defaulting to advisor approval",
    )
