"""Cockpit operator loop routes — intent to execution to audit.

The core Stage 1 organism loop:
  1. Operator gives intent (full contract)
  2. Intent classified → work packet created
  3. Risk classified → approval gate enforced
  4. Approved packets → sandbox created → commands executed
  5. Execution state tracked with live logs
  6. Outcomes recorded in reality model + memory candidates
  7. Audit trail preserved

Mounted under /api/umh/ via include_router in cockpit.py.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

operator_loop_router: APIRouter = APIRouter()

_configured: bool = False

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def configure(require_operator_dep: Any) -> None:
    global _configured, operator_loop_router
    _configured = True
    operator_loop_router = _build_router(require_operator_dep)


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route("/operator-loop/submit-intent", _submit_intent, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/approve", _approve_packet, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/reject", _reject_packet, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/execute", _execute_packet, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/complete", _complete_packet, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/status", _loop_status, methods=["GET"])
    r.add_api_route("/operator-loop/packet/{packet_id}", _packet_detail, methods=["GET"])
    r.add_api_route("/operator-loop/pending-approvals", _pending_approvals, methods=["GET"])
    r.add_api_route("/operator-loop/active-packets", _active_packets, methods=["GET"])
    r.add_api_route("/operator-loop/audit-trail", _audit_trail, methods=["GET"])
    r.add_api_route("/operator-loop/record-outcome", _record_outcome, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/health", _loop_health, methods=["GET"])

    return r


def _get_engine():
    from substrate.organism.work_packet_engine import WorkPacketEngine
    return WorkPacketEngine()


def _get_queue():
    from substrate.organism.universal_work_queue import UniversalWorkQueue
    return UniversalWorkQueue()


def _get_classifier():
    from substrate.organism.intent_classifier import IntentClassifier
    return IntentClassifier()


def _get_sandbox_manager():
    from substrate.organism.worktree_sandbox import SandboxManager
    return SandboxManager()


def _audit_log(event_type: str, data: dict[str, Any]) -> None:
    """Append to JSONL audit trail."""
    audit_path = os.path.join(_REPO_ROOT, "data", "umh", "audit", "operator_loop_audit.jsonl")
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)
    entry = {
        "id": str(uuid4()),
        "event_type": event_type,
        "timestamp": time.time(),
        "data": data,
    }
    try:
        with open(audit_path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.debug("audit log write failed: %s", e)


async def _submit_intent(request: Request):
    """Step 1: Operator submits high-level intent with full contract."""
    body = await request.json()
    user_intent = body.get("user_intent", "") or body.get("intent", "")
    if not user_intent:
        return {"success": False, "error": "user_intent is required"}

    desired_end_state = body.get("desired_end_state", "")
    constraints = body.get("constraints", [])
    non_goals = body.get("non_goals", [])
    acceptance_criteria = body.get("acceptance_criteria", [])
    quality_bar = body.get("quality_bar", "")
    allowed_environments = body.get("allowed_environments", [])
    approval_policy = body.get("approval_policy", "")
    risk_tolerance = body.get("risk_tolerance", "")
    proof_required = body.get("proof_required", [])

    queue = _get_queue()
    packet = queue.ingest_user_intent(
        user_intent=user_intent,
        desired_end_state=desired_end_state,
        constraints=constraints,
    )

    if non_goals:
        packet.failure_criteria = non_goals if isinstance(non_goals, list) else [non_goals]
    if acceptance_criteria:
        packet.success_criteria = acceptance_criteria if isinstance(acceptance_criteria, list) else [acceptance_criteria]
    if quality_bar:
        packet.validation_plan = f"Quality bar: {quality_bar}. {packet.validation_plan}"
    if allowed_environments:
        if isinstance(allowed_environments, list):
            packet.constraints = list(set(packet.constraints + [f"env:{e}" for e in allowed_environments]))
    if approval_policy:
        if approval_policy == "auto":
            packet.approval_gates = []
        elif approval_policy == "always":
            packet.approval_gates = ["operator_approval_required"]
    if risk_tolerance:
        if risk_tolerance in ("low", "medium", "high", "critical"):
            packet.risk_class = risk_tolerance
            if risk_tolerance in ("high", "critical"):
                packet.approval_gates = list(set(packet.approval_gates + ["operator_approval_required"]))
    if proof_required:
        proofs = proof_required if isinstance(proof_required, list) else [proof_required]
        existing = packet.validation_plan or ""
        packet.validation_plan = existing + " Proof required: " + ", ".join(proofs)

    queue._save()

    needs_approval = bool(packet.approval_gates)
    risk_class = packet.risk_class

    _audit_log("intent_submitted", {
        "packet_id": packet.packet_id,
        "user_intent": user_intent[:500],
        "risk_class": risk_class,
        "needs_approval": needs_approval,
        "domain": packet.domain,
        "acceptance_criteria": acceptance_criteria[:5] if acceptance_criteria else [],
        "non_goals": non_goals[:5] if non_goals else [],
    })

    return {
        "success": True,
        "packet": packet.to_safe_dict(),
        "needs_approval": needs_approval,
        "risk_class": risk_class,
        "next_action": "approve" if needs_approval else "execute",
    }


async def _approve_packet(request: Request):
    """Step 2a: Operator approves a work packet for execution."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    if not packet_id:
        return {"success": False, "error": "packet_id is required"}

    from substrate.organism.work_packet import PacketLifecycleStatus

    queue = _get_queue()
    pkt = queue.get_packet(packet_id)
    if not pkt:
        return {"success": False, "error": f"Packet {packet_id} not found"}

    current = pkt.status

    transitions_needed = []
    if current == PacketLifecycleStatus.CLASSIFIED:
        transitions_needed = [
            PacketLifecycleStatus.PLANNED,
            PacketLifecycleStatus.READY_FOR_REVIEW,
            PacketLifecycleStatus.APPROVAL_PENDING,
            PacketLifecycleStatus.APPROVED,
        ]
    elif current == PacketLifecycleStatus.PLANNED:
        transitions_needed = [
            PacketLifecycleStatus.READY_FOR_REVIEW,
            PacketLifecycleStatus.APPROVAL_PENDING,
            PacketLifecycleStatus.APPROVED,
        ]
    elif current == PacketLifecycleStatus.READY_FOR_REVIEW:
        transitions_needed = [
            PacketLifecycleStatus.APPROVAL_PENDING,
            PacketLifecycleStatus.APPROVED,
        ]
    elif current == PacketLifecycleStatus.APPROVAL_PENDING:
        transitions_needed = [PacketLifecycleStatus.APPROVED]
    elif current == PacketLifecycleStatus.APPROVED:
        return {"success": True, "packet_id": packet_id, "status": "already_approved"}
    else:
        return {
            "success": False,
            "error": f"Cannot approve from status '{current.value}'",
        }

    for next_status in transitions_needed:
        ok = queue.update_packet_status(packet_id, next_status, f"operator approved (advancing to {next_status.value})")
        if not ok:
            return {"success": False, "error": f"Transition to {next_status.value} failed"}

    _audit_log("packet_approved", {"packet_id": packet_id})

    return {
        "success": True,
        "packet_id": packet_id,
        "status": "approved",
        "next_action": "execute",
    }


