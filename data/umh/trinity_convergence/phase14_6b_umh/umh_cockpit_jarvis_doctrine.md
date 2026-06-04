# UMH Cockpit / Jarvis Doctrine

**Phase:** 14.6B-UMH (revised 14.6D)
**Status:** DRAFT -- awaiting operator ratification
**Provenance:** OPERATOR_CORRECTION + CODE_RESOLVED_CURRENT_TRUTH + DEC-146C-001/002/003 ratification
**Date:** 2026-06-03

---

## What Cockpit Is

Cockpit is part of the indivisible Stage 1 UMH organism (DEC-146C-003): Reality Model + Cockpit + Memory + Governed Execution Loop. These four components must reach minimum viability as one integrated system. Cockpit without a reality model is only a dashboard; a reality model without Cockpit is inaccessible to the operator.

Cockpit is the operator's interface into UMH's reality model -- the rendering surface through which the operator observes, commands, and governs UMH's reality-isomorphic approximation of reality across 12 layers (physical, digital, cognitive, biological, social, economic, symbolic, operational, software, memory, source-truth, and OS-level).

Cockpit is NOT:
- Merely a dashboard or status page (it is a reality-model interface)
- The whole UMH system
- A public-facing product
- A customer-facing UI
- A sequential build deliverable that ships before or after the reality model

Cockpit IS the private universal control surface that allows the operator to:

1. Observe the entire ecosystem
2. Command UMH directly
3. Inspect agents and their state
4. Inspect work packets and execution traces
5. Inspect source truth and production truth
6. Approve or deny actions
7. Pause, resume, and abort work
8. Route tasks to agents or manual handling
9. Inspect files and diffs
10. Inspect tmux sessions
11. Inspect infrastructure (VPS, Windows Beast, Tailscale mesh)
12. Inspect projection status across EOS, CreatorOS, LyfeOS
13. Inspect model routing decisions
14. Manage workflow definitions and triggers
15. Trigger agentic work
16. Supervise autonomous execution lanes
17. Use voice or text commands
18. Operate across VPS/Windows/device contexts
19. Use UMH as a Jarvis-like personal intelligence system

---

## Current Cockpit Implementation

### Backend (Python)

**Total endpoints: 276** across 12 route files under `transports/api/`

| Route File | Endpoints | LOC | Domain |
|---|---|---|---|
| `cockpit.py` | 67 | 2,304 | Core: build, pulse, models, infra, approvals, agents, memory, skills, observations, workflows, tasks, comms, tracking, analytics, settings, mesh, pipeline, organism, notifications, feedback, loops, execution, chat, config, dex, eos projection, governance, profile, activity |
| `cockpit_organism_routes.py` | 39 | 557 | Organism: status, agents, deliverables, events, tick, leverage, metrics, bottlenecks, intelligence, physics, compression, workload, execution-mode, automation, maintenance, assisted, acceptance |
| `cockpit_spine_router.py` | 30 | 518 | Governed execution spine: journal, mutations, guard, autonomous gateway, plan execution, reliability metrics, doctrine |
| `cockpit_autonomous_routes.py` | 30 | 586 | PR factory, sandboxes, manifests, cadence, templates, candidate supply, governance, reliability signals |
| `cockpit_context_assimilation_routes.py` | 24 | 551 | Sources, jobs, diagnostics, proposals, reconciliation, sync policies, permissions, environment discovery |
| `cockpit_economy_routes.py` | 21 | 447 | Economy metrics, recursion, advisor hierarchy, assimilation, runtimes, workcells, topology, throughput, reconciliation |
| `cockpit_universal_work_routes.py` | 16 | 210 | Work packets, workcells, roles, knowledge models |
| `cockpit_self_build_routes.py` | 11 | 191 | Self-build queue, roadmap, artifact linking |
| `cockpit_propagation_graph_routes.py` | 10 | 216 | Graph, impact analysis, planning, dry-run, correspondence proof |
| `cockpit_runtime_surface_routes.py` | 10 | 163 | Runtime sessions, adapters, create/start/inject/stop, handoff preview |
| `cockpit_entity_routes.py` | 9 | 333 | Portfolio, departments, roles, companies, product connections |
| `cockpit_operator_experience_routes.py` | 9 | 145 | Orchestrator kernel sessions, status, approvals, send, previews |

