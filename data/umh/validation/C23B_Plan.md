# Campaign 23B — UMH vs Industry Benchmark Suite

## Context

Campaign 23A (253 tests, 5,543 LOC) built UMH's internal benchmarking framework — proving capability compounding works with numerical evidence. But before building more substrate, we need objective evidence of where UMH stands relative to the market: what we're better at, worse at, missing, and what's uniquely ours.

This is a reality-validation campaign, not a software-production campaign. It creates a quantitative scoreboard benchmarking UMH against 13 competing systems across 16 categories (A-P). The output is a competitive matrix with gap analysis — every future campaign can be justified by a measurable gap rather than intuition.

**Critical constraint:** UMH cannot run SWE-bench against Cursor or execute code inside competitor products. The approach is:
1. **Self-benchmarks**: Run UMH's own deterministic benchmarks for all 16 categories
2. **Competitive profiles**: Structured JSON data with published scores from SWE-bench, Terminal-Bench, Aider Polyglot
3. **Comparative matrix**: UMH scores alongside competitor scores where comparable, N/A where competitors lack the capability entirely

---

## What Already Exists (reuse, don't rebuild)

| C23A Benchmark | LOC | Maps to C23B Category |
|---|---|---|
| `production_quality.py` | 246 | A (Software Production), E (Quality Assurance) |
| `production_velocity.py` | 146 | A (Software Production) |
| `capability_reuse.py` | 233 | F (Capability Reuse) |
| `operator_compression.py` | 264 | G (Operator Leverage) |
| `production_outcome_quality.py` | 248 | H (Production Outcomes) |
| `compounding_proof.py` | 217 | J (Compounding) |
| `projection_readiness.py` | 196 | K (Projection Acceleration) |
| `reality_recovery.py` | 585 | M (Reality Recovery) |

Infrastructure: `CapabilityValidationRuntime` (491 LOC), `BenchmarkRun` dataclass, JSONL persistence, cockpit routes (160 LOC). All results flow through `record_run()`.

Self-awareness runtimes: `SelfModel` (478 LOC), `WorldModel` (647 LOC), `OrchestratorAwarenessRuntime` (585 LOC), `CapabilityCompoundingRuntime` (584 LOC), `CapabilityRuntime` (472 LOC), `LeverageMetrics` (262 LOC).

---

## Phase 1: Competitive Data Layer

**Goal:** Structured competitor profiles + industry benchmark scores as JSON data, plus the registry/matrix dataclasses.

**New file:** `substrate/organism/benchmarks/competitive.py` (~250 LOC)
- `CompetitorProfile` dataclass: `competitor_id`, `name`, `vendor`, `published_scores: dict[str, float]`, `capabilities: dict[str, bool]`, `sources: list[dict]`. Has `to_dict()`/`from_dict()`.
- `CategoryScore` dataclass: `category_id` (A-P), `category_name`, `umh_score` (0.0-1.0 normalized), `umh_raw: dict[str, float]`, `competitor_scores: dict[str, float | None]`, `competitor_source` ("published"/"inferred"/"n_a"). Has `to_dict()`.
- `CompetitiveMatrix` dataclass: `timestamp`, `categories: list[CategoryScore]`, `umh_composite`, `competitor_composites`, `umh_unique_categories`, `gap_analysis`. Has `to_dict()`.
- `CompetitorRegistry` class: `load()`, `get_competitor()`, `all_competitors()`, `scores_for_benchmark()`. Reads from JSON files.

**New file:** `data/umh/validation/competitive/competitors.json`
- 13 competitor profiles: Claude Code, Codex, Cursor, Cursor Origin, Replit, Devin, OpenHands, Windsurf, Augment, Roo Code (archived), Cline, Aider, Antigravity
- Each with: name, vendor, category, architecture, pricing_model, published_scores, capabilities (bool flags for autonomous_execution, self_model, capability_reuse, compounding, organism_awareness, lineage_tracking, projection_acceleration), sources with URLs and dates

**New file:** `data/umh/validation/competitive/industry_benchmarks.json`
- Published scores for: SWE-bench Verified, SWE-bench Pro, Terminal-Bench 2.1, Aider Polyglot
- Per-competitor scores from research (Claude Code 87.6% SWE-bench Verified, Codex 85%, Cursor 51.7%, Devin 45.8%, Augment 70.6%, OpenHands 68.4%, Windsurf 72.5%, etc.)

**Tests:** ~80 (registry loading, competitor queries, score retrieval, missing data, JSON schema validation)

---

