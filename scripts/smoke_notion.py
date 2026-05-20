#!/usr/bin/env python3
"""Smoke test — exercises Notion integration operations against a real workspace.

Usage:
    python3 scripts/smoke_notion.py <database_id>                    # create_page only (default)
    SMOKE_OPS="create,update,append,query" python3 scripts/smoke_notion.py <database_id>
    SMOKE_OPS="writeback" python3 scripts/smoke_notion.py <database_id>

The database_id can be a UUID or a logical name from NOTION_*_DB env vars.
Operations: create (default), update, append, query, writeback.
Set SMOKE_OPS to run multiple.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
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
    build_append_block_payload,
    build_create_page_payload,
    build_query_database_payload,
    build_update_page_payload,
    extract_append_block_result,
    extract_create_page_result,
    extract_query_database_result,
    extract_update_page_result,
)


def _resolve_db(raw: str) -> str:
    if "-" in raw and len(raw) >= 32:
        return raw
    databases = discover_database_ids()
    resolved = databases.get(raw)
    if not resolved:
        print(f"ERROR: unknown logical name '{raw}'")
        print("Known names:", ", ".join(sorted(databases.keys())))
        sys.exit(1)
    print(f"Resolved '{raw}' → {resolved}")
    return resolved


def smoke_create(client: object, db_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    title = f"[UMH-TEST] Smoke test {timestamp}"

    payload = build_create_page_payload(db_id, title)
    print(f"\n--- create_page ---")
    print(f"  title: {title}")
    print(f"  database: {db_id}")

    response = client.pages.create(**payload)  # type: ignore[union-attr]
    result = extract_create_page_result(response)
    print(f"  SUCCESS: page_id={result['page_id']} url={result['url']}")
    return result["page_id"]


def smoke_update(client: object, page_id: str) -> None:
    properties = {
        "Status": {"select": {"name": "In Progress"}},
    }
    payload = build_update_page_payload(page_id, properties)
    print(f"\n--- update_page ---")
    print(f"  page_id: {page_id}")
    print(f"  properties: Status → In Progress")

    response = client.pages.update(**payload)  # type: ignore[union-attr]
    result = extract_update_page_result(response)
    print(f"  SUCCESS: page_id={result['page_id']} updated={result['updated']}")


def smoke_append(client: object, page_id: str) -> None:
    children = [
        {
            "paragraph": {
                "rich_text": [
                    {
                        "text": {
                            "content": f"[UMH-TEST] Appended block at "
                            f"{datetime.now(timezone.utc).strftime('%H:%M:%SZ')}"
                        }
                    }
                ]
            }
        }
    ]
    payload = build_append_block_payload(page_id, children)
    print(f"\n--- append_block ---")
    print(f"  page_id: {page_id}")

    response = client.blocks.children.append(**payload)  # type: ignore[union-attr]
    result = extract_append_block_result(response)
    print(f"  SUCCESS: block_ids={result['block_ids']} count={result['count']}")


def smoke_query(client: object, db_id: str) -> None:
    payload = build_query_database_payload(db_id, page_size=5)
    print(f"\n--- query_database ---")
    print(f"  database: {db_id}")
    print(f"  page_size: 5")

    body = {k: v for k, v in payload.items() if k != "database_id"}
    response = client.request(  # type: ignore[union-attr]
        path=f"databases/{db_id}/query",
        method="POST",
        body=body,
    )
    result = extract_query_database_result(response)
    print(f"  SUCCESS: count={result['count']} has_more={result['has_more']}")
    for r in result["results"][:3]:
        print(f"    page_id={r['page_id']} url={r['url']}")


def _ensure_umh_status_property(client: object, db_id: str) -> None:
    """Ensure the target database has the 'UMH Status' select property."""
    db = client.databases.retrieve(database_id=db_id)  # type: ignore[union-attr]
    if "UMH Status" in db.get("properties", {}):
        return
    print("  adding 'UMH Status' select property to database...")
    client.request(  # type: ignore[union-attr]
        path=f"databases/{db_id}",
        method="PATCH",
        body={
            "properties": {
                "UMH Status": {
                    "select": {
                        "options": [
                            {"name": "Success", "color": "green"},
                            {"name": "Error", "color": "red"},
                            {"name": "Blocked", "color": "orange"},
                            {"name": "Timeout", "color": "yellow"},
                            {"name": "Unknown", "color": "gray"},
                        ]
                    }
                }
            }
        },
    )
    print("  'UMH Status' property created")


def smoke_writeback(client: object, db_id: str) -> None:
    """End-to-end writeback smoke: create page → submit with writeback_to → verify status + callout."""
    umh_base = os.getenv("UMH_BASE_URL", "http://localhost:8093")

    _ensure_umh_status_property(client, db_id)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    title = f"[UMH-TEST] Writeback smoke {timestamp}"
    payload = build_create_page_payload(db_id, title)
    print(f"\n--- writeback (step 1/3: create test page) ---")
    response = client.pages.create(**payload)  # type: ignore[union-attr]
    result = extract_create_page_result(response)
    page_id = result["page_id"]
    print(f"  created page_id={page_id}")

    print(f"\n--- writeback (step 2/3: submit with writeback_to) ---")
    submit_payload = {
        "content": f"writeback smoke test {timestamp}",
        "risk_class": "READ_ONLY",
        "adapter_name": "shell",
        "operation": "generic",
        "params": {},
        "pre_approved": True,
        "writeback_to": {"page_id": page_id, "integration": "notion"},
    }
    print(f"  POST {umh_base}/api/umh/submit")
    resp = httpx.post(f"{umh_base}/api/umh/submit", json=submit_payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"submit failed: {resp.status_code} {resp.text}")
    submit_result = resp.json()
    print(f"  submit response: {json.dumps(submit_result, indent=2)}")

    time.sleep(2)

    print(f"\n--- writeback (step 3/3: verify page updated) ---")
    page = client.pages.retrieve(page_id=page_id)  # type: ignore[union-attr]
    props = page.get("properties", {})
    umh_status = props.get("UMH Status", {})
    status_select = umh_status.get("select", {})
    status_name = status_select.get("name", "<not set>") if status_select else "<not set>"
    print(f"  UMH Status property: {status_name}")

    blocks_resp = client.blocks.children.list(block_id=page_id)  # type: ignore[union-attr]
    blocks = blocks_resp.get("results", [])
    callout_found = False
    for block in blocks:
        if block.get("type") == "callout":
            callout = block["callout"]
            text_parts = callout.get("rich_text", [])
            if text_parts:
                content = text_parts[0].get("text", {}).get("content", "")
                if "[UMH]" in content:
                    callout_found = True
                    print(f"  callout block: {content[:120]}")
                    break

    if status_name in ("Success", "Error", "Blocked", "Timeout", "Unknown"):
        print(f"  PASS: UMH Status = {status_name}")
    else:
        raise RuntimeError(f"UMH Status not set correctly: got '{status_name}'")

    if callout_found:
        print(f"  PASS: callout block appended")
    else:
        raise RuntimeError("callout block not found on page")


def main() -> None:
    if len(sys.argv) < 2:
        databases = discover_database_ids()
        print("Available databases:")
        for name, uid in sorted(databases.items()):
            print(f"  {name} → {uid}")
        print(f"\nUsage: python3 {sys.argv[0]} <database_id_or_logical_name>")
        print("Set SMOKE_OPS='create,update,append,query,writeback' to test all operations.")
        sys.exit(1)

    raw_db_id = sys.argv[1]
    db_id = _resolve_db(raw_db_id)
    client = get_notion_client()

    ops_str = os.getenv("SMOKE_OPS", "create")
    ops = [o.strip() for o in ops_str.split(",")]
    print(f"Operations: {ops}")

    page_id = ""
    failures: list[str] = []

    for op in ops:
        try:
            if op == "create":
                page_id = smoke_create(client, db_id)
            elif op == "update":
                if not page_id:
                    print(f"\n--- update_page SKIPPED (no page_id — run 'create' first) ---")
                    continue
                smoke_update(client, page_id)
            elif op == "append":
                if not page_id:
                    print(f"\n--- append_block SKIPPED (no page_id — run 'create' first) ---")
                    continue
                smoke_append(client, page_id)
            elif op == "query":
                smoke_query(client, db_id)
            elif op == "writeback":
                smoke_writeback(client, db_id)
            else:
                print(f"\n--- {op} UNKNOWN (valid: create, update, append, query, writeback) ---")
                failures.append(op)
        except Exception as exc:
            print(f"\n  FAILED: {type(exc).__name__}: {exc}")
            failures.append(op)

    print(f"\n{'=' * 40}")
    if failures:
        print(f"FAILURES: {failures}")
        sys.exit(1)
    else:
        print(f"ALL {len(ops)} OPERATIONS PASSED")


if __name__ == "__main__":
    main()
