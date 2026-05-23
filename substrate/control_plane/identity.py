"""Identity resolution for the substrate control plane.

Wraps existing production code (BIS, context loader) behind a clean
Protocol interface with deterministic fallback defaults.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from substrate.types import Identity, SignalEnvelope


@runtime_checkable
class IdentityResolver(Protocol):
    """Resolves a SignalEnvelope into an Identity for execution."""

    async def resolve(self, signal: SignalEnvelope) -> Identity: ...


class ConcreteIdentityResolver:
    """Production identity resolver.

    Loads AI name, business stage, personality, and autonomy from
    existing state modules. Falls back to safe defaults when any
    state module is unavailable (no DB, test environment, etc.).
    """

    FOUNDATION_VALUES: dict[str, str] = {
        "reality": "Ground everything in observable truth",
        "intelligence": "Compound capability through every interaction",
        "personalization": "Adapt to user context and preferences",
        "execution": "Produce tangible outcomes, not just plans",
    }

    async def resolve(self, signal: SignalEnvelope) -> Identity:
        import sys

        sys.path.insert(0, "/opt/OS")

        try:
            from state.business.business_instance import get_ai_name, get_business_stage

            ai_name = get_ai_name()
            business_stage = get_business_stage()
        except Exception:
            ai_name = "DEX"
            business_stage = "pre_revenue"

        try:
            from state.context.context import load_context_from_env

            ctx = load_context_from_env()
            personality = ctx.get("personality", "professional")
            autonomy_level = ctx.get("autonomy_level", 1)
        except Exception:
            personality = "professional"
            autonomy_level = 1

        return Identity(
            user_id=signal.user_id,
            organization_id=signal.organization_id,
            venture_id=signal.venture_id,
            ai_name=ai_name,
            ai_personality=personality,
            autonomy_level=autonomy_level,
            business_stage=business_stage,
        )
