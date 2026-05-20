"""Integration tests for EOS — require real EOS database connection.

Skipped by default. To run:
    EOS_DATABASE_URL=<url> EOS_INTEGRATION_TEST=1 pytest services/umh/tests/test_eos_integration.py -v
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not (os.getenv("EOS_DATABASE_URL") and os.getenv("EOS_INTEGRATION_TEST") == "1"),
    reason="EOS_DATABASE_URL and EOS_INTEGRATION_TEST=1 required",
)


@pytest.fixture()
def eos_conn():
    """Create a real psycopg2 connection to the EOS database."""
    import psycopg2

    conn = psycopg2.connect(os.getenv("EOS_DATABASE_URL"))
    conn.autocommit = True
    yield conn
    conn.close()


class TestEOSSchemaAccess:
    def test_events_table_exists(self, eos_conn) -> None:
        with eos_conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'events')"
            )
            assert cur.fetchone()[0] is True

    def test_events_has_expected_columns(self, eos_conn) -> None:
        with eos_conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'events'
                ORDER BY ordinal_position
                """
            )
            columns = [row[0] for row in cur.fetchall()]
            for expected in ("id", "org_id", "event_type", "payload_json", "created_at"):
                assert expected in columns, f"Missing column: {expected}"

    def test_organizations_table_exists(self, eos_conn) -> None:
        with eos_conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organizations')"
            )
            assert cur.fetchone()[0] is True

    def test_fetch_org_ids(self, eos_conn) -> None:
        from services.umh.integrations.eos.tables import fetch_org_ids

        org_ids = fetch_org_ids(eos_conn)
        assert isinstance(org_ids, list)

    def test_fetch_events_since(self, eos_conn) -> None:
        from services.umh.integrations.eos.tables import fetch_events_since, fetch_org_ids

        org_ids = fetch_org_ids(eos_conn)
        if not org_ids:
            pytest.skip("No organizations in EOS database")
        rows = fetch_events_since(eos_conn, org_ids[0], "2000-01-01T00:00:00+00:00", limit=5)
        assert isinstance(rows, list)

    def test_idx_events_org_created_exists(self, eos_conn) -> None:
        with eos_conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = 'events' AND indexname = 'idx_events_org_created'
                )
                """
            )
            assert cur.fetchone()[0] is True, "idx_events_org_created index missing"


class TestPhase2SchemaAssertions:
    """Validate that EOS tables match the columns/types tables.py assumes for writes."""

    def _get_column_info(self, eos_conn, table_name: str) -> dict:
        """Return {column_name: {data_type, is_nullable, udt_name}} for a table."""
        with eos_conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable, udt_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
                """,
                (table_name,),
            )
            return {
                row[0]: {"data_type": row[1], "is_nullable": row[2], "udt_name": row[3]}
                for row in cur.fetchall()
            }

    def test_events_write_columns_match(self, eos_conn) -> None:
        cols = self._get_column_info(eos_conn, "events")
        assert "id" in cols
        assert cols["org_id"]["udt_name"] == "uuid"
        assert cols["org_id"]["is_nullable"] == "NO"
        assert cols["event_type"]["data_type"] == "text"
        assert cols["event_type"]["is_nullable"] == "NO"
        assert cols["payload_json"]["udt_name"] == "jsonb"
        assert cols["handled_by"]["is_nullable"] == "YES"

    def test_clients_schema_matches(self, eos_conn) -> None:
        cols = self._get_column_info(eos_conn, "clients")
        assert "id" in cols
        assert cols["org_id"]["data_type"] == "text"
        assert cols["org_id"]["is_nullable"] == "NO"
        assert cols["venture_id"]["data_type"] == "text"
        assert cols["venture_id"]["is_nullable"] == "NO"
        assert cols["name"]["data_type"] == "text"
        assert cols["name"]["is_nullable"] == "NO"
        assert cols["email"]["data_type"] == "text"
        assert cols["email"]["is_nullable"] == "NO"
        assert cols["phone"]["is_nullable"] == "YES"
        assert cols["status"]["is_nullable"] == "NO"
        assert cols["source"]["is_nullable"] == "NO"

    def test_ventures_schema_matches(self, eos_conn) -> None:
        cols = self._get_column_info(eos_conn, "ventures")
        assert "id" in cols
        assert cols["org_id"]["udt_name"] == "uuid"
        assert cols["org_id"]["is_nullable"] == "NO"
        assert cols["stage"]["udt_name"] == "venture_stage"
        assert cols["stage"]["is_nullable"] == "NO"
        assert cols["monthly_revenue"]["data_type"] == "numeric"
        assert cols["monthly_revenue"]["is_nullable"] == "NO"


