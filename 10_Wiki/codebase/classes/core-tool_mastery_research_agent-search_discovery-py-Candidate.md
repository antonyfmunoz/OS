---
type: codebase-class
file: core/tool_mastery_research_agent/search_discovery.py
line: 80
generated: 2026-04-12
---

# Candidate

**File:** [[core-tool_mastery_research_agent-search_discovery-py]] | **Line:** 80

A proposed source URL generated from a pattern family.

Candidates are NOT SourceRefs until an operator approves them.
Keeping the type distinct is load-bearing: it stops accidental
plumbing of unapproved URLs into the fetcher.

## Methods

- [[core-tool_mastery_research_agent-search_discovery-py-Candidate-to_dict]]`() → dict[str, object]` — 
- [[core-tool_mastery_research_agent-search_discovery-py-Candidate-to_source_ref]]`() → SourceRef` — Promote to a SourceRef after approval.

## Decorators

- `@dataclass`
