---
type: codebase-file
path: scripts/promote_to_wiki.py
module: scripts.promote_to_wiki
lines: 438
size: 15704
tags: [entry-point]
generated: 2026-05-07
---

# scripts/promote_to_wiki.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Promote durable knowledge from summaries into 10_Wiki/.

Reads wiki_candidates from summary frontmatter, creates wiki pages
following WIKI_RULES.md, updates index.md and log.md.
Template-based — no LLM call required.
...

**Lines:** 438 | **Size:** 15,704 bytes

## Contains

- **fn** [[scripts-promote_to_wiki-py-_parse_frontmatter]]`(text) → tuple[dict, str]`
- **fn** [[scripts-promote_to_wiki-py-_dump_frontmatter]]`(fm, body) → str`
- **fn** [[scripts-promote_to_wiki-py-get_existing_wiki_pages]]`() → set[str]`
- **fn** [[scripts-promote_to_wiki-py-_find_related_pages]]`(candidate_name, existing) → list[str]`
- **fn** [[scripts-promote_to_wiki-py-build_wiki_page]]`(candidate, summary_path, summary_fm) → str`
- **fn** [[scripts-promote_to_wiki-py-update_wiki_index]]`(page_slug, page_type, description) → None`
- **fn** [[scripts-promote_to_wiki-py-append_wiki_log]]`(action, page_slug, description) → None`
- **fn** [[scripts-promote_to_wiki-py-mark_summary_promoted]]`(summary_path, wiki_slug) → None`
- **fn** [[scripts-promote_to_wiki-py-should_promote]]`(candidate, existing_pages, already_promoted, salience_label, promotion_recommendation) → tuple[bool, str]`
- **fn** [[scripts-promote_to_wiki-py-promote_candidate]]`(candidate, summary_path, summary_fm, existing_pages, dry_run) → str | None`
- **fn** [[scripts-promote_to_wiki-py-main]]`() → None`

## Import Statements

```python
import sys
import os
import re
import glob
import argparse
import logging
from datetime import datetime
from datetime import timezone
```
