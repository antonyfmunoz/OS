---
phase: "14.6G"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "READINESS_GATE"
sources:
  - "Codebase survey of existing infrastructure"
  - "Phase 14.6G acceptance criteria"
  - "UMH architecture layer law"
---

# Phase 14.6G: Stage 1 Dependency Graph

## What This Is

The dependency graph for UMH Stage 1 implementation. Shows what must exist first, what can be parallelized, what must remain blocked, and what external tools are required.

## Legend

```
[EXIST]  = Production code already exists, needs wiring or extension
[BUILD]  = Must be built from scratch
[WIRE]   = Connecting existing components through routes/UI
[BLOCK]  = Cannot begin until dependency is met
[SIMUL]  = Can be manually simulated temporarily
[REAL]   = Must be real (not simulated) for Stage 1
[EXTERN] = External tool/service dependency
```

## Dependency Graph

```
                         ┌─────────────────────────────┐
                         │     WAVE 1: FOUNDATION       │
                         │     (must be first)          │
                         └─────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
          ▼                          ▼                          ▼
  ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
  │ WP-1.1        │        │ WP-1.2        │        │ WP-1.3        │
  │ Reality Model │        │ Cockpit       │        │ Memory        │
  │ HTTP Routes   │        │ Panel Wiring  │        │ Route Upgrade │
  │ [WIRE]        │        │ [WIRE]        │        │ [WIRE]        │
  │               │◄───────│ depends on    │        │               │
  │               │        │ WP-1.1        │        │               │
  └───────┬───────┘        └───────┬───────┘        └───────┬───────┘
          │                        │                        │
          │        ┌───────────────┘                        │
          │        │                                        │
          ▼        ▼                                        │
  ┌───────────────┐                                        │
  │ WP-1.4        │◄───────────────────────────────────────┘
  │ Execution     │
  │ Control Wire  │
  │ [WIRE]        │
  └───────┬───────┘
          │
          ▼
  ┌───────────────────────────────┐
  │       WAVE 1 GATE             │
  │ AC-1, AC-2, AC-3 pass        │
  │ Reality model visible in      │
  │ Cockpit. Memory persists.     │
  │ Execution endpoints live.     │
  └───────────────┬───────────────┘
                  │
                  ▼
          ┌─────────────────────────────┐
          │     WAVE 2: ORGANISM LOOP   │
          │     (depends on Wave 1)     │
          └─────────────────────────────┘
                  │
    ┌─────────────┼─────────────────────┐
    │             │                     │
    ▼             ▼                     ▼
┌─────────┐ ┌─────────────┐    ┌───────────────┐
│ WP-2.1  │ │ WP-2.2      │    │ WP-2.3        │
│ Intent  │ │ Work Packet  │    │ Approval UI   │
│ Capture │ │ Lifecycle    │    │ [WIRE]        │
│ [WIRE]  │ │ [WIRE+BUILD] │    │               │
│         │ │              │    │               │
└────┬────┘ └──────┬───────┘    └───────┬───────┘
     │             │                    │
     └─────┬───────┘                    │
           ▼                            │
    ┌─────────────┐                     │
    │ WP-2.4      │◄────────────────────┘
    │ Agent/Tool  │
    │ Routing     │
    │ [WIRE]      │
    └──────┬──────┘
           │
           ▼
   ┌───────────────────────────────┐
   │       WAVE 2 GATE             │
   │ AC-4, AC-5, AC-6 pass        │
   │ Intent → work packets →       │
   │ routing → approval loop       │
   │ works end-to-end.             │
   └───────────────┬───────────────┘
                   │
                   ▼
          ┌─────────────────────────────┐
          │     WAVE 3: FEEDBACK LOOP   │
          │     (depends on Wave 2)     │
          └─────────────────────────────┘
                   │
     ┌─────────────┼──────────────────┐
     │             │                  │
     ▼             ▼                  ▼
┌─────────┐ ┌─────────────┐  ┌───────────────┐
│ WP-3.1  │ │ WP-3.2      │  │ WP-3.3        │
│ Outcome │ │ Self-Improve │  │ Verification  │
│ → Model │ │ Cadence      │  │ Pipeline      │
│ Update  │ │ [WIRE]       │  │ [WIRE+EXTEND] │
│ [WIRE]  │ │              │  │               │
└────┬────┘ └──────┬───────┘  └───────┬───────┘
     │             │                  │
     └─────┬───────┘                  │
           ▼                          │
    ┌─────────────┐                   │
    │ WP-3.4      │◄──────────────────┘
    │ Projection  │
    │ Build Loop  │
    │ [WIRE]      │
    └──────┬──────┘
           │
           ▼
   ┌───────────────────────────────┐
   │       WAVE 3 GATE             │
   │ AC-7, AC-8, AC-9, AC-10 pass │
   │ Full organism loop works.     │
   │ Stage 1 minimum viable.       │
   └───────────────────────────────┘
```

