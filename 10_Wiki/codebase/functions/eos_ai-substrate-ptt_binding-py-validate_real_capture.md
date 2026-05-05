---
type: codebase-function
file: eos_ai/substrate/ptt_binding.py
line: 188
generated: 2026-04-12
---

# validate_real_capture

**File:** [[eos_ai-substrate-ptt_binding-py]] | **Line:** 188
**Signature:** `validate_real_capture(node_id) → dict[str, Any]`

Run one bounded REAL_READY proof attempt and return its classification.

Flow:
  1. Probe `stt_workstation_readiness()`.
  2. If real capture is unsupported AND a `simulated_fallback_text` was
...

## Calls

- [[eos_ai-substrate-ptt_binding-py-RealCaptureValidation-as_dict]]
- [[eos_ai-substrate-ptt_binding-py-_ValidationHistory-record]]
- [[eos_ai-substrate-ptt_binding-py-_log]]
- [[eos_ai-substrate-ptt_binding-py-_new_id]]
- [[eos_ai-substrate-ptt_binding-py-_pick_device]]
- [[eos_ai-substrate-ptt_binding-py-_safe_readiness]]
- [[eos_ai-substrate-ptt_binding-py-get_validation_history]]

## Called By

- [[scripts-substrate_ptt_binding_smoke_test-py-main]]
- [[scripts-substrate_transport_report_smoke_test-py-main]]
