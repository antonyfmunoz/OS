# C31 Ground Truth Audit

**Campaign:** C31 — Substrate Operational Convergence
**Date:** 2026-06-29
**Method:** Read-only. 5 parallel audit agents. No code changes.
**Scope:** All production services, substrate, adapters, transports, tests.

---

## 1. Git State

**Branch:** `main`
**Latest 10 commits:** All cockpit/canvas/terminal/EPISTEMOLOGY work. Zero production stability or substrate convergence commits in the recent window.

```
c181fb6f expand EPISTEMOLOGY.md with TRUTH MODE
a56f37c6 add EPISTEMOLOGY.md
55432c89 add full terminal capability layers
048f2e0c terminal adapter maturity: dynamic shell discovery
9500e30d unify terminal experience
f8e28d1a replace win32api display calls with ctypes
f08ff878 add rotate monitor button
24851bfa auto-resize desktop canvas window
003157b6 expand canvas zoom range
301c6675 add auto device sync hook
```

**Stale branches:** 8 remote worktree branches (c22, c29, cpu-throttle-fixes, fix-canvas-palette-toggle, fix-metaide-cleanup, fix-metaide-route, fix-right-rail-tabs, instant-render, remaining-phases).

---

## 2. Docker Service Health

| Container | Status | Uptime | Restarts | Log Rotation |
|-----------|--------|--------|----------|-------------|
| os-operator | Up (healthy) | 9 hours | 0 | json-file, 3x10MB |
| os-discord | Up | 9 days | **2** | json-file, 3x10MB |
| os-browser | Up | 2 days | 0 | json-file, 3x10MB |
| os-livekit | Up | 2 weeks | 0 | json-file, 3x10MB |
| os-webhook | Up | 2 weeks | 0 | json-file, 3x10MB |

**Findings:**
- os-discord: 2 restarts in 9 days (investigate — likely transient Discord API disconnects)
- os-operator: EventBus publishing `loop_cycle_research` and `loop_cycle_self_build` events with **no registered handlers** — events emitting into the void
- No crash loops, no OOM kills
- Log rotation properly configured on all containers

---

## 3. Test Suite Status

**14,396 tests collected.** Full suite times out (>5 min).

| Scope | Collected | Passed | Failed | Time |
|-------|-----------|--------|--------|------|
| tests/substrate/ | 70 | 70 | 0 | 0.39s |
| tests/adapters/ | 50 | 46 | 4 | — |
| substrate/organism/tests/ | 1,768 | 1,720 | 48 | 37s |
| Top-level tests/ | 14,276 | — | — | **TIMEOUT** |

### 48 Organism Test Failures

| Test File | Failures | Root Cause |
|-----------|----------|------------|
| test_workload_runner.py | 9 | Workload probes all returning False |
| test_autonomous_tick.py | 9 | Tick cycle not advancing |
| test_phase10_template_supply.py | 8 | Template count drift (11 vs 10), worktree paths |
| test_phase58_integration.py | 5 | Daemon tick produces 0 stages (expects >=5) |
| test_phase59_integration.py | 4 | Full tick cycle broken |
| test_phase14_1_source_inspection.py | 2 | Multi-tenant violations: "Jarvis" + "EntrepreneurOS" in substrate |
| test_runtime_supervisor.py | 2 | Heartbeat staleness not degrading |
| test_phase12_0_propagation_graph.py | 1 | Graph builder finds 1 workcell, expects >=5 |
| test_phase11_1_universal_work.py | 1 | 17 statuses vs expected 16 |
| test_orchestration_loop.py | 1 | 7 stages vs expected 6 |
| test_orchestration_integration.py | 1 | Daemon tick produces 0 reports |
| test_phase61_governed_spine.py | 1 | Workload envelope through spine fails |
| test_projection_reconciliation_engine.py | 1 | False positive: "sk-" in "task-shaped" |
| test_worker_cell.py | 1 | Worker execution without spine fails |
| test_assisted_executor.py | 1 | to_dict assertion failure |

### 4 Adapter Test Failures

All in `tests/adapters/broadcast/test_process_lifecycle.py` — process lifecycle timing assertions.

---

## 4. Dependency Direction Violations

**Official checker** (`scripts/check_dependency_direction.py --all`):
- Scanned: 1,270 files
- **17 violations** (down from 107 on 2026-05-27)
- All 17 are substrate->transports in test files only
- 4 files grandfathered in LEGACY_VIOLATIONS

### CRITICAL GAP: substrate->adapters NOT ENFORCED

