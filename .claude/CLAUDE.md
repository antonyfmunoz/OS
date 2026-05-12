# Developer Agent — .claude Context

You are operating as the Developer Agent for UMH (Universal Mastery Hierarchy).
See /opt/OS/CLAUDE.md for your full soul document and identity.

This file contains .claude-specific context: session protocols,
risk classes, confirmed working components, and project structure.

---

## What this project is
UMH is a production AI intelligence substrate.
EntrepreneurOS (EOS) is one application/projection built on UMH.
You are modifying a live system that a founder depends on daily.
Every change is real. Every deploy affects a running service.

## Session resume
At the start of EVERY Claude Code session run:
  python3 -c "
  import sys; sys.path.insert(0, '/opt/OS')
  from runtime.session_state import SessionState
  print(SessionState.get_resume_context())
  "

At the END of every significant build run:
  python3 -c "
  import sys; sys.path.insert(0, '/opt/OS')
  from runtime.session_state import SessionState
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
   from runtime.context import load_context_from_env
   from runtime.system_context import SystemContext
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
  python3 -c "from runtime.[module] import [Class]; print('import ok')"
- If the app crashes mid-build, run the audit pattern to check
  what was completed
- Telegram bot restarts require:
  pkill -f telegram_control &&
  python3 /opt/OS/services/telegram_control.py

## Known issues (do not attempt to fix without reading first)
- None currently. (gateway.py raw_prompt → input was confirmed fixed:
  both loop.run() calls at lines 537 and 555 already use input=prompt.
  Verified 2026-03-26.)

## Component status (phase 96.8BI truth correction)
Status taxonomy:
  CONFIRMED_RUNTIME  — imports clean, used by running services, verified
  PARTIALLY_VERIFIED — imports clean, logic present, no runtime proof
  UNVERIFIED         — exists, compiles, never tested end-to-end
  PROOF_ONLY         — generates reports/proofs, not wired into runtime
  DORMANT            — code exists, modules not imported by anything live
  DEPRECATED         — scheduled for removal

- runtime/db.py                 — CONFIRMED_RUNTIME (Neon conn, used by all services)
- runtime/memory.py             — CONFIRMED_RUNTIME (AgentMemory + ConversationMemory, Neon writes)
- runtime/agent_runtime.py      — CONFIRMED_RUNTIME (multi-model router, discord bot uses it)
- runtime/cognitive_loop.py     — PARTIALLY_VERIFIED (imports clean, 8-stage loop, param=input)
- runtime/authority_engine.py   — PARTIALLY_VERIFIED (imports clean, 4 risk classes)
- runtime/portfolio_advisor.py  — PARTIALLY_VERIFIED (imports clean, board view logic)
- runtime/orchestrator.py       — PARTIALLY_VERIFIED (EOSOrchestrator class, cron logic present)
- runtime/model_preferences.py  — CONFIRMED_RUNTIME (ModelPreferences, used by model_router)
- runtime/media_processor.py    — PARTIALLY_VERIFIED (imports clean, voice synthesis logic)
- services/telegram_control.py — DORMANT (not running in Docker, service disabled)
- services/discord_bot.py      — CONFIRMED_RUNTIME (os-discord container, daily use)
- runtime/work_state.py         — CONFIRMED_RUNTIME (pressure tracking, used by discord bot)
- core/workstation/constitutional_*_v1.py — PROOF_ONLY (report generators, not runtime-enforced)

## Current build phase
Single-user validation phase — one org, multiple ventures.
Org and venture IDs loaded from BIS at runtime.
Focus: proving the system works before UI layer.

## Project structure
/opt/OS/  (repository root — pending rename to /opt/UMH)
  core/            — substrate contracts, primitives, invariants, governance foundations
  runtime/         — single live runtime (cognition, execution, memory, transport)
  eos_ai/          — dead shim layer (zero consumers, pending removal)
  services/        — daemons and interfaces (discord_bot.py, etc.)
  scripts/         — operator tooling (cron scripts, utilities)
  saas/            — SaaS product (TypeScript/React) — EOS application projection
  03_CRM/          — pipeline and lead management — EOS application data
  orchestrator/    — scheduled tasks and approvals
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

## Ingestion pipeline status
PROOF_OF_LIFE — one real document completed full cycle on 2026-05-12.
Proof: data/runtime/canonical_memory_store/proofs/2026-05-12_ingestion_e2e/
Single proof; not yet production volume.

## Generic ingestion orchestrator
AVAILABLE — runtime.ingestion.GenericIngestionOrchestrator +
LocalFileSource. First non-GWS ingestion path. Proof:
data/runtime/canonical_memory_store/proofs/2026-05-12_orchestrator_e2e/
FullLiveIngestionSpine remains the GWS-specific path.
