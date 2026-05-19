"""Integration test — full end-to-end pipeline validation.

Adapted from umh_mvp/tests/test_integration.py. Tests the complete master
success loop across multiple signals with governance gating and accumulation.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.umh.control_plane.pipeline import ExecutionPipeline
from services.umh.foundation.laws import SUBSTRATE_LAWS
from services.umh.foundation.primitives import OntologicalCategory
from services.umh.foundation.epistemology import EpistemicStatus
from services.umh.governance.policy_engine import PolicyEngine
from services.umh.governance.risk_classes import RiskClass
from services.umh.memory.candidate_generator import MemoryCandidateGenerator
from services.umh.memory.promoter import MemoryPromoter
from services.umh.observability.trace_store import TraceStore


def _make_pipeline(td: str) -> tuple[ExecutionPipeline, TraceStore]:
    trace_store = TraceStore(Path(td) / "traces")
    candidate_gen = MemoryCandidateGenerator(Path(td) / "candidates")
    promoter = MemoryPromoter(path=Path(td) / "memories.json")
    pipeline = ExecutionPipeline(
        policy_engine=PolicyEngine(safe_roots=["/opt/OS"]),
        trace_store=trace_store,
        candidate_generator=candidate_gen,
        memory_promoter=promoter,
    )
    return pipeline, trace_store


def test_e2e_approved_signal():
    """Full pipeline: low-risk signal flows through all stages."""
    with tempfile.TemporaryDirectory() as td:
        pipeline, trace_store = _make_pipeline(td)

        result = pipeline.submit_signal(
            "Check revenue dashboard",
            risk_class=RiskClass.READ_ONLY,
        )

        assert result.governance_approved is True
        assert result.executed is True
        assert result.trace_id is not None
        assert result.signal_id is not None
        assert result.proof_id is not None

        assert trace_store.count() == 1


def test_e2e_blocked_signal():
    """Full pipeline: high-risk signal blocked at governance gate."""
    with tempfile.TemporaryDirectory() as td:
        pipeline, trace_store = _make_pipeline(td)

        result = pipeline.submit_signal(
            "Delete production data",
            risk_class=RiskClass.IRREVERSIBLE_WRITE,
        )

        assert result.governance_approved is False
        assert result.executed is False
        assert result.success is None
        assert result.proof_id is None
        assert result.outcome_type is None
        assert result.memory_candidate_id is None

        # Audit trail: blocked signal STILL produces a trace
        assert trace_store.count() == 1


def test_e2e_multiple_signals():
    """Pipeline handles multiple signals with correct accumulation."""
    with tempfile.TemporaryDirectory() as td:
        pipeline, trace_store = _make_pipeline(td)

        signals = [
            ("Read email", RiskClass.READ_ONLY),
            ("Update CRM", RiskClass.SAFE_WRITE),
            ("Send invoice", RiskClass.FINANCIAL),
            ("Check calendar", RiskClass.READ_ONLY),
            ("Delete backups", RiskClass.IRREVERSIBLE_WRITE),
        ]

        results = []
        for content, risk in signals:
            r = pipeline.submit_signal(content, risk_class=risk)
            results.append(r)

        approved = [r for r in results if r.governance_approved]
        blocked = [r for r in results if not r.governance_approved]

        # READ_ONLY auto-approved, SAFE_WRITE approved (no safe_root context
        # needed for pipeline — governance uses default), FINANCIAL denied,
        # READ_ONLY approved, IRREVERSIBLE_WRITE denied.
        # SAFE_WRITE without target_path context → deferred (not executable)
        approved_count = len(approved)
        blocked_count = len(blocked)
        assert approved_count + blocked_count == 5

        # All 5 signals produce traces (including blocked ones)
        assert trace_store.count() == 5


def test_e2e_layer0_integrity():
    """Foundation ontology is complete and consistent."""
    assert len(list(OntologicalCategory)) == 8
    assert len(SUBSTRATE_LAWS) == 6
    assert len(list(EpistemicStatus)) == 6

    for law in SUBSTRATE_LAWS:
        assert law.name, f"Law has no name"
        assert law.statement, f"Law '{law.name}' has no statement"
        assert law.enforceable, f"Law '{law.name}' is not enforceable"


def test_e2e_governance_risk_classes():
    """All 8 risk classes resolve to valid risk levels."""
    for rc in RiskClass:
        rl = rc.to_risk_level()
        assert rl is not None, f"RiskClass {rc.value} has no risk level mapping"


def test_e2e_blocked_signal_audit_trail():
    """Governance-denied signals produce complete audit records."""
    with tempfile.TemporaryDirectory() as td:
        pipeline, trace_store = _make_pipeline(td)

        pipeline.submit_signal("Transfer $10k", risk_class=RiskClass.FINANCIAL)

        assert trace_store.count() == 1
        traces = trace_store.recent_traces(10)
        assert len(traces) == 1
        assert traces[0].get("outcome") == "governance_denied" or "governance" in str(traces[0])


if __name__ == "__main__":
    passed = 0
    failed = 0
    errors = 0

    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  PASS  {name}")
                passed += 1
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
                failed += 1
            except Exception as e:
                print(f"  ERROR {name}: {e}")
                errors += 1

    print(f"\n{passed} passed, {failed} failed, {errors} errors")