The checker only blocks substrate->transports and substrate->services. There are **112 substrate->adapters violations** completely unguarded:

| Category | Count | Top Offenders |
|----------|-------|---------------|
| `from adapters.models.model_router` | ~25 | organism/, understanding/, governance/, control_plane/ |
| `from adapters.models.cc_sdk` | ~5 | organism/runtime_adapters.py, agent_execution_runner.py |
| `from adapters.notion.integration.auth` | ~5 | understanding/intelligence/person_recognition.py |
| `from adapters.scrapling` | ~4 | understanding/reality/, understanding/research/ |
| `from adapters.ssh` | 1 | organism/device_provisioner.py (top-level, not lazy) |
| `from adapters.models.agent_runtime` | 3 | understanding/intelligence/, contracts/ |
| `from adapters.google_workspace` | 2 | understanding/intelligence/ |
| Other adapter imports | ~67 | runtime_adapters.py, workstation/, integrations/ |

**substrate->transports (non-test): 0** — clean.
**substrate->services: 0** — clean.

---

## 5. Production Live Path

### Service Import Weight

| Service | Substrate Modules | Weight |
|---------|-------------------|--------|
| os-discord | ~70+ unique modules, ~15 bridge modules | **HEAVIEST** |
| os-operator | ~50 organism modules + 98 cockpit sub-routers | **HEAVY** |
| os-webhook | ~6 modules | Light |
| os-browser | 0 modules | Standalone |

### Core Hot Path (shared by discord + operator)

```
Gateway (1927 lines) -> CognitiveLoop (1539 lines) -> AgentRuntime -> model_router (1577+ lines)
```

### os-operator Runtime Chain

```
HTTP Request -> FastAPI (operator_api.py)
  +- /health -> direct response
  +- /advisor/converse, /dex/converse, /chat/converse ->
  |   ExecutionSpine -> model_router.call_with_fallback -> Claude/Gemini/CC SDK
  +- /ws -> WebSocket -> cockpit real-time events
  +- All /api/* -> 98 sub-router modules -> substrate.*
```

OrganismDaemon started at boot, imports **50 organism modules** directly.

### os-discord Runtime Chain

```
Discord Message -> on_message() -> handle_message()
  +- try_inline_commands() -> CLI commands
  +- handle_pipeline_update() -> CRM updates
  +- handle_substrate_command() -> substrate ops
  +- ingest_and_emit() -> event framing
  +- run_gateway() -> Gateway.handle() ->
      +- CognitiveLoop(ctx).run() ->
          +- ContextBuilder, KnowledgeLayerEngine, CanonicalMemoryStore
          +- LensEngine, ContextualReasoningEngine, KnowledgeIntegrator
          +- QualityTransformationGate -> governance
          +- AgentRuntime.execute() -> model_router.call_with_fallback()
```

### os-browser

Standalone Playwright-to-WebSocket bridge. **Zero substrate imports.**

### os-webhook

Light: memory.db, EventBus, person_recognition, calendar meetings, model_router.

### Adapter Production Usage

Only 4 adapter packages execute in production:
1. `adapters.models.model_router` — AI routing (all services except browser)
2. `adapters.models.cc_sdk` — Claude Code SDK
3. `adapters.google_workspace.*` — Gmail/GWS
4. `adapters.calendar.*` — meetings

CLI alternatives (codex_cli, hermes_cli, opencode_cli) loaded by model_router but at max backoff / dead runtimes.

---

## 6. Constitutional Engine Audit

**Location:** `substrate/execution/workers/workstation/`
**Total:** 42 files, 26,676 lines. `__init__.py` is empty.

### Classification Summary

| Classification | Files | Lines | % of Total |
|----------------|-------|-------|------------|
| SPECULATIVE | 19 | 4,866 | 18% |
| DORMANT (report-only) | 13 | 17,282 | 65% |
| ACTIVE | 9 | 3,477 | 13% |
| `__init__.py` | 1 | 0 | — |

**83% of workstation/ is speculative or report-only dead weight.**

### SPECULATIVE (19 files, 4,866 lines) — Zero external consumers

