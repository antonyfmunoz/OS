"""Tests for Benchmark 4 — Capability Reuse (Dual-Track)."""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/remaining-phases")

from substrate.organism.benchmarks.capability_reuse import (
    CapabilityReuseBenchmark,
    CapabilityReuseResult,
    CapabilityROI,
    ReusableCapability,
    TrackRecord,
)


class TestReusableCapability:
    def test_success_rate_no_uses(self):
        cap = ReusableCapability()
        assert cap.success_rate == 0.0

    def test_success_rate_all_success(self):
        cap = ReusableCapability(success_count=10, failure_count=0)
        assert cap.success_rate == 1.0

    def test_success_rate_mixed(self):
        cap = ReusableCapability(success_count=7, failure_count=3)
        assert cap.success_rate == 0.7


class TestTrackRecord:
    def test_defaults(self):
        r = TrackRecord()
        assert r.track == "A"
        assert r.duration_seconds == 0.0
        assert r.capabilities_reused == []


class TestCapabilityReuseBenchmark:
    def test_empty_tracks(self):
        bench = CapabilityReuseBenchmark()
        result = bench.run()
        assert result.verdict == "INSUFFICIENT_DATA"

    def test_only_track_a(self):
        bench = CapabilityReuseBenchmark()
        bench.add_track_a(TrackRecord(production_id="a1", duration_seconds=100))
        result = bench.run()
        assert result.verdict == "INSUFFICIENT_DATA"
        assert result.track_a_count == 1
        assert result.track_b_count == 0

    def test_only_track_b(self):
        bench = CapabilityReuseBenchmark()
        bench.add_track_b(TrackRecord(production_id="b1", duration_seconds=200))
        result = bench.run()
        assert result.verdict == "INSUFFICIENT_DATA"

    def test_dual_track_proven(self):
        bench = CapabilityReuseBenchmark()
        bench.register_capability(ReusableCapability(
            capability_id="cap1", name="Test Cap", success_count=5,
        ))
        bench.add_track_a(TrackRecord(
            production_id="a1", duration_seconds=50, review_rounds=1,
            defect_count=0, capabilities_reused=["cap1"],
        ))
        bench.add_track_b(TrackRecord(
            production_id="b1", duration_seconds=200, review_rounds=4,
            defect_count=3,
        ))
        result = bench.run()
        assert result.time_saved_pct > 10.0
        assert result.review_reduction_pct > 10.0
        assert result.verdict == "PROVEN"

    def test_dual_track_not_proven(self):
        bench = CapabilityReuseBenchmark()
        bench.add_track_a(TrackRecord(
            production_id="a1", duration_seconds=200, review_rounds=4, defect_count=3,
        ))
        bench.add_track_b(TrackRecord(
            production_id="b1", duration_seconds=200, review_rounds=4, defect_count=3,
        ))
        result = bench.run()
        assert result.verdict == "NOT_PROVEN"

    def test_harmful_verdict(self):
        bench = CapabilityReuseBenchmark()
        bench.add_track_a(TrackRecord(
            production_id="a1", duration_seconds=300, review_rounds=6, defect_count=10,
        ))
        bench.add_track_b(TrackRecord(
            production_id="b1", duration_seconds=100, review_rounds=1, defect_count=0,
        ))
        result = bench.run()
        assert result.verdict == "HARMFUL"

    def test_capability_roi_computed(self):
        bench = CapabilityReuseBenchmark()
        bench.register_capability(ReusableCapability(
            capability_id="cap1", name="Template Engine",
        ))
        bench.add_track_a(TrackRecord(
            production_id="a1", duration_seconds=50,
            capabilities_reused=["cap1"],
        ))
        bench.add_track_b(TrackRecord(
            production_id="b1", duration_seconds=200,
        ))
        result = bench.run()
        assert result.total_reuses == 1
        assert result.unique_capabilities_reused == 1
        assert len(result.capability_roi) == 1

    def test_aggregate_roi(self):
        bench = CapabilityReuseBenchmark()
        bench.register_capability(ReusableCapability(capability_id="c1", name="C1"))
        bench.add_track_a(TrackRecord(
            production_id="a1", duration_seconds=80, capabilities_reused=["c1"],
        ))
        bench.add_track_b(TrackRecord(
            production_id="b1", duration_seconds=200,
        ))
        result = bench.run()
        assert result.aggregate_roi > 0

    def test_add_records(self):
        bench = CapabilityReuseBenchmark()
        bench.add_records([
            TrackRecord(production_id="a1", track="A", duration_seconds=100),
            TrackRecord(production_id="b1", track="B", duration_seconds=200),
        ])
        assert bench.track_a_count == 1
        assert bench.track_b_count == 1

    def test_to_dict(self):
        bench = CapabilityReuseBenchmark()
        bench.add_track_a(TrackRecord(production_id="a1", duration_seconds=100))
        bench.add_track_b(TrackRecord(production_id="b1", duration_seconds=200))
        result = bench.run()
        d = result.to_dict()
        assert "verdict" in d
        assert "time_saved_pct" in d
        assert "aggregate_roi" in d

    def test_multiple_capabilities(self):
        bench = CapabilityReuseBenchmark()
        bench.register_capability(ReusableCapability(capability_id="c1", name="C1"))
        bench.register_capability(ReusableCapability(capability_id="c2", name="C2"))
        bench.add_track_a(TrackRecord(
            production_id="a1", duration_seconds=60,
            capabilities_reused=["c1", "c2"],
        ))
        bench.add_track_b(TrackRecord(
            production_id="b1", duration_seconds=200,
        ))
        result = bench.run()
        assert result.unique_capabilities_reused == 2
        assert result.total_reuses == 2

    def test_partially_proven(self):
        bench = CapabilityReuseBenchmark()
        bench.add_track_a(TrackRecord(
            production_id="a1", duration_seconds=50, review_rounds=3, defect_count=2,
        ))
        bench.add_track_b(TrackRecord(
            production_id="b1", duration_seconds=200, review_rounds=3, defect_count=2,
        ))
        result = bench.run()
        assert result.verdict == "PARTIALLY_PROVEN"
