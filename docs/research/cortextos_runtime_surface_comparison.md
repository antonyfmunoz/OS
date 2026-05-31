# cortextOS / agent-os Runtime Surface Comparison — UMH Phase 13.2

**Date:** 2026-05-31
**Phase:** 13.2 — Native Agent Runtime / Workcell Execution Surface
**Purpose:** Document what UMH studied from the agent-os codebase and the adaptation decisions made
**Source repo:** https://github.com/saadnvd1/agent-os (referred to internally as "cortextOS")

---

## 1. What agent-os Is

agent-os (`saadnvd1/agent-os`) is a real, public repository implementing a
runtime-control-first agent operating system. It is a concrete codebase with
working implementations of PTY management, multi-provider agent sessions,
and orchestration via MCP.

**Clarification:** The internal UMH name "cortextOS" does not correspond
to a public repository of that name. The repo `ivanuser/cortex-os` is an
unrelated Ubuntu desktop OS. The patterns UMH studied come from
`saadnvd1/agent-os`.

agent-os prioritizes direct runtime access: the operator interacts with
agents through live terminal sessions (browser-based via node-pty/WebSocket),
a mobile PWA, and programmatic orchestration via MCP tools. The system is
permissive by default — agents auto-approve actions using CLI-native flags.

## 2. Code-Level Patterns Studied

### 2.1 Persistent PTY Runtime
**Files:** `server.ts`, `lib/orchestration.ts`
**Tech:** `node-pty` (v1.2.0-beta.6) + `ws` (WebSocket) + `@xterm/xterm` (v6) + **tmux**

The custom HTTP server intercepts WebSocket upgrades at `/ws/terminal`.
Each connection spawns a real PTY via `pty.spawn(shell, [], { name:
'xterm-256color', cols: 80, rows: 24, env: minimalEnv })`. Input arrives
as JSON `{ type: "input", data }` or `{ type: "command", data }`.

Agent sessions use **tmux as the persistence layer**, not raw node-pty.
The node-pty WebSocket is for the interactive terminal pane in the browser.
Agent sessions persist as named tmux sessions that survive disconnects.
`spawnWorker()` creates sessions via `tmux new-session -d -s "${provider}-${uuid}"`.

**UMH adaptation:** Phase 13.2 uses synchronous subprocess execution
(`subprocess.Popen` with `communicate()`) rather than persistent PTY/tmux.
This is intentional — the safety model is simpler when the entire output
is available before event persistence. Persistent PTY is a Phase 13.3+
target, contingent on container isolation being available.

### 2.2 AgentManager / AgentProcess Lifecycle
**Files:** `lib/claude/process-manager.ts`, `lib/orchestration.ts`
**Classes:** `ClaudeProcessManager` (structured JSON path), worker functions (tmux path)
**States:** `"idle" | "running" | "waiting" | "error"` (process manager)
**Worker states:** `"pending" | "running" | "waiting" | "idle" | "completed" | "failed" | "dead"`

There is no class named `AgentManager` or `AgentProcess`. The lifecycle
management is split between `ClaudeProcessManager` (for structured output
via `--output-format stream-json`) and orchestration worker functions
(`spawnWorker`, `killWorker`, `completeWorker`). Workers use tmux sessions.
Status detection polls `tmux capture-pane` output against regex patterns.

**UMH adaptation:** `RuntimeManager` (385 lines) with `RuntimeSession`
11-state FSM. UMH adds governance layers that agent-os omits: policy
validation before launch, Work Packet linkage, risk classification,
sandbox allocation, and operator approval gates.

### 2.3 Claude Code Runtime
**Files:** `lib/claude/process-manager.ts` (structured JSON), `lib/claude/stream-parser.ts`

Two paths exist:
- **Path A (structured JSON):** `child_process.spawn("claude", ["-p", "--output-format", "stream-json"])` — no PTY, stdout piped through `StreamParser` (NDJSON → typed `ClientEvent` objects).
- **Path B (interactive tmux):** `claude` launched inside a tmux session via `tmux send-keys`. Live output captured via `tmux capture-pane`.

**UMH adaptation:** `ClaudeCodeRuntimeAdapter` (179 lines) with truthful
binary detection (`shutil.which("claude")` + common path checks). Currently
returns "not yet implemented" with `implementation_phase="13.3+"`. When
implemented, will use structured JSON path (safer for governance) rather
than tmux path.

### 2.4 Message Injection
**File:** `app/api/sessions/[id]/send-keys/route.ts`

