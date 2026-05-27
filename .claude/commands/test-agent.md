Test a specific EOS agent end-to-end.

Arguments: $ARGUMENTS (agent name, e.g. executive_assistant)

python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from adapters.models.agent_runtime import AgentRuntime; from substrate.contracts.agent_types import TaskType
from substrate.state.context.context import load_context_from_env
ctx = load_context_from_env()
rt = AgentRuntime(ctx)
result = rt.run(
  task_type=TaskType.GENERATE,
  prompt='what should I focus on today',
  agent='$ARGUMENTS',
  max_tokens=200
)
print(f'Agent: $ARGUMENTS')
print(f'Model: {result.model_used}')
print(f'Response: {result.output[:300]}')
"