**Auth model:**
- API Key (`UMH_OPERATOR_API_KEY` via `X-API-Key` header)
- Operator Token (`UMH_OPERATOR_TOKEN` via `X-Operator-Token` header) for mutations
- Dev Bypass (`UMH_DEV_BYPASS=true`) from private IPs only
- WebSocket auth (bearer token in `Sec-WebSocket-Protocol`)
- Rate limiting: in-memory per-action windows

### Frontend (Electron/React)

**Location:** `cockpit/src/`
**Technology:** Electron + React + TypeScript + Vite

**27 panels:**
Activity, Agents, Analytics, Approvals, Comms, Company, Dashboard, Editor, Execution, Experiments, Infrastructure, Intelligence, Knowledge, Operator, Organism, Portfolio, Profile, PropagationGraph, Runtime, SelfBuild, Settings, Skills, Tasks, Tracking, UniversalWork, Workflows, WorldModel

**26 components:**
AgentCard, ChatDrawer, CommandPalette, ConnectionBanner, ControlPanel, EventConsole, ExecutionTimeline, FabLarge, FabMedium, FabSmall, GraphView, HudBar, LeftRail, LivePreview, NavRail, OverlayToggle, RightRail, RingGauge, Shell, SplitPane, TaskBlock, TimelineView, TitleBar, TopologyMap, VoiceCommandBar, VoiceWaveform

**20 stores:**
activity, agent, analytics, approval, chat, cockpit, coherence, config, editor, execution, intelligence, knowledge, operatorExperience, organism, realtime, settings, system, task, voice, worldModel

**API integration:**
- `api/websocket.ts` -- live pulse
- `api/voice-controller.ts` -- voice commands
- `api/voice-ws.ts` -- voice WebSocket
- `api/client.ts` -- HTTP client

**Hooks:**
- `useKeyboard.ts` -- keyboard shortcuts
- `useOrganismRealtime.ts` -- organism live updates
- `usePolling.ts` -- interval polling
- `useVoiceDetection.ts` -- voice activity detection
- `useWebSocket.ts` -- WebSocket connection management

### Infrastructure

- Deployed as Electron app (can also build for web)
- `fly.toml` exists (Fly.io deployment for web version)
- Docker image: `cockpit/Dockerfile` (nginx-based for web builds)
- Domain: `universalmetaharness.tech`

---

## Stage 1 Organism Readiness Gate (DEC-146C-003)

Stage 1 readiness is the MVP gate for UMH. Per DEC-146C-003, Stage 1 is indivisible: Reality Model + Cockpit + Memory + Governed Execution Loop must reach minimum viability together. Each increment must advance the integrated organism -- completing one component in isolation and deferring the others is rejected.

Stage 1 does not require commercial-grade completeness before use. It requires a partially functional integrated vertical slice. The 10 operator-specified acceptance criteria for Stage 1 minimum viability:

1. Operator can use Cockpit/Jarvis as primary interface
2. UMH can capture intent and preserve it in memory/source truth
3. UMH can maintain a usable reality model (work, products, companies, files, artifacts, agents, blockers)
4. UMH can generate work packets from operator intent
5. UMH can route work packets to agents/tools
6. UMH can govern risky actions through approval gates
7. UMH can verify outputs (tests, audit reports, diffs, review packets)
8. UMH can update memory/reality model after outcomes
9. UMH can work on itself through governed self-improvement work packets
10. UMH can build and improve projection apps from inside the UMH operating loop

The following capabilities must be buildable and testable.

### Voice/Text Command Intake

**Status: PARTIALLY IMPLEMENTED**

- `VoiceCommandBar` component exists in frontend
- `VoiceWaveform` component exists
- `voiceStore.ts` exists
- Voice endpoints at `transports/api/voice.py` (4 endpoints: start, stop, process, status)
- Voice session bridge at `substrate/execution/bridge/` (voice_session.py, voice_first.py, voice_eos_responder.py, discord_voice_transport.py, discord_voice_playback.py, tts_sanitize.py)
- `VoiceSession` class imported from `substrate.execution.voice.session`
- `useVoiceDetection.ts` hook for frontend VAD
- `speechInputAdapter.ts` and `voiceTypes.ts` in `operator/` directory

**Evidence:** Components exist, store wired, backend endpoints present. Runtime verification required for end-to-end voice command flow.

### Command Routing

**Status: IMPLEMENTED**

