# Campaign 13 — Prediction Intelligence & Future State Modeling

## Context

Campaigns 5-12 built a complete retrospective and present-state intelligence stack:

```
Reality (C5) → Operations (C6) → Strategy (C7) → Goals (C8) →
Decisions (C9) → Capabilities (C10) → Work (C11) → Learning (C12)
```

**The gap:** UMH can explain the past and assess the present. It cannot model the future. C13 creates deterministic prediction intelligence — rule-based future-state modeling from goal trajectories, decision validity, capability maturity, execution readiness, learning patterns, and historical outcome rates. Zero LLM calls.

**Critical constraint:** ProjectionEngine (`substrate/organism/projection_engine.py`, 1449 LOC) already exists with trend detection, projection generation, risk/opportunity detection, and accuracy tracking. C13 **composes** ProjectionEngine — it does NOT recreate it.

---

## Architecture — 4 Phases

### C13.0 — TrajectoryIntelligenceRuntime (~700 LOC)

**File:** `substrate/organism/trajectory_intelligence_runtime.py`

**Purpose:** Compute probable future trajectories for goals, capabilities, work, and learning by enriching ProjectionEngine output with cross-subsystem context.

**New types (2):**
- `TrajectoryStatus(str, Enum)` — ACCELERATING, STABLE, SLOWING, STALLED, DECLINING
- `TrajectoryForecast` dataclass — entity_id, entity_type, current_state, projected_state, confidence, status, contributing_factors, forecast_horizon_days, generated_at

**Composes (7 subsystems):**
- `ProjectionEngine` → `run_projections()`, `get_projection_state()`
- `OutcomeTrackingRuntime` → `completion()`, `goals_at_risk()`
- `GoalDriftEngine` → `detect()`, `drift_for_goal()`
- `DecisionValidityEngine` → `evaluate_all()`, `at_risk()`
- `CapabilityEvolutionEngine` (C12.2) → `trajectory()`, `advancing()`, `declining()`, `stalled()`
- `LearningPortfolioRuntime` (C12.3) → `lesson_velocity()`, `health()`
- `WorkPortfolioRuntime` (C11.2) → `completions_per_day()`, `velocity()`

**Status classification (deterministic):**
- ACCELERATING: positive trend + high confidence + no drift + learning velocity above threshold
- STABLE: neutral/positive trend + moderate confidence + low drift
- SLOWING: positive trend BUT declining velocity OR increasing drift
- STALLED: no change over window + drift warnings present
- DECLINING: negative trend OR high drift + invalid decisions + capability decline

**Public API:** `forecast_goal(goal_id)`, `forecast_capability(cap_id)`, `forecast_work()`, `forecast_learning()`, `forecast_all()`, `at_risk_trajectories()`, `trajectory_summary()`, `health()`

---

### C13.1 — ScenarioIntelligenceEngine (~850 LOC)

**File:** `substrate/organism/scenario_intelligence_engine.py`

**Purpose:** Generate deterministic future-state scenarios via rule-based branching.

**New types (2):**
- `ScenarioType(str, Enum)` — BEST_CASE, EXPECTED, WORST_CASE, DISRUPTION
- `FutureScenario` dataclass — scenario_id, scenario_type, title, assumptions, projected_outcomes, probability, risks, opportunities, affected_goals, generated_at

**Composes (7 subsystems):**
- `TrajectoryIntelligenceRuntime` (C13.0) → `forecast_all()`, `at_risk_trajectories()`
- `DecisionValidityEngine` → `at_risk()`, `invalid()`
- `WorkPortfolioRuntime` → `at_risk_work()`, `velocity()`
- `CapabilityPortfolioRuntime` → `health()`
- `LearningPortfolioRuntime` → `compounding_score()`
- `StrategicPlanningEngine` → `roadmap()`
- `RiskEngine` → `detect_risks()`, `high_risks()`

**Scenario generation rules:**
- BEST_CASE: all accelerating/stable trajectories hold, at-risk decisions resolve, high learning compounding, no high risks materialize. P = avg(confidence) * capability_health * (1 - high_risk_ratio)
- EXPECTED: trajectories hold current status, 50% decision resolution, current velocity. P = avg(confidence)
- WORST_CASE: declining trajectories worsen, at-risk decisions fail, high risks materialize, velocity drops. P = risk_rate * (1 - avg_confidence)
- DISRUPTION: invalid decisions cascade, multiple high risks co-occur, capability gaps widen. Low probability.

