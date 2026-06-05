# Phase 14.10B — UMH/Jarvis Workstation MVP Blocker Dependency Graph + First Slice Plan

**Date:** 2026-06-05
**Phase:** 14.10B (Gate 2 — Blocker Extraction + First Slice)
**Status:** GATE_2_LOCKED
**Canonical main:** 9909fd0b (safe-forward from a1a2dde3)
**Stage 1 sealed:** true
**Provenance:** CODEBASE_VERIFIED_GATE_2
**Gate 1 reference:** phase14_10a_umh_jarvis_mvp_plan_realignment.md

---

## 1. Canonical MVP Reminder

Gate 1 (Phase 14.10A) locked the UMH/Jarvis Workstation MVP: a voice-first, governed, multi-environment operator cockpit that maintains continuity across absence, coordinates agents/tasks/work packets, surfaces approvals/traces/proof, and helps build software under governance. 13 pillars defined. Governance (Pillar 10) COMPLETE. All others PARTIAL or FAIL. Projection gates deferred.

---

## 2. Blocker Inventory by Pillar

### Tier Definitions

- **FIRST-SLICE** — must work for first live Jarvis vertical demo
- **MVP-CRITICAL** — must work for full MVP seal, not first demo
- **THIN-MVP-HOOK** — architecture defined + first hook only
- **HARDENING** — quality/reliability improvement
- **POST-MVP** — out of scope for MVP

### Pillar 1: Presence and Activation

| ID | Blocker | Tier | Evidence |
|----|---------|------|----------|
| P1-1 | Wake word detection | POST-MVP | No architecture; requires trained model |
| P1-2 | Clap/sound gesture | POST-MVP | No audio analysis path defined |
| P1-3 | Hotkey activation | THIN-MVP-HOOK | CommandPalette.tsx has Ctrl+K; no global Electron shortcut |
| P1-4 | Manual cockpit open | COMPLETE | Works |
| P1-5 | Typed command | COMPLETE | CommandPalette.tsx:23-45, 22 hardcoded commands |
| P1-6 | Mobile/remote command | COMPLETE | Discord text works; sufficient for first slice |

### Pillar 2: Voice-First Command Translation

| ID | Blocker | Tier | Evidence |
|----|---------|------|----------|
| P2-1 | Cockpit voice E2E | THIN-MVP-HOOK | VoiceCommandBar.tsx (413 LOC), voice.py (95 LOC) exist; E2E unverified |
| P2-2 | Natural command → intent → packet | FIRST-SLICE | intent_classifier.py (324 LOC), 17 domains, 14 work types, regex-only; NOT connected to CommandPalette |
| P2-3 | Governance gate on voice | COMPLETE | All routes through ExecutionAuthorityEngine |
| P2-4 | TTS response path | THIN-MVP-HOOK | Works via Discord; cockpit path unverified |

### Pillar 3: Eyes/Perception

| ID | Blocker | Tier | Evidence |
|----|---------|------|----------|
| P3-1 | Active window/app detection | POST-MVP | No xdotool/wmctrl integration |
| P3-2 | Terminal/session observation | FIRST-SLICE | tmux.py (137 LOC) has list_sessions, list_windows, inspect, capture_pane; tmux_operational_adapter_v1.py (265 LOC); NO cockpit endpoint or panel |
| P3-3 | Repo/runtime state surface | FIRST-SLICE | git status via shell, container health via Docker socket at cockpit.py:153-187; not surfaced in dashboard |
| P3-4 | Visual proof (screenshots) | MVP-CRITICAL | browser_agent.py + Playwright exist; no cockpit API endpoint |
| P3-5 | Idle/away detection | THIN-MVP-HOOK | No keyboard/mouse monitoring; no idle timer |
| P3-6 | Camera/mic signal path | POST-MVP | Architecture undefined; mic partial via Discord |

### Pillar 4: Continuity Across Absence

