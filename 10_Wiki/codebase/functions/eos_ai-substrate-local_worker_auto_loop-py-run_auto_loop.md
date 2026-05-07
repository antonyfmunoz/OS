---
type: codebase-function
file: eos_ai/substrate/local_worker_auto_loop.py
line: 788
generated: 2026-05-07
---

# run_auto_loop

**File:** [[eos_ai-substrate-local_worker_auto_loop-py]] | **Line:** 788
**Signature:** `run_auto_loop(packet_path) → dict[str, Any]`

Run the local worker auto-loop.

Returns a summary dict of what happened.

## Calls

- [[eos_ai-substrate-local_worker_auto_loop-py-_execute_approved_action]]
- [[eos_ai-substrate-local_worker_auto_loop-py-_extract_decision]]
- [[eos_ai-substrate-local_worker_auto_loop-py-_log]]
- [[eos_ai-substrate-local_worker_auto_loop-py-_now_iso]]
- [[eos_ai-substrate-local_worker_auto_loop-py-build_backend_health_status]]
- [[eos_ai-substrate-local_worker_auto_loop-py-build_claimed_status]]
- [[eos_ai-substrate-local_worker_auto_loop-py-build_first_gate_approval_request]]
- [[eos_ai-substrate-local_worker_auto_loop-py-build_preflight_status]]
- [[eos_ai-substrate-local_worker_auto_loop-py-load_worker_packet]]
- [[eos_ai-substrate-local_worker_auto_loop-py-run_gui_backend_healthcheck]]
- [[eos_ai-substrate-local_worker_auto_loop-py-run_safe_preflight]]
- [[eos_ai-substrate-local_worker_auto_loop-py-scan_inbox_for_response]]
- [[eos_ai-substrate-local_worker_auto_loop-py-validate_coherence_from_packet]]
- [[eos_ai-substrate-local_worker_auto_loop-py-validate_wo_001_packet]]
- [[eos_ai-substrate-local_worker_auto_loop-py-worker_should_stop]]
- [[eos_ai-substrate-local_worker_auto_loop-py-worker_should_wait_for_advisor]]
- [[eos_ai-substrate-local_worker_auto_loop-py-write_outbox_message]]
