#!/usr/bin/env python3
"""
Organism runtime bridge — exposes organism subsystem state and actions
to the TypeScript cockpit API via stdin/stdout JSON protocol.

Actions:
  organism.snapshot       — full organism snapshot (ObservabilitySnapshot)
  organism.status         — daemon status
  organism.health         — homeostasis health check
  organism.objectives     — list all objectives
  organism.objective      — get single objective by id
  organism.agents         — list organism agents with status
  organism.deliverables   — list deliverables (optional agent_id filter)
  organism.learning       — list learning signals
  organism.economy        — execution economy summary
  organism.economy.records — recent execution records
  organism.runtimes       — runtime graph topology
  organism.supervisor     — supervisor health state
  organism.governor       — recursion governor state + limits
  organism.governor.escalations — escalation log
  organism.advisors       — advisor hierarchy tree
  organism.approvals      — list approvals (optional status filter)
  organism.approvals.count — pending approval count
  organism.handoffs       — handoff stats
  organism.leverage       — leverage assimilation artifacts
  organism.workcells      — workcell daemon state

  organism.approve        — approve a pending approval
  organism.deny           — deny a pending approval
  organism.kill           — activate recursion kill switch
  organism.resume         — deactivate recursion kill switch
  organism.governor.reset — reset governor counters
  organism.refresh        — refresh runtime availability

  organism.sessions       — list tmux sessions
  organism.docker         — list Docker containers
  organism.mesh           — list Tailscale mesh nodes

  organism.converse            — route cockpit conversation through SignalEnvelope → SubstrateGateway
  organism.send_channel_message — send message to external channel (Discord, etc.) via channel_port

  organism.dev_sessions        — list active/completed development sessions (all harnesses)
  organism.dev_session_detail  — full detail for a specific session (events, decisions, coherence)

UMH substrate bridge — no instance context.
"""

import sys
import json

_stdout = sys.stdout
sys.stdout = sys.stderr

import os as _os

_BRIDGE_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
sys.path.insert(0, _BRIDGE_ROOT)

from dotenv import load_dotenv

load_dotenv(_os.path.join(_BRIDGE_ROOT, "services", ".env"))

import logging

logger = logging.getLogger(__name__)


def _emit(obj: dict) -> None:
    _stdout.write(json.dumps(obj, default=str) + "\n")
    _stdout.flush()


def _get_daemon():
    from substrate.organism.daemon import OrganismDaemon

    return OrganismDaemon()


def _get_economy():
    from substrate.organism.execution_economy import ExecutionEconomy

    return ExecutionEconomy()


def _get_governor():
    from substrate.organism.recursion_governance import RecursionGovernor

    return RecursionGovernor()


def _get_advisors():
    from substrate.organism.advisor_hierarchy import AdvisorHierarchy

    return AdvisorHierarchy()


def _get_approval_store():
    from substrate.organism.approval_store import ApprovalStore

    return ApprovalStore()


def _get_homeostasis():
    from substrate.organism.homeostasis import HomeostasisEngine

    return HomeostasisEngine()


def _get_observer(daemon=None):
    from substrate.organism.observability import OrganismObserver

    d = daemon or _get_daemon()
    return OrganismObserver(
        coordinator=getattr(d, "_coordinator", None) or getattr(d, "coordinator", None),
        graph=getattr(d, "_graph", None) or getattr(d, "graph", None),
        supervisor=getattr(d, "_supervisor", None) or getattr(d, "supervisor", None),
        daemon=getattr(d, "_workcell_daemon", None),
        homeostasis=getattr(d, "_homeostasis", None) or getattr(d, "homeostasis", None),
    )


def _get_store():
    from substrate.organism.store import OrganismStore

    return OrganismStore()


def _get_leverage():
    from substrate.organism.leverage_assimilation import LeverageAssimilator

    return LeverageAssimilator()


def _get_handoff_router():
    from substrate.organism.handoff import HandoffRouter

    return HandoffRouter()


# ── Read-only queries ──────────────────────────────────────


def _snapshot(_payload: dict) -> dict:
    daemon = _get_daemon()
    observer = _get_observer(daemon)
    snap = observer.snapshot()
    return {"success": True, "data": snap.to_dict()}


def _status(_payload: dict) -> dict:
    daemon = _get_daemon()
    return {"success": True, "data": daemon.status()}


def _health(_payload: dict) -> dict:
    engine = _get_homeostasis()
    report = engine.check()
    data = {
        "mode": report.mode.value if hasattr(report.mode, "value") else str(report.mode),
        "unhealthy": report.unhealthy,
        "actions_taken": report.actions_taken,
        "dimensions": [
            {
                "dimension": d.dimension,
                "value": d.value,
                "threshold": d.threshold,
                "healthy": d.healthy,
                "detail": d.detail,
            }
            for d in report.dimensions
        ],
    }
    return {"success": True, "data": data}


def _objectives(_payload: dict) -> dict:
    daemon = _get_daemon()
    coord = getattr(daemon, "_coordinator", None) or getattr(daemon, "coordinator", None)
    if coord:
        return {"success": True, "data": coord.list_objectives()}
    return {"success": True, "data": []}


