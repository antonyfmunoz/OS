# cortextOS — Phase 13 Runtime Surface Study

**Date:** 2026-05-31
**Phase:** 13.1 research artifact
**Purpose:** Document what UMH learned from cortextOS for operator surface design

## What cortextOS Is

cortextOS is a runtime-control-first system — it prioritizes direct access to
persistent PTY sessions, agent runtimes, and command execution. The operator
interacts with agents through a live terminal/chat interface.

## What UMH Is (by contrast)

UMH is truth/work-packet/governance-first. The operator interacts through
structured command interpretation → preview → approval → governed execution.
UMH never executes without explicit approval. cortextOS is more permissive.

## Relevant cortextOS Patterns

| Pattern | cortextOS | UMH Equivalent / Status |
|---------|-----------|------------------------|
| Persistent PTY runtime | Live terminal sessions per agent | Not yet — Phase 13.2 target |
| Message injection | Push commands into running sessions | POST /operator-experience/send (Phase 13.0) |
| Mobile/Telegram surface | Telegram bot as operator interface | Discord bot as presence layer (live) |
| Cron scheduling | Built-in cron for recurring agent tasks | Cadence engine (live, dry_run_only) |
| Agent bus | Inter-agent message routing | Organism coordinator + workcell protocol (live) |
| Runtime adapters | Pluggable execution backends | Capability router + environment types (live) |
| Approvals | Optional approval gates | Non-negotiable — never-execute invariant (live) |

## Patterns Worth Adopting

1. **Persistent PTY for agent runtimes** — cortextOS's strongest pattern. UMH
   agents currently execute via subprocess/SDK calls. A persistent PTY would
   enable interactive debugging, mid-execution steering, and live observation.
   Target: Phase 13.2.

2. **Mobile command surface** — cortextOS uses Telegram. UMH should build a
   lightweight mobile command surface (Telegram or native) that sends to the
   same /operator-experience/send endpoint. The cockpit OperatorPanel is the
   first surface; mobile is the second.

3. **Runtime adapter abstraction** — cortextOS cleanly separates "what to run"
   from "where to run." UMH has this partially via EnvironmentType and
   CapabilityRouter but should formalize it for Phase 13.2 workcell execution.

## Caution: Skip-Permissions Anti-Pattern

cortextOS allows agents to execute without explicit approval in some modes.
UMH must NOT adopt this without:
- Full sandboxing (container isolation per workcell)
- Governance classification (risk-gated execution)
- Rollback capability (undo on failure)
- Audit trail (trace recording)

The never-execute-without-approval invariant is a UMH safety law.
Relaxing it requires the full sandbox/governance stack from Phase 13.2+.

## Roadmap Implication

Phase 13.2 should build the Native Agent Runtime / Workcell Execution Surface:
- Persistent PTY sessions per workcell
- Sandboxed execution environments
- Live observation / steering
- Interactive debugging
- This is the bridge from "preview only" to "governed execution"
