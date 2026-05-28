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

UMH substrate bridge — no instance context.
"""

import sys
import json

_stdout = sys.stdout
sys.stdout = sys.stderr

import os as _os
_BRIDGE_ROOT = _os.path.dirname(
    _os.path.dirname(_os.path.dirname(
        _os.path.abspath(__file__))))
sys.path.insert(0, _BRIDGE_ROOT)

from dotenv import load_dotenv
load_dotenv(_os.path.join(_BRIDGE_ROOT, 'services', '.env'))

import logging
logger = logging.getLogger(__name__)


def _emit(obj: dict) -> None:
    _stdout.write(json.dumps(obj, default=str) + '\n')
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
        coordinator=getattr(d, '_coordinator', None) or getattr(d, 'coordinator', None),
        graph=getattr(d, '_graph', None) or getattr(d, 'graph', None),
        supervisor=getattr(d, '_supervisor', None) or getattr(d, 'supervisor', None),
        daemon=getattr(d, '_workcell_daemon', None),
        homeostasis=getattr(d, '_homeostasis', None) or getattr(d, 'homeostasis', None),
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
        "mode": report.mode.value if hasattr(report.mode, 'value') else str(report.mode),
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
    coord = getattr(daemon, '_coordinator', None) or getattr(daemon, 'coordinator', None)
    if coord:
        return {"success": True, "data": coord.list_objectives()}
    return {"success": True, "data": []}


def _objective(payload: dict) -> dict:
    obj_id = payload.get("objective_id", "")
    daemon = _get_daemon()
    coord = getattr(daemon, '_coordinator', None) or getattr(daemon, 'coordinator', None)
    if coord:
        obj = coord.get_objective(obj_id)
        if obj:
            return {"success": True, "data": obj}
    return {"success": False, "error": f"Objective {obj_id} not found"}


def _agents(_payload: dict) -> dict:
    daemon = _get_daemon()
    advisor = getattr(daemon, '_advisor', None) or getattr(daemon, 'advisor', None)
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
    return {"success": True, "data": [r.to_dict() if hasattr(r, 'to_dict') else r for r in records]}


def _runtimes(_payload: dict) -> dict:
    daemon = _get_daemon()
    graph = getattr(daemon, '_graph', None) or getattr(daemon, 'graph', None)
    if graph:
        return {"success": True, "data": graph.to_dict()}
    return {"success": True, "data": {"nodes": [], "node_count": 0}}


def _supervisor(_payload: dict) -> dict:
    daemon = _get_daemon()
    sup = getattr(daemon, '_supervisor', None) or getattr(daemon, 'supervisor', None)
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
    return {"success": True, "data": [e.to_dict() if hasattr(e, 'to_dict') else e for e in log]}


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
    wc_daemon = getattr(daemon, '_workcell_daemon', None)
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
    return {"success": True, "data": {"kill_switch": True, "message": "Autonomous execution halted"}}


def _resume_governor(_payload: dict) -> dict:
    gov = _get_governor()
    gov.resume()
    return {"success": True, "data": {"kill_switch": False, "message": "Autonomous execution resumed"}}


def _governor_reset(_payload: dict) -> dict:
    gov = _get_governor()
    gov.reset_state()
    return {"success": True, "data": {"message": "Governor counters reset"}}


def _refresh_runtimes(_payload: dict) -> dict:
    daemon = _get_daemon()
    graph = getattr(daemon, '_graph', None) or getattr(daemon, 'graph', None)
    if graph:
        availability = graph.refresh_availability()
        return {"success": True, "data": availability}
    return {"success": True, "data": {}}


# ── System visibility ──────────────────────────────────────

def _tmux_sessions(_payload: dict) -> dict:
    import subprocess
    try:
        result = subprocess.run(
            ['tmux', 'list-sessions', '-F',
             '#{session_name}|#{session_windows}|#{session_created}|#{session_attached}'],
            capture_output=True, text=True, timeout=5
        )
        sessions = []
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|')
                sessions.append({
                    "name": parts[0] if len(parts) > 0 else "",
                    "windows": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
                    "created": parts[2] if len(parts) > 2 else "",
                    "attached": parts[3] == "1" if len(parts) > 3 else False,
                })
        return {"success": True, "data": sessions}
    except Exception as e:
        return {"success": True, "data": [], "warning": str(e)}


def _docker_containers(_payload: dict) -> dict:
    import subprocess
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format',
             '{{.Names}}|{{.Status}}|{{.Image}}|{{.Ports}}|{{.State}}'],
            capture_output=True, text=True, timeout=10
        )
        containers = []
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|')
                containers.append({
                    "name": parts[0] if len(parts) > 0 else "",
                    "status": parts[1] if len(parts) > 1 else "",
                    "image": parts[2] if len(parts) > 2 else "",
                    "ports": parts[3] if len(parts) > 3 else "",
                    "state": parts[4] if len(parts) > 4 else "",
                })
        return {"success": True, "data": containers}
    except Exception as e:
        return {"success": True, "data": [], "warning": str(e)}


def _mesh_nodes(_payload: dict) -> dict:
    import subprocess
    try:
        result = subprocess.run(
            ['tailscale', 'status', '--json'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            peers = data.get("Peer", {})
            nodes = []
            self_node = data.get("Self", {})
            if self_node:
                nodes.append({
                    "hostname": self_node.get("HostName", ""),
                    "ip": self_node.get("TailscaleIPs", [""])[0] if self_node.get("TailscaleIPs") else "",
                    "os": self_node.get("OS", ""),
                    "online": True,
                    "self": True,
                })
            for _key, peer in peers.items():
                nodes.append({
                    "hostname": peer.get("HostName", ""),
                    "ip": peer.get("TailscaleIPs", [""])[0] if peer.get("TailscaleIPs") else "",
                    "os": peer.get("OS", ""),
                    "online": peer.get("Online", False),
                    "self": False,
                })
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
    return {"success": True, "data": graph.to_dict()}


def _contradictions(_payload: dict) -> dict:
    from substrate.organism.contradiction_engine import detect_contradictions
    report = detect_contradictions()
    return {"success": True, "data": report.to_dict()}


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
    return {"success": True, "data": loop.to_dict()}


def _compose(payload: dict) -> dict:
    from substrate.organism.composition_engine import compose_plan
    intent = payload.get("intent", "")
    if not intent:
        return {"success": False, "error": "intent required"}
    plan = compose_plan(intent)
    return {"success": True, "data": plan.to_dict()}


def _list_workspaces(_payload: dict) -> dict:
    import subprocess
    workspaces = []
    umh_root = _os.environ.get("UMH_ROOT", "/opt/OS")
    worktree_dir = _os.path.join(umh_root, ".claude", "worktrees")
    if _os.path.isdir(worktree_dir):
        for name in sorted(_os.listdir(worktree_dir)):
            full = _os.path.join(worktree_dir, name)
            if _os.path.isdir(full):
                workspaces.append({
                    "name": name,
                    "path": full,
                    "type": "worktree",
                })
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
            if name.startswith('.') and name not in ('.claude', '.env.example'):
                continue
            if name in ('__pycache__', 'node_modules', '.git', '.mypy_cache', '.ruff_cache', '.pytest_cache'):
                continue
            is_dir = _os.path.isdir(full)
            entries.append({
                "name": name,
                "path": full,
                "type": "directory" if is_dir else "file",
                "size": _os.path.getsize(full) if not is_dir else None,
            })
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
        with open(path, 'r', errors='replace') as f:
            content = f.read()
        return {"success": True, "data": {"path": path, "content": content, "size": size}}
    except Exception as e:
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
    "organism.memory_promotion": _memory_promotion,
    "organism.memory_promotion.approve": _memory_promotion_approve,
    "organism.memory_promotion.reject": _memory_promotion_reject,
    "organism.workspaces": _list_workspaces,
    "organism.files": _list_files,
    "organism.file.read": _read_file,
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
        import traceback
        result = {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

    _emit(result)


if __name__ == "__main__":
    main()
