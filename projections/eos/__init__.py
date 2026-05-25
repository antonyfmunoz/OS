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
        capabilities=["strategy", "decision", "delegation", "approval"],
        metadata={"department": "executive", "projection": "eos", "permission_tier": "commit"},
    ),
    Component(
        component_type=ComponentType.AGENT,
        name="eos-sales",
        capabilities=["outreach", "lead_qualification", "pipeline", "call_booking"],
        metadata={"department": "sales", "projection": "eos", "permission_tier": "execute"},
    ),
    Component(
        component_type=ComponentType.AGENT,
        name="eos-marketing",
        capabilities=["content", "brand", "audience_growth", "publishing"],
        metadata={"department": "marketing", "projection": "eos", "permission_tier": "execute"},
    ),
    Component(
        component_type=ComponentType.AGENT,
        name="eos-finance",
        capabilities=["expense_tracking", "revenue_monitoring", "forecasting", "payments"],
        metadata={"department": "finance", "projection": "eos", "permission_tier": "commit"},
    ),
    Component(
        component_type=ComponentType.AGENT,
        name="eos-customer-success",
        capabilities=["ticket_routing", "satisfaction", "churn_detection", "messaging"],
        metadata={
            "department": "customer_success",
            "projection": "eos",
            "permission_tier": "execute",
        },
    ),
    Component(
        component_type=ComponentType.AGENT,
        name="eos-hr",
        capabilities=["hiring", "onboarding", "team_performance", "outreach"],
        metadata={"department": "hr", "projection": "eos", "permission_tier": "execute"},
    ),
    Component(
        component_type=ComponentType.AGENT,
        name="eos-legal",
        capabilities=["contract_review", "compliance", "entity_management", "contract_execution"],
        metadata={"department": "legal", "projection": "eos", "permission_tier": "commit"},
    ),
    Component(
        component_type=ComponentType.AGENT,
        name="eos-operations",
        capabilities=["workflow_optimization", "process_automation", "monitoring", "reporting"],
        metadata={"department": "operations", "projection": "eos", "permission_tier": "execute"},
    ),
    Component(
        component_type=ComponentType.AGENT,
        name="eos-product",
        capabilities=["roadmap", "feature_prioritization", "user_feedback", "spec_drafting"],
        metadata={"department": "product", "projection": "eos", "permission_tier": "draft"},
    ),
    Component(
        component_type=ComponentType.AGENT,
        name="eos-engineering",
        capabilities=["code_review", "architecture", "deployment", "incident_response"],
        metadata={"department": "engineering", "projection": "eos", "permission_tier": "execute"},
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
