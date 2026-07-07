"""P4S-31D desktop ambient wake-word compile-artifact validation — compile-mode gate.

Validates the compile-only deliverables covering the wake portion of P4S-31D-3
and the ambient portion of P4S-31D-6:
  - the JSON artifact parses and declares compile_only mode,
  - all required top-level sections are present,
  - NO activation-authorizing language appears anywhere in the artifact,
  - consent per-mode strictness is stated (wake_word and always_on are separate
    grants; revocation kills listening immediately),
  - the resource budget carries NUMERIC bounds (CPU Gate Law compliance),
  - the WakeEvent shape is REFERENCED from voice_intent_contract_types.json,
    never redefined,
  - the daemon lifecycle declares the exact agreed state set,
  - mobile ambient verdicts honestly repeat the feasibility matrix
    (NOT_FEASIBLE / CONSTRAINED — never promised),
  - no first-tenant or device-hostname literal appears as global truth.

Mirrors tests/test_p4s31d_voice_matrix_artifacts.py: mechanical, fail-closed,
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
_ARTIFACT = _ROOT / "data/umh/voice/desktop_ambient_wake_compile.json"
_TYPES = _ROOT / "data/umh/voice/voice_intent_contract_types.json"
_MATRIX = _ROOT / "data/umh/voice/platform_voice_feasibility_matrix.json"
_DOC = _ROOT / "docs/DESKTOP_AMBIENT_WAKE_COMPILE.md"

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
    "start the daemon",
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
    "packets",
    "scope",
    "wake_event_contract",
    "daemon_lifecycle",
    "consent_model",
    "privacy_boundary",
    "false_positive_handling",
    "resource_budget",
    "rollback_plan",
    "mobile_ambient_verdicts",
    "forbidden_in_this_packet",
}

# The agreed daemon lifecycle state set, in order.
_LIFECYCLE_STATES = [
    "disabled",
    "consent_granted",
    "armed",
    "wake_detected",
    "capture_window",
    "rearm",
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
    assert _DOC.exists(), "DESKTOP_AMBIENT_WAKE_COMPILE.md missing"
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


# ── wake event contract: reference, not redefinition ──────────────────────────


def test_wake_event_is_referenced_not_redefined():
    data = _load(_ARTIFACT)
    contract = data["wake_event_contract"]
    assert contract.get("reference_only") is True, "wake_event_contract must be reference_only"
    assert "voice_intent_contract_types.json" in contract.get("binds_to", ""), (
        "wake_event_contract must bind to voice_intent_contract_types.json"
    )
    # No parallel field-list: redefining fields here would fork the type system.
    assert "fields" not in contract, (
        "wake_event_contract must NOT redefine WakeEvent fields — the canonical "
        "shape lives in voice_intent_contract_types.json"
    )


def test_canonical_wake_event_shape_still_exists():
    """The reference target must actually exist: WakeEvent with carries_audio
    const false in the canonical type-shapes artifact."""
    types = {t["name"]: t for t in _load(_TYPES)["types"]}
    assert "WakeEvent" in types, "canonical WakeEvent missing from types artifact"
    fields = {f["name"]: f for f in types["WakeEvent"]["fields"]}
    assert fields["carries_audio"].get("const") is False


# ── daemon lifecycle ──────────────────────────────────────────────────────────


def test_lifecycle_declares_the_agreed_state_set():
    data = _load(_ARTIFACT)
    lifecycle = data["daemon_lifecycle"]
    assert lifecycle["states"] == _LIFECYCLE_STATES, (
        f"daemon lifecycle states must be exactly {_LIFECYCLE_STATES} in order"
    )
    assert "electron" in lifecycle["owner_process"].lower(), (
        "the Electron main process must own the daemon"
    )
    assert lifecycle.get("transitions"), "lifecycle must declare transitions"


def test_lifecycle_reuses_existing_ambient_vocabulary():
    data = _load(_ARTIFACT)
    reuse = data["daemon_lifecycle"].get("vocabulary_reuse", {})
    assert "ambient_wake_runtime.py" in reuse.get("source", ""), (
        "lifecycle must bind to substrate/workstation/ambient_wake_runtime.py "
        "vocabulary, not invent a parallel state machine"
    )


# ── consent model ─────────────────────────────────────────────────────────────


def test_consent_is_per_mode_strict():
    data = _load(_ARTIFACT)
    consent = data["consent_model"]
    strictness = consent.get("per_mode_strictness", "").lower()
    assert "per-mode" in strictness or "per_mode" in strictness, (
        "consent model must state per-mode strictness"
    )
    grants = consent["required_grants"]
    assert grants["wake_word_mode"] == ["VoiceConsentGrant(wake_word)"]
    assert set(grants["always_on_mode"]) == {
        "VoiceConsentGrant(wake_word)",
        "VoiceConsentGrant(always_on)",
    }, "always_on mode must require BOTH grants"


def test_revocation_kills_listening_immediately():
    data = _load(_ARTIFACT)
    revocation = data["consent_model"]["revocation"]
    assert "immediately" in revocation["rule"].lower(), "revocation must kill listening immediately"
    assert "fail-closed" in json.dumps(data["consent_model"]).lower(), (
        "consent model must be fail-closed"
    )


# ── privacy boundary ──────────────────────────────────────────────────────────


def test_privacy_boundary_is_on_device_metadata_only():
    data = _load(_ARTIFACT)
    privacy = data["privacy_boundary"]
    assert "on-device" in privacy["on_device_detection"].lower()
    crossing = privacy["what_crosses_the_device_boundary"].lower()
    assert "metadata" in crossing and "never audio" in crossing, (
        "only WakeEvent metadata may cross the device boundary"
    )
    assert "deferred" in privacy["cloud_stt"].lower(), (
        "cloud STT must remain deferred to the privacy review"
    )
    assert "orchestrator" in privacy, "privacy boundary must restate the orchestrator exclusion"


# ── false-positive handling ───────────────────────────────────────────────────


def test_false_positive_handling_is_complete():
    data = _load(_ARTIFACT)
    fp = data["false_positive_handling"]
    threshold = fp["confidence_threshold"]
    assert isinstance(threshold["default"], (int, float))
    assert 0.0 < threshold["default"] < 1.0
    assert isinstance(fp["cooldown_seconds"]["default"], (int, float))
    assert fp["cooldown_seconds"]["default"] > 0
    assert "operator_visible_wake_log" in fp, "wake log must be operator-visible"
    assert "mute_affordance" in fp, "mute affordance must be declared"


def test_cooldown_and_timeout_reuse_existing_constants():
    """The numeric defaults must match the existing ambient_wake_runtime
    constants they claim to reuse (COOLDOWN_SECONDS=5.0, COMMAND_TIMEOUT=120.0)."""
    data = _load(_ARTIFACT)
    fp = data["false_positive_handling"]
    assert fp["cooldown_seconds"]["default"] == 5.0
    assert fp["capture_window_timeout_seconds"]["default"] == 120.0


# ── resource budget (CPU Gate Law) ────────────────────────────────────────────


def test_resource_budget_has_numeric_cpu_bounds():
    data = _load(_ARTIFACT)
    budget = data["resource_budget"]
    assert "cpu gate law" in budget["law"].lower(), "resource budget must bind to the CPU Gate Law"
    cpu = budget["cpu_bounds"]
    for key in (
        "sustained_pct_single_core_max",
        "sustained_pct_single_core_target",
        "detection_burst_pct_single_core_max",
        "detection_burst_duration_seconds_max",
    ):
        assert isinstance(cpu.get(key), (int, float)), f"cpu_bounds.{key} must be numeric"
    assert 0 < cpu["sustained_pct_single_core_max"] <= 100
    assert cpu["sustained_pct_single_core_target"] <= cpu["sustained_pct_single_core_max"]
    assert "self_disarm" in cpu, "budget breach behavior (self-disarm) must be stated"


def test_resource_budget_has_numeric_memory_bound():
    data = _load(_ARTIFACT)
    mem = data["resource_budget"]["memory_bounds"]
    assert isinstance(mem["resident_mb_max"], (int, float))
    assert mem["resident_mb_max"] > 0


def test_candidate_runtimes_carry_numeric_footprints():
    data = _load(_ARTIFACT)
    candidates = data["resource_budget"]["candidate_runtimes"]
    names = {c["runtime"] for c in candidates}
    assert {"openwakeword_onnx", "porcupine_native"} <= names, (
        "both candidate runtimes must be listed"
    )
    for c in candidates:
        for key in ("est_cpu_pct_single_core", "est_resident_mb"):
            bounds = c[key]
            assert (
                isinstance(bounds, list)
                and len(bounds) == 2
                and all(isinstance(v, (int, float)) for v in bounds)
                and bounds[0] <= bounds[1]
            ), f"{c['runtime']}.{key} must be a numeric [low, high] range"


def test_no_wake_word_dependency_added():
    """Compile mode: no wake-word library may enter any dependency manifest."""
    manifests = [
        _ROOT / "requirements.txt",
        _ROOT / "cockpit/package.json",
    ]
    for manifest in manifests:
        if not manifest.exists():
            continue
        text = manifest.read_text(encoding="utf-8").lower()
        for lib in ("openwakeword", "pvporcupine", "porcupine", "picovoice"):
            assert lib not in text, (
                f"{manifest.name} carries wake-word dependency {lib!r} — "
                "compile mode adds no dependency"
            )


# ── rollback plan ─────────────────────────────────────────────────────────────


def test_rollback_plan_is_complete():
    data = _load(_ARTIFACT)
    rollback = data["rollback_plan"]
    for key in ("flag_off", "revoke", "uninstall", "artifact_rollback"):
        assert key in rollback, f"rollback_plan missing {key}"
    assert "never starts" in rollback["flag_off"].lower(), (
        "flag off must mean the daemon never starts"
    )
    assert "immediately" in rollback["revoke"].lower(), "revoke must stop listening immediately"


# ── mobile ambient honesty ────────────────────────────────────────────────────


def test_mobile_ambient_verdicts_repeat_the_matrix_honestly():
    data = _load(_ARTIFACT)
    verdicts = data["mobile_ambient_verdicts"]
    blob = json.dumps(verdicts).upper()
    assert "NOT_FEASIBLE" in blob, "mobile ambient must repeat NOT_FEASIBLE honestly"
    assert "CONSTRAINED" in blob, "mobile ambient must repeat CONSTRAINED honestly"
    assert "PROVEN" not in blob and '"LIKELY"' not in blob, (
        "mobile ambient must never be promised as PROVEN/LIKELY"
    )


def test_mobile_verdicts_match_the_feasibility_matrix():
    matrix = _load(_MATRIX)["summary_verdicts"]["mobile_ambient_wake_word"]
    artifact = _load(_ARTIFACT)["mobile_ambient_verdicts"]["mobile_ambient_wake_word"]
    assert artifact["ambient"] == matrix["ambient"], (
        "artifact mobile ambient verdict must match the matrix verbatim"
    )
    assert artifact["wake_word"] == matrix["wake_word"], (
        "artifact mobile wake-word verdict must match the matrix verbatim"
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
            f"DESKTOP_AMBIENT_WAKE_COMPILE.md carries banned literal {literal!r}"
        )
