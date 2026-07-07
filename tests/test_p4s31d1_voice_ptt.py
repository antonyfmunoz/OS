"""P4S-31D-1 — Desktop browser push-to-talk voice adapter into Cockpit Chat.

Proves the packet's required behavior and the VoiceIntentContract invariants
(docs/VOICE_INTENT_CONTRACT.md):

1. The consent mutations (voice_consent_grant / voice_consent_revoke) are
   registered in the REAL MutationRegistry and are degraded-safe (low-risk,
   LOCAL_FILE) — consent stays governed AND revocable with the daemon down.
2. VoiceConsentStore semantics: grant → active; revoke → refused fail-closed;
   consent is PER-MODE (a push_to_talk grant never authorizes wake_word or
   always_on); non-push_to_talk modes are NOT grantable in this packet.
3. The consent WRITE routes through the governed runner (fake runner captures
   the exact mutation_name; a rejecting runner persists nothing).
4. VERBATIM + GATE HOLDS through the REAL /advisor/converse handler: a
   voice-shaped payload (source='voice', voice_turn_id) with intent-bearing
   text produces the canonical intent event, the loop record carries the
   transcript text VERBATIM, and the gate holds at AWAITING_APPROVAL with no
   proof. Classification is source-independent.
5. NO SEPARATE EXECUTION PATH (static, per contract §Non-bypass): the voice
   adapter/controller/WS client contain no intent-loop submit, no governed
   mutation call, no classify_intent call, no provider call — the ONLY exit is
   the chat seam (addVoiceTranscript → sendMessage(source='voice')), and the
   dispatched text is the assembled transcript unmodified.
6. The mic affordance goes through the consent-gated adapter (RightRail imports
   the PlatformVoiceAdapter, not the raw controller).
7. The voice_server lifecycle gap is closed by a managed unit that respects the
   CPU Gate Law.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

import pytest

from substrate.execution.intent.intent_spec import IntentLoopStage
from substrate.execution.intent.loop import IntentLoopStore
from substrate.organism.mutation_registry import MutationRegistry
from substrate.workstation.voice_consent import (
    GRANT_MUTATION_NAME,
    GRANTABLE_MODES,
    REVOKE_MUTATION_NAME,
    VoiceConsentRefused,
    VoiceConsentStore,
)
from substrate.workstation.voice_ingress_runtime import ActivationMode

_PRINCIPAL = "clerk:user_test_operator"
_DEVICE = "test_desktop_browser"
_PTT = ActivationMode.PUSH_TO_TALK.value

# Deterministically classifies as CommandIntent.INTENT_CAPTURE ("fix this").
_VOICE_INTENT_TRANSCRIPT = "Fix this flaky voice pipeline test in the cockpit"

_COCKPIT_API = Path(_WORKTREE) / "cockpit" / "src" / "renderer" / "api"
_ADAPTER_PATH = _COCKPIT_API / "platform-voice-adapter.ts"
_CONTROLLER_PATH = _COCKPIT_API / "voice-controller.ts"
_VOICE_WS_PATH = _COCKPIT_API / "voice-ws.ts"
_CHAT_STORE_PATH = Path(_WORKTREE) / "cockpit" / "src" / "renderer" / "stores" / "chatStore.ts"
_RIGHT_RAIL_PATH = Path(_WORKTREE) / "cockpit" / "src" / "renderer" / "components" / "RightRail.tsx"
_SYSTEMD_UNIT_PATH = Path(_WORKTREE) / "infra" / "systemd" / "umh-voice-server.service"


def _store(tmp_path) -> VoiceConsentStore:
    return VoiceConsentStore(store_path=str(tmp_path / "consent_grants.json"))


# ── 1. Consent mutations registered + degraded-safe ───────────────────────────


def test_consent_mutations_are_registered():
    reg = MutationRegistry()
    assert reg.is_registered(GRANT_MUTATION_NAME)
    assert reg.is_registered(REVOKE_MUTATION_NAME)


@pytest.mark.parametrize("name", [GRANT_MUTATION_NAME, REVOKE_MUTATION_NAME])
def test_consent_specs_are_degraded_safe_and_local(name):
    spec = MutationRegistry().lookup(name)
    assert spec is not None
    assert spec.risk_level == "low"
    assert spec.blast_radius.value == "local_file"
    assert spec.degraded_mode_allowed is True


# ── 2. Consent store semantics (fail-closed, per-mode) ────────────────────────


def test_no_grant_means_refusal_fail_closed(tmp_path):
    store = _store(tmp_path)
    assert store.active_grant(_PRINCIPAL, _DEVICE, _PTT) is None
    with pytest.raises(VoiceConsentRefused) as exc:
        store.require_active_grant(_PRINCIPAL, _DEVICE, _PTT)
    assert exc.value.code == "CONSENT_REQUIRED"


def test_grant_then_active_then_revoke_then_refused(tmp_path):
    store = _store(tmp_path)
    grant = store.grant(_PRINCIPAL, _DEVICE, _PTT)
    assert grant.active is True
    assert store.require_active_grant(_PRINCIPAL, _DEVICE, _PTT).grant_id == grant.grant_id

    assert store.revoke(_PRINCIPAL, _DEVICE, _PTT) is True
    with pytest.raises(VoiceConsentRefused):
        store.require_active_grant(_PRINCIPAL, _DEVICE, _PTT)


def test_grant_is_idempotent(tmp_path):
    store = _store(tmp_path)
    first = store.grant(_PRINCIPAL, _DEVICE, _PTT)
    second = store.grant(_PRINCIPAL, _DEVICE, _PTT)
    assert first.grant_id == second.grant_id


def test_consent_is_per_mode_never_cross_authorizes(tmp_path):
    """Contract hard constraint: a push_to_talk grant does NOT authorize
    wake_word or always_on."""
    store = _store(tmp_path)
    store.grant(_PRINCIPAL, _DEVICE, _PTT)
    for other_mode in ("wake_word", "always_on"):
        assert store.active_grant(_PRINCIPAL, _DEVICE, other_mode) is None
        with pytest.raises(VoiceConsentRefused):
            store.require_active_grant(_PRINCIPAL, _DEVICE, other_mode)


def test_consent_is_per_device_and_per_principal(tmp_path):
    store = _store(tmp_path)
    store.grant(_PRINCIPAL, _DEVICE, _PTT)
    assert store.active_grant(_PRINCIPAL, "other_device", _PTT) is None
    assert store.active_grant("clerk:user_other", _DEVICE, _PTT) is None


def test_only_push_to_talk_is_grantable_in_this_packet(tmp_path):
    """Ambient scope-creep guard: wake_word / always_on grants are refused
    typed until their packets (P4S-31D-3/6)."""
    assert GRANTABLE_MODES == frozenset({_PTT})
    store = _store(tmp_path)
    for mode in ("wake_word", "always_on", "clap"):
        with pytest.raises(VoiceConsentRefused) as exc:
            store.grant(_PRINCIPAL, _DEVICE, mode)
        assert exc.value.code == "MODE_NOT_GRANTABLE"


# ── 3. Consent write is governed (no ungoverned append) ───────────────────────


# The fake runner returns the REAL MutationResponse so these tests pin the
# actual router contract (field: `success`). #230 regression: a hand-rolled
# fake used a nonexistent `executed` attr, the routes checked the same wrong
# attr, and live governed grants reported as refusals while persisting.
from substrate.organism.mutation_router import MutationResponse  # noqa: E402


def _real_response(success: bool, rejected_reason: str = "") -> MutationResponse:
    return MutationResponse(success=success, rejected_reason=rejected_reason)


def test_grant_routes_through_governed_runner(tmp_path, monkeypatch):
    import substrate.workstation.voice_consent as vc_mod
    from transports.api.cockpit_voice_consent_routes import governed_consent_grant

    monkeypatch.setattr(vc_mod, "_DEFAULT_STORE_PATH", str(tmp_path / "consent_grants.json"))
    captured = {}

    def fake_runner(**kwargs):
        captured["mutation_name"] = kwargs["mutation_name"]
        kwargs["execute_fn"]()
        return _real_response(success=True)

    out = governed_consent_grant(_PRINCIPAL, _DEVICE, _PTT, mutation_runner=fake_runner)
    assert captured["mutation_name"] == GRANT_MUTATION_NAME
    assert out["granted"] is True and out["active"] is True
    assert out["grant"]["activation_mode"] == _PTT


def test_grant_success_field_matches_real_router_contract():
    """#230 regression pin: the routes must read the field the REAL
    MutationResponse defines (`success`), not an invented one. A successful
    response object must be interpreted as success."""
    fields = set(MutationResponse.__dataclass_fields__)
    assert "success" in fields
    assert "executed" not in fields  # the attr #230 wrongly checked

    src = Path(_WORKTREE, "transports", "api", "cockpit_voice_consent_routes.py").read_text(
        encoding="utf-8"
    )
    assert 'getattr(response, "success"' in src
    assert 'getattr(response, "executed"' not in src


def test_rejected_governed_grant_persists_nothing(tmp_path, monkeypatch):
    import substrate.workstation.voice_consent as vc_mod
    from transports.api.cockpit_voice_consent_routes import governed_consent_grant

    monkeypatch.setattr(vc_mod, "_DEFAULT_STORE_PATH", str(tmp_path / "consent_grants.json"))

    def rejecting_runner(**kwargs):
        # Governed gate rejects: execute_fn is NEVER called.
        return _real_response(success=False, rejected_reason="rejected by governance")

    out = governed_consent_grant(_PRINCIPAL, _DEVICE, _PTT, mutation_runner=rejecting_runner)
    assert out["granted"] is False
    assert out["error"] == "rejected by governance"
    store = VoiceConsentStore(store_path=str(tmp_path / "consent_grants.json"))
    assert store.active_grant(_PRINCIPAL, _DEVICE, _PTT) is None


def test_revoke_routes_through_governed_runner(tmp_path, monkeypatch):
    import substrate.workstation.voice_consent as vc_mod
    from transports.api.cockpit_voice_consent_routes import (
        governed_consent_grant,
        governed_consent_revoke,
    )

    monkeypatch.setattr(vc_mod, "_DEFAULT_STORE_PATH", str(tmp_path / "consent_grants.json"))
    names = []

    def fake_runner(**kwargs):
        names.append(kwargs["mutation_name"])
        kwargs["execute_fn"]()
        return _real_response(success=True)

    governed_consent_grant(_PRINCIPAL, _DEVICE, _PTT, mutation_runner=fake_runner)
    out = governed_consent_revoke(_PRINCIPAL, _DEVICE, _PTT, mutation_runner=fake_runner)
    assert names == [GRANT_MUTATION_NAME, REVOKE_MUTATION_NAME]
    assert out["revoked"] is True and out["active"] is False


def test_consent_read_is_fail_closed_on_error(monkeypatch):
    from transports.api import cockpit_voice_consent_routes as routes_mod

    class _Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("store unreadable")

    import substrate.workstation.voice_consent as vc_mod

    monkeypatch.setattr(vc_mod, "VoiceConsentStore", _Boom)
    out = routes_mod.read_consent_state(_PRINCIPAL, _DEVICE, _PTT)
    assert out["active"] is False and out["grant"] is None


# ── 4. Verbatim transcript + held gate through the REAL chat handler ──────────


def _isolate_loop_store(tmp_path, monkeypatch) -> str:
    import substrate.execution.intent.loop as loop_mod

    store_path = str(tmp_path / "loops.jsonl")
    monkeypatch.setattr(loop_mod, "_DEFAULT_STORE_PATH", store_path)
    return store_path


def _advisor_converse_endpoint():
    import transports.api.cockpit_chat_routes as chat_mod

    chat_mod.configure(
        get_organism_fn=lambda: None,
        push_chat_message_fn=lambda msg: None,
        require_operator_dep=lambda: "umh_operator",
    )
    for route in chat_mod.chat_router.routes:
        if getattr(route, "path", "") == "/advisor/converse":
            return route.endpoint
    raise AssertionError("/advisor/converse route not found")


def test_voice_payload_enters_rail_verbatim_and_gate_holds(tmp_path, monkeypatch):
    """The packet's core acceptance: a voice-shaped /advisor/converse payload
    (source='voice', voice_turn_id) with intent-bearing transcript text
    → canonical intent event, transcript VERBATIM in the loop record, gate
    HELD at AWAITING_APPROVAL with no proof."""
    store_path = _isolate_loop_store(tmp_path, monkeypatch)
    endpoint = _advisor_converse_endpoint()

    out = endpoint(
        {
            "content": _VOICE_INTENT_TRANSCRIPT,
            "source": "voice",
            "voice_turn_id": "vt-test-p4s31d1",
        }
    )
    assert out["intent"] == "intent_loop_submit"
    assert out["metadata"]["submitted"] is True
    assert out["metadata"]["stage"] == IntentLoopStage.AWAITING_APPROVAL.value

    # Server-truth store: gate held, no proof, transcript verbatim.
    rec = IntentLoopStore(store_path=store_path).get(out["metadata"]["loop_id"])
    assert rec is not None
    assert rec.stage == IntentLoopStage.AWAITING_APPROVAL.value
    assert rec.proof is None
    assert rec.spec["raw_text"] == _VOICE_INTENT_TRANSCRIPT


def test_classification_is_source_independent(tmp_path, monkeypatch):
    """Identical text classifies identically for voice and text payloads."""
    store_path = _isolate_loop_store(tmp_path, monkeypatch)
    endpoint = _advisor_converse_endpoint()

    voice_out = endpoint({"content": _VOICE_INTENT_TRANSCRIPT, "source": "voice"})
    text_out = endpoint({"content": _VOICE_INTENT_TRANSCRIPT, "source": "text"})
    assert voice_out["intent"] == text_out["intent"] == "intent_loop_submit"

    records = IntentLoopStore(store_path=store_path).load_all()
    raw_texts = {r.spec["raw_text"] for r in records}
    assert raw_texts == {_VOICE_INTENT_TRANSCRIPT}


# ── 5. No separate execution path (contract §Non-bypass, static) ──────────────

_FORBIDDEN_IN_VOICE_PATH = (
    "/intent-loop/submit",
    "governed_mutation",
    "classify_intent",
    "anthropic",
    "openai.",
    "generativeai",
)


@pytest.mark.parametrize(
    "path", [_ADAPTER_PATH, _CONTROLLER_PATH, _VOICE_WS_PATH], ids=lambda p: p.name
)
def test_voice_path_has_no_bypass_tokens(path):
    src = path.read_text(encoding="utf-8")
    for token in _FORBIDDEN_IN_VOICE_PATH:
        assert token not in src, (
            f"{path.name} must not contain '{token}' — the voice path's ONLY "
            "exit is the chat seam (sendMessage source='voice')"
        )


def test_voice_exit_is_the_chat_seam_verbatim():
    """The controller dispatches the assembled transcript UNMODIFIED into the
    chat store, and the chat store forwards the text unmodified into
    sendMessage(source='voice')."""
    controller = _CONTROLLER_PATH.read_text(encoding="utf-8")
    assert "addVoiceTranscript(text, turn.voiceTurnId)" in controller
    assert "const text = turn.assembledText" in controller

    chat_store = _CHAT_STORE_PATH.read_text(encoding="utf-8")
    assert "sendMessage(text, 'voice'" in chat_store


def test_adapter_delegates_capture_and_gates_on_consent():
    src = _ADAPTER_PATH.read_text(encoding="utf-8")
    # Capture only via the existing controller (no second audio path).
    assert "from './voice-controller'" in src
    # Fail-closed consent gate in front of capture.
    assert "getConsent('push_to_talk')" in src
    assert "ConsentRequiredError" in src
    assert "CONSENT_REQUIRED" in src


def test_mic_affordance_uses_consent_gated_adapter():
    src = _RIGHT_RAIL_PATH.read_text(encoding="utf-8")
    assert "platform-voice-adapter" in src
    assert "from '../api/voice-controller'" not in src, (
        "RightRail must reach capture ONLY through the consent-gated adapter"
    )


def test_consent_required_renders_inline_enable_control():
    """Lane A UX: CONSENT_REQUIRED must offer an inline grant path (explicit
    'Enable Push-to-Talk' control calling the governed grant route), never a
    dead-end or a blocking confirm dialog, and never an auto-grant."""
    rail = _RIGHT_RAIL_PATH.read_text(encoding="utf-8")
    adapter = _ADAPTER_PATH.read_text(encoding="utf-8")

    assert "Enable Push-to-Talk for this device" in rail
    assert "window.confirm" not in rail, "inline control replaces the blocking dialog"
    assert "grantPushToTalk" in rail and "grantPushToTalk" in adapter
    assert "revokeConsent" in rail, "revoke must stay reachable from the UI"

    # No auto-grant: the grant call happens only inside the explicit
    # user-initiated handler, never inside startCapture/getConsent.
    start_capture = adapter.split("async function startCapture")[1].split("\n}")[0]
    assert "requestConsent" not in start_capture and "grant" not in start_capture.replace(
        "VoiceConsentGrant", ""
    ), "startCapture must never grant consent implicitly"

    # Server-truth consent state: 'active' only after the governed route
    # confirms; the store flag alone can never fake it.
    grant_flow = adapter.split("async function grantPushToTalk")[1].split("\n}")[0]
    assert "requestConsent" in grant_flow and "out.active" in grant_flow


# ── 6. voice_server lifecycle unit (managed, CPU-law compliant) ────────────────


def test_voice_server_lifecycle_unit_exists_and_is_bounded():
    assert _SYSTEMD_UNIT_PATH.exists(), (
        "P4S-31D-1 must close the voice_server lifecycle gap with a managed unit"
    )
    unit = _SYSTEMD_UNIT_PATH.read_text(encoding="utf-8")
    assert "voice_server.py" in unit
    assert "Restart=on-failure" in unit
    # CPU Gate Law: the STT fallback must never saturate the host.
    assert "CPUQuota=" in unit
    assert "MemoryMax=" in unit