- `CommandPalette` component in frontend
- Intent classification in `substrate/execution/spine.py` (7 intent patterns)
- Gateway request routing at `substrate/control_plane/runtime/gateway.py`
- Substrate command handler at `transports/presence/handlers/substrate_command_handler.py`

**Evidence:** Multiple routing paths exist. Gateway handles all AI requests.

### Approval Workflows

**Status: IMPLEMENTED**

- `ApprovalsPanel` in frontend
- `approvalStore.ts` in frontend
- `/api/umh/approvals` (list), `/api/umh/approvals/{id}/approve`, `/api/umh/approvals/{id}/deny`
- `transports/discord/approval_bridge.py` (Discord approval flow)
- `substrate/organism/operator_acceptance_mode.py`
- Operator acceptance endpoints in `cockpit_organism_routes.py` (overview, runs, artifacts, scenarios, readiness, start, proof)

**Evidence:** Full CRUD + Discord bridge. Rate-limited mutation endpoints require operator token.

### Work Packet Visibility

**Status: IMPLEMENTED**

- `TasksPanel` and `UniversalWorkPanel` in frontend
- `taskStore.ts` in frontend
- `/api/umh/tasks`, `/api/umh/universal-work/*` endpoints (16 endpoints in cockpit_universal_work_routes.py)
- Execution traces serve as work packet records

**Evidence:** Panels exist, API returns recent traces and work packets.

### Agent Visibility

**Status: IMPLEMENTED**

- `AgentsPanel` in frontend
- `AgentCard` component
- `agentStore.ts` in frontend
- `/api/umh/agents` endpoint (reads .md files + organism agent state)

**Evidence:** Agent list rendered from file system + organism runtime.

### Model Routing Visibility

**Status: IMPLEMENTED**

- `/api/umh/models` endpoint returns routing config
- `IntelligencePanel` in frontend
- `intelligenceStore.ts` in frontend
- `AnalyticsPanel` shows model usage stats

**Evidence:** Current routing chain visible. Analytics endpoint aggregates provider usage.

### Infrastructure Visibility

**Status: IMPLEMENTED**

- `InfrastructurePanel` in frontend
- `/api/umh/infra` returns compute/network/service nodes
- `/api/umh/mesh/nodes` returns Tailscale peers + daemon nodes
- `TopologyMap` component for visual representation

**Evidence:** Tailscale integration, Docker socket mounted in os-operator for container visibility.

### Projection Status Visibility

**Status: PARTIALLY IMPLEMENTED**

- `CompanyPanel`, `PortfolioPanel` in frontend
- `/api/umh/eos/*` endpoints (pipeline, kpis, activity)
- `/api/umh/entity/*` endpoints (9 endpoints in cockpit_entity_routes.py: product connections CRUD, departments, roles, companies)
- `ProductConnectionManager` provides cross-product summary

**Evidence:** EOS-specific views implemented. CreatorOS/LyfeOS panels not yet present.

### Execution Control (pause/resume/abort)

**Status: STUB**

- `/api/umh/execution/start`, `/stop`, `/pause`, `/resume` all return static `{"ok": true}`
- `ExecutionPanel` exists in frontend
- `executionStore.ts` exists in frontend
- These endpoints are not wired to actual execution control

**Evidence:** Endpoints exist but are stubs (confirmed: lines 1968-1989 in cockpit.py). This is a gap.

### Source Truth / Production Truth Visibility

**Status: PARTIALLY IMPLEMENTED**

- `/api/umh/memory` endpoint returns canonical memory store
- `/api/umh/tracking` returns document tracking
- `KnowledgePanel` in frontend
- `knowledgeStore.ts` in frontend
- Autonomous PR factory has production truth endpoints (cockpit_autonomous_routes.py)
- No dedicated source truth / production truth lifecycle panel

**Evidence:** Memory and tracking visible. Lifecycle visibility (draft to approved to production) not surfaced as a unified view.

### Tmux/Session Visibility

**Status: PARTIALLY IMPLEMENTED**

- tmux socket mounted in os-discord container
- Claude CLI session targeting via `EOS_ROUTER_CLAUDE_CLI_SESSION`
- Runtime surface routes provide session management (10 endpoints in cockpit_runtime_surface_routes.py)
- No dedicated tmux panel in cockpit frontend

**Evidence:** Infrastructure exists for tmux interaction and runtime session management but no dedicated UI surface.

### File/Meta-IDE Visibility

**Status: PARTIALLY IMPLEMENTED**

