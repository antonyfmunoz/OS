# UMH Workstation / Jarvis Experience Canon

Phase: 14.6B-UMH (revised 14.6F) | Status: DRAFT | Provenance: CODE_RESOLVED_CURRENT_TRUTH + OPERATOR_CORRECTION + 18 ratified P0 decisions (2026-06-04)
Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

---

## What UMH Is to the Operator

The Universal Meta Harness (DEC-146B-UMH-001) is the operator's private Jarvis-style system -- a reality-isomorphic intelligence harness (DEC-146C-001) that builds, maintains, and acts through an integrated approximation of reality across 12 layers. It is not merely a developer tool, a business dashboard, or an operational tooling system. The operator interacts with UMH's reality model through multiple experience modes, each providing a lens onto the same underlying 12-layer reality model. The Jarvis experience is not about dashboards -- it is about interfacing with a living reality model that knows the operator's world, constraints, resources, and goals.

**Stage 1 Organism (DEC-146C-003, RATIFIED 2026-06-04 Option B):** The Jarvis experience is part of the indivisible Stage 1 organism (Reality Model + Cockpit + Memory + Governed Execution Loop). Experience modes are not separate from the reality model -- they are interfaces into it. Cockpit without reality model = only dashboard. Reality model without Cockpit = inaccessible to operator. Both must advance together; incremental builds only if each increment advances all four components.

## Current Experience Modes

Each mode is a lens onto UMH's reality model -- not a separate application or dashboard. The underlying 12-layer reality model is the same across all modes; the rendering surface differs by device and context. Every experience mode must be able to: (1) perceive reality-model state, (2) initiate governed actions, (3) receive feedback on outcomes, and (4) surface gaps and acquisition paths per the materialization principle (DEC-146C-002).

### 1. Cockpit UI Mode
**What:** Full graphical reality-model interface -- the operator's primary window into the 12-layer reality model (DEC-146C-001). Not merely a command center or dashboard.
**Technology:** Electron + React frontend at cockpit/src/
**Panels:** 27 panels covering dashboard, agents, organism, execution, infrastructure, knowledge, approvals, analytics, and more
**Components:** VoiceCommandBar, CommandPalette, ChatDrawer, HudBar, EventConsole, TopologyMap
**Access:** universalmetaharness.tech (web) or Electron desktop app
**Status:** IMPLEMENTED — frontend built, API surface extensive (~210 endpoints)

### 2. Discord Voice/Text Mode
**What:** Conversational interface via Discord
**Technology:** py-cord 2.6.1, Whisper, Silero VAD, Kokoro TTS
**Capabilities:** Text commands, voice commands, file attachments, approval responses
**Access:** Discord server with DEX bot
**Status:** IMPLEMENTED — primary production interface

### 3. CLI Mode (Claude Code)
**What:** Developer/operator CLI via Claude Code
**Technology:** Claude Code CLI, tmux sessions, SSH
**Capabilities:** Code changes, system administration, agentic development
**Access:** tmux session "dex_main" on VPS, SSH from any device
**Status:** IMPLEMENTED — used daily for development

### 4. Mobile SSH Mode
**What:** Command-line access from iPhone via Termius
**Capabilities:** Quick commands, log viewing, service management
**Status:** IMPLEMENTED — operational

## Device Graph

### VPS (100.77.233.50)
Role: Coordination brain — always-on, lightweight
Runs: Docker containers, tmux sessions, Claude Code
Connection: Tailscale mesh
Storage: Code repo (/opt/OS), logs, runtime data

### Windows Beast (100.74.199.102)
Role: GPU workhorse
Runs: Docker Engine (WSL2), Kokoro TTS, Electron builds, large models
Connection: Tailscale mesh, SSH
Storage: Full Trinity repos, media processing

### iPhone
Role: Mobile command interface
Access: Termius SSH to VPS
Capabilities: Quick commands, monitoring

### iPad
Role: Portable development interface
Access: code-server (VS Code in browser) via VPS
Capabilities: Full editing, browsing

## Voice/Text Command Architecture

### Voice Input Path
Microphone → Discord voice channel → Whisper STT → text → Gateway.handle()

### Voice Output Path
Response text → Kokoro TTS (Beast at :8880) → audio → Discord voice channel

### Text Input Path
Discord text message → signal_factory → SignalEnvelope → Gateway.handle()
Cockpit CommandPalette → API endpoint → execution
CLI command → Claude Code session → code changes

### Command Routing
1. Intent classification (7 regex patterns + 12 gateway categories)
2. Gateway routing (agent_task, event, status, brief)
3. Agent hierarchy (CEO → Department agents)
4. Model routing (10-provider chain with deterministic fallback)

