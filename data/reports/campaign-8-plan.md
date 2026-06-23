# Campaign 8 — Goal Systems & Strategic Planning

## Context

Campaigns 5-7 built the awareness stack: reality awareness (C5), operational awareness (C6), strategic interpretation (C7). UMH can identify what exists, what's happening, what matters, and what's drifting. But it cannot answer: **"What are we trying to achieve?"** — the bridge between operator intent and execution is missing.

Campaign 8 creates that bridge: a governed goal system, hierarchy, outcome tracking, strategic planning, alignment detection, and drift monitoring — all deterministic, read-only, composing existing subsystems.

**Critical finding:** GoalRegistry, Goal, GoalType, GoalStatus, SuccessCriterion, GapDetector, and scoring already exist in `substrate/organism/strategic_gap_engine.py` (Phase 4). Campaign 8 **evolves** the existing goal system — it does NOT create a parallel one. The Type Coherence Law makes this non-negotiable.

---

## Build Order

### C8.0 — Goal Registry Enhancement (~100 LOC changes)

**What:** Evolve existing GoalType enum and GoalRegistry to support the full goal hierarchy.

**Files to modify:**
- `substrate/organism/strategic_gap_engine.py` — extend GoalType, GoalStatus, add methods to GoalRegistry
- `substrate/canonical_types.py` — update registry entries if enum values change

**Changes:**

1. **Extend GoalType enum** (strategic_gap_engine.py:52):
   ```python
   class GoalType(str, Enum):
       VISION = "vision"
       OBJECTIVE = "objective"
       OUTCOME = "outcome"
       INITIATIVE = "initiative"
       PROJECT = "project"
       GOAL = "goal"        # keep for backward compat
       ROADMAP = "roadmap"  # keep for backward compat
       MILESTONE = "milestone"  # keep for backward compat
   ```

2. **Extend GoalStatus enum** (strategic_gap_engine.py:45):
   ```python
   class GoalStatus(str, Enum):
       DRAFT = "draft"
       ACTIVE = "active"
       COMPLETED = "completed"
       PAUSED = "paused"
       ABANDONED = "abandoned"
   ```

3. **Add methods to GoalRegistry** (strategic_gap_engine.py:342):
   - `ancestors(goal_id) -> list[Goal]` — walk parent_goal_id chain upward
   - `tree(root_id=None) -> dict` — nested dict of goal hierarchy
   - `goals_by_status(status) -> list[Goal]` — filter by status

**Tests:** ~10 new tests in existing `tests/test_strategic_gap_engine.py`

---

### C8.1 — Goal Hierarchy Engine (~250 LOC)

**New file:** `substrate/organism/goal_hierarchy_engine.py`

**Purpose:** Structural operations on the goal tree — validation, traversal, path computation.

**Class: GoalHierarchyEngine**

Constructor:
```python
def __init__(self, goal_registry: GoalRegistry | None = None) -> None:
```

Methods:
- `tree(root_id: str | None = None) -> dict` — nested tree from root
- `path(goal_id: str) -> list[Goal]` — root→leaf path
- `ancestors(goal_id: str) -> list[Goal]` — leaf→root chain
- `descendants(goal_id: str) -> list[Goal]` — all children recursively
- `validate_hierarchy() -> list[dict]` — check for orphans, cycles, missing parents
- `depth(goal_id: str) -> int` — distance from root
- `roots() -> list[Goal]` — goals with no parent (should be VISION type)
- `leaves() -> list[Goal]` — goals with no children

**Consumes:** GoalRegistry (from strategic_gap_engine.py)

**New test file:** `tests/test_goal_hierarchy_engine.py` (~30 tests)

---

### C8.2 — Outcome Tracking Runtime (~300 LOC)

**New file:** `substrate/organism/outcome_tracking_runtime.py`

**Types:**

```python
@dataclass
class OutcomeProgress:
    goal_id: str
    title: str
    goal_type: str
    percent_complete: float  # from success_criteria met ratio
    active_work_count: int
    completed_work_count: int
    blocker_count: int
    child_progress: list[dict]  # recursive child progress
    health: str  # healthy/watch/degraded/critical

@dataclass
class OutcomeSnapshot:
    goals: list[dict]
    overall_health: str
    total_active: int
    total_completed: int
    total_blocked: int
    generated_at: float
```

