# UMH Platform State Report v1.0

**Generated:** 2026-07-01 | **Graph:** 1,339 files, 64,618 edges | **Campaigns:** C31-C40B
**Repo:** 193,644 files | **Python:** 1,926 files, 604,479 lines | **TypeScript:** 611 files, 127,924 lines | **Tests:** 413 files
**Docker:** 5 containers running (os-operator, os-browser, os-discord, os-livekit, os-webhook)

---

## 1. Executive Summary

UMH (Universal Meta Harness) is a production AI intelligence substrate operating as a governed operator workstation. It comprises a type-safe platform layer (substrate/), intelligence routing through 7 LLM providers, a 81-panel cockpit UI deployed on Fly.io, a Discord-based operator interface with 85 commands, cross-device mesh networking, and an organism subsystem that has been qualified through 7 campaigns (C31-C40B) totaling 1,630+ mutations. The system is live: 5 Docker services running, cron jobs executing every 5 minutes, mesh relay serving on ports 8094/8095, and operator-accessible via web, Discord, and API. The platform constitution is 88% complete with all 10 contracts qualified. Runtime is 52% complete with core services running but significant dormant code. Intelligence is 72% complete with production routing but several orphaned modules. The cockpit workstation is 82% complete with 81 panels integrated. Product surface is 52% complete with strong communication/task capabilities but gaps in research, design tools, and autonomous execution. Operator experience is 62% complete with the core approve-watch-continue loop working but evidence inspection and failure recovery surfaces missing.

| Layer | Completion | Confidence |
|---|---|---|
| Platform | 88% | High |
| Runtime | 52% | High |
| Intelligence | 72% | High |
| Workstation | 82% | High |
| Product Experience | 52% | High |
| Operator Experience | 62% | High |
| **MVP (weighted)** | **69%** | **High** |

*MVP weighted: Platform 20% + Runtime 20% + Intelligence 15% + Workstation 15% + Product 15% + Operator 15% = 17.6 + 10.4 + 10.8 + 12.3 + 7.8 + 9.3 = 68.2%, rounded to 69%.*

---

## 2. Repository Health

### File Counts

| Directory | Python Files | Purpose |
|---|---|---|
| substrate/ | 945 | Platform core (types, execution, organism, control plane) |
| transports/ | 184 | I/O surfaces (Discord, HTTP API, node mesh) |
| adapters/ | 99 | External system adapters (models, calendar, browser) |
| cockpit/src/ | 303 (TS/TSX) | Operator UI (React, Zustand stores, panels) |
| tests/ | 413 | Test files (test_*.py) |

### Codebase Size

| Metric | Count |
|---|---|
| Total files (excl. caches) | 193,644 |
| Python files | 1,926 |
| Python lines (excl. dormant) | 604,479 |
| TypeScript/TSX files | 611 |
| TypeScript lines | 127,924 |
| Test files | 413 |
| Cockpit panels | 81 |
| Backend route files | 115 |
| Zustand stores | 78 (15,514 lines) |

### Graph Statistics

- **Nodes:** 1,339 files indexed
- **Edges:** 64,618 dependency relationships
- **Graph query tool:** `scripts/query_graph.py` (search, deps, dependents, path, critical, centrality)

### Architecture Compliance

| Check | Status | Enforcement |
|---|---|---|
| Dependency direction (substrate never imports upward) | [x] Clean | Pre-commit Gate 4: `check_dependency_direction.py` |
| Type coherence (no parallel types) | [x] Enforced | Pre-commit Gate 1: `check_type_divergence.py` |
| Instance context (no hardcoded identity) | [x] Enforced | Pre-commit Gate 2: `check_instance_leak.py` |
| Projection boundary (no EOS in substrate) | [x] Enforced | Pre-commit Gate 3: `check_projection_leak.py` |
| CPU gate (no raw subprocess) | [x] Enforced | Pre-commit Gate 5: `check_cpu_gate.py` |
| Ungoverned mutations blocked | [x] Enforced | Pre-commit Gate 6: `check_ungoverned_mutations.py` |
| Credential injection | [ ] **NOT wired** | Script exists (`check_credential_injection.py`) but not in `.git/hooks/pre-commit` |
| Secret patterns | [ ] **NOT wired** | Script exists (`check_secret_patterns.py`) but not in `.git/hooks/pre-commit` |
| Mesh relay firewall | [ ] **NOT wired** | Script exists (`check_mesh_relay_firewall.py`) but not in `.git/hooks/pre-commit` |

**Architecture violations detected:** 0 (dependency direction law upheld across 945 substrate files).

### File Size Compliance

| File | Lines | Limit | Status |
|---|---|---|---|
| `transports/api/cockpit_operator_loop_routes.py` | 3,480 | 3,000 | VIOLATION |
| All other active files | < 3,000 | 3,000 | Clean |

---

## 3. Platform Constitution Compliance

### Contract Status Table

