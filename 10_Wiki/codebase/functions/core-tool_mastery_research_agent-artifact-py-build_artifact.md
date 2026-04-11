---
type: codebase-function
file: core/tool_mastery_research_agent/artifact.py
line: 191
generated: 2026-04-11
---

# build_artifact

**File:** [[core-tool_mastery_research_agent-artifact-py]] | **Line:** 191
**Signature:** `build_artifact() → ResearchArtifact`

Assemble a ResearchArtifact from the plan + fetch results.

Post-fetch filtering: each OK source is measured for prose density.
Sources that fail the density gate are demoted to SKIPPED with an
explanatory error so the Author Agent never sees them.

## Calls

- [[core-tool_mastery_research_agent-artifact-py-_iso_now]]
- [[core-tool_mastery_research_agent-artifact-py-_ok_sources]]
- [[core-tool_mastery_research_agent-artifact-py-_run_phase5_extraction]]
- [[core-tool_mastery_research_agent-artifact-py-_run_signal_pass]]
