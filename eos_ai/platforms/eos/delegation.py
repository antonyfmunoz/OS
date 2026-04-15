"""
Delegation logic — decides whether EA handles a founder intent directly or
delegates to a specialist role (CEO, Portfolio Advisor).

Design rules:
- EA is always the primary interface — delegation is internal.
- Builder is never a founder-facing delegation target.
- Delegation is based on intent type, not raw text (already classified upstream).
- Returns None when EA handles directly.
"""

from __future__ import annotations

from eos_ai.platforms.eos.intent_routing import FounderIntent, FounderIntentType
from eos_ai.platforms.eos.roles import EOSRole


# ─── Delegation mapping ─────────────────────────────────────────────────────

# Intent types that trigger delegation and their target roles.
# Anything not in this map stays with EA.

_DELEGATION_MAP: dict[FounderIntentType, EOSRole] = {
    FounderIntentType.STRATEGY: EOSRole.CEO,
    FounderIntentType.PORTFOLIO: EOSRole.PORTFOLIO_ADVISOR,
}

# Intent types that EA always handles directly (no delegation).
_EA_DIRECT: frozenset[FounderIntentType] = frozenset(
    {
        FounderIntentType.DIRECT_EA,
        FounderIntentType.STATUS,
        FounderIntentType.REVIEW,
        FounderIntentType.EXECUTION,
        FounderIntentType.UNKNOWN,
    }
)


# ─── Public API ──────────────────────────────────────────────────────────────


def should_delegate(intent: FounderIntent) -> bool:
    """
    Return True if this intent should be delegated to a specialist role.

    EA handles: status, review, execution intake, direct communication, unknown.
    Delegates: strategy → CEO, portfolio → Portfolio Advisor.
    """
    return intent.intent_type in _DELEGATION_MAP


def choose_delegate(intent: FounderIntent) -> EOSRole | None:
    """
    Return the specialist role to delegate to, or None if EA handles directly.

    Never returns EOSRole.GENERAL or any builder-type role.
    """
    return _DELEGATION_MAP.get(intent.intent_type)
