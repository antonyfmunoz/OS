"""P4S-31D1-C — STT pipeline fixture tests.

Proves the ``umh/voice_server.py`` capture → decode → STT path end-to-end with
SMALL synthetic WAV fixtures (generated programmatically in
``tests/fixtures/voice/generate_fixtures.py`` — no downloads, no models).

The network STT call (``transcribe`` → ``_transcribe_groq``) is MOCKED. We do
NOT assert on a transcript string (real Whisper on a synth tone is unreliable —
that is the whole reason to mock). Instead we assert on **what the pipeline
hands to STT**: a decodable WAV that is mono / 16-bit / 16 kHz PCM — never a raw
incompatible blob.

Covered:
  1. known-good tone → pipeline feeds ONE decodable mono-16k-PCM WAV to STT,
     and a returned transcript is delivered as a final TranscriptEvent.
  2. mid-sentence-pause → the intra-utterance gap (< finalize window) yields
     exactly ONE utterance/STT call, not two (no early finalize).
  3. silence → the SILENT/NO-SPEECH typed path: an empty final transcript,
     STT never invoked, no hang.
  4. iOS audio/mp4 → xfail-marked placeholder: documents that an mp4 blob must
     be decoded to PCM before STT; we cannot synthesize valid AAC in-stdlib.
  5. STT input contract: the WAV every path writes is mono/16-bit/16 kHz.

Design note — driving the server:
  ``process_utterance`` is a closure inside ``handle_voice``. To exercise the
  REAL VAD + buffering + ``save_wav`` path (not a reimplementation), each test
  drives ``handle_voice`` with a fake websocket that replays a
  mic_start → binary-PCM-chunks → mic_stop script, then inspects the JSON the
  server sent back and the WAV bytes STT received (captured by the mock).
"""

from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import sys
import wave
from pathlib import Path
from unittest import mock

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SERVER_PATH = _REPO_ROOT / "umh" / "voice_server.py"
_FIXTURE_DIR = _REPO_ROOT / "tests" / "fixtures" / "voice"

sys.path.insert(0, str(_FIXTURE_DIR))
import generate_fixtures as gf  # noqa: E402  (fixture builders, imported after path insert)


