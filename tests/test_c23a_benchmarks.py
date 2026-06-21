"""Tests for C23A benchmarks 2-7 + projection readiness.

All tests are deterministic — no LLM calls, no network, no mocks.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


# ===================================================================
# Benchmark 2 — Production Quality
# ===================================================================

class TestProductionQuality(unittest.TestCase):
    """Test defect seeding, detection, and P/R/F1 scoring."""

    def test_catalog_has_10_defects(self):
        from substrate.organism.benchmarks.production_quality import DEFECT_CATALOG
        self.assertEqual(len(DEFECT_CATALOG), 10)

    def test_all_defect_ids_unique(self):
        from substrate.organism.benchmarks.production_quality import DEFECT_CATALOG
        ids = [d.defect_id for d in DEFECT_CATALOG]
        self.assertEqual(len(ids), len(set(ids)))

    def test_seeder_creates_files(self):
        from substrate.organism.benchmarks.production_quality import DefectSeeder
        with tempfile.TemporaryDirectory() as tmp:
            seeder = DefectSeeder()
            seeded = seeder.seed_defects(tmp)
            self.assertEqual(len(seeded), 10)
            for defect in seeded:
                path = Path(tmp) / defect.file_relative
                self.assertTrue(path.exists(), f"{defect.file_relative} not created")

    def test_detector_finds_all_patterns(self):
        from substrate.organism.benchmarks.production_quality import (
            DefectDetector, DefectSeeder
        )
        with tempfile.TemporaryDirectory() as tmp:
            seeder = DefectSeeder()
            seeder.seed_defects(tmp)
            detector = DefectDetector()
            findings = detector.detect_in_directory(tmp)
            self.assertGreaterEqual(len(findings), 10)

    def test_full_benchmark_perfect_score(self):
        from substrate.organism.benchmarks.production_quality import ProductionQualityBenchmark
        bench = ProductionQualityBenchmark()
        result = bench.run()
        self.assertEqual(result.precision, 1.0)
        self.assertEqual(result.recall, 1.0)
        self.assertEqual(result.f1, 1.0)
        self.assertEqual(result.defects_seeded, 10)
        self.assertEqual(result.defects_detected, 10)
        self.assertEqual(result.false_positives, 0)
        self.assertEqual(result.false_negatives, 0)

    def test_clean_files_no_false_positives(self):
        from substrate.organism.benchmarks.production_quality import ProductionQualityBenchmark
        bench = ProductionQualityBenchmark(include_clean_files=10)
        result = bench.run()
        self.assertEqual(result.false_positives, 0)

    def test_result_to_dict(self):
        from substrate.organism.benchmarks.production_quality import ProductionQualityBenchmark
        bench = ProductionQualityBenchmark()
        result = bench.run()
        d = result.to_dict()
        self.assertIn("precision", d)
        self.assertIn("recall", d)
        self.assertIn("f1", d)
        self.assertIn("details", d)

    def test_detector_on_nonexistent_file(self):
        from substrate.organism.benchmarks.production_quality import DefectDetector
        detector = DefectDetector()
        findings = detector.detect_in_file("/nonexistent/path.py")
        self.assertEqual(findings, [])

    def test_each_defect_category_covered(self):
        from substrate.organism.benchmarks.production_quality import DEFECT_CATALOG
        categories = {d.category for d in DEFECT_CATALOG}
        expected = {"architecture", "instance_context", "type_coherence",
                    "projection_boundary", "quality", "security", "cpu_gate"}
        self.assertEqual(categories, expected)


# ===================================================================
# Benchmark 3 — Production Velocity
# ===================================================================

class TestProductionVelocity(unittest.TestCase):
    """Test velocity measurement and acceleration detection."""

    def _make_records(self):
        from substrate.organism.benchmarks.production_velocity import ProductionRecord
        return [
            ProductionRecord("p1", 1000, 1100, True, "first"),
            ProductionRecord("p2", 1200, 1280, True, "second"),
            ProductionRecord("p3", 1300, 1360, True, "third"),
            ProductionRecord("p4", 1400, 1430, True, "fourth"),
        ]

    def test_duration_calculation(self):
        from substrate.organism.benchmarks.production_velocity import ProductionRecord
        r = ProductionRecord("p1", 1000, 1100)
        self.assertEqual(r.duration_seconds, 100.0)

    def test_duration_never_negative(self):
        from substrate.organism.benchmarks.production_velocity import ProductionRecord
        r = ProductionRecord("p1", 1100, 1000)
        self.assertEqual(r.duration_seconds, 0.0)

    def test_accelerating_trend(self):
        from substrate.organism.benchmarks.production_velocity import ProductionVelocityBenchmark
        bench = ProductionVelocityBenchmark()
        bench.add_records(self._make_records())
        result = bench.run()
        self.assertEqual(result.trend_direction, "accelerating")
        self.assertGreater(result.acceleration_ratio, 1.0)

    def test_stable_trend(self):
        from substrate.organism.benchmarks.production_velocity import (
            ProductionVelocityBenchmark, ProductionRecord
        )
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord("p1", 1000, 1100),
            ProductionRecord("p2", 1200, 1300),
            ProductionRecord("p3", 1300, 1400),
            ProductionRecord("p4", 1400, 1500),
        ])
        result = bench.run()
        self.assertEqual(result.trend_direction, "stable")

    def test_decelerating_trend(self):
        from substrate.organism.benchmarks.production_velocity import (
            ProductionVelocityBenchmark, ProductionRecord
        )
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord("p1", 1000, 1030),
            ProductionRecord("p2", 1200, 1260),
            ProductionRecord("p3", 1300, 1400),
            ProductionRecord("p4", 1400, 1550),
        ])
        result = bench.run()
        self.assertEqual(result.trend_direction, "decelerating")

    def test_empty_records(self):
        from substrate.organism.benchmarks.production_velocity import ProductionVelocityBenchmark
        bench = ProductionVelocityBenchmark()
        result = bench.run()
        self.assertEqual(result.productions, 0)

    def test_track_filter(self):
        from substrate.organism.benchmarks.production_velocity import (
            ProductionVelocityBenchmark, ProductionRecord
        )
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord("p1", 1000, 1100, True),
            ProductionRecord("p2", 1200, 1300, False),
        ])
        result_a = bench.run(track_filter=True)
        result_b = bench.run(track_filter=False)
        self.assertEqual(result_a.productions, 1)
        self.assertEqual(result_b.productions, 1)

    def test_compare_tracks(self):
        from substrate.organism.benchmarks.production_velocity import (
            ProductionVelocityBenchmark, ProductionRecord
        )
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord("p1", 1000, 1050, True),
            ProductionRecord("p2", 1200, 1300, False),
        ])
        comparison = bench.compare_tracks()
        self.assertIn("track_a_reuse_on", comparison)
        self.assertIn("track_b_reuse_off", comparison)
        self.assertIn("speedup_ratio", comparison)
        self.assertTrue(comparison["reuse_faster"])

    def test_result_to_dict(self):
        from substrate.organism.benchmarks.production_velocity import ProductionVelocityBenchmark
        bench = ProductionVelocityBenchmark()
        bench.add_records(self._make_records())
        result = bench.run()
        d = result.to_dict()
        self.assertIn("acceleration_ratio", d)
        self.assertIn("trend_direction", d)
        self.assertIn("durations", d)


# ===================================================================
# Benchmark 4 — Capability Reuse
# ===================================================================

class TestCapabilityReuse(unittest.TestCase):
    """Test dual-track comparison and ROI calculation."""

    def test_proven_verdict(self):
        from substrate.organism.benchmarks.capability_reuse import (
            CapabilityReuseBenchmark, TrackRecord, ReusableCapability
        )
        bench = CapabilityReuseBenchmark()
        bench.register_capability(ReusableCapability("cap1", "Cap 1", "general"))
        bench.add_track_a(TrackRecord("p1", "A", 80, 1, 0, ["cap1"]))
        bench.add_track_a(TrackRecord("p2", "A", 70, 1, 0, ["cap1"]))
        bench.add_track_b(TrackRecord("p3", "B", 150, 3, 3))
        bench.add_track_b(TrackRecord("p4", "B", 140, 3, 2))
        result = bench.run()
        self.assertEqual(result.verdict, "PROVEN")

    def test_harmful_verdict(self):
        from substrate.organism.benchmarks.capability_reuse import (
            CapabilityReuseBenchmark, TrackRecord
        )
        bench = CapabilityReuseBenchmark()
        bench.add_track_a(TrackRecord("p1", "A", 200, 5, 5))
        bench.add_track_a(TrackRecord("p2", "A", 180, 4, 4))
        bench.add_track_b(TrackRecord("p3", "B", 100, 1, 0))
        bench.add_track_b(TrackRecord("p4", "B", 90, 1, 0))
        result = bench.run()
        self.assertEqual(result.verdict, "HARMFUL")

    def test_insufficient_data(self):
        from substrate.organism.benchmarks.capability_reuse import (
            CapabilityReuseBenchmark, TrackRecord
        )
        bench = CapabilityReuseBenchmark()
        bench.add_track_a(TrackRecord("p1", "A", 100, 2, 1))
        result = bench.run()
        self.assertEqual(result.verdict, "INSUFFICIENT_DATA")

    def test_roi_positive(self):
        from substrate.organism.benchmarks.capability_reuse import (
            CapabilityReuseBenchmark, TrackRecord, ReusableCapability
        )
        bench = CapabilityReuseBenchmark()
        bench.register_capability(ReusableCapability("cap1", "Cap 1", "general"))
        bench.add_track_a(TrackRecord("p1", "A", 60, 1, 0, ["cap1"]))
        bench.add_track_b(TrackRecord("p3", "B", 120, 3, 3))
        result = bench.run()
        self.assertGreater(result.aggregate_roi, 0)
        self.assertGreater(result.time_saved_pct, 0)

    def test_track_counts(self):
        from substrate.organism.benchmarks.capability_reuse import (
            CapabilityReuseBenchmark, TrackRecord
        )
        bench = CapabilityReuseBenchmark()
        bench.add_track_a(TrackRecord("p1", "A", 100))
        bench.add_track_a(TrackRecord("p2", "A", 90))
        bench.add_track_b(TrackRecord("p3", "B", 150))
        self.assertEqual(bench.track_a_count, 2)
        self.assertEqual(bench.track_b_count, 1)

    def test_result_to_dict(self):
        from substrate.organism.benchmarks.capability_reuse import (
            CapabilityReuseBenchmark, TrackRecord
        )
        bench = CapabilityReuseBenchmark()
        bench.add_track_a(TrackRecord("p1", "A", 100, 2, 1))
        bench.add_track_b(TrackRecord("p2", "B", 150, 3, 3))
        result = bench.run()
        d = result.to_dict()
        self.assertIn("verdict", d)
        self.assertIn("aggregate_roi", d)
        self.assertIn("capability_roi", d)

    def test_capability_success_rate(self):
        from substrate.organism.benchmarks.capability_reuse import ReusableCapability
        cap = ReusableCapability("c1", "C1", "test", 5, 8, 2)
        self.assertAlmostEqual(cap.success_rate, 0.8)

    def test_capability_success_rate_zero(self):
        from substrate.organism.benchmarks.capability_reuse import ReusableCapability
        cap = ReusableCapability("c1", "C1", "test", 0, 0, 0)
        self.assertEqual(cap.success_rate, 0.0)

    def test_add_records_routes_by_track(self):
        from substrate.organism.benchmarks.capability_reuse import (
            CapabilityReuseBenchmark, TrackRecord
        )
        bench = CapabilityReuseBenchmark()
        bench.add_records([
            TrackRecord("p1", "A", 100),
            TrackRecord("p2", "B", 150),
            TrackRecord("p3", "A", 90),
        ])
        self.assertEqual(bench.track_a_count, 2)
        self.assertEqual(bench.track_b_count, 1)


# ===================================================================
# Benchmark 5 — Operator Compression
# ===================================================================

class TestOperatorCompression(unittest.TestCase):
    """Test operator message classification and compression metrics."""

    def test_classify_correction(self):
        from substrate.organism.benchmarks.operator_compression import classify_operator_message
        self.assertEqual(classify_operator_message("no not that"), "correction")
        self.assertEqual(classify_operator_message("wrong approach"), "correction")
        self.assertEqual(classify_operator_message("fix this bug"), "correction")

    def test_classify_approval(self):
        from substrate.organism.benchmarks.operator_compression import classify_operator_message
        self.assertEqual(classify_operator_message("yes"), "approval")
        self.assertEqual(classify_operator_message("approved"), "approval")
        self.assertEqual(classify_operator_message("looks good"), "approval")

    def test_classify_information(self):
        from substrate.organism.benchmarks.operator_compression import classify_operator_message
        result = classify_operator_message("build a new feature for the dashboard")
        self.assertEqual(result, "information")

    def test_benchmark_with_productions(self):
        from substrate.organism.benchmarks.operator_compression import (
            OperatorCompressionBenchmark, ProductionInteractions
        )
        productions = [
            ProductionInteractions(
                production_id="p1",
                operator_messages=4,
                operator_corrections=2,
                operator_approvals=1,
                operator_interventions=0,
                autonomous_actions=10,
            ),
            ProductionInteractions(
                production_id="p2",
                operator_messages=2,
                operator_corrections=0,
                operator_approvals=1,
                operator_interventions=0,
                autonomous_actions=15,
            ),
        ]
        bench = OperatorCompressionBenchmark()
        result = bench.run(productions)
        self.assertEqual(result.productions, 2)

    def test_empty_productions(self):
        from substrate.organism.benchmarks.operator_compression import OperatorCompressionBenchmark
        bench = OperatorCompressionBenchmark()
        result = bench.run([])
        self.assertEqual(result.productions, 0)


# ===================================================================
# Benchmark 6 — Production Outcome Quality
# ===================================================================

class TestProductionOutcomeQuality(unittest.TestCase):
    """Test outcome quality measurement and quality verdict."""

    def test_positive_quality(self):
        from substrate.organism.benchmarks.production_outcome_quality import (
            ProductionOutcomeQualityBenchmark, ProductionOutcome, AcceptanceCriterion
        )
        outcomes = [
            ProductionOutcome(
                production_id="p1", track="reuse_on", defect_count=0,
                test_pass_count=10, test_total_count=10,
                acceptance_criteria=[AcceptanceCriterion("c1", "test", True)],
                lines_of_code=100,
            ),
            ProductionOutcome(
                production_id="p2", track="reuse_on", defect_count=0,
                test_pass_count=10, test_total_count=10,
                acceptance_criteria=[AcceptanceCriterion("c2", "test", True)],
                lines_of_code=100,
            ),
            ProductionOutcome(
                production_id="p3", track="reuse_off", defect_count=3,
                test_pass_count=8, test_total_count=10,
                acceptance_criteria=[AcceptanceCriterion("c3", "test", False)],
                lines_of_code=100,
            ),
            ProductionOutcome(
                production_id="p4", track="reuse_off", defect_count=2,
                test_pass_count=9, test_total_count=10,
                acceptance_criteria=[AcceptanceCriterion("c4", "test", True)],
                lines_of_code=100,
            ),
        ]
        bench = ProductionOutcomeQualityBenchmark()
        result = bench.run(outcomes)
        self.assertIn(result.comparison.quality_verdict,
                       ("POSITIVE_COMPOUNDING", "NEUTRAL", "POSITIVE"))

    def test_negative_quality_fast_but_wrong(self):
        from substrate.organism.benchmarks.production_outcome_quality import (
            ProductionOutcomeQualityBenchmark, ProductionOutcome, AcceptanceCriterion
        )
        outcomes = [
            ProductionOutcome(
                production_id="p1", track="reuse_on", defect_count=5,
                test_pass_count=5, test_total_count=10,
                acceptance_criteria=[AcceptanceCriterion("c1", "test", False)],
                lines_of_code=100,
            ),
            ProductionOutcome(
                production_id="p2", track="reuse_off", defect_count=0,
                test_pass_count=10, test_total_count=10,
                acceptance_criteria=[AcceptanceCriterion("c2", "test", True)],
                lines_of_code=100,
            ),
        ]
        bench = ProductionOutcomeQualityBenchmark()
        result = bench.run(outcomes)
        self.assertIn(result.comparison.quality_verdict,
                       ("NEGATIVE_COMPOUNDING", "NO_COMPOUNDING", "NEGATIVE"))

    def test_track_metrics_computation(self):
        from substrate.organism.benchmarks.production_outcome_quality import (
            ProductionOutcomeQualityBenchmark, ProductionOutcome, AcceptanceCriterion
        )
        outcome = ProductionOutcome(
            production_id="p1", track="reuse_on", defect_count=2,
            test_pass_count=9, test_total_count=10,
            acceptance_criteria=[
                AcceptanceCriterion("c1", "one", True),
                AcceptanceCriterion("c2", "two", False),
            ],
            lines_of_code=100,
        )
        metrics = ProductionOutcomeQualityBenchmark.compute_track_metrics([outcome], "reuse_on")
        self.assertEqual(metrics.track, "reuse_on")
        self.assertEqual(metrics.productions, 1)
        self.assertEqual(metrics.total_defects, 2)
        self.assertAlmostEqual(metrics.avg_test_pass_rate, 0.9)


# ===================================================================
# Benchmark 7 — Compounding Proof (Integration)
# ===================================================================

class TestCompoundingProof(unittest.TestCase):
    """Test the integration benchmark that orchestrates all metrics."""

    def test_curve_computation(self):
        from substrate.organism.benchmarks.compounding_proof import CompoundingCurve
        curve = CompoundingCurve(
            metric_name="production_duration",
            reuse_on_values=[100.0, 80.0, 60.0],
            reuse_off_values=[100.0, 95.0, 90.0],
            lower_is_better=True,
        )
        curve.compute()
        self.assertTrue(curve.on_improved)
        self.assertTrue(curve.on_better_than_off)

    def _bm(self, bid, num, track, dur, reuse, roi, touches, reviews, defects, fpr, nnp=1.0):
        from substrate.organism.benchmarks.compounding_proof import BuildMetrics
        return BuildMetrics(
            build_id=bid, build_number=num, track=track,
            production_duration=dur, reuse_pct=reuse, capability_roi=roi,
            operator_touches=touches, review_cycles=reviews, defects_found=defects,
            first_pass_rate=fpr, net_new_pct=nnp,
        )

    def test_proven_verdict(self):
        from substrate.organism.benchmarks.compounding_proof import CompoundingProofBenchmark
        reuse_on = [
            self._bm("b1", 1, "reuse_on", 100, 10, 0.5, 5, 3, 0, 0.7, 0.9),
            self._bm("b2", 2, "reuse_on", 70, 40, 1.5, 3, 2, 0, 0.85, 0.5),
            self._bm("b3", 3, "reuse_on", 50, 60, 2.5, 1, 1, 0, 0.95, 0.3),
        ]
        reuse_off = [
            self._bm("b4", 1, "reuse_off", 100, 0, 0.0, 5, 3, 0, 0.7, 1.0),
            self._bm("b5", 2, "reuse_off", 100, 0, 0.0, 5, 3, 0, 0.7, 1.0),
            self._bm("b6", 3, "reuse_off", 100, 0, 0.0, 5, 3, 0, 0.7, 1.0),
        ]
        bench = CompoundingProofBenchmark()
        result = bench.evaluate(reuse_on, reuse_off)
        self.assertEqual(result.verdict, "PROVEN")

    def test_not_proven_when_no_improvement(self):
        from substrate.organism.benchmarks.compounding_proof import CompoundingProofBenchmark
        flat = [
            self._bm("b1", 1, "reuse_on", 100, 10, 0.5, 5, 3, 0, 0.7, 1.0),
            self._bm("b2", 2, "reuse_on", 100, 10, 0.5, 5, 3, 0, 0.7, 1.0),
            self._bm("b3", 3, "reuse_on", 100, 10, 0.5, 5, 3, 0, 0.7, 1.0),
        ]
        baseline = [
            self._bm("b4", 1, "reuse_off", 100, 0, 0.0, 5, 3, 0, 0.7, 1.0),
            self._bm("b5", 2, "reuse_off", 100, 0, 0.0, 5, 3, 0, 0.7, 1.0),
            self._bm("b6", 3, "reuse_off", 100, 0, 0.0, 5, 3, 0, 0.7, 1.0),
        ]
        bench = CompoundingProofBenchmark()
        result = bench.evaluate(flat, baseline)
        self.assertEqual(result.verdict, "NOT_PROVEN")

    def test_result_to_dict(self):
        from substrate.organism.benchmarks.compounding_proof import CompoundingProofBenchmark
        on = [
            self._bm("b1", 1, "reuse_on", 100, 10, 0.5, 5, 3, 0, 0.7, 1.0),
            self._bm("b2", 2, "reuse_on", 80, 30, 1.0, 3, 2, 0, 0.8, 0.7),
        ]
        off = [
            self._bm("b3", 1, "reuse_off", 100, 0, 0.0, 5, 3, 0, 0.7, 1.0),
            self._bm("b4", 2, "reuse_off", 100, 0, 0.0, 5, 3, 0, 0.7, 1.0),
        ]
        bench = CompoundingProofBenchmark()
        result = bench.evaluate(on, off)
        d = result.to_dict()
        self.assertIn("verdict", d)
        self.assertIn("curves", d)


# ===================================================================
# Projection Readiness
# ===================================================================

class TestProjectionReadiness(unittest.TestCase):
    """Test projection capability coverage measurement."""

    def test_full_coverage(self):
        from substrate.organism.benchmarks.projection_readiness import (
            ProjectionReadinessBenchmark, PROJECTION_REQUIREMENTS
        )
        all_caps = []
        for caps in PROJECTION_REQUIREMENTS.values():
            all_caps.extend(caps)
        bench = ProjectionReadinessBenchmark(existing_capabilities=all_caps)
        result = bench.evaluate()
        for cov in result.projections:
            self.assertEqual(cov["existing_coverage_pct"], 1.0)

    def test_zero_coverage(self):
        from substrate.organism.benchmarks.projection_readiness import ProjectionReadinessBenchmark
        bench = ProjectionReadinessBenchmark(existing_capabilities=[])
        result = bench.evaluate()
        for cov in result.projections:
            self.assertEqual(cov["existing_coverage_pct"], 0.0)
            self.assertGreater(len(cov["unmatched"]), 0)

    def test_partial_coverage(self):
        from substrate.organism.benchmarks.projection_readiness import (
            ProjectionReadinessBenchmark, PROJECTION_REQUIREMENTS
        )
        eos_first = PROJECTION_REQUIREMENTS["EOS"][:3]
        bench = ProjectionReadinessBenchmark(existing_capabilities=eos_first)
        result = bench.evaluate()
        eos_cov = next(c for c in result.projections if c["projection_name"] == "EOS")
        self.assertGreater(eos_cov["existing_coverage_pct"], 0)
        self.assertLess(eos_cov["existing_coverage_pct"], 1.0)

    def test_result_to_dict(self):
        from substrate.organism.benchmarks.projection_readiness import ProjectionReadinessBenchmark
        bench = ProjectionReadinessBenchmark(existing_capabilities=["outreach_automation"])
        result = bench.evaluate()
        d = result.to_dict()
        self.assertIn("projections", d)
        self.assertIn("overall_readiness", d)


# ===================================================================
# API Routes
# ===================================================================

class TestValidationRoutes(unittest.TestCase):
    """Test that validation routes register and import cleanly."""

    def test_routes_import(self):
        try:
            from transports.api.cockpit_validation_routes import register_validation_routes
            self.assertTrue(callable(register_validation_routes))
        except ImportError:
            self.skipTest("Routes not yet built (Phase 10)")


if __name__ == "__main__":
    unittest.main()
