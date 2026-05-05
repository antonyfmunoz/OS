---
type: codebase-function
file: scripts/promote_to_wiki.py
line: 119
generated: 2026-04-12
---

# build_wiki_page

**File:** [[scripts-promote_to_wiki-py]] | **Line:** 119
**Signature:** `build_wiki_page(candidate, summary_path, summary_fm) → str`

Build wiki page content with proper frontmatter per WIKI_RULES.md.

## Calls

- [[scripts-promote_to_wiki-py-_dump_frontmatter]]
- [[scripts-promote_to_wiki-py-_find_related_pages]]
- [[scripts-promote_to_wiki-py-get_existing_wiki_pages]]

## Called By

- [[scripts-promote_to_wiki-py-promote_candidate]]