## Tmux/Session Visibility

### Current Session Architecture
- dex_main: Primary Claude Code session on VPS
- Discord bot mounts host tmux socket (/tmp/tmux-0)
- CC_SDK_TIMEOUT_SECONDS=180 for long operations
- EOS_ROUTER_CLAUDE_CLI_SESSION=dex_main for targeting

### Visibility
- os-discord container can reach host tmux sessions
- No dedicated cockpit panel for tmux session visibility
- Session state visible via operator_api.py organism endpoints

## Infrastructure Visibility

### Current
- /api/umh/infra: Compute (CPU/mem/disk), network (Tailscale peers), service nodes
- /api/umh/mesh/nodes: Connected mesh nodes with heartbeat
- InfrastructurePanel: Visual topology map
- Docker socket mounted read-only in os-operator for container inspection

### VPS/Windows Coordination
- Tailscale mesh provides private networking
- Node mesh protocol (transports/node_mesh/) for status exchange
- Windows daemon (nodes/) for Beast coordination
- Development session bridge (substrate/organism/development_session_bridge.py)

## Overnight/Autonomous Mode

### Current Capabilities
- Organism autonomous tick (substrate/organism/autonomous_tick.py)
- Autonomous cadence (substrate/organism/autonomous_cadence.py)
- Template-based candidate supply (substrate/organism/candidate_supply_engine.py)
- Dry-run only mode (no production changes without operator approval)
- Operator acceptance mode configurable

### Return-to-Summary
- When operator returns: organism events, messages, reports available via cockpit
- Activity stream aggregates what happened during away period
- Deliverables tracked and visible
- No automated "morning summary of overnight work" yet

## Degraded Mode Operation

### Current Handling
- Deterministic fallback responses when all LLM providers fail
- Circuit breaker prevents cascading failures
- Substrate operates without memory (degraded but functional)
- No explicit degraded mode UI in cockpit

### What Happens When Things Fail
- All LLMs down: Deterministic responses via intent patterns (7 templates)
- Database down: Memory unavailable, in-memory fallback
- Discord down: Cockpit API still accessible
- VPS down: Nothing runs (single point of failure)
- Beast down: No TTS, no heavy compute, but core operations continue

## Gaps for Full Jarvis Experience

### P0 (must resolve for Stage 1 organism -- DEC-146C-003)
1. No tmux session visibility panel in cockpit
2. Execution control stubs (pause/resume/abort return static ok)
3. No overnight summary upon operator return
4. No degraded mode detection or UI indicator
5. Experience modes do not yet surface reality-model layer state -- Cockpit shows operational data, not the 12-layer reality model directly (DEC-146C-001)
6. No gap/acquisition path surfacing in any experience mode (DEC-146C-002) -- operator cannot see typed gaps or their resolution paths

### P1
1. No meta-IDE file browser in cockpit (EditorPanel exists but limited)
2. No diff viewer for source mutations
3. No integrated terminal (tmux connection from cockpit)
4. No cross-device session handoff
5. No wake-word detection for voice

### P2
1. No computer vision / screen analysis
2. No proactive alerting to operator's phone
3. No adaptive UX based on device/context
4. No ambient display mode (always-on reality-model visualization)

## Workstation Code Status (DEC-146B-UMH-004, RATIFIED 2026-06-04)

The codebase contains 26,671 lines of dead workstation code from the original Jarvis-style build. Per DEC-146B-UMH-004, conceptual value is to be extracted into design docs, then the dead code deleted. The Jarvis experience documented here captures the target vision; the dead code is a historical artifact, not the implementation path.

## Reality Model Interface Design Principles (DEC-146C-001)

The Jarvis experience is not about building better dashboards. It is about giving the operator a natural interface into UMH's living reality model:

1. **Reality model, not data model** -- Every panel, command, and voice response should reflect the operator's reality as modeled across 12 layers, not raw database records or API responses.
2. **Bidirectional** -- The operator both reads reality-model state AND initiates governed mutations through every experience mode. Reading without acting is a dashboard; acting without reading is blind execution.
3. **Gap-aware (DEC-146C-002)** -- When the reality model has gaps (typed per the materialization principle), the experience must surface them with their acquisition paths, not hide them or display empty states.
4. **Context-adaptive** -- The same reality-model state renders differently on Cockpit (full visualization), Discord (conversational summary), CLI (structured output), and Mobile (critical alerts). The model is the same; the rendering adapts.
5. **Stage 1 completeness (DEC-146C-003)** -- The Jarvis experience is not complete until it interfaces with all four indivisible components: Reality Model (perceive state), Cockpit (visualize it), Memory (recall context), Governed Execution (act on it).
