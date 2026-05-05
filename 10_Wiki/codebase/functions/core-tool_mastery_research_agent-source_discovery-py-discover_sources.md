---
type: codebase-function
file: core/tool_mastery_research_agent/source_discovery.py
line: 164
generated: 2026-04-12
---

# discover_sources

**File:** [[core-tool_mastery_research_agent-source_discovery-py]] | **Line:** 164
**Signature:** `discover_sources(tool_slug) → SourcePlan`

Build a SourcePlan for a single tool.

Honest contract: if no primary source is found, the plan is empty
and `notes` explains what was checked. Callers must handle the
empty case rather than guessing.

## Calls

- [[core-tool_mastery_research_agent-source_discovery-py-_from_claude_json]]
- [[core-tool_mastery_research_agent-source_discovery-py-_from_registry]]
