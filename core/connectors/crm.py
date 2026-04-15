"""CRM Connector — ingest lead and pipeline status changes.

Supports:
- Lead status transitions
- Pipeline stage tracking
- Conversion metrics
- JSON/CSV file fallback for MVP

Metrics produced:
- leads_total, leads_qualified, leads_converted,
  conversion_rate, pipeline_value, stage_changes
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
)


class CrmConnector(Connector):
    """Ingest CRM / lead pipeline metrics."""

    name = "crm"

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
        if self._data_path:
            return self._data_path.exists()
        if self._api_endpoint:
            return bool(self._api_key)
        return False

    def fetch_signals(self) -> list[RealSignal]:
        raw_records: list[dict[str, Any]] = []

        if self._data_path:
            suffix = self._data_path.suffix.lower()
            if suffix == ".json":
                raw_records = JsonFileAdapter.load(self._data_path)
            elif suffix == ".csv":
                raw_records = CsvFileAdapter.load(self._data_path)
            else:
                from core.connectors.base import LogFileAdapter

                raw_records = LogFileAdapter.load(self._data_path)
        elif self._api_endpoint:
            raw_records = self._fetch_from_api()

        signals = self.normalize(raw_records)
        self._mark_synced()
        return signals

    def normalize(self, raw: Any) -> list[RealSignal]:
        if not isinstance(raw, list):
            raw = [raw]

        signals: list[RealSignal] = []
        for record in raw:
            if not isinstance(record, dict):
                continue

            ts = float(record.get("timestamp", time.time()))
            entity = str(
                record.get(
                    "lead_id", record.get("deal_id", record.get("entity_id", ""))
                )
            )

            # Direct metric extraction
            metric_map = {
                "leads_total": ["leads_total", "total_leads", "lead_count"],
                "leads_qualified": ["leads_qualified", "qualified", "mqls", "sqls"],
                "leads_converted": [
                    "leads_converted",
                    "converted",
                    "conversions",
                    "won",
                ],
                "pipeline_value": ["pipeline_value", "deal_value", "revenue", "mrr"],
                "presentations": ["presentations", "demos", "calls_completed"],
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
                                    "stage": record.get("stage", ""),
                                    "source": record.get(
                                        "lead_source", record.get("source", "")
                                    ),
                                },
                            )
                        )
                        break

            # Stage change events
            if "from_stage" in record and "to_stage" in record:
                signals.append(
                    RealSignal(
                        source=self.name,
                        timestamp=ts,
                        metric_name="stage_change",
                        value=1.0,
                        entity_id=entity,
                        metadata={
                            "from_stage": record["from_stage"],
                            "to_stage": record["to_stage"],
                        },
                    )
                )

            # Compute conversion_rate if raw values present
            total = float(record.get("leads_total", record.get("total_leads", 0)))
            converted = float(record.get("leads_converted", record.get("converted", 0)))
            if total > 0 and converted > 0:
                signals.append(
                    RealSignal(
                        source=self.name,
                        timestamp=ts,
                        metric_name="conversion_rate",
                        value=converted / total,
                        entity_id=entity,
                    )
                )

        return signals

    def from_webhook(self, payload: dict[str, Any]) -> list[RealSignal]:
        events = WebhookPayloadAdapter.parse(payload)
        return self.normalize(events)

    def _fetch_from_api(self) -> list[dict[str, Any]]:
        return []


__all__ = ["CrmConnector"]
