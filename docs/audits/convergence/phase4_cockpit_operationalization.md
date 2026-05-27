# Phase 4: Cockpit Operationalization Report

**Date**: 2026-05-27
**Status**: COMPLETE
**Branch**: anti-divergence-gate (worktree)

---

## Summary

Phase 4 wired the existing UMH Cockpit into the real organism runtime,
making it the operational command surface. No UI redesign. No style
changes. Pure operational wiring.

---

## What Became Operational

### New Infrastructure
- **`saas/bridge/organism_bridge.py`** — 33-action Python bridge exposing
  all organism subsystem state and governed actions via stdin/stdout JSON
- **`callOrganism()`** helper in `python_bridge.ts` — TypeScript counterpart
  for calling the organism bridge from API routes

### Endpoints Wired (previously stubbed → now real)

| Endpoint | Was | Now |
|----------|-----|-----|
| GET /organism/snapshot | — | Full OrganismObserver snapshot |
| GET /organism/status | — | OrganismDaemon.status() |
| GET /organism/health | — | HomeostasisEngine 8-dimension check |
| GET /organism/agents | stub | Real agent status from Advisor |
| GET /organism/deliverables | `[]` | OrganismStore.list_deliverables() |
| GET /organism/learning | — | OrganismStore.list_learning_signals() |
| GET /organism/objectives | — | Coordinator.list_objectives() |
| GET /organism/objectives/:id | — | Coordinator.get_objective() |
| GET /organism/economy | — | ExecutionEconomy.economy_summary() |
| GET /organism/economy/records | — | ExecutionEconomy.recent_records() |
| GET /organism/runtimes | — | RuntimeGraph.to_dict() |
| GET /organism/supervisor | — | RuntimeSupervisor.to_dict() |
| GET /organism/governor | — | RecursionGovernor.to_dict() |
| GET /organism/governor/escalations | — | RecursionGovernor.escalation_log() |
| GET /organism/advisors | — | AdvisorHierarchy.to_dict() |
| GET /organism/advisors/tree | — | AdvisorHierarchy.hierarchy_tree() |
| GET /organism/approvals | — | ApprovalStore.list_approvals() |
| GET /organism/approvals/count | — | ApprovalStore.pending_count() |
| GET /organism/handoffs | `{followups:[]}` | HandoffRouter.stats() |
| GET /organism/leverage | — | LeverageAssimilator.to_dict() |
| GET /organism/workcells | — | WorkcellDaemon.to_dict() |
| POST /organism/approve/:id | stub | ApprovalStore.decide(approved) |
| POST /organism/deny/:id | stub | ApprovalStore.decide(denied) |
| POST /organism/kill | stub | RecursionGovernor.kill() |
| POST /organism/resume | stub | RecursionGovernor.resume() |
| POST /organism/governor/reset | — | RecursionGovernor.reset_state() |
| POST /organism/refresh | — | RuntimeGraph.refresh_availability() |
| POST /organism/control | stub | Routes to kill/resume by action |
| GET /execution/status | hardcoded 4 idle | Workcells + Governor + Snapshot |
| GET /execution/log | `[]` | ExecutionEconomy.recent_records() |
| GET /execution/authority | hardcoded LOW | RecursionGovernor state |
| POST /execution/start | stub | RecursionGovernor.resume() |
| POST /execution/stop | stub | RecursionGovernor.kill() |
| POST /execution/pause | stub | RecursionGovernor.kill() |
| POST /execution/resume | stub | RecursionGovernor.resume() |
| GET /observations | `[]` | Snapshot-derived observations |
| GET /memory | `[]` | OrganismStore learning signals |
| GET /tracking | `[]` | ExecutionEconomy metrics |
| GET /settings | hardcoded | RuntimeGraph + Governor state |
| GET /governance | hardcoded | RecursionGovernor policies + state |
| GET /eos/accountability | zeros | ExecutionEconomy summary |
| GET /eos/intelligence | `{}` | Homeostasis + Governor combined |
| GET /pulse (enhanced) | 0 pending | Real organism pending tasks/approvals/mode |

### System Visibility (new endpoints)
| Endpoint | Source |
|----------|--------|
| GET /sessions | tmux list-sessions |
| GET /docker | docker ps -a |
| GET /workspaces | Filesystem scan of .claude/worktrees/ |
| GET /files?path= | Directory listing (safe-root gated) |
| GET /file?path= | File read (safe-root gated, 512KB limit) |

### Governed Controls Added
- **Kill switch**: POST /organism/kill — halts all autonomous execution
- **Resume**: POST /organism/resume — re-enables autonomous execution
- **Governor reset**: POST /organism/governor/reset — resets all counters
- **Approve/Deny**: POST /organism/approve/:id and /deny/:id
- **Runtime refresh**: POST /organism/refresh — reprobes all runtimes

All write operations flow through the organism bridge which enforces
governance checks at the substrate level.

### Frontend Cleanup
- **SkillsPanel** — wired to knowledgeStore.fetchSkills() with 10s polling
- **CommsPanel** — labeled "Not wired — Pending transport integration"
- **TrackingPanel** — labeled "Not wired — See Knowledge panel"
- **ExperimentsPanel** — labeled "Not wired — Pending experiment framework"
- **ProfilePanel** — labeled "Not wired — Pending identity integration"
- **NavRail, ChatDrawer** — confirmed dead code (not imported anywhere)

