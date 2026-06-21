"""Tests for Benchmark 2 — Production Quality."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/opt/OS/.claude/worktrees/remaining-phases")

from substrate.organism.benchmarks.production_quality import (
    DEFECT_CATALOG,
    DefectDetector,
    DefectSeeder,
    ProductionQualityBenchmark,
    ProductionQualityResult,
    SeededDefect,
)


class TestSeededDefect:
    def test_catalog_has_10_defects(self):
        assert len(DEFECT_CATALOG) == 10

    def test_each_defect_has_required_fields(self):
        for d in DEFECT_CATALOG:
            assert d.defect_id
            assert d.category
            assert d.file_relative
            assert d.injected_content
            assert d.detection_pattern

    def test_unique_defect_ids(self):
        ids = [d.defect_id for d in DEFECT_CATALOG]
        assert len(ids) == len(set(ids))

    def test_unique_file_paths(self):
        paths = [d.file_relative for d in DEFECT_CATALOG]
        assert len(paths) == len(set(paths))

    def test_categories_covered(self):
        categories = {d.category for d in DEFECT_CATALOG}
        assert "architecture" in categories
        assert "instance_context" in categories
        assert "quality" in categories
        assert "security" in categories


class TestDefectSeeder:
    def test_seeds_all_defects(self):
        with tempfile.TemporaryDirectory() as tmp:
            seeder = DefectSeeder()
            seeded = seeder.seed_defects(tmp)
            assert len(seeded) == 10

    def test_files_created_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            seeder = DefectSeeder()
            seeder.seed_defects(tmp)
            for defect in DEFECT_CATALOG:
                fp = Path(tmp) / defect.file_relative
                assert fp.exists(), f"{defect.file_relative} not created"

    def test_file_content_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            seeder = DefectSeeder()
            seeder.seed_defects(tmp)
            for defect in DEFECT_CATALOG:
                fp = Path(tmp) / defect.file_relative
                assert fp.read_text() == defect.injected_content

    def test_custom_catalog(self):
        custom = [DEFECT_CATALOG[0]]
        with tempfile.TemporaryDirectory() as tmp:
            seeder = DefectSeeder(catalog=custom)
            seeded = seeder.seed_defects(tmp)
            assert len(seeded) == 1


class TestDefectDetector:
    def test_detects_wrong_import(self):
        detector = DefectDetector()
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "substrate" / "bad.py"
            f.parent.mkdir(parents=True)
            f.write_text("from transports.api import cockpit\n")
            findings = detector.detect_in_directory(tmp)
            assert len(findings) >= 1
            assert findings[0]["category"] == "architecture"

    def test_detects_hardcoded_ip(self):
        detector = DefectDetector()
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "substrate" / "bad.py"
            f.parent.mkdir(parents=True)
            f.write_text('HOST = "100.77.233.50"\n')
            findings = detector.detect_in_directory(tmp)
            assert any(f["category"] == "instance_context" for f in findings)

    def test_detects_eval(self):
        detector = DefectDetector()
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "substrate" / "bad.py"
            f.parent.mkdir(parents=True)
            f.write_text("result = eval(user_input)\n")
            findings = detector.detect_in_directory(tmp)
            assert any(f["category"] == "security" for f in findings)

    def test_detects_subprocess(self):
        detector = DefectDetector()
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "substrate" / "bad.py"
            f.parent.mkdir(parents=True)
            f.write_text('import subprocess\nsubprocess.run(["ls"])\n')
            findings = detector.detect_in_directory(tmp)
            assert any(f["category"] == "cpu_gate" for f in findings)

    def test_clean_file_no_findings(self):
        detector = DefectDetector()
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "substrate" / "clean.py"
            f.parent.mkdir(parents=True)
            f.write_text("import logging\ndef hello(): return 42\n")
            findings = detector.detect_in_directory(tmp)
            assert len(findings) == 0

    def test_only_scans_substrate(self):
        detector = DefectDetector()
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "services" / "bad.py"
            f.parent.mkdir(parents=True)
            f.write_text("result = eval(user_input)\n")
            findings = detector.detect_in_directory(tmp)
            assert len(findings) == 0

    def test_detect_in_file(self):
        detector = DefectDetector()
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "test.py"
            f.write_text('"DEX"\n')
            findings = detector.detect_in_file(f)
            assert any(f_item["category"] == "instance_context" for f_item in findings)


class TestProductionQualityBenchmark:
    def test_full_run_returns_result(self):
        bench = ProductionQualityBenchmark()
        result = bench.run()
        assert isinstance(result, ProductionQualityResult)

    def test_all_10_defects_detected(self):
        bench = ProductionQualityBenchmark()
        result = bench.run()
        assert result.defects_seeded == 10
        assert result.defects_detected == 10
        assert result.recall == 1.0

    def test_no_false_positives(self):
        bench = ProductionQualityBenchmark()
        result = bench.run()
        assert result.false_positives == 0
        assert result.precision == 1.0

    def test_f1_perfect(self):
        bench = ProductionQualityBenchmark()
        result = bench.run()
        assert result.f1 == 1.0

    def test_partial_detection(self):
        partial_catalog = DEFECT_CATALOG[:5]
        bench = ProductionQualityBenchmark(catalog=partial_catalog, include_clean_files=0)
        result = bench.run()
        assert result.defects_seeded == 5
        assert result.defects_detected == 5

    def test_to_dict(self):
        bench = ProductionQualityBenchmark()
        result = bench.run()
        d = result.to_dict()
        assert "precision" in d
        assert "recall" in d
        assert "f1" in d
        assert "true_positives" in d

    def test_details_per_defect(self):
        bench = ProductionQualityBenchmark()
        result = bench.run()
        detected_details = [d for d in result.details if d.get("defect_id") != "false_positive"]
        assert len(detected_details) == 10
        for detail in detected_details:
            assert detail["detected"] is True

    def test_clean_files_count(self):
        bench = ProductionQualityBenchmark(include_clean_files=10)
        result = bench.run()
        assert result.false_positives == 0
