# CEO Agent Execution Loop — Implementation Plan
**Date:** 2026-03-31
**Branch:** feature/ea-system
**Goal:** Close the CEO agent execution loop — agent tasks get created, executed, and surfaced to Discord.

## Context

The CoordinationEngine and CEOAgent exist and work. `ceo_delegate()` creates tasks in Neon.
The missing link: nothing *executes* those tasks. This plan adds:
1. A cron worker that polls and executes pending agent tasks through the cognitive loop
2. A morning delegation function wired into the 6am orchestrator cycle
3. Discord commands to view and approve agent task results
4. An updated CEO agent soul doc reflecting the full execution loop

## Architecture
- `/opt/OS/scripts/agent_task_executor.py` — standalone cron script
- `/opt/OS/eos_ai/orchestrator.py` — add `run_ceo_morning_delegation()` after `run_full_morning_cycle()`
- `/opt/OS/13_Scripts/discord_bot.py` — add `!tasks`, `!approve_task`, `!agent_results` commands
- `/opt/OS/12_Agents/ceo_agent.md` — add Execution Loop section

## Key findings from codebase read
- `CoordinationEngine.get_task_queue(status='pending')` returns all tasks, filter by `assignee_type == 'agent'`
- `CoordinationEngine.complete_task(task_id, result)` marks done
- `CoordinationEngine.ceo_delegate(company_objective, venture_id)` already exists — returns `{total, ai_tasks, human_tasks, tasks_created}`
- `CognitiveLoop(ctx).run(input=..., agent=..., task_type=..., venture_id=...)` — confirmed param is `input=`
- `CEOAgent.detect_primitives()` and `check_and_evolve()` confirmed in ceo_agent.py
- `load_ventures_from_env()` returns `list` from `VENTURES_JSON` env var
- orchestrator `run_full_morning_cycle()` ends at line ~590, main block at 1557 calls it then `start_ambient_refresh_loop`
- Discord bot uses `@bot.command()` pattern, entry point at line 4423
- `/opt/OS/scripts/` exists, `/opt/OS/logs/` does NOT exist — cron must `mkdir -p`
- Log files currently go into `/opt/OS/scripts/` — executor log can go there too for consistency

## Tasks

### Task 1 — Create agent_task_executor.py
Create `/opt/OS/scripts/agent_task_executor.py` — polls tasks table for pending AI agent tasks, executes each through cognitive loop, marks complete, surfaces results to Discord.

**Full spec:** As provided in the user's prompt PART 1, verbatim.

Key implementation notes:
- `logs/` dir does not exist; cron should use `mkdir -p /opt/OS/scripts && python3 ...` and log to `/opt/OS/scripts/agent_executor.log`
- Discord surfacing uses `discord.Client` one-shot pattern (connect, send, close) — same as `dm_monitor.py`
- `GENERAL_CHANNEL_ID` from env `DISCORD_GENERAL_CHANNEL_ID`
- `MAX_TASKS_PER_RUN = 5`
- AGENT_MAP covers all 9 agents: sales, research, content, marketing, operations, outreach, intelligence, finance, customer_success
- `execute_agent_task()` loads soul doc, builds enriched prompt, calls `CognitiveLoop.run()`
- `requires_approval()` checks for action signals in description + output
- `run_executor()` — pulls queue, filters agent tasks, executes, logs to events table, sends Discord summary

Cron: `*/5 * * * * cd /opt/OS && python3 scripts/agent_task_executor.py >> /opt/OS/scripts/agent_executor.log 2>&1`

### Task 2 — Add run_ceo_morning_delegation() to orchestrator.py
Add function `run_ceo_morning_delegation(ctx, ventures)` to `/opt/OS/eos_ai/orchestrator.py` after `run_full_morning_cycle()`.

**Full spec:** As provided in the user's prompt PART 2, verbatim.

Key implementation notes:
- Import `datetime` from stdlib (already imported as `datetime.datetime` in orchestrator)
- Use `PDT = ZoneInfo('America/Los_Angeles')` — already imported in orchestrator scope or add locally
- `PortfolioAgent` (not `PortfolioAdvisor`) is the right class for `scan_all_ventures()` and `identify_binding_constraint()`
- Wire into `__main__` block after `run_full_morning_cycle(_ctx)`:
  ```python
  try:
      from eos_ai.context import load_ventures_from_env
      _ventures = load_ventures_from_env()
      run_ceo_morning_delegation(_ctx, _ventures)
  except Exception as e:
      print(f'[Morning] CEO delegation failed: {e}')
  ```
- The function itself uses `_send_discord_webhook()` which already exists in orchestrator

### Task 3 — Add Discord commands to discord_bot.py
Add three commands to `/opt/OS/13_Scripts/discord_bot.py` using `@bot.command()` pattern (not raw `on_message` handler).

**Full spec:** As provided in the user's prompt PART 3.

Commands:
- `!approve_task [task_id]` — finds event by partial task_id, marks approved in events table
- `!tasks` — shows pending task queue split by human vs AI
- `!agent_results` — shows last 24h agent task results with approval status

Key implementation notes:
- All three as `@bot.command()` decorators like existing commands
- Insert before the `# ─── Entry point ───` comment at line 4423
- Use `await ctx.reply()` not `await message.channel.send()`
- The `payload_json` in events may come back as dict (psycopg2 JSON auto-parses) or str — handle both

### Task 4 — Update CEO agent soul doc
Add "## Execution Loop" and "## What CEO Agent Never Does" sections to `/opt/OS/12_Agents/ceo_agent.md`.

**Full spec:** As provided in the user's prompt PART 4.

## Verification (after all parts)

```python
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.context import load_context_from_env
from eos_ai.coordination_engine import CoordinationEngine
from eos_ai.ceo_agent import CEOAgent

ctx = load_context_from_env()

coordination = CoordinationEngine(ctx)
queue = coordination.get_task_queue(status='pending')
print(f'Pending tasks in queue: {len(queue)}')

ceo = CEOAgent(ctx)
primitives = ceo.detect_primitives()
print(f'Primitives detected: {list(primitives.keys())}')

from scripts.agent_task_executor import (
    execute_agent_task, requires_approval, AGENT_MAP
)
print(f'Agent map loaded: {list(AGENT_MAP.keys())}')
print('all imports clean')
"

docker restart os-discord
docker restart os-webhook
```
