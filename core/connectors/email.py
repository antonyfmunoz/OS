"""Email / DM Connector — ingest outreach reply metrics.

Supports:
- Live API integration (when available)
- JSON/CSV file fallback for MVP
- Webhook payload parsing

Metrics produced:
- sent, replies, bounces, open_rate, reply_rate
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from core.connectors.base import (
    Connector,
    CsvFileAdapter,
    JsonFileAdapter,
    RealSignal,
    WebhookPayloadAdapter,
    dict_to_signal,
)


class EmailConnector(Connector):
    """Ingest email/DM outreach metrics."""

    name = "email"

    def __init__(
        self,
        *,
        data_path: str | Path | None = None,
        api_endpoint: str | None = None,
        api_key: str | None = None,
    ) -> None:
        super().__init__()
        self._data_path = Path(data_path) if data_path else None
        self._api_endpoint = api_endpoint
        self._api_key = api_key

    def healthcheck(self) -> bool:
        """Check if data source is available."""
        if self._data_path:
            return self._data_path.exists()
        if self._api_endpoint:
            # Future: HTTP HEAD check
            return bool(self._api_key)
        return False

    def fetch_signals(self) -> list[RealSignal]:
        """Pull email metrics from configured source."""
        raw_records: list[dict[str, Any]] = []

        if self._data_path:
            suffix = self._data_path.suffix.lower()
            if suffix == ".json":
                raw_records = JsonFileAdapter.load(self._data_path)
            elif suffix == ".csv":
                raw_records = CsvFileAdapter.load(self._data_path)
            else:
                # Try JSON lines
                from core.connectors.base import LogFileAdapter

                raw_records = LogFileAdapter.load(self._data_path)
        elif self._api_endpoint:
            raw_records = self._fetch_from_api()

        signals = self.normalize(raw_records)
        self._mark_synced()
        return signals

    def normalize(self, raw: Any) -> list[RealSignal]:
        """Convert raw email records to RealSignal list."""
        if not isinstance(raw, list):
            raw = [raw]

        signals: list[RealSignal] = []
        for record in raw:
            if not isinstance(record, dict):
                continue

            ts = float(record.get("timestamp", time.time()))
            entity = str(record.get("campaign_id", record.get("entity_id", "")))

            # Extract known email metrics
            metric_map = {
                "sent": ["sent", "emails_sent", "messages_sent"],
                "replies": ["replies", "reply_count", "responses"],
                "bounces": ["bounces", "bounce_count"],
                "opens": ["opens", "open_count"],
                "meetings_booked": ["meetings_booked", "meetings", "calls_booked"],
            }

            for metric_name, keys in metric_map.items():
                for key in keys:
                    if key in record:
                        signals.append(
                            RealSignal(
                                source=self.name,
                                timestamp=ts,
                                metric_name=metric_name,
                                value=float(record[key]),
                                entity_id=entity,
                                metadata={
                                    k: v
                                    for k, v in record.items()
                                    if k
                                    not in {"timestamp", "campaign_id", "entity_id"}
                                    and k not in keys
                                },
                            )
                        )
                        break  # first matching key wins

            # Compute derived metrics if raw values present
            sent = float(record.get("sent", record.get("emails_sent", 0)))
            replies = float(record.get("replies", record.get("reply_count", 0)))
            opens = float(record.get("opens", record.get("open_count", 0)))

            if sent > 0:
                if replies:
                    signals.append(
                        RealSignal(
                            source=self.name,
                            timestamp=ts,
                            metric_name="reply_rate",
                            value=replies / sent,
                            entity_id=entity,
                        )
                    )
                if opens:
                    signals.append(
                        RealSignal(
                            source=self.name,
                            timestamp=ts,
                            metric_name="open_rate",
                            value=opens / sent,
                            entity_id=entity,
                        )
                    )

        return signals

    def from_webhook(self, payload: dict[str, Any]) -> list[RealSignal]:
        """Parse a webhook payload into email signals."""
        events = WebhookPayloadAdapter.parse(payload)
        return self.normalize(events)

    def _fetch_from_api(self) -> list[dict[str, Any]]:
        """Fetch from live API. Stub for future integration."""
        # Future: HTTP GET to self._api_endpoint with self._api_key
        return []


__all__ = ["EmailConnector"]
