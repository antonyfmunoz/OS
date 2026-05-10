# Root Semantic Migration Audit: /opt/OS → /opt/UMH

**Date:** 2026-05-10
**Status:** AUDIT COMPLETE — awaiting approval
**Phase:** R0 (audit only, no changes)

---

## Semantic Rationale

UMH (Universal Mastery Harness) is the true substrate/harness.
EOS (EntrepreneurOS) is a projection/application surface running on UMH.

The root path `/opt/OS` is legacy naming drift from when EOS was conflated
with the harness itself. The canonical root should be `/opt/UMH`.

---

## Reference Summary

| Metric | Count |
|---|---|
| Total /opt/OS references (live) | 4,695 |
| Files impacted (live) | 1,444 |
| Archive references (excluded) | 646 |
| Archive files (excluded) | 271 |
| Crontab entries | 30 |
| Docker volume mounts | 5 |
| Claude hook/permission refs | 17 |
| sys.path.insert refs | 800 |
| load_dotenv refs | 92 |
| Path() constructor refs | 322 |

---

## Classification Matrix

| Category | Files | References | Risk Level |
|---|---|---|---|
| python-core (eos_ai/) | 42 | 90 | MEDIUM |
| python-transport (eos_ai/transport/) | 19 | 49 | LOW |
| python-substrate (core/) | 62 | 146 | MEDIUM |
| shell-script (scripts/) | 192 | 486 | MEDIUM |
| docker-deployment (services/, compose) | 8 | 42 | CRITICAL |
| test-fixture (tests/) | 195 | 374 | LOW |
| dead-test (tests/legacy/) | 405 | 991 | NONE |
| documentation (docs/) | 115 | 953 | LOW |
| data-artifact (data/) | 174 | 822 | LOW |
| obsidian-vault (10_Wiki/, vault/) | 24 | 26 | MEDIUM |
| claude-config (.claude/) | 33 | 95 | CRITICAL |
| skill-doc (skills/) | 154 | 553 | LOW |
| parser (parsers/) | 4 | 4 | LOW |
| config (config/) | 1 | 1 | LOW |
| repo-root (root files) | 12 | 51 | MEDIUM |
| other | 4 | 12 | LOW |

---

## Critical Finding: Core Runtime is Path-Clean

The following runtime-critical modules have **ZERO** hardcoded `/opt/OS`
references and use relative imports or environment-based resolution:

- `eos_ai/cognitive_loop.py`
- `eos_ai/agent_runtime.py`
- `eos_ai/model_router.py`
- `eos_ai/gateway.py`
- `eos_ai/memory.py`
- `eos_ai/db.py`
- `eos_ai/context.py`

This means the cognitive loop, LLM dispatch, message classification,
memory persistence, and database access will work at `/opt/UMH` with
**zero code changes** — only `sys.path.insert` callers need updating.

---

## Existing Migration Vector: EOS_ROOT env var

Three TME paths modules already use the pattern:

```python
EOS_ROOT = Path(os.environ.get("EOS_ROOT", "/opt/OS"))
```

Files:
- `core/tool_mastery_manager/paths.py`
- `core/tool_mastery_research_agent/paths.py`
- `core/tool_mastery_author_agent/paths.py`

This is the natural precursor to `UMH_ROOT`. The migration strategy is to
generalize this pattern across all path-dependent code.

---

## Highest Risk Files

| File | Refs | Risk | Reason |
|---|---|---|---|
| docker-compose.yml | 7 | CRITICAL | Volume mounts for all 5 services |
| .claude/settings.json | 17 | CRITICAL | Permissions + hooks (all hardcoded) |
| crontab (system) | 30 | HIGH | All scheduled tasks |
| services/discord_bot.py | 4 | HIGH | Live service subprocess calls |
| scripts/orchestrator.py | 1 | HIGH | Orchestration root path |
| scripts/scheduled/nightly_maintenance.sh | 16 | MEDIUM | Nightly scripts |
| eos_ai/agent_hierarchy.py | 7 | MEDIUM | Skill/config path constants |
| eos_ai/context_builder.py | 5 | MEDIUM | Context path constants |

