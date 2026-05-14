# W0 CODEBASE TRUTH MAP — Phase 96.8BH

> Generated: 2026-05-09
> Auditor: Developer Agent (Claude Code)
> Method: Full repository forensic audit — no code modified

---

## Executive Summary

The /opt/OS repository contains **2,465 Python files** across **11,624 total files**.
Only **~95 Python modules** are reachable from the 2 running Docker services.
The remaining **~2,370 modules** fall into four categories:
proof-only (runs but produces artifacts only), standalone scripts,
legacy architecture (umh/), or dead code.

### Key Numbers

| Metric | Count |
|--------|-------|
| Total Python files | 2,465 |
| Total Markdown files | 7,949 |
| Total test files | 598 |
| Running Docker containers | 2 (os-discord, os-webhook) |
| Defined Docker services | 5 (os-discord, os-bot, os-monitor, os-scraper, os-webhook) |
| Runtime-wired eos_ai modules | ~35 of 123 top-level |
| Runtime-wired core modules | ~24 of 221 (via substrate handler only) |
| Runtime-wired umh modules | 0 of 826 |
| User-facing commands | 123 (83 bot + 11 inline + 26 substrate + 3 meta) |
| Discord bot file size | 5,296 lines |
| Substrate command handler size | 4,424 lines |

### Critical Findings

1. **83 files have unresolved git merge conflicts** — 76 skill files, 3 test files,
   3 Python files, 1 Obsidian plugin. These are committed and broken.
2. **Two disconnected ingestion systems exist** — The working one (eos_ai/gws_scanner.py)
   bypasses the substrate governance framework entirely. The substrate ingestion
   pipeline has never processed real data.
3. **19,961 lines of constitutional engines are pure proof-generators** — They
   produce artifacts claiming L5 maturity with "founder_confirmed: true" but
   these values are hardcoded, not derived from observation.
4. **5 phantom imports in discord_bot.py** — eos_ai/runtime/ modules that are
   imported via try/except but the files don't exist on disk.
5. **scripts/ and tools/ are 90% duplicated** — 178 vs 186 files, nearly identical.
6. **eos_ai/platforms/eos/ (12 modules) is completely dead code** — Self-referential
   island with zero imports from anything outside the directory.

### Truthful Maturity State

The system has **one production-grade runtime path**: Discord bot → eos_ai gateway → LLM router.
The **substrate execution spine** (Discord → spine → router → relay → Windows workstation)
is architecturally complete with proof artifacts but depends on Windows workstation availability.
The **ingestion pipeline** has two disconnected paths: the working GWS scanner (28 docs,
283K words ingested) and the substrate governance framework (never run on real data).

---

## 1. Actual Runtime Architecture

### What Is Running Right Now

```
Docker containers (UP):
  os-discord  → python3 services/discord_bot.py  (2G RAM, 16h uptime)
  os-webhook  → python3 services/calendly_webhook.py (128M RAM, 2 weeks uptime)

Docker containers (DOWN):
  os-bot      → python3 services/telegram_control.py (512M, NOT running)
  os-monitor  → python3 services/dm_monitor.py (1.5G, NOT running)
  os-scraper  → python3 services/overnight_scrape.py (one-shot, NOT running)
```

### Runtime Import Chain

```
services/discord_bot.py (5,296 lines)
  ├── eos_ai.gateway              → EOSGateway (core conversational loop)
  ├── eos_ai.context              → load_context_from_env
  ├── eos_ai.knowledge_integrator → KnowledgeIntegrator
  ├── eos_ai.voice_engine         → VoiceEngine
  ├── eos_ai.business_instance    → get_ai_name
  ├── eos_ai.model_router         → get_router, TaskType
  ├── eos_ai.cc_sdk               → query_cc_sync
  ├── eos_ai.db                   → get_conn (Neon)
  ├── eos_ai.substrate.*          → 20 substrate modules (voice, text, session)
  ├── eos_ai.runtime.*            → 5 runtime modules (work_state, live_loop, etc.)
  ├── handlers/intent_handler     → run_gateway, CHANNEL_MAP
  ├── handlers/pipeline_handler   → handle_pipeline_update
  ├── handlers/cc_command_handler → try_inline_commands (11 commands)
  └── handlers/substrate_command_handler → (4,424 lines)
        └── core.workstation.*    → 14 workstation engines
        └── core.registry.*      → canonical_command_registry_v1
        └── core.runtime.*       → 3 runtime contracts
        └── core.control_plane_router.* → router_v1
        └── core.actuation.*     → actuator_maturity_v1
```

### Layer Topology

```
Layer 0: Docker / OS
Layer 1: services/discord_bot.py — THE single runtime entry point
Layer 2: eos_ai/ — 35 modules actively imported (~29% of 123)
Layer 3: eos_ai/substrate/ — 20 of 163 modules imported at boot (~12%)
Layer 4: eos_ai/runtime/ — 5 of 2 modules imported (tiny but active)
Layer 5: core/ — 24 of 221 modules reachable via substrate_command_handler (~11%)
Layer 6: umh/ — 0 of 826 modules imported by anything running (0%)
```

---

## 2. File / Module Inventory

### Top-Level Directory Purposes

