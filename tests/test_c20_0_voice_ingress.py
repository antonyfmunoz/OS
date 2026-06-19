"""Tests for Campaign 20.0 — Voice Ingress Runtime."""

from __future__ import annotations

import sys
import time
import unittest

sys.path.insert(0, "/opt/OS/.claude/worktrees/c20-voice-operations")

from substrate.workstation.voice_ingress_runtime import (
    ActivationMode,
    VoiceChannelContext,
    VoiceIngressEvent,
    VoiceIngressRuntime,
    VoiceIngressSnapshot,
    VoicePermissionScope,
    VoiceSourceType,
)


class TestVoiceSourceType(unittest.TestCase):
    def test_enum_values(self) -> None:
        assert VoiceSourceType.RIGHT_RAIL.value == "right_rail"
        assert VoiceSourceType.CONFERENCE.value == "conference"
        assert VoiceSourceType.DISCORD.value == "discord"
        assert VoiceSourceType.SYSTEM_AUDIO.value == "system_audio"
        assert VoiceSourceType.AMBIENT.value == "ambient"

    def test_all_members(self) -> None:
        assert len(VoiceSourceType) == 5


class TestActivationMode(unittest.TestCase):
    def test_enum_values(self) -> None:
        assert ActivationMode.PUSH_TO_TALK.value == "push_to_talk"
        assert ActivationMode.WAKE_WORD.value == "wake_word"
        assert ActivationMode.ALWAYS_LISTEN_PASSIVE.value == "always_listen_passive"
        assert ActivationMode.CONFERENCE_LISTENING.value == "conference_listening"
        assert ActivationMode.BROADCAST_TRANSCRIPTION.value == "broadcast_transcription"
        assert ActivationMode.COMMAND_MODE.value == "command_mode"

    def test_all_members(self) -> None:
        assert len(ActivationMode) == 6


class TestVoiceChannelContext(unittest.TestCase):
    def test_enum_values(self) -> None:
        assert VoiceChannelContext.OPERATOR_DIRECT.value == "operator_direct"
        assert VoiceChannelContext.MEETING.value == "meeting"
        assert VoiceChannelContext.BROADCAST.value == "broadcast"
        assert VoiceChannelContext.BACKGROUND.value == "background"
        assert VoiceChannelContext.SYSTEM.value == "system"

    def test_all_members(self) -> None:
        assert len(VoiceChannelContext) == 5


class TestVoicePermissionScope(unittest.TestCase):
    def test_enum_values(self) -> None:
        assert VoicePermissionScope.FULL.value == "full"
        assert VoicePermissionScope.QUERY_ONLY.value == "query_only"
        assert VoicePermissionScope.TRANSCRIBE_ONLY.value == "transcribe_only"
        assert VoicePermissionScope.MONITOR_ONLY.value == "monitor_only"

    def test_all_members(self) -> None:
        assert len(VoicePermissionScope) == 4


class TestVoiceIngressEvent(unittest.TestCase):
    def test_defaults(self) -> None:
        event = VoiceIngressEvent()
        assert event.source_type == "right_rail"
        assert event.device_id == ""
        assert event.activation_mode == ""
        assert event.confidence == 1.0

    def test_to_dict(self) -> None:
        event = VoiceIngressEvent(
            source_type="discord",
            device_id="dev1",
            raw_text="hello",
        )
        d = event.to_dict()
        assert d["source_type"] == "discord"
        assert d["device_id"] == "dev1"
        assert d["raw_text"] == "hello"
        assert "metadata" in d

    def test_custom_metadata(self) -> None:
        event = VoiceIngressEvent(metadata={"guild_id": "123"})
        assert event.metadata["guild_id"] == "123"


class TestVoiceIngressSnapshot(unittest.TestCase):
    def test_defaults(self) -> None:
        snap = VoiceIngressSnapshot()
        assert snap.health == "idle"
        assert snap.active_sources == []
        assert snap.event_counts_by_type == {}

    def test_to_dict(self) -> None:
        snap = VoiceIngressSnapshot(health="active", generated_at=1.0)
        d = snap.to_dict()
        assert d["health"] == "active"
        assert d["generated_at"] == 1.0


class TestVoiceIngressRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = VoiceIngressRuntime()

    def test_classify_right_rail_default(self) -> None:
        event = self.runtime.classify({"text": "what is blocked?"})
        assert event.source_type == "right_rail"
        assert event.activation_mode == "push_to_talk"
        assert event.channel_context == "operator_direct"
        assert event.permission_scope == "full"

    def test_classify_explicit_source_type(self) -> None:
        event = self.runtime.classify({
            "source_type": "discord",
            "text": "hello",
        })
        assert event.source_type == "discord"

    def test_classify_explicit_source_field(self) -> None:
        event = self.runtime.classify({
            "source": "conference",
            "text": "meeting notes",
        })
        assert event.source_type == "conference"

    def test_classify_discord_regex(self) -> None:
        event = self.runtime.classify({
            "text": "hello",
            "guild_id": "12345",
            "voice_channel": "general",
        })
        assert event.source_type == "discord"

    def test_classify_conference_regex(self) -> None:
        event = self.runtime.classify({
            "text": "meeting update",
            "room": "standup",
            "livekit": True,
        })
        assert event.source_type == "conference"

    def test_classify_system_audio_regex(self) -> None:
        event = self.runtime.classify({
            "text": "stream content",
            "system_audio": True,
            "loopback": True,
        })
        assert event.source_type == "system_audio"

    def test_classify_ambient_regex(self) -> None:
        event = self.runtime.classify({
            "text": "hey there",
            "ambient": True,
            "wake_word": "jarvis",
        })
        assert event.source_type == "ambient"

    def test_activation_mode_wake_word(self) -> None:
        event = self.runtime.classify({
            "text": "status",
            "wake_word": "jarvis",
        })
        assert event.activation_mode == "wake_word"

    def test_activation_mode_command(self) -> None:
        event = self.runtime.classify({
            "text": "deploy",
            "command_mode": True,
        })
        assert event.activation_mode == "command_mode"

    def test_activation_mode_explicit(self) -> None:
        event = self.runtime.classify({
            "text": "test",
            "activation_mode": "conference_listening",
        })
        assert event.activation_mode == "conference_listening"

    def test_activation_mode_default_by_source(self) -> None:
        event = self.runtime.classify({
            "source_type": "conference",
            "text": "notes",
        })
        assert event.activation_mode == "conference_listening"

    def test_channel_context_conference(self) -> None:
        event = self.runtime.classify({
            "source_type": "conference",
            "text": "hello",
        })
        assert event.channel_context == "meeting"

    def test_channel_context_discord_broadcast(self) -> None:
        event = self.runtime.classify({
            "source_type": "discord",
            "text": "broadcast update",
            "broadcast": True,
        })
        assert event.channel_context == "broadcast"

    def test_channel_context_discord_default(self) -> None:
        event = self.runtime.classify({
            "source_type": "discord",
            "text": "hello",
        })
        assert event.channel_context == "meeting"

    def test_channel_context_system_audio(self) -> None:
        event = self.runtime.classify({
            "source_type": "system_audio",
            "text": "capture",
        })
        assert event.channel_context == "background"

    def test_channel_context_ambient(self) -> None:
        event = self.runtime.classify({
            "source_type": "ambient",
            "text": "hey",
        })
        assert event.channel_context == "background"

    def test_channel_context_explicit(self) -> None:
        event = self.runtime.classify({
            "text": "test",
            "channel_context": "system",
        })
        assert event.channel_context == "system"

    def test_permission_scope_right_rail(self) -> None:
        event = self.runtime.classify({
            "source_type": "right_rail",
            "text": "cmd",
        })
        assert event.permission_scope == "full"

    def test_permission_scope_conference(self) -> None:
        event = self.runtime.classify({
            "source_type": "conference",
            "text": "meeting",
        })
        assert event.permission_scope == "transcribe_only"

    def test_permission_scope_discord(self) -> None:
        event = self.runtime.classify({
            "source_type": "discord",
            "text": "msg",
        })
        assert event.permission_scope == "transcribe_only"

    def test_permission_scope_system_audio(self) -> None:
        event = self.runtime.classify({
            "source_type": "system_audio",
            "text": "audio",
        })
        assert event.permission_scope == "monitor_only"

    def test_permission_scope_ambient(self) -> None:
        event = self.runtime.classify({
            "source_type": "ambient",
            "text": "hey",
        })
        assert event.permission_scope == "query_only"

    def test_raw_text_from_transcript_field(self) -> None:
        event = self.runtime.classify({
            "transcript": "transcribed text",
        })
        assert event.raw_text == "transcribed text"

    def test_device_id_passthrough(self) -> None:
        event = self.runtime.classify({
            "device_id": "beast_pc",
            "text": "hello",
        })
        assert event.device_id == "beast_pc"

    def test_speaker_id_from_user_id(self) -> None:
        event = self.runtime.classify({
            "user_id": "antony",
            "text": "hello",
        })
        assert event.speaker_id == "antony"

    def test_confidence_passthrough(self) -> None:
        event = self.runtime.classify({
            "text": "hello",
            "confidence": 0.85,
        })
        assert event.confidence == 0.85

    def test_timestamp_passthrough(self) -> None:
        ts = time.time()
        event = self.runtime.classify({
            "text": "hello",
            "timestamp": ts,
        })
        assert event.timestamp == ts

    def test_active_sources_empty(self) -> None:
        runtime = VoiceIngressRuntime()
        assert runtime.active_sources() == []

    def test_active_sources_after_classify(self) -> None:
        runtime = VoiceIngressRuntime()
        runtime.classify({"text": "hello", "source_type": "right_rail"})
        sources = runtime.active_sources()
        assert len(sources) >= 1
        assert sources[0]["source_type"] == "right_rail"

    def test_snapshot_idle(self) -> None:
        runtime = VoiceIngressRuntime()
        snap = runtime.snapshot()
        assert snap.health == "idle"
        assert snap.generated_at > 0

    def test_snapshot_active(self) -> None:
        runtime = VoiceIngressRuntime()
        runtime.classify({"text": "hello"})
        snap = runtime.snapshot()
        assert snap.health == "active"
        assert len(snap.recent_events) >= 1

    def test_summary(self) -> None:
        runtime = VoiceIngressRuntime()
        runtime.classify({"text": "hello"})
        s = runtime.summary()
        assert "health" in s
        assert "total_events" in s
        assert s["total_events"] >= 1

    def test_graceful_degradation_no_deps(self) -> None:
        runtime = VoiceIngressRuntime(
            presence_runtime=None,
            voice_route_resolver=None,
            session_runtime=None,
        )
        event = runtime.classify({"text": "test"})
        assert event.raw_text == "test"


if __name__ == "__main__":
    unittest.main()
