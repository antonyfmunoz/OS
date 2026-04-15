---
type: codebase-function
file: eos_ai/substrate/capability_tagging.py
line: 88
generated: 2026-04-12
---

# tag_request

**File:** [[eos_ai-substrate-capability_tagging-py]] | **Line:** 88
**Signature:** `tag_request(request) → list[str]`

Inspect a gateway request and return the list of capability slugs that
would be required to serve it on a capability-routed substrate. Also
writes the list to `request["required_capabilities"]` for observability.

Every reasoning request implicitly needs REASONING, so that tag is added
...

## Calls

- [[eos_ai-substrate-capability_tagging-py-_is_browser]]
- [[eos_ai-substrate-capability_tagging-py-_is_long_running]]
- [[eos_ai-substrate-capability_tagging-py-_is_voice]]
- [[eos_ai-substrate-capability_tagging-py-_is_workstation]]
