"""EOS Marketing Agent — content strategy and brand execution."""

from __future__ import annotations

from substrate import Substrate
from substrate.types import Component, ComponentType, RegistrationResult


async def register_marketing_agent(substrate: Substrate) -> RegistrationResult:
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-marketing",
        capabilities=[
            "content_strategy",
            "content_creation",
            "brand_management",
            "audience_analysis",
        ],
        metadata={
            "projection": "eos",
            "department": "marketing",
            "description": "Content strategy and brand execution",
        },
    )
    return await substrate.register(component)