| Directory | Files (py) | Purpose | Status |
|-----------|-----------|---------|--------|
| eos_ai/ | 305 | AI intelligence layer | PARTIAL ACTIVE — 35 top-level + 20 substrate wired |
| umh/ | 895 | Universal Meta Harness (prior architecture) | DORMANT — 0 runtime imports |
| core/ | 234 | Execution contracts & workstation engines | PARTIAL ACTIVE — 24 wired via substrate handler |
| tests/ | 598 | Test suite | MIXED — mostly proof-validation tests |
| scripts/ | 178 | CLI tools and automation | STANDALONE — invoked manually |
| tools/ | 186 | Mirror of scripts/ (90% duplicate) | DUPLICATE — should be consolidated |
| services/ | 21 | Docker service entry points | ACTIVE — 2 of 5 running |
| skills/ | ~200 dirs | CC skill definitions (markdown) | ACTIVE — loaded on demand by CC |
| 10_Wiki/ | ~300 | Knowledge wiki (Obsidian vault) | REFERENCE — not runtime |
| data/ | ~800 | Runtime artifacts, proofs, registries | MIXED — some active, some stale |
| saas/ | ~150 | SaaS TypeScript frontend | SEPARATE PROJECT |
| docs/ | ~200 | System reports and plans | REFERENCE |

### eos_ai/ Module Classification

**RUNTIME-WIRED (imported by discord_bot or its handlers):**

```
business_instance    cc_sdk              confidentiality     context
coordination_engine  daily_sync          db                  delegation_tracker
discord_utils        doc_creator         email_gps           event_manager
expense_tracker      founder_capture     founder_rate        gateway
gws_connector        ideal_week          knowledge_integrator meetings
model_router         okr_tracker         onboarding_engine   orchestrator
person_recognition   personal_admin      portfolio_advisor   quality_gate
runtime.*            stakeholder_map     subscription_tracker substrate.*
task_yield_matrix    travel_manager      voice_engine        world_pulse
```

**STANDALONE (exist but not imported by runtime):**

```
accountability       agent_hierarchy     agent_messages      agent_runtime
agent_teams          ai_identity         authority_engine    browser_agent
ceo_agent            ceo_intelligence    ceo_operational_standards  channel
claude_skill_registry cognitive_loop     company_instantiator context_builder
context_compaction   decision_log        document_filer      ea_operational_standards
email_reviewer       embedder            embedding_engine    eod_closing_loop
error_handler        event_bus           evolution_engine    execution_engine
execution_loop       execution_spine     feedback_loop       goal_selector
gws_scanner          harness_registry    higgsfield_client   human_intelligence
input_intelligence   integration_test    intent_router       knowledge_domains
knowledge_graph      knowledge_layers    martell_patterns    media_processor
model_preferences    notebooklm_sync     notion_publisher    notion_sync
onboarding_backfill  os_registry         os_trinity          output_validator
pattern_engine       portfolio_advisor_standards  primitive_registry  primitives
principle_engine     proactive_engine    provider_health     reality_context
reality_engine       research_engine     scrapling_connector self_awareness
session_state        setup_wizard        signal_hierarchy    skill_improvement
skill_registry       skill_registry_v2   stage_manager       status
strategy_engine      system_context      system_health       task_executor
template_library     template_registry   tenant              transaction_workflow
trinity              user_model          venture_knowledge   voice_interface
week_architect       workflow_engine     world_model
```

**Note:** "Standalone" does not mean "dead" — some are invoked by scripts/ or
manually via `python3 -c "..."`. But they are not part of the live Discord bot
runtime path.

### core/ Module Classification

**RUNTIME-WIRED (via substrate_command_handler.py):**

```
actuation/actuator_maturity_v1
control_plane_router/control_plane_router_v1
control_plane_router/router_contracts
registry/canonical_command_registry_v1
runtime/adapter_registry_contracts
runtime/runtime_bootstrap_state_v1
workstation/adapter_autogeneration_engine_v1
workstation/adaptive_governance_intelligence_engine_v1
workstation/constitutional_antifragility_resilience_engine_v1
workstation/constitutional_epistemic_intelligence_engine_v1
workstation/constitutional_identity_continuity_engine_v1
workstation/constitutional_resource_economics_engine_v1
workstation/constitutional_strategic_intelligence_engine_v1
workstation/constitutional_substrate_governance_layer_v1
workstation/constitutional_telos_alignment_engine_v1
workstation/distributed_constitutional_substrate_federation_v1
workstation/environment_mapping_engine_v1
workstation/foreground_cu_ingestion_execution_v1
workstation/governed_recursive_orchestration_engine_v1
workstation/persistent_substrate_continuity_engine_v1
workstation/recursive_capability_planning_engine_v1
workstation/relay_execution_transport_v1
workstation/visible_actuation_proof_v1
workstation/workstation_node_registry_v1
workstation/workstation_relay_self_heal_v1
```

**PROOF-ONLY / CONTRACT-ONLY (not imported by any running service):**

