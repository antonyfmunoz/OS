#!/usr/bin/env python3
"""Smoke test — exercises EOS Phase 3 outcome writeback against a real database.

Usage:
    EOS_DATABASE_URL=<url> python3 scripts/smoke_eos_phase3.py

Steps:
1. Connect to EOS database.
2. Discover orgs.
3. Insert a test event as source row (simulating poll-originated signal).
4. Register correlation_id → source row in EOSCorrelationMap.
5. Build an OutcomeEnvelope and dispatch through EOSOutcomeReceiver.
6. Verify umh_status on source event row updated to 'success'.
7. Verify umh_outcomes audit row inserted with matching trace_id.
8. Clean up both rows.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

_repo_root = Path(__file__).resolve().parent.parent
_env_candidates = [
    _repo_root / "services" / ".env",
    Path("/opt/OS/services/.env"),
]
for _env in _env_candidates:
    if _env.exists():
        load_dotenv(_env)
        break

sys.path.insert(0, str(_repo_root))

import psycopg2
from services.umh.integrations.eos.correlation import EOSCorrelationMap, EOSWritebackTarget
from services.umh.integrations.eos.outcomes import EOSOutcomeReceiver
from services.umh.integrations.eos.tables import fetch_org_ids
from substrate.sockets.envelopes import OutcomeEnvelope


def _ok(msg: str) -> None:
    print(f"  OK  {msg}")


def _fail(msg: str) -> None:
    print(f"  FAIL  {msg}")
    sys.exit(1)


def main() -> None:
    database_url = os.getenv("EOS_DATABASE_URL", "")
    if not database_url:
        _fail("EOS_DATABASE_URL not set")

    print("=== EOS Phase 3 Smoke Test (Outcome Writeback) ===")

    # 1. Connect
    print("\n1. Connecting to EOS database...")
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        _ok("connected")
    except Exception as exc:
        _fail(f"connection failed: {exc}")

    # 2. Discover orgs
    print("\n2. Discovering organizations...")
    org_ids = fetch_org_ids(conn)
    if not org_ids:
        _fail("no organizations found in EOS database")
    test_org = org_ids[0]
    _ok(f"using org: {test_org}")

    # 3. Insert test event as source row
    print("\n3. Inserting source event row...")
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO events (org_id, event_type, payload_json) "
            "VALUES (%s, %s, %s) RETURNING id",
            (test_org, "umh_smoke_test.phase3", '{"marker": "[UMH-PHASE3-TEST]"}'),
        )
        event_id = str(cur.fetchone()[0])
    _ok(f"event_id={event_id}")

    # 4. Register correlation
    print("\n4. Registering correlation mapping...")
    correlation_id = uuid4()
    trace_id = uuid4()
    signal_id = uuid4()

    cmap = EOSCorrelationMap()
    cmap.register(
        correlation_id,
        EOSWritebackTarget(
            org_id=test_org,
            table_name="events",
            row_id=event_id,
        ),
    )
    _ok(f"correlation_id={correlation_id} → events.{event_id}")

    # 5. Dispatch outcome through receiver
    print("\n5. Dispatching outcome through EOSOutcomeReceiver...")
    receiver = EOSOutcomeReceiver(
        database_url=database_url,
        correlation_map=cmap,
    )

    envelope = OutcomeEnvelope(
        outcome_id=uuid4(),
        signal_id=signal_id,
        trace_id=trace_id,
        integration_id="eos",
        outcome_type="success",
        summary="smoke test phase 3: outcome writeback verified",
        result_data={"event_id": event_id},
        correlation_id=correlation_id,
    )

    try:
        receiver.on_outcome(envelope)
        _ok("outcome dispatched")
    except Exception as exc:
        _fail(f"outcome dispatch failed: {exc}")

    # 6. Verify source row updated
    print("\n6. Verifying umh_status on source event row...")
    with conn.cursor() as cur:
        cur.execute("SELECT umh_status FROM events WHERE id = %s", (event_id,))
        row = cur.fetchone()
        if row is None:
            _fail("source event row not found")
        if row[0] != "success":
            _fail(f"umh_status expected 'success', got '{row[0]}'")
    _ok(f"events.{event_id}.umh_status = 'success'")

    # 7. Verify audit row
    print("\n7. Verifying umh_outcomes audit row...")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT outcome_type, source_table, source_row_id, severity, payload "
            "FROM umh_outcomes WHERE trace_id = %s",
            (str(trace_id),),
        )
        audit_row = cur.fetchone()
        if audit_row is None:
            _fail("umh_outcomes audit row not found")
        if audit_row[0] != "success":
            _fail(f"audit outcome_type expected 'success', got '{audit_row[0]}'")
        if audit_row[1] != "events":
            _fail(f"audit source_table expected 'events', got '{audit_row[1]}'")
        if str(audit_row[2]) != event_id:
            _fail(f"audit source_row_id mismatch: expected {event_id}, got {audit_row[2]}")
        if audit_row[3] != 0:
            _fail(f"audit severity expected 0, got {audit_row[3]}")
    _ok(f"umh_outcomes row found: type=success, source=events.{event_id}")

    # 8. Verify correlation cleaned up
    print("\n8. Verifying correlation map cleanup...")
    if cmap.lookup(correlation_id) is not None:
        _fail("correlation_id still in map after outcome delivery")
    _ok("correlation_id removed from map")

    # 9. Cleanup
    print("\n9. Cleaning up test data...")
    with conn.cursor() as cur:
        cur.execute("DELETE FROM umh_outcomes WHERE trace_id = %s", (str(trace_id),))
        cur.execute("DELETE FROM events WHERE id = %s", (event_id,))
    _ok(f"deleted event {event_id} and audit row")

    conn.close()

    print("\n=== EOS Phase 3 Smoke Test PASSED ===")


if __name__ == "__main__":
    main()
