# Pass 1 (invocation 41) — Composition Conflict on OBJECTIVE.md

**Date**: 2026-08-08 | **Run**: `20260808T014829Z-p1` | **SHA**: `69f9fe272d5bbb1b4d0b16b503e1879807ff8c5d`
**Quota**: invocation 41 of 46 (consumed at collector dispatch 18:48:37 PT)
**Classification**: CANDIDATE-ATTRIBUTABLE / DETERMINISTIC / Wave-2-blocking

## The invocation-40 fix is PROVEN in the field ✅

Every stage up to composition worked, including the exact durability chain that
invocation 40 proved broken. Attempts:

| attempt | task | status | kind | # | prev |
|---|---|---|---|---|---|
| ea-55bf81e9c2b3 | wp-94f3bcd9a755 (A) | failed | worker | 1 | — |
| ea-ea6f98b562fb | wp-94f3bcd9a755 (A retry) | succeeded | worker | 2 | ea-55bf81e9c2b3 |
| ea-e1d302bfa4c3 | wp-47fb00e975d0 (B) | succeeded | worker | 1 | — |
| ea-ca042bc12120 | wp-dbaadab5f4ce (C) | blocked | control_plane_composition | 1 | — |

Captured at inspection (before runner-stop released the refs):
```
refs/umh/promoted/…/wp-47fb00e975d0/ea-e1d302bfa4c3 = 684cfb81762b8b23938eabb98cf0a4e7958345a8
refs/umh/promoted/…/wp-94f3bcd9a755/ea-ea6f98b562fb = 49d3e72ad16f2c26a755a8687363b08d44bac8e6
refs/umh/verified/…/wp-47fb00e975d0/ea-e1d302bfa4c3 = 684cfb81762b8b23938eabb98cf0a4e7958345a8
refs/umh/verified/…/wp-94f3bcd9a755/ea-ea6f98b562fb = 49d3e72ad16f2c26a755a8687363b08d44bac8e6
```

PROVEN in the real field:
- injection landed on A attempt 1; A1 failed with NO false Proof
- exactly ONE distinct retry (A2, attempt#2, prev=A1) — correct lineage
- A retry succeeded; B succeeded independently
- Task C created as `control_plane_composition`, NEVER worker
- **both A and B worker commits were PROMOTED into durable storage**
- **VERIFIED == PROMOTED** for both (verified ref == promoted ref == worker commit)
- this is exactly the invocation-40 defect class, now closed and field-proven

## The new defect: predecessors always conflict on OBJECTIVE.md

Composition reached the merge step and refused:

    composition conflict: predecessors conflict on ['OBJECTIVE.md'] —
    refusing to compose a conflicted tree

Root cause (deterministic): the worker's TRUSTED-PROJECTION phase
(`worker_claude_cli.project_task_local_objective` → `_commit_trusted_projection`)
rewrites `OBJECTIVE.md` to each Task's OWN task-local objective and commits it as
the attempt's base BEFORE the worker runs. So each retained predecessor commit
carries a DIFFERENT `OBJECTIVE.md`:

- merge-base: `# Objective: Add note search to the fixture app`
- A (ea-e1d302bfa4c3): `# Your Task … wp-47fb00e975d0`
- B (ea-ea6f98b562fb): `# Your Task … wp-94f3bcd9a755`

The worker CODE files are perfectly disjoint (A: app/static + tests/test_ui_search.py;
B: app/main.py + app/store.py + tests/test_search_api.py — zero overlap). The ONLY
conflict is the system-projected `OBJECTIVE.md`, which diverges by construction in
every lane.

## Consequence

`compose_predecessors` correctly refuses a conflicted tree — but because the
trusted-projection commits a divergent `OBJECTIVE.md` into every predecessor's
retained base, EVERY predecessor pair conflicts on it, so fan-in composition can
NEVER succeed in the field. Task C blocks → Task D never runs → the graph never
completes. This is a "contract right, production unwired" seam between the
trusted-projection design and the composition merge.

## Minimum correction scope (hypothesis — for owner review, NOT applied)

The composition merge must not treat the system-projected `OBJECTIVE.md` (and any
other trusted-projection system file, e.g. `SHARED_CONTEXT.md`) as worker content.
Options: (a) compose over the pre-projection base so system files are identical
across predecessors; (b) exclude the trusted-projection paths from the merge (they
are control-plane bookkeeping, never the Task's deliverable); (c) re-project a
single canonical OBJECTIVE.md onto the composed tree. Any of these is a
composition/worker-projection change → NEW SHA, voids the remainder of this
campaign.

## Quota / state

Field quota: 41/46 consumed, 5 available (invocation 41 consumed, correctly).
No reserve used (deterministic candidate defect — reserve law forbids it).
Runner + Beast collector stopped; refs released on runner stop.
