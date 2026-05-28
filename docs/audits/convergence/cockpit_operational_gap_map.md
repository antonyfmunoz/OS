# Cockpit Operational Gap Map

Generated: 2026-05-27
Phase: 4A — Cockpit Operationalization Without Redesign

## Frontend Panel Inventory

| # | Panel | Status | API Endpoints Used | Polling | Notes |
|---|-------|--------|-------------------|---------|-------|
| 1 | Dashboard | LIVE | /pulse, /mesh/nodes, /models, /tasks, /infra, /approvals | 3-10s | Real system telemetry |
| 2 | Agents | LIVE | /agents, /organism/agents, /organism/deliverables, /organism/control | 5s | deliverables+control stubbed |
| 3 | Tasks | LIVE | /tasks, /workflows, /workflows/{id}/trigger | 5s | tasks=interactions facade |
| 4 | Workflows | LIVE | /workflows, /workflows/{id}/trigger | 5s | trigger is stub |
| 5 | Activity | LIVE | /activity/stream + WebSocket | 3s+RT | Real events table |
| 6 | Approvals | LIVE | /approvals, /approvals/{id}/approve, /approvals/{id}/deny | 5s | DB approvals, not organism |
| 7 | Execution | LIVE | /execution/status, /log, /authority, /start, /stop, /pause, /resume | 3s | ALL stubbed |
| 8 | Knowledge | LIVE | /observations, /memory, /skills, /tracking | 10s | observations+memory+tracking stubbed |
| 9 | Analytics | LIVE | /analytics | 15s | Real model usage from DB |
| 10 | Editor | LIVE | Electron IPC (readDir/readFile/writeFile) | none | Local filesystem only |
| 11 | Settings | LIVE | /settings, /governance | 30s | Hardcoded static config |
| 12 | Portfolio | LIVE | /entities/departments, /entities/roles, /products | once | No polling |
| 13 | Company | LIVE | /entities/companies, /entities/departments, /entities/roles, /entities/workflows | once | No polling |
| 14 | Infrastructure | LIVE | /infra, /mesh/nodes | 10s | Real Docker+Tailscale |
| 15 | Comms | SKELETON | none | none | Empty placeholder |
| 16 | Tracking | SKELETON | none | none | Empty placeholder |
| 17 | Skills | SKELETON | none | none | Data exists in knowledgeStore |
| 18 | Experiments | SKELETON | none | none | Empty placeholder |
| 19 | Profile | SKELETON | none | none | Empty placeholder |

## Backend Endpoint Status

### Real (DB or system telemetry)
- GET /pulse — os metrics + Docker count
- GET /mesh/nodes — Tailscale network
- GET /models — static list + Ollama ping
- GET /infra — Docker containers + Neon + Tailscale
- GET /ventures, GET /ventures/:id, PATCH /ventures/:id
- GET /skills, GET /skills/:id, PATCH /skills/:id
- GET /interactions, GET /interactions/stats
- POST /outcomes, GET /outcomes/skill-performance
- GET /approvals, GET /approvals/pending, POST /approvals/:id/approve, POST /approvals/:id/reject
- GET /events, POST /events/publish
- GET /agents
- GET /workflows
- GET /activity/stream
- GET /tasks (interactions facade)
- GET /analytics (model usage aggregates)
- GET /eos/kpis, GET /eos/pipeline
- POST /agent/run, POST /agent/team, POST /agent/brief (Python bridge)
- POST /dex/converse (Python bridge)

### Fully Stubbed (no implementation)
- POST /agents/:id/signal → `{ ok: true }`
- GET /organism/deliverables → `[]`
- POST /organism/control → `{ ok: true }`
- POST /organism/handoff → `{ ok: true }`
- POST /organism/parallel → `{ ok: true }`
- GET /organism/delegations → `{ followups: [] }`
- POST /workflows/:id/trigger → `{ ok: true }`
- GET /execution/status → hardcoded 4 idle slots
- GET /execution/log → `{ slot, log: [] }`
- GET /execution/authority → hardcoded operator/LOW
- POST /execution/start|stop|pause|resume → `{ ok: true }`
- GET /observations → `[]`
- GET /memory → `[]`
- GET /tracking → `[]`
- GET|PATCH /settings → hardcoded config
- GET|PATCH /governance → hardcoded 4 policies
- GET /eos/accountability → all zeros
- GET /eos/intelligence → empty objects
- GET /dex/history → `[]`

## Organism Runtime Available (Python, not yet exposed)

