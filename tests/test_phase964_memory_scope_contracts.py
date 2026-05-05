"""Tests for eos_ai/substrate/memory_scope_contracts.py (Phase 96.4)."""

import sys

sys.path.insert(0, "/opt/OS")

import unittest

from eos_ai.substrate.memory_scope_contracts import (
    MemoryScope,
    MemoryScopeAssignment,
    PromotionPath,
    can_promote_to_global_canon,
    canonical_source_record_is_not_global_canon,
    raw_account_data_default_scope,
    requires_abstraction_for_global,
)


class TestMemoryScope(unittest.TestCase):
    def test_has_9_values(self) -> None:
        self.assertEqual(len(MemoryScope), 9)


class TestPromotionPath(unittest.TestCase):
    def test_has_6_values(self) -> None:
        self.assertEqual(len(PromotionPath), 6)


class TestMemoryScopeFunctions(unittest.TestCase):
    def test_raw_account_data_defaults_to_instance_memory(self) -> None:
        """User account ingestion defaults to INSTANCE_MEMORY."""
        self.assertEqual(raw_account_data_default_scope(), MemoryScope.INSTANCE_MEMORY)

    def test_canonical_source_record_is_not_global_canon(self) -> None:
        """CanonicalSourceRecord != global canon."""
        self.assertTrue(canonical_source_record_is_not_global_canon())

    def test_cannot_promote_without_both_abstraction_and_approval(self) -> None:
        # Missing both
        self.assertFalse(can_promote_to_global_canon(MemoryScope.INSTANCE_MEMORY, False, False))
        # Missing founder approval
        self.assertFalse(can_promote_to_global_canon(MemoryScope.INSTANCE_MEMORY, True, False))
        # Missing abstraction
        self.assertFalse(can_promote_to_global_canon(MemoryScope.INSTANCE_MEMORY, False, True))

    def test_can_promote_with_both_abstraction_and_approval(self) -> None:
        self.assertTrue(can_promote_to_global_canon(MemoryScope.INSTANCE_MEMORY, True, True))

    def test_do_not_promote_always_false(self) -> None:
        self.assertFalse(can_promote_to_global_canon(MemoryScope.DO_NOT_PROMOTE, True, True))

    def test_requires_abstraction_for_instance_memory(self) -> None:
        self.assertTrue(requires_abstraction_for_global(MemoryScope.INSTANCE_MEMORY))


class TestMemoryScopeAssignment(unittest.TestCase):
    def test_defaults_to_instance_memory(self) -> None:
        assignment = MemoryScopeAssignment(source_id="test-1")
        self.assertEqual(assignment.assigned_scope, MemoryScope.INSTANCE_MEMORY)

    def test_global_canon_not_allowed_by_default(self) -> None:
        assignment = MemoryScopeAssignment(source_id="test-2")
        self.assertFalse(assignment.global_canon_allowed_by_default)

    def test_can_promote_to_global_works(self) -> None:
        # Cannot promote without abstraction and approval
        assignment = MemoryScopeAssignment(source_id="test-3")
        self.assertFalse(assignment.can_promote_to_global())

        # Can promote with both
        assignment_approved = MemoryScopeAssignment(
            source_id="test-4",
            abstraction_applied=True,
            founder_approved=True,
        )
        self.assertTrue(assignment_approved.can_promote_to_global())

    def test_can_promote_to_global_respects_do_not_promote(self) -> None:
        assignment = MemoryScopeAssignment(
            source_id="test-5",
            assigned_scope=MemoryScope.DO_NOT_PROMOTE,
            abstraction_applied=True,
            founder_approved=True,
        )
        self.assertFalse(assignment.can_promote_to_global())


if __name__ == "__main__":
    unittest.main()
