# Invocation 40 — Verified-Commit Durability Defect Evidence

**Date**: 2026-08-08 | **Run**: `20260807T234550Z-p1` | **SHA**: `9fa480d106a09e985788c5d11cd4ee9dadf39516`
**Quota**: invocation 40 of 45 (consumed at collector dispatch 16:46:02 PT)
**Frozen driver digest at run time**: `fc6f318740c768450ee5daa28cd994df1d3572019b7de7388fee5bd90e5bdee7`
**Classification**: CANDIDATE-ATTRIBUTABLE / DETERMINISTIC / CRITICAL / WAVE-2-BLOCKING

## Defect

The bwrap-isolated Claude CLI worker creates git commits that exist only inside its
sandbox. After worker exit the commit objects do not exist in the shared
repository/object database. `retain_verified_commit` correctly refuses
(`update_ref … nonexistent object`), terminalize withholds the lease (SECURITY
path), no `refs/umh/verified/**` ref is ever created, and Task C blocks:
"dependency … has no retained commit under refs/umh/verified".

Deterministic across both field runs:
- This run: `ea-112cd869e5a0` (B, reported `80bee6ce…`), `ea-e626792e7f7a` (A2, reported `d4e80a47…`)
- Prior run `20260807T005250Z-p1` @ `131549ee4`: `ea-8aad39fa40a0` (reported `1145db4c…`), `ea-d7a3ea9b5b3c` (reported `8bf5eda8…`)

All four: verifier passed, retention refused with "nonexistent object".

## What invocation 40 field-qualified despite the failure

Exact-SHA pre-dispatch reconciliation; `w2-<run_id>` grant binding (18s);
run-bound scenario map; admission pause; injection landed on map-resolved Task A;
failed A1 produced NO false Proof (`files=0` refused); B succeeded independently;
exactly one distinct A retry with correct lineage; A2 succeeded; Task C created
as CONTROL_PLANE_COMPOSITION and NEVER as worker — the Round-12 store/declaration
authority boundary held in the real field.

## Files

| File | Content |
|---|---|
| `runner_20260807T234550Z-p1.log` | Runner log incl. all retention errors and SECURITY withhold lines |
| `execution_attempts.jsonl` | Attempt ledger: A1 failed / B succeeded / A2 succeeded / C blocked (`control_plane_composition`) |
| `environment_leases.jsonl` | Lease ledger incl. the two ACTIVE-WITHHELD leases |
| `proof_packages.jsonl` | The two verifier proofs (proof-03e2973ae8b0, proof-0dd43094d06a) — bound to sandbox-ephemeral state |
| `scenario_map.json`, `execution_binding.json` | Run-bound authority artifacts |
| `run_manifest.jsonl` | Registered run resources |
| `spool_20260807T234550Z-p1/` | Full spool (processed/consumed envelopes) |
| `failpass_driver_output.log` | Frozen driver stage log |
| `final_readonly_proof.txt` | Post-mortem read-only proof: refs empty, objects MISSING, worktree at fixture base |

## Withheld leases (why preserved at defect time)

- `lease-bf67fd197e50` (B): terminalize refused release because retention failed —
  by design, releasing would destroy the verified commit. In this defect the commit
  never durably existed at all.
- `lease-b418e7c936e3` (A2): same; its worktree `auto-ed6de39a` was already absent
  from disk at inspection time — additional evidence the sandbox state evaporates.

Both were torn down by governed teardown AFTER this evidence set was preserved.
