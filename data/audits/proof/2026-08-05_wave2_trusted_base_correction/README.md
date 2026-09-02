# HIGH-1 starvation — production reproduction

`starvation_repro.py` drives the REAL `SandboxManager`, `LeaseManager`, and
`ControlPlanePoller._terminalize` at the PRODUCTION concurrency limit
(`max_parallel=2`, `scripts/wave2_attempt_runner.py:256`), forcing two withheld
retentions by making the CPU gate refuse.

Run it: `python3 data/audits/proof/2026-08-05_wave2_trusted_base_correction/starvation_repro.py`
(it anchors `sys.path` on its own checkout, so it always tests the tree it ships in).

## BEFORE — `_preserve_sandbox_slot` disabled (`starvation_repro_BEFORE.txt`)

```
withhold w1: withheld=True active_sandboxes=1
withhold w2: withheld=True active_sandboxes=2
THIRD TASK BLOCKED: Max parallel sandboxes (2) reached. Active: 2
expire_stale cleared: 2
active_sandboxes after expire: 2      ← leases cleared, SLOTS never returned
BOTH PRESERVED COMMITS SURVIVE GC: True
VERDICT: FAIL
```

Two withholds halt the **whole run**. `expire_stale` runs every poller cycle and
clears the leases, but the sandbox slots are never freed, so the run never
recovers. The commits survive — the withhold does protect them — but nothing else
can execute.

## AFTER (`starvation_repro_AFTER.txt`)

```
withhold w1: withheld=True active_sandboxes=0
withhold w2: withheld=True active_sandboxes=0
THIRD TASK ADMITTED: …/wt/auto-94e1801f
expire_stale cleared: 3
BOTH PRESERVED COMMITS SURVIVE GC: True
VERDICT: PASS
```

The withhold now frees the slot via `cleanup_sandbox(preserve_branch=True)` —
worktree removed, branch ref kept — so unrelated Tasks keep running while the
verified commits stay reachable through `git gc`. The leases themselves stay
ACTIVE (retry for those Tasks remains blocked, the intended trade) and expire
non-destructively at TTL.

Pinned by `tests/test_wave2_verified_commit_retention.py::
test_two_withholds_do_not_starve_a_third_task_at_production_max_parallel`.
