"""Tests for umh.signal.event_bus — reactive pub/sub coordination."""

from __future__ import annotations

import ast
import sys
import threading
import time

sys.path.insert(0, "/opt/OS")

import pytest

from umh.signal.event_bus import (
    Event,
    EventBus,
    EventLogger,
    EventRegistry,
    EventResult,
    NullLogger,
)


# ── Import boundary ─────────────────────────────────────────────


class TestImportBoundary:
    def test_no_forbidden_imports(self):
        with open("umh/signal/event_bus.py") as f:
            tree = ast.parse(f.read())
        forbidden = {"eos", "core", "services", "scripts"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root not in forbidden, f"import {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                assert root not in forbidden, f"from {node.module}"


# ── Event dataclass ──────────────────────────────────────────────


class TestEvent:
    def test_auto_timestamp(self):
        e = Event(event_type="test", payload={"key": "val"})
        assert e.timestamp != ""
        assert "T" in e.timestamp

    def test_explicit_timestamp(self):
        e = Event(event_type="test", payload={}, timestamp="2026-01-01T00:00:00")
        assert e.timestamp == "2026-01-01T00:00:00"


# ── EventResult ──────────────────────────────────────────────────


class TestEventResult:
    def test_defaults(self):
        r = EventResult(event_type="test", handlers_called=0)
        assert r.results == []
        assert r.errors == []
        assert r.logged is False


# ── Subscribe/Publish ────────────────────────────────────────────


class TestPubSub:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe("ping", lambda p: received.append(p))
        result = bus.publish("ping", {"n": 1})
        assert result.handlers_called == 1
        assert len(received) == 1
        assert received[0]["n"] == 1

    def test_multiple_handlers(self):
        bus = EventBus()
        calls = []
        bus.subscribe("e", lambda p: calls.append("a"))
        bus.subscribe("e", lambda p: calls.append("b"))
        result = bus.publish("e", {})
        assert result.handlers_called == 2
        assert calls == ["a", "b"]

    def test_no_handlers_returns_zero(self):
        bus = EventBus()
        result = bus.publish("nothing", {})
        assert result.handlers_called == 0
        assert result.results == []

    def test_handler_error_captured(self):
        bus = EventBus()

        def bad_handler(p):
            raise ValueError("boom")

        bus.subscribe("fail", bad_handler)
        result = bus.publish("fail", {})
        assert result.handlers_called == 1
        assert len(result.errors) == 1
        assert "boom" in result.errors[0]

    def test_handler_error_does_not_stop_others(self):
        bus = EventBus()
        calls = []

        def bad(p):
            raise RuntimeError("fail")

        def good(p):
            calls.append("ok")

        bus.subscribe("e", bad)
        bus.subscribe("e", good)
        result = bus.publish("e", {})
        assert len(calls) == 1
        assert len(result.errors) == 1
        assert len(result.results) == 1


# ── Unsubscribe ──────────────────────────────────────────────────


class TestUnsubscribe:
    def test_remove_handler(self):
        bus = EventBus()
        handler = lambda p: None
        bus.subscribe("e", handler)
        assert bus.handler_count("e") == 1
        assert bus.unsubscribe("e", handler) is True
        assert bus.handler_count("e") == 0

    def test_remove_nonexistent(self):
        bus = EventBus()
        assert bus.unsubscribe("e", lambda p: None) is False


# ── Allowed types ────────────────────────────────────────────────


class TestAllowedTypes:
    def test_rejects_unknown_type(self):
        bus = EventBus(allowed_types=frozenset({"ping", "pong"}))
        with pytest.raises(ValueError, match="unknown event type"):
            bus.subscribe("invalid", lambda p: None)

    def test_allows_known_type(self):
        bus = EventBus(allowed_types=frozenset({"ping"}))
        bus.subscribe("ping", lambda p: None)
        assert bus.handler_count("ping") == 1

    def test_no_restriction_when_none(self):
        bus = EventBus()
        bus.subscribe("anything", lambda p: None)
        assert bus.handler_count("anything") == 1


# ── Logger protocol ──────────────────────────────────────────────


class RecordingLogger:
    def __init__(self):
        self.events = []

    def log_event(self, event_type, payload, handled_by):
        self.events.append(
            {
                "event_type": event_type,
                "payload": payload,
                "handled_by": handled_by,
            }
        )


class TestLogger:
    def test_null_logger_no_crash(self):
        logger = NullLogger()
        logger.log_event("test", {}, ["h1"])

    def test_custom_logger_receives_events(self):
        logger = RecordingLogger()
        bus = EventBus(logger=logger)
        bus.subscribe("e", lambda p: "ok")
        bus.publish("e", {"x": 1})
        assert len(logger.events) == 1
        assert logger.events[0]["event_type"] == "e"
        assert "x" in logger.events[0]["payload"]

    def test_logged_flag(self):
        logger = RecordingLogger()
        bus = EventBus(logger=logger)
        result = bus.publish("e", {})
        assert result.logged is True

    def test_not_logged_without_logger(self):
        bus = EventBus()
        result = bus.publish("e", {})
        assert result.logged is False

    def test_protocol_compliance(self):
        assert isinstance(RecordingLogger(), EventLogger)
        assert isinstance(NullLogger(), EventLogger)


# ── Async publish ────────────────────────────────────────────────


class TestAsyncPublish:
    def test_fires_handler_in_background(self):
        bus = EventBus()
        received = []
        bus.subscribe("async_test", lambda p: received.append(p["v"]))
        bus.publish_async("async_test", {"v": 42})
        time.sleep(0.1)
        assert received == [42]


# ── Metadata ─────────────────────────────────────────────────────


class TestMetadata:
    def test_registered_types(self):
        bus = EventBus()
        bus.subscribe("b", lambda p: None)
        bus.subscribe("a", lambda p: None)
        assert bus.registered_types == ["a", "b"]

    def test_handler_count(self):
        bus = EventBus()
        bus.subscribe("e", lambda p: None)
        bus.subscribe("e", lambda p: None)
        assert bus.handler_count("e") == 2
        assert bus.handler_count("other") == 0

    def test_clear(self):
        bus = EventBus()
        bus.subscribe("a", lambda p: None)
        bus.subscribe("b", lambda p: None)
        bus.clear()
        assert bus.registered_types == []
        assert bus.handler_count("a") == 0


# ── EventRegistry — bulk handler wiring ─────────────────────────


class TestEventRegistry:
    def test_add_and_register(self):
        bus = EventBus()
        reg = EventRegistry(bus)
        reg.add("ping", lambda p: "pong")
        reg.add("tick", lambda p: "tock")
        count = reg.register_all()
        assert count == 2
        assert bus.handler_count("ping") == 1
        assert bus.handler_count("tick") == 1

    def test_chaining(self):
        bus = EventBus()
        reg = EventRegistry(bus)
        result = reg.add("a", lambda p: None).add("b", lambda p: None)
        assert result is reg
        assert reg.pending == 2

    def test_handlers_fire_after_registration(self):
        bus = EventBus()
        received = []
        reg = EventRegistry(bus)
        reg.add("event", lambda p: received.append(p["v"]))
        reg.register_all()
        bus.publish("event", {"v": 42})
        assert received == [42]

    def test_empty_registry(self):
        bus = EventBus()
        reg = EventRegistry(bus)
        assert reg.register_all() == 0
        assert reg.pending == 0

    def test_multiple_handlers_same_type(self):
        bus = EventBus()
        reg = EventRegistry(bus)
        reg.add("e", lambda p: "first")
        reg.add("e", lambda p: "second")
        reg.register_all()
        result = bus.publish("e", {})
        assert result.handlers_called == 2
        assert result.results == ["first", "second"]
