---
type: codebase-file
path: eos_ai/agent_teams.py
module: eos_ai.agent_teams
lines: 396
size: 14842
generated: 2026-05-07
---

# eos_ai/agent_teams.py

Domain team registry for the OS agent system.

Five teams: sales, research, content, marketing, operations.
Each team maps named sub-agents to a SubAgentConfig (task type + skill + token budget).
The module-level route() function is the single entry point used by AgentRuntime.run_team_task().
...

**Lines:** 396 | **Size:** 14,842 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]

## Contains

- **class** [[eos_ai-agent_teams-py-SubAgentConfig]] — 0 methods
- **class** [[eos_ai-agent_teams-py-SalesTeam]] — 1 methods
- **class** [[eos_ai-agent_teams-py-ResearchTeam]] — 1 methods
- **class** [[eos_ai-agent_teams-py-ContentTeam]] — 1 methods
- **class** [[eos_ai-agent_teams-py-MarketingTeam]] — 1 methods
- **class** [[eos_ai-agent_teams-py-CustomerSuccessTeam]] — 1 methods
- **class** [[eos_ai-agent_teams-py-OperationsTeam]] — 1 methods
- **fn** [[eos_ai-agent_teams-py-route]]`(team, sub_agent) → SubAgentConfig`
- **fn** [[eos_ai-agent_teams-py-run_team_task]]`(team, sub_agent, prompt, venture_id, ctx, username) → dict`
- **fn** [[eos_ai-agent_teams-py-run_browser_action]]`(team, url, task, ctx) → dict`
- **fn** [[eos_ai-agent_teams-py-list_teams]]`() → dict[str, list[str]]`

## Import Statements

```python
from dataclasses import dataclass
from eos_ai.agent_runtime import TaskType
```
