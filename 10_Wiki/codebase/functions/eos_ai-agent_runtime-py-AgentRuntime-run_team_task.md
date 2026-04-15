---
type: codebase-function
file: eos_ai/agent_runtime.py
line: 401
generated: 2026-04-12
---

# AgentRuntime.run_team_task

**File:** [[eos_ai-agent_runtime-py]] | **Line:** 401
**Signature:** `run_team_task(team, sub_agent, prompt, venture_id, username) → AgentResult`

**Class:** [[eos_ai-agent_runtime-py-AgentRuntime]]

Route a task to the correct sub-agent within a domain team.

- Resolves team + sub_agent to a SubAgentConfig via agent_teams.route().
- Loads the matching skill automatically by skill_name.
- Injects human profile when username is provided and task is GENERATE/ANALYZE.
...

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]

## Called By

- [[eos_ai-agent_teams-py-run_team_task]]
- [[services-icp_scorer-py-score_comment]]
