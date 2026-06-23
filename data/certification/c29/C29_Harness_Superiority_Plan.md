# C29 — Harness Superiority Benchmark

## Context

C24-C28 proved UMH can produce software, operate through its cockpit loop, verify reality, remain coherent under entropy, and function as a workstation. None of these campaigns answer the most important question: **Is UMH actually better than the workflow it replaces?**

C29 runs two workflows in parallel against real roadmap tasks — Legacy (Claude Code + Termius + VS Code + GitHub + Fly.io) vs UMH (Cockpit + Meta IDE + RightRail + Execution/Governance/Proof/Continuity runtimes) — and measures which produces superior software-production outcomes.

**The question:** Has UMH crossed the trust threshold where building through UMH produces better outcomes than building outside UMH?

**The thesis under test:** UMH wins not because it codes faster, but because it reduces cognitive reconstruction. Claude Code already produces software. Cursor already edits files. VS Code already manages projects. Termius already accesses machines. If UMH wins, it wins on continuity, awareness, governance, and reality correspondence — the things no existing tool provides.

**The standard:** Browser-driven validation only. No API-only passes. All evidence through Playwright + Real Browser + Live Cockpit UI.

---

## Architecture

### Data Model

All scoring is deterministic. Zero LLM calls in measurement. Reuses C23B `CompositeScorer` weighted-scoring pattern and C28 `CertificationReport` evidence pattern.

#### Core Types

```
BenchmarkTask
  ├── task_id: str (e.g. "c29-001")
  ├── category: BenchmarkCategory (BUG_FIX | FEATURE | REFACTOR | DEPLOY | RECOVERY)
  ├── project: str (UMH | CreatorOS | EntrepreneurOS | LyfeOS)
  ├── title: str
  ├── description: str
  ├── complexity: str (LOW | MEDIUM | HIGH)
  ├── expected_deliverables: list[str]
  ├── created_at: str (ISO)

TrackResult
  ├── task_id: str
  ├── track: str ("A_LEGACY" | "B_UMH")
  ├── started_at / completed_at: str (ISO)
  ├── duration_seconds: float
  ├── outcome: str (SUCCESS | PARTIAL | FAILED)
  ├── deliverables_met: list[str]
  ├── quality_score: float (0-100, operator-rated)
  ├── verification_method: str
  ├── verification_passed: bool
  ├── recovery_needed: bool
  ├── recovery_successful: bool
  ├── recovery_time_seconds: float
  ├── context_switches: int
  ├── manual_reconstructions: int
  ├── tools_used: list[str]
  ├── escapes: list[EscapeEvent]  (Track B only)
  ├── continuity_test: ContinuityResult | None
  ├── governance_test: GovernanceResult | None
  ├── awareness_snapshot: AwarenessSnapshot | None
  ├── cognitive_load: CognitiveLoadResult | None        ← GAP 1
  ├── interruption_test: InterruptionResult | None      ← GAP 2
  ├── reality_drift: RealityDriftResult | None          ← GAP 4
  ├── operator_trust: OperatorTrustResult | None        ← GAP 5
  ├── meta_ide_test: MetaIDEResult | None               ← GAP 9
  ├── resource_cost: ResourceCost | None                ← GAP 7
  ├── browser_evidence: BrowserEvidence | None (Track B only)
  ├── voice_test: VoiceResult | None
  ├── preview_test: PreviewResult | None
  ├── notes: str
```

#### Gap 1 — Cognitive Load Measurement

```
CognitiveLoadResult
  ├── reconstruction_steps: int       — steps to rebuild context after interruption
  ├── clarification_questions: int    — questions asked to understand current state
  ├── context_searches: int           — searches for information (grep, find, git log)
  ├── panel_hops: int                 — navigation actions to find relevant info
  ├── memory_recovery_actions: int    — explicit memory/note lookups
  ├── cognitive_load_score: float     — derived: 1.0 - (total_actions / normalizer), clamped 0-1
```

#### Gap 2 — Interruption Resistance

