# TME Natural Language Resolver

**Version:** 1.0
**Date:** 2026-05-05
**Scope:** UMH substrate — all platform consumers

## Purpose

Detects tools, capabilities, and runtimes from natural language text
without requiring slash commands or explicit tool references.

## Module

`core/tool_mastery_manager/tool_mastery_resolver.py`

## Detection Layers

### Tool Detection

25+ tools with alias lists. Detection uses word-boundary regex matching
sorted by alias length (longest first) to prevent partial matches.
Each detection returns a `ResolvedToolMention` with confidence and reason.

### Capability Detection

7 capability categories detected via phrase matching:
- document_ingestion
- google_docs_tab_aware_extraction
- software_engineering
- test_execution
- computer_use
- deployment
- database_operations

### Runtime Detection

6 execution environment categories:
- vps, tmux, docker, wsl, local_desktop, claude_code_session

## Full Resolution

`resolve_mastery_for_task(text)` produces a `ToolMasteryResolution`:
- detected_tools, detected_capabilities, detected_runtimes
- required_mastery_packs (auto-inferred from detections)
- confidence score
- needs_clarification flag (True when nothing detected)

## Integration

The Control Plane calls `resolve_mastery_for_user_intent()` in
`core/action_system/tme.py` to detect tools from user messages
before routing to workers.

## Extensibility

- `KNOWN_TOOLS` dict can be extended with new tool entries
- `CAPABILITY_MAP` dict can be extended with new capabilities
- Custom known_tools dicts can be passed to override defaults
