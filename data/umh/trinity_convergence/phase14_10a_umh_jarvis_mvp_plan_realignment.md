# Phase 14.10A — UMH/Jarvis Workstation MVP Plan Realignment

**Date:** 2026-06-05
**Phase:** 14.10A (Gate 1 — Canonical MVP Realignment)
**Status:** PLAN_REALIGNMENT
**Canonical main:** a1a2dde3
**Stage 1 sealed:** true
**Provenance:** OPERATOR_COURSE_CORRECTION

---

## Canonical MVP Definition

Stage 1 Acceptance is sealed (a1a2dde3, 50/50 tests, 324/324 regression, 12/12 packets). The operator has corrected the post-Stage-1 direction: the next canonical objective is the **full UMH/Jarvis Workstation MVP** — not a reduced tool, not a backend organism loop, not a generic dashboard, and not projection gates.

**The MVP is:** The first functional UMH/Jarvis Workstation — a voice-first, visually aware, governed, multi-environment operator cockpit and Meta IDE that can maintain continuity across absence, coordinate agents/tasks/work packets, surface approvals/traces/proof, inspect local/VPS/container/session/runtime state, and help build software/EOS under governance.

**Software creation is the first critical proving workflow, not the whole MVP.**

**The proving workflow:** Jarvis helps build itself and then helps build EOS. But the product is broader: Jarvis is the universal cockpit.

**The essential product truth:**
- Jarvis should not reset when I leave.
- Jarvis should remain oriented.
- Jarvis should see/hear enough to know context.
- Jarvis should keep working safely.
- Jarvis should resume with me when I return.

**cortextOS stance:** Use as grounded pattern source for persistent agents, task bus, approvals, dashboard taxonomy, crons, skills, runtime adapters, and mobile control. Do not import unsafe permission defaults. UMH governance remains authoritative.

---

## 4-Gate Structure

1. **Gate 1 — Canonical MVP Realignment** (this report): lock the truth
2. **Gate 2 — Blocker Extraction**: identify only what prevents the live Jarvis demo
3. **Gate 3 — Thin Vertical Slice Implementation**: shortest live slice (activation → command → load → packet → route → visibility → approval → execution/proof → trace/memory → resume)
4. **Gate 4 — MVP Seal**: the demo works (leave → Jarvis continues → return → activate → briefing → command → execution → proof → outcome)

**MVP Seal Threshold:**
You step away. Jarvis continues safe work. You return and activate by voice/clap/hotkey/cockpit/mobile. Jarvis shows what happened, what changed, what failed, what needs approval, and what should resume. You command the next software step. It creates a work packet, routes the agent, shows runtime/repo/session state, runs checks, captures proof, and records trace/outcome/memory.

---

## 13 MVP Pillars — Current State, Blockers, Implementation Tiers

Each pillar is classified at three levels:
- **MVP functional requirement** — what it must do
- **Thin MVP implementation** — minimum viable form for demo
- **Post-MVP / end-state** — full vision that matures later

---

### Pillar 1: Presence and Activation

**MVP functional requirement:** System activates and loads context from any of: wake word, clap/sound gesture, hotkey, manual cockpit open, typed command, mobile/remote command.

**Thin MVP:** Hotkey + manual cockpit open + typed command work E2E. Wake word and clap detection have architecture defined and first hooks (audio capture path exists via Whisper/Discord). Mobile command via Discord text.

**Post-MVP:** Trained wake word model, clap/gesture recognition, camera-based presence detection, multi-device seamless handoff.

**Current state:** PARTIAL — manual cockpit open works; typed commands work via CommandPalette; Discord text/voice exist; NO hotkey activation, NO wake word, NO clap detection.

**Blockers:**

