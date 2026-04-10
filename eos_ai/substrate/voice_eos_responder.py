"""
Voice → EOS responder bridge.

Purpose
-------
This is the first real intelligence adapter for the bounded voice session
substrate. It plugs into the existing `set_voice_responder(...)` seam in
`eos_ai.substrate.voice_session` and routes utterances into EOS via the
safest available entrypoint: `eos_ai.model_router.call_with_fallback`.

Design rules
------------
- Lives OUTSIDE the substrate core. The substrate stays generic; EOS-specific
  routing lives here so it can be deleted without touching voice_session.py.
- Bounded. One responding role at a time. Roles must be in EOS_VOICE_ROLES.
- Best-effort. Never raises into the runtime — the runtime already wraps us
  in try/except, but we degrade to a safe fallback string anyway and record
  the failure into session.metadata so operators can see it.
- Read-only on session. We do not mutate turns directly; we only annotate
  `session.metadata["last_responder"]` with provider/model/role/degraded.
  The runtime persists the session right after we return, so the metadata
  flows through to the report and the store.
- Bypasses cognitive_loop / gateway / agent_runtime entirely. We use the
  router because it has zero side effects (no DB, no memory writes, no
  approval gates) and it already knows the live fallback chain
  (cc_sdk → anthropic → gemini → groq → ollama).
- Role-to-model mapping is delegated to model_router._is_ceo_agent() via
  the `agent_type` parameter — `ceo` and `portfolio_advisor` auto-upgrade
  to Opus, `ea_orchestrator` takes the fast path.

What this is NOT
----------------
- Not a streaming responder. One text in, one text out.
- Not a multi-agent moderator. Single role per call.
- Not a freeform shell. The prompt is bounded transcript context only.
- Not the full perceive/plan/act loop. We deliberately use the smallest
  intelligence seam.
"""

from __future__ import annotations

import sys
import threading
from typing import Optional

# These imports are intentionally late-bound where possible so importing
# this module never breaks the substrate even if model_router is sick.
from eos_ai.substrate.voice_session import (
    VoiceResponder,
    VoiceSession,
    set_voice_responder,
)

# ─── Bounded role allow-list ──────────────────────────────────────────────────

EOS_VOICE_ROLES: frozenset[str] = frozenset(
    {
        "ea_orchestrator",
        "ceo",
        "portfolio_advisor",
    }
)

# ─── Tunables ─────────────────────────────────────────────────────────────────

# How many recent turns to feed back as transcript context. Bounded to keep
# prompts short, deterministic, and cheap on the fallback providers.
_CONTEXT_TURN_WINDOW = 1

# Hard cap on a single utterance text we forward to the router. Anything
# beyond this is truncated; the substrate already caps turns to 50.
_MAX_UTTERANCE_CHARS = 2000

# Hard cap on the response text we hand back to the runtime. SPEAK_TEXT is
# bounded by the daemon, but we cut here too so the transcript stays sane.
_MAX_RESPONSE_CHARS = 2000

_DEFAULT_TASK_TYPE = "conversation"
_TRIGGER_SOURCE = "voice_session"


def _log(msg: str) -> None:
    print(f"[substrate.voice_eos_responder] {msg}", file=sys.stderr)


# ─── Role → system prompt ─────────────────────────────────────────────────────


_ROLE_SYSTEM_PROMPTS: dict[str, str] = {
    "ea_orchestrator": (
        "You are the Executive Assistant (EA) orchestrator for EOS. "
        "You are speaking out loud through a bounded voice session. "
        "Be tight, decisive, and operator-friendly. Prefer 1–3 short "
        "sentences. Never invent tools or actions you cannot take. "
        "If a request needs the CEO or Portfolio Advisor, say so plainly."
    ),
    "ceo": (
        "You are the CEO speaking through a bounded voice session. "
        "Be direct, strategic, and decisive. Prefer 1–3 short sentences. "
        "No hedging. No filler. If you need more context, ask for it in "
        "one specific question."
    ),
    "portfolio_advisor": (
        "You are the Portfolio Advisor for EOS, speaking through a bounded "
        "voice session. Be analytical, candid, and concise. Prefer 1–3 "
        "short sentences. Surface tradeoffs. Never invent metrics."
    ),
}


def _system_prompt_for(role_slug: str) -> str:
    return _ROLE_SYSTEM_PROMPTS.get(
        role_slug,
        "You are an EOS agent speaking through a bounded voice session. "
        "Be tight, concrete, and concise.",
    )


# ─── Prompt builder ───────────────────────────────────────────────────────────


