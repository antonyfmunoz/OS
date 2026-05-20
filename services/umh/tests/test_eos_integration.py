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
