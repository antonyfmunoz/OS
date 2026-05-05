---
type: codebase-function
file: eos_ai/substrate/station_helpers.py
line: 24
generated: 2026-04-12
---

# propose_speak_text

**File:** [[eos_ai-substrate-station_helpers-py]] | **Line:** 24
**Signature:** `propose_speak_text(node_id, text) → SafeAction`

Propose a SPEAK_TEXT action to the given node. Returns the dispatched SafeAction.

## Calls

- [[eos_ai-substrate-station-py-StationContract-propose]]
- [[eos_ai-substrate-station_helpers-py-_contract_in_drive]]

## Called By

- [[eos_ai-substrate-ritual_body-py-run_close_day_body]]
- [[eos_ai-substrate-ritual_body-py-run_open_day_body]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-submit_utterance]]
- [[scripts-substrate_smoke_test-py-main]]
