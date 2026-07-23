# Wave 2 — Critical Repair Ledger (PR #313)

## Campaign truth

```
WAVE 2 IMPLEMENTATION:          IN REPAIR
DETERMINISTIC QUALIFICATION:    INVALIDATED
FIELD HARNESS QUALIFICATION:    INVALIDATED
REAL-WORKER QUALIFICATION:      NOT RUN
SECURITY REVIEW:                OPEN
PRODUCTION DEPLOYMENT:          NOT PERFORMED
MERGE:                          PROHIBITED
```

Head before repairs: `57c266b380cac6ec982d50088f2aa0f95e704f76`.

The earlier green matrix and rehearsal remain **historical evidence only**. They
cannot satisfy the repaired contracts, because their tests encoded the same false
assumptions as the defective implementation (see §"False-green tests" below).

## Why the prior claims were invalidated

Two independent adversarial reviews found **seven CRITICAL** defects, each
independently verified before acceptance. Every one failed **toward green** — the
harness would have reported a successful qualification while proving nothing.

| ID | Finding | Verified how |
|---|---|---|
| C1 | AttemptProofs never persisted — `ProofRuntime` exposes neither `store_package` nor `persist`, so `_persist_proof` always takes the in-memory `_packages` fallback; `proof_packages.jsonl` never created. Every SUCCEEDED attempt carries a dangling `proof_id`, and `_default_dep_lookup` only checks truthiness. | Ran `ProofRuntime()`: `has store_package: False`, `has persist: False` |
| C2 | Failure injection never fires — the task-A matcher cannot match real `wp-<hex12>` packet IDs. `inject-failure` would arm a marker that revokes nothing; the failure pass silently runs clean. | 2000 real-form IDs → **0/2000** matched; literal `"A"` → revoked |
| C3 | Two-worker concurrency unobtainable, and the ledger wedges — runner claims one dispatch per iteration and runs the worker synchronously; both dispatches get `expires_at = now+600`, so B is quarantined as expired on claim, and **no reaper exists**. B strands in DISPATCHED forever, permanently consuming a slot. | Read loop (one `claim_next` + blocking `run_worker_in_lease`); `grep quarantine` in poller/scheduler/runner → docstring only |
| C4 | Independent verification is blind — `_assignment_lookup` calls a nonexistent `list_assignments` and always returns `None`; `lease_lookup` never passed; `diff_scope` hardcoded `ok=True`; no independent checks. Any commit of anything earns a Proof. | Store API inspection; runtime lookup returns `None` |
| SEC-C1 | The bare 64-hex redaction rule (added during the incident fix) **destroys the proof manifest** — eats `artifact_sha256`, `package_hash`, `scope_hash`, docker image IDs. Plus an ordering bug: files are hashed, *then* rewritten by `_redact_tree`, so recorded hashes can never re-verify. | Regex applied to real hash shapes → all redacted; 40-hex git SHAs preserved; line order 1547 → 1551 |
| SEC-C2 | `worker_home` = `dirname(worktree_path)` → **shared across all leases**; real `~/.claude/.credentials.json` copied in and **never deleted**. OAuth credential persists past teardown; both concurrent workers share it read-write. | Path derivation identical for distinct leases; no cleanup anywhere in tree |
| SEC-C3 | A NOT-ready deploy still exits 0 — `readiness` is recorded but never branched on; `main()` returns 0 unconditionally. | Code path 786→803, `main()` `return 0` |

**SEC-C2 never fired** — 0 `.worker-home` dirs, 0 credential copies, 0 lease
worktrees, 0 signed artifacts on disk, because no worker ever ran. Pausing before
quota prevented a real credential incident. See
`docs/wave2_security_incident_closure.md`.

## Repair structure

| Commit | Scope | Status |
|---|---|---|
| R0 | Containment, teardown, security closure | **DONE** |
| R1 | Per-attempt credential/home isolation; immutable evidence pipeline | pending |
| R2 | Durable canonical Proof; real-Task-ID failure injection | pending |
| R3 | Two-worker concurrency; fail-closed verification; readiness exit semantics | pending |
| R4 | Eleven warnings; migrations/reverts; read-only-path corrections; matrix + runbook | pending |

## Warning register

