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
    """R6-F3: archetypes declare `isolated_worktree`/`read_only`/`workspace`/
    `governed_runtime`; admission's rollback set is `{git_worktree}` — an EMPTY
    intersection. It is inert only because the compiler does not thread the
    archetype value through. This pins the default that keeps work alive, so
    wiring the archetype through cannot silently refuse 100% of production."""
    arch = _real_archetype(_WORK_TEXTS[0])
    packet = _packet_from_archetype(arch)
    assert _admit(packet, _grant_from_production_defaults()).admitted
    drifted = _admit(
        packet,
        _grant_from_production_defaults(environment_classes=[arch.environment_class]),
    )
    assert not drifted.admitted, (
        "the archetype's own environment_class now admits — if the vocabularies "
        "were reconciled, update this test and the ledger together"
    )
    assert drifted.refusal_code == "no_rollback_guarantee", drifted.refusal_code


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
