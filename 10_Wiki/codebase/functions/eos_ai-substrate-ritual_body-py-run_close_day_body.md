---
type: codebase-function
file: eos_ai/substrate/ritual_body.py
line: 255
generated: 2026-04-12
---

# run_close_day_body

**File:** [[eos_ai-substrate-ritual_body-py]] | **Line:** 255
**Signature:** `run_close_day_body(ritual_id, policy) → list[dict]`

Execute the close_day body. Same semantics as run_open_day_body:
best-effort, never raises, writes to ritual.outputs["body_actions"].

## Calls

- [[eos_ai-substrate-actions-py-SafeAction-to_dict]]
- [[eos_ai-substrate-nodes-py-NodeRegistry-_flush]]
- [[eos_ai-substrate-nodes-py-NodeRegistry-default]]
- [[eos_ai-substrate-nodes-py-NodeRegistry-get]]
- [[eos_ai-substrate-ritual_body-py-_log]]
- [[eos_ai-substrate-ritual_body-py-_record]]
- [[eos_ai-substrate-ritual_body-py-_resolve_station]]
- [[eos_ai-substrate-ritual_inference-py-InferredHint-to_dict]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-_flush]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-default]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-get]]
- [[eos_ai-substrate-scene_policy-py-SceneDecision-to_dict]]
- [[eos_ai-substrate-station_helpers-py-propose_play_sound]]
- [[eos_ai-substrate-station_helpers-py-propose_speak_text]]
- [[eos_ai-substrate-station_readiness-py-StationReadiness-to_dict]]
- [[eos_ai-substrate-station_readiness-py-station_readiness]]

## Called By

- [[eos_ai-substrate-ritual_runner-py-start_close_day]]
