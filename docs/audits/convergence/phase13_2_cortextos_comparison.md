# Phase 13.2 — cortextOS / agent-os Comparison Audit

**Date:** 2026-05-31 (corrected)
**Phase:** 13.2 — Native Agent Runtime / Workcell Execution Surface
**Scope:** Compare UMH runtime surface against real agent-os codebase patterns
**Source repo:** https://github.com/saadnvd1/agent-os
**Full research:** [docs/research/cortextos_runtime_surface_comparison.md](../../research/cortextos_runtime_surface_comparison.md)

---

## 1. What agent-os Is

agent-os (`saadnvd1/agent-os`) is a real, public repository implementing a
runtime-control-first agent operating system. Internally referenced as
"cortextOS" in UMH planning — corrected here to the actual repo name.

Concrete patterns studied from the codebase:

| Pattern | agent-os Implementation | Key File |
|---|---|---|
| **Persistent PTY** | node-pty + tmux sessions (survive disconnects) | `server.ts`, `lib/orchestration.ts` |
| **Agent lifecycle** | `ClaudeProcessManager` + worker state machine (7 states) | `lib/claude/process-manager.ts` |
| **Claude Code runtime** | Two paths: structured JSON (child_process) + interactive tmux | `lib/claude/stream-parser.ts` |
| **Message injection** | tmux buffer paste (temp file → load-buffer → paste-buffer) | `app/api/sessions/[id]/send-keys/route.ts` |
| **Mobile surface** | PWA (no Telegram) + Tauri desktop wrapper | `components/mobile/`, `app/sw.ts` |
| **Cron scheduler** | NOT PRESENT | — |
| **Agent bus** | MCP orchestration server + SQLite persistence | `mcp/orchestration-server.ts` |
| **Approvals** | NOT PRESENT (auto-approve via CLI flags by default) | `lib/providers/registry.ts` |
| **Multi-runtime** | 10 providers (claude, codex, gemini, aider, cursor, etc.) | `lib/providers.ts` |

## 2. What UMH Phase 13.2 Implements (Adapted from agent-os Study)

| Capability | agent-os Pattern | UMH 13.2 Implementation |
|---|---|---|
| **Runtime lifecycle** | ClaudeProcessManager + worker functions | `RuntimeManager` + `RuntimeSession` 11-state FSM |
| **Adapter abstraction** | AgentProvider interface (10 providers) | `RuntimeAdapter` ABC + `ShellRuntimeAdapter` + `ClaudeCodeRuntimeAdapter` |
| **Sandbox isolation** | None (operates on working tree) | Git worktree per session + env stripping + 19 blocked patterns |
| **Event streaming** | NDJSON StreamParser | JSONL event persistence + polling API (5s/15s) |
| **Policy enforcement** | None (auto-approve by default) | `validate_runtime_policy()` — mandatory risk/linkage/command checks |
| **Handoff transparency** | Not present | `RuntimeHandoffPreview` — what_will/what_will_not_happen |
| **Stop/cancel** | `SIGTERM` / `killWorker()` | SIGTERM → wait → SIGKILL process group cascade |
| **Message injection** | tmux buffer paste | `RuntimeInjectRequest` + stdin write |
| **Secret protection** | Not present | `_redact_secrets()` + `_sandbox_env()` |

## 3. Key Differences

### 3.1 Governance-First vs Velocity-First
agent-os defaults to `--dangerously-skip-permissions` for all providers.
UMH requires explicit operator approval for every runtime session.

### 3.2 Work Packet Tracing vs Direct Execution
agent-os uses MCP tool calls for conductor→worker communication.
UMH routes all work through Work Packets with lineage and risk classification.

### 3.3 Secret Protection
agent-os captures raw terminal output with no redaction.
UMH redacts API keys, tokens, JWTs, and connection strings from all persisted output.

### 3.4 Sandbox Isolation
agent-os operates directly on the working tree.
UMH allocates git worktrees, blocks the main repo root, and strips sensitive env vars.

## 4. Patterns Rejected

| Pattern | Why |
|---|---|
| Auto-approve (`--dangerously-skip-permissions`) | Antithetical to governance-first |
| No approval gates | Approvals are mandatory in UMH |
| tmux persistence layer | Hard to sandbox; deferred to 13.3+ with containers |
| Direct working tree operation | UMH enforces worktree sandbox |
| 10 provider adapters | Scoped to 2 until governance model supports more |

## 5. Convergence Assessment

Phase 13.2 adopts agent-os's core runtime patterns (adapter abstraction,
lifecycle state machine, multi-runtime concept) while adding governance
layers that agent-os intentionally omits. The gap is philosophical:
agent-os is a development tool optimizing for agent velocity; UMH is
an operational system optimizing for production truth integrity.

**Status:** Phase 13.2 achieves and exceeds agent-os runtime surface
capabilities with governance, transparency, and security hardening
that agent-os does not implement.
