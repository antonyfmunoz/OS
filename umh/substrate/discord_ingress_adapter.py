"""
Discord ingress adapter — translates Discord messages into orchestration events.

Transport-agnostic ingress shape: any interface (Discord text, Discord voice,
workstation, Meet) produces an IngressRequest.  The adapter translates it
into an operator_intent_requested SchedulerEvent via trigger_adapters.from_operator().

This module is the ONLY place where Discord-specific context is normalized
into the orchestration boundary.  The orchestration layer never sees Discord
channel IDs, guild IDs, or message objects.

Gating:
    EOS_DISCORD_ORCHESTRATION_ENABLED — "1" to activate (default "0")

Design constraints:
    - No hot-path imports of services/ or discord.py
    - Stateless — no mutable caches
    - Deterministic — same input always produces same event shape
    - Replay-safe — IngressRequest.to_dict() is JSON-serializable
    - Graceful degradation — disabled mode returns None, never raises

Usage:
    from umh.substrate.discord_ingress_adapter import (
        IngressRequest,
        IngressResult,
        ingest_discord_message,
    )

    result = ingest_discord_message(
        text="run morning brief",
        user_id="123456",
        channel_id="789",
        guild_id="456",
        channel_name="general",
    )
    if result.accepted:
        scheduler.emit(result.event)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from umh.substrate.event_scheduler import SchedulerEvent
from umh.substrate.trigger_adapters import from_operator

_LOG_PREFIX = "[substrate.discord_ingress_adapter]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _flag_truthy(env_var: str, default: str = "0") -> bool:
    return os.getenv(env_var, default).strip().lower() in ("1", "true", "yes")


# ── Transport types (extensible for voice/workstation) ─────────────────


TRANSPORT_DISCORD_TEXT = "discord_text"
TRANSPORT_DISCORD_VOICE = "discord_voice"
TRANSPORT_WORKSTATION = "workstation"
TRANSPORT_MEET = "meet"


# ── Intent classification ──────────────────────────────────────────────

# Channel-name hints → intent_type mapping.
# Uses the same classification vocabulary as IntentType but maps
# common Discord channel names to orchestration-level intent types.
_CHANNEL_INTENT_HINTS: dict[str, str] = {
    "morning-brief": "workflow_run",
    "decisions": "workflow_run",
    "general": "workflow_run",
    "agent-activity": "workflow_run",
}

# Command prefix → intent_type for explicit operator commands
_COMMAND_PREFIX_MAP: dict[str, str] = {
    "!run ": "workflow_run",
    "!execute ": "execution_request",
    "!workflow ": "workflow_run",
    "!intent ": "custom",
}


def classify_intent_type(
    text: str,
    channel_name: str = "",
) -> str:
    """Classify operator text into an IntentType string.

    Checks explicit command prefixes first, then channel hints,
    then defaults to workflow_run.  Always returns a valid
    IntentType value string.
    """
    lower = text.strip().lower()

    # Explicit command prefix
    for prefix, intent_type in _COMMAND_PREFIX_MAP.items():
        if lower.startswith(prefix):
            return intent_type

    # Channel-based hint
    if channel_name in _CHANNEL_INTENT_HINTS:
        return _CHANNEL_INTENT_HINTS[channel_name]

    return "workflow_run"


def extract_goal_text(text: str) -> str:
    """Strip command prefix from text to get the goal payload.

    If text starts with a known command prefix, strip it.
    Otherwise return the full text.
    """
    lower = text.strip().lower()
    for prefix in _COMMAND_PREFIX_MAP:
        if lower.startswith(prefix):
            return text.strip()[len(prefix) :].strip()
    return text.strip()


# ── IngressRequest — transport-agnostic ingress shape ──────────────────


@dataclass(frozen=True)
class IngressRequest:
    """Normalized ingress event from any interface transport.

    This is the transport-agnostic shape.  Discord text, Discord voice,
    Meet events, and workstation commands all produce IngressRequests.

    Fields:
        text:           The operator's raw text/utterance.
        operator_id:    Unique operator identifier (Discord user ID, etc).
        transport:      Transport type constant (TRANSPORT_DISCORD_TEXT, etc).
        channel_id:     Channel/room identifier (transport-specific).
        guild_id:       Server/workspace identifier (transport-specific).
        channel_name:   Human-readable channel name for classification.
        timestamp:      ISO timestamp of the original message.
        metadata:       Optional transport-specific metadata.
    """

    text: str
    operator_id: str
    transport: str = TRANSPORT_DISCORD_TEXT
    channel_id: str = ""
    guild_id: str = ""
    channel_name: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(
                self,
                "timestamp",
                datetime.now(timezone.utc).isoformat(),
            )

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable representation for replay/audit."""
        return {
            "text": self.text,
            "operator_id": self.operator_id,
            "transport": self.transport,
            "channel_id": self.channel_id,
            "guild_id": self.guild_id,
            "channel_name": self.channel_name,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


# ── IngressResult — return value from ingestion ────────────────────────


@dataclass
class IngressResult:
    """Result of ingesting a message through the adapter.

    Fields:
        accepted:       True if the message was translated into an event.
        event:          The SchedulerEvent (None if rejected/disabled).
        intent_type:    Classified intent type string.
        intent_id:      Deterministic intent ID (empty if rejected).
        reason:         Rejection reason when accepted=False.
        ingress_request: The normalized IngressRequest for audit.
    """

    accepted: bool
    event: SchedulerEvent | None = None
    intent_type: str = ""
    intent_id: str = ""
    reason: str = ""
    ingress_request: IngressRequest | None = None

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable summary."""
        d: dict[str, Any] = {
            "accepted": self.accepted,
            "intent_type": self.intent_type,
            "intent_id": self.intent_id,
            "reason": self.reason,
        }
        if self.ingress_request:
            d["ingress"] = self.ingress_request.to_dict()
        if self.event:
            d["event_type"] = self.event.event_type
            d["event_id"] = self.event.event_id
        return d


# ── Core ingestion function ────────────────────────────────────────────


def ingest_discord_message(
    text: str,
    user_id: str,
    channel_id: str = "",
    guild_id: str = "",
    channel_name: str = "",
    session_name: str = "",
    metadata: dict[str, Any] | None = None,
) -> IngressResult:
    """Translate a Discord text message into an orchestration ingress event.

    This is the canonical Discord text → orchestration boundary.
    Returns IngressResult with accepted=True and a SchedulerEvent when
    the adapter is enabled and the message is valid.

    When disabled (EOS_DISCORD_ORCHESTRATION_ENABLED != "1"), returns
    IngressResult with accepted=False and reason="disabled".

    Args:
        text:           Raw message text from Discord.
        user_id:        Discord user ID string.
        channel_id:     Discord channel ID string.
        guild_id:       Discord guild ID string.
        channel_name:   Discord channel name for intent classification.
        session_name:   Override session name (defaults to channel-derived).
        metadata:       Optional extra metadata to attach.

    Returns:
        IngressResult with the translated event or rejection reason.
    """
    # Gate check
    if not _flag_truthy("EOS_DISCORD_ORCHESTRATION_ENABLED"):
        return IngressResult(accepted=False, reason="disabled")

    # Validate input
    clean_text = text.strip()
    if not clean_text:
        return IngressResult(accepted=False, reason="empty_text")

    if not user_id:
        return IngressResult(accepted=False, reason="missing_operator_id")

    # Build transport-agnostic ingress request
    ingress = IngressRequest(
        text=clean_text,
        operator_id=user_id,
        transport=TRANSPORT_DISCORD_TEXT,
        channel_id=channel_id,
        guild_id=guild_id,
        channel_name=channel_name,
        metadata=metadata or {},
    )

    # Classify intent
    intent_type = classify_intent_type(clean_text, channel_name)
    goal_text = extract_goal_text(clean_text)

    # Derive session name
    if session_name:
        resolved_session = session_name
    elif channel_id:
        resolved_session = f"discord:{channel_id}"
    else:
        resolved_session = "discord:default"

    # Build goal payload
    goal: dict[str, Any] = {
        "text": goal_text,
        "session_name": resolved_session,
        "transport": TRANSPORT_DISCORD_TEXT,
        "channel_id": channel_id,
        "channel_name": channel_name,
    }

    # Build the orchestration event via the existing trigger adapter
    event = from_operator(
        intent_type=intent_type,
        goal=goal,
        priority=100,
        session_name=resolved_session,
        operator_id=user_id,
        source_context={
            "ingress": ingress.to_dict(),
            "adapter": "discord_ingress_adapter",
        },
    )

    _log(
        f"ingested: intent_type={intent_type} "
        f"operator={user_id} channel={channel_name} "
        f"event_id={event.event_id}"
    )

    return IngressResult(
        accepted=True,
        event=event,
        intent_type=intent_type,
        intent_id=event.event_id,
        ingress_request=ingress,
    )


# ── Convenience: full ingest + emit ────────────────────────────────────


def ingest_and_emit(
    text: str,
    user_id: str,
    channel_id: str = "",
    guild_id: str = "",
    channel_name: str = "",
    session_name: str = "",
    metadata: dict[str, Any] | None = None,
    scheduler: Any | None = None,
) -> IngressResult:
    """Ingest a Discord message and emit the event to a scheduler.

    Combines ingest_discord_message + scheduler.emit() in one call.
    If no scheduler is provided, attempts to use the process-local singleton.

    Returns the IngressResult regardless of emit success.
    """
    result = ingest_discord_message(
        text=text,
        user_id=user_id,
        channel_id=channel_id,
        guild_id=guild_id,
        channel_name=channel_name,
        session_name=session_name,
        metadata=metadata,
    )

    if not result.accepted or result.event is None:
        return result

    if scheduler is None:
        try:
            from umh.substrate.execution_authority import _get_primary_scheduler

            scheduler = _get_primary_scheduler()
        except Exception as e:
            _log(f"no scheduler available: {e}")
            return IngressResult(
                accepted=False,
                reason=f"no_scheduler: {e}",
                ingress_request=result.ingress_request,
            )

    scheduler.emit(result.event)
    _log(f"emitted event {result.event.event_id} to scheduler")
    return result
