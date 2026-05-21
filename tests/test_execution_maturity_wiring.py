"""Tests for Layer 3 Phase 2 Slice C: execution tracking → maturity evidence wiring.

Covers _build_evidence reconstruction, maturity updates on success/failure,
full lifecycle progression, and the L2 baseline from option C
(auth_verified=True + capability_count wired at evidence build time).
"""

import os
import sys
import unittest

sys.path.insert(
    0, os.environ.get("UMH_ROOT") or os.path.join(os.path.dirname(__file__), "..") or "/opt/OS"
)

from adapters.adapter_engine.adapter_manifest import AdapterMaturityLevel
from adapters.adapter_engine.adapter_maturity import MaturityEvidence
from adapters.adapter_engine.adapter_lifecycle_manager_v1 import (
    AdapterHealthRecord,
    AdapterLifecycleManager,
    AdapterState,
    _build_evidence,
)


class TestBuildEvidence(unittest.TestCase):
    def test_default_record_evidence(self):
        r = AdapterHealthRecord(adapter_id="a1", adapter_type="api")
        e = _build_evidence(r)
        self.assertTrue(e.auth_verified)
        self.assertEqual(e.capability_count, 0)
        self.assertEqual(e.execution_count, 0)
        self.assertEqual(e.success_count, 0)

    def test_record_with_executions(self):
        r = AdapterHealthRecord(
            adapter_id="a1",
            adapter_type="api",
            total_executions=20,
            total_failures=3,
        )
        e = _build_evidence(r)
        self.assertEqual(e.execution_count, 20)
        self.assertEqual(e.success_count, 17)

    def test_record_with_capabilities(self):
        r = AdapterHealthRecord(
            adapter_id="a1",
            adapter_type="api",
            capabilities=["read", "write", "delete"],
        )
        e = _build_evidence(r)
        self.assertEqual(e.capability_count, 3)

    def test_non_execution_dimensions_default(self):
        """Dimensions not wired by lifecycle tracking stay at defaults."""
        r = AdapterHealthRecord(
            adapter_id="a1",
            adapter_type="api",
            total_executions=100,
            capabilities=["read"],
        )
        e = _build_evidence(r)
        self.assertEqual(e.doc_absorption_pct, 0.0)
        self.assertEqual(e.edge_cases_mapped, 0)
        self.assertFalse(e.has_recovery_playbook)
        self.assertFalse(e.optimization_applied)
        self.assertFalse(e.cross_adapter_tested)


class TestExecutionSuccessMaturity(unittest.TestCase):
    def test_fresh_adapter_with_caps_is_l2(self):
        """Registration + capabilities → L2 (auth verified + capabilities known)."""
        mgr = AdapterLifecycleManager()
        mgr.register_adapter("a1", "api", capabilities=["read"])
        mgr.record_execution_success("a1")
        record = mgr.get_adapter("a1")
        self.assertEqual(record.maturity, AdapterMaturityLevel.L2_CAPABILITIES_KNOWN)

    def test_eleven_successes_yields_l3(self):
        mgr = AdapterLifecycleManager()
        mgr.register_adapter("a1", "api", capabilities=["read"])
        for _ in range(11):
            mgr.record_execution_success("a1")
        record = mgr.get_adapter("a1")
        self.assertEqual(record.maturity, AdapterMaturityLevel.L3_TESTED)

    def test_success_resets_consecutive_failures_maturity_reflects_total(self):
        mgr = AdapterLifecycleManager()
        mgr.register_adapter("a1", "api", capabilities=["read"])
        for _ in range(5):
            mgr.record_execution_failure("a1")
        mgr.record_execution_success("a1")
        record = mgr.get_adapter("a1")
        self.assertEqual(record.consecutive_failures, 0)
        self.assertEqual(record.total_executions, 6)

    def test_maturity_never_decreases_on_success(self):
        mgr = AdapterLifecycleManager()
        mgr.register_adapter("a1", "api", capabilities=["read"])
        for _ in range(12):
            mgr.record_execution_success("a1")
        record = mgr.get_adapter("a1")
        self.assertEqual(record.maturity, AdapterMaturityLevel.L3_TESTED)
        mgr.record_execution_success("a1")
        self.assertEqual(record.maturity, AdapterMaturityLevel.L3_TESTED)


