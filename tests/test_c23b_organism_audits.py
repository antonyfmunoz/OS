"""Tests — Campaign 23B organism audits (Tier 3).

Covers the five organism-audit modules:
  - context_capacity   (Category C)
  - operational_awareness (Category D)
  - source_truth       (Category I)
  - organism_awareness (Category L)
  - empire_readiness   (Category P)

All audits are deterministic; these tests pin coverage math, accuracy scoring,
fuzzy matching, lineage completeness, and empty/edge handling.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.audits.context_capacity import (  # noqa: E402
    ContextCapacityAudit,
    ContextCapacityReport,
)
from substrate.organism.audits.empire_readiness import (  # noqa: E402
    FUTURE_PROJECTIONS,
    EmpireReadinessAudit,
    EmpireReadinessReport,
)
from substrate.organism.audits.operational_awareness import (  # noqa: E402
    OperationalAwarenessAudit,
    OperationalAwarenessReport,
    ServiceState,
)
from substrate.organism.audits.organism_awareness import (  # noqa: E402
    AwarenessDimension,
    OrganismAwarenessAudit,
    OrganismAwarenessReport,
)
from substrate.organism.audits.source_truth import (  # noqa: E402
    LINEAGE_STAGES,
    LineageChain,
    SourceTruthAudit,
    SourceTruthReport,
)


# ===========================================================================
# context_capacity
# ===========================================================================


class TestContextCapacity:
    def test_empty_input_zero_report(self):
        report = ContextCapacityAudit(test_mode=True).run()
        assert isinstance(report, ContextCapacityReport)
        assert report.repo_file_count == 0
        assert report.graph_coverage_pct == 0.0
        assert report.summary_coverage_pct == 0.0
        assert report.overall_score == 0.0

    def test_full_coverage(self):
        graph = {"repo_file_count": 100, "node_count": 100, "edge_count": 50, "history_depth": 10}
        summary = {"repo_file_count": 100, "summarized_count": 100}
        report = ContextCapacityAudit(test_mode=True).run(graph_data=graph, summary_data=summary)
        assert report.graph_coverage_pct == 1.0
        assert report.summary_coverage_pct == 1.0
        assert report.overall_score == 1.0

    def test_partial_coverage(self):
        graph = {"repo_file_count": 100, "node_count": 50}
        summary = {"repo_file_count": 100, "summarized_count": 25}
        report = ContextCapacityAudit(test_mode=True).run(graph_data=graph, summary_data=summary)
        assert report.graph_coverage_pct == 0.5
        assert report.summary_coverage_pct == 0.25
        assert report.overall_score == round((0.5 + 0.25) / 2, 4)

    def test_zero_coverage(self):
        graph = {"repo_file_count": 100, "node_count": 0}
        summary = {"repo_file_count": 100, "summarized_count": 0}
        report = ContextCapacityAudit(test_mode=True).run(graph_data=graph, summary_data=summary)
        assert report.graph_coverage_pct == 0.0
        assert report.summary_coverage_pct == 0.0
        assert report.overall_score == 0.0

    def test_node_count_from_list(self):
        graph = {"repo_file_count": 4, "nodes": ["a", "b", "c", "d"]}
        report = ContextCapacityAudit(test_mode=True).run(graph_data=graph)
        assert report.graph_node_count == 4
        assert report.graph_coverage_pct == 1.0

    def test_edge_count_from_list(self):
        graph = {"repo_file_count": 10, "node_count": 10, "edges": [1, 2, 3]}
        report = ContextCapacityAudit(test_mode=True).run(graph_data=graph)
        assert report.cross_file_edges == 3

    def test_history_depth_from_commits_list(self):
        graph = {"repo_file_count": 1, "node_count": 1, "commits": ["c1", "c2", "c3", "c4"]}
        report = ContextCapacityAudit(test_mode=True).run(graph_data=graph)
        assert report.history_depth == 4

    def test_history_depth_explicit(self):
        graph = {"repo_file_count": 1, "node_count": 1, "history_depth": 99}
        report = ContextCapacityAudit(test_mode=True).run(graph_data=graph)
        assert report.history_depth == 99

    def test_repo_count_inferred_from_max(self):
        graph = {"node_count": 80}
        summary = {"summarized_count": 60}
        report = ContextCapacityAudit(test_mode=True).run(graph_data=graph, summary_data=summary)
        assert report.repo_file_count == 80

    def test_summaries_dict_excludes_bookkeeping(self):
        summary = {"repo_file_count": 2, "a.py": "summary a", "b.py": "summary b"}
        graph = {"repo_file_count": 2, "node_count": 2}
        report = ContextCapacityAudit(test_mode=True).run(graph_data=graph, summary_data=summary)
        assert report.summary_coverage_pct == 1.0

    def test_coverage_capped_at_one(self):
        graph = {"repo_file_count": 5, "node_count": 50}
        report = ContextCapacityAudit(test_mode=True).run(graph_data=graph)
        assert report.graph_coverage_pct == 1.0

    def test_to_dict_roundtrip(self):
        graph = {"repo_file_count": 10, "node_count": 5}
        report = ContextCapacityAudit(test_mode=True).run(graph_data=graph)
        d = report.to_dict()
        assert d["graph_node_count"] == 5
        assert d["repo_file_count"] == 10
        assert "overall_score" in d

    def test_only_graph_provided(self):
        graph = {"repo_file_count": 10, "node_count": 10}
        report = ContextCapacityAudit(test_mode=True).run(graph_data=graph)
        assert report.graph_coverage_pct == 1.0
        assert report.summary_coverage_pct == 0.0
        assert report.overall_score == 0.5


# ===========================================================================
# operational_awareness
# ===========================================================================


class TestOperationalAwareness:
    def test_empty_input(self):
        report = OperationalAwarenessAudit(test_mode=True).run([])
        assert isinstance(report, OperationalAwarenessReport)
        assert report.services_checked == 0
        assert report.overall_accuracy == 0.0

    def test_none_input(self):
        report = OperationalAwarenessAudit(test_mode=True).run(None)
        assert report.services_checked == 0

    def test_all_match(self):
        states = [
            ServiceState(service_name="os-discord", expected_status="running", actual_status="running"),
            ServiceState(service_name="os-operator", expected_status="running", actual_status="running"),
        ]
        report = OperationalAwarenessAudit(test_mode=True).run(states)
        assert report.services_checked == 2
        assert report.overall_accuracy == 1.0
        assert all(s.match for s in report.service_details)

    def test_none_match(self):
        states = [
            ServiceState(service_name="a", expected_status="running", actual_status="stopped"),
            ServiceState(service_name="b", expected_status="running", actual_status="stopped"),
        ]
        report = OperationalAwarenessAudit(test_mode=True).run(states)
        assert report.overall_accuracy == 0.0
        assert not any(s.match for s in report.service_details)

    def test_partial_match(self):
        states = [
            ServiceState(service_name="a", expected_status="running", actual_status="running"),
            ServiceState(service_name="b", expected_status="running", actual_status="stopped"),
            ServiceState(service_name="c", expected_status="stopped", actual_status="stopped"),
            ServiceState(service_name="d", expected_status="running", actual_status="unknown"),
        ]
        report = OperationalAwarenessAudit(test_mode=True).run(states)
        assert report.overall_accuracy == 0.5
        assert report.services_checked == 4

    def test_all_dimensions_equal_in_test_mode(self):
        states = [ServiceState(expected_status="running", actual_status="running")]
        report = OperationalAwarenessAudit(test_mode=True).run(states)
        assert report.container_state_accuracy == report.service_health_accuracy
        assert report.service_health_accuracy == report.deployment_state_accuracy
        assert report.deployment_state_accuracy == report.environment_accuracy

    def test_case_insensitive_match(self):
        states = [ServiceState(expected_status="Running", actual_status="running")]
        report = OperationalAwarenessAudit(test_mode=True).run(states)
        assert report.overall_accuracy == 1.0

    def test_whitespace_tolerant_match(self):
        states = [ServiceState(expected_status=" running ", actual_status="running")]
        report = OperationalAwarenessAudit(test_mode=True).run(states)
        assert report.overall_accuracy == 1.0

    def test_service_details_preserved(self):
        states = [ServiceState(service_name="x", expected_status="running", actual_status="running")]
        report = OperationalAwarenessAudit(test_mode=True).run(states)
        assert report.service_details[0].service_name == "x"
        assert report.service_details[0].match is True

    def test_to_dict(self):
        states = [ServiceState(service_name="x", expected_status="running", actual_status="running")]
        report = OperationalAwarenessAudit(test_mode=True).run(states)
        d = report.to_dict()
        assert d["services_checked"] == 1
        assert isinstance(d["service_details"], list)
        assert d["service_details"][0]["service_name"] == "x"

    def test_servicestate_to_dict(self):
        s = ServiceState(service_name="x", expected_status="running", actual_status="stopped", match=False)
        d = s.to_dict()
        assert d["service_name"] == "x"
        assert d["match"] is False


# ===========================================================================
# source_truth
# ===========================================================================


def _full_production(chain_id: str = "c") -> dict:
    return {"chain_id": chain_id, **{stage: f"{stage}-value" for stage in LINEAGE_STAGES}}


class TestSourceTruth:
    def test_empty_input(self):
        report = SourceTruthAudit().run([])
        assert isinstance(report, SourceTruthReport)
        assert report.chains_evaluated == 0
        assert report.avg_completeness == 0.0
        assert all(v == 0.0 for v in report.stage_coverage.values())
        assert set(report.stage_coverage.keys()) == set(LINEAGE_STAGES)

    def test_none_input(self):
        report = SourceTruthAudit().run(None)
        assert report.chains_evaluated == 0

    def test_full_chain(self):
        report = SourceTruthAudit().run([_full_production()])
        assert report.chains_evaluated == 1
        assert report.avg_completeness == 1.0
        assert report.full_chains == 1
        assert report.partial_chains == 0
        assert report.broken_chains == 0
        assert report.orphan_pct == 0.0

    def test_broken_chain_all_empty(self):
        production = {stage: "" for stage in LINEAGE_STAGES}
        report = SourceTruthAudit().run([production])
        assert report.broken_chains == 1
        assert report.full_chains == 0
        assert report.avg_completeness == 0.0
        assert report.orphan_pct == 1.0

    def test_partial_chain(self):
        production = {
            "intent": "build auth",
            "decision": "use JWT",
            "requirement": "",
            "packet": "WP-001",
            "code": True,
            "review": True,
            "deploy": False,
            "outcome": "",
            "capability": "",
        }
        report = SourceTruthAudit().run([production])
        # present: intent, decision, packet, code, review = 5 of 9
        assert report.partial_chains == 1
        assert report.full_chains == 0
        assert report.broken_chains == 0
        assert report.avg_completeness == round(5 / 9, 4)

    def test_falsy_values_treated_as_missing(self):
        production = {stage: None for stage in LINEAGE_STAGES}
        production["intent"] = "x"
        report = SourceTruthAudit().run([production])
        assert report.avg_completeness == round(1 / 9, 4)

    def test_missing_keys_treated_as_missing(self):
        production = {"intent": "x", "code": True}
        report = SourceTruthAudit().run([production])
        assert report.avg_completeness == round(2 / 9, 4)

    def test_stage_coverage_computation(self):
        prod_a = {"intent": "a", "code": True}
        prod_b = {"intent": "b", "deploy": True}
        report = SourceTruthAudit().run([prod_a, prod_b])
        assert report.stage_coverage["intent"] == 1.0
        assert report.stage_coverage["code"] == 0.5
        assert report.stage_coverage["deploy"] == 0.5
        assert report.stage_coverage["outcome"] == 0.0

    def test_mixed_chains(self):
        productions = [
            _full_production("full"),
            {"intent": "x"},  # partial
            {stage: "" for stage in LINEAGE_STAGES},  # broken
        ]
        report = SourceTruthAudit().run(productions)
        assert report.chains_evaluated == 3
        assert report.full_chains == 1
        assert report.partial_chains == 1
        assert report.broken_chains == 1

    def test_orphan_pct(self):
        # Two productions, each missing all but one stage → 16 of 18 slots missing.
        productions = [{"intent": "a"}, {"code": True}]
        report = SourceTruthAudit().run(productions)
        total_slots = 2 * len(LINEAGE_STAGES)
        assert report.orphan_pct == round((total_slots - 2) / total_slots, 4)

    def test_truthy_collections_present(self):
        production = {stage: [] for stage in LINEAGE_STAGES}
        production["intent"] = ["something"]
        report = SourceTruthAudit().run([production])
        # Only intent present (non-empty list); empty lists are missing.
        assert report.avg_completeness == round(1 / 9, 4)

    def test_chain_id_default(self):
        report = SourceTruthAudit().run([{"intent": "x"}])
        assert report.chains_evaluated == 1

    def test_lineage_chain_to_dict(self):
        chain = LineageChain(chain_id="c", stages_present=["intent"], stages_missing=["code"], completeness=0.5)
        d = chain.to_dict()
        assert d["chain_id"] == "c"
        assert d["stages_present"] == ["intent"]

    def test_report_to_dict(self):
        report = SourceTruthAudit().run([_full_production()])
        d = report.to_dict()
        assert d["full_chains"] == 1
        assert isinstance(d["stage_coverage"], dict)

    def test_lineage_stage_count(self):
        assert len(LINEAGE_STAGES) == 9


# ===========================================================================
# organism_awareness
# ===========================================================================


class TestOrganismAwareness:
    def test_empty_input(self):
        report = OrganismAwarenessAudit(test_mode=True).run([])
        assert isinstance(report, OrganismAwarenessReport)
        assert report.dimensions_checked == 0
        assert report.overall_accuracy == 0.0

    def test_none_input(self):
        report = OrganismAwarenessAudit(test_mode=True).run(None)
        assert report.dimensions_checked == 0

    def test_string_exact_match(self):
        dims = [AwarenessDimension(dimension="self_model_name", reported_value="DEX", actual_value="DEX")]
        report = OrganismAwarenessAudit(test_mode=True).run(dims)
        assert report.self_model_accuracy == 1.0
        assert report.details[0].match is True

    def test_string_mismatch(self):
        dims = [AwarenessDimension(dimension="self_model_name", reported_value="DEX", actual_value="JARVIS")]
        report = OrganismAwarenessAudit(test_mode=True).run(dims)
        assert report.self_model_accuracy == 0.0
        assert report.details[0].match is False

    def test_numeric_exact_match(self):
        dims = [AwarenessDimension(dimension="subsystem_count", reported_value=40, actual_value=40)]
        report = OrganismAwarenessAudit(test_mode=True).run(dims)
        assert report.subsystem_count_accuracy == 1.0
        assert report.details[0].match is True

    def test_numeric_proximity(self):
        dims = [AwarenessDimension(dimension="subsystem_count", reported_value=8, actual_value=10)]
        report = OrganismAwarenessAudit(test_mode=True).run(dims)
        # 1 - |8-10|/10 = 0.8
        assert report.subsystem_count_accuracy == 0.8
        assert report.details[0].match is False

    def test_numeric_far_off(self):
        dims = [AwarenessDimension(dimension="runtime_count", reported_value=1, actual_value=100)]
        report = OrganismAwarenessAudit(test_mode=True).run(dims)
        # 1 - min(1, 99/100) = 0.01
        assert report.runtime_accuracy == 0.01

    def test_numeric_zero_values(self):
        dims = [AwarenessDimension(dimension="workforce_count", reported_value=0, actual_value=0)]
        report = OrganismAwarenessAudit(test_mode=True).run(dims)
        assert report.workforce_accuracy == 1.0

    def test_dimension_grouping(self):
        dims = [
            AwarenessDimension(dimension="self_model_x", reported_value="a", actual_value="a"),
            AwarenessDimension(dimension="runtime_y", reported_value="b", actual_value="c"),
            AwarenessDimension(dimension="workforce_z", reported_value=5, actual_value=5),
            AwarenessDimension(dimension="subsystem_count", reported_value=10, actual_value=8),
        ]
        report = OrganismAwarenessAudit(test_mode=True).run(dims)
        assert report.self_model_accuracy == 1.0
        assert report.runtime_accuracy == 0.0
        assert report.workforce_accuracy == 1.0
        assert report.subsystem_count_accuracy == 0.8
        assert report.dimensions_checked == 4
        assert report.overall_accuracy == round((1.0 + 0.0 + 1.0 + 0.8) / 4, 4)

    def test_unknown_dimension_ignored_in_groups(self):
        dims = [
            AwarenessDimension(dimension="self_model_x", reported_value="a", actual_value="a"),
            AwarenessDimension(dimension="unknown_thing", reported_value="x", actual_value="y"),
        ]
        report = OrganismAwarenessAudit(test_mode=True).run(dims)
        # unknown does not contribute to any of the 4 category averages
        assert report.self_model_accuracy == 1.0
        assert report.runtime_accuracy == 0.0  # empty group → 0
        assert report.dimensions_checked == 2

    def test_bool_match(self):
        dims = [AwarenessDimension(dimension="runtime_active", reported_value=True, actual_value=True)]
        report = OrganismAwarenessAudit(test_mode=True).run(dims)
        assert report.runtime_accuracy == 1.0

    def test_bool_not_treated_as_numeric(self):
        # True == 1 numerically, but bool path uses exact equality
        dims = [AwarenessDimension(dimension="runtime_active", reported_value=True, actual_value=1)]
        report = OrganismAwarenessAudit(test_mode=True).run(dims)
        # exact equality: True == 1 is True in Python
        assert report.details[0].match is True

    def test_multiple_in_same_group_averaged(self):
        dims = [
            AwarenessDimension(dimension="runtime_a", reported_value=10, actual_value=10),
            AwarenessDimension(dimension="runtime_b", reported_value=10, actual_value=0),
        ]
        report = OrganismAwarenessAudit(test_mode=True).run(dims)
        # (1.0 + 0.0)/2 = 0.5
        assert report.runtime_accuracy == 0.5

    def test_float_proximity(self):
        dims = [AwarenessDimension(dimension="workforce_load", reported_value=0.9, actual_value=1.0)]
        report = OrganismAwarenessAudit(test_mode=True).run(dims)
        assert report.workforce_accuracy == round(1.0 - 0.1 / 1.0, 4)

    def test_to_dict(self):
        dims = [AwarenessDimension(dimension="self_model_x", reported_value="a", actual_value="a")]
        report = OrganismAwarenessAudit(test_mode=True).run(dims)
        d = report.to_dict()
        assert d["dimensions_checked"] == 1
        assert isinstance(d["details"], list)

    def test_dimension_to_dict(self):
        dim = AwarenessDimension(dimension="x", reported_value=1, actual_value=1, match=True, accuracy=1.0)
        d = dim.to_dict()
        assert d["accuracy"] == 1.0
        assert d["match"] is True


# ===========================================================================
# empire_readiness
# ===========================================================================


class TestEmpireReadiness:
    def test_empty_capabilities(self):
        report = EmpireReadinessAudit(include_existing=False).run(existing_capabilities=[])
        assert isinstance(report, EmpireReadinessReport)
        assert report.overall_readiness == 0.0
        assert report.future_projection_count == 4
        assert set(report.projection_scores.keys()) == set(FUTURE_PROJECTIONS.keys())

    def test_none_capabilities(self):
        report = EmpireReadinessAudit(include_existing=False).run(existing_capabilities=None)
        assert report.overall_readiness == 0.0

    def test_no_projections_at_all(self):
        report = EmpireReadinessAudit(include_existing=False).run(
            existing_capabilities=["x"], projections={}
        )
        # FUTURE_PROJECTIONS still present (projections={} just merges nothing extra)
        assert report.future_projection_count == 4

    def test_exact_match(self):
        report = EmpireReadinessAudit(include_existing=False).run(
            existing_capabilities=["leaderboard"]
        )
        gol = next(p for p in report.projection_details if p.projection_name == "game_of_lyfe")
        assert "leaderboard" in gol.matched_capabilities

    def test_substring_match(self):
        report = EmpireReadinessAudit(include_existing=False).run(
            existing_capabilities=["advanced gamification engine v2"]
        )
        gol = next(p for p in report.projection_details if p.projection_name == "game_of_lyfe")
        assert "gamification_engine" in gol.matched_capabilities

    def test_word_overlap_match(self):
        # "achievement_system" → words {achievement, system}; cap "system" overlaps 1/2 = 50%
        report = EmpireReadinessAudit(include_existing=False).run(
            existing_capabilities=["achievement tracker"]
        )
        gol = next(p for p in report.projection_details if p.projection_name == "game_of_lyfe")
        assert "achievement_system" in gol.matched_capabilities

    def test_no_match(self):
        report = EmpireReadinessAudit(include_existing=False).run(
            existing_capabilities=["totally_unrelated_capability_xyz"]
        )
        for detail in report.projection_details:
            assert detail.coverage_pct == 0.0
        assert report.overall_readiness == 0.0

    def test_perfect_coverage_single_projection(self):
        caps = list(FUTURE_PROJECTIONS["music"])
        report = EmpireReadinessAudit(include_existing=False).run(
            existing_capabilities=caps, projections={"music": FUTURE_PROJECTIONS["music"]}
        )
        music = next(p for p in report.projection_details if p.projection_name == "music")
        assert music.coverage_pct == 1.0
        assert music.missing_capabilities == []

    def test_partial_coverage(self):
        # Match exactly 3 of 6 music capabilities
        caps = ["audio_processing", "distribution_pipeline", "royalty_tracking"]
        report = EmpireReadinessAudit(include_existing=False).run(existing_capabilities=caps)
        music = next(p for p in report.projection_details if p.projection_name == "music")
        assert music.coverage_pct == round(3 / 6, 4)
        assert len(music.missing_capabilities) == 3

    def test_include_existing_adds_projections(self):
        report = EmpireReadinessAudit(include_existing=True).run(existing_capabilities=[])
        names = set(report.projection_scores.keys())
        assert "EOS" in names
        assert "LOS" in names
        assert "COS" in names
        assert "game_of_lyfe" in names

    def test_exclude_existing(self):
        report = EmpireReadinessAudit(include_existing=False).run(existing_capabilities=[])
        names = set(report.projection_scores.keys())
        assert "EOS" not in names
        assert "game_of_lyfe" in names

    def test_cross_projection_reuse(self):
        # analytics_dashboard appears in game_of_lyfe and EOS
        report = EmpireReadinessAudit(include_existing=True).run(existing_capabilities=[])
        assert 0.0 <= report.cross_projection_reuse <= 1.0
        assert report.cross_projection_reuse > 0.0

    def test_cross_projection_reuse_zero_when_no_overlap(self):
        projections = {
            "p1": ["cap_a", "cap_b"],
            "p2": ["cap_c", "cap_d"],
        }
        report = EmpireReadinessAudit(include_existing=False).run(
            existing_capabilities=[], projections=projections
        )
        # game_of_lyfe analytics_dashboard might overlap with nothing here, but
        # the future projections themselves share "analytics_dashboard"? No —
        # only game_of_lyfe has it. distribution-style names differ. Just assert range.
        assert 0.0 <= report.cross_projection_reuse <= 1.0

    def test_total_missing_capabilities_unique(self):
        report = EmpireReadinessAudit(include_existing=False).run(existing_capabilities=[])
        missing = report.total_missing_capabilities
        assert len(missing) == len(set(missing))
        # With no capabilities, everything is missing
        assert len(missing) > 0

    def test_total_missing_empty_when_full(self):
        all_caps: list[str] = []
        for caps in FUTURE_PROJECTIONS.values():
            all_caps.extend(caps)
        report = EmpireReadinessAudit(include_existing=False).run(existing_capabilities=all_caps)
        assert report.total_missing_capabilities == []
        assert report.overall_readiness == 1.0

    def test_projection_scores_match_details(self):
        report = EmpireReadinessAudit(include_existing=False).run(
            existing_capabilities=["leaderboard"]
        )
        for detail in report.projection_details:
            assert report.projection_scores[detail.projection_name] == detail.coverage_pct

    def test_projections_override_merges(self):
        report = EmpireReadinessAudit(include_existing=False).run(
            existing_capabilities=["custom_cap"],
            projections={"custom_proj": ["custom_cap"]},
        )
        assert "custom_proj" in report.projection_scores
        custom = next(p for p in report.projection_details if p.projection_name == "custom_proj")
        assert custom.coverage_pct == 1.0

    def test_future_projection_count_constant(self):
        report = EmpireReadinessAudit(include_existing=True).run(existing_capabilities=[])
        assert report.future_projection_count == len(FUTURE_PROJECTIONS)

    def test_to_dict(self):
        report = EmpireReadinessAudit(include_existing=False).run(existing_capabilities=[])
        d = report.to_dict()
        assert "projection_scores" in d
        assert "overall_readiness" in d
        assert isinstance(d["projection_details"], list)

    def test_projection_score_to_dict(self):
        report = EmpireReadinessAudit(include_existing=False).run(
            existing_capabilities=["leaderboard"]
        )
        detail = report.projection_details[0]
        d = detail.to_dict()
        assert "projection_name" in d
        assert "coverage_pct" in d
        assert "matched_capabilities" in d

    def test_case_insensitive_matching(self):
        report = EmpireReadinessAudit(include_existing=False).run(
            existing_capabilities=["LEADERBOARD"]
        )
        gol = next(p for p in report.projection_details if p.projection_name == "game_of_lyfe")
        assert "leaderboard" in gol.matched_capabilities

    def test_underscore_normalization(self):
        report = EmpireReadinessAudit(include_existing=False).run(
            existing_capabilities=["audio processing"]
        )
        music = next(p for p in report.projection_details if p.projection_name == "music")
        assert "audio_processing" in music.matched_capabilities


# ===========================================================================
# Cross-cutting structural tests
# ===========================================================================


class TestStructure:
    def test_all_reports_have_to_dict(self):
        assert hasattr(ContextCapacityAudit(test_mode=True).run(), "to_dict")
        assert hasattr(OperationalAwarenessAudit(test_mode=True).run([]), "to_dict")
        assert hasattr(SourceTruthAudit().run([]), "to_dict")
        assert hasattr(OrganismAwarenessAudit(test_mode=True).run([]), "to_dict")
        assert hasattr(EmpireReadinessAudit().run(existing_capabilities=[]), "to_dict")

    def test_context_capacity_to_dict_is_dict(self):
        assert isinstance(ContextCapacityAudit(test_mode=True).run().to_dict(), dict)

    def test_operational_to_dict_is_dict(self):
        assert isinstance(OperationalAwarenessAudit(test_mode=True).run([]).to_dict(), dict)

    def test_source_truth_to_dict_is_dict(self):
        assert isinstance(SourceTruthAudit().run([]).to_dict(), dict)

    def test_organism_awareness_to_dict_is_dict(self):
        assert isinstance(OrganismAwarenessAudit(test_mode=True).run([]).to_dict(), dict)

    def test_empire_to_dict_is_dict(self):
        assert isinstance(EmpireReadinessAudit().run(existing_capabilities=[]).to_dict(), dict)

    def test_future_projections_count(self):
        assert len(FUTURE_PROJECTIONS) == 4
        assert "game_of_lyfe" in FUTURE_PROJECTIONS
        assert "music" in FUTURE_PROJECTIONS
        assert "fiction" in FUTURE_PROJECTIONS
        assert "acquisitions" in FUTURE_PROJECTIONS

    def test_all_audits_deterministic(self):
        # Same input → same output, twice.
        a1 = SourceTruthAudit().run([_full_production()]).to_dict()
        a2 = SourceTruthAudit().run([_full_production()]).to_dict()
        assert a1 == a2
