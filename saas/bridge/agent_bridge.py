#!/usr/bin/env python3
"""
Stdin/stdout JSON bridge between the TypeScript API and the Python AI layer.

Input  (stdin):  {"action": "agent.run"|"agent.team"|"orchestrator.brief", "payload": {...}}
Output (stdout): {"success": bool, "output": ..., "model_used": ..., ...}
                 or {"success": false, "error": "..."} on failure
"""

import sys
import json

# Stdout isolation — must happen before any eos_ai imports
# so diagnostic prints never corrupt the JSON response stream
_stdout = sys.stdout
sys.stdout = sys.stderr

import os as _os
_BRIDGE_ROOT = _os.path.dirname(
    _os.path.dirname(_os.path.dirname(
        _os.path.abspath(__file__))))
sys.path.insert(0, _BRIDGE_ROOT)

from dotenv import load_dotenv
load_dotenv(_os.path.join(_BRIDGE_ROOT, 'services', '.env'))


def _emit(obj: dict) -> None:
    """Write JSON to the real stdout and flush."""
    _stdout.write(json.dumps(obj) + '\n')
    _stdout.flush()


def _run_agent(payload: dict) -> dict:
    from eos_ai.gateway import EOSGateway
    gateway = EOSGateway()
    request = {
        "type":       "agent_task",
        "prompt":     payload.get("prompt", ""),
        "venture_id": payload.get("venture_id"),
        "task_type":  payload.get("task_type"),
        "sub_agent":  payload.get("sub_agent"),
        "session_id": payload.get("session_id"),
        "channel":    payload.get("channel", "saas_ui"),
        "username":   payload.get("username"),
    }
    result = gateway.handle(request)
    return {
        "success":          result.get("status") != "error",
        "output":           result.get("output", ""),
        "model_used":       result.get("model"),
        "skill_used":       result.get("skill"),
        "interaction_id":   result.get("interaction_id"),
        "tokens":           result.get("tokens"),
        "iterations":       result.get("iterations"),
        "was_enhanced":     result.get("was_enhanced", False),
        "session_id":       result.get("session_id"),
        "status":           result.get("status"),
        "approval_required": result.get("status") == "pending",
    }


def _run_team(payload: dict) -> dict:
    from eos_ai.gateway import EOSGateway
    gateway = EOSGateway()
    request = {
        "type":       "agent_task",
        "prompt":     payload.get("prompt", ""),
        "venture_id": payload.get("venture_id"),
        "task_type":  payload.get("task_type"),
        "team":       payload.get("team"),
        "sub_agent":  payload.get("sub_agent"),
        "session_id": payload.get("session_id"),
        "channel":    payload.get("channel", "saas_ui"),
        "username":   payload.get("username"),
    }
    result = gateway.handle(request)
    return {
        "success":          result.get("status") != "error",
        "output":           result.get("output", ""),
        "model_used":       result.get("model"),
        "skill_used":       result.get("skill"),
        "interaction_id":   result.get("interaction_id"),
        "tokens":           result.get("tokens"),
        "iterations":       result.get("iterations"),
        "was_enhanced":     result.get("was_enhanced", False),
        "session_id":       result.get("session_id"),
        "status":           result.get("status"),
        "approval_required": result.get("status") == "pending",
        "team_used":        payload.get("team"),
    }


def _run_brief() -> dict:
    from eos_ai.orchestrator import EOSOrchestrator
    orch       = EOSOrchestrator()
    brief      = orch.morning_brief()
    north_star = orch.get_north_star_status()
    return {
        "success":    True,
        "brief":      brief,
        "north_star": north_star,
    }


def main():
    raw = sys.stdin.read()
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError as e:
        _emit({"success": False, "error": f"Invalid JSON: {e}"})
        return

    action  = msg.get("action", "")
    payload = msg.get("payload", {})

    try:
        if action == "agent.run":
            result = _run_agent(payload)
        elif action == "agent.team":
            result = _run_team(payload)
        elif action == "orchestrator.brief":
            result = _run_brief()
        else:
            result = {"success": False, "error": f"Unknown action: {action}"}
    except Exception as e:
        import traceback
        result = {
            "success":   False,
            "error":     str(e),
            "traceback": traceback.format_exc(),
        }

    _emit(result)


if __name__ == "__main__":
    main()
