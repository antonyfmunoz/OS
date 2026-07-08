#!/usr/bin/env python3
"""Server-side audio preflight, normalization, and precise error taxonomy.

P4S-31D1-C. Companion to ``umh/voice_server.py``.

Purpose
-------
Before this module, EVERY failure mode in the voice pipeline collapsed into a
single bare ``{"transcript","text":"","final":true}`` message which the cockpit
client turned into a blanket "No speech detected". That erased the distinction
between "no bytes arrived", "the mic was silent", "audio was present but held no
speech", "the audio container could not be decoded", and "the STT engine itself
failed". This module makes each of those a PRECISE, typed, distinct outcome.

It contains only pure, side-effect-light helpers so every branch is directly
unit-testable without a WebSocket, a network call, or a running STT engine.

Two audio lanes it serves
-------------------------
1. **Live mic lane** — the browser sends raw PCM16 mono @16kHz over the WS. No
   container decode is needed. ``preflight_pcm16()`` validates the *whole*
   buffer (bytes present, non-silent mean RMS, minimum duration) BEFORE STT.
2. **Uploaded-artifact / retry lane (Lane E)** — a retry streams a stored blob
   which may be a real container (webm/ogg/wav/mp4/m4a-AAC). ``normalize_to_pcm_wav()``
   decodes it to the canonical STT input (PCM WAV mono 16kHz) via ffmpeg,
   invoked ONLY through the CPU gate. A decode failure is ``DECODE_FAILED`` /
   ``UNSUPPORTED_AUDIO_FORMAT`` — never a silent "no speech".

Logging law (voice_message_contract.json logging_law / storage_law):
  - transcript text and audio bytes are NEVER logged at INFO or above.
  - energy / duration / format / error-code are non-secret and may be logged.
  - any content preview is bounded (<=40 chars) and DEBUG-only. This module
    logs no transcript text at all.
"""

from __future__ import annotations

import logging
import math
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("voice_server.preflight")

# Canonical STT input format. ffmpeg normalizes every container to this.
SAMPLE_RATE = 16000
SAMPLE_WIDTH_BYTES = 2  # PCM16
CHANNELS = 1

# --- Preflight thresholds (documented, tunable, non-secret) ---

# Minimum bytes of raw PCM16 that constitute an utterance worth transcribing.
# 0.3 s @ 16kHz * 2 bytes = 9600 bytes. Matches voice_server.MIN_AUDIO_BYTES.
MIN_UTTERANCE_BYTES = int(SAMPLE_RATE * SAMPLE_WIDTH_BYTES * 0.3)

# Minimum duration (seconds) for a buffer to be transcribed at all.
MIN_UTTERANCE_SECONDS = 0.3

# Silence floor over the WHOLE buffer. compute_audio_level() in voice_server
# scales RMS by /8000 and clamps to 1.0; SPEECH_LEVEL_THRESHOLD there is 0.02
# on that scale (== raw RMS 160). We compute mean RMS over the entire buffer
# here (not per-chunk) and compare on the SAME 0..1 scale so the floor is
# coherent with the live VAD threshold. A buffer whose mean level is below this
# is SILENT_AUDIO (mic effectively silent) rather than VAD_NO_SPEECH.
RMS_LEVEL_SCALE = 8000.0
SILENCE_MEAN_LEVEL_FLOOR = 0.008  # raw mean RMS ~64; below = silent mic

# Content preview bound (privacy). Nothing here previews transcript text, but
# the constant is exported so callers stay consistent.
PREVIEW_CHARS = 40


# VoiceErrorCode + error_payload were relocated to the canonical substrate home
# ``substrate/execution/voice/error_codes.py`` (P4S31 Voice Convergence). This
# module re-exports them so every existing consumer of
# ``umh.voice_preflight.VoiceErrorCode`` / ``error_payload`` keeps working — there
# is now ONE definition, owned by substrate (the canonical runtime imports it,
# and substrate may never import from umh, so the enum could not stay here).
from substrate.execution.voice.error_codes import (  # noqa: E402,F401
    VoiceErrorCode,
    error_payload,
)


@dataclass(frozen=True)
class PreflightResult:
    """Outcome of preflighting a raw PCM16 utterance buffer.

    ``ok`` True  -> the buffer is worth sending to STT.
    ``ok`` False -> ``error_code`` is set and STT MUST be skipped. The audio is
                    still preserved by the caller (this module never discards it).
    ``mean_level`` and ``duration_s`` are non-secret diagnostics safe to log.
    """

    ok: bool
    error_code: VoiceErrorCode | None
    mean_level: float
    duration_s: float
    n_bytes: int


