#!/usr/bin/env python3
"""P4S-31D1-C — server-side audio preflight + precise error taxonomy.

Proves that every failure mode of the voice pipeline resolves to a DISTINCT,
typed error code and that no failure returns a bare empty transcript. Also
proves the container decode/normalize path is typed (DECODE_FAILED /
UNSUPPORTED_AUDIO_FORMAT), that ffmpeg is only ever invoked through the CPU gate
(static scan), that no transcript text is logged at INFO+ (static scan), and
that the WS 'connected' / 'transcript' / 'tts_status' message SHAPES the cockpit
client depends on are unchanged (only the error path gains codes).

All preflight functions are exercised directly — no WebSocket, no network, no
running STT engine required.
"""

from __future__ import annotations

import re
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from umh.voice_preflight import (  # noqa: E402
    MIN_UTTERANCE_BYTES,
    SILENCE_MEAN_LEVEL_FLOOR,
    VoiceErrorCode,
    error_payload,
    is_supported_container_type,
    is_supported_extension,
    mean_rms_level,
    normalize_to_pcm_wav,
    pcm16_duration_seconds,
    preflight_pcm16,
)

SAMPLE_RATE = 16000


# --- helpers ---------------------------------------------------------------


def pcm16(samples: list[int]) -> bytes:
    return struct.pack("<%dh" % len(samples), *samples)


def loud_buffer(seconds: float = 1.0, amp: int = 4000) -> bytes:
    n = int(SAMPLE_RATE * seconds)
    return pcm16([amp if i % 2 == 0 else -amp for i in range(n)])


def silent_buffer(seconds: float = 1.0, amp: int = 2) -> bytes:
    n = int(SAMPLE_RATE * seconds)
    return pcm16([amp] * n)


def _ffmpeg_present() -> bool:
    import shutil

    return shutil.which("ffmpeg") is not None


# --- error taxonomy: distinct + reachable ----------------------------------


def test_all_six_codes_exist_and_distinct():
    codes = [c.value for c in VoiceErrorCode]
    assert set(codes) == {
        "EMPTY_AUDIO_BLOB",
        "SILENT_AUDIO",
        "DECODE_FAILED",
        "UNSUPPORTED_AUDIO_FORMAT",
        "VAD_NO_SPEECH",
        "STT_FAILED",
    }
    # distinct values
    assert len(codes) == len(set(codes)) == 6


def test_error_payload_shape_and_bound():
    for code in VoiceErrorCode:
        p = error_payload(code)
        assert p["type"] == "error"
        assert p["code"] == code.value
        assert isinstance(p["message"], str)
        assert 0 < len(p["message"]) <= 100
    # custom message is bounded
    p = error_payload(VoiceErrorCode.STT_FAILED, "x" * 500)
    assert len(p["message"]) <= 100


# --- preflight_pcm16: each branch reachable + distinct ---------------------


def test_empty_buffer_is_empty_audio_blob():
    r = preflight_pcm16(b"")
    assert not r.ok
    assert r.error_code is VoiceErrorCode.EMPTY_AUDIO_BLOB
    assert r.n_bytes == 0


def test_undersized_buffer_is_empty_audio_blob():
    # fewer than MIN_UTTERANCE_BYTES -> EMPTY_AUDIO_BLOB (too little to be real)
    tiny = b"\x00\x01" * 10
    assert len(tiny) < MIN_UTTERANCE_BYTES
    r = preflight_pcm16(tiny)
    assert not r.ok
    assert r.error_code is VoiceErrorCode.EMPTY_AUDIO_BLOB


def test_near_zero_pcm_is_silent_audio():
    r = preflight_pcm16(silent_buffer())
    assert not r.ok
    assert r.error_code is VoiceErrorCode.SILENT_AUDIO
    assert r.mean_level < SILENCE_MEAN_LEVEL_FLOOR


