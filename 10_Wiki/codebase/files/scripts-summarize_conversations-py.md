---
type: codebase-file
path: scripts/summarize_conversations.py
module: scripts.summarize_conversations
lines: 508
size: 18085
tags: [entry-point]
generated: 2026-04-12
---

# scripts/summarize_conversations.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Summarize conversation files into structured knowledge summaries.

Reads raw conversation logs from vault/memory/conversations/,
calls an LLM to extract structured knowledge, and writes
summary files to vault/memory/summaries/.
...

**Lines:** 508 | **Size:** 18,085 bytes

## Contains

- **fn** [[scripts-summarize_conversations-py-_parse_frontmatter]]`(text) → tuple[dict, str]`
- **fn** [[scripts-summarize_conversations-py-_dump_frontmatter]]`(fm, body) → str`
- **fn** [[scripts-summarize_conversations-py-get_processed_sessions]]`() → set[str]`
- **fn** [[scripts-summarize_conversations-py-_extract_body]]`(filepath) → tuple[dict, str]`
- **fn** [[scripts-summarize_conversations-py-_is_trivial]]`(body) → bool`
- **fn** [[scripts-summarize_conversations-py-_call_llm]]`(conversation_text) → str | None`
- **fn** [[scripts-summarize_conversations-py-_parse_llm_response]]`(raw) → dict | None`
- **fn** [[scripts-summarize_conversations-py-_slugify]]`(text) → str`
- **fn** [[scripts-summarize_conversations-py-write_summary]]`(session_id, parsed, source_path, date_str) → str`
- **fn** [[scripts-summarize_conversations-py-update_memory_index]]`(summary_relpath, title, session_id) → None`
- **fn** [[scripts-summarize_conversations-py-process_session]]`(filepath, dry_run) → bool`
- **fn** [[scripts-summarize_conversations-py-main]]`() → None`

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
from pathlib import Path
```