```
InterruptionResult
  ├── interruption_type: str          — TASK_SWITCH | MEETING | EMERGENCY | TIME_GAP
  ├── interruption_from: str          — task being interrupted
  ├── interruption_to: str            — task switched to (or "away")
  ├── away_duration_seconds: float
  ├── resume_time_seconds: float      — time to productively resume
  ├── context_accuracy: float         — 0-1, how correct was recalled context
  ├── decisions_recalled: int
  ├── decisions_total: int
  ├── work_recovery_complete: bool    — was previous work state fully recovered
```

#### Gap 4 — Reality Drift Detection

```
RealityDriftResult
  ├── drift_type: str                 — STALE_BRANCH | STALE_DEPLOY | WRONG_ASSUMPTION |
  │                                      FAILED_ROLLOUT | MISSING_DEPENDENCY | OUTDATED_PLAN
  ├── drift_present: bool
  ├── drift_detected: bool
  ├── detection_time_seconds: float
  ├── false_positive: bool
  ├── detection_method: str           — how it was detected (automated | manual | not_detected)
```

#### Gap 5 — Operator Trust

```
OperatorTrustResult
  ├── confidence_before: int          — 1-5 operator self-rated before task
  ├── confidence_after: int           — 1-5 operator self-rated after task
  ├── verification_needed: bool       — did operator feel need to manually verify
  ├── manual_double_checks: int       — count of "let me check that myself" actions
  ├── trust_delta: int                — after - before
```

#### Gap 7 — Resource Cost

```
ResourceCost
  ├── tokens_used: int                — LLM tokens consumed
  ├── compute_seconds: float          — CPU/GPU seconds
  ├── operator_minutes: float         — wall-clock operator attention time
  ├── clicks: int                     — total UI interactions
  ├── panel_changes: int              — navigation between panels/windows
  ├── commands_issued: int            — CLI/chat commands
  ├── cost_per_deliverable: float     — derived: operator_minutes / deliverables_met
```

#### Gap 9 — Meta IDE Scoring

```
MetaIDEResult
  ├── workspace_aware: bool
  ├── repo_aware: bool
  ├── branch_aware: bool
  ├── execution_aware: bool
  ├── preview_aware: bool
  ├── proof_aware: bool
  ├── continuity_aware: bool          — does it know where operator left off
  ├── meta_ide_score: float           — count True / 7
```

#### Existing Types (unchanged)

```
EscapeEvent
  ├── timestamp, tool, reason, could_cockpit_handle

ContinuityResult
  ├── interruption_duration_seconds, context_preserved, resume_time_seconds (TTRC),
  │   decisions_recalled, decisions_total, intent_preserved

GovernanceResult
  ├── approvals_required, approvals_enforced, proof_generated,
  │   verification_enforced, false_history_tested, false_history_blocked

AwarenessSnapshot
  ├── 10 visibility booleans + awareness_score (count / 10)

BrowserEvidence
  ├── screenshots, console_errors, console_log, network_errors,
  │   network_traces, execution_traces, proof_package_id, verification_result

VoiceResult
  ├── commands_attempted, commands_recognized, intents_correct,
  │   routes_correct, recovery_after_failure

PreviewResult
  ├── preview_loaded, mobile_viewport, tablet_viewport, desktop_viewport,
  │   expand_collapse, health_visible
```

---

### Scoring Formulas

All deterministic. Weighted averages.

**Comparative Scores** (10 dimensions — expanded from original 7):

| Score | Weight | Formula | What It Measures |
|-------|--------|---------|-----------------|
| Capability | 12% | `mean(deliverables_met_ratio * quality / 100)` | Can it complete work? |
| Execution | 10% | `mean(outcome == SUCCESS) * mean(verification_passed)` | Does work succeed? |
| **Cognitive Load** | **15%** | `mean(cognitive_load.cognitive_load_score)` | **How much brain does it cost?** |
| **Interruption Resistance** | **15%** | `mean(interruption.context_accuracy * interruption.work_recovery)` | **Can it survive real life?** |
| Continuity | 12% | `mean(continuity.context_preserved * clamp(30/resume_time))` | Does context persist? |
| Governance | 8% | `mean(governance.enforced_rate * proof_rate)` | Is execution governed? |
| Awareness | 5% | `mean(awareness.awareness_score)` | Does it know what's happening? |
| Recovery | 5% | `mean(recovery_successful if needed else 1.0)` | Can it recover from failure? |
| **Meta IDE** | **8%** | `mean(meta_ide.meta_ide_score)` | **Does it beat VS Code/Cursor?** |
| **Cost Efficiency** | **10%** | `1.0 - clamp(umh_cost_per_task / legacy_cost_per_task, 0, 2) / 2` | **Is it worth the resources?** |

