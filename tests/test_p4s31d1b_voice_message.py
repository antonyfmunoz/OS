"""P4S-31D1-B — Cockpit voice-MESSAGE rail (lanes C+D+E).

Static / shape checks that pin the binding contract
(data/umh/voice/voice_message_contract.json) against the shipped renderer
code. The doctrine: voice is a governed voice-MESSAGE rail, not dictation.
Recording produces a reviewable VoiceMessageDraft; NOTHING enters Cockpit Chat
until the operator explicitly sends. The D1-A auto-dispatch (transcript pushed
into chat on silence / tap-to-stop) is REPLACED.

These assertions are deliberately source-level (like test_p4s31d1_voice_ptt.py):
they guard the invariants that a runtime test in this repo cannot reach (no
browser, no MediaRecorder, no WebAudio), and they fail closed when a future
edit reintroduces a bypass.
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

_RENDERER = Path(_WORKTREE) / "cockpit" / "src" / "renderer"
_API = _RENDERER / "api"
_STORES = _RENDERER / "stores"

_STORE_PATH = _STORES / "voiceMessageStore.ts"
_CHAT_STORE_PATH = _STORES / "chatStore.ts"
_CONTROLLER_PATH = _API / "voice-controller.ts"
_VOICE_WS_PATH = _API / "voice-ws.ts"
_ADAPTER_PATH = _API / "platform-voice-adapter.ts"
_RIGHT_RAIL_PATH = _RENDERER / "components" / "RightRail.tsx"

_CONTRACT_PATH = (
    Path(_WORKTREE).parent / "p4s31d1b-contract" / "data" / "umh" / "voice"
    / "voice_message_contract.json"
)

_VOICE_FILES = [_STORE_PATH, _CONTROLLER_PATH, _VOICE_WS_PATH, _ADAPTER_PATH]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _strip_comments_ts(src: str) -> str:
    """Drop // line and /* */ block comments so identifier assertions test real
    code, not documentation mentioning the identifier."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)
    return src


# ── 1. Partial transcript is NEVER committed as chat content ───────────────────


def test_partial_has_no_path_into_chat_messages_or_send():
    """transcript_partial / updateActivePartial is provisional display ONLY.
    No file may route a partial into chatStore.messages or sendMessage."""
    controller = _strip_comments_ts(_read(_CONTROLLER_PATH))
    # The controller pushes partials to the DRAFT store's provisional field only.
    assert "updateActivePartial" in controller
    # It must never feed a partial into the chat draft-message bubble or send.
    assert "setDraftMessage" not in controller, (
        "voice partials must not enter the chat draft-message bubble"
    )
    # The message store never sends the partial; only the finalized transcript.
    store = _strip_comments_ts(_read(_STORE_PATH))
    # sendDraft forwards draft.transcript (finalized), NEVER transcript_partial.
    assert "addVoiceTranscript(draft.transcript" in store
    assert "addVoiceTranscript(draft.transcript_partial" not in store
    assert "sendMessage" not in store, (
        "the draft store reaches chat only through addVoiceTranscript, never a "
        "direct sendMessage"
    )


def test_partial_updates_target_the_draft_store_not_chatstore():
    """Partials go to useVoiceMessageStore.updateActivePartial, not chatStore."""
    controller = _strip_comments_ts(_read(_CONTROLLER_PATH))
    # Find the non-final transcript branch and assert it calls updateActivePartial.
    assert "vms.updateActivePartial(text)" in controller


# ── 2. D1-A auto-dispatch is GONE ──────────────────────────────────────────────


def test_controller_never_calls_add_voice_transcript():
    """The D1-A seam (_dispatchCommittedTurn -> addVoiceTranscript on silence /
    tap-to-stop) is removed. The controller drives drafts only."""
    controller = _strip_comments_ts(_read(_CONTROLLER_PATH))
    assert "addVoiceTranscript" not in controller
    assert "_dispatchCommittedTurn" not in controller


def test_add_voice_transcript_has_exactly_one_caller():
    """The ONLY caller of addVoiceTranscript is voiceMessageStore.sendDraft."""
    callers = []
    for p in _RENDERER.rglob("*.ts"):
        for i, line in enumerate(_strip_comments_ts(_read(p)).splitlines(), 1):
            if "addVoiceTranscript(" in line and "addVoiceTranscript:" not in line:
                callers.append((p.name, i, line.strip()))
    for p in _RENDERER.rglob("*.tsx"):
        for i, line in enumerate(_strip_comments_ts(_read(p)).splitlines(), 1):
            if "addVoiceTranscript(" in line and "addVoiceTranscript:" not in line:
                callers.append((p.name, i, line.strip()))
    assert len(callers) == 1, f"expected 1 addVoiceTranscript caller, got {callers}"
    assert callers[0][0] == "voiceMessageStore.ts"


