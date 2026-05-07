---
type: codebase-function
file: scripts/promote_to_wiki.py
line: 268
generated: 2026-05-07
---

# should_promote

**File:** [[scripts-promote_to_wiki-py]] | **Line:** 268
**Signature:** `should_promote(candidate, existing_pages, already_promoted, salience_label, promotion_recommendation) → tuple[bool, str]`

Return (should_promote, reason) based on salience and dedup checks.

## Called By

- [[scripts-promote_to_wiki-py-main]]
