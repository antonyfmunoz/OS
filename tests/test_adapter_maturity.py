"""Tests for Layer 3 Phase 2 Slice B: adapter maturity evidence model.

Covers MaturityEvidence, MATURITY_REQUIREMENTS, _check_predicate,
compute_adapter_maturity, validate_maturity_claim, and the
AdapterHealthRecord maturity field addition.
"""

import os
import sys
import unittest

sys.path.insert(
    0, os.environ.get("UMH_ROOT") or os.path.join(os.path.dirname(__file__), "..") or "/opt/OS"
)

from adapters.adapter_engine.adapter_manifest import AdapterMaturityLevel
from adapters.adapter_engine.adapter_maturity import (
    MATURITY_REQUIREMENTS,
    MaturityEvidence,
    _check_predicate,
    compute_adapter_maturity,
    validate_maturity_claim,
)
from adapters.adapter_engine.adapter_lifecycle_manager_v1 import (
    AdapterHealthRecord,
    AdapterLifecycleManager,
    AdapterState,
)


class TestMaturityEvidence(unittest.TestCase):
    def test_defaults_all_zero_or_false(self):
        e = MaturityEvidence()
        self.assertFalse(e.auth_verified)
        self.assertEqual(e.capability_count, 0)
        self.assertEqual(e.execution_count, 0)
        self.assertEqual(e.doc_absorption_pct, 0.0)
        self.assertFalse(e.cross_adapter_tested)

    def test_all_fields_populated(self):
        e = MaturityEvidence(
            auth_verified=True,
            capability_count=5,
            execution_count=100,
            success_count=95,
            failure_modes_documented=3,
            doc_absorption_pct=92.0,
            edge_cases_mapped=10,
            edge_case_coverage_pct=91.0,
            mean_latency_ms=150.0,
            p99_latency_ms=800.0,
            has_recovery_playbook=True,
            optimization_applied=True,
            cross_adapter_tested=True,
        )
        self.assertTrue(e.auth_verified)
        self.assertEqual(e.execution_count, 100)
        self.assertEqual(e.doc_absorption_pct, 92.0)

    def test_partial_evidence(self):
        e = MaturityEvidence(auth_verified=True, capability_count=3)
        self.assertTrue(e.auth_verified)
        self.assertEqual(e.capability_count, 3)
        self.assertEqual(e.execution_count, 0)


class TestMaturityRequirements(unittest.TestCase):
    def test_all_eight_levels_present(self):
        for level in AdapterMaturityLevel:
            self.assertIn(level, MATURITY_REQUIREMENTS)

    def test_l0_has_no_requirements(self):
        self.assertEqual(MATURITY_REQUIREMENTS[AdapterMaturityLevel.L0_REGISTERED], [])

    def test_l7_has_most_requirements(self):
        counts = {lvl: len(reqs) for lvl, reqs in MATURITY_REQUIREMENTS.items()}
        l7_count = counts[AdapterMaturityLevel.L7_MASTERFUL]
        for lvl, count in counts.items():
            self.assertGreaterEqual(l7_count, count, f"L7 should have >= reqs than {lvl.name}")

    def test_cumulative_coverage_across_levels(self):
        """Each lower-level predicate is present or superseded at upper level.

        Threshold escalation (e.g. _gt_80pct → _gt_90pct) means the
        exact string won't match, but the same field base is covered
        with a stricter threshold.
        """

        def _field_base(pred: str) -> str:
            if "_gt_" in pred:
                return pred.rsplit("_gt_", 1)[0]
            return pred

        for i in range(len(AdapterMaturityLevel) - 1):
            lower = AdapterMaturityLevel(i)
            upper = AdapterMaturityLevel(i + 1)
            upper_bases = {_field_base(p) for p in MATURITY_REQUIREMENTS[upper]}
            for pred in MATURITY_REQUIREMENTS[lower]:
                base = _field_base(pred)
                self.assertIn(
                    base,
                    upper_bases,
                    f"{lower.name} predicate '{pred}' (base '{base}') not covered in {upper.name}",
                )


