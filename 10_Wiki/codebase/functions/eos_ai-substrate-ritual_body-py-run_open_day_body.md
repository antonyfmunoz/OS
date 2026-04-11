---
type: codebase-function
file: eos_ai/substrate/ritual_body.py
line: 125
generated: 2026-04-11
---

# run_open_day_body

**File:** [[eos_ai-substrate-ritual_body-py]] | **Line:** 125
**Signature:** `run_open_day_body(ritual_id, policy) → list[dict]`

Execute the open_day body for an existing ritual. Returns the list of
body action records, which is also written into `ritual.outputs["body_actions"]`.

Never raises on station/transport problems — the ritual remains valid
even when no workstation is reachable.

## Calls

- [[eos_ai-substrate-actions-py-SafeAction-to_dict]]
- [[eos_ai-substrate-nodes-py-NodeRegistry-_flush]]
- [[eos_ai-substrate-nodes-py-NodeRegistry-default]]
- [[eos_ai-substrate-nodes-py-NodeRegistry-get]]
- [[eos_ai-substrate-ritual_body-py-_log]]
- [[eos_ai-substrate-ritual_body-py-_record]]
- [[eos_ai-substrate-ritual_body-py-_resolve_station]]
- [[eos_ai-substrate-ritual_inference-py-InferredHint-to_dict]]
- [[eos_ai-substrate-ritual_inference-py-infer_open_scene_hint]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-_flush]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-default]]
- [[eos_ai-substrate-rituals-py-RitualRegistry-get]]
- [[eos_ai-substrate-scene_policy-py-SceneDecision-to_dict]]
- [[eos_ai-substrate-scene_policy-py-select_scene]]
- [[eos_ai-substrate-scenes-py-get_scene]]
- [[eos_ai-substrate-station_helpers-py-propose_open_scene]]
- [[eos_ai-substrate-station_helpers-py-propose_speak_text]]
- [[eos_ai-substrate-station_readiness-py-StationReadiness-to_dict]]
- [[eos_ai-substrate-station_readiness-py-station_readiness]]

## Called By

- [[eos_ai-substrate-ritual_runner-py-start_open_day]]
