---
type: codebase-function
file: core/tool_mastery_research_agent/extraction.py
line: 1144
generated: 2026-04-11
---

# extract_from_source

**File:** [[core-tool_mastery_research_agent-extraction-py]] | **Line:** 1144
**Signature:** `extract_from_source() → SourceExtraction`

Run classification + pattern extraction on one fetched body.

``raw_text`` is the undecoded capture body (pre-sanitiser). We run a
code-preserving preprocessing pass over it for pattern extraction so
install commands, JSON schemas, and function signatures survive.
...

## Calls

- [[core-tool_mastery_research_agent-extraction-py-_extract_conceptual_model]]
- [[core-tool_mastery_research_agent-extraction-py-_extract_config_blocks]]
- [[core-tool_mastery_research_agent-extraction-py-_extract_design_intent]]
- [[core-tool_mastery_research_agent-extraction-py-_extract_function_signatures]]
- [[core-tool_mastery_research_agent-extraction-py-_extract_install_commands]]
- [[core-tool_mastery_research_agent-extraction-py-_extract_json_schemas]]
- [[core-tool_mastery_research_agent-extraction-py-_extract_operational_behavior]]
- [[core-tool_mastery_research_agent-extraction-py-_extract_param_defs]]
- [[core-tool_mastery_research_agent-extraction-py-_extract_setup_flows]]
- [[core-tool_mastery_research_agent-extraction-py-_extract_version_pins]]
- [[core-tool_mastery_research_agent-extraction-py-_extract_workflow_sequences]]
- [[core-tool_mastery_research_agent-extraction-py-classify_source_type]]
- [[core-tool_mastery_research_agent-extraction-py-preprocess_for_extraction]]

## Called By

- [[scripts-measure_phase8_batch-py-re_extract_patterns]]
