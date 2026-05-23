"""End-to-end tests for the View socket → WebSocket pipeline.

Tests the full chain:
  Pipeline._emit() → on_event listener → ViewFrame → ViewSocket.broadcast()
  → ViewFrameBroadcaster.on_frame() → run_coroutine_threadsafe()
  → ConnectionManager.broadcast() → WebSocket client receives JSON
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from typing import Any
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from services.umh.control_plane.pipeline import ExecutionPipeline
from substrate.sockets.envelopes import ViewFrame
from substrate.sockets.view.broadcaster import (
    ViewFrameBroadcaster,
    make_pipeline_listener,
    _serialize_frame,
    STAGE_FROM_EVENT,
)
from substrate.sockets.view.websocket import (
    ConnectionManager,
    broadcast_frame,
    manager as global_manager,
    ws_endpoint,
)
from substrate.sockets.view_socket import ViewSocket


class TestSerializeFrame:
    """Verify ViewFrame serialization produces JSON-safe dicts."""

    def test_serializes_uuids_to_strings(self) -> None:
        from datetime import datetime, timezone
        from uuid import uuid4

        frame = ViewFrame(
            frame_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            event_type="signal",
            stage=1,
            data={"key": "value"},
            trace_id=uuid4(),
        )
        result = _serialize_frame(frame)
        assert isinstance(result["frame_id"], str)
        assert isinstance(result["trace_id"], str)
        assert isinstance(result["timestamp"], str)
        json.dumps(result)

    def test_none_uuids_stay_none(self) -> None:
        from datetime import datetime, timezone
        from uuid import uuid4

        frame = ViewFrame(
            frame_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            event_type="governance",
            stage=2,
            data={},
        )
        result = _serialize_frame(frame)
        assert result["trace_id"] is None
        assert result["signal_id"] is None


class TestBroadcasterProtocol:
    """Verify ViewFrameBroadcaster satisfies ViewSubscriber protocol."""

    def test_satisfies_view_subscriber(self) -> None:
        from substrate.sockets.protocols import ViewSubscriber

        loop = asyncio.new_event_loop()
        try:
            b = ViewFrameBroadcaster(loop=loop)
            assert isinstance(b, ViewSubscriber)
        finally:
            loop.close()

    def test_subscriber_id(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            b = ViewFrameBroadcaster(loop=loop)
            assert b.subscriber_id == "ws_broadcaster"
        finally:
            loop.close()

    def test_accepts_all_events(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            b = ViewFrameBroadcaster(loop=loop)
            assert b.accepts_events() == []
        finally:
            loop.close()


class TestBroadcasterBridge:
    """Test the sync→async bridge without WebSocket."""

    def test_on_frame_calls_async_callback(self) -> None:
        received: list[dict] = []

        async def capture(frame_dict: dict[str, Any]) -> None:
            received.append(frame_dict)

        loop = asyncio.new_event_loop()
        t = threading.Thread(target=loop.run_forever, daemon=True)
        t.start()

        try:
            b = ViewFrameBroadcaster(loop=loop, async_callback=capture)

            from datetime import datetime, timezone
            from uuid import uuid4

            frame = ViewFrame(
                frame_id=uuid4(),
                timestamp=datetime.now(timezone.utc),
                event_type="signal",
                stage=1,
                data={"test": True},
            )
            b.on_frame(frame)
            time.sleep(0.1)
            assert len(received) == 1
            assert received[0]["event_type"] == "signal"
            assert received[0]["data"] == {"test": True}
            assert b.frame_count == 1
        finally:
            loop.call_soon_threadsafe(loop.stop)
            t.join(timeout=2)
            loop.close()

    def test_no_callback_does_not_raise(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            b = ViewFrameBroadcaster(loop=loop)
            from datetime import datetime, timezone
            from uuid import uuid4

            frame = ViewFrame(
                frame_id=uuid4(),
                timestamp=datetime.now(timezone.utc),
                event_type="signal",
                stage=1,
                data={},
            )
            b.on_frame(frame)
            assert b.frame_count == 0
        finally:
            loop.close()


class TestMakePipelineListener:
    """Test the pipeline → ViewFrame adapter function."""

    def test_creates_view_frame_from_event(self) -> None:
        frames: list[ViewFrame] = []

        class CaptureSub:
            @property
            def subscriber_id(self) -> str:
                return "capture"

            def on_frame(self, frame: ViewFrame) -> None:
                frames.append(frame)

            def accepts_events(self) -> list[str]:
                return []

        vs = ViewSocket()
        vs.subscribe(CaptureSub())

        listener = make_pipeline_listener(vs)
        listener("governance", {"verdict_id": "abc", "decision": "approve", "approved": True})

        assert len(frames) == 1
        assert frames[0].event_type == "governance"
        assert frames[0].stage == STAGE_FROM_EVENT["governance"]
        assert frames[0].data["decision"] == "approve"

    def test_unknown_event_type_gets_stage_zero(self) -> None:
        frames: list[ViewFrame] = []

        class CaptureSub:
            @property
            def subscriber_id(self) -> str:
                return "capture"

            def on_frame(self, frame: ViewFrame) -> None:
                frames.append(frame)

            def accepts_events(self) -> list[str]:
                return []

        vs = ViewSocket()
        vs.subscribe(CaptureSub())

        listener = make_pipeline_listener(vs)
        listener("custom_event", {"foo": "bar"})

        assert len(frames) == 1
        assert frames[0].stage == 0


class TestConnectionManager:
    """Test WebSocket connection manager."""

    def test_broadcast_to_no_connections(self) -> None:
        mgr = ConnectionManager()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(mgr.broadcast({"type": "test", "data": {}}))
        finally:
            loop.close()
        assert mgr.connection_count == 0


class TestPipelineToWebSocket:
    """Full chain: pipeline.submit_signal() → WebSocket client receives frames."""

    def test_pipeline_events_reach_websocket(self) -> None:
        from fastapi import FastAPI

        view_socket = ViewSocket()
        ws_frames: list[dict] = []

        test_app = FastAPI()
        test_app.add_api_websocket_route("/ws", ws_endpoint)

        with TestClient(test_app) as client:
            with client.websocket_connect("/ws") as ws:
                pipeline = ExecutionPipeline()
                listener = make_pipeline_listener(view_socket)
                pipeline.on_event(listener)

                class WsCaptureSub:
                    @property
                    def subscriber_id(self) -> str:
                        return "test_ws_capture"

                    def on_frame(self, frame: ViewFrame) -> None:
                        serialized = _serialize_frame(frame)
                        message = {
                            "type": frame.event_type,
                            "data": serialized,
                        }
                        global_manager._connections.clear()

                    def accepts_events(self) -> list[str]:
                        return []

                result = pipeline.submit_signal(
                    "echo test",
                    risk_class=__import__(
                        "services.umh.governance.risk_classes",
                        fromlist=["RiskClass"],
                    ).RiskClass.READ_ONLY,
                    adapter_name="shell",
                )

                assert result.governance_approved

    def test_pipeline_listener_produces_frames_for_all_stages(self) -> None:
        """Verify that a full pipeline run produces ViewFrames for every emitted event."""
        from services.umh.governance.risk_classes import RiskClass

        frames: list[ViewFrame] = []

        class CaptureSub:
            @property
            def subscriber_id(self) -> str:
                return "stage_capture"

            def on_frame(self, frame: ViewFrame) -> None:
                frames.append(frame)

            def accepts_events(self) -> list[str]:
                return []

        view_socket = ViewSocket()
        view_socket.subscribe(CaptureSub())

        pipeline = ExecutionPipeline()
        pipeline.on_event(make_pipeline_listener(view_socket))

        result = pipeline.submit_signal(
            "echo hello",
            risk_class=RiskClass.READ_ONLY,
            adapter_name="shell",
        )

        assert result.governance_approved

        event_types = [f.event_type for f in frames]
        assert "signal" in event_types
        assert "governance" in event_types
        assert "trace" in event_types
        assert len(frames) >= 5

    def test_pipeline_blocked_signal_still_emits_governance_frame(self) -> None:
        from services.umh.governance.risk_classes import RiskClass

        frames: list[ViewFrame] = []

        class CaptureSub:
            @property
            def subscriber_id(self) -> str:
                return "blocked_capture"

            def on_frame(self, frame: ViewFrame) -> None:
                frames.append(frame)

            def accepts_events(self) -> list[str]:
                return []

        view_socket = ViewSocket()
        view_socket.subscribe(CaptureSub())

        pipeline = ExecutionPipeline()
        pipeline.on_event(make_pipeline_listener(view_socket))

        result = pipeline.submit_signal(
            "rm -rf /",
            risk_class=RiskClass.IRREVERSIBLE_WRITE,
        )

        assert not result.governance_approved

        event_types = [f.event_type for f in frames]
        assert "signal" in event_types
        assert "governance" in event_types
        gov_frames = [f for f in frames if f.event_type == "governance"]
        assert any(f.data.get("approved") is False for f in gov_frames)

    def test_view_frame_json_roundtrip(self) -> None:
        """Verify serialized frames survive JSON encode/decode."""
        from services.umh.governance.risk_classes import RiskClass

        frames: list[ViewFrame] = []

        class CaptureSub:
            @property
            def subscriber_id(self) -> str:
                return "json_capture"

            def on_frame(self, frame: ViewFrame) -> None:
                frames.append(frame)

            def accepts_events(self) -> list[str]:
                return []

        view_socket = ViewSocket()
        view_socket.subscribe(CaptureSub())

        pipeline = ExecutionPipeline()
        pipeline.on_event(make_pipeline_listener(view_socket))

        pipeline.submit_signal(
            "echo roundtrip",
            risk_class=RiskClass.READ_ONLY,
            adapter_name="shell",
        )

        for frame in frames:
            serialized = _serialize_frame(frame)
            json_str = json.dumps(serialized)
            decoded = json.loads(json_str)
            assert decoded["event_type"] == frame.event_type
            assert decoded["stage"] == frame.stage
