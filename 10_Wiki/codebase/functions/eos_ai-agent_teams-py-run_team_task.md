---
type: codebase-function
file: eos_ai/agent_teams.py
line: 313
generated: 2026-04-12
---

# run_team_task

**File:** [[eos_ai-agent_teams-py]] | **Line:** 313
**Signature:** `run_team_task(team, sub_agent, prompt, venture_id, ctx, username) → dict`

Convenience wrapper — resolves team/sub_agent, runs via AgentRuntime,
returns result as a plain dict for easy inspection.

Args:
    team:       Domain team name — 'sales', 'research', 'content',
...

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run_team_task]]
