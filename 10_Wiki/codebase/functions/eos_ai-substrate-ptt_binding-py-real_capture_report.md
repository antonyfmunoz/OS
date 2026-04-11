---
type: codebase-function
file: eos_ai/substrate/ptt_binding.py
line: 347
generated: 2026-04-11
---

# real_capture_report

**File:** [[eos_ai-substrate-ptt_binding-py]] | **Line:** 347
**Signature:** `real_capture_report(node_id) → dict[str, Any]`

Bounded operator-facing summary of recent real-capture attempts.

Combines:
  - current workstation readiness
  - last N validation attempts (filtered by node if given)
...

## Calls

- [[eos_ai-substrate-ptt_binding-py-RealCaptureValidation-as_dict]]
- [[eos_ai-substrate-ptt_binding-py-_ValidationHistory-latest]]
- [[eos_ai-substrate-ptt_binding-py-_safe_readiness]]
- [[eos_ai-substrate-ptt_binding-py-_utcnow_iso]]
- [[eos_ai-substrate-ptt_binding-py-get_validation_history]]

## Called By

- [[scripts-substrate_ptt_binding_smoke_test-py-main]]
