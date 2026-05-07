---
type: codebase-function
file: eos_ai/substrate/local_control.py
line: 847
generated: 2026-05-07
---

# open_scene

**File:** [[eos_ai-substrate-local_control-py]] | **Line:** 847
**Signature:** `open_scene(scene_name) → LocalControlRequest`

Convenience: submit an OPEN_SCENE request.

Resolves scene_name against the scene registry. If the scene is not
found, the request is immediately marked FAILED.

## Calls

- [[eos_ai-substrate-local_control-py-LocalControlStore-default]]
- [[eos_ai-substrate-local_control-py-LocalControlStore-put]]
- [[eos_ai-substrate-local_control-py-_log]]
- [[eos_ai-substrate-local_control-py-_make_id]]
- [[eos_ai-substrate-local_control-py-_utcnow]]
- [[eos_ai-substrate-local_control-py-submit_control_request]]
