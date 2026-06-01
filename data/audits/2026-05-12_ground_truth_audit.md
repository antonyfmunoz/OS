# Ground Truth Audit — /opt/OS
> Date: 2026-05-12T15:05:03Z
> Auditor: Claude Opus 4.6 (read-only, no modifications)
> Mode: Factual verification against handoff claims

---

# Executive Summary

**1. Did the R8 migration happen?**
CONFIRMED. 22/22 claimed commit hashes exist and match messages; R8a through R8h sub-commits landed with cumulative file touches across 928+411+464+324+18+18+5+1+4+6 files (Section 1).

**2. Is `runtime/` the canonical runtime, or is `eos_ai/` still primary?**
`runtime/` is canonical. Zero `eos_ai` references remain in discord_bot.py, docker-compose.yml, crontab, or CLAUDE.md; all `eos_ai/*.py` files are deterministic shims redirecting to `runtime.*` (Section 3, Section 5).

**3. Is `umh/` still dormant?**
YES. `umh/__init__.py` raises an ImportError tombstone; 1 total .py file in the directory (Section 2, Section 3).

**4. Merge conflicts remaining (vs May 9 baseline of 83)?**
9 files with conflict markers remain — an 89% reduction from the May 9 baseline of 83 (Section 4).

**5. Does CLAUDE.md still falsely claim CU ingestion is proven?**
NO. Zero CU ingestion or "proven" claims exist in either CLAUDE.md file; proof documents exist in docs/system/ but are not referenced as production-proven (Section 5).

**6. Are the 5 phantom imports in discord_bot.py still present?**
NO. All phantom `eos_ai` references have been removed; discord_bot.py now uses exclusively `runtime.*` namespace imports (Section 3).

**7. Did the May 6 relay client fix land in code?**
YES. `_resolve_windows_home()` with `/mnt/c` detection and `cmd.exe /C echo %USERPROFILE%` is present in `runtime/transport/windows_desktop_relay_client.py` (Section 10).

**8. Was any full ingestion cycle ever completed end-to-end?**
NO. The canonical memory store contains 10 scripted entries from prove_w0 scripts; query proofs are all labeled "example"; no evidence of real documents traversing the full perceive-to-query pipeline (Section 7).

**9. Actual test collection count?**
11,532 tests collected (338 errors) — 33% higher than the handoff claim of 8,684 (Section 8).

**10. Actual reachable-from-runtime Python module count?**
Not directly measured in this audit. discord_bot.py has 14 direct import lines resolving to modules in `runtime.*` and `handlers.*`; gateway.py adds 4 transitive imports (`runtime.db`, `runtime.model_router`, `runtime.agent_runtime`, `runtime.cognitive_loop`). Full transitive closure was not computed (Section 3).

---

**MIGRATION NARRATIVE: CONFIRMED.** The R8 migration is real — 22 commits landed, all `eos_ai` references in operational paths (entrypoint, compose, cron, config) have been eliminated, and the shim layer functions correctly as a pass-through. The remaining 9 merge-conflict files, the empty relay proof directory, and the absence of a real ingestion cycle are post-migration cleanup items, not migration failures.

**RECONCILED PROTECTED LIST** (observed runtime imports from discord_bot.py, direct and transitive):
- `runtime/gateway.py` — direct import
- `runtime/context.py` — direct import
- `runtime/knowledge_integrator.py` — direct import
- `runtime/voice_engine.py` — direct import
- `runtime/business_instance.py` — direct import
- `runtime/discord_utils.py` — direct import
- `runtime/substrate/session_discord_bridge.py` — direct import
- `runtime/substrate/discord_text_transport.py` — direct import
- `runtime/substrate/event_spine.py` — direct import
- `runtime/onboarding_engine.py` — direct import
- `runtime/model_router.py` — direct import + transitive via gateway.py
- `runtime/db.py` — transitive via gateway.py
- `runtime/agent_runtime.py` — transitive via gateway.py
- `runtime/cognitive_loop.py` — transitive via gateway.py
- `handlers/intent_handler.py` — direct import
- `handlers/pipeline_handler.py` — direct import
- `handlers/cc_command_handler.py` — direct import
- `handlers/substrate_command_handler.py` — direct import

