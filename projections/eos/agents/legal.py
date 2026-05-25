"""EOS Legal Agent — contract review, compliance tracking, entity management."""

from __future__ import annotations

from substrate import Substrate
from substrate.types import Component, ComponentType, RegistrationResult


async def register_legal_agent(substrate: Substrate) -> RegistrationResult:
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-legal",
        capabilities=[
            "contract_review",
            "compliance_tracking",
            "entity_management",
            "terms_drafting",
            "ip_protection",
        ],
        metadata={
            "projection": "eos",
            "department": "legal",
            "description": "Contract review, compliance tracking, and entity management",
        },
    )
    return await substrate.register(component)
