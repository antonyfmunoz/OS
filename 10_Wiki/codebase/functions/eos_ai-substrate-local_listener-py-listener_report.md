---
type: codebase-function
file: eos_ai/substrate/local_listener.py
line: 387
generated: 2026-04-12
---

# listener_report

**File:** [[eos_ai-substrate-local_listener-py]] | **Line:** 387
**Signature:** `listener_report(node_id, limit) → dict`

Compact report block describing recent listener activity.

## Calls

- [[eos_ai-substrate-local_listener-py-TriggerHistory-latest]]
- [[eos_ai-substrate-local_listener-py-get_trigger_history]]
- [[eos_ai-substrate-nodes-py-NodeRegistry-get]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-get]]
- [[eos_ai-substrate-storage-py-JSONFileStorage-get]]
- [[eos_ai-substrate-storage-py-NeonStorage-get]]
- [[eos_ai-substrate-storage-py-SubstrateStorage-get]]

## Called By

- [[scripts-substrate_drain_station-py-main]]
- [[scripts-substrate_local_listener-py-main]]
- [[scripts-substrate_local_listener_smoke_test-py-main]]
