# Phase 18: Root Directory Triage Under UMH-Only Policy

**Date:** 2026-04-25
**Phase:** 18 of structural unification
**Type:** Analysis and plan only — no deletions performed
**Prior phases:** 15 (interface collapse), 16 (UMH purification), 17 (execution consolidation)

---

## 1. Root Inventory

| Path | Type | Files | Python | Size | Description |
|------|------|-------|--------|------|-------------|
| `umh/` | DIR | 532 | 529 | — | THE system. Universal Meta Harness. |
| `tests/` | DIR | 235 | 234 | — | UMH test suite (712 passing) |
| `tools/` | DIR | 211 | 186 | — | Dev tooling, scripts, utilities |
| `archive/` | DIR | 41002 | 1135 | 484MB | Historical archive (7 subdirs) |
| `core/` | SYMLINK | — | — | — | → `archive/core` (102 Python files) |
| `scripts/` | SYMLINK | — | — | — | → `tools/` |
| `infra/` | SYMLINK | — | — | — | → `runtime/` |
| `vault/` | SYMLINK | — | — | — | → `data/vault/` |
| `services/` | DIR | 33 | 19 | — | Old service layer (pre-interfaces) |
| `runtime/` | DIR | 14 | 1 | — | Docker/compose infrastructure |
| `docs/` | DIR | 7 | 0 | — | Documentation and audits |
| `data/` | DIR | 31 | 0 | — | Vault memory, conversation data |
| `logs/` | DIR | 58 | 0 | — | Runtime logs (gitignored) |
| `parsers/` | DIR | 7 | 7 | — | Code parsers (used by tools only) |
| `orchestrator/` | DIR | 0 | 0 | — | Empty directory |
| `.claude/` | DIR | 49 | 0 | — | Claude Code dev harness |
| `.agents/` | DIR | — | — | — | Agent skill definitions |
| `10_Wiki/` | DIR | — | — | — | Knowledge wiki / memory palace |
| `skills/` | DIR | — | — | — | Tool mastery skill files |
| `.vscode/` | DIR | — | — | — | VS Code settings |

### Root-level files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Developer agent soul document |
| `CLAUDE.local.md` | Local preferences (gitignored) |
| `.gitignore` | Git exclusions |
| `.dockerignore` | Docker build exclusions |
| `ARCHITECTURE.md` | Master specification |
| `PHILOSOPHY.md` | Design philosophy |
| `PROTOCOLS.md` | Protocol layers (L0-L3) |
| `requirements.txt` | Python dependencies |
| `cloud.md` | System context |
| `Makefile` | Build commands |

---

## 2. Classification Table

### BELONGS_TO_UMH_SYSTEM — Keep at root

| Path | Reason |
|------|--------|
| `umh/` | IS the system |
| `tests/` | UMH test suite — standard project layout |
| `runtime/` | Docker/compose infrastructure — deploys UMH |
| `docs/` | Documentation — standard project layout |
| `data/` | Runtime data (vault conversations) — UMH reads this |
| `logs/` | Runtime output — gitignored, ephemeral |
| `.claude/` | Development harness — drives dev workflow |
| `.agents/` | Agent definitions — part of dev tooling |
| `skills/` | Tool mastery skills — referenced by CLAUDE.md |
| `10_Wiki/` | Knowledge wiki — cognition stack dependency |
| `.vscode/` | Editor config — standard |
| `.gitignore` | Git config |
| `.dockerignore` | Docker config |
| `CLAUDE.md` | Soul document |
| `CLAUDE.local.md` | Local prefs |
| `ARCHITECTURE.md` | Master spec |
| `PHILOSOPHY.md` | Design philosophy |
| `PROTOCOLS.md` | Protocol layers |
| `requirements.txt` | Dependencies |
| `cloud.md` | System context |
| `Makefile` | Build commands |

### DELETE_AFTER_EXTRACTION — Remove from root