Weight rebalance rationale: Cognitive Load and Interruption Resistance are the two dimensions where UMH claims its strongest advantage over legacy tools. They get the highest weights because that's where the thesis is tested hardest.

**HTI** (Harness Trustworthiness Index — Track B only):

| Component | Weight | Source |
|-----------|--------|--------|
| Execution Reliability | 15% | `success_rate * verification_rate` |
| Continuity | 15% | `mean(context_preserved) * clamp(30 / mean(TTRC))` |
| Cognitive Load | 15% | `mean(cognitive_load_score)` |
| Reality Correspondence | 10% | `drift_detected_rate - false_positive_rate` |
| Governance | 10% | `mean(enforced_rate * proof_rate)` |
| Verification Coverage | 10% | `tasks_with_verification / total_tasks` |
| Recovery Capability | 5% | `successful_recoveries / recovery_attempts` |
| Workspace Awareness | 5% | `mean(awareness_score)` |
| Meta IDE | 5% | `mean(meta_ide_score)` |
| Multi-Machine Awareness | 5% | `beast_connected_rate * routing_accuracy` |
| Operator Trust | 5% | `mean(confidence_after / 5) * (1 - double_check_rate)` |

**UMH-specific metrics:**
- CPR (Continuity Preservation Rate): `tasks_with_context_preserved / tasks_with_interruption` — target >95%
- RCR (Reality Correspondence Rate): `drifts_detected / drifts_present` — target >95%
- GCR (Governance Challenge Rate): `governance_enforcements / governance_required` — target >90%
- VC (Verification Coverage): `tasks_with_proof / total_tasks` — target >95%
- TTRC (Time To Reconstruct Context): `median(resume_time_seconds)` — target <30s
- OER (Operator Escape Rate): `total_escapes / total_interactions` — target <10%
- **CLS (Cognitive Load Score):** `mean(cognitive_load_score)` — target >0.80
- **IRS (Interruption Resistance Score):** `mean(context_accuracy * work_recovery)` — target >0.85
- **DDC (Daily Driver Coverage):** `activities_coverable / 10` — target >0.80
- **OTS (Operator Trust Score):** `mean(confidence_after) / 5` — target >0.80

---

### Evidence Classification Framework

**The core rule:** UMH's claimed differentiators (continuity, awareness, governance, execution) are exactly the things that are worthless if measured synthetically. A simulated 3-hour interruption proves nothing about real resumption. A mock deployment proves nothing about trust.

Every `TrackResult` gets an `evidence_class` field:

#### Evidence Classes

| Class | Trust Level | Weight | Examples |
|-------|------------|--------|----------|
| **A — Production** | Highest | 100% | Real task, real code change, real deployment, real interruption, real resume, real approval, real proof package |
| **B — Controlled** | Medium | 50-75% | Playwright performs workflow, operator follows script, deliberate interruption inserted |
| **C — Synthetic** | Lowest | 0-25% | Mock task, generated scenario, fake branch, simulated deployment |

```
class EvidenceClass(str, Enum):
    A_PRODUCTION = "A_PRODUCTION"
    B_CONTROLLED = "B_CONTROLLED"
    C_SYNTHETIC  = "C_SYNTHETIC"

EVIDENCE_WEIGHTS = {
    EvidenceClass.A_PRODUCTION: 1.0,
    EvidenceClass.B_CONTROLLED: 0.625,
    EvidenceClass.C_SYNTHETIC:  0.125,
}
```

#### Evidence-Weighted Scoring

All scoring formulas use `weighted_mean()` instead of `mean()`:

