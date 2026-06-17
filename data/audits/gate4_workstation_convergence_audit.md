# Gate 4 — Workstation Convergence — Surface Audit

**Date:** 2026-06-16
**Purpose:** Complete inventory of all cockpit surfaces mapped to 13 canonical capabilities.

---

## Ground Truth Summary

| Layer | Count |
|-------|-------|
| Route files (`cockpit_*_routes.py`) | 37 |
| Endpoints in `cockpit_core_routes.py` | 78 |
| Panel cases in `Shell.tsx` | 50 |
| Nav items in `routes.ts` (primary) | 30 |
| Nav items in `routes.ts` (dev) | 13 |
| Nav items in `routes.ts` (system) | 1 |
| Nav items in `routes.ts` (planned/stub) | 3 |
| Zustand stores | 43 |
| `cockpit_core_routes.py` lines | 3,227 (OVER 3,000 LIMIT) |

---

## 13 Canonical Capabilities

| # | ID | Label | Operator Question |
|---|-----|-------|------------------|
| 1 | `commandcenter` | Command Center | "Where am I? What needs me? What changed?" |
| 2 | `work` | Work | "What work exists? What needs approval?" |
| 3 | `agents` | Agents | "What agents exist? What are they doing?" |
| 4 | `approvals` | Approvals | "What decisions need me?" |
| 5 | `activity` | Activity | "What happened?" |
| 6 | `editor` | Meta IDE | "What's my engineering workspace?" |
| 7 | `execution` | Execution | "What's running? What failed?" |
| 8 | `organismmap` | Organism Map | "Is the organism healthy?" |
| 9 | `rooms` | Conference Rooms | "Voice/video collaboration" |
| 10 | `vision` | Vision | "What am I looking at across devices?" |
| 11 | `broadcast` | Broadcast | "Content distribution" |
| 12 | `knowledge` | Knowledge | "Wiki, memory, docs, intent" |
| 13 | `settings` | Settings | "Configuration + Profile" |

---

## Route Files Inventory (37 files)

### Files with endpoints (non-zero route count)

| File | Endpoints | Canonical Capability | Action |
|------|-----------|---------------------|--------|
| `cockpit_core_routes.py` | 78 | MULTIPLE — must split | **SPLIT** (B1) |
| `cockpit_work_center_routes.py` | 16 | Work | KEEP |
| `cockpit_distributed_runtime_routes.py` | 10 | Execution | KEEP |
| `cockpit_reality_intelligence_routes.py` | 8 | Meta IDE | KEEP |
| `cockpit_workspace_observation_routes.py` | 6 | Meta IDE | KEEP |
| `cockpit_meta_ide_routes.py` | 6 | Meta IDE | KEEP |
| `cockpit_voice_routes.py` | 3 | Conference Rooms | KEEP |

### Files with zero endpoints (mounted but empty — configure() pattern)

| File | Canonical Capability | Action |
|------|---------------------|--------|
| `cockpit_action_bridge_routes.py` | Work | KEEP (lazy load) |
| `cockpit_autonomous_routes.py` | Execution | KEEP |
| `cockpit_broadcast_routes.py` | Broadcast | KEEP |
| `cockpit_command_center_routes.py` | Command Center | **EXTEND** (F) |
| `cockpit_context_assimilation_routes.py` | Meta IDE | KEEP |
| `cockpit_economy_routes.py` | Execution | KEEP |
| `cockpit_engineering_review_routes.py` | Meta IDE | KEEP |
| `cockpit_engineering_routes.py` | Meta IDE | KEEP |
| `cockpit_entity_routes.py` | Knowledge | KEEP |
| `cockpit_operator_experience_routes.py` | Command Center | KEEP |
| `cockpit_operator_home_routes.py` | Command Center | KEEP |
| `cockpit_operator_loop_routes.py` | Execution | KEEP |
| `cockpit_operator_presence_routes.py` | Command Center | KEEP |
| `cockpit_operator_timeline_routes.py` | Activity | KEEP |
| `cockpit_organism_routes.py` | Organism Map | KEEP |
| `cockpit_presence_routes.py` | Command Center | KEEP |
| `cockpit_propagation_graph_routes.py` | Organism Map | KEEP |
| `cockpit_reality_model_routes.py` | Knowledge | KEEP |
| `cockpit_rooms_routes.py` | Conference Rooms | KEEP |
| `cockpit_runtime_surface_routes.py` | Execution | KEEP |
| `cockpit_screen_awareness_routes.py` | Vision | KEEP |
| `cockpit_self_build_routes.py` | Meta IDE (dev) | KEEP |
| `cockpit_self_improvement_routes.py` | Meta IDE (dev) | KEEP |
| `cockpit_service_graph_routes.py` | Organism Map | KEEP |
| `cockpit_state_authority_routes.py` | Organism Map | KEEP |
| `cockpit_umh_node_routes.py` | Organism Map | KEEP |
| `cockpit_universal_work_routes.py` | Work (dev) | KEEP |
| `cockpit_workspace_routes.py` | Meta IDE | KEEP |
| `cockpit_workspace_topology_routes.py` | Meta IDE | KEEP |
| `cockpit_workstation_control_routes.py` | Meta IDE | KEEP |

