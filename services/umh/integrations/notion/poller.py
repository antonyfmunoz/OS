"""Notion poller — background thread that polls databases for changes."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable
from uuid import uuid4

from notion_client import APIResponseError, Client

from services.umh.governance.risk_classes import RiskClass
from services.umh.integrations.notion.correlation import CorrelationMap, WritebackTarget
from services.umh.integrations.notion.signals import NotionSignalEmitter
from services.umh.integrations.notion.watermarks import WatermarkStore
from substrate.sockets.envelopes import OutcomeEnvelope

logger = logging.getLogger(__name__)

_RETRY_STATUS = 429
_RETRY_BACKOFF_SECONDS = 2.0


class NotionPoller:
    """Polls configured Notion databases for page changes on a background thread.

    For each signal source:
    1. Load watermark (last_edited_time high-water mark)
    2. Query Notion for pages edited after watermark (ascending)
    3. For each page: build signal → register correlation → submit to pipeline
    4. Advance watermark and persist to JSONL
    """

    def __init__(
        self,
        client: Client,
        correlation_map: CorrelationMap,
        signal_emitter: NotionSignalEmitter,
        pipeline_submit_fn: Callable[..., Any],
        outcome_receiver: Any,
        signal_sources: list[dict[str, Any]],
        watermark_store: WatermarkStore | None = None,
        shutdown_event: threading.Event | None = None,
    ) -> None:
        self._client = client
        self._correlation_map = correlation_map
        self._emitter = signal_emitter
        self._submit_fn = pipeline_submit_fn
        self._outcome_receiver = outcome_receiver
        self._signal_sources = signal_sources
        self._watermarks = watermark_store or WatermarkStore()
        self.shutdown_event = shutdown_event or threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def signal_sources(self) -> list[dict[str, Any]]:
        return list(self._signal_sources)

    def start(self) -> threading.Thread:
        """Start the poller on a daemon thread. Returns the thread."""
        self._thread = threading.Thread(
            target=self._run_loop,
            name="notion-poller",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "notion poller started: %d signal source(s)",
            len(self._signal_sources),
        )
        return self._thread

    def _run_loop(self) -> None:
        while not self.shutdown_event.is_set():
            for source in self._signal_sources:
                if self.shutdown_event.is_set():
                    break
                try:
                    self._poll_source(source)
                except Exception as exc:
                    logger.error(
                        "notion poller error for %s: %s: %s",
                        source.get("logical_name", "?"),
                        type(exc).__name__,
                        exc,
                    )

            poll_interval = 30.0
            if self._signal_sources:
                poll_interval = self._signal_sources[0].get("poll_interval", 30.0)
            self.shutdown_event.wait(timeout=poll_interval)

    def _poll_source(self, source: dict[str, Any]) -> None:
        db_id = source["database_id"]
        logical_name = source.get("logical_name", db_id)

        watermark = self._watermarks.get_watermark(db_id)

        pages = self._query_pages_since(db_id, watermark)
        if not pages:
            return

        logger.info(
            "notion poller: %d new/updated pages in %s since %s",
            len(pages),
            logical_name,
            watermark,
        )

        for page in pages:
            if self.shutdown_event.is_set():
                break
            self._process_page(page, source)

            page_edited = page.get("last_edited_time", watermark)
            if page_edited > watermark:
                watermark = page_edited

        self._watermarks.record_watermark(db_id, watermark)

    def _query_pages_since(self, database_id: str, watermark: str) -> list[dict[str, Any]]:
        """Query Notion for pages with last_edited_time > watermark, sorted ascending."""
        body: dict[str, Any] = {
            "filter": {
                "timestamp": "last_edited_time",
                "last_edited_time": {"after": watermark},
            },
            "sorts": [{"timestamp": "last_edited_time", "direction": "ascending"}],
            "page_size": 100,
        }

        try:
            return self._do_query(database_id, body)
        except APIResponseError as exc:
            if exc.status == _RETRY_STATUS:
                logger.warning("notion poller 429 — retrying in %.1fs", _RETRY_BACKOFF_SECONDS)
                time.sleep(_RETRY_BACKOFF_SECONDS)
                return self._do_query(database_id, body)
            raise

    def _do_query(self, database_id: str, body: dict[str, Any]) -> list[dict[str, Any]]:
        response = self._client.request(
            path=f"databases/{database_id}/query",
            method="POST",
            body=body,
        )
        results = response.get("results", [])

        while response.get("has_more") and response.get("next_cursor"):
            body["start_cursor"] = response["next_cursor"]
            response = self._client.request(
                path=f"databases/{database_id}/query",
                method="POST",
                body=body,
            )
            results.extend(response.get("results", []))

        return results

    def _process_page(self, page: dict[str, Any], source: dict[str, Any]) -> None:
        envelope, writeback_to = self._emitter.build_signal(page, source)

        if envelope.correlation_id:
            self._correlation_map.register(
                envelope.correlation_id,
                WritebackTarget(
                    page_id=writeback_to["page_id"],
                    integration=writeback_to["integration"],
                ),
            )

        operation = source.get("operation", "noop")
        adapter_name = envelope.payload.get("adapter_name", "notion")
        content = envelope.raw_content or "notion signal"

        try:
            result = self._submit_fn(
                content,
                risk_class=RiskClass.READ_ONLY,
                adapter_name=adapter_name,
                operation=operation,
                params=envelope.payload,
                pre_approved=True,
            )

            if (
                envelope.correlation_id
                and self._outcome_receiver
                and hasattr(result, "outcome_type")
                and result.outcome_type
            ):
                outcome_envelope = OutcomeEnvelope(
                    outcome_id=uuid4(),
                    signal_id=result.signal_id,
                    trace_id=result.trace_id,
                    integration_id="notion",
                    outcome_type=result.outcome_type,
                    summary=f"{result.outcome_type}: {content[:200]}",
                    correlation_id=envelope.correlation_id,
                )
                try:
                    self._outcome_receiver.on_outcome(outcome_envelope)
                except Exception as exc:
                    logger.error("poller outcome writeback failed: %s", exc)

        except Exception as exc:
            logger.error(
                "notion poller submit failed for page %s: %s: %s",
                page.get("id", "?"),
                type(exc).__name__,
                exc,
            )
