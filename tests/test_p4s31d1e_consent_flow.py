"""P4S-31D1-E — single-gesture mobile-Safari consent flow.

Fixes the DOUBLE-CONSENT UX: on mobile Safari the user tapped the mic, got the
browser mic-permission prompt, and was THEN forced to tap a separate
"Enable Push-to-Talk" before recording — two gestures for one intent.

Correct flow (one user-initiated flow): mic tap ONCE → browser mic-permission
prompt (if needed) → on browser-permission success, AUTOMATICALLY request the
UMH push_to_talk grant IN THE SAME handler → record. Only if the SERVER grant
fails is the explicit "Enable Push-to-Talk" retry surfaced.

These checks pin:
  1. Single-gesture: startCapture auto-requests the grant right after the browser
     mic permission succeeds (no intervening user-action gate between them).
  2. Failure fallback: a failed SERVER grant takes the explicit enable-affordance
     path (consentState 'required' + ConsentRequiredError), NOT the happy path.
  3. Server-side hard holds (real import): GRANTABLE_MODES == {push_to_talk};
     the store refuses wake_word / always_on fail-closed.
  4. No client-side fake consent: the frontend never stamps a grant id without a
     real server round-trip (the grant is a fetch, not a local constant).
  5. Recording a note triggers NO approval / held-gate UI (input consent, not an
     execution approval).
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

from substrate.workstation.voice_consent import (
    GRANTABLE_MODES,
    VoiceConsentRefused,
    VoiceConsentStore,
)
from substrate.workstation.voice_ingress_runtime import ActivationMode

_COCKPIT = Path(_WORKTREE) / "cockpit" / "src" / "renderer"
_ADAPTER_PATH = _COCKPIT / "api" / "platform-voice-adapter.ts"
_VOICE_WS_PATH = _COCKPIT / "api" / "voice-ws.ts"
_CONTROLLER_PATH = _COCKPIT / "api" / "voice-controller.ts"
_RIGHT_RAIL_PATH = _COCKPIT / "components" / "RightRail.tsx"

_PRINCIPAL = "clerk:user_test_operator"
_DEVICE = "test_desktop_browser"
_PTT = ActivationMode.PUSH_TO_TALK.value


def _adapter() -> str:
    return _ADAPTER_PATH.read_text(encoding="utf-8")


def _strip_comments_ts(src: str) -> str:
    """Drop // line and /* */ block comments so identifier assertions test real
    code, not documentation mentioning the identifier."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)
    return src


def _start_capture_body() -> str:
    """The code (comments stripped) of the async startCapture function only."""
    src = _strip_comments_ts(_adapter())
    after = src.split("async function startCapture", 1)[1]
    # Balance braces from the first '{' to isolate the function body.
    start = after.index("{")
    depth = 0
    for i in range(start, len(after)):
        if after[i] == "{":
            depth += 1
        elif after[i] == "}":
            depth -= 1
            if depth == 0:
                return after[start : i + 1]
    return after[start:]


def _store(tmp_path) -> VoiceConsentStore:
    return VoiceConsentStore(store_path=str(tmp_path / "consent_grants.json"))


# ── 1. Single-gesture: browser permission success → auto grant, same handler ──


def test_single_gesture_no_second_manual_click():
    """After the browser mic permission resolves, startCapture requests the
    push_to_talk grant AUTOMATICALLY in the same handler — no intervening
    user-action gate (no throw between them, no separate enable tap on the
    happy path)."""
    body = _start_capture_body()

    # The browser permission probe and the auto server grant both live in
    # startCapture, and the grant is reached WITHOUT a throw between them.
    assert "ensureBrowserMicPermission" in body, (
        "startCapture must prompt the browser mic permission up front"
    )
    assert "grantPushToTalk()" in body, (
        "startCapture must auto-request the server grant in the same handler"
    )

    perm_idx = body.index("ensureBrowserMicPermission")
    grant_idx = body.index("grantPushToTalk()")
    assert perm_idx < grant_idx, (
        "the auto grant must come AFTER the browser mic permission succeeds"
    )

    # No intervening user-action gate: between a SUCCESSFUL browser permission
    # and the auto grant there is no ConsentRequiredError throw and no separate
    # button handler. (The permission-denied branch throws BEFORE grantPushToTalk;
    # the only ConsentRequiredError throw is AFTER the grant fails.)
    between = body[perm_idx:grant_idx]
    assert "throw new ConsentRequiredError" not in between, (
        "no consent-required dead-end between browser permission success and the "
        "auto grant — that would force the old second tap"
    )
    assert "handleEnablePushToTalk" not in between


