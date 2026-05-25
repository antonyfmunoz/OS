"""Tests for the 4-tier permission model (Read/Draft/Execute/Commit)."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.types import (
    PermissionTier,
    TIER_ACTION_MAP,
    required_tier_for_action,
)


class TestPermissionTierEnum:
    def test_tier_values(self):
        assert PermissionTier.READ.value == "read"
        assert PermissionTier.DRAFT.value == "draft"
        assert PermissionTier.EXECUTE.value == "execute"
        assert PermissionTier.COMMIT.value == "commit"

    def test_tier_ranks_ascending(self):
        assert PermissionTier.READ.rank < PermissionTier.DRAFT.rank
        assert PermissionTier.DRAFT.rank < PermissionTier.EXECUTE.rank
        assert PermissionTier.EXECUTE.rank < PermissionTier.COMMIT.rank

    def test_permits_self(self):
        for tier in PermissionTier:
            assert tier.permits(tier)

    def test_higher_permits_lower(self):
        assert PermissionTier.COMMIT.permits(PermissionTier.READ)
        assert PermissionTier.COMMIT.permits(PermissionTier.DRAFT)
        assert PermissionTier.COMMIT.permits(PermissionTier.EXECUTE)
        assert PermissionTier.EXECUTE.permits(PermissionTier.READ)
        assert PermissionTier.EXECUTE.permits(PermissionTier.DRAFT)
        assert PermissionTier.DRAFT.permits(PermissionTier.READ)

    def test_lower_does_not_permit_higher(self):
        assert not PermissionTier.READ.permits(PermissionTier.DRAFT)
        assert not PermissionTier.READ.permits(PermissionTier.EXECUTE)
        assert not PermissionTier.READ.permits(PermissionTier.COMMIT)
        assert not PermissionTier.DRAFT.permits(PermissionTier.EXECUTE)
        assert not PermissionTier.DRAFT.permits(PermissionTier.COMMIT)
        assert not PermissionTier.EXECUTE.permits(PermissionTier.COMMIT)


class TestActionMapping:
    def test_no_action_in_multiple_tiers(self):
        seen: dict[str, PermissionTier] = {}
        for tier, actions in TIER_ACTION_MAP.items():
            for action in actions:
                assert action not in seen, (
                    f"Action '{action}' in both {seen[action].value} and {tier.value}"
                )
                seen[action] = tier

    def test_read_actions(self):
        read_actions = TIER_ACTION_MAP[PermissionTier.READ]
        assert "analyze" in read_actions
        assert "research" in read_actions
        assert "read" in read_actions
        assert "query" in read_actions

    def test_draft_actions(self):
        draft_actions = TIER_ACTION_MAP[PermissionTier.DRAFT]
        assert "draft_message" in draft_actions
        assert "draft_content" in draft_actions
        assert "create_task" in draft_actions

    def test_execute_actions(self):
        execute_actions = TIER_ACTION_MAP[PermissionTier.EXECUTE]
        assert "send_message" in execute_actions
        assert "send_email" in execute_actions
        assert "browser_execution" in execute_actions

    def test_commit_actions(self):
        commit_actions = TIER_ACTION_MAP[PermissionTier.COMMIT]
        assert "execute_payment" in commit_actions
        assert "financial_execution" in commit_actions
        assert "production_deployment" in commit_actions


class TestRequiredTier:
    def test_known_actions(self):
        assert required_tier_for_action("analyze") == PermissionTier.READ
        assert required_tier_for_action("draft_message") == PermissionTier.DRAFT
        assert required_tier_for_action("send_message") == PermissionTier.EXECUTE
        assert required_tier_for_action("execute_payment") == PermissionTier.COMMIT

    def test_unknown_defaults_to_read(self):
        assert required_tier_for_action("totally_unknown") == PermissionTier.READ


class TestExecutionAuthorityEngineIntegration:
    def test_tier_blocks_when_insufficient(self):
        from substrate.governance.policy.execution_authority_engine_v1 import (
            AuthorityClass,
            ExecutionAuthorityEngine,
            ExecutionAuthorityRequest,
        )

        engine = ExecutionAuthorityEngine()
        req = ExecutionAuthorityRequest(
            request_id="tier-test-1",
            action_type="send_message",
            action_description="test",
            caller_permission_tier="read",
        )
        decision = engine.evaluate(req)
        assert decision.authority_class == AuthorityClass.DENY
        assert any("permission_tier" in r for r in decision.denial_reasons)

    def test_tier_permits_when_sufficient(self):
        from substrate.governance.policy.execution_authority_engine_v1 import (
            AuthorityClass,
            ExecutionAuthorityEngine,
            ExecutionAuthorityRequest,
        )

        engine = ExecutionAuthorityEngine()
        req = ExecutionAuthorityRequest(
            request_id="tier-test-2",
            action_type="read_only_query",
            action_description="test",
            caller_permission_tier="read",
        )
        decision = engine.evaluate(req)
        assert decision.authority_class == AuthorityClass.READ_ONLY
        assert not any("permission_tier" in r for r in decision.denial_reasons)


class TestGovernanceEngineIntegration:
    def test_check_tier_method(self):
        from substrate.control_plane.governance import ConcreteGovernanceEngine

        engine = ConcreteGovernanceEngine()

        result = engine.check_tier("analyze", "read")
        assert result["permitted"] is True

        result = engine.check_tier("send_message", "draft")
        assert result["permitted"] is False
        assert result["required_tier"] == "execute"

    def test_check_tier_with_invalid_tier(self):
        from substrate.control_plane.governance import ConcreteGovernanceEngine

        engine = ConcreteGovernanceEngine()
        result = engine.check_tier("analyze", "invalid_tier")
        assert result["permitted"] is True
        assert result["caller_tier"] == "execute"