**Public API:** `generate()`, `best_case()`, `expected_case()`, `worst_case()`, `disruption_case()`, `compare()`, `summary()`

---

### C13.2 — PredictionPortfolioRuntime (~700 LOC)

**File:** `substrate/organism/prediction_portfolio_runtime.py`

**Purpose:** Portfolio-level prediction health + drift detection. Read-only composition facade.

**New types (4):**
- `PredictionHealth(str, Enum)` — HIGH_CONFIDENCE, STABLE, UNCERTAIN, VOLATILE, BLIND
- `PredictionDriftType(str, Enum)` — FORECAST_DECAY, SIGNAL_WEAKNESS, SCENARIO_DIVERGENCE, CONFIDENCE_COLLAPSE, TRAJECTORY_BREAK
- `PredictionDriftWarning` dataclass — drift_type, severity, description, affected_ids, recommendation
- `PredictionPortfolioSnapshot` dataclass — forecast_count, scenario_count, prediction_health, average_confidence, uncertainty_index, drift_warnings, top_forecasts, critical_risks, generated_at

**Composes (6 subsystems):**
- `TrajectoryIntelligenceRuntime` (C13.0) → `forecast_all()`, `at_risk_trajectories()`, `trajectory_summary()`, `health()`
- `ScenarioIntelligenceEngine` (C13.1) → `generate()`, `compare()`
- `LearningPortfolioRuntime` → `compounding_score()`
- `CapabilityPortfolioRuntime` → `health()`
- `WorkPortfolioRuntime` → `health()`
- `StrategicMemoryEngine` → `detect_patterns()`

**Drift detectors (5):**
1. FORECAST_DECAY — avg confidence < 0.3
2. SIGNAL_WEAKNESS — fewer than 3 subsystems returning data
3. SCENARIO_DIVERGENCE — best/worst probability gap > 0.7
4. CONFIDENCE_COLLAPSE — avg confidence < 0.15
5. TRAJECTORY_BREAK — any trajectory changed 2+ levels in one cycle

**Health classification:** HIGH_CONFIDENCE (conf>0.7, 0 drift) → STABLE (>0.5, ≤1) → UNCERTAIN (>0.3, ≤3) → VOLATILE (>0.15 or >3 drift) → BLIND (≤0.15 or <3 subsystems)

**No persistence** — predictions are ephemeral, recomputed on demand.

**Public API:** `snapshot()`, `health()`, `uncertainty_index()`, `drift_warnings()`, `highest_risk_forecasts(limit=5)`, `summary()`

---

### C13.3 — Cockpit + Integration

#### Routes: `transports/api/cockpit_prediction_routes.py` (~200 LOC)

Lazy singletons for 3 runtimes. 10 endpoints under `/prediction/`:

| Endpoint | Returns |
|----------|---------|
| `/prediction/overview` | portfolio snapshot + scenario summary |
| `/prediction/forecasts` | all trajectory forecasts |
| `/prediction/forecast/{entity_id}` | single forecast |
| `/prediction/scenarios` | all 4 scenarios |
| `/prediction/scenarios/best` | best-case |
| `/prediction/scenarios/expected` | expected-case |
| `/prediction/scenarios/worst` | worst-case |
| `/prediction/drift` | prediction drift warnings |
| `/prediction/health` | prediction health string |
| `/prediction/uncertainty` | uncertainty index float |

#### Frontend

**Store:** `cockpit/src/renderer/stores/predictionStore.ts` (~150 LOC) — zustand, interfaces matching Python snake_case, fetchAll via Promise.all

**Panel:** `cockpit/src/renderer/panels/PredictionPanel.tsx` (~300 LOC) — 5 tabs: Overview, Forecasts, Scenarios, Risk, Confidence. wv-card CSS. Health color map. Status color coding (ACCELERATING=green, STABLE=blue, SLOWING=yellow, STALLED=orange, DECLINING=red).

#### Integration Touches

**ExecutiveBrief** (`executive_brief_runtime.py`):
- Add fields: `prediction_health: str`, `top_forecasts: list[str]`, `critical_future_risks: list[str]`
- Add `_fill_prediction()` method (lazy import PredictionPortfolioRuntime)
- Call after `_fill_learning()` in `generate()`