```
action_system/ (11 modules)      — governed action lifecycle contracts
adapter_engine/ (4 modules)      — adapter boundary validation
adapter_package_manager/ (25 modules) — CU package maturity tracking
adapters/ (4 modules)            — Google Drive/Docs adapters
coherence/ (3 modules)           — spine coherence validation
connectors/ (5 modules)          — CRM/email/content connectors
control_plane.py                 — orchestrator control plane
domain/ (3 modules)              — domain context (creator, eos, lyfe)
environment_bridge/ (15 modules) — VPS↔local bridge infrastructure
execution/ (3 modules)           — action execution contracts
governance/ (1 module)           — execution authority engine
interpretation/ (1 module)       — interpretation engine
mastery_engine/ (3 modules)      — tool mastery contracts
memory/ (1 module)               — canonical memory query contracts
ontology/ (1 module)             — primitive decomposition
orchestrator/ (8 modules)        — core orchestrator pipeline
planning/ (1 module)             — execution planning candidates
runtime/ (rest of 15 modules)    — worker runtime, supervisor, etc.
security/ (8 modules)            — RBAC, audit, identity
state/ (1 module)                — transformation state ledger
tool_mastery_author_agent/ (10 modules) — TME author agent
tool_mastery_manager/ (11 modules)     — TME manager
tool_mastery_research_agent/ (14 modules) — TME research agent
world_model/ (4 modules)         — canonical world model
```

### umh/ Classification

**STATUS: DORMANT PARALLEL ARCHITECTURE**

826 Python modules organized into 50+ subdirectories. The UMH was an earlier
attempt at a domain-independent intelligence substrate. It has:

- 170 substrate modules
- 147 runtime_engine modules
- 66 runtime modules
- Full test coverage in tests/unit/ (100+ phase tests)
- Its own entry point (umh/run.py, umh/__main__.py)
- Its own control plane API

**No umh module is imported by any running service, eos_ai module, or core module.**
The only import is from scripts/demo_mvp_loop.py (manual demo script).

The UMH represents completed engineering work that has been architecturally
superseded by eos_ai/substrate/ + core/. It should be archived, not deleted,
as it contains design patterns that may be referenced.

---

## 3. Command Surface Map

### Discord Bot Commands (83 total — all ACTIVE)

| Category | Count | Examples |
|----------|-------|---------|
| Session / Voice | 6 | !answer, !watcher_status, !join, !leave, !say, !trace |
| EOS Core | 17 | !brief, !status, !portfolio, !eod, !approve, !pending, !help |
| Day Operations | 2 | !openday, !closeday |
| Calendar / Email | 14 | !cal, !focus, !inbox, !draft, !waiting, !accept, !decline |
| Relationship | 2 | !relationship, !nurture |
| Financial | 7 | !expenses, !budget, !subscriptions, !invoices, !invoice |
| Founder Rate / Time | 8 | !yield, !founderrate, !logtime, !timeaudit, !idealweek |
| Planning | 3 | !year, !rocks, !okr |
| Drive / Documents | 13 | !drive, !driveaudit, !briefdoc, !board, !slides, !factcheck |
| Travel / Personal | 7 | !trip, !flights, !hotels, !dates, !gift |
| Stakeholder / PR | 4 | !board_update, !talkingpoints, !pr, !event |

### Inline Commands (11 — via cc_command_handler.py)

!followup, !travel, !nomeetings, !confirm_event, !meetingroi,
!competitive, !documents, !audit, !stakeholders, !add_stakeholder,
+ calendar write detection (natural language)

### Substrate Commands (26 canonical + 3 meta)

All registered in core/registry/canonical_command_registry_v1.py.
Synchronized across 4 layers: registry → router → adapter → handler.

| Category | Commands |
|----------|----------|
| Chrome/GUI | !chrome, !chrome-open-google-drive, !chrome-proof, !doc |
| Ingestion | !extract, !ingest-candidate, !ingest-safe-doc, !ingest-safe-doc-cu |
| Environment | !explore-environment |
| Memory | !promote-memory, !query-memory |
| Reports | !actuator-proof, !adapter-report, !capability-report, !orchestration-report |
| Constitutional | !constitution-report, !federation-report, !economics-report, !strategy-report |
| Constitutional (cont.) | !epistemic-report, !identity-report, !telos-report, !resilience-report |
| Continuity | !continuity-report, !governance-intelligence-report |
| Infrastructure | !ping, !relay-status |
| Meta | !commands, !version, !runtime |

### Stub Command

`!block` — defined in discord_bot.py but sends placeholder text. Not wired to calendar API.

---

## 4. Ingestion System Map

### CRITICAL: Two Disconnected Ingestion Systems

**System A — The Working Scanner (eos_ai/gws_scanner.py):**
Real Google Workspace API calls via `npx @googleworkspace/cli`. Has ingested
28 documents (283K words with tab-aware extraction), produces gws_context.md
(updated daily), writes to Neon, routes by venture. Feeds the cognitive loop.
**This system bypasses the substrate governance framework entirely.**

**System B — The Substrate Framework (core/adapters/ + core/world_model/):**
Elaborate governance/proof/lineage pipeline (~30 files, ~8K lines) defining
how ingestion *should* work through governed transitions. The spine execution
chain runs (authority → gate → sync → dispatch), but:
(a) dispatches to a simulated local worker (0ms execution)
(b) the Drive/Docs adapters don't make API calls — they wrap pre-extracted content
(c) no real document content has ever flowed through this pipeline
(d) the world model promotion path has never been executed

### Component Inventory

