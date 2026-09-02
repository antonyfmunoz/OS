#!/usr/bin/env python3
"""Wave 2 Mandatory Pass 1 — deliberate failure/recovery driver (single-flight).

Replicates the prior QUALIFIED failure/recovery lifecycle exactly:
  preseed → seed(clean) → dispatch_collector → wait w15 → write-scenario-map
  → pause-before-dispatch → inject-failure(tools-revoked-a) → start_runner
  → resume → poll → (driver returns; teardown run separately after terminal)

Bound to exact SHA c6462dc25c51e70d1a41fefd591f10c770696f58.
Consumes ONE field unit at dispatch_collector (invocation #52).
"""
import sys, json, time
from datetime import datetime, timezone

SHA = "c6462dc25c51e70d1a41fefd591f10c770696f58"
VARIANT = "tools-revoked-a"  # revokes Edit/Write on A's first attempt (genuine capability failure)

sys.argv = ["wave2_field_dispatch.py", "preflight"]
sys.path.insert(0, "/opt/OS/.claude/worktrees/OS-mvp-wave2-governed-execution/scripts")
import wave2_field_dispatch as m

# The driver runs run_passes-adjacent in-process helpers AND the CLI subcommands;
# it drives mesh reads first, so it MUST preseed the worktree substrate exactly
# like the green run_passes fix, or the in-process attempts imports crash.
m._resolve_env()
m._ensure_mesh_secrets()

runner = m.Runner(dry_run=False)

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[failrec {ts}] {msg}", flush=True)

# run_id: one pass, -p1
run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-p1"
log(f"run_id={run_id} sha={SHA} variant={VARIANT}")

# ---- 0. candidate already deployed + healthy (proven pre-dispatch). restart for RES hygiene. ----
log("restart candidate for fresh RES + wait ready")
runner.run(["docker", "restart", m._CANDIDATE_CONTAINER], timeout=120, check=False)
ready = m._wait_candidate_ready(runner, timeout_s=180.0)
if not ready.get("ready"):
    log(f"REFUSE: candidate not ready after restart: {ready}")
    print(json.dumps({"ok": False, "stage": "candidate_ready", "detail": ready}))
    sys.exit(2)
log(f"candidate ready in {ready.get('waited_s')}s")

# ---- 1. seed fixture (clean) ----
fixture = m.seed_fixture(runner, SHA, run_id, "clean")
if not fixture.get("dest"):
    log(f"REFUSE: seed_fixture failed: {fixture}")
    print(json.dumps({"ok": False, "stage": "seed", "detail": fixture})); sys.exit(2)
log(f"seed_fixture dest={fixture.get('dest')}")

# ---- 2. dispatch collector (CONSUMES THE UNIT — invocation #52) ----
log("DISPATCH COLLECTOR (consumes invocation #52)")
dispatched = m._dispatch_collector(runner, run_id=run_id, pass_num=1, scenario="full", sha=SHA)
log(f"dispatch_collector ok={dispatched.get('ok')} detail={dispatched}")
if not dispatched.get("ok"):
    print(json.dumps({"ok": False, "stage": "dispatch", "detail": dispatched})); sys.exit(3)

# ---- 3. wait for collector to reach w15 ----
log("waiting for collector w15 (execution authorization)...")
if not m._wait_collector_authorization(runner, run_id, 1):
    log("collector did NOT reach w15")
    print(json.dumps({"ok": False, "stage": "w15", "run_id": run_id})); sys.exit(4)
log("collector reached w15")

# ---- 3b. PRESEED worktree substrate before any in-process attempts import ----
m._preseed_worktree_substrate()
log("worktree substrate preseeded")

# ---- 4. bindable grant wait + write-scenario-map ----
binding, berr = m._wait_for_bindable_grant(runner, sha=SHA, run_id=run_id)
if binding is None:
    log(f"REFUSE: grant never bindable: {berr}")
    print(json.dumps({"ok": False, "stage": "bindable_grant", "detail": berr, "run_id": run_id})); sys.exit(5)
smap = m.write_scenario_map(runner, SHA, run_id)
log(f"scenario_map written={smap.get('written')} grant={smap.get('grant_id')} plan={smap.get('plan_record_id')}")
if not smap.get("written"):
    print(json.dumps({"ok": False, "stage": "scenario_map", "detail": smap, "run_id": run_id})); sys.exit(5)

# ---- 5. pause before dispatch (arm the admission window) ----
pause = m.pause_before_dispatch(runner, SHA, run_id)
log(f"pause paused={pause.get('paused')}")
if not pause.get("paused"):
    print(json.dumps({"ok": False, "stage": "pause", "detail": pause, "run_id": run_id})); sys.exit(6)

# ---- 6. inject failure (tools-revoked-a) ----
inject = m.inject_failure(runner, SHA, run_id, VARIANT)
log(f"inject armed={inject.get('armed')} target={inject.get('target_task_id')} arming={inject.get('arming','')[:80]}")
if not inject.get("armed"):
    print(json.dumps({"ok": False, "stage": "inject", "detail": inject, "run_id": run_id})); sys.exit(7)

# ---- 7. start runner ----
rs = m.start_runner(runner, SHA, run_id, 0)
log(f"start_runner started={rs.get('started')}")
if not rs.get("started", rs.get("dry_run", False)):
    print(json.dumps({"ok": False, "stage": "start_runner", "detail": rs, "run_id": run_id})); sys.exit(8)

# ---- 8. resume (release the pause; admission proceeds with failure armed) ----
resume = m.resume_after_pause(runner, SHA, run_id)
log(f"resume released={resume.get('released')} arming_valid={resume.get('arming_valid')}")
if not resume.get("released"):
    print(json.dumps({"ok": False, "stage": "resume", "detail": resume, "run_id": run_id})); sys.exit(9)

# ---- 9. poll to terminal ----
log("polling collector to terminal...")
try:
    terminal = m._poll_status(runner, run_id, 1)
    log(f"terminal state={terminal.get('state')} stages={terminal.get('stages_done')}")
finally:
    if rs.get("started"):
        stop = m.stop_runner(runner, SHA, run_id)
        log(f"stop_runner stopped={stop.get('stopped')}")

print(json.dumps({
    "ok": terminal.get("state") == "passed",
    "stage": "terminal",
    "run_id": run_id,
    "sha": SHA,
    "variant": VARIANT,
    "terminal": terminal,
}, indent=2))
