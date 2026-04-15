---
type: codebase-class
file: eos_ai/substrate/audio_loop.py
line: 253
generated: 2026-04-12
---

# AudioLoopStore

**File:** [[eos_ai-substrate-audio_loop-py]] | **Line:** 253

Durable, bounded, thread-safe index of AudioLoopStates by node_id.

Mirrors OperatorStateStore exactly: dual-layer (in-mem + substrate
storage), singleton via `get_audio_loop_store()`. Best-effort
persistence — flush failures log and the in-memory state remains
...

## Methods

- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-__init__]]`() → None` — 
- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-_load]]`() → None` — 
- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-_flush]]`() → None` — 
- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-_enforce_retention]]`() → None` — 
- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-get_or_create]]`(node_id) → AudioLoopState` — 
- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-get]]`(node_id) → Optional[AudioLoopState]` — 
- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-put]]`(state) → None` — 
- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-all]]`() → list[AudioLoopState]` — 
- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-stats]]`() → dict[str, Any]` — 
- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-clear]]`() → None` — 
- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-__len__]]`() → int` — 