| Blocker | Status |
|---------|--------|
| Wake word detection | MISSING — architecture must be defined, first hook via Whisper |
| Clap/sound gesture | MISSING — audio analysis path undefined |
| Hotkey activation | MISSING — Electron global shortcut not wired |
| Manual cockpit open | COMPLETE — works |
| Typed command | COMPLETE — CommandPalette + Discord |
| Mobile/remote command | PARTIAL — Discord text works; no dedicated mobile surface |

---

### Pillar 2: Voice-First Command Translation

**MVP functional requirement:** Natural speech/text → intent → context retrieval → command/tool/workflow mapping → governance → execution/approval → spoken/visual response.

**Thin MVP:** Natural language typed or spoken → IntentClassifier → Gateway routing → governed execution → text response + optional TTS. Not just STT — must abstract slash commands, terminal commands, tmux/git/test/deploy/agent commands into conversational intent.

**Post-MVP:** Multi-turn dialogue, disambiguation UI, contextual memory recall during conversation, proactive suggestions.

**Current state:** PARTIAL — VoiceCommandBar + VoiceEngine + Discord voice transport exist; Whisper STT, Kokoro TTS (Beast:8880); IntentClassifier with 7 regex + 12 gateway categories; E2E cockpit voice path UNVERIFIED.

**Blockers:**

| Blocker | Status |
|---------|--------|
| Cockpit-native voice input E2E | UNVERIFIED |
| Natural command → intent mapping | PARTIAL — IntentClassifier exists but limited to regex/keywords, not natural language |
| Governance gate on voice commands | COMPLETE — all commands route through ExecutionAuthorityEngine |
| TTS response path (Kokoro) | PARTIAL — works through Discord, cockpit path unverified |

---

### Pillar 3: Eyes/Perception

**MVP functional requirement:** Screen/workspace awareness, active app/window detection, terminal/session state, repo/runtime state, visual proof, idle/away detection, camera/mic signal path defined.

**Thin MVP:** Active terminal/session state (tmux capture), repo state (git status), runtime state (container health), visual proof (Playwright screenshots), idle/away detection (keyboard/mouse timer). Camera/mic architecture defined with opt-in local-first permissions; first hooks implemented.

**Post-MVP:** Computer vision analysis, proactive screen-context inference, ambient environmental sensing, multi-camera awareness.

**Current state:** SCAFFOLD — browser_agent.py + Playwright exist for visual proof; tmux adapter can capture pane output; Docker socket mounted for container inspection; NO active window detection, NO keyboard/mouse monitoring, NO idle timer, NO camera signal path.

**Blockers:**

| Blocker | Status |
|---------|--------|
| Screen/workspace awareness (active window/app) | MISSING |
| Terminal/session state observation | PARTIAL — tmux adapter captures pane, not wired to perception pipeline |
| Repo/runtime state | PARTIAL — git status via shell, container health via Docker socket |
| Visual proof (screenshots) | PARTIAL — Playwright exists, not surfaced in cockpit |
| Idle/away detection | MISSING — no keyboard/mouse monitoring, no idle timer |
| Camera/mic signal path | MISSING — architecture undefined |

---

### Pillar 4: Continuity Across Absence

**MVP functional requirement:** Active → Idle → Away → Remote → Night/Sleeping → Extended Absence → Return → Resume Brief → Next Action. For every absence horizon, Jarvis answers: what happened, what changed, what finished, what failed, what's blocked, what needs approval, what to resume, what mode was active, what's still running.

**Thin MVP:** Continuity state machine with transitions triggered by: idle timer (→ Idle), user action (→ Active), explicit "going away" command (→ Away/Remote), time-of-day rules (→ Night), operator command (→ Extended). Resume brief generated from execution journal + organism events + pending approvals.

**Post-MVP:** Predictive absence detection, learned routines, proactive checkpoint before expected absence, ambient always-on state.

**Current state:** PARTIAL — workstation boot_sequence.py (10 steps), session_state.py (ACTIVE/PAUSED/CLOSED/ERROR), operator_state.py, open_day() briefing in day_workflows.py; NO absence detection, NO continuity state machine, NO absence-horizon-aware resume.

