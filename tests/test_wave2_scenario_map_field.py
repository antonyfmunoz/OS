"""Wave 2 C-3 — scenario map + run binding: EXACT grant, never "the only ACTIVE".

C-3 was never "a scenario-map capability is missing" — `resolve_scenario_map`
already existed. The prior repairs wrote/consumed the map and removed three
fail-open shortcuts (synthetic plan-node packets, latest-plan fallback,
all-packets frontier). The FINAL run-binding microfix removes the last one: the
dispatcher used to resolve the target through "the ONE ACTIVE grant in all
candidate state" — not a run binding. A legitimate ACTIVE grant left by a prior
green pass or a parallel run breaks it (0 or 2 matches), and it discarded the
identifiers already on ``ExecutionAuthorizationGrant``.

The run's identity is now CAPTURED as ``execution_binding.json`` (identifiers +
observed versions only) and BOTH map writing and arming resolve the ONE canonical
grant matching every binding field through the single ``resolve_canonical_grant``
authority. The map's claimed authorization binding is VERIFIABLE: the persisted
``execution_authorization_ref`` must equal the canonical grant's ``decision_ref``,
the persisted ``grant_id`` must equal the canonical ``grant_id``, and the full
binding digest must recompute.

Every fail-open mode (A–N in the owner order) is pinned + mutation-verified.
"""

from __future__ import annotations

import pytest

from substrate.execution.attempts.field_failure_policy import (
    arming_is_valid_for_run,
    disallowed_tools_for,
    injection_fired,
)
from substrate.execution.attempts.field_scenario_map import (
    ExecutionBinding,
    ScenarioMapError,
    build_from_records,
    read_scenario_map,
    resolve_authorized_frontier,
    resolve_canonical_grant,
    select_plan,
    write_execution_binding,
    write_scenario_map,
)
from substrate.execution.attempts.field_task_scope import (
    BACKEND,
    FIXTURE_NODE_TITLES,
    VERIFICATION,
)

_PLAN_ID = "opr-run-1"
_TENANT = "tenant-a"
_GRANT_ID = "grant-1"
_DECISION_REF = f"objective_plan:{_PLAN_ID}:execution_authorization:v1"
_CONV = "conv-1"
_CORR = "corr-1"
_PRINCIPAL = "prin-1"
_MEMBERSHIP = "mem-1"
_RUN_ID = "run-1"

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
        # the run tag rides on the plan/grant records so capture is journey-derived
        "run_tag": _RUN_ID,
    }


def _packet_record(label, *, tenant=_TENANT):
    """A REAL persisted WorkPacket record with exact plan-node lineage."""
    node_id, packet_id = _ROLE_NODE[label]
    return {
        "packet_id": packet_id,
        "source_evidence": [{"type": "plan_node", "node_id": node_id}],
        "title": FIXTURE_NODE_TITLES[label],
        "tenant_id": tenant,
    }


def _grant_record(
    *,
    version=1,
    status="active",
    frontier=None,
    expires_at=0.0,
    not_before=0.0,
    tenant=_TENANT,
    grant_id=_GRANT_ID,
    decision_ref=_DECISION_REF,
    conversation_id=_CONV,
    correlation_id=_CORR,
    principal_id=_PRINCIPAL,
    membership_id=_MEMBERSHIP,
    run_tag=_RUN_ID,
):
    rec = {
        "grant_id": grant_id,
        "decision_ref": decision_ref,
        "plan_record_id": _PLAN_ID,
        "plan_version": version,
        "tenant_id": tenant,
        "principal_id": principal_id,
        "membership_id": membership_id,
        "conversation_id": conversation_id,
        "correlation_id": correlation_id,
        "status": status,
        "task_frontier": frontier
        if frontier is not None
        else [_ROLE_NODE[label][1] for label in _LABELS],
        "expires_at": expires_at,
        "not_before": not_before,
    }
    if run_tag:
        rec["run_tag"] = run_tag
    return rec


def _records(
    *,
    version=1,
    plan_status="approved",
    grant_status="active",
    frontier=None,
    grant_expires=0.0,
    grant_not_before=0.0,
    packets=None,
    packet_tenant=_TENANT,
    extra_grants=(),
):
    recs = [_plan_record(version=version, status=plan_status)]
    for label in packets if packets is not None else _LABELS:
        recs.append(_packet_record(label, tenant=packet_tenant))
    recs.append(
        _grant_record(
            version=version,
            status=grant_status,
            frontier=frontier,
            expires_at=grant_expires,
            not_before=grant_not_before,
        )
    )
    recs.extend(extra_grants)
    return recs