def mean_rms_level(pcm16: bytes) -> float:
    """Mean RMS energy of a whole PCM16 buffer, on the same 0..1 scale as
    ``voice_server.compute_audio_level`` (raw RMS / 8000, clamped to 1.0).

    Computed over the ENTIRE buffer, not per-chunk — a buffer that is mostly
    silence with one tiny spike still reads as low mean energy. Returns 0.0 for
    an empty or sub-sample buffer.
    """
    if len(pcm16) < SAMPLE_WIDTH_BYTES:
        return 0.0
    n_samples = len(pcm16) // SAMPLE_WIDTH_BYTES
    if n_samples == 0:
        return 0.0
    samples = struct.unpack("<%dh" % n_samples, pcm16[: n_samples * SAMPLE_WIDTH_BYTES])
    rms = math.sqrt(sum(s * s for s in samples) / n_samples)
    return min(1.0, rms / RMS_LEVEL_SCALE)


def pcm16_duration_seconds(pcm16: bytes) -> float:
    """Duration in seconds of a raw PCM16 mono @16kHz buffer."""
    return len(pcm16) / (SAMPLE_RATE * SAMPLE_WIDTH_BYTES)


def preflight_pcm16(pcm16: bytes) -> PreflightResult:
    """Validate a completed raw-PCM16 utterance buffer BEFORE transcription.

    Ordered, mutually-exclusive checks:
      1. bytes present at all           -> else EMPTY_AUDIO_BLOB
      2. minimum duration / byte count  -> else EMPTY_AUDIO_BLOB (too little to be real)
      3. non-silent mean energy         -> else SILENT_AUDIO

    A buffer that PASSES all three is ``ok=True``; whether it actually contains
    *speech* (vs noise) is decided later by the STT engine and surfaced as
    VAD_NO_SPEECH — which is why SILENT_AUDIO and VAD_NO_SPEECH are distinct.

    This function has no side effects and does not touch the audio it validates.
    """
    n = len(pcm16)
    duration = pcm16_duration_seconds(pcm16)

    if n == 0:
        return PreflightResult(False, VoiceErrorCode.EMPTY_AUDIO_BLOB, 0.0, 0.0, 0)

    # Too few bytes to be a real utterance — treat as no meaningful audio blob.
    if n < MIN_UTTERANCE_BYTES or duration < MIN_UTTERANCE_SECONDS:
        level = mean_rms_level(pcm16)
        log.info(
            "preflight: undersized buffer (%d bytes, %.2fs) -> EMPTY_AUDIO_BLOB",
            n,
            duration,
        )
        return PreflightResult(False, VoiceErrorCode.EMPTY_AUDIO_BLOB, level, duration, n)

    level = mean_rms_level(pcm16)
    if level < SILENCE_MEAN_LEVEL_FLOOR:
        log.info(
            "preflight: silent buffer (mean_level=%.4f < %.4f, %.2fs) -> SILENT_AUDIO",
            level,
            SILENCE_MEAN_LEVEL_FLOOR,
            duration,
        )
        return PreflightResult(False, VoiceErrorCode.SILENT_AUDIO, level, duration, n)

    log.info("preflight: ok (%d bytes, %.2fs, mean_level=%.4f)", n, duration, level)
    return PreflightResult(True, None, level, duration, n)


# --- Container decode / normalization (Lane E retries + future mobile mp4) ---

# Container content types we can decode+normalize with ffmpeg. The live mic lane
# never hits this path (it is already raw PCM16). Keyed on the base content type
# (codec parameters stripped by the caller).
SUPPORTED_CONTAINER_TYPES: frozenset[str] = frozenset(
    {
        "audio/webm",
        "audio/ogg",
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/mp4",
        "audio/m4a",
        "audio/x-m4a",
        "audio/aac",
        "audio/mpeg",  # mp3
    }
)

# File extensions -> whether we consider the container decodable. Used when only
# an extension is known (from the upload seam's server-derived extension).
_EXT_TO_SUPPORTED: dict[str, bool] = {
    ".weba": True,  # audio/webm (server-derived)
    ".webm": True,
    ".ogg": True,
    ".oga": True,
    ".wav": True,
    ".mp4": True,
    ".m4a": True,
    ".aac": True,
    ".mp3": True,
}


def is_supported_container_type(content_type: str) -> bool:
    """True if ``content_type`` (any casing, codec params allowed) is a
    container we will attempt to decode."""
    base = content_type.split(";", 1)[0].strip().lower()
    return base in SUPPORTED_CONTAINER_TYPES


def is_supported_extension(ext: str) -> bool:
    """True if a file extension names a container we will attempt to decode."""
    return _EXT_TO_SUPPORTED.get(ext.lower(), False)


@dataclass(frozen=True)
class NormalizeResult:
    """Outcome of decoding+normalizing a container blob to canonical PCM WAV.

    On success ``wav_path`` points to a freshly written PCM WAV mono 16kHz temp
    file the CALLER owns and must unlink. On failure ``error_code`` is set,
    ``wav_path`` is None, and the ORIGINAL blob is untouched (never discarded).
    """

    ok: bool
    wav_path: str | None
    error_code: VoiceErrorCode | None
    detail: str