**Class: OutcomeTrackingRuntime**

Constructor:
```python
def __init__(
    self,
    goal_registry: Any | None = None,
    goal_hierarchy: Any | None = None,
    reality_graph: Any | None = None,
    runtime_awareness: Any | None = None,
) -> None:
```

Methods:
- `progress(goal_id: str) -> OutcomeProgress` — single goal progress
- `completion(goal_id: str) -> float` — 0-1 from success criteria
- `health(goal_id: str) -> str` — deterministic health from blockers/progress
- `snapshot() -> OutcomeSnapshot` — all active goals with progress
- `goals_at_risk() -> list[OutcomeProgress]` — below threshold or blocked

**Consumes:** GoalRegistry, GoalHierarchyEngine, RealityGraph, RuntimeAwarenessRuntime

**New test file:** `tests/test_outcome_tracking_runtime.py` (~35 tests)

---

### C8.3 — Strategic Planning Engine (~450 LOC)

**New file:** `substrate/organism/strategic_planning_engine.py`

**Types:**

```python
class PlanningStatus(str, Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BLOCKED = "blocked"
    NOT_STARTED = "not_started"

@dataclass
class StrategicMilestone:
    milestone_id: str
    title: str
    goal_id: str
    status: str
    dependencies: list[str]
    evidence: list[str]

@dataclass
class StrategicPlan:
    plan_id: str
    goal_id: str
    goal_title: str
    status: str  # PlanningStatus
    current_state: dict
    desired_state: dict
    blockers: list[str]
    milestones: list[dict]
    recommended_actions: list[str]
    risk_factors: list[str]
    generated_at: float
```

**Class: StrategicPlanningEngine**

Constructor:
```python
def __init__(
    self,
    goal_registry: Any | None = None,
    goal_hierarchy: Any | None = None,
    outcome_tracking: Any | None = None,
    priority_engine: Any | None = None,
    risk_engine: Any | None = None,
    recommendation_engine: Any | None = None,
    reality_graph: Any | None = None,
) -> None:
```

Methods:
- `generate_plan(goal_id: str) -> StrategicPlan` — plan for single goal
- `milestones(goal_id: str) -> list[StrategicMilestone]` — derived from children
- `roadmap() -> dict` — all active goals with plans, ordered by priority
- `status(goal_id: str) -> PlanningStatus` — deterministic from progress/blockers
- `snapshot() -> dict` — full planning state

**Consumes:** GoalRegistry, GoalHierarchyEngine, OutcomeTrackingRuntime, PriorityEngine, RiskEngine, RecommendationEngine, RealityGraph

Register `PlanningStatus` in `canonical_types.py`.

**New test file:** `tests/test_strategic_planning_engine.py` (~40 tests)

---

### C8.4 — Goal Alignment Engine (~300 LOC)

**New file:** `substrate/organism/goal_alignment_engine.py`

**Types:**

```python
@dataclass
class AlignmentReport:
    total_work_count: int
    linked_work_count: int
    unlinked_work_count: int
    alignment_score: float  # 0-1
    goal_coverage: dict  # goal_id → work_count
    unlinked_items: list[dict]
    generated_at: float
```

**Class: GoalAlignmentEngine**

Constructor:
```python
def __init__(
    self,
    goal_registry: Any | None = None,
    goal_hierarchy: Any | None = None,
    reality_graph: Any | None = None,
    runtime_awareness: Any | None = None,
) -> None:
```

Methods:
- `alignment_score() -> float` — ratio of linked to total work
- `unlinked_work() -> list[dict]` — work packets with no goal connection
- `goal_for_work(work_id: str) -> list[Goal]` — trace work → goal chain
- `coverage() -> dict` — which goals have active work, which don't
- `report() -> AlignmentReport` — full alignment snapshot
- `orphan_goals() -> list[Goal]` — goals with zero linked work

**Consumes:** GoalRegistry, GoalHierarchyEngine, RealityGraph, RuntimeAwarenessRuntime

**New test file:** `tests/test_goal_alignment_engine.py` (~35 tests)

---

### C8.5 — Goal Drift Engine (~350 LOC)

**New file:** `substrate/organism/goal_drift_engine.py`

**Types:**