| ID | Blocker | Tier | Evidence |
|----|---------|------|----------|
| P4-1 | Continuity state machine | MVP-CRITICAL | 4 independent systems: OperatorMode (operator_state.py:71-87, 6 states), OperatorDayMode (operator_session.py:57-74, 5 states), StationPresenceMode (station_presence.py:56-65, 5 states), OperationalMode (workstation_operational_modes_v1.py:62-67, 4 modes); NO unified arbiter |
| P4-2 | Absence detection (idle timer) | THIN-MVP-HOOK | No heartbeat timeout; no keyboard/mouse monitoring |
| P4-3 | State checkpoint on transition | MVP-CRITICAL | WorkstationContinuityBridge generates resume_state.json; not triggered by absence transitions |
| P4-4 | Resume brief cockpit endpoint | FIRST-SLICE | WorkstationContinuityBridge at workstation_continuity_bridge_v1.py:234-299 generates resume_state with active_goals, suggested_next_actions, last_command, last_outcome, open_loops; NEVER exposed via API or surfaced in cockpit |
| P4-5 | Overnight safe-work queue | MVP-CRITICAL | AutonomousTick has pause/resume (autonomous_tick.py:140-152); OVERNIGHT_SAFE_MODE defined; not wired together |

### Pillar 5: Dual Mode Taxonomy

| ID | Blocker | Tier | Evidence |
|----|---------|------|----------|
| P5-1 | Full lifecycle mode enum | MVP-CRITICAL | OperatorDayMode has 5 states; missing EMERGENCY, MAINTENANCE, END_OF_WORKDAY |
| P5-2 | Full profile/work mode enum | MVP-CRITICAL | OperationalMode has 4 modes (DEVELOPER/RESEARCH/AUDIT/OVERNIGHT_SAFE); missing MUSIC/DESIGN/CONTENT/COMMAND_CENTER/FINANCE/LEARNING |
| P5-3 | Mode resolver (dual composition) | FIRST-SLICE | NO code resolves lifecycle + profile simultaneously; 4 independent mode systems with no arbiter |
| P5-4 | Cockpit mode display | FIRST-SLICE | HudBar.tsx:51 shows EXECUTE/PLAN/REVIEW (cockpit UI modes, NOT workstation modes); NO session state |
| P5-5 | Mode switching via command | MVP-CRITICAL | workstation PATCH /mode changes OperationalMode; not connected to voice or CommandPalette |

### Pillar 6: Cockpit Command Center

| ID | Blocker | Tier | Evidence |
|----|---------|------|----------|
| P6-1 | Dashboard resume widget | FIRST-SLICE | DashboardPanel.tsx (352 LOC) has System Pulse, Organism Status, Runtimes, Executions, Bottlenecks, Approvals, Infrastructure, Workloads; NO resume context, NO next action |
| P6-2 | Tmux session panel | FIRST-SLICE | tmux.py + tmux_operational_adapter_v1.py functional backend; NO cockpit endpoint, NO panel component |
| P6-3 | Real-time log streaming | MVP-CRITICAL | Execution logs exist; WebSocket sends pulse events; no execution log streaming |
| P6-4 | Degraded mode UI | HARDENING | ConnectionBanner exists; no full degraded fallback |
| P6-5 | cockpit.py headroom | CONSTRAINT | 2,652/3,000 lines (348 headroom); new routes MUST go in separate files (13 existing cockpit_*_routes.py) |

### Pillar 7: Agent/Task/Work-Packet Control

| ID | Blocker | Tier | Evidence |
|----|---------|------|----------|
| P7-1 | Execution control wiring | FIRST-SLICE | cockpit.py:2141 (pause→BLOCKED), :2241 (resume→CLASSIFIED), :2130 (stop→BLOCKED) are STUBS — update state only, never call runtime adapters; RuntimeAdapter base has stop() but NO pause(); ShellRuntimeAdapter.stop() at :305-340 does SIGTERM/SIGKILL; cockpit never calls it |
| P7-2 | PAUSED lifecycle state | FIRST-SLICE | PacketLifecycleStatus (work_packet.py:28-45) has 16 states, NO PAUSED; pause maps to BLOCKED which is terminal-adjacent requiring restart from CLASSIFIED |
| P7-3 | Agent persistence visibility | MVP-CRITICAL | Workcell heartbeats exist; no persistent agent registry UI |
| P7-4 | Task dependency view | POST-MVP | Coordinator tracks DAG; no visual component |

### Pillar 8: Meta IDE