## Parallelization Opportunities

### Within Wave 1 (all can start simultaneously)

| Work Packet | Can Parallelize With | Why |
|-------------|---------------------|-----|
| WP-1.1 Reality Model Routes | WP-1.3 Memory Routes | Independent HTTP route files |
| WP-1.3 Memory Routes | WP-1.1 Reality Model Routes | Independent data sources |

| Work Packet | Must Wait For | Why |
|-------------|--------------|-----|
| WP-1.2 Cockpit Panel Wiring | WP-1.1 Reality Model Routes | Panels need endpoints to call |
| WP-1.4 Execution Control Wire | WP-1.1 + WP-1.3 | Execution needs reality model + memory context |

### Within Wave 2 (partial parallelization)

| Work Packet | Can Parallelize With | Why |
|-------------|---------------------|-----|
| WP-2.1 Intent Capture | WP-2.3 Approval UI | Independent subsystems |
| WP-2.2 Work Packet Lifecycle | WP-2.3 Approval UI | Independent subsystems |

| Work Packet | Must Wait For | Why |
|-------------|--------------|-----|
| WP-2.4 Agent/Tool Routing | WP-2.1 + WP-2.2 + WP-2.3 | Routing needs intent, packets, and approval infrastructure |

### Within Wave 3 (partial parallelization)

| Work Packet | Can Parallelize With | Why |
|-------------|---------------------|-----|
| WP-3.1 Outcome → Model Update | WP-3.3 Verification Pipeline | Independent subsystems |
| WP-3.2 Self-Improvement Cadence | WP-3.3 Verification Pipeline | Independent subsystems |

| Work Packet | Must Wait For | Why |
|-------------|--------------|-----|
| WP-3.4 Projection Build Loop | WP-3.1 + WP-3.2 + WP-3.3 | Needs full feedback loop before building projections through it |

## External Dependencies

### Required External Tools/Services

| Tool/Service | Status | Required For | Can Simulate? |
|-------------|--------|-------------|---------------|
| Neon Postgres | PRODUCTION | Memory persistence, conversation storage | NO -- must be real |
| Claude Code CLI (cc_sdk) | PRODUCTION | Agent routing, LLM calls | YES -- Gemini/Groq/Ollama fallback |
| GitHub | PRODUCTION | PR creation, code review routing | YES -- local git operations |
| Docker | PRODUCTION | Service deployment | NO -- must be real for services |
| Fly.io | PRODUCTION | Cockpit deployment | YES -- local dev server for testing |
| Electron | PRODUCTION | Desktop Cockpit | YES -- browser Cockpit for testing |
| Tailscale | PRODUCTION | VPS networking | NO -- must be real |
| Apify | AVAILABLE | Scraping capabilities | YES -- not needed for Stage 1 |
| Kokoro TTS | AVAILABLE | Voice output | YES -- text output as fallback |

### Can Be Manually Simulated Temporarily

| Component | Simulation Method | When Must Be Real |
|-----------|-------------------|-------------------|
| Voice input | Text input only | After Stage 1 minimum (not required for MVP) |
| Fly.io deployment | Local dev server | Before daily use (can be deferred short-term) |
| Electron packaging | Browser-based Cockpit | Before daily use (can be deferred short-term) |
| GitHub PR routing | Local git operations | Before team collaboration |
| TTS voice output | Text response only | After voice pipeline verified |

### Must Be Real Before Stage 1 Is Usable

| Component | Why |
|-----------|-----|
| Neon Postgres | Memory and reality model persistence is non-negotiable |
| At least one LLM provider | Agent routing requires intelligence; cc_sdk or any fallback |
| Cockpit HTTP server | The interface IS the product surface |
| Docker | Services run in containers |
| Git repository | Source of truth for code |

## What Must Remain Blocked

| Item | Blocked Until | Reason |
|------|-------------|--------|
| EOS implementation | Stage 1 Wave 3 complete | UMH must coordinate work before projections use it |
| CreatorOS implementation | Stage 1 Wave 3 complete + EOS proves pattern | CreatorOS auth depends on EOS proving Clerk pattern (DEC-146B-COS-002) |
| LyfeOS Clerk migration | CreatorOS proves Clerk pattern | DEC-146B-LOS-002 explicitly gates on CreatorOS |
| Production autonomous execution | Operator explicitly enables `dry_run_only = false` | Safety gate -- autonomous cadence must remain dry-run until operator trust |
| Schema migrations | Explicit operator approval per migration | CRITICAL risk class |
| Dead code deletion (26,671 lines) | After Stage 1 functional | DEC-146B-UMH-004 -- extract useful parts first |