def _load_server_module():
    spec = importlib.util.spec_from_file_location("voice_server_p4s31d1c", _SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def vs():
    return _load_server_module()


# ── Fake websocket that replays a scripted client session ────────────────────


class _FakeWebSocket:
    """Minimal async-iterable WS stub matching what ``handle_voice`` uses.

    ``incoming`` is the scripted client → server message stream (str = JSON
    control, bytes = PCM chunk). Everything the server sends back is recorded:
    JSON control frames in ``sent_json``, binary frames in ``sent_binary``.
    """

    remote_address = ("127.0.0.1", 0)

    def __init__(self, incoming: list):
        self._incoming = list(incoming)
        self.sent_json: list[dict] = []
        self.sent_binary: list[bytes] = []

    def __aiter__(self):
        async def _gen():
            for msg in self._incoming:
                yield msg

        return _gen()

    async def send(self, data):
        if isinstance(data, (bytes, bytearray)):
            self.sent_binary.append(bytes(data))
        else:
            self.sent_json.append(json.loads(data))

    async def close(self, *args, **kwargs):  # pragma: no cover - not exercised
        return None


def _pcm_chunks(pcm: bytes, chunk_ms: int = 100, sample_rate: int = 16000) -> list[bytes]:
    """Slice a PCM16 buffer into fixed-duration chunks, like the browser sends."""
    bytes_per_chunk = int(sample_rate * (chunk_ms / 1000.0)) * 2
    return [pcm[i : i + bytes_per_chunk] for i in range(0, len(pcm), bytes_per_chunk)]


def _drive(vs, incoming: list, transcribe_return: str = "ok"):
    """Run ``handle_voice`` against a scripted session with STT mocked.

    Returns (fake_ws, captured_wav_paths, captured_wav_bytes) where the WAV
    captures are exactly what the pipeline handed to the (mocked) ``transcribe``.
    """
    captured_paths: list[str] = []
    captured_bytes: list[bytes] = []

    def _fake_transcribe(path: str) -> str:
        captured_paths.append(path)
        # Read the WAV the pipeline wrote BEFORE it is unlinked in the finally.
        with open(path, "rb") as f:
            captured_bytes.append(f.read())
        return transcribe_return

    ws = _FakeWebSocket(incoming)
    with mock.patch.object(vs, "transcribe", side_effect=_fake_transcribe) as m:
        asyncio.run(vs.handle_voice(ws))
    ws._transcribe_mock = m  # attach for call-count assertions
    return ws, captured_paths, captured_bytes


def _assert_mono_16k_pcm16(wav_bytes: bytes) -> int:
    """Assert a WAV blob is decodable mono / 16-bit / 16 kHz. Returns frame count."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnchannels() == 1, "STT must receive MONO audio"
        assert wf.getsampwidth() == 2, "STT must receive 16-bit PCM"
        assert wf.getframerate() == 16000, "STT must receive 16 kHz audio"
        return wf.getnframes()


# ── 1. known-good tone: decodable PCM fed to STT, transcript delivered ───────


def test_known_good_feeds_decoded_mono16k_pcm_to_stt(vs):
    pcm = gf.known_good_pcm()
    script = (
        [json.dumps({"type": "mic_start", "session_id": "vt-known-good"})]
        + _pcm_chunks(pcm)
        + [json.dumps({"type": "mic_stop"})]
    )
    ws, paths, wavs = _drive(vs, script, transcribe_return="transcribed text")

    # Pipeline fed STT exactly once, with a real decodable WAV (not a raw blob).
    assert len(wavs) == 1, "known-good audio should produce exactly one STT call"
    frames = _assert_mono_16k_pcm16(wavs[0])
    assert frames > 0, "STT WAV must contain PCM frames"

    # Temp WAV is unlinked after the call (privacy / no-persist invariant).
    assert not Path(paths[0]).exists(), "utterance temp WAV must be unlinked"

    # A final TranscriptEvent carrying the (mocked) text is delivered.
    finals = [m for m in ws.sent_json if m.get("type") == "transcript" and m.get("final")]
    assert finals, "a final transcript event must be sent"
    assert finals[-1]["text"] == "transcribed text"


# ── 2. mid-sentence pause: ONE utterance, not two ────────────────────────────


def test_mid_sentence_pause_is_one_utterance_not_two(vs):
    # The gap (1.0 s) is shorter than SILENCE_END_UTTERANCE_S (1.8 s), so the
    # in-stream VAD must NOT finalize during the gap. mic_stop flushes the
    # single accumulated utterance.
    assert 1.0 < vs.SILENCE_END_UTTERANCE_S, "fixture gap must be < finalize window"

    pcm = gf.mid_sentence_pause_pcm()
    script = (
        [json.dumps({"type": "mic_start", "session_id": "vt-pause"})]
        + _pcm_chunks(pcm)
        + [json.dumps({"type": "mic_stop"})]
    )
    ws, _paths, wavs = _drive(vs, script, transcribe_return="one utterance")

    assert len(wavs) == 1, (
        "a sentence-internal pause must yield ONE utterance, not an early "
        "finalize that splits it into two STT calls"
    )
    # The single WAV must span both speech bursts (i.e. include the gap) — so it
    # is longer than either burst alone. speech(0.5)+gap(1.0)+speech(0.5) ≈ 2.0s.
    frames = _assert_mono_16k_pcm16(wavs[0])
    assert frames >= int(1.5 * 16000), "one-utterance WAV should span the whole span incl. gap"


# ── 3. silence: SILENT / NO-SPEECH typed path, no hang, STT not called ───────


def test_silence_yields_no_speech_path_without_calling_stt(vs):
    pcm = gf.silence_pcm()
    script = (
        [json.dumps({"type": "mic_start", "session_id": "vt-silence"})]
        + _pcm_chunks(pcm)
        + [json.dumps({"type": "mic_stop"})]
    )
    ws, _paths, wavs = _drive(vs, script)

    # No speech ever crossed threshold → STT is never invoked (not a hang).
    assert len(wavs) == 0, "silence must not reach STT"
    assert ws._transcribe_mock.call_count == 0

    # The server emits the empty final transcript (the NO-SPEECH typed result).
    finals = [m for m in ws.sent_json if m.get("type") == "transcript" and m.get("final")]
    assert finals, "silence must still produce a final (empty) transcript event"
    assert finals[-1]["text"] == "", "NO-SPEECH path delivers an empty transcript"


def test_silence_does_not_hang(vs):
    # Regression guard: driving the whole session over silence must return
    # promptly (the async run completing at all proves no deadlock/await-hang).
    pcm = gf.silence_pcm()
    script = (
        [json.dumps({"type": "mic_start"})] + _pcm_chunks(pcm) + [json.dumps({"type": "mic_stop"})]
    )

    # asyncio.run inside _drive; wrap in wait_for to fail loudly on a hang.
    async def _run():
        ws = _FakeWebSocket(script)
        with mock.patch.object(vs, "transcribe", return_value=""):
            await asyncio.wait_for(vs.handle_voice(ws), timeout=10)
        return ws

    ws = asyncio.run(_run())
    assert any(m.get("type") == "vad_status" and m.get("active") is False for m in ws.sent_json)


# ── 4. STT input contract holds for every generated fixture ──────────────────


@pytest.mark.parametrize(
    "builder",
    [gf.known_good_pcm, gf.mid_sentence_pause_pcm],
    ids=["known_good", "mid_sentence_pause"],
)
def test_save_wav_emits_mono_16k_16bit(vs, builder, tmp_path):
    """The WAV the server writes (and hands to STT) is always mono/16k/16-bit."""
    pcm = builder()
    out = tmp_path / "utt.wav"
    vs.save_wav(pcm, str(out))
    frames = _assert_mono_16k_pcm16(out.read_bytes())
    assert frames == len(pcm) // 2


def test_committed_fixture_files_are_small_and_valid():
    """The committed fixtures exist, are < 100 KB, and are valid mono-16k WAVs."""
    gf.main()  # (re)materialize deterministically
    for name in ("known_good_tone.wav", "mid_sentence_pause.wav", "silence.wav"):
        p = _FIXTURE_DIR / name
        assert p.exists(), f"fixture {name} must exist"
        assert p.stat().st_size < 100_000, f"fixture {name} must be < 100 KB"
        _assert_mono_16k_pcm16(p.read_bytes())


# ── 5. iOS audio/mp4 — honest xfail placeholder ──────────────────────────────


def test_ios_mp4_marker_documents_decode_requirement():
    """The mp4 marker is a truthful placeholder, not fake audio."""
    marker = json.loads((_FIXTURE_DIR / "ios_audio_mp4.marker.json").read_text())
    assert marker["blob"]["mime"] == "audio/mp4"
    assert marker["blob"]["codec"].startswith("aac")
    # It must state, in plain terms, that mp4 is not raw PCM and needs decode.
    joined = " ".join(marker["decode_requirement"]).lower()
    assert "decode" in joined and "pcm" in joined and "16000" in joined


@pytest.mark.xfail(
    reason=(
        "iOS Safari MediaRecorder emits audio/mp4 (AAC). Valid AAC cannot be "
        "synthesized with the Python stdlib (no encoder), and handing an "
        "un-decoded mp4 blob to save_wav()/faster-whisper is invalid — mp4 is "
        "not raw PCM. This asserts the DESIRED end-state: the server routes an "
        "mp4 blob through a decode-to-PCM16-16k seam before STT. That decode "
        "seam is not implemented in voice_server.py (the WS transport already "
        "delivers PCM16), so this is a documented gap, not a green claim."
    ),
    strict=True,
)
def test_ios_mp4_blob_is_decoded_before_stt(vs):
    # A real audio/mp4 blob is NOT 16k mono PCM. There is no decode seam in
    # voice_server.py that accepts a container blob — the WS path assumes PCM16.
    # We assert the (not-yet-present) capability so this fails until built.
    assert hasattr(vs, "decode_container_to_pcm16"), (
        "no mp4/container decode seam exists on voice_server yet"
    )
