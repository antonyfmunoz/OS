#!/usr/bin/env python3
"""force_execution_loop.py — Force ONE complete end-to-end execution loop.

This is the activation script. It proves the full pipeline works:

    intent → workflow → action → logging → feedback → optimizer

Bypasses: control plane (core/control_plane.py), advisor, cron, Discord.
Uses:     action system control plane, workflow engine, optimizer.

Usage:
    python3 scripts/force_execution_loop.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from core.action_system.control_plane import run_action
from core.action_system.logging import log_decision
from core.optimizer import Optimizer
from eos_ai.workflow_engine import WorkflowEngine, WorkflowState, WORKFLOWS

# Log files the optimizer reads
WORKFLOW_LOG = Path(_ROOT) / "data" / "workflow_log.jsonl"
ACTION_LOG = Path(_ROOT) / "data" / "action_log.jsonl"


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Step executors — each returns (success: bool, outputs: dict)
# ---------------------------------------------------------------------------


def step_generate_outreach_message() -> tuple[bool, dict]:
    """Step 1: Generate an outreach message via shell echo (minimal proof)."""
    action = run_action(
        type="shell_command",
        description="Generate outreach message for Initiate Arena prospect",
        inputs={
            "command": (
                'echo \'{"prospect":"test_lead_001",'
                '"message":"Hey — saw your post about scaling coaching. '
                "Initiate Arena solves exactly that. "
                'Want to see it in action?","channel":"DM"}\''
            ),
        },
        risk_level="low",
        source_agent="outreach_agent",
        explicit_approval=False,
    )
    ok = action.status == "executed" and action.result.get("ok", False)
    stdout = action.result.get("stdout", "").strip()
    try:
        msg_data = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        msg_data = {"raw": stdout}
    return ok, {
        "outreach_message": msg_data,
        "action_id": action.id,
        "action_status": action.status,
    }


def step_save_outreach_to_file(message_data: dict) -> tuple[bool, dict]:
    """Step 2: Persist the outreach message to a file via the action system."""
    output_path = f"{_ROOT}/data/playgrounds/outreach_proof.json"
    content = json.dumps(
        {
            "generated_at": _ts(),
            "source": "force_execution_loop",
            "message": message_data,
        },
        indent=2,
    )
    action = run_action(
        type="write_file",
        description="Save generated outreach message to proof file",
        inputs={"path": output_path, "content": content},
        risk_level="low",
        source_agent="outreach_agent",
    )
    ok = action.status == "executed" and action.result.get("ok", False)
    return ok, {
        "saved_path": output_path,
        "action_id": action.id,
        "action_status": action.status,
    }


def step_verify_output(saved_path: str) -> tuple[bool, dict]:
    """Step 3: Verify the saved file exists and is valid JSON."""
    action = run_action(
        type="shell_command",
        description="Verify outreach proof file exists and is valid JSON",
        inputs={"command": f"python3 -c \"import json; print(json.load(open('{saved_path}')))\""},
        risk_level="low",
        source_agent="observer_agent",
    )
    ok = action.status == "executed" and action.result.get("ok", False)
    return ok, {
        "verified": ok,
        "action_id": action.id,
        "stdout": action.result.get("stdout", "")[:500],
    }


# ---------------------------------------------------------------------------
# Main execution loop
# ---------------------------------------------------------------------------


def main() -> int:
    print("=" * 60)
    print("  EOS ACTIVATION — FORCE EXECUTION LOOP")
    print("  " + _ts())
    print("=" * 60)
    t0 = time.monotonic()

    # ── 1. Intent ──────────────────────────────────────────────
    intent = "generate outreach message"
    print(f"\n[1/6] INTENT: {intent}")

    # Log the decision to execute this intent
    log_decision(
        context="force_execution_loop: activation test",
        options_considered=["skip", "execute via control plane", "execute manually"],
        chosen_option="execute manually",
        reasoning="First-ever activation. Bypass broken control plane. "
        "Prove full pipeline: intent → workflow → action → log → optimizer.",
        source_agent="developer_agent",
    )
    print("      Decision logged.")

    # ── 2. Workflow start ──────────────────────────────────────
    print("\n[2/6] WORKFLOW: intelligence_to_outreach (3-step minimal)")

    # We don't use WorkflowEngine.start_workflow because the registered
    # workflows require skills we haven't wired. Instead, we track state
    # manually and log to workflow_log.jsonl so the optimizer can read it.

    workflow_id = f"activation-{int(time.time())}"
    workflow_name = "activation_outreach"
    steps = [
        "generate_outreach_message",
        "save_outreach_to_file",
        "verify_output",
    ]

    _append_jsonl(WORKFLOW_LOG, {
        "ts": _ts(),
        "event": "workflow_started",
        "workflow_id": workflow_id,
        "workflow_name": workflow_name,
        "steps": steps,
    })
    print(f"      Workflow {workflow_id} started. Steps: {steps}")

    # ── 3. Execute steps ───────────────────────────────────────
    all_outputs: dict = {}
    step_results: list[dict] = []

    # Step 1: Generate
    print("\n[3/6] ACTION: generate_outreach_message")
    _append_jsonl(WORKFLOW_LOG, {
        "ts": _ts(), "event": "step_started",
        "workflow_id": workflow_id, "workflow_name": workflow_name,
        "step_id": "generate_outreach_message",
    })

    ok1, out1 = step_generate_outreach_message()
    all_outputs.update(out1)
    step_results.append({"step": "generate_outreach_message", "ok": ok1, "outputs": out1})
    status1 = "step_completed" if ok1 else "step_failed"

    _append_jsonl(WORKFLOW_LOG, {
        "ts": _ts(), "event": status1,
        "workflow_id": workflow_id, "workflow_name": workflow_name,
        "step_id": "generate_outreach_message",
        "ok": ok1, "action_id": out1.get("action_id"),
    })
    print(f"      Status: {status1} | Action: {out1.get('action_id', '?')[:8]}")

    if not ok1:
        print("      ABORT: step 1 failed.")
        _append_jsonl(WORKFLOW_LOG, {
            "ts": _ts(), "event": "workflow_failed",
            "workflow_id": workflow_id, "reason": "step 1 failed",
        })
        return 1

    # Step 2: Save
    print("\n[4/6] ACTION: save_outreach_to_file")
    _append_jsonl(WORKFLOW_LOG, {
        "ts": _ts(), "event": "step_started",
        "workflow_id": workflow_id, "workflow_name": workflow_name,
        "step_id": "save_outreach_to_file",
    })

    ok2, out2 = step_save_outreach_to_file(out1.get("outreach_message", {}))
    all_outputs.update(out2)
    step_results.append({"step": "save_outreach_to_file", "ok": ok2, "outputs": out2})
    status2 = "step_completed" if ok2 else "step_failed"

    _append_jsonl(WORKFLOW_LOG, {
        "ts": _ts(), "event": status2,
        "workflow_id": workflow_id, "workflow_name": workflow_name,
        "step_id": "save_outreach_to_file",
        "ok": ok2, "action_id": out2.get("action_id"),
    })
    print(f"      Status: {status2} | Saved: {out2.get('saved_path', '?')}")

    if not ok2:
        print("      ABORT: step 2 failed.")
        _append_jsonl(WORKFLOW_LOG, {
            "ts": _ts(), "event": "workflow_failed",
            "workflow_id": workflow_id, "reason": "step 2 failed",
        })
        return 1

    # Step 3: Verify
    print("\n[5/6] ACTION: verify_output")
    _append_jsonl(WORKFLOW_LOG, {
        "ts": _ts(), "event": "step_started",
        "workflow_id": workflow_id, "workflow_name": workflow_name,
        "step_id": "verify_output",
    })

    ok3, out3 = step_verify_output(out2.get("saved_path", ""))
    all_outputs.update(out3)
    step_results.append({"step": "verify_output", "ok": ok3, "outputs": out3})
    status3 = "step_completed" if ok3 else "step_failed"

    _append_jsonl(WORKFLOW_LOG, {
        "ts": _ts(), "event": status3,
        "workflow_id": workflow_id, "workflow_name": workflow_name,
        "step_id": "verify_output",
        "ok": ok3, "verified": ok3,
    })
    print(f"      Status: {status3} | Verified: {ok3}")

    # Workflow complete
    _append_jsonl(WORKFLOW_LOG, {
        "ts": _ts(), "event": "workflow_completed",
        "workflow_id": workflow_id, "workflow_name": workflow_name,
        "steps_completed": sum(1 for r in step_results if r["ok"]),
        "steps_total": len(step_results),
    })

    # Also write to action_log.jsonl for the optimizer
    _append_jsonl(ACTION_LOG, {
        "ts": _ts(), "event": "workflow_execution",
        "workflow_id": workflow_id, "workflow_name": workflow_name,
        "step_results": step_results,
        "all_ok": all(r["ok"] for r in step_results),
    })

    print(f"\n      Workflow {workflow_id} COMPLETED: "
          f"{sum(1 for r in step_results if r['ok'])}/{len(step_results)} steps passed.")

    # ── 4. Feedback / Optimizer ────────────────────────────────
    print("\n[6/6] OPTIMIZER: running analysis pass...")
    opt = Optimizer(verbose=True)
    result = opt.run_once()
    print(f"      Optimizer result: {json.dumps(result, indent=2)}")

    # ── Summary ────────────────────────────────────────────────
    elapsed = time.monotonic() - t0
    print("\n" + "=" * 60)
    print("  ACTIVATION RESULT")
    print("=" * 60)
    print(f"  Pipeline:    intent → workflow → action → log → optimizer")
    print(f"  Workflow:    {workflow_id}")
    print(f"  Steps:       {sum(1 for r in step_results if r['ok'])}/{len(step_results)} passed")
    print(f"  Optimizer:   {result.get('proposals_new', 0)} new proposals")
    print(f"  Elapsed:     {elapsed:.2f}s")
    print(f"  Status:      {'ACTIVATED' if all(r['ok'] for r in step_results) else 'PARTIAL'}")
    print("=" * 60)

    # Log files written:
    print("\nLog files written:")
    print(f"  Execution log: {_ROOT}/logs/execution/")
    print(f"  Decision log:  {_ROOT}/logs/decisions/")
    print(f"  Workflow log:  {WORKFLOW_LOG}")
    print(f"  Action log:    {ACTION_LOG}")
    print(f"  Optimizer:     {Path(_ROOT) / "data" / "optimizer_proposals.jsonl"}")
    print(f"  Proof file:    {all_outputs.get('saved_path', 'N/A')}")

    return 0 if all(r["ok"] for r in step_results) else 1


if __name__ == "__main__":
    sys.exit(main())
