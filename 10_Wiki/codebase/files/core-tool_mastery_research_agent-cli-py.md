---
type: codebase-file
path: core/tool_mastery_research_agent/cli.py
module: core.tool_mastery_research_agent.cli
lines: 250
size: 7813
tags: [entry-point]
generated: 2026-04-12
---

# core/tool_mastery_research_agent/cli.py

> **ENTRY POINT** — Contains `if __name__` or server start.

CLI entry for the Tool Mastery Research Agent.

Usage:
    python3 -m core.tool_mastery_research_agent \
        --tool notebooklm_mcp --mode research
...

**Lines:** 250 | **Size:** 7,813 bytes

## Contains

- **fn** [[core-tool_mastery_research_agent-cli-py-_load_action_file]]`(path) → ResearchRequest`
- **fn** [[core-tool_mastery_research_agent-cli-py-build_parser]]`() → argparse.ArgumentParser`
- **fn** [[core-tool_mastery_research_agent-cli-py-_parse_index_set]]`(raw) → set[int]`
- **fn** [[core-tool_mastery_research_agent-cli-py-_handle_generate_candidates]]`(tool) → int`
- **fn** [[core-tool_mastery_research_agent-cli-py-_handle_show_candidates]]`(tool) → int`
- **fn** [[core-tool_mastery_research_agent-cli-py-_handle_apply_decision]]`(args) → int`
- **fn** [[core-tool_mastery_research_agent-cli-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from agent import run
from candidate_approval import apply_decision
from candidate_approval import build_approval_file
from candidate_approval import format_candidates_for_display
from candidate_approval import latest_approval_file
from candidate_approval import load_approval_file
from candidate_approval import persist_approval_file
from candidate_approval import save_approval_file
from models import ResearchMode
from models import ResearchRequest
from search_discovery import generate_candidates
```
