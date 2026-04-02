# Developer Agent — .claude Context

You are operating as the Developer Agent for EOS.
See /opt/OS/CLAUDE.md for your full soul document and identity.

This file contains .claude-specific context: session protocols,
risk classes, confirmed working components, and project structure.

---

## What this project is
EntrepreneurOS is a production AI business operating system.
You are modifying a live system that a founder depends on daily.
Every change is real. Every deploy affects a running service.

## Session resume
At the start of EVERY Claude Code session run:
  python3 -c "
  import sys; sys.path.insert(0, '/opt/OS')
  from eos_ai.session_state import SessionState
  print(SessionState.get_resume_context())
  "

At the END of every significant build run:
  python3 -c "
  import sys; sys.path.insert(0, '/opt/OS')
  from eos_ai.session_state import SessionState
  SessionState.save(
    phase='[current phase]',
    last_completed='[what just finished]',
    in_progress=None,
    next_steps=['[next fix]', '[fix after]'],
    files_modified=['[files changed]']
  )
  print('State saved')
  "

## Before making any significant change

1. Read the current state of the file you're modifying — never assume
2. Check if the component is confirmed working in the session history
3. For HIGH/CRITICAL changes, call the validator:
   python3 -c "
   import sys; sys.path.insert(0, '/opt/OS')
   from eos_ai.context import load_context_from_env
   from eos_ai.system_context import SystemContext
   ctx = load_context_from_env()
   sc = SystemContext(ctx, 'claude_code')
   result = sc.validate_architectural_change(
     '[describe the change here]')
   print(result)
   "

## Risk classes for code changes
LOW:      Adding new files, new methods, new features
MEDIUM:   Modifying existing methods, adding parameters
HIGH:     Changing core infrastructure (gateway, cognitive_loop,
          agent_runtime, memory, authority_engine)
CRITICAL: Schema migrations, removing working features, changing
          RLS policies, data moves, dropping tables

## Rules
- Never modify a confirmed-working component without reading it first
- Never run migrations without checking row counts first
- Always test after changes:
  python3 -c "from eos_ai.[module] import [Class]; print('import ok')"
- If the app crashes mid-build, run the audit pattern to check
  what was completed
- Telegram bot restarts require:
  pkill -f telegram_control &&
  python3 /opt/OS/services/telegram_control.py

## Known issues (do not attempt to fix without reading first)
- None currently. (gateway.py raw_prompt → input was confirmed fixed:
  both loop.run() calls at lines 537 and 555 already use input=prompt.
  Verified 2026-03-26.)

## Confirmed working components (do not break)
- eos_ai/db.py                 — Neon connection with RLS
- eos_ai/memory.py             — all writes go to Neon
- eos_ai/agent_runtime.py      — multi-model router live
- eos_ai/cognitive_loop.py     — 8-stage loop working, param=input
- eos_ai/authority_engine.py   — 4 risk classes working
- eos_ai/portfolio_advisor.py  — board view working
- eos_ai/orchestrator.py       — 6am cron + morning cycle
- eos_ai/model_preferences.py  — business context routing
- eos_ai/media_processor.py    — voice synthesis 303KB confirmed
- services/telegram_control.py — natural language + media routing

## Current build phase
Single-user validation phase — one org, multiple ventures.
Org and venture IDs loaded from BIS at runtime.
Focus: proving the system works before UI layer.

## Project structure
/opt/OS/
  eos_ai/          — AI intelligence layer (Python)
  saas/        — SaaS product (TypeScript/React)
  services/      — automation scripts
  03_CRM/          — pipeline and lead management
  orchestrator/ — scheduled tasks and approvals
  .claude/         — Claude Code project config (this file)

## Docker restart: use `docker restart`, not `docker compose restart`
Use `docker restart [container_name]` for individual container restarts.
`docker compose restart [service]` uses the service alias from compose.yml
but `docker restart` uses the actual container name (set via `container_name:`).
Both exist — `os-monitor` is the container name. Use `docker restart os-monitor`.

## Instagram monitor notes
- Direct `/accounts/login/` URL returns blank page from VPS IPs (bot detection).
  Use root `https://www.instagram.com/` — login form renders correctly there.
- Apify proxy uses `INSTAGRAM_USE_PROXY=true` flag. Default is direct (no proxy).
  Proxy returns 403 when RESIDENTIAL group credits are depleted.

## Master Specification
Read /opt/OS/ARCHITECTURE.md before any significant build decision.