---

# Section 0 — Bootstrap

| Field | Value |
|-------|-------|
| HEAD | `cee8605f4af81c294516021b21c836f6e9e8c3f5` |
| Branch | `main` |
| Remote | `origin https://github.com/antonyfmunoz/OS.git` |
| Host | `srv1500858` |
| User | `root` |
| UTC Time | `2026-05-12T15:05:03Z` |
| Working Dir | `/opt/OS` |

### Dirty files (git status --short)

```
 M .obsidian/plugins/obsidian-git/main.js
 M 10_Wiki/cloud_palace.md
 M 10_Wiki/index.md
 M 10_Wiki/log.md
 M 10_Wiki/retrieval_rules.md
 D backups/eos_backup_20260326.tar.gz
 M data/gws_context.md
 M skills/meta/claude_code_best_practices/SKILL.md
 M skills/meta/tool_mastery_engine/references/research_protocol.md
 M skills/tools/*/SKILL.md (numerous tool skill files modified)
```

Note: No runtime/, core/, services/, or scripts/ files are dirty.
All migration artifacts are cleanly committed.

---

# Section 1 — Git State & Migration History

### Sync status

- **HEAD = origin/main**: YES (zero commits ahead, zero behind)
- **3 tags exist**: `pre-controlled-collapse-umh`, `pre-umh-refactor`, `umh-runtime-stable-2026-05-11`

### Tag resolution

| Tag | Resolves to | Claimed | Match? |
|-----|-------------|---------|--------|
| `umh-runtime-stable-2026-05-11` | `5c0e9c4f22dae9d89c87c0f939dfa5303e52397f` | `5c0e9c4f` | **YES** |

### Commit verification (all 22 claimed hashes)

| Hash | Exists? | Date | Message | Matches claim? |
|------|---------|------|---------|---------------|
| `ee4ca84c` | YES | 2026-05-06 | phase968g: enforce canonical spine coherence before execution | YES |
| `ecb4b9c4` | YES | 2026-05-06 | phase968g: add w0 dry validation proving coherence envelope acceptance | YES |
| `79dc8aba` | YES | 2026-05-06 | phase968h: add windows interactive desktop adapter v1 | YES |
| `d7bb8905` | YES | 2026-05-10 | root-migration-r1: introduce UMH_ROOT with OS_ROOT fallback | YES |
| `f0b4a836` | YES | 2026-05-10 | root-migration-r2: migrate runtime bootstrap to UMH_ROOT chain | YES |
| `8a0db076` | YES | 2026-05-10 | root-migration-r3: canonicalize runtime filesystem references | YES |
| `620103e0` | YES | 2026-05-10 | root-migration-r4: normalize test topology and runtime references | YES |
| `dffa0db8` | YES | 2026-05-10 | root-migration-r5: converge deployment/runtime infrastructure to UMH_ROOT | YES |
| `0fb3a787` | YES | 2026-05-10 | root-migration-r6: normalize UMH semantic identity in canonical docs | YES |
| `c2bf6b2f` | YES | 2026-05-10 | root-migration-r7: runtime namespace transition planning | YES |
| `3c73db43` | YES | 2026-05-10 | root-migration-r8a: relocate deployment runtime config to infra docker | YES (6 files) |
| `aaf43408` | YES | 2026-05-10 | root-migration-r8b: establish canonical runtime namespace with bridges | YES (928 files) |
| `fe7af75f` | YES | 2026-05-10 | root-migration-r8c: migrate internal runtime references to canonical namespace | YES (411 files) |
| `83891d12` | YES | 2026-05-10 | root-migration-r8d: generate deterministic compatibility shim layer | YES (464 files) |
| `b6b0fb4a` | YES | 2026-05-11 | root-migration-r8e: migrate external consumers to canonical runtime namespace | YES (324 files) |
| `1e4307e0` | YES | 2026-05-11 | root-migration-r8f: migrate semantic runtime references to canonical namespace | YES (18 files) |
| `99eb74cc` | YES | 2026-05-11 | root-migration-r8g: converge operational runtime infrastructure | YES (18 files) |
| `5b08791f` | YES | 2026-05-11 | root-migration-r8g-manual: patch live operational references | YES (5 files) |
| `edce0032` | YES | 2026-05-11 | root-migration-r8h: certify canonical runtime equivalence | YES (1 file — proof doc) |
| `3f6f2076` | YES | 2026-05-11 | root-migration-post-r8h: stabilize canonical runtime convergence | YES (4 files) |
| `5c0e9c4f` | YES | 2026-05-11 | root-migration-monitoring: correct architecture wording and prepare shim monitoring | YES (6 files) |
| `cee8605f` | YES | 2026-05-11 | runtime-stabilization-plan: define canonical runtime domains and execution spine | YES (3 files) |