---

## What Remains Mocked

| Area | Status | Reason |
|------|--------|--------|
| POST /workflows/:id/trigger | Stub | No workflow engine runtime |
| POST /agents/:id/signal | Stub | Agent signal routing not yet wired |
| POST /organism/handoff | Stub | Handoff submission needs task context |
| POST /organism/parallel | Stub | Parallel execution needs task factory |
| POST /dex/converse | Real (agent bridge) | Already working |
| GET /dex/history | `[]` | Chat persistence not implemented |
| PATCH /settings | Stub | Settings mutation needs governance gate design |
| PATCH /governance | Stub | Same — governance policy mutation |
| Execution canvas | Placeholder text | noVNC/screenshot stream not connected |
| Terminal in Editor | Placeholder | "Coming in Phase 5" |
| CommsPanel | Not wired | Transport integration pending |
| ExperimentsPanel | Not wired | Experiment framework pending |
| ProfilePanel | Not wired | Identity integration pending |

---

## Meta-IDE Backend Foundation

| Capability | Endpoint | Status |
|-----------|----------|--------|
| List nodes/workspaces | GET /workspaces | OPERATIONAL |
| List files by path | GET /files?path= | OPERATIONAL |
| Read file content | GET /file?path= | OPERATIONAL |
| File write/patch | — | NOT BUILT (needs approval gate design) |
| List tmux sessions | GET /sessions | OPERATIONAL |
| List Docker containers | GET /docker | OPERATIONAL |
| List workcell outputs | GET /organism/workcells | OPERATIONAL |

All file access restricted to safe roots (UMH_ROOT). Governed file write
is the main remaining gap — needs approval gate integration before exposure.

---

## Validation Results

| Gate | Result |
|------|--------|
| Organism bridge (16 actions) | 16/16 PASS |
| Daemon E2E tests | 7/7 PASS |
| Organism unit tests | 10/10 PASS |
| Type coherence gate | PASS (1 pre-existing warning: EventType) |
| Instance context gate | CLEAN (512 files scanned) |
| Dependency direction | CLEAN (no transports/services imports) |
| Python compile check | PASS |

---

## External Dashboard Learning

Analyzed 5 leverage maps (Codex, Claude Code Ecosystems, cortextOS,
Karpathy, Polsia). Key findings:

| Pattern | Evidence | UMH Status |
|---------|----------|------------|
| Async task poll | PARTIAL | Gap: coordinator is sync |
| DAG dependency visualization | PARTIAL | Data model exists, rendering gap |
| GSD milestone tracker | VERIFIED | Skills exist, cockpit panel gap |
| Daemon control surface | VERIFIED | `/loop` + `/schedule` exist |
| Night shift report | CLAIMED | Daemon + morning-brief exist |

**Conclusion**: No fundamentally new substrate concepts needed.
All gaps are rendering — projecting existing data into cockpit panels.

---

## Files Changed

### New files
- `saas/bridge/organism_bridge.py` — 33-action organism bridge (416 lines)
- `docs/audits/convergence/cockpit_operational_gap_map.md` — gap map
- `docs/audits/convergence/phase4_cockpit_operationalization.md` — this report

### Modified files
- `saas/api/lib/python_bridge.ts` — added `callOrganism()` helper
- `saas/api/routes/organism.ts` — 6 stubs → 28 real endpoints
- `saas/api/routes/execution.ts` — 7 stubs → real organism state
- `saas/api/routes/knowledge.ts` — 3 stubs → organism-derived data
- `saas/api/routes/settings.ts` — hardcoded → RuntimeGraph + Governor
- `saas/api/routes/governance.ts` — hardcoded → RecursionGovernor
- `saas/api/routes/analytics.ts` — accountability/intelligence → real
- `saas/api/routes/system.ts` — pulse enhanced, 5 new endpoints
- `saas/api/index.ts` — added /ide/* auth middleware
- `cockpit/src/renderer/panels/SkillsPanel.tsx` — wired to knowledgeStore
- `cockpit/src/renderer/panels/CommsPanel.tsx` — labeled not wired
- `cockpit/src/renderer/panels/TrackingPanel.tsx` — labeled not wired
- `cockpit/src/renderer/panels/ExperimentsPanel.tsx` — labeled not wired
- `cockpit/src/renderer/panels/ProfilePanel.tsx` — labeled not wired

---

## Architecture Metrics

- **Endpoints before**: ~20 real, ~20 stubbed
- **Endpoints after**: ~50 real, ~8 stubbed
- **Bridge actions**: 33 (16 read, 6 write, 5 system, 3 meta-IDE, 3 governance)
- **Organism modules exposed**: 14 of 22 (the remaining 8 are internal/support)
- **New frontend components**: 0 (all changes to existing panels)
- **UI style changes**: 0

---

## Next Highest-Leverage Sprint

1. **DAG visualization** in ExecutionPanel — render coordinator objectives
   with blocked_by/blocks dependency chains
2. **Async task submission** — wrap coordinator.execute_objective() in an
   async submit/poll pattern so cockpit can track progress
3. **Governed file write** — add approval-gated file mutation for Meta-IDE
4. **Chat persistence** — wire /dex/history to OrganismStore messages
5. **WebSocket organism events** — push organism state changes to cockpit
   in real-time instead of polling