class TestCheckPredicate(unittest.TestCase):
    def test_bare_bool_true(self):
        e = MaturityEvidence(auth_verified=True)
        self.assertTrue(_check_predicate("auth_verified", e))

    def test_bare_bool_false(self):
        e = MaturityEvidence(auth_verified=False)
        self.assertFalse(_check_predicate("auth_verified", e))

    def test_gt_int_pass(self):
        e = MaturityEvidence(capability_count=5)
        self.assertTrue(_check_predicate("capability_count_gt_0", e))

    def test_gt_int_fail(self):
        e = MaturityEvidence(capability_count=0)
        self.assertFalse(_check_predicate("capability_count_gt_0", e))

    def test_gt_int_boundary(self):
        e = MaturityEvidence(execution_count=10)
        self.assertFalse(_check_predicate("execution_count_gt_10", e))
        e2 = MaturityEvidence(execution_count=11)
        self.assertTrue(_check_predicate("execution_count_gt_10", e2))

    def test_gt_pct_pass(self):
        e = MaturityEvidence(doc_absorption_pct=95.0)
        self.assertTrue(_check_predicate("doc_absorption_gt_90pct", e))

    def test_gt_pct_fail(self):
        e = MaturityEvidence(doc_absorption_pct=85.0)
        self.assertFalse(_check_predicate("doc_absorption_gt_90pct", e))

    def test_gt_pct_boundary(self):
        e = MaturityEvidence(doc_absorption_pct=90.0)
        self.assertFalse(_check_predicate("doc_absorption_gt_90pct", e))

    def test_unknown_field_returns_false(self):
        e = MaturityEvidence()
        self.assertFalse(_check_predicate("nonexistent_field", e))


class TestComputeAdapterMaturity(unittest.TestCase):
    def test_empty_evidence_yields_l0(self):
        self.assertEqual(
            compute_adapter_maturity(MaturityEvidence()),
            AdapterMaturityLevel.L0_REGISTERED,
        )

    def test_auth_only_yields_l1(self):
        e = MaturityEvidence(auth_verified=True)
        self.assertEqual(compute_adapter_maturity(e), AdapterMaturityLevel.L1_CONNECTED)

    def test_auth_plus_caps_yields_l2(self):
        e = MaturityEvidence(auth_verified=True, capability_count=3)
        self.assertEqual(compute_adapter_maturity(e), AdapterMaturityLevel.L2_CAPABILITIES_KNOWN)

    def test_auth_caps_execution_yields_l3(self):
        e = MaturityEvidence(auth_verified=True, capability_count=3, execution_count=15)
        self.assertEqual(compute_adapter_maturity(e), AdapterMaturityLevel.L3_TESTED)

    def test_full_evidence_yields_l7(self):
        e = MaturityEvidence(
            auth_verified=True,
            capability_count=5,
            execution_count=100,
            success_count=95,
            failure_modes_documented=3,
            doc_absorption_pct=95.0,
            edge_cases_mapped=10,
            edge_case_coverage_pct=95.0,
            has_recovery_playbook=True,
            optimization_applied=True,
            cross_adapter_tested=True,
        )
        self.assertEqual(compute_adapter_maturity(e), AdapterMaturityLevel.L7_MASTERFUL)

    def test_nonmonotonic_gap_caps_below(self):
        """Evidence for L5 predicates but missing L4's failure_modes_documented.

        Walk-down-from-top should return L3 (highest fully satisfied),
        not L5. This is the most important behavioral test.
        """
        e = MaturityEvidence(
            auth_verified=True,
            capability_count=5,
            execution_count=50,
            failure_modes_documented=0,
            edge_cases_mapped=0,
            doc_absorption_pct=85.0,
            optimization_applied=True,
        )
        self.assertEqual(compute_adapter_maturity(e), AdapterMaturityLevel.L3_TESTED)

    def test_l4_exactly(self):
        e = MaturityEvidence(
            auth_verified=True,
            capability_count=3,
            execution_count=20,
            failure_modes_documented=2,
            edge_cases_mapped=5,
        )
        self.assertEqual(compute_adapter_maturity(e), AdapterMaturityLevel.L4_EDGE_CASES_MAPPED)

    def test_l6_exactly(self):
        e = MaturityEvidence(
            auth_verified=True,
            capability_count=5,
            execution_count=50,
            failure_modes_documented=3,
            edge_cases_mapped=8,
            doc_absorption_pct=95.0,
            optimization_applied=True,
            has_recovery_playbook=True,
            edge_case_coverage_pct=85.0,
        )
        self.assertEqual(compute_adapter_maturity(e), AdapterMaturityLevel.L6_EXPERT)


