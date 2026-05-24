"""Mic input — AmbientMic (always-on VAD) + PushToTalkMic (hotkey-gated).

Both classes produce transcribed text from the microphone. They buffer
speech frames (detected via Silero VAD), write the buffer to a temp WAV
when silence is detected, and batch-transcribe via faster-whisper.

The processing pipeline:
  sounddevice.InputStream (16kHz mono int16)
    → VAD frame check (Silero, 512-sample frames) [audio callback — fast]
    → speech buffer accumulation                   [audio callback — fast]
    → silence gap detection (utterance boundary)   [audio callback — fast]
    → hand off audio data to transcription thread  [queue put — fast]
    → temp WAV write + faster-whisper transcribe   [worker thread — slow]
    → speech classification + utterance-complete   [worker thread]
    → yield transcribed text to caller             [queue put]

Both classes expose the same interface:
  mic.start() → bool
  mic.stop() → None
  mic.get_transcript() → str | None  (non-blocking poll)
  mic.is_listening → bool
"""

from __future__ import annotations

import logging
import os
import queue
import sys
import tempfile
import threading
import wave
from typing import Any

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
FRAME_SAMPLES = 512
BYTES_PER_SAMPLE = 2
FRAME_BYTES = FRAME_SAMPLES * BYTES_PER_SAMPLE

VAD_THRESHOLD = 0.5
SILENCE_FRAMES_TO_END = int(1.5 * SAMPLE_RATE / FRAME_SAMPLES)
MIN_SPEECH_FRAMES = int(0.3 * SAMPLE_RATE / FRAME_SAMPLES)


class _MicBase:
    """Shared infrastructure for both mic modes."""

    def __init__(self) -> None:
        self._stream: Any = None
        self._vad: Any = None
        self._stt: Any = None
        self._running = False
        self._transcript_queue: queue.Queue[str] = queue.Queue(maxsize=32)
        self._audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=16)
        self._speech_buffer: list[bytes] = []
        self._silence_count = 0
        self._is_speech_active = False
        self._transcription_thread: threading.Thread | None = None

    @property
    def is_listening(self) -> bool:
        return self._running

    def _load_vad(self) -> bool:
        if self._vad is not None:
            return True
        try:
            from substrate.execution.voice.voice_engine import IntelligentVoiceProcessor

            self._vad = IntelligentVoiceProcessor()
            self._vad.load_silero()
            return True
        except (ImportError, Exception) as exc:
            logger.warning("VAD load failed: %s", exc)
            return False

    def _load_stt(self) -> bool:
        if self._stt is not None:
            return True
        try:
            from substrate.execution.voice.voice_engine import IntelligentVoiceProcessor

            if self._vad is not None and isinstance(self._vad, IntelligentVoiceProcessor):
                self._stt = self._vad
            else:
                self._stt = IntelligentVoiceProcessor()
            self._stt.load_faster_whisper()
            return True
        except (ImportError, Exception) as exc:
            logger.warning("STT load failed: %s", exc)
            return False

    def _start_transcription_worker(self) -> None:
        def _worker() -> None:
            while self._running:
                try:
                    audio_data = self._audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                text = self._transcribe(audio_data)
                if text:
                    try:
                        self._transcript_queue.put_nowait(text)
                    except queue.Full:
                        logger.debug("Transcript queue full, dropping: %s", text[:50])

        self._transcription_thread = threading.Thread(
            target=_worker, daemon=True, name="umh-transcribe"
        )
        self._transcription_thread.start()

    def _process_frame(self, frame_bytes: bytes) -> None:
        """Called from audio callback — must be fast. Only VAD + buffering."""
        confidence = 0.5
        if self._vad is not None:
            try:
                confidence = self._vad.is_speech_frame(frame_bytes, SAMPLE_RATE)
            except Exception as exc:
                logger.debug("VAD frame check failed: %s", exc)
                confidence = 0.5

        if confidence >= VAD_THRESHOLD:
            self._speech_buffer.append(frame_bytes)
            self._silence_count = 0
            self._is_speech_active = True
        elif self._is_speech_active:
            self._silence_count += 1
            self._speech_buffer.append(frame_bytes)

            if self._silence_count >= SILENCE_FRAMES_TO_END:
                self._flush_speech_buffer()
        else:
            self._speech_buffer.clear()
            self._silence_count = 0

    def _flush_speech_buffer(self) -> None:
        """Hand off buffered audio to transcription worker. Fast — no I/O here."""
        if len(self._speech_buffer) < MIN_SPEECH_FRAMES:
            self._speech_buffer.clear()
            self._silence_count = 0
            self._is_speech_active = False
            return

        audio_data = b"".join(self._speech_buffer)
        self._speech_buffer.clear()
        self._silence_count = 0
        self._is_speech_active = False

        try:
            self._audio_queue.put_nowait(audio_data)
        except queue.Full:
            logger.debug("Audio queue full, dropping speech segment")

    def _transcribe(self, audio_data: bytes) -> str | None:
        """Runs in worker thread — file I/O + model inference."""
        if self._stt is None and not self._load_stt():
            return None

        fd = None
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".wav")
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(BYTES_PER_SAMPLE)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_data)

            text = self._stt.transcribe_fast(tmp_path)
            if not text or len(text.strip()) < 2:
                return None

            classification = "conversation"
            try:
                classification = self._stt.classify_speech(text)
            except Exception as exc:
                logger.debug("Speech classification failed: %s", exc)

            if classification in ("singing", "music_background", "silence"):
                logger.debug("Filtered non-speech: %s (%s)", text[:40], classification)
                return None

            return text.strip()

        except Exception as exc:
            logger.debug("Transcription failed: %s", exc)
            return None
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def get_transcript(self) -> str | None:
        try:
            return self._transcript_queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self) -> None:
        self._running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:
                logger.debug("Stream stop/close failed: %s", exc)
            self._stream = None
        if self._transcription_thread is not None:
            self._transcription_thread.join(timeout=3.0)
            self._transcription_thread = None
        self._speech_buffer.clear()
        self._silence_count = 0
        self._is_speech_active = False