async def _reject_packet(request: Request):
    """Step 2b: Operator rejects a work packet."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    reason = body.get("reason", "operator rejected")
    if not packet_id:
        return {"success": False, "error": "packet_id is required"}

    from substrate.organism.work_packet import PacketLifecycleStatus

    queue = _get_queue()
    pkt = queue.get_packet(packet_id)
    if not pkt:
        return {"success": False, "error": f"Packet {packet_id} not found"}

    if pkt.status == PacketLifecycleStatus.APPROVAL_PENDING:
        ok = queue.update_packet_status(packet_id, PacketLifecycleStatus.REJECTED, reason)
    else:
        ok = queue.update_packet_status(packet_id, PacketLifecycleStatus.BLOCKED, reason)

    _audit_log("packet_rejected", {"packet_id": packet_id, "reason": reason})

    return {"success": ok, "packet_id": packet_id, "status": "rejected"}


async def _execute_packet(request: Request):
    """Step 3: Execute an approved work packet — creates sandbox, runs commands, captures output."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    if not packet_id:
        return {"success": False, "error": "packet_id is required"}

    from substrate.organism.work_packet import PacketLifecycleStatus
    from substrate.organism.worktree_sandbox import SandboxStatus, SandboxValidationResult
    from substrate.execution.cpu_gate import gated_subprocess_run

    queue = _get_queue()
    pkt = queue.get_packet(packet_id)
    if not pkt:
        return {"success": False, "error": f"Packet {packet_id} not found"}

    if pkt.approval_gates and pkt.status != PacketLifecycleStatus.APPROVED:
        return {
            "success": False,
            "error": "Packet requires approval before execution",
            "status": pkt.status.value,
            "approval_gates": pkt.approval_gates,
        }

    if pkt.status == PacketLifecycleStatus.APPROVED:
        queue.update_packet_status(packet_id, PacketLifecycleStatus.DELEGATED, "delegated for execution")
    elif pkt.status == PacketLifecycleStatus.CLASSIFIED and not pkt.approval_gates:
        queue.update_packet_status(packet_id, PacketLifecycleStatus.PLANNED, "auto-planned")
        queue.update_packet_status(packet_id, PacketLifecycleStatus.READY_FOR_REVIEW, "auto-reviewed")
        queue.update_packet_status(packet_id, PacketLifecycleStatus.APPROVAL_PENDING, "auto-pending")
        queue.update_packet_status(packet_id, PacketLifecycleStatus.APPROVED, "auto-approved (no gates)")
        queue.update_packet_status(packet_id, PacketLifecycleStatus.DELEGATED, "auto-delegated")
    elif pkt.status == PacketLifecycleStatus.DELEGATED:
        pass
    else:
        return {
            "success": False,
            "error": f"Cannot execute from status '{pkt.status.value}'",
        }

    queue.update_packet_status(packet_id, PacketLifecycleStatus.EXECUTING, "execution started")

    _audit_log("packet_executing", {
        "packet_id": packet_id,
        "risk_class": pkt.risk_class,
        "domain": pkt.domain,
    })

    sandbox_mgr = _get_sandbox_manager()
    execution_log: list[dict[str, Any]] = []
    sandbox_id = ""
    sandbox_path = ""
    changed_files: list[str] = []
    validation_results: list[dict[str, Any]] = []
    all_passed = True

    try:
        slug = pkt.title[:30] or pkt.packet_id[:12]
        sandbox = sandbox_mgr.create_sandbox(
            candidate_id=pkt.packet_id,
            candidate_slug=slug,
            agent_type="operator_loop",
        )
        sandbox_id = sandbox.sandbox_id
        sandbox_path = sandbox.worktree_path

        pkt.linked_sandbox_id = sandbox_id
        queue.link_execution_artifacts(packet_id, {"sandbox_id": sandbox_id})

        sandbox_mgr.update_status(sandbox_id, SandboxStatus("executing"))

        _audit_log("sandbox_created", {
            "packet_id": packet_id,
            "sandbox_id": sandbox_id,
            "worktree_path": sandbox_path,
            "branch_name": sandbox.branch_name,
        })

        execution_log.append({
            "step": "sandbox_created",
            "sandbox_id": sandbox_id,
            "path": sandbox_path,
            "branch": sandbox.branch_name,
            "timestamp": time.time(),
        })

        validation_commands = _derive_validation_commands(pkt)

        for cmd_entry in validation_commands:
            cmd = cmd_entry["command"]
            label = cmd_entry.get("label", cmd[:60])
            t0 = time.time()

            result = gated_subprocess_run(
                cmd,
                shell=True,
                cwd=sandbox_path,
                capture_output=True,
                text=True,
                timeout=120,
                caller="operator_loop_execute",
            )

            duration = round(time.time() - t0, 2)
            passed = result is not None and result.returncode == 0

            step_result = {
                "command": cmd,
                "label": label,
                "exit_code": result.returncode if result else -1,
                "stdout": (result.stdout[:2000] if result else "")[:2000],
                "stderr": (result.stderr[:2000] if result else "cpu gate blocked")[:2000],
                "passed": passed,
                "duration_seconds": duration,
                "timestamp": time.time(),
            }
            execution_log.append(step_result)
            validation_results.append(step_result)

            sandbox_mgr.add_validation_result(sandbox_id, SandboxValidationResult(
                passed=passed,
                command=cmd,
                stdout=(result.stdout[:500] if result else ""),
                stderr=(result.stderr[:500] if result else "blocked"),
                exit_code=result.returncode if result else -1,
                duration_seconds=duration,
            ))

            if not passed:
                all_passed = False

            _audit_log("command_executed", {
                "packet_id": packet_id,
                "sandbox_id": sandbox_id,
                "command": cmd[:200],
                "passed": passed,
                "exit_code": result.returncode if result else -1,
            })

        diff_result = gated_subprocess_run(
            "git diff --name-only HEAD",
            shell=True,
            cwd=sandbox_path,
            capture_output=True,
            text=True,
            timeout=15,
            caller="operator_loop_diff",
        )
        if diff_result and diff_result.returncode == 0:
            changed_files = [f for f in diff_result.stdout.strip().split("\n") if f]

        diff_stat_result = gated_subprocess_run(
            "git diff --stat HEAD",
            shell=True,
            cwd=sandbox_path,
            capture_output=True,
            text=True,
            timeout=15,
            caller="operator_loop_diff_stat",
        )
        diff_summary = diff_stat_result.stdout[:2000] if diff_stat_result and diff_stat_result.returncode == 0 else ""

        new_status = PacketLifecycleStatus.VALIDATING
        queue.update_packet_status(packet_id, new_status, "execution complete, validating")

        pkt = queue.get_packet(packet_id)
        pkt.verification_results = validation_results
        pkt.verification_passed = all_passed
        pkt.linked_sandbox_id = sandbox_id
        queue._save()

        if all_passed:
            sandbox_mgr.update_status(sandbox_id, SandboxStatus.VALIDATED)
        else:
            sandbox_mgr.update_status(sandbox_id, SandboxStatus.VALIDATION_FAILED)

        _record_outcome_internal(
            packet_id=packet_id,
            outcome_text=f"Execution {'passed' if all_passed else 'failed'}. "
                         f"Commands: {len(validation_commands)}, "
                         f"Passed: {sum(1 for v in validation_results if v['passed'])}, "
                         f"Failed: {sum(1 for v in validation_results if not v['passed'])}. "
                         f"Changed files: {len(changed_files)}. "
                         f"Sandbox: {sandbox_id}.",
            domain=pkt.domain or "execution",
            confidence=0.9 if all_passed else 0.6,
        )

        _audit_log("execution_complete", {
            "packet_id": packet_id,
            "sandbox_id": sandbox_id,
            "all_passed": all_passed,
            "commands_run": len(validation_commands),
            "changed_files": changed_files[:20],
        })

        return {
            "success": True,
            "packet_id": packet_id,
            "sandbox_id": sandbox_id,
            "sandbox_path": sandbox_path,
            "branch_name": sandbox.branch_name,
            "status": "validating",
            "all_passed": all_passed,
            "execution_log": execution_log,
            "changed_files": changed_files,
            "diff_summary": diff_summary,
            "validation_results": validation_results,
        }

    except Exception as e:
        error_msg = str(e)
        logger.warning("execute_packet failed for %s: %s", packet_id, error_msg)

        queue.update_packet_status(packet_id, PacketLifecycleStatus.FAILED, f"execution error: {error_msg[:200]}")

        _audit_log("execution_failed", {
            "packet_id": packet_id,
            "sandbox_id": sandbox_id,
            "error": error_msg[:500],
        })

        return {
            "success": False,
            "packet_id": packet_id,
            "sandbox_id": sandbox_id,
            "error": error_msg,
            "execution_log": execution_log,
        }


