"""Higgsfield Cloud API end-to-end smoke test.

Fires the cheapest possible Soul generation through the EOS wrapper,
verifies the `higgsfield_jobs` row was inserted, and polls status a
few times so we can confirm auth + submit + request_id extraction
all work against the live platform.

Burns real credits (small — Soul standard 720p 1:1). Run manually:
    python3 /opt/OS/scripts/higgsfield_smoke_test.py

Exit codes:
    0 — submit + DB insert verified (terminal state not required)
    1 — submit failed or DB row missing
"""
from __future__ import annotations

import sys
import time

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from substrate.state.storage.db import get_conn  # noqa: E402
from adapters.higgsfield.higgsfield_client import generate, get_status  # noqa: E402

VENTURE = "personal_brand"
MODEL_ID = "higgsfield-ai/soul/standard"
PROMPT = "single red apple on white background, product photo"


def main() -> int:
    print(f"[smoke] submitting {MODEL_ID} venture={VENTURE}")
    try:
        request_id = generate(
            VENTURE,
            MODEL_ID,
            prompt=PROMPT,
            aspect_ratio="1:1",
            resolution="720p",
        )
    except Exception as e:
        print(f"[smoke] FAIL submit raised: {e}")
        return 1

    print(f"[smoke] request_id={request_id}")

    with get_conn() as cur:
        cur.execute(
            "SELECT status, venture, model_id, submitted_at "
            "FROM higgsfield_jobs WHERE request_id=%s",
            (request_id,),
        )
        row = cur.fetchone()

    if row is None:
        print("[smoke] FAIL no higgsfield_jobs row inserted")
        return 1

    print(f"[smoke] DB row OK status={row['status']} submitted_at={row['submitted_at']}")

    # Light poll — don't block forever. Webhook handler owns terminal state.
    for attempt in range(5):
        time.sleep(6)
        try:
            s = get_status(request_id)
        except Exception as e:
            print(f"[smoke] poll {attempt} raised: {e}")
            continue
        print(f"[smoke] poll {attempt} status={s}")
        if s in ("Completed", "Failed", "NSFW", "Cancelled"):
            break

    print("[smoke] PASS (submit + DB insert verified; webhook owns terminal state)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
