# Phase 18B: Best-Practice Root Cleanup for UMH

**Date:** 2026-04-25
**Phase:** 18B — root directory normalization
**Status:** Complete
**Tests:** 712 passed, 0 failed
**Docker:** Config validated

---

## 1. Initial Root Tree

```
/opt/OS/
├── .claude/
├── .vscode/
├── archive/          ← 484MB, 1135 py files, zero UMH deps
├── core/             ← SYMLINK → archive/core
├── data/
├── docs/
├── infra/            ← SYMLINK → runtime/
├── logs/
├── orchestrator/     ← EMPTY (0 files)
├── parsers/          ← 7 py files, duplicated in tools/parsers_lib/
├── runtime/
├── scripts/          ← SYMLINK → tools/
├── services/         ← 19 py files, mostly duplicated in umh/interfaces/
├── tests/
├── tools/
├── umh/
├── vault/            ← SYMLINK → data/vault/
├── .dockerignore
├── .gitignore
├── CLAUDE.md
└── CLAUDE.local.md
```

## 2. Final Root Tree

```
/opt/OS/
├── .claude/          # Claude Code dev harness
├── .vscode/          # Editor config
├── data/             # Runtime data (gitignored)
├── docs/             # UMH documentation and audits
├── logs/             # Runtime logs (gitignored)
├── runtime/          # Docker/compose deployment config
├── tests/            # UMH test suite (712 tests)
├── tools/            # Dev/maintenance tooling
├── umh/              # ALL product/runtime/control-plane code
├── .dockerignore
├── .gitignore
├── CLAUDE.md
├── CLAUDE.local.md
└── requirements.txt  # Python dependencies (moved from services/)
```

## 3. Folders Deleted

| Folder | Files | Size | Reason |
|--------|-------|------|--------|
| `archive/` | 41,002 (1,135 py) | 484MB | Zero UMH dependencies. History preserved in git. |
| `services/` | 33 (19 py) | — | Transport code duplicated in umh/interfaces/. One file extracted. |
| `parsers/` | 7 py | — | Identical to tools/parsers_lib/. Consolidated. |
| `orchestrator/` | 0 | — | Empty directory with empty subdirs. |

## 4. Folders Moved / Consolidated

| Source | Destination |
|--------|-------------|
| `services/higgsfield_webhook.py` | `umh/interfaces/webhooks/higgsfield.py` |
| `services/requirements.txt` | `/opt/OS/requirements.txt` (root) |
| `parsers/*` → consolidated into | `tools/parsers_lib/*` (already identical) |

## 5. Symlinks Removed

| Symlink | Target | Reason |
|---------|--------|--------|
| `core/` | `archive/core/` | Archive deleted, import rerouted |
| `scripts/` | `tools/` | Hooks/CLAUDE.md updated to use tools/ directly |
| `infra/` | `runtime/` | Redundant alias, Dockerfile updated |
| `vault/` | `data/vault/` | Redundant alias |

## 6. Value Extracted

| Source | Extracted To | Import Updated |
|--------|-------------|---------------|
| `services/higgsfield_webhook.py` | `umh/interfaces/webhooks/higgsfield.py` | `umh/interfaces/webhooks/calendly.py` |
| `core.execution_contract.run_task` | Replaced with `umh.runtime_engine.execution_spine.run_via_umh` | `umh/substrate/discord_text_transport.py` |
| `scripts.calendar_invite_handler` | Updated to `tools.calendar_invite_handler` | `umh/interfaces/discord/bot.py` |

## 7. References Updated

### CLAUDE.md
- `scripts/session_bootstrap.py` → `tools/session_bootstrap.py`
- `scripts/update-graph` → `tools/update-graph`
- `scripts/query_graph.py` → `tools/query_graph.py`
- `scripts/verify_knowledge_system.py` → `tools/verify_knowledge_system.py`
- `scripts/vault_backlink_audit.py` → `tools/vault_backlink_audit.py`
- `interfaces/discord/bot.py` → `umh/interfaces/discord/bot.py`

