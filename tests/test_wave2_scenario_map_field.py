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
_OBJECTIVE = "goal-run-1"
_TENANT = "tenant-a"
_GRANT_ID = "grant-1"
_DECISION_REF = f"objective_plan:{_PLAN_ID}:execution_authorization:v1"
_CONV = "conv-1"
_RUN_ID = "run-1"
# The collector stamps w2-<run_id> as the journey correlation. The grant's
# canonical correlation_id must equal this for capture to resolve it.
_CORR = f"w2-{_RUN_ID}"
_PRINCIPAL = "prin-1"
_MEMBERSHIP = "mem-1"

_ROLE_NODE = {
    BACKEND: ("node-be", "wp-aaaaaaaaaaaa"),
    "frontend_task_id": ("node-fe", "wp-bbbbbbbbbbbb"),
    "integration_task_id": ("node-int", "wp-cccccccccccc"),
    VERIFICATION: ("node-ver", "wp-dddddddddddd"),
}
_LABELS = (BACKEND, "frontend_task_id", "integration_task_id", VERIFICATION)


# ── realistic candidate records: plan + 4 WorkPackets + 1 ACTIVE grant ──────
def _plan_record(*, version=1, status="approved", objective_id=_OBJECTIVE):
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
        "objective_id": objective_id,
        "graph_version": version,
        "status": status,
        "objective_text": "add note search",
        "workpacket_ids": [_ROLE_NODE[label][1] for label in _LABELS],
        "nodes": nodes,
    }


