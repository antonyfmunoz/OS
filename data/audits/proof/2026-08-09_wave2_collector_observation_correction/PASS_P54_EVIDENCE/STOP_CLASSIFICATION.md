# Pass 1 (#54) Stop Classification — NOT QUALIFIED

**Run ID:** 20260809T144154Z-p1
**SHA:** 842434dc3fa3ed16540673f5df48950ccf6a2674
**Invocation:** #54 (CONSUMED)
**Terminal:** `failed` — 33/36 stages OK; failed: w16, w26, w27
**Classification:** HARNESS DEFECT (collector live-UI observation model) —
NOT candidate-attributable, NOT an external transient.

## Candidate: INNOCENT — complete property proven

| Attempt | Task | Status | Kind | Evidence |
|---|---|---|---|---|
| ea-3cd3a2eb7f09 | wp-3153d9b11ca4 (A) | FAILED | worker | tools-revoked-a injection worked |
| ea-955f57f15c25 | wp-d5369f58e0b4 (B) | SUCCEEDED | worker | proof-41fbe9e5d756; 96.9s dispatched overlap with A |
| ea-8dea6c3fdecc | wp-3153d9b11ca4 (A retry) | SUCCEEDED | worker | prev=ea-3cd3a2eb7f09 (correct lineage); proof-e9c2a8bd904c |
| ea-249228dabe19 | wp-adcb1876a63b (C) | SUCCEEDED | control_plane_composition | proof-97f8386d9a47 with BOTH predecessor_commits |
| ea-043c1f5a8d19 | wp-cab2825165cd (D) | DISPATCHED | worker | runner stopped 25s in when collector reached terminal |

Teardown released 2 trusted + 1 composed + 2 promoted refs (they existed —
promotion/retention worked). zero_ref_residue=true.

## The proof-inspector correction is FIELD-VALIDATED

w16 detail: `concurrent_tasks=['wp-3153d9b11ca4','wp-d5369f58e0b4']
dispatched_overlap_s=96.9 both_dispatched=True execution_surface=False`.
The collector identified the composition THROUGH the proof-inspector API —
the exact read that 404'd in #53 — and w17/w18 (durable composition /
verification observation) PASSED. Three of w16's four conjuncts green.

## The three failures — one defect class (point-in-time live-UI checks)

1. **w16 `execution_surface=False`:** `page.locator('[data-testid="w2-execution-root"]').count()`
   is evaluated on whatever view the Playwright page is on. The collector
   NEVER navigates to the execution panel (only `page.goto` calls are initial
   load + fixture page); after the w15 approval flow the page sits on the
   approvals view, so the conjunct is structurally False. It was also False
   in #53 (recorded in that run's detail and flagged as "secondary" in the
   #53 root-cause analysis) — outside the authorized proof-surface-only
   correction, and never green in the field since the 95a88fc99 w16 rewrite.
2. **w26 `report_in_thread=False`:** point-in-time body-text check at t=309s,
   4s after w25. Task D — the task whose completion produces the report —
   was dispatched at t≈296s and takes ~100s; the report could not exist yet.
   Consequential timing: w16's 224s stall (waiting on ~236s of real worker
   latency: A-fail 97s → retry 111s → C) pushed w26 into an impossible
   window.
3. **w27 lineage all-False with opened=True:** clicks the first open-task
   affordance found and immediately counts drawer elements on a page that is
   not on the execution/work panel; same navigation gap as w16.

## Why this is a STOP (Zero-Margin Stop Law)

Consumed and not qualified → STOP after governed teardown (done, clean) and
evidence preservation (this dir). No retry, no substitution, no source edit,
no self-authorization. The minimum correction is collector-side (tracked
source) → new SHA → this campaign cannot be completed at 842434dc3 regardless.

## Quota consequence (arithmetic, not a recommendation)

54/57 consumed; 3 remain. A fresh campaign at any new SHA requires 4
mandatory passes. 3 < 4 — the standing ceiling can no longer satisfy the
campaign protocol. Owner decision required.

## Minimum correction boundary (collector only — zero candidate changes)

- `scripts/wave2_field_collector.py` w16: navigate to the execution panel
  before the `execution_surface` check, or replace the conjunct with the
  already-passing durable evidence (attempt intervals + composition proof).
- w26: bounded wait for Task D completion/report instead of a point-in-time
  body check (driver/runner must remain up until D terminalizes).
- w27: perform the open-task interaction from the panel that hosts it, with
  a bounded wait for drawer mount.
No substrate, cockpit, or candidate-side changes required.