class TestPhase3SchemaAssertions:
    """Validate Phase 3 outcome writeback schema — umh_status columns + umh_outcomes table."""

    def _get_column_info(self, eos_conn, table_name: str) -> dict:
        with eos_conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable, udt_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
                """,
                (table_name,),
            )
            return {
                row[0]: {"data_type": row[1], "is_nullable": row[2], "udt_name": row[3]}
                for row in cur.fetchall()
            }

    def test_events_umh_status_column(self, eos_conn) -> None:
        cols = self._get_column_info(eos_conn, "events")
        assert "umh_status" in cols, "events.umh_status column missing"
        assert cols["umh_status"]["data_type"] == "text"
        assert cols["umh_status"]["is_nullable"] == "YES"

    def test_clients_umh_status_column(self, eos_conn) -> None:
        cols = self._get_column_info(eos_conn, "clients")
        assert "umh_status" in cols, "clients.umh_status column missing"
        assert cols["umh_status"]["data_type"] == "text"
        assert cols["umh_status"]["is_nullable"] == "YES"

    def test_ventures_umh_status_column(self, eos_conn) -> None:
        cols = self._get_column_info(eos_conn, "ventures")
        assert "umh_status" in cols, "ventures.umh_status column missing"
        assert cols["umh_status"]["data_type"] == "text"
        assert cols["umh_status"]["is_nullable"] == "YES"

    def test_umh_outcomes_table_exists(self, eos_conn) -> None:
        with eos_conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'umh_outcomes')"
            )
            assert cur.fetchone()[0] is True, "umh_outcomes table missing"

    def test_umh_outcomes_schema_matches(self, eos_conn) -> None:
        cols = self._get_column_info(eos_conn, "umh_outcomes")
        assert cols["id"]["udt_name"] == "uuid"
        assert cols["id"]["is_nullable"] == "NO"
        assert cols["org_id"]["udt_name"] == "uuid"
        assert cols["org_id"]["is_nullable"] == "NO"
        assert cols["trace_id"]["data_type"] == "text"
        assert cols["trace_id"]["is_nullable"] == "NO"
        assert cols["source_table"]["data_type"] == "text"
        assert cols["source_table"]["is_nullable"] == "NO"
        assert cols["source_row_id"]["udt_name"] == "uuid"
        assert cols["source_row_id"]["is_nullable"] == "YES"
        assert cols["outcome_type"]["data_type"] == "text"
        assert cols["outcome_type"]["is_nullable"] == "NO"
        assert cols["severity"]["data_type"] == "integer"
        assert cols["severity"]["is_nullable"] == "NO"
        assert cols["payload"]["udt_name"] == "jsonb"
        assert cols["payload"]["is_nullable"] == "NO"
        assert cols["created_at"]["data_type"] == "timestamp with time zone"
        assert cols["created_at"]["is_nullable"] == "NO"

    def test_umh_outcomes_indexes_exist(self, eos_conn) -> None:
        with eos_conn.cursor() as cur:
            cur.execute(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'umh_outcomes'
                ORDER BY indexname
                """
            )
            indexes = {row[0] for row in cur.fetchall()}
            expected = {
                "idx_umh_outcomes_org_id",
                "idx_umh_outcomes_trace_id",
                "idx_umh_outcomes_source",
                "idx_umh_outcomes_org_created",
                "idx_umh_outcomes_type",
            }
            missing = expected - indexes
            assert not missing, f"Missing indexes: {missing}"

    def test_outcome_writeback_e2e(self, eos_conn) -> None:
        """End-to-end: insert a source event, write outcome back, verify both targets."""
        from uuid import uuid4

        from services.umh.integrations.eos.tables import (
            fetch_org_ids,
            insert_umh_outcome,
            update_umh_status,
        )

        org_ids = fetch_org_ids(eos_conn)
        if not org_ids:
            pytest.skip("No organizations in EOS database")
        org_id = org_ids[0]

        # Insert a test event as source row
        with eos_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO events (org_id, event_type, payload_json) VALUES (%s, %s, %s) RETURNING id",
                (org_id, "umh_test.phase3", '{"marker": "phase3-e2e"}'),
            )
            event_id = str(cur.fetchone()[0])
            eos_conn.commit()

        trace_id = str(uuid4())
        try:
            # Write success outcome to source row
            updated = update_umh_status(eos_conn, "events", event_id, "success")
            assert updated is True

            # Insert audit row
            audit_id = insert_umh_outcome(
                eos_conn,
                trace_id=trace_id,
                source_table="events",
                source_row_id=event_id,
                org_id=org_id,
                outcome_type="success",
                severity=0,
                payload={"summary": "phase3 e2e test"},
            )
            assert audit_id

            # Verify source row updated
            with eos_conn.cursor() as cur:
                cur.execute("SELECT umh_status FROM events WHERE id = %s", (event_id,))
                assert cur.fetchone()[0] == "success"

            # Verify audit row inserted
            with eos_conn.cursor() as cur:
                cur.execute(
                    "SELECT outcome_type, source_table, source_row_id FROM umh_outcomes WHERE id = %s",
                    (audit_id,),
                )
                audit_row = cur.fetchone()
                assert audit_row[0] == "success"
                assert audit_row[1] == "events"
                assert str(audit_row[2]) == event_id

        finally:
            # Cleanup
            with eos_conn.cursor() as cur:
                cur.execute("DELETE FROM umh_outcomes WHERE trace_id = %s", (trace_id,))
                cur.execute("DELETE FROM events WHERE id = %s", (event_id,))
                eos_conn.commit()