| ID | Blocker | Tier | Evidence |
|----|---------|------|----------|
| P8-1 | File browser (tree view) | MVP-CRITICAL | EditorPanel.tsx exists (read-only); no tree navigation |
| P8-2 | Terminal panel (tmux) | FIRST-SLICE | Same as P6-2; tmux adapter exists, no panel |
| P8-3 | Diff viewer | MVP-CRITICAL | No component |
| P8-4 | Test results panel | MVP-CRITICAL | Test execution exists; no cockpit surface |
| P8-5 | Log stream | MVP-CRITICAL | Same as P6-3 |
| P8-6 | Unified workspace layout | MVP-CRITICAL | 27 panels exist; no IDE-like composition |

### Pillar 9: App Preview / Projection Proof

| ID | Blocker | Tier | Evidence |
|----|---------|------|----------|
| P9-1 | Screenshot capture to cockpit | THIN-MVP-HOOK | browser_agent.py + Playwright + computer_use.py exist; no cockpit rendering endpoint |
| P9-2 | Console log capture | MVP-CRITICAL | Execution logs exist; no browser console capture |
| P9-3 | Health check badge | MVP-CRITICAL | No component |

### Pillar 10: Governance

**COMPLETE.** No blockers. ExecutionAuthorityEngine, 62 tests, AC-6 7/7, DESTRUCTIVE_DATA_ACTIONS frozenset.

### Pillar 11: Memory/World/Context Visibility

| ID | Blocker | Tier | Evidence |
|----|---------|------|----------|
| P11-1 | Memory browsing/search panel | MVP-CRITICAL | ConversationMemory + AgentMemory backends exist; no cockpit search panel |
| P11-2 | World model fact display | MVP-CRITICAL | WorldModelPanel.tsx (649 LOC) exists; structured fact display unclear |
| P11-3 | Trace timeline | FIRST-SLICE | ExecutionPanel.tsx (132 LOC) is read-only; needs execution history timeline |
| P11-4 | Resume state widget | FIRST-SLICE | Same as P6-1; WorkstationContinuityBridge generates resume_state.json; never surfaced |
| P11-5 | Contradiction detection | POST-MVP | No implementation |

### Pillar 12: Infrastructure Self-Awareness

| ID | Blocker | Tier | Evidence |
|----|---------|------|----------|
| P12-1 | Unified cross-node dashboard | MVP-CRITICAL | InfrastructurePanel.tsx (157 LOC) + node mesh exist; no unified view |
| P12-2 | Live container log streaming | MVP-CRITICAL | Docker socket RO mount exists; no log stream |
| P12-3 | Model availability display | MVP-CRITICAL | error_recorder tracks failures; no cockpit surface |

### Pillar 13: cortextOS Stance

**No blockers.** Design-time pattern reference only.

---

### Blocker Counts by Tier

| Tier | Count |
|------|-------|
| FIRST-SLICE | 12 |
| MVP-CRITICAL | 20 |
| THIN-MVP-HOOK | 5 |
| HARDENING | 1 |
| POST-MVP | 14 |
| COMPLETE | 5 |
| CONSTRAINT | 1 |
| **Total** | **58** |

---

## 3. Blocker Dependency Graph

