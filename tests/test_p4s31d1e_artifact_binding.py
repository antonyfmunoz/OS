"""P4S-31D1-E — the local MediaRecorder blob is the SINGLE SOURCE OF TRUTH.

The D1-B voice rail captured audio two independent ways on one MediaStream:
(1) live PCM16 streamed over the WS for STT, and (2) a MediaRecorder blob held
locally for playback. The transcript was completed ONLY from the WS stream, so
when the PCM path delivered nothing (Safari / AudioContext timing) the server
reported "no audio received" EVEN THOUGH the local blob captured fine and played
back — two divergent artifacts, one of them reliable.

D1-E makes the blob the source of truth for TRANSCRIPTION, not just playback:
  - finalize completes from the WS text when present (fast path), ELSE
    transcribes FROM THE BLOB via the SAME machinery the retry uses,
  - the decode/stream logic lives in ONE shared helper (no duplication),
  - transcription is guarded by binding assertions that emit a DISTINCT,
    precise error code — NEVER a bare "no audio" while a size>0 blob exists,
  - the single artifact (blob + object URL) feeds playback + transcription +
    retry + send + delete, and its object URL is revoked ONLY on delete.

These assertions are source-level (like test_p4s31d1c_ui_signal.py): they guard
invariants a runtime test in this repo cannot reach (no browser, no
MediaRecorder, no WebAudio) and fail closed if a future edit regresses the
blob-fallback, re-duplicates the decode/stream logic, collapses the error
taxonomy, revokes the URL on failure, or opens a second chat entry point.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

import pytest

_ROOT = Path(_WORKTREE)
_RENDERER = _ROOT / "cockpit" / "src" / "renderer"
_API = _RENDERER / "api"
_STORES = _RENDERER / "stores"

_CONTROLLER_PATH = _API / "voice-controller.ts"
_STORE_PATH = _STORES / "voiceMessageStore.ts"
_RIGHT_RAIL_PATH = _RENDERER / "components" / "RightRail.tsx"

# The binding taxonomy the packet requires, each mapping to a DISTINCT string.
_ARTIFACT_CODES = [
    "LOCAL_AUDIO_PRESENT_UPLOAD_MISSING",
    "LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY",
    "AUDIO_ARTIFACT_REF_NOT_FOUND",
    "MISSING_AUDIO_FIELD",
    "EMPTY_AUDIO_BLOB",
    "UNSUPPORTED_AUDIO_FORMAT",
    "DECODE_FAILED",
    "STT_FAILED",
]


def _read(p: Path) -> str:
    assert p.exists(), f"expected file missing: {p}"
    return p.read_text(encoding="utf-8")


def _slice(src: str, start_marker: str, end_marker: str) -> str:
    """Return the substring of src between the first start_marker and the next
    end_marker after it (both markers inclusive). Fails loudly if not found."""
    i = src.index(start_marker)
    j = src.index(end_marker, i)
    return src[i : j + len(end_marker)]


# ── 1. Finalize has a blob-fallback (transcribe from blob when WS text absent) ─


def test_finalize_uses_blob_fallback_when_ws_text_absent():
    """_finalizeRecording: WS text is the fast path; a present blob is the
    fallback source of truth — it calls the shared _transcribeBlob helper."""
    src = _read(_CONTROLLER_PATH)
    block = _slice(src, "function _finalizeRecording", "log('recording_finalized'")

    # Fast path: use the WS final transcript when present.
    assert "if (finalTranscriptText)" in block, "finalize must keep the WS fast path"
    assert "completeActiveTranscript(finalTranscriptText" in block, (
        "fast path must complete from the WS transcript"
    )

    # Fallback: when no WS text, transcribe FROM the attached blob.
    assert "_transcribeBlob(" in block, (
        "finalize must fall back to _transcribeBlob when WS text is absent"
    )
    # The fallback is gated on a real, non-empty blob.
    assert re.search(r"blob\s*&&\s*blob\.size\s*>\s*0", block), (
        "finalize blob-fallback must gate on blob.size > 0"
    )
    # On a successful blob transcription, complete the active transcript.
    assert "completeActiveTranscript(res.text" in block, (
        "blob-fallback success must complete the active transcript"
    )


def test_finalize_fast_path_precedes_fallback():
    """The WS fast path is checked BEFORE the blob fallback runs."""
    src = _read(_CONTROLLER_PATH)
    block = _slice(src, "function _finalizeRecording", "log('recording_finalized'")
    fast = block.index("completeActiveTranscript(finalTranscriptText")
    fallback = block.index("_transcribeBlob(")
    assert fast < fallback, "WS fast path must be evaluated before the blob fallback"


# ── 2. The decode/stream logic is shared (single helper, not duplicated) ──────


def test_shared_transcribe_helper_exists():
    """A single _transcribeBlob helper owns the decode→stream→collect flow."""
    src = _read(_CONTROLLER_PATH)
    assert "async function _transcribeBlob(" in src, "shared _transcribeBlob helper missing"
    # It centralizes the decode (resample) and the WS control frames.
    helper = _slice(src, "async function _transcribeBlob(", "return result")
    assert "_resampleToPcm16(" in helper, "helper must own the decode/resample"
    assert "sendControl('mic_start')" in helper and "sendControl('mic_stop')" in helper, (
        "helper must own the WS control frames"
    )
    assert "sendPcm(" in helper, "helper must own the PCM streaming"


def test_both_callers_use_the_shared_helper():
    """Finalize-fallback AND retry both route through _transcribeBlob."""
    src = _read(_CONTROLLER_PATH)
    finalize = _slice(src, "function _finalizeRecording", "log('recording_finalized'")
    retry = _slice(
        src, "export async function retryDraftTranscription", "markRetryFailed(draftId, RETRY_CODE"
    )
    assert "_transcribeBlob(" in finalize, "finalize-fallback must call _transcribeBlob"
    assert "_transcribeBlob(" in retry, "retry must call _transcribeBlob"


def test_decode_stream_logic_not_duplicated():
    """The decode/stream primitives appear exactly ONCE (inside the shared
    helper), not re-implemented in the retry or finalize paths."""
    src = _read(_CONTROLLER_PATH)
    # The retry path no longer inlines the WS control frames / PCM loop.
    retry = _slice(
        src, "export async function retryDraftTranscription", "markRetryFailed(draftId, RETRY_CODE"
    )
    assert "sendControl('mic_start')" not in retry, (
        "retry must NOT re-inline the WS control frames (use the shared helper)"
    )
    assert "for (const chunk of chunks)" not in retry, (
        "retry must NOT re-inline the PCM streaming loop"
    )
    # And the mic_start control frame for the blob path exists exactly once in
    # the whole controller (the shared helper). (Live-capture mic_start lives in
    # voice-ws.ts, not here.)
    assert src.count("sendControl('mic_start')") == 1, (
        "the blob-transcribe mic_start frame must exist exactly once (single helper)"
    )
    assert src.count("for (const chunk of chunks)") == 1, (
        "the PCM streaming loop must exist exactly once (single helper)"
    )


# ── 3. Binding assertions + precise, distinct error taxonomy ──────────────────


def test_binding_assertion_helper_present():
    """A binding pre-flight asserts draft id, blob presence, size>0, mime."""
    src = _read(_CONTROLLER_PATH)
    assert "_assertTranscribableBlob(" in src, "binding assertion helper missing"
    guard = _slice(src, "function _assertTranscribableBlob(", "return null")
    assert re.search(r"blob\.size\s*<=\s*0", guard) or re.search(r"blob\.size\s*<\s*1", guard), (
        "binding must assert blob.size > 0"
    )
    assert "blob.type" in guard, "binding must assert the blob mimeType"
    assert "startsWith('audio/')" in guard, "binding must require an audio/* mime"


def test_artifact_error_codes_defined_and_distinct():
    """All eight binding codes exist in the controller taxonomy, distinct."""
    src = _read(_CONTROLLER_PATH)
    m = re.search(r"VOICE_ARTIFACT_ERROR\s*=\s*\{(.*?)\}\s*as const", src, re.DOTALL)
    assert m, "VOICE_ARTIFACT_ERROR map missing from controller"
    body = m.group(1)
    pairs = dict(re.findall(r"([A-Z_]+)\s*:\s*'([^']+)'", body))
    for code in _ARTIFACT_CODES:
        assert code in pairs, f"artifact taxonomy missing {code}"
        # Each code maps to its own literal (the enum value equals the name).
        assert pairs[code] == code, f"{code} must map to its own literal value"


def test_artifact_codes_have_distinct_ui_strings():
    """Each artifact code maps to a DISTINCT human string in the RightRail map
    (nothing collapses)."""
    src = _read(_RIGHT_RAIL_PATH)
    m = re.search(r"VOICE_FAILURE_REASON\s*:\s*Record<[^>]+>\s*=\s*\{(.*?)\n\}", src, re.DOTALL)
    assert m, "VOICE_FAILURE_REASON map missing"
    pairs = dict(re.findall(r"([A-Z_]+)\s*:\s*'([^']+)'", m.group(1)))
    strings = []
    for code in _ARTIFACT_CODES:
        assert code in pairs, f"UI map missing string for {code}"
        assert pairs[code].strip(), f"{code} maps to empty UI string"
        strings.append(pairs[code])
    assert len(set(strings)) == len(strings), (
        f"duplicate UI strings among artifact codes: {strings}"
    )


# ── 4. No code path emits "no audio" while a blob is present ───────────────────


def test_no_bare_no_audio_when_blob_present():
    """No 'no audio received' / 'No audio was received' phrasing anywhere in the
    voice surfaces. The precise codes replace it entirely."""
    for p in (_CONTROLLER_PATH, _STORE_PATH, _RIGHT_RAIL_PATH):
        low = _read(p).lower()
        assert "no audio received" not in low, f"forbidden 'no audio received' in {p.name}"
        assert "no audio was received" not in low, f"forbidden 'no audio was received' in {p.name}"


def test_present_blob_failure_never_maps_to_no_audio_string():
    """The codes emitted when a blob IS present must not read like 'no audio'."""
    src = _read(_RIGHT_RAIL_PATH)
    m = re.search(r"VOICE_FAILURE_REASON\s*:\s*Record<[^>]+>\s*=\s*\{(.*?)\n\}", src, re.DOTALL)
    pairs = dict(re.findall(r"([A-Z_]+)\s*:\s*'([^']+)'", m.group(1)))
    # These fire when the local blob exists but transcription of it failed —
    # they must describe the real cause, never claim no audio was captured.
    for code in (
        "LOCAL_AUDIO_PRESENT_UPLOAD_MISSING",
        "LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY",
        "STT_FAILED",
        "DECODE_FAILED",
    ):
        s = pairs[code].lower()
        assert "no audio" not in s, f"{code} string '{pairs[code]}' must not claim 'no audio'"


def test_finalize_missing_blob_branch_uses_precise_code():
    """Only the genuinely-blobless branch may report a missing artifact, and it
    uses a precise code (MISSING_AUDIO_FIELD / EMPTY_AUDIO_BLOB), never a bare
    no-audio phrase."""
    src = _read(_CONTROLLER_PATH)
    block = _slice(src, "function _finalizeRecording", "log('recording_finalized'")
    assert "VOICE_ARTIFACT_ERROR.MISSING_AUDIO_FIELD" in block, (
        "blobless finalize branch must emit MISSING_AUDIO_FIELD"
    )
    assert "VOICE_ARTIFACT_ERROR.EMPTY_AUDIO_BLOB" in block, (
        "empty-blob finalize branch must emit EMPTY_AUDIO_BLOB"
    )


# ── 5. Single artifact: object URL revoked ONLY on delete ─────────────────────


def test_object_url_created_once_on_attach():
    """The object URL is minted once, in attachAudio."""
    src = _read(_STORE_PATH)
    assert src.count("URL.createObjectURL(") == 1, (
        "object URL must be created exactly once (attachAudio)"
    )
    attach = _slice(src, "attachAudio: (blob)", "log('audio_attached'")
    assert "URL.createObjectURL(blob)" in attach, "attachAudio must mint the object URL"


def test_object_url_revoked_only_on_delete():
    """revokeObjectURL appears only in deleteDraft — never on a failure path."""
    src = _read(_STORE_PATH)
    assert src.count("URL.revokeObjectURL(") == 1, (
        "object URL must be revoked exactly once (delete only)"
    )
    delete = _slice(src, "deleteDraft: (draftId)", "log('draft_deleted'")
    assert "URL.revokeObjectURL(draft.audioUrl)" in delete, "deleteDraft must revoke the object URL"
    # Failure paths must NOT revoke.
    for action in ("markTranscriptFailed", "markRetryFailed", "markNoSpeech"):
        block_start = src.index(action)
        block_end = src.index("\n\n", block_start) if "\n\n" in src[block_start:] else len(src)
        block = src[block_start:block_end]
        assert "revokeObjectURL" not in block, f"{action} must NOT revoke the object URL"


def test_audio_preserved_on_all_failure_paths():
    """Failure paths keep the audio (the store documents + enforces this)."""
    src = _read(_STORE_PATH)
    # attachAudio never conditional on STT success; failure actions don't null it.
    for action in ("markTranscriptFailed", "markRetryFailed"):
        block_start = src.index(f"{action}:")
        block = src[block_start : block_start + 400]
        assert "audioBlob: null" not in block, f"{action} must not discard the blob"


# ── 6. sendDraft remains the sole chat entry; gate intact ─────────────────────


def test_send_draft_is_sole_chat_entry():
    """addVoiceTranscript is called ONLY from sendDraft (store), never the
    controller. The blob-fallback must not open a second path into chat."""
    store = _read(_STORE_PATH)
    controller = _read(_CONTROLLER_PATH)
    assert store.count("addVoiceTranscript(") == 1, (
        "addVoiceTranscript must be called exactly once (sendDraft)"
    )
    send_block = _slice(store, "sendDraft: async (draftId)", "log('send_complete'")
    assert "addVoiceTranscript(" in send_block, (
        "the sole addVoiceTranscript call must live in sendDraft"
    )
    assert "addVoiceTranscript(" not in controller, (
        "controller must never call addVoiceTranscript (send-only path)"
    )


def test_send_gate_preserved():
    """Send stays gated on status == ready AND transcript_status ∈ {final,edited}."""
    store = _read(_STORE_PATH)
    assert "draft.status !== 'ready'" in store, "send must refuse when not ready"
    assert "transcript_status !== 'final'" in store and "transcript_status !== 'edited'" in store, (
        "send must require final|edited transcript"
    )


# ── 7. D1-C resume fix + meter must not regress ───────────────────────────────


def test_d1c_resume_fix_and_meter_intact():
    """The capture-context resume fix and the RMS meter remain in place."""
    ws = _read(_API / "voice-ws.ts")
    assert "this.audioContext.resume()" in ws, "D1-C capture-context resume fix regressed"
    assert re.search(r"\bget\s+clientRms\s*\(\s*\)", ws), "clientRms meter getter regressed"
    controller = _read(_CONTROLLER_PATH)
    assert "client.clientRms" in controller and "setCaptureRms" in controller, (
        "meter poll wiring regressed"
    )


# ── 8. Naming: VoiceNoteDraft == VoiceMessageDraft (doc alias, not a rename) ───


def test_voice_note_draft_documented_as_alias():
    """The controller documents VoiceNoteDraft == VoiceMessageDraft without
    renaming the store type (which stays VoiceMessageDraft)."""
    controller = _read(_CONTROLLER_PATH)
    assert "VoiceNoteDraft == VoiceMessageDraft" in controller, (
        "controller must document the VoiceNoteDraft alias"
    )
    store = _read(_STORE_PATH)
    assert "export interface VoiceMessageDraft" in store, (
        "store type must remain VoiceMessageDraft (no destabilizing rename)"
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-v"]))
