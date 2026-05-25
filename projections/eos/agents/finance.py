"""EOS Finance Agent — revenue tracking, expense management, financial forecasting.

Permission tier: COMMIT — handles financial actions requiring human approval.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from substrate import Substrate
from substrate.types import Component, ComponentType, PermissionTier, RegistrationResult

from projections.eos.agents.base import DepartmentAgent, SkillResult


class FinanceAgent(DepartmentAgent):
    DEPARTMENT = "finance"
    PERMISSION_TIER = PermissionTier.COMMIT

    def _register_skills(self) -> None:
        self._add_skill(
            "revenue_report",
            "report",
            "Generate revenue summary for a time period",
            self._revenue_report,
        )
        self._add_skill(
            "expense_tracking",
            "report",
            "Track and categorize expenses",
            self._expense_tracking,
        )
        self._add_skill(
            "budget_forecast",
            "analyze",
            "Forecast budget based on current burn rate and revenue",
            self._budget_forecast,
        )
        self._add_skill(
            "unit_economics",
            "analyze",
            "Calculate unit economics (CAC, LTV, margins)",
            self._unit_economics,
        )
        self._add_skill(
            "cashflow_analysis",
            "analyze",
            "Analyze cash flow and runway",
            self._cashflow_analysis,
        )
        self._add_skill(
            "payment_processing",
            "execute_payment",
            "Process a payment (requires human approval)",
            self._payment_processing,
        )
        self._add_skill(
            "invoice_draft",
            "draft_content",
            "Draft an invoice for review",
            self._invoice_draft,
        )

    def _revenue_report(self, period: str = "month", **kwargs: Any) -> SkillResult:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT COALESCE(SUM((payload_json->>'amount')::numeric), 0) as total,
                           COUNT(*) as count
                    FROM events
                    WHERE org_id = %s AND event_type = 'revenue'
                    AND created_at >= NOW() - INTERVAL '1 month'
                    """,
                    (self._org_id,),
                )
                row = cur.fetchone()
                return SkillResult(
                    success=True,
                    output={
                        "period": period,
                        "total_revenue": float(row["total"]) if row else 0,
                        "transaction_count": row["count"] if row else 0,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
        except Exception as e:
            return SkillResult(
                success=True,
                output={
                    "period": period,
                    "total_revenue": 0,
                    "transaction_count": 0,
                    "note": f"No revenue data available: {e}",
                },
            )

    def _expense_tracking(self, category: str = "all", **kwargs: Any) -> SkillResult:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json->>'category' as category,
                           COALESCE(SUM((payload_json->>'amount')::numeric), 0) as total
                    FROM events
                    WHERE org_id = %s AND event_type = 'expense'
                    AND created_at >= NOW() - INTERVAL '1 month'
                    GROUP BY payload_json->>'category'
                    ORDER BY total DESC
                    """,
                    (self._org_id,),
                )
                rows = cur.fetchall()
                return SkillResult(
                    success=True,
                    output={
                        "expenses_by_category": [
                            {"category": r["category"], "total": float(r["total"])} for r in rows
                        ],
                    },
                )
        except Exception:
            return SkillResult(success=True, output={"expenses_by_category": []})

    def _budget_forecast(self, months_ahead: int = 3, **kwargs: Any) -> SkillResult:
        monthly_burn = kwargs.get("monthly_burn", 0)
        monthly_revenue = kwargs.get("monthly_revenue", 0)
        cash_on_hand = kwargs.get("cash_on_hand", 0)

        net_monthly = monthly_revenue - monthly_burn
        runway_months = cash_on_hand / monthly_burn if monthly_burn > 0 else float("inf")

        forecast = []
        balance = cash_on_hand
        for m in range(1, months_ahead + 1):
            balance += net_monthly
            forecast.append({"month": m, "projected_balance": round(balance, 2)})

        return SkillResult(
            success=True,
            output={
                "monthly_burn": monthly_burn,
                "monthly_revenue": monthly_revenue,
                "net_monthly": net_monthly,
                "runway_months": round(runway_months, 1),
                "forecast": forecast,
            },
        )

    def _unit_economics(self, **kwargs: Any) -> SkillResult:
        cac = kwargs.get("cac", 0)
        ltv = kwargs.get("ltv", 0)
        margin = kwargs.get("margin", 0)

        ltv_cac_ratio = ltv / cac if cac > 0 else 0
        healthy = ltv_cac_ratio >= 3.0

        return SkillResult(
            success=True,
            output={
                "cac": cac,
                "ltv": ltv,
                "margin_pct": margin,
                "ltv_cac_ratio": round(ltv_cac_ratio, 2),
                "healthy": healthy,
                "recommendation": (
                    "Unit economics healthy"
                    if healthy
                    else f"LTV:CAC ratio {ltv_cac_ratio:.1f} below 3.0 threshold"
                ),
            },
        )

    def _cashflow_analysis(self, **kwargs: Any) -> SkillResult:
        inflows = kwargs.get("inflows", [])
        outflows = kwargs.get("outflows", [])
        total_in = sum(i.get("amount", 0) for i in inflows)
        total_out = sum(o.get("amount", 0) for o in outflows)

        return SkillResult(
            success=True,
            output={
                "total_inflows": total_in,
                "total_outflows": total_out,
                "net_cashflow": total_in - total_out,
                "cash_positive": total_in > total_out,
            },
        )

    def _payment_processing(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            success=True,
            output={
                "status": "pending_approval",
                "amount": kwargs.get("amount", 0),
                "recipient": kwargs.get("recipient", ""),
                "description": kwargs.get("description", ""),
                "note": "Payment queued for human approval (COMMIT tier)",
            },
        )

    def _invoice_draft(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            success=True,
            output={
                "status": "draft",
                "client": kwargs.get("client", ""),
                "amount": kwargs.get("amount", 0),
                "line_items": kwargs.get("line_items", []),
                "note": "Invoice drafted — requires review before sending",
            },
        )


async def register_finance_agent(substrate: Substrate) -> RegistrationResult:
    agent = FinanceAgent()
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-finance",
        capabilities=[
            "expense_tracking",
            "revenue_monitoring",
            "budget_forecasting",
            "unit_economics",
            "cashflow_analysis",
            "payment_processing",
            "invoice_drafting",
        ],
        metadata=agent.metadata(),
    )
    return await substrate.register(component)
