"""
Discord integration hook — thin wrapper for calling the EOS platform from Discord.

This module provides handle_eos_discord_message() which wraps:
- handle_founder_message() for intent routing
- format output for Discord delivery

Also provides EOS-level live session helpers that bridge platform roles
into the generic substrate live session store.

Design rules:
- Thin adapter — no business logic here.
- Does NOT modify existing Discord routing (services/discord_bot.py).
- Callable from Discord paths but does not import discord.py.
- Live session helpers use platform role strings, not substrate role slugs.
"""

from __future__ import annotations

import sys
from typing import Optional

from eos_ai.platforms.eos.ea_orchestrator import EAResponse, handle_founder_message
from eos_ai.platforms.eos.roles import EOSRole


def _log(msg: str) -> None:
    print(f"[platform.eos.discord_hook] {msg}", file=sys.stderr)


# ─── Discord message handler ────────────────────────────────────────────────


def handle_eos_discord_message(
    text: str,
    *,
    session_id: Optional[str] = None,
) -> str:
    """
    Process a founder Discord message through the EOS platform layer.

    Returns the formatted response text ready for Discord delivery.
    The caller (discord_bot.py) is responsible for sending it.
    """
    response: EAResponse = handle_founder_message(text, session_id=session_id)
    return response.response_text


# ─── Live session platform bridge ────────────────────────────────────────────


def create_ea_live_session(
    title: str,
    *,
    session_type: str = "DISCORD_VOICE",
    participant_roles: Optional[list[EOSRole]] = None,
    day_session_id: Optional[str] = None,
) -> Optional[str]:
    """
    Create a live session with EOS platform role participants.

    Returns the live_session_id, or None on failure.
    Participant roles are stored as their string values (platform-level,
    not substrate slugs).
    """
    try:
        from eos_ai.substrate.live_sessions import (
            LiveSessionType,
            create_live_session,
        )

        # Map string to LiveSessionType
        type_map = {
            "VOICE": LiveSessionType.VOICE,
            "MEETING": LiveSessionType.MEETING,
            "DISCORD_VOICE": LiveSessionType.DISCORD_VOICE,
            "GOOGLE_MEET": LiveSessionType.GOOGLE_MEET,
            "LOCAL": LiveSessionType.LOCAL,
        }
        s_type = type_map.get(session_type, LiveSessionType.DISCORD_VOICE)

        # Convert platform roles to string list for substrate
        role_strings = [EOSRole.EA.value]  # EA always participates
        if participant_roles:
            for r in participant_roles:
                if r.value not in role_strings:
                    role_strings.append(r.value)

        session = create_live_session(
            title=title,
            session_type=s_type,
            primary_agent_role=EOSRole.EA.value,
            participant_agent_roles=role_strings,
            day_session_id=day_session_id,
        )
        _log(f"created live session {session.live_session_id}")
        return session.live_session_id

    except Exception as exc:
        _log(f"live session creation failed: {exc}")
        return None


def attach_founder_issue_to_live_session(
    live_session_id: str,
    issue_text: str,
    *,
    session_id: Optional[str] = None,
) -> Optional[str]:
    """
    Attach a founder issue to a live session by creating a substrate task
    and linking it to the session.

    Returns the created task_id, or None on failure.
    """
    try:
        from eos_ai.substrate.live_sessions import attach_task_to_live_session
        from eos_ai.substrate.task_system import create_task

        task = create_task(issue_text, session_id=session_id)
        attach_task_to_live_session(live_session_id, task.task_id)
        _log(f"attached task {task.task_id} to live session {live_session_id}")
        return task.task_id

    except Exception as exc:
        _log(f"attach to live session failed: {exc}")
        return None


# ─── Live runtime bridge ─────────────────────────────────────────────────────


def handle_eos_discord_live_message(
    text: str,
    *,
    session_id: Optional[str] = None,
    dry_run: bool = False,
) -> str:
    """
    Process a founder Discord message through the EA live runtime.

    Unlike handle_eos_discord_message (which uses the EA orchestrator directly),
    this routes through the live runtime for control phrase interception,
    immediate execution, and live session binding.

    Falls back to handle_eos_discord_message if the live runtime fails.
    """
    try:
        from eos_ai.platforms.eos.live_runtime import handle_live_user_utterance

        result = handle_live_user_utterance(
            text, session_id=session_id, dry_run=dry_run
        )
        return result.spoken_text

    except Exception as exc:
        _log(f"live runtime failed, falling back to direct EA: {exc}")
        return handle_eos_discord_message(text, session_id=session_id)
