---
type: codebase-function
file: eos_ai/platforms/eos/ea_orchestrator.py
line: 299
generated: 2026-05-07
---

# handle_founder_message

**File:** [[eos_ai-platforms-eos-ea_orchestrator-py]] | **Line:** 299
**Signature:** `handle_founder_message(text) → EAResponse`

Main platform entrypoint — every founder message enters here.

Flow:
1. Parse founder intent (deterministic, zero LLM).
2. Route to handler based on intent type.
...

## Calls

- [[eos_ai-platforms-eos-context_builder-py-_log]]
- [[eos_ai-platforms-eos-decision_log-py-DecisionLog-default]]
- [[eos_ai-platforms-eos-decision_log-py-DecisionLog-get]]
- [[eos_ai-platforms-eos-decision_log-py-DecisionLog-record]]
- [[eos_ai-platforms-eos-decision_log-py-_log]]
- [[eos_ai-platforms-eos-ea_orchestrator-py-_log]]
- [[eos_ai-platforms-eos-intent_routing-py-parse_founder_intent]]

## Called By

- [[eos_ai-platforms-eos-discord_hook-py-handle_eos_discord_message]]
