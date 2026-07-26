"""Pre-quota graph-shape gate — prove the Task graph BEFORE spending a worker.

Field run 20260726T025143Z-p1 spent real worker quota and then failed at stage
``w16_ab_running_concurrent`` for a reason that was knowable before dispatch:
the objective had compiled to ONE combined Task, so a journey asserting two
concurrent implementation Tasks could never pass. The execution system did not
mis-schedule a valid graph — the planning layer never produced one.

This gate closes that loop. It is READ-ONLY: it rereads the persisted canonical
Plan and WorkPackets and answers one question — does the materialized graph have
the shape the multi-lane protocol requires? — and it is meant to run BEFORE HUD
execution authorization and BEFORE any dispatch, so a wrong-shaped graph costs
zero quota.

It is NOT a second planning authority and NOT a scope authority:
  * it never creates, mutates, or repairs a Task;
  * it never derives authority (it asserts what the Task contract already says);
  * it never infers lanes from titles, packet-id shapes, or a worker's diff;
  * a failure STOPS the campaign — it never downgrades to a warning.

Evidence is provenance, never mutation authority: this gate reads the persisted
contracts alone.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# The canonical multi-lane shape the field protocol asserts:
#     A ─┐
#        ├→ C → D
#     B ─┘
# Two independent implementation lanes, one fan-in integration lane, one
# zero-write independent verification lane.
REQUIRED_TASK_COUNT = 4
IMPLEMENTATION_LANES = 2


class GraphShapeError(RuntimeError):
    """The persisted graph does not have the required shape. Fail closed."""


@dataclass
class GraphShapeVerdict:
    """Typed, inspectable result of one gate evaluation."""

    ok: bool = False
    checks: list[dict[str, Any]] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)
    plan_record_id: str = ""
    plan_version: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": list(self.checks),
            "failures": list(self.failures),
            "task_ids": list(self.task_ids),
            "plan_record_id": self.plan_record_id,
            "plan_version": self.plan_version,
        }

    def raise_if_failed(self) -> None:
        if not self.ok:
            raise GraphShapeError(
                "graph-shape gate FAILED before dispatch (zero quota spent): "
                + "; ".join(self.failures)
            )


def _record(
    verdict: GraphShapeVerdict, check_id: str, ok: bool, detail: str
) -> None:
    verdict.checks.append({"check_id": check_id, "ok": bool(ok), "detail": detail})
    if not ok:
        verdict.failures.append(f"{check_id}: {detail}")


def _scope_of(packet: dict[str, Any]) -> tuple[bool, list[str]]:
    req = packet.get("requirements") or {}
    return bool(req.get("scope_declared")), [str(p) for p in (req.get("writable_path_scope") or [])]


def evaluate_graph_shape(
    *,
    packets: list[dict[str, Any]],
    plan_record_id: str,
    plan_version: int = 0,
    attempt_count: int | None = None,
) -> GraphShapeVerdict:
    """Evaluate the persisted Tasks of ONE accepted plan version.

    ``packets`` are the canonical WorkPacket dicts already filtered to the plan
    under evaluation. ``attempt_count``, when supplied, asserts the pre-dispatch
    invariant that no ExecutionAttempt exists yet.
    """
    verdict = GraphShapeVerdict(plan_record_id=plan_record_id, plan_version=plan_version)
    verdict.task_ids = [str(p.get("packet_id") or "") for p in packets]

    # 1. exactly 4 Tasks
    _record(
        verdict,
        "task_count",
        len(packets) == REQUIRED_TASK_COUNT,
        f"{len(packets)} Task(s) materialized, need exactly {REQUIRED_TASK_COUNT}",
    )

    # 2. unique packet ids
    ids = [i for i in verdict.task_ids if i]
    _record(
        verdict,
        "unique_task_ids",
        len(set(ids)) == len(packets) and len(ids) == len(packets),
        f"{len(set(ids))} unique id(s) across {len(packets)} Task(s)",
    )

    # 3. all Tasks belong to the accepted plan version
    wrong_plan = [
        str(p.get("packet_id") or "")
        for p in packets
        if str((p.get("lineage") or {}).get("plan_record_id") or p.get("plan_record_id") or "")
        != plan_record_id
    ]
    _record(
        verdict,
        "plan_binding",
        not wrong_plan,
        f"out-of-plan Task(s): {wrong_plan}" if wrong_plan else f"all bound to {plan_record_id}",
    )

    by_id = {str(p.get("packet_id") or ""): p for p in packets}

    def deps(packet: dict[str, Any]) -> list[str]:
        return [str(d) for d in (packet.get("dependencies") or [])]

    roots = [p for p in packets if not deps(p)]
    # 4. exactly two dependency-free implementation lanes (A, B)
    _record(
        verdict,
        "independent_implementation_lanes",
        len(roots) == IMPLEMENTATION_LANES,
        f"{len(roots)} Task(s) with no dependencies, need exactly {IMPLEMENTATION_LANES}",
    )

    # 5. exactly one fan-in Task (C) depending on BOTH roots
    root_ids = {str(p.get("packet_id") or "") for p in roots}
    fan_in = [p for p in packets if set(deps(p)) == root_ids and root_ids]
    _record(
        verdict,
        "fan_in_depends_on_both",
        len(fan_in) == 1,
        f"{len(fan_in)} Task(s) depend on exactly both implementation lanes, need 1",
    )

    # 6. exactly one terminal verifier (D) depending only on C
    verifier: dict[str, Any] | None = None
    if len(fan_in) == 1:
        c_id = str(fan_in[0].get("packet_id") or "")
        terminal = [p for p in packets if deps(p) == [c_id]]
        _record(
            verdict,
            "verifier_depends_on_fan_in",
            len(terminal) == 1,
            f"{len(terminal)} Task(s) depend exactly on the integration Task, need 1",
        )
        if len(terminal) == 1:
            verifier = terminal[0]
    else:
        _record(
            verdict,
            "verifier_depends_on_fan_in",
            False,
            "fan-in Task not uniquely identified — verifier chain unverifiable",
        )

    # 7. every Task declares authority (never inferred, never empty-by-omission)
    undeclared = [
        str(p.get("packet_id") or "") for p in packets if not _scope_of(p)[0]
    ]
    _record(
        verdict,
        "scope_declared_everywhere",
        not undeclared,
        f"Task(s) with scope_declared=False: {undeclared}"
        if undeclared
        else "all Tasks declare mutation authority",
    )

    # 8. the two implementation lanes have DISTINCT scopes
    if len(roots) == IMPLEMENTATION_LANES:
        a_scope = tuple(sorted(_scope_of(roots[0])[1]))
        b_scope = tuple(sorted(_scope_of(roots[1])[1]))
        _record(
            verdict,
            "distinct_implementation_scopes",
            a_scope != b_scope and bool(a_scope) and bool(b_scope),
            f"lane scopes {'differ' if a_scope != b_scope else 'are IDENTICAL'} "
            f"({len(a_scope)} vs {len(b_scope)} path(s))",
        )
    else:
        _record(
            verdict,
            "distinct_implementation_scopes",
            False,
            "implementation lanes not uniquely identified — scope distinctness unverifiable",
        )

    # 9. the verifier is zero-write
    if verifier is not None:
        declared, paths = _scope_of(verifier)
        _record(
            verdict,
            "verifier_zero_write",
            declared and not paths,
            f"verifier declares {len(paths)} writable path(s), need 0 (declared={declared})",
        )
    else:
        _record(
            verdict,
            "verifier_zero_write",
            False,
            "verifier Task not identified — zero-write authority unverifiable",
        )

    # 10. no ExecutionAttempt exists yet (pre-dispatch invariant)
    if attempt_count is not None:
        _record(
            verdict,
            "zero_attempts_pre_dispatch",
            attempt_count == 0,
            f"{attempt_count} ExecutionAttempt(s) already exist, need 0 before authorization",
        )

    verdict.ok = not verdict.failures
    return verdict


__all__ = [
    "GraphShapeError",
    "GraphShapeVerdict",
    "evaluate_graph_shape",
    "REQUIRED_TASK_COUNT",
    "IMPLEMENTATION_LANES",
]
