"""Input router — normalizes transport-specific inputs into lifecycle requests.

Sits between raw ingress (Discord message, local CLI, voice transcript)
and the LiveRuntime. Converts freeform text into one of three request types:

    open_day   — session start ritual
    close_day  — session end ritual
    action     — mid-session command (everything else)

Design rules:
- NO intelligence here — pure normalization
- NO adapter imports — transport-agnostic
- NO LLM calls — deterministic classification
- Frozen InputEvent — immutable once created
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InputEvent:
    """Immutable input from any transport.

    Attributes:
        transport: Origin channel (discord, local, voice).
        text:      Raw input text.
        metadata:  Transport-specific extras (user_id, channel, etc.).
    """

    transport: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.transport:
            raise ValueError("InputEvent.transport must not be empty")


# ── Command prefixes ─────────────────────────────────────────────────────

_OPEN_COMMANDS = frozenset({"!open", "!start", "!begin"})
_CLOSE_COMMANDS = frozenset({"!close", "!end", "!shutdown"})
_OBJECTIVE_PREFIX = "objective:"


def _extract_command(text: str) -> str:
    """Return the first whitespace-delimited token, lowercased."""
    stripped = text.strip()
    if not stripped:
        return ""
    return stripped.split()[0].lower()


# ── Public API ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RoutedInput:
    """Result of routing an InputEvent.

    Attributes:
        request_type: Lifecycle request type (open_day, close_day, action).
        intent_text:  The actionable text (command stripped if present).
        transport:    Passed through from the InputEvent.
        metadata:     Passed through from the InputEvent.
    """

    request_type: str
    intent_text: str
    transport: str
    metadata: dict[str, Any] = field(default_factory=dict)


def route_input(event: InputEvent) -> RoutedInput:
    """Classify an InputEvent into a lifecycle request type.

    Rules:
        - Text starting with !open/!start/!begin → open_day
        - Text starting with !close/!end/!shutdown → close_day
        - Everything else → action

    Returns:
        RoutedInput with request_type, cleaned intent_text, and passthrough fields.
    """
    raw_text = event.text.strip()
    lower_text = raw_text.lower()

    if lower_text.startswith(_OBJECTIVE_PREFIX):
        objective_text = raw_text[len(_OBJECTIVE_PREFIX) :].strip()
        return RoutedInput(
            request_type="set_objective",
            intent_text=objective_text,
            transport=event.transport,
            metadata=event.metadata,
        )

    command = _extract_command(event.text)

    if command in _OPEN_COMMANDS:
        # Strip the command prefix to get any trailing intent
        intent = raw_text[len(command) :].strip()
        return RoutedInput(
            request_type="open_day",
            intent_text=intent,
            transport=event.transport,
            metadata=event.metadata,
        )

    if command in _CLOSE_COMMANDS:
        intent = raw_text[len(command) :].strip()
        return RoutedInput(
            request_type="close_day",
            intent_text=intent,
            transport=event.transport,
            metadata=event.metadata,
        )

    # Default: action
    return RoutedInput(
        request_type="action",
        intent_text=raw_text,
        transport=event.transport,
        metadata=event.metadata,
    )
