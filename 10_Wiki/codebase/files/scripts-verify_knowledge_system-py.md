---
type: codebase-file
path: scripts/verify_knowledge_system.py
module: scripts.verify_knowledge_system
lines: 353
size: 11870
tags: [entry-point]
generated: 2026-04-12
---

# scripts/verify_knowledge_system.py

> **ENTRY POINT** — Contains `if __name__` or server start.

verify_knowledge_system.py — Acceptance check for the EOS cognition stack.

Runs validation in retrieval-hierarchy order so any failure maps directly to
the layer it breaks. Exit 0 = all checks pass. Exit 1 = at least one failure.

...

**Lines:** 353 | **Size:** 11,870 bytes

## Contains

- **class** [[scripts-verify_knowledge_system-py-CheckResult]] — 0 methods
- **fn** [[scripts-verify_knowledge_system-py-check_session_docs]]`() → CheckResult`
- **fn** [[scripts-verify_knowledge_system-py-check_data_artifacts]]`() → CheckResult`
- **fn** [[scripts-verify_knowledge_system-py-check_palace_structure]]`() → CheckResult`
- **fn** [[scripts-verify_knowledge_system-py-check_codebase_vault]]`() → CheckResult`
- **fn** [[scripts-verify_knowledge_system-py-check_graph_loads]]`() → CheckResult`
- **fn** [[scripts-verify_knowledge_system-py-check_freshness]]`() → CheckResult`
- **fn** [[scripts-verify_knowledge_system-py-check_parser_registry]]`() → CheckResult`
- **fn** [[scripts-verify_knowledge_system-py-check_query_cli]]`() → CheckResult`
- **fn** [[scripts-verify_knowledge_system-py-check_summaries_alignment]]`() → CheckResult`
- **fn** [[scripts-verify_knowledge_system-py-check_palace_alignment]]`() → CheckResult`
- **fn** [[scripts-verify_knowledge_system-py-check_claude_md_directives]]`() → CheckResult`
- **fn** [[scripts-verify_knowledge_system-py-run_all]]`() → list[CheckResult]`
- **fn** [[scripts-verify_knowledge_system-py-print_report]]`(results) → None`
- **fn** [[scripts-verify_knowledge_system-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
```