# ── 3. VAD thresholds equal the contract defaults ──────────────────────────────


def test_vad_config_matches_contract_defaults():
    import json

    contract = json.loads(_read(_CONTRACT_PATH))
    vad = contract["types"]["VadConfig"]["fields"]

    def _default(field: str) -> str:
        # "float, default 0.02 — …" / "int, default 400 — …" / "bool, default false"
        m = re.search(r"default\s+([\w.]+)", vad[field])
        assert m, f"no default in contract for {field}"
        return m.group(1)

    store = _read(_STORE_PATH)
    expected = {
        "silence_threshold_level": _default("silence_threshold_level"),
        "min_speech_ms": _default("min_speech_ms"),
        "intra_utterance_pause_ms": _default("intra_utterance_pause_ms"),
        "min_silence_before_finalize_ms": _default("min_silence_before_finalize_ms"),
        "max_recording_ms": _default("max_recording_ms"),
        "auto_send": _default("auto_send"),
    }
    for key, val in expected.items():
        assert re.search(rf"{key}:\s*{re.escape(val)}\b", store), (
            f"VAD_CONFIG.{key} must equal contract default {val}"
        )


def test_auto_send_is_false():
    store = _read(_STORE_PATH)
    assert re.search(r"auto_send:\s*false", store)


def test_controller_uses_vad_config_for_finalization():
    """Finalization decisions read VAD_CONFIG, not hardcoded magic numbers."""
    controller = _read(_CONTROLLER_PATH)
    assert "VAD_CONFIG.min_silence_before_finalize_ms" in controller
    assert "VAD_CONFIG.intra_utterance_pause_ms" in controller
    assert "VAD_CONFIG.min_speech_ms" in controller
    assert "VAD_CONFIG.max_recording_ms" in controller


# ── 4. Audio preserved on failure (never discarded) ────────────────────────────


def test_failure_paths_never_revoke_or_discard_audio():
    """Contract: audio is NEVER discarded on STT failure — revokeObjectURL only
    on delete. markTranscriptFailed / markRetryFailed / markNoSpeech keep it."""
    store = _read(_STORE_PATH)

    def _body(fn: str) -> str:
        # Extract from the arrow-function name up to the next top-level "},"
        start = store.index(f"{fn}:")
        return store[start : start + 600]

    for fn in ("markTranscriptFailed", "markRetryFailed", "markNoSpeech"):
        body = _body(fn)
        assert "revokeObjectURL" not in body, f"{fn} must not revoke audio"
        assert "audioBlob: null" not in body, f"{fn} must not discard the blob"
        assert "audioUrl: null" not in body, f"{fn} must not discard the url"


def test_only_delete_revokes_the_blob_url():
    """revokeObjectURL appears ONLY in deleteDraft (the single discard path)."""
    store = _strip_comments_ts(_read(_STORE_PATH))
    revoke_positions = [m.start() for m in re.finditer(r"revokeObjectURL", store)]
    assert revoke_positions, "deleteDraft must revoke the blob url"
    delete_idx = store.index("deleteDraft:")
    for pos in revoke_positions:
        assert pos > delete_idx, "revokeObjectURL must live only in deleteDraft"


def test_retry_keeps_audio_when_ws_unavailable():
    """Lane E: on WS failure the retry marks the draft failed with a typed code
    and keeps the audio (no discard)."""
    controller = _read(_CONTROLLER_PATH)
    assert "RETRY_WS_UNAVAILABLE" in controller
    assert "markRetryFailed(draftId" in controller


# ── 5. Send gated on {final,edited} && ready ───────────────────────────────────


def test_send_gate_requires_final_or_edited_and_ready():
    store = _strip_comments_ts(_read(_STORE_PATH))
    send_block = store[store.rindex("sendDraft:") : store.rindex("deleteDraft:")]
    assert "draft.status !== 'ready'" in send_block
    assert "'final'" in send_block and "'edited'" in send_block


def test_ui_send_button_gated_on_final_or_edited_and_ready():
    rail = _read(_RIGHT_RAIL_PATH)
    # The card computes canSend from status==ready && transcript_status in {final,edited}.
    assert "draft.status === 'ready'" in rail
    assert "transcript_status === 'final'" in rail
    assert "transcript_status === 'edited'" in rail
    assert "disabled={!canSend}" in rail


# ── 6. Diagnostics never store transcript text ─────────────────────────────────


def test_diagnostics_never_store_transcript_text():
    """VoiceDiagnostics carries timings + counts only. No assignment ever puts
    transcript / transcript_partial text INTO the diagnostics object."""
    store = _strip_comments_ts(_read(_STORE_PATH))
    # Every diagnostics: { ... } update must not embed transcript text fields.
    for m in re.finditer(r"diagnostics:\s*\{(.*?)\}", store, flags=re.DOTALL):
        body = m.group(1)
        assert "transcript:" not in body
        assert "transcript_partial:" not in body
        # counts are fine; the content field must be a count, not text
        assert "text" not in body


