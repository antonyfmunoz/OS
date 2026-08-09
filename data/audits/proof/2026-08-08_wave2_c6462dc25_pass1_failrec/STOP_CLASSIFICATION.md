# Wave 2 — Mandatory Pass 1 (failure/recovery) — CONSUMED, NOT QUALIFIED — STOP

**Exact SHA:** `c6462dc25c51e70d1a41fefd591f10c770696f58`
**Invocation:** #52
**run_id:** `20260808T233546Z-p1`
**Purpose:** Mandatory Pass 1 — deliberate failure/recovery
**Outcome:** collector pass verdict = **failed** (`failed_stage: w16_ab_running_concurrent`, stages_done=36)
**Classification:** HARNESS TIMING/OBSERVATION DEFECT — candidate INNOCENT
**QUALIFIED / NOT QUALIFIED:** **NOT QUALIFIED**
**Quota:** consumed 1 → **52/56 consumed, 4 available (3 mandatory + 1 reserve)**
**Reserve state:** R1 unused (and NOT eligible for this defect class — see below)
**Residue:** teardown clean — `zero_ref_residue: true`, 0 homes/leases/worktrees, secret shredded, serve restored. Source clean, SHA intact, 0 procs.

---

## The governed property SUCCEEDED at the attempt level
All five ExecutionAttempts reached correct terminal states:

| Task | Attempt | Status | execution_kind | commits |
|---|---|---|---|---|
| A `wp-d322f3853606` | a1 | **failed** | worker | 0 | ← deliberate tools-revoked-a injection landed; no false Proof |
| B `wp-d22f64e318c6` | a1 | **succeeded** | worker | 1 | ← B independent success |
| A `wp-d322f3853606` | a2 | **succeeded** | worker | 1 | ← exactly one retry, correct lineage (same task, attempt 2), recovered |
| C `wp-9a428972beb0` | a1 | **succeeded** | **control_plane_composition** | 1 | ← Task C is composition, NEVER worker; A2+B fan-in |
| D `wp-d87f2198112e` | a1 | **succeeded** | worker | 0 | ← zero-write verification lane (files=0/commits=0) |

The binding materialized before runner admission (`scenario_map written=True`, grant
`exgrant-7b9dd319ece4`, plan `opr-7264f2b95df4`); the worktree substrate preseed worked
in the real field driver (`[failrec] worktree substrate preseeded`); injection targeted
`wp-d322f3853606` (task A). The A+B→C→D governed graph is present and correct.

## Why the pass did NOT qualify — the collector could not OBSERVE it
The collector's UI-observation stages failed because the entire graph completed FASTER
than the collector's DOM polling windows:

- `w16_ab_running_concurrent`: `dom_running=0, execution_surface=False` — A and B finished
  before the collector polled for "running."
- `w17_c_blocked`: `advanced_non_ab=3` — C had already composed+succeeded, never observed
  "blocked."
- `w18_ab_verified`: `succeeded_ab=[] proofs=[]` — by query time the graph had reconverged
  and refs released, so the UI showed no succeeded-AB/proofs.

## Root cause — harness timing assumption, NOT candidate, NOT external transient
The harness assumes the collector takes ~15-19 min to walk w01→w16 (documented in
`_wait_collector_authorization`), so the runner (started at w15) has workers RUNNING when
the collector reaches w16. Here the candidate was WARM (freshly deployed + restarted), so
the collector walked w01→w16 in **~30 seconds** (23:36:07 dispatch → 23:36:37 w16). The
runner started at 23:36:51; by the time its workers were created and running, the collector
had already polled w16 and seen `dom_running=0`. The graph then completed in ~2-3 min and
reconverged before w17/w18 could observe intermediate states.

This is a **harness ordering/observation assumption** (collector UI-walk speed vs runner
worker-creation latency), closest to a HARNESS DEFECT. It is NOT:
- a candidate defect (the property succeeded);
- an external transient (no mesh/executor/host/tooling failure — all green pre-dispatch);
- stale runtime state (fresh candidate, 0 prior attempts).

## Why I STOP and do NOT use the reserve
Per the owner's **RESERVE LAW**, R1 is explicitly **NOT available for "deterministic
harness defects," "module-resolution defects," or "stale runtime state."** This w16
timing/observation failure is a harness-side assumption, not a proven external transient
with the required class (mesh/executor/host/tooling). Per the **CANDIDATE/HARNESS STOP
LAW**: "Any deterministic harness defect: STOP. Any requirement for a tracked
source/harness edit: STOP. A tracked edit creates a NEW SHA and voids the remainder of
this campaign." The likely fix (make the collector's w16 observation robust to fast graph
completion — e.g. the collector waits/retries the running-observation, or the runner is
gated to start only once the collector is at the w16 boundary) is a **tracked harness edit**
→ new SHA → voids this campaign. Therefore I STOP and return to the owner.

## Evidence preserved (this dir)
- `driver.log` — full lifecycle trace (preseed → seed → dispatch → w15 → binding → pause →
  inject → start → resume → poll → terminal).
- `attempts_ledger.jsonl` — the 5 attempts (property success).
- `collector_result.json` — the collector's stage-by-stage verdict (w16-w18 detail).
- `scenario_map.json` — the run's authenticated binding.
- `failrec_driver.py` — the exact driver used.
- Full shipped UI evidence: `/opt/OS/data/audits/proof/2026-08-08_wave2_field/raw/20260808T233546Z-p1/pass1/` (w01-w27 screenshots + DOM + network.jsonl).

## Exact state
- Quota: **52/56 consumed, 4 available (3 mandatory + 1 reserve)**. Prior invocations unchanged.
- Five-way SHA: intact at `c6462dc25…` (VPS/origin/PR/Beast-main/Beast-collector all verified pre-dispatch).
- Source clean. PR #313 OPEN/DRAFT/UNMERGED. Wave 3 NOT STARTED.
