# Tool Mastery Loop Closure — 2026-04-08

Closes the gap between the Tool Mastery Research Agent and the Tool
Mastery Author Agent. After this build, a single research run
automatically queues an authoring run through the Control Plane —
no human in the middle, no direct agent-to-agent imports.

## Pipeline before

```
detect (Manager) -> classify -> queue research action (CP)
                                       |
                                       v
                          dispatcher --execute (Research Agent)
                                       |
                                       v
                          research_artifact.json on disk
                                       |
                                       X  <-- manual hop required
                                       |
                          human runs author CLI
                                       |
                                       v
                          skill authored + verified
```

## Pipeline after

```
detect (Manager) -> classify -> queue research action (CP)
                                       |
                                       v
                          dispatcher --execute (Research Agent)
                                       |
                                       v
                          research_artifact.json on disk
                                       |
                                       v
                  Research Agent calls run_action(
                      type="run_script",
                      description="tool_mastery:author:<slug> ...",
                      risk_level="medium",
                      source_agent="tool_mastery_research_agent",
                      idempotency_key="tool_mastery:author:<slug>")
                                       |
                                       v
                          deferred queue (medium-risk policy)
                                       |
                                       v
                  dispatcher --execute-author (drainer)
                          for each match -> resume_action(id)
                                       |
                                       v
                  CP run_script executor invokes
                  scripts/tool_mastery_author.py
                                       |
                                       v
                          Author Agent (verify -> READY)
```

The Research Agent never imports the Author Agent. The only allowed
transport between them is `core.action_system.control_plane.run_action`.

## Files modified / created

- `core/tool_mastery_research_agent/agent.py` — added
  `_queue_author_action` and call site at end of `run()`. Queues a
  `run_script` action whose semantic type is `tool_mastery:author:<slug>`
  (encoded in description + inputs). Idempotent on
  `tool_mastery:author:<slug>` for 24h. Failure-tolerant — a CP outage
  cannot break a research run.
- `scripts/tool_mastery_research_dispatcher.py` — added
  `--execute-author` flag and `_drain_author_queue` helper. Lists
  deferred actions, filters by description prefix
  `tool_mastery:author:`, optionally filters by `--tool`, calls
  `resume_action` for each. Reports status, result_ok, stderr tail.
- `scripts/tool_mastery_author.py` (NEW) — thin CLI shim that supports
  both direct invocation (`--tool` + `--artifact`) and Control Plane
  action consumption (`--consume-action <file>`). Imports
  `core.tool_mastery_author_agent.agent.author` and returns the agent's
  result as JSON.

## Deviations from spec

1. **Action `type` field** — `core/action_system/actions.py`
   `ALLOWED_ACTION_TYPES` is a closed set: `run_script`, `shell_command`,
   `write_file`, `call_api`. A new `tool_mastery.author` type would be
   rejected by `validate_action`. Adapted by re-using `run_script` and
   encoding the semantic type in the action description prefix
   (`tool_mastery:author:<slug>`) and in `inputs.work_type="author"`.
   This matches the existing pattern used by
   `core/tool_mastery_manager/ensure.py` for research/refresh/repair
   actions.

2. **Drainer routing** — instead of synthesising a new author invocation
   from action JSON files on disk, the drainer calls
   `resume_action(id)`, which sends the action through the standard CP
   lifecycle (approve -> execute -> log). The `run_script` executor then
   invokes `scripts/tool_mastery_author.py` with the args queued by the
   Research Agent. This means every authoring run is fully logged in
   `/opt/OS/logs/execution/` with the same trail as any other CP
   action — no parallel pipeline.

3. **`--consume-action` mode** of `scripts/tool_mastery_author.py` is
   implemented and tested for parser correctness, but the live drain
   path goes through the CP executor + CLI args (not file consumption),
   so `--consume-action` is currently a fallback for manual replay.

## Validation trace

### 1. Initial deferred queue (baseline)

```
$ ls /opt/OS/logs/deferred/*.json | grep -v status | wc -l
2
```

Two pre-existing deferred actions, neither tool_mastery.author.

### 2. Run research dispatcher with --execute (loop fires here)

```
$ python3 /opt/OS/scripts/tool_mastery_research_dispatcher.py \
    --work-type research --tool stitch --execute --json
```

Output (trimmed):

```json
{
  "request": { "tool_slug": "stitch", "mode": "research", ... },
  "status": "fetch_failed",
  "run_dir": "/opt/OS/logs/tool_mastery_research/stitch/2026-04-09T01-28-23Z",
  "artifact_path": ".../research_artifact.json",
  ...
}
```

### 3. Confirm research artifact AND author action queued

```
$ cat /opt/OS/logs/tool_mastery_research/stitch/2026-04-09T01-28-23Z/manifest.json
```

