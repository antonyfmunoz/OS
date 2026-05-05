#!/usr/bin/env python3
"""TME staleness sweep — summary-first report for hooks and cron."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

sys.path.insert(0, "/opt/OS")

from scripts._tme_common import (
    NEAR_STALE_FRACTION,
    load_all_skills,
    days_since,
    freshness_window,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--quiet", action="store_true", help="suppress fresh skills")
    ap.add_argument("--speed", choices=["fast", "medium", "stable", "slow"],
                    help="filter to one speed_category (for tiered scheduling)")
    args = ap.parse_args()

    today = date.today()
    all_skills = load_all_skills()
    skills = [s for s in all_skills if s.speed_category == args.speed] if args.speed else all_skills

    stale, near_stale, fresh = [], [], []
    for rec in skills:
        window = freshness_window(rec.speed_category)
        lr = rec.last_researched
        if lr is None:
            stale.append({"slug": rec.slug, "age": None, "window": window,
                          "speed": rec.speed_category, "status": "missing_date"})
            continue
        age = days_since(lr, today)
        if age > window:
            stale.append({"slug": rec.slug, "age": age, "window": window,
                          "speed": rec.speed_category, "status": "stale"})
        elif age >= int(window * NEAR_STALE_FRACTION):
            near_stale.append({"slug": rec.slug, "age": age, "window": window,
                               "speed": rec.speed_category, "status": "near_stale"})
        else:
            fresh.append({"slug": rec.slug, "age": age, "window": window,
                          "speed": rec.speed_category, "status": "fresh"})

    if args.json:
        print(json.dumps({"stale": stale, "near_stale": near_stale,
                          "fresh": fresh, "counts": {
                              "stale": len(stale), "near_stale": len(near_stale),
                              "fresh": len(fresh), "total": len(skills)}}, indent=2))
        return 1 if stale else 0

    # Summary line always prints
    print(f"TME sweep: {len(stale)} stale, {len(near_stale)} near_stale, "
          f"{len(fresh)} fresh ({len(skills)} total)")

    if stale:
        print("\n--- STALE ---")
        for s in stale:
            age_txt = f"{s['age']}d" if s["age"] is not None else "no date"
            print(f"  {s['slug']:30s} age={age_txt} window={s['window']}d "
                  f"speed={s['speed']}")

    if near_stale:
        print("\n--- NEAR STALE ---")
        for s in near_stale:
            suffix = "  ** fast-moving tool **" if s["speed"] == "fast" else ""
            print(f"  {s['slug']:30s} age={s['age']}d window={s['window']}d "
                  f"speed={s['speed']}{suffix}")

    if not args.quiet and fresh:
        print("\n--- FRESH ---")
        for s in fresh:
            print(f"  {s['slug']:30s} age={s['age']}d window={s['window']}d")

    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