```
LEGEND: [FS] = First-Slice    [MC] = MVP-Critical    [TH] = Thin-MVP-Hook
        ───> = "must precede"
        (Pn-m) = blocker ID from section 2

                    ┌──────────────────────────────────────────────────┐
                    │           EXECUTION CONTROL SPINE                │
                    │                                                  │
                    │  P7-2 Add PAUSED state ──────> P7-1 Wire        │
                    │  to PacketLifecycleStatus      pause/resume/     │
                    │  [FS] (zero deps)              abort to runtime  │
                    │                                adapters [FS]     │
                    └──────────────┬──────────────────────┬────────────┘
                                   │                      │
                     ┌─────────────┼──────────────────────┼────────────┐
                     │             v                      v            │
                     │  ┌──────────────────┐  ┌──────────────────────┐ │
                     │  │ P5-3 Mode        │  │ P2-2 Natural command │ │
                     │  │ resolver (dual   │  │ → intent → work     │ │
                     │  │ lifecycle +      │  │ packet creation [FS] │ │
                     │  │ profile) [FS]    │  │                      │ │
                     │  └────────┬─────────┘  └──────────┬───────────┘ │
                     │           │                       │             │
                     │           v                       v             │
                     │  ┌──────────────────┐  ┌──────────────────────┐ │
                     │  │ P5-4 HudBar mode │  │ P6-1 Dashboard      │ │
                     │  │ display [FS]     │  │ resume widget [FS]  │ │
                     │  └────────┬─────────┘  └──────────┬───────────┘ │
                     │           │                       │             │
                     └───────────┼───────────────────────┼─────────────┘
                                 │                       │
                  PARALLEL ──────┼───────────────────────┼──────── PARALLEL
                                 │                       │
              ┌──────────────────┼───────────────────────┼──────────────────┐
              │                  v                       v                  │
              │  ┌──────────────────────────────────────────────────────┐   │
              │  │ P6-2/P3-2/P8-2 Tmux panel + observation [FS]       │   │
              │  │ P3-3 Repo/runtime state surface [FS]                │   │
              │  │ P4-4 Resume brief endpoint [FS]                     │   │
              │  └──────────────────────┬───────────────────────────────┘   │
              │                         │                                   │
              │                         v                                   │
              │  ┌──────────────────────────────────────────────────────┐   │
              │  │ P11-3 Trace timeline [FS]                           │   │
              │  └──────────────────────┬───────────────────────────────┘   │
              │                         │                                   │
              └─────────────────────────┼───────────────────────────────────┘
                                        │
                                        v
                               ┌─────────────────┐
                               │ FIRST SLICE DEMO │
                               └─────────────────┘


CRITICAL PATH (sequential):

  P7-2 ──> P7-1 ──> P2-2 ──> E2E LOOP PROOF

PARALLEL with critical path (no dependency on execution control):

  P5-3 (mode resolver)           ── can start immediately
  P5-4 (HudBar mode display)     ── depends on P5-3
  P6-1 (resume widget)           ── depends on P4-4 endpoint
  P4-4 (resume endpoint)         ── can start immediately
  P6-2/P3-2/P8-2 (tmux panel)   ── can start immediately
  P3-3 (repo/runtime surface)    ── can start immediately
  P11-3 (trace timeline)         ── can start immediately


MVP-CRITICAL SECOND WAVE (depends on first slice):

  P4-1 (continuity state machine)  ── depends on P5-3 mode resolver
  P4-3 (checkpoint on transition)  ── depends on P4-1
  P4-5 (overnight queue)           ── depends on P4-1 + P7-1
  P5-1 (full lifecycle enum)       ── depends on P5-3 proving pattern
  P5-2 (full profile enum)         ── depends on P5-3 proving pattern
  P5-5 (mode switching)            ── depends on P5-3 + P2-2
  P8-1/P8-3/P8-4/P8-5/P8-6       ── Meta IDE builds on first slice
```

---

## 4. First-Slice Blocker List

These 12 blockers must be resolved for the first live Jarvis vertical demo. The demo proves: **command → load state → resolve mode → show visibility → create/resume work packet → route → pause/approval gate → execute → trace/proof → resume brief.**