### New route files (Gate 4)

| File | Canonical Capability | Workcell |
|------|---------------------|----------|
| `cockpit_organism_map_routes.py` | Organism Map | G |
| `cockpit_intent_routes.py` | Knowledge | H |
| `cockpit_execution_routes.py` | Execution | H |
| `cockpit_activity_routes.py` | Activity | H |

---

## core_routes.py Split Plan (B1)

### File 1: `cockpit_core_routes.py` (~1,500 lines)
- Build/pulse/mesh-metrics/models/infra (lines 225-390)
- Agents/memory/skills/observations/workflows/tasks (lines 420-678)
- Comms/tracking/analytics (lines 680-763)
- Pipeline submit/comms send/workflow trigger (lines 953-1055)
- Activity stream (lines 1105-1196)
- EOS projection endpoints (lines 1518-1651)
- Notifications/feedback (lines 1652-1782)
- WebSocket streams (lines 1783-2116)
- Loops (lines 2117-2220)
- Providers health (lines 2565-2648)
- Bootstrap (lines 2851-3002)
- Config (lines 3003-3038)
- Late routes: Claude session, tmux, council, device presence (lines 3039-3227)

### File 2: `cockpit_core_governance_routes.py`
- Governance controls (lines 1197-1302)
- Governance tiers + tier-check (lines 1265-1363)

### File 3: `cockpit_core_conversation_routes.py`
- DEX channel: advisor/converse, dex/converse (lines 1303-1517)
- Chat endpoints: history, converse, send, push, attachment (lines 2690-2850)
- Intent classification (lines 2647-2689)

### File 4: `cockpit_core_execution_routes.py`
- Execution substrate: status, log, authority, start, stop, complete, fail (lines 2221-2564)

---

## Duplicate Endpoints (B2)

| Duplicate | Canonical Owner | Remove From |
|-----------|----------------|-------------|
| `GET /approvals` | `cockpit_work_center_routes.py` | `cockpit_core_routes.py` |
| `GET /current` | `cockpit_command_center_routes.py` | `cockpit_screen_awareness_routes.py` |
| `GET /health` | `cockpit_command_center_routes.py` | `cockpit_service_graph_routes.py` |
| `GET /nodes` | `cockpit_umh_node_routes.py` | `cockpit_broadcast_routes.py` |
| `GET /services` | `cockpit_service_graph_routes.py` | `cockpit_operator_home_routes.py` |
| `GET /timeline` | `cockpit_operator_timeline_routes.py` | `cockpit_operator_home_routes.py` |
| `WS /ws` | `cockpit_core_routes.py` | `cockpit_broadcast_routes.py` |

---

## Nav Items Inventory (routes.ts)

### Current primary (30) → Target primary (13)

| Current ID | Current Label | Target Capability | Action |
|-----------|---------------|-------------------|--------|
| `commandcenter` | Command Center | Command Center | **KEEP** |
| `work` | Work | Work | **KEEP** |
| `agents` | Agents | Agents | **KEEP** |
| `approvals` | Approvals | Approvals | **KEEP** |
| `activity` | Activity | Activity | **KEEP** |
| `editor` | Meta IDE | Meta IDE | **KEEP** |
| `execution` | Execution | Execution | **KEEP** |
| `infrastructure` | Infrastructure | Organism Map | **MERGE → organismmap** |
| `rooms` | Conference Rooms | Conference Rooms | **KEEP** |
| `comms` | Comms | Command Center | **DEMOTE → dev** |
| `vision` | Vision | Vision | **KEEP** |
| `broadcast` | Broadcast | Broadcast | **KEEP** |
| `strategy` | Strategy | Command Center | **DEMOTE → dev** |
| `tickloop` | Tick Loop | Command Center | **DEMOTE → dev** |
| `projections` | Projections | Command Center | **DEMOTE → dev** |
| `continuity` | Continuity | Command Center | **DEMOTE → dev** |
| `presence` | Presence | Command Center | **DEMOTE → dev** |
| `commands` | Commands | Command Center | **DEMOTE → dev** |
| `workstation` | Workstation | Meta IDE | **DEMOTE → dev** |
| `knowledge` | Knowledge | Knowledge | **KEEP** |
| `sessions` | Sessions | Execution | **DEMOTE → dev** |
| `execcoord` | Exec Coordinator | Execution | **DEMOTE → dev** |
| `executor` | Executor | Execution | **DEMOTE → dev** |
| `organismloop` | Organism Loop | Execution | **DEMOTE → dev** |
| `operatortimeline` | Operator Timeline | Activity | **DEMOTE → dev** |
| `realitytimeline` | Reality Timeline | Activity | **DEMOTE → dev** |
| `realityintelligence` | Reality Intelligence | Meta IDE | **DEMOTE → dev** |
| `metaide` | Meta IDE (dup) | Meta IDE | **DEMOTE → dev** |
| `engineering` | Engineering | Meta IDE | **DEMOTE → dev** |
| `profile` | Profile | Settings | **DEMOTE → dev** |