```
def weighted_mean(results, extract_fn):
    total_weight = sum(EVIDENCE_WEIGHTS[r.evidence_class] for r in results)
    if total_weight == 0: return 0.0
    return sum(extract_fn(r) * EVIDENCE_WEIGHTS[r.evidence_class] for r in results) / total_weight
```

This applies to all 10 comparative scores AND all 11 HTI components.

#### Per-Metric Evidence Confidence

Every metric reports both value and confidence:

```
MetricWithConfidence
  |-- name: str
  |-- value: float
  |-- confidence: EvidenceConfidence (HIGH | MEDIUM | LOW)
  |-- class_a_count: int
  |-- class_b_count: int
  |-- class_c_count: int
```

Confidence derivation (deterministic):
- **HIGH**: `class_a_count / total >= 0.5` (majority production evidence)
- **MEDIUM**: `(class_a_count + class_b_count) / total >= 0.5` (majority real or controlled)
- **LOW**: everything else

Report displays: `CPR = 97% (HIGH)` or `Voice Accuracy = 91% (LOW)`

#### Hard Rules

1. **No Synthetic-Only Pass**: Any metric with 0 Class A + 0 Class B runs = **automatic fail** regardless of score value.

2. **The Litmus Test**: After computing the full verdict, re-derive it with all Class C runs removed. If the verdict would drop below PRIMARY_WORKSTATION, the final verdict is **capped at PARTIALLY_TRUSTED** with the note: *"Verdict downgraded: would not hold without synthetic evidence."*

3. **Minimum Production Evidence**: At least 15 Class A+B runs required for any verdict above PARTIALLY_TRUSTED.

4. **Synthetic Cannot Lift Verdict**: Class C runs may increase coverage (identifying areas to investigate) but may NOT increase the final MVP Trust Verdict. The decisive verdict is computed from Class A+B evidence only. Synthetic runs are additive for diagnostics, never for certification.

#### The Standard

> *If I removed every synthetic run from the dataset, would the verdict still hold?*
>
> If yes: approaching evidence quality used by top engineering organizations.
> If no: the benchmark is measuring the benchmark, not the harness.

---

### Gap 6 — Daily Driver Coverage

Track across all runs which workday activities can be performed without leaving the cockpit:

```
WorkdayCoverage
  ├── coding: bool
  ├── debugging: bool
  ├── review: bool
  ├── deployment: bool
  ├── planning: bool
  ├── continuity: bool          — resume/handoff
  ├── documentation: bool
  ├── approvals: bool
  ├── knowledge_retrieval: bool
  ├── runtime_inspection: bool
  ├── coverage_score: float     — count True / 10
```

Computed incrementally as benchmark runs exercise different activities. More meaningful than OER because it measures capability, not just escape avoidance.

---

### Gap 3 — Multi-Project Pressure Tests

Dedicated benchmark runs that exercise simultaneous project juggling:

**Multi-Project Pressure Run (at least 4 of these in the 40-run corpus):**
```
1. Start Task A on CreatorOS
2. INTERRUPT → switch to Task B on UMH
3. INTERRUPT → switch to Task C on EntrepreneurOS
4. Return to Task A on CreatorOS
5. Measure: resume time, context accuracy, decision recall per switch
```

Each switch produces an `InterruptionResult`. Multi-project runs contribute to Interruption Resistance score with higher weight (3 switches per run vs 0-1 for normal runs).

---

### Gap 8 — Longitudinal Continuity Checkpoints

Volume-triggered, not calendar-triggered. Preserves the "volume not time" philosophy.

**Continuity Recall Challenge — every 10 completed benchmark runs:**

```
LongitudinalCheckpoint
  ├── checkpoint_number: int          — 1, 2, 3, ...
  ├── runs_completed_at_checkpoint: int
  ├── challenge_tasks: list[str]      — 5 questions about prior runs
  │   Example:
  │   - "What was the last bug fix on CreatorOS?"
  │   - "What branch was the EOS refactor on?"
  │   - "What failed in run c29-014?"
  │   - "What was the governance decision on c29-008?"
  │   - "What's the current deploy status of LyfeOS?"
  ├── correct_answers: int
  ├── total_questions: int
  ├── track_a_recall_score: float     — legacy: how many could operator recall
  ├── track_b_recall_score: float     — UMH: how many could cockpit surface
  ├── time_to_answer_seconds: float   — per-question average
```

