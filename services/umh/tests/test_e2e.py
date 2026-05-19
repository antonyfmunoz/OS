"""End-to-end test for UMH trace, proof, memory candidate, and workstation state.

Tests the full lifecycle: create trace → store proof → classify outcome →
generate memory candidate → update workstation state → query trace → build resume.

Produces JSON proof samples in the job directory.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.umh.memory.candidate_generator import (
    MemoryCandidate,
    MemoryCandidateGenerator,
    PromotionStatus,
)
from services.umh.observability.outcome_classifier import (
    ClassificationResult,
    OutcomeCategory,
    OutcomeClassifier,
)
from services.umh.observability.proof_store import ProofArtifact, ProofStore
from services.umh.observability.trace_store import Trace, TraceStatus, TraceStore
from services.umh.orchestrator import Orchestrator
from services.umh.workstation.state import (
    ResumeState,
    WorkstationProfile,
    WorkstationSessionState,
    WorkstationSnapshot,
    WorkstationStateManager,
)

PASS = 0
FAIL = 0
PROOF_SAMPLES: dict[str, dict] = {}


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name} — {detail}")


def test_trace_store() -> None:
    print("\n--- TraceStore ---")
    with tempfile.TemporaryDirectory() as td:
        store = TraceStore(td)

        trace = store.create_trace(
            "test signal: user requested dashboard build",
            interpretation_ref="interp-001",
            governance_decision="approved",
            work_packet={"task": "build dashboard", "priority": "high"},
            adapter_used="discord",
            environment="vps",
            metadata={"session": "test-session-001"},
        )
        check("trace created", trace.trace_id.startswith("trace-"))
        check("trace status pending", trace.status == TraceStatus.PENDING)
        check("trace input preserved", "dashboard" in trace.input_signal)

        store.update_trace(
            trace.trace_id,
            status=TraceStatus.RUNNING,
            started_at="2026-05-18T10:00:00+00:00",
        )

        store.update_trace(
            trace.trace_id,
            status=TraceStatus.COMPLETED,
            execution_result={"success": True, "output": "dashboard built"},
            outcome="success",
            outcome_detail="completed successfully",
            completed_at="2026-05-18T10:01:00+00:00",
        )

        retrieved = store.get_trace(trace.trace_id)
        check("trace retrieved", retrieved is not None)
        check("trace status completed", retrieved.status == TraceStatus.COMPLETED)
        check("trace outcome success", retrieved.outcome == "success")

        results = store.query_traces(status=TraceStatus.COMPLETED)
        check("query by status", len(results) == 1)
        check("query has trace_id", results[0]["trace_id"] == trace.trace_id)

        recent = store.recent_traces(5)
        check("recent traces", len(recent) == 1)

        check("trace count", store.count() == 1)

        PROOF_SAMPLES["trace"] = retrieved.to_dict()


def test_proof_store() -> None:
    print("\n--- ProofStore ---")
    with tempfile.TemporaryDirectory() as td:
        store = ProofStore(td)

        proof = store.store_proof(
            trace_id="trace-abc123",
            proof_type="test_result",
            content={
                "test_name": "test_dashboard_build",
                "passed": True,
                "assertions": 5,
                "duration_ms": 120,
            },
            summary="All 5 assertions passed in 120ms",
        )
        check("proof created", proof.proof_id.startswith("proof-"))
        check("proof type", proof.proof_type == "test_result")

        retrieved = store.get_proof(proof.proof_id)
        check("proof retrieved", retrieved is not None)
        check("proof content", retrieved.content["passed"] is True)

        by_trace = store.proofs_for_trace("trace-abc123")
        check("proofs for trace", len(by_trace) == 1)

        recent = store.recent_proofs(5)
        check("recent proofs", len(recent) == 1)

        PROOF_SAMPLES["proof_artifact"] = proof.to_dict()


def test_outcome_classifier() -> None:
    print("\n--- OutcomeClassifier ---")
    classifier = OutcomeClassifier()

    r = classifier.classify({"success": True, "output": "done"})
    check("success classified", r.category == OutcomeCategory.SUCCESS)

    r = classifier.classify({"error": "connection refused"})
    check("error classified", r.category == OutcomeCategory.ERROR)

    r = classifier.classify({"exit_code": 1})
    check("failure classified", r.category == OutcomeCategory.FAILURE)

    r = classifier.classify({"timeout": True, "timeout_detail": "30s exceeded"})
    check("timeout classified", r.category == OutcomeCategory.TIMEOUT)

    r = classifier.classify({"skipped": True, "skip_reason": "not applicable"})
    check("skipped classified", r.category == OutcomeCategory.SKIPPED)

    r = classifier.classify({"partial": True, "partial_detail": "3 of 5 tasks done"})
    check("partial classified", r.category == OutcomeCategory.PARTIAL)

    r = classifier.classify({})
    check("empty → unknown", r.category == OutcomeCategory.UNKNOWN)

    r = classifier.classify({"output": "some data"})
    check("output-only → success", r.category == OutcomeCategory.SUCCESS)


def test_memory_candidate_generator() -> None:
    print("\n--- MemoryCandidateGenerator ---")
    with tempfile.TemporaryDirectory() as td:
        gen = MemoryCandidateGenerator(td)

        candidate = gen.generate_candidate(
            source_trace_id="trace-abc123",
            content="Dashboard build pattern works with adapter=discord",
            reason="successful execution pattern worth remembering",
            confidence=0.8,
            scope="project",
            tags=["dashboard", "discord", "pattern"],
        )
        check("candidate created", candidate.candidate_id.startswith("memcand-"))
        check("candidate staged", candidate.promotion_status == PromotionStatus.STAGED)
        check("candidate content", "Dashboard" in candidate.content)

        auto = gen.generate_from_trace(
            trace_id="trace-def456",
            input_signal="user requested KPI report generation",
            outcome="success",
            outcome_detail="report generated with 12 metrics",
            execution_result={"output": "report.pdf", "adapter": "operator_api"},
        )
        check("auto-candidate created", auto is not None)
        check("auto-candidate tagged", "auto-generated" in auto.tags)

        skipped = gen.generate_from_trace(
            trace_id="trace-ghi789",
            input_signal="failed task",
            outcome="failure",
            outcome_detail="connection refused",
        )
        check("failure not candidated", skipped is None)

        candidates = gen.get_candidates()
        check("candidates persisted", len(candidates) == 2)

        by_trace = gen.get_candidates(trace_id="trace-abc123")
        check("query by trace", len(by_trace) == 1)

        check("candidate count", gen.count() == 2)

        PROOF_SAMPLES["memory_candidate"] = candidate.to_dict()


def test_workstation_state() -> None:
    print("\n--- WorkstationState ---")
    with tempfile.TemporaryDirectory() as td:
        manager = WorkstationStateManager(td)

        profile = WorkstationProfile.detect(user_id="antony", session_id="session-d")
        check("profile detected", profile.hostname != "")
        check("profile env", profile.active_environment in ("vps", "local"))

        session = WorkstationSessionState()
        session.record_activity("trace-001", "success")
        session.record_activity("trace-002", "failure")
        session.record_error()
        session.candidate_count = 1
        check("session traces", session.trace_count == 2)
        check("session errors", session.error_count == 1)

        recent_traces = [
            {
                "trace_id": "trace-002",
                "status": "failed",
                "outcome": "failure",
                "input_signal_preview": "failed task",
            },
            {
                "trace_id": "trace-001",
                "status": "completed",
                "outcome": "success",
                "input_signal_preview": "successful task",
            },
        ]

        snapshot = manager.build_snapshot(profile, session, recent_traces)
        check("snapshot built", snapshot.snapshot_at != "")
        check("resume summary", "2 traces" in snapshot.resume.resume_summary)
        check("resume errors", "1 error" in snapshot.resume.resume_summary)
        check("resume actions", len(snapshot.resume.next_suggested_actions) > 0)
        check(
            "resume has review errors",
            any("error" in a.lower() for a in snapshot.resume.next_suggested_actions),
        )

        loaded = manager.load_snapshot()
        check("snapshot persisted", loaded is not None)
        check("snapshot round-trip", loaded.profile.user_id == "antony")

        PROOF_SAMPLES["resume_state"] = snapshot.to_dict()


def test_orchestrator_e2e() -> None:
    print("\n--- Orchestrator E2E ---")
    with tempfile.TemporaryDirectory() as td:
        orch = Orchestrator(td)

        result = orch.execute_trace(
            "build sales dashboard with KPI overlay",
            interpretation_ref="interp-sales-001",
            governance_decision="approved by CEO agent",
            work_packet={"task": "sales_dashboard", "priority": "high"},
            adapter_used="discord",
            execution_result={
                "success": True,
                "output": "Dashboard built with 8 KPIs",
                "exit_code": 0,
            },
            proof_content={
                "screenshot": "dashboard_v1.png",
                "kpi_count": 8,
                "render_time_ms": 340,
            },
            metadata={"source": "e2e_test"},
        )
        check("orch trace_id", result["trace_id"].startswith("trace-"))
        check("orch status completed", result["status"] == TraceStatus.COMPLETED)
        check("orch outcome success", result["outcome"] == "success")
        check("orch proof created", result["proof_artifact_id"].startswith("proof-"))
        check("orch candidate created", result["memory_candidate_id"].startswith("memcand-"))

        result2 = orch.execute_trace(
            "send outreach emails to 50 leads",
            execution_result={"error": "SMTP connection refused", "exit_code": 1},
        )
        check("orch failure detected", result2["outcome"] in ("error", "failure"))
        check("orch no candidate for failure", result2["memory_candidate_id"] == "")

        traces_resp = orch.get_traces()
        check("get_traces total", traces_resp["total"] == 2)
        check("get_traces list", len(traces_resp["traces"]) == 2)

        detail = orch.get_trace_detail(result["trace_id"])
        check("trace detail found", detail is not None)
        check("trace detail has proofs", len(detail["proofs"]) == 1)
        check("trace detail has candidates", len(detail["memory_candidates"]) == 1)

        resume = orch.get_resume()
        check("resume has profile", "profile" in resume)
        check("resume has session", "session" in resume)
        check("resume has resume", "resume" in resume)
        check("resume trace count", resume["session"]["trace_count"] == 2)
        check("resume error count", resume["session"]["error_count"] == 1)

        stats = orch.get_stats()
        check("stats traces", stats["traces"] == 2)
        check("stats candidates", stats["candidates"] == 1)

        PROOF_SAMPLES["orchestrator_result"] = result
        PROOF_SAMPLES["orchestrator_resume"] = resume


def save_proof_samples() -> None:
    job_dir = Path("/root/.claude/jobs/d690beb6")
    job_dir.mkdir(parents=True, exist_ok=True)
    out = job_dir / "proof_samples.json"
    out.write_text(json.dumps(PROOF_SAMPLES, indent=2))
    print(f"\nProof samples saved to {out}")


def main() -> None:
    print("=" * 60)
    print("UMH E2E Test Suite")
    print("=" * 60)

    test_trace_store()
    test_proof_store()
    test_outcome_classifier()
    test_memory_candidate_generator()
    test_workstation_state()
    test_orchestrator_e2e()

    save_proof_samples()

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    if FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