| Component | Files | Status | Evidence |
|-----------|-------|--------|----------|
| **SYSTEM A (Working)** | | | |
| GWS scanner | eos_ai/gws_scanner.py | **PROVEN** | 28 docs, 283K words, updated daily |
| GWS connector | eos_ai/gws_connector.py | **PROVEN** | Runtime-wired, calendar/drive/gmail |
| Tab-aware extraction | data/drive_doc_ingestion_tab_aware/ | **PROVEN** | 321 tabs, real API data |
| Canonical source records | data/canonical_source_records/w0_001/ | **PROVEN** | 28 doc records + analysis |
| **SYSTEM B (Framework)** | | | |
| Google Drive adapter | core/adapters/google_drive_adapter_v1.py | **SIMULATED** | No API calls, proof-object factory |
| Google Docs adapter | core/adapters/google_docs_adapter_v1.py | **SIMULATED** | Wraps pre-extracted content |
| Live ingestion pipeline | core/adapters/live_drive_docs_ingestion_pipeline_v1.py | **SIMULATED** | Never run end-to-end |
| **CU PATH** | | | |
| CU sample execution | data/drive_doc_cu_review_sample/ | **PARTIALLY_PROVEN** | Tab detection worked, extraction failed |
| Drive CU inventory | data/drive_cu_inventory/ | **PROVEN** | Real UI Automation result |
| Foreground CU verification | core/runtime/foreground_cu_verification_v1.py | **UNVERIFIED** | No proof artifacts |
| CU ingestion execution | core/workstation/foreground_cu_ingestion_execution_v1.py | **UNVERIFIED** | No ingestion proofs |
| **POST-EXTRACTION** | | | |
| Primitive decomposition | core/ontology/primitive_decomposition_v1.py | **UNVERIFIED** | Code exists, never run |
| Canonical world model | core/world_model/ (4 files) | **SIMULATED** | Example candidates only |
| Memory promotion governance | data/runtime/w0_memory_governance/ | **SIMULATED** | Example/template files |
| Interpretation engine | core/interpretation/interpretation_engine_v1.py | **SIMULATED** | 1 proof file |
| **INFRASTRUCTURE** | | | |
| Spine coherence | core/coherence/ (3 files) | **PROVEN** | Gate proofs + sync proofs |
| Transformation ledger | core/state/transformation_state_ledger.py | **PROVEN** | 131 entries, active today |
| Spine dispatch queue | data/runtime/spine_dispatch_queue/ | **PROVEN** | Active dispatch records |
| Environment mapping | core/workstation/environment_mapping_engine_v1.py | **UNVERIFIED** | Output dir doesn't exist |

### Ingestion Pipeline Completeness

```
Source Discovery (Google Drive scan)     ████████████████████ 100% — GWS scanner works
Document Access (API or CU)              ████████████░░░░░░░░  60% — API works, CU needs relay
Content Extraction                       ████████████████░░░░  80% — Tab-aware, needs real doc run
Primitive Decomposition                  ████░░░░░░░░░░░░░░░░  20% — Code exists, never run
Canonical Memory Promotion               ██░░░░░░░░░░░░░░░░░░  10% — Framework only
World Model Integration                  ██░░░░░░░░░░░░░░░░░░  10% — Example candidates only
Full End-to-End Pipeline                  ░░░░░░░░░░░░░░░░░░░░   0% — Never completed
```

### What's Blocking Full Ingestion

1. **No end-to-end pipeline execution** — Individual components work in isolation
   but the full path (scan → extract → decompose → promote → integrate) has
   never run on a single real document
2. **CU path depends on Windows workstation relay** — Relay is not always online
3. **Primitive decomposition is unverified** — ontology/primitive_decomposition_v1.py
   has no test evidence or proof artifacts
4. **Memory promotion is framework-only** — Example JSONs exist but no real
   document has been promoted to canonical memory
5. **No canonical memory query validation on real data** — Query contracts exist
   but have only been tested against example candidates

---

## 5. Workstation / Relay Map

### Component Inventory

| Component | File | Status | Evidence |
|-----------|------|--------|----------|
| Relay node registry | core/workstation/workstation_node_registry_v1.py | ACTIVE | Loaded by substrate handler |
| Relay execution transport | core/workstation/relay_execution_transport_v1.py | ACTIVE | SSH check, Chrome proof send |
| Relay self-heal | core/workstation/workstation_relay_self_heal_v1.py | ACTIVE | Health assessment wired |
| Relay heartbeat | core/workstation/workstation_relay_heartbeat_v1.py | PARTIALLY_PROVEN | Heartbeat JSON exists |
| Relay proof | core/workstation/workstation_relay_proof_v1.py | SIMULATED | Proof classification code |
| Relay node | core/workstation/workstation_relay_node_v1.py | PARTIALLY_PROVEN | Test file exists |
| VPS-local bridge | core/environment_bridge/vps_local_bridge.py | PROOF_ONLY | Not imported by runtime |
| Local pull protocol | core/environment_bridge/local_pull_protocol.py | PROOF_ONLY | Not imported by runtime |
| Heartbeat monitor | core/environment_bridge/heartbeat.py | PROOF_ONLY | Not imported by runtime |
| Work packet builder | core/environment_bridge/w0_packet_builder.py | PROOF_ONLY | Not imported by runtime |
| Tmux surface | core/environment_bridge/tmux_surface.py | PROOF_ONLY | Not imported by runtime |
| Chrome visible launch | core/environment_bridge/chrome_visible_launch.py | PROOF_ONLY | Test exists |
| Windows foreground actuator | core/actuation/windows_foreground_actuator_v1.py | SIMULATED | Actuator maturity proofs |
| Visible actuation proof | core/workstation/visible_actuation_proof_v1.py | ACTIVE | Called by substrate handler |
| Desktop adapter contracts | core/environment_bridge/windows_desktop_*.py | ACTIVE | 3 files used by handler |
| Local worker runtime daemon | eos_ai/substrate/local_worker_runtime_daemon.py | PARTIALLY_PROVEN | Has test, heartbeat JSON exists |
| Local worker auto loop | eos_ai/substrate/local_worker_auto_loop.py | PARTIALLY_PROVEN | Dispatcher code exists |
| PowerShell relay scripts | *.ps1 (4 files) | UNKNOWN | Present but not audited |

