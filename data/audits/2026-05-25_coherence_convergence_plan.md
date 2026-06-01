# UMH Coherence Convergence Phase — Execution Plan

**Date:** 2026-05-25
**Author:** Developer Agent + Classifier Agent
**Grounded in:** 100% ground-truth audit (17 agents, 1,450+ files)

---

## THE MISSION

Make every existing part either serve the unified organism or leave the active body.

Nothing gets deleted just because it's not running. Every subsystem classified as:

| Tag | Meaning |
|-----|---------|
| **PROMOTE** | Belongs in canonical runtime now |
| **MERGE** | Duplicates another system; absorb best parts |
| **ISOLATE** | Valid future module, not hot path yet |
| **ARCHIVE** | Useful reference, not active code |
| **DELETE** | Objectively dead/stale/no unique value |

---

## PART 1: COMPLETE SUBSYSTEM CLASSIFICATION

### Top-Level Directories

| Current | Files | Class | Destination | Action |
|---------|-------|-------|-------------|--------|
| `substrate/` | 594 py | PROMOTE | `substrate/` | Internal reorg. Fix 20+ outward dependency violations. |
| `adapters/` | 94 py | PROMOTE | `adapters/` | Delete awareness/, sensing/. Merge model_adapters/ into models/. |
| `transports/` | 37 py | PROMOTE | **`interfaces/`** (rename) | Rename. Already has discord/, api/, node_mesh/, presence/. |
| `services/` | 25 py | PROMOTE | `services/` | Thin entrypoints only. Delete jarvis/ (empty). Delete services/umh/ (data-only). |
| `projections/` | 23 py | PROMOTE | `projections/` | Absorb substrate/integrations/eos,lyfeos,creatoros/ here. |
| `cockpit/` | 55 ts | ISOLATE | `interfaces/cockpit/` | Move when deploying. Not hot path today. |
| `daemon/` | 15 py | ISOLATE | **`nodes/`** (rename) | Rename. Will contain vps/, windows/, containers/. |
| `scripts/` | 109 py | PROMOTE | `scripts/` | Archive ~25 dormant. Keep 10 active cron + 34 utility. |
| `tests/` | 55 py | PROMOTE | `tests/` | Keep. |
| `skills/` | varies | PROMOTE | `skills/` | Refresh 60/96 stale tool skills. Move .agents/ packages here. |
| `knowledge/` | 252 | PROMOTE | `knowledge/` | Absorb 10_Wiki/. |
| `docs/` | ~250 | ARCHIVE (partial) | `docs/` | Mass-update 107 stale eos_ai refs + 111 stale core/ refs. |
| `data/` | varies | PROMOTE | `data/` | Rotate mesh metrics (192 MB). Clean intermediaries. |
| `saas/` | 16 ts | ISOLATE | `projections/eos-saas/` (future) | Keep for now. Move under projections/ when deploying. |
| `agents/` | 11 md | PROMOTE | `agents/` | Keep. Soul docs. |
| `archive/` | 1 md | PROMOTE | `archive/` | Keep as archive destination. |
| `infra/` | 4 | PROMOTE | `infra/` | Absorb docker/. Consolidate secret duplication. |
| `docker/` | 3 | PROMOTE | `infra/docker/` | Merge into infra/. |
| `logs/` | varies | PROMOTE | `data/logs/` or keep | Consolidate under data/ or keep. |
| `umh/` | 44 py | **DELETE** | — | 0 external imports. 10,695 dead lines. Fix pyproject.toml first. |
| `runtime/` | 0 py | **DELETE** | — | Empty dir. Move .substrate_state.json to data/. |
| `frontend/` | 0 src | **DELETE** | — | Empty shell. Only compiled dist/, no source. |
| `apps/cockpit/` | 0 src | **DELETE** | — | Ghost. 150 MB node_modules, 0 source. Frees disk. |
| `media/` | 0 | **DELETE** | — | Empty directory. |
| `.claire/` | 3 py | **DELETE** | — | Stale worktree from merged branch. |
| `.planning/` | 7 md | **DELETE** | — | 2026-03-26 artifacts. Ref dead eos_ai/, 13_Scripts/. |
| `vault/` | 931 | ARCHIVE | `archive/vault/` | Historical session summaries. Move to archive/. |
| `10_Wiki/` | 37 | MERGE | `knowledge/wiki/` | Merge into knowledge/. |

