---
type: codebase-function
file: eos_ai/quality_gate.py
line: 416
generated: 2026-05-07
---

# quality_check

**File:** [[eos_ai-quality_gate-py]] | **Line:** 416
**Signature:** `quality_check(content, content_type, recipient_context) → dict`

Run quality check on outgoing communication.

Returns dict with keys: approved (bool), score (int 0-10),
issues (list[str]), suggestions (list[str]), revised_version (str).

## Called By

- [[eos_ai-quality_gate-py-gate_outgoing_email]]
