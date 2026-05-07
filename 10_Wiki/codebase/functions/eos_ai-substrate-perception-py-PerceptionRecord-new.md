---
type: codebase-function
file: eos_ai/substrate/perception.py
line: 103
generated: 2026-05-07
---

# PerceptionRecord.new

**File:** [[eos_ai-substrate-perception-py]] | **Line:** 103
**Signature:** `new(source, summary, severity) → 'PerceptionRecord'`

**Class:** [[eos_ai-substrate-perception-py-PerceptionRecord]]

Create a new PerceptionRecord with generated ID and fingerprint.

## Calls

- [[eos_ai-substrate-perception-py-_make_fingerprint]]
- [[eos_ai-substrate-perception-py-_new_id]]
- [[eos_ai-substrate-perception-py-_utcnow]]

## Called By

- [[eos_ai-substrate-perception-py-collect_git_perception]]
- [[eos_ai-substrate-perception-py-collect_live_session_perception]]
- [[eos_ai-substrate-perception-py-collect_local_control_perception]]
- [[eos_ai-substrate-perception-py-collect_node_status_perception]]
- [[eos_ai-substrate-perception-py-collect_operator_session_perception]]
- [[eos_ai-substrate-perception-py-collect_pipeline_perception]]
- [[eos_ai-substrate-perception-py-collect_runtime_log_perception]]
- [[eos_ai-substrate-perception-py-collect_station_presence_perception]]
- [[eos_ai-substrate-perception-py-collect_task_perception]]

## Decorators

- `@classmethod`
