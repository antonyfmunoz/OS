# UMH Workstation / Jarvis Experience Canon

Phase: 14.6B-UMH (revised 14.6D) | Status: DRAFT | Provenance: CODE_RESOLVED_CURRENT_TRUTH + OPERATOR_CORRECTION + DEC-146C-001/002/003 ratification

---

## What UMH Is to the Operator

UMH is the operator's private Jarvis-style system — a reality-isomorphic intelligence harness (DEC-146C-001) that builds, maintains, and acts through an integrated approximation of reality. It is not merely a developer tool, a business dashboard, or an operational tooling system. The operator interacts with UMH's reality model through multiple experience modes, each providing a lens onto the same underlying 12-layer reality model.

**Stage 1 Organism (DEC-146C-003):** The Jarvis experience is part of the indivisible Stage 1 organism (Reality Model + Cockpit + Memory + Governed Execution Loop). Experience modes are not separate from the reality model — they are interfaces into it.

## Current Experience Modes

Each mode is a lens onto UMH's reality model. The underlying reality model is the same; the rendering surface differs by device and context.

### 1. Cockpit UI Mode
**What:** Full graphical reality-model interface (not merely a command center)
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

### P0
1. No tmux session visibility panel in cockpit
2. Execution control stubs (pause/resume/abort return static ok)
3. No overnight summary upon operator return
4. No degraded mode detection or UI indicator

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
4. No ambient display mode (always-on dashboard)
