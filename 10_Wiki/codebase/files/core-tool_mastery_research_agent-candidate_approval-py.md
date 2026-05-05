---
type: codebase-file
path: core/tool_mastery_research_agent/candidate_approval.py
module: core.tool_mastery_research_agent.candidate_approval
lines: 272
size: 9037
generated: 2026-04-12
---

# core/tool_mastery_research_agent/candidate_approval.py

Candidate approval gate for search-based source discovery.

The approval flow is deliberately simple and file-based so it composes
with the existing Control Plane without introducing a new action type:

...

**Lines:** 272 | **Size:** 9,037 bytes

## Contains

- **class** [[core-tool_mastery_research_agent-candidate_approval-py-CandidateRecord]] — 2 methods
- **class** [[core-tool_mastery_research_agent-candidate_approval-py-ApprovalFile]] — 2 methods
- **fn** [[core-tool_mastery_research_agent-candidate_approval-py-_now_iso]]`() → str`
- **fn** [[core-tool_mastery_research_agent-candidate_approval-py-_candidates_dir]]`(tool_slug) → Path`
- **fn** [[core-tool_mastery_research_agent-candidate_approval-py-build_approval_file]]`(plan) → ApprovalFile`
- **fn** [[core-tool_mastery_research_agent-candidate_approval-py-persist_approval_file]]`(approval) → Path`
- **fn** [[core-tool_mastery_research_agent-candidate_approval-py-load_approval_file]]`(path) → ApprovalFile`
- **fn** [[core-tool_mastery_research_agent-candidate_approval-py-save_approval_file]]`(path, approval) → None`
- **fn** [[core-tool_mastery_research_agent-candidate_approval-py-latest_approval_file]]`(tool_slug) → Path | None`
- **fn** [[core-tool_mastery_research_agent-candidate_approval-py-apply_decision]]`(approval) → ApprovalFile`
- **fn** [[core-tool_mastery_research_agent-candidate_approval-py-approved_source_refs]]`(approval) → list[SourceRef]`
- **fn** [[core-tool_mastery_research_agent-candidate_approval-py-format_candidates_for_display]]`(approval) → str`

## Import Statements

```python
from __future__ import annotations
import json
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from models import SourceRef
from search_discovery import Candidate
from search_discovery import CandidatePlan
from paths import RESEARCH_LOG_DIR
```
