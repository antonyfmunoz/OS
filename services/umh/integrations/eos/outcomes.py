"""EOS outcome receiver — writes pipeline outcomes back to EOS Postgres.

Phase 3: dual writeback (source row umh_status + umh_outcomes audit table).
Replaces the Phase 1 log-only stub.

Satisfies OutcomeReceiver Protocol structurally. Uses direct Postgres via
psycopg2 — writebacks are outcome side-effects, not new signals, so they
bypass governance reentry (same pattern as NotionOutcomeReceiver).
"""

from __future__ import annotations

import logging
from typing import Any

import psycopg2

from services.umh.sockets.envelopes import OutcomeEnvelope

from .correlation import EOSCorrelationMap
from .manifest import INTEGRATION_ID
from .tables import (
    SOURCE_ROW_UPDATE_TYPES,
    insert_umh_outcome,
    outcome_severity,
    update_umh_status,
)

logger = logging.getLogger(__name__)

_STATUS_MAP: dict[str, str] = {
    "success": "success",
    "failure": "error",
    "error": "error",
    "governance_denied": "governance_denied",
    "timeout": "timeout",
}


class EOSOutcomeReceiver:
    """Receives pipeline outcomes and writes them back to EOS Postgres.

    Dual writeback (Decision 1 = C):
    - Source row: UPDATE umh_status on events/clients/ventures (known-state outcomes only)
    - Audit table: INSERT into umh_outcomes (all outcomes)

    Severity ladder (Decision 5): source row umh_status only advances to
    higher severity, never retreats. Prevents success overwriting error
    when multiple capabilities target the same source row.

    Failure handling (Decision 4): error/failure outcomes write ONLY to
    the audit table — they do NOT update umh_status on the source row,
    because failed outcomes mean the source data may be in unknown state.
    """

    def __init__(
        self,
        database_url: str,
        correlation_map: EOSCorrelationMap,
    ) -> None:
        self._database_url = database_url
        self._correlation_map = correlation_map
        self._conn: Any = None

    @property
    def integration_id(self) -> str:
        return INTEGRATION_ID

    def on_outcome(self, envelope: OutcomeEnvelope) -> None:
        if envelope.correlation_id is None:
            logger.debug("eos outcome: no correlation_id, skipping writeback")
            return

        target = self._correlation_map.lookup(envelope.correlation_id)
        if target is None:
            logger.debug(
                "eos outcome: correlation_id %s not in map",
                envelope.correlation_id,
            )
            return

        if target.integration != "eos":
            logger.debug(
                "eos outcome: target integration is %s, not eos",
                target.integration,
            )
            return

        try:
            conn = self._get_connection()
            self._writeback(conn, target, envelope)
            self._correlation_map.remove(envelope.correlation_id)
        except psycopg2.Error as exc:
            logger.error(
                "eos writeback db error: %s for %s.%s",
                exc,
                target.table_name,
                target.row_id,
            )
            self._conn = None
        except Exception as exc:
            logger.error(
                "eos writeback failed: %s: %s for %s.%s",
                type(exc).__name__,
                exc,
                target.table_name,
                target.row_id,
            )

    def accepts_outcomes(self) -> list[str]:
        return []

    def _get_connection(self) -> Any:
        if self._conn is not None:
            try:
                with self._conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return self._conn
            except Exception:
                self._conn = None

        self._conn = psycopg2.connect(self._database_url)
        self._conn.autocommit = False
        return self._conn

    def _writeback(self, conn: Any, target: Any, envelope: OutcomeEnvelope) -> None:
        mapped_status = _STATUS_MAP.get(envelope.outcome_type, envelope.outcome_type)
        severity = outcome_severity(mapped_status)

        # Decision 4: only known-state outcomes update the source row
        if mapped_status in SOURCE_ROW_UPDATE_TYPES and target.row_id:
            try:
                updated = update_umh_status(
                    conn,
                    target.table_name,
                    target.row_id,
                    mapped_status,
                )
                if updated:
                    logger.info(
                        "eos writeback: %s.%s umh_status=%s",
                        target.table_name,
                        target.row_id,
                        mapped_status,
                    )
                else:
                    logger.debug(
                        "eos writeback: %s.%s umh_status not updated (higher severity already set)",
                        target.table_name,
                        target.row_id,
                    )
            except Exception as exc:
                logger.error(
                    "eos writeback source row update failed: %s for %s.%s",
                    exc,
                    target.table_name,
                    target.row_id,
                )

        # Always insert into audit table
        payload = _build_audit_payload(envelope)
        try:
            audit_id = insert_umh_outcome(
                conn,
                trace_id=str(envelope.trace_id),
                source_table=target.table_name,
                source_row_id=target.row_id,
                org_id=target.org_id,
                outcome_type=mapped_status,
                severity=severity,
                payload=payload,
            )
            logger.info(
                "eos writeback: umh_outcomes id=%s type=%s trace=%s",
                audit_id,
                mapped_status,
                envelope.trace_id,
            )
        except Exception as exc:
            logger.error(
                "eos writeback audit insert failed: %s for trace %s",
                exc,
                envelope.trace_id,
            )


def _build_audit_payload(envelope: OutcomeEnvelope) -> dict[str, Any]:
    """Build the jsonb payload for the umh_outcomes audit row."""
    payload: dict[str, Any] = {
        "signal_id": str(envelope.signal_id),
        "outcome_type": envelope.outcome_type,
        "summary": envelope.summary[:500] if envelope.summary else "",
        "confidence": envelope.confidence,
        "duration_ms": envelope.duration_ms,
    }
    if envelope.governance_decision:
        payload["governance_decision"] = envelope.governance_decision
    if envelope.result_data:
        payload["result_data"] = envelope.result_data
    if envelope.metadata:
        payload["metadata"] = envelope.metadata
    return payload
