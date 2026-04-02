# Notion Fixes — DB IDs, Task Push, Ollama Fallback

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three Notion/runtime issues: per-venture DB ID separation, tasks not being pushed to Notion from agent execution, and Ollama timeout crashing the CEO morning cycle.

**Architecture:** Fix 1 is a diagnosis + data patch (VENTURES_JSON). Fix 2 adds a `notion_page_id` column to `tasks`, wires `write_task()` into the executor, and creates a poller. Fix 3 adds an Ollama health-check to both `model_router.py` and `agent_runtime.py` so VPS environments without Ollama fall back immediately instead of timing out.

**Tech Stack:** Python 3.12, Neon/PostgreSQL (psycopg2), Notion REST API, `eos_ai` runtime

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `scripts/notion_setup.py` | Modify | Add debug output confirming per-venture page IDs used |
| `eos_ai/notion_sync.py` | Modify | Add `push_pending_tasks_to_notion()` + `push_all_ventures()` |
| `scripts/agent_task_executor.py` | Modify | Wire `write_task()` call after each task completes |
| `scripts/notion_sync_poller.py` | Create | Thin cron script calling push + sync |
| `eos_ai/model_router.py` | Modify | Add `_ollama_available()` health check; don't mark ollama-qwen available until checked |
| `eos_ai/agent_runtime.py` | Modify | Catch Ollama `RuntimeError`/`ConnectionError` and fall back to Groq or skip |

---

## Task 1: Diagnose Fix 1 — Confirm per-venture DB IDs

**Files:**
- Read: `scripts/notion_setup.py` (already read — VENTURES dict at line 44 has distinct page_ids per venture)
- Diagnose: run two diagnostic commands below

- [ ] **Step 1: Run DB duplicate check**

```bash
python3 -c "
import os, requests, json
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')

token = os.getenv('NOTION_API_KEY')
headers = {
    'Authorization': f'Bearer {token}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
}
resp = requests.post(
    'https://api.notion.com/v1/search',
    headers=headers,
    json={'page_size': 100},
)

dbs_by_title = {}
for r in resp.json().get('results', []):
    if r.get('object') != 'database':
        continue
    tl = r.get('title', [])
    title = tl[0].get('plain_text','') if tl else ''
    parent_id = r.get('parent',{}).get('page_id','')
    if title not in dbs_by_title:
        dbs_by_title[title] = []
    dbs_by_title[title].append({'id': r['id'], 'parent': parent_id[:8]})

for title, dbs in dbs_by_title.items():
    if len(dbs) > 1:
        print(f'DUPLICATE: {title}')
        for db in dbs:
            print(f'  {db[\"id\"][:8]} parent:{db[\"parent\"]}')
    else:
        print(f'UNIQUE: {title} | {dbs[0][\"id\"][:8]} | parent:{dbs[0][\"parent\"]}')
"
```

Expected: Each DB title appears once under 3 different parent IDs (one per venture page). If any title shows `DUPLICATE` with the **same** parent, the setup script created duplicates in the same parent.

- [ ] **Step 2: Check VENTURES_JSON task DB IDs**

```bash
python3 -c "
import os, json
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
ventures = json.loads(os.getenv('VENTURES_JSON','[]'))
task_ids = set()
for v in ventures:
    tid = v.get('notion_tasks_db','') or v.get('notion_tasks_db','')
    print(f'{v[\"id\"]}: tasks_db={tid[:8] if tid else \"MISSING\"}')
    if tid in task_ids:
        print(f'  WARNING: DUPLICATE task DB ID')
    else:
        task_ids.add(tid)
"
```

Expected: three different 8-char prefixes. If duplicates appear, proceed to Step 3. If all unique, skip to Step 4.

- [ ] **Step 3 (only if duplicates found): Add debug to notion_setup.py and re-run**

In `scripts/notion_setup.py`, find `def main()` (line 954). After line `existing_dbs = _get_all_dbs()`, add:

