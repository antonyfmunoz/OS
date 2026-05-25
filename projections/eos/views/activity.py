"""Activity view — projects recent system activity into a founder-facing feed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActivityEntry:
    event_type: str
    summary: str
    agent: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActivityFeed:
    entries: list[ActivityEntry] = field(default_factory=list)
    total_count: int = 0


class ActivityView:
    """Projects recent system events into a chronological activity feed."""

    def __init__(self, org_id: str = "") -> None:
        self._org_id = org_id

    def feed(self, limit: int = 30) -> ActivityFeed:
        """Build activity feed from recent events."""
        raw = self._fetch_events(limit)
        entries = []
        for event in raw:
            entries.append(
                ActivityEntry(
                    event_type=event.get("event_type", ""),
                    summary=self._summarize(event),
                    agent=event.get("agent", event.get("payload", {}).get("agent", "")),
                    timestamp=str(event.get("created_at", "")),
                    metadata=event.get("payload", {}),
                )
            )
        return ActivityFeed(entries=entries, total_count=len(entries))

    def _summarize(self, event: dict[str, Any]) -> str:
        """Generate a human-readable summary of an event."""
        etype = event.get("event_type", "")
        payload = event.get("payload", {})

        summaries = {
            "crm_lead": f"New lead: {payload.get('name', 'unknown')}",
            "outreach": f"Outreach sent to {payload.get('recipient', 'unknown')}",
            "revenue": f"Revenue: ${payload.get('amount', 0)}",
            "commitment": f"Commitment: {payload.get('text', '')[:60]}",
            "cognitive_reflection": f"Reflection: {payload.get('insight', '')[:60]}",
            "agent_task": f"Agent task: {payload.get('task', '')[:60]}",
        }
        return summaries.get(etype, f"{etype}: {str(payload)[:80]}")

    def _fetch_events(self, limit: int) -> list[dict[str, Any]]:
        try:
            from substrate import get_conn
            import json

            with get_conn(self._org_id) as cur:
                cur.execute(
                    """
                    SELECT event_type, payload_json, created_at
                    FROM events
                    WHERE org_id = %s
                    ORDER BY created_at DESC LIMIT %s
                    """,
                    (self._org_id, limit),
                )
                rows = cur.fetchall()
                results = []
                for r in rows:
                    payload = r["payload_json"]
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    results.append(
                        {
                            "event_type": r["event_type"],
                            "payload": payload,
                            "created_at": str(r["created_at"]),
                        }
                    )
                return results
        except Exception:
            return []
