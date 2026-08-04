# Wave 2 — Shipped Lifecycle Trace (BEFORE), at 0c5b3be96

Each boundary traced from source at the exact SHA. Findings confirmed, not inferred.

| # | Boundary | File / function | Carries scope? |
|---|---|---|---|
| 1 | canonical WorkPacket | `WorkRequirements.writable_path_scope` + `scope_declared` | **YES** — first-class, persisted |
| 2 | canonical package build | `attempts/dispatch.py:109-110` `compile_attempt_package` → `governance_constraints.append(f"writable_path_scope={sorted(...)}")` | **YES**, sealed under `package_hash` |
| 3 | **runner package build** | `scripts/wave2_attempt_runner.py:595-599` `class _Package` | **NO — F-2.** 4 attrs only: `role_instructions`, `operation_instructions`, `ordered_context`, `operation_identity` |
| 4 | spool envelope | `attempts/spool.py:39-68` `DispatchEnvelope` | **NO — F-2.** No scope field exists |
| 5 | spool deserialize | `spool.py` `claim()` → `DispatchEnvelope(**d)` | nothing to validate |
| 6 | launcher | `worker_claude_cli.py:450` `run_worker_in_lease` | reads `_sealed_writable_scope(package)` |
| 7 | scope resolution | `worker_claude_cli.py:556-568` | `declared_scope is None` → **refuses**. With (3), refuses **100% of real dispatches** |
| 8 | bind computation | `field_task_scope.py:457` `readonly_binds_for_scope` | `.git` **always** read-only (`:513-515`) |
| 9 | sandbox profile | `host_isolation.py` `build_bwrap_command` | `--bind <lease>` then `--ro-bind` each subpath |
| 10 | **git ops** | worker, inside bwrap | **F-1.** `.git` read-only → `index.lock` fails, `ADD_RC=128` |
| 11 | **projection** | `worker_claude_cli.py:548` (writes `OBJECTIVE.md`, `SHARED_CONTEXT.md`) | **F-3.** Runs AFTER `base_commit` fixed at `:477` → inside `<base>..HEAD` |
| 12 | artifact capture | `worker_claude_cli.py:629` `_capture_git(worktree, base_commit)` | `<base>..HEAD` |
| 13 | verification | `verification.py` `_diff_scope_verdict` | `git diff --name-only <snapshot_ref>` + `ls-files --others` |

## Process attribution (BEFORE)

- Git operations: the **worker**, inside bwrap.
- Projection/evidence writes: the **worker process**, inside bwrap, pre-launch — the
  defect. System bookkeeping is executed under worker confinement and attributed to
  worker authority.

## Where scope is LOST

Between boundary 2 (correct, sealed) and boundary 3 (hand-built stub). The canonical
authority is built correctly and then **discarded** by the runner, which substitutes a
4-attribute object. Everything downstream is starved, and the fail-closed guard at
boundary 7 then denies every real dispatch.

**F-2 is the same defect class this campaign exists to fix: a correction that never
reaches production.**

## F-4

`tests/test_wave2_hard_write_scope.py::_drive_launcher` always passes
`governance_constraints=[...]` — a shape boundary 3 never constructs — and never runs a
real `git commit`. So the suite proves the launcher works on input production cannot
produce, and never exercises boundary 10 at all. The stand-in bypass moved from the
object level (fixed earlier) to the **data** level.

## AFTER (target)

3. runner passes the **real** `ModelExecutionPackage` (or a faithful reconstruction
   carrying `governance_constraints`), never a stub.
4. `DispatchEnvelope` carries the governance fields; signature covers them.
5. deserialization **validates**: missing/malformed/widened → fail closed pre-launch.
10. per-attempt private ref namespace → authorized commit succeeds; hooks/config/HEAD/
    packed-refs/foreign refs stay read-only (18/18 proven).
11. projection moves to a **trusted phase** that commits it and re-anchors the attempt
    base, so worker diff excludes it (proven: worker diff = `['app/main.py']`; zero-write
    lane = `[]`).
