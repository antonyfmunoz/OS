---
type: codebase-function
file: core/wiki_navigation.py
line: 232
generated: 2026-05-07
---

# wiki_traverse

**File:** [[core-wiki_navigation-py]] | **Line:** 232
**Signature:** `wiki_traverse(candidates, wiki_index, max_expansions) → list[str]`

Traverse 1 hop through wikilinks from top wiki-mapped candidates.

Returns additional node IDs discovered via wiki navigation.
Capped aggressively. Ignores operational pages.

...

## Calls

- [[core-wiki_navigation-py-WikiIndex-get_nodes_for_slug]]
- [[core-wiki_navigation-py-WikiIndex-is_operational]]