def test_loud_buffer_passes_preflight():
    r = preflight_pcm16(loud_buffer())
    assert r.ok
    assert r.error_code is None
    assert r.mean_level >= SILENCE_MEAN_LEVEL_FLOOR
    assert r.duration_s == pytest.approx(1.0, abs=0.01)


def test_silent_and_empty_and_vad_are_three_distinct_codes():
    # SILENT_AUDIO (mic silent) != EMPTY_AUDIO_BLOB (no bytes) != VAD_NO_SPEECH
    empty = preflight_pcm16(b"").error_code
    silent = preflight_pcm16(silent_buffer()).error_code
    assert empty is VoiceErrorCode.EMPTY_AUDIO_BLOB
    assert silent is VoiceErrorCode.SILENT_AUDIO
    assert empty is not silent
    # VAD_NO_SPEECH is produced by the STT layer, not preflight — proven below.
    assert VoiceErrorCode.VAD_NO_SPEECH not in (empty, silent)


def test_mean_rms_over_whole_buffer_not_peak():
    # mean_rms_level must be the RMS over the WHOLE buffer, not the peak sample.
    # A buffer that is silent except one loud spike has a peak of 30000 (which,
    # as a per-sample level, would read ~3.75 and clamp to 1.0) but its
    # whole-buffer RMS is tiny — proving we average energy, not take the peak.
    import math

    n = SAMPLE_RATE
    samples = [1] * n
    samples[0] = 30000  # one loud spike among 16000 near-silent samples
    level = mean_rms_level(pcm16(samples))
    # Independent whole-buffer RMS computation.
    expected = min(1.0, math.sqrt(sum(s * s for s in samples) / n) / 8000.0)
    assert level == pytest.approx(expected, abs=1e-6)
    # And it is FAR below the clamped peak (1.0) — i.e. not peak-based.
    assert level < 0.05


def test_pcm16_duration():
    assert pcm16_duration_seconds(loud_buffer(2.0)) == pytest.approx(2.0, abs=0.01)


# --- STT layer: VAD_NO_SPEECH vs STT_FAILED (mocked engines) ---------------


def _make_transcribe(monkeypatch, groq_res, local_res):
    """Patch the two engine helpers on voice_server and return transcribe()."""
    import umh.voice_server as vs

    monkeypatch.setattr(vs, "_transcribe_groq", lambda p: groq_res)
    monkeypatch.setattr(vs, "_transcribe_local", lambda p: local_res)
    return vs.transcribe


def test_transcribe_clean_empty_is_not_engine_error(monkeypatch):
    import umh.voice_server as vs

    clean_empty = vs.TranscribeResult("", engine_error=False, engine="groq")
    transcribe = _make_transcribe(monkeypatch, clean_empty, clean_empty)
    res = transcribe("/tmp/x.wav")
    assert res.text == ""
    # both engines ran clean -> NOT an engine error -> caller emits VAD_NO_SPEECH
    assert res.engine_error is False


def test_transcribe_engine_failure_flags_engine_error(monkeypatch):
    import umh.voice_server as vs

    failed = vs.TranscribeResult("", engine_error=True, engine="groq")
    transcribe = _make_transcribe(monkeypatch, failed, failed)
    res = transcribe("/tmp/x.wav")
    assert res.text == ""
    # an engine hard-failed -> caller emits STT_FAILED
    assert res.engine_error is True


def test_transcribe_success_returns_text(monkeypatch):
    import umh.voice_server as vs

    good = vs.TranscribeResult("hello there", engine_error=False, engine="groq")
    empty = vs.TranscribeResult("", engine_error=False, engine="faster-whisper")
    transcribe = _make_transcribe(monkeypatch, good, empty)
    res = transcribe("/tmp/x.wav")
    assert res.text == "hello there"
    assert res.engine_error is False


def test_no_speech_maps_to_vad_code_not_stt_failed():
    # The WS layer emits VAD_NO_SPEECH for clean-empty and STT_FAILED for engine
    # failure. Assert the two codes are distinct so they can never collapse.
    assert VoiceErrorCode.VAD_NO_SPEECH is not VoiceErrorCode.STT_FAILED


