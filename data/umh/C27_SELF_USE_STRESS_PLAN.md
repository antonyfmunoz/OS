# C27 — Self-Use Stress Certification

## Context

C24 proved UMH can produce software. C25 proved UMH can operate through its cockpit loop. C26 proved UMH can verify reality and detect divergence. None of these tested whether UMH can *use itself* across the full breadth of operator tasks before Antony daily-drives it.

C27 compresses a month of daily-driver risk discovery into a controlled stress campaign: 100+ operator tasks across 15 domains, all executed through the actual cockpit UI in a browser, all outcome-verified, all gaps captured in a structured ledger.

The gap ledger is the primary deliverable — not the pass rate. The pass rate tells us where we are. The ledger tells us what to fix before C28 (30-Day Daily Driver Certification).

---

## Execution Model — Browser-Driven (NON-NEGOTIABLE)

Every task is executed through the cockpit UI in a real browser on Beast Session 1 via Playwright MCP. This is operator simulation — the test exercises the exact same path a human operator would use:

```
Browser on Beast → Cockpit UI (universalmetaharness.tech) → RightRail Chat →
  Type intent → Hono route → Python bridge → SubstrateGateway →
  CommandRuntime.submit() → Classification → Routing → Response →
  Browser observes result
```

No programmatic bypasses. No direct Python calls. The browser IS the test harness.

**Why browser-first:** Programmatic CommandRuntime.submit() tests the brain. Browser testing tests the full organism — auth, API, frontend rendering, state persistence, context assembly, and the operator experience. If the cockpit doesn't work for a human, the brain doesn't matter.

Sequential execution. Each task is typed into the cockpit chat, response observed, result verified. This is slow by design — it's how an operator uses UMH.

---

## Two-Layer Architecture

### Layer 1: Task Catalog + Taxonomy (substrate — reusable infrastructure)

The task catalog and taxonomy are substrate components that define WHAT to test. They're reusable across C27, C28, and any future self-use certification.

### Layer 2: Browser Runner + Gap Ledger (campaign execution)

The runner executes tasks through the cockpit browser via Playwright MCP, observes results, and records gaps. This is the C27-specific execution layer.

---

## Files Created

| File | Purpose |
|------|---------|
| `substrate/organism/self_use/__init__.py` | Public API |
| `substrate/organism/self_use/task_catalog.py` | SelfUseTask dataclass + JSON loader |
| `substrate/organism/self_use/task_taxonomy.py` | 15-domain taxonomy with subsystem mapping |
| `substrate/organism/self_use/gap_ledger.py` | Structured friction/capability gap log |
| `substrate/organism/self_use/certification_report.py` | Aggregates metrics, dispatches to Discord |
| `data/umh/self_use_tasks.json` | 103 task definitions across 15 domains |
| `scripts/run_self_use_certification.py` | CLI entry point — orchestrates browser-driven run |
| `tests/test_self_use_catalog.py` | Catalog loading + validation tests |
| `tests/test_self_use_taxonomy.py` | Taxonomy coverage tests |
| `tests/test_self_use_gap_ledger.py` | Gap ledger tests |
| `tests/test_self_use_report.py` | Report + certification check tests |

### Files Modified

| File | Change |
|------|--------|
| `substrate/canonical_types.py` | Register new types (GapType, GapEntry, CertificationMetrics) |

---

## Component Design

### 1. SelfUseTask + SelfUseTaskCatalog (`task_catalog.py`)

Data-driven task definitions loaded from `data/umh/self_use_tasks.json`.

```python
@dataclass
class SelfUseTask:
    task_id: str           # "SWP-001"
    domain: str            # "software_production"
    intent: str            # exact text to type into cockpit chat
    expected_behavior: str # what should happen (for manual/browser verification)
    verification: dict     # what to check in UI after submission
    difficulty: str = "medium"
    requires_mutation: bool = False
    requires_approval: bool = False
    tags: list[str] = field(default_factory=list)
```

`verification` dict describes what the browser should observe after submission:
```json
{
  "response_contains": ["classified as", "work packet"],
  "response_not_contains": ["error", "failed"],
  "panel_expected": "engineering",
  "status_expected": "completed"
}
```

### 2. OperatorTaskTaxonomy (`task_taxonomy.py`)

Maps 15 domains to their cockpit behavior expectations:

