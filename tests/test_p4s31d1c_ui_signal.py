"""P4S-31D1-C — voice-note UI capture-signal checks (live meter + precise failures).

Static / shape checks that pin the capture-signal contract
(data/umh/voice/voice_capture_signal_contract.json) against the shipped
renderer + controller + WS client code. The doctrine: capture must be VISIBLE
(a live client-RMS meter) and failure must be LEGIBLE (every server + client
error code maps to a DISTINCT human string — none collapses to the bare
"No speech detected" that hid the original suspended-capture bug).

These assertions are source-level (like test_p4s31d1b_voice_message.py):
they guard invariants a runtime test in this repo cannot reach (no browser, no
MediaRecorder, no WebAudio), and they fail closed when a future edit regresses
the meter, the taxonomy, the send-gate, or the no-premature-paste rule.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

import pytest

_ROOT = Path(_WORKTREE)
_RENDERER = _ROOT / "cockpit" / "src" / "renderer"
_API = _RENDERER / "api"
_STORES = _RENDERER / "stores"

_WS_PATH = _API / "voice-ws.ts"
_CONTROLLER_PATH = _API / "voice-controller.ts"
_STORE_PATH = _STORES / "voiceMessageStore.ts"
_RIGHT_RAIL_PATH = _RENDERER / "components" / "RightRail.tsx"

_CONTRACT_PATH = _ROOT / "data" / "umh" / "voice" / "voice_capture_signal_contract.json"
_DOC_PATH = _ROOT / "docs" / "VOICE_CAPTURE_SIGNAL_CONTRACT.md"

# Server error taxonomy + client/retry/send codes that must each have a distinct
# UI string. (The taxonomy the packet requires, plus the failure codes the store
# actually emits.)
_SERVER_TAXONOMY = [
    "EMPTY_AUDIO_BLOB",
    "SILENT_AUDIO",
    "UNSUPPORTED_AUDIO_FORMAT",
    "DECODE_FAILED",
    "VAD_NO_SPEECH",
    "STT_FAILED",
]
_CLIENT_CODES = ["NO_SPEECH"]
_ALL_UI_CODES = _SERVER_TAXONOMY + _CLIENT_CODES


def _read(p: Path) -> str:
    assert p.exists(), f"expected file missing: {p}"
    return p.read_text(encoding="utf-8")


# ── 1. Live audio-level meter reads client RMS ───────────────────────────────


def test_ws_exposes_client_rms_getter():
    """voice-ws must expose a client-computed clientRms getter (0..1)."""
    src = _read(_WS_PATH)
    assert re.search(r"\bget\s+clientRms\s*\(\s*\)", src), (
        "clientRms getter missing on VoiceWsClient"
    )
    # RMS is computed from the capture buffer (sqrt of mean square), not faked.
    # The accumulator is `sumSq` in the merged capture path (post-#241/#249).
    assert "sumSq" in src and "Math.sqrt" in src, (
        "clientRms must be a real RMS of the capture buffer"
    )


def test_ws_exposes_capture_diagnostics():
    """captureDiagnostics() surfaces capture liveness fields, never transcript."""
    src = _read(_WS_PATH)
    assert "captureDiagnostics" in src, "captureDiagnostics() missing on VoiceWsClient"
    for field in ("clientRms", "peakRms", "chunksSent", "capturing"):
        assert field in src, f"captureDiagnostics missing field {field}"


def test_controller_polls_client_rms_into_store():
    """The meter poll reads client.clientRms and writes it into the store (~10Hz)."""
    src = _read(_CONTROLLER_PATH)
    assert "client.clientRms" in src, "meter must source the value from client.clientRms"
    assert "setCaptureRms" in src, "meter poll must write RMS into the store"
    assert "startCaptureMeter" in src and "stopCaptureMeter" in src, (
        "meter start/stop helpers missing"
    )
    # ~10Hz cadence and a cheap interval (no render loop).
    assert re.search(r"METER_POLL_MS\s*=\s*100", src), "meter cadence must be ~10Hz (100ms)"
    assert "setInterval" in src, "meter must be an interval poll"


def test_controller_clears_meter_on_stop():
    """The meter interval is cleared on finalize / abort / stop / destroy."""
    src = _read(_CONTROLLER_PATH)
    assert "clearInterval" in src, "meter interval must be cleared (no leak)"
    # stopCaptureMeter is invoked on every teardown path.
    for teardown in ("_finalizeRecording", "abortActiveRecording", "stopVoice", "destroyVoice"):
        block_start = (
            src.index(f"function {teardown}")
            if f"function {teardown}" in src
            else src.index(teardown)
        )
        assert block_start >= 0
    # At least one stopCaptureMeter() call exists per teardown intent.
    assert src.count("stopCaptureMeter()") >= 4, "meter must be stopped on all teardown paths"


def test_store_has_capture_meter_field():
    """The store carries the live capture RMS the card reads (no card audio loop)."""
    src = _read(_STORE_PATH)
    assert "captureRms" in src, "store missing captureRms field"
    assert "setCaptureRms" in src, "store missing setCaptureRms action"
    assert "resetCaptureMeter" in src, "store missing resetCaptureMeter action"
    assert "captureSilentMs" in src, "store missing captureSilentMs (silent-mic hint gate)"


def test_meter_component_reads_store_rms():
    """The RightRail meter reads the store RMS field, not a local audio loop."""
    src = _read(_RIGHT_RAIL_PATH)
    assert "CaptureMeter" in src, "CaptureMeter component missing"
    assert "s.captureRms" in src, "meter must read captureRms from the store"
    assert "mic appears silent" in src, "silent-mic hint missing from meter"
    # The meter is shown during recording.
    assert "<CaptureMeter" in src, "CaptureMeter not rendered in the recording card"


# ── 2. Precise failure reasons — every code maps to a distinct human string ───


def test_failure_reason_map_present():
    """RightRail carries an error-code → human-string map."""
    src = _read(_RIGHT_RAIL_PATH)
    assert "VOICE_FAILURE_REASON" in src, "VOICE_FAILURE_REASON map missing"
    assert "voiceFailureReason" in src, "voiceFailureReason resolver missing"


def _extract_failure_map(src: str) -> dict[str, str]:
    """Parse the VOICE_FAILURE_REASON object literal into {code: string}."""
    m = re.search(r"VOICE_FAILURE_REASON\s*:\s*Record<[^>]+>\s*=\s*\{(.*?)\n\}", src, re.DOTALL)
    assert m, "could not locate VOICE_FAILURE_REASON object literal"
    body = m.group(1)
    pairs: dict[str, str] = {}
    for code, val in re.findall(r"([A-Z_]+)\s*:\s*'([^']+)'", body):
        pairs[code] = val
    return pairs


def test_every_taxonomy_code_has_ui_string():
    """Each server + client code maps to a UI string (assert coverage)."""
    pairs = _extract_failure_map(_read(_RIGHT_RAIL_PATH))
    for code in _ALL_UI_CODES:
        assert code in pairs, f"taxonomy code {code} has no UI string"
        assert pairs[code].strip(), f"taxonomy code {code} maps to an empty string"


def test_failure_strings_are_distinct():
    """No two taxonomy codes collapse to the same human string."""
    pairs = _extract_failure_map(_read(_RIGHT_RAIL_PATH))
    subset = {c: pairs[c] for c in _ALL_UI_CODES}
    values = list(subset.values())
    assert len(set(values)) == len(values), f"duplicate failure strings: {subset}"


def test_no_bare_no_speech_for_silent_or_decode():
    """SILENT_AUDIO / EMPTY_AUDIO_BLOB / decode failures never read 'No speech detected'."""
    pairs = _extract_failure_map(_read(_RIGHT_RAIL_PATH))
    for code in ("SILENT_AUDIO", "EMPTY_AUDIO_BLOB", "DECODE_FAILED", "UNSUPPORTED_AUDIO_FORMAT"):
        assert pairs[code] != "No speech detected", f"{code} must not read 'No speech detected'"
        assert "No speech detected" not in pairs[code], (
            f"{code} must not embed the bare no-speech phrase"
        )


def test_bare_no_speech_string_removed_from_card():
    """The old unconditional 'No speech detected' branch is gone."""
    src = _read(_RIGHT_RAIL_PATH)
    # The literal must not appear as a hardcoded fallback anymore.
    assert "'No speech detected'" not in src, "bare 'No speech detected' fallback must be removed"
    # Failures now render via the resolver.
    assert "voiceFailureReason(draft.error)" in src, (
        "failed drafts must render via voiceFailureReason"
    )


# ── 3. Send-gate + no premature paste / no premature send preserved ──────────


def test_send_gate_intact():
    """Send stays gated on transcript_status in {final, edited} and status == ready."""
    store = _read(_STORE_PATH)
    assert "draft.status !== 'ready'" in store, "send must refuse when not ready"
    assert "transcript_status !== 'final'" in store and "transcript_status !== 'edited'" in store, (
        "send must require final|edited transcript"
    )
    # UI canSend mirrors the same gate.
    rail = _read(_RIGHT_RAIL_PATH)
    assert "draft.status === 'ready'" in rail, "UI send-gate: status must be ready"
    assert "'final'" in rail and "'edited'" in rail, (
        "UI send-gate: transcript_status must be final|edited"
    )
    assert "disabled={!canSend}" in rail, "Send button must be disabled when canSend is false"


def test_no_premature_paste():
    """A partial transcript never lands in the message input; auto_send stays false."""
    store = _read(_STORE_PATH)
    assert "auto_send: false" in store, "auto_send must remain false"
    # The partial is display-only: it is never CALLED into the chat draft/input.
    # (The phrase may appear in a doc comment stating exactly that; a call must not.)
    assert "setDraftMessage(" not in store, "voice store must not call the chat input draft setter"
    controller = _read(_CONTROLLER_PATH)
    # The controller may DOCUMENT that no such call exists; it must not CALL it.
    assert "addVoiceTranscript(" not in controller, (
        "controller must not push transcript into chat (send-only path)"
    )


def test_controls_present():
    """Send / Retry / Edit / Delete controls remain on the card."""
    rail = _read(_RIGHT_RAIL_PATH)
    for ctrl in (
        "sendDraft(draft.draft_id)",
        "retryDraft(draft.draft_id)",
        "deleteDraft(draft.draft_id)",
    ):
        assert ctrl in rail, f"missing control call {ctrl}"
    assert "setEditing(true)" in rail, "Edit control missing"


# ── 4. Contract JSON: platform matrix + acceptance list ──────────────────────


def test_contract_json_parses():
    data = json.loads(_read(_CONTRACT_PATH))
    assert data["record"] == "voice_capture_signal_contract"


def test_contract_has_acceptance_chain():
    data = json.loads(_read(_CONTRACT_PATH))
    chain = data["acceptance_criteria"]["ordered_signal_chain"]
    joined = " ".join(chain).lower()
    for token in (
        "non_zero_energy",
        "valid_blob",
        "server_decode",
        "vad_speech",
        "stt_transcript",
        "preserved_artifact",
        "transcript_under_card",
        "pause_doesnt_send",
        "explicit_send",
        "chat_only_after_send",
        "delete_leaves_no_trace",
    ):
        assert token in joined, f"acceptance chain missing {token}"


def test_contract_has_platform_matrix_with_per_platform_status():
    data = json.loads(_read(_CONTRACT_PATH))
    platforms = data["platform_matrix"]["platforms"]
    for p in ("desktop_chrome", "mobile_safari", "mobile_chrome", "desktop_safari"):
        assert p in platforms, f"platform matrix missing {p}"
        assert "capture_status" in platforms[p], f"{p} missing capture_status"

    # Desktop chrome = root cause suspended context, FIXED.
    dc = platforms["desktop_chrome"]
    assert dc["capture_status"] == "FIXED"
    assert "suspended" in dc["root_cause"].lower()

    # Mobile safari = mp4/codec gap, documented, does not reject desktop.
    ms = platforms["mobile_safari"]
    assert ms["capture_status"] == "BLOCKED"
    assert "mp4" in (ms["mime"] + ms["root_cause"] + ms["resolution"]).lower()
    assert ms.get("tracked_as") == "P4S-31D-5"

    # Mobile chrome supported; desktop safari deferred.
    assert platforms["mobile_chrome"]["capture_status"] == "SUPPORTED"
    assert platforms["desktop_safari"]["capture_status"] == "DEFERRED"


def test_contract_error_taxonomy_complete_and_distinct():
    data = json.loads(_read(_CONTRACT_PATH))
    codes = data["error_taxonomy"]["codes"]
    for code in _ALL_UI_CODES:
        assert code in codes, f"contract taxonomy missing {code}"
    # No two codes share a string (contract-level distinctness).
    subset = [codes[c] for c in _ALL_UI_CODES]
    assert len(set(subset)) == len(subset), "contract taxonomy has duplicate strings"
    for code in ("SILENT_AUDIO", "EMPTY_AUDIO_BLOB", "DECODE_FAILED"):
        assert codes[code] != "No speech detected"


def test_contract_ui_map_matches_shipped_map():
    """Contract taxonomy strings must match the shipped RightRail map for the taxonomy codes."""
    data = json.loads(_read(_CONTRACT_PATH))
    contract_codes = data["error_taxonomy"]["codes"]
    ui_codes = _extract_failure_map(_read(_RIGHT_RAIL_PATH))
    for code in _ALL_UI_CODES:
        assert contract_codes[code] == ui_codes[code], (
            f"drift for {code}: contract={contract_codes[code]!r} ui={ui_codes[code]!r}"
        )


def test_doc_exists_and_names_platforms():
    doc = _read(_DOC_PATH)
    for p in ("desktop_chrome", "mobile_safari", "mobile_chrome", "desktop_safari"):
        assert p in doc, f"doc missing platform {p}"
    assert "P4S-31D-5" in doc, "doc must cite the mobile_safari tracking packet"


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-v"]))