- `EditorPanel` exists in frontend
- `editorStore.ts` exists in frontend
- `/api/umh/chat/attachment` provides file access (path-restricted)
- No integrated file browser or diff viewer

**Evidence:** Editor panel exists, file download works. Full meta-IDE not implemented.

### Error/Log Visibility

**Status: PARTIALLY IMPLEMENTED**

- `EventConsole` component in frontend
- `/api/umh/activity/stream` (unified feed)
- `activityStore.ts` in frontend
- `substrate/observability/error_recorder.py` (centralized error recording)
- No dedicated log viewer panel

**Evidence:** Errors recorded centrally, activity stream aggregates events. No log streaming UI.

### Organism Visibility

**Status: IMPLEMENTED**

- `OrganismPanel` in frontend
- `organismStore.ts` in frontend
- `useOrganismRealtime.ts` hook for live updates
- 39 endpoints in `cockpit_organism_routes.py`
- 21 economy endpoints in `cockpit_economy_routes.py`
- Workload, bottleneck, intelligence, physics, compression, automation, maintenance views

**Evidence:** Most complete subsystem. Full lifecycle visibility from status through intelligence to assisted execution.

### Autonomous Execution Supervision

**Status: IMPLEMENTED**

- 30 endpoints in `cockpit_autonomous_routes.py`
- 30 endpoints in `cockpit_spine_router.py`
- PR factory, sandbox management, cadence scheduling, template governance
- Autonomous gateway with policy control and threshold management
- Reliability-weighted candidate ranking

**Evidence:** Backend fully implemented. Frontend panels (Execution, Organism) surface this data.

### Propagation Graph

**Status: IMPLEMENTED**

- `PropagationGraphPanel` in frontend
- `GraphView` component for visualization
- 10 endpoints in `cockpit_propagation_graph_routes.py`
- Impact analysis, planning, dry-run execution, correspondence proof

**Evidence:** Full graph infrastructure with visual component.

### Context Assimilation

**Status: IMPLEMENTED**

- 24 endpoints in `cockpit_context_assimilation_routes.py`
- Sources, jobs, diagnostics, proposals, reconciliation
- Sync policies, permissions, environment discovery
- Cross-source signal handling

**Evidence:** Backend fully implemented. No dedicated frontend panel yet.

### Self-Build

**Status: IMPLEMENTED**

- `SelfBuildPanel` in frontend
- 11 endpoints in `cockpit_self_build_routes.py`
- Queue management, roadmap phases, artifact linking

**Evidence:** Full queue and roadmap management via API and UI.

### Security/Risk Visibility

**Status: PARTIALLY IMPLEMENTED**

- `/api/umh/governance` endpoint returns policy table
- `/api/umh/governance/tiers` returns permission model
- Spine guard status and blocked items via `cockpit_spine_router.py`
- No dedicated security dashboard panel

**Evidence:** Governance model visible via API. No UI surface for security posture.

### Degraded Mode Operation

**Status: NOT IMPLEMENTED**

- No degraded mode detection or fallback UI
- No offline capability
- `ConnectionBanner` component exists but only shows connection state, not degraded mode handling

**Evidence:** No code found for degraded mode handling in cockpit.

---

## Readiness Summary

| Capability | Status | Gap Severity |
|---|---|---|
| Voice/Text Command Intake | PARTIALLY IMPLEMENTED | MEDIUM -- components exist, end-to-end unverified |
| Command Routing | IMPLEMENTED | NONE |
| Approval Workflows | IMPLEMENTED | NONE |
| Work Packet Visibility | IMPLEMENTED | NONE |
| Agent Visibility | IMPLEMENTED | NONE |
| Model Routing Visibility | IMPLEMENTED | NONE |
| Infrastructure Visibility | IMPLEMENTED | NONE |
| Projection Status Visibility | PARTIALLY IMPLEMENTED | LOW -- EOS done, others not present |
| Execution Control | STUB | HIGH -- endpoints are non-functional stubs |
| Source/Production Truth | PARTIALLY IMPLEMENTED | MEDIUM -- no unified lifecycle view |
| Tmux/Session Visibility | PARTIALLY IMPLEMENTED | MEDIUM -- no UI surface |
| File/Meta-IDE | PARTIALLY IMPLEMENTED | MEDIUM -- editor exists, no browser/diff |
| Error/Log Visibility | PARTIALLY IMPLEMENTED | LOW -- events exist, no log stream |
| Organism Visibility | IMPLEMENTED | NONE |
| Autonomous Execution | IMPLEMENTED | NONE |
| Propagation Graph | IMPLEMENTED | NONE |
| Context Assimilation | IMPLEMENTED | LOW -- no frontend panel |
| Self-Build | IMPLEMENTED | NONE |
| Security/Risk | PARTIALLY IMPLEMENTED | LOW -- no UI surface |
| Degraded Mode | NOT IMPLEMENTED | MEDIUM -- no offline/fallback |