```python
class GoalDriftType(str, Enum):
    ACTIVITY_DRIFT = "activity_drift"      # lots of work, no progress
    ALIGNMENT_DRIFT = "alignment_drift"    # work not connected to goals
    OUTCOME_DRIFT = "outcome_drift"        # goals with no active execution
    PLANNING_DRIFT = "planning_drift"      # plan not advancing

@dataclass
class GoalDriftWarning:
    drift_id: str
    goal_id: str
    goal_title: str
    drift_type: str  # GoalDriftType
    severity: str    # critical/high/medium/low
    description: str
    evidence: list[str]
    detected_at: float

@dataclass
class GoalDriftSnapshot:
    warnings: list[dict]
    high_drift_count: int
    drift_by_type: dict  # type → count
    overall_drift_health: str
    generated_at: float
```

**Class: GoalDriftEngine**

Constructor:
```python
def __init__(
    self,
    goal_registry: Any | None = None,
    goal_hierarchy: Any | None = None,
    outcome_tracking: Any | None = None,
    alignment_engine: Any | None = None,
    planning_engine: Any | None = None,
) -> None:
```

Methods:
- `detect() -> list[GoalDriftWarning]` — all drift warnings
- `high_drift() -> list[GoalDriftWarning]` — critical + high only
- `drift_for_goal(goal_id: str) -> list[GoalDriftWarning]` — single goal
- `summary() -> GoalDriftSnapshot` — aggregated snapshot

Register `GoalDriftType` in `canonical_types.py`.

**Consumes:** GoalRegistry, GoalHierarchyEngine, OutcomeTrackingRuntime, GoalAlignmentEngine, StrategicPlanningEngine

**New test file:** `tests/test_goal_drift_engine.py` (~40 tests)

---

### C8.6 — Strategic Planning Cockpit

Three new files + integration touches.

#### API Routes (~150 LOC)

**New file:** `transports/api/cockpit_goal_routes.py`

Pattern: lazy singleton _get_*() initialization, FastAPI APIRouter with `/goals` prefix.

Endpoints:
```
GET /goals              — all goals
GET /goals/{goal_id}    — single goal
GET /goals/tree         — hierarchy tree
GET /goals/active       — active goals only
GET /plans              — all strategic plans
GET /plans/{goal_id}    — plan for specific goal
GET /plans/roadmap      — full roadmap
GET /alignment          — alignment report
GET /alignment/unlinked — unlinked work items
GET /outcomes           — outcome progress snapshot
GET /outcomes/{goal_id} — single goal outcome
GET /goal-drift         — drift warnings
GET /goal-drift/high    — high severity only
```

Mount in `cockpit.py`: add `_mount_goal_router()` function after `_mount_strategic_router()`.

#### Frontend Store (~120 LOC)

**New file:** `cockpit/src/renderer/stores/goalStore.ts`

Zustand store with fetchApi pattern:
```typescript
interface GoalState {
  goals: Record<string, unknown>[]
  tree: Record<string, unknown> | null
  plans: Record<string, unknown>[]
  roadmap: Record<string, unknown> | null
  alignment: Record<string, unknown> | null
  outcomes: Record<string, unknown> | null
  drift: Record<string, unknown>[]
  loading: boolean
  fetchGoals: () => Promise<void>
  fetchTree: () => Promise<void>
  fetchPlans: () => Promise<void>
  fetchRoadmap: () => Promise<void>
  fetchAlignment: () => Promise<void>
  fetchOutcomes: () => Promise<void>
  fetchDrift: () => Promise<void>
}
```

#### Frontend Panel (~400 LOC)

**New file:** `cockpit/src/renderer/panels/GoalPanel.tsx`

Tabs: `'goals' | 'outcomes' | 'plans' | 'alignment' | 'drift'`

- **Goals tab:** Hierarchy tree view, status badges, goal type badges
- **Outcomes tab:** Progress bars per goal, health indicators
- **Plans tab:** Roadmap view, milestone timeline, status cards
- **Alignment tab:** Score gauge, linked/unlinked counts, unlinked items list
- **Drift tab:** Warning list with severity, type badges, evidence

Icons: Target (goals), TrendingUp (outcomes), Map (plans), Crosshair (alignment), AlertTriangle (drift)