def _objective(payload: dict) -> dict:
    obj_id = payload.get("objective_id", "")
    daemon = _get_daemon()
    coord = getattr(daemon, "_coordinator", None) or getattr(daemon, "coordinator", None)
    if coord:
        obj = coord.get_objective(obj_id)
        if obj:
            return {"success": True, "data": obj}
    return {"success": False, "error": f"Objective {obj_id} not found"}


def _agents(_payload: dict) -> dict:
    daemon = _get_daemon()
    advisor = getattr(daemon, "_advisor", None) or getattr(daemon, "advisor", None)
    if advisor:
        return {"success": True, "data": advisor.list_agents()}
    agents = daemon.status().get("agents", [])
    return {"success": True, "data": agents}


def _deliverables(payload: dict) -> dict:
    store = _get_store()
    agent_id = payload.get("agent_id")
    limit = payload.get("limit", 50)
    items = store.list_deliverables(agent_id=agent_id, limit=limit)
    return {"success": True, "data": items}


def _learning(_payload: dict) -> dict:
    store = _get_store()
    limit = _payload.get("limit", 50)
    items = store.list_learning_signals(limit=limit)
    return {"success": True, "data": items}


def _economy(_payload: dict) -> dict:
    eco = _get_economy()
    return {"success": True, "data": eco.economy_summary()}


def _economy_records(payload: dict) -> dict:
    eco = _get_economy()
    limit = payload.get("limit", 20)
    records = eco.recent_records(limit=limit)
    return {"success": True, "data": [r.to_dict() if hasattr(r, "to_dict") else r for r in records]}


def _runtimes(_payload: dict) -> dict:
    daemon = _get_daemon()
    graph = getattr(daemon, "_graph", None) or getattr(daemon, "graph", None)
    if graph:
        return {"success": True, "data": graph.to_dict()}
    return {"success": True, "data": {"nodes": [], "node_count": 0}}


def _supervisor(_payload: dict) -> dict:
    daemon = _get_daemon()
    sup = getattr(daemon, "_supervisor", None) or getattr(daemon, "supervisor", None)
    if sup:
        return {"success": True, "data": sup.to_dict()}
    return {"success": True, "data": {"supervised_count": 0}}


def _governor(_payload: dict) -> dict:
    gov = _get_governor()
    return {"success": True, "data": gov.to_dict()}


def _governor_escalations(payload: dict) -> dict:
    gov = _get_governor()
    limit = payload.get("limit", 20)
    log = gov.escalation_log(limit=limit)
    return {"success": True, "data": [e.to_dict() if hasattr(e, "to_dict") else e for e in log]}


def _advisors(_payload: dict) -> dict:
    hierarchy = _get_advisors()
    return {"success": True, "data": hierarchy.to_dict()}


def _advisors_tree(_payload: dict) -> dict:
    hierarchy = _get_advisors()
    return {"success": True, "data": hierarchy.hierarchy_tree()}


def _approvals(payload: dict) -> dict:
    store = _get_approval_store()
    status = payload.get("status")
    limit = payload.get("limit", 50)
    items = store.list_approvals(status=status, limit=limit)
    return {"success": True, "data": items}


def _approvals_count(_payload: dict) -> dict:
    store = _get_approval_store()
    return {"success": True, "data": {"pending": store.pending_count()}}


def _handoffs(_payload: dict) -> dict:
    router = _get_handoff_router()
    return {"success": True, "data": router.stats()}


def _leverage(_payload: dict) -> dict:
    assim = _get_leverage()
    return {"success": True, "data": assim.to_dict()}


def _workcells(_payload: dict) -> dict:
    daemon = _get_daemon()
    wc_daemon = getattr(daemon, "_workcell_daemon", None)
    if wc_daemon:
        return {"success": True, "data": wc_daemon.to_dict()}
    return {"success": True, "data": {"status": "not_initialized", "workcell_count": 0}}


# ── Governed actions ──────────────────────────────────────


def _approve(payload: dict) -> dict:
    store = _get_approval_store()
    approval_id = payload.get("approval_id", "")
    decided_by = payload.get("decided_by", "cockpit")
    store.decide(approval_id, "approved", decided_by=decided_by)
    return {"success": True, "data": {"approval_id": approval_id, "decision": "approved"}}


def _deny(payload: dict) -> dict:
    store = _get_approval_store()
    approval_id = payload.get("approval_id", "")
    decided_by = payload.get("decided_by", "cockpit")
    store.decide(approval_id, "denied", decided_by=decided_by)
    return {"success": True, "data": {"approval_id": approval_id, "decision": "denied"}}


def _kill(_payload: dict) -> dict:
    gov = _get_governor()
    gov.kill()
    return {
        "success": True,
        "data": {"kill_switch": True, "message": "Autonomous execution halted"},
    }


def _resume_governor(_payload: dict) -> dict:
    gov = _get_governor()
    gov.resume()
    return {
        "success": True,
        "data": {"kill_switch": False, "message": "Autonomous execution resumed"},
    }


def _governor_reset(_payload: dict) -> dict:
    gov = _get_governor()
    gov.reset_state()
    return {"success": True, "data": {"message": "Governor counters reset"}}