**Absence horizon model:**

| Horizon | Duration | Thin MVP Behavior |
|---------|----------|-------------------|
| Micro absence | Minutes | Maintain state, continue work |
| Break | 30min–2hr | Checkpoint, reduce to safe ops |
| Context switch | Variable | Preserve state, adapt workspace |
| Remote work | Hours | Same context from mobile/Discord |
| Sleep/night cycle | 6–12hr | Overnight mode: safe work, trace all, morning brief |
| Extended absence | Days+ | Deep checkpoint, minimal ops, comprehensive return brief |

**Overnight / absence behavior:**
- Continue only permitted safe work (dry_run_only enforcement)
- Pause high-risk/destructive work
- Create approval objects for blocked actions
- Trace all actions
- Update outcome/memory candidates
- Produce morning/return brief
- Surface resume points in cockpit

**User sovereignty rule:**
- The system may suggest routines based on observed patterns
- The system may ask whether to open a usual mode/tool stack (e.g., "You usually start Developer Mode at 9 PM. Want me to open it?")
- If the user says no, the system obeys
- The system must not override the user's stated desire unless governance/safety requires intervention

**Blockers:**

| Blocker | Status |
|---------|--------|
| Continuity state machine | MISSING |
| Absence detection (idle timer) | MISSING |
| State checkpoint on transition | PARTIAL — session state exists, not triggered by absence |
| Resume brief generation | PARTIAL — open_day() exists, not wired to absence horizons |
| Overnight safe-work queue | PARTIAL — autonomous cadence dry_run_only exists, no explicit overnight queue |

---

### Pillar 5: Dual Mode Taxonomy

**MVP functional requirement:** System lifecycle modes (Day, Night, Overnight, Maintenance, Idle, AFK, Remote, End-of-workday, Emergency/Degraded) and profile/work modes (Developer, Research, Music, Design, Content, Command Center, Finance, Learning) run simultaneously. System adapts to routines but does not override user intent unless governance/safety requires it.

**Thin MVP:** Both mode types defined as enums. Mode resolver loads both on activation. Cockpit renders current mode pair in HudBar. Mode switching via voice/command. User sovereignty: suggest, don't override.

**Post-MVP:** Learned mode transitions, predictive mode suggestions, mode-specific workspace layouts, mode-specific agent configurations.

**Current state:** PARTIAL — workstation state.py has 9 modes and boot sequence; OperationalMode enum (5 modes: developer, operator, autonomous, restricted, maintenance); NOT the full dual taxonomy, NOT wired to cockpit mode switching.

**Simultaneous mode example:**
- System lifecycle mode: Night Cycle / Overnight Mode
- Profile/work mode: Music Mode or Developer Mode
- Both active simultaneously; system lifecycle governs safety, profile governs workspace

**Blockers:**

| Blocker | Status |
|---------|--------|
| Full lifecycle mode enum | PARTIAL — 9 modes exist but not the specified taxonomy |
| Full profile/work mode enum | MISSING — only 5 OperationalModes, not the full set |
| Mode resolver (dual composition) | MISSING — no simultaneous lifecycle + profile resolution |
| Cockpit mode display | MISSING — HudBar exists but doesn't show mode pair |
| Mode switching (voice/command) | MISSING — no command wired to mode transition |

---

### Pillar 6: Cockpit Command Center

**MVP functional requirement:** Current mode, agents, tasks, traces, approvals, runtime health, infrastructure health, model routing, cost/burn, resume context, next action.

**Thin MVP:** DashboardPanel shows mode + agents + tasks + approvals + health. Each subsystem already has a dedicated panel. Wire existing panels into a unified command center layout.

**Post-MVP:** Customizable layouts, drag-and-drop panels, saved workspaces per mode.

**Current state:** PARTIAL (strong) — 27 panels, ~210 endpoints, WebSocket, auth model, WorldView design system. Missing: tmux session panel, real-time log streaming, degraded mode fallback, mode/resume/next-action in dashboard.

