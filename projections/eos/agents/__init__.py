"""EOS department agents — one per department in the ARCHITECTURE.md hierarchy."""

from projections.eos.agents.ceo import CEOAgent, register_ceo_agent
from projections.eos.agents.customer_success import (
    CustomerSuccessAgent,
    register_customer_success_agent,
)
from projections.eos.agents.engineering import EngineeringAgent, register_engineering_agent
from projections.eos.agents.finance import FinanceAgent, register_finance_agent
from projections.eos.agents.hr import HRAgent, register_hr_agent
from projections.eos.agents.legal import LegalAgent, register_legal_agent
from projections.eos.agents.marketing import MarketingAgent, register_marketing_agent
from projections.eos.agents.operations import OperationsAgent, register_operations_agent
from projections.eos.agents.product import ProductAgent, register_product_agent
from projections.eos.agents.sales import SalesAgent, register_sales_agent

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

AGENT_CLASSES = {
    "ceo": CEOAgent,
    "sales": SalesAgent,
    "marketing": MarketingAgent,
    "finance": FinanceAgent,
    "customer_success": CustomerSuccessAgent,
    "hr": HRAgent,
    "legal": LegalAgent,
    "operations": OperationsAgent,
    "product": ProductAgent,
    "engineering": EngineeringAgent,
}

__all__ = ["ALL_AGENTS", "AGENT_CLASSES"]
