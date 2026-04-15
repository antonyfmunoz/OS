---
type: codebase-function
file: eos_ai/agent_teams.py
line: 298
generated: 2026-04-12
---

# route

**File:** [[eos_ai-agent_teams-py]] | **Line:** 298
**Signature:** `route(team, sub_agent) → SubAgentConfig`

Resolve a team + sub_agent name to a SubAgentConfig.

Raises ValueError for unknown team or sub_agent.
Called by AgentRuntime.run_team_task().

## Calls

- [[eos_ai-agent_teams-py-ContentTeam-route]]
- [[eos_ai-agent_teams-py-CustomerSuccessTeam-route]]
- [[eos_ai-agent_teams-py-MarketingTeam-route]]
- [[eos_ai-agent_teams-py-OperationsTeam-route]]
- [[eos_ai-agent_teams-py-ResearchTeam-route]]
- [[eos_ai-agent_teams-py-SalesTeam-route]]