### Constitutional / Governance Engines (core/workstation/)

All 10 constitutional engines are **callable via bot commands** through substrate_command_handler.py
and produce report artifacts to data/runtime/workstation_relay/.
They are **PROOF_ONLY / REPORT_GENERATORS** — not runtime enforcement.

| Engine | Command | Evidence |
|--------|---------|----------|
| constitutional_substrate_governance_layer_v1 | !constitution-report | Report artifacts exist |
| distributed_constitutional_substrate_federation_v1 | !federation-report | Report artifacts exist |
| constitutional_resource_economics_engine_v1 | !economics-report | Report artifacts exist |
| constitutional_strategic_intelligence_engine_v1 | !strategy-report | Report artifacts exist |
| constitutional_epistemic_intelligence_engine_v1 | !epistemic-report | Report artifacts exist |
| constitutional_identity_continuity_engine_v1 | !identity-report | Report artifacts exist |
| constitutional_telos_alignment_engine_v1 | !telos-report | Report artifacts exist |
| constitutional_antifragility_resilience_engine_v1 | !resilience-report | Report artifacts exist |
| adaptive_governance_intelligence_engine_v1 | !governance-intelligence-report | Report artifacts exist |
| governed_recursive_orchestration_engine_v1 | !orchestration-report | Report artifacts exist |

**Note:** These engines produce governance analysis reports. They do NOT control
runtime behavior — they analyze and report on the system's constitutional state.
They are proof-generation systems, not enforcement systems.

### Workstation Readiness

```
SSH transport to Windows          ████████████████████ PROVEN — relay_execution_transport works
Chrome proof via relay            ████████████████░░░░ PARTIALLY — works when relay online
Local worker daemon               ████████████░░░░░░░░ PARTIALLY — heartbeat exists, not always running
Foreground CU via relay           ████████░░░░░░░░░░░░ SIMULATED — code wired, never founder-confirmed
Desktop actuation (real)          ████░░░░░░░░░░░░░░░░ UNVERIFIED — Windows actuator not confirmed
Auto-start / self-heal            ████████████░░░░░░░░ PARTIALLY — code exists, health check works
Tailscale connectivity            ████████████████████ PROVEN — VPS on Tailscale network
```

---

## 6. Proof / Test Matrix

### Test File Distribution

| Directory | Count | What it tests |
|-----------|-------|---------------|
| tests/ (root) | ~350 | Mostly core/ and recent phase proofs |
| tests/unit/ | ~180 | UMH phases 2-74 (ALL umh/ only) |
| tests/substrate/ | ~40 | eos_ai/substrate/ modules |
| tests/runtime/ | ~10 | eos_ai/runtime/ lifecycle |
| tests/platforms/ | ~10 | eos_ai/platforms/eos/ |
| tests/adapters/ | ~5 | Voice/event adapters |

### Proof Artifact Inventory (data/runtime/)

| Directory | Files | Evidence Type |
|-----------|-------|---------------|
| sync_proofs/ | 195 | **REAL** — live spine sync checks from today |
| transformation_ledger/ | 131 | **REAL** — active state transitions from today |
| test_spine_ledger/ | 42 | Test spine states |
| test_spine_gate_proofs/ | 14 | Test gate validations |
| workstation_relay/ | 11 | Constitutional report artifacts |
| local_worker_runtime/ | 6 | Heartbeat + processed requests |
| spine_gate_proofs/ | 6 | Live gate proofs |
| actuator_maturity_proofs/ | 6 | Actuator maturity summaries |
| canonical_world_models/ | 6 | **EXAMPLE** — rollback/template files |
| workpacket_execution_gate_proofs/ | 5 | Gate validation examples |
| w0_ingestion_candidates/ | 5 | **EXAMPLE** — ingestion router result examples |
| w0_memory_governance/ | 5 | **EXAMPLE** — promotion router examples |
| spine_proofs/ | 4 | Spine execution proofs |
| spine_dispatch_queue/ | 4 | Active dispatch records |
| canonical_memory_query_proofs/ | 4 | **EXAMPLE** — query examples |
| execution_authority_proofs/ | 4 | Authority validation examples |
| execution_planning_candidates/ | 4 | Planning examples |
| w0_extraction_proofs/ | 4 | **EXAMPLE** — extraction proof examples |
| e2e_execution_proofs/ | 3 | Execution chain summaries |
| routed_execution_proofs/ | 3 | Routed work packet examples |
| w0_interaction_proofs/ | 3 | **EXAMPLE** — interaction proof examples |
| interpretation_proofs/ | 1 | Single interpretation proof |
| runtime_proofs/ | 2 | .gitkeep files only |

