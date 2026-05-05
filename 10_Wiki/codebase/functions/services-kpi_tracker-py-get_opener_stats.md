---
type: codebase-function
file: services/kpi_tracker.py
line: 120
generated: 2026-04-12
---

# get_opener_stats

**File:** [[services-kpi_tracker-py]] | **Line:** 120
**Signature:** `get_opener_stats()`

Return openers sorted by reply rate. Reads opener_stats.json if present,
falls back to scanning lead file frontmatter.

## Calls

- [[services-kpi_tracker-py-_parse_lead_frontmatter]]

## Called By

- [[services-kpi_tracker-py-build_eod_report]]