def _binding(**kw):
    return ExecutionBinding(
        run_id=kw.pop("run_id", _RUN_ID),
        candidate_sha=kw.pop("candidate_sha", "deadbeef1234"),
        plan_record_id=kw.pop("plan_record_id", _PLAN_ID),
        plan_version=kw.pop("plan_version", 1),
        grant_id=kw.pop("grant_id", _GRANT_ID),
        decision_ref=kw.pop("decision_ref", _DECISION_REF),
        tenant_id=kw.pop("tenant_id", _TENANT),
        principal_id=kw.pop("principal_id", _PRINCIPAL),
        membership_id=kw.pop("membership_id", _MEMBERSHIP),
        conversation_id=kw.pop("conversation_id", _CONV),
        correlation_id=kw.pop("correlation_id", _CORR),
    )


def _arm(targets, variant="tools-revoked-backend"):
    (targets / ".inject_failure").write_text(variant, encoding="utf-8")


def _build(records=None, binding=None):
    return build_from_records(
        records if records is not None else _records(),
        binding=binding if binding is not None else _binding(),
    )


def _prime(targets, *, records=None, binding=None, map_payload=None):
    """Write execution_binding.json + scenario_map.json for a run (the two files
    the field pipeline captures before arming)."""
    b = binding if binding is not None else _binding()
    write_execution_binding(targets, b)
    write_scenario_map(
        targets, map_payload if map_payload is not None else _build(records=records, binding=b)
    )


def _arm_check(targets, records, **kw):
    return arming_is_valid_for_run(str(targets), records=records, **kw)


# ── happy path over REAL records + captured binding ─────────────────────────


def test_build_requires_real_packets_and_binds_exactly():
    payload = _build()
    assert payload[BACKEND] == "wp-aaaaaaaaaaaa"
    assert payload["plan_record_id"] == _PLAN_ID
    assert payload["plan_version"] == 1
    assert payload["grant_id"] == _GRANT_ID
    assert payload["execution_authorization_ref"] == _DECISION_REF
    assert payload["digest"] and payload["binding_digest"]