| ID | Blocker | Current State | Required Change | Files |
|----|---------|---------------|-----------------|-------|
| P7-2 | PAUSED lifecycle state | 16 states, no PAUSED | Add `PAUSED = "paused"` + transitions: EXECUTING→PAUSED, PAUSED→{EXECUTING, BLOCKED, FAILED, ARCHIVED} | `substrate/organism/work_packet.py` |
| P7-1 | Execution control wiring | Stubs update state only | Wire pause→SIGSTOP+PAUSED, resume→SIGCONT+EXECUTING, stop→adapter.stop(); add abstract pause()/resume() to RuntimeAdapter; implement SIGSTOP/SIGCONT in ShellRuntimeAdapter | `transports/api/cockpit_workstation_control_routes.py` (NEW), `substrate/organism/runtime_adapter.py`, `substrate/organism/shell_runtime_adapter.py`, `substrate/organism/claude_code_runtime_adapter.py` |
| P2-2 | Natural command → intent → packet | IntentClassifier exists but NOT connected to CommandPalette | Add natural-language fallback in CommandPalette: when no hardcoded match, POST to /api/umh/intent/classify, offer "Create Work Packet" from result | `cockpit/src/renderer/components/CommandPalette.tsx`, `substrate/organism/intent_classifier.py` (add classify_to_work_packet_draft) |
| P5-3 | Mode resolver (dual composition) | 4 independent mode systems | Create WorkstationModeResolver that reads OperatorDayMode + OperationalMode → composite record; no new enums | NEW: `substrate/workstation/mode_resolver.py` |
| P5-4 | HudBar mode display | Shows EXECUTE/PLAN/REVIEW only | Add lifecycle mode + profile mode badges from /api/umh/workstation/mode-composite | `cockpit/src/renderer/components/HudBar.tsx` |
| P6-1 | Dashboard resume widget | No resume context in dashboard | Add ResumeWidget: last command, outcome, active goals, next actions, open loops | `cockpit/src/renderer/panels/DashboardPanel.tsx` |
| P4-4 | Resume brief endpoint | Generated but never exposed | Add GET /api/umh/workstation/resume serving WorkstationContinuityBridge.load_resume_state() | NEW: `transports/api/cockpit_workstation_control_routes.py` |
| P6-2 | Tmux session panel | Backend functional, no cockpit exposure | Add GET /api/umh/tmux/sessions, GET /api/umh/tmux/capture/{session}/{pane}; add TmuxPanel.tsx | NEW: `transports/api/cockpit_workstation_control_routes.py`, NEW: `cockpit/src/renderer/panels/TmuxPanel.tsx` |
| P3-2 | Terminal/session observation | Same backend as P6-2 | Wire tmux capture into cockpit via P6-2 endpoints | Same as P6-2 |
| P3-3 | Repo/runtime state surface | git status + Docker health not in dashboard | Add workspace state widget: git branch, last commit, container health | `cockpit/src/renderer/panels/DashboardPanel.tsx` or new widget |
| P11-3 | Trace timeline | ExecutionPanel is read-only | Add chronological trace history view with status, duration, outcome | `cockpit/src/renderer/panels/ExecutionPanel.tsx` |
| P8-2 | Terminal panel (tmux embedding) | Same as P6-2 | TmuxPanel with pane capture output rendering | Same as P6-2 |

**Effective work packets: ~8-10** (P6-2/P3-2/P8-2 merge; P6-1/P11-4 merge; P4-4 in same route file as P7-1)

---

## 5. MVP-Critical But Not First-Slice

| ID | Blocker | Why Not First-Slice | Depends On |
|----|---------|---------------------|------------|
| P4-1 | Continuity state machine (unified arbiter) | First demo shows current mode pair; arbiter needed for absence transitions | P5-3 |
| P4-3 | State checkpoint on transition | First demo shows manual resume; auto-checkpoint needs arbiter | P4-1 |
| P4-5 | Overnight safe-work queue | First demo is active session | P4-1 + P7-1 |
| P5-1 | Full lifecycle mode enum | First demo proves dual taxonomy with existing enums | P5-3 |
| P5-2 | Full profile/work mode enum | Existing 4 OperationalModes cover developer demo | P5-3 |
| P5-5 | Mode switching via voice/command | First demo shows current mode; switching is refinement | P5-3 + P2-2 |
| P6-3 | Real-time log streaming | First demo shows cached logs | WebSocket extension |
| P7-3 | Agent persistence visibility | First demo shows active agents | Standalone |
| P8-1 | File browser (tree view) | Terminal panel covers first demo | Standalone |
| P8-3 | Diff viewer | Not in first demo loop | Standalone |
| P8-4 | Test results panel | Not in first demo loop | Standalone |
| P8-5 | Log stream panel | Same as P6-3 | WebSocket extension |
| P8-6 | Unified workspace layout | First demo uses panel navigation | P8-1..P8-5 |
| P3-4 | Screenshot capture API | Screenshot is thin hook; API is MVP | P9-1 |
| P9-2 | Console log capture | Deeper than screenshot | P9-1 |
| P9-3 | Health check badge | Visual indicator | Standalone |
| P11-1 | Memory browsing/search panel | First demo proves trace; memory is knowledge | Standalone |
| P11-2 | World model fact display | WorldModelPanel exists; structured is refinement | Standalone |
| P12-1 | Unified cross-node dashboard | InfrastructurePanel exists | Standalone |
| P12-2 | Live container log streaming | Docker socket exists; streaming is quality | WebSocket |
| P12-3 | Model availability display | error_recorder exists; needs surface | Standalone |

---

## 6. Thin MVP Hooks

Architecture + first hook only. Not full implementation.

