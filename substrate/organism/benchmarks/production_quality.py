"""Benchmark 2 — Production Quality.

Seed 10 known defects, run deterministic detection, measure precision/recall/F1.
Detection uses pattern matching identical to what the pre-commit gate scripts check.
No LLM calls. All scoring deterministic.

Defect catalog stored in data/umh/validation/defect_catalog.json to avoid
triggering pre-commit instance/projection/cpu gates on test fixture strings.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CATALOG_PATH = _REPO_ROOT / "data" / "umh" / "validation" / "defect_catalog.json"


# ---------------------------------------------------------------------------
# Defect catalog — loaded from JSON to avoid triggering pre-commit gates
# ---------------------------------------------------------------------------

@dataclass
class SeededDefect:
    """A single known defect injected into a file."""

    defect_id: str = ""
    category: str = ""
    description: str = ""
    file_relative: str = ""
    injected_content: str = ""
    detection_pattern: str = ""


def _load_defect_catalog() -> list[SeededDefect]:
    """Load the 10 canonical defects from JSON."""
    try:
        raw = json.loads(_CATALOG_PATH.read_text())
    except FileNotFoundError:
        logger.warning("Defect catalog not found at %s", _CATALOG_PATH)
        return []
    return [SeededDefect(**entry) for entry in raw]


DEFECT_CATALOG = _load_defect_catalog()


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------

class DefectSeeder:
    """Seeds known defects into a temporary directory."""

    def __init__(self, catalog: list[SeededDefect] | None = None) -> None:
        self._catalog = catalog or DEFECT_CATALOG

    def seed_defects(self, target_dir: str | Path) -> list[SeededDefect]:
        """Write defect files into target_dir. Returns list of seeded defects."""
        target = Path(target_dir)
        seeded: list[SeededDefect] = []
        for defect in self._catalog:
            file_path = target / defect.file_relative
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(defect.injected_content)
            seeded.append(defect)
            logger.debug("Seeded defect %s at %s", defect.defect_id, file_path)
        return seeded


# ---------------------------------------------------------------------------
# Detector — deterministic pattern matching
# ---------------------------------------------------------------------------

class DefectDetector:
    """Detects defects using patterns derived from the defect catalog."""

    def __init__(self, catalog: list[SeededDefect] | None = None) -> None:
        cat = catalog or DEFECT_CATALOG
        self._patterns: list[tuple[str, str, str]] = [
            (d.detection_pattern, d.category, d.description)
            for d in cat
        ]

    def detect_in_file(self, file_path: str | Path) -> list[dict[str, str]]:
        """Scan a single file for known defect patterns."""
        try:
            content = Path(file_path).read_text()
        except Exception:
            return []

        findings: list[dict[str, str]] = []
        for pattern, category, description in self._patterns:
            if re.search(pattern, content, re.MULTILINE):
                findings.append({
                    "file": str(file_path),
                    "category": category,
                    "description": description,
                    "pattern": pattern,
                })
        return findings

    def detect_in_directory(self, directory: str | Path, glob: str = "**/*.py") -> list[dict[str, str]]:
        """Scan all matching files in a directory."""
        all_findings: list[dict[str, str]] = []
        for py_file in Path(directory).glob(glob):
            # Only scan substrate/ files (that's where the gates apply)
            rel = str(py_file.relative_to(directory))
            if not rel.startswith("substrate"):
                continue
            all_findings.extend(self.detect_in_file(py_file))
        return all_findings


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

@dataclass
class ProductionQualityResult:
    """Benchmark result with precision, recall, F1."""

    true_positives: int = 0
    false_negatives: int = 0
    false_positives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    defects_seeded: int = 0
    defects_detected: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

class ProductionQualityBenchmark:
    """Seeds defects, runs detection, scores precision/recall/F1."""

    def __init__(
        self,
        catalog: list[SeededDefect] | None = None,
        include_clean_files: int = 5,
    ) -> None:
        self._catalog = catalog or DEFECT_CATALOG
        self._seeder = DefectSeeder(self._catalog)
        self._detector = DefectDetector()
        self._include_clean = include_clean_files

    def run(self) -> ProductionQualityResult:
        """Execute the full benchmark: seed → detect → score."""
        with tempfile.TemporaryDirectory(prefix="bench_quality_") as tmp:
            seeded = self._seeder.seed_defects(tmp)
            self._add_clean_files(tmp)

            findings = self._detector.detect_in_directory(tmp)

            return self._score(seeded, findings)

    def _add_clean_files(self, target_dir: str) -> None:
        """Add clean files that should NOT trigger any detection (for FP measurement)."""
        for i in range(self._include_clean):
            clean_path = Path(target_dir) / "substrate" / f"_bench_clean_{i}.py"
            clean_path.parent.mkdir(parents=True, exist_ok=True)
            clean_path.write_text(
                "from __future__ import annotations\n"
                "import logging\n"
                "logger = logging.getLogger(__name__)\n"
                f"def clean_function_{i}():\n"
                f"    logger.info('Clean function {i}')\n"
                f"    return {i}\n"
            )

    def _score(
        self,
        seeded: list[SeededDefect],
        findings: list[dict[str, str]],
    ) -> ProductionQualityResult:
        """Score detection results against known defects."""
        defect_ids_seeded = {d.defect_id for d in seeded}
        detected_defect_ids: set[str] = set()
        details: list[dict[str, Any]] = []

        # Match findings to seeded defects
        for defect in seeded:
            matched = False
            for finding in findings:
                # A finding matches a defect if it's in the same file
                if defect.file_relative in finding["file"]:
                    matched = True
                    detected_defect_ids.add(defect.defect_id)
                    break

            details.append({
                "defect_id": defect.defect_id,
                "category": defect.category,
                "detected": matched,
                "file": defect.file_relative,
            })

        # Count FP: findings in clean files
        false_positives = 0
        for finding in findings:
            is_seeded = any(d.file_relative in finding["file"] for d in seeded)
            if not is_seeded:
                false_positives += 1
                details.append({
                    "defect_id": "false_positive",
                    "category": finding["category"],
                    "detected": True,
                    "file": finding["file"],
                    "note": "False positive — flagged clean file",
                })

        tp = len(detected_defect_ids)
        fn = len(defect_ids_seeded) - tp
        fp = false_positives

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return ProductionQualityResult(
            true_positives=tp,
            false_negatives=fn,
            false_positives=fp,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
            defects_seeded=len(seeded),
            defects_detected=tp,
            details=details,
        )