class TestExecutionFailureMaturity(unittest.TestCase):
    def test_failure_increments_execution_count(self):
        mgr = AdapterLifecycleManager()
        mgr.register_adapter("a1", "api", capabilities=["read"])
        for _ in range(12):
            mgr.record_execution_failure("a1")
        record = mgr.get_adapter("a1")
        self.assertEqual(record.total_executions, 12)
        self.assertEqual(record.maturity, AdapterMaturityLevel.L3_TESTED)

    def test_three_failures_degraded_but_maturity_independent(self):
        """State goes DEGRADED after 3 consecutive failures; maturity is orthogonal."""
        mgr = AdapterLifecycleManager()
        mgr.register_adapter("a1", "api", capabilities=["read"])
        for _ in range(3):
            mgr.record_execution_failure("a1")
        record = mgr.get_adapter("a1")
        self.assertEqual(record.state, AdapterState.DEGRADED)
        self.assertEqual(record.maturity, AdapterMaturityLevel.L2_CAPABILITIES_KNOWN)

    def test_failure_success_mix_correct_maturity(self):
        mgr = AdapterLifecycleManager()
        mgr.register_adapter("a1", "api", capabilities=["read", "write"])
        for _ in range(6):
            mgr.record_execution_success("a1")
        for _ in range(6):
            mgr.record_execution_failure("a1")
        record = mgr.get_adapter("a1")
        self.assertEqual(record.total_executions, 12)
        self.assertEqual(record.maturity, AdapterMaturityLevel.L3_TESTED)


class TestMaturityProgression(unittest.TestCase):
    def test_full_lifecycle_to_l3(self):
        mgr = AdapterLifecycleManager()
        record = mgr.register_adapter("a1", "api", capabilities=["read"])
        self.assertEqual(record.maturity, AdapterMaturityLevel.L0_REGISTERED)

        mgr.record_execution_success("a1")
        self.assertEqual(record.maturity, AdapterMaturityLevel.L2_CAPABILITIES_KNOWN)

        for _ in range(10):
            mgr.record_execution_success("a1")
        self.assertEqual(record.maturity, AdapterMaturityLevel.L3_TESTED)

    def test_interleaved_success_failure_progression(self):
        mgr = AdapterLifecycleManager()
        record = mgr.register_adapter("a1", "api", capabilities=["read"])

        for i in range(12):
            if i % 3 == 0:
                mgr.record_execution_failure("a1")
            else:
                mgr.record_execution_success("a1")

        self.assertEqual(record.total_executions, 12)
        self.assertEqual(record.maturity, AdapterMaturityLevel.L3_TESTED)

    def test_l4_unreachable_without_failure_modes_documented(self):
        """L4 requires failure_modes_documented_gt_0 — not wired in this slice."""
        mgr = AdapterLifecycleManager()
        mgr.register_adapter("a1", "api", capabilities=["read"])
        for _ in range(100):
            mgr.record_execution_success("a1")
        record = mgr.get_adapter("a1")
        self.assertEqual(record.maturity, AdapterMaturityLevel.L3_TESTED)


class TestMaturityBaseline(unittest.TestCase):
    def test_registration_starts_at_l0(self):
        """register_adapter() does NOT recompute — record starts at L0."""
        mgr = AdapterLifecycleManager()
        record = mgr.register_adapter("a1", "api", capabilities=["read"])
        self.assertEqual(record.maturity, AdapterMaturityLevel.L0_REGISTERED)

    def test_no_capabilities_caps_at_l1(self):
        """Without capabilities, auth_verified alone → L1."""
        mgr = AdapterLifecycleManager()
        mgr.register_adapter("a1", "api", capabilities=[])
        mgr.record_execution_success("a1")
        record = mgr.get_adapter("a1")
        self.assertEqual(record.maturity, AdapterMaturityLevel.L1_CONNECTED)

    def test_nonexistent_adapter_no_crash(self):
        mgr = AdapterLifecycleManager()
        mgr.record_execution_success("ghost")
        mgr.record_execution_failure("ghost")


if __name__ == "__main__":
    unittest.main()
