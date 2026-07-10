"""Warm VoiceEngine singleton — one preloaded STT/TTS engine, process-wide.

P4S31 Voice Convergence. Cold-starting ``VoiceEngine`` loads the faster-whisper
``WhisperModel`` (hundreds of MB, seconds of latency) on first transcription.
The governed WS constructs a ``VoiceSession(engine=get_warm_engine())`` per turn,
and the operator_api startup preloads the SAME instance, so the first real voice
turn never pays cold-start latency (GAP A). Because ``VoiceSession`` retains the
injected engine by identity, the preload is never wasted on an engine nobody uses.

Deterministic-first / FREE+LOCAL: the engine's STT is local faster-whisper — no
cloud default. This module only owns the singleton lifecycle, not the engine
logic.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import threading

from substrate.execution.voice.voice_engine import VoiceEngine

logger = logging.getLogger(__name__)

_engine_singleton: VoiceEngine | None = None
_engine_lock = threading.Lock()


def get_warm_engine() -> VoiceEngine:
    """Return the process-wide warm ``VoiceEngine``, constructing it once.

    Thread-safe double-checked singleton. The instance is shared between the
    governed WS (per-turn ``VoiceSession(engine=…)``) and the startup preload so
    both reference the exact same loaded model.
    """
    global _engine_singleton
    if _engine_singleton is None:
        with _engine_lock:
            if _engine_singleton is None:
                _engine_singleton = VoiceEngine()
    return _engine_singleton


def preload_warm_engine() -> None:
    """Eagerly construct the warm engine and load its STT model.

    Called at operator_api startup so the STT model is resident before the first
    voice turn. Best-effort: a load failure logs and leaves the singleton to
    lazy-construct on first use (the runtime still works, just cold on turn 1).

    We preload **faster-whisper** — the model ``transcribe_fast`` actually uses on
    the hot path — NOT openai-whisper via ``load_whisper()``. Preloading the wrong
    model left faster-whisper to cold-load on turn 1 (and, before the fallback was
    removed, made every empty-result clip pay a ~28 s openai-whisper cold load).
    """
    try:
        engine = get_warm_engine()
        # Load the canonical hot-path STT (faster-whisper) now, not on turn 1.
        proc = getattr(engine, "intelligent", None)
        fw = getattr(proc, "load_faster_whisper", None)
        if callable(fw):
            fw()
            logger.info("warm VoiceEngine preloaded (faster-whisper resident)")
        else:  # pragma: no cover — engine shape changed
            logger.warning("warm VoiceEngine: no faster-whisper loader found")
    except Exception as e:  # best-effort — never block startup
        logger.warning("warm VoiceEngine preload failed (will lazy-load): %s", e)


def reset_warm_engine_for_tests() -> None:
    global _engine_singleton
    with _engine_lock:
        _engine_singleton = None
