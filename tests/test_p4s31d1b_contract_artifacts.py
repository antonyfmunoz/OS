"""P4S-31D1-B — VoiceMessage contract artifact validation (Lane B).

The contract is the binding spec for the voice-message rail. These tests keep
it structurally sound and keep its non-negotiables (draft-before-chat, partial
never committed, pause != send, audio preserved) machine-checked.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

_CONTRACT_PATH = Path(_WORKTREE) / "data" / "umh" / "voice" / "voice_message_contract.json"
_DOC_PATH = Path(_WORKTREE) / "docs" / "VOICE_MESSAGE_CONTRACT.md"
_WORKGRAPH_PATH = Path(_WORKTREE) / "data" / "umh" / "roadmap" / "p4_sync_workgraph.json"


def _contract() -> dict:
    return json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))


def test_contract_parses_and_binds_packet():
    c = _contract()
    assert c["record"] == "voice_message_contract"
    assert c["packet"] == "P4S-31D1-B-VOICE-MESSAGE-UX-001"
    assert "no ambient" in c["mode"] or "activation authorized" in c["mode"]


def test_required_type_shapes_present():
    types = _contract()["types"]
    for name in ("VoiceMessageDraft", "AudioArtifactRef", "RecordingSessionState", "VadConfig", "VoiceDiagnostics"):
        assert name in types, f"missing type shape: {name}"


def test_draft_fields_cover_owner_spec():
    fields = _contract()["types"]["VoiceMessageDraft"]["fields"]
    for f in (
        "audio_artifact", "transcript", "duration_ms", "confidence",
        "device_registry_id", "session_id", "consent_grant_id",
        "transcript_status", "created_at", "finalized_by",
    ):
        assert f in fields, f"VoiceMessageDraft missing field: {f}"


def test_partial_transcript_never_committed_is_binding():
    c = json.dumps(_contract())
    assert "MUST NEVER be committed" in c
    forbidden = _contract()["ux_states"]["forbidden"]
    assert any("partial" in f for f in forbidden)
    assert any("auto-submit on pause" in f for f in forbidden)


def test_vad_defaults_sane_and_auto_send_false():
    vad = _contract()["types"]["VadConfig"]["fields"]
    assert "default false" in vad["auto_send"]
    # finalize threshold must exceed the intra-utterance pause window
    intra = int(vad["intra_utterance_pause_ms"].split("default ")[1].split(" ")[0])
    fin = int(vad["min_silence_before_finalize_ms"].split("default ")[1].split(" ")[0])
    speech = int(vad["min_speech_ms"].split("default ")[1].split(" ")[0])
    assert fin > intra > 0 and speech > 0


def test_audio_preserved_on_stt_failure():
    c = _contract()
    assert any("preserved on STT failure" in r for r in c["stt_quality"]["requirements"])
    assert "NEVER null after stop" in c["types"]["VoiceMessageDraft"]["fields"]["audio_artifact"]


def test_finalized_by_enum_matches_owner_spec():
    diag = _contract()["types"]["VoiceDiagnostics"]["fields"]["finalized_by"]
    for v in ("manual_stop", "silence_timeout", "cancel"):
        assert v in diag


def test_storage_and_logging_law():
    c = _contract()
    law = c["types"]["AudioArtifactRef"]["storage_law"]
    assert any("tenant/user/session scoped" in item for item in law)
    assert any("never logged" in item for item in law)
    assert "never transcript text" in c["types"]["VoiceDiagnostics"]["logging_law"]


def test_hard_constraints_hold_the_line():
    hc = " | ".join(_contract()["hard_constraints"])
    for token in ("no separate execution path", "no ambient", "always-on", "P4S-21", "provider execution"):
        assert token in hc


def test_workgraph_reclassified_and_new_packet_registered():
    wg = json.loads(_WORKGRAPH_PATH.read_text(encoding="utf-8"))
    ids = [p.get("id") for p in wg["packets"]]
    assert "P4S-31D1-B-VOICE-MESSAGE-UX-001" in ids
    d1 = next(p for p in wg["packets"] if p["id"] == "P4S-31D-1-DESKTOP-BROWSER-PTT-001")
    assert "reclassification" in d1 and "P4S-31D1-A" in d1["reclassification"]
    d1b = next(p for p in wg["packets"] if p["id"] == "P4S-31D1-B-VOICE-MESSAGE-UX-001")
    assert d1b["dependencies"] == ["P4S-31D-1-DESKTOP-BROWSER-PTT-001"]
    assert any("bypasses /advisor/converse" in s for s in d1b["stop_conditions"])


def test_doc_exists_and_names_canonical_artifact():
    doc = _DOC_PATH.read_text(encoding="utf-8")
    assert "voice_message_contract.json" in doc
    assert "P4S-31D1-A" in doc
    assert "never bypasses Cockpit Chat" in doc


def test_taxonomy_scopes_packet_to_uservoicenote():
    """2026-07-07 owner correction: this packet is the UserVoiceNote input rail,
    NOT AIOutboundVoiceMessage. The taxonomy must say so, in both artifacts, so
    docs can never falsely imply outbound AI voice is built."""
    tax = _contract()["voice_taxonomy"]
    assert tax["this_packet_implements"] == "UserVoiceNote"
    # All five canonical categories are named.
    for cat in ("UserVoiceNote", "LiveVoiceSession", "AmbientActivation",
                "AIOutboundVoiceMessage", "ManualCockpitControl"):
        assert cat in tax["categories"]
    # Outbound AI voice + cloning are explicitly NOT built here.
    assert "AIOutboundVoiceMessage" in tax["not_implemented_here"]
    assert "voice_clone_execution" in tax["not_implemented_here"]
    # Intent ingress law: text + voice-first only; manual buttons are execution.
    assert "Cockpit Chat text" in tax["intent_ingress_law"]
    # The human-readable doc carries the same scoping.
    doc = _DOC_PATH.read_text(encoding="utf-8")
    assert "UserVoiceNote" in doc
    assert "AIOutboundVoiceMessage" in doc
    assert "NOT built" in doc or "NOT this packet, NOT built" in doc
