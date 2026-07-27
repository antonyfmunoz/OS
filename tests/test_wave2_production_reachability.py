"""Admission judged on inputs the REAL PRODUCERS make — not hand-built ones.

Round 6's finding, and the root cause of this whole campaign: guard mutation
killed 9/9, while mutating the production DATA SOURCE survived 6/6 across 765
tests. The most alarming survivor was changing one grant default —
`max_attempts_per_task: 2 -> 0` — which refuses EVERY attempt system-wide, a
total execution outage, with the entire suite still green.

Root cause: every admission test hand-builds its inputs, so the PRODUCER
(`resolve_archetype` -> compiler packet shape -> `request_execution_authorization`
grant defaults -> the real resolvers) and the CONSUMER (`authorize_admission`)
are tested in separate universes. A vocabulary can drift, a default can change,
a store can go unwritten — and nothing notices.

These tests close that seam. They derive admission inputs from the real
producers and assert BOTH directions:

  LIVENESS  — real work the producers emit must ADMIT (a guard that refuses
              everything is as broken as one that admits everything: R4-3)
  AUTHORITY — a bound the operator actually sets must REFUSE

Every prior round's escaped defect (R5-F1 role store, R5-F2 verifier namespace,
R5-F3 role substitution, R6-F3 environment-class disjointness, R6-F4 verifier
reachability) is caught by this shape.
"""

from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace
from typing import Any

import pytest

from substrate.contracts.work_context import WorkScope
from substrate.execution.attempts.admission import authorize_admission
from substrate.execution.attempts.field_control_plane import (
    _default_role_resolver,
    _verifier_role_resolver,
)
from substrate.execution.planning.archetypes import resolve_archetype

# One work text per archetype the resolver can select.
_WORK_TEXTS = [
    "implement the search endpoint and add tests",
    "research the competitive landscape and synthesise findings",
    "write the launch announcement copy",
    "restart the runtime and check the deployment health",
    "send the outreach sequence to the new leads",
]


def _real_archetype(work_text: str):
    scope = WorkScope(tenant_id="tenant-a", target_kind="umh_substrate")
    return resolve_archetype(work_text, scope)


def _packet_from_archetype(arch) -> SimpleNamespace:
    """A packet shaped the way `planning/compiler.py` materializes one.

    Mirrors compiler.py: `required_tools=list(archetype.tool_policy)`,
    `required_role_contracts=[archetype.default_role_contract_id]`,
    `required_skill_refs` from the archetype, `validation_plan` stamped
    unconditionally, WorkScope carrying tenant_id + target_kind, and
    `lineage.plan_record_id`.
    """
    return SimpleNamespace(
        packet_id="wp-real",
        status=SimpleNamespace(value="approved"),
        dependencies=[],
        work_scope={"tenant_id": "tenant-a", "target_kind": "umh_substrate"},
        lineage={"plan_record_id": "opr-1"},
        requirements={
            "required_skill_refs": [dict(s) for s in arch.required_skill_refs],
            "scope_declared": True,
            "writable_path_scope": ["app"],
        },
        validation_plan="verification node of the owning plan",
        required_tools=list(arch.tool_policy),
        required_role_contracts=[arch.default_role_contract_id],
        rollback_plan="",
    )


def _grant_from_production_defaults(**overrides) -> Any:
    """A grant minted by the REAL producer, `request_execution_authorization`.

    Deliberately NOT a hand-built dict of "what the defaults are". Hardcoding
    the defaults here would reproduce the exact defect these tests exist to
    catch: the producer's default could change (e.g. `max_attempts_per_task`
    to 0 — a total execution outage) and a hand-built copy would keep the suite
    green. The grant is therefore built by CALLING the producer with exactly
    what the sole production caller passes (`objective_plan_routes.py:426`
    supplies no bounds at all), and the mutation matrix proves that changing a
    producer default breaks these tests.

    `overrides` are applied AFTER minting, modelling an operator who declared
    that bound on the decision.
    """
    from substrate.execution.attempts.decisions import request_execution_authorization
    from substrate.execution.attempts.store import ExecutionAttemptStore

    tmp = tempfile.mkdtemp(prefix="prod-reach-")
    store = ExecutionAttemptStore(
        attempts_path=os.path.join(tmp, "a.jsonl"),
        grants_path=os.path.join(tmp, "g.jsonl"),
        readiness_path=os.path.join(tmp, "r.jsonl"),
        leases_path=os.path.join(tmp, "l.jsonl"),
        assignments_path=os.path.join(tmp, "asn.jsonl"),
    )
    plan = SimpleNamespace(
        plan_record_id="opr-1",
        objective_id="goal-1",
        graph_version=1,
        status="approved",
        workpacket_ids=["wp-real"],
        work_scope={"tenant_id": "tenant-a", "target_kind": "umh_substrate"},
    )

    def _runner(**kw):
        fn = kw.get("execute_fn")
        out, ok = fn() if fn else ("", True)
        return SimpleNamespace(success=ok, output=out)

    grant, _approval = request_execution_authorization(
        store,
        plan=plan,
        task_frontier=["wp-real"],
        tenant_id="tenant-a",
        principal_id="u",
        membership_id="m",
        conversation_id="conv-1",
        correlation_id="c",
        requested_by="test-operator",
        mutation_runner=_runner,
    )
    grant.status = "active"
    for key, value in overrides.items():
        setattr(grant, key, value)
    return grant


def _admit(packet, grant, *, attempt_number=1):
    role = _default_role_resolver(packet)
    attempt = SimpleNamespace(
        task_id=packet.packet_id,
        attempt_id="ea-real",
        execution_authorization_ref=grant.decision_ref,
        attempt_number=attempt_number,
    )
    return authorize_admission(
        packet=packet,
        grant=grant,
        attempt=attempt,
        role_contract=role,
        verifier_role_id=_verifier_role_resolver(packet),
        plan_lookup=lambda _o: SimpleNamespace(plan_record_id="opr-1", status="approved"),
        attempts_for_task=lambda _t: [],
    )


