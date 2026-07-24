"""Wave 2 C-3 — scenario map from REAL records, exact plan + authorization.

C-3 was never "a scenario-map capability is missing" — `resolve_scenario_map`
already existed. C-3 was that NOTHING in the real pipeline wrote the map. The
first repair wrote/consumed it but left three fail-open shortcuts (owner
microfix): a plan node's workpacket_id was treated as proof a packet exists;
run selection fell back to "latest plan" via a run-tag substring; and the
"authorized frontier" was "all packets I can find" rather than the granted
task_frontier.

This suite now requires, for every semantic role:

    exact plan node → node_id → exactly one PERSISTED canonical WorkPacket record
    whose source_evidence names that node AND whose packet_id == node.workpacket_id

and derives the authorized frontier from the ONE ACTIVE
execution-authorization grant for the EXACT plan version. Every fail-open mode
(A–L in the order) is pinned.
"""

from __future__ import annotations

import pytest

from substrate.execution.attempts.field_failure_policy import (
    arming_is_valid_for_run,
    disallowed_tools_for,
    injection_fired,
)
from substrate.execution.attempts.field_scenario_map import (
    ScenarioMapError,
    build_from_records,
    read_scenario_map,
    resolve_authorized_frontier,
    select_plan,
    write_scenario_map,
)
from substrate.execution.attempts.field_task_scope import (
    BACKEND,
    FIXTURE_NODE_TITLES,
    VERIFICATION,
)

_PLAN_ID = "opr-run-1"
_TENANT = "tenant-a"
_ROLE_NODE = {
    BACKEND: ("node-be", "wp-aaaaaaaaaaaa"),
    "frontend_task_id": ("node-fe", "wp-bbbbbbbbbbbb"),
    "integration_task_id": ("node-int", "wp-cccccccccccc"),
    VERIFICATION: ("node-ver", "wp-dddddddddddd"),
}
_LABELS = (BACKEND, "frontend_task_id", "integration_task_id", VERIFICATION)


# ── realistic candidate records: plan + 4 WorkPackets + 1 ACTIVE grant ──────
def _plan_record(*, version=1, status="approved"):
    nodes = [
        {
            "node_id": _ROLE_NODE[label][0],
            "kind": "packet",
            "status": "active",
            "title": FIXTURE_NODE_TITLES[label],
            "workpacket_id": _ROLE_NODE[label][1],
        }
        for label in _LABELS
    ]
    return {
        "plan_record_id": _PLAN_ID,
        "graph_version": version,
        "status": status,
        "objective_text": "add note search",
        "workpacket_ids": [_ROLE_NODE[label][1] for label in _LABELS],
        "nodes": nodes,
    }


def _packet_record(label):
    """A REAL persisted WorkPacket record with exact plan-node lineage."""
    node_id, packet_id = _ROLE_NODE[label]
    return {
        "packet_id": packet_id,
        "source_evidence": [{"type": "plan_node", "node_id": node_id}],
        "title": FIXTURE_NODE_TITLES[label],
    }


def _grant_record(*, version=1, status="active", frontier=None, expires_at=0.0, tenant=_TENANT):
    return {
        "grant_id": "grant-1",
        "decision_ref": f"objective_plan:{_PLAN_ID}:execution_authorization:v1",
        "plan_record_id": _PLAN_ID,
        "plan_version": version,
        "tenant_id": tenant,
        "status": status,
        "task_frontier": frontier
        if frontier is not None
        else [_ROLE_NODE[label][1] for label in _LABELS],
        "expires_at": expires_at,
    }


def _records(
    *,
    version=1,
    plan_status="approved",
    grant_status="active",
    frontier=None,
    grant_expires=0.0,
    packets=None,
):
    recs = [_plan_record(version=version, status=plan_status)]
    for label in packets if packets is not None else _LABELS:
        recs.append(_packet_record(label))
    recs.append(
        _grant_record(
            version=version, status=grant_status, frontier=frontier, expires_at=grant_expires
        )
    )
    return recs


def _arm(targets, variant="tools-revoked-backend"):
    (targets / ".inject_failure").write_text(variant, encoding="utf-8")


def _build(records=None, **kw):
    return build_from_records(
        records if records is not None else _records(),
        run_id="run-1",
        plan_record_id=_PLAN_ID,
        plan_version=kw.pop("plan_version", 1),
        **kw,
    )


def _arm_check(targets, records, **kw):
    return arming_is_valid_for_run(
        str(targets),
        run_id="run-1",
        records=records,
        plan_record_id=kw.pop("plan_record_id", _PLAN_ID),
        plan_version=kw.pop("plan_version", 1),
        tenant_id=kw.pop("tenant_id", _TENANT),
        **kw,
    )


# ── happy path over REAL records ────────────────────────────────────────────


def test_build_requires_real_packets_and_binds_exactly():
    payload = _build()
    assert payload[BACKEND] == "wp-aaaaaaaaaaaa"
    assert payload["plan_record_id"] == _PLAN_ID
    assert payload["plan_version"] == 1
    assert payload["digest"]
    assert payload["execution_authorization_ref"] == ""


