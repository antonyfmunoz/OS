"""Tests for CU Parity Validator.

Validates API baseline construction, parity pass/fail conditions,
and mismatch detection for Drive and Docs CU.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_cu_parity_validator import (
    CUParityValidationResult,
    build_w0_001_api_baseline,
    cu_parity_blocks_maturity,
    summarize_cu_parity,
    validate_docs_cu_against_api,
    validate_drive_cu_against_api,
)


class TestAPIBaseline(unittest.TestCase):
    def test_baseline_builds(self) -> None:
        b = build_w0_001_api_baseline()
        self.assertEqual(b["expected_docs"], 28)
        self.assertEqual(b["expected_tabs"], 321)
        self.assertEqual(b["expected_child_tabs"], 134)
        self.assertEqual(b["expected_words"], 283831)

    def test_baseline_has_packages(self) -> None:
        b = build_w0_001_api_baseline()
        self.assertEqual(b["drive_api_package"], "W-GDRIVE-API-001")
        self.assertEqual(b["docs_api_package"], "W-GDOCS-API-001")


class TestDriveCUParity(unittest.TestCase):
    def test_parity_passes_when_match(self) -> None:
        result = validate_drive_cu_against_api(26, 26)
        self.assertTrue(result.parity_passed)
        self.assertEqual(result.mismatches, [])

    def test_parity_fails_when_count_mismatch(self) -> None:
        result = validate_drive_cu_against_api(20, 26)
        self.assertFalse(result.parity_passed)
        self.assertTrue(len(result.mismatches) > 0)

    def test_parity_fails_when_provenance_missing(self) -> None:
        result = validate_drive_cu_against_api(26, 26, provenance_match=False)
        self.assertFalse(result.parity_passed)
        self.assertIn("provenance_mismatch", result.mismatches)

    def test_blocks_maturity_on_fail(self) -> None:
        result = validate_drive_cu_against_api(20, 26)
        self.assertTrue(cu_parity_blocks_maturity(result))

    def test_does_not_block_on_pass(self) -> None:
        result = validate_drive_cu_against_api(26, 26)
        self.assertFalse(cu_parity_blocks_maturity(result))

    def test_result_to_dict(self) -> None:
        result = validate_drive_cu_against_api(26, 26)
        d = result.to_dict()
        self.assertEqual(d["source_package_id"], "W-GDRIVE-CU-001")


class TestDocsCUParity(unittest.TestCase):
    def test_parity_passes_when_all_match(self) -> None:
        result = validate_docs_cu_against_api(28, 321, 134, 283831)
        self.assertTrue(result.parity_passed)
        self.assertEqual(result.mismatches, [])

    def test_parity_fails_when_docs_mismatch(self) -> None:
        result = validate_docs_cu_against_api(20, 321, 134, 283831)
        self.assertFalse(result.parity_passed)
        self.assertTrue(any("docs:" in m for m in result.mismatches))

    def test_parity_fails_when_tabs_mismatch(self) -> None:
        result = validate_docs_cu_against_api(28, 200, 134, 283831)
        self.assertFalse(result.parity_passed)
        self.assertTrue(any("tabs:" in m for m in result.mismatches))

    def test_parity_fails_when_child_tabs_mismatch(self) -> None:
        result = validate_docs_cu_against_api(28, 321, 100, 283831)
        self.assertFalse(result.parity_passed)
        self.assertTrue(any("child_tabs:" in m for m in result.mismatches))

    def test_parity_fails_when_words_mismatch(self) -> None:
        result = validate_docs_cu_against_api(28, 321, 134, 100000)
        self.assertFalse(result.parity_passed)
        self.assertTrue(any("words:" in m for m in result.mismatches))

    def test_parity_fails_when_provenance_missing(self) -> None:
        result = validate_docs_cu_against_api(
            28, 321, 134, 283831, provenance_match=False
        )
        self.assertFalse(result.parity_passed)
        self.assertIn("provenance_mismatch", result.mismatches)

    def test_blocks_maturity_on_fail(self) -> None:
        result = validate_docs_cu_against_api(0, 0, 0, 0)
        self.assertTrue(cu_parity_blocks_maturity(result))

    def test_summarize(self) -> None:
        result = validate_docs_cu_against_api(28, 321, 134, 283831)
        s = summarize_cu_parity(result)
        self.assertTrue(s["parity_passed"])
        self.assertEqual(s["mismatch_count"], 0)


if __name__ == "__main__":
    unittest.main()