# ── LIVENESS: real producer output must ADMIT ──────────────────────────────


@pytest.mark.parametrize("work_text", _WORK_TEXTS)
def test_real_archetype_work_is_admitted(work_text):
    """Every archetype the resolver can select must produce admissible work.

    This is the guard that would have caught R4-3 (5/5 archetypes refused
    because two tool vocabularies were compared) and would catch any future
    vocabulary drift between a producer and admission — including the
    environment-class disjointness recorded as an open finding.
    """
    arch = _real_archetype(work_text)
    verdict = _admit(_packet_from_archetype(arch), _grant_from_production_defaults())
    assert verdict.admitted, (
        f"archetype {arch.archetype_id!r} produces work admission REFUSES "
        f"({verdict.refusal_code}: {verdict.reason}) — a guard that refuses real "
        f"work is as broken as one that admits unauthorized work"
    )


def test_the_production_attempt_budget_default_admits_a_first_attempt():
    """R6-D10: `max_attempts_per_task: 2 -> 0` is a TOTAL execution outage and
    the whole suite stayed green, because no test used the real default."""
    arch = _real_archetype(_WORK_TEXTS[0])
    packet = _packet_from_archetype(arch)
    assert _admit(packet, _grant_from_production_defaults()).admitted
    outage = _admit(packet, _grant_from_production_defaults(max_attempts_per_task=0))
    assert not outage.admitted and outage.refusal_code == "attempt_budget_exhausted"


def test_the_production_environment_class_default_carries_a_rollback_guarantee():
    """R6-F3 RESOLVED: the two vocabularies are reconciled under one owner.

    This test previously asserted the DISJOINTNESS as a standing property —
    archetypes declaring `isolated_worktree` while admission accepted only
    `git_worktree` — and said in its own failure message: *"if the vocabularies
    were reconciled, update this test and the ledger together."* Round 7 did
    reconcile them (`ROLLBACK_GUARANTEED_ENVIRONMENT_CLASSES` is now the single
    owner naming both spellings of the one worktree concept), so the assertion
    inverts: forwarding the archetype's OWN class must now ADMIT.

    It pins two things at once: the producer default still keeps work alive,
    AND the archetype value is no longer refused for a rollback that is in fact
    structurally guaranteed.
    """
    arch = _real_archetype(_WORK_TEXTS[0])
    packet = _packet_from_archetype(arch)
    assert _admit(packet, _grant_from_production_defaults()).admitted

    forwarded = _admit(
        packet,
        _grant_from_production_defaults(environment_classes=[arch.environment_class]),
    )
    assert forwarded.admitted, (
        f"the archetype's own environment_class {arch.environment_class!r} is "
        f"REFUSED ({forwarded.refusal_code}) — the R6-F3 vocabulary "
        f"disjointness has regressed"
    )

    # The reconciliation is NOT a blanket widening: a class with no rollback
    # mechanism must still refuse.
    ungoverned = _admit(
        packet, _grant_from_production_defaults(environment_classes=["workspace"])
    )
    assert not ungoverned.admitted
    assert ungoverned.refusal_code == "no_rollback_guarantee", ungoverned.refusal_code


# ── AUTHORITY: a bound the operator DOES declare must REFUSE ───────────────


def test_an_operator_declared_role_bound_refuses_a_task_outside_it():
    arch = _real_archetype(_WORK_TEXTS[0])
    verdict = _admit(
        _packet_from_archetype(arch),
        _grant_from_production_defaults(role_ids=["role-SOMETHING-ELSE"]),
    )
    assert not verdict.admitted
    assert verdict.refusal_code == "role_not_authorized", verdict.refusal_code


def test_an_operator_declared_tool_bound_refuses_a_task_outside_it():
    arch = _real_archetype(_WORK_TEXTS[0])
    verdict = _admit(
        _packet_from_archetype(arch),
        _grant_from_production_defaults(allowed_tools=["something-the-task-lacks"]),
    )
    assert not verdict.admitted
    assert verdict.refusal_code == "tool_not_authorized", verdict.refusal_code


def test_an_operator_declared_cost_ceiling_that_cannot_be_enforced_refuses():
    arch = _real_archetype(_WORK_TEXTS[0])
    verdict = _admit(
        _packet_from_archetype(arch),
        _grant_from_production_defaults(cost_limit_usd=500.0, cost_enforceable=False),
    )
    assert not verdict.admitted
    assert verdict.refusal_code == "unenforceable_cost_ceiling", verdict.refusal_code


def test_real_producer_role_and_verifier_are_distinct_for_every_archetype():
    """R5-F2 / R6-F4: the worker role and the verifier must be comparable AND
    distinct for every archetype the resolver can select. Disjoint namespaces
    made this a tautology; identical ones would make it refuse real work."""
    verifier = _verifier_role_resolver(SimpleNamespace(packet_id="wp-real"))
    for work_text in _WORK_TEXTS:
        arch = _real_archetype(work_text)
        role = _default_role_resolver(_packet_from_archetype(arch))
        assert role is not None, f"{arch.archetype_id}: role did not resolve"
        assert role.role_id != verifier, (
            f"{arch.archetype_id}: worker role equals the verifier — real work "
            f"would be refused for separation of duty"
        )


def test_an_operator_bound_equal_to_the_archetype_tools_admits():
    """Pins the PRODUCER's tool vocabulary against admission.

    An operator who authorizes exactly the tools the archetype declares must
    get admission. If the archetype's `tool_policy` drifts, this breaks — which
    is the point: a producer-side vocabulary change must not silently become an
    authorization change.
    """
    arch = _real_archetype(_WORK_TEXTS[0])
    packet = _packet_from_archetype(arch)
    verdict = _admit(packet, _grant_from_production_defaults(allowed_tools=list(arch.tool_policy)))
    assert verdict.admitted, (
        f"authorizing exactly the archetype's own tools {list(arch.tool_policy)} "
        f"was refused ({verdict.refusal_code}) — producer and admission disagree"
    )