def _derive_validation_commands(pkt) -> list[dict[str, str]]:
    """Derive validation commands from work packet context."""
    commands: list[dict[str, str]] = []

    commands.append({
        "command": "python3 -c \"import sys; sys.path.insert(0,'/opt/OS'); import substrate; print('substrate import ok')\"",
        "label": "substrate import check",
    })

    if pkt.validation_plan:
        plan_lower = pkt.validation_plan.lower()
        if "test" in plan_lower or "pytest" in plan_lower:
            commands.append({
                "command": "python3 -m pytest tests/ -x -q --tb=short 2>&1 | tail -30",
                "label": "run test suite",
            })
        if "lint" in plan_lower or "ruff" in plan_lower:
            commands.append({
                "command": "python3 -m ruff check . --select E,F --ignore E501 2>&1 | tail -20",
                "label": "ruff lint check",
            })
        if "typecheck" in plan_lower or "mypy" in plan_lower:
            commands.append({
                "command": "python3 -m mypy substrate/ --ignore-missing-imports 2>&1 | tail -20",
                "label": "type check",
            })
        if "build" in plan_lower:
            commands.append({
                "command": "cd cockpit && npx tsc --noEmit 2>&1 | tail -20",
                "label": "TypeScript build",
            })

    if pkt.domain == "infrastructure" or "gate" in (pkt.title or "").lower():
        commands.append({
            "command": "python3 scripts/check_dependency_direction.py --all 2>&1 | tail -10",
            "label": "dependency direction gate",
        })

    if not commands or len(commands) == 1:
        commands.append({
            "command": "python3 -m pytest tests/ -x -q --tb=short 2>&1 | tail -30",
            "label": "default test suite",
        })
        commands.append({
            "command": "python3 scripts/check_dependency_direction.py --all 2>&1 | tail -10",
            "label": "dependency direction gate",
        })

    return commands