def _build_prompt(session: VoiceSession, utterance: str) -> str:
    """Build a small bounded prompt from recent transcript + new utterance.

    Includes only the last `_CONTEXT_TURN_WINDOW` turns and only USER/AGENT
    sources (system turns are noisy lifecycle markers). Agent turns are
    scrubbed of CLI chrome (tmux/Claude Code UI artifacts) before inclusion.
    Pure-string output.
    """
    from eos_ai.substrate.claude_session_bridge import _scrub_cli_chrome

    clean_utt = (utterance or "").strip()
    if len(clean_utt) > _MAX_UTTERANCE_CHARS:
        clean_utt = clean_utt[: _MAX_UTTERANCE_CHARS - 3] + "..."

    lines: list[str] = []
    recent = session.turns[-_CONTEXT_TURN_WINDOW:] if session.turns else []
    for turn in recent:
        src = getattr(turn.source, "value", str(turn.source))
        if src not in ("user", "agent"):
            continue
        text = (turn.text or "").strip()
        if not text:
            continue
        # Scrub CLI chrome from agent turns — they may contain tmux/CC artifacts
        if src == "agent":
            text = _scrub_cli_chrome(text)
            if not text:
                continue
        speaker = "User" if src == "user" else "Agent"
        lines.append(f"{speaker}: {text}")

    transcript = "\n".join(lines)
    if transcript:
        return (
            "Recent voice session transcript (most recent last):\n"
            f"{transcript}\n\n"
            f"User just said: {clean_utt}\n\n"
            "Reply as the active role, in 1-3 short spoken sentences."
        )
    return (
        f"User just said: {clean_utt}\n\n"
        "Reply as the active role, in 1-3 short spoken sentences."
    )


# ─── Metadata helpers ─────────────────────────────────────────────────────────


def _record_responder_meta(
    session: VoiceSession,
    *,
    mode: str,
    role: str,
    provider: Optional[str],
    model: Optional[str],
    degraded: bool,
    error: Optional[str] = None,
) -> None:
    """Annotate the session with the responder outcome.

    The runtime persists the session immediately after we return, so this
    metadata flows into voice_session_report() automatically.
    """
    try:
        session.metadata["last_responder"] = {
            "mode": mode,
            "role_used": role,
            "provider": provider,
            "model": model,
            "degraded": bool(degraded),
            "error": error,
        }
    except Exception as e:  # noqa: BLE001
        _log(f"failed to record responder metadata: {e}")


# ─── The responder itself ────────────────────────────────────────────────────


def _safe_fallback_text(role: str, reason: str) -> str:
    """Structured, speakable degradation message. Never empty."""
    return (
        f"[{role}] I heard you, but my reasoning path is degraded right now "
        f"({reason}). Try again or switch role."
    )


def _route_role(session_role: str) -> str:
    """Map a voice-session role slug to a router agent_type.

    Anything outside EOS_VOICE_ROLES gets clamped to ea_orchestrator so the
    voice loop never falls into an unbounded mode. The substrate already
    rejects unknown roles at switch_role() time, but we double-guard here.
    """
    if session_role in EOS_VOICE_ROLES:
        return session_role
    return "ea_orchestrator"


def _eos_voice_responder(session: VoiceSession, utterance: str) -> str:
    """The actual responder callable installed via set_voice_responder."""
    role = _route_role(session.role_slug)
    system_prompt = _system_prompt_for(role)
    prompt = _build_prompt(session, utterance)

    # Late import so a router import error never poisons module load.
    try:
        from eos_ai.model_router import call_with_fallback
    except Exception as e:  # noqa: BLE001
        _log(f"model_router import failed: {e}")
        _record_responder_meta(
            session,
            mode="eos",
            role=role,
            provider=None,
            model=None,
            degraded=True,
            error=f"router_import_failed: {e}",
        )
        return _safe_fallback_text(role, "router import failed")

    try:
        result = call_with_fallback(
            prompt=prompt,
            system=system_prompt,
            task_type=_DEFAULT_TASK_TYPE,
            trigger_source=_TRIGGER_SOURCE,
            agent_type=role,
        )
    except Exception as e:  # noqa: BLE001
        _log(f"call_with_fallback raised for role={role}: {e}")
        _record_responder_meta(
            session,
            mode="eos",
            role=role,
            provider=None,
            model=None,
            degraded=True,
            error=f"router_raised: {e}",
        )
        return _safe_fallback_text(role, "router error")

    output = (getattr(result, "output", "") or "").strip()
    provider = getattr(result, "provider", None)
    model = getattr(result, "model", None)

    if not output:
        _record_responder_meta(
            session,
            mode="eos",
            role=role,
            provider=provider,
            model=model,
            degraded=True,
            error="empty_output",
        )
        return _safe_fallback_text(role, "no output")

    if len(output) > _MAX_RESPONSE_CHARS:
        output = output[: _MAX_RESPONSE_CHARS - 3] + "..."

    _record_responder_meta(
        session,
        mode="eos",
        role=role,
        provider=provider,
        model=model,
        degraded=False,
        error=None,
    )
    _log(
        f"router responder used role={role} provider={provider} "
        f"model={model} output_chars={len(output)}"
    )
    return output


# ─── Public adapter contract ─────────────────────────────────────────────────


def build_eos_voice_responder() -> VoiceResponder:
    """Return the EOS-backed responder callable.

    Useful when a caller wants to install a customized variant or test the
    bridge in isolation without flipping the global responder.
    """
    return _eos_voice_responder


_install_lock = threading.Lock()
_installed = False


def install_default_eos_voice_responder() -> None:
    """Install the EOS-backed responder as the global voice responder.

    Idempotent. Safe to call multiple times. Backward compatible: pass
    `set_voice_responder(None)` later to restore the substrate stub.
    """
    global _installed
    with _install_lock:
        set_voice_responder(_eos_voice_responder)
        _installed = True


def is_eos_voice_responder_installed() -> bool:
    """True if install_default_eos_voice_responder has been called this process."""
    with _install_lock:
        return _installed


def uninstall_eos_voice_responder() -> None:
    """Restore the substrate's default echo stub. Test/operator helper."""
    global _installed
    with _install_lock:
        set_voice_responder(None)
        _installed = False