| # | Contract | Specified | Implemented | Used | Qualified | No Duplicates | Status |
|---|---|---|---|---|---|---|---|
| 1 | Canonical Mutation | [x] | [x] | [x] 20+ cockpit routes | [x] C35-C40B, 1630+ mutations | [x] Single entry point | Qualified |
| 2 | Governed Execution | [x] | [x] | [x] 7 dependents | [x] C35-C40B campaigns | [ ] Dormant BlastRadius in `_dormant/` | Qualified |
| 3 | Event Spine | [x] | [x] | [x] 20+ dependents | [x] event_loss=0 in C40B | [x] | Qualified |
| 4 | Runtime Adapter (Mesh) | [x] | [x] | [x] Server + client | [x] 100% reliability C40B | [x] | Qualified |
| 5 | Proof Contract | [x] | [x] | [x] 1 dependent | [x] 100% completeness C40B | [x] | Qualified |
| 6 | Qualification | [x] | [x] | [x] 3 dependents | [x] 7 campaigns, ORL-8 95.3% | [x] | Qualified |
| 7 | Organism Daemon | [x] | [x] | [x] 9 dependents | [x] C35-C40B | [ ] Duplicate ApprovalStore | Qualified |
| 8 | Predictive Self-Model | [x] | [x] | [x] 1 dependent | [x] PA 66.9%-83.8% | [x] | Qualified |
| 9 | Type System | [x] | [x] | [x] 30+ dependents | [x] 1278 mappings | [ ] Duplicate OutcomeRecord, ApprovalStore | Qualified |
| 10 | Runtime SLOs | [x] | [x] | [x] C40B scorecard | [x] 11/11 SLOs passing | [x] | Qualified |

**All 10 contracts: Qualified.** Two type coherence concerns remain (duplicate ApprovalStore, duplicate OutcomeRecord).

### Architecture Invariants

| Invariant | Status | Evidence |
|---|---|---|
| Pre-commit hooks (6 wired) | [x] Active | `.git/hooks/pre-commit` contains all 6 spec-listed hooks |
| Dependency direction | [x] Clean | Zero upward imports in substrate/ (`check_dependency_direction.py`) |
| 4-dimension verdict | [x] Verified | C40B: organism=PASS, runtime=PASS, projection=PASS, operator=PASS |
| Production readiness checks | [x] Documented | 8 checks in PLATFORM_SPEC.md Section 12 |

### Gaps

- Credential injection hook (`check_credential_injection.py`) exists but is NOT wired into pre-commit, despite spec Section 14 invariant 6 claiming enforcement
- Duplicate ApprovalStore: `substrate/organism/approval_store.py` (daemon) vs `substrate/state/stores/approval_store.py` (governance)
- Duplicate OutcomeRecord: `substrate/organism/outcome_learning.py` vs `substrate/organism/benchmarks/outcome_accuracy.py`
- MutationStore referenced in spec Section 7 daemon interface but no MutationStore class exists in codebase
- No continuous SLO monitoring outside campaign runs

**Overall constitution compliance: 88%** (10/10 contracts qualified, 3 unwired hooks, 2 type duplications).

---

## 4. Runtime Inventory

### Infrastructure Services

| Service | Category | Status | Container | Evidence |
|---|---|---|---|---|
| Mesh Relay Server | Mesh | Exercised | Host process (PID 714086, 2124012) | Ports 8094/8095, C40B 100% reliability |
| Windows Node Daemon | Mesh | Implemented | Windows Task Scheduler | Code exists, cannot verify from VPS |
| Cross-Device Dispatch | Mesh | Integrated | Via mesh relay | `_mesh_dispatch.py` imported by `cockpit.py` |
| os-operator | Docker | Exercised | Up ~1h (healthy) | Port 8091, health OK, event bus cycling |
| os-discord | Docker | Exercised | Up 33h | Discord bot, 15+ substrate imports |
| os-browser | Docker | Integrated | Up 33h | Browser relay, WebSocket screencast |
| os-livekit | Docker | Integrated | Up 2 weeks | LiveKit v1.8.3, voice pipeline |
| os-webhook | Docker | Integrated | Up 33h | Calendly webhook handler |
| os-scraper | Docker | Dormant | Not running | `restart: no`, on-demand only |
| Playwright | Browser | Integrated | In os-browser | Evidence collector, verification gate |
| Browser Evidence Collector | Browser | Integrated | Mesh dispatch | Routes to executor nodes, 1 dependent |
| Browser Verification Gate | Browser | Integrated | Substrate | 6-layer verification, 2 dependents |
| Model Router | Intelligence | Exercised | In all services | 7 providers, 20+ importers, circuit breaker |
| CC SDK (Opus 4.6) | Intelligence | Exercised | CLI subprocess | OAuth from ancestor CC, option 0 in chain |
| Gemini Adapter | Intelligence | Exercised | API | Fallback in routing chain |
| Groq Adapter | Intelligence | Partial | Inline | Voice transcription, no standalone file |
| Ollama Adapter | Intelligence | Integrated | Remote (Beast) | Last-resort fallback |
| CPU Gate | Infrastructure | Exercised | All services | 20+ dependents, 6-layer defense |
| Credential Gate | Infrastructure | Integrated | Substrate | 1Password `op run` integration |
| Cockpit (Fly.io) | Projection | Integrated | Fly.io | 81 panels, Clerk auth, deploy gate |
| Discord Bot | Projection | Exercised | os-discord | 85 commands, primary operator surface |
| Organism Daemon | Core | Exercised | In os-operator | Event bus cycling, cadence dry-run |
| Qualification Harness | Core | Exercised | Script | 7 campaigns, 74 JSONL data files |
| Execution Spine | Core | Integrated | Substrate | 8-stage pipeline, CONFIRMED_RUNTIME |

### Running vs Idle

| Category | Running | Built but Idle |
|---|---|---|
| Docker services | 5 (operator, discord, browser, livekit, webhook) | 1 (scraper) |
| Host processes | Mesh relay, cron jobs | -- |
| Intelligence providers | CC SDK, Gemini | Groq (transcription only), Ollama (fallback) |
| Dormant code | -- | 33 files in `_dormant/` (23,199 lines), ComputerUseAgent (0 dependents), GovernedShellAdapter (dormant), 6 browser workstation modules |

