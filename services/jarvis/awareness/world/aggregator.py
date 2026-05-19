"""GlobalAwarenessAggregator — unified entry point for all awareness adapters."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from services.jarvis.awareness.world.schema import EventCategory, GlobalEvent
from services.jarvis.awareness.world import adapter_rss
from services.jarvis.awareness.world import adapter_weather
from services.jarvis.awareness.world import adapter_markets
from services.jarvis.awareness.world import adapter_crypto

logger = logging.getLogger(__name__)

ADAPTER_MAP = {
    EventCategory.NEWS: adapter_rss.fetch,
    EventCategory.WEATHER: adapter_weather.fetch,
    EventCategory.MARKETS: adapter_markets.fetch,
    EventCategory.CRYPTO: adapter_crypto.fetch,
}


class GlobalAwarenessAggregator:
    """Fetches events from all adapters and returns a normalized snapshot."""

    def __init__(
        self,
        categories: list[EventCategory] | None = None,
        max_workers: int = 4,
    ) -> None:
        self.categories = categories or list(EventCategory)
        self.max_workers = max_workers

    def fetch_all(self) -> list[GlobalEvent]:
        """Fetch from all configured adapters in parallel."""
        events: list[GlobalEvent] = []
        errors: dict[str, str] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(ADAPTER_MAP[cat]): cat for cat in self.categories if cat in ADAPTER_MAP
            }
            for future in as_completed(futures):
                cat = futures[future]
                try:
                    result = future.result()
                    events.extend(result)
                    logger.info("Adapter %s returned %d events", cat.value, len(result))
                except Exception as e:
                    errors[cat.value] = str(e)
                    logger.error("Adapter %s raised: %s", cat.value, e)

        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events

    def snapshot(self) -> dict[str, Any]:
        """Return cockpit-compatible JSON snapshot."""
        events = self.fetch_all()
        by_category: dict[str, list[dict[str, Any]]] = {}
        for event in events:
            cat = event.category.value
            by_category.setdefault(cat, []).append(event.to_dict())

        mock_count = sum(1 for e in events if e.metadata.get("mock"))
        live_count = len(events) - mock_count

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_events": len(events),
            "live_events": live_count,
            "mock_events": mock_count,
            "categories": {cat: len(evts) for cat, evts in by_category.items()},
            "events": by_category,
        }

    def snapshot_json(self, indent: int = 2) -> str:
        """Return snapshot as formatted JSON string."""
        return json.dumps(self.snapshot(), indent=indent, default=str)
