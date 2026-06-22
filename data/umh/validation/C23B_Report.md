# Campaign 23B — UMH vs Industry Benchmark Suite

## Status: COMPLETE

All 7 phases delivered. 579 tests passing (326 new + 253 C23A zero regressions).

## What Was Built

### Competitive Data Layer (Phase 1)
- `competitive.py` (273 LOC) — CompetitorRegistry, MarketCategory, CategoryScore, CompetitiveMatrix
- `competitors.json` — 13 competitor profiles (Claude Code, Codex, Cursor, Devin, OpenHands, Windsurf, Augment, Roo Code, Cline, Aider, Antigravity, Replit, Cursor Origin)
- `industry_benchmarks.json` — 4 benchmarks with published scores (SWE-bench Verified/Pro, Terminal-Bench, Aider Polyglot)

### External Benchmark Adapters (Phase 2)
- `external_adapters.py` (363 LOC) — 5 adapters: SWEBenchAdapter, TerminalBenchAdapter, WebArenaAdapter, GAIAAdapter, BrowseCompAdapter
- Synthetic test mode with 5 tasks each; real dataset loading is follow-up
- ADAPTER_REGISTRY + get_adapter() factory

### Production Benchmarks (Phase 3)
- `autonomous_execution.py` (85 LOC) — Category B: session depth, recovery, autonomy
- `outcome_accuracy.py` (87 LOC) — Category N: intent achievement rate
- `efficiency.py` (117 LOC) — Category Q: capability per dollar, cost trend
- `reliability.py` (94 LOC) — Category R: success variance, consistency score

### Organism Audits (Phase 4)
- `context_capacity.py` (181 LOC) — Category C: graph/summary coverage
- `operational_awareness.py` (87 LOC) — Category D: service state accuracy
- `source_truth.py` (138 LOC) — Category I: 9-stage lineage completeness
- `organism_awareness.py` (129 LOC) — Category L: self-model accuracy
- `empire_readiness.py` (196 LOC) — Category P: future projection coverage

### Reality Model + Strategic (Phase 5)
- `model_correspondence.py` (164 LOC) — Category T: predicted vs observed reality
- `strategic_compression.py` (91 LOC) — Category O: intent-to-execution ratio
- `human_amplification.py` (131 LOC) — Category S: capability expansion beyond speed

### Composite Scorer (Phase 6)
- `composite_scorer.py` (245 LOC) — 7 domain scores + overall, tier-weighted, gap analysis, market category comparison
- Extended BENCHMARK_TYPES (8 → 22 types)

### API Routes (Phase 7)
- 8 new routes on cockpit_validation_routes.py:
  - `/validation/competitive/matrix`
  - `/validation/competitive/competitors`
  - `/validation/competitive/gap-analysis`
  - `/validation/competitive/category/{id}`
  - `/validation/competitive/market/{category}`
  - `/validation/composite`
  - `/validation/external/{name}/latest`
  - `/validation/audits/{name}/latest`

## Numbers

| Metric | Count |
|---|---|
| New source files | 15 |
| New data files | 2 |
| Modified files | 2 |
| New test files | 6 |
| Production LOC | 2,823 |
| Test LOC | 2,468 |
| Total new LOC | 5,291 |
| C23B tests | 326 |
| C23A tests | 253 |
| **Total tests** | **579 (all passing)** |

## The Three Questions

1. **Can I trust it?** (R — Reliability) — success variance, failure frequency, recovery rate, consistency score
2. **Does it make me stronger?** (S — Human Amplification) — capability expansion rate, complexity ceiling with/without UMH
3. **Is its model of reality correct?** (T — Model Correspondence) — 5-dimension accuracy, drift detection, best/worst domain

## What's Unique to UMH

Categories where no competitor scores (only UMH measures these):
- F: Capability Reuse
- I: Source Truth (lineage completeness)
- J: Compounding
- K: Projection Readiness
- L: Organism Awareness
- M: Reality Recovery
- O: Strategic Compression
- P: Empire Readiness
- S: Human Amplification
- T: Model Correspondence

10 out of 20 categories are UMH-unique. No competitor even attempts to measure them.

## Architecture

All code follows UMH laws: no substrate imports from transports/services, no instance context, no projection names in substrate, Python 3.11 compatible, all scoring deterministic (zero LLM calls).