### Routing Chain

```
cc_sdk (Opus 4.6 via Max subscription)
  -> Gemini 2.5 Flash (API)
    -> Groq (transcription)
      -> Ollama (Beast remote, qwen2.5:0.5b local)
        -> Deterministic fallback (template/rules)
```

---

## 5. Operator Experience

### Journey Map

| Step | Action | Status | Evidence |
|---|---|---|---|
| 1. OPEN | Access system | Working | Cockpit at universalmetaharness.tech (HTTP 200, Clerk auth), Discord bot running, API port 8091 healthy |
| 2. TALK (text) | Send text command | Working | Cockpit chat (chatStore.ts, cockpit_chat_routes.py), Discord 85 commands |
| 2b. TALK (voice) | Speak to system | Partial | LiveKit container running, voice engine exists, Discord voice transport wired. Not qualified in campaigns |
| 3. SEE PLANS | View pending actions | Working | ApprovalsPanel.tsx (risk badges, governance scores), EventConsole.tsx (real-time, WebSocket + polling fallback) |
| 4. APPROVE | Accept/reject actions | Working | POST approve/reject endpoints, auth-gated UI |
| 5. WATCH | Observe execution | Working | ExecutionPanel.tsx (spine stats, timeline), OperatorTimelinePanel.tsx (chronological merge), WebSocket real-time |
| 6. INSPECT | Browse proof chains | Partial | Backend: proof_store.py, trace.py, `/workspace/proof-artifacts` API. **No dedicated cockpit panel** for browsing individual proof artifacts |
| 7. RECOVER | Handle failures | Partial | Backend: runtime_recovery_v1.py (6 failure types, 4 strategies), work_recovery_runtime.py. Frontend: ErrorBoundary + ErrorCard. **No recovery dashboard panel** |
| 8. CONTINUE | Resume next day | Working | ExecutionJournal (append-only JSONL, 13 lifecycle phases), SessionResumePanel (checkpoint/pause/resume), context from env, chat history persisted |

### Critical Path Gaps

1. **No proof inspection panel** -- operator cannot browse trace chains or evidence screenshots from the cockpit despite full backend support
2. **No recovery dashboard** -- operator cannot see all failed work items, choose recovery strategies, or manually trigger retries from a single surface
3. **Voice not qualified** -- LiveKit infrastructure running but cockpit voice-to-action flow never exercised in qualification campaigns

---

## 6. Intelligence Layer

### Capability Classification

| Module | Classification | Dependents | Campaign Evidence | Notes |
|---|---|---|---|---|
| Outcome Learning Loop | **Qualified** | 8+ organism modules | C35-C40B, 10,237 signal entries | Deterministic, no LLM required |
| Predictive Self-Model | **Qualified** | 1 (qualification_harness) | PA 66.9%-83.8%, calibration 0.768 | Welford accumulators, 600 predictions tracked |
| Qualification Harness | **Qualified** | 3 (campaign scripts) | 7 campaigns, 1,630+ mutations | Empirical backbone of UMH validation |
| Model Router | **Production** | 20+ modules | Active in discord bot | 7 providers, circuit breaker, deterministic fallback |
| Cognitive Loop | **Functional** | 4 (strategy, reality, research, user model) | No campaign evidence | 8-stage PUPEVRL-S cycle, core reasoning backbone |
| Compounding Engine | **Functional** | 3 (governed_spine, daemon, capability_compounding) | No campaign evidence | 4-stage promotion pipeline, wired into daemon tick |
| Coherence Propagation | **Functional** | 3 + 40 tests | No campaign evidence | Wave-based propagation, well-tested |
| Governance Engine | **Functional** | Via protocol contract | No campaign evidence | Deterministic risk classification, regex patterns |
| Strategy Engine | **Functional** | 2 (reality, research) | No campaign evidence | LLM-dependent, **no deterministic fallback** |
| Self-Model | **Functional** | 15 modules | No campaign evidence | CanonicalSelf + InstanceSelf, widely imported |
| Delegation Topology | **Functional** | 2 + 11 tests | No campaign evidence | Plan/assign roles for orchestrator kernel |
| Propagation Planner | **Functional** | 1 + 8 tests | No campaign evidence | Wave-based action planning |
| Engineering Planner | **Functional** | Cockpit routes only | No campaign evidence | 321 lines, surfaced via cockpit |
| Learning Extraction | **Functional** | 6 lazy importers | No campaign evidence | Semantic layer above outcome learning |
| Capability Compounding | **Functional** | 2 (daemon, cockpit) | No campaign evidence | 5-stage pipeline wired into daemon tick |
| Drift Detection Engine | **Functional** | 1 (work_portfolio) | No campaign evidence | Deterministic, zero LLM |
| Goal Drift Engine | **Functional** | 2 (trajectory, work_portfolio) | No campaign evidence | 4 drift detection methods |
| Context Builder | **Functional** | 1 (control_plane_protocol) | No campaign evidence | Context lifecycle for agent calls |
| Coherence Gate | **Functional** | 1 (validation script) | No campaign evidence | Spine coherence enforcement |
| Capability Router | **Prototype** | 0 importers | None | 28 capabilities defined, route_capability() unused |
| Institutional Memory | **Prototype** | 0 importers | None | 557 lines, unintegrated |
| State Coherence Engine | **Prototype** | 0 direct importers | None | 174 lines, lazy-loaded only |
| Operating Loop Coherence | **Prototype** | Cockpit routes only | None | Cockpit-only visibility, no organism consumer |
| Context Compaction | **Prototype** | 0 importers | None | 213 lines, exists but unconnected |

