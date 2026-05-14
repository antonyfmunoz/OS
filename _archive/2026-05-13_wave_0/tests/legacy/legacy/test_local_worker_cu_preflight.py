"""Tests for Local Worker CU Preflight.

Validates preflight detection, blocker identification, and
host/GUI/governance gating.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.local_worker_cu_preflight import (
    LocalWorkerCUPreflightResult,
    LocalWorkerCUPreflightStatus,
    local_worker_preflight_blocks_docs_cu,
    local_worker_preflight_blocks_drive_cu,
    run_local_worker_cu_preflight,
    summarize_local_worker_preflight,
)


class TestLocalWorkerCUPreflight(unittest.TestCase):
    def test_preflight_builds(self) -> None:
        r = run_local_worker_cu_preflight()
        self.assertIsInstance(r, LocalWorkerCUPreflightResult)

    def test_vps_is_wrong_host(self) -> None:
        r = run_local_worker_cu_preflight()
        self.assertEqual(
            r.preflight_status, LocalWorkerCUPreflightStatus.WRONG_HOST
        )
        self.assertFalse(r.worker_detected)
        self.assertFalse(r.gui_available)

    def test_missing_worker_blocks_cu_run(self) -> None:
        r = run_local_worker_cu_preflight(
            force_host="windows", force_worker=False
        )
        self.assertEqual(
            r.preflight_status, LocalWorkerCUPreflightStatus.NOT_RUNNING
        )
        self.assertTrue(local_worker_preflight_blocks_drive_cu(r))
        self.assertTrue(local_worker_preflight_blocks_docs_cu(r))

    def test_gui_unavailable_blocks_cu_run(self) -> None:
        r = run_local_worker_cu_preflight(
            force_host="windows", force_worker=True, force_gui=False
        )
        self.assertEqual(
            r.preflight_status, LocalWorkerCUPreflightStatus.GUI_UNAVAILABLE
        )
        self.assertTrue(local_worker_preflight_blocks_drive_cu(r))

    def test_wrong_host_blocks_cu_run(self) -> None:
        r = run_local_worker_cu_preflight(force_host="linux")
        self.assertTrue(local_worker_preflight_blocks_drive_cu(r))
        self.assertTrue(local_worker_preflight_blocks_docs_cu(r))

    def test_governance_unsafe_blocks_cu_run(self) -> None:
        r = run_local_worker_cu_preflight(
            force_host="windows",
            force_worker=True,
            force_gui=True,
            governance_safe=False,
        )
        self.assertEqual(
            r.preflight_status,
            LocalWorkerCUPreflightStatus.GOVERNANCE_BLOCKED,
        )
        self.assertFalse(r.can_run_drive_cu)
        self.assertFalse(r.can_run_docs_cu)

    def test_founder_not_present_blocks_final_maturity(self) -> None:
        r = run_local_worker_cu_preflight(
            force_host="windows",
            force_worker=True,
            force_gui=True,
            founder_presence_confirmed=False,
        )
        self.assertEqual(
            r.preflight_status,
            LocalWorkerCUPreflightStatus.FOUNDER_NOT_PRESENT,
        )
        self.assertTrue(r.can_run_drive_cu)
        self.assertTrue(r.can_run_docs_cu)
        self.assertTrue(len(r.blockers) > 0)

    def test_ready_preflight_allows_hardening(self) -> None:
        r = run_local_worker_cu_preflight(
            force_host="windows",
            force_worker=True,
            force_gui=True,
            founder_presence_confirmed=True,
        )
        self.assertEqual(
            r.preflight_status, LocalWorkerCUPreflightStatus.READY
        )
        self.assertTrue(r.can_run_drive_cu)
        self.assertTrue(r.can_run_docs_cu)
        self.assertFalse(local_worker_preflight_blocks_drive_cu(r))
        self.assertFalse(local_worker_preflight_blocks_docs_cu(r))

    def test_summarize(self) -> None:
        r = run_local_worker_cu_preflight()
        s = summarize_local_worker_preflight(r)
        self.assertIn("preflight_status", s)
        self.assertIn("blockers", s)

    def test_result_to_dict(self) -> None:
        r = run_local_worker_cu_preflight()
        d = r.to_dict()
        self.assertEqual(d["preflight_status"], "wrong_host")


if __name__ == "__main__":
    unittest.main()