This directly tests whether UMH's continuity system actually preserves institutional memory better than the operator's brain + scattered notes.

---

### Gap 10 — MVP Trust Verdict

The report ends not with HTI >90 but with the real decision:

```
MVPTrustVerdict
  ├── would_choose_first: str         — YES | SOMETIMES | NO
  ├── would_stay_in: str              — YES | MOSTLY | NO
  ├── trusts_with_production: str     — YES | WITH_OVERSIGHT | NO
  ├── recommends_replacing_legacy: str — YES | PARTIALLY | NO
  ├── projection_acceleration_justified: str — YES | NOT_YET | NO
  ├── verdict: str                    — NOT_READY | PARTIALLY_TRUSTED |
  │                                      PRIMARY_WORKSTATION | CERTIFIED_DAILY_DRIVER
  ├── evidence_summary: str           — 2-3 sentence justification from scores
```

Verdict derivation (deterministic from scores):
- **CERTIFIED_DAILY_DRIVER**: HTI >90 AND all comparative scores pass AND CLS >0.80 AND IRS >0.85 AND DDC >0.80 AND OTS >0.80
- **PRIMARY_WORKSTATION**: HTI >85 AND most comparative scores pass AND CLS >0.70 AND IRS >0.75
- **PARTIALLY_TRUSTED**: HTI >75 AND execution/capability scores pass
- **NOT_READY**: anything below PARTIALLY_TRUSTED

The operator fields (would_choose_first, etc.) are filled by Antony after reviewing the quantitative scores. They inform the verdict but don't override it — if the scores say CERTIFIED but Antony says NO, the gap between quantitative and qualitative is itself a finding.

---

## Phasing

### Phase 1 — Benchmark Framework (the measurement engine)

Build the data model, scoring engine, and task runner. No benchmark execution yet — this is the instrument.

**1.1 — Data model and task registry**
- Create `substrate/organism/benchmarks/harness_superiority.py`
- All dataclasses: `BenchmarkTask`, `TrackResult`, `EscapeEvent`, `ContinuityResult`, `GovernanceResult`, `AwarenessSnapshot`, `CognitiveLoadResult`, `InterruptionResult`, `RealityDriftResult`, `OperatorTrustResult`, `MetaIDEResult`, `ResourceCost`, `WorkdayCoverage`, `LongitudinalCheckpoint`, `MVPTrustVerdict`, `BenchmarkCategory` (enum)
- `TaskRegistry` — loads/saves tasks from `data/certification/c29/tasks.jsonl`
- `ResultStore` — loads/saves results from `data/certification/c29/results.jsonl`

**1.2 — Comparative scorer**
- Create `substrate/organism/benchmarks/harness_scorer.py`
- `HarnessScorer` — computes all 10 comparative scores from TrackResult pairs
- `HTICalculator` — computes HTI from Track B results only (11 components)
- `UMHMetricCalculator` — computes CPR, RCR, GCR, VC, TTRC, OER, CLS, IRS, DDC, OTS
- `MVPVerdictEngine` — derives verdict from scores
- All formulas deterministic, no LLM
- Reuses `CompositeScorer` tier-weighting pattern from C23B

**1.3 — Benchmark runner**
- Create `tests/certification/c29_benchmark.py`
- CLI: `--register-task` | `--record-legacy <id>` | `--record-umh <id>` | `--score` | `--report` | `--status` | `--checkpoint` (longitudinal recall challenge)
- Extends C28 certification pattern (SSH → Beast Playwright for Track B evidence)
- Multi-project pressure runs via `--multi-project` flag

**1.4 — Browser evidence extension for C29**
- Create `tests/certification/c29_evidence.py`
- Extends `browser_evidence_collector.py` with C29-specific evidence:
  - Continuity test: close cockpit → reopen → measure TTRC → verify resume card
  - Governance challenge: attempt unauthorized action → verify block
  - Awareness check: navigate workspace → verify 10 items visible
  - Recovery test: inject failure → measure detection + recovery time
  - Cognitive load test: count reconstruction steps during resume
  - Reality drift test: verify cockpit detects planted divergence
  - Meta IDE test: check 7 awareness dimensions in IDE panel

