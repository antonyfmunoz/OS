---
type: codebase-function
file: core/tool_mastery_manager/mastery_assurance.py
line: 185
generated: 2026-05-07
---

# ensure_mastery_before_execution

**File:** [[core-tool_mastery_manager-mastery_assurance-py]] | **Line:** 185
**Signature:** `ensure_mastery_before_execution(tool_name, pack_exists, pack_text, last_researched, speed_category, tier, founder_waiver, current_date) → MasteryAssuranceDecision`

Evaluate mastery and produce a blocking/allowing decision.

## Calls

- [[core-tool_mastery_manager-mastery_assurance-py-determine_required_tme_flow]]
- [[core-tool_mastery_manager-mastery_assurance-py-evaluate_pack_completeness]]
- [[core-tool_mastery_manager-mastery_assurance-py-evaluate_pack_freshness]]
- [[core-tool_mastery_manager-mastery_assurance-py-evaluate_pack_quality]]
- [[core-tool_mastery_manager-mastery_assurance-py-normalize_tool_name]]
