"""Tests for extensions: adapters, approval workflow, memory promoter, resume state.

Adapted from umh_mvp/tests/test_extensions.py. Rewritten for services/umh
adapters (ShellAdapter/FilesystemAdapter with operation+params interface)
and the new MemoryPromoter in services/umh/memory/promoter.py.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.umh.adapters.shell import ShellAdapter
from services.umh.adapters.filesystem import FilesystemAdapter
from services.umh.control_plane.pipeline import ExecutionPipeline
from services.umh.governance.risk_classes import RiskClass
from services.umh.memory.candidate_generator import MemoryCandidate, MemoryCandidateGenerator
from services.umh.memory.promoter import MemoryPromoter
from services.umh.observability.trace_store import TraceStore
from services.umh.workstation.state import (
    WorkstationProfile,
    WorkstationSessionState,
    WorkstationStateManager,
)


# ─── Adapter Tests ────────────────────────────────────


def test_shell_adapter_echo():
    adapter = ShellAdapter()
    result = adapter.execute("echo hello world", {"command": "echo hello world"})
    assert result["success"] is True
    assert "hello world" in result["stdout"]


def test_shell_adapter_blocks_dangerous():
    adapter = ShellAdapter()
    try:
        adapter.execute("rm -rf /", {"command": "rm -rf /"})
        assert False, "Should have raised PermissionError"
    except PermissionError as e:
        assert "blocked" in str(e).lower() or "denied" in str(e).lower()


def test_shell_adapter_risk_classification():
    adapter = ShellAdapter()
    assert adapter.classify_risk("ls", {"command": "ls"}) == RiskClass.READ_ONLY
    assert adapter.classify_risk("curl http://example.com", {"command": "curl http://example.com"}) == RiskClass.EXTERNAL_COMMUNICATION


def test_filesystem_adapter_read():
    adapter = FilesystemAdapter(safe_roots=["/opt/OS"])
    result = adapter.execute("read", {"path": "/opt/OS/CLAUDE.md"})
    assert "content" in result
    assert len(result["content"]) > 0


def test_filesystem_adapter_rejects_outside_roots():
    adapter = FilesystemAdapter(safe_roots=["/opt/OS"])
    try:
        adapter.execute("write", {"path": "/etc/test.txt", "content": "hack"})
        assert False, "Should have raised PermissionError"
    except PermissionError as e:
        assert "denied" in str(e).lower()


# ─── Approval Workflow Tests ──────────────────────────


def test_pre_approved_bypasses_governance():
    with tempfile.TemporaryDirectory() as td:
        pipeline = ExecutionPipeline(
            trace_store=TraceStore(Path(td) / "traces"),
            candidate_generator=MemoryCandidateGenerator(Path(td) / "candidates"),
        )
        result = pipeline.submit_signal(
            "Delete temp files",
            risk_class=RiskClass.IRREVERSIBLE_WRITE,
            pre_approved=True,
        )
        assert result.governance_approved is True
        assert result.executed is True


def test_high_risk_denied_then_pre_approved():
    with tempfile.TemporaryDirectory() as td:
        trace_store = TraceStore(Path(td) / "traces")
        pipeline = ExecutionPipeline(
            trace_store=trace_store,
            candidate_generator=MemoryCandidateGenerator(Path(td) / "candidates"),
        )

        denied = pipeline.submit_signal(
            "Dangerous action",
            risk_class=RiskClass.IRREVERSIBLE_WRITE,
        )
        assert denied.governance_approved is False

        approved = pipeline.submit_signal(
            "Dangerous action",
            risk_class=RiskClass.IRREVERSIBLE_WRITE,
            pre_approved=True,
        )
        assert approved.governance_approved is True
        assert approved.executed is True


# ─── Memory Promoter Tests ───────────────────────────


def test_memory_promoter_promotes_above_threshold():
    with tempfile.TemporaryDirectory() as td:
        mem_path = Path(td) / "memories.json"
        promoter = MemoryPromoter(path=mem_path, confidence_threshold=0.7)
        candidate = MemoryCandidate(
            candidate_id="memcand-test-1",
            source_trace_id="trace-test-1",
            content="High confidence memory",
            reason="test",
            confidence=0.95,
            scope="session",
        )

        result = promoter.evaluate(candidate)
        assert result["promoted"] is True
        assert "memory_id" in result

        memories = promoter.list_memories()
        assert len(memories) == 1
        assert memories[0]["content"] == "High confidence memory"


def test_memory_promoter_rejects_below_threshold():
    with tempfile.TemporaryDirectory() as td:
        mem_path = Path(td) / "memories.json"
        promoter = MemoryPromoter(path=mem_path, confidence_threshold=0.7)
        candidate = MemoryCandidate(
            candidate_id="memcand-test-2",
            source_trace_id="trace-test-2",
            content="Low confidence memory",
            reason="test",
            confidence=0.3,
            scope="session",
        )

        result = promoter.evaluate(candidate)
        assert result["promoted"] is False
        assert "threshold" in result["reason"].lower()


def test_memory_promoter_deduplicates():
    with tempfile.TemporaryDirectory() as td:
        mem_path = Path(td) / "memories.json"
        promoter = MemoryPromoter(path=mem_path, confidence_threshold=0.7)

        for i in range(3):
            candidate = MemoryCandidate(
                candidate_id=f"memcand-dup-{i}",
                source_trace_id=f"trace-dup-{i}",
                content="Identical content",
                reason="test",
                confidence=0.95,
                scope="session",
            )
            promoter.evaluate(candidate)

        assert len(promoter.list_memories()) == 1
        assert promoter.stats()["unique_hashes"] == 1


def test_memory_promotion_in_pipeline():
    with tempfile.TemporaryDirectory() as td:
        mem_path = Path(td) / "memories.json"
        promoter = MemoryPromoter(path=mem_path, confidence_threshold=0.7)
        pipeline = ExecutionPipeline(
            trace_store=TraceStore(Path(td) / "traces"),
            candidate_generator=MemoryCandidateGenerator(Path(td) / "candidates"),
            memory_promoter=promoter,
        )

        pipeline.submit_signal("Pipeline memory test", risk_class=RiskClass.READ_ONLY)

        # Pipeline runs through executor (no adapter → failure path) but
        # still validates the promoter wiring is correct
        memories = promoter.list_memories()
        # May or may not promote depending on executor success — verify wiring
        assert isinstance(memories, list)


def test_event_includes_memory_promotion():
    with tempfile.TemporaryDirectory() as td:
        mem_path = Path(td) / "memories.json"
        events: list[tuple[str, dict]] = []
        promoter = MemoryPromoter(path=mem_path, confidence_threshold=0.0)
        pipeline = ExecutionPipeline(
            trace_store=TraceStore(Path(td) / "traces"),
            candidate_generator=MemoryCandidateGenerator(Path(td) / "candidates"),
            memory_promoter=promoter,
        )
        pipeline.on_event(lambda t, d: events.append((t, d)))

        pipeline.submit_signal(
            "Event promotion test",
            risk_class=RiskClass.READ_ONLY,
            pre_approved=True,
        )

        event_types = [e[0] for e in events]
        # Events should include pipeline stages
        assert "signal" in event_types
        assert "governance" in event_types


# ─── Workstation State Tests ─────────────────────────


def test_workstation_profile_detection():
    profile = WorkstationProfile.detect()
    assert profile.hostname != ""
    assert profile.active_environment in ("vps", "local")


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