---

## Blocker Analysis

### Runtime Import Blockers
- 800 `sys.path.insert(0, '/opt/OS')` calls across the codebase
- These are the primary Python import mechanism
- All can be resolved via env var: `sys.path.insert(0, os.environ.get('UMH_ROOT', '/opt/OS'))`

### Docker/Deployment Blockers
- 5 volume mounts in docker-compose.yml: `/opt/OS:/app`
- 2 log path mounts: `/opt/OS/logs:/opt/OS/logs`
- Services internally use `/app` (already abstracted), but host mounts are hardcoded

### Cron/Tmux Blockers
- 30 crontab entries with `cd /opt/OS` or `/opt/OS/scripts/` paths
- 5 tmux sessions (already renamed: umh_core, umh_tests, umh_worker, dex_main, dex_builder_main)
- Tmux session names already reflect UMH naming — ahead of filesystem

### Obsidian/Vault Blockers
- 24 files, 26 references
- Obsidian workspace config references `/opt/OS` as vault root
- `.obsidian/` plugins may cache paths

### Claude/Cursor Blockers
- `.claude/settings.json`: 17 references (permissions, hooks)
- 30 skill/command files with paths
- Claude project memory at `~/.claude/projects/-opt-OS/` — path is derived from cwd
- Renaming root will create a new project context in Claude Code

### Ingestion Blockers
- **NO** — the convergence waves (W0-W6) have made the architecture ingestion-safe
- Path references in data artifacts are historical snapshots, not runtime dependencies

### Discord Service Blockers
- **YES** — 4 hardcoded paths in services/discord_bot.py
- All are subprocess calls or Path constants, not import paths
- Fixable with env var resolution

---

## Staged Migration Plan

### Wave R0 — Path Audit (THIS DOCUMENT)
- Complete repository scan ✅
- Classification matrix ✅
- Risk assessment ✅
- Machine-readable report ✅

### Wave R1 — Introduce UMH_ROOT env var
- Add `UMH_ROOT=/opt/OS` to eos_ai/.env and services/.env
- Create `core/paths.py` with: `UMH_ROOT = Path(os.environ.get('UMH_ROOT', os.environ.get('EOS_ROOT', '/opt/OS')))`
- Update 3 existing TME paths.py files to use UMH_ROOT → EOS_ROOT → /opt/OS fallback chain
- Zero runtime change (same resolved path)
- Validation: all services import clean, all tests pass

### Wave R2 — Scripts use UMH_ROOT
- Update `scripts/orchestrator.py` `_REPO_ROOT` to use env var
- Update `sys.path.insert` calls in scripts/ to use env var with fallback
- Update load_dotenv calls in scripts/ to use env var with fallback
- Validation: cron-executed scripts still resolve correctly

### Wave R3 — Python path resolution helpers
- Create `umh_paths.py` (or extend core/paths.py) with helper functions:
  - `get_root() → Path` (UMH_ROOT → EOS_ROOT → /opt/OS)
  - `get_env_path(name) → Path` (resolves .env files)
  - `get_data_path(rel) → Path`
  - `get_logs_path(rel) → Path`
- Migrate eos_ai/ modules from hardcoded paths to helper calls
- Validation: import graph clean, discord dry-run passes

### Wave R4 — Docker/compose dual-path compatibility
- Update docker-compose.yml volumes: `${UMH_ROOT:-/opt/OS}:/app`
- Update log mount: `${UMH_ROOT:-/opt/OS}/logs:${UMH_ROOT:-/opt/OS}/logs`
- Update .env with UMH_ROOT
- Validation: `docker compose config` shows correct mounts, services restart clean

### Wave R5 — Documentation and system status
- Update CLAUDE.md, .claude/CLAUDE.md, ARCHITECTURE.md
- Update .claude/settings.json paths to use env var or ${UMH_ROOT}
- Update .claude/skills/ and .claude/commands/
- Update docs/system/ references
- Validation: Claude Code session starts clean

