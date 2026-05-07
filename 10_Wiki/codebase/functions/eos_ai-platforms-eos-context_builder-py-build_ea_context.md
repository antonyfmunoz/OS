---
type: codebase-function
file: eos_ai/platforms/eos/context_builder.py
line: 118
generated: 2026-05-07
---

# build_ea_context

**File:** [[eos_ai-platforms-eos-context_builder-py]] | **Line:** 118
**Signature:** `build_ea_context() → dict[str, Any]`

Build EA context — communication, coordination, next actions, blocked decisions.

EA sees the widest view: tasks, pipelines, perceptions, session state,
station presence, live sessions.

## Calls

- [[eos_ai-platforms-eos-context_builder-py-_safe]]
- [[eos_ai-platforms-eos-context_builder-py-_utcnow]]

## Called By

- [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_direct_ea]]
- [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_execution]]
- [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_review]]
- [[eos_ai-platforms-eos-ea_orchestrator-py-_handle_status]]
