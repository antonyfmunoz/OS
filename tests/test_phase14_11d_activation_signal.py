"""Phase 14.11D — ActivationSignal model tests."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest


class TestActivationSource:
    def test_all_sources_defined(self) -> None:
        from substrate.workstation.activation import ActivationSource
        expected = [
            "manual_cockpit_open", "hotkey", "typed_command",
            "push_to_talk_voice", "discord_remote_command",
            "wake_word_unavailable", "clap_unavailable",
            "mobile_remote_command_unavailable",
        ]
        actual = [s.value for s in ActivationSource]
        for e in expected:
            assert e in actual, f"Missing source: {e}"

    def test_source_count(self) -> None:
        from substrate.workstation.activation import ActivationSource
        assert len(ActivationSource) == 8


class TestActivationCapabilityStatus:
    def test_all_statuses(self) -> None:
        from substrate.workstation.activation import ActivationCapabilityStatus
        expected = ["available", "degraded", "unavailable", "not_implemented"]
        actual = [s.value for s in ActivationCapabilityStatus]
        for e in expected:
            assert e in actual


class TestActivationSignal:
    def test_auto_id(self) -> None:
        from substrate.workstation.activation import ActivationSignal
        sig = ActivationSignal(source="hotkey")
        assert sig.activation_id.startswith("act_")

    def test_auto_timestamp(self) -> None:
        from substrate.workstation.activation import ActivationSignal
        sig = ActivationSignal(source="typed_command")
        assert sig.timestamp != ""

    def test_auto_node(self) -> None:
        from substrate.workstation.activation import ActivationSignal
        sig = ActivationSignal(source="manual_cockpit_open")
        assert sig.node != ""

    def test_auto_device(self) -> None:
        from substrate.workstation.activation import ActivationSignal
        sig = ActivationSignal(source="manual_cockpit_open")
        assert sig.device != ""

    def test_to_dict(self) -> None:
        from substrate.workstation.activation import ActivationSignal
        sig = ActivationSignal(source="hotkey", user_id="test_user")
        d = sig.to_dict()
        assert d["source"] == "hotkey"
        assert d["user_id"] == "test_user"
        assert "activation_id" in d
        assert "timestamp" in d

    def test_from_dict(self) -> None:
        from substrate.workstation.activation import ActivationSignal
        sig = ActivationSignal(source="typed_command", raw_payload="status")
        d = sig.to_dict()
        restored = ActivationSignal.from_dict(d)
        assert restored.source == "typed_command"
        assert restored.raw_payload == "status"
        assert restored.activation_id == sig.activation_id

    def test_required_fields(self) -> None:
        from substrate.workstation.activation import ActivationSignal
        sig = ActivationSignal(
            source="push_to_talk_voice",
            user_id="u1",
            session_id="s1",
            lifecycle_mode="default",
            profile_mode="developer",
            continuity_state="active",
        )
        d = sig.to_dict()
        assert d["source"] == "push_to_talk_voice"
        assert d["user_id"] == "u1"
        assert d["session_id"] == "s1"
        assert d["lifecycle_mode"] == "default"
        assert d["profile_mode"] == "developer"
        assert d["continuity_state"] == "active"

    def test_degraded_reason(self) -> None:
        from substrate.workstation.activation import ActivationSignal
        sig = ActivationSignal(
            source="wake_word_unavailable",
            degraded_reason="Wake word model not trained",
            confidence=0.0,
        )
        assert sig.degraded_reason == "Wake word model not trained"
        assert sig.confidence == 0.0

    def test_confidence_default(self) -> None:
        from substrate.workstation.activation import ActivationSignal
        sig = ActivationSignal(source="hotkey")
        assert sig.confidence == 1.0


class TestPresenceCapability:
    def test_capability_creation(self) -> None:
        from substrate.workstation.activation import PresenceCapability
        cap = PresenceCapability(
            name="Wake Word",
            source="wake_word_unavailable",
            status="not_implemented",
            blocker="Model not trained",
        )
        assert cap.name == "Wake Word"
        assert cap.status == "not_implemented"

    def test_capability_to_dict(self) -> None:
        from substrate.workstation.activation import PresenceCapability
        cap = PresenceCapability(name="Hotkey", source="hotkey", status="available")
        d = cap.to_dict()
        assert d["name"] == "Hotkey"
        assert d["status"] == "available"


class TestGetActivationCapabilities:
    def test_returns_all_sources(self) -> None:
        from substrate.workstation.activation import get_activation_capabilities
        caps = get_activation_capabilities()
        assert len(caps) == 8

    def test_unavailable_sources_have_blockers(self) -> None:
        from substrate.workstation.activation import get_activation_capabilities
        caps = get_activation_capabilities()
        for cap in caps:
            if cap.status in ("unavailable", "not_implemented"):
                assert cap.blocker != "", f"{cap.name} is {cap.status} but has no blocker"

    def test_wake_word_not_implemented(self) -> None:
        from substrate.workstation.activation import get_activation_capabilities
        caps = get_activation_capabilities()
        wake = next(c for c in caps if "wake" in c.name.lower())
        assert wake.status == "not_implemented"
        assert "not implemented" in wake.blocker.lower()

    def test_clap_not_implemented(self) -> None:
        from substrate.workstation.activation import get_activation_capabilities
        caps = get_activation_capabilities()
        clap = next(c for c in caps if "clap" in c.name.lower())
        assert clap.status == "not_implemented"

    def test_mobile_not_implemented(self) -> None:
        from substrate.workstation.activation import get_activation_capabilities
        caps = get_activation_capabilities()
        mobile = next(c for c in caps if "mobile" in c.name.lower())
        assert mobile.status == "not_implemented"
        assert "discord" in mobile.blocker.lower()

    def test_manual_always_available(self) -> None:
        from substrate.workstation.activation import get_activation_capabilities
        caps = get_activation_capabilities()
        manual = next(c for c in caps if "manual" in c.name.lower())
        assert manual.status == "available"

    def test_typed_always_available(self) -> None:
        from substrate.workstation.activation import get_activation_capabilities
        caps = get_activation_capabilities()
        typed = next(c for c in caps if "typed" in c.name.lower())
        assert typed.status == "available"


class TestPresenceSession:
    def test_session_auto_id(self) -> None:
        from substrate.workstation.activation import PresenceSession
        session = PresenceSession()
        assert session.session_id.startswith("ps_")

    def test_session_auto_timestamp(self) -> None:
        from substrate.workstation.activation import PresenceSession
        session = PresenceSession()
        assert session.created_at != ""

    def test_session_with_activation(self) -> None:
        from substrate.workstation.activation import ActivationSignal, PresenceSession
        sig = ActivationSignal(source="hotkey")
        session = PresenceSession(activation=sig, continuity_state="active")
        d = session.to_dict()
        assert d["activation"]["source"] == "hotkey"
        assert d["continuity_state"] == "active"

    def test_session_from_dict(self) -> None:
        from substrate.workstation.activation import ActivationSignal, PresenceSession
        sig = ActivationSignal(source="typed_command")
        session = PresenceSession(
            activation=sig,
            continuity_state="idle",
            resume_summary="3 traces executed",
        )
        d = session.to_dict()
        restored = PresenceSession.from_dict(d)
        assert restored.continuity_state == "idle"
        assert restored.resume_summary == "3 traces executed"
        assert restored.activation is not None
        assert restored.activation.source == "typed_command"
