"""P4S-LIVE-VOICE-SESSION-001 LiveVoiceSession compile-artifact validation — compile-mode gate.

Validates the compile-only deliverables for the LiveVoiceSession runtime
(voice taxonomy category 2 — real-time DEX conversation):
  - the JSON artifact parses and declares compile_only mode,
  - the activation gate is CLOSED (activation_authorized is false),
  - all required top-level sections are present,
  - NO activation-authorizing language appears anywhere in the artifact or doc,
  - governance-not-bypassed language is present (actions hold at
    AWAITING_APPROVAL and route to the held intent-loop gate),
  - the artifact asserts NO auto-execute of a voice-implied action,
  - the new 'live_session' consent mode is declared FUTURE-grantable, not
    grantable now (grantable_now is false),
  - the barge-in model REUSES the existing voice-controller barge-in (no new one),
  - transcript AND events still hit the Cockpit Chat ledger (no separate store),
  - the VoiceSession shape is REFERENCED from voice_intent_contract_types.json,
    never redefined,
  - the CPU budget carries NUMERIC bounds (CPU Gate Law) and adds no new process,
  - rollback = flag off -> no live mode,
  - no first-tenant or device-hostname literal appears as global truth,
  - no implementation actually shipped (no live-session store field added to
    voiceStore.ts).

Mirrors tests/test_p4s31d_ambient_compile_artifacts.py: mechanical, fail-closed,
and truthful about what "done" means for a compile packet.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

_ROOT = Path(_WORKTREE)
_ARTIFACT = _ROOT / "data/umh/voice/live_voice_session_compile.json"
_TYPES = _ROOT / "data/umh/voice/voice_intent_contract_types.json"
_MESSAGE_CONTRACT = _ROOT / "data/umh/voice/voice_message_contract.json"
_DOC = _ROOT / "docs/LIVE_VOICE_SESSION_COMPILE.md"
_VOICE_STORE = _ROOT / "cockpit/src/renderer/stores/voiceStore.ts"

# First-tenant + device-hostname literals that must never appear as global truth.
_BANNED_LITERALS = ("antony", "afm", "munoz", "beast")

# Phrases that would authorize activation/implementation. The artifact is
# compile-only: it must never carry any of these (checked lowercase).
_ACTIVATION_PHRASES = (
    "activation approved",
    "authorized for activation",
    "cleared for activation",
    "activation is authorized",
    "activate now",
    "may activate",
    "may be activated",
    "begin implementation",
    "implementation may begin",
    "implementation approved",
    "start the session runtime",
    "greenlit",
    "go-live",
)

# Required top-level sections of the compile artifact.
_REQUIRED_KEYS = {
    "record",
    "compiled",
    "mode",
    "compile_only",
    "activation_gate",
    "taxonomy_binding",
    "grounding",
    "session_lifecycle",
    "turn_taking_and_barge_in",
    "voice_default_response_rule",
    "ledger_recording",
    "governance_boundary",
    "consent_model",
    "stt_tts_path",
    "state_store_shape",
    "cpu_gate_budget",
    "rollback_plan",
    "forbidden_in_this_packet",
}

# The agreed live-session lifecycle state set, in order.
_LIFECYCLE_STATES = [
    "closed",
    "opening",
    "listening",
    "capturing",
    "transcribing",
    "responding",
    "ledger_write",
    "closing",
]


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── parse + compile mode ──────────────────────────────────────────────────────


def test_artifact_parses():
    assert _ARTIFACT.exists(), f"missing artifact {_ARTIFACT}"
    _load(_ARTIFACT)  # raises on bad JSON


def test_artifact_declares_compile_only():
    data = _load(_ARTIFACT)
    assert data.get("compile_only") is True, "artifact must flag compile_only=true"
    assert "compile_only" in data.get("mode", ""), "artifact mode must declare compile_only"
    assert "no activation authorized" in data.get("mode", "").lower(), (
        "artifact mode must state 'no activation authorized'"
    )


def test_activation_gate_is_closed():
    data = _load(_ARTIFACT)
    gate = data["activation_gate"]
    assert gate.get("activation_authorized") is False, (
        "activation_gate.activation_authorized must be false"
    )


def test_doc_exists_and_declares_compile_mode():
    assert _DOC.exists(), "LIVE_VOICE_SESSION_COMPILE.md missing"
    text = _DOC.read_text(encoding="utf-8").lower()
    assert "compile mode" in text, "doc must declare compile mode"
    assert "no activation authorized" in text, "doc must state no activation is authorized"


# ── required sections ─────────────────────────────────────────────────────────


def test_all_required_top_level_keys_present():
    data = _load(_ARTIFACT)
    missing = _REQUIRED_KEYS - set(data)
    assert not missing, f"artifact missing required top-level keys: {missing}"


# ── no activation-authorizing language ────────────────────────────────────────


def test_no_activation_authorizing_language():
    text = json.dumps(_load(_ARTIFACT)).lower()
    for phrase in _ACTIVATION_PHRASES:
        assert phrase not in text, (
            f"artifact carries activation-authorizing phrase {phrase!r} — "
            "compile mode must never authorize activation"
        )


def test_doc_free_of_activation_authorizing_language():
    text = _DOC.read_text(encoding="utf-8").lower()
    for phrase in _ACTIVATION_PHRASES:
        assert phrase not in text, f"doc carries activation-authorizing phrase {phrase!r}"


# ── taxonomy binding: this is category 2, not the others ──────────────────────


def test_taxonomy_binds_to_live_voice_session():
    data = _load(_ARTIFACT)
    tax = data["taxonomy_binding"]
    assert tax["category"] == "LiveVoiceSession"
    is_not = json.dumps(tax["is_not"]).lower()
    assert "dictation" in is_not, "must state it is NOT dictation"
    assert "ambient" in is_not, "must state it is NOT ambient"
    assert "outbound" in is_not, "must state it is NOT outbound AI voice"


def test_taxonomy_matches_the_message_contract():
    """The canonical taxonomy definition of LiveVoiceSession must exist and this
    artifact must not contradict it."""
    contract = _load(_MESSAGE_CONTRACT)
    cats = contract["voice_taxonomy"]["categories"]
    assert "LiveVoiceSession" in cats, "canonical LiveVoiceSession missing from message contract"
    # The message contract must NOT claim LiveVoiceSession is this-packet-built.
    assert "LiveVoiceSession" in contract["voice_taxonomy"]["not_implemented_here"]


# ── governance NOT bypassed ───────────────────────────────────────────────────


def test_governance_not_bypassed_language_present():
    data = _load(_ARTIFACT)
    gov = data["governance_boundary"]
    principle = gov["principle"].lower()
    assert "never auto-execute" in principle or "never auto-executes" in principle, (
        "governance principle must state a live session NEVER auto-executes"
    )
    blob = json.dumps(gov).lower()
    assert "awaiting_approval" in blob, "governance must state actions hold at AWAITING_APPROVAL"
    assert "intent" in blob and "loop" in blob, "governance must route actions to the intent loop"


def test_no_auto_execute_flag():
    data = _load(_ARTIFACT)
    assert data["governance_boundary"].get("never_auto_executes") is True, (
        "governance_boundary.never_auto_executes must be true"
    )


def test_forbidden_list_bans_auto_execute_and_activation():
    data = _load(_ARTIFACT)
    forbidden = json.dumps(data["forbidden_in_this_packet"]).lower()
    assert "auto-execute" in forbidden, "forbidden list must ban auto-execute"
    assert "activation" in forbidden, "forbidden list must ban activation"
    assert "bypass" in forbidden, "forbidden list must ban bypassing Cockpit Chat / the intent loop"
    assert "outbound ai voice" in forbidden or "cloning" in forbidden, (
        "forbidden list must ban outbound AI voice / cloning"
    )


def test_non_bypass_invariants_inherited():
    data = _load(_ARTIFACT)
    inv = json.dumps(data["governance_boundary"]["non_bypass_invariants_inherited"]).lower()
    assert "same endpoint" in inv, "must inherit the same-endpoint invariant"
    assert "same gate" in inv, "must inherit the same-gate invariant"
    assert "source is never passed" in inv or "source is never" in inv, (
        "must inherit source-independent classification"
    )


# ── voice-default response + ledger ───────────────────────────────────────────


def test_voice_default_response_rule_keeps_text():
    data = _load(_ARTIFACT)
    rule = data["voice_default_response_rule"]
    assert "default" in rule["rule"].lower()
    text_never = rule["text_is_never_skipped"].lower()
    assert "ledger" in text_never, "voice-default must still write the text turn to the ledger"


def test_ledger_records_transcript_and_events():
    data = _load(_ARTIFACT)
    ledger = data["ledger_recording"]
    assert "_save_turn" in json.dumps(ledger), "ledger write must go through _save_turn"
    assert ledger.get("no_separate_store"), "there must be no separate store"
    assert "verbatim" in json.dumps(ledger).lower(), "operator transcript must be recorded verbatim"


# ── consent: live_session is future-grantable, not now ────────────────────────


def test_live_session_consent_mode_is_future_not_now():
    data = _load(_ARTIFACT)
    consent = data["consent_model"]
    assert "live_session" in consent["required_grant_future"], (
        "consent must name the future VoiceConsentGrant(live_session) mode"
    )
    assert consent.get("grantable_now") is False, "live_session mode must NOT be grantable now"
    note = consent["future_grantable_note"].lower()
    assert "future-grantable" in note and "not grantable now" in note, (
        "consent must declare live_session future-grantable, not grantable now"
    )


def test_consent_is_fail_closed_and_revocation_immediate():
    data = _load(_ARTIFACT)
    consent = data["consent_model"]
    assert "fail-closed" in json.dumps(consent).lower(), "consent model must be fail-closed"
    assert "immediately" in consent["revocation"]["rule"].lower(), (
        "revocation must close the session immediately"
    )
    assert consent["revocation"].get("immediate") is True


# ── barge-in reuse ────────────────────────────────────────────────────────────


def test_barge_in_is_reused_not_reinvented():
    data = _load(_ARTIFACT)
    bi = data["turn_taking_and_barge_in"]
    assert bi.get("no_new_barge_in") is True, "barge-in must not be reinvented"
    reuse = bi["barge_in_reuse"].lower()
    assert "voice-controller.ts" in reuse, "barge-in must reuse voice-controller.ts"
    assert "canceltts" in reuse, "barge-in reuse must reference the existing cancelTts path"


# ── VoiceSession reference, not redefinition ──────────────────────────────────


def test_voice_session_is_referenced_not_redefined():
    data = _load(_ARTIFACT)
    lifecycle = data["session_lifecycle"]
    assert lifecycle.get("reference_only_for_voice_session") is True, (
        "session_lifecycle must reference VoiceSession, not redefine it"
    )
    assert "voice_intent_contract_types.json" in lifecycle.get("voice_session_binds_to", ""), (
        "session_lifecycle must bind to voice_intent_contract_types.json"
    )


def test_canonical_voice_session_shape_still_exists():
    """The reference target must actually exist: VoiceSession in the canonical
    type-shapes artifact."""
    types = {t["name"]: t for t in _load(_TYPES)["types"]}
    assert "VoiceSession" in types, "canonical VoiceSession missing from types artifact"


def test_lifecycle_declares_the_agreed_state_set():
    data = _load(_ARTIFACT)
    lifecycle = data["session_lifecycle"]
    assert lifecycle["states"] == _LIFECYCLE_STATES, (
        f"session lifecycle states must be exactly {_LIFECYCLE_STATES} in order"
    )
    assert lifecycle.get("transitions"), "lifecycle must declare transitions"


# ── STT/TTS path: reuse, no outbound voice ────────────────────────────────────


def test_stt_tts_path_reuses_voice_server():
    data = _load(_ARTIFACT)
    path = data["stt_tts_path"]
    assert "voice_server.py" in path["stt"]["engine"], "STT must reuse umh/voice_server.py"
    assert "voice_server.py" in path["tts"]["engine"], "TTS must reuse umh/voice_server.py"
    assert "kokoro" in path["tts"]["engine"].lower(), "TTS must reuse Kokoro"
    assert "whisper" in path["stt"]["engine"].lower(), "STT must reuse whisper"
    assert path.get("protocol_unchanged"), "voice_server WS protocol must be unchanged"


def test_tts_is_not_outbound_ai_voice():
    data = _load(_ARTIFACT)
    no_outbound = data["stt_tts_path"]["tts"]["no_outbound_voice"].lower()
    assert "never" in no_outbound, "TTS must never render outbound AI voice"
    assert "clone" in no_outbound, "TTS must never clone any voice"


# ── CPU budget (CPU Gate Law) ─────────────────────────────────────────────────


def test_cpu_budget_has_numeric_bounds_and_adds_no_process():
    data = _load(_ARTIFACT)
    budget = data["cpu_gate_budget"]
    assert "cpu gate law" in budget["law"].lower(), "budget must bind to the CPU Gate Law"
    cpu = budget["cpu_bounds"]
    for key in ("server_sustained_pct_single_core_max", "server_sustained_pct_single_core_target"):
        assert isinstance(cpu.get(key), (int, float)), f"cpu_bounds.{key} must be numeric"
    assert (
        cpu["server_sustained_pct_single_core_target"]
        <= cpu["server_sustained_pct_single_core_max"]
    )
    mem = budget["memory_bounds"]
    assert (
        isinstance(mem["server_resident_mb_max"], (int, float))
        and mem["server_resident_mb_max"] > 0
    )
    assert "no new server process" in json.dumps(budget).lower().replace("adds no", "no"), (
        "budget must state no new server process is added"
    )


# ── rollback ──────────────────────────────────────────────────────────────────


def test_rollback_flag_off_means_no_live_mode():
    data = _load(_ARTIFACT)
    rollback = data["rollback_plan"]
    for key in ("flag_off", "revoke", "artifact_rollback"):
        assert key in rollback, f"rollback_plan missing {key}"
    flag_off = rollback["flag_off"].lower()
    assert "off" in flag_off and ("no live session" in flag_off or "no live mode" in flag_off), (
        "flag off must mean no live mode / no live session"
    )
    assert "immediately" in rollback["revoke"].lower(), "revoke must close the session immediately"


# ── no implementation actually shipped ────────────────────────────────────────


def test_no_live_session_field_added_to_voice_store():
    """Compile mode: the future store fields must NOT have been added to the real
    voiceStore.ts — the artifact declares them, it does not implement them."""
    if not _VOICE_STORE.exists():
        return
    text = _VOICE_STORE.read_text(encoding="utf-8")
    for field in ("liveSessionState", "liveSessionId", "liveModeEngaged"):
        assert field not in text, (
            f"voiceStore.ts already carries {field!r} — compile mode adds no "
            "implementation; the field is declared in the artifact only"
        )


# ── tenant / device safety ────────────────────────────────────────────────────


def test_no_tenant_or_device_literal_in_artifact():
    text = json.dumps(_load(_ARTIFACT)).lower()
    for literal in _BANNED_LITERALS:
        assert literal not in text, (
            f"artifact carries banned literal {literal!r} — device/tenant "
            "bindings must go through registry references, never literals"
        )


def test_doc_free_of_tenant_and_device_literals():
    text = _DOC.read_text(encoding="utf-8").lower()
    for literal in _BANNED_LITERALS:
        assert literal not in text, (
            f"LIVE_VOICE_SESSION_COMPILE.md carries banned literal {literal!r}"
        )