| ID | Blocker | Hook | First Implementation |
|----|---------|------|---------------------|
| P1-3 | Hotkey activation | Electron globalShortcut | Register Super+J in main process → bring cockpit to focus |
| P2-1 | Voice E2E verification | Whisper→VoiceCommandBar→intent→response→TTS | Manual E2E test run; verify transcript + classify + TTS |
| P2-4 | TTS response path | Kokoro at Beast:8880 → cockpit audio | Verify reachable; add AudioContext playback |
| P3-5 | Idle/away detection | Last-input timestamp → idle threshold | Record last interaction; fire event on threshold; surface in operator state |
| P9-1 | Screenshot proof | Playwright→base64→API→panel | POST /api/umh/screenshot endpoint; render in cockpit |

---

## 7. Post-MVP Exclusions

| ID | Exclusion | Reason |
|----|-----------|--------|
| P1-1 | Trained wake word model | Requires ML pipeline |
| P1-2 | Clap/gesture recognition | Requires audio model |
| P3-1 | Active window/app detection | Requires X11/Wayland integration |
| P3-6 | Camera/mic (full) | Architecture undefined |
| P7-4 | Task dependency graph visual | Post-MVP UX |
| P11-5 | Contradiction detection | Requires world model maturity |
| -- | Voice-Wave Ambient Mode | End-state feature |
| -- | Ghost Mode | End-state feature |
| -- | Full VS Code fork | End-state; Meta IDE is thin path |
| -- | Global awareness | Beyond operator cockpit |
| -- | Cross-device seamless handoff | Discord covers remote |
| -- | Computer vision inference | Screenshot only for MVP |
| -- | Proactive phone alerting | Post-MVP notification |
| -- | EOS/CreatorOS/LyfeOS gates | Deferred per Gate 1 |

---

## 8. Recommended First Implementation Phase

**Phase 14.11A — Workstation Control Spine + Resume Slice**

**Scope:** The minimum changes that produce a live end-to-end Jarvis workstation demo loop.

**Why "Control Spine":** Execution control wiring (P7-1, P7-2) is the foundational dependency. Without real pause/resume/abort, the cockpit is a read-only dashboard pretending to be a workstation. You cannot let the system work while you sleep if it cannot actually pause.

**Why "Resume Slice":** The operator's essential truth — "Jarvis should remain oriented and resume with me" — is proven by surfacing the resume state that already exists but is invisible in the cockpit.

**Why this order:**
1. P7-2 (PAUSED state) has zero dependencies → first commit
2. P7-1 (execution wiring) depends only on P7-2 → second commit
3. P5-3 + P5-4 (mode resolver + HudBar) can proceed in parallel
4. P4-4 + P6-1 (resume endpoint + widget) can proceed in parallel
5. P6-2/P3-2/P8-2 (tmux panel) can proceed in parallel
6. P2-2 (natural command path) can proceed in parallel
7. P11-3 (trace timeline) depends on traces from execution → last

**What this phase does NOT attempt:**
- Full continuity state machine (P4-1) — that's MVP-critical second wave
- Full dual taxonomy enum expansion (P5-1, P5-2) — second wave
- Meta IDE workspace composition (P8-6) — second wave
- Voice E2E (P2-1) — thin hook tier
- Idle detection (P3-5) — thin hook tier

**Estimated work packets:** 8-10

---

## 9. Exact First Implementation Scope

### Backend (Python) — 5 files modified, 2 new

**NEW: `transports/api/cockpit_workstation_control_routes.py`** (~200 LOC)
- Follows existing pattern (13 cockpit_*_routes.py files)
- Routes:
  - `POST /api/umh/execution/pause` — replace stub; call adapter, set PAUSED
  - `POST /api/umh/execution/resume` — replace stub; call adapter, set EXECUTING
  - `POST /api/umh/execution/stop` — replace stub; call adapter.stop()
  - `GET /api/umh/workstation/resume` — serve ContinuityBridge resume state
  - `GET /api/umh/workstation/mode-composite` — serve ModeResolver output
  - `GET /api/umh/tmux/sessions` — proxy tmux.py list_sessions
  - `GET /api/umh/tmux/capture/{session}/{pane}` — proxy tmux.py capture_pane

**MODIFY: `substrate/organism/work_packet.py`**
- Add `PAUSED = "paused"` to PacketLifecycleStatus (~line 44)
- Add to `_VALID_TRANSITIONS` (~line 55):
  - EXECUTING → add PAUSED to existing frozenset
  - PAUSED → frozenset({EXECUTING, BLOCKED, FAILED, ARCHIVED})

