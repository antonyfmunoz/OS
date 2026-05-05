---
type: codebase-function
file: scripts/promote_to_wiki.py
line: 307
generated: 2026-04-12
---

# promote_candidate

**File:** [[scripts-promote_to_wiki-py]] | **Line:** 307
**Signature:** `promote_candidate(candidate, summary_path, summary_fm, existing_pages, dry_run) → str | None`

Promote a single candidate. Returns wiki page path or None.

## Calls

- [[scripts-promote_to_wiki-py-append_wiki_log]]
- [[scripts-promote_to_wiki-py-build_wiki_page]]
- [[scripts-promote_to_wiki-py-mark_summary_promoted]]
- [[scripts-promote_to_wiki-py-update_wiki_index]]

## Called By

- [[scripts-promote_to_wiki-py-main]]
