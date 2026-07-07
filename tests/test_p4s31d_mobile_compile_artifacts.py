"""P4S-31D-4/5 mobile voice compile artifact validation — compile-mode gate.

Validates the compile-only deliverables of the mobile voice plan (Lane F):
  - data/umh/voice/mobile_voice_compile.json parses and declares
    compile_only with NO activation authorized,
  - every required section/key is present (per-surface PTT, mobile-browser
    limitations, native permissions, background/ambient, battery/privacy,
    adapter-into-chat),
  - the verdicts AGREE with data/umh/voice/platform_voice_feasibility_matrix.json
    (both files loaded and cross-checked — the compile deepens the matrix,
    never contradicts it),
  - NO activation language and NO mobile ambient/background promise,
  - NO first-tenant or device-hostname literal,
  - NO implementation files shipped by this compile.

Mirrors tests/test_p4s31d_voice_matrix_artifacts.py: mechanical, fail-closed,
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
_COMPILE = _ROOT / "data/umh/voice/mobile_voice_compile.json"
_MATRIX = _ROOT / "data/umh/voice/platform_voice_feasibility_matrix.json"
_DOC = _ROOT / "docs/MOBILE_VOICE_COMPILE.md"

# First-tenant + device-hostname literals that must never appear as global truth.
_BANNED_LITERALS = ("antony", "afm", "munoz", "beast")

# Phrases that would authorize activation/implementation. "no activation
# authorized" is REQUIRED language and deliberately does not match these.
_ACTIVATION_LANGUAGE = (
    "activation is authorized",
    "authorized to activate",
    "activation approved",
    "implementation is authorized",
    "authorized to implement",
    "begin implementation",
    "start implementation",
    "ship now",
    "go live",
)

_REQUIRED_SURFACES = {"native_ios", "native_android", "mobile_safari", "mobile_chrome"}

_REQUIRED_TOP_KEYS = {
    "mode",
    "compile_only",
    "activation",
    "packets",
    "doctrine",
    "agrees_with",
    "owner_observation_2026_07_06",
    "push_to_talk_per_surface",
    "mobile_browser_limitations",
    "native_app_permissions",
    "background_ambient_feasibility",
    "battery_privacy_constraints",
    "adapter_into_cockpit_chat",
    "verdict_consistency",
}

# Files this compile is allowed to ship. Anything voice-*implementation*
# (adapter/route/cockpit/service code) shipping under this compile is a stop
# condition.
_ALLOWED_FILES = {
    "docs/MOBILE_VOICE_COMPILE.md",
    "data/umh/voice/mobile_voice_compile.json",
    "tests/test_p4s31d_mobile_compile_artifacts.py",
}


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── parse + compile mode ──────────────────────────────────────────────────────


def test_artifacts_exist_and_parse():
    assert _COMPILE.exists(), "mobile_voice_compile.json missing"
    assert _MATRIX.exists(), "feasibility matrix missing (cross-check source)"
    assert _DOC.exists(), "MOBILE_VOICE_COMPILE.md missing"
    _load(_COMPILE)  # raises on bad JSON
    _load(_MATRIX)


def test_compile_declares_compile_only_no_activation():
    data = _load(_COMPILE)
    assert data.get("compile_only") is True, "compile artifact must flag compile_only"
    mode = data.get("mode", "")
    assert "compile_only" in mode, "mode must declare compile_only"
    assert "no activation authorized" in mode.lower(), (
        "mode must state that no activation is authorized"
    )
    assert "not authorized" in data.get("activation", "").lower(), (
        "activation field must explicitly deny authorization"
    )


def test_doc_declares_compile_mode_no_activation():
    text = _DOC.read_text(encoding="utf-8").lower()
    assert "compile mode" in text, "doc must declare compile mode"
    assert "no activation authorized" in text, "doc must state that no activation is authorized"


def test_no_activation_language_in_artifacts():
    """Neither artifact may carry language that authorizes activation/impl."""
    for path in (_COMPILE, _DOC):
        text = path.read_text(encoding="utf-8").lower()
        for phrase in _ACTIVATION_LANGUAGE:
            assert phrase not in text, (
                f"{path.name} carries activation language {phrase!r} — "
                "compile mode authorizes nothing"
            )


# ── required keys / sections ──────────────────────────────────────────────────


def test_required_top_level_keys_present():
    data = _load(_COMPILE)
    missing = _REQUIRED_TOP_KEYS - set(data)
    assert not missing, f"mobile_voice_compile.json missing keys: {missing}"
    assert set(data["packets"]) == {"P4S-31D-4", "P4S-31D-5"}, (
        "compile must cover exactly the two mobile packets"
    )


def test_push_to_talk_covers_all_four_surfaces():
    data = _load(_COMPILE)
    surfaces = data["push_to_talk_per_surface"]
    missing = _REQUIRED_SURFACES - set(surfaces)
    assert not missing, f"push_to_talk_per_surface missing surfaces: {missing}"
    for name in _REQUIRED_SURFACES:
        row = surfaces[name]
        for key in ("verdict", "tap_to_talk_semantics", "breaks_on_background_lock"):
            assert row.get(key), f"{name} missing {key!r}"


def test_mobile_browser_limitations_complete():
    data = _load(_COMPILE)
    limits = data["mobile_browser_limitations"]
    for key in (
        "autoplay_policy",
        "mic_policy",
        "ws_keepalive",
        "pwa_constraints",
        "consent_ux_small_viewport",
    ):
        assert limits.get(key), f"mobile_browser_limitations missing {key!r}"


def test_native_app_permissions_complete():
    data = _load(_COMPILE)
    perms = data["native_app_permissions"]
    ios = perms["ios"]
    assert ios.get("info_plist") and ios.get("tcc") and ios.get("background_modes")
    plist = json.dumps(ios["info_plist"])
    assert "NSMicrophoneUsageDescription" in plist
    assert "NSSpeechRecognitionUsageDescription" in plist
    android = perms["android"]
    assert android.get("manifest") and android.get("runtime_flow")
    assert "RECORD_AUDIO" in json.dumps(android["manifest"])
    assert "foreground_service_types" in android, (
        "android permissions must document (not ship) the FGS constraint"
    )


def test_battery_privacy_constraints_complete():
    data = _load(_COMPILE)
    bp = data["battery_privacy_constraints"]
    on_device = bp["on_device_stt_preferred"]
    assert "SFSpeechRecognizer" in on_device["ios"]
    assert "SpeechRecognizer" in on_device["android"]
    assert "authenticated" in bp["server_stt_fallback"].lower(), (
        "server STT fallback must be authenticated-channel only"
    )
    assert "deferred" in bp["cloud_transcription"].lower(), (
        "cloud transcription must remain deferred to the privacy review"
    )
    assert bp.get("no_audio_persistence"), "no-audio-persistence constraint missing"


def test_owner_observation_recorded():
    data = _load(_COMPILE)
    obs = data["owner_observation_2026_07_06"]
    for key in ("event", "reading", "gap", "implication_for_this_plan"):
        assert obs.get(key), f"owner observation missing {key!r}"
    assert "consent" in obs["event"].lower()
    assert "fail-closed" in obs["reading"].lower() or "fail closed" in obs["reading"].lower()


# ── adapter-into-chat invariants ──────────────────────────────────────────────


def test_adapter_output_is_chat_only():
    data = _load(_COMPILE)
    adapter = data["adapter_into_cockpit_chat"]
    seam = adapter["output_seam"]
    assert "/advisor/converse" in seam
    assert "source='voice'" in seam
    never = json.dumps(adapter["never_calls"])
    for forbidden in ("classify_intent", "intent_loop_submit", "governed_mutation"):
        assert forbidden in never, f"never_calls must name {forbidden!r}"
    assert "Clerk" in adapter["identity"], "identity must be the Clerk session principal"
    assert (
        "server-side" in adapter["identity"].lower() or "server side" in adapter["identity"].lower()
    )
    assert "VoiceConsentGrant" in adapter["consent"]
    assert "push_to_talk" in adapter["consent"], "consent must be per-mode"
    assert "device_registry_id" in adapter["consent"], "consent must be per-device via registry id"
    assert "voice-ws.ts" in adapter["mobile_browser_transport_reuse"], (
        "mobile browser must reuse the existing PCM16 WS protocol"
    )


# ── cross-check against the feasibility matrix ────────────────────────────────


def _matrix_target(matrix: dict, name: str) -> dict:
    return {row["target"]: row for row in matrix["targets"]}[name]


def test_verdicts_agree_with_matrix_summary():
    compile_data = _load(_COMPILE)
    matrix = _load(_MATRIX)
    vc = compile_data["verdict_consistency"]
    summary = matrix["summary_verdicts"]

    assert vc["mobile_app_push_to_talk"] == summary["mobile_app"]["push_to_talk"]
    assert vc["mobile_browser_push_to_talk"] == summary["mobile_browser"]["push_to_talk"]
    assert vc["mobile_browser_wake_word"] == summary["mobile_browser"]["wake_word"]
    assert vc["mobile_browser_ambient"] == summary["mobile_browser"]["ambient"]


def test_ambient_background_verdicts_match_matrix_sub_verdicts():
    """The load-both-and-cross-check gate: mobile ambient/background verdicts in
    the compile must equal the matrix's mobile_app sub_verdicts."""
    compile_data = _load(_COMPILE)
    matrix = _load(_MATRIX)

    sub = _matrix_target(matrix, "mobile_app")["ambient_always_on"]["sub_verdicts"]
    bg = compile_data["background_ambient_feasibility"]

    assert sub["ios_background"].startswith("NOT_FEASIBLE")
    assert bg["ios_background"]["verdict"] == "NOT_FEASIBLE", (
        "compile must repeat the matrix iOS-background NOT_FEASIBLE verdict"
    )
    assert (
        compile_data["verdict_consistency"]["mobile_app_ios_background_ambient"] == "NOT_FEASIBLE"
    )

    assert sub["android_background"].startswith("CONSTRAINED")
    assert bg["android_background"]["verdict"] == "CONSTRAINED", (
        "compile must repeat the matrix Android-FGS CONSTRAINED verdict"
    )
    assert (
        compile_data["verdict_consistency"]["mobile_app_android_background_ambient"]
        == "CONSTRAINED"
    )

    # Mobile-browser wake/ambient: NOT_FEASIBLE in both files.
    mb = _matrix_target(matrix, "mobile_browser")
    assert mb["wake_word"]["verdict"] == "NOT_FEASIBLE"
    assert mb["ambient_always_on"]["verdict"] == "NOT_FEASIBLE"
    assert bg["mobile_browser_wake_word"]["verdict"] == "NOT_FEASIBLE"
    assert bg["mobile_browser_ambient"]["verdict"] == "NOT_FEASIBLE"