| Domain | Prefix | Count | Expected Behavior |
|--------|--------|-------|------------------|
| software_production | SWP | 10 | Routes to engineering panel, creates work packet |
| deployment_verification | DEP | 7 | Returns deployment/certification status in chat |
| bug_diagnosis | BUG | 8 | Routes to engineering, creates investigation packet |
| repo_inspection | REP | 7 | Returns repo info directly in chat response |
| documentation_generation | DOC | 6 | Routes to engineering, creates doc generation packet |
| memory_state_retrieval | MEM | 7 | Returns organism state/memory in chat response |
| planning_rescheduling | PLN | 7 | Creates/updates work packets or schedule entries |
| priority_enforcement | PRI | 6 | Returns priority ranking in chat response |
| project_admission | ADM | 6 | Triggers review flow, requires approval |
| recovery_after_failure | REC | 7 | Routes to execution, recovery actions |
| proof_package_review | PRF | 6 | Navigates to proof review, shows recommendation |
| projection_certification | CRT | 6 | Returns certification levels in chat response |
| context_compression | CTX | 6 | Returns compressed summary in chat response |
| operator_briefing | BRF | 7 | Returns briefing with attention items |
| decision_support | DEC | 7 | Returns analysis with tradeoffs/recommendation |
| **TOTAL** | | **103** | |

### 3. GapLedger (`gap_ledger.py`)

Structured JSONL log of every friction point discovered during browser testing.

```python
class GapType(str, Enum):
    UI_ERROR = "ui_error"                # cockpit rendering/interaction failure
    API_ERROR = "api_error"              # backend API returned error
    CLASSIFICATION_ERROR = "classification_error"  # wrong intent classification
    ROUTING_ERROR = "routing_error"      # routed to wrong subsystem
    CAPABILITY_MISSING = "capability_missing"  # feature not implemented
    STALE_STATE = "stale_state"          # UI showed stale/incorrect data
    FALSE_SUCCESS = "false_success"      # claimed success but didn't work
    TIMEOUT = "timeout"                  # response took too long or hung
    AUTH_ERROR = "auth_error"            # authentication/authorization failure
    UX_FRICTION = "ux_friction"          # works but operator experience is bad

@dataclass
class GapEntry:
    gap_id: str
    task_id: str
    domain: str
    gap_type: GapType
    description: str
    expected: str          # what should have happened
    actual: str            # what actually happened
    severity: str          # critical/high/medium/low
    screenshot_path: str   # Playwright screenshot at time of failure
    console_errors: list[str]  # browser console errors
    human_intervention_required: bool
    remediation_hint: str
    recorded_at: float
```

### 4. SelfUseCertificationReport (`certification_report.py`)

Aggregates all results into certification metrics and a markdown report.

```python
@dataclass
class TaskResult:
    task_id: str
    domain: str
    status: str           # completed/failed/gap/timeout/blocked
    response_text: str    # what the cockpit responded
    verification_passed: bool
    duration_ms: int
    gap_entry: GapEntry | None
    screenshot_path: str  # screenshot of final state
    notes: str = ""

@dataclass
class CertificationMetrics:
    total_tasks: int
    completed: int
    failed: int
    gaps: int
    timeouts: int
    false_successes: int
    completion_rate: float
    verification_rate: float
    by_domain: dict[str, dict]
    by_gap_type: dict[str, int]
    worst_domains: list[str]
    strongest_domains: list[str]
```

**Acceptance criteria:**
- 100+ tasks executed through cockpit UI
- 0 false-success promotions
- >= 95% verified completion
- 100% failures captured in gap ledger
- Every failure has a screenshot

### 5. Browser Execution Flow (`scripts/run_self_use_certification.py`)

This is the orchestrator script. It runs on the VPS and drives Playwright MCP on Beast Session 1.

**Per-task flow:**
1. Navigate to cockpit (universalmetaharness.tech) — verify loaded
2. Click RightRail chat input
3. Type `task.intent` into chat
4. Wait for response (timeout: 30s for queries, 120s for mutations)
5. Read response text from chat message
6. Take screenshot
7. Check browser console for errors
8. Verify response against `task.verification` criteria
9. If panel navigation expected, verify correct panel loaded
10. Record TaskResult
11. If verification failed → record GapEntry with screenshot + console errors
12. Move to next task

**Between domains:** take a "domain checkpoint" screenshot showing the dashboard state.