def test_the_producers_attempt_budget_permits_at_least_one_attempt():
    """The grant's budget comes from the REAL producer, so a producer-side
    default change (2 -> 0, a total execution outage) breaks this test."""
    arch = _real_archetype(_WORK_TEXTS[0])
    grant = _grant_from_production_defaults()
    assert int(getattr(grant, "max_attempts_per_task", 0)) >= 1, (
        f"the production grant producer mints max_attempts_per_task="
        f"{getattr(grant, 'max_attempts_per_task', None)} — NO attempt can ever "
        f"be admitted; this is a total execution outage"
    )
    assert _admit(_packet_from_archetype(arch), grant).admitted


def test_the_producers_environment_class_carries_a_rollback_guarantee():
    """The grant's environment class comes from the REAL producer, so changing
    that default to a class with no structural rollback (e.g. the archetype
    vocabulary) refuses 100% of production work and breaks this test."""
    arch = _real_archetype(_WORK_TEXTS[0])
    grant = _grant_from_production_defaults()
    verdict = _admit(_packet_from_archetype(arch), grant)
    assert verdict.admitted, (
        f"the production grant producer mints environment_classes="
        f"{getattr(grant, 'environment_classes', None)}, which admission refuses "
        f"({verdict.refusal_code}) — every Task would be blocked"
    )


def test_archetype_tool_policy_reaches_the_packet_unchanged():
    """Producer→packet tool fidelity, pinned against a STABLE fact.

    `test_an_operator_bound_equal_to_the_archetype_tools_admits` derives the
    operator bound FROM the archetype, so if the archetype's vocabulary drifts
    both sides move together and the drift is invisible — the same
    "producer and consumer in one universe" defect this file exists to close,
    reproduced inside the fix.

    This asserts what must hold regardless of vocabulary: the compiler copies
    `tool_policy` onto the packet verbatim (compiler.py:705), the development
    archetype declares a NON-EMPTY policy, and every declared tool is a
    non-empty string. A drift to an empty or malformed policy would make the
    operator's tool bound silently unenforceable.
    """
    arch = _real_archetype(_WORK_TEXTS[0])
    packet = _packet_from_archetype(arch)

    assert list(packet.required_tools) == list(arch.tool_policy), (
        "the packet's required_tools diverged from the archetype's tool_policy "
        "— admission would judge tools the Task does not actually declare"
    )
    assert arch.tool_policy, (
        f"archetype {arch.archetype_id!r} declares NO tools — the operator's "
        f"`allowed_tools` bound becomes unenforceable for this work"
    )
    for tool in arch.tool_policy:
        assert isinstance(tool, str) and tool.strip(), (
            f"archetype {arch.archetype_id!r} declares a malformed tool {tool!r}"
        )

    # And the bound must be able to REFUSE: a grant authorizing a strict subset
    # of the archetype's own tools refuses the Task that needs the rest.
    if len(arch.tool_policy) > 1:
        partial = list(arch.tool_policy)[:1]
        verdict = _admit(packet, _grant_from_production_defaults(allowed_tools=partial))
        assert not verdict.admitted, (
            f"authorizing only {partial} admitted a Task requiring "
            f"{list(arch.tool_policy)} — the operator's tool bound is inert"
        )

    # NOT ASSERTED, deliberately: that the tool NAMES are any particular value.
    # Renaming a tool is a planning-vocabulary change, not an authorization
    # defect — the packet and the operator's bound are expressed in the SAME
    # vocabulary, so both move together and admission cannot (and should not)
    # detect it. A data-source mutation that renames `tool_policy` therefore
    # survives this suite BY DESIGN. The real exposure it hints at — that no
    # worker capability is gated on tool names at all — is ledger #15, not
    # something to paper over with an assertion on a literal here.


# ─────────────────────────────────────────────────────────────────────────────
# COMPILER PRODUCER PINNING (round-7 finding N1/N2)
#
# The tests above close the GRANT half of the producer→consumer seam: the grant
# is minted by calling `request_execution_authorization`, so changing a producer
# default breaks them (proven by mutation: max_attempts 2→0, env_class→docker,
# cost_limit→unenforceable each fail 10-13 tests).
#
# The PACKET half was still a hand-built mirror. `_packet_from_archetype` above
# returns a SimpleNamespace "shaped the way compiler.py materializes one" — the
# exact defect this module's own docstring condemns, applied to the other half
# of the seam. Because the mirror keeps stamping `validation_plan` and
# `role-impl-op` no matter what the real compiler does, TWO one-line compiler
# regressions passed the whole Wave 2 suite green:
#
#   M4  compiler stops stamping `validation_plan`
#       → every packet refused `verification_obligation_declared`
#       → ZERO attempts dispatch system-wide (total execution outage)
#       → 111 passed, 0 failed
#
#   M5  compiler stamps `role-verify-op` as the WORKER role
#       → worker role == verifier role
#       → refused `verifier_distinct`; and had the guard not caught it, the
#         Wave 2 "no worker verifies its own Task" contract breaks AT ITS SOURCE
#       → 111 passed, 0 failed
#
# Both were reproduced independently before these tests were written. The tests
# below drive the REAL `compose_plan_for_session` and assert the properties
# admission depends on, so a compiler regression cannot ship green.
# ─────────────────────────────────────────────────────────────────────────────


def _module_runner(**kw):
    """Governed-mutation runner for the real compiler (module scope)."""
    fn = kw.get("execute_fn")
    out = ""
    if callable(fn):
        r = fn()
        out = r[0] if isinstance(r, tuple) else r
    return SimpleNamespace(success=True, output=out)