**MODIFY: `substrate/organism/runtime_adapter.py`**
- Add abstract `pause(self, session_id: str, reason: str = "") -> dict` (after line 83)
- Add abstract `resume(self, session_id: str) -> dict` (after pause)

**MODIFY: `substrate/organism/shell_runtime_adapter.py`**
- Implement `pause()` using `os.kill(proc.pid, signal.SIGSTOP)` (~15 LOC)
- Implement `resume()` using `os.kill(proc.pid, signal.SIGCONT)` (~15 LOC)
- Add `_paused_sessions: set[str]` tracking

**MODIFY: `substrate/organism/claude_code_runtime_adapter.py`**
- Implement `pause()` and `resume()` — minimum: raise NotImplementedError with clear message

**NEW: `substrate/workstation/mode_resolver.py`** (~100 LOC)
- WorkstationModeResolver class
- Reads OperatorDayMode from operator_session.py
- Reads OperationalMode from workstation state
- Returns composite: `{ lifecycle_mode: str, profile_mode: str, constraints: dict }`
- No new enums — uses existing types

**MODIFY: `substrate/organism/intent_classifier.py`**
- Add `classify_to_work_packet_draft()` (~30 LOC) — takes classification, returns WorkPacket draft with domain, subdomain, work_type, title, user_intent

### Frontend (TypeScript/React) — 5 files modified, 1 new

**NEW: `cockpit/src/renderer/panels/TmuxPanel.tsx`** (~250 LOC)
- Fetches /api/umh/tmux/sessions on interval
- Session list with expandable pane capture
- Follows existing panel patterns

**MODIFY: `cockpit/src/renderer/panels/DashboardPanel.tsx`**
- Add ResumeWidget section (~60 LOC): last command, outcome, active goals, next actions, open loops
- Add workspace state widget (~40 LOC): git branch, last commit, container health

**MODIFY: `cockpit/src/renderer/components/HudBar.tsx`**
- Add lifecycle + profile mode badges (~20 LOC) from /api/umh/workstation/mode-composite

**MODIFY: `cockpit/src/renderer/components/CommandPalette.tsx`**
- Add natural-language fallback (~40 LOC): when no hardcoded match, POST to /api/umh/intent/classify, show classification, offer "Create Work Packet"

**MODIFY: `cockpit/src/renderer/panels/ExecutionPanel.tsx`**
- Add trace timeline section (~50 LOC): chronological history with status, duration, outcome

**MODIFY: `cockpit/src/renderer/stores/cockpitStore.ts`**
- Add TmuxPanel to Panel type union + navigation

### Route Registration

**MODIFY: cockpit.py or app.py**
- Register cockpit_workstation_control_routes router
- Remove/deprecate stubs at cockpit.py:2126-2253

---

## 10. Forbidden Actions

During Phase 14.11A implementation:

1. **DO NOT add routes to cockpit.py** — 348 lines headroom; use new route file
2. **DO NOT replace 4 state systems** — add WorkstationModeResolver as read-only aggregator
3. **DO NOT expand OperationalMode or OperatorDayMode enums** — first slice proves pattern with existing values
4. **DO NOT build full continuity state machine** — P4-1 is MVP-critical second wave
5. **DO NOT attempt voice E2E wiring** — P2-1 is thin-hook tier; first slice uses typed commands
6. **DO NOT build idle/away detection** — P3-5 is thin-hook tier
7. **DO NOT build Meta IDE panels beyond TmuxPanel** — file browser, diff viewer, test panel are second wave
8. **DO NOT modify governance configuration** — Pillar 10 is COMPLETE
9. **DO NOT break 50/50 AC or 324/324 regression** — all additions are additive
10. **DO NOT commit runtime daemon data, dist-web, or Playwright screenshots**
11. **DO NOT begin EOS/CreatorOS/LyfeOS projection work**

---

## 11. Required Proof Artifacts