### substrate/ Internal Classification

| Subdirectory | Files | Lines | Class | Destination | Action |
|--------------|-------|-------|-------|-------------|--------|
| `control_plane/` | ~50 | ~15K | PROMOTE | Keep | Core runtime. gateway.py shrinks as bot migrates to Substrate. |
| `control_plane/runtime/` | ~5 | ~5K | PROMOTE | Keep | Hot path: gateway.py + cognitive_loop.py. |
| `control_plane/router/` | 5 | ~2K | MERGE | Keep 1 canonical | Merge IntentRouter + ControlPlaneRouterV1 into ConcreteSignalRouter. |
| `control_plane/orchestrator/` | ~5 | ~3K | PROMOTE | Keep | Delete dead pipeline.py (0 imports). |
| `control_plane/agents,goals,strategy,...` | 11 dirs | varies | PROMOTE | Keep | All actively imported with clear consumers. |
| `execution/spine.py` | 1 | ~600 | PROMOTE | Keep | **THE canonical spine.** 8-stage async. |
| `execution/bridge/` | 71 | 27,261 | PROMOTE | Split subdirs | Zero dead code. Reorg into voice/, tasks/, station/, rituals/, discord/, nodes/. |
| `execution/runtime/` | 49 | ~19K | **DELETE** (mostly) | — | ~32 dormant v1 files. 2 shim files need import path migration first. |
| `execution/workers/workstation/` | 41 | ~17K | ISOLATE | `nodes/workstation/` | Constitutional engines. Only consumed by report_handlers.py. |
| `execution/pipeline.py` | 1 | ~400 | MERGE | Into spine.py | Absorb unique logic (DeliberationCouncil wire). |
| `execution/ingestion/` | ~5 | ~2K | PROMOTE | Keep | Canonical ingestion path. |
| `execution/voice/` | 3 | 853 | ISOLATE | Keep | STT/VAD/TTS. Not continuously active. |
| `execution/media/` | 2 | 346 | ISOLATE | Keep | Multimodal processor. |
| `execution/environments/` | 18 | 3,726 | ISOLATE | `nodes/environments/` | Windows desktop execution. |
| `execution/agents/` | 3 | 888 | ISOLATE | Keep | Browser + computer use agents. |
| `state/` | 62 | 10,386 | PROMOTE | Keep | Persistence backbone. Massively imported. |
| `governance/` | ~12 | ~4K | PROMOTE | Keep | Three engines → unified API. |
| `memory/` | 5 | ~1.5K | PROMOTE | Keep | Pipeline: candidate → promote → reconcile. |
| `understanding/` | 54 | 13,450 | PROMOTE | Keep | perception, knowledge, intelligence (20+ imports!), ontology, embedding. |
| `understanding/intelligence/` | 5 | ~1,800 | **PROMOTE** | Keep | **AUDIT CORRECTION**: 20+ external imports. NOT dormant. |
| `understanding/deliberation/` | 1 | 528 | ISOLATE | Keep | 1 import from pipeline.py. Council pattern. |
| `understanding/reality/` | 1 | 588 | **PROMOTE** | Keep | 4 imports from orchestrator.py. |
| `understanding/research/` | 1 | 677 | **PROMOTE** | Keep | 4 imports from orchestrator.py. |
| `sockets/` | 15 | 1,440 | PROMOTE | Keep | Clean hexagonal port layer. |
| `composition/` | 45 | 10,446 | PROMOTE | Keep | Tool Mastery Engine. |
| `integrations/` | 43 | 5,626 | MERGE | Split out | eos/lyfeos/creatoros → projections/. notion → adapters/. node_mesh → interfaces/. |
| `organism/` | 24 | 2,815 | PROMOTE | Keep | Agent runtime, advisor, homeostasis. |
| `intelligence/` | 3 | 1,128 | PROMOTE | Keep | runtime.py is hot-path. |
| `reality_model/` | 4 | 733 | ISOLATE | `substrate/simulation/` | Hypothesis testing. Not hot path. |
| `observability/` | ~5 | ~800 | PROMOTE | Keep | error_recorder.py. |
| `ontology/` | ~5 | ~1.5K | PROMOTE | Keep | primitives.py. Heavily imported. |
| `foundation/` | ~3 | ~500 | PROMOTE | Keep | laws.py. |
| `distribution/` | 3 | 513 | ISOLATE | `nodes/distribution/` | Node distribution. |
| `workstation/` | 2 | 238 | ISOLATE | `nodes/` | Workstation state. |
| `deployment/` | 2 | 239 | **DELETE** | — | 0 imports. Placeholder. |
| `learning/` | 1 | 1 | **DELETE** | — | Empty placeholder. |