**StrategicContext** (`strategic_context_runtime.py`):
- Add field: `prediction_health: dict[str, Any]`
- Add `_fill_from_prediction_system()` method
- Call after `_fill_from_learning_system()` in `build()`

**cockpit.py:** Add `_mount_prediction_router()` after `_mount_learning_router()`

**cockpitStore.ts:** Add `| 'prediction'` to Panel type after `'learning'`

**Shell.tsx:** Add `import { PredictionPanel }` + `case 'prediction': return <PredictionPanel />`

---

## Type Registration

11 new types in `substrate/canonical_types.py`:

```
# ── Campaign 13: Prediction Intelligence ──────────────────────────
TrajectoryStatus, TrajectoryForecast, TrajectoryIntelligenceRuntime
ScenarioType, FutureScenario, ScenarioIntelligenceEngine
PredictionHealth, PredictionDriftType, PredictionDriftWarning,
PredictionPortfolioSnapshot, PredictionPortfolioRuntime
```

---

## Files

**Created (11):**
1. `substrate/organism/trajectory_intelligence_runtime.py`
2. `substrate/organism/scenario_intelligence_engine.py`
3. `substrate/organism/prediction_portfolio_runtime.py`
4. `transports/api/cockpit_prediction_routes.py`
5. `cockpit/src/renderer/stores/predictionStore.ts`
6. `cockpit/src/renderer/panels/PredictionPanel.tsx`
7. `tests/test_trajectory_intelligence_runtime.py`
8. `tests/test_scenario_intelligence_engine.py`
9. `tests/test_prediction_portfolio_runtime.py`
10. `tests/test_prediction_routes.py`

**Modified (6):**
1. `substrate/canonical_types.py` — 11 new type registrations
2. `substrate/organism/executive_brief_runtime.py` — 3 fields + `_fill_prediction()`
3. `substrate/organism/strategic_context_runtime.py` — 1 field + `_fill_from_prediction_system()`
4. `transports/api/cockpit.py` — `_mount_prediction_router()`
5. `cockpit/src/renderer/stores/cockpitStore.ts` — `'prediction'` in Panel type
6. `cockpit/src/renderer/components/Shell.tsx` — prediction case + import

---

## Build Order

```
C13.0 (Trajectory)  → composes only existing subsystems
C13.1 (Scenario)    → depends on C13.0
C13.2 (Portfolio)   → depends on C13.0 + C13.1
C13.3 (Cockpit)     → depends on all above
```

---

## Engineering Attention

| Phase | Weight | Rationale |
|-------|--------|-----------|
| C13.0 Trajectory | 30% | Cross-subsystem enrichment is the novel core |
| C13.1 Scenario | 35% | Intellectual core — deterministic scenario branching rules |
| C13.2 Portfolio | 20% | Composition facade + drift detection |
| C13.3 Cockpit | 15% | Mechanical pattern replication |

---

## Estimated Scope

| Phase | LOC | Tests |
|-------|-----|-------|
| C13.0 Trajectory Intelligence | ~700 | ~35 |
| C13.1 Scenario Intelligence | ~850 | ~40 |
| C13.2 Prediction Portfolio | ~700 | ~35 |
| C13.3 Cockpit + Integration | ~650 | ~20 |
| **Total** | **~2,900** | **~130** |

---

## Invariants

- **Deterministic-first:** Zero LLM calls
- **Read-only:** No mutation, no execution authority
- **Composition:** ProjectionEngine remains projection authority; C13 enriches
- **Constructor injection:** `Any | None = None` for every dependency
- **Error isolation:** try/except with logger.debug() on all subsystem calls
- **Python 3.11:** No 3.12+ syntax
- **No persistence:** Predictions are ephemeral — recomputed on demand

---

## Verification

1. `python3 -m py_compile` each new .py file
2. `pytest tests/test_trajectory_intelligence_runtime.py tests/test_scenario_intelligence_engine.py tests/test_prediction_portfolio_runtime.py tests/test_prediction_routes.py -v`
3. `python3 scripts/check_type_divergence.py --all`
4. `python3 scripts/check_dependency_direction.py --all`
5. `python3 scripts/check_instance_leak.py --all`
6. `python3 scripts/check_projection_leak.py --all`

---

## Commit

```
feat(C13): add prediction intelligence & future state modeling — 3 runtimes, ~130 tests
```
