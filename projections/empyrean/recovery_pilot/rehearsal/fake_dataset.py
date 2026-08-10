"""D1 — synthetic roofer dataset for the rehearsal. Deterministic seed."""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

COMPANY = "Cascade Summit Roofing (SYNTHETIC)"

FIRST = ("Jim", "Maria", "Dale", "Sandra", "Luis", "Pat", "Kevin", "Donna",
         "Ray", "Beth", "Carl", "Nina", "Ted", "Gloria", "Hank", "Rosa")
LAST = ("Miller", "Nguyen", "Olsen", "Garcia", "Thompson", "Baker", "Reed",
        "Foster", "Hansen", "Ortiz", "Weber", "Chandler")


def generate(out_csv: Path, seed: int = 20260810) -> dict:
    """Write the synthetic CRM export. Returns ground-truth counts."""
    rng = random.Random(seed)
    base = date(2026, 8, 10)
    rows = []

    def person(i: int) -> str:
        return "%s %s" % (FIRST[i % len(FIRST)], LAST[(i * 7) % len(LAST)])

    # 230 past customers (>=200 -> PASS leg one)
    for i in range(230):
        rows.append({
            "Record Type": "Completed Job", "Customer Name": person(i),
            "Created Date": (base - timedelta(days=rng.randint(90, 2400))).strftime("%m/%d/%Y"),
            "Total Amount": str(rng.randint(9000, 34000)), "Status": "closed won",
        })
    # 58 open estimates <=12mo (>=50 -> PASS leg two) + 15 stale/resolved noise
    for i in range(58):
        rows.append({
            "Record Type": "Estimate", "Customer Name": person(300 + i),
            "Created Date": (base - timedelta(days=rng.randint(7, 330))).strftime("%m/%d/%Y"),
            "Total Amount": str(rng.randint(11000, 30000)), "Status": "open - no response",
        })
    for i in range(15):
        rows.append({
            "Record Type": "Estimate", "Customer Name": person(400 + i),
            "Created Date": (base - timedelta(days=rng.randint(400, 900))).strftime("%m/%d/%Y"),
            "Total Amount": str(rng.randint(11000, 30000)), "Status": "lost",
        })
    # 26 missed calls last 30 days
    for i in range(26):
        rows.append({
            "Record Type": "Missed Call", "Customer Name": person(500 + i),
            "Created Date": (base - timedelta(days=rng.randint(1, 29))).strftime("%m/%d/%Y"),
            "Total Amount": "", "Status": "",
        })
    rng.shuffle(rows)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Record Type", "Customer Name",
                                          "Created Date", "Total Amount", "Status"])
        w.writeheader()
        w.writerows(rows)
    return {"past_customers": 230, "open_estimates_12mo": 58,
            "stale_estimates": 15, "missed_calls": 26, "total_rows": len(rows)}