### adapters/ Internal

| Subdirectory | Class | Destination | Action |
|--------------|-------|-------------|--------|
| `models/` | PROMOTE | Keep | Canonical intelligence routing. Absorb model_adapters/. |
| `model_adapters/` | MERGE | Into `models/` | Shim layer. 6 import sites to update. |
| `adapter_engine/` | PROMOTE | Keep | Lifecycle, capability catalog. |
| `google_workspace/` | PROMOTE | `adapters/google/` (rename) | GWS adapter. |
| `calendar/` | PROMOTE | `adapters/google/calendar/` or keep | Calendar adapter. |
| `notion/` | PROMOTE | Keep | Absorb substrate/integrations/notion/. |
| `browser/` | PROMOTE | Keep | Absorb browser_exports/. |
| `browser_exports/` | MERGE | Into `browser/` | Merge. |
| `data_source_adapters/` | PROMOTE | `adapters/data_sources/` (rename) | Ingestion sources. |
| `higgsfield/` | PROMOTE | Keep | Webhook adapter. |
| `scrapling/` | PROMOTE | Keep | Scraping adapter. |
| `tool_adapters/` | PROMOTE | `adapters/tools/` (rename) | Tool contracts. |
| `capabilities/` | ISOLATE | Keep | Creative gen, goose, ui_tars harnesses. |
| `notebooklm/` | ISOLATE | Keep | NotebookLM adapter. |
| `awareness/` | **DELETE** | — | 0 imports. crypto/markets/RSS/weather. |
| `sensing/` | **DELETE** | — | 0 imports. ABC with no implementations. |

---

## PART 2: SHADOW SYSTEM CONSOLIDATION

### Routers → 2 Canonical + 3 Supporting

| Router | Verdict | Action |
|--------|---------|--------|
| **ModelRouter** (adapters/models/model_router.py) | **CANONICAL** — intelligence | Keep. 24 direct + 50 via shim. |
| **ConcreteSignalRouter** (control_plane/router/) | **CANONICAL** — signals | Keep. Absorb IntentRouter + ControlPlaneRouterV1. |
| ControlPlaneRouterV1 | MERGE | Best logic → ConcreteSignalRouter. |
| IntentRouter | MERGE | Intent classification → stage in signal router. |
| HandoffRouter (organism/handoff.py) | PROMOTE | Different concern (agent handoff). Keep. |
| SignalRouter (transports/api/) | PROMOTE | Different layer (API). Keep. |
| ChannelRouter (transports/channels/) | PROMOTE | Different concern (channel mux). Keep. |
| CapabilityRouterV1 (execution/runtime/) | ISOLATE | CLI model routing. Future. |
| LiveRuntimeRouter (execution/runtime/) | DELETE | Dormant v1. |
| PerceptionRouter (umh/) | DELETE | Inside dead umh/. |
| DistributionLayer (distribution/) | ISOLATE | Node distribution. Future. |

