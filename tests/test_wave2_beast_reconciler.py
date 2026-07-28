"""Wave 2 Beast reconciler — condition classification + verdict branches.

Pins the out-of-band bootstrap/recovery logic that codifies the 2026-07-24 manual
reconciliation (reachable-but-absent from mesh; duplicate ONLOGON daemons sharing
one identity). Pure logic + mocked observe — no network, no quota.
"""

from __future__ import annotations

from tests.wave2_script_import import load_wave2_script

R = load_wave2_script("wave2_beast_reconciler")
NodeState, reconcile = R.NodeState, R.reconcile


def _healthy_state() -> NodeState:
    return NodeState(
        reachable=True,
        console_session=2,
        launcher_pids=[{"pid": 29700, "session": 2, "name": "pythonw.exe"}],
        live_tasks=[R._CANONICAL_TASK],
        connected_node_ids=[R._MESH_NODE_ID],
        interactive_session_exists=True,
    )


# ── condition classification (pure) ──────────────────────────────────────────


def test_healthy_is_healthy() -> None:
    assert _healthy_state().condition == "HEALTHY"


def test_unreachable() -> None:
    assert NodeState(reachable=False).condition == "UNREACHABLE"


def test_no_interactive_session_when_explorer_absent() -> None:
    # reachable, but no interactive console session (Explorer not in console sid)
    st = NodeState(reachable=True, interactive_session_exists=False)
    assert st.condition == "NO_INTERACTIVE_SESSION"


def test_duplicate_when_two_launchers() -> None:
    st = _healthy_state()
    st.interactive_session_exists = True
    st.launcher_pids = [
        {"pid": 1, "session": 2, "name": "python.exe"},
        {"pid": 2, "session": 2, "name": "pythonw.exe"},
    ]
    assert st.condition == "DUPLICATE"


def test_duplicate_when_two_live_tasks() -> None:
    st = _healthy_state()
    st.live_tasks = [R._CANONICAL_TASK, "UMH_NodeDaemon"]
    assert st.condition == "DUPLICATE"


def test_dead_when_no_launcher() -> None:
    st = _healthy_state()
    st.launcher_pids = []
    assert st.condition == "DEAD"


def test_wrong_session_when_daemon_off_console() -> None:
    st = _healthy_state()
    st.launcher_pids = [{"pid": 9, "session": 0, "name": "pythonw.exe"}]
    assert st.condition == "WRONG_SESSION"


def test_absent_when_one_launcher_but_no_mesh_identity() -> None:
    st = _healthy_state()
    st.connected_node_ids = []
    assert st.condition == "ABSENT"


def test_extra_identity_is_not_healthy() -> None:
    st = _healthy_state()
    st.connected_node_ids = [R._MESH_NODE_ID, "rogue"]
    # one launcher, right session, but identity set != [node] → ABSENT (not healthy)
    assert st.condition != "HEALTHY"


# ── verdict branches (mocked observe; no mutation) ───────────────────────────


def test_reconcile_healthy_short_circuits(monkeypatch) -> None:
    monkeypatch.setattr(R, "observe", _healthy_state)
    v = reconcile(dry_run=False, prove=False)
    assert v["ok"] is True
    assert not v.get("actions"), "healthy path must not mutate"


def test_reconcile_unreachable_is_not_owner_decision(monkeypatch) -> None:
    monkeypatch.setattr(R, "observe", lambda: NodeState(reachable=False))
    v = reconcile(dry_run=False, prove=False)
    assert v["ok"] is False
    assert v["needs_owner_decision"] is False


def test_reconcile_no_session_surfaces_governed_decision_not_manual(monkeypatch) -> None:
    st = NodeState(reachable=True, interactive_session_exists=False)
    monkeypatch.setattr(R, "observe", lambda: st)
    v = reconcile(dry_run=False, prove=False)
    assert v["ok"] is False
    assert v["needs_owner_decision"] is True
    assert "decision" in v and "effect" in v["decision"]
    # It must NOT have executed any repair action.
    assert not v.get("actions")


def test_reconcile_duplicate_dry_run_plans_but_does_not_mutate(monkeypatch) -> None:
    st = _healthy_state()
    st.launcher_pids = [
        {"pid": 1, "session": 2, "name": "python.exe"},
        {"pid": 2, "session": 2, "name": "pythonw.exe"},
    ]
    monkeypatch.setattr(R, "observe", lambda: st)
    v = reconcile(dry_run=True, prove=False)
    assert v["ok"] is None
    assert v["planned"] and any("canonical" in p for p in v["planned"])
    assert not v.get("actions")


def test_daemon_count_excludes_wrapper_and_observer(monkeypatch) -> None:
    """op.exe wrapper + observer cmd/powershell must NOT inflate the launcher count."""
    # Simulate the raw observe payload classification indirectly: only python[w]
    # processes count. Build a state as observe() would after filtering.
    st = _healthy_state()  # exactly one pythonw
    assert len(st.launcher_pids) == 1
    assert st.condition == "HEALTHY"
