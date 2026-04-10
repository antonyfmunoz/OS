"""
Role resolver — bridges existing agent_hierarchy ids to substrate AgentRoles.

The current codebase routes through agent_hierarchy.AgentHierarchy, which
uses long-form agent ids like `executive_assistant`, `lyfe_institute_ceo`,
`empyrean_ceo`, `portfolio_advisor`. The substrate uses three abstract role
slugs: `ea_orchestrator`, `ceo`, `portfolio_advisor`.

This module is the translation seam. Orchestration code that wants to speak
in substrate terms (for SafeAction.issued_by, RitualRegistry handoffs, etc.)
calls `resolve_role()` with an agent_hierarchy id and gets back the
corresponding AgentRole without touching agent_hierarchy itself.

Usage:
    from eos_ai.substrate.role_resolver import resolve_role

    role = resolve_role("executive_assistant")
    assert role.slug == "ea_orchestrator"

    role = resolve_role("lyfe_institute_ceo")
    assert role.slug == "ceo"
    assert role.metadata["concrete_id"] == "lyfe_institute_ceo"
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from eos_ai.substrate.roles import AgentRole, RoleRegistry


# Hierarchy agent id → substrate role slug. Any id not in this map resolves
# to None; callers should treat that as "not a substrate-aware agent yet".
_HIERARCHY_TO_ROLE: dict[str, str] = {
    "executive_assistant": "ea_orchestrator",
    "portfolio_advisor": "portfolio_advisor",
    "lyfe_institute_ceo": "ceo",
    "empyrean_ceo": "ceo",
}


def resolve_role(hierarchy_id: str) -> Optional[AgentRole]:
    """
    Return the substrate AgentRole for a given agent_hierarchy id.

    For CEO slots, the resolved role is cloned with `metadata["concrete_id"]`
    set to the original hierarchy id, so callers can still distinguish
    lyfe_institute_ceo from empyrean_ceo at the substrate layer without
    having to enumerate them in the registry.
    """
    slug = _HIERARCHY_TO_ROLE.get(hierarchy_id)
    if slug is None:
        return None
    base = RoleRegistry.default().get(slug)
    if base is None:
        return None
    if slug == "ceo":
        # Clone with concrete id so the substrate can tell CEOs apart.
        return replace(
            base,
            metadata={**base.metadata, "concrete_id": hierarchy_id},
        )
    return base


def substrate_slug_for(hierarchy_id: str) -> Optional[str]:
    """Shortcut for call sites that only need the slug string."""
    return _HIERARCHY_TO_ROLE.get(hierarchy_id)


def all_mappings() -> dict[str, str]:
    """Expose the full hierarchy→substrate mapping for debug endpoints."""
    return dict(_HIERARCHY_TO_ROLE)
