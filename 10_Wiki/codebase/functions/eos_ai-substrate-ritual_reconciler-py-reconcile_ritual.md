---
type: codebase-function
file: eos_ai/substrate/ritual_reconciler.py
line: 67
generated: 2026-04-12
---

# reconcile_ritual

**File:** [[eos_ai-substrate-ritual_reconciler-py]] | **Line:** 67
**Signature:** `reconcile_ritual(ritual_id) → Optional[ReconcileSummary]`

Reconcile a single ritual's body actions against ingested results.

Returns None if the ritual is unknown; otherwise returns a
ReconcileSummary describing how many body entries got matched to
stored results. Any matched entry has these fields added in-place:
...

## Calls

- [[eos_ai-substrate-result_store-py-IngestedResult-as_dict]]
- [[eos_ai-substrate-result_store-py-ResultStore-_flush]]
- [[eos_ai-substrate-result_store-py-ResultStore-get]]
- [[eos_ai-substrate-result_store-py-ResultStore-put]]
- [[eos_ai-substrate-result_store-py-_log]]
- [[eos_ai-substrate-result_store-py-get_result_store]]
- [[eos_ai-substrate-ritual_reconciler-py-ReconcileSummary-as_dict]]
- [[eos_ai-substrate-ritual_reconciler-py-_log]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-_flush]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-default]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-get]]

## Called By

- [[eos_ai-substrate-ritual_reconciler-py-reconcile_recent]]
- [[scripts-substrate_durable_result_smoke_test-py-main]]
- [[scripts-substrate_result_loop_smoke_test-py-main]]
