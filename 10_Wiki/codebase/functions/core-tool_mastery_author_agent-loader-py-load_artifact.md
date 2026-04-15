---
type: codebase-function
file: core/tool_mastery_author_agent/loader.py
line: 156
generated: 2026-04-12
---

# load_artifact

**File:** [[core-tool_mastery_author_agent-loader-py]] | **Line:** 156
**Signature:** `load_artifact(artifact_path) → LoadedArtifact`

Load research_artifact.json and all OK raw captures.

Raises nothing on per-file failures — load_errors accumulates.

## Calls

- [[core-tool_mastery_author_agent-loader-py-_read_text_safely]]

## Called By

- [[scripts-measure_phase8_batch-py-measure_tool]]
