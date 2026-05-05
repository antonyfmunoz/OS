# Phase 10 — System Behavior Stress Test Report

**Date:** 2026-04-28
**Scope:** GoalSelector (eos_ai/), UMH GoalArbitrator/GoalEvaluator/MetaGoalEngine (umh/runtime_engine/)
**Method:** 39 adversarial tests + 500-cycle simulation, all in-memory, no DB, no LLM, deterministic
**Verdict:** PASS — system is predictable, stable, and rational under all tested conditions

---

## 1. Adversarial Goals

### 1a. High Priority + Low Success Rate

| Goal | Priority | Success Rate | Score |
|---|---|---|---|
| High Priority Trap | 10 | 10% | 0.5100 |
| Steady Performer | 6 | 90% | 0.5490 |

**Finding:** With default weights (priority=0.25, performance=0.20), priority is the dominant signal. A priority-10 goal with 10% success rate beats a priority-6 goal with 90% success. The performance penalty reduces the score (0.5100 vs 0.5865 for an equally-prioritized good performer), but priority+impact base dominates.

**Assessment:** By design. The system trusts human-assigned priority as a strong anchor. Operators who want performance to dominate should use aggressive weights (performance=0.40, priority=0.10).

### 1b. Conflicting Dependencies

**Finding:** The `blocked_by` field is metadata — it only gates scoring when the goal's state is `GoalState.BLOCKED`. Goals created with `blocked_by` but starting in `DEFERRED` state are scored normally. The `add_goal()` method handles this correctly (auto-sets BLOCKED if blocked_by is provided), but external callers must set the state explicitly.

**Assessment:** Correct behavior. Dependency blocking is state-driven, not field-driven. Documented.

### 1c. Delayed Reward vs Immediate Win

**Result:** PASS. Strategic bet (priority=8, impact=0.95) correctly outranks quick win (priority=5, impact=0.4) despite higher cost and lower success rate.

### 1d. No Starvation

**Result:** PASS. With 10 goals and budget=2, all non-terminal goals maintain positive scores. No goal is locked out of scoring.

### 1e. No Irrational Locking

**Result:** PASS. When an incumbent's performance degrades (0.9→0.1) while a challenger improves (0.5→0.95), the challenger displaces the incumbent within 5 cycles via swap pressure.

---

## 2. Long-Run Simulation (500 Cycles)

### Configuration

- 8 goals, random priorities (3-9), random initial performance (0.2-0.8)
- Focus budget: 3
- Per-cycle noise: Gaussian σ=0.02 on success rate

### Results

| Metric | Value | Threshold | Status |
|---|---|---|---|
| Convergence point | Cycle 0 | < 50 | PASS |
| Churn rate | 6.81% | < 20% | PASS |
| Score range | [0.3500, 0.5865] | [-0.5, 1.5] | PASS |
| Score mean | 0.4560 | — | Healthy |
| Score stdev | 0.0553 | — | Low variance |

**Analysis:** The system converges immediately when performance signals are stable (low noise). With Gaussian noise σ=0.02, churn stays well below 10%. Score distributions are tightly bounded within [0.35, 0.59] — no runaway inflation or collapse.

### Gradual Performance Shift

When one goal degrades linearly (0.9→0.1 over 200 cycles) and another rises (0.3→0.95), the system correctly transitions. The rising star appears in >40/50 final cycles. No oscillation during transition.

---

## 3. Failure-Heavy Scenarios

### 3a. All Goals Failing (success_rate ≈ 0.05-0.10)

**Result:** PASS. Scores remain positive (floor ≈ 0.35). System selects the "least bad" by priority tiebreak. No score collapse to zero.

### 3b. Noisy Outcomes (σ=0.3 per cycle)

**Result:** PASS. With extreme noise (Gaussian σ=0.3 on success rate), churn stays below 80%. Priority provides sufficient anchoring to prevent pure noise-driven selection. Under mild noise (σ=0.02), churn is 6.81%.

### 3c. Intermittent Success

**Result:** PASS. Score ordering is strictly monotonic: always-fails (0.05 sr) < intermittent (0.50 sr) < always-wins (0.95 sr). The system correctly ranks partial performers between extremes.

---

## 4. Opportunity Traps

### 4a. Short-Term Performance Spike

**Result:** PASS. A low-priority (4) goal with perfect performance (1.0 across all metrics) does NOT displace a high-priority (9) strategic goal. Priority anchoring prevents reactive displacement.

### 4b. Long-Term Goals Through Performance Dips