```python
    print('\nVenture page IDs being used:')
    for v in VENTURES:
        print(f'  {v["id"]}: {v["page_id"][:8]}')
```

Run:
```bash
python3 /opt/OS/scripts/notion_setup.py
```

Confirm each venture uses a different parent page ID. The setup is idempotent — existing DBs are skipped, missing ones created. After re-run, VENTURES_JSON will be updated with correct per-venture IDs.

- [ ] **Step 4: Commit**

```bash
cd /opt/OS
git add scripts/notion_setup.py
git commit -m "fix: add debug output for per-venture page IDs in notion_setup"
```

---

## Task 2A: Add notion_page_id column to tasks table

**Files:**
- Modify: Neon schema (via Python migration script, no file changes needed)

- [ ] **Step 1: Check if column already exists**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
from eos_ai.context import load_context_from_env
from eos_ai.db import get_conn
ctx = load_context_from_env()
with get_conn(ctx.org_id) as cur:
    cur.execute('''
        SELECT column_name 
        FROM information_schema.columns
        WHERE table_name = 'tasks'
        AND column_name = 'notion_page_id'
    ''')
    exists = cur.fetchone()
    print('EXISTS' if exists else 'MISSING')
"
```

Expected: `MISSING` (proceed to Step 2) or `EXISTS` (skip to Task 2B).

- [ ] **Step 2: Add column**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
from eos_ai.context import load_context_from_env
from eos_ai.db import get_conn
ctx = load_context_from_env()
with get_conn(ctx.org_id) as cur:
    cur.execute('ALTER TABLE tasks ADD COLUMN IF NOT EXISTS notion_page_id text null')
    print('Column added')
"
```

Expected: `Column added`

