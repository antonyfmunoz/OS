# Phase 13.2 — cortextOS Comparison Audit

**Date:** 2026-05-31
**Phase:** 13.2 — Native Agent Runtime / Workcell Execution Surface
**Scope:** Compare UMH runtime surface architecture against cortextOS patterns

---

## 1. What cortextOS Does

cortextOS is a hypothetical "agent OS" pattern that provides:
- Agent runtime lifecycle management (spawn, monitor, terminate)
- Sandboxed execution environments per agent task
- Event streaming from running agents to operator dashboards
- Policy-gated launch (approval gates, risk classification)
- Artifact collection and validation after execution

## 2. What UMH Phase 13.2 Implements

| Capability | cortextOS Pattern | UMH 13.2 Implementation |
|---|---|---|
| **Runtime session model** | Agent session with state machine | `RuntimeSession` with 11-state FSM (drafted → completed/failed/stopped/expired) |
| **Adapter abstraction** | Pluggable runtime backends | `RuntimeAdapter` ABC with `ShellRuntimeAdapter` + `ClaudeCodeRuntimeAdapter` skeleton |
| **Sandbox isolation** | Container/VM per agent | Git worktree per session + env stripping + blocked command patterns |
| **Event streaming** | WebSocket event feed | JSONL event persistence + polling API (5s/15s intervals) |
| **Policy enforcement** | Pre-launch policy check | `validate_runtime_policy()` — risk class, command blocking, linkage requirement, repo root guard |
| **Handoff transparency** | Pre-launch preview | `RuntimeHandoffPreview` — what_will_happen / what_will_not_happen lists |
| **Stop/cancel** | Graceful termination | SIGTERM → wait → SIGKILL process group cascade |
| **Artifact collection** | Post-execution artifact sweep | `collect_artifacts()` + `validate()` on adapter interface |
| **Operator dashboard** | Runtime monitoring UI | `RuntimePanel.tsx` — overview stats, adapter status, session table, event stream |
| **Secret protection** | Credential isolation | `_redact_secrets()` on all output + `_sandbox_env()` stripping 8 sensitive prefixes |

## 3. Key Differences from cortextOS

### 3.1 UMH Is Governance-First, Not Autonomy-First
cortextOS patterns typically aim to maximize agent autonomy — the system asks "what can the agent do unsupervised?" UMH inverts this: the system asks "what has the operator explicitly approved?" Every runtime session requires:
- Work Packet or OperatorSession linkage
- Operator approval for medium+ risk
- Sandbox/worktree boundary
- Blocked command filtering

### 3.2 No Container Isolation (Intentional)
cortextOS often uses Docker containers or VM isolation. UMH Phase 13.2 uses git worktrees + process groups instead. Reasons:
- VPS is lightweight orchestrator, not a compute beast
- Git worktrees give full repo context without main mutation risk
- Process group isolation (start_new_session=True) prevents zombie cascades
- Container isolation planned for Phase 13.3+ when Beast node is active

### 3.3 Synchronous Shell Adapter (Not Async Streaming)
The shell adapter blocks on `proc.communicate()` and persists events after completion. A true streaming adapter would read stdout line-by-line in real-time. This is intentional for Phase 13.2 — the safety model is simpler when the entire output is available before any event persistence. Async streaming is a Phase 13.3+ enhancement.

### 3.4 No Auto-Merge / No Production Truth Mutation
cortextOS patterns often include automated merge workflows. UMH explicitly forbids this:
- Runtime sessions operate in sandbox only
- No PR creation from runtime
- No merge capability
- No ProductionOutcomeCommitted emission
- The _WILL_NOT_HAPPEN list is a governance contract, not a TODO

## 4. What UMH Does That cortextOS Typically Doesn't

| UMH Feature | Description |
|---|---|
| **Idempotency keys** | Prevent duplicate sessions from retried requests |
| **19 blocked command patterns** | Regex-based command denylist covering destructive, credential, and mutation commands |
| **Secret redaction in events** | API keys, JWT tokens, connection strings scrubbed from all persisted output |
| **Environment stripping** | Child processes don't inherit ANTHROPIC_*, OPENAI_*, GITHUB_TOKEN, etc. |
| **Truthful degradation** | Claude Code adapter honestly reports "not available" instead of faking capabilities |
| **Handoff preview with negatives** | Explicitly tells operator what will NOT happen, not just what will |
| **Main repo root guard** | Runtime cannot operate directly on the main working tree |

## 5. Convergence Assessment

Phase 13.2 implements the core cortextOS runtime surface pattern while maintaining UMH governance principles. The key architectural difference is intentional: UMH favors operator control over agent autonomy, which means the runtime surface is a tool the operator wields, not a self-directing agent infrastructure.

**Status:** Phase 13.2 achieves parity with cortextOS core runtime patterns while exceeding it in governance, transparency, and security hardening.
