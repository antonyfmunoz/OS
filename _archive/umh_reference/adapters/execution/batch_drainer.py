"""
umh.adapters.execution.batch_drainer — Drains pending execution
batches and transitions them to active.

Pure function over state: reads pending batches, loads each, marks started,
and returns the started batches with their accumulated mutations. Does NOT
dispatch work — that is the execution_bridge's responsibility.

Public API:
    drain_pending_batches  — load and start all pending batches
    DrainResult            — return type with batches + mutations

Usage:
    result = drain_pending_batches(state)
    # Apply result.mutations to store
    # Then dispatch result.batches via execution_bridge
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

from umh.substrate.execution_batch import (
    ExecutionBatch,
    list_pending_batches,
    load_execution_batch,
    mark_batch_started,
)

_LOG_PREFIX = "[adapters.execution.batch_drainer]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


@dataclass
class DrainResult:
    """Result of a drain_pending_batches call.

    Fields:
        batches:   list of batches that were transitioned to active
        mutations: accumulated SET/REMOVE mutations to apply to state
        skipped:   batch IDs that were in the pending index but could
                   not be loaded (orphaned index entries)
    """

    batches: list[ExecutionBatch] = field(default_factory=list)
    mutations: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def drain_pending_batches(state: dict[str, Any]) -> DrainResult:
    """Load all pending batches from state and mark them started.

    Iterates in deterministic (sorted) order. For each pending batch:
    1. Load the full batch record from state
    2. Mark it started (pending → active)
    3. Accumulate mutations

    Does NOT dispatch tasks — the caller is responsible for passing
    the returned batches to execution_bridge.dispatch_batch().

    Args:
        state: current state snapshot (dict[str, Any])

    Returns:
        DrainResult with started batches, mutations, and any skipped IDs.
    """
    result = DrainResult()
    pending_ids = list_pending_batches(state)

    if not pending_ids:
        return result

    _log(f"draining {len(pending_ids)} pending batch(es)")

    for batch_id in pending_ids:
        batch = load_execution_batch(state, batch_id)
        if batch is None:
            _log(f"skip orphaned index entry: {batch_id}")
            result.skipped.append(batch_id)
            continue

        if batch.status != "pending":
            _log(f"skip non-pending batch {batch_id} (status={batch.status})")
            result.skipped.append(batch_id)
            continue

        started, mutations = mark_batch_started(batch)
        result.batches.append(started)
        result.mutations.extend(mutations)
        _log(f"started batch {batch_id} ({len(batch.tasks)} tasks)")

    return result
