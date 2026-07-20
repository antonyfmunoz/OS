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
  from substrate.state.context.context import try_load_context_from_env
  ctx = try_load_context_from_env()
  if ctx:
      print(f'Org: {ctx.org_id}')
      print(f'Active venture: {ctx.active_venture_id}')
  else:
      print('Context: UMH_ORG_ID/UMH_USER_ID not set')
  "

## Before making any significant change

1. Read the current state of the file you're modifying — never assume
2. Check if the component is confirmed working in the session history
3. For HIGH/CRITICAL changes, review the convergence roadmap:
   data/audits/2026-05-25_exhaustive_codebase_audit.md (Section 22)

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

- substrate/types.py                     — CONFIRMED_RUNTIME (single type system, 30+ Pydantic models)
- substrate/__init__.py                  — CONFIRMED_RUNTIME (Substrate public API)
- substrate/control_plane/governance.py  — CONFIRMED_RUNTIME (deterministic risk classification)
- substrate/control_plane/router/__init__.py — CONFIRMED_RUNTIME (signal lifecycle orchestration; router.py became the router/ package — stale path caught by grounded self-model run-20260719T230853Z)
- substrate/execution/spine.py           — CONFIRMED_RUNTIME (LLM/cognitive 8-stage pipeline — NOT the canonical mutation runtime; see substrate/organism/canonical_runtime.py)
- substrate/organism/canonical_runtime.py — CONFIRMED_RUNTIME (WP-P1-001: declares the one canonical operation runtime: governed_mutation → MutationRouter → GovernedExecutionSpine)
- substrate/execution/trace.py           — CONFIRMED_RUNTIME (trace recording + Neon persistence)
- substrate/execution/feedback.py        — CONFIRMED_RUNTIME (quality scoring + learning loop)
- adapters/models/model_router.py        — CONFIRMED_RUNTIME (intelligence routing, call_with_fallback)
- adapters/models/llm_adapter.py         — CONFIRMED_RUNTIME (LLM adapter wrapping model_router)
- transports/discord/signal_factory.py   — CONFIRMED_RUNTIME (message → SignalEnvelope)
- services/discord_bot.py                — CONFIRMED_RUNTIME (primary Discord bot, os-discord container)

## Current build phase
Single-user validation phase — one org, multiple ventures.
Org and venture IDs loaded from BIS at runtime.
Focus: proving the system works before UI layer.

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

## Ingestion + cc_sdk — see CLAUDE.md Intelligence Routing and Ingestion sections