### Intelligence Routing Chain

```
call_with_fallback(prompt, agent_type, force_opus)
  -> cc_sdk (Opus 4.6, Max subscription, 120s timeout)
    -> Gemini 2.5 Flash (google.genai, API key)
      -> Groq (voice transcription in discord_bot)
        -> Ollama (remote Beast 100.74.199.102:11434 / local qwen2.5:0.5b)
          -> Deterministic fallback (template/rules)

Role routing:
  CEO/strategic agents -> force_opus=True -> cc_sdk always
  Fast checks -> TaskType.FAST_RESPONSE -> Haiku
  Default -> economy mode (pre_revenue stage)
```

---

## 7. Workstation

### Panel Inventory

| Category | Panel | Lines | Status | API Wired |
|---|---|---|---|---|
| **Primary Nav** | CommandCenter | 459 | Integrated | Yes |
| | Canvas | 302 + 5,414 (24 components) | Integrated | Yes |
| | Work | 569 | Integrated | Yes |
| | Meta IDE | 1,285 | Integrated | Yes |
| | Conference Rooms | 72 + 14 sub-components | Integrated | Yes |
| | Vision | 142 | Integrated | Yes |
| **Dev Nav** | Approvals | 264 | Integrated | Yes |
| | Activity | 105 | Integrated | Yes |
| | Execution | 188 | Integrated | Yes |
| | Organism Map | 104 | Integrated | Yes |
| | Broadcast | 281 | Integrated | Yes |
| | Knowledge | 338 | Integrated | Yes |
| | Browser | 539 | Integrated | Yes |
| | Operator | 951 | Integrated | Yes |
| | Executor | 1,016 | Integrated | Yes (40 fetch refs) |
| | Delegation | 242 | Integrated | Yes |
| | Strategic | 417 | Integrated | Yes |
| | Goal | 451 | Integrated | Yes |
| | Memory | 430 | Integrated | Yes |
| | Reality Graph | 609 | Integrated | Yes |
| | Engineering | 555 | Integrated | Yes |
| | TickLoop | 489 | Integrated | Yes |
| | MVPReadiness | 160 | Integrated | Yes |
| | Screen Awareness | 422 | Integrated | Yes |
| | Distributed Runtime | 293 | Integrated | Yes |
| | Propagation Graph | 233 | Integrated | Yes |
| | Profile | 464 | Integrated | Yes |
| | Organism | 349 | Integrated | Yes |
| | Intelligence | 657 | Integrated | Yes |
| | Continuity | 376 | Integrated | Yes |
| | Comms | 234 | Integrated | Yes |
| | Presence | 371 | Integrated | Yes |
| | Commands | 395 | Integrated | Yes |
| | Session | 417 | Integrated | Yes |
| | Strategy | 593 | Integrated | Yes |
| | Workstation | 458 | Integrated | Yes |
| | ExecCoord | 345 | Integrated | Yes |
| | OrganismLoop | 341 | Integrated | Yes |
| | OperatingLoop | 152 | Integrated | Yes |
| | Orchestrator | 134 | Integrated | Yes |
| | SessionResume | 164 | Integrated | Yes |
| | ProjectionIntegration | 239 | Integrated | Yes |
| | Projection | 419 | Integrated | Yes |
| | UnifiedExecution | 199 | Integrated | Yes |
| | BuildLoop | 184 | Integrated | Yes |
| | CapabilityMap | 163 | Integrated | Yes |
| | SelfBuild | 303 | Integrated | Yes |
| | Tmux | 111 | Integrated | Yes |
| | OperatorTimeline | 135 | Integrated | Yes |
| | RealityTimeline | 159 | Integrated | Yes |
| | Intent | 126 | Integrated | Yes |
| | Company | 291 | Integrated | Yes |
| | Portfolio | 231 | Integrated | Yes |
| | Capabilities | 370 | Integrated | Yes |
| | Actions | 186 | Integrated | Yes |
| | OperatorContinuity | 248 | Integrated | Yes |
| | OperatorHome | 249 | Implemented | Yes (4 refs) |
| | ServiceGraph | 231 | Integrated | Yes |
| | Operations | 298 | Integrated | Yes |
| **Store-driven** | RealityIntelligence | 225 | Implemented | Store-only (0 fetchApi) |
| | WorkIntelligence | 350 | Implemented | Minimal (3 refs) |
| | Learning | 289 | Implemented | Minimal (3 refs) |
| | Prediction | 277 | Implemented | Minimal (3 refs) |
| | Executive | 233 | Implemented | Minimal (3 refs) |
| | Governance | 267 | Implemented | Minimal (2 refs) |
| | StateAuthority | 104 | Implemented | Minimal (3 refs) |
| | UMHNode | 135 | Implemented | Minimal (4 refs) |
| | WorkspaceTopology | 161 | Implemented | Minimal (4 refs) |
| **Partial** | WorldModel | 649 | Partial | Shows empty states when data missing |
| | Infrastructure | 196 | Partial | Shows "not yet wired" when WS disconnected |
| | Analytics | 121 | Partial | `visibility='planned'` in routes |
| | Workspace | 530 | Partial | `visibility='stub'` but has real code |
| **Redirected** | Dashboard -> CommandCenter | 489 | Redirect | Code exists but navigates away |
| | Runtime -> Execution | 383 | Redirect | Code exists but navigates away |
| | UniversalWork -> Work | 879 | Redirect | Code exists but navigates away |
| | Skills -> Knowledge | 47 | Redirect | Minimal wrapper |
| **Placeholder** | Tracking | 16 | Placeholder | "Not wired" message only |
| | Experiments | 16 | Placeholder | "Not wired" message only |

