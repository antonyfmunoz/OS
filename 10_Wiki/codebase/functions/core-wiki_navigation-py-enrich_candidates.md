---
type: codebase-function
file: core/wiki_navigation.py
line: 213
generated: 2026-04-12
---

# enrich_candidates

**File:** [[core-wiki_navigation-py]] | **Line:** 213
**Signature:** `enrich_candidates(candidates, wiki_index) → list[dict]`

Attach wiki metadata to each candidate (non-destructive enrichment).

Adds 'wiki' key to candidates that have a mapped wiki page.
Candidates without a mapping get wiki=None.

## Calls

- [[core-wiki_navigation-py-WikiIndex-get_wiki_for_node]]
