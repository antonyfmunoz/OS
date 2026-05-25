"""EOS department agents — one per department in the ARCHITECTURE.md hierarchy."""

from projections.eos.agents.ceo import register_ceo_agent
from projections.eos.agents.sales import register_sales_agent
from projections.eos.agents.marketing import register_marketing_agent
from projections.eos.agents.finance import register_finance_agent
from projections.eos.agents.customer_success import register_customer_success_agent
from projections.eos.agents.hr import register_hr_agent
from projections.eos.agents.legal import register_legal_agent
from projections.eos.agents.operations import register_operations_agent
from projections.eos.agents.product import register_product_agent
from projections.eos.agents.engineering import register_engineering_agent

ALL_AGENTS = [
    register_ceo_agent,
    register_sales_agent,
    register_marketing_agent,
    register_finance_agent,
    register_customer_success_agent,
    register_hr_agent,
    register_legal_agent,
    register_operations_agent,
    register_product_agent,
    register_engineering_agent,
]

__all__ = ["ALL_AGENTS"]