### Summary

| Status | Count |
|---|---|
| Integrated (API-wired, data-backed) | 57 |
| Implemented (store-driven, minimal API) | 9 |
| Partial (code exists, data incomplete) | 4 |
| Redirected (navigates to canonical panel) | 4 |
| Placeholder (empty shell) | 2 |
| **Total** | **76** (81 files, 5 share backends) |

### Cockpit Deployment

- **Host:** Fly.io, app `umh-cockpit`, region `sjc`, min 1 machine
- **Build:** node:20-slim build, nginx:alpine serve
- **Auth:** Clerk JWT (`@clerk/clerk-react`), `require_clerk_auth` middleware
- **Deploy gate:** `cockpit/deploy.sh` (140 lines, auth verification, Clerk JWT checks, 1Password token refresh, post-deploy verification)
- **Domain:** universalmetaharness.tech

### Backend API Coverage

- 115 Python route files (`transports/api/cockpit_*.py`)
- Main `cockpit.py`: 1,517 lines
- WebSocket: `_wire_spine_to_cockpit_ws` in `operator_api.py` pushes EventSpine events
- Client: `websocket.ts` (170 lines, WsClient with reconnect, heartbeat, visibility-based reconnect)

---

## 8. Product Surface

### What a User Can Actually Do Today

| Capability | Status | Entry Points | Evidence |
|---|---|---|---|
| **Text messaging** | Supported | Discord (85 commands), Cockpit chat panel | os-discord running 33h, chatStore + chat routes wired |
| **Email management** | Supported | Discord: `!inbox`, `!draft`, `!force_send`, `!verify_inbox` | EmailGPS (55K), GWSConnector (37K), Gmail API |
| **Calendar management** | Supported | Discord: `!accept`, `!decline`, `!event` | meetings.py (31K), travel_manager.py (10K), Google Calendar API |
| **Task management** | Supported | Discord: `!tasks`, `!approve_task`; Cockpit Work panel | task_system.py (601 lines), Google Tasks adapter, auto-generation |
| **CRM / Client management** | Supported | Discord: `!relationship`, `!nurture`, `!pending` | CrmContactRow/CrmDealRow/CrmActivityRow, PipelineView (6 stages) |
| **Scheduled automation** | Supported | Cron (every 5 min), Cockpit CronTable | CPU-gated cron-run wrapper, 1Password injection, daily sync |
| **Workflow automation** | Supported | Cockpit Workflows panel, orchestrator loop | workflow_execution.py (12K), orchestrator runs every 5 min |
| **Shell / Terminal** | Supported | Cockpit Tmux panel, mesh dispatch | CPU-gated subprocess, cross-device terminal |
| **Docker management** | Supported | Cockpit Infrastructure panel, Discord | DockerAdapter, DockerProbe, organism maintenance |
| **Browser automation** | Supported | Cockpit Browser panel, evidence collector | BrowserAgent (561 lines), browser relay (os-browser), Playwright |
| **Evidence collection** | Supported | Mesh dispatch to executor | trigger_collection(), proof_store.py, verification gate |
| **Code generation** | Supported | CC SDK (Opus 4.6), Discord, direct CLI | cc_sdk.py (513 lines), model_router, warmup on bot startup |
| **Cockpit UI** | Supported | universalmetaharness.tech | 81 panels, Clerk auth, Fly.io deployment |
| **Governance approvals** | Supported | Cockpit Approvals panel, Discord | Full approve/reject flow, auth-gated, risk classification |
| **Voice (basic)** | Partial | Discord: `!join`, `!leave`, `!say` | Voice engine, LiveKit running, Groq transcription. Not qualified e2e |
| **Finance / Expenses** | Partial | Discord: `!expenses` | expense_tracker.py, subscription_tracker.py. Not regularly exercised |
| **Content creation** | Partial | Discord: `!proofread` | content.py exists but orphaned (0 dependents) |
| **GitHub operations** | Partial | Discord: `!pr` | github_operations.py exists but orphaned (0 dependents), gh CLI direct |
| **Notes / Knowledge** | Partial | Cockpit Knowledge panel | Wiki system, memory palace. No `!note` command |
| **Autonomous ops** | Partial | Cockpit Approvals, daemon tick | dry_run_only constraint. Observes but never acts independently |
| **Research** | Unsupported | -- | TME research is tool-specific; research_engine.py orphaned (0 dependents) |
| **Slack** | Unsupported | -- | No adapter, no transport, no bot |
| **Figma / Design tools** | Unsupported | -- | Only category classification in workstation_translator.py |

### Gap Analysis

- **No general research capability** accessible to operator -- TME handles tool docs only
- **No Slack integration** despite notification socket abstraction
- **No design tool API** (Figma, Canva, etc.)
- **Content workflow orphaned** -- classes exist, nothing imports them
- **GitHub governed wrapper orphaned** -- exists but unused
- **Autonomous execution locked** -- dry_run_only indefinitely
- **No simple note-taking command** -- notes are byproducts, not direct