### Execution Spines → 1 Canonical + 1 Downstream

| Spine | Verdict | Action |
|-------|---------|--------|
| **ConcreteExecutionSpine** (spine.py) | **CANONICAL** | 8-stage async. THE spine. |
| ExecutionSpine (legacy sync) | MERGE | Migrate 3 callers → ConcreteExecutionSpine. Delete. |
| ExecutionPipeline (pipeline.py) | MERGE | Absorb unique logic (council wire) into spine.py. |
| TaskPipeline (bridge/task_pipeline.py) | PROMOTE | Downstream task pipeline. Different concern. Keep. |
| CanonicalRuntimeSpine | DELETE | 1 ref (validation script). |
| LiveSubstrateRuntimeSpine | DELETE | 1 ref (test-only). |
| FullLiveIngestionSpine | DELETE | 0 refs. |
| OrchestratorPipeline | DELETE | 0 refs. |

### Memory → AgentMemory canonical, pipeline stays, thin wrappers merge

| System | Verdict | Action |
|--------|---------|--------|
| **AgentMemory + ConversationMemory** (state/memory/) | **CANONICAL** | 49 imports. Production Neon-backed. |
| Memory pipeline (candidate→promote→reconcile) | PROMOTE | Works. Start watcher daemon. |
| CanonicalMemoryStore (state/memory/contracts/) | PROMOTE | File-based store. Part of pipeline. |
| ClaudeBridge (memory/claude_bridge.py) | PROMOTE | Syncs CC memories. |
| ConcreteMemorySystem (control_plane/memory.py) | MERGE | Protocol wrapper. Merge into state/memory/. |
| RuntimeMemoryGovernanceBridge | DELETE | 0 imports. |

### Governance → Single API, Three Implementations

| Engine | Verdict | Production Path |
|--------|---------|-----------------|
| **AuthorityEngine** | PROMOTE | CognitiveLoop.run() L517 |
| **ConcreteGovernanceEngine** | PROMOTE | Substrate.execute() → router.route() |
| **ExecutionAuthorityEngine v1** | PROMOTE | spine_integration_v1.py L149 |

**Collapse plan:** Create `GovernanceGateway` in `substrate/governance/` that provides ONE API surface. Internally delegates to the appropriate engine based on execution context. Engines stay as implementations. End-state flow:

```
Structural Deny → Risk Classification → Permission Tier
→ Autonomy Level → Environment Policy → Approval Requirement → Audit Proof
```

### Duplicate Classes → Single Canonical Definition

| Class | Canonical | Duplicates to Remove |
|-------|-----------|---------------------|
| MemoryCandidate | `substrate/types.py` | memory/candidate_generator.py (dataclass), adapter_engine/ (dataclass) |
| MemoryEntry | `substrate/types.py` | state/memory/contracts/ (plain class) |
| MemoryType | `substrate/types.py` | adapter_engine/ (str Enum) |
| AgentRuntime | `adapters/models/agent_runtime.py` | organism/agent_runtime.py → rename to OrganismAgentRuntime |
| ApprovalStore | `substrate/state/stores/approval_store.py` | organism/ → make import from state/stores/ |
| TaskStore | `substrate/state/stores/task_store.py` | execution/bridge/ → extract embedded, import from state/stores/ |

---

## PART 3: THE 9-PHASE EXECUTION SEQUENCE

### Phase 1 — Freeze and Protect Production

**Goal:** Current DEX keeps working. Zero risk of breakage.

