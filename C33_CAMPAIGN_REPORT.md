# C33 Meta-Harness Validation Campaign — Report

**Date:** 2026-06-29
**Campaign:** C33 — Meta-Harness Validation
**Predecessor:** C32 (FAIL — benchmarked UMH as "slower Claude Code")
**Reframe:** Benchmark UMH as what it is — a governed meta-harness

---

## Executive Verdict

### FAIL — Compounding + Governance Bypass

Both defining benchmarks (E and H) failed. UMH is not ready to be the default operating environment.

**Benchmark E (Compound Intelligence): FAIL** — 2/6 signals present. Core thesis not proven. The compounding pipeline exists structurally but has not produced an end-to-end chain.

**Benchmark H (Mutation Equivalence): FAIL** — 92.3% mutation route bypass rate. 12 of 13 mutation-bearing route files bypass the GovernedExecutionSpine entirely. Only `cockpit_unified_approval_routes.py` is spine-connected.

**Campaign Verdict:** Per C33 rules — if E or H fail, UMH is not ready regardless of dev speed. Both failed.

---

## Benchmark Results

### Benchmark E — Compound Intelligence (DEFINING)

**Verdict: FAIL — 2/6 signals present**

| Signal | Evidence | Present |
|--------|----------|---------|
| Learning to Capability | 6 capabilities in capabilities.jsonl | YES |
| Capability to Template | templates.jsonl not found | NO |
| Template to Reuse | No template reuse recorded | NO |
| Signal to Decision | 6 auto-approve candidates in signal_feed.jsonl | YES |
| Decision to Speed | No governed execution timing data | NO |
| Speed to Automation | No fast-path activations recorded | NO |

**Root cause:** Compounding pipeline exists in code but is not wired into the main execution loop.

### Benchmark H — Mutation Equivalence (DEFINING)

**Verdict: FAIL — 92.3% mutation route bypass rate**

| Metric | Value |
|--------|-------|
| Total route files | 136 |
| Mutation route files | 13 |
| Query-only route files | 123 |
| Spine-connected | 1 (7.7%) |
| Bypassing | 12 (92.3%) |

**Root cause:** GovernedExecutionSpine exists but is not the universal mutation path.

### Benchmarks A, C, D — Not Yet Executed
Infrastructure built. Requires governed task execution for data.

### Benchmarks B, F, G — Requires Human
Frameworks ready. Requires AFM workday and real business operations.

---

## Phase 0 — D1-D4 Fixes (COMPLETE)

All 4 critical C32 deficiencies fixed. 15/15 exit gate tests pass.

## Phase 1 — Infrastructure (COMPLETE)

All 8 benchmark types have infrastructure. 28/28 tests pass.

Multi-surface atomic approval implemented (cockpit + Discord).
Harness comparison with 10 profiles and 8-entry route table.

---

## C34 Repair Backlog

1. **P0:** Wire all 12 mutation routes through GovernedExecutionSpine
2. **P1:** Wire TemplateExtractor into execution cycle
3. **P2:** Run 5+ governed tasks, measure compound chain
4. **P3:** AFM operator experience workday
5. **P4:** Real business operations through governance
6. **P5:** Surface switching test

---

## Test Summary

43 total tests pass (15 Phase 0 + 28 Phase 1/2). 0 failures.
