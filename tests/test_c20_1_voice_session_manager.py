"""Tests for Campaign 20.1 — Voice Session Manager."""

from __future__ import annotations

import sys
import time
import unittest

sys.path.insert(0, "/opt/OS/.claude/worktrees/c20-voice-operations")

from substrate.workstation.voice_ingress_runtime import VoiceIngressEvent
from substrate.workstation.voice_session_manager import (
    ManagedVoiceSession,
    SessionConflictResolution,
    VoiceSessionManager,
    VoiceSessionManagerSnapshot,
    VoiceSessionPriority,
    VoiceSessionType,
)


class TestVoiceSessionType(unittest.TestCase):
    def test_enum_values(self) -> None:
        assert VoiceSessionType.OPERATOR_CHAT.value == "operator_chat"
        assert VoiceSessionType.CONFERENCE_TRANSCRIPTION.value == "conference_transcription"
        assert VoiceSessionType.BROADCAST_CAPTURE.value == "broadcast_capture"
        assert VoiceSessionType.AMBIENT_LISTENING.value == "ambient_listening"
        assert VoiceSessionType.SYSTEM_MONITOR.value == "system_monitor"

    def test_all_members(self) -> None:
        assert len(VoiceSessionType) == 5


class TestVoiceSessionPriority(unittest.TestCase):
    def test_enum_values(self) -> None:
        assert VoiceSessionPriority.COMMAND.value == "command"
        assert VoiceSessionPriority.CONVERSATION.value == "conversation"
        assert VoiceSessionPriority.PASSIVE.value == "passive"

    def test_rank_ordering(self) -> None:
        assert VoiceSessionPriority.COMMAND.rank > VoiceSessionPriority.CONVERSATION.rank
        assert VoiceSessionPriority.CONVERSATION.rank > VoiceSessionPriority.PASSIVE.rank

    def test_rank_values(self) -> None:
        assert VoiceSessionPriority.COMMAND.rank == 3
        assert VoiceSessionPriority.CONVERSATION.rank == 2
        assert VoiceSessionPriority.PASSIVE.rank == 1


class TestManagedVoiceSession(unittest.TestCase):
    def test_defaults(self) -> None:
        s = ManagedVoiceSession()
        assert s.session_id == ""
        assert s.session_type == "operator_chat"
        assert s.priority == "conversation"
        assert s.status == "active"
        assert s.turn_count == 0

    def test_to_dict(self) -> None:
        s = ManagedVoiceSession(
            session_id="test-1",
            session_type="conference_transcription",
            source_type="conference",
        )
        d = s.to_dict()
        assert d["session_id"] == "test-1"
        assert d["session_type"] == "conference_transcription"
        assert d["source_type"] == "conference"
        assert "speaker_ids" in d
        assert "metadata" in d


class TestSessionConflictResolution(unittest.TestCase):
    def test_defaults(self) -> None:
        r = SessionConflictResolution()
        assert r.resolution == ""
        assert r.winner_id == ""

    def test_to_dict(self) -> None:
        r = SessionConflictResolution(
            resolution="priority_override",
            winner_id="s1",
            demoted_ids=["s2"],
        )
        d = r.to_dict()
        assert d["resolution"] == "priority_override"
        assert d["winner_id"] == "s1"
        assert d["demoted_ids"] == ["s2"]


class TestVoiceSessionManagerSnapshot(unittest.TestCase):
    def test_defaults(self) -> None:
        snap = VoiceSessionManagerSnapshot()
        assert snap.total_sessions == 0
        assert snap.conflict_count == 0

    def test_to_dict(self) -> None:
        snap = VoiceSessionManagerSnapshot(
            total_sessions=5,
            conflict_count=1,
            generated_at=1.0,
        )
        d = snap.to_dict()
        assert d["total_sessions"] == 5
        assert d["conflict_count"] == 1


