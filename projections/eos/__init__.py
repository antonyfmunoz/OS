"""EOS projection — EntrepreneurOS department agents registered on the substrate.

This is an application projection. It uses ONLY the public Substrate API
(substrate.execute, substrate.register) and substrate.types. No internal
substrate imports allowed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from substrate.types import Component, ComponentType

if TYPE_CHECKING:
    from substrate import Substrate

EOS_AGENTS = [
    Component(
        component_type=ComponentType.AGENT,
        name="eos-ceo",
        capabilities=["strategy", "decision", "delegation"],
        metadata={"department": "executive", "projection": "eos"},
    ),
    Component(
        component_type=ComponentType.AGENT,
        name="eos-sales",
        capabilities=["outreach", "lead_qualification", "pipeline"],
        metadata={"department": "sales", "projection": "eos"},
    ),
    Component(
        component_type=ComponentType.AGENT,
        name="eos-marketing",
        capabilities=["content", "brand", "audience_growth"],
        metadata={"department": "marketing", "projection": "eos"},
    ),
]


async def register_eos_agents(substrate: Substrate) -> list[Component]:
    """Register all EOS department agents in the substrate registry."""
    registered = []
    for agent in EOS_AGENTS:
        result = await substrate.register(agent)
        if result.success:
            registered.append(agent)
    return registered