**1.5 — Per-run evidence requirements**

Every Track B benchmark run must generate ALL of these (spec non-negotiable):
- Screenshots (at each step of mandatory test path)
- Console logs (full capture during run)
- Network traces (all requests/responses)
- Execution traces (executor dispatch + log stream)
- Proof package (auto-generated on execution completion)
- Verification result (pass/fail with evidence)

Stored at `data/certification/c29/runs/{task_id}/{track}/` with timestamped artifacts.

**Verification:** `python3 tests/certification/c29_benchmark.py --status` shows empty registry. Register a test task, record dummy results for both tracks, compute all 10 scores + HTI + 10 UMH metrics. All formulas produce expected outputs.

---

### Phase 2 — Task Corpus (real roadmap work)

Build the corpus of 40+ real tasks from actual project roadmaps. NOT synthetic.

**2.1 — Seed tasks from existing backlogs**
- Create `data/certification/c29/tasks.jsonl` with 40+ tasks
- Distribution:
  - 8+ per category (Bug Fix, Feature, Refactor, Deploy, Recovery)
  - 10+ per project (UMH, CreatorOS, EntrepreneurOS, LyfeOS)
  - 4+ multi-project pressure runs (Gap 3)
  - 4+ reality drift tasks — planted divergences (Gap 4)

**2.2 — Task pairing strategy**
- Direct comparison: same task on both tracks where possible
- Category comparison: equivalent-complexity tasks, different tracks
- Multi-project runs: both tracks execute the same project-switching sequence
- Longitudinal checkpoints: scheduled every 10 runs

**Verification:** `--status` shows 40+ tasks across all 5 categories, all 4 projects, with multi-project and drift tasks tagged.

---

### Phase 3 — Benchmark Execution (the actual runs)

Execute tasks on both tracks. Runs until statistical significance is achieved.

**3.1 — Track A execution (legacy workflow)**
- Operator performs task using legacy tools
- Records all fields including cognitive load (reconstruction steps, context searches, etc.)
- For interruption tests: switch projects, return, log resume effort
- For drift tests: operator must detect planted divergence manually

**3.2 — Track B execution (UMH workflow)**
- Operator performs task through cockpit with browser evidence
- Mandatory test path per spec
- Every escape logged with reason
- Cognitive load measured from browser evidence (panel hops, searches)
- Interruption resistance measured from TTRC + context accuracy
- Reality drift detection measured from cockpit alerting

**3.3 — Longitudinal checkpoints (every 10 runs)**
- 5-question recall challenge on both tracks
- Tests whether UMH continuity system retains institutional memory

**3.4 — Incremental scoring**
- After every 5 run pairs, recompute all scores
- Dashboard: running HTI, 10 comparative scores, 10 UMH metrics, workday coverage
- Benchmark ends when: (a) minimum 20 runs AND (b) HTI confidence ±5 or narrower

---

### Phase 4 — Certification Report (the verdict)

**4.1 — Report generation**
- Create `tests/certification/c29_report.py`
- Executive summary with MVP Trust Verdict (Gap 10)
- HTI score with 11 component breakdown
- 10 comparative scores with UMH vs Legacy side-by-side
- All 10 UMH-specific metrics vs targets
- Cognitive Load analysis (Gap 1): where UMH saved brain, where it cost brain
- Interruption Resistance analysis (Gap 2): best/worst resume scenarios
- Multi-Project Pressure results (Gap 3)
- Reality Drift Detection results (Gap 4)
- Operator Trust trajectory (Gap 5): did trust increase over the benchmark?
- Daily Driver Coverage matrix (Gap 6): what can/can't be done in cockpit
- Cost Efficiency comparison (Gap 7)
- Longitudinal Continuity results (Gap 8): institutional memory retention
- Meta IDE comparative analysis (Gap 9): vs VS Code/Cursor specific dimensions
- Category-by-category and project-by-project breakdowns
- Full evidence index
- Gap ledger for C30