def _grant_for_real_plan(plan: Any, frontier: list[str], tenant: str = "tenant-a") -> Any:
    """Mint a grant via the REAL producer, bound to a REAL compiled plan.

    Same producer as `_grant_from_production_defaults` and the same argument
    list the sole production caller passes — but bound to the plan the compiler
    actually produced, so both halves of the seam are production-derived.
    """
    from substrate.execution.attempts.decisions import request_execution_authorization
    from substrate.execution.attempts.store import ExecutionAttemptStore

    tmp = tempfile.mkdtemp(prefix="prod-reach-plan-")
    store = ExecutionAttemptStore(
        attempts_path=os.path.join(tmp, "a.jsonl"),
        grants_path=os.path.join(tmp, "g.jsonl"),
        readiness_path=os.path.join(tmp, "r.jsonl"),
        leases_path=os.path.join(tmp, "l.jsonl"),
        assignments_path=os.path.join(tmp, "asn.jsonl"),
    )
    grant, _approval = request_execution_authorization(
        store,
        plan=plan,
        task_frontier=list(frontier),
        tenant_id=tenant,
        principal_id="u",
        membership_id="m",
        conversation_id="conv-1",
        correlation_id="c",
        requested_by="cockpit_chat_operator",
        mutation_runner=_module_runner,
    )
    grant.status = "active"
    return grant


def _real_compiler_packets(tmp_dir: str, tenant: str = "tenant-a"):
    """Drive the REAL compiler → real persisted WorkPackets. No mirrors."""
    from substrate.execution.planning.compiler import compose_plan_for_session
    from substrate.execution.planning.records import (
        GroundingSnapshot,
        ObjectiveLane,
        PlanningSession,
    )
    from substrate.execution.planning.store import PlanningStore
    from substrate.organism.universal_work_queue import UniversalWorkQueue

    store = PlanningStore(
        sessions_path=os.path.join(tmp_dir, "sessions.jsonl"),
        plans_path=os.path.join(tmp_dir, "plans.jsonl"),
        grounding_path=os.path.join(tmp_dir, "grounding.jsonl"),
        current_path=os.path.join(tmp_dir, "current.jsonl"),
        desired_path=os.path.join(tmp_dir, "desired.jsonl"),
        gaps_path=os.path.join(tmp_dir, "gaps.jsonl"),
    )
    queue = UniversalWorkQueue(store_path=os.path.join(tmp_dir, "packets.jsonl"))
    lanes = [
        ObjectiveLane(
            lane_key="backend",
            title="backend search endpoint",
            writable_path_scope=["app/main.py"],
        ),
        ObjectiveLane(
            lane_key="frontend",
            title="frontend search box",
            writable_path_scope=["app/static"],
        ),
        ObjectiveLane(
            lane_key="integration",
            title="integrate and verify",
            writable_path_scope=["app/main.py"],
            depends_on=["backend", "frontend"],
        ),
        ObjectiveLane(
            lane_key="verify",
            title="independent verification",
            writable_path_scope=[],
            depends_on=["integration"],
        ),
    ]
    plan = compose_plan_for_session(
        session=PlanningSession(
            objective_id=f"goal-{tenant}",
            objective_text="Add note search: backend + frontend, integrated and verified.",
            conversation_id=f"conv-{tenant}",
        ),
        scope=WorkScope(tenant_id=tenant, target_kind="self_build"),
        planning_scale="task_objective",
        snapshot=GroundingSnapshot(intent_id="int-pin"),
        store=store,
        work_queue=queue,
        mutation_runner=_module_runner,
        writable_path_scope=["app"],
        lanes=lanes,
    )
    packets = [queue.get_packet(pid) for pid in plan.workpacket_ids]
    return plan, [p for p in packets if p is not None], store


def test_compiler_stamps_a_verification_obligation_on_every_packet():
    """PRODUCER PIN: the compiler must stamp `validation_plan`.

    Admission check 15 refuses a packet with neither `validation_plan` nor a
    grant verification obligation, and no production caller sets the grant side.
    So `validation_plan` is the ONLY thing standing between the fleet and a
    total execution outage. Mutation M4 (compiler stops stamping it) previously
    passed 111/111 green.
    """
    tmp = tempfile.mkdtemp(prefix="pin-validation-")
    _plan, packets, _store = _real_compiler_packets(tmp)
    assert packets, "the real compiler produced no packets"
    for pkt in packets:
        assert str(getattr(pkt, "validation_plan", "") or "").strip(), (
            f"packet {getattr(pkt, 'packet_id', '')} carries no validation_plan — "
            "admission check 15 will refuse EVERY attempt (execution outage)"
        )


def test_compiler_never_stamps_the_verifier_role_as_the_worker_role():
    """PRODUCER PIN: worker role must differ from the resolved verifier role.

    This is the Wave 2 "no worker verifies its own Task" contract at its
    SOURCE. Admission check 14 catches a collision, but mutation M5 (compiler
    stamps `role-verify-op` as the worker role) previously passed 111/111 green
    — the suite could not see the producer break the contract.
    """
    tmp = tempfile.mkdtemp(prefix="pin-verifier-")
    _plan, packets, _store = _real_compiler_packets(tmp)
    assert packets, "the real compiler produced no packets"
    for pkt in packets:
        worker_role = _default_role_resolver(pkt)
        worker_role_id = str(getattr(worker_role, "role_id", "") or "")
        verifier_role_id = str(_verifier_role_resolver(pkt) or "")
        assert worker_role_id, (
            f"packet {getattr(pkt, 'packet_id', '')} resolves to no worker role"
        )
        assert verifier_role_id, "no verifier role resolves"
        assert worker_role_id != verifier_role_id, (
            f"packet {getattr(pkt, 'packet_id', '')} names the VERIFIER role "
            f"{verifier_role_id!r} as its worker role — separation of duty is "
            "broken at the producer"
        )