**Result: 22/22 commits exist and match claimed messages. 0 discrepancies.**

---

# Section 2 — Filesystem Topology

### Directory existence

| Directory | Exists? | Evidence |
|-----------|---------|----------|
| `/opt/OS/runtime/` | YES | 125 top-level .py files |
| `/opt/OS/eos_ai/` | YES | 459 .py files (shim layer) |
| `/opt/OS/umh/` | YES | 1 .py file (__init__.py — raises ImportError tombstone) |
| `/opt/OS/core/` | YES | 493 .py files |
| `/opt/OS/services/` | YES | discord_bot.py + 29 other files |
| `/opt/OS/platforms/` | **NO** | `ls: cannot access: No such file or directory` |
| `/opt/OS/archive/` | YES | 9 subdirectories (core_legacy, deprecated, dormant_reference, etc.) |
| `/opt/OS/handoffs/` | **NO** | `ls: cannot access: No such file or directory` |
| `/opt/OS/infra/` | YES | docker-compose.yml, install.sh, setup.sh |

### Python file counts

| Location | Count | Command |
|----------|-------|---------|
| runtime/ | 455 | `find /opt/OS/runtime -name "*.py"` |
| eos_ai/ | 459 | `find /opt/OS/eos_ai -name "*.py"` |
| umh/ | 1 | `find /opt/OS/umh -name "*.py"` |
| core/ | 493 | `find /opt/OS/core -name "*.py"` |
| tests/ | 630 | `find /opt/OS/tests -name "*.py"` |
| Total (depth≤4, excl git/node_modules/saas) | 3,399 | `find /opt/OS -maxdepth 4 -name "*.py"` |

### runtime/ subdirectory breakdown