async def _complete_packet(request: Request):
    """Step 4: Mark an executing/validating packet as completed with outcome."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    outcome = body.get("outcome", "")
    success = body.get("success", True)
    if not packet_id:
        return {"success": False, "error": "packet_id is required"}

    from substrate.organism.work_packet import PacketLifecycleStatus

    queue = _get_queue()
    pkt = queue.get_packet(packet_id)
    if not pkt:
        return {"success": False, "error": f"Packet {packet_id} not found"}

    if success:
        if pkt.status != PacketLifecycleStatus.VALIDATING:
            queue.update_packet_status(packet_id, PacketLifecycleStatus.VALIDATING, "validating outcome")
        ok = queue.update_packet_status(packet_id, PacketLifecycleStatus.COMPLETED, outcome or "completed")
    else:
        ok = queue.update_packet_status(packet_id, PacketLifecycleStatus.FAILED, outcome or "failed")

    pkt = queue.get_packet(packet_id)
    pkt.outcome_summary = outcome[:500] if outcome else ""
    queue._save()

    _record_outcome_internal(
        packet_id=packet_id,
        outcome_text=f"Packet {packet_id} {'completed' if success else 'failed'}: {outcome[:300]}",
        domain=pkt.domain or "execution",
        confidence=0.85 if success else 0.5,
    )

    _audit_log("packet_completed", {
        "packet_id": packet_id,
        "success": success,
        "outcome": outcome[:500] if outcome else "",
    })

    return {"success": ok, "packet_id": packet_id, "status": "completed" if success else "failed"}


async def _loop_status():
    """Current operator loop status — packets, approvals, execution."""
    queue = _get_queue()
    summary = queue.compute_queue_summary()

    pending_approval = queue.get_packets_requiring_approval()
    blocked = queue.get_blocked_packets()
    human_required = queue.get_packets_requiring_human()

    next_best = queue.get_next_best_packet()

    return {
        "queue_summary": summary,
        "pending_approval_count": len(pending_approval),
        "blocked_count": len(blocked),
        "human_required_count": len(human_required),
        "next_best": next_best.to_safe_dict() if next_best else None,
    }


async def _packet_detail(packet_id: str):
    """Full work packet detail with audit trail."""
    queue = _get_queue()
    pkt = queue.get_packet(packet_id)
    if not pkt:
        return {"error": "Not found", "packet_id": packet_id}

    audit_entries = _get_audit_entries_for_packet(packet_id)

    result = pkt.to_dict()
    result["audit_trail"] = audit_entries

    if pkt.linked_sandbox_id:
        try:
            sandbox_mgr = _get_sandbox_manager()
            sb = sandbox_mgr.get_sandbox(pkt.linked_sandbox_id)
            if sb:
                result["sandbox"] = sb.to_dict()
        except Exception:
            pass

    return result


async def _pending_approvals():
    """List all packets needing operator approval."""
    queue = _get_queue()
    pending = queue.get_packets_requiring_approval()
    return [p.to_safe_dict() for p in pending]


async def _active_packets():
    """List all packets currently executing or recently completed."""
    queue = _get_queue()
    all_packets = queue.all_packets()
    active = [p for p in all_packets if p.status.value in (
        "executing", "delegated", "reconverging", "validating",
    )]
    return [p.to_safe_dict() for p in active]


async def _audit_trail(packet_id: str | None = None, limit: int = 50):
    """Read audit trail, optionally filtered by packet."""
    if packet_id:
        return _get_audit_entries_for_packet(packet_id)

    audit_path = os.path.join(_REPO_ROOT, "data", "umh", "audit", "operator_loop_audit.jsonl")
    if not os.path.exists(audit_path):
        return []

    entries = []
    try:
        with open(audit_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass

    entries.reverse()
    return entries[:limit]


async def _record_outcome(request: Request):
    """Record an execution outcome in the reality model."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    outcome_text = body.get("outcome", "")
    domain = body.get("domain", "execution")
    confidence = body.get("confidence", 0.7)

    if not outcome_text:
        return {"success": False, "error": "outcome is required"}

    obs_id = _record_outcome_internal(
        packet_id=packet_id,
        outcome_text=outcome_text,
        domain=domain,
        confidence=confidence,
    )

    if obs_id:
        return {"success": True, "observation_id": obs_id}
    return {"success": False, "error": "outcome recording failed"}