| ID | Severity | Affected | Verified cause | Resolution | Test | Status |
|---|---|---|---|---|---|---|
| W5 | warning | `scheduler.py`, `field_control_plane.py`, `wave2_attempt_runner.py` | Un-APPROVED packets skipped with a bare `continue`; runner logs only when something happened → **silent forever stall** | report `skipped_not_approved`; log idle cycles with reason | pending | R3 |
| W6 | warning | `field_control_plane.py` | `dispatch_id` not unique per dispatch; `_seq`/`nonce` reset on restart → silent spool overwrite, stranded attempt | uuid-suffixed `dispatch_id`, uuid `nonce`, monotonic sequence | pending | R3 |
| W7 | warning | `field_control_plane.py` | `_role_resolver_for` dead code with the same uuid blindness | delete or wire with resolved IDs | pending | R2 |
| W8 | warning | `field_control_plane.py`, `poller.py` | Broad `except` → error text never surfaced (`errors=N` only) | log at warning; abort on N consecutive erroring cycles | pending | R3 |
| W9 | warning | `tests/test_wave2_field_control_plane.py` | Tests encode the same wrong assumptions; stub unfaithful (real worker keeps `Bash` and can still commit) | replace per §False-green tests; add `Bash` to revoked set | pending | R2/R4 |
| SEC-W1 | warning | `substrate/memory/candidate_generator.py` | Default relocation **orphans 259 live production records** (no migration) | revert (Wave 2 does not need it) or bounded migration | pending | R4 |
| SEC-W2 | warning | `substrate/memory/candidate_generator.py` | Explicit-`store_dir` branch still does eager `mkdir` → same crash pattern | move `mkdir` into `_append_jsonl` for both branches | pending | R4 |
| SEC-W3 | warning | `memory/watcher.py`, `promoter.py`, `claude_bridge.py` | Repo-relative writable paths → crash under `/app:ro` mid-run, burning a pass | route through `runtime_state_dir` | pending | R4 |
| SEC-W4 | warning | `wave2_field_dispatch.py` | Secret shredded only by explicit `teardown`; no `atexit`/`finally`/crash-handler shred (one orphan found on disk) | shred in crash handler + `finally` | pending | R1 |
| SEC-W5 | warning | `wave2_field_dispatch.py` | `$(cat)` failure → empty secret; runner fails closed but diagnosis is generic | verify secret file exists and is non-empty in `start_runner` | pending | R1 |
| SEC-W6 | warning | `wave2_field_dispatch.py` | `_run_secret_path` docstring claims container-readable; it is **host-only** — a future edit could "fix" the mount and hand the secret to the container | correct the docstring | pending | R1 |

Security, evidence, Proof, readiness, concurrency and current-truth warnings are
**not deferrable** per the order.

## False-green tests to replace

| Old test | Wrong assumption | Replacement |
|---|---|---|
| `test_driver_drives_full_graph_to_green` | asserts `a.proof_id` is *truthy*, never that it **resolves** | assert durable reread from a fresh `ProofRuntime` after restart |
| `test_driver_dispatch_fn_consults_failure_marker` | uses hand-picked `packet_id = "A"` — the one shape the matcher accepts | use real `wp-<hex12>` IDs from the scenario map |
| `test_driver_admits_independent_frontier_first` | admission ≠ execution; no concurrency asserted | assert `max(started) < min(completed)` with real overlap |
| `_stub_worker_drain` | zero-latency drain hides expiry/sequencing; models revocation ⇒ failure, but the real worker keeps `Bash` and may still commit | slow-worker stub; add `Bash` to the revoked set; assert genuine no-commit |

A test that mocks away the contract under test does not count.

## Verified-sound (not changed by the repair)

- Launch line does **not** leak to `ps`/`cmdline` (400 `/proc` samples); old form
  reproduced side-by-side and still leaks — regression genuinely closed.
- `_mint_run_secret` atomic `O_EXCL|0600`, fail-closed, 256-bit.
- `launch_log_tail` redacted **before** slicing.
- Worker cannot inherit `UMH_W2_DISPATCH_SECRET` (allowlist scrub →
  `['CLAUDE_CODE_OAUTH_TOKEN','HOME','PATH']`).
- nginx `${CANDIDATE_UPSTREAM}` substitution complete and fail-closed; WS block
  keeps a literal address (no keepalive pool).
- Poller always runs the scheduler pass after draining — the driver's
  first-frontier assumption is correct, and removing the redundant direct pass
  eliminated the lease-conflict path.
- Runner never mutates the ledger; no status inferred from file presence.
