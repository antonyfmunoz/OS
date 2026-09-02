"""Canonical execution-attempt slice (MVP Wave 2).

Sibling of ``substrate.execution.planning`` — the governed EXECUTION half of the
operator vertical slice. Where planning owns intent → Objective → Plan → Task →
plan-acceptance Decision, this package owns the bounded EFFECT of an APPROVED
``execution_authorization`` Decision:

    ExecutionAuthorizationGrant  (bounded effect of an approved ApprovalRequest)
    → ExecutionAttempt           (the one canonical concrete execution object)
    → placement / lease / dispatch / verification / Proof

Ownership rulings (Convergence Law + Wave 2 Amendment v1):

- ``substrate.types.ApprovalRequest`` remains the SOLE Decision identity and
  lifecycle authority. ``ExecutionAuthorizationGrant`` is NOT a Decision — it is
  the persisted bounded effect of one that was already approved. It carries no
  REQUESTED/DENIED state; rejected requests live only in ApprovalRequest history.
- ``substrate.organism.work_packet.WorkPacket`` remains the only Task.
- ``substrate.organism.work_graph.WorkGraph`` remains the sole read projection.
- ``ExecutionAttemptStore`` is the sole CURRENT execution truth. The dispatch
  spool is an ephemeral transport representation only.

Hard import law (enforced by tests/test_wave2_convergence_gates.py): this
package never imports execution_coordinator, executor_runtime (SimulationExecutor
home), plan_execution_adapter, composition_engine, or governed_work_runtime.
"""

from __future__ import annotations

from substrate.execution.attempts.records import (
    AttemptTransition,
    ExecutionAttempt,
    ExecutionAttemptStatus,
    ExecutionAuthorizationGrant,
    ExecutionAuthorizationGrantStatus,
)

__all__ = [
    "AttemptTransition",
    "ExecutionAttempt",
    "ExecutionAttemptStatus",
    "ExecutionAuthorizationGrant",
    "ExecutionAuthorizationGrantStatus",
]
