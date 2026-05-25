"""Voice Session — end-to-end voice pipeline loop.

Wires the complete voice cycle:
  Audio input → VAD → STT → Classify → Pipeline submit → TTS response

The session runs as a stateful loop. Audio chunks are fed in,
the session handles everything from speech detection through
to generating a spoken response.

Not wake-word triggered — the session is manually started/stopped.
"""

from __future__ import annotations

import logging
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from substrate.execution.voice.voice_engine import VoiceEngine, SpeechClassification

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class VoiceExchange:
    """A single voice exchange (user utterance → system response)."""

    utterance: str = ""
    classification: str = ""
    responded: bool = False
    response_text: str = ""
    response_audio_path: str = ""
    pipeline_outcome: str = ""
    duration_ms: float = 0.0
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class SessionState:
    session_id: str = ""
    status: SessionStatus = SessionStatus.IDLE
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
    ) -> None:
        self._engine = VoiceEngine()
        self._pipeline_submit = pipeline_submit_fn
        self._max_exchanges = max_exchanges
        self._state = SessionState(
            session_id=session_id or f"voice-{int(time.time())}",
        )

    @property
    def state(self) -> SessionState:
        return self._state

    def start(self) -> None:
        self._state.status = SessionStatus.LISTENING
        self._state.started_at = time.time()
        self._state.last_activity = time.time()
        logger.info("Voice session started: %s", self._state.session_id)

    def stop(self) -> None:
        self._state.status = SessionStatus.IDLE
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
        self._state.status = SessionStatus.PROCESSING
        self._state.last_activity = time.time()

        try:
            text = self._engine.intelligent.transcribe_fast(audio_path)
            if not text or len(text.strip()) < 2:
                exchange.classification = SpeechClassification.SILENCE
                self._state.status = SessionStatus.LISTENING
                return exchange

            exchange.utterance = text
            self._engine.intelligent.add_to_context(text, "user")

            should_respond, classification = self._engine.should_respond(text)
            exchange.classification = classification

            if not should_respond:
                exchange.duration_ms = (time.monotonic() - t0) * 1000
                self._state.status = SessionStatus.LISTENING
                self._record_exchange(exchange)
                return exchange

            response_text = self._get_response(text)
            exchange.response_text = response_text
            exchange.responded = True

            if response_text:
                self._state.status = SessionStatus.SPEAKING
                audio_out = self._engine.speak(response_text)
                exchange.response_audio_path = audio_out
                self._engine.intelligent.add_to_context(response_text, "assistant")

        except Exception as e:
            self._state.errors.append(str(e)[:200])
            self._state.status = SessionStatus.ERROR
            logger.warning("Voice processing error: %s", e)

        exchange.duration_ms = (time.monotonic() - t0) * 1000
        self._state.status = SessionStatus.LISTENING
        self._record_exchange(exchange)
        return exchange

    def process_text(self, text: str) -> VoiceExchange:
        """Process text input directly (skip STT). Useful for testing."""
        t0 = time.monotonic()
        exchange = VoiceExchange(utterance=text)
        self._state.status = SessionStatus.PROCESSING
        self._state.last_activity = time.time()

        try:
            should_respond, classification = self._engine.should_respond(text)
            exchange.classification = classification

            if not should_respond:
                exchange.duration_ms = (time.monotonic() - t0) * 1000
                self._state.status = SessionStatus.LISTENING
                self._record_exchange(exchange)
                return exchange

            response_text = self._get_response(text)
            exchange.response_text = response_text
            exchange.responded = True

            if response_text:
                self._state.status = SessionStatus.SPEAKING
                audio_out = self._engine.speak(response_text)
                exchange.response_audio_path = audio_out

        except Exception as e:
            self._state.errors.append(str(e)[:200])
            self._state.status = SessionStatus.ERROR
            logger.warning("Voice processing error: %s", e)

        exchange.duration_ms = (time.monotonic() - t0) * 1000
        self._state.status = SessionStatus.LISTENING
        self._record_exchange(exchange)
        return exchange

    def _get_response(self, text: str) -> str:
        """Get a response — pipeline first, then voice engine routing."""
        if self._pipeline_submit:
            try:
                from substrate.governance.risk_classes import RiskClass

                result = self._pipeline_submit(
                    text,
                    source="voice",
                    risk_class=RiskClass.READ_ONLY,
                    adapter_name="voice",
                    operation="voice_query",
                    metadata={"session_id": self._state.session_id},
                )
                outcome = getattr(result, "outcome_type", None)
                if outcome and outcome not in ("governance_denied", "mastery_blocked"):
                    return f"Processed: {outcome}"
            except Exception as e:
                logger.debug("Pipeline submit failed, falling back to voice routing: %s", e)

        return self._engine.route_query(text)

    def _record_exchange(self, exchange: VoiceExchange) -> None:
        self._state.exchange_count += 1
        self._state.exchanges.append(exchange)
        if len(self._state.exchanges) > self._max_exchanges:
            self._state.exchanges = self._state.exchanges[-self._max_exchanges :]
