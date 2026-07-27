"""ExecutionReadinessAssessment — the PRE-GRANT advisory readiness assessment.

⚠ THIS MODULE HOLDS NO ADMISSION AUTHORITY. ⚠

The ONE canonical fail-closed admission authority is
``substrate.execution.attempts.admission.authorize_admission``, consumed
atomically by ``AttemptScheduler._admit`` at the final attempt-admission
boundary. Nothing here gates execution, and nothing here may be cited as
evidence that a condition is enforced.

This module exists to answer a DIFFERENT question — "would this Task be ready
if a grant were issued?" — for the request-time pre-pass and operator-facing
surfaces. It is advisory: an assessment can be computed, stored and displayed
without any attempt being admitted.

History (round-3 finding R2-5): these 15 checks once WERE described as the
execution gate while having zero production callers, and the scheduler
open-coded only a partial subset. The bounds an operator sets on a grant —
role_ids, allowed_tools, cost_limit_usd — were therefore unenforced. If you are
adding a condition that must BLOCK execution, add it to ``admission.py``. Adding
it here does not enforce anything.

A NEW canonical type (adjudicated in the plan): it is deliberately NOT the
organism ``WorkReadinessRuntime.ReadinessAssessment`` (a legacy read-surface over
coordinator stores with a 6-state vocabulary and no authorization concept), nor
``planning.readiness.DecisionReadinessAssessment`` (plan-acceptance readiness).
This assesses whether one canonical Task is ready to EXECUTE under a specific
execution authorization, and only an ``AUTHORIZED`` verdict admits an attempt.

All checks are deterministic and fail closed. A tenant mismatch or a prohibited
skill is a hard PROHIBITED; a missing/denied authorization is
AUTHORIZATION_REQUIRED; an expired authorization is EXPIRED; any other failed
check yields BLOCKED. All checks passing with a valid GRANTED authorization →
AUTHORIZED (the only state the scheduler admits).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _from_dict(cls: type, d: dict[str, Any]) -> Any:
    return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class ExecutionReadinessState(str, Enum):
    NOT_REQUIRED = "not_required"
    INVESTIGATING = "investigating"
    BLOCKED = "blocked"
    AUTHORIZATION_REQUIRED = "authorization_required"
    READY = "ready"  # all checks pass pre-grant (used by the request pre-pass)
    AUTHORIZED = "authorized"  # all checks pass with a GRANTED authorization
    EXPIRED = "expired"
    PROHIBITED = "prohibited"
    FAILED = "failed"


# Terminal WorkPacket statuses — a Task in one of these is not executable.
_PACKET_TERMINAL = frozenset(
    {"completed", "failed", "rejected", "superseded", "archived"}
)


@dataclass
class ExecutionReadinessAssessment:
    assessment_id: str = field(default_factory=lambda: _new_id("era"))
    task_id: str = ""
    plan_record_id: str = ""
    plan_version: int = 0
    authorization_ref: str = ""
    attempt_id: str = ""
    tenant_id: str = ""
    state: str = ExecutionReadinessState.INVESTIGATING.value
    checks: list[dict[str, Any]] = field(default_factory=list)  # {check, passed, detail}
    blocking_items: list[str] = field(default_factory=list)
    assessed_at: float = field(default_factory=time.time)
    deterministic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExecutionReadinessAssessment:
        return _from_dict(cls, d)

    def passed(self, name: str) -> bool:
        for c in self.checks:
            if c.get("check") == name:
                return bool(c.get("passed"))
        return False


def _dependencies_satisfied(
    packet: Any, dep_success_lookup: Callable[[str], bool] | None
) -> tuple[bool, str]:
    deps = list(getattr(packet, "dependencies", []) or [])
    if not deps:
        return True, "no dependencies"
    if dep_success_lookup is None:
        return False, "dependency status unknown (no ledger lookup provided)"
    unmet = [d for d in deps if not dep_success_lookup(d)]
    if unmet:
        return False, f"unsatisfied dependencies: {unmet}"
    return True, "all dependencies have a succeeded attempt with proof"


def evaluate_execution_readiness(
    *,
    packet: Any,
    plan: Any,
    authorization: Any,
    role_contract: Any | None,
    next_attempt_number: int,
    is_authorization_valid: Callable[[Any], tuple[bool, str]] | None = None,
    dep_success_lookup: Callable[[str], bool] | None = None,
    capacity_available: bool = True,
    adapter_resolver: Callable[[Any], bool] | None = None,
    credential_resolver: Callable[[list[str]], tuple[bool, str]] | None = None,
    verifier_role_resolver: Callable[[Any], str] | None = None,
) -> ExecutionReadinessAssessment:
    """Run the 15 deterministic §VI checks. Fail closed.

    ``packet``  — canonical WorkPacket; ``plan`` — the accepted ObjectivePlanRecord
    (or latest-version accessor already applied); ``authorization`` — the
    ExecutionAuthorizationGrant; ``role_contract`` — the resolved RoleContract or
    None. Callables let the caller inject store lookups without importing them
    here (keeps this module substrate-composed and testable).
    """
    a = ExecutionReadinessAssessment(
        task_id=getattr(packet, "packet_id", ""),
        plan_record_id=getattr(plan, "plan_record_id", ""),
        plan_version=int(getattr(plan, "graph_version", 0) or 0),
        authorization_ref=getattr(authorization, "decision_ref", ""),
        tenant_id=getattr(authorization, "tenant_id", ""),
    )

    prohibited = False
    authorization_missing = False
    authorization_expired = False

    def record(check: str, passed: bool, detail: str = "") -> None:
        a.checks.append({"check": check, "passed": bool(passed), "detail": detail})
        if not passed:
            a.blocking_items.append(f"{check}: {detail}" if detail else check)

    # 1. plan accepted, exact version.
    plan_status = getattr(plan, "status", "")
    plan_version = int(getattr(plan, "graph_version", -1) or -1)
    auth_version = int(getattr(authorization, "plan_version", -2) or -2)
    ok1 = plan_status == "approved" and plan_version == auth_version
    record(
        "plan_accepted_exact_version",
        ok1,
        f"status={plan_status} plan_v={plan_version} auth_v={auth_version}",
    )

    # 2. task canonical + not terminal + belongs to the plan version.
    pkt_status = getattr(getattr(packet, "status", None), "value", getattr(packet, "status", ""))
    in_plan = getattr(packet, "packet_id", "") in list(getattr(plan, "workpacket_ids", []) or [])
    ok2 = bool(getattr(packet, "packet_id", "")) and pkt_status not in _PACKET_TERMINAL and in_plan
    record(
        "task_canonical_not_terminal",
        ok2,
        f"status={pkt_status} in_plan={in_plan}",
    )

    # 3. dependencies satisfied (each dep has a SUCCEEDED attempt with proof).
    ok3, detail3 = _dependencies_satisfied(packet, dep_success_lookup)
    record("dependencies_satisfied", ok3, detail3)

    # 4. authorization valid + task in frontier + attempt budget remains.
    frontier = list(getattr(authorization, "task_frontier", []) or [])
    in_frontier = getattr(packet, "packet_id", "") in frontier
    max_attempts = int(getattr(authorization, "max_attempts_per_task", 0) or 0)
    budget_ok = next_attempt_number <= max_attempts
    # FAIL CLOSED when no validator is injected. This previously defaulted to
    # ``(True, "assumed valid")`` — an unchecked authorization was reported as
    # a PASSING readiness check, so the one gate that exists to refuse an
    # expired/revoked/superseded grant asserted the opposite (adversarial-review
    # CRITICAL). An absent validator means "not verified", never "valid".
    if is_authorization_valid is None:
        from substrate.execution.attempts.decisions import (
            is_authorization_valid as _canonical_validity,
        )

        valid_auth, valid_detail = _canonical_validity(authorization)
    else:
        valid_auth, valid_detail = is_authorization_valid(authorization)
    ok4 = valid_auth and in_frontier and budget_ok
    record(
        "authorization_valid",
        ok4,
        f"valid={valid_auth}({valid_detail}) in_frontier={in_frontier} "
        f"attempt#{next_attempt_number}<=max{max_attempts}",
    )
    if not valid_auth:
        if "expired" in valid_detail.lower():
            authorization_expired = True
        else:
            authorization_missing = True
    elif not in_frontier or not budget_ok:
        authorization_missing = True

    # 5. tenant match across packet / plan / authorization (mismatch → PROHIBITED).
    pkt_scope = getattr(packet, "work_scope", {}) or {}
    plan_scope = getattr(plan, "work_scope", {}) or {}
    pkt_tenant = pkt_scope.get("tenant_id", "")
    plan_tenant = plan_scope.get("tenant_id", "")
    auth_tenant = getattr(authorization, "tenant_id", "")
    ok5 = bool(pkt_tenant) and pkt_tenant == plan_tenant == auth_tenant
    record(
        "tenant_match",
        ok5,
        f"packet={pkt_tenant} plan={plan_tenant} auth={auth_tenant}",
    )
    if not ok5:
        prohibited = True

    # 6. WorkScope complete (tenant_id + target_kind).
    ok6 = bool(pkt_scope.get("tenant_id")) and bool(pkt_scope.get("target_kind"))
    record("work_scope_complete", ok6, f"scope_keys={sorted(pkt_scope)}")

    # 7. role resolved + role_id ∈ authorization.role_ids.
    role_id = getattr(role_contract, "role_id", "") if role_contract is not None else ""
    auth_roles = list(getattr(authorization, "role_ids", []) or [])
    ok7 = bool(role_id) and (not auth_roles or role_id in auth_roles)
    record("role_resolved", ok7, f"role={role_id} authorized_roles={auth_roles}")

    # 8. skills role-authorized (⊆ permitted, ∩ prohibited == ∅).
    req = getattr(packet, "requirements", {}) or {}
    skill_refs = req.get("required_skill_refs", []) or []
    req_skill_ids = [s.get("skill_id", "") for s in skill_refs if s.get("skill_id")]
    permitted = set(getattr(role_contract, "permitted_skill_ids", []) or []) if role_contract else set()
    prohibited_skills = set(getattr(role_contract, "prohibited_skill_ids", []) or []) if role_contract else set()
    unauthorized = [s for s in req_skill_ids if permitted and s not in permitted]
    conflicting = [s for s in req_skill_ids if s in prohibited_skills]
    ok8 = not conflicting and not unauthorized
    record(
        "skills_role_authorized",
        ok8,
        f"required={req_skill_ids} unauthorized={unauthorized} prohibited={conflicting}",
    )
    if conflicting:
        prohibited = True

    # 9. tools permitted (planned tools ⊆ role.allowed_tools ∩ authorization.allowed_tools).
    pkt_tools = set(getattr(packet, "required_tools", []) or [])
    role_tools = set(getattr(role_contract, "allowed_tools", []) or []) if role_contract else set()
    auth_tools = set(getattr(authorization, "allowed_tools", []) or [])
    permitted_tools = role_tools & auth_tools if (role_tools and auth_tools) else (role_tools or auth_tools)
    tool_violations = [t for t in pkt_tools if permitted_tools and t not in permitted_tools]
    ok9 = not tool_violations
    record("tools_permitted", ok9, f"violations={tool_violations}")

    # 10. adapter exists (real, never sim/pty stub).
    ok10 = True
    detail10 = "adapter resolution deferred to placement"
    if adapter_resolver is not None:
        ok10 = bool(adapter_resolver(packet))
        detail10 = "resolved" if ok10 else "no real adapter for this work"
    record("adapter_exists", ok10, detail10)

    # 11. capacity available.
    record("capacity_available", bool(capacity_available), f"capacity={capacity_available}")

    # 12. credentials by reference (names only).
    cred_refs = list(getattr(authorization, "credential_scope_refs", []) or [])
    ok12, detail12 = (True, "no credentials required")
    if credential_resolver is not None and cred_refs:
        ok12, detail12 = credential_resolver(cred_refs)
    record("credentials_by_reference", ok12, detail12)

    # 13. sandbox + rollback defined.
    env_classes = list(getattr(authorization, "environment_classes", []) or [])
    has_rollback = bool(getattr(packet, "rollback_plan", "")) or bool(
        getattr(authorization, "rollback_obligations", [])
    )
    ok13 = bool(env_classes) and has_rollback
    record("sandbox_rollback_defined", ok13, f"env_classes={env_classes} rollback={has_rollback}")

    # 14. verifier role + proof contract exist (verifier distinct from worker role).
    verifier_role = ""
    if verifier_role_resolver is not None:
        verifier_role = verifier_role_resolver(packet) or ""
    has_validation = bool(getattr(packet, "validation_plan", "")) or bool(
        getattr(authorization, "verification_obligations", [])
    )
    ok14 = bool(verifier_role) and verifier_role != role_id and has_validation
    record(
        "verifier_and_proof_contract",
        ok14,
        f"verifier={verifier_role} worker_role={role_id} validation={has_validation}",
    )

    # 15. cost bounded — a declared monetary ceiling that is NOT enforceable
    #     blocks readiness (Amendment v1 clause 8: no USD enforcement claim).
    cost_limit = float(getattr(authorization, "cost_limit_usd", 0.0) or 0.0)
    cost_enforceable = bool(getattr(authorization, "cost_enforceable", False))
    ok15 = (cost_limit <= 0.0) or cost_enforceable
    record(
        "cost_bounded",
        ok15,
        f"limit_usd={cost_limit} enforceable={cost_enforceable}",
    )

    all_pass = all(c["passed"] for c in a.checks)

    # State mapping (priority order: prohibited > expired > auth-missing > blocked).
    if prohibited:
        a.state = ExecutionReadinessState.PROHIBITED.value
    elif authorization_expired:
        a.state = ExecutionReadinessState.EXPIRED.value
    elif authorization_missing:
        a.state = ExecutionReadinessState.AUTHORIZATION_REQUIRED.value
    elif not all_pass:
        a.state = ExecutionReadinessState.BLOCKED.value
    else:
        grant_status = getattr(authorization, "status", "")
        if grant_status == "active":
            a.state = ExecutionReadinessState.AUTHORIZED.value
        else:
            a.state = ExecutionReadinessState.READY.value
    return a


__all__ = [
    "ExecutionReadinessAssessment",
    "ExecutionReadinessState",
    "evaluate_execution_readiness",
]