### Active vs Example Classification

**ACTIVE (generated by running system today):**
- sync_proofs/ — 195 sync checks, timestamps from 2026-05-09
- transformation_ledger/ — 131 state transitions, timestamps from 2026-05-09
- spine_dispatch_queue/ — dispatch records with today's commit hashes
- spine_gate_proofs/ — gate validation records

**EXAMPLE/TEMPLATE (manually created, not from real execution):**
- canonical_world_models/ — "rollback_receipt_example.json"
- w0_* directories — files named "*_example.json", "*_runtime_proof_example.json"
- canonical_memory_query_proofs/ — "rollback_reference_query_example.json"
- execution_planning_candidates/ — "risk_envelope_example.json"
- workpacket_execution_gate_proofs/ — "expired_packet_gate.json"

### Overclaimed Maturity

**CLAUDE.md "Confirmed Working" Overclaims (6 of 10 entries have zero evidence):**

| Component | Claimed | Tests | Proofs | Verdict |
|-----------|---------|-------|--------|---------|
| eos_ai/cognitive_loop.py | 8-stage loop working | 0 | 0 | **OVERCLAIMED** |
| eos_ai/agent_runtime.py | multi-model router live | 0 | 0 | **OVERCLAIMED** |
| eos_ai/portfolio_advisor.py | board view working | 0 | 0 | **OVERCLAIMED** |
| eos_ai/model_preferences.py | business context routing | 0 | 0 | **OVERCLAIMED** |
| eos_ai/media_processor.py | voice synthesis 303KB | 0 | 0 | **OVERCLAIMED** |
| services/telegram_control.py | NL + media routing | 0 | 0 | **OVERCLAIMED** |
| eos_ai/db.py | Neon connection + RLS | 20 | 0 | Partially supported |
| eos_ai/memory.py | all writes to Neon | 55 | 8 | Supported |
| eos_ai/authority_engine.py | 4 risk classes | 6 | 4 | Supported |
| eos_ai/orchestrator.py | 6am cron + morning | 8 | 0 | Partially supported |

Note: These may work in practice (they are imported by the running Discord bot),
but "confirmed working" in CLAUDE.md should be backed by at least one test or
proof artifact. Manual verification that was never codified is not confirmation.

**Proof artifact overclaims:**
- Constitutional engines produce proof files claiming `founder_confirmed: true`
  and `is_dry_run: false`, but these values are hardcoded in the code, not
  derived from founder interaction or real execution.
- All w0_* proof directories contain only `*_example.json` template files.
- Canonical world model "rollback receipts" are example structures, not real rollbacks.

### Test Suite Reality

**22,087 pytest-discoverable test functions across 719 files** — but:

- 9,891 test functions (45%) are in tests/unit/ and test only umh/ (dormant)
- 159 test files use a non-standard check() runner invisible to pytest
- 17 test files fail to collect due to broken imports
- 83 files have unresolved merge conflicts (3 test files included)
- All 15 service modules have zero test coverage
- 120 of 123 eos_ai top-level modules have zero dedicated test coverage
- core/ has good coverage only in workstation/ (800+ tests) and execution/ (114 tests)

---

## 7. Drift / Deprecation Findings

### CRITICAL: Unresolved Merge Conflicts (83 files)

**3 Python test files with merge markers:**
- tests/test_command_surface_sync_v1.py
- tests/test_tme_umh_scope.py
- tests/test_live_runtime_identity_v1.py

**~76 SKILL.md files** in skills/tools/ (anthropic_api, claude_code, apify, bash,
docker, gmail, tmux, and many more). These are actively loaded by TME.

**1 Obsidian plugin** (.obsidian/plugins/obsidian-tasks-plugin/main.js)

**1 fix script** (scripts/fix_merge_conflicts.py — itself has conflicts)

These files are committed to git with `<<<<<<<` markers. The skill files are
broken for TME loading. The test files cannot pass.

### Phantom Imports (5 missing files)

discord_bot.py imports these via try/except — they silently fail:
- eos_ai/runtime/input_router.py — DOES NOT EXIST
- eos_ai/runtime/live_loop.py — DOES NOT EXIST
- eos_ai/runtime/session_registry.py — DOES NOT EXIST
- eos_ai/runtime/session_router.py — DOES NOT EXIST
- eos_ai/runtime/surface_registry.py — DOES NOT EXIST

Only 2 files actually exist in eos_ai/runtime/:
- eos_ai/runtime/work_state.py (imported and used)
- eos_ai/runtime/provider_state.py (imported via model_router)

### Dead Code Islands

**eos_ai/platforms/eos/ — 12 modules, zero external imports:**
context_builder, decision_log, delegation, discord_hook, ea_orchestrator,
execution_bridge, intent_routing, live_runtime, response_formatter, roles,
streaming_bridge, voice_runtime. These form a self-referential island with
no connection to any running service or eos_ai core module.

**eos_ai/ top-level — 9 modules with zero imports anywhere:**
company_instantiator, higgsfield_client, integration_test, notion_sync,
primitive_registry, system_context, transaction_workflow, week_architect,
workflow_engine.

