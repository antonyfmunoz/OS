---
phase: "14.6G"
status: "DRAFT"
operator_approved: false
allows_implementation: false
date: "2026-06-04"
provenance: "READINESS_GATE"
sources:
  - "DEC-146B-EOS-001/002/003 -- EOS decisions"
  - "DEC-146B-COS-001/002/003/004 -- CreatorOS decisions"
  - "DEC-146B-LOS-001/002/003 -- LyfeOS decisions"
  - "DEC-146C-003 -- Indivisible Stage 1 Organism"
  - "Phase 14.6G acceptance criteria AC-10"
---

# Phase 14.6G: Projection App Dependency Gate

## What This Is

This document defines when EOS, CreatorOS, and LyfeOS implementation may begin. All three projection apps remain blocked until UMH Stage 1 can coordinate work through Cockpit, work packets, memory, and governed execution.

## The Principle

Projection apps are applications built ON UMH. They use UMH as their intelligence substrate. Building them before the substrate is functional means building without the coordination system that is supposed to manage the build process itself.

Per DEC-146C-003: Stage 1 acceptance criterion 10 requires that "UMH can build and improve projection apps from inside the UMH operating loop." This means:

1. UMH Stage 1 must be functional FIRST
2. Projection apps are THEN built THROUGH UMH, not independently
3. The build process itself validates that Stage 1 works

## Projection Dependency Chain

```
UMH Stage 1 (Waves 1-3)
    │
    ▼
EOS Implementation (DEC-146B-EOS-001/002/003)
    │
    ├── Beast branch promotion (DEC-146B-EOS-001)
    ├── MVP scope R1-R5 (DEC-146B-EOS-002)
    └── Clerk auth (DEC-146B-EOS-003)
    │
    ▼
CreatorOS Implementation (DEC-146B-COS-001/002/003/004)
    │
    ├── MVP scope confirmed (DEC-146B-COS-001)
    ├── Clerk auth AFTER EOS proves pattern (DEC-146B-COS-002)
    ├── Source baseline verified (DEC-146B-COS-003)
    └── Module build sequence (DEC-146B-COS-004)
    │
    ▼
LyfeOS Clerk Migration (DEC-146B-LOS-001/002/003)
    │
    ├── PRD v2.0 canonical (DEC-146B-LOS-001)
    ├── Clerk migration AFTER CreatorOS proves pattern (DEC-146B-LOS-002)
    └── Fly.io infrastructure (DEC-146B-LOS-003)
```

## Gate Conditions Per Projection

### EOS: When Can Implementation Begin?

| Condition | Required State | Source |
|-----------|---------------|--------|
| UMH Stage 1 Wave 3 complete | All 50 acceptance criteria pass | Phase 14.6G AC |
| Beast branch promoted to canonical | Git history verified, merged to main | DEC-146B-EOS-001 |
| MVP scope R1-R5 confirmed | Requirements documented in canon | DEC-146B-EOS-002 |
| Clerk auth integration ready | Clerk SDK installed, config documented | DEC-146B-EOS-003 |
| Work packets route to saas/ | AC-10.1 passes | Phase 14.6G AC-10 |
| Build coordinated through Cockpit | Operator submits intent, UMH generates packets | Phase 14.6G AC-4 |

**EOS implementation begins ONLY after all 6 conditions are met.**

### CreatorOS: When Can Implementation Begin?

| Condition | Required State | Source |
|-----------|---------------|--------|
| UMH Stage 1 Wave 3 complete | All 50 acceptance criteria pass | Phase 14.6G AC |
| EOS Clerk auth proven in production | EOS login/auth flow working with Clerk | DEC-146B-COS-002 |
| Source baseline verified and pushed to GitHub | Current CreatorOS code audited, pushed | DEC-146B-COS-003 |
| MVP scope confirmed | Content + Community + Courses + Sales modules defined | DEC-146B-COS-001 |
| Module build sequence confirmed | Auth → Split → Tests → ... sequence locked | DEC-146B-COS-004 |
| Work packets route to creatoros repo | AC-10.2 or equivalent passes | Phase 14.6G AC-10 |

**CreatorOS implementation begins ONLY after all 6 conditions are met.**

The critical dependency: CreatorOS Clerk auth is explicitly gated on EOS proving the Clerk pattern first. This is a ratified P0 decision, not a suggestion.

### LyfeOS: When Can Clerk Migration Begin?

| Condition | Required State | Source |
|-----------|---------------|--------|
| UMH Stage 1 Wave 3 complete | All 50 acceptance criteria pass | Phase 14.6G AC |
| CreatorOS Clerk migration complete | CreatorOS proven Clerk in production | DEC-146B-LOS-002 |
| PRD v2.0 canonical | Current PRD version locked as baseline | DEC-146B-LOS-001 |
| Fly.io infrastructure confirmed | Trinity standard deployment documented | DEC-146B-LOS-003 |
| Current Passport.js + Firebase state documented | Migration source state locked | LyfeOS auth canon |

**LyfeOS Clerk migration begins ONLY after all 5 conditions are met.**

The critical dependency: LyfeOS migration is explicitly gated on CreatorOS proving the Clerk pattern. Two ratified P0 decisions (COS-002 and LOS-002) create a sequential dependency chain.

## What Remains Blocked

| Item | Blocked Until |
|------|-------------|
| Writing code in saas/ | EOS gate conditions met |
| Writing code in creatoros repo | CreatorOS gate conditions met |
| Running LyfeOS Clerk migration | LyfeOS gate conditions met |
| Any projection schema migration | Stage 1 complete + explicit operator approval |
| Projection deployment to Fly.io | Stage 1 complete + explicit operator approval |
| Projection-specific Cockpit views | Stage 1 complete (projection views register through universal interface) |

## What Can Be Prepared Now (Without Implementation)

| Activity | Why Allowed |
|----------|-------------|
| Document EOS Beast branch state | Read-only audit, no code changes |
| Document CreatorOS source baseline | Read-only audit, per DEC-146B-COS-003 |
| Document LyfeOS current auth state | Read-only audit, per LyfeOS canon |
| Update canon artifacts with implementation notes | Canon revision, not implementation |
| Create EOS/CreatorOS/LyfeOS work packet templates | Templates, not execution |

## Projection Agnosticism Requirement

The UMH Stage 1 work packet routing system MUST be projection-agnostic. This means:

1. No `if projection == "EOS"` branching in substrate/ or organism/ code
2. Projections register their file paths and capabilities at runtime
3. The same work packet generation, routing, approval, and verification pipeline handles all projections
4. Architecture layer law enforcement is automatic via pre-commit gates
5. Adding a new projection requires registration, not code changes in the substrate

This is verified by acceptance criterion AC-10.5: "No hardcoded EOS-only logic in work packet routing; projection-agnostic."
