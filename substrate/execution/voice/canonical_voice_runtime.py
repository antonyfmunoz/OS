"""Canonical voice runtime — the single declared voice-session entry.

P4S31 Voice Convergence. This module *declares* the one canonical path from a
captured utterance (any surface) to a governed conversation turn:

    capture-edge  →  VoiceSession(VoiceEngine local STT/TTS)
                  →  governed_mutation(conversation_send)  →  OrganismStore

There is exactly one voice-session runtime: ``substrate.execution.voice.session
.VoiceSession``. It is the only runtime that owns a real audio pipeline
(``VoiceEngine`` → local faster-whisper STT → classify → TTS) AND the only one
wired to governance. Rival voice runtimes become *adapters* or *records*:

- ``substrate/execution/bridge/voice_session.py`` — a compat re-export/store
  shim; its record + turn store fold into ``voice/store.py``. It no longer owns
  a session-execution runtime of its own.
- ``umh/voice_server.py`` — RETIRED. The standalone STT/VAD/TTS server (and its
  Groq-first STT) was removed entirely; voice runs inside the API backend behind
  the governed WS. No separate voice process, no second STT/TTS engine.
- ``substrate/workstation/voice_session_manager.py`` — kept as the multi-session
  PRIORITY ARBITER (COMMAND>CONVERSATION>PASSIVE); it delegates turn *execution*
  to the one runtime.
- ``substrate/execution/bridge/live_sessions.py`` — a DISTINCT lifecycle tracker
  (calls/meetings as state machines, zero audio); NOT a voice runtime and never
  folded into the audio runtime.

This module holds no execution logic of its own — it is a declaration plus a
deterministic routing flag, mirroring ``substrate/organism/canonical_runtime
.py`` (WP-P1-001). It never imports transports/ or services/ (substrate
dependency direction). The concrete engine/router are obtained at call time.

Design constraints:
- Deterministic-first: the flag is a plain env/default lookup, never an LLM.
- Fail-safe default: routing is OFF by default so deploying this packet is a
  no-op for running services until the flag is explicitly enabled. Rollback is
  "unset the flag" with no code revert.
- FREE + LOCAL: the canonical runtime's STT is local faster-whisper via
  ``VoiceEngine``; no cloud STT default may exist on this path. Gate 14
  (``scripts/check_voice_runtime_divergence.py``) makes a rival runtime,
  a second STT/TTS engine, a rogue voice WS, or a cloud-STT import
  mechanically impossible.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# The single canonical voice runtime, named once here so tests, docs, adapters,
# and the divergence gate reference one string instead of re-deriving it.
CANONICAL_VOICE_RUNTIME = (
    "capture-edge -> VoiceSession(VoiceEngine local STT/TTS) "
    "-> governed_mutation(conversation_send) -> OrganismStore"
)

# The one legal module home for a VoiceSession runtime class. Gate 14 blocks any
# voice-session runtime class defined outside this path.
CANONICAL_VOICE_RUNTIME_MODULE = "substrate/execution/voice/session.py"

# The one legal STT/TTS engine home. Gate 14 blocks a second engine that both
# imports faster_whisper/WhisperModel/groq and defines transcribe/generate_tts
# outside this module.
CANONICAL_VOICE_ENGINE_MODULE = "substrate/execution/voice/voice_engine.py"

# The one legal governed voice WS surface. Gate 14 blocks a raw websockets.serve
# on a voice path anywhere else (this is what stops a new :8096-style bridge).
CANONICAL_VOICE_WS_MODULE = "transports/api/voice.py"

# Env flag that enables surface routing through the canonical governed WS. Off by
# default: deploying this packet changes no running behavior until it is set, so
# the staged cutover is controlled entirely by this switch.
_ROUTE_FLAG_ENV = "UMH_CANONICAL_VOICE_ROUTING"

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def canonical_voice_routing_enabled() -> bool:
    """Deterministic check: should capture edges route through the one governed
    voice runtime (``/api/umh/voice/ws`` → ``VoiceSession``)?

    Reads ``UMH_CANONICAL_VOICE_ROUTING``. Any of 1/true/yes/on (case-insensitive)
    enables routing; anything else (including unset) keeps the pre-convergence
    behavior. No LLM, no network — a pure lookup so the routing decision is part
    of the deterministic spine.
    """
    return os.environ.get(_ROUTE_FLAG_ENV, "").strip().lower() in _TRUTHY


def canonical_voice_runtime_name() -> str:
    """Return the declared canonical voice runtime identifier."""
    return CANONICAL_VOICE_RUNTIME
