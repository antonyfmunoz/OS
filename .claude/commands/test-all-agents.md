Test all 4 EOS agents end-to-end.

python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.agent_runtime import AgentRuntime, TaskType
from eos_ai.agent_hierarchy import AgentHierarchy
from eos_ai.context import load_context_from_env
ctx = load_context_from_env()
rt = AgentRuntime(ctx)
ah = AgentHierarchy()
# Test core agents: EA, Portfolio Advisor, and all CEO-level agents
core = ['executive_assistant', 'portfolio_advisor']
ceos = [aid for aid, cfg in ah.agents.items() if cfg.get('ceo_intelligence')]
agents = [(a, 'status update') for a in core + ceos]
for agent, prompt in agents:
  result = rt.run(TaskType.GENERATE, prompt,
    agent=agent, max_tokens=100)
  status = 'OK' if result.output else 'FAILED'
  print(f'{status} {agent}: {(result.output or \"FAILED\")[:80]}')
"
