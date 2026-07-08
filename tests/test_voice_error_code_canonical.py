"""P4S31 Voice Convergence — the ONE voice error taxonomy.

Proves ``VoiceErrorCode`` has a single owner (substrate), that
``umh.voice_preflight`` re-exports the SAME object (not a copy), that the canon
is exactly 9 UPPERCASE codes, and that CONSENT_EXPIRED is deliberately absent.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.execution.voice.error_codes import VoiceErrorCode, error_payload


def test_single_owner() -> None:
    # umh.voice_preflight.VoiceErrorCode must BE the canonical object by identity
    # (re-export, not a parallel definition).
    from umh.voice_preflight import VoiceErrorCode as PreflightCode
    from umh.voice_preflight import error_payload as preflight_payload

    assert PreflightCode is VoiceErrorCode
    assert preflight_payload is error_payload


def test_nine_code_canon() -> None:
    members = {c.name for c in VoiceErrorCode}
    assert len(members) == 9, members
    # CONSENT_EXPIRED is deliberately absent — the consent grant has no expiry.
    assert "CONSENT_EXPIRED" not in members


def test_values_are_uppercase() -> None:
    for c in VoiceErrorCode:
        assert c.value == c.name
        assert c.value == c.value.upper()


def test_error_payload_shape_is_bounded() -> None:
    p = error_payload(VoiceErrorCode.SILENT_AUDIO)
    assert p["type"] == "error"
    assert p["code"] == "SILENT_AUDIO"
    assert len(p["message"]) <= 100
    # a custom message is bounded and never carries content beyond 100 chars
    long = error_payload(VoiceErrorCode.STT_FAILED, "x" * 500)
    assert len(long["message"]) == 100
