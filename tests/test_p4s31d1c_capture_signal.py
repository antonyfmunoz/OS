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


# ── Root-cause fix: the METER context is resumed (P4S-31D1-F blob-only) ───────
# The live capture ScriptProcessor was removed (blob-only rail). The only
# AudioContext in the capture path is now the metering AnalyserNode in the
# controller — it must still resume when suspended (iOS creates it 'suspended'),
# else the RMS meter stays frozen at 0 and false-fires the silent-mic hint.


def test_meter_audio_context_is_resumed():
    """The metering AnalyserNode AudioContext must resume when suspended, else the
    RMS meter never moves on iOS (context created 'suspended')."""
    src = _controller()
    assert "meterAudioContext.resume()" in src
    assert "'suspended'" in src or '"suspended"' in src
    # The resume lives in the meter path (startMeterAnalyser).
    meter = src.split("function startMeterAnalyser")[1].split("function stopMeterAnalyser")[0]
    assert "resume()" in meter


def test_meter_analyser_does_not_echo_mic_to_speakers():
    """The metering AnalyserNode must NOT connect to destination — routing mic →
    speakers would echo. Source connects to the analyser only."""
    src = _controller()
    assert "createAnalyser()" in src
    assert "meterSource.connect(meterAnalyser)" in src
    # It must NOT connect the meter graph to the speakers.
    assert "connect(meterAudioContext.destination)" not in src
    # And the deprecated ScriptProcessor / live PCM streaming must be gone.
    assert "createScriptProcessor" not in _ws()
    assert "onaudioprocess" not in _ws()


# ── Client diagnostics (non-secret) ───────────────────────────────────────────


def test_client_rms_is_measured_from_the_analyser():
    """RMS is computed by the controller's metering AnalyserNode (0..1) and pushed
    into the WS client (setMeterRms), which exposes it via get clientRms()."""
    ctrl = _controller()
    assert "getFloatTimeDomainData" in ctrl
    assert "Math.sqrt(sumSq" in ctrl
    assert "client?.setMeterRms(" in ctrl
    ws = _ws()
    assert "_lastClientRms" in ws and "_maxClientRms" in ws
    # Exposed for the recording meter.
    assert "get clientRms()" in ws


def test_capture_diagnostics_are_non_secret_and_complete():
    src = _ws()
    # The diagnostics METHOD DEFINITION (not its call site), up to the
    # `get clientRms` accessor that follows it.
    diag = src.split("captureDiagnostics(): Record")[1].split("get clientRms")[0]
    for field in (
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


def test_dead_capture_is_surfaced():
    """A non-live mic track or a failed meter AnalyserNode must be surfaced
    immediately (logged), not swallowed into a silent dead recording."""
    src = _controller()
    # Track liveness is checked up front (blob-only: no capture AudioContext).
    assert "capture_track_not_live" in src
    assert "track_ready_state !== 'live'" in src
    # A meter AnalyserNode that fails to start is logged, not swallowed.
    assert "meter_analyser_start_failed" in src