## Phase 2: Comparable Self-Benchmarks (Categories B, C, D)

**Goal:** 3 new benchmarks for categories where competitors also claim capabilities, enabling direct comparison.

### `substrate/organism/benchmarks/autonomous_execution.py` (~200 LOC) — Category B
- `AutonomousExecutionResult` dataclass: `avg_session_duration_seconds`, `avg_task_depth`, `recovery_rate`, `validation_pass_rate`, `autonomous_completion_rate`
- `AutonomousExecutionBenchmark.evaluate(sessions: list[dict])` -> result
- Data source: execution_journal.jsonl, organism event log
- Measures: tasks completed without intervention, recovery from errors, validation passes

### `substrate/organism/benchmarks/context_capacity.py` (~200 LOC) — Category C
- `ContextCapacityResult` dataclass: `repo_file_count`, `graph_coverage_pct`, `cross_file_accuracy`, `history_recovery_accuracy`, `overall_accuracy`
- `ContextCapacityBenchmark.evaluate(repo_root)` -> result
- Data source: query_graph.py output (file coverage), node_summaries.json, git log
- Measures: how much of the repo is indexed, dependency graph accuracy, history question accuracy

### `substrate/organism/benchmarks/operational_awareness.py` (~200 LOC) — Category D
- `OperationalAwarenessResult` dataclass: `container_state_accuracy`, `service_health_accuracy`, `deployment_state_accuracy`, `environment_accuracy`, `overall_accuracy`
- `OperationalAwarenessBenchmark.evaluate(repo_root)` -> result
- Data source: Docker inspect, daemon_state.json, device_registry.json
- Reuses `_run_cmd` pattern from reality_recovery.py

**Tests:** ~90 (synthetic data, edge cases, empty data, scoring math per benchmark)

---

## Phase 3: UMH-Unique Self-Benchmarks (Categories I, L, N, O, P)

**Goal:** 5 benchmarks for capabilities competitors don't have. These are what make UMH category-defining.

### `substrate/organism/benchmarks/source_truth.py` (~250 LOC) — Category I
- `LINEAGE_STAGES` constant: intent -> decision -> requirement -> packet -> code -> review -> deploy -> outcome -> capability (9 stages)
- `LineageChain` dataclass: `chain_id`, `stages_present`, `stages_missing`, `completeness`
- `SourceTruthResult` dataclass: `chains_evaluated`, `avg_completeness`, `full_chains`, `partial_chains`, `orphan_pct`, `stage_coverage: dict[str, float]`
- `SourceTruthBenchmark.evaluate(productions: list[dict])` -> result

### `substrate/organism/benchmarks/organism_awareness.py` (~220 LOC) — Category L
- `OrganismAwarenessResult` dataclass: `self_model_accuracy`, `runtime_accuracy`, `workforce_accuracy`, `subsystem_count_accuracy`, `overall_accuracy`
- `OrganismAwarenessBenchmark.evaluate(repo_root)` -> result
- Compares SelfModel/WorldModel reported state against actual filesystem/process state

### `substrate/organism/benchmarks/outcome_accuracy.py` (~180 LOC) — Category N
- `OutcomeRecord` dataclass: `production_id`, `original_intent`, `acceptance_criteria: list[str]`, `criteria_met: list[bool]`, `tests_passed`, `deployed`
- `OutcomeAccuracyResult` dataclass: `productions_evaluated`, `intent_achievement_rate`, `deployment_success_rate`, `test_pass_rate`
- `OutcomeAccuracyBenchmark.evaluate(outcomes: list[OutcomeRecord])` -> result

### `substrate/organism/benchmarks/strategic_compression.py` (~200 LOC) — Category O
- `IntentRecord` dataclass: `intent_text`, `word_count`, `clarification_rounds`, `steps_to_execution`, `output_loc`
- `StrategicCompressionResult` dataclass: `intents_processed`, `avg_steps_to_execution`, `avg_clarification_rounds`, `direct_execution_rate`, `compression_ratio`
- `StrategicCompressionBenchmark.evaluate(intent_records: list[IntentRecord])` -> result

### `substrate/organism/benchmarks/empire_readiness.py` (~180 LOC) — Category P
- Wraps existing `ProjectionReadinessBenchmark` and adds future projections (Game of Lyfe, Music, Fiction, Acquisitions)
- `EmpireReadinessResult` dataclass: `projection_scores: dict[str, float]`, `cross_projection_reuse`, `overall_readiness`, `future_projection_count`, `missing_capabilities: list[str]`
- `EmpireReadinessBenchmark.evaluate(existing_capabilities)` -> result

