---
name: claude-code-cli
description: Use when operating as the Developer Agent inside EOS — session management, deploy decision tree, protocol layers.
allowed-tools: Bash, Read
---

# Claude Code CLI — Best Practices

## When to use this skill
Any time you are operating as the Developer Agent inside EOS.
Read PHILOSOPHY.md before building any feature.

## Session management
- Always start with `/session-start` to load full EOS context
- Use `/compact` at ~50% context window
- Use `/clear` when switching between unrelated tasks
- Save session state at end of significant builds

## Memory system
```
CLAUDE.md           — project-level soul doc (loaded every session)
.claude/CLAUDE.md   — .claude-specific context (loaded every session)
.claude/skills/     — on-demand skill files (read when relevant)
~/.claude/MEMORY.md — global auto-memory (first 200 lines loaded every session)
```

## EOS commands
```
/status             — full system state
/deploy [service]   — targeted service restart
/test-agent         — test single agent end-to-end
/test-all-agents    — test all 4 agents
/voice-debug        — voice pipeline diagnostics
/session-start      — load full EOS context
/primitive-check    — validate primitive applicability
/eos-audit          — full system audit
/eos-build          — build new feature
/eos-fix            — fix broken module
/eos-deploy         — rebuild + restart services
/eos-sync           — reload skills, user model, domains
```

## EOS protocols (always follow)

**Before any change:**
1. Read the module being changed — never assume
2. Check if what you're building already exists
3. Understand which protocol layer is affected

**Before declaring done:**
1. Import check: `python3 -c "from substrate.[module] import [Class]"`
2. Relevant test passes
3. Deploy command provided to user

**Before any deploy:**
```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import substrate
print('imports: clean')
" 2>&1
```

## Four-layer protocol
```
Layer 0 → ai_identity.py      (universal — all instances)
Layer 1 → cognitive_loop.py   (platform — all EOS users)
Layer 2 → os_registry.py      (OS module — per subscription)
Layer 3 → BIS + database       (instance — per user/venture)
```
Never put Layer 3 data in Layer 0-2 files.

## Risk classes for code changes
```
LOW      — new files, new methods, new features
MEDIUM   — modifying existing methods, adding parameters
HIGH     — cognitive_loop, agent_runtime, gateway, authority_engine, memory
CRITICAL — schema migrations, dropping tables, removing working features
```

## Deploy decision tree
```
Python file changed (no Dockerfile change):
  docker compose restart [service]
  sleep 15
  docker logs [service] --tail 10

requirements.txt changed:
  docker compose build --no-cache [service]
  docker compose up -d [service]
  sleep 20
  docker logs [service] --tail 10
```

## Services
```
os-discord  → services/discord_bot.py
os-webhook  → services/higgsfield_webhook.py
os-operator → transports/api/operator.py
```

## Confirmed working — do not break
- `db.py`, `memory.py`, `cognitive_loop.py`, `agent_runtime.py`
- `authority_engine.py`, `gateway.py`, `embedding_engine.py`
- `orchestrator.py` (6am cron + proactive triggers)
- `business_instance.py` (BIS stage tracker, Neon-backed)
- `agent_teams.py` (6 teams, 25 sub-agents)
- `discord_bot.py` (NLP + voice routing, text working)

## Never do inside EOS
- Never hardcode founder/user-specific values in platform files
- Never skip Neon registration for new agents or skills
- Never rebuild Docker for Python-only changes
- Never deploy without import verification
- Never create new patterns when EOS has one
- Never put instance context (BIS, venture IDs) in platform files