Relevant fields:

```json
{
  "status": "fetch_failed",
  "fetched": 1,
  "fetched_ok": 0,
  "author_handoff": {
    "queued": true,
    "action_id": "1f96dd92-0430-464e-9dc8-b547e23e3eb6",
    "action_status": "validated"
  }
}
```

The Research Agent queued the author action even though fetches
failed (the rule is: queue when status != NO_SOURCES). Status
`validated` means the action sits in the deferred queue awaiting
explicit approval — exactly what the medium-risk policy requires.

### 4. Run dispatcher with --execute-author (drain)

```
$ python3 /opt/OS/scripts/tool_mastery_research_dispatcher.py \
    --execute-author --tool stitch
=== Tool Mastery AUTHOR queue drain ===
deferred actions scanned: 3
author actions matched : 1

  action_id : 1f96dd92-0430-464e-9dc8-b547e23e3eb6
  desc      : tool_mastery:author:stitch — Author skill from research artifact
  status    : failed
  result_ok : False
```

The drainer correctly:
- Read 3 deferred files (the 2 pre-existing + the new author action).
- Filtered down to the 1 author action for `stitch`.
- Called `resume_action`, which transitioned proposed → validated →
  approved → executed via the `run_script` executor.
- The executor ran `scripts/tool_mastery_author.py` with the queued
  args. The author agent returned `BLOCKED_NO_SOURCES` (exit code 1)
  because the underlying artifact had `fetched_ok=0`. This is the
  correct, honest failure — the loop closure works.

### 5. Direct authoring against a known-good artifact

To prove the full READY path end-to-end (the failure above was a fetch
problem from the network-restricted run, not a loop bug), invoked the
author script directly against an earlier artifact that has 1
successful fetch:

```
$ python3 /opt/OS/scripts/tool_mastery_author.py --tool stitch \
    --artifact /opt/OS/logs/tool_mastery_research/stitch/2026-04-08T23-26-05Z/research_artifact.json
```

Result:

```json
{
  "status": "authored_ready",
  "skill_path": "/opt/OS/skills/tools/stitch/SKILL.md",
  "best_practices_path": "/opt/OS/skills/tools/stitch/references/best_practices.md",
  "provenance_path": ".../authored_provenance.json",
  "sections_preserved": 19,
  "verifier_passed": true,
  "verifier_failures": [],
  "notes": [
    "existing skill appears human-authored; refusing to overwrite without force_rewrite=True"
  ]
}
```

Verifier passes. Skill marked AUTHORED_READY in preserve mode.
Provenance sidecar written. Same code path the drainer takes via the
`run_script` executor.

## Action queue logs

Before research run:

```
deferred files: 2 (unrelated pre-existing actions)
```

After research run:

```
deferred files: 3
new entry: 1f96dd92-0430-464e-9dc8-b547e23e3eb6
  description: "tool_mastery:author:stitch — Author skill from research artifact"
  source_agent: tool_mastery_research_agent
  risk_level: medium
  status: validated
```

After --execute-author:

```
deferred files: 2 (the action was resolved via resume_action and removed)
```

`resume_action` calls `delete_deferred(action_id)` on terminal state
regardless of success/failure, so the queue self-cleans.

## Final pipeline state

Automatic now:
- Manager detects coverage gap -> queues research action.
- Operator/cron drains research queue with `--execute`.
- Research Agent automatically queues a `tool_mastery.author` action
  through the Control Plane on every run that produces *anything*
  (status != NO_SOURCES).
- Operator/cron drains author queue with `--execute-author`.
- Author Agent runs via the standard CP run_script executor.
- Skill is verified; provenance is written.

Still manual:
- The two `--execute` and `--execute-author` drains. These are
  intentionally separate so a human (or scheduled job) can gate each
  expensive step. They can be wired into `orchestrator/` cron once the
  cycle is observed in production.
- Real-source authoring still requires that the underlying research
  fetch actually succeed. Network/fetch failures are honest no-ops, not
  fabrications.

## Gotchas

- The loop is gated on `status != NO_SOURCES`, not on `fetched_ok > 0`.
  A `fetch_failed` run will still queue an author action — the author
  agent then correctly returns `BLOCKED_NO_SOURCES`. This is by
  design: the manifest captures the queue attempt + author refusal as
  one auditable trail, rather than silently swallowing the run.
- Idempotency window is 24h on key `tool_mastery:author:<slug>`. A
  second research run within 24h returns a `skipped_duplicate` action
  rather than queuing again. To force re-author, drain the queue first
  or wait out the TTL.
- `resume_action` removes the deferred file on terminal state, so
  failed authoring runs are NOT auto-retried. The Manager's next
  coverage scan is what re-detects the gap and re-queues.