**4.2 — Pass criteria evaluation**
- Capability Score >= Legacy
- Execution Score >= Legacy
- Cognitive Load Score > Legacy (must exceed — this is the thesis)
- Interruption Resistance > Legacy (must exceed — this is the thesis)
- Continuity Score > Legacy
- Governance Score > Legacy
- Awareness Score > Legacy
- Recovery Score > Legacy
- Meta IDE Score > Legacy
- Cost Efficiency >= Legacy (equal or exceed)
- HTI > 90, CPR > 95%, RCR > 95%, GCR > 90%, VC > 95%
- TTRC < 30s, OER < 10%, CLS > 0.80, IRS > 0.85, DDC > 0.80, OTS > 0.80
- MVP Trust Verdict >= PRIMARY_WORKSTATION

**4.3 — Discord dispatch**
- Full report as file attachment to Founders Office (channel 1485765456739696714)

---

## Dependencies & Ordering

```
Phase 1 (framework) ─── BLOCKS ALL
    │
    ├── Phase 2 (task corpus) ─── can start during Phase 1 as task list
    │
    └── Phase 3 (execution) ─── needs Phase 1 + Phase 2
            │
            └── Phase 4 (certification) ─── needs Phase 3 complete
```

Phase 1 is the only build phase. Phases 2-4 are operational.

---

## Critical Files

### Create
| File | Purpose | Est. Lines |
|------|---------|-----------|
| `substrate/organism/benchmarks/harness_superiority.py` | Data model (all types), TaskRegistry, ResultStore | ~700 |
| `substrate/organism/benchmarks/harness_scorer.py` | HarnessScorer (10 dims), HTICalculator (11 components), UMHMetricCalculator (10 metrics), MVPVerdictEngine | ~600 |
| `tests/certification/c29_benchmark.py` | CLI runner, interactive recording, status dashboard, longitudinal checkpoints | ~700 |
| `tests/certification/c29_evidence.py` | C29-specific browser evidence (cognitive load, interruption, drift, meta IDE) | ~450 |
| `tests/certification/c29_report.py` | Report generation, pass criteria (expanded), MVP verdict, Discord dispatch | ~550 |
| `data/certification/c29/tasks.jsonl` | Task corpus (40+ real tasks including multi-project and drift tasks) | ~200 |

### Modify
| File | Change |
|------|--------|
| `tests/certification/__init__.py` | Ensure importable |

### Reuse (no modification)
| File | What's Reused |
|------|---------------|
| `substrate/organism/benchmarks/composite_scorer.py` | Weighted scoring pattern |
| `substrate/organism/benchmarks/competitive.py` | CategoryScore, CompetitorRegistry pattern |
| `substrate/meta_ide/browser_evidence_collector.py` | Beast Playwright evidence collection |
| `tests/certification/c28_certification.py` | CertificationReport pattern, SSH → Beast pattern |

---

## Tests

| Test File | Coverage |
|-----------|----------|
| `tests/test_harness_superiority.py` | All 15+ dataclass types, TaskRegistry CRUD, ResultStore CRUD | ~100 tests |
| `tests/test_harness_scorer.py` | 10 comparative scores, HTI (11 components), 10 UMH metrics, MVP verdict logic, longitudinal checkpoint scoring | ~150 tests |
| `tests/test_c29_benchmark.py` | CLI parsing, interactive flow, multi-project mode, checkpoint trigger | ~50 tests |
| `tests/test_c29_report.py` | Report generation, expanded pass criteria, MVP verdict derivation, workday coverage matrix | ~70 tests |

Total: ~370 tests

---

## What C29 Proves

```
C24: UMH can produce software                              ✅
C25: UMH can operate through its cockpit loop               ✅
C26: UMH verifies reality and detects divergence            ✅
C27: UMH ecosystem is coherent under operator entropy       ✅
C28: Cockpit workstation is operational                     ✅
C29: UMH has crossed the MVP trust threshold               ⬜
     → Not just "can it complete tasks?"
     → "Has it earned the right to become the primary
        software-production harness?"
```

Only after C29 produces a CERTIFIED_DAILY_DRIVER or PRIMARY_WORKSTATION verdict should projection acceleration become the primary focus.
