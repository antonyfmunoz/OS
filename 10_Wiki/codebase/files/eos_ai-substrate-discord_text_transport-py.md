---
type: codebase-file
path: eos_ai/substrate/discord_text_transport.py
module: eos_ai.substrate.discord_text_transport
lines: 1674
size: 62037
generated: 2026-04-12
---

# eos_ai/substrate/discord_text_transport.py

Discord text transport — Pseudo-Live Voice Loop v1.

Purpose
-------
This is the **bounded Discord text-channel ingress** for the shared voice
...

**Lines:** 1674 | **Size:** 62,037 bytes

## Depends On

- [[eos_ai-substrate-context_lifecycle-py]]
- [[eos_ai-substrate-resource_guard-py]]
- [[eos_ai-substrate-workload_policy-py]]

## Used By

- [[scripts-substrate_discord_claude_hardswitch_smoke_test-py]]
- [[scripts-substrate_discord_text_tts_smoke_test-py]]
- [[scripts-substrate_discord_tts_body_only_smoke_test-py]]
- [[scripts-substrate_mode_behavior_control_smoke_test-py]]
- [[services-discord_bot-py]]

## Contains

- **class** [[eos_ai-substrate-discord_text_transport-py-DiscordTextEvent]] — 1 methods
- **class** [[eos_ai-substrate-discord_text_transport-py-_TextHistory]] — 4 methods
- **fn** [[eos_ai-substrate-discord_text_transport-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_utcnow_iso]]`() → str`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_flag_truthy]]`(name) → bool`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_ingress_enabled]]`() → bool`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_tts_enabled]]`() → bool`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_parse_allowlist]]`(name) → set[str]`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_allowlist_permits]]`(name, value) → bool`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_reply_max_chars]]`() → int`
- **fn** [[eos_ai-substrate-discord_text_transport-py-truncate_reply]]`(text) → str`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_record_backend]]`() → None`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_backend_snapshot]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-discord_text_transport-py-reset_backend_state_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-discord_text_transport-py-get_text_history]]`() → _TextHistory`
- **fn** [[eos_ai-substrate-discord_text_transport-py-reset_text_history_for_tests]]`() → None`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_short_preview]]`(text, n) → str`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_check_gating]]`() → Optional[str]`
- **fn** [[eos_ai-substrate-discord_text_transport-py-ingest_text_message]]`(text) → dict[str, Any]`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_latest_agent_reply]]`(session_id) → Optional[str]`
- **fn** [[eos_ai-substrate-discord_text_transport-py-build_tts_reply_envelope]]`(reply_text) → dict[str, Any]`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_handle_session_command]]`(command) → dict[str, Any]`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_handle_trace_command]]`(text) → dict[str, Any]`
- **fn** [[eos_ai-substrate-discord_text_transport-py-maybe_mirror_discord_text_message]]`(text) → Optional[dict[str, Any]]`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_claude_failure_envelope]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_claude_responder_ingest]]`(text) → dict[str, Any]`
- **fn** [[eos_ai-substrate-discord_text_transport-py-pseudo_live_status]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-discord_text_transport-py-_hybrid_execution_status]]`() → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import os
import sys
import threading
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Optional
from eos_ai.substrate.workload_policy import classify_workload
from eos_ai.substrate.resource_guard import evaluate_resource_guard
from eos_ai.substrate.context_lifecycle import detect_context_pressure
from eos_ai.substrate.context_lifecycle import maybe_clear_and_restore
```