| Organism Module | Queryable State | Actions | Cockpit Target |
|----------------|----------------|---------|---------------|
| OrganismDaemon | .status(), is_running | .start(), .tick(), .stop() | Dashboard, Execution |
| OrganismCoordinator | .list_objectives(), .get_objective(), .status() | .decompose(), .execute_objective() | Dashboard, Tasks |
| RuntimeGraph | .to_dict(), .all_nodes(), .select() | .register(), .update_status(), .refresh_availability() | Infrastructure, Execution |
| RuntimeSupervisor | .to_dict(), .check_all(), .get_recovery_plan() | .supervise(), .heartbeat(), .reconcile_graph() | Infrastructure |
| Workcell | .to_dict(), .is_alive(), .read_heartbeat() | .send_message(), .process_next(), .shutdown() | Execution |
| WorkcellDaemon | .to_dict(), .stats | .register_workcell(), .run(), .stop() | Execution |
| ExecutionEconomy | .economy_summary(), .recent_records(), .get_profile() | .record_execution() | Analytics, Execution |
| RecursionGovernor | .to_dict(), .state, .limits, .escalation_log() | .kill(), .resume(), .reset_state() | Settings, Approvals |
| AdvisorHierarchy | .hierarchy_tree(), .to_dict(), .overdue_reports() | .register_primary(), .spawn(), .terminate(), .suspend() | Agents |
| ApprovalStore | .list_approvals(), .pending_count() | .create_approval(), .decide() | Approvals |
| HomeostasisEngine | .check(), .current_mode, .override_history() | .record_override(), .record_override_outcome() | Dashboard |
| OrganismObserver | .snapshot(), .history(), .trend() | (read-only) | Dashboard |
| OrganismStore | .list_deliverables(), .list_learning_signals() | .save_deliverable() | Agents, Knowledge |
| HandoffRouter | .stats(), .pending_for() | .submit(), .resolve() | Agents |
| LeverageAssimilator | .list_artifacts(), .to_dict() | .full_pipeline() | Knowledge |
| ExecutionEconomy | .task_execution_profile(), .best_runtime_for_task() | — | Analytics |

## Gap Map: UI Surface → Wiring Path

| UI Surface | Current Source | Real Source Available? | Wiring Path | Priority |
|-----------|---------------|----------------------|-------------|----------|
| Dashboard: system health mode | hardcoded | HomeostasisEngine.check() | bridge → /organism/health | P0 |
| Dashboard: pending approvals count | DB approvals table | ApprovalStore.pending_count() | bridge → /organism/approvals | P0 |
| Dashboard: active objectives | none | Coordinator.list_objectives() | bridge → /organism/objectives | P0 |
| Agents: deliverables | stub `[]` | OrganismStore.list_deliverables() | bridge → /organism/deliverables | P0 |
| Agents: agent control | stub `{ ok }` | Advisor.handle_signal() | bridge → /organism/control | P0 |
| Execution: status slots | hardcoded idle | WorkcellDaemon.to_dict() | bridge → /organism/execution/status | P0 |
| Execution: authority | hardcoded LOW | RecursionGovernor.to_dict() | bridge → /organism/execution/authority | P0 |
| Execution: start/stop/pause/resume | stubs | RecursionGovernor.kill/resume | bridge → /organism/execution/control | P0 |
| Knowledge: observations | stub `[]` | OrganismStore or ontology | bridge → /organism/observations | P1 |
| Knowledge: memory | stub `[]` | OrganismStore | bridge → /organism/memory | P1 |
| Settings: governance policies | hardcoded | RecursionGovernor.limits | bridge → /organism/governance | P1 |
| Settings: model routing | hardcoded | RuntimeGraph.to_dict() | bridge → /organism/runtimes | P1 |
| Infrastructure: runtime topology | none | RuntimeGraph + Supervisor | bridge → /organism/topology | P1 |
| Analytics: execution economy | none | ExecutionEconomy.economy_summary() | bridge → /organism/economy | P1 |
| Agents: advisor hierarchy | none | AdvisorHierarchy.hierarchy_tree() | bridge → /organism/advisors | P1 |
| Agents: handoff stats | none | HandoffRouter.stats() | bridge → /organism/handoffs | P2 |
| Dashboard: bottlenecks | none | OrganismObserver.snapshot().bottlenecks | bridge → /organism/snapshot | P2 |
| Knowledge: leverage artifacts | none | LeverageAssimilator.list_artifacts() | bridge → /organism/leverage | P2 |

## Dead Code / Redundancy

| Item | Location | Issue |
|------|----------|-------|
| NavRail | components/NavRail.tsx | Orphaned — Shell uses LeftRail |
| ChatDrawer | components/ChatDrawer.tsx | Orphaned — RightRail has ChatSection |
| SkillsPanel | panels/SkillsPanel.tsx | Empty despite knowledgeStore having skills data |
| AnalyticsStore EOS methods | stores/analyticsStore.ts | fetchKPIs/Pipeline/etc exist but panel never calls them |
| /organism/agents | saas/api/routes/organism.ts | Duplicate of /agents endpoint |

## Architecture Decision

The wiring path for all organism state: extend `saas/bridge/agent_bridge.py` with
`organism.*` actions that instantiate an OrganismDaemon (or individual modules)
and return their state as JSON. The TypeScript routes call `callBridge()` with
the appropriate action. No new infrastructure needed — the pattern already works.
