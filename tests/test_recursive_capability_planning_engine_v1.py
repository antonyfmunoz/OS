"""Tests for Phase 96.8AV — Recursive Capability Planning Engine.

Verifies:
  1. Capability graph generation (21 capabilities)
  2. Dependency graph correctness
  3. Bottleneck analysis (8 categories)
  4. Leverage scoring (8-dimensional composite)
  5. Upgrade proposals ranked by composite
  6. Maturity classification L0-L5
  7. Hard ceilings block escalation
  8. Canonical/instance separation
  9. Proof persistence and serialization
  10. Full pipeline integration
  11. Registry integration (16 commands)
  12. Infrastructure self-analysis
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/OS")
sys.path.insert(0, "/opt/OS/services")


class TestCapabilityNode:
    def test_node_has_id(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import CapabilityNode

        node = CapabilityNode(name="relay_transport")
        assert node.capability_id.startswith("CAP-")

    def test_node_defaults(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import CapabilityNode

        node = CapabilityNode(name="test")
        assert node.status == "missing"
        assert node.proven is False
        assert node.replayable is False
        assert node.governance_covered is False
        assert node.evidence_quality == 0.0

    def test_node_to_dict(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import CapabilityNode

        node = CapabilityNode(name="relay_transport", proven=True, evidence_quality=0.8)
        d = node.to_dict()
        assert d["name"] == "relay_transport"
        assert d["proven"] is True
        assert d["evidence_quality"] == 0.8

    def test_node_timestamp(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import CapabilityNode

        node = CapabilityNode(name="test")
        assert len(node.timestamp) > 0


class TestLeverageScore:
    def test_composite_positive_only(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import LeverageScore

        score = LeverageScore(
            upgrade_name="test",
            leverage_gain=1.0,
            replayability_impact=1.0,
            evidence_quality=1.0,
            infrastructure_reuse=1.0,
            recursive_expansion_value=1.0,
            automation_potential=1.0,
            governance_risk=0.0,
            execution_complexity=0.0,
        )
        assert score.composite_score == 1.0

    def test_composite_with_penalties(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import LeverageScore

        score = LeverageScore(
            upgrade_name="test",
            leverage_gain=0.5,
            governance_risk=0.5,
            execution_complexity=0.5,
        )
        assert score.composite_score < 0.5 * 0.25

    def test_composite_floor_at_zero(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import LeverageScore

        score = LeverageScore(
            upgrade_name="test",
            leverage_gain=0.0,
            governance_risk=1.0,
            execution_complexity=1.0,
        )
        assert score.composite_score == 0.0

    def test_score_has_id(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import LeverageScore

        score = LeverageScore(upgrade_name="test")
        assert score.score_id.startswith("LSCR-")

    def test_score_to_dict(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import LeverageScore

        score = LeverageScore(upgrade_name="test", leverage_gain=0.7)
        d = score.to_dict()
        assert d["upgrade_name"] == "test"
        assert d["leverage_gain"] == 0.7
        assert "composite_score" in d

    def test_eight_dimensions_present(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import LeverageScore

        score = LeverageScore(upgrade_name="test")
        d = score.to_dict()
        dims = [
            "leverage_gain",
            "governance_risk",
            "replayability_impact",
            "execution_complexity",
            "evidence_quality",
            "infrastructure_reuse",
            "recursive_expansion_value",
            "automation_potential",
        ]
        for dim in dims:
            assert dim in d


class TestBottleneck:
    def test_bottleneck_has_id(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import Bottleneck

        b = Bottleneck(category="manual", description="test")
        assert b.bottleneck_id.startswith("BTNK-")

    def test_bottleneck_to_dict(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import Bottleneck

        b = Bottleneck(category="relay", description="test", severity=0.5)
        d = b.to_dict()
        assert d["category"] == "relay"
        assert d["severity"] == 0.5

    def test_bottleneck_categories_valid(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            BOTTLENECK_CATEGORIES,
        )

        assert len(BOTTLENECK_CATEGORIES) == 8
        expected = {
            "manual",
            "replay",
            "governance",
            "execution",
            "relay",
            "ingestion",
            "maturity",
            "scaling",
        }
        assert BOTTLENECK_CATEGORIES == expected


class TestUpgradeProposal:
    def test_proposal_has_id(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import UpgradeProposal

        p = UpgradeProposal(name="test")
        assert p.proposal_id.startswith("UPGR-")

    def test_proposal_defaults_canonical(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import UpgradeProposal

        p = UpgradeProposal(name="test")
        assert p.candidate_type == "canonical"

    def test_proposal_to_dict(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            LeverageScore,
            UpgradeProposal,
        )

        score = LeverageScore(upgrade_name="test", leverage_gain=0.8)
        p = UpgradeProposal(name="test", leverage_score=score)
        d = p.to_dict()
        assert d["name"] == "test"
        assert d["leverage_score"]["leverage_gain"] == 0.8


class TestSubstrateCapabilities:
    def test_exactly_21_capabilities(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            SUBSTRATE_CAPABILITIES,
        )

        assert len(SUBSTRATE_CAPABILITIES) == 21

    def test_all_capabilities_have_dependencies(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CAPABILITY_DEPENDENCIES,
            SUBSTRATE_CAPABILITIES,
        )

        for cap in SUBSTRATE_CAPABILITIES:
            assert cap in CAPABILITY_DEPENDENCIES

    def test_all_dependencies_are_valid_capabilities(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CAPABILITY_DEPENDENCIES,
            SUBSTRATE_CAPABILITIES,
        )

        cap_set = set(SUBSTRATE_CAPABILITIES)
        for cap, deps in CAPABILITY_DEPENDENCIES.items():
            for dep in deps:
                assert dep in cap_set, f"{cap} depends on unknown {dep}"

    def test_no_self_dependencies(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CAPABILITY_DEPENDENCIES,
        )

        for cap, deps in CAPABILITY_DEPENDENCIES.items():
            assert cap not in deps, f"{cap} has self-dependency"

    def test_all_capabilities_have_proof_indicators(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CAPABILITY_PROOF_INDICATORS,
            SUBSTRATE_CAPABILITIES,
        )

        for cap in SUBSTRATE_CAPABILITIES:
            assert cap in CAPABILITY_PROOF_INDICATORS


class TestCapabilityGraph:
    def test_graph_from_empty_evidence(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            build_capability_graph,
        )

        evidence = CapabilityPlanningEvidence()
        graph = build_capability_graph(evidence)
        assert len(graph.nodes) == 21
        assert graph.proven_count == 0
        assert graph.missing_count == 21

    def test_graph_from_full_evidence(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            build_capability_graph,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            cu_ingestion_proven=True,
            environment_mapped=True,
            blueprints_generated=True,
            replay_contracts_defined=True,
            governance_classified=True,
            screenshots_present=True,
            founder_confirmed=True,
            capability_graph_generated=True,
        )
        graph = build_capability_graph(evidence)
        assert graph.proven_count == 21
        assert graph.missing_count == 0

    def test_graph_has_id(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            build_capability_graph,
        )

        graph = build_capability_graph(CapabilityPlanningEvidence())
        assert graph.graph_id.startswith("CGRAPH-")

    def test_graph_to_dict(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            build_capability_graph,
        )

        graph = build_capability_graph(CapabilityPlanningEvidence())
        d = graph.to_dict()
        assert d["node_count"] == 21
        assert len(d["nodes"]) == 21

    def test_node_statuses_blocked_vs_missing(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            build_capability_graph,
        )

        evidence = CapabilityPlanningEvidence(actuation_proven=True)
        graph = build_capability_graph(evidence)
        statuses = {n.name: n.status for n in graph.nodes}
        assert statuses["relay_transport"] == "proven"
        assert statuses["desktop_actuation"] == "proven"
        assert statuses["clipboard_extraction"] == "blocked"

    def test_evidence_quality_scores(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            build_capability_graph,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            replay_contracts_defined=True,
            governance_classified=True,
        )
        graph = build_capability_graph(evidence)
        proven_nodes = [n for n in graph.nodes if n.proven]
        for n in proven_nodes:
            assert n.evidence_quality >= 0.8


class TestDependencyGraph:
    def test_dependents_computed(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import _DEPENDENTS

        assert "desktop_actuation" in _DEPENDENTS["relay_transport"]

    def test_relay_transport_has_most_dependents(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import _DEPENDENTS

        relay_deps = len(_DEPENDENTS["relay_transport"])
        for cap, deps in _DEPENDENTS.items():
            if cap == "relay_transport":
                continue
            assert relay_deps >= len(deps) or cap in (
                "desktop_actuation",
                "topology_mapping",
                "command_registration",
                "adapter_autogeneration",
            )

    def test_recursive_planning_depends_on_adapter_layer(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CAPABILITY_DEPENDENCIES,
        )

        deps = CAPABILITY_DEPENDENCIES["recursive_planning"]
        assert "adapter_autogeneration" in deps
        assert "replay_contract_generation" in deps
        assert "governance_classification" in deps
        assert "maturity_evaluation" in deps

    def test_no_circular_dependencies(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CAPABILITY_DEPENDENCIES,
        )

        def has_cycle(start: str, visited: set[str]) -> bool:
            if start in visited:
                return True
            visited.add(start)
            for dep in CAPABILITY_DEPENDENCIES.get(start, []):
                if has_cycle(dep, visited.copy()):
                    return True
            return False

        for cap in CAPABILITY_DEPENDENCIES:
            assert not has_cycle(cap, set()), f"Circular dependency detected for {cap}"


class TestBottleneckAnalysis:
    def test_empty_evidence_max_bottlenecks(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            analyze_bottlenecks,
            build_capability_graph,
        )

        evidence = CapabilityPlanningEvidence()
        graph = build_capability_graph(evidence)
        bottlenecks = analyze_bottlenecks(evidence, graph)
        assert len(bottlenecks) >= 8

    def test_bottlenecks_sorted_by_severity(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            analyze_bottlenecks,
            build_capability_graph,
        )

        evidence = CapabilityPlanningEvidence()
        graph = build_capability_graph(evidence)
        bottlenecks = analyze_bottlenecks(evidence, graph)
        severities = [b.severity for b in bottlenecks]
        assert severities == sorted(severities, reverse=True)

    def test_actuation_bottleneck_highest_severity(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            analyze_bottlenecks,
            build_capability_graph,
        )

        evidence = CapabilityPlanningEvidence()
        graph = build_capability_graph(evidence)
        bottlenecks = analyze_bottlenecks(evidence, graph)
        assert bottlenecks[0].severity == 1.0
        assert bottlenecks[0].category == "execution"

    def test_all_bottleneck_categories_valid(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            BOTTLENECK_CATEGORIES,
            CapabilityPlanningEvidence,
            analyze_bottlenecks,
            build_capability_graph,
        )

        evidence = CapabilityPlanningEvidence()
        graph = build_capability_graph(evidence)
        bottlenecks = analyze_bottlenecks(evidence, graph)
        for b in bottlenecks:
            assert b.category in BOTTLENECK_CATEGORIES

    def test_fewer_bottlenecks_with_evidence(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            analyze_bottlenecks,
            build_capability_graph,
        )

        empty_ev = CapabilityPlanningEvidence()
        empty_graph = build_capability_graph(empty_ev)
        empty_count = len(analyze_bottlenecks(empty_ev, empty_graph))

        partial_ev = CapabilityPlanningEvidence(
            actuation_proven=True,
            cu_ingestion_proven=True,
            screenshots_present=True,
        )
        partial_graph = build_capability_graph(partial_ev)
        partial_count = len(analyze_bottlenecks(partial_ev, partial_graph))

        assert partial_count < empty_count


class TestLeverageScoring:
    def test_upgrade_catalog_has_5_entries(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import UPGRADE_CATALOG

        assert len(UPGRADE_CATALOG) == 5

    def test_score_upgrade_returns_leverage_score(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            UPGRADE_CATALOG,
            score_upgrade,
        )

        score = score_upgrade(UPGRADE_CATALOG[0])
        assert score.composite_score > 0.0
        assert score.upgrade_name == UPGRADE_CATALOG[0]["name"]

    def test_all_catalog_entries_have_scores(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            UPGRADE_CATALOG,
            score_upgrade,
        )

        for entry in UPGRADE_CATALOG:
            score = score_upgrade(entry)
            assert score.composite_score >= 0.0
            assert score.composite_score <= 1.0

    def test_local_adapter_highest_leverage(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            UPGRADE_CATALOG,
            score_upgrade,
        )

        scores = [
            (entry["name"], score_upgrade(entry).composite_score) for entry in UPGRADE_CATALOG
        ]
        scores.sort(key=lambda x: x[1], reverse=True)
        assert scores[0][0] == "local_adapter_execution"


class TestUpgradeProposals:
    def test_proposals_generated(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            build_capability_graph,
            generate_upgrade_proposals,
        )

        evidence = CapabilityPlanningEvidence()
        graph = build_capability_graph(evidence)
        proposals = generate_upgrade_proposals(evidence, graph)
        assert len(proposals) == 5

    def test_proposals_ranked_by_composite(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            build_capability_graph,
            generate_upgrade_proposals,
        )

        evidence = CapabilityPlanningEvidence()
        graph = build_capability_graph(evidence)
        proposals = generate_upgrade_proposals(evidence, graph)
        composites = [p.leverage_score.composite_score for p in proposals]
        assert composites == sorted(composites, reverse=True)

    def test_proposals_have_priority(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            build_capability_graph,
            generate_upgrade_proposals,
        )

        evidence = CapabilityPlanningEvidence()
        graph = build_capability_graph(evidence)
        proposals = generate_upgrade_proposals(evidence, graph)
        priorities = [p.priority for p in proposals]
        assert priorities == [1, 2, 3, 4, 5]

    def test_all_proposals_canonical(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            build_capability_graph,
            generate_upgrade_proposals,
        )

        evidence = CapabilityPlanningEvidence()
        graph = build_capability_graph(evidence)
        proposals = generate_upgrade_proposals(evidence, graph)
        for p in proposals:
            assert p.candidate_type == "canonical"


class TestMaturityClassification:
    def test_dry_run_always_l0(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            compute_capability_maturity,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            cu_ingestion_proven=True,
            environment_mapped=True,
            is_dry_run=True,
        )
        assert compute_capability_maturity(evidence) == "L0_SIMULATED"

    def test_l1_with_actuation(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            compute_capability_maturity,
        )

        evidence = CapabilityPlanningEvidence(actuation_proven=True)
        assert compute_capability_maturity(evidence) == "L1_VISIBLE_ACTUATION"

    def test_l2_with_cu_ingestion(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            compute_capability_maturity,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            cu_ingestion_proven=True,
        )
        assert compute_capability_maturity(evidence) == "L2_FOREGROUND_CU_INGESTION"

    def test_l3_with_environment(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            compute_capability_maturity,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            cu_ingestion_proven=True,
            environment_mapped=True,
        )
        assert compute_capability_maturity(evidence) == "L3_ENVIRONMENT_INTELLIGENCE"

    def test_l4_with_adapters(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            compute_capability_maturity,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            cu_ingestion_proven=True,
            environment_mapped=True,
            blueprints_generated=True,
            replay_contracts_defined=True,
            governance_classified=True,
        )
        assert compute_capability_maturity(evidence) == "L4_ADAPTER_MATURITY"

    def test_l5_with_planning(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            compute_capability_maturity,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            cu_ingestion_proven=True,
            environment_mapped=True,
            blueprints_generated=True,
            replay_contracts_defined=True,
            governance_classified=True,
            capability_graph_generated=True,
            leverage_analyzed=True,
            upgrade_paths_proposed=True,
        )
        assert compute_capability_maturity(evidence) == "L5_RECURSIVE_CAPABILITY_PLANNING"

    def test_maturity_levels_count(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CAPABILITY_MATURITY_LEVELS,
        )

        assert len(CAPABILITY_MATURITY_LEVELS) == 6


class TestHardCeilings:
    def test_dry_run_ceiling_l0(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            capability_maturity_ceiling,
        )

        evidence = CapabilityPlanningEvidence(is_dry_run=True)
        assert capability_maturity_ceiling(evidence) == "L0_SIMULATED"

    def test_no_screenshots_ceiling_l1(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            capability_maturity_ceiling,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            screenshots_present=False,
        )
        assert capability_maturity_ceiling(evidence) == "L1_VISIBLE_ACTUATION"

    def test_no_env_ceiling_l2(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            capability_maturity_ceiling,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            screenshots_present=True,
            environment_mapped=False,
        )
        assert capability_maturity_ceiling(evidence) == "L2_FOREGROUND_CU_INGESTION"

    def test_no_blueprints_ceiling_l3(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            capability_maturity_ceiling,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            screenshots_present=True,
            environment_mapped=True,
            blueprints_generated=False,
        )
        assert capability_maturity_ceiling(evidence) == "L3_ENVIRONMENT_INTELLIGENCE"

    def test_no_governance_ceiling_l3(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            capability_maturity_ceiling,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            screenshots_present=True,
            environment_mapped=True,
            blueprints_generated=True,
            governance_classified=False,
        )
        assert capability_maturity_ceiling(evidence) == "L3_ENVIRONMENT_INTELLIGENCE"

    def test_no_graph_ceiling_l4(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            capability_maturity_ceiling,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            screenshots_present=True,
            environment_mapped=True,
            blueprints_generated=True,
            governance_classified=True,
            capability_graph_generated=False,
        )
        assert capability_maturity_ceiling(evidence) == "L4_ADAPTER_MATURITY"

    def test_no_leverage_ceiling_l4(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            capability_maturity_ceiling,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            screenshots_present=True,
            environment_mapped=True,
            blueprints_generated=True,
            governance_classified=True,
            capability_graph_generated=True,
            leverage_analyzed=False,
        )
        assert capability_maturity_ceiling(evidence) == "L4_ADAPTER_MATURITY"

    def test_no_founder_ceiling_l4(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            capability_maturity_ceiling,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            screenshots_present=True,
            environment_mapped=True,
            blueprints_generated=True,
            governance_classified=True,
            capability_graph_generated=True,
            leverage_analyzed=True,
            founder_confirmed=False,
        )
        assert capability_maturity_ceiling(evidence) == "L4_ADAPTER_MATURITY"

    def test_full_evidence_ceiling_l5(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            capability_maturity_ceiling,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            screenshots_present=True,
            environment_mapped=True,
            blueprints_generated=True,
            governance_classified=True,
            capability_graph_generated=True,
            leverage_analyzed=True,
            founder_confirmed=True,
        )
        assert capability_maturity_ceiling(evidence) == "L5_RECURSIVE_CAPABILITY_PLANNING"

    def test_ceiling_blocks_escalation(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            classify_capability_maturity,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            cu_ingestion_proven=True,
            environment_mapped=True,
            blueprints_generated=True,
            replay_contracts_defined=True,
            governance_classified=True,
            capability_graph_generated=True,
            leverage_analyzed=True,
            upgrade_paths_proposed=True,
            screenshots_present=False,
        )
        level, ceiling, blocked, reason = classify_capability_maturity(evidence)
        assert blocked is True
        assert level == "L1_VISIBLE_ACTUATION"
        assert "ceiling" in reason


class TestProofPersistence:
    def test_proof_persists(self, tmp_path: Path) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningProof,
            persist_capability_proof,
        )

        proof = CapabilityPlanningProof(trace_id="test-trace")
        path = persist_capability_proof(proof, base_dir=tmp_path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["proof_type"] == "recursive_capability_planning"

    def test_proof_filename(self, tmp_path: Path) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningProof,
            persist_capability_proof,
        )

        proof = CapabilityPlanningProof(trace_id="test-trace")
        path = persist_capability_proof(proof, base_dir=tmp_path)
        assert path.name.startswith("CAPPLAN-")
        assert path.name.endswith(".json")

    def test_proof_creates_directory(self, tmp_path: Path) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningProof,
            persist_capability_proof,
        )

        proof = CapabilityPlanningProof(trace_id="test-trace")
        persist_capability_proof(proof, base_dir=tmp_path)
        report_dir = tmp_path / "data/runtime/workstation_relay/capability_reports"
        assert report_dir.exists()

    def test_proof_serialization_complete(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningProof,
            CapabilityPlanningEvidence,
            CapabilityGraph,
        )

        proof = CapabilityPlanningProof(
            trace_id="test",
            evidence=CapabilityPlanningEvidence(),
            capability_graph=CapabilityGraph(),
        )
        d = proof.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0
        parsed = json.loads(serialized)
        assert parsed["proof_type"] == "recursive_capability_planning"


class TestFullPipeline:
    def test_full_proof_from_empty(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        proof = build_full_capability_proof(
            env_proof=None,
            adapter_proof=None,
            founder_confirmed=False,
            is_dry_run=False,
            trace_id="test",
            request_id="req-test",
        )
        assert proof.maturity_level == "L0_SIMULATED"
        assert proof.capability_graph is not None
        assert len(proof.capability_graph.nodes) == 21
        assert len(proof.bottlenecks) > 0
        assert len(proof.upgrade_proposals) == 5

    def test_full_proof_dry_run(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        proof = build_full_capability_proof(
            is_dry_run=True,
            trace_id="test",
        )
        assert proof.maturity_level == "L0_SIMULATED"
        assert proof.execution_strategy == "simulation_only"

    def test_full_proof_has_strategy(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        proof = build_full_capability_proof(
            founder_confirmed=False,
            trace_id="test",
        )
        assert proof.execution_strategy in (
            "simulation_only",
            "prove_prerequisites_first",
            "execute_safest_upgrade",
            "await_founder_confirmation",
        )

    def test_full_proof_safest_and_highest(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        proof = build_full_capability_proof(trace_id="test")
        assert proof.safest_next_phase != ""
        assert proof.highest_leverage_upgrade != ""
        assert proof.safest_next_phase != proof.highest_leverage_upgrade

    def test_full_proof_serializable(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        proof = build_full_capability_proof(trace_id="test")
        d = proof.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0
        parsed = json.loads(serialized)
        assert parsed["upgrade_count"] == 5
        assert parsed["bottleneck_count"] > 0


class TestInfrastructureAnalysis:
    def test_analyze_registries(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import analyze_registries

        result = analyze_registries()
        assert result["adapter_registry_exists"] is True
        assert result["router_config_exists"] is True
        assert result["config_action_count"] == 24

    def test_analyze_proof_artifacts(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            analyze_proof_artifacts,
        )

        result = analyze_proof_artifacts()
        assert "runtime_proofs" in result
        assert "environment_maps" in result
        assert "adapter_reports" in result
        assert "capability_reports" in result

    def test_analyze_governance_surface(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            analyze_governance_surface,
        )

        result = analyze_governance_surface()
        assert result["total_commands"] == 24
        assert result["founder_approval_required"] > 0
        assert result["governance_coverage"] > 0.0

    def test_find_infrastructure_reuse(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            build_capability_graph,
            generate_upgrade_proposals,
            find_infrastructure_reuse,
        )

        evidence = CapabilityPlanningEvidence(
            actuation_proven=True,
            environment_mapped=True,
        )
        graph = build_capability_graph(evidence)
        proposals = generate_upgrade_proposals(evidence, graph)
        reuse = find_infrastructure_reuse(graph, proposals)
        assert isinstance(reuse, list)


class TestCanonicalInstanceSeparation:
    def test_proposals_always_canonical(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            build_capability_graph,
            generate_upgrade_proposals,
        )

        evidence = CapabilityPlanningEvidence()
        graph = build_capability_graph(evidence)
        proposals = generate_upgrade_proposals(evidence, graph)
        for p in proposals:
            assert p.candidate_type == "canonical"

    def test_proof_type_field(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_full_capability_proof,
        )

        proof = build_full_capability_proof(trace_id="test")
        d = proof.to_dict()
        assert d["proof_type"] == "recursive_capability_planning"


class TestRegistryIntegration:
    def test_registry_count_is_20(self) -> None:
        from core.registry.canonical_command_registry_v1 import CanonicalCommandRegistryV1

        reg = CanonicalCommandRegistryV1()
        assert len(reg) == 24

    def test_capability_report_in_registry(self) -> None:
        from core.registry.canonical_command_registry_v1 import CanonicalCommandRegistryV1

        reg = CanonicalCommandRegistryV1()
        assert reg.contains("!capability-report")
        entry = reg.get("!capability-report")
        assert entry.canonical_action == "capability_report"
        assert entry.capability_type == "CAPABILITY_PLANNING"

    def test_capability_report_in_router_config(self) -> None:
        config = json.loads(Path("/opt/OS/config/control_plane_router_v1.json").read_text())
        assert "capability_report" in config["allowed_action_types"]

    def test_capability_report_in_contracts(self) -> None:
        from core.control_plane_router.router_contracts import (
            ALLOWED_ACTION_TYPES,
            CapabilityType,
        )

        assert "capability_report" in ALLOWED_ACTION_TYPES
        assert hasattr(CapabilityType, "CAPABILITY_PLANNING")

    def test_capability_report_in_action_map(self) -> None:
        from core.control_plane_router.control_plane_router_v1 import ACTION_CAPABILITY_MAP

        assert "capability_report" in ACTION_CAPABILITY_MAP

    def test_capability_report_in_adapter_contracts(self) -> None:
        from core.environment_bridge.windows_desktop_adapter_contracts import (
            WindowsDesktopActionType,
        )

        assert hasattr(WindowsDesktopActionType, "CAPABILITY_REPORT")

    def test_capability_report_in_adapter_registry(self) -> None:
        data = json.loads(
            Path("/opt/OS/data/registries/local_worker_adapter_registry_v1.json").read_text()
        )
        wsl_caps = data["workers"]["local_wsl_worker"]["capabilities"]
        assert "capability_report" in wsl_caps

    def test_substrate_commands_includes_capability_report(self) -> None:
        from handlers.substrate_command_handler import SUBSTRATE_COMMANDS

        assert "!capability-report" in SUBSTRATE_COMMANDS


class TestMaturityRequirements:
    def test_l0_no_requirements(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CAPABILITY_MATURITY_REQUIREMENTS,
        )

        assert CAPABILITY_MATURITY_REQUIREMENTS["L0_SIMULATED"] == []

    def test_l5_has_most_requirements(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CAPABILITY_MATURITY_REQUIREMENTS,
        )

        l5_reqs = CAPABILITY_MATURITY_REQUIREMENTS["L5_RECURSIVE_CAPABILITY_PLANNING"]
        for level, reqs in CAPABILITY_MATURITY_REQUIREMENTS.items():
            assert len(l5_reqs) >= len(reqs)

    def test_each_level_adds_requirements(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CAPABILITY_MATURITY_LEVELS,
            CAPABILITY_MATURITY_REQUIREMENTS,
        )

        prev_len = 0
        for level in CAPABILITY_MATURITY_LEVELS:
            curr_len = len(CAPABILITY_MATURITY_REQUIREMENTS[level])
            assert curr_len >= prev_len
            prev_len = curr_len

    def test_l5_includes_planning_requirements(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CAPABILITY_MATURITY_REQUIREMENTS,
        )

        l5_reqs = CAPABILITY_MATURITY_REQUIREMENTS["L5_RECURSIVE_CAPABILITY_PLANNING"]
        assert "capability_graph_generated" in l5_reqs
        assert "leverage_analyzed" in l5_reqs
        assert "upgrade_paths_proposed" in l5_reqs


class TestPlanningEvidence:
    def test_evidence_to_dict(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
        )

        ev = CapabilityPlanningEvidence(
            capability_graph_generated=True,
            leverage_analyzed=True,
        )
        d = ev.to_dict()
        assert d["capability_graph_generated"] is True
        assert d["leverage_analyzed"] is True

    def test_build_planning_evidence_from_nothing(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            build_planning_evidence,
        )

        ev = build_planning_evidence()
        assert ev.actuation_proven is False
        assert ev.capability_graph_generated is False

    def test_build_planning_evidence_with_graph(self) -> None:
        from core.workstation.recursive_capability_planning_engine_v1 import (
            CapabilityPlanningEvidence,
            build_capability_graph,
            build_planning_evidence,
        )

        stub = CapabilityPlanningEvidence(actuation_proven=True)
        graph = build_capability_graph(stub)
        ev = build_planning_evidence(graph=graph)
        assert ev.capability_count == 21
        assert ev.proven_count > 0
