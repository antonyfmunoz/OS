# Wave 2 — Beast Reconciliation + Zero-Quota Pre-Field Preflight

**Target exact SHA:** `c6462dc25c51e70d1a41fefd591f10c770696f58`
**Performed:** 2026-08-08. **ZERO field quota consumed. No collector dispatched.**

## 1. Five-way exact-SHA agreement — PROVEN
```
VPS HEAD                                   = c6462dc25c51e70d1a41fefd591f10c770696f58
origin/feat/mvp-wave2-governed-execution   = c6462dc25c51e70d1a41fefd591f10c770696f58
PR #313 headRefOid                         = c6462dc25c51e70d1a41fefd591f10c770696f58
Beast-main       (C:\dev\dev\OS)           = c6462dc25c51e70d1a41fefd591f10c770696f58
Beast-collector  (C:\dev\wave2_wt)         = c6462dc25c51e70d1a41fefd591f10c770696f58
```
- Reconciliation mechanism (sanctioned): `git -C C:\dev\dev\OS fetch origin <branch>` →
  `git -C C:\dev\dev\OS reset --hard origin/<branch>` (Beast-main, "HEAD is now at c6462dc25");
  `git -C C:\dev\wave2_wt fetch` → `git -C C:\dev\wave2_wt checkout --detach <sha>` (collector).
- **BEFORE:** both Beast worktrees at the OLD `4778030c7…`. **AFTER:** both at `c6462dc25…`.

## 2. Clean-state proof
- VPS source: clean.
- Beast-main: tracked-clean (untracked scratch only — `data/proof/`, `data/certification/`,
  scan scripts, `*.png`, `yolov8n.pt`, etc.; none are Wave 2 field evidence and none were
  destroyed by the fetch/reset — reset --hard does not touch untracked files).
- Beast-collector: fully clean (empty `git status --porcelain`).
- PR #313: OPEN / DRAFT / UNMERGED (mergedAt=null). Wave 3: NOT STARTED.

## 3. Driver / freeze truth — DEFINITIVE
Field execution consumes TWO tracked scripts, both at the reconciled SHA, tracked-clean,
with NO separate frozen artifact:
- **Host driver (VPS):** `scripts/wave2_field_dispatch.py` (green `run` → `run_passes` +
  failure/recovery subcommands). Runs from the VPS worktree at `c6462dc25…`.
- **Collector (Beast):** `C:\dev\wave2_wt\scripts\wave2_field_collector.py` — invoked by
  `_build_start_command`; confirmed present, at HEAD `c6462dc25…`, tracked-clean.
- **No frozen 0444 `.py` driver artifact exists** (0 `*frozen*` files, 0 `DIGEST.md`).
  The summary-referenced digest `978a3757…` has NO corresponding live file in this tree.
  **No external frozen copy participates.** The SHA pinning + five-way agreement IS the
  freeze; there is nothing to re-freeze.

## 4. Host state
- Disk: 32G free (84% used) — healthy. Inodes: 19% used — healthy.
- Swap: 929Mi/4.0Gi = 22.7% — well under the 60% critical threshold.
- Provider pressure: `moderate`; `_get_swap_pct()`=22.7; **`allow_execution()=True`** (non-critical).
- Docker: `os-operator` healthy; all production containers up.

## 5. Worker-CLI liveness — PROVEN through the exact worker path
- `worker_claude_cli._resolve_cli_path()` → `/usr/local/bin/claude`.
- Real prompt via that exact path (`-p ... --output-format stream-json --verbose`):
  returncode **0** (NOT -7 SIGBUS); assistant content **'ready'** (real model output);
  ResultMessage `subtype=success, is_error=False`; no stderr. The ENOSPC truncation is
  fully repaired.

## 6. Mutex / residue — CLEAN
- VPS: 0 field procs (dispatch/runner/collector/worker).
- Beast: 0 collector / 0 runner / 0 candidate worker (only the probe's own shells matched).
- Target SHA: 0 protected refs, 0 targets dirs, 0 spool, 0 leases.

## 7. Fresh state — PROVEN
- Candidate mutable runtime `/var/lib/umh/candidates/wave2/c6462dc25…/`: **ABSENT** →
  ExecutionAttempt count = 0 by construction; no targets/spool/correlated state.
- Old-SHA (`4778030c7…`) state is isolated by the SHA-keyed path; cannot bleed into the
  new SHA. Fresh-state law retires per-run state at dispatch under the new SHA's own path.

## 8. Corrected green import/binding lifecycle — PROVEN at reconciled SHA
- `test_wave2_run_passes_runner_lifecycle.py` + `test_wave2_dispatch_import_paths.py`: 45 passed.
- Green-harness invariants (20 targeted): stale `/opt/OS` substrate cannot win; worktree
  `substrate.execution.attempts` resolves deterministically; binding materializes before
  runner admission; green injects NO deliberate failure.

## 9. Zero-quota preflight verdict
`preflight ok: True`, `qualification_verdict.ok: True`, reasons: [].
mesh_health: healthy (node `windows-desktop`); daemon Ready; session 1 (interactive).

**One flagged pre-dispatch condition (NOT a defect):** `beast_to_origin: 000`. Root cause:
the candidate container `os-operator-candidate-w2` is NOT running (only production
`os-operator` is up), so port 10443 has no listener (the VPS itself also gets 000 → not a
Beast network fault). The candidate is brought up at campaign start (`deploy-candidate` +
`run_passes` `docker restart` + `_wait_candidate_ready`), so this is expected idle-state.
The dispatcher's preflight correctly excludes `beast_to_origin` from its required gate.
**Precondition for a live campaign: deploy + start the candidate container at `c6462dc25…`
and confirm health before dispatch.**

## 10. Exact-head readiness verdict
**READY** to begin a fresh four-pass Wave 2 field qualification campaign at
`c6462dc25c51e70d1a41fefd591f10c770696f58`, subject to the single expected pre-dispatch
step of bringing the candidate container up at this SHA (handled by the campaign's own
`deploy-candidate` + pass-1 restart). No candidate/harness/host/worker blocker remains.
