# Phase 11 — UMH-Only Productization Report

**Date:** 2026-04-25
**Status:** STRUCTURAL CONSOLIDATION COMPLETE

---

## 1. Final Directory Tree

```
/opt/OS/
├── umh/                    # Canonical substrate (96 modules, 15.7K LOC)
│   ├── adapters/           # LLM routing, platform bridges
│   ├── capability/         # Capability registry + router
│   ├── context/            # Token-budgeted context assembly
│   ├── core/               # Clock utilities
│   ├── decision/           # Decision trace observability
│   ├── environments/       # Runtime detection, env loading
│   ├── execution/          # Engine, pipeline, harness, quality gates
│   ├── feedback/           # Outcome learning loop
│   ├── gateway/            # UMHInput/UMHOutput entry point
│   ├── goals/              # Multi-objective optimization
│   ├── governance/         # Authority, capability enforcement
│   ├── intent/             # Signal-to-intent compilation
│   ├── interface/          # CLI, Discord/Telegram stubs
│   ├── memory/             # Memory subsystem
│   ├── primitives/         # Ontological primitive tags
│   ├── protocols/          # 12 protocol definitions
│   ├── security/           # Access control
│   ├── signal/             # Event bus, signal ingestion
│   ├── storage/            # Neon adapter, storage backend
│   ├── strategy/           # Strategy memory + performance
│   ├── workstation/        # Business instance management
│   └── world/              # World model (8 files, 3.5K LOC)
│
├── interfaces/             # Transport adapters (copies — Docker still reads services/)
│   ├── discord/            # bot.py, handlers/
│   ├── telegram/           # bot.py
│   └── webhooks/           # calendly.py, higgsfield.py, cc_receiver.py
│
├── runtime/                # Docker, provisioning, env templates
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── .env.example
│   └── setup.sh, install.sh, patch_pycord.py
│
├── tools/                  # Scripts, dev utilities (171 Python files)
│   ├── orchestrator*.py    # Continuous execution loops
│   ├── *_smoke_test.py     # 50+ substrate smoke tests
│   ├── notion_*.py         # Notion workspace sync
│   ├── morning_intel.py    # Daily operations
│   ├── codebase_graph.py   # Knowledge graph system
│   └── scheduled/          # Cron-triggered scripts
│
├── data/                   # Runtime data (non-code)
│   ├── vault/              # Conversation memory
│   └── logs -> ../logs     # Log symlink
│
├── docs/                   # Documentation
│   └── audits/             # Phase audit documents
│
├── archive/                # Frozen legacy (from _holding/)
│   ├── runtime_legacy/     # Old eos_ai, core, parsers, services, tests
│   ├── eos_product/        # SaaS product code
│   ├── knowledge_vault/    # Obsidian vault
│   ├── claude_code_harnessing/  # Skills, planning docs
│   ├── data_artifacts/     # Bulk data (313 MB)
│   ├── infra_ops/          # Old infra docs
│   └── core/               # Archived core/ (102 modules)
│
├── tests/                  # Test suite (248 Python files)
│   ├── unit/               # UMH unit tests
│   ├── substrate/          # Substrate integration tests
│   ├── platforms/eos/      # Platform tests
│   ├── adapters/           # Adapter tests
│   └── runtime/            # Runtime tests
│
├── .claude/                # Claude Code config
│
├── eos_ai/                 # TRANSITIONAL — platform compat layer
├── services/               # TRANSITIONAL — Docker entry points
├── parsers/                # TRANSITIONAL — graph parsers
│
├── infra/ → runtime/       # Compatibility symlink
├── scripts/ → tools/       # Compatibility symlink
├── vault/ → data/vault/    # Compatibility symlink
├── core/ → archive/core/   # Compatibility symlink
├── logs/                   # Runtime logs (gitignored)
│
├── CLAUDE.md               # Developer Agent soul document
└── .gitignore
```

---

## 2. Files Moved Into UMH

**None.** UMH was already fully extracted across Waves 0–9. The dependency analysis
confirmed that zero modules in `core/`, `parsers/`, or `eos_ai/` are generic enough
to warrant UMH extraction. The one violation (`umh/workstation/business.py` importing
from `eos_ai`) was fixed in Phase 10A by replacing with `umh.gateway.entry.utility_llm_call`.

---

## 3. Files Moved Into interfaces/runtime/tools/data