| # | Artifact | Pass Criteria |
|---|----------|---------------|
| 1 | Execution control demo | POST /execution/pause → process SIGSTOP → packet PAUSED; POST /execution/resume → process SIGCONT → packet EXECUTING |
| 2 | Natural command demo | Type natural language in CommandPalette → intent classified → work packet draft created → visible in UniversalWorkPanel |
| 3 | Mode display proof | HudBar shows composite mode (lifecycle + profile) from /api/umh/workstation/mode-composite |
| 4 | Resume widget proof | DashboardPanel shows resume context (last command, outcome, goals, next actions) from ContinuityBridge |
| 5 | Tmux panel proof | TmuxPanel renders live tmux sessions + pane capture from /api/umh/tmux/ |
| 6 | Repo/runtime state proof | Dashboard shows git branch, last commit, container health |
| 7 | Trace timeline proof | ExecutionPanel shows chronological trace history with outcomes |
| 8 | End-to-end loop proof | Natural command → classify → create packet → route → (pause if risky) → execute → trace → resume state updated → resume widget reflects |
| 9 | Regression pass | 50/50 AC tests PASS; 324/324 regression PASS |
| 10 | Route headroom proof | cockpit.py line count unchanged (new routes in separate file) |

---

## 12. GO / PARTIAL GO / NO-GO

| Factor | Score | Evidence |
|--------|-------|----------|
| Execution control foundation | GO | RuntimeAdapter.stop() implemented (SIGTERM/SIGKILL at shell_runtime_adapter.py:305-340); adding SIGSTOP/SIGCONT is OS-level |
| Work packet lifecycle | GO | PacketLifecycleStatus has clear enum + transition map (work_packet.py:28-107); adding PAUSED is mechanical |
| Intent classification backend | GO | intent_classifier.py (324 LOC) works with 17 domains + 14 work types; cockpit.py:2258 already exposes /intent/classify |
| Resume state backend | GO | WorkstationContinuityBridge generates complete resume_state.json (workstation_continuity_bridge_v1.py:234-299); only needs endpoint |
| Tmux backend | GO | tmux.py (137 LOC) + tmux_operational_adapter_v1.py (265 LOC) both functional; only needs endpoint + panel |
| Mode state systems | GO | All 4 systems have stores, enums, persistence; resolver is read-only aggregation |
| Cockpit headroom | GO (constrained) | 348 lines; 13 existing cockpit_*_routes.py files prove pattern; enforced via Forbidden Action #1 |
| Frontend patterns | GO | 27 panels + zustand stores + WorldView design system; adding TmuxPanel + widgets follows known patterns |
| CommandPalette extensibility | GO | Simple text filter (CommandPalette.tsx:70-77); adding intent fallback is ~40 LOC |
| Regression safety | GO | Additions are additive; no hot-path changes; existing test suite validates |
| Scope creep risk | CAUTION | 13 pillars with 58 blockers; Forbidden Actions must be enforced |
| State complexity | CAUTION | Adding ModeResolver as 5th aggregation layer; must stay read-only, not become new independent system |

**OVERALL: GO**

All first-slice blockers have existing backend foundations needing wiring, not greenfield construction. Critical path has verified code locations with exact line numbers. No blocker requires LLM inference, ML training, external service, or architectural invention. Risk is scope creep, not technical impossibility.

**First commit:** P7-2 (PAUSED state in work_packet.py)
**Second commit:** P7-1 (execution control wiring)
**Parallel:** P5-3, P4-4, P6-2, P3-3 can all start immediately

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| cockpit.py headroom (348 lines) | HIGH | All new routes in cockpit_workstation_control_routes.py; forbidden to add to cockpit.py |
| Dead workstation code (26,671 LOC) | MEDIUM | First slice uses existing adapters; dead code triage is separate phase |
| Execution control stubs | CRITICAL (blocked) | P7-1/P7-2 are first-slice priority #1 |
| Runtime daemon data in git | MEDIUM | Forbidden Action #10; .gitignore enforcement |
| Playwright artifact hygiene | LOW | Screenshots not committed per Forbidden Action #10 |
| Governance bypass | ZERO | All execution routes through ExecutionAuthorityEngine; Pillar 10 COMPLETE |
| State system fragmentation | MEDIUM | ModeResolver is read-only aggregator, not replacement; 4 systems remain |

---

## Verdict

**GATE 2 LOCKED.** Blocker dependency graph complete. First slice identified: 12 blockers, ~8-10 work packets, named **Phase 14.11A — Workstation Control Spine + Resume Slice**. Determination: **GO**. Begin implementation with P7-2 (PAUSED state), then P7-1 (execution wiring), then parallel fan-out.
