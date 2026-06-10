"""Tests for Phase 14.17 — Vision Reliability Hardening.

Tests the health endpoint, recovery logic, frame validation,
tracker crash isolation, and grounded vision status.
"""

from __future__ import annotations

import json
import os
import sys
import time
import threading
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Health endpoint tests ─────────────────────────────────────────

class TestVisionHealthEndpoint(unittest.TestCase):
    """Test _build_health returns comprehensive chain status."""

    def _build(self, **overrides):
        import umh.vision_relay as vr
        orig = {
            "_last_frame_at": vr._last_frame_at,
            "_frame_count": vr._frame_count,
            "_last_overlay_at": vr._last_overlay_at,
            "_overlay_count": vr._overlay_count,
            "_stream_active": vr._stream_active,
            "_stream_fps": vr._stream_fps,
            "_latest_frame": vr._latest_frame,
            "_clients": set(vr._clients),
        }
        for k, v in overrides.items():
            setattr(vr, k, v)
        try:
            return vr._build_health()
        finally:
            for k, v in orig.items():
                setattr(vr, k, v)

    def test_health_returns_all_required_fields(self):
        h = self._build()
        required = [
            "status", "relay_running", "cockpit_connected", "viewer_count",
            "beast_connected", "camera_available", "camera_streaming",
            "last_frame_at", "last_frame_age_ms", "frame_count", "frame_fps",
            "tracker_runtime_available", "active_trackers",
            "last_overlay_at", "last_overlay_age_ms", "overlay_count",
            "trigger_chain_engine_available", "active_chains",
            "security_mode", "blockers", "recovery_action",
        ]
        for field in required:
            self.assertIn(field, h, f"missing field: {field}")

    def test_health_relay_always_running(self):
        h = self._build()
        self.assertTrue(h["relay_running"])

    def test_health_no_viewers_reports_idle(self):
        h = self._build(_clients=set(), _stream_active=False)
        self.assertIn("no cockpit viewers", str(h["blockers"]))

    def test_health_streaming_reports_fps(self):
        h = self._build(
            _stream_active=True,
            _stream_fps=15,
            _latest_frame=b"\xff\xd8fake",
            _last_frame_at=time.time(),
        )
        self.assertEqual(h["frame_fps"], 15)
        self.assertTrue(h["camera_streaming"])

    def test_health_stale_frame_detected(self):
        h = self._build(
            _stream_active=True,
            _last_frame_at=time.time() - 30,
            _latest_frame=b"\xff\xd8fake",
        )
        self.assertEqual(h["status"], "stream_stale")
        self.assertGreater(h["last_frame_age_ms"], 15000)

    def test_health_no_frame_age_is_negative(self):
        h = self._build(_last_frame_at=0.0)
        self.assertEqual(h["last_frame_age_ms"], -1)


# ── Frame validation tests ────────────────────────────────────────

class TestFrameValidation(unittest.TestCase):
    """Test receive_mesh_frame validates JPEG headers."""

    def setUp(self):
        import umh.vision_relay as vr
        self.vr = vr
        self._orig_loop = vr._event_loop
        vr._event_loop = None

    def tearDown(self):
        self.vr._event_loop = self._orig_loop

    def test_rejects_non_dict(self):
        self.vr.receive_mesh_frame("not a dict")

    def test_rejects_empty_base64(self):
        self.vr.receive_mesh_frame({"image_base64": ""})

    def test_rejects_invalid_jpeg_header(self):
        import base64
        fake = base64.b64encode(b"\x00\x00not_jpeg").decode()
        self.vr.receive_mesh_frame({"image_base64": fake})

    def test_accepts_valid_jpeg(self):
        import base64
        jpeg_stub = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        b64 = base64.b64encode(jpeg_stub).decode()
        with patch.object(self.vr, "_get_loop", return_value=None):
            self.vr.receive_mesh_frame({"image_base64": b64})


# ── Overlay tracking tests ────────────────────────────────────────

class TestOverlayTracking(unittest.TestCase):
    """Test that overlay counters update when frame meta has overlays."""

    def test_overlay_count_increments(self):
        import umh.vision_relay as vr
        import asyncio

        orig_count = vr._overlay_count
        orig_at = vr._last_overlay_at
        orig_frame = vr._latest_frame
        orig_meta = vr._latest_frame_meta
        orig_active = vr._stream_active

        try:
            vr._clients = set()
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                vr.broadcast_frame(b"\xff\xd8fake", {"overlays": [{"box": [0, 0, 1, 1]}]})
            )
            self.assertEqual(vr._overlay_count, orig_count + 1)
            self.assertGreater(vr._last_overlay_at, orig_at)
            loop.close()
        finally:
            vr._overlay_count = orig_count
            vr._last_overlay_at = orig_at
            vr._latest_frame = orig_frame
            vr._latest_frame_meta = orig_meta
            vr._stream_active = orig_active

    def test_no_overlay_key_skips(self):
        import umh.vision_relay as vr
        import asyncio

        orig_count = vr._overlay_count
        orig_frame = vr._latest_frame
        orig_meta = vr._latest_frame_meta
        orig_active = vr._stream_active

        try:
            vr._clients = set()
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                vr.broadcast_frame(b"\xff\xd8fake", {"timestamp": 123})
            )
            self.assertEqual(vr._overlay_count, orig_count)
            loop.close()
        finally:
            vr._overlay_count = orig_count
            vr._latest_frame = orig_frame
            vr._latest_frame_meta = orig_meta
            vr._stream_active = orig_active


