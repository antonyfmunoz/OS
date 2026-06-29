"""C32 Benchmark Harness Tests.

Validates metrics collection, comparison, and persistence.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, "/opt/OS")


class TestBenchmarkHarness:
    def test_start_and_end_cycle(self):
        from substrate.organism.benchmark_harness import BenchmarkHarness

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "bench.jsonl")
        harness = BenchmarkHarness(store_path=path)

        harness.start_cycle("c1", "legacy", "test task")
        time.sleep(0.05)
        metrics = harness.end_cycle("c1", "legacy", files_changed=3, tests_written=2)

        assert metrics.cycle_id == "c1"
        assert metrics.pipeline == "legacy"
        assert metrics.elapsed_seconds > 0
        assert metrics.files_changed == 3
        assert metrics.tests_written == 2

    def test_persists_to_jsonl(self):
        from substrate.organism.benchmark_harness import BenchmarkHarness

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "bench.jsonl")
        harness = BenchmarkHarness(store_path=path)

        harness.start_cycle("c1", "legacy", "task A")
        harness.end_cycle("c1", "legacy", files_changed=1)

        assert os.path.exists(path)
        with open(path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 1
        assert lines[0]["cycle_id"] == "c1"

    def test_loads_from_disk(self):
        from substrate.organism.benchmark_harness import BenchmarkHarness

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "bench.jsonl")

        h1 = BenchmarkHarness(store_path=path)
        h1.start_cycle("c1", "governed", "task B")
        h1.end_cycle("c1", "governed", spine_submissions=3)

        h2 = BenchmarkHarness(store_path=path)
        assert len(h2.all_records()) == 1
        assert h2.all_records()[0].spine_submissions == 3

    def test_compare_produces_report(self):
        from substrate.organism.benchmark_harness import BenchmarkHarness

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "bench.jsonl")
        harness = BenchmarkHarness(store_path=path)

        harness.start_cycle("c1", "legacy", "compare test")
        harness.end_cycle("c1", "legacy", files_changed=5, tests_written=3)

        harness.start_cycle("c1", "governed", "compare test")
        harness.end_cycle("c1", "governed", files_changed=4, tests_written=4,
                         spine_submissions=2, learning_signals_generated=1)

        report = harness.compare("c1")
        assert "Cycle c1" in report
        assert "Legacy (A)" in report
        assert "Governed (B)" in report
        assert "Spine submissions: 2" in report
        assert "Learning signals: 1" in report

    def test_campaign_summary(self):
        from substrate.organism.benchmark_harness import BenchmarkHarness

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "bench.jsonl")
        harness = BenchmarkHarness(store_path=path)

        for cid in ["c1", "c2"]:
            harness.start_cycle(cid, "legacy", f"task {cid}")
            harness.end_cycle(cid, "legacy")
            harness.start_cycle(cid, "governed", f"task {cid}")
            harness.end_cycle(cid, "governed", learning_signals_generated=2)

        summary = harness.campaign_summary()
        assert "C32 Campaign Summary" in summary
        assert "c1" in summary
        assert "c2" in summary

    def test_overrides_applied(self):
        from substrate.organism.benchmark_harness import BenchmarkHarness

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "bench.jsonl")
        harness = BenchmarkHarness(store_path=path)

        harness.start_cycle("c1", "governed", "override test")
        metrics = harness.end_cycle(
            "c1", "governed",
            work_packets_created=3,
            approvals_required=1,
            proof_packages_created=2,
            capabilities_extracted=1,
            reusable_assets_created=1,
        )
        assert metrics.work_packets_created == 3
        assert metrics.proof_packages_created == 2
        assert metrics.capabilities_extracted == 1

    def test_incomplete_compare(self):
        from substrate.organism.benchmark_harness import BenchmarkHarness

        tmp = tempfile.mkdtemp()
        harness = BenchmarkHarness(store_path=os.path.join(tmp, "b.jsonl"))

        harness.start_cycle("c1", "legacy", "only one side")
        harness.end_cycle("c1", "legacy")

        report = harness.compare("c1")
        assert "incomplete data" in report
