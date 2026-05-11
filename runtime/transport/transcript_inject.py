"""
Transcript injection — the bounded entry point for text-shaped input
into an active (or resumable) voice session.

Purpose
-------
This is the ONLY sanctioned way for text that looks like "the human just
said something" to flow into the live voice loop without going through
the wake producer or a real STT pipeline. It exists so that:

  - manual operator testing can push transcripts into a node
  - a future local STT producer has a clean, bounded target
  - the audio loop and voice session state stay coherent no matter how
    the text arrived

It is NOT:
  - a command parser
  - a freeform mic → action router
  - a trust-boundary widener
  - an arbitrary audio pipeline

Behavior
--------
inject_transcript(node_id, text, ...):

    1. Validate text is non-empty (strip; return error if empty).
    2. Resolve an active voice session on the node.
       - If none and start_if_missing=True, start a bounded one via
         VoiceSessionRuntime.start_session(node_id, role_slug).
       - Otherwise return {"status": "no_active_session"}.
    3. Delegate to VoiceSessionRuntime.submit_utterance() which:
       - records the user turn
       - marks audio loop LISTENING_WINDOW + transcript
       - invokes the responder (EOS-backed if installed)
       - emits SPEAK_TEXT via station_helpers.propose_speak_text
       - marks audio loop RESPONDING + COOLING_DOWN
    4. Return a small JSON-friendly result dict.

The audio loop / operator state coherence comes for free because
submit_utterance() already wires both layers.
"""

from __future__ import annotations

import sys
from typing import Any, Optional

from runtime.transport.voice_session import (
    VoiceSessionRuntime,
    VoiceSessionStatus,
    VoiceTurnSource,
    get_voice_session_store,
)


def _log(msg: str) -> None:
    print(f"[substrate.transcript_inject] {msg}", file=sys.stderr)


def _resolve_active_session_id(node_id: str) -> Optional[str]:
    try:
        store = get_voice_session_store()
        active = store.active(node_id=node_id)
        if active:
            return active[0].session_id
    except Exception as e:  # noqa: BLE001
        _log(f"active lookup failed for {node_id}: {e}")
    return None


def inject_transcript(
    node_id: str,
    text: str,
    *,
    source: str = "manual",
    start_if_missing: bool = True,
    role_slug: str = "ea_orchestrator",
    metadata: Optional[dict] = None,
    emit_tts: bool = True,
) -> dict[str, Any]:
    """Bounded entry point for transcript-shaped input into the voice loop.

    Returns a JSON-friendly dict with keys:
        status:        "ok" | "empty_text" | "no_active_session" |
                       "start_failed" | "submit_failed" | "session_terminal"
        session_id:    resolved or newly started session id (or None)
        role_slug:     role on the session
        detail:        short human-readable reason
        audio_loop:    post-call audio loop snapshot for this node
    """
    result: dict[str, Any] = {
        "status": "ok",
        "session_id": None,
        "role_slug": None,
        "detail": "",
        "audio_loop": None,
    }

    clean = (text or "").strip()
    if not clean:
        result["status"] = "empty_text"
        result["detail"] = "empty text"
        return result

    # 1. Resolve or start a session.
    session_id = _resolve_active_session_id(node_id)
    runtime = VoiceSessionRuntime()

    if session_id is None:
        if not start_if_missing:
            result["status"] = "no_active_session"
            result["detail"] = (
                "no active voice session on node (start_if_missing=False)"
            )
            return result
        try:
            session = runtime.start_session(
                node_id,
                role_slug=role_slug,
                metadata={"started_by": "transcript_inject", **(metadata or {})},
            )
        except Exception as e:  # noqa: BLE001
            result["status"] = "start_failed"
            result["detail"] = f"start_session crashed: {e}"
            return result
        if session is None or session.status == VoiceSessionStatus.ERROR:
            result["status"] = "start_failed"
            result["detail"] = (
                f"voice session unavailable: "
                f"{getattr(session, 'error_reason', None) or 'unknown'}"
            )
            if session is not None:
                result["session_id"] = session.session_id
                result["role_slug"] = session.role_slug
            return result
        session_id = session.session_id
        result["session_id"] = session_id
        result["role_slug"] = session.role_slug
    else:
        store = get_voice_session_store()
        session = store.get(session_id)
        if session is not None:
            result["session_id"] = session.session_id
            result["role_slug"] = session.role_slug
            if session.status.is_terminal:
                result["status"] = "session_terminal"
                result["detail"] = f"session {session.session_id} is terminal"
                return result

    # 2. Delegate to submit_utterance. This is where audio_loop marks +
    #    responder + SPEAK_TEXT all happen in the canonical path.
    try:
        updated = runtime.submit_utterance(
            session_id,
            clean,
            source=VoiceTurnSource.USER,
            emit_tts=emit_tts,
        )
    except Exception as e:  # noqa: BLE001
        result["status"] = "submit_failed"
        result["detail"] = f"submit_utterance crashed: {e}"
        return result

    if updated is None:
        result["status"] = "submit_failed"
        result["detail"] = "submit_utterance returned None"
        return result

    result["session_id"] = updated.session_id
    result["role_slug"] = updated.role_slug
    result["detail"] = f"submitted via transcript_inject source={source}"

    # 3. Tag the source onto the audio_loop transcript metadata. The
    #    voice session path already recorded a transcript with
    #    source="voice_turn"; if the caller marked a different source
    #    (e.g. "future_stt"), append a light annotation record that
    #    carries that tag explicitly.
    if source != "voice_turn":
        try:
            from runtime.transport.audio_loop import record_transcript

            record_transcript(
                node_id,
                clean,
                source=source,
                session_id=updated.session_id,
                metadata={"annotated_by": "transcript_inject", **(metadata or {})},
            )
        except Exception as e:  # noqa: BLE001
            _log(f"annotation record_transcript failed: {e}")

    # 4. Snapshot audio loop state for the caller's convenience.
    try:
        from runtime.transport.audio_loop import snapshot as audio_snapshot

        result["audio_loop"] = audio_snapshot(node_id=node_id)
    except Exception as e:  # noqa: BLE001
        _log(f"audio_loop snapshot failed: {e}")
        result["audio_loop"] = None

    return result


__all__ = ["inject_transcript"]
