#!/usr/bin/env python3
"""Smoke test — exercises EOS integration polling against a real EOS database.

Usage:
    EOS_DATABASE_URL=<url> python3 scripts/smoke_eos.py
    EOS_DATABASE_URL=<url> EOS_ORG_IDS=<org_id> python3 scripts/smoke_eos.py

Steps:
1. Connect to EOS database.
2. Discover orgs (or use EOS_ORG_IDS whitelist).
3. Insert a [UMH-TEST] event in the first org.
4. Instantiate EOSPoller with short poll interval.
5. Wait one poll cycle.
6. Verify signal was submitted with correct org_id.
7. Clean up test event.
"""

from __future__ import annotations

import os
import sys
import time
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
from services.umh.integrations.eos.correlation import EOSCorrelationMap
from services.umh.integrations.eos.poller import EOSPoller
from services.umh.integrations.eos.signals import EOSSignalEmitter
from services.umh.integrations.eos.tables import fetch_org_ids, insert_test_event
from services.umh.integrations.notion.watermarks import WatermarkStore

MARKER = "[UMH-TEST]"


def _ok(msg: str) -> None:
    print(f"  OK  {msg}")


def _fail(msg: str) -> None:
    print(f"  FAIL  {msg}")
    sys.exit(1)


def main() -> None:
    database_url = os.getenv("EOS_DATABASE_URL", "")
    if not database_url:
        _fail("EOS_DATABASE_URL not set")

    print("=== EOS Smoke Test ===")

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
    org_ids_raw = os.getenv("EOS_ORG_IDS", "").strip()
    if org_ids_raw:
        org_ids = [oid.strip() for oid in org_ids_raw.split(",") if oid.strip()]
        _ok(f"using whitelist: {org_ids}")
    else:
        org_ids = fetch_org_ids(conn)
        if not org_ids:
            _fail("no organizations found in EOS database")
        _ok(f"found {len(org_ids)} org(s): {org_ids[:5]}")

    test_org = org_ids[0]
    print(f"   using org: {test_org}")

    # 3. Insert test event
    print("\n3. Inserting [UMH-TEST] event...")
    try:
        test_event_id = insert_test_event(
            conn,
            org_id=test_org,
            event_type="umh_smoke_test",
            payload={"marker": MARKER, "smoke_run": str(uuid4())[:8]},
        )
        _ok(f"event_id={test_event_id}")
    except Exception as exc:
        _fail(f"insert failed: {exc}")

    # 4. Set up poller with short cycle
    print("\n4. Setting up poller...")
    correlation_map = EOSCorrelationMap()
    emitter = EOSSignalEmitter()
    submitted: list[dict] = []

    def capture_submit(content, **kwargs):
        submitted.append({"content": content, **kwargs})

        class FakeResult:
            signal_id = uuid4()
            trace_id = uuid4()
            outcome_type = "success"

        return FakeResult()

    import tempfile
    wm_path = Path(tempfile.mkdtemp()) / "smoke_eos_wm.jsonl"

    poller = EOSPoller(
        database_url=database_url,
        correlation_map=correlation_map,
        signal_emitter=emitter,
        pipeline_submit_fn=capture_submit,
        outcome_receiver=None,
        tables=["events"],
        org_ids=[test_org],
        poll_interval=2.0,
        watermark_store=WatermarkStore(path=wm_path),
    )

    # 5. Run one poll cycle
    print("\n5. Running poll cycle...")
    try:
        poll_conn = psycopg2.connect(database_url)
        poll_conn.autocommit = True
        poller._conn = poll_conn
        for table in poller._tables:
            poller._poll_table_org(poll_conn, table, test_org)
        _ok(f"poll complete, {len(submitted)} signal(s) submitted")
    except Exception as exc:
        _fail(f"poll failed: {exc}")

    # 6. Verify signal
    print("\n6. Verifying signal...")
    test_signals = [s for s in submitted if MARKER in str(s)]
    if not test_signals:
        all_signals = [s for s in submitted if "umh_smoke_test" in str(s)]
        if all_signals:
            test_signals = all_signals

    if not test_signals:
        _fail(f"no signal with marker found. total submitted: {len(submitted)}")

    sig = test_signals[-1]
    params = sig.get("params", {})
    if params.get("org_id") != test_org:
        _fail(f"org_id mismatch: expected {test_org}, got {params.get('org_id')}")

    _ok(f"signal found: org_id={params.get('org_id')}, event_type={params.get('event_type')}")

    # 7. Clean up test event
    print("\n7. Cleaning up test event...")
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events WHERE id = %s", (test_event_id,))
        _ok(f"deleted event {test_event_id}")
    except Exception as exc:
        print(f"  WARN  cleanup failed (non-fatal): {exc}")

    conn.close()
    poll_conn.close()

    print("\n=== EOS Smoke Test PASSED ===")


if __name__ == "__main__":
    main()
