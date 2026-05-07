---
type: codebase-file
path: core/tool_mastery_author_agent/cli.py
module: core.tool_mastery_author_agent.cli
lines: 133
size: 4438
tags: [entry-point]
generated: 2026-05-07
---

# core/tool_mastery_author_agent/cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

CLI entry for the Tool Mastery Author Agent.

Usage:
    # Author from a specific research artifact
    python3 -m core.tool_mastery_author_agent \
...

**Lines:** 133 | **Size:** 4,438 bytes

## Contains

- **fn** [[core-tool_mastery_author_agent-cli-py-_latest_artifact_for]]`(tool_slug) → Path | None`
- **fn** [[core-tool_mastery_author_agent-cli-py-build_parser]]`() → argparse.ArgumentParser`
- **fn** [[core-tool_mastery_author_agent-cli-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from agent import author
from models import AuthorRequest
from paths import RESEARCH_LOG_DIR
```