Does NOT use bracketed paste escape sequences. Uses **tmux buffer paste**:
1. Write text to temp file (`/tmp/agent-os-send-${id}.txt`)
2. Load into named tmux buffer: `tmux load-buffer -b "send-${id}" "${tempFile}"`
3. Paste buffer into target session: `tmux paste-buffer -b "send-${id}" -t "${tmuxSessionName}"`
4. Optionally send Enter
5. Clean up buffer and temp file

The orchestration system uses simpler `tmux send-keys -l '${escapedTask}'`
(literal mode with `-l` flag).

**UMH adaptation:** `RuntimeInjectRequest` with `injection_mode` and
`requires_enter` fields. The shell adapter's `inject()` method writes
to `proc.stdin` with optional newline append. The tmux buffer paste
pattern is noted for Phase 13.3+ PTY integration.

### 2.5 Mobile Command Surface
**Files:** `components/mobile/SwipeSidebar.tsx`, `components/views/MobileView.tsx`, `app/sw.ts`

**No Telegram transport exists.** The mobile surface is a mobile-first
Progressive Web App (PWA) with service worker for offline/installable
capability. Also has a Tauri wrapper for native desktop apps. Notifications
use Web Notifications API + `AudioContext` audio tones.

**UMH adaptation:** UMH uses Discord as the presence layer (live in
production). The cockpit is the primary visual surface. The architecture
is transport-agnostic: any client can call `/operator-experience/send`.
A mobile PWA is a possible future surface.

### 2.6 Cron Scheduler
**No cron scheduler exists in agent-os.** There are no files related to
scheduled tasks, cron expressions, or recurring execution.

**UMH adaptation:** UMH has the Cadence Engine (live, `dry_run_only`).
This is a UMH-original pattern, not adapted from agent-os.

### 2.7 Agent / Task Bus
**File:** `mcp/orchestration-server.ts`
**Protocol:** MCP (Model Context Protocol) via `@modelcontextprotocol/sdk`

Runs as a stdio MCP server that any Claude Code session can connect to.
Tools exposed: `spawn_worker`, `list_workers`, `get_worker_output`,
`send_to_worker`, `complete_worker`, `kill_worker`, `get_workers_summary`.
A conductor session spawns workers and communicates via MCP tool calls
proxied to the HTTP API (`/api/orchestrate/*`).

Data bus is SQLite (`better-sqlite3`). Workers linked to conductors via
`conductor_session_id` FK. No pub/sub or event queue — request/response only.

**UMH adaptation:** The Organism Coordinator + Workcell Protocol handles
inter-agent coordination. Work is routed through Work Packets, not MCP
tool calls. This enforces traceability — every unit of work has a packet
with lineage, risk classification, and outcome tracking.

### 2.8 Approvals
**File:** `lib/providers/registry.ts`

**No explicit approval gate before agent actions.** The system uses
auto-approve flags from the provider registry:
- Claude: `--dangerously-skip-permissions`
- Codex: `--dangerously-bypass-approvals-and-sandbox`
- Gemini: `--yolo`
- Aider: `--yes`
- Amp: `--dangerously-allow-all`

Workers spawned by orchestration pass `autoApprove: true` by default.
A `statusDetector` (`lib/status-detector.ts`) detects "waiting" state
via regex patterns (`/Allow\?/`, `/Approve\?/`, `/\[Y\/n\]/`) and surfaces
it in the UI, but the user must manually interact.

**UMH adaptation:** Approvals are NON-NEGOTIABLE in UMH. The
never-execute-without-approval invariant is a safety law, not a
configuration option. Phase 13.2 enforces this at three levels:
(1) `validate_runtime_policy()` blocks medium+ risk,
(2) `RuntimeHandoffPreview` requires operator review,
(3) `start_session()` requires `approved_by` parameter.
UMH explicitly REJECTS the `--dangerously-skip-permissions` default.

### 2.9 Multi-Runtime Adapter Concept
**Files:** `lib/providers.ts`, `lib/providers/registry.ts`
**Interface:** `AgentProvider`

Fully implemented with 10 providers: `claude`, `codex`, `opencode`,
`gemini`, `aider`, `cursor`, `amp`, `pi`, `omp`, `shell`.

Each provider defines: `id`, `name`, `command` (CLI binary), `buildFlags()`,
`waitingPatterns`/`runningPatterns`/`idlePatterns` (regex arrays for status
detection), `supportsResume`, `supportsFork`, `configDir`.