def test_compiler_stamps_the_scope_and_lineage_admission_binds_on():
    """PRODUCER PIN: work_scope and lineage carry what checks 3/4/7 compare.

    Checks 3 (tenant_match), 4 (plan_record_match) and 7 (work_scope_complete)
    are the genuinely-enforced core of bounded authorization. Each compares a
    field the compiler stamps; if the compiler stops stamping one, the check
    refuses everything (outage) rather than admitting wrongly — still a
    production break the suite must see.
    """
    tmp = tempfile.mkdtemp(prefix="pin-scope-")
    plan, packets, planning_store = _real_compiler_packets(tmp)
    assert packets, "the real compiler produced no packets"
    for pkt in packets:
        scope = dict(getattr(pkt, "work_scope", {}) or {})
        lineage = dict(getattr(pkt, "lineage", {}) or {})
        assert scope.get("tenant_id"), f"packet {pkt.packet_id} lost work_scope.tenant_id"
        assert scope.get("target_kind"), f"packet {pkt.packet_id} lost work_scope.target_kind"
        assert lineage.get("plan_record_id") == plan.plan_record_id, (
            f"packet {pkt.packet_id} lineage.plan_record_id "
            f"{lineage.get('plan_record_id')!r} != plan {plan.plan_record_id!r}"
        )


def test_real_compiler_packets_admit_under_a_real_grant():
    """LIVENESS end-to-end: real compiler + real grant producer ⇒ ADMIT.

    The strongest form of the liveness assertion: neither side of the seam is
    hand-built. A guard that refuses what the real producers jointly emit is as
    broken as one that admits everything (R4-3 refused 5/5 real archetypes).
    """
    tmp = tempfile.mkdtemp(prefix="pin-live-")
    plan, packets, planning_store = _real_compiler_packets(tmp)
    assert packets, "the real compiler produced no packets"

    frontier = [p.packet_id for p in packets]

    # Accept the plan through the REAL decision authority first — the producer
    # correctly refuses to authorize execution for an unaccepted plan, which is
    # the Wave 1 invariant "plan acceptance is a separate decision".
    from substrate.execution.planning.decisions import apply_plan_decision

    plan = apply_plan_decision(
        planning_store,
        plan.plan_record_id,
        "approve",
        decided_by="operator",
        mutation_runner=_module_runner,
    )

    # Mint via the REAL producer, bound to the REAL accepted plan.
    grant = _grant_for_real_plan(plan, frontier)

    admitted_any = False
    for pkt in packets:
        pkt.status = SimpleNamespace(value="approved")
        attempt = SimpleNamespace(
            attempt_id=f"ea-{pkt.packet_id}",
            task_id=pkt.packet_id,
            attempt_number=1,
            execution_authorization_ref=grant.decision_ref,
        )
        verdict = authorize_admission(
            packet=pkt,
            grant=grant,
            attempt=attempt,
            role_contract=_default_role_resolver(pkt),
            verifier_role_id=_verifier_role_resolver(pkt),
            plan_lookup=lambda _oid: SimpleNamespace(
                plan_record_id=plan.plan_record_id,
                status=str(getattr(plan.status, "value", plan.status)),
            ),
            attempts_for_task=lambda _t: [],
        )
        failed = [c["check"] for c in verdict.checks if not c["passed"]]
        assert not failed, (
            f"real compiler packet {pkt.packet_id} REFUSED by {failed} — a guard "
            "that refuses real production work is as broken as one that admits "
            "everything"
        )
        admitted_any = True
    assert admitted_any


# ─────────────────────────────────────────────────────────────────────────────
# GRANT-PRODUCER PASS-THROUGH PINNING (round-7 finding D5/D11/D12)
#
# The bound tests above apply operator bounds as POST-MINT overrides
# (`_grant_from_production_defaults(role_ids=[...])` sets the attribute after
# `request_execution_authorization` returns). That proves admission ENFORCES a
# bound, but it cannot see the PRODUCER silently DISCARD one — the grant object
# is overwritten either way.
#
# Independently reproduced producer mutations that survived every suite:
#
#   D12 `request_execution_authorization` drops the operator's `role_ids`
#       -> admission admits a role the operator explicitly excluded
#       -> a bound the operator SET is unenforced, 270 tests green
#
#   D11 compiler stops stamping `required_tools`
#       -> check 10 goes vacuous for ALL real work; an unauthorized-tool bound
#          stops refusing
#
#   D5  grant default `ttl_seconds: 3600.0 -> 0.0`
#       -> every grant expires at mint; total authorization outage. The oracle
#          (`is_authorization_valid`) AGREES the grant is dead — it just was
#          never asserted.
#
# These tests pass the bounds THROUGH the producer and assert they survive the
# round trip, and pin the mint-time validity window.
# ─────────────────────────────────────────────────────────────────────────────


def _mint_with_bounds(**producer_kwargs) -> Any:
    """Mint a grant passing bounds THROUGH the real producer (not after it)."""
    from substrate.execution.attempts.decisions import request_execution_authorization
    from substrate.execution.attempts.store import ExecutionAttemptStore

    tmp = tempfile.mkdtemp(prefix="prod-reach-bounds-")
    store = ExecutionAttemptStore(
        attempts_path=os.path.join(tmp, "a.jsonl"),
        grants_path=os.path.join(tmp, "g.jsonl"),
        readiness_path=os.path.join(tmp, "r.jsonl"),
        leases_path=os.path.join(tmp, "l.jsonl"),
        assignments_path=os.path.join(tmp, "asn.jsonl"),
    )
    plan = SimpleNamespace(
        plan_record_id="opr-1",
        objective_id="goal-1",
        graph_version=1,
        status="approved",
        workpacket_ids=["wp-real"],
        work_scope={"tenant_id": "tenant-a", "target_kind": "umh_substrate"},
    )
    grant, _approval = request_execution_authorization(
        store,
        plan=plan,
        task_frontier=["wp-real"],
        tenant_id="tenant-a",
        principal_id="u",
        membership_id="m",
        conversation_id="conv-1",
        correlation_id="c",
        requested_by="cockpit_chat_operator",
        mutation_runner=_module_runner,
        **producer_kwargs,
    )
    grant.status = "active"
    return grant