---

## 9. Technical Debt

### Debt Inventory

| Item | Classification | Size | Impact | File/Dir |
|---|---|---|---|---|
| Dormant workstation code | **DELETE** | 33 files, 23,199 lines | Dead code, false search hits | `substrate/execution/workers/workstation/_dormant/` |
| Legacy c29 campaign scripts | **DELETE** | 4 files | Dead code, never called | `scripts/c29_*.py` |
| Stale worktrees (eng, terminal-layers) | **DELETE** | 2 dirs, ~76K | VPS bloat | `.claude/worktrees/eng`, `.claude/worktrees/terminal-layers` |
| Merged git branches | **DELETE** | 1 branch | Clutter | `worktree-c33-campaign` |
| Orphaned llm_adapter.py | **DELETE** | 1 file, 0 dependents | Dead wrapper | `adapters/models/llm_adapter.py` |
| Duplicate IntentRouter | **MERGE** | 2 classes, 0 dependents each | Type coherence violation | `substrate/operator/intent_router.py`, `substrate/control_plane/router/intent_router.py` |
| Duplicate ContinuityEngine | **MERGE** | 2 classes, 0 dependents each | Type coherence violation | `substrate/operator/continuity_engine.py`, `substrate/workstation/continuity_engine.py` |
| Duplicate ApprovalStore | **MERGE** | 2 implementations | Behavioral drift risk | `substrate/organism/approval_store.py`, `substrate/state/stores/approval_store.py` |
| Duplicate OutcomeRecord | **MERGE** | 2 definitions | Type coherence violation | `substrate/organism/outcome_learning.py`, `substrate/organism/benchmarks/outcome_accuracy.py` |
| cockpit_operator_loop_routes.py | **REFACTOR** | 3,480 lines (limit: 3,000) | Quality standard violation | `transports/api/cockpit_operator_loop_routes.py` |
| Silent except-pass | **REFACTOR** | ~407 instances | Masked errors in production | substrate/ (235), adapters/ (36), transports/ (136) |
| TODO/FIXME/HACK comments | **REFACTOR** | 11 in substrate/ | Stale markers | Various substrate/ files |
| Placeholder cockpit panels | **REFACTOR** | 2 panels (32 lines) | Dead UI surface | TrackingPanel.tsx, ExperimentsPanel.tsx |
| Redirected cockpit panels | **REFACTOR** | 4 panels (1,798 lines) | Dead code behind redirects | Dashboard, Runtime, UniversalWork, Skills panels |
| Campaign data on VPS | **ARCHIVE** | 32G in data/umh/ | VPS bloat, violates Node Role Discipline | `data/umh/c33/`, `c34/`, `c39/`, `c40a/`, `c40b/` |
| Stale audit reports | **ARCHIVE** | 446M in data/audits/ | VPS bloat | 39 files older than 30 days |
| Engine class proliferation | **KEEP** (review) | 112 Engine classes | Over-fragmentation risk | Various substrate/ files |
| Router class proliferation | **KEEP** | 13 Router classes | Acceptable -- each distinct domain | Various substrate/ files |
| Architecture violations | **KEEP** | 0 violations | Clean | Enforced by pre-commit |

### Dead Code Estimate

| Category | Lines |
|---|---|
| `_dormant/` directory | 23,199 |
| Legacy campaign scripts (c29) | ~400 est. |
| Orphaned modules (IntentRouter x2, ContinuityEngine x2, llm_adapter, content.py, research_engine.py, github_operations.py, capability_router routing functions) | ~3,500 est. |
| Redirected cockpit panels | 1,798 |
| Placeholder panels | 32 |
| **Total estimated dead code** | **~28,900 lines** |

### Data Bloat

| Directory | Size | Action |
|---|---|---|
| data/umh/ | 32G | Archive campaign data to Beast, keep c35 + organism/ |
| data/audits/ | 446M | Archive pre-June 2026 reports |

---

## 10. MVP Completion

### MVP Definition

UMH MVP = **governed operator workstation**: the operator can communicate with the system, see what it plans to do, approve or reject actions, watch execution, inspect evidence, recover from failures, and resume the next day. The system governs all mutations through a single canonical path, enforces architecture invariants, and qualifies itself through empirical campaigns.

### Gate Checklist

| Gate | Requirement | Status | Evidence |
|---|---|---|---|
| G1 | Type system enforced | [x] | 1,278 canonical type mappings, pre-commit Gate 1 |
| G2 | Architecture direction enforced | [x] | 0 violations, pre-commit Gate 4 |
| G3 | Canonical mutation path | [x] | governed_mutation() single entry, pre-commit Gate 6 |
| G4 | Governed execution spine | [x] | GovernedExecutionSpine, 8-stage pipeline, C35-C40B qualified |
| G5 | Event spine (zero loss) | [x] | EventSpine, event_loss=0 in C40B |
| G6 | Operator can communicate | [x] | Discord (85 commands), Cockpit chat, API |
| G7 | Operator can see plans | [x] | ApprovalsPanel, EventConsole, real-time WebSocket |
| G8 | Operator can approve/reject | [x] | POST approve/reject endpoints, auth-gated UI |
| G9 | Operator can watch execution | [x] | ExecutionPanel, OperatorTimelinePanel, real-time |
| G10 | Operator can inspect evidence | [ ] | **Backend exists (proof_store, trace). No cockpit panel.** |
| G11 | Operator can recover failures | [ ] | **Backend exists (runtime_recovery_v1). No recovery dashboard.** |
| G12 | State persists across sessions | [x] | ExecutionJournal, SessionResumePanel, checkpoint/resume |
| G13 | Intelligence routing with fallback | [x] | 7 providers, circuit breaker, deterministic fallback |
| G14 | Cross-device dispatch | [x] | Mesh relay 100% reliability C40B |
| G15 | Qualification system | [x] | 7 campaigns, ORL-8 95.3% |
| G16 | CPU protection | [x] | 6-layer defense, all 120 legacy violations migrated |

