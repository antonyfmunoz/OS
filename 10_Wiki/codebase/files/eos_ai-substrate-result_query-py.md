---
type: codebase-file
path: eos_ai/substrate/result_query.py
module: eos_ai.substrate.result_query
lines: 455
size: 14682
generated: 2026-04-12
---

# eos_ai/substrate/result_query.py

Result query helpers — tiny operator-facing view over the ResultStore.

Not a UI, not an API — just the smallest useful set of lookups so operators
and reporting scripts can answer questions like:

...

**Lines:** 455 | **Size:** 14,682 bytes

## Depends On

- [[eos_ai-substrate-result_store-py]]

## Used By

- [[eos_ai-substrate-ritual_body-py]]
- [[eos_ai-substrate-station_readiness-py]]
- [[scripts-substrate_audio_loop_smoke_test-py]]
- [[scripts-substrate_drain_station-py]]
- [[scripts-substrate_durable_result_smoke_test-py]]
- [[scripts-substrate_operator_state_smoke_test-py]]
- [[scripts-substrate_voice_session_smoke_test-py]]
- [[scripts-substrate_wake_producer_smoke_test-py]]

## Contains

- **fn** [[eos_ai-substrate-result_query-py-_row]]`(r) → dict[str, Any]`
- **fn** [[eos_ai-substrate-result_query-py-latest]]`(limit) → list[dict]`
- **fn** [[eos_ai-substrate-result_query-py-latest_by_node]]`(node_id, limit) → list[dict]`
- **fn** [[eos_ai-substrate-result_query-py-by_action_id]]`(action_id) → Optional[dict]`
- **fn** [[eos_ai-substrate-result_query-py-latest_failed]]`(limit) → list[dict]`
- **fn** [[eos_ai-substrate-result_query-py-stats]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-result_query-py-latest_by_kind]]`(kind, limit) → list[dict]`
- **fn** [[eos_ai-substrate-result_query-py-node_health_summary]]`(node_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-result_query-py-unresolved_rituals]]`(limit) → list[dict]`
- **fn** [[eos_ai-substrate-result_query-py-station_readiness_report]]`(node_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-result_query-py-recent_open_close_summaries]]`(limit) → list[dict]`
- **fn** [[eos_ai-substrate-result_query-py-recent_voice_sessions]]`(limit, node_id) → list[dict]`
- **fn** [[eos_ai-substrate-result_query-py-recent_wake_producer_events]]`(limit) → list[dict]`
- **fn** [[eos_ai-substrate-result_query-py-operator_state_snapshot]]`(node_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-result_query-py-audio_loop_snapshot]]`(node_id) → dict[str, Any]`
- **fn** [[eos_ai-substrate-result_query-py-recent_audio_loop_transcripts]]`(node_id, limit) → list[dict]`
- **fn** [[eos_ai-substrate-result_query-py-ritual_outcomes_summary]]`(limit) → list[dict]`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from typing import Optional
from eos_ai.substrate.result_store import IngestedResult
from eos_ai.substrate.result_store import ResultStore
from eos_ai.substrate.result_store import get_result_store
```
