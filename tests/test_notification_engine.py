"""Tests for substrate.sockets.notification_engine."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from substrate.sockets.notification_engine import (
    Notification,
    NotificationChannel,
    NotificationEngine,
    NotificationPriority,
    NotificationResult,
    get_notification_engine,
)


def test_engine_starts_with_no_channels():
    engine = NotificationEngine()
    assert engine.available_channels == []


def test_register_sync_channel():
    engine = NotificationEngine()
    engine.register_channel(
        NotificationChannel.DISCORD,
        lambda **kw: True,
    )
    assert "discord" in engine.available_channels


def test_register_async_channel():
    engine = NotificationEngine()

    async def handler(**kw):
        return True

    engine.register_async_channel(NotificationChannel.EMAIL, handler)
    assert "email" in engine.available_channels


def test_send_success():
    engine = NotificationEngine()
    engine.register_channel(NotificationChannel.DISCORD, lambda **kw: True)

    note = Notification(
        title="Test",
        body="Hello",
        channel_preference=[NotificationChannel.DISCORD],
    )
    result = engine.send(note)
    assert result.sent is True
    assert result.channel == NotificationChannel.DISCORD


def test_send_fallback_on_failure():
    engine = NotificationEngine()
    engine.register_channel(NotificationChannel.DISCORD, lambda **kw: False)
    engine.register_channel(NotificationChannel.EMAIL, lambda **kw: True)

    note = Notification(
        title="Test",
        body="Fallback",
        channel_preference=[NotificationChannel.DISCORD, NotificationChannel.EMAIL],
    )
    result = engine.send(note)
    assert result.sent is True
    assert result.channel == NotificationChannel.EMAIL


def test_send_all_fail():
    engine = NotificationEngine()
    engine.register_channel(NotificationChannel.DISCORD, lambda **kw: False)

    note = Notification(
        title="Test",
        body="Fail",
        channel_preference=[NotificationChannel.DISCORD],
    )
    result = engine.send(note)
    assert result.sent is False
    assert "all channels failed" in result.error


def test_send_no_handler():
    engine = NotificationEngine()
    note = Notification(
        title="Test",
        body="No handler",
        channel_preference=[NotificationChannel.SMS],
    )
    result = engine.send(note)
    assert result.sent is False
    assert any("no handler" in a for a in result.attempts)


def test_send_exception_in_handler():
    def bad_handler(**kw):
        raise RuntimeError("boom")

    engine = NotificationEngine()
    engine.register_channel(NotificationChannel.PUSH, bad_handler)

    note = Notification(
        title="Test",
        body="Boom",
        channel_preference=[NotificationChannel.PUSH],
    )
    result = engine.send(note)
    assert result.sent is False
    assert any("boom" in a for a in result.attempts)


def test_default_channels_critical():
    engine = NotificationEngine()
    channels = engine._default_channels(NotificationPriority.CRITICAL)
    assert channels[0] == NotificationChannel.COCKPIT
    assert len(channels) == 5


def test_default_channels_low():
    engine = NotificationEngine()
    channels = engine._default_channels(NotificationPriority.LOW)
    assert len(channels) == 2


def test_history_tracking():
    engine = NotificationEngine()
    engine.register_channel(NotificationChannel.COCKPIT, lambda **kw: True)

    for i in range(3):
        engine.send(Notification(title=f"N{i}", body="body"))

    history = engine.recent_history(limit=10)
    assert len(history) == 3
    assert history[0]["title"] == "N2"


def test_stats():
    engine = NotificationEngine()
    engine.register_channel(NotificationChannel.COCKPIT, lambda **kw: True)
    engine.register_channel(NotificationChannel.DISCORD, lambda **kw: False)

    engine.send(
        Notification(title="OK", body="b", channel_preference=[NotificationChannel.COCKPIT])
    )
    engine.send(
        Notification(title="Fail", body="b", channel_preference=[NotificationChannel.DISCORD])
    )

    stats = engine.stats
    assert stats["total"] == 2
    assert stats["sent"] == 1
    assert stats["failed"] == 1


def test_history_cap():
    engine = NotificationEngine()
    engine._max_history = 5
    engine.register_channel(NotificationChannel.COCKPIT, lambda **kw: True)

    for i in range(10):
        engine.send(Notification(title=f"N{i}", body="b"))

    assert len(engine._history) == 5
    assert engine._history[0]["title"] == "N5"


def test_singleton():
    e1 = get_notification_engine()
    e2 = get_notification_engine()
    assert e1 is e2


def test_notification_defaults():
    note = Notification(title="T", body="B")
    assert note.priority == NotificationPriority.NORMAL
    assert note.channel_preference == []
    assert note.source == ""
    assert note.target_user == ""


def test_result_defaults():
    result = NotificationResult(sent=False)
    assert result.channel is None
    assert result.error == ""
    assert result.attempts == []


import asyncio


def test_send_async_success():
    engine = NotificationEngine()

    async def async_handler(**kw):
        return True

    engine.register_async_channel(NotificationChannel.COCKPIT, async_handler)

    note = Notification(
        title="Async", body="test", channel_preference=[NotificationChannel.COCKPIT]
    )
    result = asyncio.run(engine.send_async(note))
    assert result.sent is True
    assert result.channel == NotificationChannel.COCKPIT


def test_send_async_falls_back_to_sync():
    engine = NotificationEngine()
    engine.register_channel(NotificationChannel.DISCORD, lambda **kw: True)

    note = Notification(
        title="Sync fallback", body="test", channel_preference=[NotificationChannel.DISCORD]
    )
    result = asyncio.run(engine.send_async(note))
    assert result.sent is True
