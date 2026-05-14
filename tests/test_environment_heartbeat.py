"""Tests for environment_bridge/heartbeat.py — Phase 96.8A."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from execution.environments.heartbeat import (
    WorkerHeartbeat,
    WorkerHeartbeatStatus,
    build_worker_heartbeat,
    heartbeat_is_stale,
    write_heartbeat,
    read_heartbeat,
    summarize_heartbeat,
)


class TestHeartbeatBuilds(unittest.TestCase):
    def test_build_returns_heartbeat(self):
        hb = build_worker_heartbeat()
        self.assertIsInstance(hb, WorkerHeartbeat)
        self.assertEqual(hb.worker_id, "local-windows-worker")
        self.assertEqual(hb.status, WorkerHeartbeatStatus.ONLINE)

    def test_has_capabilities(self):
        hb = build_worker_heartbeat()
        self.assertTrue(len(hb.capabilities) > 0)
        self.assertIn("local_windows_gui", hb.capabilities)


class TestFreshHeartbeatOnline(unittest.TestCase):
    def test_fresh_heartbeat_not_stale(self):
        hb = build_worker_heartbeat()
        self.assertFalse(heartbeat_is_stale(hb))


class TestStaleHeartbeatDetected(unittest.TestCase):
    def test_old_heartbeat_is_stale(self):
        hb = build_worker_heartbeat()
        old_time = datetime.now(timezone.utc) - timedelta(seconds=120)
        hb.last_seen_at = old_time.isoformat()
        self.assertTrue(heartbeat_is_stale(hb, threshold_seconds=60))

    def test_empty_last_seen_is_stale(self):
        hb = WorkerHeartbeat()
        self.assertTrue(heartbeat_is_stale(hb))


class TestWriteReadHeartbeat(unittest.TestCase):
    def test_write_and_read_roundtrip(self):
        hb = build_worker_heartbeat()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "heartbeat.json")
            self.assertTrue(write_heartbeat(path, hb))
            read_back = read_heartbeat(path)
            self.assertIsNotNone(read_back)
            self.assertEqual(read_back.worker_id, hb.worker_id)
            self.assertEqual(read_back.host, hb.host)

    def test_read_nonexistent_returns_none(self):
        self.assertIsNone(read_heartbeat("/nonexistent/heartbeat.json"))


class TestSummarizeHeartbeat(unittest.TestCase):
    def test_summarize_returns_dict(self):
        hb = build_worker_heartbeat()
        s = summarize_heartbeat(hb)
        self.assertIsInstance(s, dict)
        self.assertIn("worker_id", s)
        self.assertIn("status", s)
        self.assertIn("stale", s)
        self.assertFalse(s["stale"])


if __name__ == "__main__":
    unittest.main()
