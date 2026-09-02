"""Regressions for the whole-tree shard result model (false-COMPLETE defect).

The defect these pin: the previous harness emitted ``COMPLETE`` after a shard's
pytest call returned, regardless of exit code. shard_04 of the ``e7ff662c`` run
was KILLED at its 5400s bound (EXIT=124, no summary, ~70% executed) and still
carried a ``COMPLETE`` marker beside it. Nothing structurally prevented a
consumer from reading that run as green.

Every test below asserts BEHAVIOUR of the canonical result model, not source
text — a source-text assertion would survive the logic being reverted at
runtime, which is exactly the failure mode in question.
"""

from __future__ import annotations

import pytest

from tests.wave2_script_import import load_wave2_script

# Loaded by explicit path, never through sys.path: a stale /opt/OS checkout on
# sys.path carries its own ``scripts`` package that would shadow this
# candidate's. That is a real, previously-fixed contamination defect, and
# tests/test_wave2_script_loader.py fails any Wave 2 test that reintroduces it.
_wt = load_wave2_script("wave2_whole_tree")

BASELINE_EXCEPTED_NODE_IDS = _wt.BASELINE_EXCEPTED_NODE_IDS
COMPLETE_MARKER = _wt.COMPLETE_MARKER
TIMEOUT_EXIT_CODE = _wt.TIMEOUT_EXIT_CODE
ShardResult = _wt.ShardResult
WholeTreeVerdict = _wt.WholeTreeVerdict


def _ok(shard_id: str = "shard_00", **over) -> ShardResult:
    """A shard that passed everything, unless a field is overridden."""
    base = dict(
        shard_id=shard_id,
        assigned_files=10,
        collected_files=10,
        executed_files=10,
        exit_code=0,
        duration_seconds=12.0,
        artifact_present=True,
        artifact_malformed=False,
        summary_line="100 passed",
    )
    base.update(over)
    return ShardResult(**base)


# ── the exact shard_04 regression ────────────────────────────────────


def test_the_exact_shard_04_case_is_not_complete():
    """EXIT=124, no summary, partial execution — the real observed shard.

    This is the concrete case that motivated the correction, reproduced with
    its measured values.
    """
    s = ShardResult(
        shard_id="shard_04",
        assigned_files=85,
        collected_files=85,
        executed_files=59,  # ~70% — killed mid-run
        exit_code=TIMEOUT_EXIT_CODE,
        duration_seconds=5400.0,
        summary_line="",  # pytest never wrote one
    )
    assert s.succeeded is False
    assert s.marker() != COMPLETE_MARKER
    assert s.marker() == f"INCOMPLETE_EXIT_{TIMEOUT_EXIT_CODE}"
    assert WholeTreeVerdict(shards=[_ok(), s]).complete is False


# ── exit codes ───────────────────────────────────────────────────────


@pytest.mark.parametrize("code", [1, 2, TIMEOUT_EXIT_CODE, 3, 127, -9])
def test_any_nonzero_exit_is_not_complete(code):
    s = _ok(exit_code=code)
    assert s.succeeded is False
    assert s.marker() != COMPLETE_MARKER


def test_missing_exit_status_fails_closed():
    """No recorded exit status is 'unknown', which must never read as success."""
    s = _ok(exit_code=None)
    assert s.succeeded is False
    assert s.marker() == "INCOMPLETE_NO_EXIT_STATUS"


def test_clean_shard_is_complete():
    """The correction must not make success impossible — that would be a
    different defect, and a suite where nothing can pass proves nothing."""
    s = _ok()
    assert s.succeeded is True
    assert s.marker() == COMPLETE_MARKER


# ── completeness invariants beyond the exit code ─────────────────────


def test_missing_artifact_is_not_complete():
    s = _ok(artifact_present=False)
    assert s.succeeded is False
    assert "artifact missing" in " ".join(s.failure_reasons())


def test_malformed_artifact_is_not_complete():
    s = _ok(artifact_malformed=True)
    assert s.succeeded is False
    assert "malformed" in " ".join(s.failure_reasons())


def test_partial_execution_is_not_complete_even_on_exit_zero():
    """Exit 0 while executing fewer files than assigned is still incomplete.

    A shard that quietly skipped work has proven nothing about the remainder.
    """
    s = _ok(assigned_files=85, collected_files=85, executed_files=59)
    assert s.exit_code == 0
    assert s.succeeded is False
    assert s.marker() == "INCOMPLETE_COVERAGE"


def test_collection_shortfall_is_not_complete():
    s = _ok(assigned_files=85, collected_files=60, executed_files=60)
    assert s.succeeded is False


def test_zero_assigned_files_is_not_complete():
    """An empty shard is a harness defect, not a pass."""
    s = _ok(assigned_files=0, collected_files=0, executed_files=0)
    assert s.succeeded is False


# ── the aggregate cannot be fooled ───────────────────────────────────


def test_aggregate_fails_when_any_shard_incomplete():
    v = WholeTreeVerdict(shards=[_ok("s0"), _ok("s1"), _ok("s2", exit_code=TIMEOUT_EXIT_CODE)])
    assert v.complete is False
    assert "INCOMPLETE" in v.verdict()
    assert "s2" in v.verdict()


def test_aggregate_with_no_shards_is_not_complete():
    """Zero shards must never read as success — the run did not happen."""
    assert WholeTreeVerdict(shards=[]).complete is False


def test_aggregate_verdict_derives_from_results_not_markers():
    """A stale/forged COMPLETE marker cannot override the canonical result.

    This is the heart of the correction: the aggregate consults
    ``ShardResult.succeeded``, never marker text, so marker and truth cannot
    diverge.
    """
    bad = _ok("s1", exit_code=TIMEOUT_EXIT_CODE)
    assert bad.marker() != COMPLETE_MARKER
    v = WholeTreeVerdict(shards=[_ok("s0"), bad])
    assert v.complete is False


def test_all_clean_shards_aggregate_complete():
    v = WholeTreeVerdict(shards=[_ok("s0"), _ok("s1")])
    assert v.complete is True
    assert v.verdict() == "COMPLETE"


# ── truthful disposition when a node is excepted ─────────────────────


def test_excluded_node_is_never_reported_as_absolute_green():
    """With an accepted exception the verdict must SAY so, not claim green."""
    v = WholeTreeVerdict(
        shards=[_ok("s0"), _ok("s1")],
        excluded_node_ids=list(BASELINE_EXCEPTED_NODE_IDS),
    )
    assert v.complete is True
    verdict = v.verdict()
    assert verdict != "COMPLETE"
    assert "EXCEPTION" in verdict
    assert "ACCEPTED" in verdict


def test_baseline_exception_is_exactly_one_exact_node_id():
    """Not a file, class, directory, or glob — one fully-qualified node.

    Guards against the exception list quietly widening into a way to hide slow
    or failing tests.
    """
    assert len(BASELINE_EXCEPTED_NODE_IDS) == 1
    node = BASELINE_EXCEPTED_NODE_IDS[0]
    assert node.count("::") == 2, "must be file::Class::test, a single exact node"
    assert not node.endswith("::")
    assert "*" not in node and "?" not in node
    assert node.startswith("tests/") and node.split("::")[0].endswith(".py")


def test_excepted_node_is_the_strategic_context_one():
    assert BASELINE_EXCEPTED_NODE_IDS[0] == (
        "tests/test_strategic_context_runtime.py::"
        "TestHealthClassification::test_healthy_no_engines"
    )
