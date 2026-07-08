"""P4S31 Voice Convergence — canonical VoiceSession runtime upgrades (Commit 2).

Covers the injectable warm engine (GAP A), shaped-spoken-text response (GAP K),
_ended ENDED precedence (GAP C), content-type-branched blob preflight (raw PCM vs
container), and resume() SYSTEM-skip / consecutive-AGENT fold.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from substrate.execution.voice import session as S
from substrate.execution.voice.store import (
    VoiceSessionRecord,
    VoiceSessionRecordStatus,
    VoiceTurn,
    VoiceTurnSource,
)


def _fake_engine(transcript: str = "hello there"):
    fe = MagicMock()
    fe.intelligent = MagicMock()
    fe.intelligent.transcribe_fast = MagicMock(return_value=transcript)
    fe.should_respond = MagicMock(return_value=(True, "question"))
    fe.route_query = MagicMock(return_value="engine-routed reply")
    fe.speak = MagicMock(return_value="/tmp/out.wav")
    return fe


def test_engine_param_retained() -> None:
    # GAP A: a passed engine IS self._engine (is-identity); default constructs one.
    sentinel = _fake_engine()
    sess = S.VoiceSession(engine=sentinel)
    assert sess._engine is sentinel


def test_canonical_path_speaks_spoken_text() -> None:
    # GAP K: TTS speaks the shaped spoken_text, never the raw long text.
    from substrate.organism.advisor_conversation import AdvisorResponse

    fe = _fake_engine()

    def converse_fn(content, conversation_id, source, voice_turn_id):
        return AdvisorResponse(
            text="raw", conversation_id=conversation_id, intent="q", spoken_text="shaped"
        )

    sess = S.VoiceSession(engine=fe, converse_fn=converse_fn)
    ex = sess.process_text("hi")
    fe.speak.assert_called_once_with("shaped")
    assert ex.spoken_text == "shaped"


def test_stopped_session_record_is_ended() -> None:
    # GAP C: _ended takes strict precedence over the operational status.
    sess = S.VoiceSession(engine=_fake_engine())
    sess.start()
    sess.stop()
    rec = sess.to_record()
    assert rec.status == VoiceSessionRecordStatus.ENDED


def test_transcribe_receiver_is_intelligent() -> None:
    # STT goes through self._engine.intelligent.transcribe_fast, never a bare
    # self._engine.transcribe (which does not exist).
    fe = _fake_engine()
    assert not hasattr(fe, "transcribe") or isinstance(fe.transcribe, MagicMock)
    sess = S.VoiceSession(engine=fe)
    sess.process_audio_file("/tmp/x.wav")
    fe.intelligent.transcribe_fast.assert_called_once()


def test_empty_blob_sets_error_code() -> None:
    fe = _fake_engine()
    sess = S.VoiceSession(engine=fe)
    ex = sess.process_audio_blob(b"", content_type="audio/pcm")
    assert ex.error_code == "EMPTY_AUDIO_BLOB"
    assert ex.classification == ""
    fe.intelligent.transcribe_fast.assert_not_called()


def test_silent_pcm_sets_error_code() -> None:
    fe = _fake_engine()
    sess = S.VoiceSession(engine=fe)
    # 1 second of pure-silence PCM16 → SILENT_AUDIO, STT skipped.
    silent = b"\x00\x00" * 16000
    ex = sess.process_audio_blob(silent, content_type="audio/pcm")
    assert ex.error_code == "SILENT_AUDIO"
    fe.intelligent.transcribe_fast.assert_not_called()


def test_container_blob_calls_normalize(monkeypatch) -> None:
    # A container content type takes the normalize path, not raw preflight.
    import umh.voice_preflight as pf

    called = {"normalize": 0}

    class _Norm:
        ok = True
        wav_path = "/tmp/normalized.wav"
        error_code = None

    def fake_normalize(src_bytes, *, content_type="", src_ext="", caller=""):
        called["normalize"] += 1
        return _Norm()

    monkeypatch.setattr(pf, "normalize_to_pcm_wav", fake_normalize)
    fe = _fake_engine()
    sess = S.VoiceSession(engine=fe)
    sess.process_audio_blob(b"RIFFfake-webm-bytes", content_type="audio/webm")
    assert called["normalize"] == 1


def test_resume_skips_system_turns() -> None:
    r = VoiceSessionRecord(session_id="vs_r", node_id="n", role_slug="ea")
    r.turns = [
        VoiceTurn("t1", VoiceTurnSource.SYSTEM, "lifecycle", ""),
        VoiceTurn("t2", VoiceTurnSource.USER, "real q", ""),
        VoiceTurn("t3", VoiceTurnSource.AGENT, "real a", ""),
        VoiceTurn("t4", VoiceTurnSource.SYSTEM, "role switch", ""),
    ]
    sess = S.VoiceSession.resume(r, engine=_fake_engine())
    responded = [e for e in sess._state.exchanges if e.responded]
    assert len(responded) == 1
    assert responded[0].utterance == "real q"
    assert responded[0].response_text == "real a"


def test_resume_folds_consecutive_agent() -> None:
    # [USER, AGENT, AGENT] -> one responded exchange, last agent wins.
    r = VoiceSessionRecord(session_id="vs_f", node_id="n", role_slug="ea")
    r.turns = [
        VoiceTurn("t1", VoiceTurnSource.USER, "q", ""),
        VoiceTurn("t2", VoiceTurnSource.AGENT, "a1", ""),
        VoiceTurn("t3", VoiceTurnSource.AGENT, "a2", ""),
    ]
    sess = S.VoiceSession.resume(r, engine=_fake_engine())
    responded = [e for e in sess._state.exchanges if e.responded]
    assert len(responded) == 1
    assert responded[-1].response_text == "a2"


def test_error_code_field_serializes() -> None:
    # GAP7: a failed exchange carries a typed error_code and an EMPTY
    # classification — mutually exclusive — so the WS can relay it verbatim.
    ex = S.VoiceExchange(error_code="SILENT_AUDIO")
    assert ex.error_code == "SILENT_AUDIO"
    assert ex.classification == ""
    # a successful exchange has the inverse
    ok = S.VoiceExchange(utterance="hi", classification="question", responded=True)
    assert ok.error_code == ""
    assert ok.classification == "question"


def test_resume_from_real_bridge_record() -> None:
    # A runtime submit then resume(engine=fake) reconstructs the exchange.
    from substrate.organism.advisor_conversation import AdvisorResponse

    def converse_fn(content, conversation_id, source, voice_turn_id):
        return AdvisorResponse(
            text="answer", conversation_id=conversation_id, intent="q", spoken_text="ans"
        )

    live = S.VoiceSession(session_id="vs_live", engine=_fake_engine(), converse_fn=converse_fn)
    live.process_text("a real question")
    rec = live.to_record()
    resumed = S.VoiceSession.resume(rec, engine=_fake_engine())
    responded = [e for e in resumed._state.exchanges if e.responded]
    assert len(responded) == 1
    assert responded[0].utterance == "a real question"
