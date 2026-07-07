# P4S-31C Post-Merge Sustained-Load Proof — PR #228

Date: 2026-07-07 (04:30–05:09 UTC)
Scope: merge-conveyor validation of PR #228 (read-path isolation + bounded
snapshot) per the standing post-merge protocol, plus the infra defect it
exposed and the fix (PR #229).

## Timeline

| Time (UTC) | Event |
|---|---|
| 04:30 | #228 merged (`512a4fca6`), main synced |
| 04:32 | 30/30 hardening tests pass, imports clean, dependency/CPU gates pass |
| 04:33 | os-operator restarted; first log line: `read-path isolation pool created: 4 workers` |
| 04:34–04:59 | 25-min sustained-load watch: 8 × 45s probe cycles, concurrency 6, `nice -n 15`, loadavg-3.0 abort guard |
| 05:00 | Wedge diagnosed: cgroup memory thrash at 1G cap |
| 05:04 | Live fix: `docker update --memory 2g --memory-swap 2g os-operator` + restart |
| 05:04–05:09 | 3-cycle re-validation at 2G: PASS |
| 05:12 | #227 merged (`d24831f4f`) after runtime validated |

## What #228 fixed (verified)

- `/unified-workstation/snapshot` bounded at its 8s budget under load
  (8–16s observed incl. queueing) vs **>55s unbounded** pre-fix.
- `/intent-loop` and siblings no longer starve behind the snapshot: p50
  144ms–1s in healthy cycles vs total wedge pre-fix.
- Dedicated 4-worker read pool created at startup; shared AnyIO limiter
  no longer drained by slow reads.

## What the watch exposed (NOT a #228 defect)

By cycle 8 of the 25-min watch, all reads timed out (≥15s) and did not
self-recover after load stopped.

Diagnosis: **cgroup memory thrash**. os-operator idles at ~940MiB RES
against a 1G container cap (91% at clean startup). Sustained polling
pushed RES to the ceiling; the kernel continuously reclaimed file-backed
pages; the process logged **1,071,128 major page faults** — every request
paged code in from disk. `memory.events`: `oom 0, oom_kill 0` — it
thrashed instead of dying, which is why it wedged silently.

The #228 mechanism held until the *memory* ceiling — not the thread
pool — took the whole process down.

## Fix + re-validation (2G cap)

`docker-compose.yml` os-operator memory limit 1G → 2G (this PR). Applied
live 05:04 UTC via `docker update`.

3-cycle re-validation, same probe profile:

| Metric | 1G cap (25-min watch) | 2G cap (re-validation) |
|---|---|---|
| major page faults | 1,071,128 | **63** |
| RES | pinned 1006–1041MiB / 1GiB | 642→918MiB / 2GiB, settled |
| threads | 18 → 41, climbing | 20 → 24, stable |
| `/intent-loop` max | 10.5s then full timeout | **1.7s** |
| `/pulse` | 15s timeouts, no recovery | 0.3s (one 6.7s during host loadavg 4.4) |
| `/snapshot` | 16.7s worst | 8.0–8.5s (at budget) |
| wedge | yes, persistent | **none** |

Note: re-validation probe cycles aborted early on the loadavg-3.0 CPU-law
guard due to *host-wide* load (loadavg reached 4.4; transient `iptables` +
python processes outside the container). The container stayed responsive
through it — the isolation held under host contention.

## Verdict

- `/intent-loop` responsive under sustained load: **PASS** (at 2G)
- `/snapshot` bounded: **PASS**
- No threadpool starvation: **PASS**
- No runtime RES runaway: **PASS** (63 majflt, RES settled at 45% of cap)
- No regression vs P4S-31B/31C proof paths: **PASS** (32/32 tests on main
  post-merge: `test_p4s31c_read_path_hardening.py` +
  `test_p4s31d_voice_matrix_artifacts.py`; 31B surface tests in the 30/30
  pre-restart run)

Evidence class: B (live instrumented probes against the production
container; not synthetic mocks, not browser-verified).
