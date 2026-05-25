"""Pipeline view — projects CRM/sales data into a founder-facing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineStage:
    name: str
    count: int = 0
    total_value: float = 0.0
    leads: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PipelineSnapshot:
    stages: list[PipelineStage] = field(default_factory=list)
    total_leads: int = 0
    total_value: float = 0.0
    conversion_rate: float = 0.0


class PipelineView:
    """Projects lead/prospect data into a visual pipeline."""

    STAGES = ["prospect", "contacted", "qualified", "proposal", "negotiation", "closed"]

    def __init__(self, org_id: str = "") -> None:
        self._org_id = org_id

    def snapshot(self) -> PipelineSnapshot:
        """Build a pipeline snapshot from current CRM data."""
        raw_leads = self._fetch_leads()
        stages = []
        for stage_name in self.STAGES:
            stage_leads = [l for l in raw_leads if l.get("stage") == stage_name]
            stages.append(
                PipelineStage(
                    name=stage_name,
                    count=len(stage_leads),
                    total_value=sum(l.get("value", 0) for l in stage_leads),
                    leads=stage_leads[:10],
                )
            )

        total = len(raw_leads)
        closed = sum(1 for l in raw_leads if l.get("stage") == "closed")
        return PipelineSnapshot(
            stages=stages,
            total_leads=total,
            total_value=sum(s.total_value for s in stages),
            conversion_rate=closed / max(total, 1),
        )

    def _fetch_leads(self) -> list[dict[str, Any]]:
        """Fetch leads from the CRM store."""
        try:
            from substrate import get_conn

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json FROM events
                    WHERE org_id = %s AND event_type = 'crm_lead'
                    ORDER BY created_at DESC LIMIT 200
                    """,
                    (self._org_id,),
                )
                rows = cur.fetchall()
                import json

                return [
                    json.loads(r["payload_json"])
                    if isinstance(r["payload_json"], str)
                    else r["payload_json"]
                    for r in rows
                ]
        except Exception:
            return []