```
browser_continuity_bridge_v1.py (275)
browser_execution_orchestrator_v1.py (225)
browser_gui_contracts_v1.py (510)
browser_gui_embodiment_engine_v1.py (245)
browser_observability_pipeline_v1.py (153)
browser_operational_modes_v1.py (237)
browser_replay_validator_v1.py (259)
governed_browser_adapter_v1.py (450)
governed_shell_adapter_v1.py (381)
visible_gui_adapter_v1.py (282)
workstation_continuity_bridge_v1.py (306)
workstation_observability_pipeline_v1.py (134)
workstation_operational_embodiment_engine_v1.py (316)
workstation_operational_modes_v1.py (210)
workstation_relay_heartbeat_v1.py (158)
workstation_relay_node_v1.py (130)
workstation_relay_proof_v1.py (97)
workstation_replay_validator_v1.py (286)
workstation_state_registry_v1.py (212)
```

### DORMANT (13 files, 17,282 lines) — Only used by report generators

```
constitutional_antifragility_resilience_engine_v1.py (1,241)
constitutional_epistemic_intelligence_engine_v1.py (1,512)
constitutional_identity_continuity_engine_v1.py (1,494)
constitutional_resource_economics_engine_v1.py (1,262)
constitutional_strategic_intelligence_engine_v1.py (1,852)
constitutional_substrate_governance_layer_v1.py (1,559)
constitutional_telos_alignment_engine_v1.py (1,381)
distributed_constitutional_substrate_federation_v1.py (1,444)
adaptive_governance_intelligence_engine_v1.py (1,350)
governed_recursive_orchestration_engine_v1.py (1,464)
persistent_substrate_continuity_engine_v1.py (1,469)
adapter_autogeneration_engine_v1.py (992)
recursive_capability_planning_engine_v1.py (1,313)
```

### ACTIVE (9 files, 3,477 lines) — Used by live services

```
environment_mapping_engine_v1.py (1,124) — substrate/workstation/
tmux_operational_adapter_v1.py (266) — cockpit_core_session_routes.py
workstation_contracts_v1.py (485) — substrate/workstation/, transports/api/
workstation_execution_orchestrator_v1.py (189) — transports/api/workstation.py
visible_actuation_proof_v1.py (285) — substrate_command_handler
relay_execution_transport_v1.py (285) — substrate_command_handler
workstation_relay_self_heal_v1.py (160) — substrate_command_handler
foreground_cu_ingestion_execution_v1.py (575) — substrate_command_handler
workstation_node_registry_v1.py (108) — substrate_command_handler
```

---

## 7. execution/bridge/ Audit

**Total:** 70 module files + `__init__.py`, 27,307 lines.
`__init__.py` uses PEP 562 lazy imports — only 4 modules registered.

### Classification Summary

| Classification | Files | Lines |
|----------------|-------|-------|
| ACTIVE (external consumers) | 24 | 10,128 |
| DORMANT (internal only) | 45 | 16,593 |
| DELETE-CANDIDATE | 1 | 586 |

### P0 BUG: Unguarded Missing Import

`discord_bot_commands.py:156` imports `discord_output_policy` from bridge without try/except guard. **This file does not exist.** Will crash at runtime when that code path is hit.

7 other missing bridge modules are properly guarded with try/except:
`message_framing`, `event_store`, `interaction_archive`, `discord_ingress_adapter`, `run_lifecycle`, `task_finalization`, `operator_trace`.

### ACTIVE Bridge Modules (24 files, 10,128 lines)

Top by external reference count:

| File | Lines | Refs | Primary Consumers |
|------|-------|------|-------------------|
| session_discord_bridge.py | 459 | 6 | discord_bot, discord_bot_commands |
| claude_session_bridge.py | 1,185 | 5 | control_plane, transports/presence |
| wake_producer.py | 490 | 5 | organism (5 refs) |
| discord_text_transport.py | 1,653 | 2 | discord_bot, discord_message_handlers |
| voice_first.py | 434 | 7 | operator_api, discord_bot |
| voice_session.py | 789 | 7 | organism (7 refs) |
| storage.py | 213 | 7 | discord_bot, transports, substrate |
| station_daemon.py | 869 | 1 | discord_bot |
| event_spine.py | 206 | 2 | discord_bot |
| day_workflows.py | 570 | 1 | discord_bot |

### DELETE-CANDIDATE

`meeting_types.py` (586 lines) — zero references anywhere in the codebase.

---

## 8. Adapter Engine Wiring Status

**Verdict: Built but functionally disconnected from production.**

The `adapter_engine/` contains 16 Python files with a complete maturity system (L0-L7), lifecycle manager, capability catalog, and discovery.

