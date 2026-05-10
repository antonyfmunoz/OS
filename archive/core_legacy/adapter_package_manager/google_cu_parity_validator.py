"""CU Parity Validator.

Validates Computer Use extraction results against API baselines
for Drive inventory and Docs tab-aware extraction.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


W0_001_API_BASELINE = {
    "expected_docs": 28,
    "expected_tabs": 321,
    "expected_child_tabs": 134,
    "expected_words": 283831,
    "drive_api_package": "W-GDRIVE-API-001",
    "docs_api_package": "W-GDOCS-API-001",
}


@dataclass
class CUParityValidationResult:
    source_package_id: str = ""
    target_package_id: str = ""
    api_baseline_package_id: str = ""
    expected_docs: int = 0
    actual_docs: int = 0
    expected_tabs: int = 0
    actual_tabs: int = 0
    expected_child_tabs: int = 0
    actual_child_tabs: int = 0
    expected_words: int = 0
    actual_words: int = 0
    provenance_match: bool = False
    coverage_match: bool = False
    parity_passed: bool = False
    mismatches: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_package_id": self.source_package_id,
            "target_package_id": self.target_package_id,
            "api_baseline_package_id": self.api_baseline_package_id,
            "expected_docs": self.expected_docs,
            "actual_docs": self.actual_docs,
            "expected_tabs": self.expected_tabs,
            "actual_tabs": self.actual_tabs,
            "expected_child_tabs": self.expected_child_tabs,
            "actual_child_tabs": self.actual_child_tabs,
            "expected_words": self.expected_words,
            "actual_words": self.actual_words,
            "provenance_match": self.provenance_match,
            "coverage_match": self.coverage_match,
            "parity_passed": self.parity_passed,
            "mismatches": self.mismatches,
            "notes": self.notes,
        }


def build_w0_001_api_baseline() -> dict[str, Any]:
    return dict(W0_001_API_BASELINE)


def validate_drive_cu_against_api(
    cu_file_count: int,
    api_file_count: int,
    provenance_match: bool = True,
) -> CUParityValidationResult:
    result = CUParityValidationResult(
        source_package_id="W-GDRIVE-CU-001",
        target_package_id="W-GDRIVE-CU-001",
        api_baseline_package_id="W-GDRIVE-API-001",
        expected_docs=api_file_count,
        actual_docs=cu_file_count,
        provenance_match=provenance_match,
    )
    mismatches = []

    if cu_file_count != api_file_count:
        mismatches.append(
            f"file_count: expected={api_file_count}, actual={cu_file_count}"
        )

    if not provenance_match:
        mismatches.append("provenance_mismatch")

    result.mismatches = mismatches
    result.coverage_match = cu_file_count >= api_file_count
    result.parity_passed = len(mismatches) == 0
    return result


def validate_docs_cu_against_api(
    actual_docs: int = 0,
    actual_tabs: int = 0,
    actual_child_tabs: int = 0,
    actual_words: int = 0,
    provenance_match: bool = True,
) -> CUParityValidationResult:
    baseline = W0_001_API_BASELINE
    result = CUParityValidationResult(
        source_package_id="W-GDOCS-CU-001",
        target_package_id="W-GDOCS-CU-001",
        api_baseline_package_id="W-GDOCS-API-001",
        expected_docs=baseline["expected_docs"],
        actual_docs=actual_docs,
        expected_tabs=baseline["expected_tabs"],
        actual_tabs=actual_tabs,
        expected_child_tabs=baseline["expected_child_tabs"],
        actual_child_tabs=actual_child_tabs,
        expected_words=baseline["expected_words"],
        actual_words=actual_words,
        provenance_match=provenance_match,
    )
    mismatches = []

    if actual_docs != baseline["expected_docs"]:
        mismatches.append(
            f"docs: expected={baseline['expected_docs']}, actual={actual_docs}"
        )
    if actual_tabs != baseline["expected_tabs"]:
        mismatches.append(
            f"tabs: expected={baseline['expected_tabs']}, actual={actual_tabs}"
        )
    if actual_child_tabs != baseline["expected_child_tabs"]:
        mismatches.append(
            f"child_tabs: expected={baseline['expected_child_tabs']}, actual={actual_child_tabs}"
        )
    if actual_words != baseline["expected_words"]:
        mismatches.append(
            f"words: expected={baseline['expected_words']}, actual={actual_words}"
        )
    if not provenance_match:
        mismatches.append("provenance_mismatch")

    result.mismatches = mismatches
    result.coverage_match = (
        actual_docs >= baseline["expected_docs"]
        and actual_tabs >= baseline["expected_tabs"]
    )
    result.parity_passed = len(mismatches) == 0
    return result


def cu_parity_blocks_maturity(result: CUParityValidationResult) -> bool:
    return not result.parity_passed


def summarize_cu_parity(
    result: CUParityValidationResult,
) -> dict[str, Any]:
    return {
        "source": result.source_package_id,
        "baseline": result.api_baseline_package_id,
        "parity_passed": result.parity_passed,
        "mismatch_count": len(result.mismatches),
        "mismatches": result.mismatches,
    }