| Subdir | .py count |
|--------|-----------|
| top-level (runtime/*.py) | 125 |
| runtime/substrate/ | 164 |
| runtime/transport/ | 164 |
| runtime/runtime/ | DOES NOT EXIST |
| runtime/interfaces/ | 2 |

**Discrepancy with handoff**: Handoff summary claims `runtime/runtime/` contains `work_state.py` and `provider_state.py`. In reality, `runtime/runtime/` does NOT exist. These files are at `runtime/work_state.py` and `runtime/provider_state.py` (top-level). The `eos_ai/runtime/` subdirectory exists and contains shim versions.

### Key deliverable files

| File | Exists? | Lines | Evidence |
|------|---------|-------|----------|
| docs/system/runtime_domain_architecture_plan.md | YES | 608 | Created in cee8605f |
| docs/system/current_canonical_runtime_spine.md | YES | 217 | Created in cee8605f |
| data/system/runtime_domain_module_map.json | YES | 368 | Created in cee8605f |
| data/migration/r8h_equivalence_certification.md | YES | 458 | Created in edce0032 |
| data/migration/post_r8h_stabilization_report.md | YES | 318 | Created in 3f6f2076 |
| data/migration/shim_monitoring_plan.md | YES | 98 | Created in 5c0e9c4f |
| scripts/shim_retirement_monitor.py | YES | 272 | Created in 5c0e9c4f |
| runtime/CLAUDE.md | YES | 52 | Updated in 5c0e9c4f |

### Symlink status

| Path | Target | Status |
|------|--------|--------|
| `eos_ai/.env` | `../runtime/.env` | VALID symlink, target exists (12,754 bytes) |

---

# Section 3 — Live Runtime Import Graph

### Package status

| Package | Import result | Type | Evidence |
|---------|--------------|------|----------|
| `runtime` | `OK None _NamespacePath(['/opt/OS/runtime', '/opt/OS/runtime'])` | **Namespace package** (no __init__.py) | `python3 -c "import runtime"` |
| `eos_ai` | `OK None _NamespacePath(['/opt/OS/eos_ai', '/opt/OS/eos_ai'])` | **Namespace package** (no __init__.py) | `python3 -c "import eos_ai"` |
| `umh` | `ImportError: umh/ has been archived to archive/umh_reference/` | **Tombstone** (__init__.py raises ImportError) | `python3 -c "import umh"` |

### Gateway resolution

| Import path | Resolves to | Evidence |
|------------|-------------|----------|
| `from eos_ai import gateway` | `/opt/OS/runtime/gateway.py` | Shim redirects via `sys.modules[__name__] = _mod` |
| `from runtime import gateway` | `/opt/OS/runtime/gateway.py` | Direct resolution |

Both paths resolve to the same file. Shim identity is preserved.

### eos_ai shim pattern (verified on eos_ai/gateway.py)

```python
# Generated by r8d_generate_shims.py — do not edit
import runtime.gateway as _mod
import sys as _sys
_sys.modules[__name__] = _mod
```

### discord_bot.py imports (entrypoint, verified static analysis)

| Import | Namespace | Resolves? |
|--------|-----------|-----------|
| `from runtime.gateway import EOSGateway` | runtime | YES |
| `from runtime.context import load_context_from_env` | runtime | YES |
| `from runtime.knowledge_integrator import KnowledgeIntegrator` | runtime | YES |
| `from runtime.voice_engine import VoiceEngine` | runtime | YES |
| `from runtime.business_instance import get_ai_name` | runtime | YES |
| `from runtime.discord_utils import chunk_message, post_to_webhook` | runtime | YES |
| `from runtime.substrate.session_discord_bridge import send_reply` | runtime | YES |
| `from runtime.substrate.discord_text_transport import ...` | runtime | YES |
| `from runtime.substrate.event_spine import ...` | runtime | YES |
| `from runtime.onboarding_engine import OnboardingEngine` | runtime | YES |
| `from handlers.intent_handler import run_gateway` | handlers | YES |
| `from handlers.pipeline_handler import handle_pipeline_update` | handlers | YES |
| `from handlers.cc_command_handler import try_inline_commands` | handlers | YES |
| `from handlers.substrate_command_handler import ...` | handlers | YES |

**Zero eos_ai references in discord_bot.py** (`grep -nE "eos_ai" services/discord_bot.py` returned empty).

### Phantom imports from May 9 audit

May 9 flagged `eos_ai.runtime.work_state` as a phantom import in discord_bot.py. Current state: **FIXED. Zero eos_ai references remain in discord_bot.py.** All imports use `runtime.*` namespace.

### Transitive import chain (gateway.py)

gateway.py imports: `runtime.db`, `runtime.model_router`, `runtime.agent_runtime`, `runtime.cognitive_loop`. These are lazy/conditional imports within method bodies, not top-level. All 4 resolve to files that exist on disk.

---

# Section 4 — Merge Conflicts

| Category | Count | Evidence |
|----------|-------|----------|
| Python files with `<<<<<<<` | 2 | `grep -rln` |
| Markdown files with `<<<<<<<` | 5 | `grep -rln` |
| Skill files with `<<<<<<<` | 2 | `grep -rln` (subset of .md) |
| **Total files** | **9** | `grep -rln` (excl .git/) |

### Affected files

```
/opt/OS/tests/test_tme_umh_scope.py
/opt/OS/skills/tools/git/references/best_practices.md
/opt/OS/scripts/fix_merge_conflicts.py
/opt/OS/docs/system/tme_scope_correction_umh_report_v1.md
/opt/OS/archive/stale_backups/discord_bot.py.bak.20260508
/opt/OS/vault/memory/conversations/1d0a7ea5-936b-4f61-8c65-0b49c999acee.md
/opt/OS/saas/db/schema.ts
/opt/OS/skills/tools/obsidian_markdown/references/best_practices.md
/opt/OS/docs/system/phase968aj_command_surface_sync_proof.md
```

### Comparison to May 9 baseline

| Metric | May 9 | May 12 | Change |
|--------|-------|--------|--------|
| Total files with conflicts | 83 | 9 | **-74 (89% reduction)** |
| SKILL.md files | 76 | 2 | **-74** |
| Test files | 3 | 1 | -2 |
| Python files | 3 | 2 | -1 |

### Backup files

1 backup file found: `/opt/OS/archive/stale_backups/discord_bot.py.bak.20260508`

---

# Section 5 — Claims vs Reality

### eos_ai references in configuration files

| File | eos_ai refs | Context |
|------|-------------|---------|
| `/opt/OS/CLAUDE.md` | **0** | Fully migrated |
| `/opt/OS/.claude/CLAUDE.md` | **1** | Correct: "eos_ai/ — dead shim layer (zero consumers, pending removal)" |
| `/opt/OS/.claude/settings.json` | **0** | Fully migrated |
| `/opt/OS/runtime/CLAUDE.md` | **1** | Correct: "The `eos_ai/` directory is a dead shim layer" |
| Crontab | **0** | Fully migrated |
| docker-compose.yml | **0** | Fully migrated |

### Component status claims (.claude/CLAUDE.md lines 88-99)

| Claim | Current namespace | Verdict |
|-------|-------------------|---------|
| runtime/db.py — CONFIRMED_RUNTIME | runtime.* | CORRECT (used by all services) |
| runtime/memory.py — CONFIRMED_RUNTIME | runtime.* | CORRECT (Neon writes) |
| runtime/agent_runtime.py — CONFIRMED_RUNTIME | runtime.* | CORRECT (imported by gateway.py) |
| runtime/cognitive_loop.py — PARTIALLY_VERIFIED | runtime.* | CORRECT (imported by gateway.py, but lazy) |
| runtime/authority_engine.py — PARTIALLY_VERIFIED | runtime.* | CORRECT (imported by execution_spine.py) |
| runtime/portfolio_advisor.py — PARTIALLY_VERIFIED | runtime.* | CORRECT (file exists, no runtime import chain to discord_bot) |
| runtime/orchestrator.py — PARTIALLY_VERIFIED | runtime.* | CORRECT (cron runs it directly) |
| runtime/model_preferences.py — CONFIRMED_RUNTIME | runtime.* | CORRECT (imported by model_router) |
| runtime/media_processor.py — PARTIALLY_VERIFIED | runtime.* | CORRECT (voice_engine uses it) |
| services/discord_bot.py — CONFIRMED_RUNTIME | N/A | CORRECT (running container) |
| runtime/work_state.py — CONFIRMED_RUNTIME | runtime.* | CORRECT (imported by discord_bot.py via substrate) |

### "Do-not-touch core" (5 files from May 9 audit)

May 9 identified gateway, model_router, cognitive_loop, agent_runtime, primitives as "do-not-touch core" but noted only the first two were directly runtime-wired.

| File | Directly imported by discord_bot.py? | Transitively imported? |
|------|--------------------------------------|----------------------|
| gateway.py | YES (1 ref) | N/A — direct |
| model_router.py | YES (2 refs) | Also via gateway.py |
| cognitive_loop.py | NO | YES (gateway.py imports it) |
| agent_runtime.py | NO | YES (gateway.py imports it) |
| primitives.py | NO | UNVERIFIED (May 9 noted no runtime chain) |

**CLAUDE.md correction status**: CLAUDE.md does NOT contain a "do-not-touch" list for these 5 files. The risk classification system (HIGH for core infrastructure) implicitly protects them but does not name them.

### CU ingestion claim

May 9 flagged that CU ingestion was claimed as "proven" in documentation.

**Current state**: `grep -niE "computer.use|CU ingestion|cu.*proven|ingestion.*proven" CLAUDE.md .claude/CLAUDE.md` returned **ZERO results**. No CU ingestion claims exist in either CLAUDE.md file.

**However**: 30+ proof documents exist in docs/system/ with names like `phase968ah_real_foreground_cu_ingestion_proof.md`. These documents contain proof narratives but CLAUDE.md does not reference them as "proven" or "production".

---

# Section 6 — Service State

### Running containers

| Container | Image | Status | Uptime | Port |
|-----------|-------|--------|--------|------|
| os-discord | os-os-discord | Up | 3 days | 8765 |
| os-webhook | os-os-webhook | Up | 2 weeks | 8080 |

### Stopped containers

| Container | Image | Status | Notes |
|-----------|-------|--------|-------|
| os-bot | runtime-os-bot | Exited (1) 2 weeks ago | Telegram bot, DORMANT per CLAUDE.md |
| os-monitor | os-os-monitor | Exited (137) 13 days ago | Instagram DM monitor, killed |
| os-scraper | os-os-scraper | Exited (0) 6 weeks ago | Overnight scraper, normal exit |

### docker-compose.yml env_file references

| Service | env_file entries | eos_ai refs |
|---------|-----------------|-------------|
| os-bot | `services/.env` | 0 |
| os-monitor | `services/.env`, `runtime/.env` | 0 |
| os-scraper | `services/.env`, `runtime/.env` | 0 |
| os-webhook | `services/.env` | 0 |
| os-discord | `services/.env`, `runtime/.env` | 0 |

**Note**: os-bot uses image `runtime-os-bot` and command `python3 umh/interface...` — this is a STALE image/command from before the migration. The container is DORMANT (Exited) so it does not affect runtime, but would fail if restarted without rebuilding.

### Crontab

| Feature | Status | Evidence |
|---------|--------|---------|
| eos_ai refs | **0** | `crontab -l \| grep eos_ai` — empty |
| runtime refs | Present | `runtime/orchestrator.py`, `runtime/.env`, `runtime.email_reviewer`, `runtime.context`, `runtime.discord_utils` |
| Shim monitor cron | **INSTALLED** | `30 3 * * * python3 scripts/shim_retirement_monitor.py >> /opt/OS/logs/shim_monitor.log 2>&1` |
| Total cron entries | ~35 | Active entries (excluding comments) |

---

# Section 7 — Ingestion State

### Ingestion infrastructure

| Component | Exists? | Location |
|-----------|---------|----------|
| gws_scanner.py | YES (x2) | runtime/ + eos_ai/ (shim) |
| instance_ingestion_contracts.py | YES (x4) | runtime/substrate/ + runtime/transport/ + eos_ai mirrors |
| primitive_decomposition_v1.py | YES | core/ontology/ |
| canonical_memory_store/ | YES | data/runtime/canonical_memory_store/ |
| canonical_memory_query_proofs/ | YES | data/runtime/canonical_memory_query_proofs/ |
| full_live_ingestion_spine_v1.py | YES | core/runtime/ |

### Canonical memory store contents

| File | Content |
|------|---------|
| memories.jsonl | 10 lines (entries like "I'd won the money game...") |
| promotion_summary.json | 3 promoted entries with receipt IDs |
| promotion_receipts.jsonl | EXISTS |
| index.json | EXISTS |

### Query proofs

4 files in canonical_memory_query_proofs/. All filenames contain "example": `rollback_reference_query_example.json`, `lineage_query_example.json`, `canonical_query_example.json`, `query_proof_artifact_example.json`.

### Ingested files count

`find . -path "*ingested*" -type f` returned **1** file.

### End-to-end ingestion cycle assessment

**No evidence of a complete end-to-end ingestion cycle.** The canonical memory store contains 10 scripted entries (from prove_w0_* scripts), not real ingested data. Query proofs are all labeled "example". The ingestion infrastructure exists as code but has not processed real documents through the full pipeline (perceive → interpret → decompose → map → persist → query).

---

# Section 8 — Test Baseline

### Test collection

| Metric | Handoff claim | Actual | Match? |
|--------|---------------|--------|--------|
| Tests collected | 8,684 | **11,532** | **NO — 2,848 more tests** |
| Collection errors | 495 | **338** | **NO — 157 fewer errors** |
| Passed/Failed | 8,684/2,691 | UNVERIFIED (collection-only run) | N/A |

Command: `python3 -m pytest tests/ --collect-only -q --continue-on-collection-errors`
Output: `11532 tests collected, 338 errors in 11.55s`

**Discrepancy**: The handoff baseline of 8684/2691/495 was captured at a specific point during the R8 migration. The current collection count is 33% higher. This could be caused by:
1. New test files added since baseline was captured
2. Migration fixes resolving collection errors that previously masked tests
3. Different pytest collection scope

### Test file count

621 test files in tests/ (`find tests/ -name "test_*.py" -o -name "*_test.py"`)

### Pytest config

`/opt/OS/pyproject.toml` exists.

---

# Section 9 — Constitutional Engines

### founder_confirmed hardcoding

| Metric | Value | Evidence |
|--------|-------|---------|
| Files with `founder_confirmed.*True` | 30+ | `grep -rl` across .py and .json |
| Total occurrences | **203** | `grep -rc` summed |
| Location pattern | tests/test_constitutional_*_v1.py + data/runtime/workstation_relay/ | Proof generators and their tests |

### Sample (test_constitutional_antifragility_resilience_engine_v1.py)

```python
# Line 666: founder_confirmed=True,
# Line 707: founder_confirmed=True,
# Line 775: proof = build_full_resilience_proof(founder_confirmed=True)
# Line 776: assert proof.evidence.founder_confirmed is True
```

### maturity L5 hardcoding

| Metric | Value |
|--------|-------|
| Files with `maturity.*L5` | 20 |
| Location pattern | 10 in tests/test_constitutional_*_v1.py + 10 in core/workstation/constitutional_*_v1.py |

### Sample (core/workstation/constitutional_antifragility_resilience_engine_v1.py)

```python
# Line 657: maturity_ceiling: str = "L5_CONSTITUTIONAL_ANTIFRAGILITY"
```

### Assessment

The constitutional engines and their tests contain **203 instances of hardcoded `founder_confirmed=True`** and **20 files with hardcoded `maturity: L5`**. These are proof-generator modules (PROOF_ONLY status in CLAUDE.md) — they produce report artifacts, not runtime decisions. The hardcoding means these "proofs" always pass regardless of actual system state.

---

# Section 10 — Relay Client Fix

### File locations

| File | Exists? | Content |
|------|---------|---------|
| runtime/transport/windows_desktop_relay_client.py | YES | 60+ line implementation with `_resolve_windows_home()` |
| runtime/substrate/windows_desktop_relay_client.py | YES | Shim: `from runtime.transport.windows_desktop_relay_client import *` |
| eos_ai/substrate/windows_desktop_relay_client.py | YES | Shim (r8d-generated) |
| eos_ai/transport/windows_desktop_relay_client.py | YES | Shim (r8d-generated) |
| scripts/windows_interactive_desktop_relay.ps1 | YES | PowerShell script |

### Fix verification (runtime/transport/windows_desktop_relay_client.py)

| Fix marker | Present? | Evidence |
|------------|----------|---------|
| `_resolve_windows_home()` function | YES | Line ~35 |
| `/mnt/c` detection | YES | `Path("/mnt/c").exists()` in function body |
| `cmd.exe /C echo %USERPROFILE%` | YES | subprocess call in function body |
| `USERPROFILE` variable | YES | Referenced in docstring and subprocess call |

**Verdict**: The May 6 relay client fix IS present in code. The `_resolve_windows_home()` function correctly resolves WSL paths via `cmd.exe` → `%USERPROFILE%`.

### End-to-end relay proof

Relay proof directory `data/runtime/workstation_relay/proofs/` exists but is **EMPTY**. Proof documents exist in docs/system/ (phase968j, phase968ao, phase968ap) but these are report narratives, not runtime artifacts. No evidence of a successful end-to-end relay ping.

---

# Section 11 — Synthesis

### Key discrepancies between handoff claims and reality

1. **Test baseline inflated by 33%**: Handoff claimed 8,684 tests collected with 495 errors. Actual collection yields 11,532 tests with 338 errors. The baseline number was either captured mid-migration or under a different collection scope — it cannot be used as a regression anchor.

2. **`runtime/runtime/` subdirectory does not exist**: Handoff summary referenced `runtime/runtime/work_state.py` and `runtime/runtime/provider_state.py`. These files live at `runtime/work_state.py` and `runtime/provider_state.py` (top-level). The nested path was fabricated or confused with `eos_ai/runtime/`.

3. **Ingestion infrastructure exists as code but has never run end-to-end**: 10 scripted memory entries and "example"-labeled query proofs are the only artifacts. No real document has traversed the perceive-to-query pipeline. Documentation stopped short of claiming this was production-proven (the May 9 CU ingestion claim was removed), but the gap between code existence and operational proof remains.

4. **Constitutional proof hardcoding**: 203 instances of `founder_confirmed=True` and 20 files with hardcoded `maturity: L5` mean the constitutional engines always pass. These are PROOF_ONLY modules per CLAUDE.md, but their outputs could be mistaken for genuine runtime validation.

5. **os-bot container stale**: The Telegram bot container references `umh/interface...` — a pre-migration command path that would fail on restart. Dormant status masks the breakage.

### Top 3 risks

1. **9 unresolved merge conflicts** — down from 83, but the remaining files include `saas/db/schema.ts` (database schema) and `tests/test_tme_umh_scope.py` (test infrastructure). These are not cosmetic; a schema file with conflict markers will break any migration or build that touches it.

2. **No ingestion proof-of-life** — the ingestion pipeline is the core differentiator of the substrate. Every component exists as code, but zero real data has flowed through it. Until a single real document completes the full cycle, the pipeline is theoretical.

3. **Shim layer as indefinite dependency** — 459 shim files in `eos_ai/` redirect to `runtime/`. The shim monitor cron is installed, but no retirement timeline or consumer audit exists. The shim layer adds surface area for confusion (as demonstrated by the `runtime/runtime/` path error in the handoff) and doubles the apparent codebase size.

### Overall assessment

The R8 migration is real, structurally complete, and operationally landed — discord_bot.py, docker-compose, crontab, and both CLAUDE.md files reference only `runtime.*`. The 22-commit migration sequence is fully verified. What the migration did NOT accomplish is equally clear: the ingestion pipeline has no operational proof, the constitutional engines produce unfalsifiable outputs, and the shim layer remains as a 459-file maintenance burden with no retirement schedule. The test baseline needs to be re-anchored at 11,532/338 since the handoff number is stale. The 9 remaining merge conflicts need manual resolution, with `saas/db/schema.ts` as the highest-priority target. The system is in a legitimate post-migration stabilization phase — the structural work is done, but operational proof across ingestion, relay, and constitutional validation has not been established.