**Error recovery:** if the cockpit becomes unresponsive or throws a JS error, take a screenshot, record the gap, refresh the page, and continue with the next task.

---

## Task Catalog Sample

Tasks use natural operator language — exactly what Antony would type:

**Software Production (SWP):**
- "Create a utility function for timestamp formatting in substrate/utils"
- "Add error handling to the deployment verification worker"
- "Implement a health check endpoint for the self-use runner"

**Deployment Verification (DEP):**
- "Check if the cockpit is healthy"
- "What certification level is EOS at?"
- "Run deployment verification on all projections"

**Bug Diagnosis (BUG):**
- "Why is the organism daemon tick count not incrementing?"
- "Debug the trust score — it's showing zero for everything"
- "Find why cockpit chat responses are slow"

**Memory/State Retrieval (MEM):**
- "What does the organism know about deployment health?"
- "Show me the active work packets"
- "What's the current trust score for EOS?"

**Operator Briefing (BRF):**
- "What happened since I was away?"
- "Give me the morning brief"
- "What needs my attention right now?"

**Decision Support (DEC):**
- "Should we deploy to production now or wait for Beast to come online?"
- "What are the tradeoffs of splitting cockpit_core_routes into smaller files?"
- "Compare using cc_sdk vs direct Anthropic API for this task"

(Full 103-task catalog defined in the JSON file)

---

## Phasing

### C27.0 — Infrastructure (task catalog + taxonomy + gap ledger)
Build the reusable substrate components:
- `task_catalog.py` + `task_taxonomy.py` + `gap_ledger.py` + `certification_report.py`
- `data/umh/self_use_tasks.json` with all 103 tasks
- Register types in `canonical_types.py`
- Unit tests for all components

### C27.1 — Cockpit Smoke Test (Beast Session 1)
Before running 103 tasks, verify the cockpit is functional:
- SSH to Beast, Playwright MCP navigates to universalmetaharness.tech
- Login via Clerk
- Verify: Shell loads, LeftRail renders, RightRail chat is interactive
- Send 3 test messages, verify responses render
- Check console for JS errors
- Take screenshots at each step
- Fix any blocking issues before proceeding

### C27.2 — Full Browser-Driven Run (103 tasks)
Execute all 103 tasks through the cockpit UI:
- Domain by domain, sequential
- Each task: type → wait → verify → screenshot → record
- Gap ledger captures every failure with evidence
- Domain checkpoint screenshots between domains
- Error recovery: refresh and continue on crash

### C27.3 — Certification Report + Dispatch
- Compute CertificationMetrics from all TaskResults
- Generate markdown report with:
  - Overall pass/fail against acceptance criteria
  - Domain-by-domain breakdown
  - Gap ledger summary (by type, by severity)
  - Top 10 most critical gaps
  - Screenshots of key failures
- Dispatch to Discord Founders Office as .md attachment
- If gaps found: prioritized remediation list for C28 prep

---

## Verification Plan

1. **Unit tests** — catalog, taxonomy, gap ledger, report (~60 tests)
2. **Catalog validation** — 15 domains covered, 103 tasks, unique IDs
3. **Cockpit smoke test** — Beast Session 1, Playwright MCP, visual verification
4. **Full run** — 103 tasks through cockpit UI, all results recorded
5. **Gap ledger completeness** — every failure has a GapEntry with screenshot
6. **Certification check** — `passes_certification()` evaluates acceptance criteria
7. **Report dispatch** — full report sent to Discord Founders Office

---

## Done Criteria

1. 103 tasks defined across 15 domains in data-driven JSON catalog
2. All 103 tasks executed through cockpit UI in browser (Beast Session 1)
3. 0 false-success promotions (no task marked "passed" that didn't actually work)
4. >= 95% verified completion rate
5. 100% of failures captured in gap ledger with screenshot evidence
6. Gap ledger identifies every friction point, missing capability, and UX issue
7. Certification report dispatched to Discord Founders Office
8. If certification fails: gap ledger becomes the remediation roadmap for C28

---

## Strategic Outcome

```
C24: UMH can produce software                              ✅
C25: UMH can operate through its cockpit loop               ✅
C26: UMH verifies reality and detects divergence            ✅
C27: UMH can use itself across 15 operator task domains     ⬜
C28: UMH survives 30 days of daily-driver use               ⬜ (after C27)
```

C27 compresses a month of risk discovery into one controlled campaign. The gap ledger becomes the roadmap for C28.