**Blockers:**

| Blocker | Status |
|---------|--------|
| Dashboard resume context + next action | MISSING — no resume widget in DashboardPanel |
| Tmux session panel | MISSING — backend exists (tmux adapter), no panel |
| Real-time log streaming | MISSING — execution logs exist, no WebSocket stream |
| Degraded mode UI | MISSING — no fallback when backend unreachable |
| cockpit.py headroom (2,652/3,000) | CAUTION — new routes in specialized files only |

---

### Pillar 7: Agent/Task/Work-Packet Control

**MVP functional requirement:** Persistent agents, task lifecycle, approvals, dependencies, proof, audit, resume.

**Thin MVP:** Existing panels (AgentsPanel, UniversalWorkPanel, TasksPanel, ApprovalsPanel) with execution control wired (pause/resume/abort actually interrupt agents).

**Post-MVP:** Agent configuration UI, task dependency graph visualization, inline proof review, bulk approval workflows.

**Current state:** PARTIAL (strong) — work packet engine (15-stage lifecycle), 6 runtime adapters, approval workflows, cockpit panels. Execution control endpoints are STUBS (return static ok, don't actually interrupt).

**Blockers:**

| Blocker | Status |
|---------|--------|
| Execution control wiring (pause/resume/abort) | SCAFFOLD — highest severity gap |
| Agent persistence visibility | PARTIAL — workcell heartbeats exist, no persistent agent registry UI |
| Task dependency view | MISSING — coordinator tracks DAG, no visual |

---

### Pillar 8: Meta IDE

**MVP functional requirement:** Unified organism workspace across local machine, VPS, containers, repos, sessions, agents, previews, tests, diffs, commits, logs, approvals, and traces.

**Thin MVP:** Cursor/Replit-inspired workspace: file browser (tree view), terminal panel (tmux pane), diff viewer (git diff rendering), test results panel, log stream, agent status sidebar, approval queue overlay. Not a VS Code fork.

**Post-MVP:** Full VS Code fork embedded in cockpit, live co-editing, inline AI suggestions, integrated version control UI.

**Current state:** PARTIAL — EditorPanel (read-only file view), tmux adapter (capture + send keys), Docker socket (container inspection), workstation state (9 modes, boot sequence). NO file browser, NO diff viewer, NO inline editing, NO terminal embedding, NO unified workspace layout.

**Blockers:**

| Blocker | Status |
|---------|--------|
| File browser (tree view) | MISSING — EditorPanel exists, no tree navigation |
| Terminal panel (tmux embedding) | MISSING — tmux adapter exists, no cockpit panel |
| Diff viewer (git diff) | MISSING — no component |
| Test results panel | MISSING — test execution exists, no cockpit surface |
| Log stream | MISSING — execution logs exist, no real-time stream |
| Unified workspace layout | MISSING — panels exist individually, no IDE-like composition |

---

### Pillar 9: App Preview / Projection Proof

**MVP functional requirement:** Live preview, desktop/tablet/mobile viewport where applicable, Playwright/screenshot proof, console/runtime validation.

**Thin MVP:** Playwright screenshot endpoint → cockpit preview panel. Console log capture → cockpit display. Browser health check → pass/fail badge.

**Post-MVP:** Live iframe preview, responsive viewport switching, visual regression testing, automated screenshot diffing.

**Current state:** SCAFFOLD — browser_agent.py (494 LOC), computer_use.py endpoint (container start/stop), governed_browser_adapter, Playwright infrastructure; NOT surfaced in cockpit.

**Blockers:**

| Blocker | Status |
|---------|--------|
| Screenshot capture → cockpit panel | PARTIAL — Playwright exists, no cockpit rendering |
| Console log capture | PARTIAL — execution logs exist, no browser console capture in cockpit |
| Health check badge | MISSING |

---

### Pillar 10: Governance

**MVP functional requirement:** Safe work continues; risky/destructive/external/financial/security/legal actions require approval; unknown mutating actions fail closed.

**Thin MVP:** Already implemented — ExecutionAuthorityEngine, risk classification, approval gates, destructive data actions escalated (d728b0e2).

**Post-MVP:** Governance analytics dashboard, risk trend visualization, policy editor UI.

**Current state:** COMPLETE — 62 tests, AC-6 7/7, DESTRUCTIVE_DATA_ACTIONS frozenset, approval workflows through cockpit + Discord.

**Blockers:** None for MVP.

---

### Pillar 11: Memory/World/Context Visibility

**MVP functional requirement:** Trace, memory candidate, canonical memory, world facts, confidence, source, timestamp, contradictions, resume state.

**Thin MVP:** Memory panel (search + browse), world model panel (fact list with confidence/source), trace timeline, resume state widget in dashboard.

**Post-MVP:** Memory promotion pipeline visualization, contradiction resolution UI, memory graph explorer, 12-layer reality model rendered per DEC-146C-001.

**Current state:** PARTIAL — ConversationMemory + AgentMemory (semantic search), WorldModelPanel (27K LOC, largest panel), KnowledgePanel (13.7K LOC), reality model APIs, execution trace. NO memory browsing panel, NO gap/acquisition path visualization, NO resume state widget.

**Blockers:**

| Blocker | Status |
|---------|--------|
| Memory browsing/search panel | MISSING in cockpit |
| World model fact display (confidence, source, timestamp) | PARTIAL — WorldModelPanel exists, unclear if structured per spec |
| Trace timeline | PARTIAL — ExecutionPanel exists, needs timeline rendering |
| Resume state widget | MISSING |
| Contradiction detection | MISSING |

---

### Pillar 12: Infrastructure Self-Awareness

**MVP functional requirement:** VPS, Windows workstation, mobile, Tailscale mesh, containers, tmux/sessions, runtime services, adapter health, model availability.

**Thin MVP:** InfrastructurePanel shows VPS + containers + mesh nodes + model availability. Node mesh heartbeats surface Windows Beast status. Docker socket provides container health.

**Post-MVP:** Topology map with live latency, automated failover visualization, cost-per-node tracking.

**Current state:** PARTIAL — InfrastructurePanel (7.8K LOC), TopologyMap, node mesh server/client, Docker socket RO mount, model_router fallback chain observable, Tailscale peer visibility. NO unified cross-node dashboard, NO live container log streaming, NO model availability dashboard.

**Blockers:**

| Blocker | Status |
|---------|--------|
| Unified cross-node dashboard | MISSING |
| Live container log streaming | MISSING |
| Model availability display | PARTIAL — error_recorder tracks failures, no cockpit surface |

---

### Pillar 13: cortextOS Stance

**MVP functional requirement:** Use cortextOS as grounded pattern source for persistent agents, task bus, approvals, dashboard taxonomy, crons, skills, runtime adapters, and mobile control. Do not import unsafe permission defaults. UMH governance remains authoritative.

**Thin MVP:** Evaluate cortextOS patterns during implementation; adopt architecture patterns (task bus, persistent agent registry, approval queue, cron scheduling) that map to existing UMH infrastructure. Document mappings. No code import — pattern adoption only.

**Post-MVP:** Deeper integration where patterns prove superior to current UMH implementation.

**Current state:** N/A — cortextOS is a reference, not implemented code. Pattern evaluation is a design-time activity.

**Blockers:** None — this is a design stance, not a build item.

---

## Stage 2 Gate Reclassification

| ID | Original | New | Rationale |
|----|----------|-----|-----------|
| S2-A1 | production-blocking | **COMPLETE** | 50/50 PASS sealed |
| S2-A2 | operational | **required for MVP** | Clean test suite is MVP baseline |
| S2-A3 | operational | **required for MVP** | Template seeding feeds autonomous cadence |
| S2-A4 | operational | **required for MVP** | cockpit.py headroom management |
| S2-B1 | production-blocking | **COMPLETE** | Sealed |
| S2-B2–B5 | various | deferred/post-MVP | EOS-specific gate conditions |
| S2-B6 | deferred | **required for MVP** | Cockpit coordination IS the workstation |
| S2-C1–C8 | operational/UX | **required for MVP** | Phase 10.0 operational hardening — cadence must work E2E |
| S2-D1 | production-blocking | **required for MVP** | Reality model needs real data |
| S2-D2–D4 | architecture/operational | deferred/post-MVP | EOS-specific or post-MVP |

**Summary: 2 COMPLETE, 14 required for MVP, 5 deferred (all EOS/projection-specific)**

---

## Why Projection Gates Are Deferred

- Stage 1 built the governed organism spine. The highest-leverage move is to build the first usable Jarvis Workstation that can command, observe, govern, resume, and help build the rest of the system.
- Projection gates assume a functional workstation — but the workstation can't yet: detect operator presence, maintain continuity across absence, translate natural commands, show its own tmux sessions, pause agents, or render overnight summaries.
- The workstation must be the operator's daily driver FIRST.
- EOS/CreatorOS/LyfeOS are not the immediate MVP — they are domain surfaces that come after the universal cockpit is usable enough.
- Stop expanding the architecture. Stop drifting into projections. Stop treating Stage 2 as generic. Lock the UMH/Jarvis Workstation MVP. Extract blockers. Build the thinnest complete Jarvis loop. Use that workstation to build the rest. That is maximum leverage under governance.

---

## MVP Inclusions (explicitly IN scope)

- Phase 10.0 operational hardening (all 8 items: S2-C1–C8)
- Stale test cleanup (S2-A2) + template seeding (S2-A3)
- Reality model data seeding (S2-D1)
- Full-Screen Command Center + Floating Overlay presence states
- Workspace + Network awareness tiers (partial Embodied, Cloud, Learning)
- All system lifecycle and profile/work modes (dual taxonomy)
- cortextOS patterns under UMH governance
- Presence + perception + continuity architecture with first functional hooks
- Dead workstation code triage (26,671 LOC)

## MVP Exclusions (explicitly OUT of scope)

- EOS/CreatorOS/LyfeOS projection implementation
- Clerk SDK, schema migrations, Fly.io deployment
- Full VS Code fork
- Trained wake word model (architecture + first hook only)
- Computer vision inference (screenshot capture only for MVP)
- Proactive phone alerting
- Voice-Wave Ambient Mode, Ghost Mode
- Global awareness tier (market signals, competitor intel)
- Cross-device seamless handoff (Discord bridge covers remote for MVP)
- Recovery/rollback mechanism

---

## Minimum Build Sequence

**Stream A: Execution Control Wiring** (FIRST — unblocks everything)
- Wire pause/resume/abort to actual agent interruption

**Stream B: Voice-First Command Translation** (parallel with C–F)
- Cockpit voice input E2E + natural command → intent mapping

**Stream C: Eyes/Perception Hooks** (parallel)
- Tmux state capture, repo/runtime observation, idle timer, Playwright screenshot → cockpit, camera/mic architecture

**Stream D: Meta IDE / Organism Workspace** (parallel)
- File browser, terminal panel, diff viewer, test results, log stream, unified layout

**Stream E: Continuity State Machine + Presence** (parallel)
- State machine (Active → Idle → Away → ... → Return → Resume), absence detection, resume brief, hotkey activation

**Stream F: Memory + World Model + Infrastructure Panels** (parallel)
- Memory search panel, world model fact display, infrastructure dashboard, cross-node view

**Stream G: Lifecycle Mode Wiring + Overnight + Morning Brief** (depends on A, E)
- Dual mode taxonomy, mode resolver, overnight safe-work queue, morning brief

**Stream H: Autonomous Cadence E2E + Phase 10.0** (depends on A)
- Template seeding → governance → candidate supply → cadence → cockpit → PR preview → browser verification

**Stream I: App Preview + Projection Proof** (depends on D)
- Playwright screenshot → cockpit panel, console capture, health badge

**Dependency structure:**
A → (B+C+D+E+F parallel) → (G+H+I parallel)
3 sequential phases, estimated 24–36 work packets.

---

## Required Proof Artifacts

- Voice natural command demo (conversational intent → governed execution → response)
- Execution control demo (pause/resume interrupts running agent)
- Meta IDE screenshot (unified workspace: files, sessions, agents, diffs, tests, logs)
- Tmux panel screenshot (live tmux in cockpit without SSH)
- Leave/return simulation (operator leaves → absence detected → return → resume brief)
- Overnight simulation (end-of-workday → night cycle → safe work → morning brief)
- Wake/clap activation proof (activation signal → presence → mode → cockpit)
- Screen awareness proof (terminal/session state observed, repo state loaded)
- AFK detection proof (idle timeout → Away state → safe-mode operations)
- Resume summary proof (structured brief on return from any absence horizon)
- Approval pause/resume proof (high-risk blocked during absence → surfaced on return)
- Memory search demo (semantic search in cockpit panel)
- Autonomous cadence demo (template → candidate → tick → cockpit → PR preview)
- Mode switching demo (lifecycle + profile mode change reflected in workspace)
- App preview demo (Playwright screenshot rendered in cockpit)
- Full loop demo (voice → packet → agent → result → approval → outcome → memory → resume)
- Regression pass (50/50 AC + 324/324)

---

## GO / PARTIAL GO / NO-GO

| Factor | Score |
|--------|-------|
| Stage 1 completeness | PASS |
| Cockpit foundation (27 panels, ~210 endpoints) | PASS |
| Voice infrastructure | PASS (E2E verification + natural command abstraction is the task) |
| Governance | PASS (complete — 62 tests, AC-6 7/7) |
| Execution control | PARTIAL (stubs exist, wiring required — highest severity) |
| Meta IDE foundation | PARTIAL (EditorPanel + tmux adapter exist, workspace is the task) |
| Autonomous cadence engines | PASS (template registry, candidate supply, cadence exist) |
| Memory/world model backend | PASS (APIs exist, cockpit panels needed) |
| Infrastructure visibility | PARTIAL (InfrastructurePanel + node mesh exist, unified dashboard needed) |
| Continuity state machine | FAIL (net-new — no absence detection, no state transitions) |
| Presence activation (wake/clap/hotkey) | FAIL (net-new for wake/clap; Electron hotkey achievable) |
| Screen/workspace awareness | SCAFFOLD (Playwright + tmux exist, no perception pipeline) |
| AFK/idle detection | FAIL (net-new — no keyboard/mouse monitoring) |
| Camera/mic signal path | FAIL (architecture undefined — mic via Discord partial) |
| Dual mode taxonomy | PARTIAL (workstation modes exist, not the full dual taxonomy) |
| Dead code risk (26,671 LOC) | CAUTION |
| cockpit.py headroom (348 lines) | CAUTION |

**Determination: PARTIAL GO** — strong infrastructure foundation (cockpit, organism, voice, governance, cadence all exist). 4 FAIL items are thin MVP builds (continuity state machine, activation triggers, AFK detection, camera/mic path) — architecture + first hooks, not full systems. Critical path is integration, wiring, and perception hooks. The workstation MVP is achievable by composing existing subsystems into a coherent operator experience.

---

## Verdict

**GATE 1 LOCKED.** The canonical MVP is the UMH/Jarvis Workstation. Projection gates are deferred. The next gate is blocker extraction (Gate 2), followed by thin vertical slice implementation (Gate 3), followed by MVP seal (Gate 4).
