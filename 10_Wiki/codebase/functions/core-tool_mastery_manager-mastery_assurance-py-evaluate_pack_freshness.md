---
type: codebase-function
file: core/tool_mastery_manager/mastery_assurance.py
line: 131
generated: 2026-05-07
---

# evaluate_pack_freshness

**File:** [[core-tool_mastery_manager-mastery_assurance-py]] | **Line:** 131
**Signature:** `evaluate_pack_freshness(last_researched, speed_category, current_date) → str`

Return 'fresh', 'near_stale', 'stale', or 'missing_date'.

## Calls

- [[core-tool_mastery_manager-mastery_assurance-py-determine_staleness_threshold]]

## Called By

- [[core-tool_mastery_manager-mastery_assurance-py-ensure_mastery_before_execution]]