def _ffmpeg_available() -> bool:
    """Whether the ffmpeg binary is resolvable on PATH. Cheap, no gate needed
    (no process spawned — this only inspects PATH)."""
    import shutil

    return shutil.which("ffmpeg") is not None


def normalize_to_pcm_wav(
    src_bytes: bytes,
    *,
    content_type: str = "",
    src_ext: str = "",
    caller: str = "voice_server.normalize_audio",
) -> NormalizeResult:
    """Decode an arbitrary supported container to canonical PCM WAV mono 16kHz.

    Used by the uploaded-artifact / Lane-E retry path (and future mobile mp4).
    The live mic path does NOT call this — it already sends raw PCM16.

    Behavior:
      - Empty input           -> EMPTY_AUDIO_BLOB.
      - Unknown/unsupported    -> UNSUPPORTED_AUDIO_FORMAT (before spending ffmpeg).
        format
      - ffmpeg absent          -> DECODE_FAILED with a clear detail (degrade
        gracefully; never crash the server).
      - CPU gate blocks ffmpeg -> DECODE_FAILED (host overloaded) — the caller
        can surface it or retry later; the audio is preserved.
      - ffmpeg non-zero / no    -> DECODE_FAILED (corrupt/truncated/not audio).
        output
      - success                 -> ok=True, wav_path set (caller unlinks).

    ffmpeg is invoked ONLY through ``gated_subprocess_run`` (CPU Gate Law): no
    raw subprocess is ever used here.
    """
    if not src_bytes:
        return NormalizeResult(False, None, VoiceErrorCode.EMPTY_AUDIO_BLOB, "empty blob")

    # Reject formats we do not claim to support BEFORE spending any CPU. Prefer
    # the declared content type; fall back to the file extension.
    fmt_known = False
    if content_type and is_supported_container_type(content_type):
        fmt_known = True
    elif src_ext and is_supported_extension(src_ext):
        fmt_known = True

    if not fmt_known:
        detail = "content_type=%s ext=%s" % (content_type.split(";", 1)[0][:40], src_ext[:10])
        log.info("normalize: unsupported format (%s) -> UNSUPPORTED_AUDIO_FORMAT", detail)
        return NormalizeResult(False, None, VoiceErrorCode.UNSUPPORTED_AUDIO_FORMAT, detail)

    if not _ffmpeg_available():
        log.warning("normalize: ffmpeg not on PATH -> DECODE_FAILED (graceful degrade)")
        return NormalizeResult(False, None, VoiceErrorCode.DECODE_FAILED, "ffmpeg unavailable")

    # Write the source blob to a temp file, decode to a second temp WAV. Reading
    # ffmpeg from a pipe would work too, but a temp file keeps the command
    # simple and avoids partial-pipe edge cases on malformed containers.
    src_fd, src_path = tempfile.mkstemp(suffix=src_ext or ".bin", prefix="voice_src_")
    dst_fd, dst_path = tempfile.mkstemp(suffix=".wav", prefix="voice_norm_")
    import os

    os.close(dst_fd)
    try:
        with os.fdopen(src_fd, "wb") as f:
            f.write(src_bytes)

        from substrate.execution.cpu_gate import gated_subprocess_run

        # -vn: ignore any video stream; -ac 1 mono; -ar 16000; s16le PCM in WAV.
        # -y overwrite (dst temp already exists). -nostdin so it never blocks.
        result = gated_subprocess_run(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                src_path,
                "-vn",
                "-ac",
                str(CHANNELS),
                "-ar",
                str(SAMPLE_RATE),
                "-c:a",
                "pcm_s16le",
                dst_path,
            ],
            caller=caller,
            timeout=30,
        )

        if result is None:
            # gate blocked (host overloaded) OR binary vanished mid-flight.
            log.warning("normalize: ffmpeg gated/blocked -> DECODE_FAILED")
            _safe_unlink(dst_path)
            return NormalizeResult(
                False, None, VoiceErrorCode.DECODE_FAILED, "cpu gate blocked ffmpeg"
            )

        if result.returncode != 0 or not _nonempty_file(dst_path):
            log.info(
                "normalize: ffmpeg decode failed (rc=%s) -> DECODE_FAILED",
                result.returncode,
            )
            _safe_unlink(dst_path)
            return NormalizeResult(
                False,
                None,
                VoiceErrorCode.DECODE_FAILED,
                "ffmpeg rc=%s" % result.returncode,
            )

        log.info("normalize: decoded to PCM WAV 16k mono (%d src bytes)", len(src_bytes))
        return NormalizeResult(True, dst_path, None, "ok")
    finally:
        _safe_unlink(src_path)


def _safe_unlink(path: str) -> None:
    import os

    try:
        os.unlink(path)
    except OSError as e:  # noqa: BLE001 - non-fatal cleanup
        log.debug("temp cleanup failed for %s: %s", Path(path).name, e)


def _nonempty_file(path: str) -> bool:
    import os

    try:
        return os.path.getsize(path) > 44  # WAV header is 44 bytes; >44 = has PCM
    except OSError:
        return False
