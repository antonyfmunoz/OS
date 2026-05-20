#!/usr/bin/env python3
"""Smoke test — creates a [UMH-TEST] page in a real Notion database.

Usage:
    NOTION_API_KEY=... python3 scripts/smoke_notion.py <database_id>

The database_id can be a UUID or a logical name from NOTION_*_DB env vars.
Creates a page with [UMH-TEST] prefix, prints the result, then exits.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from pathlib import Path
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

from services.umh.integrations.notion.auth import discover_database_ids, get_notion_client
from services.umh.integrations.notion.transforms import (
    build_create_page_payload,
    extract_create_page_result,
)


def main() -> None:
    if len(sys.argv) < 2:
        databases = discover_database_ids()
        print("Available databases:")
        for name, uid in sorted(databases.items()):
            print(f"  {name} → {uid}")
        print(f"\nUsage: python3 {sys.argv[0]} <database_id_or_logical_name>")
        sys.exit(1)

    raw_db_id = sys.argv[1]

    if "-" not in raw_db_id or len(raw_db_id) < 32:
        databases = discover_database_ids()
        resolved = databases.get(raw_db_id)
        if not resolved:
            print(f"ERROR: unknown logical name '{raw_db_id}'")
            print("Known names:", ", ".join(sorted(databases.keys())))
            sys.exit(1)
        print(f"Resolved '{raw_db_id}' → {resolved}")
        db_id = resolved
    else:
        db_id = raw_db_id

    client = get_notion_client()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    title = f"[UMH-TEST] Smoke test {timestamp}"

    payload = build_create_page_payload(db_id, title)
    print(f"Creating page: {title}")
    print(f"Database: {db_id}")

    try:
        response = client.pages.create(**payload)
        result = extract_create_page_result(response)
        print(f"\nSUCCESS")
        print(f"  page_id: {result['page_id']}")
        print(f"  url:     {result['url']}")
    except Exception as exc:
        print(f"\nFAILED: {type(exc).__name__}: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
