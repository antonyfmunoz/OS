---
phase: "14.7A"
artifact: internal_production_plan
created: "2026-06-04"
product_name: "Universal Meta Harness"
---

# Phase 14.7A — Internal Production Plan

## Mission

Make UMH internally production-ready as a Jarvis-style internal operating
system loop. The operator can:

1. Use Cockpit/Jarvis as primary interface
2. Give high-level intent
3. Have UMH create/surface work packets
4. Route work packets to approved agents/tools
5. Preserve memory/source-truth/audit traces
6. Enforce approval gates for risky actions
7. View system/work packet/execution state
8. Verify outputs
9. Update memory/reality model after outcomes
10. Use UMH for governed self-improvement

## Architecture

All work is WIRING — connecting existing production substrate classes
through HTTP routes in the transport layer.

```
Operator → Cockpit HTTP → Route Layer → Substrate Classes
                                ↓
                    Reality Model / Memory / Governance
                                ↓
                    Work Packets / Execution Spine
                                ↓
                    Self-Improvement / Cadence
```

## Mutation Scope

ONLY these paths are modified:
- `transports/api/cockpit*.py` — new route modules + cockpit.py modifications
- `tests/test_phase14_7a_*.py` — test suites per wave
- `data/umh/trinity_convergence/phase14_7a_production/` — artifacts

NEVER modified:
- `substrate/` — read only (routes call, don't modify)
- `saas/` — EOS projection untouched
- `projections/` — untouched
- `services/` — no service changes
- Database schemas — no migrations

## Wave Structure

### Wave 1: Foundation Wiring
- WP-1.1: Reality model HTTP routes (15 routes)
- WP-1.2: WorldModelPanel wiring (deferred — frontend)
- WP-1.3: Memory route upgrade (typed ConversationMemory + AgentMemory)
- WP-1.4: Execution status wiring (live spine + work packet data)

### Wave 2: Organism Loop
- WP-2.1: Operator loop routes (11 routes — intent to execution)
- WP-2.2: Approval gates enforced in lifecycle
- WP-2.3: Approval UI wiring (deferred — frontend)
- WP-2.4: Audit trail (JSONL append-only)

### Wave 3: Self-Improvement Loop
- WP-3.1: Outcome → reality model assimilation
- WP-3.2: Cadence candidate supply integration
- WP-3.3: Verification pipeline
- WP-3.4: Projection build loop (follow-up generation)

## Hard Rules Enforced

1. No EOS/CreatorOS/LyfeOS feature implementation
2. No auth migrations
3. No public/customer-facing infrastructure deployment
4. No paid external infrastructure provisioning
5. No approval gate bypass
6. No unsafe autonomous execution
7. No source-truth destruction
8. No cosmetic-only cockpit work
9. No isolated component building
10. No product naming changes
