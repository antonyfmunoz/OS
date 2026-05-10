"""Tests for environment_bridge/vps_local_bridge.py — Phase 96.8A."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest
from core.environment_bridge.vps_local_bridge import (
    VPSLocalBridge,
    VPSLocalBridgeStatus,
    BridgeMode,
    build_vps_local_bridge,
    evaluate_vps_local_bridge_status,
    bridge_can_dispatch_by_push,
    bridge_can_dispatch_by_pull,
    bridge_requires_manual_bootstrap,
    summarize_vps_local_bridge,
)
from core.environment_bridge.heartbeat import build_worker_heartbeat


class TestBridgeBuilds(unittest.TestCase):
    def test_build_returns_bridge(self):
        b = build_vps_local_bridge()
        self.assertIsInstance(b, VPSLocalBridge)

    def test_primary_mode_is_local_pull(self):
        b = build_vps_local_bridge()
        self.assertEqual(b.primary_mode, BridgeMode.LOCAL_PULL_PRIMARY)


class TestSSHPushOptional(unittest.TestCase):
    def test_ssh_push_when_available(self):
        b = build_vps_local_bridge(ssh_push_available=True)
        self.assertTrue(bridge_can_dispatch_by_push(b))

    def test_no_ssh_push_when_unavailable(self):
        b = build_vps_local_bridge(ssh_push_available=False)
        self.assertFalse(bridge_can_dispatch_by_push(b))


class TestPullAlwaysAvailable(unittest.TestCase):
    def test_pull_always_available(self):
        b = build_vps_local_bridge()
        self.assertTrue(bridge_can_dispatch_by_pull(b))


class TestPushBlockedPullAvailable(unittest.TestCase):
    def test_push_blocked_pull_available(self):
        hb = build_worker_heartbeat()
        b = build_vps_local_bridge(
            worker_heartbeat=hb,
            ssh_push_available=False,
        )
        b = evaluate_vps_local_bridge_status(
            b,
            ssh_reachable=False,
            heartbeat_present=True,
        )
        self.assertEqual(b.status, VPSLocalBridgeStatus.PUSH_BLOCKED_PULL_AVAILABLE)


class TestManualBootstrapRequired(unittest.TestCase):
    def test_no_heartbeat_requires_bootstrap(self):
        b = build_vps_local_bridge()
        b = evaluate_vps_local_bridge_status(
            b,
            ssh_reachable=False,
            heartbeat_present=False,
        )
        self.assertTrue(bridge_requires_manual_bootstrap(b))
        self.assertEqual(b.status, VPSLocalBridgeStatus.PULL_NOT_BOOTSTRAPPED)
        self.assertIn("NO_HEARTBEAT", b.blockers)


class TestReadyWhenAllPresent(unittest.TestCase):
    def test_ready_with_heartbeat_and_ssh(self):
        hb = build_worker_heartbeat()
        b = build_vps_local_bridge(
            worker_heartbeat=hb,
            ssh_push_available=True,
        )
        b = evaluate_vps_local_bridge_status(
            b,
            ssh_reachable=True,
            heartbeat_present=True,
        )
        self.assertEqual(b.status, VPSLocalBridgeStatus.READY)


class TestSummarize(unittest.TestCase):
    def test_summarize_returns_dict(self):
        b = build_vps_local_bridge()
        s = summarize_vps_local_bridge(b)
        self.assertIsInstance(s, dict)
        self.assertIn("primary_mode", s)
        self.assertIn("can_push", s)
        self.assertIn("can_pull", s)
        self.assertIn("requires_bootstrap", s)


if __name__ == "__main__":
    unittest.main()