#### Panel Registration

1. `cockpit/src/renderer/stores/cockpitStore.ts` — add `| 'goals'` to Panel type
2. `cockpit/src/renderer/types/routes.ts` — add route entry:
   ```typescript
   { id: 'goals', label: 'Goals', icon: Target, group: 'primary', visibility: 'primary', key: 'G' },
   ```
3. `cockpit/src/renderer/components/Shell.tsx` — add import + case:
   ```typescript
   import { GoalPanel } from '../panels/GoalPanel'
   // ...
   case 'goals':
     return <GoalPanel />
   ```

---

### Integration Touches

#### StrategicContextRuntime (strategic_context_runtime.py)

Add to StrategicContext dataclass:
```python
goal_summary: dict[str, Any] = field(default_factory=dict)
goal_alignment: dict[str, Any] = field(default_factory=dict)
```

Add constructor parameter: `goal_alignment_engine: Any | None = None`

Add fill method: `_fill_from_goal_system(ctx)` — populates goal_summary (active count, health) and goal_alignment (score, unlinked count).

#### ExecutiveBriefRuntime (executive_brief_runtime.py)

Add to ExecutiveBrief dataclass:
```python
active_goals: list[str] = field(default_factory=list)
goal_health: str = "unknown"
goal_drift: list[str] = field(default_factory=list)
```

Add constructor parameter: `goal_drift_engine: Any | None = None`, `outcome_tracking: Any | None = None`

Add fill methods: `_fill_goal_health(brief)`, `_fill_goal_drift(brief)`

#### DelegationRuntime (delegation_runtime.py)

Add optional field to DelegationProposal:
```python
goal_refs: list[str] = field(default_factory=list)  # optional goal IDs
```

Add to `to_dict()` and `from_dict()`.

#### ContextResolutionEngine (context_resolution.py)

Add to ResolvedContext:
```python
goals: list[dict[str, Any]] = field(default_factory=list)
```

Add goal name resolution in `resolve()` and `resolve_entity_reference()` — match goal titles from GoalRegistry.

#### canonical_types.py

Register new types:
- `GoalDriftType` → `substrate.organism.goal_drift_engine`
- `PlanningStatus` → `substrate.organism.strategic_planning_engine`

Update existing entries if GoalType/GoalStatus enum values changed.

---

## Estimated Scope

| Phase | LOC | Tests |
|-------|-----|-------|
| C8.0 — Goal Registry Enhancement | ~100 | ~10 |
| C8.1 — Goal Hierarchy Engine | ~250 | ~30 |
| C8.2 — Outcome Tracking Runtime | ~300 | ~35 |
| C8.3 — Strategic Planning Engine | ~450 | ~40 |
| C8.4 — Goal Alignment Engine | ~300 | ~35 |
| C8.5 — Goal Drift Engine | ~350 | ~40 |
| C8.6 — Cockpit (API + store + panel) | ~670 | — |
| Integration touches | ~150 | ~15 |
| **Total** | **~2,570** | **~205** |

---

## Hard Invariants

1. **Compose, don't rebuild** — reuse C5 RealityGraph, C6 RuntimeAwareness, C7 Strategic engines
2. **No parallel goal system** — evolve existing GoalRegistry from strategic_gap_engine.py
3. **Every plan traces to a goal**
4. **Every recommendation traces to a goal**
5. **Deterministic only. Zero LLM calls.**
6. **No execution authority. Read-only planning.**
7. **No mutation outside GoalRegistry**
8. **Python 3.11 compatible**
9. **All new types registered in canonical_types.py**

---

## Verification

After each phase:
1. `python3 -m py_compile <file>` — every new/modified file
2. `python3 -m pytest tests/test_<file>.py -v` — all new tests pass
3. `python3 scripts/check_type_divergence.py --all` — no parallel types
4. `python3 scripts/check_dependency_direction.py --all` — no layer violations
5. `python3 scripts/check_projection_leak.py --all` — no projection leaks
6. `python3 scripts/check_instance_leak.py --all` — no instance context

After C8.6:
7. `bash cockpit/deploy.sh` — cockpit builds clean (if deploying)
8. Manual verification: goal panel loads, tabs work, data renders
9. Full test suite: `python3 -m pytest tests/ -v --tb=short`