def test_producer_preserves_the_operator_role_bound():
    """D12: a `role_ids` bound passed to the producer must reach the grant AND refuse.

    Asserted end-to-end (producer round-trip THEN admission), so a producer that
    silently discards the bound is caught even though admission is unchanged.
    """
    grant = _mint_with_bounds(role_ids=["role-research-op"])
    assert list(getattr(grant, "role_ids", [])) == ["role-research-op"], (
        "the producer DISCARDED the operator's role_ids bound — a bound the "
        "operator set would be silently unenforced"
    )
    arch = _real_archetype(_WORK_TEXTS[0])  # development -> role-impl-op
    verdict = _admit(_packet_from_archetype(arch), grant)
    assert not verdict.admitted and verdict.refusal_code == "role_not_authorized", (
        f"a role outside the operator's declared bound must REFUSE, got "
        f"admitted={verdict.admitted} code={verdict.refusal_code}"
    )


def test_producer_preserves_the_operator_tool_bound():
    """D12 sibling: an `allowed_tools` bound must survive the producer AND refuse."""
    grant = _mint_with_bounds(allowed_tools=["repository"])
    assert list(getattr(grant, "allowed_tools", [])) == ["repository"], (
        "the producer DISCARDED the operator's allowed_tools bound"
    )
    arch = _real_archetype(_WORK_TEXTS[0])
    packet = _packet_from_archetype(arch)
    # The development archetype requires more than `repository`.
    assert set(packet.required_tools) - {"repository"}, "archetype tool policy too narrow to test"
    verdict = _admit(packet, grant)
    assert not verdict.admitted and verdict.refusal_code == "tool_not_authorized", (
        f"tools outside the operator's declared bound must REFUSE, got "
        f"admitted={verdict.admitted} code={verdict.refusal_code}"
    )


def test_compiler_stamps_the_tools_the_operator_bound_is_compared_against():
    """D11: packets must carry `required_tools`, or check 10 is vacuous for all work.

    If the compiler stops stamping tools, `pkt_tools` is empty, admission takes
    the "task requires no tools" branch, and an operator tool bound stops
    refusing anything — silently.
    """
    tmp = tempfile.mkdtemp(prefix="pin-tools-")
    _plan, packets, _store = _real_compiler_packets(tmp)
    assert packets, "the real compiler produced no packets"
    for pkt in packets:
        assert list(getattr(pkt, "required_tools", []) or []), (
            f"packet {pkt.packet_id} carries no required_tools — admission "
            "check 10 becomes vacuous for ALL real work"
        )


def test_the_production_grant_ttl_is_a_live_window():
    """D5: the default TTL must yield a grant that is valid now and expires later.

    `ttl_seconds: 3600.0 -> 0.0` makes every grant expire at mint — a total
    authorization outage — and every suite stayed green. `is_authorization_valid`
    already knows; nothing asserted it.
    """
    import time as _time

    from substrate.execution.attempts.decisions import is_authorization_valid

    grant = _mint_with_bounds()
    now = _time.time()
    valid, reason = is_authorization_valid(grant, now=now)
    assert valid, f"a freshly minted grant must be valid at mint time ({reason})"
    assert float(getattr(grant, "expires_at", 0.0)) > now, (
        "the grant's expiry window is not in the future — every grant expires at "
        "mint (total authorization outage)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# R6-F3 — the environment-class vocabularies are RECONCILED (was ACTIVE_DEBT)
#
# Planning and execution named one concept two ways:
#   archetypes.py:87  environment_class = "isolated_worktree"
#   decisions.py:208  environment_classes default = ["git_worktree"]
# The sets were DISJOINT, so check 12 passed only because the grant producer's
# default happened to be the single literal the guard accepted — never because
# an archetype agreed. Any caller forwarding the archetype's own class (the
# obvious thing to do) would have been refused for a rollback that IS in fact
# guaranteed.
# ─────────────────────────────────────────────────────────────────────────────


def test_every_archetype_environment_class_is_adjudicated():
    """No archetype env class may be silently unknown to admission.

    Each must be either rollback-guaranteed (admits) or deliberately excluded
    (refuses) — never accidentally absent from the vocabulary.
    """
    from substrate.execution.attempts.admission import (
        ROLLBACK_GUARANTEED_ENVIRONMENT_CLASSES,
    )

    guaranteed, ungoverned = set(), set()
    for work_text in _WORK_TEXTS:
        arch = _real_archetype(work_text)
        env = str(getattr(arch, "environment_class", "") or "")
        assert env, f"archetype {arch.archetype_id!r} declares no environment_class"
        (guaranteed if env in ROLLBACK_GUARANTEED_ENVIRONMENT_CLASSES else ungoverned).add(env)

    # The worktree concept must be reconciled under BOTH spellings.
    assert "isolated_worktree" in ROLLBACK_GUARANTEED_ENVIRONMENT_CLASSES, (
        "the planning spelling of the git-worktree lease is not recognised — "
        "the R6-F3 disjointness has regressed"
    )
    assert "git_worktree" in ROLLBACK_GUARANTEED_ENVIRONMENT_CLASSES
    assert guaranteed, "no archetype maps to a rollback-guaranteed environment"

    # Classes with no rollback mechanism must NOT have been swept in.
    assert "workspace" not in ROLLBACK_GUARANTEED_ENVIRONMENT_CLASSES
    assert "governed_runtime" not in ROLLBACK_GUARANTEED_ENVIRONMENT_CLASSES


@pytest.mark.parametrize(
    ("env_class", "should_admit"),
    [
        ("git_worktree", True),        # execution vocabulary
        ("isolated_worktree", True),   # planning vocabulary — same concept
        ("read_only", True),           # zero-write: nothing to roll back
        ("workspace", False),          # no rollback mechanism
        ("governed_runtime", False),   # no rollback mechanism
        ("docker", False),             # unrecognised
    ],
)
def test_rollback_guarantee_is_decided_by_the_property_not_a_default(
    env_class, should_admit
):
    """Admission must judge the environment class on its rollback guarantee.

    Parametrized over BOTH vocabularies so neither side can drift again without
    a failure, and over ungoverned classes so the reconciliation cannot be
    mistaken for a blanket widening.
    """
    arch = _real_archetype(_WORK_TEXTS[0])
    grant = _grant_from_production_defaults(environment_classes=[env_class])
    verdict = _admit(_packet_from_archetype(arch), grant)
    if should_admit:
        assert verdict.admitted, (
            f"env class {env_class!r} carries a guaranteed rollback but was "
            f"REFUSED ({verdict.refusal_code})"
        )
    else:
        assert not verdict.admitted and verdict.refusal_code == "no_rollback_guarantee", (
            f"env class {env_class!r} has no rollback mechanism and must REFUSE, "
            f"got admitted={verdict.admitted} code={verdict.refusal_code}"
        )


def test_a_mixed_environment_set_refuses_unless_every_class_is_guaranteed():
    """One ungoverned class in the set must refuse the whole grant."""
    arch = _real_archetype(_WORK_TEXTS[0])
    grant = _grant_from_production_defaults(
        environment_classes=["isolated_worktree", "workspace"]
    )
    verdict = _admit(_packet_from_archetype(arch), grant)
    assert not verdict.admitted and verdict.refusal_code == "no_rollback_guarantee"


# ─────────────────────────────────────────────────────────────────────────────
# R6-F1 / R6-F2 — the RECLASSIFICATION is pinned, in both directions
#
# These checks are CORRECT-BUT-UNDECLARED: strict, and they DO refuse the moment
# a bound is declared — but the sole production caller declares none, and
# `apply_execution_decision` has no parameter through which an operator could.
# That surface is Wave 5.
#
# Deliberately NOT "fixed" by deriving the bound from the plan's own archetypes:
# `grant.role_ids := union(packet.required_role_contracts)` is true BY
# CONSTRUCTION — a tautology, and deletable-green behind check 2
# (`task_in_authorized_frontier`). That would manufacture fake reachability
# rather than a control. A bound is a control only when its authority is
# INDEPENDENT of the thing it bounds.
#
# These tests pin BOTH halves so the classification cannot rot:
#   (a) the ENFORCEMENT half really works (bound declared -> refusal), and
#   (b) the DECLARATION half is genuinely absent in production.
# If (b) ever starts passing a bound, the reclassification must be revisited —
# the test says so and fails.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("producer_kwargs", "expected_code"),
    [
        ({"role_ids": ["role-research-op"]}, "role_not_authorized"),
        ({"allowed_tools": ["repository"]}, "tool_not_authorized"),
        ({"cost_limit_usd": 25.0}, "unenforceable_cost_ceiling"),
    ],
)
def test_undeclared_bounds_do_enforce_once_declared(producer_kwargs, expected_code):
    """(a) ENFORCEMENT half: a bound passed THROUGH the real producer refuses.

    This is what makes R6-F1 a Wave 5 gap rather than a broken guard. The
    bound goes through `request_execution_authorization`, not a post-mint
    override, so a producer that discarded it would fail here too.
    """
    grant = _mint_with_bounds(**producer_kwargs)
    arch = _real_archetype(_WORK_TEXTS[0])  # development: role-impl-op, 3 tools
    verdict = _admit(_packet_from_archetype(arch), grant)
    assert not verdict.admitted, (
        f"a declared bound {producer_kwargs} must REFUSE work outside it"
    )
    assert verdict.refusal_code == expected_code, verdict.refusal_code


