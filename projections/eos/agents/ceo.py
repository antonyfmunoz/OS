"""EOS CEO Agent — strategic decision making for entrepreneur operations."""

from __future__ import annotations

from substrate import Substrate
from substrate.types import Component, ComponentType, RegistrationResult


async def register_ceo_agent(substrate: Substrate) -> RegistrationResult:
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-ceo",
        capabilities=[
            "strategic_analysis",
            "decision_making",
            "outreach_strategy",
            "pipeline_review",
        ],
        metadata={
            "projection": "eos",
            "department": "executive",
            "description": "Strategic decision making for entrepreneur operations",
        },
    )
    return await substrate.register(component)
