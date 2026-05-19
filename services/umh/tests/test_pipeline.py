"""Tests for ExecutionPipeline — the master success loop.

Adapted from umh_mvp/tests/test_pipeline.py. Tests submit_signal() flowing
through signal → governance → execute → proof → outcome → memory_candidate.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.umh.control_plane.pipeline import ExecutionPipeline, PipelineResult
from services.umh.governance.risk_classes import RiskClass
from services.umh.memory.candidate_generator import MemoryCandidateGenerator
from services.umh.memory.promoter import MemoryPromoter
from services.umh.observability.trace_store import TraceStore


def _make_pipeline(td: str) -> ExecutionPipeline:
    return ExecutionPipeline(
        trace_store=TraceStore(Path(td) / "traces"),
        candidate_generator=MemoryCandidateGenerator(Path(td) / "candidates"),
        memory_promoter=MemoryPromoter(path=Path(td) / "memories.json"),
    )


def test_full_pipeline_low_risk():
    with tempfile.TemporaryDirectory() as td:
        pipeline = _make_pipeline(td)
        result = pipeline.submit_signal("Check dashboard", risk_class=RiskClass.READ_ONLY)

        assert result.governance_approved is True
        assert result.executed is True
        assert isinstance(result, PipelineResult)
        assert result.trace_id is not None
        assert result.signal_id is not None


def test_full_pipeline_high_risk_blocked():
    with tempfile.TemporaryDirectory() as td:
        pipeline = _make_pipeline(td)
        result = pipeline.submit_signal(
            "Delete database",
            risk_class=RiskClass.IRREVERSIBLE_WRITE,
        )

        assert result.governance_approved is False
        assert result.executed is False
        assert result.success is None
        assert result.proof_id is None


def test_pipeline_pre_approved_override():
    with tempfile.TemporaryDirectory() as td:
        pipeline = _make_pipeline(td)
        result = pipeline.submit_signal(
            "Delete temp files",
            risk_class=RiskClass.IRREVERSIBLE_WRITE,
            pre_approved=True,
        )

        assert result.governance_approved is True
        assert result.executed is True


def test_store_accumulates():
    with tempfile.TemporaryDirectory() as td:
        trace_store = TraceStore(Path(td) / "traces")
        pipeline = ExecutionPipeline(
            trace_store=trace_store,
            candidate_generator=MemoryCandidateGenerator(Path(td) / "candidates"),
        )

        pipeline.submit_signal("First")
        pipeline.submit_signal("Second")
        pipeline.submit_signal("Third")

        assert trace_store.count() == 3


def test_result_has_all_fields():
    with tempfile.TemporaryDirectory() as td:
        pipeline = _make_pipeline(td)
        result = pipeline.submit_signal("Test fields")

        assert hasattr(result, "trace_id")
        assert hasattr(result, "signal_id")
        assert hasattr(result, "governance_approved")
        assert hasattr(result, "governance_rationale")
        assert hasattr(result, "executed")
        assert hasattr(result, "success")
        assert hasattr(result, "proof_id")
        assert hasattr(result, "outcome_type")
        assert hasattr(result, "memory_candidate_id")
        assert hasattr(result, "memory_promoted")


def test_event_listeners():
    events: list[tuple[str, dict]] = []

    with tempfile.TemporaryDirectory() as td:
        pipeline = _make_pipeline(td)
        pipeline.on_event(lambda t, d: events.append((t, d)))

        pipeline.submit_signal("Test events")

    event_types = [e[0] for e in events]
    assert "signal" in event_types
    assert "governance" in event_types
    assert "work_packet" in event_types
    assert "execution" in event_types
    assert "proof" in event_types
    assert "outcome" in event_types
    assert "trace" in event_types


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  PASS  {name}")
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
            except Exception as e:
                print(f"  ERROR {name}: {e}")
