"""Tests for Phase 94D.4 governance gate contracts."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest

from runtime.substrate.governance_gate_contracts import (
    ALLOWED_SCOPED_ACTIONS,
    ALWAYS_BLOCKED_ACTIONS,
    APPROVAL_REQUIRED_ACTIONS,
    GateDecision,
    GovernanceGate,
    GovernancePolicy,
    RiskLevel,
    evaluate_action_gate,
)


class TestAlwaysBlockedActions:
    def test_send_emails_blocked(self):
        policy = GovernancePolicy()
        gate = evaluate_action_gate("send_emails", policy)
        assert gate.decision == GateDecision.BLOCK
        assert gate.risk_level == RiskLevel.CRITICAL

    def test_delete_files_blocked(self):
        policy = GovernancePolicy()
        gate = evaluate_action_gate("delete_files", policy)
        assert gate.decision == GateDecision.BLOCK

    def test_process_payments_blocked(self):
        policy = GovernancePolicy()
        gate = evaluate_action_gate("process_payments", policy)
        assert gate.decision == GateDecision.BLOCK

    def test_run_arbitrary_shell_commands_blocked(self):
        policy = GovernancePolicy()
        gate = evaluate_action_gate("run_arbitrary_shell_commands", policy)
        assert gate.decision == GateDecision.BLOCK

    def test_all_blocked_actions_are_blocked(self):
        policy = GovernancePolicy()
        for action in ALWAYS_BLOCKED_ACTIONS:
            gate = evaluate_action_gate(action, policy)
            assert gate.decision == GateDecision.BLOCK, f"{action} should be BLOCKED"


class TestApprovalRequiredActions:
    def test_read_document_requires_approval(self):
        policy = GovernancePolicy()
        gate = evaluate_action_gate("read_document", policy)
        assert gate.decision == GateDecision.REQUIRE_ADVISOR_APPROVAL

    def test_download_file_requires_approval(self):
        policy = GovernancePolicy()
        gate = evaluate_action_gate("download_file", policy)
        assert gate.decision == GateDecision.REQUIRE_ADVISOR_APPROVAL

    def test_browser_automation_fallback_requires_approval(self):
        policy = GovernancePolicy()
        gate = evaluate_action_gate("browser_automation_fallback", policy)
        assert gate.decision == GateDecision.REQUIRE_ADVISOR_APPROVAL

    def test_all_approval_actions_require_approval(self):
        policy = GovernancePolicy()
        for action in APPROVAL_REQUIRED_ACTIONS:
            gate = evaluate_action_gate(action, policy)
            assert gate.decision == GateDecision.REQUIRE_ADVISOR_APPROVAL, (
                f"{action} should require approval"
            )


class TestAllowedScopedActions:
    def test_inventory_files_allowed(self):
        policy = GovernancePolicy()
        gate = evaluate_action_gate("inventory_files", policy)
        assert gate.decision == GateDecision.ALLOW
        assert gate.risk_level == RiskLevel.LOW

    def test_read_metadata_allowed(self):
        policy = GovernancePolicy()
        gate = evaluate_action_gate("read_metadata", policy)
        assert gate.decision == GateDecision.ALLOW

    def test_all_scoped_actions_allowed(self):
        policy = GovernancePolicy()
        for action in ALLOWED_SCOPED_ACTIONS:
            gate = evaluate_action_gate(action, policy)
            assert gate.decision == GateDecision.ALLOW, f"{action} should be ALLOWED"


class TestUnknownActions:
    def test_unknown_action_defaults_to_approval(self):
        policy = GovernancePolicy()
        gate = evaluate_action_gate("some_new_action_never_seen", policy)
        assert gate.decision == GateDecision.REQUIRE_ADVISOR_APPROVAL
        assert gate.risk_level == RiskLevel.MEDIUM

    def test_reason_mentions_unknown(self):
        policy = GovernancePolicy()
        gate = evaluate_action_gate("mystery_action", policy)
        assert "unknown" in gate.reason.lower()


class TestMemoryPromotionGovernance:
    def test_memory_promotion_blocked_by_default(self):
        policy = GovernancePolicy()
        gate = evaluate_action_gate("promote_memory_without_governance", policy)
        assert gate.decision == GateDecision.BLOCK

    def test_memory_promotion_allowed_when_policy_disabled(self):
        policy = GovernancePolicy(memory_promotion_requires_review=False)
        gate = evaluate_action_gate("promote_memory_without_governance", policy)
        assert gate.decision != GateDecision.BLOCK


class TestGovernanceGateSerialization:
    def test_to_dict(self):
        gate = GovernanceGate(
            action_type="test_action",
            decision=GateDecision.ALLOW,
            risk_level=RiskLevel.LOW,
            reason="Test reason",
        )
        d = gate.to_dict()
        assert d["action_type"] == "test_action"
        assert d["decision"] == "allow"
        assert d["risk_level"] == "low"
        assert "evaluated_at" in d


class TestGovernancePolicySerialization:
    def test_policy_to_dict(self):
        policy = GovernancePolicy()
        d = policy.to_dict()
        assert "blocked_actions" in d
        assert "approval_required_actions" in d
        assert "allowed_scoped_actions" in d
        assert isinstance(d["blocked_actions"], list)
        assert d["memory_promotion_requires_review"] is True
