"""The ONE canonical fail-closed admission authority.

Every condition that must hold before a real worker is leased, sealed and
dispatched is decided HERE, once, by ``authorize_admission``. There is exactly
one consumer (``AttemptScheduler._admit``) and it consumes this verdict
ATOMICALLY at the final admission boundary — inside the single-writer scheduler
lease, on freshly re-read state, immediately before the lease is acquired.

Why this module exists (finding R2-5, escalated to HIGH in round 3)
-------------------------------------------------------------------
``readiness.evaluate_execution_readiness`` defines 15 deterministic checks and
had **zero production callers**. The scheduler open-coded a partial subset
inline and simply never asked the rest, so bounds the OPERATOR sets on the
execution decision were decorative:

* ``grant.role_ids``      — a grant restricted to one Role placed any role;
* ``grant.allowed_tools`` — a Task demanding an unauthorized tool dispatched;
* ``grant.cost_limit_usd``— an UNENFORCEABLE monetary ceiling admitted, in
  direct violation of Amendment v1 clause 8;
* ``work_scope.target_kind``, rollback obligations, prohibited skills — all
  unchecked.

Worse, three live comments described the absence as coverage
(``lifecycle.py`` claimed ready→leased required "AUTHORIZED readiness";
``placement.py`` claimed tools were "already validated ... in readiness" above
an identity list-comprehension). That is why the hole survived every prior
review: the files a reviewer opens to check it asserted it was checked.

What is ENFORCED today vs what is CORRECT-BUT-UNDECLARED
--------------------------------------------------------
Stated here so no reader mistakes "the guard exists" for "the bound is set"
(round-7 findings R6-F1 / R6-F2, measured against the real production path).

**Enforced on every production input** — the bounded-authorization triad the
Wave 2 acceptance contract actually names, plus the structural guards:
attempt↔grant identity, frontier membership, tenant, plan record, packet
status (TOCTOU), work-scope completeness, attempt budget, environment class,
rollback guarantee, verifier distinctness, verification obligation, live
sibling, and plan supersession.

**Correct but never exercised in production** — checks 9 (``role_ids``),
11 (``allowed_tools``) and 16 (``cost_limit_usd``). Each is strict and DOES
refuse the moment its bound is declared — verified by passing the bound
through the real producer and observing ``role_not_authorized`` /
``tool_not_authorized`` / ``unenforceable_cost_ceiling``. But the sole
production caller (``objective_plan_routes.py:426``) declares none of them,
and ``apply_execution_decision`` has no parameter through which an operator
could. **There is no operator surface for these bounds; that surface is
Wave 5.** They are correct-and-waiting, NOT active controls today.

These bounds are deliberately NOT derived from the plan's own archetypes.
``grant.role_ids := union(packet.required_role_contracts)`` would be true by
construction — a tautology, and deletable-green behind check 2. A bound is a
control only when its authority is INDEPENDENT of the thing it bounds.

**Vacuous today** — check 10 (``skills_role_authorized``): no production
writer populates the role store and no seed role carries either skill list, so
both legs vacate (convergence ledger #16). Skills are advisory metadata; no
worker capability is gated on a skill name.

Design rules this module obeys
------------------------------
1. **One authority.** No caller may re-derive or partially re-interpret these
   conditions. ``_admit`` calls this and honours the verdict.
2. **Fail closed, always.** Missing, empty, or unreadable data is a REFUSAL,
   never a pass. Every predicate states its empty-case verdict explicitly.
3. **Atomic at the boundary.** Evaluated under the scheduler lock, on the
   re-read packet and the re-read grant, in the same transaction that leases
   and dispatches. No stale assessment can authorize execution.
4. **Not another earlier check.** This does not add a gate before the existing
   ones; it is the gate the existing partial ones defer to.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Statuses a canonical Task may hold and still be admissible. An ALLOWLIST:
# an unknown/empty status is refused, unlike a terminal denylist which passes
# anything it has not heard of.
ADMISSIBLE_PACKET_STATUSES = frozenset({"approved", "delegated"})

# The ONE owner of "which environment classes carry a mechanically-enforced
# rollback" (Convergence Law: one concept, one semantic owner).
#
# Wave 2 rollback is STRUCTURAL, not declarative: every lease is a disposable
# git worktree anchored to `snapshot_ref = base_commit` with
# `rollback_policy = git_reset_to_snapshot` (leases.py:72-73, :193), and
# `worker_claude_cli.py:322` fail-closes when that anchor is missing.
# Discarding the worktree IS the rollback.
#
# `isolated_worktree` (planning vocabulary, archetypes.py:87) and
# `git_worktree` (execution vocabulary, decisions.py:208) are the SAME concept
# under two names — the disjointness recorded as R6-F3. Both are named here so
# the guard is satisfied by the property, not by a coincidence of defaults.
#
# `read_only` qualifies on its own merit: a zero-write environment has nothing
# to roll back. That is the environment the independent verifier runs in.
#
# NOT included, deliberately — no mechanism guarantees their rollback today, so
# they must continue to refuse: `workspace`, `governed_runtime`.
ROLLBACK_GUARANTEED_ENVIRONMENT_CLASSES = frozenset(
    {"git_worktree", "isolated_worktree", "read_only"}
)


@dataclass
class AdmissionVerdict:
    """The single admission answer. ``admitted`` is the only field that grants."""

    admitted: bool = False
    task_id: str = ""
    attempt_id: str = ""
    decision_ref: str = ""
    refusal_code: str = ""
    reason: str = ""
    checks: list[dict[str, Any]] = field(default_factory=list)

    def failed_checks(self) -> list[str]:
        return [c["check"] for c in self.checks if not c.get("passed")]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _status_of(packet: Any) -> str:
    raw = getattr(packet, "status", None)
    return str(getattr(raw, "value", raw) or "")


def authorize_admission(
    *,
    packet: Any,
    grant: Any,
    attempt: Any,
    role_contract: Any,
    verifier_role_id: str,
    plan_lookup: Callable[[str], Any] | None = None,
    attempts_for_task: Callable[[str], list[Any]] | None = None,
) -> AdmissionVerdict:
    """Decide whether THIS attempt may be leased and dispatched. Fail closed.

    Every argument is the freshly re-read object the caller is about to act on,
    not a cached one. A refusal names the exact condition violated so the
    scheduler can park the attempt with a truthful ``blocked_reason``.
    """
    verdict = AdmissionVerdict(
        task_id=str(getattr(attempt, "task_id", "") or ""),
        attempt_id=str(getattr(attempt, "attempt_id", "") or ""),
        decision_ref=str(getattr(grant, "decision_ref", "") or ""),
    )

    def check(
        name: str, passed: bool, detail: str = "", code: str = "", note: str = ""
    ) -> bool:
        """Record one check. ``detail`` is the REFUSAL message — never shown on a pass.

        Every call site passes the message that explains a REFUSAL ("task X not
        in the authorized frontier"). Storing it unconditionally made a PASSING
        verdict state the exact opposite of what happened on 4 of 18 checks:

            PASS  task_in_authorized_frontier  task 'wp-a' not in the authorized frontier
            PASS  task_admissible_status       packet status 'approved' is not one of [...]

        This verdict IS the durable audit record for a governed execution
        decision. A campaign whose root cause is "comments asserted guarantees
        nothing provided" cannot ship an audit trail with the same property
        (round-7 review N4).

        `detail` is therefore attached ONLY to a refusal. A check that passes
        for a reason worth recording — "the operator declared no tool bound, so
        nothing was narrowed" — passes that provenance as `note`, which is
        stored only on a PASS. The two can never be confused for one another.
        """
        passed_b = bool(passed)
        row: dict[str, Any] = {"check": name, "passed": passed_b}
        if passed_b:
            if note:
                row["note"] = note
        else:
            row["detail"] = detail
        verdict.checks.append(row)
        if not passed_b and not verdict.refusal_code:
            verdict.refusal_code = code or name
            verdict.reason = detail or name
        return passed_b

    ok = True

    # ── 1. identity: the attempt belongs to THIS grant ────────────────────
    # An attempt minted under a different grant must never be admitted by the
    # pass that happens to be running (R2-1 was exactly this door).
    att_ref = str(getattr(attempt, "execution_authorization_ref", "") or "")
    grant_ref = str(getattr(grant, "decision_ref", "") or "")
    ok &= check(
        "attempt_bound_to_grant",
        bool(att_ref) and bool(grant_ref) and att_ref == grant_ref,
        f"attempt authorization {att_ref!r} vs grant {grant_ref!r}",
        "attempt_not_authorized_by_this_grant",
    )

    # ── 2. frontier membership ────────────────────────────────────────────
    frontier = {str(t) for t in (getattr(grant, "task_frontier", []) or [])}
    task_id = str(getattr(attempt, "task_id", "") or "")
    ok &= check(
        "task_in_authorized_frontier",
        bool(task_id) and task_id in frontier,
        f"task {task_id!r} not in the authorized frontier",
        "task_outside_frontier",
    )

    # ── 3. tenant binding (packet's OWN tenant vs the grant's) ────────────
    scope = _as_dict(getattr(packet, "work_scope", None))
    pkt_tenant = str(scope.get("tenant_id", "") or "")
    grant_tenant = str(getattr(grant, "tenant_id", "") or "")
    ok &= check(
        "tenant_match",
        bool(pkt_tenant) and bool(grant_tenant) and pkt_tenant == grant_tenant,
        f"packet tenant {pkt_tenant!r} vs grant tenant {grant_tenant!r}",
        "cross_tenant",
    )

    # ── 4. plan binding, INCLUDING the exact version integer ──────────────
    # Only plan_record_id was compared before; graph_version vs
    # grant.plan_version was never checked on the admission path.
    lineage = _as_dict(getattr(packet, "lineage", None))
    pkt_plan = str(lineage.get("plan_record_id", "") or "")
    grant_plan = str(getattr(grant, "plan_record_id", "") or "")
    ok &= check(
        "plan_record_match",
        bool(pkt_plan) and bool(grant_plan) and pkt_plan == grant_plan,
        f"packet plan {pkt_plan!r} vs grant plan {grant_plan!r}",
        "wrong_plan",
    )

    grant_version = getattr(grant, "plan_version", None)
    pkt_version = lineage.get("plan_version", None)
    if pkt_version is None:
        # Not every materialized packet stamps a version; when it does, it must
        # agree. An absent stamp is not treated as a mismatch, but a PRESENT
        # and DIFFERENT one is a hard refusal.
        check("plan_version_match", True, note="packet declares no plan_version (not compared)")
    else:
        ok &= check(
            "plan_version_match",
            str(pkt_version) == str(grant_version),
            f"packet plan_version {pkt_version!r} vs grant {grant_version!r}",
            "stale_plan_version",
        )

    # ── 5. packet status re-checked AT admission (TOCTOU) ─────────────────
    # The frontier loop checks this at CREATION time; a packet that goes
    # terminal between creation and admission was still leased and dispatched.
    pkt_status = _status_of(packet)
    ok &= check(
        "task_admissible_status",
        pkt_status in ADMISSIBLE_PACKET_STATUSES,
        f"packet status {pkt_status!r} is not one of {sorted(ADMISSIBLE_PACKET_STATUSES)}",
        "task_not_admissible",
    )

    # ── 6. WorkScope completeness (tenant_id AND target_kind) ─────────────
    ok &= check(
        "work_scope_complete",
        bool(scope.get("tenant_id")) and bool(scope.get("target_kind")),
        f"work_scope keys={sorted(scope)} (tenant_id and target_kind are required)",
        "incomplete_work_scope",
    )

    # ── 7. attempt budget re-checked AT admission ─────────────────────────
    max_attempts = int(getattr(grant, "max_attempts_per_task", 0) or 0)
    attempt_number = int(getattr(attempt, "attempt_number", 0) or 0)
    ok &= check(
        "attempt_budget_remaining",
        max_attempts > 0 and 0 < attempt_number <= max_attempts,
        f"attempt #{attempt_number} vs max_attempts_per_task={max_attempts}",
        "attempt_budget_exhausted",
    )

    # ── 8. role resolved AND within the grant's authorized role set ───────
    role_id = str(getattr(role_contract, "role_id", "") or "") if role_contract is not None else ""
    auth_roles = [str(r) for r in (getattr(grant, "role_ids", []) or [])]
    role_ok = bool(role_id) and (not auth_roles or role_id in auth_roles)
    ok &= check(
        "role_authorized",
        role_ok,
        f"role {role_id!r} vs authorized roles {auth_roles}",
        "role_not_authorized",
    )

    # ── 9. skills: ⊆ permitted, and disjoint from prohibited ──────────────
    reqs = _as_dict(getattr(packet, "requirements", None))
    skill_refs = list(reqs.get("required_skill_refs", []) or [])
    required_skills = [
        str(s.get("skill_id", "")) for s in skill_refs if isinstance(s, dict) and s.get("skill_id")
    ]
    permitted_skills = {str(s) for s in (getattr(role_contract, "permitted_skill_ids", []) or [])}
    prohibited_skills = {str(s) for s in (getattr(role_contract, "prohibited_skill_ids", []) or [])}
    conflicting = sorted(s for s in required_skills if s in prohibited_skills)
    # The DENYLIST always applies. The ALLOWLIST applies only when the role
    # declares one — an empty `permitted_skill_ids` means "this role does not
    # narrow skills", not "every skill is fine to skip checking".
    #
    # That distinction is stated explicitly rather than smuggled into the
    # comprehension as `if permitted_skills and ...`: production's `_RoleView`
    # had NO `permitted_skill_ids` field at all, so `getattr(..., [])` made the
    # allowlist half unreachable and a Task requiring ANY skill was admitted
    # (adversarial review F2, HIGH). The field now exists on `_RoleView`, so
    # populating it enforces instead of silently doing nothing.
    if permitted_skills:
        unauthorized = sorted(s for s in required_skills if s not in permitted_skills)
    else:
        unauthorized = []
    ok &= check(
        "skills_role_authorized",
        not conflicting and not unauthorized,
        f"required={required_skills} prohibited_hit={conflicting} "
        f"unauthorized={unauthorized} allowlist_active={bool(permitted_skills)}",
        "skill_not_authorized",
    )

    # ── 10. tools ⊆ grant.allowed_tools (the OPERATOR's bound) ────────────
    # This is the check `placement.py` claimed happened "in readiness".
    #
    # SCOPE — deliberately the GRANT bound, not role ∩ grant.
    # ``packet.required_tools`` is PLANNING vocabulary, copied verbatim from the
    # archetype's ``tool_policy`` (compiler.py:705): repository, typecheck,
    # editor, shell_gated, docker, crm, search, read, graph_query, test_runner.
    # ``RoleContract.allowed_tools`` is an INDEPENDENTLY-AUTHORED vocabulary:
    # code_edit, test_runner, deploy, web_search, document_analysis, monitor,
    # config. The two namespaces share exactly ONE token out of sixteen
    # (`test_runner`) and no mapping between them exists anywhere in the tree.
    #
    # Comparing them refused 5 of 5 real archetypes `tool_not_authorized` —
    # every packet the canonical compiler produces (adversarial review R4-3).
    # The fixture suites could not see it because they hand-build packets with
    # ``required_tools=[]``. A guard that refuses ALL legitimate work is as
    # broken as one that admits everything, so the role leg is NOT enforced
    # here. Reconciling the two vocabularies is real work with a real owner
    # (see the ledger entry) — not something to fake with a lenient predicate.
    #
    # ``grant.allowed_tools`` IS comparable: an operator narrowing execution to
    # a tool set expresses it in the Task's own vocabulary, which is what they
    # see on the decision. That bound is enforced strictly.
    #
    # The empty cases are decided EXPLICITLY. The original predicate, copied
    # from readiness.py as
    # ``t for t in pkt_tools if permitted_tools and t not in permitted_tools``,
    # VACATED whenever the permitted set was empty, so a NARROWER operator
    # bound admitted MORE (F1, R4-1 — the same inversion twice).
    pkt_tools = [str(t) for t in (getattr(packet, "required_tools", []) or [])]
    role_tools = {str(t) for t in (getattr(role_contract, "allowed_tools", []) or [])}
    auth_tools = {str(t) for t in (getattr(grant, "allowed_tools", []) or [])}

    if not pkt_tools:
        # The Task requires no tools — nothing to authorize.
        check("tools_permitted", True, note="task requires no tools")
    elif not auth_tools:
        # The operator declared no tool bound, so this check adds no narrowing.
        # Recorded explicitly (never silently skipped) so the absence is legible
        # in the verdict, and it names the role vocabulary it did NOT compare.
        check(
            "tools_permitted",
            True,
            note=(
                f"grant declares no tool bound; required={pkt_tools} "
                f"(role vocabulary {sorted(role_tools)} not comparable — see ledger #15)"
            ),
        )
    else:
        # A declared operator bound is enforced STRICTLY: every required tool
        # must appear in it. Empty never means "unrestricted" here — that case
        # is the branch above, decided on its own terms.
        tool_violations = sorted(t for t in pkt_tools if t not in auth_tools)
        ok &= check(
            "tools_permitted",
            not tool_violations,
            f"required={pkt_tools} authorized={sorted(auth_tools)} violations={tool_violations}",
            "tool_not_authorized",
        )

    # ── 11. environment class declared (empty must REFUSE, not default) ───
    env_classes = [str(e) for e in (getattr(grant, "environment_classes", []) or [])]
    ok &= check(
        "environment_class_declared",
        bool(env_classes),
        "grant declares no environment_classes",
        "no_environment_class",
    )

    # ── 12. rollback is GUARANTEED for this environment class ─────────────
    # Deliberately NOT "a rollback field is declared". Wave 2 rollback is
    # STRUCTURAL: every lease is a disposable git worktree anchored to
    # `snapshot_ref = base_commit` with `rollback_policy = git_reset_to_snapshot`
    # (leases.py:70-71, :193), and `worker_claude_cli.py:322` fail-closes when
    # that anchor is missing. Discarding the worktree IS the rollback.
    #
    # Requiring `packet.rollback_plan` / `grant.rollback_obligations` here would
    # refuse 100% of real execution: no production caller passes
    # `rollback_obligations` (decisions.py:160 defaults it to []) and the
    # compiler never stamps `rollback_plan`. A guard that refuses everything is
    # not a strict guard — it is a wrong one, and it would have been "fixed" by
    # weakening it later. So this asserts the guarantee that actually exists:
    # the environment class must be one whose rollback is mechanically
    # enforced. An UNRECOGNIZED environment class has no such guarantee and is
    # refused.
    # VOCABULARY RECONCILIATION (round-7 finding R6-F3, previously ACTIVE_DEBT).
    # Planning and execution named the SAME concept differently:
    #   archetypes.py:87  environment_class = "isolated_worktree"
    #   decisions.py:208  environment_classes default = ["git_worktree"]
    # The two sets were DISJOINT, so this guard passed only because the grant
    # producer's default happened to be the one literal the guard accepted —
    # never because an archetype agreed. Any future caller that forwarded the
    # archetype's own class (the obvious thing to do) would have been refused
    # `no_rollback_guarantee` for a rollback that IS in fact guaranteed.
    #
    # `ROLLBACK_GUARANTEED_ENVIRONMENT_CLASSES` is now the single owner of which
    # environment classes carry a mechanically-enforced rollback, and it names
    # BOTH spellings of the one worktree concept. `read_only` is included on its
    # own merit: a zero-write environment has nothing to roll back, and that is
    # the environment the independent verifier (Task D) runs in.
    #
    # `workspace` and `governed_runtime` are deliberately NOT included — no
    # mechanism guarantees their rollback today, so they must keep refusing.
    declared_rollback = bool(getattr(packet, "rollback_plan", "")) or bool(
        getattr(grant, "rollback_obligations", []) or []
    )
    structural_rollback = bool(env_classes) and all(
        e in ROLLBACK_GUARANTEED_ENVIRONMENT_CLASSES for e in env_classes
    )
    ok &= check(
        "rollback_guaranteed",
        structural_rollback or declared_rollback,
        f"env_classes={env_classes} (structural rollback: {structural_rollback}); "
        f"declared rollback: {declared_rollback}",
        "no_rollback_guarantee",
    )

    # ── 13. verifier exists and differs from the worker role ──────────────
    verifier = str(verifier_role_id or "")
    ok &= check(
        "verifier_distinct",
        bool(verifier) and bool(role_id) and verifier != role_id,
        f"verifier {verifier!r} vs worker role {role_id!r}",
        "verifier_not_distinct",
    )

    # ── 14. a verification obligation exists BEFORE quota is spent ────────
    has_validation = bool(getattr(packet, "validation_plan", "")) or bool(
        getattr(grant, "verification_obligations", []) or []
    )
    ok &= check(
        "verification_obligation_declared",
        has_validation,
        "neither packet.validation_plan nor grant.verification_obligations is set",
        "no_verification_obligation",
    )

    # ── 15. cost: a declared ceiling that cannot be enforced BLOCKS ───────
    # Amendment v1 clause 8, verbatim. Production admitted these.
    # A NEGATIVE limit is a MALFORMED ceiling, not an absent one. `<= 0.0`
    # treated it as "no ceiling declared" and admitted it unenforceable
    # (adversarial review F5). Absent is exactly 0.0; anything below is refused.
    try:
        cost_limit = float(getattr(grant, "cost_limit_usd", 0.0) or 0.0)
    except (TypeError, ValueError):
        cost_limit = float("nan")
    cost_enforceable = bool(getattr(grant, "cost_enforceable", False))
    if cost_limit != cost_limit:  # NaN — unparseable ceiling, fail closed
        cost_ok, cost_code = False, "malformed_cost_ceiling"
    elif cost_limit < 0.0:
        cost_ok, cost_code = False, "malformed_cost_ceiling"
    elif cost_limit == float("inf"):
        # An INFINITE ceiling is not a ceiling. Marking it "enforceable" would
        # otherwise satisfy the bound while bounding nothing (review R4-5).
        cost_ok, cost_code = False, "malformed_cost_ceiling"
    else:
        cost_ok, cost_code = (cost_limit == 0.0 or cost_enforceable), "unenforceable_cost_ceiling"
    ok &= check(
        "cost_bounded",
        cost_ok,
        f"cost_limit_usd={cost_limit} enforceable={cost_enforceable}",
        cost_code,
    )

    # ── 16. no sibling attempt already live for this Task ─────────────────
    # An ABSENT resolver REFUSES. A guard that silently vanishes when its
    # lookup is not supplied is the fail-open shape this module exists to
    # remove: `readiness` skipped its authorization check whenever no validator
    # was injected, and `is_authorization_valid` still skips supersession when
    # `latest_plan_lookup` is None. The scheduler always passes both; a future
    # caller that forgets gets a refusal, never an unchecked pass.
    if attempts_for_task is None:
        ok &= check(
            "no_live_sibling_attempt",
            False,
            "no attempt-ledger lookup supplied (fail closed)",
            "sibling_lookup_unavailable",
        )
    else:
        this_id = str(getattr(attempt, "attempt_id", "") or "")
        try:
            siblings = list(attempts_for_task(task_id))
        except Exception as exc:  # unreadable ledger → fail closed
            logger.debug("admission sibling lookup failed for %s: %s", task_id, exc)
            siblings = None  # type: ignore[assignment]
        if siblings is None:
            ok &= check(
                "no_live_sibling_attempt",
                False,
                "attempt ledger unreadable (fail closed)",
                "ledger_unreadable",
            )
        else:
            live = [
                a
                for a in siblings
                if str(getattr(a, "attempt_id", "")) != this_id
                and not a.is_terminal()
                and str(getattr(a, "status", "")) != "ready"
            ]
            ok &= check(
                "no_live_sibling_attempt",
                not live,
                f"live sibling attempts: {[getattr(a, 'attempt_id', '') for a in live]}",
                "duplicate_active_attempt",
            )

    # ── 17. plan still current + approved (supersession, re-asked here) ───
    # As with check 16: an ABSENT lookup REFUSES rather than skipping.
    if plan_lookup is None:
        ok &= check(
            "plan_current_and_approved",
            False,
            "no plan lookup supplied — supersession unverifiable (fail closed)",
            "plan_lookup_unavailable",
        )
    else:
        objective_id = str(getattr(grant, "objective_id", "") or "")
        latest = None
        try:
            latest = plan_lookup(objective_id)
        except Exception as exc:
            logger.debug("admission plan lookup failed for %s: %s", objective_id, exc)
            latest = None
        if latest is None:
            ok &= check(
                "plan_current_and_approved",
                False,
                f"no current plan resolvable for objective {objective_id!r}",
                "plan_unresolvable",
            )
        else:
            latest_id = str(getattr(latest, "plan_record_id", "") or "")
            latest_status = str(getattr(latest, "status", "") or "")
            ok &= check(
                "plan_current_and_approved",
                latest_id == grant_plan and latest_status == "approved",
                f"latest plan {latest_id!r} status={latest_status!r} vs grant plan {grant_plan!r}",
                "plan_superseded_or_unapproved",
            )

    verdict.admitted = bool(ok)
    if not verdict.admitted and not verdict.reason:
        verdict.reason = "admission refused"
    return verdict


__all__ = [
    "ADMISSIBLE_PACKET_STATUSES",
    "ROLLBACK_GUARANTEED_ENVIRONMENT_CLASSES",
    "AdmissionVerdict",
    "authorize_admission",
]
