"""EOS Customer Success Agent — retention, satisfaction, support routing."""

from __future__ import annotations

from substrate import Substrate
from substrate.types import Component, ComponentType, RegistrationResult


async def register_customer_success_agent(substrate: Substrate) -> RegistrationResult:
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-customer-success",
        capabilities=[
            "ticket_routing",
            "satisfaction_tracking",
            "churn_detection",
            "onboarding_guidance",
            "feedback_analysis",
        ],
        metadata={
            "projection": "eos",
            "department": "customer_success",
            "description": "Client retention, satisfaction tracking, and support routing",
        },
    )
    return await substrate.register(component)