| Path | Classification | Extraction Needed | Risk |
|------|---------------|-------------------|------|
| `archive/` | DELETE_AFTER_EXTRACTION | No — purely historical | LOW |
| `core/` | DELETE (symlink) | No — points to archive/core | LOW |
| `scripts/` | DELETE (symlink) | No — points to tools/ | LOW |
| `infra/` | DELETE (symlink) | No — points to runtime/ | LOW |
| `vault/` | DELETE (symlink) | No — points to data/vault/ | LOW |
| `services/` | DELETE_AFTER_EXTRACTION | Yes — 1 guarded import from UMH | MEDIUM |
| `tools/` | DELETE_AFTER_EXTRACTION | Yes — Docker references, dev scripts | MEDIUM |
| `parsers/` | DELETE_AFTER_EXTRACTION | Yes — used by tools/ | LOW |
| `orchestrator/` | DELETE (empty) | No | ZERO |

---

## 3. Import / Runtime Dependency Map

### UMH → Root Dependencies (3 total, all guarded)

| UMH File | Imports From | Guard |
|----------|-------------|-------|
| `umh/interfaces/discord/bot.py` | `scripts.calendar_invite_handler` | try/except |
| `umh/interfaces/webhooks/calendly.py` | `services.higgsfield_webhook` | try/except |
| `umh/substrate/discord_text_transport.py` | `core.execution_contract.run_task` | try/except |

### Docker / Compose Dependencies

| Reference | File | Line |
|-----------|------|------|
| `tools/overnight_scrape.py` | `runtime/docker-compose.yml` | ~68 |
| `infra/patch_pycord.py` | `runtime/Dockerfile` | build step |

### Root → UMH Dependencies (0)

No root directory imports from UMH. The dependency is one-way.

---

## 4. Extraction Map

### From `services/` (before deletion)

| File | Used By | Action |
|------|---------|--------|
| `services/higgsfield_webhook.py` | `umh/interfaces/webhooks/calendly.py` | Move to `umh/interfaces/webhooks/higgsfield.py` |
| All other services/ files | Nothing in UMH | No extraction needed |

### From `tools/` (before deletion)

| File | Used By | Action |
|------|---------|--------|
| `tools/overnight_scrape.py` | Docker compose | Move to `umh/interfaces/cron/overnight_scrape.py` or update compose path |
| `tools/calendar_invite_handler.py` (via scripts/ symlink) | `umh/interfaces/discord/bot.py` | Move to `umh/interfaces/discord/calendar_handler.py` |
| All other tools/ files | Dev workflow only | Archive or delete — not UMH dependencies |

### From `core/` (symlink → archive/core)

| File | Used By | Action |
|------|---------|--------|
| `core/execution_contract.py` | `umh/substrate/discord_text_transport.py` | Remove import — `run_task` should route through `umh.execution.engine.execute()` |

### From `parsers/`

| File | Used By | Action |
|------|---------|--------|
| All 7 files | `tools/parsers_lib` only | No UMH dependency. Delete with tools/ or archive. |

---

## 5. Deletion Risk Assessment

### Immediately safe to delete (ZERO risk)

| Path | Reason |
|------|--------|
| `orchestrator/` | Empty directory, 0 files |
| `core/` | Symlink to archive/core — 1 guarded import, easily rerouted |
| `scripts/` | Symlink to tools/ — removing symlink doesn't affect tools/ |
| `infra/` | Symlink to runtime/ — removing symlink doesn't affect runtime/ |
| `vault/` | Symlink to data/vault/ — removing symlink doesn't affect data/ |

### Safe after extraction (LOW risk)

| Path | Extraction Required First |
|------|--------------------------|
| `services/` | Move `higgsfield_webhook.py` into `umh/interfaces/webhooks/` |
| `parsers/` | None — no UMH dependency |

### Requires careful handling (MEDIUM risk)