**Current state:**
- `__init__.py` is **empty** — exports nothing
- **Zero adapters** outside adapter_engine/ import the manifest/maturity/lifecycle systems
- Only production touchpoint: `AdapterRegistry` from contracts file, used by 2 transports
- Google Drive adapter files live **inside** adapter_engine/ rather than in adapters/google_workspace/
- Batch scripts (reconciliation) use the scanner/decomposer but are not running services

**Systems built but unwired:**
- AdapterManifest — zero production callers
- AdapterMaturityLevel (L0-L7) — zero production callers
- MaturityEvidence — zero production callers
- AdapterLifecycleManager — zero production callers
- CapabilityDiscovery — zero production callers
- CapabilityCatalog — zero production callers

---

## 9. GovernedExecutionSpine Usage/Bypass Audit

**Verdict: Well-integrated into daemon, massive bypass surface.**

### Spine IS Wired (Positive)

- `substrate/organism/daemon.py:289` — instantiates GovernedExecutionSpine
- Daemon injects into workload_runner, assisted_executor, autonomous_action_gateway
- `transports/api/cockpit_spine_router.py` — full CRUD/approval cockpit API
- `transports/discord/spine_integration_v1.py:237` — calls spine.execute()
- `substrate/control_plane/router/__init__.py:89` — calls spine.execute()

### Spine Bypass (Critical)

**Only 2 production callers** of `spine.execute()`:
1. `transports/discord/spine_integration_v1.py`
2. `substrate/control_plane/router/__init__.py`

**75 subprocess calls** in substrate bypass the spine entirely:

| Count | File | Bypass Type |
|-------|------|-------------|
| 16 | execution/bridge/station_daemon.py | Direct shell commands |
| 6 | execution/cpu_gate.py | System resource checks |
| 5 | organism/shell_runtime_adapter.py | Direct shell execution |
| 4 | organism/executors/agent_executor.py | Agent spawning |
| 4 | execution/workers/workstation/workstation_state_registry_v1.py | Direct subprocess |
| 4 | execution/runtime/node_sync_gate_v1.py | Node sync |
| 3 | organism/autonomous_pr_factory.py | Git/PR operations |
| 3 | organism/production_merge_verifier.py | Git verification |

**149+ file write patterns** in substrate bypass the spine (open with 'w'):

| Count | File | Bypass Type |
|-------|------|-------------|
| 8 | organism/device_registry_writer.py | Device state |
| 5 | organism/strategic_gap_engine.py | Gap analysis output |
| 5 | organism/projection_engine.py | Projection state |
| 4 | organism/continuity_runtime.py | Continuity state |
| 3 | organism/execution_coordinator.py | Execution state |
| 3 | organism/approval_store.py | Approval records |

**Conclusion:** The spine is a governance gateway that most of the system walks around.

---

## 10. Silent Exception Priority List

**Total: 605 silent except:pass blocks** (previously estimated at 267 — actual count is 2.3x higher).

### Tier 1: Boot / DB / Governance / Execution / Adapters — 118 blocks

| Count | File | Risk |
|-------|------|------|
| 9 | substrate/control_plane/orchestrator/orchestrator.py | HIGH — core routing |
| 6 | adapters/models/cc_sdk.py | HIGH — Claude Code SDK |
| 6 | adapters/calendar/meetings.py | MEDIUM |
| 6 | substrate/__init__.py | HIGH — boot path |
| 5 | substrate/execution/bridge/session_discord_bridge.py | HIGH — live transport |
| 4 | substrate/execution/pipeline.py | HIGH — execution pipeline |
| 4 | substrate/control_plane/scheduling/daily_sync.py | MEDIUM |
| 3 | substrate/execution/bridge/claude_session_bridge.py | HIGH — CC bridge |

### Tier 2: Organism Runtime / Bridge / WebSocket — 107 blocks

| Count | File | Risk |
|-------|------|------|
| 11 | substrate/organism/learning_portfolio_runtime.py | MEDIUM |
| 10 | substrate/organism/advisor_conversation.py | MEDIUM |
| 6 | substrate/organism/operator_loop_runtime.py | MEDIUM |
| 3 | substrate/organism/workload_runner.py | HIGH — executes workloads |

### Tier 3: Scripts / Old Services / Dormant / Transports — 380 blocks

| Count | File | Risk |
|-------|------|------|
| 25 | transports/api/cockpit_core_routes.py | HIGH — cockpit API |
| 19 | scripts/c29_thesis_runner.py | LOW — one-off |
| 13 | services/browser_relay.py | MEDIUM — running service |
| 11 | transports/api/cockpit_operator_loop_routes.py | MEDIUM |

---