**Tests:** ~100 (synthetic data, lineage completeness, self-model accuracy, empty/edge cases)

---

## Phase 4: Composite Scoring + Matrix Generation

**Goal:** Aggregate all 16 categories into composite scores, generate competitive matrix, produce gap analysis.

**New file:** `substrate/organism/benchmarks/composite_scorer.py` (~300 LOC)

- `CATEGORY_WEIGHTS` dict: A-H at 0.8-1.0, I-P (UMH-unique) at 0.4-0.6
- `CATEGORY_REGISTRY` dict: maps category_id -> name, benchmark_types list, comparable flag
- `CompositeScorer` class:
  - `__init__(registry: CompetitorRegistry, validation_runtime: CapabilityValidationRuntime)`
  - `score_category(category_id) -> CategoryScore` — pulls latest benchmark run, normalizes 0-1
  - `score_all_categories() -> list[CategoryScore]`
  - `compute_composite(category_scores) -> float` — weighted average
  - `generate_matrix() -> CompetitiveMatrix` — full scoreboard
  - `gap_analysis(matrix) -> list[dict]` — where UMH wins/loses/is unique

**Normalization rules:**
- Comparable categories (A-H, N): natural scale (F1, accuracy, rate are already 0-1)
- UMH-unique categories (I, J, K, L, M, O, P): scored 0-1 against own rubric; competitors get `null` (not 0)
- Composite: weighted average. Missing competitor categories flagged as "structural gap" not "performance gap"

**Modify:** `capability_validation_runtime.py` — extend `BENCHMARK_TYPES` frozenset with 9 new types

**Composite scores generated:**
- Software Production Score (A, E)
- Autonomy Score (B)
- Awareness Score (C, D, L, M)
- Compounding Score (F, J, K)
- Outcome Score (H, N)
- Reality Score (I, O, P)
- UMH Overall Score (all 16, weighted)

**Tests:** ~70 (composite math, normalization, gap detection, weight sensitivity, missing data)

---

## Phase 5: API Routes + Report Generation

**Goal:** Expose competitive matrix via cockpit API and generate deliverable reports.

**Modify:** `transports/api/cockpit_validation_routes.py` — add 5 new routes to existing `_build_router`:
- `GET /validation/competitive/matrix` — full competitive matrix
- `GET /validation/competitive/competitors` — all competitor profiles
- `GET /validation/competitive/gap-analysis` — where UMH wins/loses
- `GET /validation/competitive/category/{category_id}` — single category deep-dive
- `GET /validation/composite` — composite scores (7 domain scores + overall)

All routes use existing `require_operator_dep` auth and lazy `_get_runtime()` pattern.

**Tests:** ~50 (route response shapes, auth, error cases, integration)

---

## Estimated Totals

| Metric | Count |
|---|---|
| New files | 11 (8 benchmarks + 1 composite + 2 JSON data) |
| Modified files | 2 (capability_validation_runtime.py, cockpit_validation_routes.py) |
| New LOC | ~2,530 |
| New tests | ~390 |
| Phases | 5 |
| Reused from C23A | 2,135 LOC (8 benchmarks) + 492 LOC (runtime) + 160 LOC (routes) |

---

## Verification

1. All existing C23A tests still pass (253 tests — zero regressions)
2. All new C23B tests pass (~390 tests)
3. `CompetitorRegistry.load()` returns 13 competitors with complete profiles
4. Each of 8 new benchmarks produces numerical scores from synthetic data
5. `CompositeScorer.generate_matrix()` returns a `CompetitiveMatrix` with all 16 categories scored
6. Gap analysis identifies at least 1 win, 1 loss, and 1 unique UMH capability
7. All 5 new API routes return valid JSON with auth enforced
8. `BENCHMARK_TYPES` contains all 17 types (8 existing + 9 new)
9. No subjective scoring anywhere — every metric is computed from data
10. Pre-commit gates pass (dependency direction, type coherence, projection boundary, instance context, CPU gate)

---

## Answers This Campaign Produces

1. What is UMH already better at? -> Categories where UMH score > competitor scores
2. What is UMH worse at? -> Categories where competitors score higher
3. What capabilities are missing? -> Gap analysis missing_capabilities list
4. What competitors have advantages? -> Per-category competitor leaders
5. What is uniquely UMH? -> Categories I-P where competitors score null
6. What is the shortest path to category-defining? -> Strategic recommendations from gap analysis
7. What is the highest leverage next experiment? -> Highest-weight gap with feasible closure path