| Source | Destination | Files | Purpose |
|--------|-------------|-------|---------|
| `services/discord_bot.py` | `interfaces/discord/bot.py` | 1 | Discord transport |
| `services/telegram_control.py` | `interfaces/telegram/bot.py` | 1 | Telegram transport |
| `services/calendly_webhook.py` | `interfaces/webhooks/calendly.py` | 1 | Calendly webhook |
| `services/higgsfield_webhook.py` | `interfaces/webhooks/higgsfield.py` | 1 | Higgsfield webhook |
| `services/cc_webhook_receiver.py` | `interfaces/webhooks/cc_receiver.py` | 1 | CC webhook |
| `services/handlers/*` | `interfaces/discord/handlers/*` | 4 | Discord handler modules |
| `services/heartbeat.py` | `tools/heartbeat.py` | 1 | Health check |
| `services/cost_tracker.py` | `tools/cost_tracker.py` | 1 | Cost tracking |
| `services/local_bridge_*.py` | `tools/local_bridge_*.py` | 2 | Local bridge |
| `infra/*` | `runtime/*` | 8 | Docker, provisioning |
| `scripts/*` | `tools/*` | 171 | All scripts |
| `vault/` | `data/vault/` | 16 | Conversation memory |
| `core/execution_contract.py` | `eos_ai/execution_contract.py` | 1 | Platform execution entry |

---

## 4. Files Archived or Deleted

| Source | Action | Size | Reason |
|--------|--------|------|--------|
| `_holding/` (entire) | → `archive/` | 483 MB | Frozen legacy |
| `core/` (102 modules) | → `archive/core/` | 4.3 MB | Zero live production consumers |
| `external_services/` | Deleted | 4 KB | Empty stub |
| `media/` | Deleted | 8 KB | Empty dirs |
| `orchestrator/` | Deleted | 16 KB | Empty dirs (runtime-created) |

---

## 5. Logic That Could NOT Be Extracted Into UMH

| Module | Reason |
|--------|--------|
| `eos_ai/gateway.py` (EOSGateway) | Platform-specific request routing, agent selection, approval gates |
| `eos_ai/agent_runtime.py` | EOS-specific LLM dispatch with TaskType enum, AgentResult |
| `eos_ai/memory.py` | Neon-backed conversation persistence (UMH has in-memory only) |
| `eos_ai/voice_engine.py` | Discord-specific STT/VAD/speech classification |
| `eos_ai/discord_utils.py` | Discord message chunking, webhook posting |
| `eos_ai/knowledge_integrator.py` | EOS-specific knowledge accumulation |
| `eos_ai/onboarding_engine.py` | EOS founder onboarding flow |
| `eos_ai/error_handler.py` | Self-healing error handler with Telegram alerts |
| `eos_ai/substrate/*` (~150 modules) | Discord transport, session management, station system, voice pipeline |
| `eos_ai/execution_spine.py` | Platform execution orchestrator (wraps UMH) |
| `eos_ai/context_builder.py` | Platform context assembly (wraps UMH context builder) |
| `eos_ai/model_router.py` | Platform model router (wraps UMH model router, adds CC SDK) |

**Why:** These are platform-specific orchestration, not generic intelligence. UMH extracted
the reusable kernel (execution engine, model routing, context assembly, world model,
governance). What remains in eos_ai is the EOS-specific wrapper that composes UMH
capabilities for a specific deployment. This is the correct architectural boundary.

---

## 6. Confirmation

### UMH is sole execution engine
- All LLM calls route through `umh.adapters.model_router` or `umh.execution.engine`
- Platform code (`eos_ai`) wraps UMH, never bypasses it
- One known violation: `dm_monitor.py` calls `google.genai` directly for Instagram OCR

### No parallel systems exist
- `core/` archived (zero production consumers)
- `eos_ai/` is a platform layer that delegates to UMH, not a competing engine
- `CognitiveLoop` deprecated (format_response_footer only)
- `ExecutionSpine` delegates to UMH's `run_via_umh()`

### System behavior unchanged
- 753/755 unit tests pass (same 2 pre-existing Neon UUID failures)
- 288/290 adapter tests pass (same 2 pre-existing lifecycle failures)
- 120/120 runtime tests pass
- All 4 Docker containers restart cleanly
- Docker compose config validates

### Boundary enforcement
- UMH imports: ZERO references to eos_ai, core, services, or scripts
- `_holding` references: ZERO in runtime code
- Structural compliance: 23/23 checks pass

---

## Remaining Work (Phase 12)

| Item | Description |
|------|-------------|
| Eliminate `eos_ai/` | Migrate 14 service-critical modules to `interfaces/` + UMH adapters |
| Eliminate `services/` | Update Docker compose to reference `interfaces/` paths |
| Eliminate `parsers/` | Move into `tools/` |
| Remove compatibility symlinks | `infra/`, `scripts/`, `vault/`, `core/` |
| Create `pyproject.toml` | Package definition for UMH |
| Update `CLAUDE.md` | Remove references to deleted paths |
| Clean eos_ai dead code | 134 modules never imported by anything |

---

*Phase 11 establishes the target structure. Phase 12 completes the migration.*