class AmbientMic(_MicBase):
    """Always-on mic with Silero VAD gating.

    Continuously captures audio. VAD filters non-speech. When speech ends
    (silence gap), the buffered audio is handed to a worker thread for
    transcription and queued as text.
    """

    def start(self) -> bool:
        if self._running:
            return True

        if not self._load_vad():
            logger.warning("Cannot start ambient mic without VAD")
            return False
        self._load_stt()

        try:
            import sounddevice as sd

            def _callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
                if status:
                    logger.debug("Sounddevice status: %s", status)
                raw = bytes(indata)
                offset = 0
                while offset + FRAME_BYTES <= len(raw):
                    self._process_frame(raw[offset : offset + FRAME_BYTES])
                    offset += FRAME_BYTES

            self._stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=FRAME_SAMPLES * 4,
                callback=_callback,
            )
            self._stream.start()
            self._running = True
            self._start_transcription_worker()
            logger.info("Ambient mic started (16kHz mono, Silero VAD)")
            return True

        except Exception as exc:
            logger.warning("Failed to start ambient mic: %s", exc)
            return False


class PushToTalkMic(_MicBase):
    """Hotkey-gated mic — only captures while push-to-talk is active.

    Call activate() to start capturing and deactivate() to stop + transcribe.
    """

    def __init__(self) -> None:
        super().__init__()
        self._capturing = False
        self._capture_buffer: list[bytes] = []

    def start(self) -> bool:
        if self._running:
            return True

        self._load_vad()
        self._load_stt()

        try:
            import sounddevice as sd

            def _callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
                if not self._capturing:
                    return
                raw = bytes(indata)
                self._capture_buffer.append(raw)

            self._stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=FRAME_SAMPLES * 4,
                callback=_callback,
            )
            self._stream.start()
            self._running = True
            self._start_transcription_worker()
            logger.info("Push-to-talk mic ready (16kHz mono)")
            return True

        except Exception as exc:
            logger.warning("Failed to start push-to-talk mic: %s", exc)
            return False

    def activate(self) -> None:
        self._capture_buffer.clear()
        self._capturing = True
        logger.debug("Push-to-talk: capturing")

    def deactivate(self) -> None:
        self._capturing = False
        if not self._capture_buffer:
            return

        audio_data = b"".join(self._capture_buffer)
        self._capture_buffer.clear()

        try:
            self._audio_queue.put_nowait(audio_data)
        except queue.Full:
            logger.debug("Audio queue full, dropping PTT segment")

    def stop(self) -> None:
        self._capturing = False
        self._capture_buffer.clear()
        super().stop()

    def __enter__(self) -> PushToTalkMic:
        self.activate()
        return self

    def __exit__(self, *args: Any) -> None:
        self.deactivate()
