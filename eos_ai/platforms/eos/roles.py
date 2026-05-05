"""
EOS platform roles — domain-specific business roles projected onto the substrate.

These are EOS-level roles used for founder intent routing, delegation, and
response formatting.  They are NOT substrate roles (those live in
eos_ai/substrate/roles.py).  The mapping between platform roles and substrate
AgentRole slugs is maintained here as ROLE_TO_SUBSTRATE_SLUG.

Design rules:
- Platform-only — never imported by substrate modules.
- Metadata is static — no LLM, no DB, no runtime state.
- Substrate slug mapping enables platform → substrate bridging without
  coupling the substrate to EOS business semantics.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


# ─── Role enum ───────────────────────────────────────────────────────────────


class EOSRole(str, Enum):
    """Business roles within the EOS platform layer."""

    EA = "ea"
    CEO = "ceo"
    PORTFOLIO_ADVISOR = "portfolio_advisor"
    GENERAL = "general"


# ─── Role metadata ───────────────────────────────────────────────────────────


_ROLE_META: dict[EOSRole, dict[str, Any]] = {
    EOSRole.EA: {
        "title": "Executive Assistant",
        "domains": [
            "communication",
            "coordination",
            "summaries",
            "escalation",
            "task_intake",
            "briefings",
        ],
        "description": (
            "Sole founder-facing communication interface. "
            "Routes intent, delegates to specialists, returns "
            "condensed outputs to the founder."
        ),
        "founder_facing": True,
    },
    EOSRole.CEO: {
        "title": "Chief Executive Officer",
        "domains": [
            "strategy",
            "priorities",
            "resource_allocation",
            "business_decisions",
            "revenue",
        ],
        "description": (
            "Strategic decision-maker. Handles priorities, business "
            "direction, resource allocation, and revenue strategy. "
            "Reports back through EA."
        ),
        "founder_facing": False,
    },
    EOSRole.PORTFOLIO_ADVISOR: {
        "title": "Portfolio Advisor",
        "domains": [
            "investments",
            "capital_allocation",
            "risk",
            "portfolio_review",
            "financial_analysis",
        ],
        "description": (
            "Investment and capital intelligence. Reads everything, "
            "decides nothing. Provides analysis and recommendations "
            "through EA."
        ),
        "founder_facing": False,
    },
    EOSRole.GENERAL: {
        "title": "General",
        "domains": ["utility", "fallback"],
        "description": "Fallback utility role for unclassified requests.",
        "founder_facing": False,
    },
}


def get_role_meta(role: EOSRole) -> dict[str, Any]:
    """Return metadata for a platform role."""
    return dict(_ROLE_META[role])


def get_all_roles() -> list[dict[str, Any]]:
    """Return metadata for all platform roles."""
    return [{"role": r.value, **get_role_meta(r)} for r in EOSRole]


def is_founder_facing(role: EOSRole) -> bool:
    """Only EA is founder-facing."""
    return _ROLE_META[role]["founder_facing"]


# ─── Substrate bridge ────────────────────────────────────────────────────────

# Maps EOS platform roles to substrate AgentRole slugs.
# This is the ONLY coupling point between platform and substrate role systems.

ROLE_TO_SUBSTRATE_SLUG: dict[EOSRole, str] = {
    EOSRole.EA: "ea_orchestrator",
    EOSRole.CEO: "ceo",
    EOSRole.PORTFOLIO_ADVISOR: "portfolio_advisor",
    EOSRole.GENERAL: "ea_orchestrator",  # general falls through to EA in substrate
}


def substrate_slug(role: EOSRole) -> str:
    """Return the substrate AgentRole slug for a platform role."""
    return ROLE_TO_SUBSTRATE_SLUG[role]