def _record_outcome_internal(
    packet_id: str,
    outcome_text: str,
    domain: str = "execution",
    confidence: float = 0.7,
) -> str | None:
    """Internal outcome recorder — writes to reality model and audit trail."""
    try:
        from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation
        org_id = os.environ.get("UMH_ORG_ID", os.environ.get("EOS_ORG_ID", "default"))
        user_id = os.environ.get("UMH_USER_ID", os.environ.get("EOS_USER_ID", "default"))
        instance = InstanceRealityModel(user_id=user_id, org_id=org_id)
        obs = InstanceObservation(
            content=outcome_text[:2000],
            domain=domain,
            confidence=confidence,
            tags=["execution_outcome", "operator_loop"],
            metadata={"packet_id": packet_id} if packet_id else {},
        )
        obs_id = instance.record(obs)

        if packet_id:
            try:
                queue = _get_queue()
                pkt = queue.get_packet(packet_id)
                if pkt:
                    pkt.outcome_observation_id = str(obs_id)
                    pkt.outcome_ids = list(set(pkt.outcome_ids + [str(obs_id)]))
                    queue._save()
            except Exception:
                pass

        _audit_log("outcome_recorded", {
            "packet_id": packet_id,
            "observation_id": str(obs_id),
            "domain": domain,
        })

        return str(obs_id)
    except Exception as e:
        logger.debug("record_outcome failed: %s", e)
        return None