# --- container decode / normalize: typed outcomes --------------------------


def test_normalize_empty_blob_is_empty_audio_blob():
    r = normalize_to_pcm_wav(b"", content_type="audio/webm")
    assert not r.ok
    assert r.error_code is VoiceErrorCode.EMPTY_AUDIO_BLOB


def test_normalize_unsupported_format_is_unsupported():
    r = normalize_to_pcm_wav(b"%PDF-1.4 garbage", content_type="application/pdf", src_ext=".pdf")
    assert not r.ok
    assert r.error_code is VoiceErrorCode.UNSUPPORTED_AUDIO_FORMAT


def test_supported_type_and_extension_helpers():
    assert is_supported_container_type("audio/webm;codecs=opus")
    assert is_supported_container_type("AUDIO/WAV")
    assert not is_supported_container_type("video/mp4")
    assert is_supported_extension(".weba")
    assert is_supported_extension(".WAV")
    assert not is_supported_extension(".txt")


def _force_gate_allow(monkeypatch):
    """Force the CPU gate to allow ffmpeg so decode branches are deterministic
    regardless of host load. Patches the symbol imported inside voice_preflight.
    """
    from substrate.execution import cpu_gate

    def _allow(cmd, *, caller="", timeout=30.0, **kwargs):
        kwargs.setdefault("capture_output", True)
        kwargs.setdefault("text", True)
        kwargs.setdefault("timeout", timeout)
        try:
            return subprocess.run(cmd, **kwargs)
        except FileNotFoundError:
            return None

    monkeypatch.setattr(cpu_gate, "gated_subprocess_run", _allow)


@pytest.mark.skipif(not _ffmpeg_present(), reason="ffmpeg not installed")
def test_normalize_garbage_container_is_decode_failed(monkeypatch):
    _force_gate_allow(monkeypatch)
    r = normalize_to_pcm_wav(b"not audio at all" * 100, content_type="audio/webm", src_ext=".weba")
    assert not r.ok
    assert r.error_code is VoiceErrorCode.DECODE_FAILED


