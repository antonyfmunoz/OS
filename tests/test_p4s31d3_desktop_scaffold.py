"""P4S-31D-3 SCAFFOLD — desktop app (Electron) voice adapter shell.

Static contract checks for the flag-disabled scaffold
(cockpit/src/main/desktop-voice-adapter.ts + docs/DESKTOP_APP_VOICE_SCAFFOLD.md).

Pins, per docs/VOICE_INTENT_CONTRACT.md §Non-bypass and the Lane-D packet:

1. FLAG OFF BY DEFAULT — DESKTOP_VOICE_ENABLED is a hard `false` constant with
   no env/config/IPC/client override anywhere in the module.
2. NO BYPASS TOKENS — the adapter contains no intent-loop submit route, no
   governed-mutation call, no classifier call, no provider call.
3. EVERY METHOD REFUSES — all five PlatformVoiceAdapter methods exist and each
   returns the typed DESKTOP_VOICE_DISABLED refusal.
4. NO WAKE / ALWAYS-ON / CAPTURE IMPLEMENTATION — no media APIs, no wake
   runtimes, no IPC registration, and index.ts does not import the module
   (zero activation path).
5. Substrate consent gate untouched: GRANTABLE_MODES is still push_to_talk
   only (wake_word/always_on stay non-grantable until their packets).
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

_MAIN_DIR = Path(_WORKTREE) / "cockpit" / "src" / "main"
_ADAPTER_PATH = _MAIN_DIR / "desktop-voice-adapter.ts"
_INDEX_PATH = _MAIN_DIR / "index.ts"
_DOC_PATH = Path(_WORKTREE) / "docs" / "DESKTOP_APP_VOICE_SCAFFOLD.md"

_ADAPTER_METHODS = (
    "requestConsent",
    "openSession",
    "startCapture",
    "stopCapture",
    "closeSession",
)


def _adapter_src() -> str:
    assert _ADAPTER_PATH.exists(), "desktop-voice-adapter.ts scaffold must exist"
    return _ADAPTER_PATH.read_text(encoding="utf-8")


# ── 1. Flag defaults OFF and cannot be enabled from client input ───────────────


def test_flag_is_hard_false_constant():
    src = _adapter_src()
    assert re.search(r"export\s+const\s+DESKTOP_VOICE_ENABLED\s*:\s*boolean\s*=\s*false", src), (
        "DESKTOP_VOICE_ENABLED must be a hard `false` build-time constant"
    )


def test_flag_has_no_env_config_or_ipc_override():
    src = _adapter_src()
    for token in ("process.env", "ipcMain", "ipcRenderer", "readFile", "require("):
        assert token not in src, (
            f"scaffold must not contain '{token}' — the flag is not enableable "
            "from env, config, IPC, or any client input"
        )


# ── 2. No bypass tokens (contract §Non-bypass, static) ────────────────────────

_FORBIDDEN_IN_VOICE_PATH = (
    "/intent-loop/submit",
    "governed_mutation",
    "classify_intent",
    "anthropic",
    "openai.",
    "generativeai",
)


@pytest.mark.parametrize("token", _FORBIDDEN_IN_VOICE_PATH)
def test_adapter_has_no_bypass_tokens(token):
    assert token not in _adapter_src(), (
        f"desktop-voice-adapter.ts must not contain '{token}' — the voice "
        "path's ONLY exit is the chat seam (sendMessage source='voice')"
    )


def test_adapter_states_chat_only_output_contract():
    src = _adapter_src()
    assert "sendMessage" in src and "'voice'" in src, (
        "the scaffold must state (in code comments) that output is ONLY "
        "chat sendMessage(source='voice')"
    )
    assert "/advisor/converse" in src


# ── 3. Every adapter method refuses while disabled ────────────────────────────


def test_adapter_exposes_full_platform_voice_adapter_surface():
    src = _adapter_src()
    for method in _ADAPTER_METHODS:
        assert re.search(rf"export\s+(async\s+)?function\s+{method}\b", src), (
            f"scaffold must implement the PlatformVoiceAdapter method '{method}'"
        )
        assert re.search(rf"\b{method},", src), (
            f"'{method}' must be exported on the desktopAppVoiceAdapter object"
        )


def test_every_method_returns_typed_disabled_refusal():
    src = _adapter_src()
    assert "DESKTOP_VOICE_DISABLED" in src
    assert "disabledRefusal" in src
    for method in _ADAPTER_METHODS:
        body = _method_body(src, method)
        assert "disabledRefusal(" in body, (
            f"'{method}' must return the typed disabled refusal while the "
            "flag is off — no other behavior exists in the scaffold"
        )


def _method_body(src: str, method: str) -> str:
    match = re.search(rf"export\s+(?:async\s+)?function\s+{method}\b.*?\n}}", src, re.DOTALL)
    assert match is not None, f"could not locate body of '{method}'"
    return match.group(0)


# ── 4. No wake-word / always-on / capture implementation, no activation path ──


def test_no_capture_or_wake_implementation_exists():
    src = _adapter_src().lower()
    forbidden_impl = (
        "getusermedia",
        "mediadevices",
        "audiocontext",
        "mediarecorder",
        "porcupine_native",  # runtime ids may be named in prose; instantiation may not
        "new porcupine",
        "openwakeword(",
        "onwake(",
        "websocket(",
        "spawn(",
        "child_process",
    )
    for token in forbidden_impl:
        assert token not in src, f"scaffold must contain no capture/wake implementation ('{token}')"


def test_index_ts_does_not_wire_the_scaffold():
    """Zero activation path: the Electron entrypoint must not import or
    activate the scaffold module."""
    index_src = _INDEX_PATH.read_text(encoding="utf-8")
    assert "desktop-voice-adapter" not in index_src
    assert "DESKTOP_VOICE_ENABLED" not in index_src


def test_substrate_consent_gate_still_push_to_talk_only():
    """Wake-word/always-on stay non-grantable until their own packets
    (P4S-31D-3 implementation / P4S-31D-6)."""
    from substrate.workstation.voice_consent import GRANTABLE_MODES

    assert GRANTABLE_MODES == frozenset({"push_to_talk"})


# ── 5. Permission-model doc exists and carries the binding statements ─────────


def test_scaffold_doc_exists_with_contract_and_proof_plan():
    assert _DOC_PATH.exists(), "docs/DESKTOP_APP_VOICE_SCAFFOLD.md must exist"
    doc = _DOC_PATH.read_text(encoding="utf-8")
    # Chat-only output contract stated in the doc.
    assert "sendMessage" in doc and "source='voice'" in doc
    assert "/advisor/converse" in doc
    # Two-layer permission model.
    assert "VoiceConsentGrant" in doc
    assert "NSMicrophoneUsageDescription" in doc
    # push_to_talk first, wake_word later.
    assert "push_to_talk" in doc and "wake_word" in doc
    # Proof plan present.
    assert "Class-A" in doc
    assert "AWAITING_APPROVAL" in doc
    # Flag discipline documented.
    assert "DESKTOP_VOICE_ENABLED" in doc