- [ ] **Step 3: Verify**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
from eos_ai.context import load_context_from_env
from eos_ai.db import get_conn
ctx = load_context_from_env()
with get_conn(ctx.org_id) as cur:
    cur.execute(\"SELECT column_name FROM information_schema.columns WHERE table_name='tasks' AND column_name='notion_page_id'\")
    print('column present:', cur.fetchone() is not None)
"
```

Expected: `column present: True`

---

## Task 2B: Wire write_task() into agent_task_executor.py

**Files:**
- Modify: `scripts/agent_task_executor.py` (lines 210–251 — after `execute_agent_task` call in `run_executor`)

The existing `write_task()` signature (from `eos_ai/notion_sync.py:130`) is:
```python
def write_task(venture_id, name, status, priority, department, assigned_to,
               assignee_type, source, task_type, due_date, neon_id, notes,
               requires_approval) -> str
```

- [ ] **Step 1: Add Notion write block to agent_task_executor.py**

In `scripts/agent_task_executor.py`, find the line (around line 214):
```python
        # Mark task complete in Neon
        output_summary = exec_result.get('output', '')[:500]
        coordination.complete_task(task_id, output_summary)
```

Add a Notion write block immediately **after** `coordination.complete_task(...)` and **before** the events-table write:

```python
        # Write task result to Notion
        try:
            from eos_ai.notion_sync import write_task
            from eos_ai.db import get_conn
            venture_id = task.get('venture_id') or 'lyfe_institute'
            needs_approval = requires_approval(task, exec_result)
            notion_status = 'In review' if needs_approval else 'Done'
            agent_cfg = AGENT_MAP.get(
                exec_result.get('agent_id', ''), {}
            )
            notion_page_id = write_task(
                venture_id=venture_id,
                name=(
                    f'[{agent_cfg.get("display","Agent")}] '
                    f'{description[:120]}'
                ),
                status=notion_status,
                priority='Normal',
                department='Operations',
                assignee_type='Agent',
                assigned_to=agent_cfg.get('display', 'None'),
                source=agent_cfg.get('display', 'None'),
                task_type='Agent Task',
                neon_id=task_id,
                notes=exec_result.get('output', '')[:1000],
                requires_approval=needs_approval,
            )
            if notion_page_id:
                with get_conn(ctx.org_id) as cur:
                    cur.execute(
                        'UPDATE tasks SET notion_page_id = %s '
                        'WHERE id::text = %s AND org_id = %s',
                        (notion_page_id, task_id, str(ctx.org_id)),
                    )
                print(f'[Executor] → Notion: {notion_page_id[:8]}')
        except Exception as e:
            print(f'[Executor] Notion write skipped: {e}')
```

- [ ] **Step 2: Verify import is clean**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
load_dotenv('/opt/OS/13_Scripts/.env')
import scripts.agent_task_executor
print('import ok')
"
```

Expected: `import ok`

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add scripts/agent_task_executor.py
git commit -m "feat: wire write_task() to notion on agent task completion"
```

---

## Task 2C: Add push_pending_tasks_to_notion to notion_sync.py

**Files:**
- Modify: `eos_ai/notion_sync.py` (append after line 364 — after `write_document()`)

- [ ] **Step 1: Add push functions to notion_sync.py**

At the end of `eos_ai/notion_sync.py`, append:

```python

import logging
import json as _json

logger = logging.getLogger(__name__)


def push_pending_tasks_to_notion(venture_id: str, ctx=None) -> int:
    """
    Push tasks from Neon to Notion that don't have a notion_page_id yet.
    Returns count of tasks pushed.
    """
    db_id = get_db_id(venture_id, 'tasks')
    if not db_id:
        return 0

    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn

        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute(
                '''
                SELECT id, description,
                       assignee_id, assignee_type,
                       priority, status,
                       venture_id, created_at
                FROM tasks
                WHERE org_id = %s
                  AND (notion_page_id IS NULL
                       OR notion_page_id = '')
                  AND status != 'cancelled'
                  AND created_at >= NOW() - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT 20
                ''',
                (str(ctx.org_id),),
            )
            rows = cur.fetchall()

        status_map = {
            'pending': 'Not started',
            'in_progress': 'In progress',
            'completed': 'Done',
            'blocked': 'Blocked',
        }
        priority_map = {
            'critical': 'Critical',
            'high': 'High',
            'normal': 'Normal',
            'low': 'Low',
        }

        pushed = 0
        for row in rows:
            task_id = str(row['id'])
            description = row.get('description', '') or ''
            assignee = row.get('assignee_id', '') or ''
            priority = row.get('priority', 'normal') or 'normal'
            status = row.get('status', 'pending') or 'pending'
            assignee_type_raw = row.get('assignee_type', '') or ''

            notion_status = status_map.get(status, 'Not started')
            notion_priority = priority_map.get(priority.lower(), 'Normal')
            assignee_type = 'Agent' if assignee_type_raw == 'agent' else 'Human'

            notion_page_id = write_task(
                venture_id=venture_id,
                name=description[:200],
                status=notion_status,
                priority=notion_priority,
                assignee_type=assignee_type,
                assigned_to=assignee[:100] if assignee else 'Founder',
                source='Neon Sync',
                task_type='Task',
                neon_id=task_id,
            )

            if notion_page_id:
                with get_conn(ctx.org_id) as cur:
                    cur.execute(
                        'UPDATE tasks SET notion_page_id = %s '
                        'WHERE id::text = %s AND org_id = %s',
                        (notion_page_id, task_id, str(ctx.org_id)),
                    )
                pushed += 1

        return pushed
    except Exception as e:
        logger.warning(f'[Notion] push_tasks failed for {venture_id}: {e}')
        return 0


def push_all_ventures(ctx=None) -> dict:
    """Push pending tasks to Notion for all ventures in VENTURES_JSON."""
    ventures = _json.loads(os.getenv('VENTURES_JSON', '[]'))
    results = {}
    for v in ventures:
        vid = v.get('id', '')
        if not vid:
            continue
        pushed = push_pending_tasks_to_notion(vid, ctx)
        results[vid] = {'pushed': pushed}
    return results
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
from eos_ai.notion_sync import push_all_ventures, push_pending_tasks_to_notion
print('import ok')
"
```

Expected: `import ok`

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add eos_ai/notion_sync.py
git commit -m "feat: add push_pending_tasks_to_notion and push_all_ventures to notion_sync"
```

---

## Task 2D: Create notion_sync_poller.py

**Files:**
- Create: `scripts/notion_sync_poller.py`

- [ ] **Step 1: Write the file**

Create `/opt/OS/scripts/notion_sync_poller.py`:

```python
"""
Notion Sync Poller — runs every 15 minutes via cron.

1. Pushes Neon tasks without a notion_page_id → Notion
2. Pulls Notion status changes back → Neon events table
   (delegates to notion_tasks_sync.sync_neon_to_notion)
"""

import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')

PDT = ZoneInfo('America/Los_Angeles')


def run():
    from eos_ai.context import load_context_from_env
    from eos_ai.notion_sync import push_all_ventures
    from scripts.notion_tasks_sync import sync_neon_to_notion

    ctx = load_context_from_env()
    now = datetime.now(PDT)
    print(f'[NotionPoller] {now.strftime("%Y-%m-%d %H:%M")} PDT')

    # 1. Push Neon tasks → Notion
    push_results = push_all_ventures(ctx)
    for vid, counts in push_results.items():
        print(f'  {vid}: pushed={counts["pushed"]}')

    # 2. Push Neon status changes → Notion pages
    synced_back = sync_neon_to_notion()
    print(f'  status_sync_back={synced_back}')

    print('[NotionPoller] Done.')


if __name__ == '__main__':
    run()
```

- [ ] **Step 2: Verify**

```bash
python3 /opt/OS/scripts/notion_sync_poller.py
```

Expected: Output showing push counts per venture, no tracebacks. May show `pushed=0` if all tasks already have notion_page_id — that's correct.

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add scripts/notion_sync_poller.py
git commit -m "feat: create notion_sync_poller — push neon tasks to notion on cron"
```

---

## Task 3: Fix Ollama timeout in model_router.py and agent_runtime.py

**Files:**
- Modify: `eos_ai/model_router.py` (lines 168–179 `_check_availability`, add `_ollama_available()`)
- Modify: `eos_ai/agent_runtime.py` (line 258–261 `_call_ollama` error handler)

### 3A — model_router.py

The current code marks `ollama-qwen` as `available=True` because `api_key_env` is empty (line 172: `config.available = True`). This makes the router pick Ollama as a fallback for `FAST_RESPONSE` even when it isn't running, causing a 60-second hang.

- [ ] **Step 1: Add _ollama_available() to model_router.py**

In `eos_ai/model_router.py`, after the `MODEL_REGISTRY` dict (after line 159), add:

```python

def _ollama_available() -> bool:
    """Returns True only if Ollama HTTP endpoint responds within 2s."""
    try:
        import requests as _req
        resp = _req.get(
            'http://localhost:11434/api/tags',
            timeout=2,
        )
        return resp.status_code == 200
    except Exception:
        return False
```

- [ ] **Step 2: Update _check_availability() to use the health check**

In `eos_ai/model_router.py`, in `ModelRouter._check_availability()`, replace:

```python
            if not config.api_key_env:
                # Local model (Ollama) — always available
                config.available = True
```

with:

```python
            if not config.api_key_env:
                # Local model (Ollama) — check if actually running
                config.available = (
                    config.provider == ModelProvider.OLLAMA
                    and _ollama_available()
                )
```

- [ ] **Step 3: Verify model_router imports cleanly**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
from eos_ai.model_router import get_router, TaskType
router = get_router()
print(router.get_status())
"
```

Expected: `ollama-qwen` shows `❌` (Ollama not running on VPS), all other models based on key availability.

### 3B — agent_runtime.py

The current `_call_ollama` raises `RuntimeError` on `ConnectionError`, which propagates up through `run()` and crashes the morning cycle. We need it to return an empty string and log instead.

- [ ] **Step 4: Add pre-flight check to _call_ollama in agent_runtime.py**

In `eos_ai/agent_runtime.py`, find `def _call_ollama` (line 237). Replace the entire method:

```python
    def _call_ollama(
        self, model: str, prompt: str, system: str | None,
        max_tokens: int = 1000,
    ) -> str:
        import requests
        # Fast pre-flight: skip 60s timeout if Ollama isn't running
        try:
            requests.get('http://localhost:11434/api/tags', timeout=2)
        except Exception:
            print('[AgentRuntime] Ollama not reachable — skipping local model')
            return ''
        try:
            payload: dict = {
                'model': model,
                'prompt': prompt,
                'stream': False,
                'options': {'num_predict': max_tokens},
            }
            if system:
                payload['system'] = system
            resp = requests.post(
                'http://localhost:11434/api/generate',
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()['response']
        except Exception as e:
            print(f'[AgentRuntime] Ollama call failed: {e}')
            return ''
```

Note: The caller (around lines 470–528) already handles empty string returns by checking `output` — no further changes needed there.

- [ ] **Step 5: Verify agent_runtime imports cleanly**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
from eos_ai.agent_runtime import AgentRuntime
print('import ok')
"
```

Expected: `import ok`

- [ ] **Step 6: Commit**

```bash
cd /opt/OS
git add eos_ai/model_router.py eos_ai/agent_runtime.py
git commit -m "fix: skip ollama when not running — health check in model_router and agent_runtime"
```

---

## Task 4: Integration test

- [ ] **Step 1: Test push_all_ventures end-to-end**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
from eos_ai.context import load_context_from_env
from eos_ai.notion_sync import push_all_ventures
ctx = load_context_from_env()
print('Testing push_all_ventures...')
result = push_all_ventures(ctx)
print(f'Result: {result}')
"
```

Expected: `Result: {'personal_brand': {'pushed': N}, 'lyfe_institute': {'pushed': N}, 'empyrean_creative': {'pushed': N}}` — no exceptions.

- [ ] **Step 2: Run the poller manually**

```bash
python3 /opt/OS/scripts/notion_sync_poller.py
```

Expected: Push counts printed per venture, `Done.` at end.

- [ ] **Step 3: Test model router doesn't hang on Ollama**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
from eos_ai.model_router import get_router, TaskType
router = get_router()
model = router.route(TaskType.FAST_RESPONSE)
print(f'Routed to: {model.model_id if model else \"None\"}')
print(f'Provider: {model.provider.value if model else \"None\"}')
"
```

Expected: routes to `claude-haiku` or `groq-llama`, NOT `qwen2.5:3b`.

- [ ] **Step 4: Restart Discord service**

```bash
docker restart os-discord
sleep 10
docker logs os-discord --tail 10
```

Expected: `online` or `started`, no `Traceback`.

- [ ] **Step 5: Restart webhook service**

```bash
docker restart os-webhook
sleep 5
docker logs os-webhook --tail 10
```

Expected: no `Traceback`.

---

## Self-Review

### Spec coverage
- ✅ Fix 1: Diagnosis + debug output + idempotent re-run
- ✅ Fix 2A: `notion_page_id` column migration
- ✅ Fix 2B: Executor wires `write_task()` after each task
- ✅ Fix 2C: `push_pending_tasks_to_notion` + `push_all_ventures` in `notion_sync.py`
- ✅ Fix 2C poller: `notion_sync_poller.py` created
- ✅ Fix 3 model_router: `_ollama_available()` + `_check_availability()` fix
- ✅ Fix 3 agent_runtime: `_call_ollama` pre-flight check, returns `''` instead of raising

### Type consistency
- `write_task()` called with `name=` (not `title=`) throughout — matches existing signature at `notion_sync.py:130`
- `get_conn(ctx.org_id)` used consistently — matches existing pattern
- `push_all_ventures(ctx)` returns `dict[str, dict]` — matches caller in poller

### Placeholder scan
- No TBDs, no TODOs, no "implement later"
- All code is complete and matches existing signatures
