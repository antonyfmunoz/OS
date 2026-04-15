---
type: codebase-function
file: eos_ai/business_instance.py
line: 470
generated: 2026-04-12
---

# get_ai_name

**File:** [[eos_ai-business_instance-py]] | **Line:** 470
**Signature:** `get_ai_name(ctx, venture_id) → str`

Resolve AI name for this user.
Priority: BIS.ai_name → AI_NAME env var → default 'DEX'.

## Calls

- [[eos_ai-business_instance-py-BusinessInstanceManager-get_bis]]

## Called By

- [[services-discord_bot-py-on_ready]]