| Path | Risk Factor |
|------|-------------|
| `tools/` | Docker compose references `tools/overnight_scrape.py`. Dev scripts used in CLAUDE.md workflows (`scripts/session_bootstrap.py`, `scripts/update-graph`, `scripts/query_graph.py`, etc.). These are accessed via the `scripts/` symlink, so after symlink removal, direct `tools/` paths in CLAUDE.md and compose need updating. |
| `archive/` | 484MB, 41K files. No UMH imports. Only risk: `core/` symlink points here. After `core/` symlink removal, archive/ has zero dependents. Can be moved to separate repo or deleted. |

---

## 6. Symlink Inventory

| Symlink | Target | Status | Action |
|---------|--------|--------|--------|
| `core/` | `archive/core/` | Stale — pre-UMH code | Delete symlink |
| `scripts/` | `tools/` | Active — CLAUDE.md references `scripts/` paths | Delete symlink, update all `scripts/` refs to `tools/` |
| `infra/` | `runtime/` | Redundant — `runtime/` is canonical | Delete symlink |
| `vault/` | `data/vault/` | Redundant — `data/vault/` is canonical | Delete symlink |

**CLAUDE.md / .claude/ references to update after symlink removal:**
- `scripts/session_bootstrap.py` → `tools/session_bootstrap.py`
- `scripts/update-graph` → `tools/update-graph`
- `scripts/query_graph.py` → `tools/query_graph.py`
- `scripts/verify_knowledge_system.py` → `tools/verify_knowledge_system.py`
- `scripts/vault_backlink_audit.py` → `tools/vault_backlink_audit.py`
- `scripts/orchestrator.py` → `tools/orchestrator.py`

---

## 7. Docker Dependency Audit

### runtime/docker-compose.yml

All 4 service commands now correctly reference `umh/interfaces/`:
- `os-discord` → `python -m umh.interfaces.discord.bot`
- `os-bot` → `python -m umh.interfaces.telegram.bot`
- `os-monitor` → `python -m umh.interfaces.monitor.main`
- `os-webhook` → `python -m umh.interfaces.webhooks.server`

**Remaining root references:**
- Line ~68: `tools/overnight_scrape.py` — needs relocation or path update

### runtime/Dockerfile

- `infra/patch_pycord.py` — referenced via `infra/` symlink, actually at `runtime/patch_pycord.py`. After `infra/` symlink removal, update Dockerfile to use `runtime/patch_pycord.py` directly.

---

## 8. Archive Analysis

`archive/` contains 7 subdirectories:

| Subdirectory | Files | Description |
|-------------|-------|-------------|
| `archive/core/` | 102 py | Pre-UMH core (symlinked as `core/`) |
| `archive/claude_code_harnessing/` | — | CC development history |
| `archive/data_artifacts/` | — | Historical data |
| `archive/eos_product/` | — | Old EOS product code |
| `archive/infra_ops/` | — | Infrastructure scripts |
| `archive/knowledge_vault/` | — | Old knowledge base |
| `archive/runtime_legacy/` | — | Legacy runtime code |

**UMH imports from archive:** 0 direct (1 via `core/` symlink — guarded)
**Archive imports from UMH:** 0
**Verdict:** Fully decoupled. Can be moved to separate repo or deleted entirely.

---

## 9. Staged Execution Plan

### Wave A: Zero-risk cleanup (no extractions needed)

1. Delete `orchestrator/` (empty)
2. Reroute `umh/substrate/discord_text_transport.py` import from `core.execution_contract.run_task` to `umh.execution.engine.execute()`
3. Delete `core/` symlink
4. Delete `infra/` symlink, update Dockerfile: `infra/patch_pycord.py` → `runtime/patch_pycord.py`
5. Delete `vault/` symlink

**Validation gate:** `python3 -m pytest tests/ -x -q` — all 712 tests pass

### Wave B: Service extraction + symlink collapse

1. Move `services/higgsfield_webhook.py` → `umh/interfaces/webhooks/higgsfield.py`
2. Update import in `umh/interfaces/webhooks/calendly.py`
3. Delete `services/` directory
4. Move `tools/overnight_scrape.py` → `umh/interfaces/cron/overnight_scrape.py` (or keep in tools/, update compose path)
5. Move relevant calendar handler into `umh/interfaces/discord/`
6. Update import in `umh/interfaces/discord/bot.py`
7. Delete `scripts/` symlink
8. Update all CLAUDE.md / .claude/ references from `scripts/` to `tools/`