def test_per_surface_ptt_verdicts_match_matrix():
    compile_data = _load(_COMPILE)
    matrix = _load(_MATRIX)
    surfaces = compile_data["push_to_talk_per_surface"]
    app_ptt = _matrix_target(matrix, "mobile_app")["push_to_talk"]["verdict"]
    browser_ptt = _matrix_target(matrix, "mobile_browser")["push_to_talk"]["verdict"]

    assert surfaces["native_ios"]["verdict"] == app_ptt
    assert surfaces["native_android"]["verdict"] == app_ptt
    assert surfaces["mobile_safari"]["verdict"] == browser_ptt
    assert surfaces["mobile_chrome"]["verdict"] == browser_ptt


def test_mobile_ambient_never_promised():
    """No PROVEN/LIKELY verdict anywhere in the background/ambient section."""
    data = _load(_COMPILE)
    blob = json.dumps(data["background_ambient_feasibility"]).upper()
    assert "PROVEN" not in blob and "LIKELY" not in blob, (
        "mobile ambient/background must never be promised — matrix says "
        "NOT_FEASIBLE (iOS background) / CONSTRAINED (Android FGS)"
    )
    for artifact in (_COMPILE, _DOC):
        text = artifact.read_text(encoding="utf-8").lower()
        assert "always-on listening is supported" not in text
        assert "background listening is supported" not in text