def _packet_record(
    label,
    *,
    tenant=_TENANT,
    plan_record_id=_PLAN_ID,
    objective_id=_OBJECTIVE,
    work_scope=None,
    lineage=None,
    top_level_tenant=False,
):
    """A REAL persisted WorkPacket record with FIRST-CLASS work_scope + lineage.

    WorkPacket has no canonical top-level tenant_id — ownership lives at
    work_scope.tenant_id and lineage.plan_record_id/objective_id. ``top_level_tenant``
    lets a test forge a fake top-level tenant_id to prove it is NOT honored.
    """
    node_id, packet_id = _ROLE_NODE[label]
    rec = {
        "packet_id": packet_id,
        "source_evidence": [{"type": "plan_node", "node_id": node_id}],
        "title": FIXTURE_NODE_TITLES[label],
        "work_scope": {"tenant_id": tenant} if work_scope is None else work_scope,
        "lineage": (
            {"plan_record_id": plan_record_id, "objective_id": objective_id}
            if lineage is None
            else lineage
        ),
    }
    if top_level_tenant:
        rec["tenant_id"] = tenant
    return rec


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
):
    return {
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
        correlation_id="w2-run-OTHER",
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
        correlation_id="w2-run-PRIOR",
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


# ── K. plan status is an ALLOWLIST — exactly APPROVED, never a denylist ────


def test_K_approved_plan_passes():
    grant = resolve_canonical_grant(_records(plan_status="approved"), _binding())
    assert grant["grant_id"] == _GRANT_ID


@pytest.mark.parametrize(
    "plan_status",
    ["awaiting_approval", "draft", "rejected", "cancelled", "superseded", "", "bogus_status"],
)
def test_K_non_approved_plan_status_fails(plan_status):
    # superseded is caught earlier by select_plan; everything else — including
    # awaiting_approval, empty, and unknown — by the APPROVED allowlist. All fail.
    recs = _records(plan_status=plan_status)
    with pytest.raises(ScenarioMapError, match="not an APPROVED|SUPERSEDED"):
        resolve_canonical_grant(recs, _binding())


def test_K_status_check_is_allowlist_not_denylist():
    """Source-level: the plan-status check compares == APPROVED (allowlist), and no
    residual _PLAN_NONLIVE denylist frozenset survives."""
    import ast
    import inspect

    from substrate.execution.attempts import field_scenario_map as fsm

    tree = ast.parse(inspect.getsource(fsm.resolve_canonical_grant).lstrip())
    fn = tree.body[0]
    body = fn.body[1:] if isinstance(fn.body[0], ast.Expr) else fn.body
    code = "\n".join(ast.unparse(n) for n in body)
    assert "_PLAN_APPROVED" in code and "!=" in code, "must be an == APPROVED allowlist"
    assert "_PLAN_NONLIVE" not in code, "the denylist must be gone"
    assert not hasattr(fsm, "_PLAN_NONLIVE"), "the denylist frozenset must be removed"


# ── L. frontier packet outside the exact Plan or tenant fails ──────────────


def test_L_frontier_packet_outside_plan_fails():
    recs = _records(frontier=["wp-aaaaaaaaaaaa", "wp-not-a-packet"])
    with pytest.raises(
        ScenarioMapError, match="persisted canonical WorkPacket|persisted WorkPacket"
    ):
        resolve_canonical_grant(recs, _binding())


# ── M. removed global-singleton inference; capture is correlation-scoped ───


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


def test_M_capture_is_exact_correlation_scoped():
    """The capture helper selects the grant by THIS run's EXACT correlation_id
    (w2-<run_id>), so a legitimate ACTIVE grant from another run is not picked up,
    and a non-canonical run_tag/base-tag is NOT a selection path."""
    import scripts.wave2_field_dispatch as wd

    this_run = _grant_record(correlation_id="w2-run-1")
    other_run = _grant_record(
        grant_id="grant-OTHER", correlation_id="w2-run-OTHER", conversation_id="conv-x"
    )
    binding, err = wd._capture_execution_binding(
        [this_run, other_run], sha="deadbeef1234", run_id="run-1"
    )
    assert err == "" and binding is not None
    assert binding.grant_id == _GRANT_ID and binding.correlation_id == "w2-run-1"
    # a run whose correlation matches NO grant fails closed
    none_binding, none_err = wd._capture_execution_binding(
        [other_run], sha="deadbeef1234", run_id="run-1"
    )
    assert none_binding is None and "need exactly 1" in none_err


def test_M_capture_rejects_run_tag_and_base_tag_selection():
    """A grant that carries only a non-canonical run_tag (or matches only the base
    tag before -p) is NOT selected — run_tag is not part of the grant identity
    contract, and there is no base-pass fallback."""
    import scripts.wave2_field_dispatch as wd

    # grant carries run_tag but the WRONG correlation → must not be selected
    tag_only = _grant_record(correlation_id="w2-somethingelse")
    tag_only["run_tag"] = "20260724T0000Z-p1"
    b, err = wd._capture_execution_binding([tag_only], sha="sha", run_id="20260724T0000Z-p1")
    assert b is None and "need exactly 1" in err

    # a grant correlated to the BASE tag (no -pN) must not satisfy a -p1 run
    base = _grant_record(correlation_id="w2-20260724T0000Z")
    b2, err2 = wd._capture_execution_binding([base], sha="sha", run_id="20260724T0000Z-p1")
    assert b2 is None and "need exactly 1" in err2


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


# ═══════════════════════════════════════════════════════════════════════════
# C-3 CLOSURE CORRECTION — resolve_canonical_grant IS the single authority for
# map creation, and packet ownership is validated through FIRST-CLASS contracts.
# (Owner mutation letters A–N.)
# ═══════════════════════════════════════════════════════════════════════════


def test_corr_A_map_creation_calls_resolve_canonical_grant():
    """A. Source-level: build_from_records must invoke resolve_canonical_grant
    BEFORE producing any payload. Asserted on AST-unparsed CODE (docstring
    stripped) so removing the call fails the suite."""
    import ast
    import inspect

    from substrate.execution.attempts import field_scenario_map as fsm

    tree = ast.parse(inspect.getsource(fsm.build_from_records).lstrip())
    fn = tree.body[0]
    body = fn.body[1:] if isinstance(fn.body[0], ast.Expr) else fn.body
    code = "\n".join(ast.unparse(n) for n in body)
    assert "resolve_canonical_grant(records, binding" in code, (
        "map creation must reach the same resolve_canonical_grant as arming"
    )


def test_corr_B_expired_grant_cannot_write_scenario_map(tmp_path):
    """B. An expired grant cannot even PRODUCE scenario_map.json — map creation
    fails closed, not merely later arming."""
    recs = _records(grant_expires=1.0)
    with pytest.raises(ScenarioMapError, match="expired"):
        build_from_records(recs, binding=_binding(), now=1e9)


def test_corr_C_not_yet_valid_grant_cannot_write_scenario_map(tmp_path):
    """C. A not-yet-valid grant cannot PRODUCE scenario_map.json."""
    recs = _records(grant_not_before=1e9)
    with pytest.raises(ScenarioMapError, match="not yet valid"):
        build_from_records(recs, binding=_binding(), now=1.0)


def test_corr_D_empty_work_scope_tenant_fails():
    """D. Empty work_scope.tenant_id fails closed — no permissive empty allowance.
    Caught by the materialization-set validator (it checks every declared packet's
    first-class tenant) OR the frontier-ownership validator — both fail closed."""
    recs = _records()
    for r in recs:
        if r.get("packet_id") == "wp-aaaaaaaaaaaa":
            r["work_scope"] = {"tenant_id": ""}
    with pytest.raises(ScenarioMapError, match="tenant"):
        resolve_canonical_grant(recs, _binding())


def test_corr_E_fake_top_level_tenant_is_not_honored():
    """E. A packet whose tenant is only at a fake top-level tenant_id (no
    work_scope.tenant_id) fails — the top-level field is never read as authority."""
    recs = [_plan_record()]
    for label in _LABELS:
        # forge top-level tenant, blank the first-class scope tenant
        p = _packet_record(label, work_scope={"tenant_id": ""}, top_level_tenant=True)
        recs.append(p)
    recs.append(_grant_record())
    with pytest.raises(ScenarioMapError, match="tenant"):
        resolve_canonical_grant(recs, _binding())


def test_corr_F_missing_lineage_fails():
    """F. Missing/empty lineage fails closed — caught by the materialization-set
    validator (empty lineage → empty lineage.plan_record_id) or frontier ownership."""
    recs = _records()
    for r in recs:
        if r.get("packet_id") == "wp-aaaaaaaaaaaa":
            r["lineage"] = {}
    with pytest.raises(ScenarioMapError, match="lineage|no lineage"):
        resolve_canonical_grant(recs, _binding())


def test_corr_G_wrong_lineage_plan_record_id_fails():
    """G. Wrong lineage.plan_record_id fails closed."""
    recs = _records()
    for r in recs:
        if r.get("packet_id") == "wp-aaaaaaaaaaaa":
            r["lineage"] = {"plan_record_id": "opr-OTHER", "objective_id": _OBJECTIVE}
    with pytest.raises(ScenarioMapError, match="lineage.plan_record_id"):
        resolve_canonical_grant(recs, _binding())


def test_corr_H_wrong_lineage_objective_id_fails():
    """H. Wrong lineage.objective_id fails closed."""
    recs = _records()
    for r in recs:
        if r.get("packet_id") == "wp-aaaaaaaaaaaa":
            r["lineage"] = {"plan_record_id": _PLAN_ID, "objective_id": "goal-OTHER"}
    with pytest.raises(ScenarioMapError, match="lineage.objective_id"):
        resolve_canonical_grant(recs, _binding())


def test_corr_I_frontier_packet_absent_from_plan_workpacket_ids_fails():
    """I. A frontier packet not in the Plan's materialized workpacket_ids fails."""
    recs = _records()
    for r in recs:
        if _is_plan_record_dict(r):
            r["workpacket_ids"] = [_ROLE_NODE[label][1] for label in _LABELS if label != BACKEND]
    with pytest.raises(ScenarioMapError, match="materialized\n?.*WorkPacket set|WorkPacket set"):
        resolve_canonical_grant(recs, _binding())


def test_corr_J_frontier_packet_without_node_correspondence_fails():
    """J. A frontier packet whose source_evidence names no plan node fails."""
    recs = _records()
    for r in recs:
        if r.get("packet_id") == "wp-aaaaaaaaaaaa":
            r["source_evidence"] = []
    with pytest.raises(ScenarioMapError, match="names no plan node|no plan node"):
        resolve_canonical_grant(recs, _binding())


def test_corr_K_packet_node_workpacket_id_disagreement_fails():
    """K. Packet/node workpacket_id disagreement fails closed."""
    recs = _records()
    for r in recs:
        for n in r.get("nodes", []):
            if n.get("node_id") == "node-be":
                n["workpacket_id"] = "wp-different0001"
    with pytest.raises(ScenarioMapError, match="disagree"):
        resolve_canonical_grant(recs, _binding())


def test_corr_L_restoring_empty_tenant_compatibility_fails():
    """L. Restoring an empty-tenant "compatibility allowance" fails: a packet whose
    work_scope.tenant_id is empty must NOT be treated as matching."""
    recs = _records()
    for r in recs:
        if r.get("packet_id") == "wp-bbbbbbbbbbbb":
            r["work_scope"] = {"tenant_id": ""}
    with pytest.raises(ScenarioMapError, match="tenant"):
        resolve_canonical_grant(recs, _binding())


def test_corr_N_exact_correlation_with_unrelated_active_grants_is_green():
    """N. Exact correlation with unrelated ACTIVE grants present remains green —
    the correct grant is selected and a full map is produced."""
    other = _grant_record(
        grant_id="grant-OTHER", correlation_id="w2-run-OTHER", conversation_id="conv-x"
    )
    other["plan_record_id"] = "opr-OTHER"
    recs = _records(extra_grants=[other])
    payload = build_from_records(recs, binding=_binding())
    assert payload[BACKEND] == "wp-aaaaaaaaaaaa"
    assert payload["grant_id"] == _GRANT_ID


def _is_plan_record_dict(rec):
    return bool(rec.get("plan_record_id")) and "nodes" in rec


# ═══════════════════════════════════════════════════════════════════════════
# FINAL FAIL-CLOSED MICROFIX — nonempty materialized Task set + nonempty
# canonical objective identity. (Owner: sections 2 & 3.)
# ═══════════════════════════════════════════════════════════════════════════


def _set_plan(recs, **plan_kw):
    """Replace the plan record in ``recs`` with one mutated by ``plan_kw``."""
    out = []
    for r in recs:
        if _is_plan_record_dict(r):
            r = {**r, **plan_kw}
        out.append(r)
    return out


# ── section 2: nonempty exact Plan workpacket set ──────────────────────────


def test_mat_missing_workpacket_ids_fails():
    recs = _records()
    for r in recs:
        if _is_plan_record_dict(r):
            del r["workpacket_ids"]
    with pytest.raises(ScenarioMapError, match="no workpacket_ids list"):
        resolve_canonical_grant(recs, _binding())


def test_mat_workpacket_ids_none_fails():
    recs = _set_plan(_records(), workpacket_ids=None)
    with pytest.raises(ScenarioMapError, match="no workpacket_ids list"):
        resolve_canonical_grant(recs, _binding())


def test_mat_empty_workpacket_ids_fails():
    recs = _set_plan(_records(), workpacket_ids=[])
    with pytest.raises(ScenarioMapError, match="EMPTY workpacket_ids"):
        resolve_canonical_grant(recs, _binding())


def test_mat_empty_id_in_set_fails():
    ids = [_ROLE_NODE[label][1] for label in _LABELS] + [""]
    recs = _set_plan(_records(), workpacket_ids=ids)
    with pytest.raises(ScenarioMapError, match="empty id"):
        resolve_canonical_grant(recs, _binding())


def test_mat_duplicate_workpacket_ids_fails():
    ids = [_ROLE_NODE[label][1] for label in _LABELS] + ["wp-aaaaaaaaaaaa"]
    recs = _set_plan(_records(), workpacket_ids=ids)
    with pytest.raises(ScenarioMapError, match="duplicates"):
        resolve_canonical_grant(recs, _binding())


def test_mat_frontier_packet_absent_from_nonempty_set_fails():
    # A nonempty set that omits a frontier id — the frontier packet is absent.
    recs = _set_plan(
        _records(),
        workpacket_ids=[_ROLE_NODE[label][1] for label in _LABELS if label != BACKEND],
    )
    with pytest.raises(
        ScenarioMapError, match="materialized\n?.*WorkPacket|WorkPacket set|persisted canonical"
    ):
        resolve_canonical_grant(recs, _binding())


def test_mat_exact_nonempty_set_passes():
    grant = resolve_canonical_grant(_records(), _binding())
    assert grant["grant_id"] == _GRANT_ID


def test_mat_no_node_inferred_fallback():
    """Source-level: the materialization set comes from workpacket_ids, never
    inferred from nodes as a fallback."""
    import ast
    import inspect

    from substrate.execution.attempts import field_scenario_map as fsm

    tree = ast.parse(inspect.getsource(fsm._validate_plan_materialization_set).lstrip())
    fn = tree.body[0]
    body = fn.body[1:] if isinstance(fn.body[0], ast.Expr) else fn.body
    code = "\n".join(ast.unparse(n) for n in body)
    assert "workpacket_ids" in code
    assert "nodes" not in code, "the materialization set must not be inferred from nodes"


def test_mat_restoring_conditional_check_fails():
    """Mutation guard: the old `if plan_packet_ids and tid not in ...` (fail-open
    when the set is empty/absent) must not return. The frontier check is now
    UNCONDITIONAL. Asserted at source level."""
    import ast
    import inspect

    from substrate.execution.attempts import field_scenario_map as fsm

    tree = ast.parse(inspect.getsource(fsm._validate_frontier_packet_ownership).lstrip())
    fn = tree.body[0]
    body = fn.body[1:] if isinstance(fn.body[0], ast.Expr) else fn.body
    code = "\n".join(ast.unparse(n) for n in body)
    assert "if plan_packet_ids and" not in code, (
        "the conditional (fail-open) materialization check must be removed"
    )
    assert "if tid not in plan_packet_ids" in code, "the frontier check must be unconditional"


# ═══════════════════════════════════════════════════════════════════════════
# IDENTITY-CARDINALITY MICROFIX — no last-write-wins packet authority. A packet
# id that resolves to >1 persisted record is canonical identity ambiguity and
# fails closed (both byte-identical and conflicting duplicates). (Owner A–H.)
# ═══════════════════════════════════════════════════════════════════════════


def _dup_packet(label, *, conflict=False):
    """A second persisted record for the same packet_id — identical, or (conflict)
    payload-divergent (different tenant/lineage) to prove BOTH cases fail."""
    node_id, packet_id = _ROLE_NODE[label]
    if conflict:
        return {
            "packet_id": packet_id,
            "source_evidence": [{"type": "plan_node", "node_id": node_id}],
            "title": FIXTURE_NODE_TITLES[label],
            "work_scope": {"tenant_id": "tenant-CONFLICT"},
            "lineage": {"plan_record_id": "opr-CONFLICT", "objective_id": "goal-CONFLICT"},
        }
    return _packet_record(label)  # byte-identical to the canonical record


def test_card_A_one_record_per_declared_id_passes():
    """A. Exactly one persisted record for every declared id passes."""
    grant = resolve_canonical_grant(_records(), _binding())
    assert grant["grant_id"] == _GRANT_ID


def test_card_B_zero_records_fails():
    """B. A declared id with zero persisted records fails closed."""
    recs = _records(packets=["frontend_task_id", "integration_task_id", VERIFICATION])
    # backend declared in workpacket_ids but no persisted record
    with pytest.raises(ScenarioMapError, match="no persisted canonical WorkPacket"):
        resolve_canonical_grant(recs, _binding())


def test_card_C_two_identical_records_fail():
    """C. Two byte-identical records with the same packet_id fail — a duplicate
    current-truth identity is corruption even when payloads match."""
    recs = _records()
    recs.append(_dup_packet(BACKEND, conflict=False))
    with pytest.raises(ScenarioMapError, match="canonical identity ambiguity|resolves to 2"):
        resolve_canonical_grant(recs, _binding())


def test_card_D_two_conflicting_records_fail():
    """D. Two conflicting records with the same packet_id fail."""
    recs = _records()
    recs.append(_dup_packet(BACKEND, conflict=True))
    with pytest.raises(ScenarioMapError, match="canonical identity ambiguity|resolves to 2"):
        resolve_canonical_grant(recs, _binding())


def test_card_E_reversing_conflicting_duplicate_order_same_rejection():
    """E. Reversing the duplicate rows produces the SAME rejection — order-invariant,
    never last-write-wins."""
    base = _records()
    dup = _dup_packet(BACKEND, conflict=True)
    forward = [*base, dup]
    reversed_recs = [dup, *base]
    for recs in (forward, reversed_recs):
        with pytest.raises(ScenarioMapError, match="canonical identity ambiguity|resolves to 2"):
            resolve_canonical_grant(recs, _binding())


def test_card_F_duplicate_of_non_frontier_plan_declared_packet_fails():
    """F. A duplicate of a Plan-declared packet that is NOT in the frontier still
    fails — the materialization set proves cardinality for every declared id."""
    # frontier authorizes only backend; verification is Plan-declared but not in frontier
    recs = _records(frontier=["wp-aaaaaaaaaaaa"])
    recs.append(_dup_packet(VERIFICATION, conflict=False))
    with pytest.raises(ScenarioMapError, match="canonical identity ambiguity|resolves to 2"):
        resolve_canonical_grant(recs, _binding())


def test_card_G_unrelated_duplicate_outside_plan_and_frontier_does_not_block():
    """G. A duplicate of an id OUTSIDE the exact Plan and frontier does not block —
    the cardinality check is bounded to the identities this run trusts."""
    recs = _records()
    # two records for an unrelated id never referenced by this Plan/frontier
    unrelated = {
        "packet_id": "wp-unrelated9999",
        "source_evidence": [],
        "work_scope": {"tenant_id": "tenant-a"},
        "lineage": {"plan_record_id": "opr-elsewhere", "objective_id": "goal-elsewhere"},
    }
    recs.append(unrelated)
    recs.append({**unrelated})
    grant = resolve_canonical_grant(recs, _binding())
    assert grant["grant_id"] == _GRANT_ID


def test_card_H_no_lossy_packet_id_dict_comprehension_in_authority_path():
    """H. Source/AST guard: the lossy {packet_id: packet} comprehension must NOT
    appear in the C-3 authority path (resolve_canonical_grant); packet indexing
    goes through the cardinality-preserving _index_packet_records."""
    import ast
    import inspect

    from substrate.execution.attempts import field_scenario_map as fsm

    for func in (fsm.resolve_canonical_grant, fsm._validate_plan_materialization_set):
        tree = ast.parse(inspect.getsource(func).lstrip())
        fn = tree.body[0]
        body = fn.body[1:] if isinstance(fn.body[0], ast.Expr) else fn.body
        code = "\n".join(ast.unparse(n) for n in body)
        # a dict comprehension keyed on packet_id mapping to the packet is the lossy form
        assert "for p in _canonical_packets(records)}" not in code, (
            f"{func.__name__} must not build a lossy packet_id→packet dict"
        )
        assert "packets_by_id" not in code, (
            f"{func.__name__} must not use the lossy packets_by_id index"
        )
    # the authority path must reach the cardinality-preserving index + exact-one rule
    rcg = ast.unparse(ast.parse(inspect.getsource(fsm.resolve_canonical_grant).lstrip()))
    assert "_index_packet_records" in rcg
    assert "_exactly_one_packet" in rcg


# ── section 3: nonempty canonical objective identity ───────────────────────


def test_obj_empty_plan_objective_id_fails():
    recs = _set_plan(_records(), objective_id="")
    with pytest.raises(ScenarioMapError, match="objective correspondence is unproven|objective"):
        resolve_canonical_grant(recs, _binding())


def test_obj_empty_packet_lineage_objective_id_fails():
    recs = _records()
    for r in recs:
        if r.get("packet_id") == "wp-aaaaaaaaaaaa":
            r["lineage"] = {"plan_record_id": _PLAN_ID, "objective_id": ""}
    with pytest.raises(ScenarioMapError, match="objective correspondence is unproven"):
        resolve_canonical_grant(recs, _binding())


def test_obj_both_empty_objective_id_still_fails():
    # plan.objective_id="" AND packet lineage.objective_id="" — equality of two
    # empty strings must NEVER be valid correspondence.
    recs = _set_plan(_records(), objective_id="")
    for r in recs:
        if r.get("packet_id") == "wp-aaaaaaaaaaaa":
            r["lineage"] = {"plan_record_id": _PLAN_ID, "objective_id": ""}
    with pytest.raises(ScenarioMapError, match="objective correspondence is unproven"):
        resolve_canonical_grant(recs, _binding())


def test_obj_empty_plan_record_id_both_sides_fails():
    # A packet with empty lineage.plan_record_id must not match — even against an
    # empty grant plan (which cannot happen for a resolved grant, but the guard is
    # explicit): equality of two empty strings is never correspondence.
    recs = _records()
    for r in recs:
        if r.get("packet_id") == "wp-aaaaaaaaaaaa":
            r["lineage"] = {"plan_record_id": "", "objective_id": _OBJECTIVE}
    with pytest.raises(
        ScenarioMapError, match="plan correspondence is unproven|lineage.plan_record_id"
    ):
        resolve_canonical_grant(recs, _binding())


def test_obj_valid_exact_objective_identity_passes():
    grant = resolve_canonical_grant(_records(), _binding())
    assert grant["grant_id"] == _GRANT_ID


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