**Validation gate:** Docker compose dry-run + test suite pass

### Wave C: tools/ decision

`tools/` is dev tooling — graph scripts, session bootstrap, overnight scrape, parsers.
Two options:

**Option 1: Keep tools/ at root** (recommended for now)
- Dev tooling is standard at project root
- CLAUDE.md cognition stack depends on these scripts
- Not part of UMH kernel — that's fine, they're developer tools

**Option 2: Move into umh/tools/**
- Full UMH containment
- Requires updating every CLAUDE.md and skill reference
- High churn, low value in single-founder phase

**Recommendation:** Keep `tools/` at root. It's dev infrastructure, not product code. Rename `parsers/` contents into `tools/parsers/` for consolidation.

### Wave D: Archive disposition

1. Verify `core/` symlink already deleted (Wave A)
2. Confirm zero imports from archive/
3. Either:
   - Move `archive/` to separate git repo for historical reference
   - Or `rm -rf archive/` if history is in git log
4. Reclaim 484MB disk

**Validation gate:** Full grep for `archive/` references, test suite pass

---

## 10. Final Recommended Root Tree

After all waves complete:

```
/opt/OS/
├── umh/                    # THE system — intelligence kernel
│   ├── execution/          # Canonical execution (contract, engine, pipeline)
│   ├── runtime_engine/     # Production intelligence (agent runtime, memory, routing)
│   ├── substrate/          # Live session infrastructure (storage, events, transport)
│   ├── interfaces/         # Transport boundary (discord, telegram, cli, webhooks)
│   ├── adapters/           # External system adapters
│   ├── context/            # Context assembly
│   ├── goals/              # Goal tracking
│   ├── strategy/           # Strategy layer
│   ├── stages/             # Pipeline stages
│   ├── primitives/         # Ontological primitives
│   └── storage/            # Storage adapters
├── tests/                  # UMH test suite
├── tools/                  # Dev tooling (graph, bootstrap, scrape, parsers)
│   └── parsers/            # Code parsers (consolidated from root parsers/)
├── runtime/                # Docker/compose infrastructure
├── docs/                   # Documentation and audits
├── data/                   # Runtime data (vault conversations)
├── logs/                   # Runtime logs (gitignored)
├── 10_Wiki/                # Knowledge wiki / memory palace
├── skills/                 # Tool mastery skills
├── .claude/                # Claude Code dev harness
├── .agents/                # Agent definitions
├── .vscode/                # Editor config
├── CLAUDE.md               # Developer agent soul document
├── CLAUDE.local.md         # Local preferences
├── ARCHITECTURE.md         # Master specification
├── PHILOSOPHY.md           # Design philosophy
├── PROTOCOLS.md            # Protocol layers
├── requirements.txt        # Python dependencies
├── cloud.md                # System context
├── Makefile                # Build commands
├── .gitignore
└── .dockerignore
```

**Deleted in this cleanup:**
- `archive/` (484MB, 41K files — zero UMH dependency)
- `core/` (symlink → archive/core)
- `scripts/` (symlink → tools/)
- `infra/` (symlink → runtime/)
- `vault/` (symlink → data/vault/)
- `services/` (19 Python files — 1 extracted to UMH)
- `orchestrator/` (empty)
- `parsers/` (7 files — consolidated into tools/parsers/)

**Net reduction:** ~41,300 files, ~484MB reclaimed, 4 symlinks eliminated, root directory count from ~20 to ~14.

---

## Summary

The root directory has accumulated significant historical weight. After extraction of 3 guarded imports (higgsfield webhook, calendar handler, execution contract reroute), every root directory outside the recommended tree has **zero UMH dependency** and can be safely deleted.

The 4-wave staged plan ensures each deletion is independently validated before proceeding. The highest-risk items (tools/, archive/) are handled last with the most conservative approach.
