"""P4S31 Voice Convergence — the canonical voice runtime declaration.

Mirrors ``tests/test_single_spine_architecture.py``: asserts the declaration
module names exactly one canonical runtime and that its routing flag defaults OFF
(so deploying the packet is a no-op until the flag is set — a clean staged
cutover with rollback == "unset the flag").
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, "/opt/OS")

from substrate.execution.voice import canonical_voice_runtime as cvr


def test_declares_single_canonical_runtime() -> None:
    assert cvr.CANONICAL_VOICE_RUNTIME_MODULE == "substrate/execution/voice/session.py"
    assert cvr.canonical_voice_runtime_name() == cvr.CANONICAL_VOICE_RUNTIME
    assert "VoiceSession" in cvr.CANONICAL_VOICE_RUNTIME
    assert "governed_mutation" in cvr.CANONICAL_VOICE_RUNTIME


def test_routing_defaults_off(monkeypatch) -> None:
    monkeypatch.delenv("UMH_CANONICAL_VOICE_ROUTING", raising=False)
    assert cvr.canonical_voice_routing_enabled() is False


def test_routing_flag_is_deterministic(monkeypatch) -> None:
    for truthy in ("1", "true", "YES", "on"):
        monkeypatch.setenv("UMH_CANONICAL_VOICE_ROUTING", truthy)
        assert cvr.canonical_voice_routing_enabled() is True
    for falsy in ("", "0", "false", "off", "nope"):
        monkeypatch.setenv("UMH_CANONICAL_VOICE_ROUTING", falsy)
        assert cvr.canonical_voice_routing_enabled() is False


def test_single_engine_and_ws_home_named() -> None:
    # The gate references these constants; pin them so a rename can't silently
    # widen the allowed homes.
    assert cvr.CANONICAL_VOICE_ENGINE_MODULE == ("substrate/execution/voice/voice_engine.py")
    assert cvr.CANONICAL_VOICE_WS_MODULE == "transports/api/voice.py"


def test_no_ambient_env_leak() -> None:
    # Phase 0 is convergence only — no ambient/wake activation is declared here.
    src = os.path.join(os.path.dirname(cvr.__file__), "canonical_voice_runtime.py")
    with open(src, encoding="utf-8") as f:
        body = f.read()
    assert "wake_word" not in body.lower() or "no ambient" in body.lower()