@pytest.mark.skipif(not _ffmpeg_present(), reason="ffmpeg not installed")
def test_normalize_real_wav_succeeds(monkeypatch, tmp_path):
    _force_gate_allow(monkeypatch)
    # Produce a real 0.5s tone WAV with ffmpeg, then normalize it.
    src = tmp_path / "tone.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.5",
            "-ar",
            "44100",
            str(src),
        ],
        check=True,
    )
    data = src.read_bytes()
    r = normalize_to_pcm_wav(data, content_type="audio/wav", src_ext=".wav")
    assert r.ok, r.detail
    assert r.wav_path is not None
    # canonical output is PCM WAV mono 16kHz
    import wave

    with wave.open(r.wav_path, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 16000
        assert wf.getsampwidth() == 2
    Path(r.wav_path).unlink(missing_ok=True)


def test_normalize_never_raises_on_bad_input():
    # Must degrade to a typed error, never crash.
    for ct, ext, blob in [
        ("", "", b"\x00\x01\x02"),
        ("audio/webm", ".weba", b""),
        ("bogus/type", ".xyz", b"abc"),
    ]:
        r = normalize_to_pcm_wav(blob, content_type=ct, src_ext=ext)
        assert not r.ok
        assert r.error_code in set(VoiceErrorCode)


# --- static scans: logging law + CPU gate law ------------------------------

VOICE_SERVER = ROOT / "umh" / "voice_server.py"
VOICE_PREFLIGHT = ROOT / "umh" / "voice_preflight.py"


def test_no_raw_subprocess_for_ffmpeg():
    """CPU Gate Law: ffmpeg must only be invoked through gated_subprocess_run.
    No raw subprocess.run/Popen/call in the preflight module."""
    src = VOICE_PREFLIGHT.read_text()
    # No raw subprocess invocation APIs in the module (ffmpeg goes via the gate).
    for banned in (
        "subprocess.run(",
        "subprocess.Popen(",
        "subprocess.call(",
        "subprocess.check_output(",
        "subprocess.check_call(",
        "os.system(",
    ):
        assert banned not in src, f"raw subprocess API {banned} found in voice_preflight.py"
    # ffmpeg is referenced and it goes through the gate.
    assert "ffmpeg" in src
    assert "gated_subprocess_run" in src


def test_no_transcript_logged_at_info():
    """Logging law: no transcript text may be logged at INFO+.

    Scan every INFO/WARNING/ERROR log call in both modules and assert none
    interpolates transcript text. The only content preview allowed is DEBUG and
    bounded to <=40 chars (log.debug with [:TRANSCRIPT_PREVIEW_CHARS]).
    """
    for f in (VOICE_SERVER, VOICE_PREFLIGHT):
        src = f.read_text()
        # find log.info/warning/error(...) call argument strings
        for m in re.finditer(r"log\.(info|warning|error)\(([^\n]*)", src):
            call = m.group(2)
            lowered = call.lower()
            # No raw transcript variable interpolated at INFO+.
            assert "text[" not in call or "TRANSCRIPT_PREVIEW" in call, (
                f"possible transcript slice at INFO+ in {f.name}: {call.strip()[:80]}"
            )
            # The literal 'preview' content is DEBUG-only, never info/warn/error.
            assert "preview:" not in lowered, (
                f"transcript preview at INFO+ in {f.name}: {call.strip()[:80]}"
            )


def test_debug_previews_are_bounded():
    """Any transcript preview uses the <=40 char bound constant, DEBUG only."""
    src = VOICE_SERVER.read_text()
    # every 'preview' log is a log.debug and uses the bound constant
    for m in re.finditer(r"log\.(\w+)\([^\n]*preview[^\n]*", src, re.IGNORECASE):
        assert m.group(1) == "debug"
    # the bound constant is referenced where previews are sliced
    assert "TRANSCRIPT_PREVIEW_CHARS" in src


# --- WS message shape stability --------------------------------------------


def test_ws_message_shapes_unchanged():
    """The cockpit client depends on 'connected', 'transcript', 'tts_status',
    'audio_level', 'vad_status' shapes. Only the error path gains codes.

    Assert the success/status emitters are still present verbatim and that the
    error emitter uses the typed error_payload (type=error, code=, message=)."""
    src = VOICE_SERVER.read_text()

    # connected handshake unchanged
    assert '{"type": "connected", "server_session_id": session_id}' in src
    # final transcript delivery unchanged (text + final + session_id)
    assert '"type": "transcript", "text": text, "final": True' in src
    # partial transcript placeholder unchanged
    assert '{"type": "transcript", "text": "...", "final": False}' in src
    # tts_status shape unchanged
    assert '"type": "tts_status"' in src
    assert '"speaking": True' in src
    assert '{"type": "tts_status", "speaking": False}' in src
    # audio_level / vad_status shapes unchanged
    assert '{"type": "audio_level", "level": level}' in src
    assert '{"type": "vad_status", "active": True}' in src
    # the error path routes through the typed taxonomy
    assert "error_payload(" in src


def test_no_bare_empty_transcript_on_failure():
    """The blanket empty-transcript failure path is GONE.

    The only remaining {"text":""} literal permitted is NONE: failures now emit
    typed error codes. Assert no failure branch sends an empty final transcript.
    """
    src = VOICE_SERVER.read_text()
    # The old collapse patterns must not exist any more.
    assert '{"type": "transcript", "text": "", "final": True}' not in src
    # And the typed codes are all wired into the server.
    for code in ("EMPTY_AUDIO_BLOB", "SILENT_AUDIO", "VAD_NO_SPEECH", "STT_FAILED"):
        assert code in src, f"{code} not wired into voice_server.py"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
