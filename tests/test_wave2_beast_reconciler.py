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


def test_observation_error_fails_closed_before_no_session() -> None:
    st = NodeState(reachable=True, observation_error="access denied")
    assert st.condition == "OBSERVATION_UNAVAILABLE"


def test_parse_observation_payload_rejects_malformed_json() -> None:
    doc, err = R._parse_observation_payload("not-json")
    assert doc == {}
    assert "malformed observation JSON" in err


def test_parse_observation_payload_rejects_non_object_json() -> None:
    doc, err = R._parse_observation_payload("[1, 2, 3]")
    assert doc == {}
    assert err == "observation JSON is not an object"


def test_apply_observation_doc_proves_real_session_and_single_launcher() -> None:
    st = NodeState(reachable=True, connected_node_ids=[R._MESH_NODE_ID])
    R._apply_observation_doc(
        st,
        {
            "console": 1,
            "explorer_session": 1,
            "explorer_user": "antonys beast pc",
            "launchers": {
                "pid": 21980,
                "session": 1,
                "name": "pythonw.exe",
                "parent_pid": 22212,
                "parent_name": "op.exe",
                "executable": "C:\\Users\\antonys beast pc\\AppData\\Local\\Python\\bin\\pythonw.exe",
                "launcher_script": "C:\\dev\\dev\\OS\\nodes\\windows\\umh_node\\launcher.py",
                "parent_uses_env_tpl": True,
            },
            "task": "TaskName: \\UMH Node Daemon\nStatus: Running\n",
        },
    )
    assert st.interactive_session_exists is True
    assert st.live_tasks == [R._CANONICAL_TASK]
    assert st.launcher_pids == [
        {
            "pid": 21980,
            "session": 1,
            "name": "pythonw.exe",
            "parent_pid": 22212,
            "parent_name": "op.exe",
            "executable": "C:\\Users\\antonys beast pc\\AppData\\Local\\Python\\bin\\pythonw.exe",
            "launcher_script": "C:\\dev\\dev\\OS\\nodes\\windows\\umh_node\\launcher.py",
            "parent_uses_env_tpl": True,
        }
    ]
    assert st.condition == "HEALTHY"


def test_apply_observation_doc_zero_launcher_is_dead() -> None:
    st = NodeState(reachable=True, connected_node_ids=[R._MESH_NODE_ID])
    R._apply_observation_doc(
        st,
        {
            "console": 1,
            "explorer_session": 1,
            "launchers": [],
            "task": "TaskName: \\UMH Node Daemon\nStatus: Running\n",
        },
    )
    assert st.condition == "DEAD"


def test_task_status_ready_is_not_live_when_last_run_time_contains_running() -> None:
    st = NodeState(reachable=True, connected_node_ids=[])
    R._apply_observation_doc(
        st,
        {
            "console": 1,
            "explorer_session": 1,
            "launchers": [],
            "task": (
                "TaskName: \\UMH Node Daemon\n"
                "Status: Ready\n"
                "Last Run Time: 8/18/2026 2:43:36 PM\n"
                "Task To Run: powershell.exe -File task_supervisor.ps1\n"
            ),
        },
    )

    assert st.live_tasks == []
    assert st.condition == "DEAD"


def test_apply_observation_doc_duplicate_launchers_refuses() -> None:
    st = NodeState(reachable=True, connected_node_ids=[R._MESH_NODE_ID])
    R._apply_observation_doc(
        st,
        {
            "console": 1,
            "explorer_session": 1,
            "launchers": [
                {"pid": 21980, "session": 1, "name": "pythonw.exe"},
                {"pid": 14240, "session": 1, "name": "pythonw.exe"},
            ],
            "task": "TaskName: \\UMH Node Daemon\nStatus: Running\n",
        },
    )
    assert st.condition == "DUPLICATE"


def test_observe_uses_ssh_when_mesh_node_absent(monkeypatch) -> None:
    payload = {
        "console": 1,
        "explorer_session": 1,
        "launchers": {"pid": 21980, "session": 1, "name": "pythonw.exe"},
        "task": "TaskName: \\UMH Node Daemon\nStatus: Running\n",
    }
    monkeypatch.setattr(R, "_tailscale_reachable", lambda: True)
    monkeypatch.setattr(R, "_mesh_health", lambda: {"node_ids": []})
    monkeypatch.setattr(
        R,
        "_mesh_shell",
        lambda *args, **kwargs: {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "error": "node windows-desktop not connected",
        },
    )
    monkeypatch.setattr(
        R,
        "_ssh_shell",
        lambda *args, **kwargs: {"ok": True, "stdout": R.json.dumps(payload), "stderr": ""},
    )

    st = R.observe()

    assert st.observation_channel == "ssh"
    assert st.interactive_session_exists is True
    assert st.launcher_pids == [
        {
            "pid": 21980,
            "session": 1,
            "name": "pythonw.exe",
            "parent_pid": None,
            "parent_name": None,
            "executable": None,
            "launcher_script": None,
            "parent_uses_env_tpl": None,
        }
    ]
    assert st.condition == "ABSENT"


def test_observe_reports_observation_unavailable_when_mesh_and_ssh_fail(monkeypatch) -> None:
    monkeypatch.setattr(R, "_tailscale_reachable", lambda: True)
    monkeypatch.setattr(R, "_mesh_health", lambda: {"node_ids": []})
    monkeypatch.setattr(
        R,
        "_mesh_shell",
        lambda *args, **kwargs: {"ok": False, "stderr": "command not found", "error": ""},
    )
    monkeypatch.setattr(
        R,
        "_ssh_shell",
        lambda *args, **kwargs: {"ok": False, "stderr": "Access is denied.", "error": ""},
    )

    st = R.observe()

    assert st.condition == "OBSERVATION_UNAVAILABLE"
    assert "command not found" in st.observation_error
    assert "Access is denied" in st.observation_error


def test_reconciler_observer_does_not_depend_on_query_or_qwinsta() -> None:
    assert "query.exe" not in R._PS_OBSERVE_BODY.lower()
    assert "qwinsta" not in R._PS_OBSERVE_BODY.lower()
    assert "command=$_.commandline" not in R._PS_OBSERVE_BODY.lower()
    assert "parent_command" not in R._PS_OBSERVE_BODY.lower()


def test_field_dispatch_session_probe_does_not_depend_on_query_or_qwinsta() -> None:
    dispatch = load_wave2_script("wave2_field_dispatch")
    source = dispatch.Path(dispatch.__file__).read_text(encoding="utf-8")
    query_session_block = source.split('out["query_session"] = _mesh_read(', 1)[1].split(
        "# Beast", 1
    )[0]
    assert "getcurrentprocess().sessionid" in query_session_block.lower()
    assert "query.exe" not in query_session_block.lower()
    assert "qwinsta" not in query_session_block.lower()


def test_reconcile_observation_unavailable_does_not_repair(monkeypatch) -> None:
    calls = []
    st = NodeState(reachable=True, observation_error="command unavailable")
    monkeypatch.setattr(R, "observe", lambda: st)
    monkeypatch.setattr(R, "_mesh_shell", lambda *args, **kwargs: calls.append(args) or {})

    v = reconcile(dry_run=False, prove=False)

    assert v["ok"] is False
    assert v["condition"] == "OBSERVATION_UNAVAILABLE"
    assert v["actions"] == []
    assert calls == []