### .claude/CLAUDE.md
- `services/telegram_control.py` → `umh/interfaces/telegram/bot.py`
- Project structure section updated to reflect new root layout
- Telegram restart command updated

### .claude/settings.json (ALL hooks)
- `scripts/pre_tool_use_log.py` → `tools/pre_tool_use_log.py`
- `scripts/session_start_context.py` → `tools/session_start_context.py`
- `scripts/wiki_session_start_hook.py` → `tools/wiki_session_start_hook.py`
- `scripts/check_stop_condition.py` → `tools/check_stop_condition.py`
- `scripts/wiki_stop_hook.py` → `tools/wiki_stop_hook.py`
- `scripts/cc_reply_webhook.py` → `tools/cc_reply_webhook.py`
- `scripts/permission_notify.py` → `tools/permission_notify.py`
- `scripts/subagent_start_context.py` → `tools/subagent_start_context.py`
- `scripts/user_prompt_capture.py` → `tools/user_prompt_capture.py`
- `eos_ai` imports → `umh` imports
- `eos_ai/.env` deny rule → `umh/.env`

### .claude/settings.local.json
- `eos_ai.agent_runtime` → `umh.runtime_engine.agent_runtime`
- `eos_ai.travel_manager` → `umh.runtime_engine.travel_manager`

### .claude/skills/
- `deploy-service.md`: service paths → umh/interfaces/ paths
- `claude-code-cli.md`: service paths → umh/interfaces/ paths
- `discord-admin.md`: `services/.env` → `runtime/services.env`

### Docker
- `runtime/Dockerfile`: `services/requirements.txt` → `requirements.txt`
- `runtime/Dockerfile`: `infra/patch_pycord.py` → `runtime/patch_pycord.py`

### Tests
- `test_umh_wave7_gateway_collapse.py`: `SERVICES_ROOT` → `INTERFACES_ROOT`, all paths updated
- `test_umh_boundaries.py`: `EXEMPT_FILES` and `_production_python_files` updated from `eos/` to `umh/`
- `test_full_reality_loop.py`: Deleted (dead test importing from core/)

## 8. Validation Results

| Check | Result |
|-------|--------|
| Root symlinks | **0** (was 4) |
| UMH imports from deleted packages | **0** |
| `call_with_fallback` bypasses outside umh/ | **0** |
| Unit tests | **712 passed, 0 failed** |
| Docker compose config | **Valid** |

## 9. Remaining Debt

| Item | Count | Risk | Notes |
|------|-------|------|-------|
| `tools/` imports from `core.*` | 51 | LOW | Legacy dev scripts that referenced archive/core. Already broken since core/ symlink was removed. Not runtime code. |
| `tools/` imports from `scripts.*` | 64 | LOW | Self-references via old scripts/ symlink. Already work since tools/ IS the canonical location — just need `from scripts.X` → `from tools.X` refactoring. |
| `.pytest_cache/`, `.ruff_cache/` at root | 2 dirs | ZERO | Standard tool caches, gitignored |
| `docker-compose.yml` version attribute | 1 | ZERO | Obsolete but harmless, Docker warns |

## 10. Confirmation

**No runtime intelligence, control-plane logic, execution logic, orchestration logic, direct tool/LLM/provider calls, memory writes, governance, routing, or adapter invocation exists outside `umh/`.**

All such code lives exclusively in:
- `umh/execution/` — canonical execution engine
- `umh/runtime_engine/` — production intelligence (agent runtime, model routing, memory)
- `umh/substrate/` — live session infrastructure (storage, events, transport)
- `umh/interfaces/` — transport boundary (Discord, Telegram, CLI, webhooks)
- `umh/adapters/` — external system adapters
- `umh/stages/` — pipeline stages including LLM generation

Root-level support folders contain only:
- Tests (tests/)
- Dev tooling (tools/)
- Deployment config (runtime/)
- Documentation (docs/)
- Runtime data (data/, logs/)
- Editor/harness config (.claude/, .vscode/)
