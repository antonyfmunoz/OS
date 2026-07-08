"""P4S31 — playable voice messages (iMessage/Instagram/Telegram-style).

The operator's REAL recorded audio is sent as a playable voice message: the blob
(already captured + uploaded + attached by the convergence pipeline) renders as an
inline audio player, alongside the transcript text. Structural guards over the
frontend wiring; runtime behavior is covered by tsc + the cockpit build.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ROOT = Path(__file__).resolve().parent.parent
_REN = _ROOT / "cockpit" / "src" / "renderer"


def _read(rel: str) -> str:
    return (_REN / rel).read_text(encoding="utf-8")


def test_media_attachment_type_includes_audio() -> None:
    store = _read("stores/chatStore.ts")
    # the 'audio' media type must exist so an uploaded voice blob renders as a
    # player, not a generic file/download.
    assert "'image' | 'video' | 'audio' | 'file'" in store
    # client-side pending-media derivation detects audio/* too
    assert "startsWith('audio/') ? 'audio'" in store


def test_message_bubble_renders_audio_player() -> None:
    rail = _read("components/RightRail.tsx")
    # a dedicated playable component, wired into MediaGrid on media_type audio
    assert "VoiceMessagePlayer" in rail
    assert "m.media_type === 'audio'" in rail
    # it is a real <audio> player with play/pause + scrub
    assert "<audio" in rail
    assert "onLoadedMetadata" in rail and "onTimeUpdate" in rail


def test_server_upload_returns_audio_media_type() -> None:
    # The backend already classifies audio uploads as media_type 'audio' — the
    # frontend player depends on this. Guard it so a refactor can't silently
    # relabel voice messages as files.
    routes = (
        _ROOT / "transports" / "api" / "cockpit_chat_routes.py"
    ).read_text(encoding="utf-8")
    assert 'media_type = "audio"' in routes


def test_operator_message_carries_media_through_send() -> None:
    # The voice-note send path rides the audio artifact as message media so the
    # operator's own bubble renders the player (not just the transcript).
    store = _read("stores/chatStore.ts")
    assert "media: opts.media" in store  # addVoiceTranscript → sendMessage
    assert "const preUploaded = opts?.media" in store  # sendMessage consumes it
