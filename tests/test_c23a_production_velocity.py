"""Tests for Benchmark 3 — Production Velocity."""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/remaining-phases")

from substrate.organism.benchmarks.production_velocity import (
    ProductionRecord,
    ProductionVelocityBenchmark,
    VelocityResult,
)


class TestProductionRecord:
    def test_duration_calculation(self):
        r = ProductionRecord(start_epoch=100.0, end_epoch=200.0)
        assert r.duration_seconds == 100.0

    def test_duration_non_negative(self):
        r = ProductionRecord(start_epoch=200.0, end_epoch=100.0)
        assert r.duration_seconds == 0.0

    def test_zero_duration(self):
        r = ProductionRecord(start_epoch=100.0, end_epoch=100.0)
        assert r.duration_seconds == 0.0

    def test_defaults(self):
        r = ProductionRecord()
        assert r.production_id == ""
        assert r.reuse_enabled is True


class TestVelocityResult:
    def test_defaults(self):
        r = VelocityResult()
        assert r.productions == 0
        assert r.trend_direction == "stable"

    def test_to_dict(self):
        r = VelocityResult(productions=3, avg_duration_seconds=100.0)
        d = r.to_dict()
        assert d["productions"] == 3
        assert d["avg_duration_seconds"] == 100.0


class TestProductionVelocityBenchmark:
    def test_empty_records(self):
        bench = ProductionVelocityBenchmark()
        result = bench.run()
        assert result.productions == 0

    def test_single_record(self):
        bench = ProductionVelocityBenchmark()
        bench.add_record(ProductionRecord(
            production_id="p1", start_epoch=0, end_epoch=100,
        ))
        result = bench.run()
        assert result.productions == 1
        assert result.avg_duration_seconds == 100.0

    def test_accelerating_trend(self):
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord(production_id="p1", start_epoch=0, end_epoch=200),
            ProductionRecord(production_id="p2", start_epoch=200, end_epoch=350),
            ProductionRecord(production_id="p3", start_epoch=350, end_epoch=450),
            ProductionRecord(production_id="p4", start_epoch=450, end_epoch=520),
        ])
        result = bench.run()
        assert result.trend_direction == "accelerating"
        assert result.acceleration_ratio > 1.05

    def test_decelerating_trend(self):
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord(production_id="p1", start_epoch=0, end_epoch=50),
            ProductionRecord(production_id="p2", start_epoch=50, end_epoch=120),
            ProductionRecord(production_id="p3", start_epoch=120, end_epoch=250),
            ProductionRecord(production_id="p4", start_epoch=250, end_epoch=500),
        ])
        result = bench.run()
        assert result.trend_direction == "decelerating"
        assert result.acceleration_ratio < 0.95

    def test_stable_trend(self):
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord(production_id="p1", start_epoch=0, end_epoch=100),
            ProductionRecord(production_id="p2", start_epoch=100, end_epoch=200),
            ProductionRecord(production_id="p3", start_epoch=200, end_epoch=300),
            ProductionRecord(production_id="p4", start_epoch=300, end_epoch=400),
        ])
        result = bench.run()
        assert result.trend_direction == "stable"

    def test_track_filter_reuse_on(self):
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord(production_id="a1", start_epoch=0, end_epoch=100, reuse_enabled=True),
            ProductionRecord(production_id="b1", start_epoch=0, end_epoch=200, reuse_enabled=False),
        ])
        result = bench.run(track_filter=True)
        assert result.productions == 1
        assert result.avg_duration_seconds == 100.0

    def test_track_filter_reuse_off(self):
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord(production_id="a1", start_epoch=0, end_epoch=100, reuse_enabled=True),
            ProductionRecord(production_id="b1", start_epoch=0, end_epoch=200, reuse_enabled=False),
        ])
        result = bench.run(track_filter=False)
        assert result.productions == 1
        assert result.avg_duration_seconds == 200.0

    def test_compare_tracks(self):
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord(production_id="a1", start_epoch=0, end_epoch=100, reuse_enabled=True),
            ProductionRecord(production_id="a2", start_epoch=100, end_epoch=180, reuse_enabled=True),
            ProductionRecord(production_id="b1", start_epoch=0, end_epoch=200, reuse_enabled=False),
            ProductionRecord(production_id="b2", start_epoch=200, end_epoch=400, reuse_enabled=False),
        ])
        comparison = bench.compare_tracks()
        assert comparison["reuse_faster"] is True
        assert comparison["speedup_ratio"] > 1.0

    def test_record_count(self):
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord(production_id="p1", start_epoch=0, end_epoch=100),
            ProductionRecord(production_id="p2", start_epoch=100, end_epoch=200),
        ])
        assert bench.record_count == 2

    def test_durations_in_result(self):
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord(production_id="p1", start_epoch=0, end_epoch=100),
            ProductionRecord(production_id="p2", start_epoch=100, end_epoch=250),
        ])
        result = bench.run()
        assert result.durations == [100.0, 150.0]

    def test_details_in_result(self):
        bench = ProductionVelocityBenchmark()
        bench.add_record(ProductionRecord(
            production_id="p1", start_epoch=0, end_epoch=100, description="test build",
        ))
        result = bench.run()
        assert len(result.details) == 1
        assert result.details[0]["production_id"] == "p1"
        assert result.details[0]["description"] == "test build"

    def test_total_duration(self):
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord(production_id="p1", start_epoch=0, end_epoch=100),
            ProductionRecord(production_id="p2", start_epoch=100, end_epoch=300),
        ])
        result = bench.run()
        assert result.total_duration_seconds == 300.0

    def test_sorted_by_start_epoch(self):
        bench = ProductionVelocityBenchmark()
        bench.add_records([
            ProductionRecord(production_id="p2", start_epoch=100, end_epoch=200),
            ProductionRecord(production_id="p1", start_epoch=0, end_epoch=50),
        ])
        result = bench.run()
        assert result.details[0]["production_id"] == "p1"
        assert result.details[1]["production_id"] == "p2"