**eos_ai/substrate/ — 56 modules not imported by anything:**
contracts, comparators, and infrastructure modules built during proof phases
but never wired to the runtime.

### Naming Collisions (Confusing but Not Duplicates)

1. **core/control_plane.py ↔ core/action_system/control_plane.py** — Different
   systems with same name. Orchestrator lifecycle vs. governed action pipeline.

2. **core/capabilities.py ↔ core/capability.py** — Capability registry vs.
   permission/risk matrix. Recommend renaming capability.py to capability_enforcement.py.

3. **core/primitives.py ↔ core/primitives_extended.py ↔ eos_ai/primitives.py** —
   Three different abstraction layers (L0 ontological, extended overlays, runtime engine).

4. **eos_ai/context.py ↔ core/context.py** — Runtime env config vs. semantic
   composition context. eos_ai/context.py is the runtime-wired one.

### scripts/ ↔ tools/ Duplication

~90% identical content. 178 files in scripts/, 186 in tools/.
tools/ has a few extras (apify_scraper, cc_reply_webhook, cost_tracker,
heartbeat, icp_scorer, kpi_tracker, local_bridge_client/server, overnight_scrape).
scripts/ has a few extras (demo_mvp_loop, fix_merge_conflicts, phase75a_classifier,
phase75a_dep_scanner, prove_w0_* scripts).
**Consolidate to one directory.**

### Hardcoded Tailscale IPs (9 substrate files)

`100.74.199.102` (Windows desktop) hardcoded in 5 files:
advisor_bridge_transport.py, chrome_accessibility_launch_backend.py,
topology_contracts.py, tmux_environment_manager.py, windows_user_session_launcher.py

`100.77.233.50` (VPS) hardcoded in 2 files:
advisor_bridge_transport.py, topology_contracts.py

**Should read from os.getenv("EOS_LOCAL_BRIDGE_IP") instead.**

### Stale / Deprecated

