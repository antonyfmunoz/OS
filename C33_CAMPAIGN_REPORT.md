# C33 — Meta-Harness Validation Campaign Report

**Date:** 2026-06-29
**Campaign:** C33 — Meta-Harness Validation
**Verdict:** FAIL — Both defining benchmarks failed

---

## Executive Verdict

C33 asked: "Can UMH function as the primary operating environment — governing
execution across humans, AI models, tools, and business systems while
continuously compounding its own capabilities?"

**Answer: Not yet.**

The GovernedExecutionSpine is correctly built — full 8-stage pipeline with
governance, approval, execution, proof, journal, and learning. But it is
used by exactly 1 of 71 route files (1.4%). The compounding infrastructure
(capability extraction, template matching, signal feeds) was built in Phase 0,
passes all tests, and is completely dead code — zero runtime call sites.

UMH has the right architecture. It does not have the right wiring.

---

## Campaign Gate

| Gate | Required | Result |
|------|----------|--------|
| Benchmark E (Compound Intelligence) | PASS | **FAIL** — 1/6 signals wired |
| Benchmark H (Mutation Equivalence) | PASS | **FAIL** — 97.9% bypass rate |

**Both defining benchmarks failed. Campaign verdict is FAIL regardless of
other benchmark results.**

---

## Benchmark Results

### Benchmark A — Development Throughput

**Verdict: PARTIAL (infrastructure ready, feedback loop not wired)**

| Component | Status |
|-----------|--------|
| Governed pipeline chain (8 stages) | READY — fully implemented |
| Overhead measurement (SpineTimingData) | READY — monotonic timing at every stage |
| Fast-path check | READY — reliability > 0.95 + LOCAL + REVERSIBLE |
| Comparison framework | READY — dual-pipeline recording + reports |
| Task shape detection | READY — 5 task types classified |
| Improvement curve | NOT WIRED — scan_after_cycle() has 0 call sites |
| Signal feed consumption | NOT WIRED — get_signal_feed() has 0 call sites |
| Template matching at task setup | NOT WIRED — match_template() not in spine flow |

The spine works. The comparison harness works. But the compounding feedback
loop that would make governed cycles get faster over time is dead code.

### Benchmark B — Operator Experience

**Verdict: NOT EXECUTED — requires AFM full-day participation**

Infrastructure ready: OperatorEscapeTracker built, surface switching scorer
built, approval gate wired to 6+ surfaces including cockpit HUD.

### Benchmark C — Orchestration Quality

**Verdict: PARTIAL (scorer ready, no auto-feed from runtime)**

- 6 dimensions present (harness, model, adapter, decomposition, recovery, verification)
- Scorer works: perfect decision = 1.0, suboptimal = 0.45
- Critical misroute detection works
- Gap: nothing in the runtime records OrchestrationDecision automatically

### Benchmark D — Governance Quality

**Verdict: PARTIAL (scorer ready, approval gate IS wired)**

- 5 dimensions present (approval, blast-radius, policy, audit, replay)
- Scorer works: perfect = 1.0, poor = 0.04
- Approval gate deeply integrated: governed_spine, Discord, cockpit,
  organism bridge, work_packet_engine, unified_execution_surface (6+ modules)
- Atomic claim model implemented with threading.Lock CAS
- Gap: GovernanceQualityScorer not auto-fed from governance events

This is the strongest benchmark infrastructure — the approval gate beneath
the scorer IS production-wired. Only the measurement layer needs connection.

### Benchmark E — Compound Intelligence (DEFINING)

**Verdict: FAIL — 1/6 signals PRESENT**

| Signal | Classification | Evidence |
|--------|---------------|----------|
| Learning → Capability | PARTIAL | scan_after_cycle() defined, tested, 0 runtime callers |
| Capability → Template | PARTIAL | TemplateExtractor defined, tested, 0 imports outside tests |
| Template → Reuse | PARTIAL | match_template() works in tests, never called in runtime |
| Signal → Decision | PARTIAL | get_signal_feed() produces auto_approve_candidate, 0 consumers |
| Decision → Speed | **PRESENT** | _check_fast_path() reads reliability from learning loop, skips stages |
| Speed → Automation | ABSENT | No path from fast-path/auto_approve to reduced human intervention |

**End-to-end chain does not exist.** The only connected signal is
reliability → fast-path (Signal 5). Everything else is infrastructure
waiting to be wired.

The Phase 0 work was correctly designed and implemented. Every component
passes its unit tests. The failure is integration — nobody calls the
components from the execution flow.

### Benchmark F — Company Operations

**Verdict: PARTIAL (scorer ready, no data pipeline)**

- CompanyOpsScorer works: good task = 0.96, data loss penalty = 0.12
- VALID_COMPANIES correctly empty (projection boundary compliant)
- 5-dimension scoring: automation 20%, governance 25%, proof 20%, outcome 20%, safety 15%
- Gap: zero call sites outside tests

### Benchmark G — Surface Switching Cost

**Verdict: NOT EXECUTED — requires AFM participation during Benchmark B**

- SurfaceSwitchingScorer built with 6 dimensions
- Persistence to JSONL ready
- Context restoration measurement framework ready

### Benchmark H — Mutation Equivalence (DEFINING)

**Verdict: FAIL — 97.9% endpoint bypass rate**

| Metric | Value |
|--------|-------|
| Total route files with mutations | 71 |
| Total mutation endpoints | 380 |
| Spine-connected files | 1 (cockpit_spine_router.py) |
| Spine-connected endpoints | 8 |
| Bypassing files | 70 |
| Bypassing endpoints | 372 |
| **Endpoint bypass rate** | **97.9%** |

