"""P4S-31D1-C — voice capture signal contract (root-cause fix + client diagnostics).

The UserVoiceNote rail failed in production: recordings ran 30-40s and always
ended in "No speech detected". Root cause (diagnosed from the deployed bundle):
the CAPTURE AudioContext was created 'suspended' and never resumed, so
ScriptProcessor.onaudioprocess never fired, zero PCM chunks reached the server,
RMS stayed 0, and every recording finalized as NO_SPEECH.

These static checks pin the fix and the client-side diagnostics so the defect
cannot silently regress. (Runtime audio behavior is proven by the Class-A
browser run; these guard the source contract.)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

_API = Path(_WORKTREE) / "cockpit" / "src" / "renderer" / "api"
_VOICE_WS = _API / "voice-ws.ts"
_CONTROLLER = _API / "voice-controller.ts"


def _ws() -> str:
    return _VOICE_WS.read_text(encoding="utf-8")


def _controller() -> str:
    return _CONTROLLER.read_text(encoding="utf-8")


# ── Root-cause fix: the capture context is resumed ────────────────────────────


def test_capture_audio_context_is_resumed():
    """THE fix: the capture AudioContext must resume when suspended, else
    onaudioprocess never fires and no audio is ever captured."""
    src = _ws()
    assert "await this.audioContext.resume()" in src
    assert "'suspended'" in src or '"suspended"' in src
    # The resume must live in the capture path (startMic), not only TTS playback.
    start_mic = src.split("async startMic")[1].split("captureDiagnostics(")[0]
    assert "resume()" in start_mic


def test_processor_does_not_echo_mic_to_speakers():
    """The ScriptProcessor needs a destination to fire, but routing mic → speakers
    echoes. It must sink through a zero-gain node."""
    src = _ws()
    assert "createGain()" in src
    assert "gain.value = 0" in src
    # It must NOT connect the processor straight to destination.
    assert "processorNode.connect(this.audioContext.destination)" not in src


# ── Client diagnostics (non-secret) ───────────────────────────────────────────


def test_client_rms_is_measured_from_the_same_pcm():
    src = _ws()
    assert "_lastClientRms" in src and "_maxClientRms" in src
    assert "Math.sqrt(sumSq" in src
    # Exposed for the recording meter.
    assert "get clientRms()" in src


def test_capture_diagnostics_are_non_secret_and_complete():
    src = _ws()
    # The diagnostics object literal, from the method body's `return {` to the
    # `get clientRms` accessor that follows it.
    diag = src.split("captureDiagnostics(")[1].split("get clientRms")[0]
    for field in (
        "audio_context_state",
        "chunk_count",
        "last_client_rms",
        "max_client_rms",
        "track_ready_state",
        "track_muted",
    ):
        assert field in diag, f"missing capture diagnostic: {field}"
    # No transcript / audio bytes in diagnostics.
    assert "transcript" not in diag.lower()
    assert "blob" not in diag.lower()


# ── Concurrent-recording guard (no zombie cards) ──────────────────────────────


def test_exactly_one_active_recorder():
    """A second mic tap while recording must not spawn a concurrent recorder /
    zombie 'listening…' card."""
    src = _controller()
    guard = src.split("export async function startVoice")[1].split("log('mic_clicked')")[0]
    assert "start_ignored_recorder_active" in guard
    assert "recorder || finalizing" in guard


def test_capture_context_not_running_is_surfaced():
    """If the context did not resume, that must be surfaced immediately, not
    after a 40s dead recording."""
    src = _controller()
    assert "capture_context_not_running" in src
    assert "audio_context_state !== 'running'" in src
