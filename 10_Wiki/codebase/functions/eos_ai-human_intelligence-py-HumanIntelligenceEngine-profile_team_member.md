---
type: codebase-function
file: eos_ai/human_intelligence.py
line: 430
generated: 2026-04-12
---

# HumanIntelligenceEngine.profile_team_member

**File:** [[eos_ai-human_intelligence-py]] | **Line:** 430
**Signature:** `profile_team_member(user_id, org_id) → dict`

**Class:** [[eos_ai-human_intelligence-py-HumanIntelligenceEngine]]

Profile a team member from their org_members entry and interaction
history with the system (tasks completed, notes, communication pattern).

Returns:
    user_id:                  str
...

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-db-py-get_conn]]
- [[eos_ai-human_intelligence-py-HumanIntelligenceEngine-_store_profile]]