### Wave R6 — Evaluate eos_ai semantic ownership
- Assess whether `eos_ai/` should become `umh_ai/` or `harness/`
- Decision: likely NO — eos_ai is the application intelligence layer, not the harness
- The harness is the repo root + core/ + scripts/ orchestration
- eos_ai correctly represents the EOS projection's brain
- If rename needed: same shim pattern as substrate→transport

### Wave R7 — Controlled filesystem move
- Option A (symlink): `mv /opt/OS /opt/UMH && ln -s /opt/UMH /opt/OS`
- Option B (direct): `mv /opt/OS /opt/UMH` with env var already resolving
- Crontab: `sed -i 's|/opt/OS|/opt/UMH|g'` (after symlink confirmed)
- Tmux: sessions already named umh_* — just update working dirs
- Validation: all services start, cron fires, Claude session works

### Wave R8 — Service restart validation
- `docker compose down && docker compose up -d`
- Verify all 4 containers healthy
- Verify discord bot responds
- Verify cron jobs fire next cycle
- Verify Claude Code session in new path
- 24h stabilization window

### Wave R9 — Remove OS compatibility
- Remove symlink `/opt/OS → /opt/UMH` (if used)
- Remove EOS_ROOT fallback from env var chain (UMH_ROOT only)
- Remove `/opt/OS` from .claude/settings.json permissions
- Clean remaining documentation references
- Archive this audit document

---

## Rollback Strategy

| Wave | Rollback Method |
|---|---|
| R1 | Unset UMH_ROOT, EOS_ROOT fallback activates |
| R2 | git revert (scripts still have /opt/OS fallback) |
| R3 | git revert (helpers are additive) |
| R4 | git revert + `docker compose up` with old compose |
| R5 | git revert (docs only) |
| R6 | Shim pattern (same as substrate→transport) |
| R7 | `ln -sfn /opt/UMH /opt/OS` or `mv /opt/UMH /opt/OS` |
| R8 | `docker compose down && docker compose up -d` |
| R9 | Re-add symlink |

Instant rollback at any point: `ln -sfn /opt/UMH /opt/OS` restores
all hardcoded paths immediately.

---

## eos_ai Semantic Assessment

`eos_ai/` does NOT need renaming. Analysis:

- `eos_ai/` is the **application intelligence layer** — it contains EOS-specific
  cognitive loop, agent hierarchy, gateway, memory, primitives
- The **harness/substrate** is `core/` (substrate v1 domains) + `scripts/`
  (orchestration) + `services/` (deployment)
- `eos_ai/transport/` is correctly named — it's the transport layer between
  the EOS application and the UMH substrate
- Renaming `eos_ai/` to `umh_ai/` would be semantically incorrect — UMH is the
  harness, not the AI brain. The AI brain belongs to EOS.

The correct semantic model is:
```
/opt/UMH/              ← UMH harness (repo root)
  core/                ← substrate v1 domains (UMH-owned)
  scripts/             ← orchestration (UMH-owned)
  services/            ← deployment (UMH-owned)
  eos_ai/              ← EOS application intelligence (EOS-owned, hosted by UMH)
  eos_ai/transport/    ← transport bridge (interface between EOS ↔ UMH)
```

---

## Final Assessment

| Question | Answer |
|---|---|
| Can rename /opt/OS now? | **NO** |
| Recommended first wave | **R1** (env var introduction) |
| Runtime-critical path references | **5 files** (discord_bot, orchestrator, agent_hierarchy, context_builder, system_health) |
| Docker/deployment blockers | **7 mounts** in docker-compose.yml |
| Cron blockers | **30 entries** |
| Script blockers | **192 files, 486 references** |
| Python blockers | **123 files, 285 references** (core + transport + substrate) |
| Docs-only references | **115 files, 953 references** |
| Archive/dead references | **676 files, 1,637 references** (dead-test + archive) |
| Ingestion blockers | **NO** |
| Discord service blockers | **YES** (4 hardcoded paths, fixable) |
| Rollback plan complete | **YES** (symlink instant-rollback at every wave) |
| Core cognitive loop affected | **NO** (zero /opt/OS refs in 7 core modules) |
| Estimated total migration effort | **R1-R5: low risk, ~2 sessions. R7: medium risk, 1 session + 24h stabilization** |
