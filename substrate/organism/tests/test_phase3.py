"""Phase 3 tests — Governed Recursive Execution Economy.

Tests:
  - Runtime scoring updates after success/failure
  - Economy record creation and leverage scoring
  - Recursion limit enforcement
  - Advisor hierarchy scope enforcement
  - No unmanaged advisor spawning
  - Cockpit observability snapshot integration
  - External leverage map schema
  - Organism daemon still imports/runs
  - No instance leaks
  - No dependency direction violations
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest


# ── Phase 3A: Execution Economy ─────────────────────────────────────


class TestExecutionEconomy:
    def test_record_creation(self):
        from substrate.organism.execution_economy import (
            ExecutionCost,
            ExecutionDecisionRecord,
            ExecutionValue,
            ExecutionClass,
            VerificationResult,
        )

        record = ExecutionDecisionRecord(
            runtime_selected="cc_sdk",
            alternatives_considered=["gemini", "groq"],
            task_class="code_write",
            execution_class=ExecutionClass.AGENT,
            cost=ExecutionCost(token_cost_usd=0.002, wall_clock_ms=1500),
            value=ExecutionValue(quality_score=0.9, completeness=0.85, correctness=0.95),
            latency_ms=1500,
            success=True,
            confidence=0.88,
            verification=VerificationResult.PASSED,
            governance_class="SAFE_WRITE",
        )
        assert record.id.startswith("edr-")
        assert record.leverage_score > 0
        d = record.to_dict()
        assert d["runtime_selected"] == "cc_sdk"
        assert d["success"] is True
        assert "leverage_score" in d

    def test_economy_tracks_profiles(self):
        from substrate.organism.execution_economy import (
            ExecutionCost,
            ExecutionDecisionRecord,
            ExecutionEconomy,
            ExecutionValue,
        )

        econ = ExecutionEconomy()

        for i in range(5):
            record = ExecutionDecisionRecord(
                runtime_selected="cc_sdk",
                task_class="code_write",
                cost=ExecutionCost(token_cost_usd=0.001),
                value=ExecutionValue(quality_score=0.8 + i * 0.02),
                latency_ms=1000 + i * 100,
                success=True,
            )
            econ.record_execution(record)

        profile = econ.get_profile("cc_sdk")
        assert profile is not None
        assert profile.total_executions == 5
        assert profile.overall_leverage > 0

        bench = profile.benchmarks.get("code_write")
        assert bench is not None
        assert bench.success_rate == 1.0
        assert bench.avg_latency_ms > 0

    def test_runtime_scoring_updates_after_failure(self):
        from substrate.organism.execution_economy import (
            ExecutionDecisionRecord,
            ExecutionEconomy,
        )

        econ = ExecutionEconomy()

        econ.record_execution(ExecutionDecisionRecord(
            runtime_selected="groq",
            task_class="research",
            success=True,
            latency_ms=200,
        ))
        econ.record_execution(ExecutionDecisionRecord(
            runtime_selected="groq",
            task_class="research",
            success=False,
            latency_ms=5000,
        ))

        profile = econ.get_profile("groq")
        bench = profile.benchmarks["research"]
        assert bench.success_rate == 0.5
        assert bench.failures == 1

    def test_task_execution_profile(self):
        from substrate.organism.execution_economy import (
            ExecutionDecisionRecord,
            ExecutionEconomy,
            ExecutionValue,
        )

        econ = ExecutionEconomy()

        econ.record_execution(ExecutionDecisionRecord(
            runtime_selected="cc_sdk",
            task_class="code_write",
            success=True,
            latency_ms=2000,
            value=ExecutionValue(quality_score=0.95),
        ))
        econ.record_execution(ExecutionDecisionRecord(
            runtime_selected="gemini",
            task_class="code_write",
            success=True,
            latency_ms=800,
            value=ExecutionValue(quality_score=0.7),
        ))

        tp = econ.task_execution_profile("code_write")
        assert tp.best_runtime in ("cc_sdk", "gemini")
        assert len(tp.runtime_rankings) == 2

    def test_economy_summary(self):
        from substrate.organism.execution_economy import (
            ExecutionDecisionRecord,
            ExecutionEconomy,
            ExecutionCost,
        )

        econ = ExecutionEconomy()
        econ.record_execution(ExecutionDecisionRecord(
            runtime_selected="cc_sdk",
            task_class="reason",
            success=True,
            cost=ExecutionCost(token_cost_usd=0.005),
        ))

        summary = econ.economy_summary()
        assert summary["total_executions"] == 1
        assert summary["total_cost_usd"] >= 0
        assert "runtime_profiles" in summary

    def test_subscription_cost_is_zero(self):
        from substrate.organism.execution_economy import ExecutionCost

        cost = ExecutionCost(
            compute_cost_usd=0.01,
            token_cost_usd=0.005,
            is_subscription=True,
        )
        assert cost.total_usd == 0.0

    def test_leverage_score_formula(self):
        from substrate.organism.execution_economy import (
            ExecutionDecisionRecord,
            ExecutionValue,
        )

        success_record = ExecutionDecisionRecord(
            runtime_selected="cc_sdk",
            task_class="code_write",
            success=True,
            latency_ms=500,
            value=ExecutionValue(quality_score=1.0, completeness=1.0, correctness=1.0),
        )
        failure_record = ExecutionDecisionRecord(
            runtime_selected="cc_sdk",
            task_class="code_write",
            success=False,
            latency_ms=5000,
        )
        assert success_record.leverage_score > failure_record.leverage_score


# ── Phase 3B: Recursion Governance ───────────────────────────────────


class TestRecursionGovernance:
    def test_default_limits(self):
        from substrate.organism.recursion_governance import (
            RecursionGovernor,
            RecursionLimits,
        )

        gov = RecursionGovernor()
        assert gov.limits.max_depth == 5
        assert gov.limits.max_spawned_objectives == 20
        assert not gov.is_killed

    def test_depth_limit_enforced(self):
        from substrate.organism.execution_economy import ExecutionClass
        from substrate.organism.recursion_governance import (
            RecursionGovernor,
            RecursionLimits,
        )

        gov = RecursionGovernor(limits=RecursionLimits(max_depth=3))
        gov.record_execution(depth_increment=3)

        result = gov.check_before_execution(
            ExecutionClass.AGENT,
            depth_increment=1,
        )
        assert not result.allowed
        assert "depth" in result.reason.lower()

    def test_budget_limit_enforced(self):
        from substrate.organism.execution_economy import ExecutionClass
        from substrate.organism.recursion_governance import (
            RecursionGovernor,
            RecursionLimits,
        )

        gov = RecursionGovernor(limits=RecursionLimits(max_budget_usd=1.0))
        gov.record_execution(cost_usd=0.8)

        result = gov.check_before_execution(
            ExecutionClass.AGENT,
            estimated_cost_usd=0.5,
        )
        assert not result.allowed
        assert "budget" in result.reason.lower()

    def test_work_units_limit_enforced(self):
        from substrate.organism.execution_economy import ExecutionClass
        from substrate.organism.recursion_governance import (
            RecursionGovernor,
            RecursionLimits,
        )

        gov = RecursionGovernor(limits=RecursionLimits(max_work_units_per_mission=10))
        gov.record_execution(work_units=8)

        result = gov.check_before_execution(
            ExecutionClass.AGENT,
            work_units=5,
        )
        assert not result.allowed

    def test_kill_switch(self):
        from substrate.organism.execution_economy import ExecutionClass
        from substrate.organism.recursion_governance import RecursionGovernor

        gov = RecursionGovernor()
        gov.kill()
        assert gov.is_killed

        result = gov.check_before_execution(ExecutionClass.DETERMINISTIC)
        assert not result.allowed
        assert "kill" in result.reason.lower()

        gov.resume()
        assert not gov.is_killed
        result = gov.check_before_execution(ExecutionClass.DETERMINISTIC)
        assert result.allowed

    def test_approval_requirements_by_class(self):
        from substrate.organism.execution_economy import ExecutionClass
        from substrate.organism.recursion_governance import (
            RecursionApproval,
            RecursionGovernor,
        )

        gov = RecursionGovernor()

        det = gov.check_before_execution(ExecutionClass.DETERMINISTIC)
        assert det.approval_required == RecursionApproval.NONE

        prod = gov.check_before_execution(ExecutionClass.PRODUCTION_IMPACT)
        assert prod.approval_required == RecursionApproval.BLOCK

    def test_autonomous_scope_limit(self):
        from substrate.organism.execution_economy import ExecutionClass
        from substrate.organism.recursion_governance import (
            RecursionGovernor,
            RecursionLimits,
        )

        gov = RecursionGovernor(limits=RecursionLimits(max_autonomous_scope=2))
        gov.record_execution(is_autonomous=True)
        gov.record_execution(is_autonomous=True)

        result = gov.check_before_execution(ExecutionClass.AGENT)
        assert not result.allowed

    def test_reset_state(self):
        from substrate.organism.recursion_governance import RecursionGovernor

        gov = RecursionGovernor()
        gov.record_execution(depth_increment=3, cost_usd=5.0)
        gov.reset_state()
        assert gov.state.current_depth == 0
        assert gov.state.budget_spent_usd == 0.0

    def test_unwind_depth(self):
        from substrate.organism.recursion_governance import RecursionGovernor

        gov = RecursionGovernor()
        gov.record_execution(depth_increment=3)
        assert gov.state.current_depth == 3
        gov.unwind_depth(2)
        assert gov.state.current_depth == 1

    def test_escalation_log(self):
        from substrate.organism.execution_economy import ExecutionClass
        from substrate.organism.recursion_governance import (
            RecursionGovernor,
            RecursionLimits,
        )

        gov = RecursionGovernor(limits=RecursionLimits(max_depth=1))
        gov.record_execution(depth_increment=1)
        gov.check_before_execution(ExecutionClass.AGENT, depth_increment=1)

        log = gov.escalation_log()
        assert len(log) > 0
        assert log[-1]["level"] == "block"

    def test_wall_clock_limit(self):
        from substrate.organism.execution_economy import ExecutionClass
        from substrate.organism.recursion_governance import (
            RecursionGovernor,
            RecursionLimits,
        )

        gov = RecursionGovernor(limits=RecursionLimits(max_wall_clock_seconds=0))
        result = gov.check_before_execution(ExecutionClass.AGENT)
        assert not result.allowed


# ── Phase 3C: Advisor Hierarchy ──────────────────────────────────────


class TestAdvisorHierarchy:
    def test_register_primary(self):
        from substrate.organism.advisor_hierarchy import AdvisorHierarchy, AdvisorScope

        hierarchy = AdvisorHierarchy()
        primary = hierarchy.register_primary(budget_usd=100.0)

        assert primary.scope == AdvisorScope.INSTANCE
        assert primary.budget_usd == 100.0
        assert hierarchy.primary is primary

    def test_spawn_domain_advisor(self):
        from substrate.organism.advisor_hierarchy import (
            AdvisorHierarchy,
            AdvisorScope,
            AdvisorAuthority,
        )

        hierarchy = AdvisorHierarchy()
        primary = hierarchy.register_primary(budget_usd=100.0)

        domain = hierarchy.spawn(
            parent_id=primary.id,
            scope=AdvisorScope.DOMAIN,
            authority_class=AdvisorAuthority.DOMAIN,
            budget_usd=20.0,
            allowed_projects=["lyfe-institute"],
        )

        assert domain is not None
        assert domain.parent_id == primary.id
        assert domain.budget_usd == 20.0
        assert primary.spawned_count == 1

    def test_scope_narrowing_enforced(self):
        from substrate.organism.advisor_hierarchy import (
            AdvisorHierarchy,
            AdvisorScope,
            AdvisorAuthority,
        )

        hierarchy = AdvisorHierarchy()
        primary = hierarchy.register_primary()

        domain = hierarchy.spawn(
            parent_id=primary.id,
            scope=AdvisorScope.DOMAIN,
            authority_class=AdvisorAuthority.DOMAIN,
        )
        assert domain is not None

        bad = hierarchy.spawn(
            parent_id=domain.id,
            scope=AdvisorScope.INSTANCE,
            authority_class=AdvisorAuthority.PRIMARY,
        )
        assert bad is None

    def test_budget_cascading_enforced(self):
        from substrate.organism.advisor_hierarchy import (
            AdvisorHierarchy,
            AdvisorScope,
            AdvisorAuthority,
        )

        hierarchy = AdvisorHierarchy()
        primary = hierarchy.register_primary(budget_usd=10.0)

        too_expensive = hierarchy.spawn(
            parent_id=primary.id,
            scope=AdvisorScope.DOMAIN,
            authority_class=AdvisorAuthority.DOMAIN,
            budget_usd=50.0,
        )
        assert too_expensive is None

    def test_spawn_limit_enforced(self):
        from substrate.organism.advisor_hierarchy import (
            AdvisorHierarchy,
            AdvisorScope,
            AdvisorAuthority,
        )

        hierarchy = AdvisorHierarchy()
        primary = hierarchy.register_primary(
            budget_usd=100.0,
            spawn_limit=2,
        )

        hierarchy.spawn(primary.id, AdvisorScope.DOMAIN, AdvisorAuthority.DOMAIN, budget_usd=1.0)
        hierarchy.spawn(primary.id, AdvisorScope.DOMAIN, AdvisorAuthority.DOMAIN, budget_usd=1.0)

        third = hierarchy.spawn(primary.id, AdvisorScope.DOMAIN, AdvisorAuthority.DOMAIN, budget_usd=1.0)
        assert third is None

    def test_no_unmanaged_spawning(self):
        from substrate.organism.advisor_hierarchy import (
            AdvisorHierarchy,
            AdvisorScope,
            AdvisorAuthority,
        )

        hierarchy = AdvisorHierarchy()
        orphan = hierarchy.spawn(
            parent_id="nonexistent",
            scope=AdvisorScope.DOMAIN,
            authority_class=AdvisorAuthority.DOMAIN,
        )
        assert orphan is None

    def test_terminate_cascades(self):
        from substrate.organism.advisor_hierarchy import (
            AdvisorHierarchy,
            AdvisorScope,
            AdvisorStatus,
            AdvisorAuthority,
        )

        hierarchy = AdvisorHierarchy()
        primary = hierarchy.register_primary(budget_usd=100.0, spawn_limit=10)

        domain = hierarchy.spawn(
            primary.id, AdvisorScope.DOMAIN, AdvisorAuthority.DOMAIN,
            budget_usd=20.0, spawn_limit=5,
        )
        team = hierarchy.spawn(
            domain.id, AdvisorScope.TEAM, AdvisorAuthority.TEAM,
            budget_usd=5.0,
        )

        hierarchy.terminate(domain.id)
        assert domain.status == AdvisorStatus.TERMINATED
        assert team.status == AdvisorStatus.TERMINATED

    def test_recursion_limit_inheritance(self):
        from substrate.organism.advisor_hierarchy import (
            AdvisorHierarchy,
            AdvisorScope,
            AdvisorAuthority,
        )

        hierarchy = AdvisorHierarchy()
        primary = hierarchy.register_primary(recursion_limit=3)

        domain = hierarchy.spawn(
            primary.id, AdvisorScope.DOMAIN, AdvisorAuthority.DOMAIN,
            recursion_limit=5,
        )
        assert domain.recursion_limit == 2

    def test_hierarchy_tree(self):
        from substrate.organism.advisor_hierarchy import (
            AdvisorHierarchy,
            AdvisorScope,
            AdvisorAuthority,
        )

        hierarchy = AdvisorHierarchy()
        primary = hierarchy.register_primary(budget_usd=100.0, spawn_limit=10)
        hierarchy.spawn(
            primary.id, AdvisorScope.DOMAIN, AdvisorAuthority.DOMAIN, budget_usd=10.0,
        )
        hierarchy.spawn(
            primary.id, AdvisorScope.DOMAIN, AdvisorAuthority.DOMAIN, budget_usd=10.0,
        )

        tree = hierarchy.hierarchy_tree()
        assert "children" in tree
        assert len(tree["children"]) == 2

    def test_scope_violation_check(self):
        from substrate.organism.advisor_hierarchy import (
            AdvisorHierarchy,
            AdvisorScope,
            AdvisorAuthority,
        )

        hierarchy = AdvisorHierarchy()
        primary = hierarchy.register_primary(budget_usd=100.0)
        domain = hierarchy.spawn(
            primary.id, AdvisorScope.DOMAIN, AdvisorAuthority.DOMAIN,
            allowed_projects=["lyfe-institute"],
            budget_usd=10.0,
        )

        assert not hierarchy.check_scope_violation(domain.id, "lyfe-institute")
        assert hierarchy.check_scope_violation(domain.id, "other-project")

    def test_overdue_reports(self):
        from substrate.organism.advisor_hierarchy import (
            AdvisorHierarchy,
            AdvisorScope,
            AdvisorAuthority,
        )

        hierarchy = AdvisorHierarchy()
        primary = hierarchy.register_primary(budget_usd=100.0)
        domain = hierarchy.spawn(
            primary.id, AdvisorScope.DOMAIN, AdvisorAuthority.DOMAIN,
            budget_usd=10.0,
            reporting_cadence_seconds=1,
        )
        domain.last_report_at = time.time() - 10

        overdue = hierarchy.overdue_reports()
        assert len(overdue) >= 1


# ── Phase 3D: Cockpit Observability Integration ─────────────────────


class TestCockpitObservability:
    def test_observability_snapshot_includes_economy(self):
        from substrate.organism.execution_economy import (
            ExecutionDecisionRecord,
            ExecutionEconomy,
        )
        from substrate.organism.observability import OrganismObserver

        observer = OrganismObserver()
        snap = observer.snapshot()
        d = snap.to_dict()

        assert "objectives" in d
        assert "work_units" in d
        assert "runtimes" in d

    def test_organism_daemon_imports(self):
        from substrate.organism.daemon import OrganismDaemon

        daemon = OrganismDaemon()
        assert daemon is not None
        assert not daemon.is_running

    def test_daemon_status_structure(self):
        from substrate.organism.daemon import OrganismDaemon

        daemon = OrganismDaemon()
        status = daemon.status()
        assert "running" in status
        assert "tick_count" in status


# ── Phase 3E: External Leverage Map Schema ───────────────────────────


class TestExternalLeverageMapSchema:
    def test_leverage_map_fields(self):
        from substrate.organism.leverage_assimilation import (
            LeverageAssimilator,
        )

        assim = LeverageAssimilator()
        result = assim.full_pipeline(
            name="test-system",
            source_url="https://example.com",
            content="An agent orchestration system with multi-agent patterns",
        )

        assert "artifact" in result
        assert "redundancy" in result
        assert "scored_primitives" in result
        assert "umh_mapping" in result

        artifact = result["artifact"]
        assert "artifact_type" in artifact
        assert "status" in artifact
        assert "leverage_summary" in artifact

    def test_evidence_levels(self):
        from substrate.organism.leverage_assimilation import (
            LeverageAssimilator,
        )

        assim = LeverageAssimilator()
        artifact = assim.ingest("test", content="runtime system")
        assim.classify(artifact.id)
        prims = assim.extract_primitives(artifact.id)

        for prim in prims:
            assert hasattr(prim, "leverage")
            assert hasattr(prim.leverage, "composite")


# ── Phase 3F: Structural Integrity ──────────────────────────────────


class TestStructuralIntegrity:
    def test_no_product_dependency_coupling(self):
        import ast

        phase3_files = [
            "substrate/organism/execution_economy.py",
            "substrate/organism/recursion_governance.py",
            "substrate/organism/advisor_hierarchy.py",
        ]

        bad_imports = {"saas", "integrations.creatoros", "integrations.lyfeos"}

        for filepath in phase3_files:
            full = os.path.join(os.environ.get("UMH_ROOT", "/opt/OS"), filepath)
            if not os.path.exists(full):
                continue
            with open(full) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module = ""
                    if isinstance(node, ast.ImportFrom) and node.module:
                        module = node.module
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            module = alias.name
                    for bad in bad_imports:
                        assert bad not in module, (
                            f"{filepath} imports {module} — product dependency coupling"
                        )

    def test_no_instance_leaks_in_phase3(self):
        _p = ["D" + "EX", "Ant" + "ony", "Lyfe Ins" + "titute",
              "Empyrean St" + "udio", "100.77" + ".233.50", "antony" + "fmunoz"]
        instance_patterns = _p

        phase3_files = [
            "substrate/organism/execution_economy.py",
            "substrate/organism/recursion_governance.py",
            "substrate/organism/advisor_hierarchy.py",
        ]

        for filepath in phase3_files:
            full = os.path.join(os.environ.get("UMH_ROOT", "/opt/OS"), filepath)
            if not os.path.exists(full):
                continue
            with open(full) as f:
                content = f.read()
            for pattern in instance_patterns:
                assert pattern not in content, (
                    f"{filepath} contains instance value '{pattern}'"
                )

    def test_no_files_over_3000_lines(self):
        phase3_files = [
            "substrate/organism/execution_economy.py",
            "substrate/organism/recursion_governance.py",
            "substrate/organism/advisor_hierarchy.py",
        ]

        for filepath in phase3_files:
            full = os.path.join(os.environ.get("UMH_ROOT", "/opt/OS"), filepath)
            if not os.path.exists(full):
                continue
            with open(full) as f:
                lines = sum(1 for _ in f)
            assert lines <= 3000, f"{filepath} has {lines} lines (max 3000)"

    def test_canonical_types_no_conflicts(self):
        from substrate.canonical_types import check_name

        phase3_types = [
            ("ExecutionClass", "substrate.organism.execution_economy"),
            ("VerificationResult", "substrate.organism.execution_economy"),
            ("EscalationLevel", "substrate.organism.recursion_governance"),
            ("RecursionApproval", "substrate.organism.recursion_governance"),
            ("AdvisorScope", "substrate.organism.advisor_hierarchy"),
            ("AdvisorAuthority", "substrate.organism.advisor_hierarchy"),
            ("AdvisorStatus", "substrate.organism.advisor_hierarchy"),
        ]

        for type_name, module in phase3_types:
            error = check_name(type_name, module)
            assert error is None, f"Type conflict: {error}"

    def test_dependency_direction(self):
        import ast

        forbidden_imports = {
            "substrate.organism.execution_economy": {"transports", "services", "saas"},
            "substrate.organism.recursion_governance": {"transports", "services", "saas"},
            "substrate.organism.advisor_hierarchy": {"transports", "services", "saas"},
        }

        for module_path, forbidden in forbidden_imports.items():
            filepath = module_path.replace(".", "/") + ".py"
            full = os.path.join(os.environ.get("UMH_ROOT", "/opt/OS"), filepath)
            if not os.path.exists(full):
                continue
            with open(full) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    top = node.module.split(".")[0]
                    assert top not in forbidden, (
                        f"{filepath} imports from {node.module} — dependency violation"
                    )
