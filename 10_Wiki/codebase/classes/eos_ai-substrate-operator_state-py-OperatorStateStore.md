---
type: codebase-class
file: eos_ai/substrate/operator_state.py
line: 255
generated: 2026-04-12
---

# OperatorStateStore

**File:** [[eos_ai-substrate-operator_state-py]] | **Line:** 255

Durable, bounded, thread-safe index of OperatorStates by node_id.

Mirrors VoiceSessionStore: dual-layer (in-mem + substrate storage), singleton
via `get_operator_state_store()`. Best-effort persistence — flush failures
log and the in-memory state remains correct.

## Methods

- [[eos_ai-substrate-operator_state-py-OperatorStateStore-__init__]]`() → None` — 
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-_load]]`() → None` — 
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-_flush]]`() → None` — 
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-_enforce_retention]]`() → None` — 
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-get_or_create]]`(node_id) → OperatorState` — 
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-get]]`(node_id) → Optional[OperatorState]` — 
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-put]]`(state) → None` — 
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-all]]`() → list[OperatorState]` — 
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-stats]]`() → dict[str, Any]` — 
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-clear]]`() → None` — Test helper. Drops in-memory rows AND the durable payload.
- [[eos_ai-substrate-operator_state-py-OperatorStateStore-__len__]]`() → int` — 
