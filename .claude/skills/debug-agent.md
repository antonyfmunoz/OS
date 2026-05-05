---
name: debug-agent
description: Use when an EOS agent produces wrong output, blank responses, or fails to load identity/soul docs.
allowed-tools: Bash, Read, Grep
---

# How to Debug an EOS Agent

## Step 1 — Isolate
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.agent_runtime import AgentRuntime, TaskType
from eos_ai.context import load_context_from_env
rt = AgentRuntime(load_context_from_env())
result = rt.run(TaskType.GENERATE, 'test',
  agent='AGENT_ID', max_tokens=100)
print('Model:', result.model_used)
print('Output:', result.output)
"

## Step 2 — Check soul doc loading
grep -n "soul_doc\|0a" \
  /opt/OS/eos_ai/agent_runtime.py | head -10

## Step 3 — Check hierarchy
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.agent_hierarchy import AgentHierarchy
print(AgentHierarchy().format_for_prompt('AGENT_ID'))
"

## Step 4 — Check Neon registration
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.db import get_conn
from eos_ai.context import load_context_from_env
ctx = load_context_from_env()
with get_conn(ctx.org_id) as cur:
  cur.execute('SELECT name,is_active FROM agents WHERE org_id=%s', (ctx.org_id,))
  for r in cur.fetchall(): print(r)
"

## Failure modes
- Soul doc path wrong → blank identity
- Not in Neon → generic fallback
- Credits depleted → Qwen, lower quality
- Hierarchy missing → not in prompt