### Current dev (13) — remain dev

| ID | Label | Capability |
|----|-------|-----------|
| `dashboard` | Dashboard | Command Center (dev) |
| `organism` | Organism | Organism Map (dev) |
| `intelligence` | Intelligence | Meta IDE (dev) |
| `propagation` | Propagation | Organism Map (dev) |
| `operator` | Operator | Command Center (dev) |
| `tmux` | Tmux | Meta IDE (dev) |
| `runtime` | Runtime | Execution (dev) |
| `selfbuild` | Self-Build | Meta IDE (dev) |
| `universalwork` | Universal Work | Work (dev) |
| `worldmodel` | World Model | Knowledge (dev) |
| `portfolio` | Portfolio | (EOS projection) |
| `company` | Company | (EOS projection) |

### System (1)

| ID | Label | Action |
|----|-------|--------|
| `settings` | Settings | **KEEP** — becomes canonical #13 |

### New primary nav item (Gate 4)

| ID | Label | Capability |
|----|-------|-----------|
| `organismmap` | Organism Map | Organism Map — replaces `infrastructure` |

---

## Panel Inventory (Shell.tsx — 50 cases)

| Panel ID | Canonical Capability | Action |
|----------|---------------------|--------|
| `dashboard` | Command Center (dev) | DEMOTE → dev |
| `agents` | Agents | KEEP |
| `tasks` | Work | MERGE → work |
| `approvals` | Approvals | KEEP |
| `activity` | Activity | KEEP |
| `knowledge` | Knowledge | KEEP |
| `analytics` | (planned) | KEEP (stub) |
| `editor` | Meta IDE | KEEP |
| `settings` | Settings | KEEP |
| `execution` | Execution | KEEP |
| `portfolio` | (EOS projection) | DEMOTE → dev |
| `company` | (EOS projection) | DEMOTE → dev |
| `comms` | Command Center | ABSORB → Command Center |
| `workflows` | Work | MERGE → work |
| `tracking` | (stub) | KEEP (stub) |
| `skills` | Agents | MERGE → agents |
| `experiments` | (stub) | KEEP (stub) |
| `infrastructure` | Organism Map | **REPLACE → organismmap** |
| `profile` | Settings | ABSORB → Settings |
| `organism` | Organism Map (dev) | DEMOTE → dev |
| `intelligence` | Meta IDE (dev) | DEMOTE → dev |
| `worldmodel` | Knowledge (dev) | DEMOTE → dev |
| `selfbuild` | Meta IDE (dev) | DEMOTE → dev |
| `universalwork` | Work (dev) | DEMOTE → dev |
| `propagation` | Organism Map (dev) | DEMOTE → dev |
| `operator` | Command Center (dev) | DEMOTE → dev |
| `runtime` | Execution (dev) | DEMOTE → dev |
| `tmux` | Meta IDE (dev) | DEMOTE → dev |
| `work` | Work | KEEP |
| `workspace` | Meta IDE | ABSORB → Meta IDE |
| `commandcenter` | Command Center | KEEP |
| `vision` | Vision | KEEP |
| `rooms` | Conference Rooms | KEEP |
| `broadcast` | Broadcast | KEEP |
| `strategy` | Command Center | ABSORB → Command Center |
| `tickloop` | Command Center | ABSORB → Command Center |
| `projections` | Command Center | ABSORB → Command Center |
| `continuity` | Command Center | ABSORB → Command Center |
| `presence` | Command Center | ABSORB → Command Center |
| `commands` | Command Center | ABSORB → Command Center |
| `workstation` | Meta IDE | ABSORB → Meta IDE |
| `sessions` | Execution | ABSORB → Execution |
| `execcoord` | Execution | ABSORB → Execution |
| `executor` | Execution | ABSORB → Execution |
| `organismloop` | Execution | ABSORB → Execution |
| `operatortimeline` | Activity | ABSORB → Activity |
| `realitytimeline` | Activity | ABSORB → Activity |
| `realityintelligence` | Meta IDE | ABSORB → Meta IDE |
| `metaide` | Meta IDE | ABSORB → Meta IDE |
| `engineering` | Meta IDE | ABSORB → Meta IDE |

