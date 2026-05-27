---
name: new-agent
description: Use when creating a new EOS agent — hierarchy entry, soul doc, Neon registration, and verification.
allowed-tools: Bash, Read, Write, Edit
---

# How to Create a New EOS Agent

## Steps

### 1. Add to HIERARCHY in agent_hierarchy.py
  'agent_id': {
    'level': N,
    'title': 'Agent Title',
    'reports_to': 'parent_id',
    'manages': [],
    'owns': ['what_it_owns'],
    'handle_directly': ['task_types'],
    'escalate_to': {'task': 'target'},
    'soul_doc': '/opt/OS/agents/id.md',
    'emoji': '🎯',
  }

### 2. Create soul doc
/opt/OS/agents/agent_id.md
Must have: Identity, Role, Tone,
  What you never do, Example responses

### 3. Register in Neon
python3 -c "
import sys, uuid
sys.path.insert(0, '/opt/OS')
from substrate.state.storage.db import get_conn
from substrate.state.context.context import load_context_from_env
ctx = load_context_from_env()
with get_conn(ctx.org_id) as cur:
  cur.execute('''
    INSERT INTO agents
      (id, org_id, name, type, department,
       soul_doc_path, is_active)
    VALUES (%s,%s,%s,%s,%s,%s,true)
    ON CONFLICT (org_id, name)
    DO UPDATE SET soul_doc_path=EXCLUDED.soul_doc_path
  ''', (str(uuid.uuid4()), ctx.org_id,
    'agent_id', 'Title', 'dept',
    '/opt/OS/agents/agent_id.md'))
  print('Registered')
"

### 4. Test
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from adapters.models.agent_runtime import AgentRuntime, TaskType
from substrate.state.context.context import load_context_from_env
rt = AgentRuntime(load_context_from_env())
result = rt.run(TaskType.GENERATE, 'test',
  agent='agent_id', max_tokens=100)
print(result.output)
"

### 5. Restart services
docker restart os-discord

## Common mistakes
- Forgetting Neon registration
- Missing tone examples in soul doc
- Not testing before restart
