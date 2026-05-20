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
