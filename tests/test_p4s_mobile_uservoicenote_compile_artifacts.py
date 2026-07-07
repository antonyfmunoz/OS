"""P4S-MOBILE-VOICE-SURFACE-001 mobile UserVoiceNote rail compile — compile gate.

Validates the compile-only deliverables that DEEPEN the mobile voice plan for
the UserVoiceNote draft rail (record -> VoiceMessageDraft -> audio bubble +
transcript -> review -> explicit send):

  - data/umh/voice/mobile_uservoicenote_compile.json parses and declares
    compile_only with NO activation authorized,
  - every required section/key is present (per-surface rail, shipped-rail
    adaptation deltas, draft-lifecycle-on-interruptions, consent UX small
    viewport, audio upload, on-device-vs-server STT, adapter-into-chat,
    background/ambient, verdict_consistency),
  - the verdicts AGREE with data/umh/voice/platform_voice_feasibility_matrix.json
    (BOTH files loaded and cross-checked — this compile deepens the matrix,
    never contradicts it),
  - the codec break (audio/webm -> audio/mp4 fallback) and background/lock
    graceful-finalize are recorded (the two concerns this packet must deepen),
  - NO activation language and NO mobile ambient/background promise,
  - NO first-tenant or device-hostname literal,
  - NO implementation files shipped by this compile.

Mirrors tests/test_p4s31d_mobile_compile_artifacts.py: mechanical, fail-closed,
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
_COMPILE = _ROOT / "data/umh/voice/mobile_uservoicenote_compile.json"
_MATRIX = _ROOT / "data/umh/voice/platform_voice_feasibility_matrix.json"
_DOC = _ROOT / "docs/MOBILE_USERVOICENOTE_COMPILE.md"

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
    "extends",
    "desktop_reference_impl",
    "central_thesis",
    "owner_observation_2026_07_07",
    "uservoicenote_rail_per_surface",
    "shipped_rail_adaptation_deltas",
    "draft_lifecycle_on_mobile_interruptions",
    "consent_ux_small_viewport",
    "audio_upload_over_mobile_radio",
    "on_device_vs_server_stt",
    "adapter_into_cockpit_chat",
    "background_ambient_feasibility",
    "verdict_consistency",
}

# Files this compile is allowed to ship. Anything voice-*implementation*
# (adapter/route/cockpit/service code) shipping under this compile is a stop
# condition.
_ALLOWED_FILES = {
    "docs/MOBILE_USERVOICENOTE_COMPILE.md",
    "data/umh/voice/mobile_uservoicenote_compile.json",
    "tests/test_p4s_mobile_uservoicenote_compile_artifacts.py",
}


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── parse + compile mode ──────────────────────────────────────────────────────


def test_artifacts_exist_and_parse():
    assert _COMPILE.exists(), "mobile_uservoicenote_compile.json missing"
    assert _MATRIX.exists(), "feasibility matrix missing (cross-check source)"
    assert _DOC.exists(), "MOBILE_USERVOICENOTE_COMPILE.md missing"
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


# ── deepen (not restate) the merged artifact ──────────────────────────────────


def test_compile_deepens_merged_artifact_not_restates():
    """This packet must EXTEND the already-merged mobile compile, not duplicate
    it — it references the merged artifact and the shipped desktop rail."""
    data = _load(_COMPILE)
    extends = data["extends"]
    assert extends["mobile_voice_compile"] == "data/umh/voice/mobile_voice_compile.json"
    assert "not a restatement" in extends["statement"].lower() or (
        "deepen" in extends["statement"].lower()
    ), "must declare it deepens (not restates) the merged artifact"
    ref = data["desktop_reference_impl"]
    assert "voiceMessageStore.ts" in ref["store"]
    assert "voice-controller.ts" in ref["controller"]


# ── required keys / sections ──────────────────────────────────────────────────


def test_required_top_level_keys_present():
    data = _load(_COMPILE)
    missing = _REQUIRED_TOP_KEYS - set(data)
    assert not missing, f"mobile_uservoicenote_compile.json missing keys: {missing}"


def test_rail_covers_all_four_surfaces():
    data = _load(_COMPILE)
    surfaces = data["uservoicenote_rail_per_surface"]
    missing = _REQUIRED_SURFACES - set(surfaces)
    assert not missing, f"uservoicenote_rail_per_surface missing surfaces: {missing}"
    for name in _REQUIRED_SURFACES:
        row = surfaces[name]
        for key in ("verdict", "draft_model_fit", "breaks_on_background_lock"):
            assert row.get(key), f"{name} missing {key!r}"


def test_central_thesis_draft_suits_mobile_without_upgrading_verdict():
    data = _load(_COMPILE)
    thesis = data["central_thesis"]
    # The draft/review model is the claim — tap-to-talk-then-review beats live.
    assert "draft" in thesis["claim"].lower() and "mobile" in thesis["claim"].lower()
    # ...but it must NOT upgrade any matrix verdict.
    assert thesis.get("does_not_upgrade_verdict"), (
        "thesis must state it does not promote any matrix verdict"
    )
    dnu = thesis["does_not_upgrade_verdict"].lower()
    assert "constrained" in dnu and "not_feasible" in dnu


def test_codec_break_recorded_webm_to_mp4():
    """The MediaRecorder codec difference (iOS has no webm/opus -> audio/mp4)
    is the central mobile-browser break this packet must deepen."""
    data = _load(_COMPILE)
    safari = data["uservoicenote_rail_per_surface"]["mobile_safari"]
    codec = safari.get("codec_break", "")
    assert codec, "mobile_safari must record the codec_break"
    assert "audio/mp4" in codec, "codec break must name the iOS audio/mp4 fallback"
    assert "audio/webm" in codec, "codec break must reference the webm assumption it breaks"
    assert "_pickRecorderMime" in codec, "codec break must reference the shipped mime picker"
    # Chrome-on-Android keeps webm; the delta is truthful about the split.
    chrome = data["uservoicenote_rail_per_surface"]["mobile_chrome"]
    assert "audio/webm" in chrome.get("codec", ""), "mobile_chrome must note webm support"

    deltas = data["shipped_rail_adaptation_deltas"]
    assert "audio/mp4" in deltas["codec_candidate_list"]
    assert "audio/mp4" in deltas["content_type_normalization"]


def test_background_lock_finalizes_to_recoverable_draft():
    """Background/lock must GRACEFULLY finalize to a recoverable draft — never a
    lost turn, never an auto-send."""
    data = _load(_COMPILE)
    for name in _REQUIRED_SURFACES:
        row = data["uservoicenote_rail_per_surface"][name]
        blob = row["breaks_on_background_lock"].lower()
        assert "draft" in blob or "review" in blob, (
            f"{name} background/lock must finalize to a review draft"
        )
        assert "auto-send" in blob or "never" in blob, (
            f"{name} background/lock must never auto-send"
        )
    lifecycle = data["draft_lifecycle_on_mobile_interruptions"]
    for key in (
        "background_or_lock_mid_record",
        "no_speech",
        "stt_failed_over_radio",
        "ws_dropped_by_proxy",
        "upload_failed_on_send",
        "delete",
    ):
        assert lifecycle.get(key), f"draft lifecycle missing {key!r}"
    # No failure path discards audio except explicit delete.
    assert "preserved" in lifecycle["stt_failed_over_radio"].lower() or (
        "kept" in lifecycle["stt_failed_over_radio"].lower()
    )


def test_shipped_rail_adaptation_deltas_complete():
    data = _load(_COMPILE)
    deltas = data["shipped_rail_adaptation_deltas"]
    for key in (
        "codec_candidate_list",
        "content_type_normalization",
        "finalize_on_lifecycle_event",
        "no_auto_reacquire",
        "ws_reconnect_lazy",
        "review_ui_viewport",
    ):
        assert deltas.get(key), f"shipped_rail_adaptation_deltas missing {key!r}"
    # Lifecycle-finalize is additive to the existing state machine (no new state).
    assert "no new state" in deltas["finalize_on_lifecycle_event"].lower()


def test_consent_ux_small_viewport_recorded():
    data = _load(_COMPILE)
    obs = data["owner_observation_2026_07_07"]
    for key in ("event", "reading", "gap", "implication_for_this_rail"):
        assert obs.get(key), f"owner observation missing {key!r}"
    assert "consent" in obs["event"].lower()
    assert "fail-closed" in obs["reading"].lower() or "fail closed" in obs["reading"].lower()
    consent = data["consent_ux_small_viewport"]
    assert consent.get("inline_enable_on_refusal"), "inline enable-on-refusal missing"
    assert consent.get("grant_does_not_prove_surface"), (
        "must state that granting consent does not promote the surface verdict"
    )


def test_on_device_vs_server_stt_complete():
    data = _load(_COMPILE)
    stt = data["on_device_vs_server_stt"]
    assert "SFSpeechRecognizer" in stt["native_ios"]
    assert "SpeechRecognizer" in stt["native_android"]
    assert "authenticated" in stt["mobile_browser"].lower(), (
        "mobile browser STT must be authenticated-channel only"
    )
    assert "no on-device" in stt["mobile_browser"].lower() or (
        "no on device" in stt["mobile_browser"].lower()
    ), "mobile browser must record it has no on-device STT"
    assert "deferred" in stt["cloud_transcription"].lower()


def test_audio_upload_over_mobile_radio_complete():
    data = _load(_COMPILE)
    up = data["audio_upload_over_mobile_radio"]
    assert "/chat/upload" in up["seam"], "must reuse the existing /chat/upload seam"
    # Upload only on explicit send, never chunked-during-capture.
    timing = up["size_and_radio"].lower()
    assert "only on explicit send" in timing or "only on send" in timing
    assert up.get("no_persistence_beyond_seam"), "no-persistence constraint missing"


# ── adapter-into-chat invariants ──────────────────────────────────────────────


def test_adapter_output_is_chat_only():
    data = _load(_COMPILE)
    adapter = data["adapter_into_cockpit_chat"]
    seam = adapter["output_seam"]
    assert "/advisor/converse" in seam
    assert "source='voice'" in seam
    assert "sendDraft" in seam, "output seam must be the explicit-send path (sendDraft)"
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
    # Send is the ONLY ingress — partials never committed, delete leaves no trace.
    ingress = adapter["send_is_the_only_ingress"].lower()
    assert "explicit operator send" in ingress
    assert "never" in ingress


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


def test_per_surface_verdicts_match_matrix():
    compile_data = _load(_COMPILE)
    matrix = _load(_MATRIX)
    surfaces = compile_data["uservoicenote_rail_per_surface"]
    app_ptt = _matrix_target(matrix, "mobile_app")["push_to_talk"]["verdict"]
    browser_ptt = _matrix_target(matrix, "mobile_browser")["push_to_talk"]["verdict"]

    assert surfaces["native_ios"]["verdict"] == app_ptt
    assert surfaces["native_android"]["verdict"] == app_ptt
    assert surfaces["mobile_safari"]["verdict"] == browser_ptt
    assert surfaces["mobile_chrome"]["verdict"] == browser_ptt


def test_ambient_background_verdicts_match_matrix_sub_verdicts():
    """Load-both-and-cross-check: mobile ambient/background verdicts in the
    compile must equal the matrix's mobile_app sub_verdicts and mobile_browser
    wake/ambient verdicts."""
    compile_data = _load(_COMPILE)
    matrix = _load(_MATRIX)

    sub = _matrix_target(matrix, "mobile_app")["ambient_always_on"]["sub_verdicts"]
    bg = compile_data["background_ambient_feasibility"]

    assert sub["ios_background"].startswith("NOT_FEASIBLE")
    assert bg["ios_background"]["verdict"] == "NOT_FEASIBLE"
    assert (
        compile_data["verdict_consistency"]["mobile_app_ios_background_ambient"] == "NOT_FEASIBLE"
    )

    assert sub["android_background"].startswith("CONSTRAINED")
    assert bg["android_background"]["verdict"] == "CONSTRAINED"
    assert (
        compile_data["verdict_consistency"]["mobile_app_android_background_ambient"]
        == "CONSTRAINED"
    )

    mb = _matrix_target(matrix, "mobile_browser")
    assert mb["wake_word"]["verdict"] == "NOT_FEASIBLE"
    assert mb["ambient_always_on"]["verdict"] == "NOT_FEASIBLE"
    assert bg["mobile_browser_wake_word"]["verdict"] == "NOT_FEASIBLE"
    assert bg["mobile_browser_ambient"]["verdict"] == "NOT_FEASIBLE"


def test_agrees_with_merged_mobile_compile():
    """The verdict_consistency block must equal the merged mobile_voice_compile
    verdicts too — this deepens that artifact, it never diverges from it."""
    compile_data = _load(_COMPILE)
    merged_path = _ROOT / "data/umh/voice/mobile_voice_compile.json"
    assert merged_path.exists(), "merged mobile_voice_compile.json missing"
    merged = _load(merged_path)
    a = compile_data["verdict_consistency"]
    b = merged["verdict_consistency"]
    for key in (
        "mobile_app_push_to_talk",
        "mobile_browser_push_to_talk",
        "mobile_browser_wake_word",
        "mobile_browser_ambient",
        "mobile_app_ios_background_ambient",
        "mobile_app_android_background_ambient",
    ):
        assert a[key] == b[key], (
            f"verdict {key} diverges from the merged mobile compile: {a[key]} != {b[key]}"
        )


def test_mobile_ambient_never_promised():
    """No PROVEN/LIKELY verdict anywhere in the background/ambient section."""
    data = _load(_COMPILE)
    blob = json.dumps(data["background_ambient_feasibility"]).upper()
    assert "PROVEN" not in blob and "LIKELY" not in blob, (
        "mobile ambient/background must never be promised"
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
    assert py_deliverables == ["tests/test_p4s_mobile_uservoicenote_compile_artifacts.py"], (
        "the only code deliverable in compile mode is the validation test"
    )