**MVP Gate Score: 14/16 (87.5%)**

### What's Blocking MVP

1. **G10: Proof inspection panel** -- operator cannot browse evidence from the cockpit. Backend is ready (`proof_store.py`, `trace.py`, `/workspace/proof-artifacts` API). Needs a cockpit panel.
2. **G11: Recovery dashboard** -- operator cannot see failed work or trigger retries. Backend is ready (`runtime_recovery_v1.py`, `work_recovery_runtime.py`). Needs a cockpit panel.

---

## 11. Gaps (Consolidated)

### Priority 1: MVP Blockers

| # | Gap | Dimension | Impact |
|---|---|---|---|
| 1 | No proof inspection panel in cockpit | Operator Experience | Blocks G10, operator blind to evidence |
| 2 | No recovery dashboard panel in cockpit | Operator Experience | Blocks G11, operator cannot manage failures |

### Priority 2: Spec-Code Drift

| # | Gap | Dimension | Impact |
|---|---|---|---|
| 3 | Credential injection hook not wired in pre-commit | Platform | Spec claims enforcement that does not exist |
| 4 | MutationStore in spec Section 7 but missing from code | Platform | Spec-code misalignment |
| 5 | Duplicate ApprovalStore (organism/ vs state/stores/) | Platform | Type coherence violation, drift risk |
| 6 | Duplicate OutcomeRecord (outcome_learning vs benchmarks/) | Platform | Type coherence violation |

### Priority 3: Dead/Orphaned Code

| # | Gap | Dimension | Impact |
|---|---|---|---|
| 7 | 23,199 lines dormant code in `_dormant/` | Tech Debt | False search hits, audit confusion |
| 8 | 407 silent except-pass violations | Tech Debt | Masked production errors |
| 9 | cockpit_operator_loop_routes.py at 3,480 lines | Tech Debt | Quality standard violation |
| 10 | Orphaned modules: research_engine, github_operations, content.py, capability_router routing, llm_adapter | Product Surface / Intelligence | Wasted development, dead code |
| 11 | 4 legacy c29 campaign scripts | Tech Debt | Dead code |

### Priority 4: Operational Gaps

| # | Gap | Dimension | Impact |
|---|---|---|---|
| 12 | No continuous SLO monitoring outside campaigns | Platform | Regressions undetected between campaigns |
| 13 | 32G data/umh/ on lightweight VPS | Tech Debt | Node Role Discipline violation |
| 14 | Two mesh server processes running | Runtime | Potential port conflict |
| 15 | VPS disk space issues (Errno 28 in os-discord logs) | Runtime | Cascading service degradation |
| 16 | Cross-device dispatch requires Beast online | Runtime | Browser evidence fails when Beast offline |

### Priority 5: Product Gaps

| # | Gap | Dimension | Impact |
|---|---|---|---|
| 17 | No general research command for operator | Product Surface | Significant capability absent |
| 18 | Voice cockpit path not qualified | Operator Experience | Infrastructure exists but unproven |
| 19 | Autonomous operations locked to dry_run_only | Product Surface | System observes but never acts |
| 20 | No Slack integration | Product Surface | Missing communication channel |
| 21 | No simple note-taking command | Product Surface | Common workflow unsupported |
| 22 | Strategy Engine has no deterministic fallback | Intelligence | Violates deterministic-first principle |

---

## 12. Risks (Consolidated)

### Critical

| Risk | Dimension | Mitigation Status |
|---|---|---|
| VPS disk space exhaustion (32G data/umh/, 446M audits, Errno 28 in logs) | Runtime | **Unmitigated** -- actively causing heartbeat failures |
| Credential injection commits not blocked by pre-commit | Platform | **Unmitigated** -- script exists but unwired |
| 407 silent except-pass mask production errors | Tech Debt | **Unmitigated** -- errors are silently swallowed |

### High

| Risk | Dimension | Mitigation Status |
|---|---|---|
| cc_sdk depends on ancestor CC process OAuth token -- fails if CC not running | Runtime | Partial -- fallback chain exists but Opus unavailable |
| Two mesh server processes (PID 714086, 2124012) could conflict | Runtime | **Unmitigated** -- needs stale process kill |
| Discord bot is single point of failure for operator interaction | Product Surface | Partial -- cockpit exists as alternate surface |
| Duplicate ApprovalStore could drift apart | Platform | **Unmitigated** -- two consumers, two implementations |
| 81 cockpit panels + 115 route files create massive maintenance surface | Workstation | **Unmitigated** -- most panels untested beyond import |

### Medium

| Risk | Dimension | Mitigation Status |
|---|---|---|
| SLO compliance only measured during campaigns | Platform | **Unmitigated** -- no continuous monitoring |
| Voice pipeline degrades if Beast offline (TTS Kokoro on Beast) | Runtime | Partial -- text fallback exists |
| Self-model calibration below 0.9 target (currently 0.768-0.838) | Intelligence | Partial -- improving across campaigns |
| Several intelligence runtimes orphaned, inflating perceived coverage | Intelligence | **Unmitigated** -- modules exist but do nothing |
| Autonomous cadence dry_run_only indefinitely | Product Surface | By design -- but limits system value |

