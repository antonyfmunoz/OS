---
type: codebase-function
file: core/wiki_navigation.py
line: 288
generated: 2026-04-12
---

# wiki_rerank_bonus

**File:** [[core-wiki_navigation-py]] | **Line:** 288
**Signature:** `wiki_rerank_bonus(candidate) → float`

Compute a bounded rerank bonus from wiki signal.

Returns a float in [0, WIKI_BONUS_MAX].

Bonus components:
...
