"""Tests for W-GWS-API-001 Governance Policy.

Validates read-only enforcement, mutation blocking, credential capture
blocking, permission controls, and instance scope preservation.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_workspace_api_governance import (
    GovernancePolicy,
    build_w_gws_api_001_governance_policy,
    governance_blocks_credential_capture,
    governance_blocks_memory_promotion,
    governance_blocks_mutation,
    governance_blocks_permission_changes,
    governance_is_read_only,
    governance_preserves_instance_scope,
    governance_requires_export_approval,
)


class TestGovernancePolicy(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = build_w_gws_api_001_governance_policy()

    def test_policy_builds(self) -> None:
        self.assertIsInstance(self.policy, GovernancePolicy)

    def test_policy_id(self) -> None:
        self.assertEqual(
            self.policy.policy_id, "w_gws_api_001_governance_policy"
        )

    def test_is_read_only(self) -> None:
        self.assertTrue(governance_is_read_only(self.policy))

    def test_blocks_mutations(self) -> None:
        self.assertTrue(governance_blocks_mutation(self.policy))

    def test_blocks_edit_documents(self) -> None:
        self.assertIn("edit_documents", self.policy.blocked_actions)

    def test_blocks_delete_documents(self) -> None:
        self.assertIn("delete_documents", self.policy.blocked_actions)

    def test_blocks_move_documents(self) -> None:
        self.assertIn("move_documents", self.policy.blocked_actions)

    def test_blocks_credential_capture(self) -> None:
        self.assertTrue(governance_blocks_credential_capture(self.policy))

    def test_blocks_all_capture_actions(self) -> None:
        for action in [
            "capture_credentials",
            "capture_tokens",
            "capture_api_keys",
            "capture_cookies",
            "capture_secrets",
        ]:
            self.assertIn(
                action,
                self.policy.blocked_actions,
                f"missing blocked action: {action}",
            )

    def test_blocks_permission_changes(self) -> None:
        self.assertTrue(governance_blocks_permission_changes(self.policy))

    def test_blocks_memory_promotion(self) -> None:
        self.assertTrue(governance_blocks_memory_promotion(self.policy))

    def test_requires_export_approval(self) -> None:
        self.assertTrue(governance_requires_export_approval(self.policy))

    def test_preserves_instance_scope(self) -> None:
        self.assertTrue(governance_preserves_instance_scope(self.policy))

    def test_global_canon_default_false(self) -> None:
        self.assertFalse(self.policy.global_canon_default)

    def test_auth_token_opaque(self) -> None:
        self.assertTrue(self.policy.auth_token_opaque)

    def test_allowed_actions_present(self) -> None:
        self.assertTrue(len(self.policy.allowed_actions) >= 7)
        self.assertIn("read_metadata", self.policy.allowed_actions)

    def test_blocked_actions_count(self) -> None:
        self.assertTrue(len(self.policy.blocked_actions) >= 18)

    def test_blocks_account_switching(self) -> None:
        self.assertIn("switch_accounts", self.policy.blocked_actions)

    def test_blocks_gmail_access(self) -> None:
        self.assertIn("open_gmail", self.policy.blocked_actions)

    def test_blocks_global_canon_write(self) -> None:
        self.assertIn("write_global_canon", self.policy.blocked_actions)

    def test_to_dict_roundtrip(self) -> None:
        d = self.policy.to_dict()
        self.assertEqual(d["policy_id"], "w_gws_api_001_governance_policy")
        self.assertTrue(d["read_only"])
        self.assertIsInstance(d["allowed_actions"], list)
        self.assertIsInstance(d["blocked_actions"], list)

    def test_non_read_only_policy_fails_check(self) -> None:
        policy = GovernancePolicy(read_only=False)
        self.assertFalse(governance_is_read_only(policy))

    def test_missing_blocked_actions_fails_mutation_check(self) -> None:
        policy = GovernancePolicy(blocked_actions=[])
        self.assertFalse(governance_blocks_mutation(policy))

    def test_missing_blocked_actions_fails_capture_check(self) -> None:
        policy = GovernancePolicy(blocked_actions=[])
        self.assertFalse(governance_blocks_credential_capture(policy))

    def test_global_canon_true_breaks_instance_scope(self) -> None:
        policy = GovernancePolicy(global_canon_default=True)
        self.assertFalse(governance_preserves_instance_scope(policy))


if __name__ == "__main__":
    unittest.main()
