---
type: codebase-function
file: eos_ai/platforms/eos/intent_routing.py
line: 198
generated: 2026-05-07
---

# parse_founder_intent

**File:** [[eos_ai-platforms-eos-intent_routing-py]] | **Line:** 198
**Signature:** `parse_founder_intent(text) → FounderIntent`

Classify founder text into a FounderIntent.

Rules evaluated top-to-bottom; first match wins.
Falls back to UNKNOWN / EA / 0.5 if nothing matches.

## Calls

- [[eos_ai-platforms-eos-intent_routing-py-_extract_directives]]
- [[eos_ai-platforms-eos-intent_routing-py-_new_id]]

## Called By

- [[eos_ai-platforms-eos-ea_orchestrator-py-handle_founder_message]]
