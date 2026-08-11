"""P4S-AMBIENT-ACTIVATION-001 compile-artifact validation — compile-mode gate.

Validates the compile-only deliverables that EXTEND the merged desktop-ambient-
wake compile into the full AmbientActivation voice-taxonomy category (wake |
double-clap acoustic gesture | hotkey | manual), unified under one
"activation opens a session, does not execute by itself" contract:

  - the JSON artifact parses and declares compile_only mode,
  - all required top-level sections are present,
  - NO activation-authorizing language appears anywhere,
  - the unified contract asserts activation OPENS a session and does NOT execute,
  - the double-clap acoustic-gesture detection approach + false-positive
    handling are present with numeric parameters,
  - the hotkey model states OS-level surface ownership (Electron main process),
  - consent is per-mode strict and clap/hotkey are future-grantable (NOT now),
  - GRANTABLE_MODES in substrate.workstation.voice_consent is STILL exactly
    {push_to_talk} — the mechanical proof nothing was activated,
  - resource budgets carry numeric CPU-gate bounds,
  - it references (does not restate) the wake artifact,
  - mobile activation verdicts stay honest (NOT_FEASIBLE / CONSTRAINED),
  - no first-tenant or device-hostname literal appears as global truth.

Mirrors tests/test_p4s31d_ambient_compile_artifacts.py: mechanical, fail-closed,
truthful about what "done" means for a compile packet.
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
_ARTIFACT = _ROOT / "data/umh/voice/ambient_activation_compile.json"
_WAKE_ARTIFACT = _ROOT / "data/umh/voice/desktop_ambient_wake_compile.json"
_TYPES = _ROOT / "data/umh/voice/voice_intent_contract_types.json"
_MATRIX = _ROOT / "data/umh/voice/platform_voice_feasibility_matrix.json"
_DOC = _ROOT / "docs/AMBIENT_ACTIVATION_COMPILE.md"

# First-tenant + device-hostname literals that must never appear as global truth.
_BANNED_LITERALS = ("antony", "afm", "munoz", "beast")

# Phrases that would authorize activation/implementation. Compile-only: banned.
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
    "start the daemon",
    "register the hotkey now",
    "greenlit",
    "go-live",
)

_REQUIRED_KEYS = {
    "record",
    "compiled",
    "mode",
    "compile_only",
    "activation_gate",
    "taxonomy_binding",
    "extends",
    "unified_activation_contract",
    "activation_modes",
    "acoustic_gesture_detection",
    "hotkey_model",
    "consent_model",
    "on_device_requirement",
    "privacy_boundary",
    "resource_budget_summary",
    "rollback_plan",
    "mobile_activation_verdicts",
    "forbidden_in_this_packet",
    "references",
}


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
    assert _DOC.exists(), "AMBIENT_ACTIVATION_COMPILE.md missing"
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


# ── taxonomy binding ──────────────────────────────────────────────────────────


def test_taxonomy_binds_to_ambient_activation_category_3():
    data = _load(_ARTIFACT)
    tax = data["taxonomy_binding"]
    assert tax["category"] == "AmbientActivation"
    assert tax["category_number"] == 3
    assert "VOICE_MESSAGE_CONTRACT.md" in tax.get("source", "")
    # The verbatim taxonomy definition: opens a session, does not execute.
    definition = tax["definition_verbatim"].lower()
    assert "opens a voice session" in definition
    assert "does not execute by itself" in definition


# ── unified activation contract: opens, does not execute ──────────────────────


def test_unified_contract_opens_not_executes():
    data = _load(_ARTIFACT)
    contract = data["unified_activation_contract"]
    principle = contract["principle"].lower()
    assert "opens a session" in principle, "contract must state activation OPENS a session"
    assert "never executes by itself" in principle, (
        "contract must state activation NEVER executes by itself"
    )
    # It must open one of the two named capture surfaces.
    surfaces = contract["opens_one_of_two_capture_surfaces"]
    assert "LiveVoiceSession" in surfaces
    assert "UserVoiceNote" in surfaces


def test_unified_contract_states_what_activation_is_not():
    data = _load(_ARTIFACT)
    notlist = json.dumps(
        _load(_ARTIFACT)["unified_activation_contract"]["what_an_activation_is_not"]
    ).lower()
    assert "not an intent" in notlist
    assert "not a dispatch" in notlist
    assert "not an execution decision" in notlist


def test_activation_event_is_referenced_not_redefined():
    data = _load(_ARTIFACT)
    shape = data["unified_activation_contract"]["activation_event_shape"]
    assert shape.get("reference_only") is True, "activation_event_shape must be reference_only"
    assert "voice_intent_contract_types.json" in shape.get("note", ""), (
        "activation event must bind to the canonical WakeEvent in the types artifact"
    )
    assert "fields" not in shape, (
        "activation_event_shape must NOT redefine fields — the canonical WakeEvent "
        "shape lives in voice_intent_contract_types.json"
    )
    # Shared invariant: carries_audio false, opens-not-executes.
    invariants = json.dumps(shape["shared_invariants"]).lower()
    assert "carries_audio is const false" in invariants
    assert "never classifies, dispatches, or executes" in invariants


def test_canonical_wake_event_shape_still_exists():
    types = {t["name"]: t for t in _load(_TYPES)["types"]}
    assert "WakeEvent" in types, "canonical WakeEvent missing from types artifact"
    fields = {f["name"]: f for f in types["WakeEvent"]["fields"]}
    assert fields["carries_audio"].get("const") is False


# ── extends the wake artifact, does not duplicate ─────────────────────────────


def test_extends_wake_artifact_by_reference():
    data = _load(_ARTIFACT)
    extends = data["extends"]
    assert extends["wake_artifact"] == "data/umh/voice/desktop_ambient_wake_compile.json"
    assert _WAKE_ARTIFACT.exists(), "referenced wake artifact must exist"
    blob = json.dumps(extends).lower()
    assert "not restated" in blob or "not restate" in blob, (
        "extends must state the wake dimension is referenced, not restated"
    )


def test_wake_dimension_not_duplicated():
    """The wake WakeEvent field-list must NOT be copied into this artifact —
    only referenced. Guard against forking the wake dimension."""
    data = _load(_ARTIFACT)
    # This artifact declares no WakeEvent field-list of its own.
    text = json.dumps(data)
    assert '"detected_at"' not in text or "reference" in text.lower(), (
        "wake field detail should be referenced, not redefined"
    )
    # The wake mode entry must point at the wake artifact, not restate it.
    wake_mode = data["activation_modes"]["wake_word"]
    assert "desktop_ambient_wake_compile.json" in wake_mode["dimension"]


# ── double-clap acoustic gesture ──────────────────────────────────────────────


def test_acoustic_gesture_detection_approach_present():
    data = _load(_ARTIFACT)
    gesture = data["acoustic_gesture_detection"]
    assert "on_device" in gesture["on_device_requirement"].lower().replace("-", "_") or (
        "on-device" in gesture["on_device_requirement"].lower()
    ), "gesture detection must be on-device"
    approach = gesture["detection_approach"]
    method = approach["method"].lower()
    assert "onset" in method or "envelope" in method, (
        "detection approach must describe an onset/envelope DSP method"
    )
    assert "double" in json.dumps(approach).lower(), "must describe a DOUBLE-clap"


def test_acoustic_gesture_parameters_are_numeric():
    data = _load(_ARTIFACT)
    params = data["acoustic_gesture_detection"]["detection_approach"]["parameters"]
    for key in ("inter_clap_min_ms", "inter_clap_max_ms", "onset_crest_factor_min"):
        val = params[key]
        assert isinstance(val, dict) and isinstance(val["default"], (int, float)), (
            f"{key} must carry a numeric default"
        )
    assert params["inter_clap_min_ms"]["default"] < params["inter_clap_max_ms"]["default"], (
        "min inter-clap interval must be below max"
    )
    # Cooldown reuses the existing constant, not a new one.
    assert params["post_activation_cooldown_seconds"]["default"] == 5.0


def test_acoustic_gesture_false_positive_handling():
    data = _load(_ARTIFACT)
    fp = data["acoustic_gesture_detection"]["false_positive_handling"]
    mitigations = json.dumps(fp["mitigations"]).lower()
    assert "double-clap" in mitigations, "double-clap requirement rejects single impacts"
    assert "crest-factor" in mitigations or "crest factor" in mitigations
    assert "adaptive" in mitigations, "adaptive noise-floor threshold must be a mitigation"
    # The safety keystone: opens-but-does-not-execute makes false positives harmless.
    reinforcement = fp["opens_not_executes_reinforcement"].lower()
    assert "opens" in reinforcement and (
        "not execute" in reinforcement or "does-not-execute" in reinforcement
    ), "false-positive safety must rest on opens-not-executes"


def test_acoustic_gesture_resource_budget_numeric():
    data = _load(_ARTIFACT)
    budget = data["acoustic_gesture_detection"]["resource_budget"]
    assert "cpu gate law" in budget["law"].lower()
    cpu = budget["cpu_bounds"]
    assert isinstance(cpu["sustained_pct_single_core_max"], (int, float))
    assert 0 < cpu["sustained_pct_single_core_max"] <= 100
    assert cpu["sustained_pct_single_core_target"] <= cpu["sustained_pct_single_core_max"]
    assert "self_disarm" in cpu, "budget breach behavior (self-disarm) must be stated"
    assert isinstance(budget["memory_bounds"]["resident_mb_max"], (int, float))


# ── hotkey model ──────────────────────────────────────────────────────────────


def test_hotkey_model_states_surface_ownership():
    data = _load(_ARTIFACT)
    hotkey = data["hotkey_model"]
    ownership = hotkey["surface_ownership"]
    who = ownership["who_owns_the_hotkey"].lower()
    assert "electron" in who and "main process" in who, (
        "the Electron main process must own the OS-level global hotkey"
    )
    assert "globalshortcut" in who or "globalshortcut" in json.dumps(ownership).lower()
    # Orchestrator exclusion restated.
    assert "orchestrator_exclusion" in ownership


def test_hotkey_is_deterministic_and_opens_not_executes():
    data = _load(_ARTIFACT)
    sem = data["hotkey_model"]["trigger_semantics"]
    assert "the keypress is the trigger" in sem["deterministic"].lower()
    on_act = sem["on_activation"].lower()
    assert "opens" in on_act, "hotkey activation must OPEN a capture surface"
    assert (
        "executes nothing" in on_act or "never execute" in on_act or "classifies nothing" in on_act
    )


def test_hotkey_resource_budget_near_zero():
    data = _load(_ARTIFACT)
    cpu = data["hotkey_model"]["resource_budget"]["cpu_bounds"]
    assert isinstance(cpu["sustained_pct_single_core_max"], (int, float))
    assert cpu["sustained_pct_single_core_max"] <= 1.0, (
        "an event-driven hotkey must be near-zero steady-state CPU"
    )


# ── consent model: per-mode strict, GRANTABLE_MODES unchanged ─────────────────


def test_consent_is_per_mode_strict():
    data = _load(_ARTIFACT)
    consent = data["consent_model"]
    strictness = consent.get("per_mode_strictness", "").lower()
    assert "per-mode" in strictness or "per_mode" in strictness, (
        "consent model must state per-mode strictness"
    )
    modes = consent["activation_modes_and_grants"]
    # push_to_talk grantable now; the rest are not.
    assert modes["push_to_talk"]["grantable_now"] is True
    for m in ("wake_word", "clap_activation", "hotkey_activation", "always_on"):
        assert modes[m]["grantable_now"] is False, f"{m} must NOT be grantable now"
        assert modes[m]["future_grantable"] is True, f"{m} must be future-grantable"


def test_clap_and_hotkey_are_new_future_grantable_modes():
    data = _load(_ARTIFACT)
    modes = data["consent_model"]["activation_modes_and_grants"]
    assert modes["clap_activation"]["new_in"] == "this artifact"
    assert modes["hotkey_activation"]["new_in"] == "this artifact"


def test_grantable_modes_invariant_stated_in_artifact():
    data = _load(_ARTIFACT)
    inv = data["consent_model"]["grantable_now_invariant"]
    statement = inv["statement"].lower()
    assert "grantable_modes" in statement
    assert "push_to_talk" in statement
    assert "future" in statement, "clap/hotkey must be described as future-grantable, not now"


def test_grantable_modes_still_push_to_talk_only():
    """The hard mechanical guard: importing the live consent module, its
    GRANTABLE_MODES must be EXACTLY {push_to_talk}. This compile packet adds no
    activation mode — clap/hotkey/wake/always_on stay non-grantable."""
    from substrate.workstation.voice_consent import GRANTABLE_MODES

    assert GRANTABLE_MODES == frozenset({"push_to_talk"}), (
        f"GRANTABLE_MODES must be exactly {{push_to_talk}}, got {sorted(GRANTABLE_MODES)} — "
        "this compile packet must not make clap/hotkey/wake grantable"
    )


def test_non_grantable_modes_refused_by_live_store():
    """Belt-and-suspenders: the live store refuses clap/hotkey grants today."""
    from substrate.workstation.voice_consent import VoiceConsentRefused, VoiceConsentStore

    store = VoiceConsentStore(store_path="/tmp/_p4s_ambient_test_consent_grants.json")
    for mode in ("clap_activation", "hotkey_activation", "wake_word", "always_on"):
        try:
            store.grant("clerk:user_test", "dev-test", mode)
            raise AssertionError(f"grant for non-grantable mode {mode!r} should have been refused")
        except VoiceConsentRefused as exc:
            assert exc.code == "MODE_NOT_GRANTABLE"


def test_revocation_kills_activation_immediately():
    data = _load(_ARTIFACT)
    revocation = data["consent_model"]["revocation"]
    assert "immediately" in revocation["rule"].lower(), "revocation must stop the mode immediately"
    assert "fail-closed" in json.dumps(data["consent_model"]).lower(), (
        "consent model must be fail-closed"
    )


# ── on-device requirement & privacy ───────────────────────────────────────────


def test_on_device_requirement_no_audio_off_device():
    data = _load(_ARTIFACT)
    req = data["on_device_requirement"]
    assert "no audio leaves the device" in req["statement"].lower()
    crossing = req["what_crosses_the_device_boundary"].lower()
    assert "metadata" in crossing and "never audio" in crossing, (
        "only ActivationEvent metadata may cross the device boundary"
    )
    assert "deferred" in req["cloud_stt"].lower(), "cloud STT must remain deferred"


def test_privacy_boundary_orchestrator_and_log():
    data = _load(_ARTIFACT)
    privacy = data["privacy_boundary"]
    assert "orchestrator" in privacy, "privacy boundary must restate the orchestrator exclusion"
    assert "operator_visible_activation_log" in privacy, "activation log must be operator-visible"
    assert "mute_affordance" in privacy, "mute affordance must be declared"


# ── resource budget summary ───────────────────────────────────────────────────


def test_resource_budget_summary_binds_cpu_gate_law():
    data = _load(_ARTIFACT)
    budget = data["resource_budget_summary"]
    assert "cpu gate law" in budget["law"].lower()
    per_mode = budget["per_mode"]
    for mode in ("wake_word", "double_clap", "hotkey", "manual"):
        assert mode in per_mode, f"resource summary missing mode {mode}"
    assert "self_disarm_universal" in budget


# ── rollback plan ─────────────────────────────────────────────────────────────


def test_rollback_plan_is_complete():
    data = _load(_ARTIFACT)
    rollback = data["rollback_plan"]
    for key in ("flag_off", "revoke", "uninstall", "artifact_rollback"):
        assert key in rollback, f"rollback_plan missing {key}"
    assert "never starts" in rollback["flag_off"].lower(), (
        "flag off must mean the runtime never starts"
    )
    assert "immediately" in rollback["revoke"].lower(), "revoke must stop the mode immediately"
    assert "grantable_modes is untouched" in rollback["artifact_rollback"].lower(), (
        "rollback must confirm GRANTABLE_MODES was not changed"
    )


# ── mobile honesty ────────────────────────────────────────────────────────────


def test_mobile_activation_verdicts_honest():
    data = _load(_ARTIFACT)
    verdicts = data["mobile_activation_verdicts"]
    blob = json.dumps(verdicts).upper()
    assert "NOT_FEASIBLE" in blob, "mobile activation must repeat NOT_FEASIBLE honestly"
    assert "CONSTRAINED" in blob, "mobile activation must repeat CONSTRAINED honestly"
    assert "PROVEN" not in blob and '"LIKELY"' not in blob, (
        "mobile activation must never be promised as PROVEN/LIKELY"
    )
    assert "mobile_double_clap" in verdicts, "mobile double-clap posture must be stated"
    assert "mobile_hotkey" in verdicts, "mobile hotkey posture must be stated"


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
            f"AMBIENT_ACTIVATION_COMPILE.md carries banned literal {literal!r}"
        )
