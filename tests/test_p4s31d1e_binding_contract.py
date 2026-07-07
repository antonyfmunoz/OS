"""P4S-31D1-E — VoiceNote artifact-binding contract shape checks.

Pins data/umh/voice/voicenote_artifact_binding_contract.json: the canonical
VoiceNoteDraft==VoiceMessageDraft aliasing, the blob-as-single-source-of-truth
law, the precise binding error taxonomy (never "no audio" while playback works),
the collapsible-transcript + single-gesture-consent requirements, and the
send/delete semantics. The behavioral fixes are proven by the companion D1-E
tests (artifact binding / consent flow / transcript UI); this guards the spec.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONTRACT = (
    Path(_WORKTREE) / "data" / "umh" / "voice" / "voicenote_artifact_binding_contract.json"
)


def _load() -> dict:
    return json.loads(_CONTRACT.read_text(encoding="utf-8"))


def test_contract_parses():
    c = _load()
    assert c["record"].startswith("P4S-31D1-E")


def test_root_cause_names_the_two_divergent_artifacts():
    c = _load()
    rc = c["root_cause"]
    assert "two_capture_paths" in rc and len(rc["two_capture_paths"]) == 2
    # The fix is blob-fallback for the PRIMARY transcription, centralized.
    assert "blob" in rc["the_fix"].lower()
    assert "finalTranscriptText" in rc["the_bug"]


def test_blob_is_single_source_of_truth():
    c = _load()
    feeds = c["single_artifact_source_of_truth"]["the_blob_feeds"]
    for surface in ("local playback", "retry transcription", "send", "delete cleanup"):
        assert surface in feeds, f"blob must feed {surface}"
    # Object URL revoked ONLY on delete (preserved on failure for retry).
    lifecycle = c["single_artifact_source_of_truth"]["object_url_lifecycle"]
    assert "delete" in lifecycle and "never" in lifecycle.lower()


# The ONE canonical local error vocabulary shared across #252/#253/#254/#255.
CANONICAL_CODES = frozenset(
    {
        "LOCAL_AUDIO_PRESENT_UPLOAD_MISSING",
        "LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY",
        "AUDIO_ARTIFACT_REF_NOT_FOUND",
        "MISSING_AUDIO_FIELD",
        "EMPTY_AUDIO_BLOB",
        "UNSUPPORTED_AUDIO_FORMAT",
        "DECODE_FAILED",
        "SILENT_AUDIO",
        "VAD_NO_SPEECH",
        "STT_FAILED",
    }
)


def test_binding_taxonomy_is_exactly_the_canonical_ten():
    c = _load()
    codes = set(c["binding_error_taxonomy"]["codes"].keys())
    assert codes == CANONICAL_CODES, (
        f"contract taxonomy must be EXACTLY the canonical set; "
        f"extra={codes - CANONICAL_CODES} missing={CANONICAL_CODES - codes}"
    )
    # The law: never "no audio" when a blob is present.
    assert "size > 0" in c["binding_error_taxonomy"]["law"]
    # Declared authoritative — no packet may fork the vocabulary.
    assert "canonical" in c["binding_error_taxonomy"]["authority"].lower()


def test_mobile_consent_is_single_gesture_no_fake_consent():
    c = _load()
    mc = c["mobile_safari_consent"]
    assert "same user-initiated flow" in mc["correct"].lower()
    rules = " ".join(mc["rules"]).lower()
    assert "no client-side fake consent" in rules
    assert "wake_word" in rules and "refused" in rules
    assert "push_to_talk only" in rules


def test_input_consent_is_not_action_approval():
    c = _load()
    iva = c["input_vs_action_approval"]
    assert "once per device/session" in iva["voice_input_consent"]
    assert "not for recording" in iva["rule"].lower() or "NOT for recording" in iva["rule"]


def test_send_semantics_gate_chat_on_explicit_send():
    c = _load()
    ss = c["send_semantics"]
    before = " ".join(ss["before_send"]).lower()
    assert "no chat message committed" in before
    assert "no intent-loop entry" in before
    on_send = " ".join(ss["on_explicit_send_only"]).lower()
    assert "cockpit chat" in on_send and "senddraft" in on_send.replace(" ", "")


def test_hard_constraints_preserved():
    c = _load()
    hc = " ".join(c["hard_constraints"]).lower()
    for held in ("no ambient activation", "no always-on mic", "no ai outbound voice"):
        assert held in hc
    for phase in ("p4s-21", "p4s-40", "p4s-22"):
        assert phase in hc