**IMPLEMENTED:** 10 of 20 capabilities
**PARTIALLY IMPLEMENTED:** 8 of 20 capabilities
**STUB:** 1 of 20 capabilities (Execution Control)
**NOT IMPLEMENTED:** 1 of 20 capabilities (Degraded Mode)

---

## Architecture Position

Cockpit occupies the `transports/` layer in UMH architecture:

```
Cockpit Frontend (Electron/React)
    |
    v
transports/api/cockpit*.py  (12 route files, 276 endpoints)
    |
    v
substrate/  (types, execution, organism, governance, state)
    |
    v
adapters/  (models, GWS, browser)
```

Cockpit never contains business logic. It is a transport surface that exposes substrate capabilities to the operator. All intelligence, governance, and execution live in substrate. Cockpit renders, commands, and observes.

---

## Jarvis Doctrine

The Jarvis analogy is the correct mental model for Cockpit:

1. **Cockpit is the operator's reality-model interface.** It is not a product. It is not a demo. It is not a dashboard. It is the surface through which the operator perceives UMH's 12-layer reality model and acts through it. Aesthetics serve function.

2. **Every reality-model layer must be observable through Cockpit.** If a reality layer exists in substrate but has no Cockpit surface, the operator is blind to it. Blindness is unacceptable.

3. **Every UMH capability must be commandable through Cockpit.** Observation without control is a dashboard. Cockpit is not a dashboard. The operator must be able to act on anything they observe.

4. **Voice and text are equal input channels.** The operator may be at a desk, on a phone, or walking. Cockpit must accept commands through whatever channel is available.

5. **Cockpit degrades gracefully.** When infrastructure is down, Cockpit shows what is down and what still works. It never shows a blank page or a spinner.

6. **Cockpit is the single pane of glass onto reality.** The operator should not need to SSH into the VPS, open Docker logs, check Discord, and inspect files separately. All of that flows through Cockpit as layers of the reality model.

7. **Cockpit is the approval gateway.** Autonomous execution proposes. The operator approves or denies through Cockpit. This is the governance boundary.

8. **Cockpit is projection-agnostic.** It shows EOS, CreatorOS, LyfeOS, and any future projection as instance reality models through the same universal interface. Projections register their views; Cockpit renders them.

9. **Cockpit is indivisible from the reality model (DEC-146C-003).** Cockpit and the reality model advance together. Every increment that advances the reality model must also advance its Cockpit rendering. Every Cockpit improvement must be grounded in reality-model state, not synthetic/mock data.

---

## Priority Gaps (ordered by impact)

1. **Execution Control stubs** -- The 4 execution control endpoints return static `{"ok": true}`. Wiring these to actual spine control is the highest-impact gap.

2. **Degraded Mode** -- No fallback behavior when backend is unreachable. ConnectionBanner shows state but does not enable degraded operation.

3. **Voice end-to-end** -- All components exist but the full voice command flow (capture, transcribe, route, execute, speak response) has not been verified as a working pipeline.

4. **Source/Production Truth lifecycle** -- Production truth exists in autonomous routes but there is no unified view showing the draft-to-approved-to-production lifecycle across all artifacts.

5. **Tmux/Session UI** -- Runtime session management exists in the backend (10 endpoints) but no dedicated frontend panel surfaces it.

6. **Context Assimilation UI** -- 24 backend endpoints exist with no frontend panel.

7. **File browser/diff viewer** -- EditorPanel exists but lacks file browsing and diff capabilities needed for the meta-IDE vision.

8. **Log streaming** -- EventConsole shows events but there is no real-time log streaming from Docker containers or system services.

9. **Multi-projection views** -- Only EOS projection has dedicated views. CreatorOS and LyfeOS need projection registration and panel rendering.

10. **Security dashboard** -- Governance data is available via API but has no dedicated UI surface.