| # | Task | Risk | Verification |
|---|------|------|--------------|
| 1.1 | Fix docker-compose.yml os-webhook path: `interface/api/webhooks/` → `transports/api/webhooks/` | LOW | `docker compose config --services` |
| 1.2 | Remove os-monitor from compose (services/dm_monitor.py doesn't exist) | LOW | `docker compose config` |
| 1.3 | Fix systemd umh-mesh.service ExecStart: `services/umh/node_mesh/run.py` → `transports/node_mesh/run.py` | LOW | `systemctl cat umh-mesh` |
| 1.4 | Fix crontab orchestrator path: `control_plane/orchestrator/` → `substrate/control_plane/orchestrator/` | LOW | `crontab -l \| grep orchestrator` |
| 1.5 | Fix discord_bot.py L778,873: `runtime.agent_teams` → `substrate.control_plane.agents.agent_teams` | MEDIUM | `python3 -c "from substrate.control_plane.agents.agent_teams import ..."` |
| 1.6 | Kill 5 orphaned processes (PIDs in audit) | LOW | `ps aux \| grep -E "5175\|8092\|gws_auth\|electron\|test_provider"` |
| 1.7 | Snapshot current env/config: `cp services/.env data/snapshots/2026-05-25_env.bak` | LOW | File exists |
| 1.8 | Snapshot database schema: `pg_dump --schema-only > data/snapshots/2026-05-25_schema.sql` | LOW | File exists |
| 1.9 | Snapshot cron/systemd/docker configs to data/snapshots/ | LOW | Files exist |
| 1.10 | Add smoke test: Discord message → response round-trip verification | MEDIUM | Test passes |

### Phase 2 — Define Canonical Contracts

**Goal:** Lock the type contracts that every subsystem must speak.

All contracts already live in `substrate/types.py` (50+ Pydantic models). This phase audits completeness and adds missing contracts.

| # | Contract | Current Location | Status | Action |
|---|----------|-----------------|--------|--------|
| 2.1 | SignalEnvelope | substrate/sockets/envelopes.py | EXISTS | Verify all signal sources emit this |
| 2.2 | Intent | substrate/types.py | EXISTS | Verify cognitive_loop uses this |
| 2.3 | ExecutionContext | substrate/types.py | EXISTS | Verify spine consumes this |
| 2.4 | GovernanceVerdict | substrate/types.py | CHECK | May need to create unified verdict type |
| 2.5 | ExecutionEnvelope | substrate/types.py | CHECK | May need to unify with SignalEnvelope |
| 2.6 | ExecutionResult | substrate/types.py | EXISTS | Verify spine produces this |
| 2.7 | MemoryEntry | substrate/types.py | EXISTS | Deduplicate (3 defs → 1) |
| 2.8 | WorldModelUpdate | CHECK | May need to create | For reality_model updates |
| 2.9 | TraceRecord | substrate/execution/trace.py | EXISTS | Verify consistent usage |
| 2.10 | AdapterContract | substrate/sockets/protocols.py | EXISTS | Protocol definitions |
| 2.11 | ProjectionContract | CHECK | May need to create | For projection boundaries |
| 2.12 | NodeCapability | daemon/umh_node/ | EXISTS | Verify mesh protocol uses this |

### Phase 3 — One Runtime Spine

**Goal:** Discord becomes just another interface, not the brain.

**End-state flow:**
```
Interface → SignalEnvelope → Substrate → Governance
→ Planning/Composition → Execution Spine → Adapter/Node/Human Approval
→ Trace → Memory/Feedback/World Model → Response
```

| # | Task | Risk | Dependencies |
|---|------|------|-------------|
| 3.1 | Merge ExecutionPipeline logic into ConcreteExecutionSpine | MEDIUM | Phase 2 contracts |
| 3.2 | Delete 5 dead spines (Canonical, Live, FullIngestion, Orchestrator, legacy sync) | LOW | 3.1 |
| 3.3 | Update discord_bot.py to route through Substrate class → ConcreteExecutionSpine | HIGH | 3.1, Phase 1.5 |
| 3.4 | Make Gateway a thin adapter that creates SignalEnvelopes and delegates to Substrate | HIGH | 3.3 |
| 3.5 | Verify Discord bot still works end-to-end through new path | HIGH | 3.4 |

### Phase 4 — Collapse Governance

**Goal:** One layered governance engine, no bypass possible.

```
Structural Deny → Risk Classification → Permission Tier
→ Autonomy Level → Environment Policy → Approval Requirement → Audit Proof
```

| # | Task | Risk | Dependencies |
|---|------|------|-------------|
| 4.1 | Create GovernanceGateway interface in substrate/governance/ | MEDIUM | Phase 2.4 |
| 4.2 | Wire AuthorityEngine as permission/approval layer | MEDIUM | 4.1 |
| 4.3 | Wire ConcreteGovernanceEngine as risk classification layer | MEDIUM | 4.1 |
| 4.4 | Wire ExecutionAuthorityEngine as structural deny layer | MEDIUM | 4.1 |
| 4.5 | Replace all 3 direct engine calls with GovernanceGateway calls | HIGH | 4.2-4.4 |
| 4.6 | Verify no execution path bypasses governance | HIGH | 4.5 |

### Phase 5 — Reclassify All Dormant Systems

**Goal:** Every subsystem either serves the organism or archives cleanly.

| # | Subsystem | Classification | Action |
|---|-----------|---------------|--------|
| 5.1 | Constitutional engines (workers/workstation/) | ISOLATE → `nodes/workstation/` | Move. Future simulation/governance intelligence. |
| 5.2 | Organism agents (organism/) | PROMOTE | Already classified. Start daemon when ready. |
| 5.3 | Sensing adapters (adapters/sensing/) | DELETE | ABC with no implementations. No unique value. |
| 5.4 | Awareness adapters (adapters/awareness/) | DELETE | 0 imports. No unique value. |
| 5.5 | Cockpit (cockpit/) | ISOLATE → `interfaces/cockpit/` | Becomes operator interface. Deploy backend first. |
| 5.6 | SaaS (saas/) | ISOLATE | External projection shell. Future. |
| 5.7 | umh/ package | DELETE | 0 imports. 10,695 dead lines. |
| 5.8 | v1 runtime files (execution/runtime/) | DELETE (~32 files) | Update 50+ stale import paths first, then delete shims. |
| 5.9 | reality_model/ | ISOLATE → `substrate/simulation/` | Rename. Hypothesis testing. |
| 5.10 | world_pulse/ | ISOLATE | Market/creator monitoring. Future. |
| 5.11 | deliberation/council.py | ISOLATE | Council pattern. 1 import. |

### Phase 6 — Separate Substrate from Projections

**Goal:** Hard rule — substrate NEVER imports projections or product-specific logic.

| # | Task | Risk | Dependencies |
|---|------|------|-------------|
| 6.1 | Move substrate/integrations/eos/ → projections/eos/integration/ | MEDIUM | Phase 3 (spine unified first) |
| 6.2 | Move substrate/integrations/lyfeos/ → projections/lyfeos/integration/ | LOW | None |
| 6.3 | Move substrate/integrations/creatoros/ → projections/creatoros/integration/ | LOW | None |
| 6.4 | Move substrate/integrations/notion/ → adapters/notion/ (merge) | MEDIUM | Update imports |
| 6.5 | Move substrate/integrations/node_mesh/ → interfaces/node_mesh/ (merge) | MEDIUM | Update imports |
| 6.6 | Fix 20+ substrate → adapters dependency violations | HIGH | Create abstract ports in sockets/ |
| 6.7 | Verify: `grep -r "from projections\|from transports\|from services" substrate/` returns 0 | HIGH | 6.1-6.6 |

### Phase 7 — Cockpit as Command Center

**Goal:** Cockpit becomes the "Jarvis workstation" UI.

| # | Task | Dependencies |
|---|------|-------------|
| 7.1 | Deploy cockpit backend (transports/api/cockpit.py) — merge into os-operator or separate container | Phase 6 (interfaces/ rename) |
| 7.2 | Move cockpit/ → interfaces/cockpit/ | 7.1 |
| 7.3 | Connect cockpit stores to live WebSocket data from VPS | 7.1 |
| 7.4 | Verify 12 panels render with live data: agents, execution, approvals, memory, company, nodes, logs, voice | 7.3 |

### Phase 8 — Activate Node Mesh

**Goal:** VPS = brain, Beast = body, containers = sandboxes, browser = actuator.

| # | Task | Dependencies |
|---|------|-------------|
| 8.1 | Fix systemd mesh path (Phase 1.3) | Phase 1 |
| 8.2 | Move daemon/ → nodes/windows/ | Phase 5 |
| 8.3 | Move execution/environments/ → nodes/environments/ | Phase 5 |
| 8.4 | Move distribution/ → nodes/distribution/ | Phase 5 |
| 8.5 | Start Windows daemon on Beast, verify mesh connection | 8.2 |
| 8.6 | Route execution tasks through unified governance → node mesh | Phase 4 |

### Phase 9 — Three Persistent Loops

**Goal:** Post-convergence autonomous operation.

| Loop | Purpose | Components |
|------|---------|------------|
| **Business Ops** | Runs empire operations | Cron scripts, calendar, email, Notion, outreach |
| **UMH Self-Build** | Improves the system | Research engine, tool mastery, skill creation |
| **Research/World Model** | Learns frontier systems | reality_engine, research_engine, world_pulse |

---

## PART 4: IMMEDIATE DELETE LIST

Files/directories with objectively zero value. Safe to remove now.

| Target | Size | Lines | Evidence |
|--------|------|-------|----------|
| `umh/` | 488 KB | 10,695 | 0 external imports anywhere |
| `runtime/` | ~1 KB | 0 | Empty dir (0 Python files) |
| `frontend/` | 272 KB | ~100 | No source, only compiled dist/ |
| `apps/cockpit/` | 150 MB | 0 src | Ghost dir. node_modules only. |
| `media/` | 0 | 0 | Empty directory |
| `.claire/worktrees/` | ~5 KB | 158 | Stale from merged branch |
| `.planning/` | 60 KB | ~500 | Pre-convergence 2026-03-26. Dead refs. |
| `services/jarvis/` | ~1 KB | 0 | 12 empty subdirs. Ghost. |
| `substrate/deployment/` | ~5 KB | 239 | 0 imports. Placeholder. |
| `substrate/learning/` | ~1 KB | 1 | Empty placeholder. |
| `adapters/awareness/` | ~10 KB | 745 | 0 imports. Never connected. |
| `adapters/sensing/` | ~5 KB | 224 | 0 imports. No implementations. |
| Dead spines (5 files) | ~30 KB | ~3,000 | 0-1 refs each. See spine table. |
| RuntimeMemoryGovernanceBridge | ~5 KB | ~200 | 0 imports. |
| OrchestratorPipeline | ~5 KB | ~200 | 0 imports. |
| **TOTAL** | **~151 MB** | **~16,000** | |

**Pre-delete requirements:**
1. Fix pyproject.toml wheel target (`umh/` → `substrate/`) before deleting umh/
2. Move `runtime/.substrate_state.json` to `data/` before deleting runtime/
3. Move `services/umh/data/*.jsonl` to `data/watermarks/` before deleting services/umh/

---

## PART 5: STALE IMPORT PATH MIGRATION

**Must complete before deleting execution/runtime/ shims.**

50+ files import via stale path `substrate.execution.runtime.model_router`.
Canonical path: `adapters.models.model_router`.

6 files import via stale path `adapters.model_adapters.*`.
Canonical path: `adapters.models.*`.

This is a mechanical find-and-replace but must be verified with import checks after.

---

## PART 6: END-STATE DIRECTORY TREE

```
substrate/                    # Universal intelligence substrate (innermost)
├── __init__.py               # THE public API entry point
├── types.py                  # Single Pydantic type system (all contracts)
├── foundation/               # Laws, principles
├── ontology/                 # Primitives, domains, relationships
├── sockets/                  # Hexagonal ports
├── control_plane/            # Runtime, router, orchestrator, agents, goals, strategy
├── execution/                # Spine, bridge/, ingestion/, voice/, media/, agents/
├── governance/               # Unified GovernanceGateway + 3 engine implementations
├── memory/                   # Pipeline: candidate → promote → reconcile
├── state/                    # Persistence backbone (memory, stores, db)
├── understanding/            # Perception, knowledge, intelligence, ontology, embedding
├── composition/              # Tool Mastery Engine
├── organism/                 # Agent runtime, advisor, homeostasis
├── intelligence/             # Runtime intelligence
├── reality_model/            # Simulation, hypothesis testing
└── observability/            # Error recording, metrics

projections/                  # Scoped products built on UMH
├── eos/                      # EntrepreneurOS (+ integration/ from substrate/integrations/)
├── lyfeos/
└── creatoros/

interfaces/                   # How humans/systems access UMH (renamed from transports/)
├── discord/
├── api/                      # Operator API + cockpit backend + webhooks
├── cockpit/                  # Electron desktop (from cockpit/)
├── presence/
├── channels/
├── node_mesh/                # WebSocket mesh
└── voice/                    # (future)

nodes/                        # Distributed execution (renamed from daemon/)
├── windows/                  # umh_node, umh_desktop
├── workstation/              # Constitutional workers (from execution/workers/)
├── environments/             # (from execution/environments/)
├── containers/               # (future)
├── browser/                  # (future)
└── distribution/             # (from substrate/distribution/)

adapters/                     # External tools/services
├── models/                   # Intelligence routing (+ model_adapters/)
├── google/                   # GWS + calendar
├── notion/                   # (+ substrate/integrations/notion/)
├── browser/                  # (+ browser_exports/)
├── data_sources/             # Ingestion sources
├── adapter_engine/           # Lifecycle, capability catalog
├── tools/                    # Tool adapter contracts
├── higgsfield/
├── scrapling/
├── capabilities/             # Creative gen, goose, ui_tars
└── notebooklm/

services/                     # Thin deployment entrypoints
agents/                       # Soul docs (11 department agents)
skills/                       # Business + tool skills + packages
scripts/                      # Operator utilities + cron
tests/                        # Consolidated test suite
infra/                        # Docker, env, systemd, cron configs
docs/                         # Current canonical docs
knowledge/                    # Wiki, memory palace, concepts
data/                         # Runtime data, proofs, audits, snapshots
archive/                      # vault/, old backups, deprecated
```

---

## PART 7: AUDIT CORRECTIONS

The ground-truth audit incorrectly classified these as dormant:

| Subsystem | Audit Said | Reality | External Imports |
|-----------|-----------|---------|-----------------|
| understanding/intelligence/ | "DORMANT — 0 external imports" | **ACTIVE — 20+ imports** | cognitive_loop, gateway, calendly_webhook, intent_handler, agent_runtime, email_gps, discord_bot_commands, day_reminder, relationship_nurture, meetings |
| understanding/reality/ | "DORMANT" | **ACTIVE — 4 imports** | orchestrator.py (4 call sites) |
| understanding/research/ | "DORMANT" | **ACTIVE — 4 imports** | orchestrator.py (4 call sites) |
| understanding/deliberation/ | "DORMANT — 0 external imports" | **1 import** | execution/pipeline.py |

**Updated dead code total: ~48,100 lines** (was ~51,700 minus ~3,600 reclassified as active).

---

*This plan is grounded in the 100% ground-truth audit findings, verified
against actual filesystem imports. Every classification backed by evidence.
Ready for phase-by-phase execution on AFM's go.*
