#!/usr/bin/env python3
"""Generate SMALL synthetic voice fixtures for the P4S-31D1-C STT pipeline tests.

All fixtures are produced programmatically with the stdlib (``wave`` + ``struct``
+ ``math``). No downloads, no models, no ffmpeg. Every WAV is mono / 16-bit /
16 kHz — exactly the shape ``umh/voice_server.save_wav`` writes and the shape the
STT call must receive — and each file is kept well under 100 KB.

Run directly to (re)materialize the fixtures on disk:

    python3 tests/fixtures/voice/generate_fixtures.py

The test module (``tests/test_p4s31d1c_stt_fixtures.py``) also imports the
builder functions and regenerates in-memory, so the committed files are a
convenience/inspection artifact — the tests do not depend on them existing.

Fixtures
--------
known_good_tone.wav
    A short formant-like burst (two summed sine partials with an amplitude
    envelope) at clear energy. Proves the pipeline can feed decodable,
    above-threshold PCM to STT.

mid_sentence_pause.wav
    energy → a short intra-utterance silence gap → energy. The gap is SHORTER
    than the server's ``SILENCE_END_UTTERANCE_S`` finalize window, so a
    correct VAD treats the whole thing as ONE utterance, not two.

silence.wav
    Near-zero samples (dither only). Proves the SILENT/NO-SPEECH typed path
    rather than a hang or a spurious transcript.

ios_audio_mp4.marker.json
    NOT real AAC. Documents what a real iOS ``audio/mp4`` blob needs
    (container/codec/decode-before-STT) since we cannot synthesize valid AAC
    without ffmpeg/libs. The matching test is xfail-marked with a clear reason.
"""

from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 16000  # matches umh/voice_server.SAMPLE_RATE
_FIXTURE_DIR = Path(__file__).resolve().parent


def _pack_pcm16(samples: list[int]) -> bytes:
    """Clamp to int16 range and pack as little-endian signed 16-bit PCM."""
    clamped = [max(-32768, min(32767, int(s))) for s in samples]
    return struct.pack("<%dh" % len(clamped), *clamped)


def tone_samples(
    duration_s: float,
    f0: float = 180.0,
    f1: float = 720.0,
    amplitude: int = 9000,
    sample_rate: int = SAMPLE_RATE,
) -> list[int]:
    """A formant-like burst: fundamental + a higher partial, amplitude-enveloped.

    Deliberately NOT pure speech — real Whisper on a synth tone is unreliable,
    which is exactly why the tests mock the network STT call and assert on what
    the pipeline HANDS it (decoded mono-16k PCM above the speech threshold),
    not on a returned transcript string.
    """
    n = int(duration_s * sample_rate)
    out: list[int] = []
    for i in range(n):
        t = i / sample_rate
        # Hann-ish envelope so the burst has a soft attack/decay (no clicks).
        env = math.sin(math.pi * (i / n)) if n > 1 else 1.0
        val = (
            amplitude
            * env
            * (0.7 * math.sin(2 * math.pi * f0 * t) + 0.3 * math.sin(2 * math.pi * f1 * t))
        )
        out.append(int(val))
    return out


def silence_samples(
    duration_s: float,
    dither: int = 2,
    sample_rate: int = SAMPLE_RATE,
) -> list[int]:
    """Near-zero samples. A tiny deterministic dither keeps it from being a
    literal all-zero buffer (more realistic; still far below the 0.02 level
    threshold and below the RMS the server treats as speech)."""
    n = int(duration_s * sample_rate)
    # Deterministic low-amplitude triangle dither, |value| <= dither.
    return [((i % (2 * dither + 1)) - dither) for i in range(n)]


def known_good_pcm() -> bytes:
    """~0.6 s clear formant burst — well above MIN_AUDIO_BYTES and threshold."""
    return _pack_pcm16(tone_samples(0.6))


def mid_sentence_pause_pcm() -> bytes:
    """energy(0.5s) → silence(1.0s intra-utterance gap) → energy(0.5s).

    The 1.0 s gap is intentionally shorter than the server's
    ``SILENCE_END_UTTERANCE_S`` (1.8 s) finalize window, so a correct VAD keeps
    this as ONE utterance. Total ~2.0 s.
    """
    return _pack_pcm16(
        tone_samples(0.5) + silence_samples(1.0) + tone_samples(0.5),
    )


def silence_pcm() -> bytes:
    """~0.8 s of near-silence — long enough to clear MIN_AUDIO_BYTES so the
    silent-path assertion isn't confused with the too-short-audio path."""
    return _pack_pcm16(silence_samples(0.8))


def write_wav(pcm: bytes, path: Path, sample_rate: int = SAMPLE_RATE) -> Path:
    """Write mono / 16-bit / ``sample_rate`` WAV — mirrors save_wav()."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return path


# What a real iOS audio/mp4 blob needs before it can reach Whisper. This is a
# PLACEHOLDER descriptor, not audio — synthesizing valid AAC needs ffmpeg/libs.
IOS_MP4_MARKER = {
    "record": "ios_audio_mp4_marker",
    "why_placeholder": (
        "iOS Safari MediaRecorder emits audio/mp4 (AAC in an MP4/M4A "
        "container). Valid AAC cannot be synthesized with the Python stdlib "
        "(no encoder); producing a fake .mp4 would be dishonest fixture data. "
        "This marker documents the contract the decode seam must satisfy."
    ),
    "blob": {
        "mime": "audio/mp4",
        "codec": "aac (mp4a.40.2)",
        "container": "mp4 / m4a",
        "typical_sample_rate_hz": 44100,
        "channels": 1,
    },
    "decode_requirement": [
        "audio/mp4 is NOT raw PCM — it MUST be demuxed + decoded to PCM first",
        "decoded PCM must be downsampled to 16000 Hz mono int16 before STT",
        "the server STT path (save_wav -> _transcribe_groq) assumes 16k mono "
        "PCM already; an mp4 blob handed to it un-decoded would be wrong",
        "Groq whisper-large-v3-turbo DOES accept m4a/mp4 as an uploaded file, "
        "so the decode may also be delegated to Groq — but the LOCAL "
        "faster-whisper fallback needs real decode-to-PCM first",
    ],
    "route": "browser MediaRecorder(audio/mp4) -> upload seam -> decode-to-PCM16-16k -> STT",
}


def main() -> None:
    write_wav(known_good_pcm(), _FIXTURE_DIR / "known_good_tone.wav")
    write_wav(mid_sentence_pause_pcm(), _FIXTURE_DIR / "mid_sentence_pause.wav")
    write_wav(silence_pcm(), _FIXTURE_DIR / "silence.wav")
    (_FIXTURE_DIR / "ios_audio_mp4.marker.json").write_text(
        json.dumps(IOS_MP4_MARKER, indent=2) + "\n", encoding="utf-8"
    )
    for name in (
        "known_good_tone.wav",
        "mid_sentence_pause.wav",
        "silence.wav",
        "ios_audio_mp4.marker.json",
    ):
        p = _FIXTURE_DIR / name
        print(f"wrote {p.name}: {p.stat().st_size} bytes")


if __name__ == "__main__":
    main()
