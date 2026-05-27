"""Seed EOS watermarks to NOW — skip historical replay on next poller start.

Connects to EOS_DATABASE_URL, discovers all org_ids, writes a watermark entry
for each (table, org_id) combination with timestamp = now(UTC).

Usage:
    python3 scripts/seed_eos_watermarks_to_now.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import psycopg2
from dotenv import load_dotenv

load_dotenv("/opt/OS/services/.env")

import os

from projections.eos.integration.manifest import POLLED_TABLES
from projections.eos.integration.tables import fetch_org_ids
from adapters.notion.integration.watermarks import WatermarkStore

WATERMARK_PATH = Path("/opt/OS/services/umh/data/eos_watermarks.jsonl")


def main() -> None:
    database_url = os.getenv("EOS_DATABASE_URL", "").strip()
    if not database_url:
        print("ERROR: EOS_DATABASE_URL not set in services/.env")
        sys.exit(1)

    print(f"Connecting to EOS database...")
    conn = psycopg2.connect(database_url)
    try:
        org_ids = fetch_org_ids(conn)
        print(f"Discovered {len(org_ids)} org(s): {[oid[:8] + '...' for oid in org_ids]}")
    finally:
        conn.close()

    if not org_ids:
        print("ERROR: No orgs found in EOS database")
        sys.exit(1)

    now = datetime.now(timezone.utc).isoformat()
    store = WatermarkStore(path=WATERMARK_PATH)
    count = 0

    for table in POLLED_TABLES:
        for org_id in org_ids:
            key = f"{table}:{org_id}"
            store.record_watermark(key, now)
            count += 1
            print(f"  seeded {key} → {now}")

    print(f"\nSeeded {count} watermark(s) to {WATERMARK_PATH}")


if __name__ == "__main__":
    main()
