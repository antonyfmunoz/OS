"""EOS Sales Agent — pipeline management and outreach execution."""

from __future__ import annotations

from substrate import Substrate
from substrate.types import Component, ComponentType, RegistrationResult


async def register_sales_agent(substrate: Substrate) -> RegistrationResult:
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-sales",
        capabilities=["lead_scoring", "outreach_drafting", "pipeline_management", "follow_up"],
        metadata={
            "projection": "eos",
            "department": "sales",
            "description": "Pipeline management and outreach execution",
        },
    )
    return await substrate.register(component)
