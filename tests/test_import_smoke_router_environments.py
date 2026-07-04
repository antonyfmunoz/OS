"""Import-smoke tests for modules whose symbol renames have repeatedly
stranded stale test imports and interrupted full-suite pytest collection.

Each of these three substrate modules renamed an exported symbol, and a test
kept importing the old name — turning `pytest --collect-only` INTERRUPTED
(WP-P0-011):

  * substrate.organism.execution_coordinator      ExecutionMode  → ExecutionTiming
  * substrate.organism.benchmarks.outcome_accuracy OutcomeRecord  → BenchmarkOutcomeRecord
  * substrate.organism.dev_session_tracker         SessionStatus  → DevSessionStatus

These tests import each module and assert the CURRENT canonical symbols exist
and the retired names are gone. If a future rename drifts again, this file
fails at collection/run time with a clear message pointing at the module and
the symbol — a fast, targeted signal on top of the collect-only pre-commit gate
(scripts/check_pytest_collection.py).
"""

from __future__ import annotations

import importlib

import pytest


def test_execution_coordinator_imports_and_exports_current_symbols() -> None:
    mod = importlib.import_module("substrate.organism.execution_coordinator")

    # Current canonical timing enum.
    assert hasattr(mod, "ExecutionTiming"), "ExecutionTiming missing from execution_coordinator"
    assert {e.value for e in mod.ExecutionTiming} == {
        "synchronous",
        "asynchronous",
        "background",
        "scheduled",
    }

    # Retired name must not silently reappear (that would hide drift).
    assert not hasattr(mod, "ExecutionMode"), (
        "ExecutionMode was renamed to ExecutionTiming — a back-compat alias "
        "hides the drift; fix the test import instead"
    )


def test_outcome_accuracy_imports_and_exports_current_symbols() -> None:
    mod = importlib.import_module("substrate.organism.benchmarks.outcome_accuracy")

    assert hasattr(mod, "BenchmarkOutcomeRecord"), (
        "BenchmarkOutcomeRecord missing from outcome_accuracy"
    )
    # The record must still carry the fields the benchmark relies on.
    rec = mod.BenchmarkOutcomeRecord(production_id="p1")
    assert rec.production_id == "p1"
    assert rec.acceptance_criteria == []
    assert rec.criteria_met == []
    assert rec.tests_passed is False
    assert rec.deployed is False

    assert not hasattr(mod, "OutcomeRecord"), (
        "OutcomeRecord was renamed to BenchmarkOutcomeRecord — no back-compat alias"
    )


def test_dev_session_tracker_imports_and_exports_current_symbols() -> None:
    mod = importlib.import_module("substrate.organism.dev_session_tracker")

    assert hasattr(mod, "DevSessionStatus"), "DevSessionStatus missing from dev_session_tracker"
    assert mod.DevSessionStatus.ACTIVE == "active"
    assert mod.DevSessionStatus.COMPLETED == "completed"
    assert mod.DevSessionStatus.ABANDONED == "abandoned"

    assert not hasattr(mod, "SessionStatus"), (
        "SessionStatus was renamed to DevSessionStatus — no back-compat alias"
    )


@pytest.mark.parametrize(
    "module_path",
    [
        "substrate.organism.execution_coordinator",
        "substrate.organism.benchmarks.outcome_accuracy",
        "substrate.organism.dev_session_tracker",
        "substrate.organism.benchmarks.autonomous_execution",
        "substrate.organism.benchmarks.efficiency",
        "substrate.organism.benchmarks.reliability",
        "substrate.organism.action_envelope",
    ],
)
def test_module_imports_clean(module_path: str) -> None:
    """Every routinely-imported module must import without error."""
    assert importlib.import_module(module_path) is not None
