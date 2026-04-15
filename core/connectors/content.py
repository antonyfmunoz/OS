"""Content Connector — ingest content performance metrics.

Supports:
- Social media metrics (views, likes, comments, saves, shares)
- Audience growth (follower_delta)
- JSON/CSV file fallback for MVP

Metrics produced:
- impressions, engagements, likes, comments, saves, shares,
  follower_delta, engagement_rate
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


class ContentConnector(Connector):
    """Ingest content performance metrics."""

    name = "content"

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
                    "content_id", record.get("post_id", record.get("entity_id", ""))
                )
            )

            # Direct metric extraction
            metric_map = {
                "impressions": ["impressions", "views", "reach"],
                "engagements": ["engagements", "interactions", "engagement_count"],
                "likes": ["likes", "like_count", "hearts"],
                "comments": ["comments", "comment_count", "replies"],
                "saves": ["saves", "save_count", "bookmarks"],
                "shares": ["shares", "share_count", "reposts", "retweets"],
                "follower_delta": [
                    "follower_delta",
                    "new_followers",
                    "follower_change",
                ],
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
                                    "platform": record.get("platform", ""),
                                    "content_type": record.get(
                                        "content_type", record.get("type", "")
                                    ),
                                },
                            )
                        )
                        break

            # Compute engagement_rate if we have the raw values
            impressions = float(record.get("impressions", record.get("views", 0)))
            engagements = float(record.get("engagements", 0))

            # Sum engagement components if engagements not directly provided
            if not engagements:
                engagements = sum(
                    float(record.get(k, 0))
                    for k in ["likes", "comments", "saves", "shares"]
                )

            if impressions > 0 and engagements > 0:
                signals.append(
                    RealSignal(
                        source=self.name,
                        timestamp=ts,
                        metric_name="engagement_rate",
                        value=engagements / impressions,
                        entity_id=entity,
                        metadata={"platform": record.get("platform", "")},
                    )
                )

        return signals

    def from_webhook(self, payload: dict[str, Any]) -> list[RealSignal]:
        events = WebhookPayloadAdapter.parse(payload)
        return self.normalize(events)

    def _fetch_from_api(self) -> list[dict[str, Any]]:
        return []


__all__ = ["ContentConnector"]