1. **services/discord_bot.py.bak.20260508** — Contains merge conflict markers. Delete.
2. **eos_ai/.substrate_sandbox/** — Empty sandbox directory.
3. **eos_ai/.substrate_station/** — Meet captions directory, unclear if active.
4. **data/playgrounds/** — 6 playground directories from April 10-11, likely stale.
5. **data/sandboxes/** — 3 sandbox directories from April 10-11, likely stale.

### Stale Registry

**eos_ai/claude_skill_registry.py** is out of sync:
- 5 registered skills are missing from disk (voice-pipeline, agent-hierarchy,
  primitive-system, database-schema, ollama)
- 3 on-disk skills are not registered (browser-control, humanizer, last30days)

### UMH Status

**DORMANT PARALLEL ARCHITECTURE — 895 files, 0 runtime imports.**

The UMH (Universal Meta Harness) at /opt/OS/umh/ represents a complete prior
architecture generation with 50+ subdirectories. It has its own entry point
(umh/run.py), control plane API, and full test coverage in tests/unit/.

No umh/ module is imported by any running service, eos_ai/ module, or core/ module.
The only reference is scripts/demo_mvp_loop.py (manual demo).

78 Python filenames in umh/ are identical to eos_ai/ filenames — this is intentional
mirroring for a future migration, not accidental duplication. UMH was last modified
2026-05-08. It is an active parallel architecture, not dead code.

### Hardcoded Paths

`/opt/OS` appears in 228 files. This is appropriate for a single-VPS deployment
where Docker mounts /opt/OS:/app. Low priority for cleanup.

---

## 8. Current Truthful Maturity State

### By Layer

| Layer | Claimed | Actual | Gap |
|-------|---------|--------|-----|
| Discord bot + conversational AI | Production | **Production** | None — runs 24/7, 83 commands work |
| LLM routing (model_router) | Production | **Production** | None — CC SDK + Ollama chain active |
| Google Workspace connector | Production | **Production** | None — Drive/Docs/Gmail/Calendar work |
| Substrate voice pipeline | Production | **Partial** | Voice works but meeting intelligence untested in production |
| Substrate execution spine | Proven | **Proven (with constraints)** | Spine runs, but depends on Windows relay availability |
| Canonical command registry | Proven | **Proven** | 26 commands synchronized across 4 layers |
| Control plane router | Proven | **Proven** | Deterministic routing works |
| Workstation relay transport | Proven | **Partially proven** | SSH works, Chrome proof works when relay online |
| Foreground CU ingestion | Proven | **Simulated** | Code wired, never completed on real document |
| Canonical world model | Proven | **Framework only** | Example artifacts, no real data |
| Memory promotion governance | Proven | **Framework only** | Example artifacts, no real governance cycle |
| UMH (entire layer) | N/A | **Dormant** | Complete architecture, zero runtime connections |
| core/ action system | N/A | **Proof-only** | Contracts exist, not enforced at runtime |
| core/ security | N/A | **Proof-only** | RBAC/audit code, not enforced |

---

## 9. Full Ingestion Blockers

### Must Be Resolved Before Full Ingestion

1. **No end-to-end pipeline test** — The full path from source discovery through
   canonical memory promotion has never been executed as a single flow.
   Individual components work in isolation.

2. **Primitive decomposition is unverified** — core/ontology/primitive_decomposition_v1.py
   exists but has no test results, no proof artifacts, and no evidence of ever
   having been run on real content.

3. **No canonical memory store** — Memory promotion governance produces example
   JSONs but there is no actual canonical memory store to promote into.
   The destination doesn't exist.

4. **World model integration is framework-only** — core/world_model/ has candidate
   generation and promotion code but no real entities have been resolved or promoted.

5. **CU path requires Windows relay** — Foreground Comprehension Unit ingestion
   depends on the Windows workstation relay being online. The relay is not
   persistent (manual start required).

6. **No content quality validation** — After extraction, there is no validation
   that extracted content is correct, complete, or useful before promotion.

7. **No rollback mechanism tested** — Rollback receipt examples exist in
   canonical_world_models/ but the rollback path has never been exercised.

---

## 10. Recommended Next 3 Phases

### Phase 1: CRITICAL FIXES (Immediate, blocks everything)

**Goal:** Fix broken files and correct false claims.

1. **Resolve 83 merge conflict files** — Fix scripts/fix_merge_conflicts.py first,
   then run it. The 76 broken SKILL.md files block TME. 3 broken test files
   poison the test suite.
2. **Update CLAUDE.md confirmed-working list** — Remove the 6 components with
   zero evidence or add tests for them. Current list gives false confidence.
3. **Fix phantom imports** — Either create the 5 missing eos_ai/runtime/ files
   or remove the try/except imports from discord_bot.py.
4. **Sync claude_skill_registry.py** — Remove 5 phantom skills, add 3 missing ones.
5. **Replace hardcoded Tailscale IPs** — 9 substrate files should use env vars.
6. **Delete discord_bot.py.bak.20260508** — Contains merge conflicts, adds confusion.

### Phase 2: CONSOLIDATION (Low risk, high impact)

**Goal:** Reduce repo surface area by ~40%.

1. **Consolidate scripts/ and tools/** — Pick one, symlink or delete the other.
2. **Remove dead code** — eos_ai/platforms/eos/ (12 files), 9 dead eos_ai top-level
   modules, 56 dead eos_ai/substrate modules.
3. **Archive stale data** — data/playgrounds/, data/sandboxes/ (April artifacts).
4. **Move UMH tests** — The 180 tests/unit/ files that only test umh/ should be
   moved to umh/tests/ or umh_tests/ to separate them from production tests.

### Phase 3: CONNECT THE TWO INGESTION SYSTEMS (High impact, the actual goal)

**Goal:** Bridge System A (working scanner) and System B (substrate framework)
into a single end-to-end pipeline that completes one real ingestion cycle.

1. **Feed scanner output into substrate pipeline** — The GWS scanner extracts real
   content. The substrate pipeline takes pre-extracted content as input. Wire
   scanner output → substrate pipeline input.
2. **Run primitive decomposition on real content** — Use the 28 already-extracted
   documents as test data. This has never been done.
3. **Create canonical memory store** — The destination doesn't exist yet. Build it.
4. **Run one complete cycle** — scan → extract → decompose → promote → query.
5. **This is the only path from "framework" to "working ingestion."**

---

## Appendix A: File Count Summary

```
Python modules:    2,465
  eos_ai/:           305  (123 top-level + 163 substrate + 2 runtime + 17 other)
  umh/:              895  (dormant)
  core/:             234  (24 runtime-wired)
  tests/:            598  (180 umh-only, rest mixed)
  scripts/:          178  (standalone)
  tools/:            186  (90% duplicate of scripts/)
  services/:          21  (5 entry points)
  other:              48

Markdown:          7,949
  skills/:         ~2,000  (tool + business skills)
  10_Wiki/:          ~300  (knowledge wiki)
  docs/:             ~200  (system reports)
  .claude/:          ~100  (CC configuration)
  other:           ~5,349

Config/Data:         824 JSON, 45 JSONL, 40 shell scripts
```

## Appendix B: Docker Service Map

| Service | Container | Entrypoint | Status | Memory |
|---------|-----------|-----------|--------|--------|
| os-discord | os-discord | services/discord_bot.py | UP (16h) | 2G |
| os-webhook | os-webhook | services/calendly_webhook.py | UP (2w) | 128M |
| os-bot | os-bot | services/telegram_control.py | DOWN | 512M |
| os-monitor | os-monitor | services/dm_monitor.py | DOWN | 1.5G |
| os-scraper | os-scraper | services/overnight_scrape.py | DOWN (one-shot) | — |

## Appendix C: Runtime Data Directories

Active (today):
- data/runtime/sync_proofs/ — 195 files
- data/runtime/transformation_ledger/ — 131 files
- data/runtime/spine_dispatch_queue/ — 4 files
- data/runtime/spine_gate_proofs/ — 6 files

Static (example/proof artifacts):
- All w0_* directories — example JSONs
- canonical_world_models/ — rollback examples
- canonical_memory_query_proofs/ — query examples
- execution_planning_candidates/ — risk examples

---

**W0 CODEBASE TRUTH MAP — COMPLETE**

```
Repo mapped:                    YES
Runtime paths mapped:           YES
Command surface mapped:         YES
Ingestion components mapped:    YES
Workstation components mapped:  YES
Proof/test matrix created:      YES
Drift detected:                 YES
Overclaims identified:          YES
Full ingestion blockers:        YES (7 identified)
Next 3 phases recommended:      YES
Report: docs/system/phase968bh_codebase_truth_map.md
```
