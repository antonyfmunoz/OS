"""KPI view — projects business metrics into founder-facing KPI cards."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class KPICard:
    name: str
    value: float | str
    unit: str = ""
    trend: str = ""
    period: str = "month"


@dataclass
class KPIDashboard:
    cards: list[KPICard] = field(default_factory=list)
    venture_id: str = ""


class KPIView:
    """Projects business metrics into a KPI dashboard."""

    def __init__(self, org_id: str = "", venture_id: str = "") -> None:
        self._org_id = org_id
        self._venture_id = venture_id

    def dashboard(self) -> KPIDashboard:
        """Build KPI dashboard from current business data."""
        cards = [
            self._revenue_card(),
            self._lead_count_card(),
            self._conversion_card(),
            self._outreach_card(),
            self._response_rate_card(),
        ]
        return KPIDashboard(
            cards=[c for c in cards if c is not None],
            venture_id=self._venture_id,
        )

    def _revenue_card(self) -> KPICard | None:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT COALESCE(SUM((payload_json->>'amount')::numeric), 0) AS total
                    FROM events
                    WHERE org_id = %s AND event_type = 'revenue'
                    AND created_at >= date_trunc('month', NOW())
                    """,
                    (self._org_id,),
                )
                row = cur.fetchone()
                return KPICard(name="Monthly Revenue", value=float(row["total"] or 0), unit="$")
        except Exception:
            return KPICard(name="Monthly Revenue", value=0, unit="$")

    def _lead_count_card(self) -> KPICard:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt FROM events
                    WHERE org_id = %s AND event_type = 'crm_lead'
                    AND created_at >= date_trunc('month', NOW())
                    """,
                    (self._org_id,),
                )
                row = cur.fetchone()
                return KPICard(name="Leads This Month", value=int(row["cnt"] or 0))
        except Exception:
            return KPICard(name="Leads This Month", value=0)

    def _conversion_card(self) -> KPICard:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE payload_json->>'stage' = 'closed') AS closed
                    FROM events
                    WHERE org_id = %s AND event_type = 'crm_lead'
                    """,
                    (self._org_id,),
                )
                row = cur.fetchone()
                total = int(row["total"] or 0)
                closed = int(row["closed"] or 0)
                rate = (closed / total * 100) if total > 0 else 0
                return KPICard(name="Conversion Rate", value=round(rate, 1), unit="%")
        except Exception:
            return KPICard(name="Conversion Rate", value=0, unit="%")

    def _outreach_card(self) -> KPICard:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt FROM events
                    WHERE org_id = %s AND event_type = 'outreach'
                    AND created_at >= date_trunc('week', NOW())
                    """,
                    (self._org_id,),
                )
                row = cur.fetchone()
                return KPICard(name="Outreach This Week", value=int(row["cnt"] or 0), period="week")
        except Exception:
            return KPICard(name="Outreach This Week", value=0, period="week")

    def _response_rate_card(self) -> KPICard:
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE payload_json->>'responded' = 'true') AS responded
                    FROM events
                    WHERE org_id = %s AND event_type = 'outreach'
                    AND created_at >= date_trunc('month', NOW())
                    """,
                    (self._org_id,),
                )
                row = cur.fetchone()
                total = int(row["total"] or 0)
                responded = int(row["responded"] or 0)
                rate = (responded / total * 100) if total > 0 else 0
                return KPICard(name="Response Rate", value=round(rate, 1), unit="%")
        except Exception:
            return KPICard(name="Response Rate", value=0, unit="%")