def test_full_chain_arms_targets_backend_first_attempt(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    _prime(targets)
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


# ── A. two unrelated ACTIVE grants — exact run binding selects the correct one


def test_A_two_unrelated_active_grants_exact_binding_selects_correct():
    other = _grant_record(
        grant_id="grant-OTHER",
        decision_ref="objective_plan:opr-OTHER:execution_authorization:v1",
        conversation_id="conv-OTHER",
        correlation_id="corr-OTHER",
        run_tag="run-OTHER",
    )
    other["plan_record_id"] = "opr-OTHER"
    recs = _records(extra_grants=[other])
    grant = resolve_canonical_grant(recs, _binding())
    assert grant["grant_id"] == _GRANT_ID


# ── B. prior pass leaves an ACTIVE grant; next pass resolves ITS OWN grant ──


def test_B_prior_pass_active_grant_does_not_shadow_this_run():
    prior = _grant_record(
        grant_id="grant-PRIOR",
        decision_ref="objective_plan:opr-PRIOR:execution_authorization:v1",
        conversation_id="conv-PRIOR",
        correlation_id="corr-PRIOR",
        run_tag="run-PRIOR",
    )
    prior["plan_record_id"] = "opr-PRIOR"
    recs = _records(extra_grants=[prior])
    # this run's binding still resolves grant-1 (both grants are ACTIVE)
    grant = resolve_canonical_grant(recs, _binding())
    assert grant["grant_id"] == _GRANT_ID


# ── C. same plan/version under another tenant cannot match ──────────────────


def test_C_same_plan_version_other_tenant_cannot_match():
    recs = _records()
    with pytest.raises(ScenarioMapError, match="need exactly 1"):
        resolve_canonical_grant(recs, _binding(tenant_id="tenant-OTHER"))


# ── D. wrong conversation_id fails ──────────────────────────────────────────


def test_D_wrong_conversation_id_fails():
    recs = _records()
    with pytest.raises(ScenarioMapError, match="need exactly 1"):
        resolve_canonical_grant(recs, _binding(conversation_id="conv-WRONG"))


# ── E. wrong correlation_id fails ───────────────────────────────────────────


def test_E_wrong_correlation_id_fails():
    recs = _records()
    with pytest.raises(ScenarioMapError, match="need exactly 1"):
        resolve_canonical_grant(recs, _binding(correlation_id="corr-WRONG"))


# ── F. wrong grant_id fails ─────────────────────────────────────────────────


def test_F_wrong_grant_id_fails():
    recs = _records()
    with pytest.raises(ScenarioMapError, match="need exactly 1"):
        resolve_canonical_grant(recs, _binding(grant_id="grant-WRONG"))


# ── G. tampered execution_authorization_ref fails at arming ────────────────


def test_G_tampered_authorization_ref_fails(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    payload = _build()
    payload["execution_authorization_ref"] = "objective_plan:opr-run-1:execution_authorization:v9"
    _prime(targets, map_payload=payload)
    _arm(targets)
    ok, reason = _arm_check(targets, _records())
    assert ok is False and "decision_ref" in reason


def test_G_tampered_grant_id_in_map_fails(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    payload = _build()
    payload["grant_id"] = "grant-TAMPERED"
    _prime(targets, map_payload=payload)
    _arm(targets)
    ok, reason = _arm_check(targets, _records())
    assert ok is False and "grant_id" in reason


# ── H. missing execution_binding.json fails ─────────────────────────────────


def test_H_missing_execution_binding_fails(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    write_scenario_map(targets, _build())  # map present, binding NOT written
    _arm(targets)
    ok, reason = _arm_check(targets, _records())
    assert ok is False and "binding" in reason.lower()


# ── I. multiple records matching the complete binding fail ─────────────────


def test_I_duplicate_exact_binding_grants_fail():
    dup = _grant_record()  # identical binding fields
    recs = _records(extra_grants=[dup])
    with pytest.raises(ScenarioMapError, match="need exactly 1"):
        resolve_canonical_grant(recs, _binding())


# ── J. expired / not-yet-valid / non-ACTIVE grant fails ────────────────────


@pytest.mark.parametrize("status", ["revoked", "invalidated", "failed_activation", "activating"])
def test_J_non_active_grant_fails(status):
    recs = _records(grant_status=status)
    with pytest.raises(ScenarioMapError, match="not ACTIVE"):
        resolve_canonical_grant(recs, _binding())


def test_J_expired_grant_fails():
    recs = _records(grant_expires=1.0)
    with pytest.raises(ScenarioMapError, match="expired"):
        resolve_canonical_grant(recs, _binding(), now=1e9)


def test_J_not_yet_valid_grant_fails():
    recs = _records(grant_not_before=1e9)
    with pytest.raises(ScenarioMapError, match="not yet valid"):
        resolve_canonical_grant(recs, _binding(), now=1.0)


# ── K. active grant bound to a draft/rejected/superseded Plan fails ────────


@pytest.mark.parametrize("plan_status", ["draft", "rejected", "cancelled", "superseded"])
def test_K_grant_bound_to_nonlive_plan_fails(plan_status):
    # superseded is caught earlier by select_plan; draft/rejected/cancelled by the
    # _PLAN_NONLIVE check. Both fail closed — accept either message.
    recs = _records(plan_status=plan_status)
    with pytest.raises(ScenarioMapError, match="not a live accepted plan|SUPERSEDED"):
        resolve_canonical_grant(recs, _binding())


# ── L. frontier packet outside the exact Plan or tenant fails ──────────────


def test_L_frontier_packet_outside_plan_fails():
    recs = _records(frontier=["wp-aaaaaaaaaaaa", "wp-not-a-packet"])
    with pytest.raises(
        ScenarioMapError, match="not a\n?.*persisted WorkPacket|persisted WorkPacket"
    ):
        resolve_canonical_grant(recs, _binding())


def test_L_frontier_packet_wrong_tenant_fails():
    # a frontier packet persisted under a DIFFERENT tenant than the grant
    recs = _records()
    for r in recs:
        if r.get("packet_id") == "wp-aaaaaaaaaaaa":
            r["tenant_id"] = "tenant-OTHER"
    with pytest.raises(ScenarioMapError, match="does not.*match grant tenant|tenant"):
        resolve_canonical_grant(recs, _binding())


# ── M. restoring global "one ACTIVE grant" selection fails the suite ───────


def test_M_no_global_singleton_grant_inference_remains():
    """Source-level: the dispatcher must NOT resolve the run's grant by 'the only
    ACTIVE grant'. The removed helper (_active_grant_binding) must not exist, and
    the binding must be captured by run identity."""
    import scripts.wave2_field_dispatch as wd

    assert not hasattr(wd, "_active_grant_binding"), (
        "global-singleton grant inference (_active_grant_binding) must be removed"
    )
    assert hasattr(wd, "_capture_execution_binding"), (
        "the run must capture its binding by journey identity"
    )


def test_M_capture_is_run_tag_scoped_not_status_only():
    """The capture helper selects the grant by THIS run's tag, so a legitimate
    ACTIVE grant from another run is not picked up."""
    import scripts.wave2_field_dispatch as wd

    this_run = _grant_record(run_tag="run-1")
    other_run = _grant_record(grant_id="grant-OTHER", run_tag="run-OTHER", conversation_id="conv-x")
    binding, err = wd._capture_execution_binding(
        [this_run, other_run], sha="deadbeef1234", run_id="run-1"
    )
    assert err == "" and binding is not None
    assert binding.grant_id == _GRANT_ID
    # a run whose tag matches NO grant fails closed
    none_binding, none_err = wd._capture_execution_binding(
        [other_run], sha="deadbeef1234", run_id="run-1"
    )
    assert none_binding is None and "need exactly 1" in none_err


# ── N. removing authorization-ref comparison or digest coverage fails ──────


def test_N_authorization_ref_comparison_is_present():
    """Source-level: validate_against_run must compare the map's
    execution_authorization_ref to the canonical grant's decision_ref AND compare
    the binding digest. Asserted on AST-unparsed CODE (docstring stripped)."""
    import ast
    import inspect

    from substrate.execution.attempts import field_scenario_map as fsm

    tree = ast.parse(inspect.getsource(fsm.validate_against_run).lstrip())
    fn = tree.body[0]
    body = fn.body[1:] if isinstance(fn.body[0], ast.Expr) else fn.body
    code = "\n".join(ast.unparse(n) for n in body)
    assert "execution_authorization_ref" in code and "decision_ref" in code, (
        "map ref must be compared to the canonical grant decision_ref"
    )
    assert "grant_id" in code, "map grant_id must be compared to the canonical grant_id"
    assert "binding_digest" in code, "the full binding digest must be checked"


def test_N_binding_digest_covers_full_authorization():
    """Mutation: altering any binding identifier changes the binding digest, so a
    map whose claimed binding was tampered no longer recomputes."""
    from substrate.execution.attempts.field_scenario_map import binding_digest

    mapping = {label: _ROLE_NODE[label][1] for label in _LABELS}
    base = binding_digest(mapping, _binding())
    for kw in (
        {"grant_id": "grant-X"},
        {"decision_ref": "objective_plan:opr:execution_authorization:v9"},
        {"conversation_id": "conv-X"},
        {"correlation_id": "corr-X"},
        {"tenant_id": "tenant-X"},
        {"plan_version": 2},
    ):
        assert binding_digest(mapping, _binding(**kw)) != base, kw


def test_N_persisted_binding_digest_is_the_real_content_digest(tmp_path):
    """A persisted map whose binding_digest was corrupted after writing (without a
    real rebuild) is caught at arming — pins that the build wires the REAL digest,
    not a constant. Guards against a build that stamps a static/empty digest."""
    targets = tmp_path / "t"
    targets.mkdir()
    payload = _build()
    payload["binding_digest"] = "0" * 64  # corrupt the claimed content digest
    _prime(targets, map_payload=payload)
    _arm(targets)
    ok, reason = _arm_check(targets, _records())
    assert ok is False and "stale" in reason.lower() and "binding_digest" in reason


# ── plan selection + frontier wrappers still fail closed ───────────────────


def test_no_plan_for_binding_id_fails_no_fallback():
    recs = _records()
    with pytest.raises(ScenarioMapError, match="matched 0 records"):
        select_plan(recs, plan_record_id="opr-run-B", plan_version=1)


def test_exact_plan_version_selection_is_unambiguous():
    recs = _records()
    other = _plan_record(version=1)
    other["plan_record_id"] = "opr-OTHER"
    recs.append(other)
    plan = select_plan(recs, plan_record_id=_PLAN_ID, plan_version=1)
    assert plan["plan_record_id"] == _PLAN_ID
    recs.append(_plan_record(version=1))
    with pytest.raises(ScenarioMapError, match="matched 2 records"):
        select_plan(recs, plan_record_id=_PLAN_ID, plan_version=1)


def test_empty_frontier_fails():
    recs = _records(frontier=[])
    with pytest.raises(ScenarioMapError, match="EMPTY task_frontier"):
        resolve_canonical_grant(recs, _binding())


def test_resolve_authorized_frontier_wraps_canonical_grant():
    recs = _records()
    frontier, why = resolve_authorized_frontier(recs, _binding())
    assert set(frontier) == {_ROLE_NODE[label][1] for label in _LABELS}
    assert "grant-1" in why


# ── build-lineage fail-open modes (retained from prior microfix) ───────────


def test_node_references_ghost_packet_with_no_record_fails():
    recs = _records(packets=["frontend_task_id", "integration_task_id", VERIFICATION])
    with pytest.raises(ScenarioMapError):
        build_from_records(recs, binding=_binding())


def test_packet_lineage_points_to_another_node_fails():
    recs = _records()
    for r in recs:
        if r.get("packet_id") == "wp-aaaaaaaaaaaa":
            r["source_evidence"] = [{"type": "plan_node", "node_id": "node-fe"}]
    with pytest.raises(ScenarioMapError):
        build_from_records(recs, binding=_binding())


def test_node_and_packet_id_disagree_fails():
    recs = _records()
    for r in recs:
        for n in r.get("nodes", []):
            if n.get("node_id") == "node-be":
                n["workpacket_id"] = "wp-mismatch1234"
    with pytest.raises(ScenarioMapError, match="disagree"):
        build_from_records(recs, binding=_binding())


def test_build_does_not_synthesize_packets_from_plan_nodes():
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


# ── staleness + run-binding (arming path, full binding) ────────────────────


def test_stale_plan_version_fails(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    # capture binding + map at v1, then present v2 live state
    _prime(targets, binding=_binding(plan_version=1))
    _arm(targets)
    recs = [_plan_record(version=2)]
    for label in _LABELS:
        recs.append(_packet_record(label))
    recs.append(_grant_record(version=2))
    ok, reason = _arm_check(targets, recs)
    # binding still says v1; canonical grant for v1 no longer present → fail closed
    assert ok is False


def test_wrong_run_binding_fails(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    payload = _build()
    payload["run_id"] = "run-OTHER"
    write_execution_binding(targets, _binding())
    write_scenario_map(targets, payload)
    _arm(targets)
    ok, reason = _arm_check(targets, _records())
    assert ok is False and "another run" in reason.lower()


def test_absent_map_fails(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    write_execution_binding(targets, _binding())  # binding present, map absent
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
    _prime(targets)
    (targets / ".inject_failure").write_text("tools-revoked-nonsense", encoding="utf-8")
    ok, reason = _arm_check(targets, _records())
    assert ok is False and "unknown" in reason.lower()


# ── task outside granted frontier cannot be targeted ───────────────────────


def test_task_outside_granted_frontier_cannot_be_targeted(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    _prime(targets)
    _arm(targets)
    # grant now authorizes only 3 of 4 tasks (backend excluded)
    recs = _records(frontier=["wp-bbbbbbbbbbbb", "wp-cccccccccccc", "wp-dddddddddddd"])
    ok, reason = _arm_check(targets, recs)
    assert ok is False and "frontier" in reason.lower()


# ── injection fires + map is identity-only ──────────────────────────────────


def test_injection_fired_detects_never_observed():
    assert injection_fired([{"disallowed_tools": []}]) is False
    assert injection_fired([{"disallowed_tools": ["Edit"]}]) is True


def test_end_to_end_fires_on_backend_first_attempt_only(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    payload = _build()
    _prime(targets, map_payload=payload)
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
        "candidate_sha",
        "plan_record_id",
        "plan_version",
        "grant_id",
        "execution_authorization_ref",
        "tenant_id",
        "conversation_id",
        "correlation_id",
        "digest",
        "binding_digest",
    }


def test_persisted_map_round_trips(tmp_path):
    targets = tmp_path / "t"
    targets.mkdir()
    payload = _build()
    write_scenario_map(targets, payload)
    got = read_scenario_map(targets)
    assert got["backend_task_id"] == payload["backend_task_id"]
    assert got["binding_digest"] == payload["binding_digest"]


def test_execution_binding_round_trips(tmp_path):
    from substrate.execution.attempts.field_scenario_map import read_execution_binding

    targets = tmp_path / "t"
    targets.mkdir()
    write_execution_binding(targets, _binding())
    got = read_execution_binding(targets)
    assert got is not None
    assert got.grant_id == _GRANT_ID and got.decision_ref == _DECISION_REF
    assert got.conversation_id == _CONV and got.correlation_id == _CORR
