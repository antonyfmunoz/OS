"""EOS HR Agent — hiring pipeline, team management, onboarding."""

from __future__ import annotations

from substrate import Substrate
from substrate.types import Component, ComponentType, RegistrationResult


async def register_hr_agent(substrate: Substrate) -> RegistrationResult:
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-hr",
        capabilities=[
            "hiring_pipeline",
            "candidate_screening",
            "onboarding_workflow",
            "team_performance",
            "contractor_management",
        ],
        metadata={
            "projection": "eos",
            "department": "hr",
            "description": "Hiring pipeline management, team operations, and onboarding",
        },
    )
    return await substrate.register(component)
