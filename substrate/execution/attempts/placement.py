"""Deterministic placement — the durable execution assignment record.

Placement answers "who/what/where executes this Task, and why" and persists the
answer. The pipeline is deterministic (directive §VII):

    Task requirements → responsible RoleContract → versioned Skill requirements
    → eligible workers → model/harness/tool profile → compute node → environment
    class → verifier Role → ranked assignment + alternatives + rejection reasons.

Same requirements + same observed availability ⇒ the same placement (stable
sorts, zero randomness, zero time-based scoring). AgentType is a worker/harness
CAPABILITY CLASS, never the organizational Role — the Role comes from the
packet's RoleContract; the worker's AgentType is one compatibility signal.

The record is durable (persisted via a governed mutation) so an attempt's
placement is reconstructable and attributable after the fact.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _from_dict(cls: type, d: dict[str, Any]) -> Any:
    return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class PlacementError(RuntimeError):
    """Raised when no eligible worker/role/verifier can be placed (fail closed)."""


@dataclass
class ExecutionAssignment:
    """The one durable canonical placement record for an attempt."""

    assignment_id: str = field(default_factory=lambda: _new_id("exasn"))
    task_id: str = ""
    attempt_id: str = ""
    tenant_id: str = ""
    # Role is the organizational owner (from the packet's RoleContract).
    role_contract_id: str = ""
    skill_requirement_refs: list[dict[str, Any]] = field(default_factory=list)
    # Worker is the qualified runtime identity; agent_type is a capability class.
    worker_identity: str = ""
    worker_agent_type: str = ""
    model_profile: dict[str, Any] = field(default_factory=dict)
    harness_profile: dict[str, Any] = field(default_factory=dict)
    tool_profile: list[str] = field(default_factory=list)
    compute_node_id: str = ""
    environment_class: str = "git_worktree"
    verifier_role_id: str = ""
    # Attribution: why this, and why not the alternatives.
    deterministic_scores: dict[str, float] = field(default_factory=dict)
    alternatives: list[str] = field(default_factory=list)
    rejection_reasons: dict[str, str] = field(default_factory=dict)
    rationale: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExecutionAssignment:
        return _from_dict(cls, d)


def _rank_workers(
    candidates: list[dict[str, Any]],
    required_capabilities: list[str],
) -> tuple[list[tuple[str, float]], dict[str, str]]:
    """Deterministic capability-overlap ranking. Returns (ranked, rejections)."""
    ranked: list[tuple[str, float]] = []
    rejections: dict[str, str] = {}
    for cand in candidates:
        cid = cand.get("worker_identity") or cand.get("agent_type", "")
        caps = set(cand.get("capabilities", []) or [])
        if required_capabilities and not (set(required_capabilities) & caps):
            rejections[cid] = "no required-capability overlap"
            continue
        overlap = (
            len(set(required_capabilities) & caps) / len(required_capabilities)
            if required_capabilities
            else 1.0
        )
        reliability = float(cand.get("reliability", 0.5))
        score = round(overlap * 0.6 + reliability * 0.4, 6)
        ranked.append((cid, score))
    # Stable sort: score desc, then id asc (no randomness, no time).
    ranked.sort(key=lambda t: (-t[1], t[0]))
    return ranked, rejections


def place_attempt(
    *,
    packet: Any,
    grant: Any,
    role_contract: Any,
    attempt_id: str,
    worker_candidates: list[dict[str, Any]],
    compute_nodes: list[dict[str, Any]],
    verifier_role_id: str,
    model_profile: dict[str, Any] | None = None,
    harness_profile: dict[str, Any] | None = None,
    store: Any | None = None,
    mutation_runner: Callable[..., Any] | None = None,
    persist: bool = True,
) -> ExecutionAssignment:
    """Produce (and optionally persist) the durable placement for one attempt.

    Fail closed: an empty worker ranking, a missing role, or a verifier equal to
    the worker role raises PlacementError.
    """
    role_id = getattr(role_contract, "role_id", "") if role_contract is not None else ""
    if not role_id:
        raise PlacementError(f"no RoleContract resolved for task {getattr(packet, 'packet_id', '')}")
    if verifier_role_id and verifier_role_id == role_id:
        raise PlacementError(
            f"verifier role {verifier_role_id!r} must differ from the worker role {role_id!r} "
            f"(separation of duty)"
        )

    req = getattr(packet, "requirements", {}) or {}
    skill_refs = list(req.get("required_skill_refs", []) or [])
    required_capabilities = list(req.get("required_capability_ids", []) or [])
    tool_profile = [
        t
        for t in (getattr(packet, "required_tools", []) or [])
        # tools already validated against role ∩ authorization in readiness.
    ]

    ranked, rejections = _rank_workers(worker_candidates, required_capabilities)
    if not ranked:
        raise PlacementError(
            f"no eligible worker for task {getattr(packet, 'packet_id', '')} "
            f"(rejections: {rejections})"
        )
    winner_id, winner_score = ranked[0]
    winner = next(
        (c for c in worker_candidates if (c.get("worker_identity") or c.get("agent_type")) == winner_id),
        {},
    )

    # Compute node: stable sort by (headroom desc, node_id asc).
    nodes_sorted = sorted(
        compute_nodes,
        key=lambda n: (-int(n.get("headroom", 0)), str(n.get("node_id", ""))),
    )
    node = nodes_sorted[0] if nodes_sorted else {}

    env_classes = list(getattr(grant, "environment_classes", []) or ["git_worktree"])

    assignment = ExecutionAssignment(
        task_id=getattr(packet, "packet_id", ""),
        attempt_id=attempt_id,
        tenant_id=getattr(grant, "tenant_id", ""),
        role_contract_id=role_id,
        skill_requirement_refs=skill_refs,
        worker_identity=winner.get("worker_identity", winner_id),
        worker_agent_type=winner.get("agent_type", ""),
        model_profile=dict(model_profile or winner.get("model_profile", {})),
        harness_profile=dict(harness_profile or winner.get("harness_profile", {})),
        tool_profile=tool_profile,
        compute_node_id=str(node.get("node_id", "")),
        environment_class=env_classes[0] if env_classes else "git_worktree",
        verifier_role_id=verifier_role_id,
        deterministic_scores={cid: score for cid, score in ranked},
        alternatives=[cid for cid, _ in ranked[1:]],
        rejection_reasons=rejections,
        rationale=(
            f"worker {winner_id} (score {winner_score}) owns role {role_id}; "
            f"node {node.get('node_id', '')} by headroom; verifier {verifier_role_id}"
        ),
    )

    if persist and store is not None:
        runner = mutation_runner
        if runner is None:
            from substrate.execution.intent.loop import _substrate_native_governed_mutation

            runner = _substrate_native_governed_mutation

        def _apply() -> tuple[str, bool]:
            store.append_assignment(assignment)
            return (f"placement recorded: {assignment.assignment_id}", True)

        runner(
            mutation_name="execution_placement_record",
            intent=f"record placement for attempt {attempt_id}",
            execute_fn=_apply,
            source="execution_attempts_placement",
            metadata={"assignment_id": assignment.assignment_id, "task_id": assignment.task_id},
        )
    return assignment


__all__ = ["ExecutionAssignment", "PlacementError", "place_attempt"]
