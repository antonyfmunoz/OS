---
type: codebase-function
file: eos_ai/substrate/ritual_reconciler.py
line: 152
generated: 2026-04-12
---

# reconcile_recent

**File:** [[eos_ai-substrate-ritual_reconciler-py]] | **Line:** 152
**Signature:** `reconcile_recent(limit) → list[ReconcileSummary]`

Reconcile the most recent rituals in the registry. Useful as a single
operator call after a drain pass: "update everything that might have
pending results." Never raises on individual failures.

## Calls

- [[eos_ai-substrate-result_store-py-_log]]
- [[eos_ai-substrate-ritual_reconciler-py-_log]]
- [[eos_ai-substrate-ritual_reconciler-py-reconcile_ritual]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-default]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-history]]

## Called By

- [[scripts-substrate_drain_station-py-main]]
