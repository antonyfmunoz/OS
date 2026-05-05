---
type: codebase-function
file: core/tool_mastery_manager/coverage.py
line: 36
generated: 2026-04-12
---

# evaluate_coverage

**File:** [[core-tool_mastery_manager-coverage-py]] | **Line:** 36
**Signature:** `evaluate_coverage(slug) → CoverageReport`

Classify a single tool slug into one CoverageStatus.

Composes the three existing TME internals:
    - _tme_common.load_skill   — filesystem + frontmatter
    - verify_tool_skill._check  — 9-point verifier
...

## Calls

- [[scripts-_tme_common-py-load_skill]]
- [[scripts-check_skill_staleness-py-_assess]]
- [[scripts-verify_tool_skill-py-_check]]

## Called By

- [[core-tool_mastery_manager-coverage-py-evaluate_many]]
- [[scripts-tool_mastery_manager-py-cmd_status]]
- [[scripts-tool_mastery_research_dispatcher-py-main]]
