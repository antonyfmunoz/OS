"""EOS Finance Agent — revenue tracking, expense management, financial forecasting."""

from __future__ import annotations

from substrate import Substrate
from substrate.types import Component, ComponentType, RegistrationResult


async def register_finance_agent(substrate: Substrate) -> RegistrationResult:
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-finance",
        capabilities=[
            "expense_tracking",
            "revenue_monitoring",
            "budget_forecasting",
            "unit_economics",
            "cashflow_analysis",
        ],
        metadata={
            "projection": "eos",
            "department": "finance",
            "description": "Revenue tracking, expense management, and financial forecasting",
        },
    )
    return await substrate.register(component)
