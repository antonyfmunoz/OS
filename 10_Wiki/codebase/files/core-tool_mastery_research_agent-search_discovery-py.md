---
type: codebase-file
path: core/tool_mastery_research_agent/search_discovery.py
module: core.tool_mastery_research_agent.search_discovery
lines: 354
size: 11610
generated: 2026-04-12
---

# core/tool_mastery_research_agent/search_discovery.py

Deterministic search candidate generator for the Research Agent.

When registry + MCP discovery return nothing, we still need a way to
*propose* primary sources without hallucinating. This module generates
candidate URLs from explicit pattern families keyed off the tool slug.
...

**Lines:** 354 | **Size:** 11,610 bytes

## Contains

- **class** [[core-tool_mastery_research_agent-search_discovery-py-Candidate]] — 2 methods
- **class** [[core-tool_mastery_research_agent-search_discovery-py-CandidatePlan]] — 1 methods
- **fn** [[core-tool_mastery_research_agent-search_discovery-py-_tokenize]]`(slug) → list[str]`
- **fn** [[core-tool_mastery_research_agent-search_discovery-py-_join]]`(tokens, sep) → str`
- **fn** [[core-tool_mastery_research_agent-search_discovery-py-_variants]]`(slug) → dict[str, str]`
- **fn** [[core-tool_mastery_research_agent-search_discovery-py-_family_pypi]]`(v) → list[Candidate]`
- **fn** [[core-tool_mastery_research_agent-search_discovery-py-_family_npm]]`(v) → list[Candidate]`
- **fn** [[core-tool_mastery_research_agent-search_discovery-py-_family_github_search]]`(v) → list[Candidate]`
- **fn** [[core-tool_mastery_research_agent-search_discovery-py-_family_github_repo_guess]]`(v) → list[Candidate]`
- **fn** [[core-tool_mastery_research_agent-search_discovery-py-_family_vendor_domain]]`(v) → list[Candidate]`
- **fn** [[core-tool_mastery_research_agent-search_discovery-py-_family_api_reference]]`(v) → list[Candidate]`
- **fn** [[core-tool_mastery_research_agent-search_discovery-py-_dedupe]]`(candidates) → list[Candidate]`
- **fn** [[core-tool_mastery_research_agent-search_discovery-py-generate_candidates]]`(tool_slug) → CandidatePlan`

## Import Statements

```python
from __future__ import annotations
import re
from dataclasses import dataclass
from dataclasses import field
from typing import Iterable
from models import SourceRef
from models import SourceTier
```