def test_the_production_caller_still_declares_no_operator_bound():
    """(b) DECLARATION half: production genuinely sets none of these bounds.

    Parsed from the AST of the sole production call site, not asserted and not
    regex-matched over source text. The moment an operator surface ships and
    starts passing a bound, this test FAILS — which is the intended signal to
    revisit the R6-F1 reclassification (MEDIUM / RESERVED_FUTURE / Wave 5)
    rather than letting a stale classification persist.

    An earlier version of this test regex-matched the call body with a
    12-space-indent terminator while the real call closes at 16 spaces. It
    over-captured 776 characters past the call — the `except` block, the
    `metadata[...]` assignments and the whole `_respond(...)` block — so it
    could have fired on unrelated text, and it substring-matched rather than
    argument-matched, so `**kwargs` forwarding would have slipped through
    (round-7 independent adjudication, defect D). The AST walk below inspects
    the actual keyword arguments of the actual call.
    """
    import ast
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    path = root / "transports" / "api" / "objective_plan_routes.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "request_execution_authorization"
    ]
    assert len(calls) == 1, (
        f"expected exactly ONE production grant-minting call site, found "
        f"{len(calls)} — the 'sole producer' premise of the R6-F1 "
        f"classification no longer holds"
    )
    call = calls[0]

    declared = {kw.arg for kw in call.keywords if kw.arg is not None}
    bounds = {"role_ids", "allowed_tools", "cost_limit_usd", "cost_enforceable"}
    leaked = sorted(declared & bounds)
    assert not leaked, (
        f"the production caller now declares {leaked} — an operator bound "
        "surface has shipped. Revisit the R6-F1 reclassification: these checks "
        "are no longer 'correct but undeclared', they are LIVE controls and "
        "must be covered as such."
    )

    # `**kwargs` forwarding would smuggle a bound past a keyword-name check.
    assert not any(kw.arg is None for kw in call.keywords), (
        "the production call now forwards **kwargs — a bound could be passed "
        "without appearing as a keyword. The AST check can no longer prove the "
        "bounds are undeclared; verify by executing the producer."
    )


def test_grant_bounds_are_not_derived_from_the_plans_own_packets():
    """The anti-tautology pin.

    If a future change derives `role_ids` from the plan's own packets, check 9
    becomes true by construction and stops being a control. This asserts the
    production grant does NOT carry such a derived bound — the honest empty
    default is preferable to a bound that can never refuse.
    """
    grant = _grant_from_production_defaults()
    assert list(getattr(grant, "role_ids", [])) == [], (
        "grant.role_ids is populated on the default production path — if this "
        "was derived from the plan's own packets it is a TAUTOLOGY (check 9 can "
        "never refuse) and fake reachability, not a control"
    )
    assert list(getattr(grant, "allowed_tools", [])) == [], (
        "grant.allowed_tools is populated by default — same tautology risk"
    )


