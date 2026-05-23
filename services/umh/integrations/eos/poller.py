"""EOS poller — background thread that polls EOS Postgres tables for new rows."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable
from uuid import uuid4

import psycopg2

from services.umh.governance.risk_classes import RiskClass
from services.umh.integrations.notion.watermarks import WatermarkStore
from substrate.sockets.envelopes import OutcomeEnvelope

from .correlation import EOSCorrelationMap, EOSWritebackTarget
from .signals import EOSSignalEmitter
from .tables import (
    CrmActivityRow,
    CrmContactRow,
    CrmDealRow,
    fetch_activities_since,
    fetch_contacts_since,
    fetch_deals_since,
    fetch_user_ids,
)

logger = logging.getLogger(__name__)

_DEFAULT_WATERMARK = "2000-01-01T00:00:00+00:00"


class EOSPoller:
    """Polls EOS Postgres tables for new rows on a background thread.

    For each configured table x each in-scope user:
    1. Load watermark (created_at high-water mark) keyed on (table, user_id)
    2. Query rows with created_at > watermark, sorted ascending, LIMIT 100
    3. For each row: build signal -> register correlation -> submit to pipeline
    4. Advance watermark and persist to JSONL
    """

    def __init__(
        self,
        database_url: str,
        correlation_map: EOSCorrelationMap,
        signal_emitter: EOSSignalEmitter,
        pipeline_submit_fn: Callable[..., Any],
        outcome_receiver: Any,
        tables: list[str],
        user_ids: list[str] | None = None,
        poll_interval: float = 15.0,
        watermark_store: WatermarkStore | None = None,
        shutdown_event: threading.Event | None = None,
    ) -> None:
        self._database_url = database_url
        self._correlation_map = correlation_map
        self._emitter = signal_emitter
        self._submit_fn = pipeline_submit_fn
        self._outcome_receiver = outcome_receiver
        self._tables = tables
        self._user_ids_whitelist = user_ids or []
        self._poll_interval = poll_interval
        self._watermarks = watermark_store or WatermarkStore(
            path=self._default_watermark_path()
        )
        self.shutdown_event = shutdown_event or threading.Event()
        self._thread: threading.Thread | None = None
        self._conn: Any = None

    @staticmethod
    def _default_watermark_path():
        from pathlib import Path

        return Path(__file__).resolve().parent.parent.parent / "data" / "eos_watermarks.jsonl"

    @property
    def tables(self) -> list[str]:
        return list(self._tables)

    def start(self) -> threading.Thread:
        """Start the poller on a daemon thread. Returns the thread."""
        self._thread = threading.Thread(
            target=self._run_loop,
            name="eos-poller",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "eos poller started: tables=%s, user_whitelist=%s, interval=%.1fs",
            self._tables,
            self._user_ids_whitelist or "all",
            self._poll_interval,
        )
        return self._thread

    def _get_connection(self) -> Any:
        if self._conn is not None:
            try:
                with self._conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return self._conn
            except Exception:
                self._close_connection()

        try:
            self._conn = psycopg2.connect(self._database_url)
            self._conn.autocommit = True
            return self._conn
        except Exception as exc:
            logger.error("eos poller: connection failed: %s", exc)
            raise

    def _close_connection(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def _resolve_user_ids(self, conn: Any) -> list[str]:
        """Return user IDs to poll: whitelist if set, otherwise discover all."""
        if self._user_ids_whitelist:
            return list(self._user_ids_whitelist)
        return fetch_user_ids(conn)

    def _run_loop(self) -> None:
        while not self.shutdown_event.is_set():
            try:
                conn = self._get_connection()
                user_ids = self._resolve_user_ids(conn)

                for table_name in self._tables:
                    if self.shutdown_event.is_set():
                        break
                    for user_id in user_ids:
                        if self.shutdown_event.is_set():
                            break
                        try:
                            self._poll_table_user(conn, table_name, user_id)
                        except Exception as exc:
                            logger.error(
                                "eos poller error for %s/%s: %s: %s",
                                table_name,
                                user_id,
                                type(exc).__name__,
                                exc,
                            )

            except Exception as exc:
                logger.error("eos poller connection error: %s: %s", type(exc).__name__, exc)
                self._close_connection()

            self.shutdown_event.wait(timeout=self._poll_interval)

        self._close_connection()

    def _watermark_key(self, table_name: str, user_id: str) -> str:
        return f"{table_name}:{user_id}"

    def _poll_table_user(self, conn: Any, table_name: str, user_id: str) -> None:
        """Poll a single (table, user) pair."""
        wm_key = self._watermark_key(table_name, user_id)
        watermark = self._watermarks.get_watermark(wm_key)

        if table_name == "crm_contacts":
            rows = fetch_contacts_since(conn, user_id, watermark)
        elif table_name == "crm_deals":
            rows = fetch_deals_since(conn, user_id, watermark)
        elif table_name == "crm_activities":
            rows = fetch_activities_since(conn, user_id, watermark)
        else:
            return

        if not rows:
            return

        logger.info(
            "eos poller: %d new rows in %s for user %s since %s",
            len(rows),
            table_name,
            user_id[:8],
            watermark,
        )

        latest_watermark = watermark
        for row in rows:
            if self.shutdown_event.is_set():
                break
            self._process_row(row, table_name)

            row_ts = row.created_at.isoformat()
            if row_ts > latest_watermark:
                latest_watermark = row_ts

        self._watermarks.record_watermark(wm_key, latest_watermark)

    def _process_row(
        self, row: CrmContactRow | CrmDealRow | CrmActivityRow, table_name: str
    ) -> None:
        """Build signal, register correlation, submit to pipeline."""
        if isinstance(row, CrmContactRow):
            envelope, writeback_target = self._emitter.build_contact_signal(row)
        elif isinstance(row, CrmDealRow):
            envelope, writeback_target = self._emitter.build_deal_signal(row)
        elif isinstance(row, CrmActivityRow):
            envelope, writeback_target = self._emitter.build_activity_signal(row)
        else:
            return

        if envelope.correlation_id:
            self._correlation_map.register(
                envelope.correlation_id,
                writeback_target,
            )

        content = envelope.raw_content or f"eos {table_name} signal"

        try:
            result = self._submit_fn(
                content,
                risk_class=RiskClass.READ_ONLY,
                adapter_name="eos",
                operation="noop",
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
                    integration_id="eos",
                    outcome_type=result.outcome_type,
                    summary=f"{result.outcome_type}: {content[:200]}",
                    correlation_id=envelope.correlation_id,
                )
                try:
                    self._outcome_receiver.on_outcome(outcome_envelope)
                except Exception as exc:
                    logger.error("eos poller outcome dispatch failed: %s", exc)

        except Exception as exc:
            logger.error(
                "eos poller submit failed for %s row %s: %s: %s",
                table_name,
                row.id[:8],
                type(exc).__name__,
                exc,
            )