---

## Store Inventory (43 files)

| Store | Canonical Capability | Action |
|-------|---------------------|--------|
| `cockpitStore.ts` | Shell | KEEP (update Panel type) |
| `chatStore.ts` | Right Rail (orchestrator) | KEEP |
| `agentStore.ts` | Agents | KEEP |
| `approvalStore.ts` | Approvals | KEEP |
| `activityStore.ts` | Activity | EXTEND (absorb realityTimeline, actions) |
| `editorStore.ts` | Meta IDE | KEEP |
| `executionStore.ts` | Execution | EXTEND (absorb operatorLoop, operatorTimeline, organismLoop) |
| `knowledgeStore.ts` | Knowledge | KEEP |
| `roomsStore.ts` | Conference Rooms | KEEP |
| `visionStore.ts` | Vision | KEEP |
| `broadcastStore.ts` | Broadcast | KEEP |
| `settingsStore.ts` | Settings | KEEP |
| `voiceStore.ts` | Conference Rooms | KEEP |
| `voiceSessionStore.ts` | Conference Rooms | KEEP |
| `taskStore.ts` | Work | KEEP |
| `realtimeStore.ts` | Shell (WebSocket) | KEEP |
| `bootstrapStore.ts` | Shell (boot) | KEEP |
| `configStore.ts` | Settings | KEEP |
| `systemStore.ts` | Shell | KEEP |
| `viewContextStore.ts` | Shell | KEEP |
| `providerRegistryStore.ts` | Shell | KEEP |
| `metaIDEStore.ts` | Meta IDE | EXTEND (absorb screenAwareness, workspaceTopology, engineering, realityIntelligence) |
| `analyticsStore.ts` | (planned) | KEEP |
| `operatorHomeStore.ts` | Command Center | DEPRECATE → delegate to commandCenterStore |
| `operatorExperienceStore.ts` | Command Center | DEPRECATE → delegate to commandCenterStore |
| `presenceStore.ts` | Command Center | DEPRECATE → delegate to commandCenterStore |
| `operatorLoopStore.ts` | Execution | DEPRECATE → delegate to executionStore |
| `operatorTimelineStore.ts` | Activity | DEPRECATE → delegate to activityStore |
| `organismLoopStore.ts` | Execution | DEPRECATE → delegate to executionStore |
| `organismStore.ts` | Organism Map | DEPRECATE → delegate to organismMapStore |
| `umhNodeStore.ts` | Organism Map | DEPRECATE → delegate to organismMapStore |
| `serviceGraphStore.ts` | Organism Map | DEPRECATE → delegate to organismMapStore |
| `stateAuthorityStore.ts` | Organism Map | DEPRECATE → delegate to organismMapStore |
| `coherenceStore.ts` | Organism Map | DEPRECATE → delegate to organismMapStore |
| `screenAwarenessStore.ts` | Meta IDE | DEPRECATE → delegate to metaIDEStore |
| `workspaceTopologyStore.ts` | Meta IDE | DEPRECATE → delegate to metaIDEStore |
| `engineeringStore.ts` | Meta IDE | DEPRECATE → delegate to metaIDEStore |
| `realityIntelligenceStore.ts` | Meta IDE | DEPRECATE → delegate to metaIDEStore |
| `realityTimelineStore.ts` | Activity | DEPRECATE → delegate to activityStore |
| `actionsStore.ts` | Activity | DEPRECATE → delegate to activityStore |
| `intelligenceStore.ts` | Meta IDE (dev) | KEEP (dev) |
| `worldModelStore.ts` | Knowledge (dev) | KEEP (dev) |
| `deviceSessionStore.ts` | Command Center | KEEP |

### New stores (Gate 4)

| Store | Canonical Capability |
|-------|---------------------|
| `commandCenterStore.ts` | Command Center |
| `organismMapStore.ts` | Organism Map |
| `intentStore.ts` | Knowledge (intent queries) |
| `workStore.ts` | Work |

---

## Convergence Summary

| Metric | Before | After |
|--------|--------|-------|
| Primary nav items | 30 | 13 |
| Panel cases | 50 | 50 (all preserved, dev-demoted) |
| Stores | 43 | 43 + 4 new (deprecated delegate) |
| Route files | 37 | 37 + 4 new (none removed) |
| `core_routes.py` lines | 3,227 | ~1,500 (split into 4) |
| Duplicate endpoints | 7 | 0 |

Nothing is deleted. Everything is preserved via compatibility layer.