async def _loop_health():
    """Health endpoint — queue summary, latest audit event, trace/memory status."""
    queue = _get_queue()
    summary = queue.compute_queue_summary()

    audit_path = os.path.join(_REPO_ROOT, "data", "umh", "audit", "operator_loop_audit.jsonl")
    latest_audit = None
    if os.path.exists(audit_path):
        try:
            with open(audit_path) as f:
                lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                if last_line:
                    latest_audit = json.loads(last_line)
        except Exception:
            pass

    sandbox_summary = {}
    try:
        sandbox_mgr = _get_sandbox_manager()
        sandbox_summary = sandbox_mgr.to_dict()
    except Exception:
        sandbox_summary = {"error": "sandbox manager unavailable"}

    reality_model_status = "unknown"
    try:
        from substrate.reality_model.instance import InstanceRealityModel
        org_id = os.environ.get("UMH_ORG_ID", os.environ.get("EOS_ORG_ID", "default"))
        user_id = os.environ.get("UMH_USER_ID", os.environ.get("EOS_USER_ID", "default"))
        instance = InstanceRealityModel(user_id=user_id, org_id=org_id)
        count = len(instance.all_observations())
        reality_model_status = f"operational ({count} observations)"
    except Exception as e:
        reality_model_status = f"error: {e}"

    return {
        "healthy": True,
        "timestamp": time.time(),
        "queue_summary": summary,
        "latest_audit_event": latest_audit,
        "sandbox_summary": {
            "total": sandbox_summary.get("total_sandboxes", 0),
            "active": sandbox_summary.get("active_sandboxes", 0),
        },
        "reality_model": reality_model_status,
    }


def _get_audit_entries_for_packet(packet_id: str) -> list[dict]:
    """Read audit entries for a specific packet."""
    audit_path = os.path.join(_REPO_ROOT, "data", "umh", "audit", "operator_loop_audit.jsonl")
    if not os.path.exists(audit_path):
        return []

    entries = []
    try:
        with open(audit_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("data", {}).get("packet_id") == packet_id:
                        entries.append(entry)
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass

    return entries
