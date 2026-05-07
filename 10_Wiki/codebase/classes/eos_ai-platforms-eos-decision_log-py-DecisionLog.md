---
type: codebase-class
file: eos_ai/platforms/eos/decision_log.py
line: 82
generated: 2026-05-07
---

# DecisionLog

**File:** [[eos_ai-platforms-eos-decision_log-py]] | **Line:** 82

Thread-safe, bounded decision log backed by substrate storage.

Singleton via DecisionLog.default().

## Methods

- [[eos_ai-platforms-eos-decision_log-py-DecisionLog-__init__]]`() → None` — 
- [[eos_ai-platforms-eos-decision_log-py-DecisionLog-_ensure_loaded]]`() → None` — 
- [[eos_ai-platforms-eos-decision_log-py-DecisionLog-_flush]]`() → None` — 
- [[eos_ai-platforms-eos-decision_log-py-DecisionLog-_prune]]`() → None` — 
- [[eos_ai-platforms-eos-decision_log-py-DecisionLog-record]]`(decision) → None` — Persist a decision record.
- [[eos_ai-platforms-eos-decision_log-py-DecisionLog-get]]`(decision_id) → Optional[EOSDecisionRecord]` — Retrieve a decision by ID.
- [[eos_ai-platforms-eos-decision_log-py-DecisionLog-recent]]`(limit) → list[EOSDecisionRecord]` — Return most recent decisions, newest first.
- [[eos_ai-platforms-eos-decision_log-py-DecisionLog-all]]`() → list[EOSDecisionRecord]` — Return all decisions.
- [[eos_ai-platforms-eos-decision_log-py-DecisionLog-default]]`() → 'DecisionLog'` — Return process-wide singleton.
- [[eos_ai-platforms-eos-decision_log-py-DecisionLog-reset_for_tests]]`() → None` — Test hook — drop the singleton.