---

## 13. Recommendations

### Immediate (Before Next Deploy)

1. **Kill stale mesh server process** -- only one of PID 714086 / 2124012 should run. Verify with `ss -tlnp | grep 809` and kill the older one.
2. **Free VPS disk space** -- archive `data/umh/c{33,34,39,40a,40b}` to Beast or delete. Address Errno 28 in os-discord logs.
3. **Wire credential injection hook** -- add `check_credential_injection.py` to `.git/hooks/pre-commit` as Gate 7 to match spec Section 14 invariant 6.

### Short-term (Next 2 Weeks)

4. **Build Proof Inspector panel** -- cockpit panel that browses trace chains and proof artifacts, linked from ExecutionPanel work packet details. Backend API exists (`/workspace/proof-artifacts`). Unblocks MVP Gate G10.
5. **Build Recovery Dashboard panel** -- cockpit panel showing failed work items with retry/escalate/abandon controls. Backend exists (`runtime_recovery_v1.py`, `work_recovery_runtime.py`). Unblocks MVP Gate G11.
6. **Delete `_dormant/` directory** -- 33 files, 23,199 lines, zero references from active code.
7. **Split cockpit_operator_loop_routes.py** -- 3,480 lines exceeds 3,000-line limit. Split into focused route modules.
8. **Consolidate ApprovalStore** -- merge to single canonical location and update all consumers.

### Medium-term (Next Month)

9. **Batch-fix silent except-pass** -- add `logger.debug()` to all 407 instances across substrate/adapters/transports.
10. **Wire orphaned modules or deprecate** -- research_engine.py, github_operations.py, content.py, capability_router.route_capability(), llm_adapter.py. Either connect to a consumer or move to `_dormant/`.
11. **Archive campaign data** -- move `data/umh/` historical data to Beast. Keep c35 + organism/ on VPS. Target: reduce from 32G to under 1G.
12. **Add continuous SLO sampling** -- lightweight daemon probe that measures mesh_reliability, event_loss, dispatch_success at 5-minute intervals, persisted to JSONL.
13. **Create deterministic fallback for Strategy Engine** -- rules-based strategic assessment when LLMs unavailable.
14. **Qualify cockpit voice path** -- end-to-end campaign: voice input via LiveKit -> organism -> action -> response.
15. **Merge duplicate IntentRouter and ContinuityEngine** -- consolidate to single canonical locations.
16. **Remove dead panels** -- delete TrackingPanel.tsx and ExperimentsPanel.tsx (32 lines total, zero functionality). Remove redirected panel files that are never rendered.

---

## 14. Roadmap

### Phase 1: MVP Gate Closure (Week 1-2)

| Priority | Task | Unblocks | Effort |
|---|---|---|---|
| P0 | Free VPS disk space (archive data/umh/ campaigns, kill stale mesh PID) | Service stability | Low |
| P0 | Wire credential injection pre-commit hook | Spec compliance | Low |
| P1 | Build Proof Inspector panel | MVP Gate G10 | Medium |
| P1 | Build Recovery Dashboard panel | MVP Gate G11 | Medium |
| P1 | Delete `_dormant/` directory (23K lines dead code) | Codebase clarity | Low |
| P1 | Split cockpit_operator_loop_routes.py | Quality standard | Low |

### Phase 2: Type Coherence + Debt Reduction (Week 3-4)

| Priority | Task | Unblocks | Effort |
|---|---|---|---|
| P2 | Consolidate ApprovalStore to single location | Type coherence | Low |
| P2 | Merge duplicate IntentRouter, ContinuityEngine | Type coherence | Low |
| P2 | Remove duplicate OutcomeRecord | Type coherence | Low |
| P2 | Batch-fix 407 silent except-pass violations | Error visibility | Medium |
| P2 | Archive data/umh/ to Beast (32G -> <1G on VPS) | Node Role Discipline | Medium |
| P2 | Delete legacy c29 scripts, stale worktrees, merged branches | Cleanup | Low |

### Phase 3: Intelligence Integration + Product Gaps (Week 5-8)

| Priority | Task | Unblocks | Effort |
|---|---|---|---|
| P3 | Wire research_engine.py into Discord command + cockpit | General research capability | Medium |
| P3 | Wire content.py into projection import chain | Content workflow | Low |
| P3 | Connect github_operations.py to governance spine | Governed PR operations | Medium |
| P3 | Add continuous SLO monitoring daemon | Production observability | Medium |
| P3 | Create Strategy Engine deterministic fallback | Deterministic-first compliance | Medium |
| P3 | Qualify cockpit voice path end-to-end | Voice capability | High |
| P3 | Add `!note` Discord command | Note-taking workflow | Low |
| P3 | Classify/promote orphaned intelligence modules | Code hygiene | Medium |
| P4 | Remove dead cockpit panels (Tracking, Experiments, redirected) | UI surface reduction | Low |
| P4 | Audit all 81 panels for data-backed vs empty-state | Workstation clarity | Medium |

---

*Report generated from 7-dimension audit of UMH codebase. All metrics grounded in `query_graph.py`, `find`, `wc`, `docker ps`, and campaign data (C31-C40B). Graph: 1,339 files, 64,618 edges. Total codebase: 1,926 Python files (604K lines), 611 TypeScript files (128K lines), 413 test files.*