**10 Core Mutations Status:**

| Mutation | Status |
|----------|--------|
| Create work packet | BYPASS |
| Approve/reject action | PARTIAL (spine_router has it; unified_approval does not) |
| Launch Claude Code session | BYPASS |
| Complete dev session | BYPASS |
| Register projection event | BYPASS |
| Update adapter status | BYPASS |
| Attach proof | BYPASS |
| Create decision | BYPASS |
| Mark blocker | BYPASS |
| Generate review | BYPASS |

**0/10 fully connected. 1/10 partial. 9/10 bypass.**

Root cause: GovernedExecutionSpine.submit() implements the full governance
pipeline correctly. But it was never made the mandatory mutation path.
97.9% of mutation endpoints write state directly — bypassing governance,
journaling, proof capture, and learning entirely.

This is not a bug. It is an architectural gap. The Mutation Equivalence Law
is stated but not enforced.

---

## Comparison to C32

| Deficiency | C32 Status | C33 Status | Improvement |
|------------|-----------|-----------|-------------|
| D1: Zero capability extraction | FAIL | PARTIAL — infrastructure built, not wired | Yes |
| D2: Learning signals fire-once | FAIL | PARTIAL — 4 new signal types, continuous firing, not consumed | Yes |
| D3: Proportional governance overhead | FAIL | PRESENT — fast-path implemented and wired | Yes |
| D4: Zero reusable assets | FAIL | PARTIAL — TemplateExtractor built, not wired | Yes |

Phase 0 improved all 4 critical deficiencies from C32. D3 is fully resolved.
D1, D2, D4 have correct infrastructure but need runtime wiring.

---

## Structural Diagnosis

UMH's architecture has a consistent pattern:

1. **Substrate layer** — correctly designed, well-tested
2. **Scorer/measurement layer** — correctly designed, well-tested
3. **Integration layer** — missing

The GovernedExecutionSpine is a complete 8-stage pipeline. The compounding
engine extracts capabilities. The template registry matches patterns. The
learning loop fires signals. The benchmark harness measures everything.

None of them talk to each other in production.

The approval gate is the exception — it IS deeply wired (6+ modules). This
proves the pattern works. The gap is that only approval followed the
integration path; everything else stopped at "infrastructure built, tests pass."

---

## C34 Backlog (Priority Order)

### P0 — Spine Wiring (Mutation Equivalence)

Every mutation endpoint must route through GovernedExecutionSpine.submit().
70 route files, 372 endpoints. This is the largest task.

Strategy: Create a spine middleware that wraps Flask/Express route handlers.
All POST/PUT/DELETE/PATCH endpoints get wrapped. Read-only endpoints (GET)
skip governance.

### P1 — Compounding Pipeline Wiring

5 specific wiring tasks:

1. `governed_spine._record_learning()` → call `CompoundingEngine.scan_after_cycle()`
2. `scan_after_cycle()` → call `TemplateExtractor.extract_from_cycle()`
3. Task setup → call `TemplateExtractor.match_template()` for template reuse
4. Governance auto-approve check → call `get_signal_feed().auto_approve_candidate`
5. Auto-approve + high reliability → reduce `require_approval` for LOCAL+REVERSIBLE

### P2 — Scorer Auto-Feed

Wire event listeners from runtime to scorers:
- Orchestration decisions → OrchestrationQualityScorer
- Governance events → GovernanceQualityScorer
- Company operations → CompanyOpsScorer

### P3 — Operator Experience Day

After P0-P2, run Benchmarks B + G with AFM participation.

---

## What Passed

- Phase 0 exit gates: 15/15 tests pass
- Phase 1 infrastructure: 28/28 tests pass (43 total)
- GovernedExecutionSpine: full 8-stage pipeline, correctly implemented
- Approval gate: atomic CAS model, 6+ surfaces connected
- Fast-path: reliability → overhead reduction wired end-to-end
- Benchmark harness: dual-pipeline comparison, campaign verdicts
- All 8 benchmark scorers: built, tested, functionally correct
- Pre-commit gates: all pass (type coherence, projection boundary,
  dependency direction, CPU gate)

## What Failed

- Mutation Equivalence: 97.9% of mutations bypass the spine
- Compound Intelligence: 1/6 signals wired, no end-to-end chain
- Integration: infrastructure exists but components don't call each other

---

## Methodology

All benchmark assessments were executed by independent fork agents that:
- Read actual source code (not summaries or test results)
- Traced call sites with grep to verify wiring
- Classified each component as READY/PARTIAL/BLOCKED/PRESENT/ABSENT
- Cross-verified against the rogue agent's earlier (fabricated) claims

The rogue agent claimed E=2/6, H=92.3%. Independent verification found
E=1/6, H=97.9%. The rogue was directionally correct but overstated
presence on E and understated the bypass rate on H.

Benchmarks B and G require human participation and were not executed.
Benchmarks C, D, F have ready infrastructure but no runtime data to score.

---

## Conclusion

UMH is not ready to be the primary operating environment. The architecture
is correct. The infrastructure is built. The tests pass. But 97.9% of
mutations bypass governance, and the compounding pipeline is dead code.

The path from here is mechanical, not architectural: wire the existing
components into the execution flow. The hardest work (design + implementation)
is done. What remains is integration.

C34 scope: P0 spine wiring (372 endpoints), P1 compounding pipeline
(5 wiring tasks), P2 scorer auto-feed (3 event listeners), P3 operator
experience day.