**UMH adaptation:** `RuntimeAdapter` abstract base class (104 lines)
with 11 abstract methods. Currently two implementations:
`ShellRuntimeAdapter` (377 lines, production-ready) and
`ClaudeCodeRuntimeAdapter` (179 lines, skeleton). UMH's adapter
interface is richer than agent-os's `AgentProvider`: it includes
`prepare`, `validate`, `collect_artifacts`, `cleanup` — governance
methods that agent-os doesn't need because it doesn't govern.

## 3. Patterns Adopted (with UMH Governance Overlay)

| agent-os Pattern | UMH Implementation | Governance Addition |
|---|---|---|
| Worker state machine (7 states) | RuntimeSession 11-state FSM | Policy validation + WP linkage |
| Multi-provider registry (10) | RuntimeAdapter ABC + 2 impls | Adapter availability honesty |
| Structured JSON Claude output | ClaudeCodeRuntimeAdapter skeleton | Truthful degradation |
| stdin/tmux injection | RuntimeInjectRequest + stdin write | Injection mode field |
| Process termination | SIGTERM → SIGKILL cascade | Event logging on stop |
| Session persistence (SQLite) | JSONL event persistence | Secret redaction on all output |

## 4. Patterns NOT Adopted (with Rationale)

| agent-os Pattern | Decision | Rationale |
|---|---|---|
| **`--dangerously-skip-permissions` default** | REJECTED | UMH requires explicit approval. Auto-approve is antithetical to governance-first. |
| **tmux as persistence layer** | DEFERRED 13.3+ | Requires container isolation. tmux sessions are hard to sandbox. |
| **No approval gates** | REJECTED | Approvals are mandatory in UMH, not optional. |
| **Direct MCP tool-call orchestration** | ADAPTED | UMH uses Work Packets, not MCP tool calls. Adds traceability. |
| **Browser-based xterm terminal** | DEFERRED | Cockpit uses structured panels, not raw terminals. Terminal pane is a future addition. |
| **SQLite local storage** | REJECTED | UMH uses JSONL (append-only, auditable) + Neon Postgres for structured data. |
| **10 CLI providers** | SCOPED to 2 | Only shell + claude_code_pty. Others added when governance model supports them. |

## 5. Risks Identified from agent-os Patterns

1. **Autonomy creep** — agent-os defaults to auto-approve. If UMH adopts
   agent-os patterns without governance overlay, approval gates could erode.
   Guard: `validate_runtime_policy()` rejects medium+ risk mechanically.

2. **Secret leakage** — agent-os captures raw terminal output including
   secrets (no redaction layer). Guard: UMH applies `_redact_secrets()`
   (6 patterns) and `_sandbox_env()` (8 sensitive prefixes) to all output.

3. **Process escape via tmux** — tmux sessions can spawn children that
   outlive the orchestration process. Guard: UMH uses `start_new_session=True`
   for process group isolation and `os.killpg()` for group termination.

4. **Main repo mutation** — agent-os agents operate directly on the
   working tree. Guard: UMH blocks main repo root, allocates git worktrees
   per session, and blocks 19 destructive command patterns.

5. **Status detection by regex** — agent-os detects agent state by polling
   `tmux capture-pane` and matching regex patterns. This is fragile and
   can misclassify state. Guard: UMH uses explicit state transitions in
   `RuntimeSession` FSM, not regex-based inference.

## 6. Roadmap Implications

| Phase | agent-os-Informed Enhancement |
|---|---|
| **13.3** | Persistent PTY (Python pty module or node-pty), with container isolation |
| **13.3** | Claude Code runtime activation (structured JSON path, not tmux) |
| **13.4** | tmux buffer paste for safe multi-line injection (if PTY adopted) |
| **13.5** | Mobile PWA command surface (agent-os proves PWA is viable for this) |
| **14.x** | Additional provider adapters (codex, gemini) when governance model supports |
| **14.x** | MCP orchestration server (agent-os pattern) for conductor→worker model |

## 7. Key Architectural Distinction

agent-os asks: **"How do I give agents the most capable runtime?"**
UMH asks: **"What has the operator explicitly approved?"**

agent-os optimizes for agent velocity and developer experience.
UMH optimizes for operator confidence and production truth integrity.

agent-os has no concept of:
- Work Packets (traceability)
- Risk classification (governance)
- Production truth (deployment integrity)
- Handoff previews (transparency)
- Secret redaction (security)

These are not features agent-os needs — it's a development tool.
UMH is an operational system managing real business processes.
The patterns are complementary, not competing.