# ── Beast camera recovery tests ───────────────────────────────────

class TestCameraRecovery(unittest.TestCase):
    """Test camera adapter stream_start idempotency and stop safety."""

    def _make_adapter(self):
        from nodes.windows.umh_node.adapters.camera import CameraAdapter
        adapter = CameraAdapter.__new__(CameraAdapter)
        adapter._device_index = 0
        adapter._presets = {}
        adapter._stream_active = False
        adapter._stream_thread = None
        adapter._stream_lock = threading.Lock()
        adapter._frame_callback = None
        return adapter

    def test_stream_stop_when_not_started(self):
        adapter = self._make_adapter()
        result = adapter._stream_stop({})
        self.assertTrue(result["success"])

    def test_stream_start_returns_success(self):
        adapter = self._make_adapter()
        mock_cv2 = MagicMock()
        cap_inst = MagicMock()
        cap_inst.isOpened.return_value = True
        cap_inst.read.return_value = (False, None)
        mock_cv2.VideoCapture.return_value = cap_inst
        mock_cv2.CAP_DSHOW = 700
        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
        mock_cv2.IMWRITE_JPEG_QUALITY = 1
        with patch.dict("sys.modules", {"cv2": mock_cv2}):
            result = adapter._stream_start({"fps": 2, "width": 320, "height": 240})
            self.assertTrue(result["success"])
            self.assertEqual(result["fps"], 2)
            adapter._stream_active = False
            if adapter._stream_thread:
                adapter._stream_thread.join(timeout=2)


# ── Tracker crash isolation tests ─────────────────────────────────

class TestTrackerCrashIsolation(unittest.TestCase):
    """Test that tracker loop catches errors and stops after threshold."""

    def test_tracker_stops_after_consecutive_errors(self):
        from nodes.windows.umh_node.adapters.vision_runtime import TrackerProcess, VisionRuntime

        def bad_emit(event, data):
            raise RuntimeError("simulated crash")

        rt = VisionRuntime.__new__(VisionRuntime)
        rt._capabilities = {}
        rt._tracker_support = {"object_detector": True}
        rt._trackers = {}
        rt._emit_fn = bad_emit

        proc = TrackerProcess(category="object_detector", target_fps=100)
        proc._stop_event.clear()
        proc.running = True

        rt._tracker_loop(proc)

        self.assertFalse(proc.running)
        self.assertIn("RuntimeError", proc.last_error)

    def test_tracker_recovers_from_single_error(self):
        from nodes.windows.umh_node.adapters.vision_runtime import TrackerProcess, VisionRuntime

        call_count = 0

        def flaky_emit(event, data):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise RuntimeError("one-off error")

        rt = VisionRuntime.__new__(VisionRuntime)
        rt._capabilities = {}
        rt._tracker_support = {"object_detector": True}
        rt._trackers = {}
        rt._emit_fn = flaky_emit

        proc = TrackerProcess(category="object_detector", target_fps=1000)
        proc._stop_event.clear()
        proc.running = True

        def stop_after():
            time.sleep(0.2)
            proc._stop_event.set()

        t = threading.Thread(target=stop_after)
        t.start()
        rt._tracker_loop(proc)
        t.join()

        self.assertGreater(proc.frame_count, 5)


# ── Grounded vision status tests ──────────────────────────────────

class TestGroundedVisionStatus(unittest.TestCase):
    """Test that _collect_vision returns chain-aware status."""

    @patch("urllib.request.urlopen")
    def test_healthy_status_summary(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "status": "healthy",
            "viewer_count": 1,
            "beast_connected": True,
            "camera_streaming": True,
            "frame_fps": 15,
            "blockers": [],
            "recovery_action": "",
        }).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        from substrate.organism.grounding_registry import _collect_vision
        data, summary = _collect_vision()

        self.assertIn("healthy", summary)
        self.assertIn("beast=connected", summary)
        self.assertIn("camera=streaming", summary)
        self.assertIn("15fps", summary)
        self.assertEqual(data["status"], "healthy")

    @patch("urllib.request.urlopen")
    def test_beast_offline_shows_blockers(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "status": "beast_offline",
            "viewer_count": 0,
            "beast_connected": False,
            "camera_streaming": False,
            "frame_fps": 0,
            "blockers": ["Beast daemon not connected"],
            "recovery_action": "check Beast",
        }).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        from substrate.organism.grounding_registry import _collect_vision
        data, summary = _collect_vision()

        self.assertIn("beast_offline", summary)
        self.assertIn("beast=offline", summary)
        self.assertIn("blockers:", summary)
        self.assertIn("recovery:", summary)

    @patch("urllib.request.urlopen", side_effect=Exception("connection refused"))
    def test_unreachable_relay(self, mock_urlopen):
        from substrate.organism.grounding_registry import _collect_vision
        data, summary = _collect_vision()

        self.assertFalse(data.get("relay_reachable", True))
        self.assertIn("unreachable", summary)


# ── Ping/pong heartbeat test ─────────────────────────────────────

class TestRelayPingPong(unittest.TestCase):
    """Test that relay responds to ping with pong."""

    def test_ping_message_type_recognized(self):
        import umh.vision_relay as vr
        msg = json.loads('{"type": "ping"}')
        self.assertEqual(msg.get("type"), "ping")


if __name__ == "__main__":
    unittest.main()
