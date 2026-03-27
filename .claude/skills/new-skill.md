# How to Add a New Agent Skill

## Steps

### 1. Create skill file
/opt/OS/06_Skills/{Department}/{name}.md

8-component structure required:
Purpose, Outcome, Best-Practice Benchmark,
Decision Criteria, Execution Steps,
Failure Modes, Measurement,
Improvement Opportunities

### 2. Sync to Neon
python3 -c "
import sys, uuid
sys.path.insert(0, '/opt/OS')
from eos_ai.db import get_conn
from eos_ai.context import load_context_from_env
from pathlib import Path
ctx = load_context_from_env()
path = '/opt/OS/06_Skills/Dept/name.md'
with get_conn(ctx.org_id) as cur:
  cur.execute('''
    INSERT INTO skills
      (id, org_id, name, content, version)
    VALUES (%s,%s,%s,%s,1)
    ON CONFLICT (org_id, name)
    DO UPDATE SET content=EXCLUDED.content
  ''', (str(uuid.uuid4()), ctx.org_id,
    'skill_name', Path(path).read_text()))
  print('Synced')
"

### 3. Wire to agent_teams.py
Add skill to relevant sub-agent in department.

### 4. Verify
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.skill_registry import get_skill_registry
sr = get_skill_registry()
print(f'Total: {len(sr._skills)}')
"

## Common mistakes
- File created but not synced to Neon
- Wrong 8-component structure
- Not wiring to agent_teams.py
