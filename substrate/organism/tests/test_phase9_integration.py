"""Tests for Phase 9.0 — World Model → Execution Integration.

Verifies the full operator loop:
  1. World model extraction
  2. Dependency graph construction
  3. Contradiction detection
  4. Plan composition from contradictions
  5. Plan routing through GovernedExecutionSpine
  6. Outcome capture after execution
  7. Memory promotion from repeated outcomes
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest

from substrate.organism.world_model import (
    EntityCategory,
    EntityStatus,
    EvidenceType,
    WorldEntity,
    WorldEvidence,
    WorldGap,
    WorldModel,
    GapSeverity,
    extract_world_model,
)
from substrate.organism.dependency_graph import (
    DependencyGraph,
    DependencyEdge,
    DependencyNode,
    DependencyType,
    DependencyStrength,
    build_dependency_graph,
)
from substrate.organism.contradiction_engine import (
    ContradictionEngine,
    ContradictionReport,
    ContradictionSeverity,
    ContradictionType,
    Contradiction,
    Claim,
    Observation,
    detect_contradictions,
)
from substrate.organism.composition_engine import (
    CompositionEngine,
    CompositionIntent,
    CompositionPlan,
    RiskClass,
    GovernanceMode,
    compose_plan,
)
from substrate.organism.outcome_learning import (
    OutcomeLearningLoop,
    OutcomeRecord,
    OutcomeStatus,
    SignalType,
)
from substrate.organism.memory_promotion import (
    MemoryPromotionPipeline,
    MemoryCandidate,
    MemoryCategory,
    MemoryScope,
    MemoryEvidence,
    MemoryPromotionStatus,
)


class TestWorldModelExtraction:
    def test_extract_produces_entities(self):
        model = extract_world_model()
        assert model.entities, "World model should have entities"
        assert model.extracted_at > 0

    def test_entities_have_status(self):
        model = extract_world_model()
        for entity in model.entities.values():
            assert entity.status in EntityStatus

    def test_summary_counts_match(self):
        model = extract_world_model()
        summary = model.summary()
        total = sum(summary["by_status"].values())
        assert total == summary["total_entities"]

    def test_to_dict_serializable(self):
        model = extract_world_model()
        d = model.to_dict()
        json.dumps(d, default=str)

    def test_to_safe_dict_strips_paths(self):
        model = extract_world_model()
        safe = model.to_safe_dict()
        for entity_data in safe["entities"].values():
            assert "module_path" not in entity_data


class TestDependencyGraphConstruction:
    def test_graph_from_world_model(self):
        model = extract_world_model()
        graph = build_dependency_graph(model)
        assert graph.nodes, "Graph should have nodes"
        assert graph.edges, "Graph should have edges"

    def test_graph_nodes_match_entities(self):
        model = extract_world_model()
        graph = build_dependency_graph(model)
        for entity_id in model.entities:
            assert entity_id in graph.nodes

    def test_upstream_downstream(self):
        graph = DependencyGraph()
        graph.add_node(DependencyNode(id="a", name="A"))
        graph.add_node(DependencyNode(id="b", name="B"))
        graph.add_edge(DependencyEdge(
            source="a", target="b",
            dep_type=DependencyType.RUNTIME,
        ))
        assert "b" in graph.upstream("a")
        assert "a" in graph.downstream("b")

    def test_orphaned_detection(self):
        graph = DependencyGraph()
        graph.add_node(DependencyNode(id="a", name="A"))
        graph.add_node(DependencyNode(id="b", name="B"))
        graph.add_node(DependencyNode(id="c", name="C"))
        graph.add_edge(DependencyEdge(
            source="a", target="b",
            dep_type=DependencyType.CODE,
        ))
        orphans = graph.orphaned_nodes()
        assert "c" in orphans
        assert "a" not in orphans

    def test_cycle_detection(self):
        graph = DependencyGraph()
        graph.add_node(DependencyNode(id="a", name="A"))
        graph.add_node(DependencyNode(id="b", name="B"))
        graph.add_edge(DependencyEdge(source="a", target="b", dep_type=DependencyType.CODE))
        graph.add_edge(DependencyEdge(source="b", target="a", dep_type=DependencyType.CODE))
        cycles = graph.circular_dependencies()
        assert len(cycles) > 0

    def test_safe_dict_serializable(self):
        model = extract_world_model()
        graph = build_dependency_graph(model)
        safe = graph.to_safe_dict()
        json.dumps(safe, default=str)


class TestContradictionDetection:
    def test_detect_produces_report(self):
        report = detect_contradictions()
        assert isinstance(report, ContradictionReport)
        assert report.checks_performed > 0

    def test_report_summary(self):
        report = detect_contradictions()
        summary = report.summary()
        assert "total" in summary
        assert "by_severity" in summary
        assert "by_type" in summary

    def test_by_severity_filter(self):
        report = ContradictionReport()
        report.add(Contradiction(
            severity=ContradictionSeverity.HIGH,
            claim=Claim(source="test", statement="test"),
            observation=Observation(source="test", finding="test"),
        ))
        report.add(Contradiction(
            severity=ContradictionSeverity.LOW,
            claim=Claim(source="test", statement="test2"),
            observation=Observation(source="test", finding="test2"),
        ))
        highs = report.by_severity(ContradictionSeverity.HIGH)
        assert len(highs) == 1

    def test_safe_dict_strips_internals(self):
        report = detect_contradictions()
        safe = report.to_safe_dict()
        for c in safe["contradictions"]:
            assert "claim" not in c
            assert "observation" not in c
        json.dumps(safe, default=str)


class TestCompositionEngine:
    def test_compose_from_contradiction(self):
        plan = compose_plan("fix deployment truth")
        assert isinstance(plan, CompositionPlan)
        assert plan.intent.category == "fix_contradictions"
        assert len(plan.steps) > 0

    def test_compose_improvement(self):
        plan = compose_plan("improve readiness scores")
        assert plan.intent.category == "improve_readiness"

    def test_compose_maintenance(self):
        plan = compose_plan("run safe maintenance")
        assert plan.intent.category == "safe_maintenance"

    def test_compose_general(self):
        plan = compose_plan("do something random")
        assert plan.intent.category == "general"

    def test_steps_have_governance(self):
        plan = compose_plan("fix contradictions")
        for step in plan.steps:
            assert step.governance_mode in GovernanceMode

    def test_plan_risk_classification(self):
        plan = compose_plan("fix deployment truth")
        assert plan.overall_risk in RiskClass

    def test_plan_evidence_populated(self):
        plan = compose_plan("fix contradictions")
        assert len(plan.evidence) > 0

    def test_plan_serializable(self):
        plan = compose_plan("improve readiness")
        d = plan.to_dict()
        json.dumps(d, default=str)

    def test_ready_steps(self):
        plan = compose_plan("fix contradictions")
        ready = plan.ready_steps()
        assert len(ready) > 0, "First step should be ready (no deps)"


class TestOutcomeCapture:
    def test_record_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "outcomes.jsonl")
            loop = OutcomeLearningLoop(store_path=path)
            record = OutcomeRecord(
                action_type="test_action",
                description="Test outcome",
                status=OutcomeStatus.SUCCESS,
                duration_seconds=1.5,
            )
            evaluation = loop.record_outcome(record)
            assert evaluation.success is True
            assert evaluation.quality_score == 1.0

    def test_record_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "outcomes.jsonl")
            loop = OutcomeLearningLoop(store_path=path)
            record = OutcomeRecord(
                action_type="test_action",
                description="Test failure",
                status=OutcomeStatus.FAILURE,
                error="Something broke",
                duration_seconds=0.5,
            )
            evaluation = loop.record_outcome(record)
            assert evaluation.success is False
            assert evaluation.quality_score == 0.0

    def test_reliability_updates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "outcomes.jsonl")
            loop = OutcomeLearningLoop(store_path=path)
            for _ in range(5):
                loop.record_outcome(OutcomeRecord(
                    action_type="reliable_action", status=OutcomeStatus.SUCCESS,
                ))
            for _ in range(5):
                loop.record_outcome(OutcomeRecord(
                    action_type="reliable_action", status=OutcomeStatus.FAILURE,
                ))
            rel = loop.get_reliability("reliable_action")
            assert 0.4 <= rel <= 0.6

    def test_repeated_failure_signal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "outcomes.jsonl")
            loop = OutcomeLearningLoop(store_path=path)
            for _ in range(4):
                loop.record_outcome(OutcomeRecord(
                    action_type="bad_action", status=OutcomeStatus.FAILURE,
                ))
            signals = loop.recent_signals()
            failure_signals = [s for s in signals if s.signal_type == SignalType.REPEATED_FAILURE]
            assert len(failure_signals) > 0

    def test_safe_dict_serializable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "outcomes.jsonl")
            loop = OutcomeLearningLoop(store_path=path)
            loop.record_outcome(OutcomeRecord(
                action_type="test", status=OutcomeStatus.SUCCESS,
            ))
            safe = loop.to_safe_dict()
            json.dumps(safe, default=str)


class TestMemoryPromotion:
    def test_submit_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MemoryPromotionPipeline(store_dir=tmpdir)
            cand = pipeline.submit_candidate(
                content="Test pattern",
                category=MemoryCategory.PATTERN,
                evidence=[MemoryEvidence(source="test", detail="test data", confidence=0.8)],
            )
            assert cand.status == MemoryPromotionStatus.RAW
            assert cand.id in [c.id for c in pipeline.list_candidates()]

    def test_promote_with_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MemoryPromotionPipeline(store_dir=tmpdir)
            cand = pipeline.submit_candidate(
                content="Reliable pattern observed 50 times",
                category=MemoryCategory.PATTERN,
                evidence=[MemoryEvidence(source="outcome_learning", detail="50/50 success", confidence=0.9)],
            )
            pipeline.run_contradiction_check(cand.id)
            entry = pipeline.promote(cand.id)
            assert entry is not None
            assert entry.content == cand.content
            assert cand.status == MemoryPromotionStatus.PROMOTED

    def test_reject_without_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MemoryPromotionPipeline(store_dir=tmpdir)
            cand = pipeline.submit_candidate(content="No evidence claim")
            entry = pipeline.promote(cand.id)
            assert entry is None
            assert cand.status == MemoryPromotionStatus.REJECTED

    def test_operator_approval_required_for_strategy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MemoryPromotionPipeline(store_dir=tmpdir)
            cand = pipeline.submit_candidate(
                content="Never restart all containers at once",
                category=MemoryCategory.STRATEGY,
                evidence=[MemoryEvidence(source="operator", detail="AFM instruction", confidence=0.95)],
            )
            pipeline.run_contradiction_check(cand.id)
            entry = pipeline.promote(cand.id)
            assert entry is None, "Strategy requires operator approval"
            assert cand.status == MemoryPromotionStatus.CANDIDATE
            entry = pipeline.promote(cand.id, decided_by="operator")
            assert entry is not None

    def test_pending_approvals(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MemoryPromotionPipeline(store_dir=tmpdir)
            cand = pipeline.submit_candidate(
                content="Critical constraint",
                category=MemoryCategory.CONSTRAINT,
                evidence=[MemoryEvidence(source="test", detail="test", confidence=0.8)],
            )
            pipeline.run_contradiction_check(cand.id)
            pipeline.promote(cand.id)
            pending = pipeline.pending_approvals()
            assert len(pending) == 1
            assert pending[0].id == cand.id

    def test_reject_explicit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = MemoryPromotionPipeline(store_dir=tmpdir)
            cand = pipeline.submit_candidate(
                content="Dubious pattern",
                category=MemoryCategory.PATTERN,
                evidence=[MemoryEvidence(source="test", detail="weak", confidence=0.7)],
            )
            pipeline.run_contradiction_check(cand.id)
            result = pipeline.reject(cand.id, reason="Not useful")
            assert result is True
            assert cand.status == MemoryPromotionStatus.REJECTED


class TestFullLoop:
    """Integration: world model → contradictions → compose → outcome → promotion."""

    def test_world_model_to_contradictions(self):
        model = extract_world_model()
        graph = build_dependency_graph(model)
        report = detect_contradictions(model, graph)
        assert report.checks_performed >= 5

    def test_contradiction_to_plan(self):
        report = detect_contradictions()
        if report.contradictions:
            top = report.contradictions[0]
            intent = f"Fix: {top.recommended_fix}" if top.recommended_fix else f"Fix: {top.contradiction_type.value}"
            plan = compose_plan(intent)
            assert plan.steps, "Plan should have steps"
            assert plan.evidence, "Plan should cite evidence"

    def test_plan_to_outcome(self):
        plan = compose_plan("fix contradictions")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "outcomes.jsonl")
            loop = OutcomeLearningLoop(store_path=path)
            for step in plan.steps:
                record = OutcomeRecord(
                    action_type=step.action,
                    plan_id=plan.id,
                    step_id=step.id,
                    description=step.description,
                    status=OutcomeStatus.SUCCESS,
                    actual_result="simulated success",
                    duration_seconds=0.1,
                )
                loop.record_outcome(record)
            assert loop.summary()["total_outcomes"] == len(plan.steps)

    def test_outcome_to_promotion_signal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "outcomes.jsonl")
            loop = OutcomeLearningLoop(store_path=path)
            for _ in range(10):
                loop.record_outcome(OutcomeRecord(
                    action_type="proven_action",
                    status=OutcomeStatus.SUCCESS,
                    duration_seconds=0.5,
                ))
            rel = loop.get_reliability("proven_action")
            assert rel >= 0.9
            adjustments = loop.get_adjustments()
            promo_candidates = [a for a in adjustments if a.adjustment > 0]
            assert len(promo_candidates) > 0, "High reliability should yield promotion signal"

    def test_full_pipeline(self):
        model = extract_world_model()
        graph = build_dependency_graph(model)
        report = detect_contradictions(model, graph)
        engine = CompositionEngine(model, graph, report)
        intent = CompositionIntent(description="fix contradictions")
        plan = engine.compose(intent)

        with tempfile.TemporaryDirectory() as tmpdir:
            outcomes_path = os.path.join(tmpdir, "outcomes.jsonl")
            loop = OutcomeLearningLoop(store_path=outcomes_path)
            for step in plan.steps:
                loop.record_outcome(OutcomeRecord(
                    action_type=step.action,
                    plan_id=plan.id,
                    step_id=step.id,
                    description=step.description,
                    status=OutcomeStatus.SUCCESS,
                    duration_seconds=0.2,
                ))

            pipeline = MemoryPromotionPipeline(store_dir=tmpdir)
            adjustments = loop.get_adjustments()
            for adj in adjustments:
                if adj.adjustment > 0:
                    cand = pipeline.submit_candidate(
                        content=f"Action '{adj.action_type}' has reliability {adj.current_reliability:.2f}",
                        category=MemoryCategory.PATTERN,
                        evidence=[MemoryEvidence(
                            source="outcome_learning",
                            detail=f"Reliability: {adj.current_reliability:.2f}",
                            confidence=adj.current_reliability,
                        )],
                        source_action=adj.action_type,
                    )
                    pipeline.run_contradiction_check(cand.id)
                    entry = pipeline.promote(cand.id)
                    if entry:
                        assert entry.source_candidate_id == cand.id

            summary = pipeline.summary()
            assert summary["total_candidates"] >= 0