class TestValidateMaturityClaim(unittest.TestCase):
    def test_claim_l0_with_empty_is_valid(self):
        valid, actual, missing = validate_maturity_claim(
            AdapterMaturityLevel.L0_REGISTERED, MaturityEvidence()
        )
        self.assertTrue(valid)
        self.assertEqual(actual, AdapterMaturityLevel.L0_REGISTERED)
        self.assertEqual(missing, [])

    def test_claim_l3_with_l1_evidence_invalid(self):
        e = MaturityEvidence(auth_verified=True)
        valid, actual, missing = validate_maturity_claim(AdapterMaturityLevel.L3_TESTED, e)
        self.assertFalse(valid)
        self.assertEqual(actual, AdapterMaturityLevel.L1_CONNECTED)
        self.assertIn("capability_count_gt_0", missing)
        self.assertIn("execution_count_gt_10", missing)

    def test_overclaim_is_valid(self):
        """Claiming L1 when evidence supports L3 is valid."""
        e = MaturityEvidence(auth_verified=True, capability_count=3, execution_count=20)
        valid, actual, missing = validate_maturity_claim(AdapterMaturityLevel.L1_CONNECTED, e)
        self.assertTrue(valid)
        self.assertEqual(actual, AdapterMaturityLevel.L3_TESTED)
        self.assertEqual(missing, [])

    def test_missing_predicates_content_correct(self):
        e = MaturityEvidence(auth_verified=True, capability_count=3)
        valid, actual, missing = validate_maturity_claim(AdapterMaturityLevel.L3_TESTED, e)
        self.assertFalse(valid)
        self.assertEqual(missing, ["execution_count_gt_10"])


class TestHealthRecordMaturityField(unittest.TestCase):
    def test_default_is_l0(self):
        r = AdapterHealthRecord(adapter_id="test-1", adapter_type="api")
        self.assertEqual(r.maturity, AdapterMaturityLevel.L0_REGISTERED)

    def test_explicit_maturity_in_constructor(self):
        r = AdapterHealthRecord(
            adapter_id="test-2",
            adapter_type="api",
            maturity=AdapterMaturityLevel.L3_TESTED,
        )
        self.assertEqual(r.maturity, AdapterMaturityLevel.L3_TESTED)

    def test_to_dict_includes_maturity(self):
        r = AdapterHealthRecord(
            adapter_id="test-3",
            adapter_type="api",
            maturity=AdapterMaturityLevel.L2_CAPABILITIES_KNOWN,
        )
        d = r.to_dict()
        self.assertEqual(d["maturity"], 2)
        self.assertEqual(d["maturity_label"], "L2_CAPABILITIES_KNOWN")

    def test_lifecycle_register_returns_l0(self):
        mgr = AdapterLifecycleManager()
        mgr.register_adapter(
            adapter_id="a1",
            adapter_type="api",
            capabilities=["read"],
            environment_type="test",
        )
        record = mgr.get_adapter("a1")
        self.assertIsNotNone(record)
        self.assertEqual(record.maturity, AdapterMaturityLevel.L0_REGISTERED)


if __name__ == "__main__":
    unittest.main()
