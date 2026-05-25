"""EOS Product Agent — roadmap management, feature prioritization, user feedback."""

from __future__ import annotations

from substrate import Substrate
from substrate.types import Component, ComponentType, RegistrationResult


async def register_product_agent(substrate: Substrate) -> RegistrationResult:
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-product",
        capabilities=[
            "roadmap_management",
            "feature_prioritization",
            "user_feedback_analysis",
            "competitor_tracking",
            "release_planning",
        ],
        metadata={
            "projection": "eos",
            "department": "product",
            "description": "Roadmap management, feature prioritization, and user feedback",
        },
    )
    return await substrate.register(component)