def test_every_documented_check_number_matches_the_code():
    """M-4: documentation check numbers must agree with the code's own numbering.

    The admission docstring once numbered the checks 9/11/16/10 while the inline
    `── N.` section comments numbered those same checks 8/10/15/9. The
    correction fixed the docstring but left two stale numbers in convergence
    ledger row #18 — including the very number the commit set out to fix, later
    in the same row — plus a reference to a "check 18" that does not exist
    (the module has 17). Found by round-8 independent review.

    This module's whole premise is that a comment must never misdescribe the
    code it documents. That standard applies to the ledger too, so the numbering
    is pinned mechanically rather than by proofreading.
    """
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[1]
    admission = (root / "substrate" / "execution" / "attempts" / "admission.py").read_text()

    # Ground truth: the inline `── N. <name>` section comments.
    inline = re.findall(r"^    # ── (\d+)\. (.+?)\s*─*$", admission, re.M)
    numbers = {int(n) for n, _ in inline}
    assert numbers, "no inline check sections found — the anchor format changed"
    highest = max(numbers)
    assert numbers == set(range(1, highest + 1)), (
        f"inline check numbering is not contiguous 1..{highest}: {sorted(numbers)}"
    )

    # No document may reference a check number the module does not have.
    ledger = (root / "docs" / "cockpit-surface-convergence.md").read_text()

    def _cited_numbers(text: str) -> set[int]:
        """Every check number a document cites.

        Two earlier versions of this gate were defeated by their own target
        defect. The first matched only the number immediately after `check(s)`,
        so `checks 3, 4 and 18` cited three numbers but only 3 was inspected.
        The second consumed list continuations but broke on an interrupting
        parenthetical — `checks 3 (tenant), 4 (...) and 18` — which is exactly
        the shape the real ledger row uses.

        Regex-walking prose is the wrong instrument. Instead: take a WINDOW of
        text after each `check(s)` anchor and inspect EVERY bare integer in it,
        stopping at a sentence end. Over-inspecting is safe here (a false
        positive is a number > 17 that a human must justify); under-inspecting
        is what let the defect back in twice.
        """
        cited: set[int] = set()
        for match in re.finditer(r"\bcheck(?:s)?\b", text):
            window = text[match.end() : match.end() + 160]
            window = re.split(r"(?<=[.;])\s|\n\n|\| ", window)[0]
            cited.update(int(n) for n in re.findall(r"(?<![\w-])(\d{1,3})(?![\w-]|\.\d)", window))
        return cited

    for source_name, text in (("admission.py", admission), ("ledger", ledger)):
        for cited_num in sorted(_cited_numbers(text)):
            assert cited_num <= highest, (
                f"{source_name} cites check {cited_num}, but admission.py has only "
                f"{highest} checks — a stale number from an earlier numbering"
            )

    # HOLE (b), and the harder half: an IN-RANGE stale number passes any range
    # check. "making check 9 a tautology" cites 9, which is <= 17 and therefore
    # numerically valid — but 9 is `skills_role_authorized`, while the tautology
    # argument is about `role_ids` = check 8. That is the ORIGINAL M-4 defect,
    # and a range check structurally cannot see it (round-8 review N-2).
    #
    # Catching it requires binding the number to the CONCERN named beside it.
    # Where prose cites a check number AND names a check in the same breath —
    # `check 8 (``role_ids``)`, "check 9 (`skills_role_authorized`)" — the
    # number must match that check's inline section.
    concern_tokens = {
        "role_ids": 8,
        "skills_role_authorized": 9,
        "allowed_tools": 10,
        "cost_limit_usd": 15,
        "rollback_guaranteed": 12,
    }
    for source_name, text in (("admission.py", admission), ("ledger", ledger)):
        for match in re.finditer(
            r"check(?:s)?\s+(\d{1,3})\s*\(+`*([a-z_]+)`*\)+", text
        ):
            num, token = int(match.group(1)), match.group(2)
            if token in concern_tokens:
                assert num == concern_tokens[token], (
                    f"{source_name} cites check {num} for {token!r}, but {token!r} "
                    f"is check {concern_tokens[token]} — an IN-RANGE stale number, "
                    "the exact M-4 defect a range check cannot detect"
                )

    # KNOWN LIMITATION, stated rather than papered over (round-8 review N-2b).
    #
    # A bare in-range stale number that names NO concern beside it — e.g.
    # "making check 9 a tautology", where the tautology is really about check 8
    # — is NOT mechanically detectable here. Nothing in the text ties that "9"
    # to a concern, so neither the range check (9 <= 17) nor the name<->number
    # binding above can fire. Detecting it would require understanding the
    # PROSE, not the number.
    #
    # This gate therefore catches: out-of-range numbers anywhere (including in
    # list continuations, after interrupting parentheticals, and at sentence
    # end), and in-range numbers cited beside a named concern. It does NOT
    # catch a bare in-range number whose surrounding argument is about a
    # different check. That residual case is a review responsibility, and it is
    # written down here so no one mistakes a green gate for full coverage —
    # which is the failure mode this whole campaign exists to eliminate.

    # The four checks the R6-F1/R6-F2 classification names must map to the right
    # concerns, so a renumbering cannot silently repoint the argument.
    by_number = {int(n): name for n, name in inline}
    expected = {
        8: "role",       # grant.role_ids
        9: "skills",     # skills_role_authorized
        10: "tools",     # grant.allowed_tools
        15: "cost",      # cost_limit_usd
    }
    for num, token in expected.items():
        assert num in by_number, f"check {num} no longer exists"
        assert token in by_number[num].lower(), (
            f"check {num} is now {by_number[num]!r}, not the {token!r} check the "
            "R6-F1/R6-F2 classification and ledger rows #16/#18 refer to"
        )