def test_browser_permission_probe_is_a_real_getusermedia():
    """ensureBrowserMicPermission is the FIRST layer — a real getUserMedia
    prompt on the user gesture — not a fake/local success."""
    ws = _strip_comments_ts(_VOICE_WS_PATH.read_text(encoding="utf-8"))
    assert "export async function ensureBrowserMicPermission" in ws
    probe = ws.split("ensureBrowserMicPermission", 1)[1]
    assert "navigator.mediaDevices" in probe and "getUserMedia" in probe, (
        "the browser permission layer must be a real getUserMedia call"
    )


# ── 2. Failure fallback: server grant failure → explicit enable retry ─────────


def test_server_grant_failure_takes_explicit_enable_path():
    """Only a FAILED server grant surfaces the explicit enable affordance:
    startCapture throws ConsentRequiredError (→ RightRail keeps the inline
    'Enable Push-to-Talk' retry) after grantPushToTalk returns not-active."""
    body = _start_capture_body()

    # The ConsentRequiredError throw is gated on the grant NOT being active.
    assert "grantPushToTalk()" in body
    grant_idx = body.index("grantPushToTalk()")
    tail = body[grant_idx:]
    assert "!granted.active" in tail, (
        "the failure branch must key off the server grant result, not a local flag"
    )
    assert "throw new ConsentRequiredError" in tail, (
        "a failed server grant must throw ConsentRequiredError so the UI shows the "
        "explicit enable-retry affordance"
    )

    # grantPushToTalk sets consentState 'required' on failure — that drives the
    # RightRail inline enable control.
    adapter = _strip_comments_ts(_adapter())
    grant_flow = adapter.split("async function grantPushToTalk", 1)[1].split("\n}", 1)[0]
    assert "setConsentState('required')" in grant_flow

    rail = _RIGHT_RAIL_PATH.read_text(encoding="utf-8")
    assert "consentState === 'required'" in rail
    assert "Enable Push-to-Talk for this device" in rail
    assert "handleEnablePushToTalk" in rail


def test_rightrail_catches_consent_required_for_retry():
    """RightRail's mic handler catches ConsentRequiredError and defers to the
    inline enable control (no crash, no blocking dialog)."""
    rail = _RIGHT_RAIL_PATH.read_text(encoding="utf-8")
    assert "ConsentRequiredError" in rail
    assert "window.confirm" not in rail


# ── 3. Server-side hard holds (REAL import, fail-closed) ──────────────────────


def test_grantable_modes_is_push_to_talk_only():
    assert GRANTABLE_MODES == frozenset({_PTT})


def test_store_refuses_wake_word_and_always_on(tmp_path):
    """Ambient scope-creep guard stays: the store refuses non-push_to_talk modes
    typed, and never cross-authorizes them from a push_to_talk grant."""
    store = _store(tmp_path)
    for mode in ("wake_word", "always_on"):
        with pytest.raises(VoiceConsentRefused) as exc:
            store.grant(_PRINCIPAL, _DEVICE, mode)
        assert exc.value.code == "MODE_NOT_GRANTABLE"

    store.grant(_PRINCIPAL, _DEVICE, _PTT)
    for mode in ("wake_word", "always_on"):
        assert store.active_grant(_PRINCIPAL, _DEVICE, mode) is None
        with pytest.raises(VoiceConsentRefused):
            store.require_active_grant(_PRINCIPAL, _DEVICE, mode)


def test_grant_is_revocable(tmp_path):
    store = _store(tmp_path)
    store.grant(_PRINCIPAL, _DEVICE, _PTT)
    assert store.revoke(_PRINCIPAL, _DEVICE, _PTT) is True
    with pytest.raises(VoiceConsentRefused):
        store.require_active_grant(_PRINCIPAL, _DEVICE, _PTT)