def test_full_chain_arms_targets_backend_first_attempt(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    write_scenario_map(targets, _build())
    _arm(targets)
    ok, reason = _arm_check(targets, _records())
    assert ok, reason
    assert "Edit" in disallowed_tools_for(
        targets_dir=str(targets), task_id="wp-aaaaaaaaaaaa", attempt_number=1
    )
    assert (
        disallowed_tools_for(targets_dir=str(targets), task_id="wp-aaaaaaaaaaaa", attempt_number=2)
        == []
    )
    assert (
        disallowed_tools_for(targets_dir=str(targets), task_id="wp-bbbbbbbbbbbb", attempt_number=1)
        == []
    )


# ── A. node references a packet with NO WorkPacket record → fail ────────────


def test_A_node_references_ghost_packet_with_no_record_fails():
    recs = _records(packets=["frontend_task_id", "integration_task_id", VERIFICATION])
    with pytest.raises(ScenarioMapError):
        build_from_records(recs, run_id="run-1", plan_record_id=_PLAN_ID, plan_version=1)


# ── B. a packet exists but its lineage points to ANOTHER node → fail ───────


def test_B_packet_lineage_points_to_another_node_fails():
    recs = _records()
    for r in recs:
        if r.get("packet_id") == "wp-aaaaaaaaaaaa":
            r["source_evidence"] = [{"type": "plan_node", "node_id": "node-fe"}]
    with pytest.raises(ScenarioMapError):
        build_from_records(recs, run_id="run-1", plan_record_id=_PLAN_ID, plan_version=1)


# ── C. node.workpacket_id disagrees with packet.packet_id → fail ───────────


def test_C_node_and_packet_id_disagree_fails():
    recs = _records()
    for r in recs:
        for n in r.get("nodes", []):
            if n.get("node_id") == "node-be":
                n["workpacket_id"] = "wp-mismatch1234"
    with pytest.raises(ScenarioMapError, match="disagree"):
        build_from_records(recs, run_id="run-1", plan_record_id=_PLAN_ID, plan_version=1)


# ── D. state has only run-A plan; writer requested for run-B → no fallback ──


def test_D_no_plan_for_requested_id_fails_no_fallback():
    recs = _records()
    with pytest.raises(ScenarioMapError, match="matched 0 records"):
        build_from_records(recs, run_id="run-B", plan_record_id="opr-run-B", plan_version=1)


# ── E. two plans share graph_version; exact id/version selects one ─────────


def test_E_exact_plan_version_selection_is_unambiguous():
    recs = _records()
    other = _plan_record(version=1)
    other["plan_record_id"] = "opr-OTHER"
    recs.append(other)
    plan = select_plan(recs, plan_record_id=_PLAN_ID, plan_version=1)
    assert plan["plan_record_id"] == _PLAN_ID
    recs.append(_plan_record(version=1))
    with pytest.raises(ScenarioMapError, match="matched 2 records"):
        select_plan(recs, plan_record_id=_PLAN_ID, plan_version=1)


# ── F. no granted authorization → fail ──────────────────────────────────────


def test_F_no_grant_fails():
    recs = [r for r in _records() if not r.get("grant_id")]
    with pytest.raises(ScenarioMapError, match="no execution-authorization grant"):
        resolve_authorized_frontier(
            recs, plan_record_id=_PLAN_ID, plan_version=1, tenant_id=_TENANT
        )


# ── G. authorization denied/expired/revoked/invalidated → fail ─────────────


@pytest.mark.parametrize("status", ["revoked", "invalidated", "failed_activation", "activating"])
def test_G_non_active_grant_fails(status):
    recs = _records(grant_status=status)
    with pytest.raises(ScenarioMapError, match="not ACTIVE"):
        resolve_authorized_frontier(
            recs, plan_record_id=_PLAN_ID, plan_version=1, tenant_id=_TENANT
        )


def test_G_expired_grant_fails():
    recs = _records(grant_expires=1.0)
    with pytest.raises(ScenarioMapError, match="expired"):
        resolve_authorized_frontier(
            recs, plan_record_id=_PLAN_ID, plan_version=1, tenant_id=_TENANT, now=1e9
        )


# ── H. authorization for another plan version → fail ───────────────────────


def test_H_grant_for_another_plan_version_fails():
    recs = [_plan_record(version=2)]
    for label in _LABELS:
        recs.append(_packet_record(label))
    recs.append(_grant_record(version=1))
    with pytest.raises(ScenarioMapError, match="no execution-authorization grant"):
        resolve_authorized_frontier(
            recs, plan_record_id=_PLAN_ID, plan_version=2, tenant_id=_TENANT
        )


# ── I. an unrelated canonical packet never enters the frontier ─────────────


def test_I_unrelated_packet_never_enters_frontier():
    recs = _records()
    recs.append({"packet_id": "wp-unrelated99", "source_evidence": []})
    frontier, _ = resolve_authorized_frontier(
        recs, plan_record_id=_PLAN_ID, plan_version=1, tenant_id=_TENANT
    )
    assert "wp-unrelated99" not in frontier


# ── J. plan has 4 tasks, grant authorizes 3; excluded task cannot target ───


def test_J_task_outside_granted_frontier_cannot_be_targeted(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    write_scenario_map(targets, _build())
    _arm(targets)
    recs = _records(frontier=["wp-bbbbbbbbbbbb", "wp-cccccccccccc", "wp-dddddddddddd"])
    ok, reason = _arm_check(targets, recs)
    assert ok is False and "frontier" in reason.lower()


# ── K. empty authorization frontier → fail, never "skip" ───────────────────


def test_K_empty_frontier_fails():
    recs = _records(frontier=[])
    with pytest.raises(ScenarioMapError, match="EMPTY task_frontier"):
        resolve_authorized_frontier(
            recs, plan_record_id=_PLAN_ID, plan_version=1, tenant_id=_TENANT
        )


# ── L. reverting to synthetic plan-node packets / all-packet frontier fails ─


def test_L_build_does_not_synthesize_packets_from_plan_nodes():
    """Source-level: build_from_records must not fabricate packet records from
    plan nodes. Asserted on AST-unparsed CODE (the docstring explains the ban)."""
    import ast
    import inspect

    from substrate.execution.attempts import field_scenario_map as fsm

    tree = ast.parse(inspect.getsource(fsm.build_from_records).lstrip())
    fn = tree.body[0]
    body = fn.body[1:] if isinstance(fn.body[0], ast.Expr) else fn.body
    code = "\n".join(ast.unparse(n) for n in body)
    assert "node_packets" not in code, "must not synthesize packets from plan nodes"
    assert "workpacket_id" in code, "node/packet id agreement must still be checked"


def test_L_frontier_is_grant_derived_not_all_packets():
    """Source-level: the field frontier binding comes from the ACTIVE grant, not
    an aggregation over all packet records."""
    import inspect

    import scripts.wave2_field_dispatch as wd

    src = inspect.getsource(wd._active_grant_binding)
    assert "active" in src
    assert not hasattr(wd, "_authorized_frontier"), (
        "the all-packets frontier helper must be removed"
    )


# ── staleness + run-binding ─────────────────────────────────────────────────


def test_stale_plan_version_fails(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    write_scenario_map(targets, _build(plan_version=1))
    _arm(targets)
    recs = [_plan_record(version=2)]
    for label in _LABELS:
        recs.append(_packet_record(label))
    recs.append(_grant_record(version=2))
    ok, reason = _arm_check(targets, recs, plan_version=2)
    assert ok is False and "stale" in reason.lower()


def test_wrong_run_binding_fails(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    payload = _build()
    payload["run_id"] = "run-OTHER"
    write_scenario_map(targets, payload)
    _arm(targets)
    ok, reason = _arm_check(targets, _records())
    assert ok is False and "another run" in reason.lower()


def test_absent_map_fails(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    _arm(targets)
    ok, reason = _arm_check(targets, _records())
    assert ok is False and "absent" in reason


def test_clean_run_is_always_valid(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    ok, _ = _arm_check(targets, _records())
    assert ok is True


def test_unknown_variant_fails(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    write_scenario_map(targets, _build())
    (targets / ".inject_failure").write_text("tools-revoked-nonsense", encoding="utf-8")
    ok, reason = _arm_check(targets, _records())
    assert ok is False and "unknown" in reason.lower()


# ── injection fires + map is identity-only ──────────────────────────────────


def test_injection_fired_detects_never_observed():
    assert injection_fired([{"disallowed_tools": []}]) is False
    assert injection_fired([{"disallowed_tools": ["Edit"]}]) is True


def test_end_to_end_fires_on_backend_first_attempt_only(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    payload = _build()
    write_scenario_map(targets, payload)
    _arm(targets)
    ok, reason = _arm_check(targets, _records())
    assert ok, reason
    be = payload[BACKEND]
    dispatched = [
        {
            "task_id": t,
            "attempt": a,
            "disallowed_tools": disallowed_tools_for(
                targets_dir=str(targets), task_id=t, attempt_number=a
            ),
        }
        for t in [_ROLE_NODE[label][1] for label in _LABELS]
        for a in (1, 2)
    ]
    fired = [d for d in dispatched if d["disallowed_tools"]]
    assert len(fired) == 1 and fired[0]["task_id"] == be and fired[0]["attempt"] == 1
    assert injection_fired(dispatched) is True


def test_map_is_identity_only_never_mutation_authority():
    payload = _build()
    for key in (
        "writable_path_scope",
        "allowed_tools",
        "scope_declared",
        "allowed_paths",
        "tool_policy",
        "risk_class",
    ):
        assert key not in payload
    assert set(payload) <= {
        *_LABELS,
        "run_id",
        "plan_record_id",
        "plan_version",
        "execution_authorization_ref",
        "digest",
    }


def test_persisted_map_round_trips(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    payload = _build()
    write_scenario_map(targets, payload)
    got = read_scenario_map(targets)
    assert got["backend_task_id"] == payload["backend_task_id"]
    assert got["digest"] == payload["digest"]