def _refresh_runtimes(_payload: dict) -> dict:
    daemon = _get_daemon()
    graph = getattr(daemon, "_graph", None) or getattr(daemon, "graph", None)
    if graph:
        availability = graph.refresh_availability()
        return {"success": True, "data": availability}
    return {"success": True, "data": {}}


# ── System visibility ──────────────────────────────────────


def _tmux_sessions(_payload: dict) -> dict:
    import subprocess

    try:
        result = subprocess.run(
            [
                "tmux",
                "list-sessions",
                "-F",
                "#{session_name}|#{session_windows}|#{session_created}|#{session_attached}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        sessions = []
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|")
                sessions.append(
                    {
                        "name": parts[0] if len(parts) > 0 else "",
                        "windows": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
                        "created": parts[2] if len(parts) > 2 else "",
                        "attached": parts[3] == "1" if len(parts) > 3 else False,
                    }
                )
        return {"success": True, "data": sessions}
    except Exception as e:
        return {"success": True, "data": [], "warning": str(e)}


def _docker_containers(_payload: dict) -> dict:
    import subprocess

    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--format",
                "{{.Names}}|{{.Status}}|{{.Image}}|{{.Ports}}|{{.State}}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        containers = []
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|")
                containers.append(
                    {
                        "name": parts[0] if len(parts) > 0 else "",
                        "status": parts[1] if len(parts) > 1 else "",
                        "image": parts[2] if len(parts) > 2 else "",
                        "ports": parts[3] if len(parts) > 3 else "",
                        "state": parts[4] if len(parts) > 4 else "",
                    }
                )
        return {"success": True, "data": containers}
    except Exception as e:
        return {"success": True, "data": [], "warning": str(e)}


def _mesh_nodes(_payload: dict) -> dict:
    import subprocess

    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            peers = data.get("Peer", {})
            nodes = []
            self_node = data.get("Self", {})
            if self_node:
                nodes.append(
                    {
                        "hostname": self_node.get("HostName", ""),
                        "ip": self_node.get("TailscaleIPs", [""])[0]
                        if self_node.get("TailscaleIPs")
                        else "",
                        "os": self_node.get("OS", ""),
                        "online": True,
                        "self": True,
                    }
                )
            for _key, peer in peers.items():
                nodes.append(
                    {
                        "hostname": peer.get("HostName", ""),
                        "ip": peer.get("TailscaleIPs", [""])[0] if peer.get("TailscaleIPs") else "",
                        "os": peer.get("OS", ""),
                        "online": peer.get("Online", False),
                        "self": False,
                    }
                )
            return {"success": True, "data": nodes}
        return {"success": True, "data": []}
    except Exception as e:
        return {"success": True, "data": [], "warning": str(e)}


# ── Meta-IDE: workspace and filesystem ──────────────────────


def _world_model(_payload: dict) -> dict:
    from substrate.organism.world_model import extract_world_model

    model = extract_world_model()
    return {"success": True, "data": model.to_safe_dict()}


def _dependency_graph(_payload: dict) -> dict:
    from substrate.organism.dependency_graph import build_dependency_graph

    graph = build_dependency_graph()
    return {"success": True, "data": graph.to_safe_dict()}


def _contradictions(_payload: dict) -> dict:
    from substrate.organism.contradiction_engine import detect_contradictions

    report = detect_contradictions()
    return {"success": True, "data": report.to_safe_dict()}


def _memory_promotion(_payload: dict) -> dict:
    from substrate.organism.memory_promotion import MemoryPromotionPipeline

    pipeline = MemoryPromotionPipeline()
    return {"success": True, "data": pipeline.to_dict()}


def _memory_promotion_approve(payload: dict) -> dict:
    from substrate.organism.memory_promotion import MemoryPromotionPipeline

    pipeline = MemoryPromotionPipeline()
    cid = payload.get("id", "")
    if not cid:
        return {"success": False, "error": "id required"}
    entry = pipeline.promote(cid, decided_by="cockpit")
    if entry:
        return {"success": True, "data": entry.to_dict()}
    return {"success": False, "error": "Promotion failed or not eligible"}


def _memory_promotion_reject(payload: dict) -> dict:
    from substrate.organism.memory_promotion import MemoryPromotionPipeline

    pipeline = MemoryPromotionPipeline()
    cid = payload.get("id", "")
    reason = payload.get("reason", "Operator rejected")
    if not cid:
        return {"success": False, "error": "id required"}
    result = pipeline.reject(cid, reason=reason, decided_by="cockpit")
    return {"success": result, "data": {"id": cid, "decision": "rejected"}}


def _learning_loop(_payload: dict) -> dict:
    from substrate.organism.outcome_learning import OutcomeLearningLoop

    loop = OutcomeLearningLoop()
    return {"success": True, "data": loop.to_safe_dict()}


def _outcome_capture(payload: dict) -> dict:
    from substrate.organism.outcome_learning import (
        OutcomeLearningLoop,
        OutcomeRecord,
        OutcomeStatus,
    )

    action_type = payload.get("action_type", "")
    status_str = payload.get("status", "success")
    description = payload.get("description", "")
    plan_id = payload.get("plan_id", "")
    step_id = payload.get("step_id", "")
    actual_result = payload.get("actual_result", "")
    duration = float(payload.get("duration_seconds", 0))
    error = payload.get("error", "")
    if not action_type:
        return {"success": False, "error": "action_type required"}
    status_map = {s.value: s for s in OutcomeStatus}
    status = status_map.get(status_str, OutcomeStatus.SUCCESS)
    record = OutcomeRecord(
        action_type=action_type,
        plan_id=plan_id,
        step_id=step_id,
        description=description,
        status=status,
        actual_result=actual_result,
        duration_seconds=duration,
        error=error,
    )
    loop = OutcomeLearningLoop()
    evaluation = loop.record_outcome(record)
    return {"success": True, "data": {"outcome_id": record.id, "evaluation": evaluation.to_dict()}}


def _compose(payload: dict) -> dict:
    from substrate.organism.composition_engine import compose_plan

    intent = payload.get("intent", "")
    if not intent:
        return {"success": False, "error": "intent required"}
    plan = compose_plan(intent)
    return {"success": True, "data": plan.to_dict()}


def _execute_plan(payload: dict) -> dict:
    from substrate.organism.composition_engine import compose_plan
    from substrate.organism.plan_execution_adapter import PlanExecutionAdapter
    from substrate.organism.governed_spine import GovernedExecutionSpine
    from substrate.organism.execution_modes import ExecutionModeManager
    from substrate.organism.mutation_registry import MutationRegistry
    from substrate.organism.execution_journal import ExecutionJournal
    from substrate.organism.event_spine import EventSpine
    from substrate.organism.outcome_learning import OutcomeLearningLoop
    from substrate.organism.memory_promotion import MemoryPromotionPipeline
    from substrate.organism.spine_guard import SpineGuard
    from substrate.organism.coherence_propagation import ParallelPropagationEngine

    intent = payload.get("intent", "")
    if not intent:
        return {"success": False, "error": "intent required"}

    composition_plan = compose_plan(intent)

    event_spine = EventSpine()
    journal = ExecutionJournal()
    propagation_engine = ParallelPropagationEngine()
    spine = GovernedExecutionSpine(
        event_spine=event_spine,
        execution_mode=ExecutionModeManager(),
        mutation_registry=MutationRegistry(),
        journal=journal,
        propagation_engine=propagation_engine,
    )
    outcome_loop = OutcomeLearningLoop()
    memory_pipeline = MemoryPromotionPipeline()

    adapter = PlanExecutionAdapter(
        governed_spine=spine,
        spine_guard=SpineGuard(event_spine=event_spine, journal=journal),
        outcome_loop=outcome_loop,
        memory_pipeline=memory_pipeline,
    )

    executable = adapter.convert_plan(composition_plan)
    result = adapter.execute_plan(executable)
    return {"success": True, "data": result.to_dict()}


def _execution_graph(_payload: dict) -> dict:
    from substrate.organism.plan_execution_adapter import PlanExecutionAdapter

    adapter = PlanExecutionAdapter()
    return {"success": True, "data": adapter.to_dict()}


def _execution_graph_detail(payload: dict) -> dict:
    plan_id = payload.get("plan_id", "")
    if not plan_id:
        return {"success": False, "error": "plan_id required"}
    from substrate.organism.plan_execution_adapter import PlanExecutionAdapter

    adapter = PlanExecutionAdapter()
    plan = adapter.get_execution_graph(plan_id)
    if plan is None:
        return {"success": False, "error": f"plan {plan_id} not found"}
    return {"success": True, "data": plan.to_dict()}


def _execute_plan_approve_step(payload: dict) -> dict:
    plan_id = payload.get("plan_id", "")
    step_id = payload.get("step_id", "")
    if not plan_id or not step_id:
        return {"success": False, "error": "plan_id and step_id required"}
    return {
        "success": False,
        "error": "step approval not yet implemented — use cockpit spine router",
    }


def _execute_plan_pending(payload: dict) -> dict:
    plan_id = payload.get("plan_id", "")
    if not plan_id:
        return {"success": False, "error": "plan_id required"}
    return {"success": True, "data": []}


def _trial_status(_payload: dict) -> dict:
    """Return the latest self-improvement trial results."""
    import glob

    umh_root = _os.environ.get("UMH_ROOT", "/opt/OS")
    trials_dir = _os.path.join(umh_root, "data", "umh", "trials")

    result: dict = {"has_trial": False}

    results_path = _os.path.join(trials_dir, "phase9_2_trial_results.json")
    if _os.path.isfile(results_path):
        with open(results_path) as f:
            result["trial_results"] = json.loads(f.read())
        result["has_trial"] = True

    plan_path = _os.path.join(trials_dir, "phase9_2_composition_plan.json")
    if _os.path.isfile(plan_path):
        with open(plan_path) as f:
            result["composition_plan"] = json.loads(f.read())

    graph_path = _os.path.join(trials_dir, "phase9_2_execution_graph.json")
    if _os.path.isfile(graph_path):
        with open(graph_path) as f:
            result["execution_graph"] = json.loads(f.read())

    outcomes_path = _os.path.join(trials_dir, "trial_outcomes.jsonl")
    if _os.path.isfile(outcomes_path):
        outcomes = []
        with open(outcomes_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    outcomes.append(json.loads(line))
        result["outcomes"] = outcomes

    memory_candidates_path = _os.path.join(trials_dir, "memory", "memory_candidates", "candidates.jsonl")
    if _os.path.isfile(memory_candidates_path):
        candidates = []
        with open(memory_candidates_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    candidates.append(json.loads(line))
        result["memory_candidates"] = candidates

    journal_path = _os.path.join(trials_dir, "trial_journal.jsonl")
    if _os.path.isfile(journal_path):
        journal_entries = []
        with open(journal_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    journal_entries.append(json.loads(line))
        result["journal_entries"] = journal_entries[-50:]

    campaign_path = _os.path.join(trials_dir, "phase9_3_campaign_results.json")
    if _os.path.isfile(campaign_path):
        with open(campaign_path) as f:
            campaign_data = json.loads(f.read())
        result["has_campaign"] = True
        result["campaign_summary"] = campaign_data.get("summary", {})
        result["campaign_baseline"] = campaign_data.get("baseline", {})
        result["campaign_after"] = campaign_data.get("after", {})
        result["campaign_trials"] = campaign_data.get("trials", [])
    else:
        result["has_campaign"] = False

    queue_path = _os.path.join(trials_dir, "phase9_3_candidate_queue.json")
    if _os.path.isfile(queue_path):
        with open(queue_path) as f:
            result["candidate_queue"] = json.loads(f.read())

    return {"success": True, "data": result}


def _list_workspaces(_payload: dict) -> dict:
    import subprocess

    workspaces = []
    umh_root = _os.environ.get("UMH_ROOT", "/opt/OS")
    worktree_dir = _os.path.join(umh_root, ".claude", "worktrees")
    if _os.path.isdir(worktree_dir):
        for name in sorted(_os.listdir(worktree_dir)):
            full = _os.path.join(worktree_dir, name)
            if _os.path.isdir(full):
                workspaces.append(
                    {
                        "name": name,
                        "path": full,
                        "type": "worktree",
                    }
                )
    workspaces.insert(0, {"name": "main", "path": umh_root, "type": "main"})
    return {"success": True, "data": workspaces}


def _list_files(payload: dict) -> dict:
    path = payload.get("path", "")
    if not path:
        return {"success": False, "error": "path required"}
    safe_roots = [
        _os.environ.get("UMH_ROOT", "/opt/OS"),
    ]
    allowed = any(path.startswith(root) for root in safe_roots)
    if not allowed:
        return {"success": False, "error": "path outside safe roots"}
    if not _os.path.isdir(path):
        return {"success": False, "error": "not a directory"}
    entries = []
    try:
        for name in sorted(_os.listdir(path)):
            full = _os.path.join(path, name)
            if name.startswith(".") and name not in (".claude", ".env.example"):
                continue
            if name in (
                "__pycache__",
                "node_modules",
                ".git",
                ".mypy_cache",
                ".ruff_cache",
                ".pytest_cache",
            ):
                continue
            is_dir = _os.path.isdir(full)
            entries.append(
                {
                    "name": name,
                    "path": full,
                    "type": "directory" if is_dir else "file",
                    "size": _os.path.getsize(full) if not is_dir else None,
                }
            )
    except PermissionError:
        return {"success": False, "error": "permission denied"}
    return {"success": True, "data": entries}


def _read_file(payload: dict) -> dict:
    path = payload.get("path", "")
    if not path:
        return {"success": False, "error": "path required"}
    safe_roots = [_os.environ.get("UMH_ROOT", "/opt/OS")]
    allowed = any(path.startswith(root) for root in safe_roots)
    if not allowed:
        return {"success": False, "error": "path outside safe roots"}
    if not _os.path.isfile(path):
        return {"success": False, "error": "not a file"}
    size = _os.path.getsize(path)
    if size > 512_000:
        return {"success": False, "error": f"file too large ({size} bytes, max 512KB)"}
    try:
        with open(path, "r", errors="replace") as f:
            content = f.read()
        return {"success": True, "data": {"path": path, "content": content, "size": size}}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Report Dispatcher ─────────────────────────────────────

def _dispatch_report(payload: dict) -> dict:
    """Send a report to Discord + cockpit chat."""
    title = payload.get("title", "")
    summary = payload.get("summary", "")
    body = payload.get("body", "")
    file_path = payload.get("file_path")
    metadata = payload.get("metadata", {})

    if not title or not summary:
        return {"success": False, "error": "title and summary required"}

    try:
        from substrate.organism.report_dispatcher import ReportDispatcher, Report
        dispatcher = ReportDispatcher()
        report = Report(
            title=title,
            summary=summary,
            body=body,
            file_path=file_path,
            metadata=metadata,
        )
        result = dispatcher.dispatch_report(report)
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _list_reports(payload: dict) -> dict:
    """List recent reports from organism store."""
    limit = int(payload.get("limit", 20))
    try:
        from substrate.organism.report_dispatcher import ReportDispatcher
        dispatcher = ReportDispatcher()
        reports = dispatcher.list_reports(limit=limit)
        return {"success": True, "data": reports}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _converse(payload: dict) -> dict:
    """Route cockpit conversation through SignalEnvelope → SubstrateGateway.

    Same canonical path as Discord: builds SignalEnvelope, enters through
    SubstrateGateway.handle(), returns ExecutionResult as response dict.
    """
    content = (payload.get("content") or "").strip()
    if not content:
        return {"success": False, "error": "content is required"}

    try:
        from substrate.control_plane.runtime.substrate_gateway import SubstrateGateway
        from substrate.types import SignalEnvelope, SignalSource

        signal = SignalEnvelope(
            source=SignalSource.USER,
            content=content,
            user_id=payload.get("username", "operator"),
            organization_id=_os.environ.get("UMH_ORG_ID")
            or _os.environ.get("EOS_ORG_ID", ""),
            venture_id=payload.get("venture_id")
            or _os.environ.get("UMH_PORTFOLIO_ID")
            or _os.environ.get("EOS_PORTFOLIO_ID"),
            metadata={
                "channel": "cockpit",
                "username": payload.get("username", "operator"),
                "session_id": payload.get("session_id"),
                "request_type": "agent_task",
                "task_type": payload.get("task_type", "GENERATE"),
                "projection_id": payload.get("projection_id", "eos"),
            },
        )

        gw = SubstrateGateway()
        result = gw.handle(signal)

        response_text = result.output or "No response"

        try:
            from substrate.organism.store import OrganismStore
            store = OrganismStore()
            ai_name = _os.environ.get("AI_NAME", "system")
            store.save_conversation_turn(
                content=content,
                response=response_text,
                origin_channel="cockpit",
                projection_id=payload.get("projection_id", "eos"),
                responder=ai_name,
            )
        except Exception as persist_err:
            logger.warning("conversation persist failed (non-fatal): %s", persist_err)

        return {
            "success": True,
            "data": {
                "message_id": str(signal.id),
                "response": response_text,
                "timestamp": result.completed_at.isoformat(),
                "outcome": result.outcome.value if result.outcome else "unknown",
                "provider": result.provider or "",
            },
        }
    except Exception as e:
        logger.exception("converse failed")
        return {"success": False, "error": "internal error"}


def _send_channel_message(payload: dict) -> dict:
    """Send a message to an external channel (Discord, etc.) via channel_port."""
    channel = payload.get("channel", "")
    content = (payload.get("content") or "").strip()
    if not channel or not content:
        return {"success": False, "error": "channel and content are required"}

    try:
        from substrate.sockets.channel_port import get_channel_router

        router = get_channel_router()
        if not router:
            return {"success": False, "error": "no channel router registered"}

        result = router.send(channel=channel, content=content)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("send_channel_message failed: %s", e)
        return {"success": False, "error": str(e)}


def _chat_history(payload: dict) -> dict:
    """Return chat history including system report messages."""
    limit = int(payload.get("limit", 50))
    origin_channel = payload.get("origin_channel")
    try:
        from substrate.organism.store import OrganismStore
        store = OrganismStore()
        messages = store.list_messages(limit=limit, origin_channel=origin_channel)
        return {"success": True, "data": messages}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Development session handlers ──────────────────────────────────────

def _dev_sessions(payload: dict) -> dict:
    """List active and recent development sessions across all harnesses."""
    try:
        import json as _json
        from pathlib import Path

        sessions_dir = Path(_os.environ.get("UMH_ROOT", "/opt/OS")) / "data" / "umh" / "sessions"
        result: dict = {"active": [], "completed": []}

        active_path = sessions_dir / "active_sessions.jsonl"
        if active_path.exists():
            for line in active_path.read_text().strip().split("\n"):
                if line.strip():
                    result["active"].append(_json.loads(line))

        completed_path = sessions_dir / "completed_sessions.jsonl"
        if completed_path.exists():
            lines = completed_path.read_text().strip().split("\n")
            limit = int(payload.get("limit", 20))
            for line in lines[-limit:]:
                if line.strip():
                    result["completed"].append(_json.loads(line))

        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _dev_session_detail(payload: dict) -> dict:
    """Get full detail for a specific development session."""
    session_id = payload.get("session_id", "")
    if not session_id:
        return {"success": False, "error": "session_id required"}
    try:
        import json as _json
        from pathlib import Path

        session_file = (
            Path(_os.environ.get("UMH_ROOT", "/opt/OS"))
            / "data" / "umh" / "sessions" / f"{session_id}.json"
        )
        if not session_file.exists():
            return {"success": False, "error": f"session {session_id} not found"}

        data = _json.loads(session_file.read_text())
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Config handlers ────────────────────────────────────────

def _config_get(payload: dict) -> dict:
    """Get resolved config or a single key."""
    try:
        from substrate.sockets.config_port import get_config, get_all_config
        key = payload.get("key")
        if key:
            return {"success": True, "data": {"key": key, "value": get_config(key)}}
        return {"success": True, "data": get_all_config()}
    except Exception as e:
        logger.exception("config.get failed")
        return {"success": False, "error": str(e)}


_WRITABLE_LAYERS = {"system", "user", "venture"}


def _config_set(payload: dict) -> dict:
    """Set a config value. Requires key, value, optional layer (default: system)."""
    try:
        from substrate.sockets.config_port import set_config, get_config
        from substrate.state.config.config_store import VALID_KEYS
        key = payload.get("key")
        value = payload.get("value")
        layer = payload.get("layer", "system")
        if not key:
            return {"success": False, "error": "key is required"}
        if value is None:
            return {"success": False, "error": "value is required"}
        if key not in VALID_KEYS:
            return {"success": False, "error": f"invalid config key: {key}"}
        if layer not in _WRITABLE_LAYERS:
            return {"success": False, "error": f"invalid layer: {layer}"}
        set_config(key, value, layer=layer)
        return {"success": True, "data": {"key": key, "value": get_config(key), "layer": layer}}
    except Exception as e:
        logger.exception("config.set failed")
        return {"success": False, "error": str(e)}


def _config_layers(payload: dict) -> dict:
    """Get raw layer data for debugging/admin."""
    try:
        from substrate.state.config import config_store
        result = {}
        for layer_name in ("system", "user", "venture", "channel"):
            result[layer_name] = config_store.get_layer(layer_name)
        return {"success": True, "data": result}
    except Exception as e:
        logger.exception("config.layers failed")
        return {"success": False, "error": str(e)}


# ── Phase 9.4: Template Registry, Agent Capability, Propagation ──

def _templates(_payload: dict) -> dict:
    try:
        from substrate.organism.template_registry import TemplateRegistry
        reg = TemplateRegistry()
        return {"success": True, "data": reg.to_safe_dict()}
    except Exception as e:
        logger.exception("organism.templates failed")
        return {"success": False, "error": str(e)}


def _template_candidates(_payload: dict) -> dict:
    try:
        from substrate.organism.template_registry import TemplateRegistry
        reg = TemplateRegistry()
        candidates = [t.to_dict() for t in reg.pending_approvals()]
        return {"success": True, "data": {"candidates": candidates, "count": len(candidates)}}
    except Exception as e:
        logger.exception("organism.template_candidates failed")
        return {"success": False, "error": str(e)}


def _template_candidate_approve(payload: dict) -> dict:
    try:
        from substrate.organism.template_registry import TemplateRegistry
        template_id = payload.get("id", "")
        if not template_id:
            return {"success": False, "error": "Missing template id"}
        reg = TemplateRegistry()
        ok = reg.approve(template_id, decided_by="cockpit")
        if ok:
            reg.promote(template_id, decided_by="cockpit")
        return {"success": ok, "data": {"template_id": template_id, "approved": ok}}
    except Exception as e:
        logger.exception("organism.template_candidates.approve failed")
        return {"success": False, "error": str(e)}


def _template_candidate_reject(payload: dict) -> dict:
    try:
        from substrate.organism.template_registry import TemplateRegistry
        template_id = payload.get("id", "")
        reason = payload.get("reason", "")
        if not template_id:
            return {"success": False, "error": "Missing template id"}
        reg = TemplateRegistry()
        ok = reg.reject(template_id, reason=reason, decided_by="cockpit")
        return {"success": ok, "data": {"template_id": template_id, "rejected": ok}}
    except Exception as e:
        logger.exception("organism.template_candidates.reject failed")
        return {"success": False, "error": str(e)}


def _agent_capabilities(_payload: dict) -> dict:
    try:
        from substrate.organism.agent_capability_model import AgentCapabilityModel
        model = AgentCapabilityModel()
        return {"success": True, "data": model.to_safe_dict()}
    except Exception as e:
        logger.exception("organism.agent_capabilities failed")
        return {"success": False, "error": str(e)}


def _propagation(_payload: dict) -> dict:
    try:
        from substrate.organism.coherence_propagation import ParallelPropagationEngine
        engine = ParallelPropagationEngine()
        return {"success": True, "data": engine.to_safe_dict()}
    except Exception as e:
        logger.exception("organism.propagation failed")
        return {"success": False, "error": str(e)}


def _propagation_detail(payload: dict) -> dict:
    try:
        from substrate.organism.coherence_propagation import ParallelPropagationEngine
        event_id = payload.get("id", "")
        engine = ParallelPropagationEngine()
        event = engine.get_event(event_id)
        if not event:
            return {"success": False, "error": f"Propagation event {event_id} not found"}
        return {"success": True, "data": event.to_dict()}
    except Exception as e:
        logger.exception("organism.propagation.detail failed")
        return {"success": False, "error": str(e)}


def _outcomes(payload: dict) -> dict:
    try:
        from substrate.organism.outcome_learning import OutcomeLearningLoop
        loop = OutcomeLearningLoop()
        limit = int(payload.get("limit", 20))
        recent = loop.recent_outcomes(limit)
        return {"success": True, "data": {
            "outcomes": [o.to_dict() for o in recent],
            "count": len(recent),
            "summary": loop.summary(),
        }}
    except Exception as e:
        logger.exception("organism.outcomes failed")
        return {"success": False, "error": str(e)}


def _outcome_detail(payload: dict) -> dict:
    try:
        from substrate.organism.outcome_learning import OutcomeLearningLoop
        outcome_id = payload.get("id", "")
        loop = OutcomeLearningLoop()
        recent = loop.recent_outcomes(100)
        outcome = next((o for o in recent if o.id == outcome_id), None)
        if not outcome:
            return {"success": False, "error": f"Outcome {outcome_id} not found"}
        return {"success": True, "data": outcome.to_dict()}
    except Exception as e:
        logger.exception("organism.outcomes.detail failed")
        return {"success": False, "error": str(e)}


def _spine_propagation_status(_payload: dict) -> dict:
    try:
        from substrate.organism.coherence_propagation import ParallelPropagationEngine
        engine = ParallelPropagationEngine()
        summary = engine.summary()
        return {"success": True, "data": {
            "spine_native": True,
            "summary": summary,
            "registered_targets": [t.to_dict() for t in engine._targets],
            "processed_outcome_count": len(engine._processed_keys),
            "recent_failures": [f.to_dict() for f in engine.failed_outcomes(5)],
        }}
    except Exception as e:
        logger.exception("organism.spine_propagation_status failed")
        return {"success": False, "error": str(e)}


def _template_reuse_proof(_payload: dict) -> dict:
    try:
        umh_root = _os.environ.get("UMH_ROOT", "/opt/OS")
        proof_path = _os.path.join(umh_root, "data", "umh", "trials", "phase9_4_propagation_trial.json")
        if not _os.path.isfile(proof_path):
            return {"success": True, "data": {"has_proof": False}}
        with open(proof_path) as f:
            data = json.loads(f.read())
        return {"success": True, "data": {"has_proof": True, **data}}
    except Exception as e:
        logger.exception("organism.template_reuse_proof failed")
        return {"success": False, "error": str(e)}


# ── Action router ──────────────────────────────────────────

_ACTIONS: dict = {
    "organism.snapshot": _snapshot,
    "organism.status": _status,
    "organism.health": _health,
    "organism.objectives": _objectives,
    "organism.objective": _objective,
    "organism.agents": _agents,
    "organism.deliverables": _deliverables,
    "organism.learning": _learning,
    "organism.economy": _economy,
    "organism.economy.records": _economy_records,
    "organism.runtimes": _runtimes,
    "organism.supervisor": _supervisor,
    "organism.governor": _governor,
    "organism.governor.escalations": _governor_escalations,
    "organism.advisors": _advisors,
    "organism.advisors.tree": _advisors_tree,
    "organism.approvals": _approvals,
    "organism.approvals.count": _approvals_count,
    "organism.handoffs": _handoffs,
    "organism.leverage": _leverage,
    "organism.workcells": _workcells,
    "organism.approve": _approve,
    "organism.deny": _deny,
    "organism.kill": _kill,
    "organism.resume": _resume_governor,
    "organism.governor.reset": _governor_reset,
    "organism.refresh": _refresh_runtimes,
    "organism.sessions": _tmux_sessions,
    "organism.docker": _docker_containers,
    "organism.mesh": _mesh_nodes,
    "organism.world_model": _world_model,
    "organism.dependency_graph": _dependency_graph,
    "organism.contradictions": _contradictions,
    "organism.compose": _compose,
    "organism.learning_loop": _learning_loop,
    "organism.outcome_capture": _outcome_capture,
    "organism.memory_promotion": _memory_promotion,
    "organism.memory_promotion.approve": _memory_promotion_approve,
    "organism.memory_promotion.reject": _memory_promotion_reject,
    "organism.workspaces": _list_workspaces,
    "organism.files": _list_files,
    "organism.file.read": _read_file,
    "organism.execute_plan": _execute_plan,
    "organism.execution_graph": _execution_graph,
    "organism.execution_graph.detail": _execution_graph_detail,
    "organism.execute_plan.approve_step": _execute_plan_approve_step,
    "organism.execute_plan.pending": _execute_plan_pending,
    "organism.trial_status": _trial_status,
    "organism.dispatch_report": _dispatch_report,
    "organism.reports": _list_reports,
    "organism.converse": _converse,
    "organism.send_channel_message": _send_channel_message,
    "organism.chat_history": _chat_history,
    "organism.dev_sessions": _dev_sessions,
    "organism.dev_session_detail": _dev_session_detail,
    "organism.templates": _templates,
    "organism.template_candidates": _template_candidates,
    "organism.template_candidates.approve": _template_candidate_approve,
    "organism.template_candidates.reject": _template_candidate_reject,
    "organism.agent_capabilities": _agent_capabilities,
    "organism.propagation": _propagation,
    "organism.propagation.detail": _propagation_detail,
    "organism.template_reuse_proof": _template_reuse_proof,
    "organism.outcomes": _outcomes,
    "organism.outcomes.detail": _outcome_detail,
    "organism.spine_propagation_status": _spine_propagation_status,
    "config.get": _config_get,
    "config.set": _config_set,
    "config.layers": _config_layers,
}


def main():
    raw = sys.stdin.read()
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError as e:
        _emit({"success": False, "error": f"Invalid JSON: {e}"})
        return

    action = msg.get("action", "")
    payload = msg.get("payload", {})

    handler = _ACTIONS.get(action)
    if not handler:
        _emit({"success": False, "error": f"Unknown action: {action}"})
        return

    try:
        result = handler(payload)
    except Exception as e:
        logger.exception("handler %s failed", action)
        result = {
            "success": False,
            "error": "internal error",
        }

    _emit(result)


if __name__ == "__main__":
    main()
