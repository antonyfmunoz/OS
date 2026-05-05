"""Tests for CU Execution Probe.

Validates probe construction, blocker detection, and the distinction
between hardening-ready and production parity-ready.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_cu_execution_probe import (
    CUExecutionProbeResult,
    CUExecutionProbeStatus,
    build_cu_probe_result,
    build_vps_environment_probe,
    build_windows_local_probe,
    cu_probe_allows_hardening,
    cu_probe_allows_production_parity,
    cu_probe_blocks_maturity,
    summarize_cu_probe,
)


class TestCUExecutionProbe(unittest.TestCase):
    def test_probe_result_builds(self) -> None:
        result = build_cu_probe_result(probe_id="test")
        self.assertIsInstance(result, CUExecutionProbeResult)

    def test_missing_visible_session_blocks_maturity(self) -> None:
        result = build_cu_probe_result(visible_session_available=False)
        self.assertTrue(cu_probe_blocks_maturity(result))
        self.assertIn("NO_VISIBLE_SESSION", result.blockers)

    def test_wrong_account_blocks_production_parity(self) -> None:
        result = build_cu_probe_result(
            visible_session_available=True,
            ui_access_available=True,
            account_confirmed=False,
        )
        self.assertFalse(cu_probe_allows_production_parity(result))
        self.assertIn("ACCOUNT_NOT_CONFIRMED", result.blockers)

    def test_drive_not_visible_blocks(self) -> None:
        result = build_cu_probe_result(
            visible_session_available=True,
            ui_access_available=True,
            account_confirmed=True,
            drive_visible=False,
        )
        self.assertIn("DRIVE_NOT_VISIBLE", result.blockers)
        self.assertFalse(cu_probe_allows_production_parity(result))

    def test_doc_not_visible_tracked(self) -> None:
        result = build_cu_probe_result(doc_visible=False)
        self.assertFalse(result.doc_visible)

    def test_governance_unsafe_blocks_hardening(self) -> None:
        result = build_cu_probe_result(
            visible_session_available=True,
            ui_access_available=True,
            governance_safe=False,
        )
        self.assertFalse(cu_probe_allows_hardening(result))
        self.assertIn("GOVERNANCE_BLOCKED", result.blockers)

    def test_hardening_ready_differs_from_parity(self) -> None:
        result = build_cu_probe_result(
            visible_session_available=True,
            ui_access_available=True,
            governance_safe=True,
            account_confirmed=False,
            extraction_available=False,
        )
        self.assertTrue(cu_probe_allows_hardening(result))
        self.assertFalse(cu_probe_allows_production_parity(result))

    def test_full_ready_probe(self) -> None:
        result = build_cu_probe_result(
            visible_session_available=True,
            ui_access_available=True,
            governance_safe=True,
            account_confirmed=True,
            drive_visible=True,
            doc_visible=True,
            extraction_available=True,
        )
        self.assertTrue(cu_probe_allows_hardening(result))
        self.assertTrue(cu_probe_allows_production_parity(result))
        self.assertFalse(cu_probe_blocks_maturity(result))
        self.assertEqual(result.blockers, [])

    def test_vps_probe_blocks(self) -> None:
        result = build_vps_environment_probe("W-GDRIVE-CU-001")
        self.assertTrue(cu_probe_blocks_maturity(result))
        self.assertFalse(cu_probe_allows_hardening(result))
        self.assertEqual(result.source_system, "linux_vps")

    def test_windows_probe_partial(self) -> None:
        result = build_windows_local_probe(
            "W-GDRIVE-CU-001", account_confirmed=True, drive_visible=True
        )
        self.assertTrue(cu_probe_allows_hardening(result))
        self.assertEqual(result.source_system, "windows_desktop")

    def test_summarize_probe(self) -> None:
        result = build_cu_probe_result(probe_id="test")
        s = summarize_cu_probe(result)
        self.assertEqual(s["probe_id"], "test")
        self.assertIn("blockers", s)

    def test_probe_to_dict(self) -> None:
        result = build_cu_probe_result(probe_id="test")
        d = result.to_dict()
        self.assertEqual(d["probe_id"], "test")

    def test_extraction_blocked(self) -> None:
        result = build_cu_probe_result(
            visible_session_available=True,
            ui_access_available=True,
            extraction_available=False,
        )
        self.assertIn("EXTRACTION_BLOCKED", result.blockers)

    def test_status_enum(self) -> None:
        self.assertEqual(
            CUExecutionProbeStatus.NO_VISIBLE_SESSION.value,
            "no_visible_session",
        )
        self.assertEqual(
            CUExecutionProbeStatus.READY.value, "ready"
        )


if __name__ == "__main__":
    unittest.main()