## 11. P0 Blockers

| # | Blocker | Severity | Evidence |
|---|---------|----------|----------|
| 1 | **Unguarded missing import** — `discord_bot_commands.py:156` imports `discord_output_policy` without try/except. File does not exist. Will crash at runtime. | P0 | Section 7 |
| 2 | **605 silent except:pass** — 2.3x the estimated 267. Boot path (`substrate/__init__.py`, 6 blocks) and core routing (`orchestrator.py`, 9 blocks) silently swallow errors. | P0 | Section 10 |
| 3 | **112 unguarded substrate->adapters violations** — dependency checker does not enforce this boundary. substrate/ imports directly from adapters/ 112 times. | P1 | Section 4 |
| 4 | **os-discord 2 restarts** — unexplained restarts in 9 days. | P1 | Section 2 |
| 5 | **Unhandled EventBus events** — `loop_cycle_research` and `loop_cycle_self_build` publish with zero handlers. Wasted daemon cycles. | P2 | Section 2 |
| 6 | **48 organism test failures** — workload runner, autonomous tick, daemon tick all broken in tests. | P2 | Section 3 |
| 7 | **Full test suite timeout** — 14,276 top-level tests cannot complete in 5 min. Likely hanging tests. | P2 | Section 3 |
| 8 | **Multi-tenant violations** — "Jarvis" and "EntrepreneurOS" found in substrate (test_phase14_1 failures). | P2 | Section 3 |

---

## 12. Recommended Phase 2 Execution Order

Based on ground truth, the CTO-approved tiered approach, and entropy reduction priority:

### Step 1: Fix P0 — Unguarded Missing Import (1 hour)
- Fix `discord_bot_commands.py:156` — add try/except guard or create the missing `discord_output_policy` module
- This is a runtime crash waiting to happen

### Step 2: Freeze Speculative Architecture (1 session)
- Move 19 SPECULATIVE workstation files (4,866 lines) to `substrate/execution/workers/workstation/_dormant/`
- Move 13 DORMANT constitutional engines (17,282 lines) to same dormant directory
- Delete `meeting_types.py` (586 lines, zero refs)
- Net: 22,734 lines of dead weight quarantined, 33 files out of the import path
- **Do NOT delete** — freeze. Ideas may be harvested later.

### Step 3: Silent Exceptions — Tier 1 Only (1 session)
- Fix 118 blocks in boot/db/governance/execution/adapter paths
- Priority order: `substrate/__init__.py` (6), `orchestrator.py` (9), `cc_sdk.py` (6), `session_discord_bridge.py` (5), `execution/pipeline.py` (4)
- At minimum: replace `except: pass` with `except Exception: logger.debug("...", exc_info=True)`
- Do NOT touch Tier 2/3 yet

### Step 4: Dependency Boundary Enforcement (1 session)
- Add substrate->adapters to `check_dependency_direction.py`
- Triage the 112 violations: which can be converted to lazy imports, which need an adapter interface in contracts/
- `model_router` is the hardest — 25 imports from substrate. May need a `contracts/model_protocol.py` interface.

### Step 5: Test Suite Stabilization (1 session)
- Fix the 48 organism failures (most are integration tests with drifted expectations)
- Add pytest timeout markers to prevent full-suite hangs
- Fix multi-tenant violations ("Jarvis", "EntrepreneurOS" in substrate)

### Step 6: Wire Adapter Engine (1 session)
- Populate `adapter_engine/__init__.py` with real exports
- Wire AdapterRegistry into operator_api.py startup
- Create manifests for the 4 production adapters (model_router, cc_sdk, google_workspace, calendar)

### Step 7: Bridge Consolidation (1 session)
- Delete `meeting_types.py`
- Classify 45 dormant bridge modules: KEEP (voice subsystem, perception) vs FREEZE
- Ensure all missing-module imports are properly guarded

---

## CTO Recommendation

**PROCEED.**

The system is operationally stable (no crash loops, no OOM, healthy Docker). The problems are structural, not existential:
- Dead code ratio is high but quarantinable
- Silent exceptions are dangerous but tiered fix is tractable
- Dependency boundary has a gap but the substrate->transports/services boundaries are clean
- The spine exists and is wired — it just needs to be made mandatory
- The adapter engine exists and is complete — it just needs to be connected

The wartime order holds: stabilize live path first, freeze speculative code, then consolidate. No new architecture until the existing architecture is proven alive.

**Estimated Phase 2 effort:** 5-7 focused sessions across Steps 1-7 above.