# ── 7. Delete revokes blob + leaves no chat message ────────────────────────────


def test_delete_leaves_no_chat_message():
    """deleteDraft removes the draft + revokes the blob and NEVER pushes a chat
    message. No draft with status != 'sent' may correspond to a chat message."""
    store = _strip_comments_ts(_read(_STORE_PATH))
    delete_block = store[store.rindex("deleteDraft:") :]
    assert "revokeObjectURL" in delete_block
    assert "addVoiceTranscript" not in delete_block
    assert "sendMessage" not in delete_block
    assert "pushExternalMessage" not in delete_block


def test_delete_aborts_active_recording_without_dispatch():
    """Deleting an in-flight recording cancels capture with no chat trace."""
    store = _read(_STORE_PATH)
    assert "abortActiveRecording" in store
    controller = _read(_CONTROLLER_PATH)
    abort = controller[controller.index("export function abortActiveRecording") :]
    abort = abort[: abort.index("\n}")]
    assert "addVoiceTranscript" not in abort
    assert "notifyVoiceMessageSent" not in abort


# ── 8. No bypass tokens in any voice file ──────────────────────────────────────

_FORBIDDEN_IN_VOICE_PATH = (
    "/intent-loop/submit",
    "classify_intent",
    "governed_mutation",
    "anthropic",
    "openai.",
    "generativeai",
)


@pytest.mark.parametrize("path", _VOICE_FILES, ids=lambda p: p.name)
def test_voice_files_have_no_bypass_tokens(path):
    src = _read(path)
    for token in _FORBIDDEN_IN_VOICE_PATH:
        assert token not in src, (
            f"{path.name} must not contain '{token}' — voice's ONLY exit is the "
            "chat seam (sendMessage source='voice')"
        )


def test_message_store_only_exit_is_the_chat_seam():
    """The draft store reaches Cockpit Chat ONLY via addVoiceTranscript, and
    uploads audio ONLY through the existing /chat/upload seam."""
    store = _strip_comments_ts(_read(_STORE_PATH))
    assert "/chat/upload" in store
    assert "/advisor/converse" not in store, (
        "the draft store must not POST to advisor directly — chatStore owns that"
    )


# ── 9. Recorder shares the capture MediaStream; retry uses stored audio ────────


def test_recorder_uses_the_shared_capture_stream():
    """Lane C/D: a MediaRecorder is created on the SAME getUserMedia stream the
    PCM16 WS capture uses (startMic returns the stream; controller records it)."""
    ws = _read(_VOICE_WS_PATH)
    assert "return { stream, trackState" in ws, (
        "voice-ws.startMic must expose the MediaStream for the recorder"
    )
    controller = _read(_CONTROLLER_PATH)
    assert "new MediaRecorder(" in controller
    assert "started.stream" in controller and "_startRecorder(stream)" in controller


def test_retry_decodes_and_streams_the_stored_blob():
    """Lane E: retry decodes the stored blob (AudioContext.decodeAudioData),
    resamples to 16kHz PCM16, and streams over the existing WS."""
    controller = _read(_CONTROLLER_PATH)
    assert "decodeAudioData" in controller
    assert "16000" in controller
    assert "sendControl('mic_start')" in controller
    assert "sendControl('mic_stop')" in controller
    assert "completeRetry(draftId" in controller


# ── 10. UI renders drafts as chat-style cards (Lane C) ─────────────────────────


def test_right_rail_renders_voice_draft_cards():
    rail = _read(_RIGHT_RAIL_PATH)
    assert "useVoiceMessageStore" in rail
    assert "<VoiceDraftCards />" in rail
    # Audio playback affordance + transcript + status.
    assert "<audio controls" in rail
    assert "DRAFT_STATUS_LABEL" in rail
    # Operator actions present.
    for action in ("sendDraft(draft.draft_id)", "retryDraft(draft.draft_id)",
                   "editTranscript(draft.draft_id", "deleteDraft(draft.draft_id)"):
        assert action in rail, f"missing operator action wiring: {action}"


def test_no_speech_draft_shows_error_and_retry_not_a_message():
    """A NO_SPEECH / failed draft renders an error with Retry + Delete and never
    a chat message."""
    rail = _read(_RIGHT_RAIL_PATH)
    assert "NO_SPEECH" in rail or "No speech detected" in rail
    # failed drafts still offer retry + delete (assert both buttons unconditional
    # of failure state in the card).
    assert "Retry" in rail and "Delete" in rail