# ── 4. No client-side fake consent (grant id only from a server round-trip) ───


def test_grant_id_only_from_server_round_trip():
    """The frontend never stamps a consent grant id without a real server
    response: setActiveConsentGrantId flows from _rememberGrantId, which reads
    grant.grant_id off a VoiceConsentState returned by fetchApi — never a local
    constant, never a fabricated vcg- literal."""
    adapter = _strip_comments_ts(_adapter())

    # The grant id is remembered only from a server-shaped consent object.
    remember = adapter.split("function _rememberGrantId", 1)[1].split("\n}", 1)[0]
    assert "grant.grant_id" in remember and "setActiveConsentGrantId" in remember

    # Every grant/consent read is a real fetchApi round-trip.
    assert "fetchApi<VoiceConsentState>('/voice/consent/grant'" in adapter
    assert "requestConsent" in adapter and "await requestConsent" in adapter

    # No fabricated grant id anywhere in the consent adapter (a vcg- literal
    # assigned client-side would be a fake grant).
    assert not re.search(r"['\"]vcg-[0-9a-f]", adapter), (
        "no hardcoded vcg- grant id — grant ids come only from the server"
    )
    # grantPushToTalk flips to 'active' ONLY on the server's out.active.
    grant_flow = adapter.split("async function grantPushToTalk", 1)[1].split("\n}", 1)[0]
    assert "out.active" in grant_flow and "setConsentState('active')" in grant_flow


# ── 5. Recording a note triggers no approval / held-gate UI ───────────────────


def test_recording_triggers_no_approval_or_held_gate():
    """Voice INPUT consent is once-per-device; recording a note must NOT open any
    execution-approval / held-gate UI. The controller finalizes to a reviewable
    draft and never calls an approval/gate surface."""
    controller = _strip_comments_ts(_CONTROLLER_PATH.read_text(encoding="utf-8"))
    adapter = _strip_comments_ts(_adapter())

    forbidden = (
        "AWAITING_APPROVAL",
        "requireApproval",
        "approveGate",
        "heldGate",
        "held_gate",
        "/intent-loop/submit",
        "governed_mutation",
    )
    for token in forbidden:
        assert token not in controller, (
            f"recording path must not touch execution-approval surface '{token}'"
        )
        assert token not in adapter, (
            f"consent adapter must not touch execution-approval surface '{token}'"
        )

    # The consent adapter's ONLY grant is the INPUT consent (push_to_talk),
    # never an execution/action approval.
    assert "activationMode: 'push_to_talk'" in adapter


def test_startcapture_gives_immediate_feedback_before_first_await():
    """P4S-31D1-E first-click fix: startCapture must flip micState OUT of 'idle'
    SYNCHRONOUSLY, before its first `await`. Otherwise the whole async chain
    (getConsent → browser permission → grant → WS connect) runs while the button
    still reads 'idle' — it looks dead on first click, and a second click
    re-enters startCapture concurrently (the `micState === 'idle'` guard is still
    true). Setting a non-idle state up front gives instant feedback AND makes the
    guard block re-entry."""
    src = _adapter()
    # Isolate the startCapture body up to its FIRST await.
    body = src.split("async function startCapture")[1]
    before_first_await = body.split("await ", 1)[0]
    assert (
        "setMicState('requesting_permission')" in before_first_await
        or "setMicState('connecting_voice_ws')" in before_first_await
    ), (
        "startCapture must set a non-idle micState before its first await "
        "(instant first-click feedback + concurrent-reentry guard)"
    )


def test_mic_toggle_guard_blocks_reentry():
    """The click handler only enters startCapture when micState is 'idle', so the
    synchronous non-idle flip above prevents a concurrent second-click re-entry."""
    rr = (_COCKPIT / "components" / "RightRail.tsx").read_text(encoding="utf-8")
    assert "micState === 'idle'" in rr, (
        "handleMicToggle must guard startCapture on micState === 'idle'"
    )