class TestVoiceSessionManagerStartSession(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mgr = VoiceSessionManager()

    def test_start_from_right_rail(self) -> None:
        event = VoiceIngressEvent(source_type="right_rail")
        session = self.mgr.start_session(event)
        assert session.session_type == "operator_chat"
        assert session.status == "active"
        assert session.session_id.startswith("vms_")

    def test_start_from_conference(self) -> None:
        event = VoiceIngressEvent(source_type="conference")
        session = self.mgr.start_session(event)
        assert session.session_type == "conference_transcription"
        assert session.priority == "conversation"

    def test_start_from_discord(self) -> None:
        event = VoiceIngressEvent(source_type="discord")
        session = self.mgr.start_session(event)
        assert session.session_type == "broadcast_capture"
        assert session.priority == "passive"

    def test_start_from_system_audio(self) -> None:
        event = VoiceIngressEvent(source_type="system_audio")
        session = self.mgr.start_session(event)
        assert session.session_type == "system_monitor"
        assert session.priority == "passive"

    def test_start_from_ambient(self) -> None:
        event = VoiceIngressEvent(source_type="ambient")
        session = self.mgr.start_session(event)
        assert session.session_type == "ambient_listening"
        assert session.priority == "passive"

    def test_command_mode_gets_command_priority(self) -> None:
        event = VoiceIngressEvent(
            source_type="ambient",
            activation_mode="command_mode",
        )
        session = self.mgr.start_session(event)
        assert session.priority == "command"

    def test_push_to_talk_gets_command_priority(self) -> None:
        event = VoiceIngressEvent(
            source_type="right_rail",
            activation_mode="push_to_talk",
        )
        session = self.mgr.start_session(event)
        assert session.priority == "command"

    def test_device_id_propagated(self) -> None:
        event = VoiceIngressEvent(
            source_type="right_rail",
            device_id="beast_pc",
        )
        session = self.mgr.start_session(event)
        assert session.device_id == "beast_pc"

    def test_speaker_id_propagated(self) -> None:
        event = VoiceIngressEvent(
            source_type="right_rail",
            speaker_id="antony",
        )
        session = self.mgr.start_session(event)
        assert "antony" in session.speaker_ids

    def test_started_at_set(self) -> None:
        before = time.time()
        event = VoiceIngressEvent(source_type="right_rail")
        session = self.mgr.start_session(event)
        assert session.started_at >= before


class TestVoiceSessionManagerEndSession(unittest.TestCase):
    def test_end_session(self) -> None:
        mgr = VoiceSessionManager()
        event = VoiceIngressEvent(source_type="right_rail")
        session = mgr.start_session(event)
        result = mgr.end_session(session.session_id)
        assert result is True
        assert mgr.get_session(session.session_id).status == "ended"

    def test_end_nonexistent_session(self) -> None:
        mgr = VoiceSessionManager()
        result = mgr.end_session("nonexistent")
        assert result is False


class TestVoiceSessionManagerActiveSessions(unittest.TestCase):
    def test_active_sessions_empty(self) -> None:
        mgr = VoiceSessionManager()
        assert mgr.active_sessions() == []

    def test_active_sessions_after_start(self) -> None:
        mgr = VoiceSessionManager()
        event = VoiceIngressEvent(source_type="right_rail")
        mgr.start_session(event)
        active = mgr.active_sessions()
        assert len(active) == 1

    def test_ended_sessions_not_in_active(self) -> None:
        mgr = VoiceSessionManager()
        event = VoiceIngressEvent(source_type="right_rail")
        session = mgr.start_session(event)
        mgr.end_session(session.session_id)
        assert len(mgr.active_sessions()) == 0


class TestVoiceSessionManagerConflictResolution(unittest.TestCase):
    def test_command_beats_conversation(self) -> None:
        mgr = VoiceSessionManager()
        ev1 = VoiceIngressEvent(source_type="conference")
        s1 = mgr.start_session(ev1)
        ev2 = VoiceIngressEvent(
            source_type="right_rail",
            activation_mode="push_to_talk",
        )
        s2 = mgr.start_session(ev2)
        resolution = mgr.resolve_conflict(s1.session_id, s2.session_id)
        assert resolution.winner_id == s2.session_id
        assert s1.session_id in resolution.demoted_ids

    def test_conversation_beats_passive(self) -> None:
        mgr = VoiceSessionManager()
        ev1 = VoiceIngressEvent(source_type="discord")
        s1 = mgr.start_session(ev1)
        ev2 = VoiceIngressEvent(source_type="conference")
        s2 = mgr.start_session(ev2)
        resolution = mgr.resolve_conflict(s1.session_id, s2.session_id)
        assert resolution.winner_id == s2.session_id

    def test_same_priority_newer_wins(self) -> None:
        mgr = VoiceSessionManager()
        ev1 = VoiceIngressEvent(source_type="discord")
        s1 = mgr.start_session(ev1)
        ev2 = VoiceIngressEvent(source_type="system_audio")
        s2 = mgr.start_session(ev2)
        resolution = mgr.resolve_conflict(s1.session_id, s2.session_id)
        assert resolution.winner_id == s2.session_id

    def test_conflict_not_found(self) -> None:
        mgr = VoiceSessionManager()
        resolution = mgr.resolve_conflict("a", "b")
        assert resolution.resolution == "no_conflict"


class TestVoiceSessionManagerRouteUtterance(unittest.TestCase):
    def test_route_utterance(self) -> None:
        mgr = VoiceSessionManager()
        event = VoiceIngressEvent(source_type="right_rail")
        session = mgr.start_session(event)
        result = mgr.route_utterance(session.session_id, "hello")
        assert result["session_id"] == session.session_id
        assert result["text"] == "hello"
        assert result["turn_count"] == 1

    def test_route_utterance_increments_turn_count(self) -> None:
        mgr = VoiceSessionManager()
        event = VoiceIngressEvent(source_type="right_rail")
        session = mgr.start_session(event)
        mgr.route_utterance(session.session_id, "hello")
        mgr.route_utterance(session.session_id, "world")
        updated = mgr.get_session(session.session_id)
        assert updated.turn_count == 2

    def test_route_utterance_updates_last_activity(self) -> None:
        mgr = VoiceSessionManager()
        event = VoiceIngressEvent(source_type="right_rail")
        session = mgr.start_session(event)
        before = time.time()
        mgr.route_utterance(session.session_id, "test")
        updated = mgr.get_session(session.session_id)
        assert updated.last_activity_at >= before

    def test_route_utterance_not_found(self) -> None:
        mgr = VoiceSessionManager()
        result = mgr.route_utterance("nonexistent", "hello")
        assert result["error"] == "session_not_found"


class TestVoiceSessionManagerSnapshot(unittest.TestCase):
    def test_snapshot_empty(self) -> None:
        mgr = VoiceSessionManager()
        snap = mgr.snapshot()
        assert snap.total_sessions == 0
        assert snap.conflict_count == 0

    def test_snapshot_with_sessions(self) -> None:
        mgr = VoiceSessionManager()
        mgr.start_session(VoiceIngressEvent(source_type="right_rail"))
        mgr.start_session(VoiceIngressEvent(source_type="conference"))
        snap = mgr.snapshot()
        assert snap.total_sessions == 2
        assert len(snap.active_sessions) == 2
        assert "operator_chat" in snap.sessions_by_type
        assert "conference_transcription" in snap.sessions_by_type

    def test_snapshot_to_dict(self) -> None:
        mgr = VoiceSessionManager()
        snap = mgr.snapshot()
        d = snap.to_dict()
        assert "active_sessions" in d
        assert "total_sessions" in d
        assert "sessions_by_type" in d
        assert "sessions_by_priority" in d


class TestVoiceSessionManagerConflictDetection(unittest.TestCase):
    def test_same_device_same_source_supersedes(self) -> None:
        mgr = VoiceSessionManager()
        ev1 = VoiceIngressEvent(
            source_type="right_rail",
            device_id="dev1",
            activation_mode="push_to_talk",
        )
        s1 = mgr.start_session(ev1)
        ev2 = VoiceIngressEvent(
            source_type="right_rail",
            device_id="dev1",
            activation_mode="push_to_talk",
        )
        s2 = mgr.start_session(ev2)
        s1_updated = mgr.get_session(s1.session_id)
        assert s1_updated.status == "superseded"
        assert s2.status == "active"

    def test_different_source_coexists(self) -> None:
        mgr = VoiceSessionManager()
        ev1 = VoiceIngressEvent(
            source_type="conference",
            device_id="dev1",
        )
        s1 = mgr.start_session(ev1)
        ev2 = VoiceIngressEvent(
            source_type="ambient",
            device_id="dev1",
        )
        s2 = mgr.start_session(ev2)
        assert s1.status == "active"
        assert s2.status == "active"
        assert len(mgr.active_sessions()) == 2


class TestVoiceSessionManagerGracefulDegradation(unittest.TestCase):
    def test_no_deps(self) -> None:
        mgr = VoiceSessionManager(
            voice_session_runtime=None,
            voice_ingress_runtime=None,
            session_runtime=None,
        )
        event = VoiceIngressEvent(source_type="right_rail")
        session = mgr.start_session(event)
        assert session.status == "active"

    def test_snapshot_no_deps(self) -> None:
        mgr = VoiceSessionManager(
            voice_session_runtime=None,
            voice_ingress_runtime=None,
            session_runtime=None,
        )
        snap = mgr.snapshot()
        assert snap.total_sessions == 0


if __name__ == "__main__":
    unittest.main()