# ── tenant / device safety ────────────────────────────────────────────────────


def test_no_tenant_or_device_literals():
    for path in (_COMPILE, _DOC):
        text = path.read_text(encoding="utf-8").lower()
        for literal in _BANNED_LITERALS:
            assert literal not in text, (
                f"{path.name} carries banned literal {literal!r} — device/tenant "
                "bindings must go through registry references, never literals"
            )


def test_no_plaintext_secret_shapes():
    """No secret-looking values in the artifacts (compile-mode stop condition)."""
    for path in (_COMPILE, _DOC):
        text = path.read_text(encoding="utf-8")
        for marker in ("sk-", "ghp_", "gsk_", "AKIA", "-----BEGIN"):
            assert marker not in text, f"{path.name} carries secret-shaped value {marker!r}"


# ── compile-mode: no implementation shipped ───────────────────────────────────


def test_no_implementation_files_shipped_by_this_compile():
    """Compile mode: deliverables are one doc + one JSON + this test. None may
    live under a runtime dir, and the only code deliverable is this test."""
    for rel in _ALLOWED_FILES:
        assert (_ROOT / rel).exists(), f"expected compile deliverable missing: {rel}"

    runtime_dirs = ("adapters/", "transports/", "services/", "substrate/", "cockpit/src/")
    for rel in _ALLOWED_FILES:
        assert not any(rel.startswith(d) for d in runtime_dirs), (
            f"compile shipped a runtime file {rel} — implementation not allowed"
        )
    py_deliverables = [r for r in _ALLOWED_FILES if r.endswith(".py")]
    assert py_deliverables == ["tests/test_p4s31d_mobile_compile_artifacts.py"], (
        "the only code deliverable in compile mode is the validation test"
    )
