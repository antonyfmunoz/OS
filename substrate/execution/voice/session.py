"""Voice Session — the ONE canonical voice runtime.

Wires the complete voice cycle:
  Audio input → preflight → STT → Classify → governed converse → TTS response

The session runs as a stateful loop. Audio (blob or raw PCM) is fed in, and the
session handles everything from preflight through a governed conversation turn to
generating a spoken response. This is the single audio-bearing, governed voice
runtime; every surface (web, mobile, Electron, Capacitor, CLI, Discord) reaches
it through the governed WS. See ``canonical_voice_runtime.py``.

Not wake-word triggered — the session is manually started/stopped (Phase 0 is
convergence only; ambient/wake activation is out of scope).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.execution.voice.voice_engine import SpeechClassification, VoiceEngine

logger = logging.getLogger(__name__)


class VoiceSessionStatus(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class VoiceExchange:
    """A single voice exchange (user utterance → system response).

    ``error_code`` (GAP7) carries a typed ``VoiceErrorCode`` value when the
    exchange failed a preflight/STT/consent gate. It is mutually exclusive with a
    real ``classification``: a failed exchange has ``error_code`` set and
    ``classification`` empty, so the WS can relay the exact typed failure verbatim
    instead of collapsing to a generic "no speech".
    """

    utterance: str = ""
    classification: str = ""
    responded: bool = False
    response_text: str = ""
    spoken_text: str = ""
    response_audio_path: str = ""
    pipeline_outcome: str = ""
    error_code: str = ""
    action_id: str = ""
    duration_ms: float = 0.0
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class SessionState:
    session_id: str = ""
    status: VoiceSessionStatus = VoiceSessionStatus.IDLE
    node_id: str = ""
    role_slug: str = "ea_orchestrator"
    exchange_count: int = 0
    exchanges: list[VoiceExchange] = field(default_factory=list)
    started_at: float = 0.0
    last_activity: float = 0.0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "exchange_count": self.exchange_count,
            "recent_exchanges": [
                {
                    "utterance": e.utterance[:100],
                    "classification": e.classification,
                    "responded": e.responded,
                    "response_text": e.response_text[:100],
                    "pipeline_outcome": e.pipeline_outcome,
                    "duration_ms": round(e.duration_ms, 1),
                }
                for e in self.exchanges[-5:]
            ],
            "started_at": self.started_at,
            "last_activity": self.last_activity,
            "errors": self.errors[-5:],
        }


class VoiceSession:
    """Stateful voice session managing the full STT → pipeline → TTS loop."""

    def __init__(
        self,
        session_id: str = "",
        pipeline_submit_fn: Any = None,
        max_exchanges: int = 100,
        engine: VoiceEngine | None = None,
        node_id: str = "",
        role_slug: str = "ea_orchestrator",
        converse_fn: Any = None,
    ) -> None:
        # GAP A: engine is injectable. A warm, preloaded VoiceEngine (WhisperModel
        # already loaded) is passed in by the WS/operator_api so the first turn
        # does not pay cold-start latency. Falls back to a fresh engine when none
        # is supplied (CLI/tests). Retain-if-passed: the exact instance is kept.
        self._engine = engine or VoiceEngine()
        self._pipeline_submit = pipeline_submit_fn
        # Injected governed converse: (content, conversation_id, source,
        # voice_turn_id) -> AdvisorResponse. Supplied by the transport/WS layer
        # (which legitimately holds the running organism daemon + its advisor and
        # ledger); substrate must not import transports, so the runtime receives
        # the governed path rather than reaching up for it. When absent (CLI /
        # tests / daemon down), the runtime degrades to deterministic engine
        # routing (Deterministic-First law).
        self._converse_fn = converse_fn
        self._max_exchanges = max_exchanges
        # _ended (GAP C): explicit terminal flag. stop() sets this True so the
        # persisted record reads ENDED regardless of the transient operational
        # status the loop last left behind.
        self._ended = False
        self._state = SessionState(
            session_id=session_id or f"voice-{int(time.time())}",
            node_id=node_id,
            role_slug=role_slug,
        )

    @property
    def state(self) -> SessionState:
        return self._state

    def start(self) -> None:
        self._state.status = VoiceSessionStatus.LISTENING
        self._state.started_at = time.time()
        self._state.last_activity = time.time()
        logger.info("Voice session started: %s", self._state.session_id)

    def stop(self) -> None:
        # GAP C: mark the session ENDED. The operational status stays IDLE (the
        # loop is no longer processing) but _ended takes strict precedence in
        # to_record(), so the persisted record is ENDED, never IDLE.
        self._ended = True
        self._state.status = VoiceSessionStatus.IDLE
        self._persist_record()
        logger.info(
            "Voice session stopped: %s (%d exchanges)",
            self._state.session_id,
            self._state.exchange_count,
        )

    def process_audio_file(self, audio_path: str) -> VoiceExchange:
        """Process an audio file through the full pipeline.

        1. STT: Transcribe audio to text
        2. Classify: Determine if response is needed
        3. Pipeline: Submit to execution pipeline
        4. TTS: Convert response to audio
        """
        t0 = time.monotonic()
        exchange = VoiceExchange()
        self._state.status = VoiceSessionStatus.PROCESSING
        self._state.last_activity = time.time()

        try:
            text = self._engine.intelligent.transcribe_fast(audio_path)
            if not text or len(text.strip()) < 2:
                exchange.classification = SpeechClassification.SILENCE
                self._state.status = VoiceSessionStatus.LISTENING
                return exchange

            exchange.utterance = text
            self._engine.intelligent.add_to_context(text, "user")

            should_respond, classification = self._engine.should_respond(text)
            exchange.classification = classification

            if not should_respond:
                exchange.duration_ms = (time.monotonic() - t0) * 1000
                self._state.status = VoiceSessionStatus.LISTENING
                self._record_exchange(exchange)
                return exchange

            self._apply_response(exchange, text, add_context=True)

        except Exception as e:
            self._state.errors.append(str(e)[:200])
            self._state.status = VoiceSessionStatus.ERROR
            logger.warning("Voice processing error: %s", e)
            # A genuine STT/processing crash must surface as a TYPED error, not a
            # blank "success". Previously this fell through with empty utterance and
            # no error_code, so the client saw an empty transcript instead of a
            # failure. The legitimate no-speech path above sets classification=SILENCE
            # and returns early (never reaches here), so this only fires on a real
            # exception — empty-audio/silence stays distinct.
            from substrate.execution.voice.error_codes import VoiceErrorCode

            exchange.error_code = VoiceErrorCode.STT_FAILED.value

        exchange.duration_ms = (time.monotonic() - t0) * 1000
        self._state.status = VoiceSessionStatus.LISTENING
        self._record_exchange(exchange)
        return exchange

    def process_text(self, text: str) -> VoiceExchange:
        """Process text input directly (skip STT). Useful for testing."""
        t0 = time.monotonic()
        exchange = VoiceExchange(utterance=text)
        self._state.status = VoiceSessionStatus.PROCESSING
        self._state.last_activity = time.time()

        try:
            should_respond, classification = self._engine.should_respond(text)
            exchange.classification = classification

            if not should_respond:
                exchange.duration_ms = (time.monotonic() - t0) * 1000
                self._state.status = VoiceSessionStatus.LISTENING
                self._record_exchange(exchange)
                return exchange

            self._apply_response(exchange, text, add_context=False)

        except Exception as e:
            self._state.errors.append(str(e)[:200])
            self._state.status = VoiceSessionStatus.ERROR
            logger.warning("Voice processing error: %s", e)

        exchange.duration_ms = (time.monotonic() - t0) * 1000
        self._state.status = VoiceSessionStatus.LISTENING
        self._record_exchange(exchange)
        return exchange

    def _apply_response(self, exchange: VoiceExchange, text: str, *, add_context: bool) -> None:
        """Run the governed converse turn and speak the SHAPED reply.

        GAP K: TTS speaks ``spoken_text or text`` — the concise, TTS-friendly
        version the advisor produces via ``prepare_voice_response`` — never the
        raw long-form text.
        """
        result = self._governed_converse(text)
        exchange.response_text = result.text
        # GAP K: prefer the shaped spoken_text; fall back to text if unset.
        spoken = (getattr(result, "spoken_text", "") or result.text).strip()
        exchange.spoken_text = spoken
        exchange.action_id = str(getattr(result, "routing", {}).get("action_id", ""))
        exchange.responded = True

        if spoken:
            self._state.status = VoiceSessionStatus.SPEAKING
            audio_out = self._engine.speak(spoken)
            exchange.response_audio_path = audio_out
            if add_context:
                self._engine.intelligent.add_to_context(result.text, "assistant")

    def _governed_converse(self, text: str) -> Any:
        """Run one governed conversation turn.

        When a ``converse_fn`` was injected (by the governed WS layer), it is the
        single governed write path — the advisor's ``converse(source="voice",
        voice_turn_id=…)`` persists the turn to the OrganismStore ledger, sets a
        concise ``spoken_text`` for TTS, and returns an ``AdvisorResponse``.
        Deterministic-first (GAP I): the advisor already falls back to a template
        response when the LLM yields empty, so the injected path always returns a
        usable ``AdvisorResponse``. When no ``converse_fn`` is present, the runtime
        degrades to deterministic engine routing so a voice turn still produces a
        usable spoken response (Deterministic-First law) — never None, never a
        raise into the caller.
        """
        voice_turn_id = f"{self._state.session_id}:{self._state.exchange_count}"
        if self._converse_fn is not None:
            try:
                result = self._converse_fn(
                    content=text,
                    conversation_id=self._state.session_id,
                    source="voice",
                    voice_turn_id=voice_turn_id,
                )
                if result is not None and getattr(result, "text", None) is not None:
                    return result
            except Exception as e:
                logger.debug("injected governed converse failed, degrading: %s", e)

        # Deterministic fallback: usable spoken response with no organism.
        from substrate.organism.advisor_conversation import AdvisorResponse

        routed = self._engine.route_query(text)
        return AdvisorResponse(
            text=routed,
            conversation_id=self._state.session_id,
            intent="voice_query",
            spoken_text=routed,
        )

    def _record_exchange(self, exchange: VoiceExchange) -> None:
        self._state.exchange_count += 1
        self._state.exchanges.append(exchange)
        if len(self._state.exchanges) > self._max_exchanges:
            self._state.exchanges = self._state.exchanges[-self._max_exchanges :]
        self._persist_record()

    # ── Preflight-gated blob entry (content-type branched) ──────────────────

    def process_audio_blob(
        self, audio: bytes, content_type: str = "application/octet-stream"
    ) -> VoiceExchange:
        """Process a captured audio buffer, branching on content type (GAP:
        raw-PCM vs container).

        - ``audio/pcm`` / ``audio/l16`` / raw PCM16 → validated by
          ``preflight_pcm16`` (no decode) and transcribed directly.
        - a container blob (webm/ogg/wav/mp4/m4a) → normalized to PCM WAV via
          ``normalize_to_pcm_wav`` (ffmpeg, CPU-gated), then transcribed.

        A preflight failure sets a typed ``error_code`` on the exchange and SKIPS
        STT entirely (``transcribe_fast`` is never called), so the WS relays the
        exact typed failure verbatim. The audio is never discarded here.
        """
        from umh.voice_preflight import (
            VoiceErrorCode,
            is_raw_pcm_content_type,
            normalize_to_pcm_wav,
            preflight_pcm16,
        )

        t0 = time.monotonic()
        exchange = VoiceExchange()
        self._state.status = VoiceSessionStatus.PROCESSING
        self._state.last_activity = time.time()

        try:
            if not audio:
                exchange.error_code = VoiceErrorCode.EMPTY_AUDIO_BLOB.value
                self._state.status = VoiceSessionStatus.LISTENING
                self._record_exchange(exchange)
                return exchange

            if is_raw_pcm_content_type(content_type):
                pre = preflight_pcm16(audio)
                if not pre.ok:
                    exchange.error_code = pre.error_code.value if pre.error_code else "STT_FAILED"
                    self._state.status = VoiceSessionStatus.LISTENING
                    self._record_exchange(exchange)
                    return exchange
                wav_path = _write_pcm16_wav(audio)
            else:
                norm = normalize_to_pcm_wav(audio, content_type=content_type)
                if not norm.ok:
                    exchange.error_code = (
                        norm.error_code.value if norm.error_code else "DECODE_FAILED"
                    )
                    self._state.status = VoiceSessionStatus.LISTENING
                    self._record_exchange(exchange)
                    return exchange
                wav_path = norm.wav_path

            return self.process_audio_file(wav_path)

        except Exception as e:
            self._state.errors.append(str(e)[:200])
            self._state.status = VoiceSessionStatus.ERROR
            exchange.error_code = VoiceErrorCode.STT_FAILED.value
            logger.warning("Voice blob processing error: %s", e)
            exchange.duration_ms = (time.monotonic() - t0) * 1000
            self._state.status = VoiceSessionStatus.LISTENING
            self._record_exchange(exchange)
            return exchange

    # ── Record emission + resume (fold into the ONE store) ──────────────────

    def to_record(self) -> Any:
        """Snapshot this session as a durable ``VoiceSessionRecord``.

        GAP C: ``_ended`` takes STRICT precedence — a stopped session reads ENDED
        regardless of the transient operational status the loop last left behind.
        """
        from substrate.execution.voice.store import (
            VoiceSessionRecord,
            VoiceSessionRecordStatus,
            exchange_to_turns,
            runtime_status_to_record,
        )

        status = (
            VoiceSessionRecordStatus.ENDED
            if self._ended
            else runtime_status_to_record(self._state.status.value)
        )
        rec = VoiceSessionRecord(
            session_id=self._state.session_id,
            node_id=self._state.node_id,
            role_slug=self._state.role_slug,
            status=status,
        )
        for ex in self._state.exchanges:
            for turn in exchange_to_turns(
                ex.utterance,
                ex.response_text,
                ex.responded,
                role_slug=self._state.role_slug,
                action_id=ex.action_id or None,
            ):
                rec.turns.append(turn)
        return rec

    def _persist_record(self) -> None:
        """Emit the current session snapshot into the ONE canonical store."""
        try:
            from substrate.execution.voice.store import get_voice_session_store

            get_voice_session_store().put(self.to_record())
        except Exception as e:  # best-effort, never raise into the loop
            logger.debug("voice record persist failed: %s", e)

    @classmethod
    def resume(
        cls,
        record: Any,
        *,
        engine: VoiceEngine | None = None,
        pipeline_submit_fn: Any = None,
        converse_fn: Any = None,
    ) -> VoiceSession:
        """Rebuild a live session from a persisted ``VoiceSessionRecord``.

        Forwards the injected ``engine`` (GAP A) so a resumed session reuses the
        warm engine. SYSTEM turns (lifecycle/role-switch/error notices) are
        skipped — they are not conversational exchanges and would corrupt the
        replayed context.
        """
        from substrate.execution.voice.store import VoiceTurnSource

        session = cls(
            session_id=getattr(record, "session_id", ""),
            engine=engine,
            pipeline_submit_fn=pipeline_submit_fn,
            converse_fn=converse_fn,
            node_id=getattr(record, "node_id", ""),
            role_slug=getattr(record, "role_slug", "ea_orchestrator"),
        )

        def _append(ex: VoiceExchange) -> None:
            session._state.exchanges.append(ex)
            session._state.exchange_count += 1

        pending_user: str | None = None
        for turn in getattr(record, "turns", []) or []:
            if turn.source == VoiceTurnSource.SYSTEM:
                continue  # SYSTEM turns are not conversational exchanges
            if turn.source == VoiceTurnSource.USER:
                # a fresh USER turn closes any still-open user (an unanswered
                # utterance) as its own exchange, then opens the new one.
                if pending_user is not None:
                    _append(VoiceExchange(utterance=pending_user))
                pending_user = turn.text
            elif turn.source == VoiceTurnSource.AGENT:
                last = session._state.exchanges[-1] if session._state.exchanges else None
                if pending_user is None and last is not None and last.responded:
                    # consecutive AGENT with no intervening USER — fold into the
                    # last exchange; last agent turn wins.
                    last.response_text = turn.text
                    last.spoken_text = turn.text
                    last.action_id = turn.action_id or last.action_id
                    continue
                _append(
                    VoiceExchange(
                        utterance=pending_user or "",
                        response_text=turn.text,
                        spoken_text=turn.text,
                        responded=True,
                        action_id=turn.action_id or "",
                    )
                )
                pending_user = None
        if pending_user is not None:
            _append(VoiceExchange(utterance=pending_user))
        return session


def _write_pcm16_wav(pcm16: bytes) -> str:
    """Write a raw PCM16 mono@16kHz buffer to a temp WAV file for STT input."""
    import tempfile
    import wave

    fd, path = tempfile.mkstemp(suffix=".wav", prefix="voice_pcm_")
    import os

    os.close(fd)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm16)
    return path