**Result:** PASS. A priority-9 goal persists through 5 cycles of poor performance (sr=0.3) because priority+impact base score exceeds the performance penalty. Goal was active in 15+/20 cycles.

---

## 5. Edge Cases

| Scenario | Result | Notes |
|---|---|---|
| All goals equal | PASS | Deterministic — same input produces same output |
| No goals | PASS | Returns empty list, no crash |
| Single goal | PASS | Always active |
| All failing | PASS | Picks by priority tiebreak |
| All succeeding | PASS | Top 2 by priority selected |
| All blocked (circular) | PASS | Returns empty — no infinite loop |
| Focus budget = 0 | PASS | Zero active goals |
| Focus budget > goal count | PASS | All goals active |

---

## 6. Operator Control Validation

### Weight Sensitivity Matrix

| Configuration | High-Pri (10) / Low-Perf (10%) | Low-Pri (3) / High-Perf (90%) | Winner |
|---|---|---|---|
| Default | 0.5100 | 0.4080 | Priority |
| Aggressive (perf=0.40) | 0.3400 | 0.4070 | Performance |
| Conservative (pri=0.50) | 0.7750 | 0.4500 | Priority |

**Assessment:** Weight configuration works as expected. Operators can tune the priority-performance tradeoff by adjusting these two weights. The system faithfully reflects operator intent with no hidden behavior.

### Focus Budget

**Result:** PASS. Changing budget from 1→2→3→5 immediately changes active set size. No lag, no residual state.

### Custom Horizon Weights

**Result:** PASS. Short-term heavy weights (0.80/0.15/0.05) produce higher scores for goals with strong short-term but weak long-term performance, and vice versa. No hidden defaults overriding the configuration.

### Determinism

**Result:** PASS. Identical inputs produce identical outputs across repeated runs. No hidden randomness.

---

## 7. UMH Arbitrator Stress

| Test | Result | Notes |
|---|---|---|
| Switch cost prevents thrashing | PASS | <10 switches in 50 turns for near-identical goals |
| Blend entropy bounded | PASS | Non-negative entropy, weights sum to 1.0 |
| Single goal fast path | PASS | Reason = "single_goal" |
| Empty registry | PASS | Returns NO_ARBITRATION |

---

## 8. Meta-Goal Engine Stress

| Test | Result | Notes |
|---|---|---|
| MAX_GOALS cap enforced | PASS | Never generates beyond cap |
| Cooldown period respected | PASS | No generation within 5-turn cooldown |
| Retirement lifecycle | PASS | Confidence decays below floor → retired |
| Confidence bounds | PASS | Always within [0.05, 0.95] after 100 updates |

---

## Observed Patterns

1. **Priority is king under default weights.** A 4-point priority gap cannot be overcome by performance alone. This is intentional but operators must understand it.

2. **Performance adjustments are symmetric and bounded.** The max performance adjustment is ~±0.08 (depending on horizon profile). This means performance is a tiebreaker between similarly-prioritized goals, not an override.

3. **Opportunity cost penalty is modest.** The 0.10 weight means the max penalty is small. Combined with hysteresis (3 sustained cycles), swaps are rare and deliberate.

4. **Stability bonus rewards consistency.** Goals performing above 0.6 across all horizons get a +0.03 max bonus. This dampens oscillation.

5. **UMH switch cost (0.10) effectively prevents thrashing.** Two goals with utility difference <0.10 will not flip-flop.

---

## Tuning Recommendations

1. **If performance should matter more:** Set `performance` weight to 0.30-0.40 and reduce `priority` to 0.10-0.15. This shifts the system toward meritocratic selection.

2. **If stability matters most:** Increase `swap_sustained_cycles` from 3 to 5 or higher. This makes swaps rarer.

3. **If the system is too conservative:** Reduce `swap_threshold` from 0.05 to 0.02 and increase `OPPORTUNITY_COST_WEIGHT` from 0.10 to 0.15. This makes the system more responsive to underperformance.

4. **If focus budget feels wrong:** Budget of 3 is appropriate for 5-10 goals. For >15 goals, consider budget of 5. For <5 goals, budget of 1-2.

5. **UMH blend K:** Default 3 is appropriate. Increasing K dilutes focus; decreasing to 1 loses cross-goal signal.

---

## Test Harness

**File:** `tests/test_system_behavior_stress.py`
**Tests:** 39 (9 sections)
**Runtime:** ~18 seconds
**Dependencies:** None (all in-memory, no DB, no LLM)

```bash
python3 -m pytest tests/test_system_behavior_stress.py -v
```
