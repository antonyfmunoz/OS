"""P4S-31D1-E — collapsible transcript dropdown on the voice-note card.

Static / source-level checks (like test_p4s31d1c_ui_signal.py): a browser is not
reachable in this repo, so these assertions pin the invariants the packet
requires against the shipped renderer source. They fail closed if a future edit
regresses the collapsible control, the under-card placement, the status labels,
the D1-E binding-error human strings, the operator controls, or the
no-premature-paste rule.

Scope: RightRail.tsx transcript-section UI ONLY. This packet does NOT own the
voice-controller (transcription binding) or the consent/mic-button flow.
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

_ROOT = Path(_WORKTREE)
_RENDERER = _ROOT / "cockpit" / "src" / "renderer"
_RIGHT_RAIL_PATH = _RENDERER / "components" / "RightRail.tsx"

# D1-E transcription-binding error codes. Each MUST have a distinct human string
# and MUST NOT collapse to a no-audio / no-speech phrase (local audio DID arrive;
# the binding, not the mic, failed).
# The canonical local error vocabulary
# (data/umh/voice/voicenote_artifact_binding_contract.json). The earlier
# off-canon UI names (TRANSCRIPT_BINDING_* / UPLOAD_PRESENT_TRANSCRIPT_MISSING)
# were folded into these — controller and UI now share ONE vocabulary.
_D1E_BINDING_CODES = [
    "LOCAL_AUDIO_PRESENT_UPLOAD_MISSING",
    "LOCAL_AUDIO_PRESENT_SERVER_BYTES_EMPTY",
    "AUDIO_ARTIFACT_REF_NOT_FOUND",
    "MISSING_AUDIO_FIELD",
]

# Phrases a binding failure must never read as — these describe a mic that never
# captured, which is precisely NOT what a binding failure is.
_FORBIDDEN_COLLAPSE_PHRASES = [
    "No audio was received",
    "No speech detected",
    "No speech found",
    "no audio captured",
]


def _read(p: Path) -> str:
    assert p.exists(), f"expected file missing: {p}"
    return p.read_text(encoding="utf-8")


def _extract_failure_map(src: str) -> dict[str, str]:
    """Parse the VOICE_FAILURE_REASON object literal into {code: string}."""
    m = re.search(r"VOICE_FAILURE_REASON\s*:\s*Record<[^>]+>\s*=\s*\{(.*?)\n\}", src, re.DOTALL)
    assert m, "could not locate VOICE_FAILURE_REASON object literal"
    body = m.group(1)
    pairs: dict[str, str] = {}
    for code, val in re.findall(r"([A-Z_]+)\s*:\s*'([^']+)'", body):
        pairs[code] = val
    return pairs


# ── 1. A collapsible transcript control exists (toggle + conditional render) ──


def test_transcript_section_component_exists():
    """A dedicated TranscriptSection component renders the dropdown."""
    src = _read(_RIGHT_RAIL_PATH)
    assert "function TranscriptSection" in src, "TranscriptSection component missing"
    assert "data-testid=\"transcript-section\"" in src, "transcript-section test id missing"


def test_collapsible_has_toggle_handler():
    """A local-state toggle drives expand/collapse (no store field touched)."""
    src = _read(_RIGHT_RAIL_PATH)
    # Local state for the toggle.
    assert re.search(r"const\s*\[\s*expanded\s*,\s*setExpanded\s*\]\s*=\s*useState", src), (
        "expand/collapse must be local useState, not store-backed"
    )
    # A toggle handler flips it.
    assert "setExpanded((e) => !e)" in src or "setExpanded(!expanded)" in src, (
        "toggle handler must flip expanded state"
    )
    assert "data-testid=\"transcript-toggle\"" in src, "toggle control test id missing"
    assert "aria-expanded={expanded}" in src, "toggle must expose aria-expanded"


def test_collapsed_expanded_conditional_render():
    """The transcript body is conditionally rendered on the expanded flag."""
    src = _read(_RIGHT_RAIL_PATH)
    assert "{expanded && (" in src, "collapsible body must be gated on `expanded`"
    assert "data-testid=\"transcript-body\"" in src, "transcript-body (collapsible) missing"


def test_chevron_reflects_state():
    """A chevron caret reflects open/closed state."""
    src = _read(_RIGHT_RAIL_PATH)
    assert "ChevronDown" in src and "ChevronRight" in src, "chevron icons missing"
    assert "expanded ? ChevronDown : ChevronRight" in src, (
        "chevron must reflect expanded/collapsed state"
    )


# ── 2. Transcript renders UNDER the audio card ───────────────────────────────


def test_transcript_renders_under_audio_card():
    """The <TranscriptSection> is rendered AFTER the <audio> player in the card."""
    src = _read(_RIGHT_RAIL_PATH)
    audio_idx = src.index("<audio controls")
    section_idx = src.index("<TranscriptSection")
    assert audio_idx < section_idx, "transcript section must render under the audio card"


def test_transcript_section_wired_into_card():
    """VoiceDraftCard mounts the section (passing draft + edit state)."""
    src = _read(_RIGHT_RAIL_PATH)
    assert "<TranscriptSection" in src, "TranscriptSection not mounted in the card"
    assert "draft={draft}" in src, "section must receive the draft"
    assert "editing={editing}" in src, "section must receive editing state"


# ── 3. Status labels: transcribing / ready / failed / edited ─────────────────


def test_status_labels_present():
    """Every transcript lifecycle state surfaces a human label in the header."""
    src = _read(_RIGHT_RAIL_PATH)
    assert "transcriptSectionStatus" in src, "status-deriver missing"
    for label in ("transcribing", "ready", "failed", "edited"):
        assert f"'{label}" in src or f"{label}…" in src, f"status label {label!r} missing"


def test_transcribing_shows_spinner():
    """The transcribing state exposes a spinner affordance."""
    src = _read(_RIGHT_RAIL_PATH)
    assert "Loader2" in src, "transcribing spinner (Loader2) missing"
    assert "animate-spin" in src, "spinner must actually spin"


def test_edited_marker_present():
    """An 'edited' marker is shown for an edited transcript."""
    src = _read(_RIGHT_RAIL_PATH)
    assert "'edited'" in src, "edited status must be handled"
    assert "transcript_status === 'edited'" in src, "edited transcript status must drive a marker"


# ── 4. D1-E binding error codes: distinct human strings, no collapse ─────────


def test_binding_codes_have_distinct_strings():
    """Each D1-E binding error code maps to its own non-empty human string."""
    pairs = _extract_failure_map(_read(_RIGHT_RAIL_PATH))
    for code in _D1E_BINDING_CODES:
        assert code in pairs, f"binding code {code} has no UI string"
        assert pairs[code].strip(), f"binding code {code} maps to an empty string"
    subset = [pairs[c] for c in _D1E_BINDING_CODES]
    assert len(set(subset)) == len(subset), f"duplicate binding strings: {subset}"


def test_binding_codes_do_not_collapse_to_no_audio():
    """A binding failure never reads as a no-audio / no-speech phrase."""
    pairs = _extract_failure_map(_read(_RIGHT_RAIL_PATH))
    for code in _D1E_BINDING_CODES:
        s = pairs[code].lower()
        for phrase in _FORBIDDEN_COLLAPSE_PHRASES:
            assert phrase.lower() not in s, (
                f"{code} must not collapse to {phrase!r} — local audio was present"
            )


def test_reuses_single_failure_map():
    """The binding codes live in the SAME map — not a duplicated second map."""
    src = _read(_RIGHT_RAIL_PATH)
    assert src.count("VOICE_FAILURE_REASON") >= 1
    # There is exactly one object-literal definition of the map.
    assert len(re.findall(r"VOICE_FAILURE_REASON\s*:\s*Record<", src)) == 1, (
        "failure map must not be duplicated"
    )


# ── 5. Edit / Retry / Delete / Send controls remain reachable ────────────────


def test_controls_remain():
    """Send / Retry / Edit / Delete controls are still on the card."""
    src = _read(_RIGHT_RAIL_PATH)
    for ctrl in (
        "sendDraft(draft.draft_id)",
        "retryDraft(draft.draft_id)",
        "deleteDraft(draft.draft_id)",
    ):
        assert ctrl in src, f"missing control call {ctrl}"
    assert "setEditing(true)" in src, "Edit control missing"


def test_edit_reachable_inside_dropdown():
    """The edit textarea lives inside the collapsible body, bound to editText."""
    src = _read(_RIGHT_RAIL_PATH)
    # The editing textarea is rendered within TranscriptSection.
    sect = src[src.index("function TranscriptSection") : src.index("function VoiceDraftCard")]
    assert "editing ?" in sect and "<textarea" in sect, (
        "edit affordance must live inside the transcript dropdown"
    )
    assert "editTranscript(draft.draft_id, editText)" in src, (
        "Save must commit the edit (→ transcript_status 'edited')"
    )


def test_send_gate_preserved():
    """Send stays gated on status ready + transcript_status final|edited."""
    src = _read(_RIGHT_RAIL_PATH)
    assert "draft.status === 'ready'" in src, "send-gate: status must be ready"
    assert "'final'" in src and "'edited'" in src, "send-gate: transcript_status final|edited"
    assert "disabled={!canSend}" in src, "Send must be disabled when canSend is false"


# ── 6. No premature paste — transcript never lands in the chat input ─────────


def test_no_premature_paste_in_rightrail():
    """RightRail never pushes the transcript into the chat input."""
    src = _read(_RIGHT_RAIL_PATH)
    # No call into the chat-input draft setter from the voice card.
    assert "setDraftMessage(" not in src, "transcript must not be pasted into the chat input"
    assert "addVoiceTranscript(" not in src, "transcript must not be pushed into chat (send-only)"


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-v"]))
