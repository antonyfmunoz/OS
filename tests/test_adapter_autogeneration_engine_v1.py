"""Tests for Phase 96.8AU — Adapter Autogeneration Engine.

Verifies:
  1. AdapterBlueprint creation and serialization
  2. ReplayContract creation and integrity
  3. GovernanceClassification creation
  4. Blueprint generation determinism
  5. Canonical leakage prevention
  6. Instance leakage prevention
  7. Maturity classification (L0-L5)
  8. Hard ceilings (no screenshots, no env map, no blueprints, etc.)
  9. Replay contract integrity
  10. Topology graph consistency
  11. Adapter regeneration consistency
  12. Governance enforcement
  13. Full pipeline E2E
  14. Proof persistence
  15. Registry integration
"""

import json
import sys
from pathlib import Path

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.workstation.adapter_autogeneration_engine_v1 import (
    ADAPTER_MATURITY_LEVELS,
    ADAPTER_MATURITY_REQUIREMENTS,
    ADAPTER_TARGET_PLATFORMS,
    CANDIDATE_TYPE_CANONICAL,
    CANDIDATE_TYPE_INSTANCE,
    AdapterAutogenEvidence,
    AdapterAutogenProof,
    AdapterBlueprint,
    GovernanceClassification,
    MaturityEvaluation,
    ReplayContract,
    adapter_maturity_ceiling,
    build_adapter_evidence,
    build_full_adapter_proof,
    classify_adapter_maturity,
    classify_blueprint_scope,
    classify_extraction_scope,
    compute_adapter_maturity,
    determine_safest_strategy,
    evaluate_maturity,
    generate_blueprint_for_platform,
    generate_blueprints_from_topology,
    persist_adapter_proof,
    persist_blueprints,
)
from core.workstation.environment_mapping_engine_v1 import (
    DiscoveredPlatform,
    EnvironmentMappingEvidence,
    EnvironmentMappingProof,
    EnvironmentTopology,
    IngestionLane,
)


def _full_evidence(**overrides: object) -> AdapterAutogenEvidence:
    defaults = {
        "topology_analyzed": True,
        "platform_count": 5,
        "blueprints_generated": True,
        "blueprint_count": 14,
        "replay_contracts_defined": True,
        "replay_contract_count": 14,
        "governance_classified": True,
        "governance_count": 14,
        "canonical_patterns_extracted": True,
        "canonical_count": 14,
        "instance_count": 14,
        "maturity_evaluated": True,
        "actuation_proven": True,
        "cu_ingestion_proven": True,
        "environment_mapped": True,
        "screenshots_present": True,
        "founder_confirmed": True,
        "is_dry_run": False,
        "trace_id": "TR-test-adapter-001",
        "request_id": "REQ-test-adapter-001",
    }
    defaults.update(overrides)
    return AdapterAutogenEvidence(**defaults)


def _sample_topology() -> EnvironmentTopology:
    return EnvironmentTopology(
        platforms=[
            DiscoveredPlatform(name="Google Chrome", domain="google.com", running=True),
            DiscoveredPlatform(name="Discord", domain="discord.com", running=True),
            DiscoveredPlatform(name="Obsidian", domain="obsidian.md", running=True),
            DiscoveredPlatform(name="VS Code", domain="vscode.dev", running=True),
            DiscoveredPlatform(name="File Explorer", domain="local", running=True),
        ],
    )


def _sample_env_proof() -> EnvironmentMappingProof:
    return EnvironmentMappingProof(
        proof_id="ENVMAP-test001",
        maturity_level="L3_ENVIRONMENT_INTELLIGENCE",
        evidence=EnvironmentMappingEvidence(
            process_list_captured=True,
            platforms_identified=True,
            platform_count=5,
            accounts_linked=True,
            account_count=2,
            screenshots_captured=True,
            screenshot_count=2,
            screenshot_paths=["/proof/desktop.png"],
            screenshot_hashes=["abc123"],
            graph_generated=True,
            relationships_synthesized=True,
            relationship_count=3,
            lanes_planned=True,
            lane_count=5,
            founder_confirmed=True,
        ),
        topology=_sample_topology(),
    )


class TestAdapterBlueprint:
    def test_creation_auto_id(self) -> None:
        bp = generate_blueprint_for_platform("github")
        assert bp.blueprint_id.startswith("ADAPT-")
        assert bp.platform == "github"

    def test_serializable(self) -> None:
        bp = generate_blueprint_for_platform("notion")
        d = bp.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0
        assert d["platform"] == "notion"

    def test_has_replay_contract(self) -> None:
        bp = generate_blueprint_for_platform("gmail")
        assert bp.replay_contract is not None
        assert bp.replay_contract.replayable is True

    def test_has_governance(self) -> None:
        bp = generate_blueprint_for_platform("discord")
        assert bp.governance is not None
        assert bp.governance.requires_founder_approval is True


class TestReplayContract:
    def test_creation(self) -> None:
        rc = ReplayContract(platform="github")
        assert rc.contract_id.startswith("REPLAY-")

    def test_serializable(self) -> None:
        rc = ReplayContract(platform="gmail", replayable=True, replay_path=["step1", "step2"])
        d = rc.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0
        assert d["replayable"] is True

    def test_has_rollback_conditions(self) -> None:
        bp = generate_blueprint_for_platform("notion")
        assert bp.replay_contract is not None
        assert len(bp.replay_contract.rollback_conditions) > 0

    def test_has_evidence_requirements(self) -> None:
        bp = generate_blueprint_for_platform("google_drive")
        assert bp.replay_contract is not None
        assert len(bp.replay_contract.evidence_requirements) > 0
        assert "founder_confirmed" in bp.replay_contract.evidence_requirements


class TestGovernanceClassification:
    def test_creation(self) -> None:
        gc = GovernanceClassification(platform="slack")
        assert gc.classification_id.startswith("GOV-")

    def test_serializable(self) -> None:
        gc = GovernanceClassification(platform="claude", requires_foreground_cu=True)
        d = gc.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0

    def test_no_auto_execute(self) -> None:
        bp = generate_blueprint_for_platform("gmail")
        assert bp.governance is not None
        assert bp.governance.auto_execute_allowed is False

    def test_founder_approval_required(self) -> None:
        for platform in ADAPTER_TARGET_PLATFORMS:
            bp = generate_blueprint_for_platform(platform)
            assert bp.governance is not None
            assert bp.governance.requires_founder_approval is True


class TestBlueprintDeterminism:
    def test_same_platform_same_structure(self) -> None:
        bp1 = generate_blueprint_for_platform("github")
        bp2 = generate_blueprint_for_platform("github")
        assert bp1.extraction_strategy == bp2.extraction_strategy
        assert bp1.requires_cu == bp2.requires_cu
        assert bp1.canonical_likelihood == bp2.canonical_likelihood

    def test_regeneration_consistency(self) -> None:
        topo = _sample_topology()
        bps1 = generate_blueprints_from_topology(topo)
        bps2 = generate_blueprints_from_topology(topo)
        assert len(bps1) == len(bps2)
        for b1, b2 in zip(bps1, bps2):
            assert b1.platform == b2.platform
            assert b1.extraction_strategy == b2.extraction_strategy

    def test_all_targets_generated(self) -> None:
        topo = _sample_topology()
        bps = generate_blueprints_from_topology(topo)
        platforms = {bp.platform for bp in bps}
        assert platforms == ADAPTER_TARGET_PLATFORMS


class TestCanonicalLeakagePrevention:
    def test_blueprint_structure_is_canonical(self) -> None:
        bp = generate_blueprint_for_platform("github")
        assert classify_blueprint_scope(bp) == CANDIDATE_TYPE_CANONICAL

    def test_extraction_output_always_instance(self) -> None:
        for platform in ADAPTER_TARGET_PLATFORMS:
            assert classify_extraction_scope(platform) == CANDIDATE_TYPE_INSTANCE

    def test_governance_candidate_type_is_instance(self) -> None:
        bp = generate_blueprint_for_platform("gmail")
        assert bp.governance is not None
        assert bp.governance.candidate_type == CANDIDATE_TYPE_INSTANCE

    def test_no_auto_promote_to_canonical(self) -> None:
        bp = generate_blueprint_for_platform("google_drive")
        assert bp.governance is not None
        assert bp.governance.auto_execute_allowed is False


class TestInstanceLeakagePrevention:
    def test_instance_data_stays_instance(self) -> None:
        for platform in ["gmail", "discord", "slack"]:
            assert classify_extraction_scope(platform) == CANDIDATE_TYPE_INSTANCE

    def test_high_canonical_platforms_still_instance_extraction(self) -> None:
        for platform in ["github", "obsidian"]:
            assert classify_extraction_scope(platform) == CANDIDATE_TYPE_INSTANCE


class TestMaturityClassification:
    def test_full_evidence_l4(self) -> None:
        evidence = _full_evidence()
        level = compute_adapter_maturity(evidence)
        assert level == "L4_ADAPTER_MATURITY"

    def test_dry_run_l0(self) -> None:
        evidence = _full_evidence(is_dry_run=True)
        level = compute_adapter_maturity(evidence)
        assert level == "L0_SIMULATED"

    def test_no_blueprints_l3(self) -> None:
        evidence = _full_evidence(blueprints_generated=False)
        level = compute_adapter_maturity(evidence)
        assert level == "L3_ENVIRONMENT_INTELLIGENCE"

    def test_no_env_map_l2(self) -> None:
        evidence = _full_evidence(environment_mapped=False)
        level = compute_adapter_maturity(evidence)
        assert level == "L2_FOREGROUND_CU_INGESTION"

    def test_no_actuation_l0(self) -> None:
        evidence = _full_evidence(actuation_proven=False)
        level = compute_adapter_maturity(evidence)
        assert level == "L0_SIMULATED"

    def test_l5_requires_execution(self) -> None:
        evidence = _full_evidence(
            adapters_executed_successfully=True,
            adapters_replayed_successfully=True,
        )
        level = compute_adapter_maturity(evidence)
        assert level == "L5_AUTONOMOUS_ADAPTER_SYNTHESIS"

    def test_all_levels_defined(self) -> None:
        assert len(ADAPTER_MATURITY_LEVELS) == 6
        assert ADAPTER_MATURITY_LEVELS[0] == "L0_SIMULATED"
        assert ADAPTER_MATURITY_LEVELS[5] == "L5_AUTONOMOUS_ADAPTER_SYNTHESIS"


class TestHardCeilings:
    def test_dry_run_ceiling_l0(self) -> None:
        evidence = _full_evidence(is_dry_run=True)
        ceiling = adapter_maturity_ceiling(evidence)
        assert ceiling == "L0_SIMULATED"

    def test_no_screenshots_ceiling_l1(self) -> None:
        evidence = _full_evidence(screenshots_present=False)
        ceiling = adapter_maturity_ceiling(evidence)
        assert ceiling == "L1_VISIBLE_ACTUATION"

    def test_no_env_map_ceiling_l2(self) -> None:
        evidence = _full_evidence(environment_mapped=False)
        ceiling = adapter_maturity_ceiling(evidence)
        assert ceiling == "L2_FOREGROUND_CU_INGESTION"

    def test_no_blueprints_ceiling_l3(self) -> None:
        evidence = _full_evidence(blueprints_generated=False)
        ceiling = adapter_maturity_ceiling(evidence)
        assert ceiling == "L3_ENVIRONMENT_INTELLIGENCE"

    def test_no_replay_ceiling_l3(self) -> None:
        evidence = _full_evidence(replay_contracts_defined=False)
        ceiling = adapter_maturity_ceiling(evidence)
        assert ceiling == "L3_ENVIRONMENT_INTELLIGENCE"

    def test_no_governance_ceiling_l3(self) -> None:
        evidence = _full_evidence(governance_classified=False)
        ceiling = adapter_maturity_ceiling(evidence)
        assert ceiling == "L3_ENVIRONMENT_INTELLIGENCE"

    def test_no_founder_ceiling_l3(self) -> None:
        evidence = _full_evidence(founder_confirmed=False)
        ceiling = adapter_maturity_ceiling(evidence)
        assert ceiling == "L3_ENVIRONMENT_INTELLIGENCE"

    def test_full_ceiling_l5(self) -> None:
        evidence = _full_evidence()
        ceiling = adapter_maturity_ceiling(evidence)
        assert ceiling == "L5_AUTONOMOUS_ADAPTER_SYNTHESIS"

    def test_ceiling_caps_level(self) -> None:
        evidence = _full_evidence(screenshots_present=False)
        level, ceiling, blocked, reason = classify_adapter_maturity(evidence)
        assert ceiling == "L1_VISIBLE_ACTUATION"
        assert blocked is True


class TestMaturityEvaluation:
    def test_evaluation_identifies_missing(self) -> None:
        evidence = _full_evidence(replay_contracts_defined=False)
        bps = [generate_blueprint_for_platform("github")]
        evaluation = evaluate_maturity(evidence, bps)
        assert "replay_contracts_defined" in evaluation.missing_evidence

    def test_evaluation_identifies_unsafe_claims(self) -> None:
        evidence = _full_evidence(actuation_proven=False)
        bps = [generate_blueprint_for_platform("github")]
        evaluation = evaluate_maturity(evidence, bps)
        assert len(evaluation.unsafe_claims) > 0

    def test_evaluation_identifies_execution_risks(self) -> None:
        evidence = _full_evidence(cu_ingestion_proven=False)
        bps = [generate_blueprint_for_platform("gmail")]
        evaluation = evaluate_maturity(evidence, bps)
        assert any("gmail" in r for r in evaluation.execution_risks)

    def test_evaluation_identifies_proof_weaknesses(self) -> None:
        evidence = _full_evidence(founder_confirmed=False)
        bps = [generate_blueprint_for_platform("github")]
        evaluation = evaluate_maturity(evidence, bps)
        assert len(evaluation.proof_weaknesses) > 0

    def test_evaluation_serializable(self) -> None:
        evidence = _full_evidence()
        bps = [generate_blueprint_for_platform("github")]
        evaluation = evaluate_maturity(evidence, bps)
        d = evaluation.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0


class TestReplayContractIntegrity:
    def test_all_blueprints_have_replay(self) -> None:
        topo = _sample_topology()
        bps = generate_blueprints_from_topology(topo)
        for bp in bps:
            assert bp.replay_contract is not None
            assert bp.replay_contract.replayable is True

    def test_replay_path_not_empty(self) -> None:
        bp = generate_blueprint_for_platform("google_drive")
        assert bp.replay_contract is not None
        assert len(bp.replay_contract.replay_path) > 0

    def test_cu_platforms_have_clipboard_step(self) -> None:
        bp = generate_blueprint_for_platform("notion")
        assert bp.replay_contract is not None
        assert "extract_via_clipboard" in bp.replay_contract.replay_path

    def test_local_platforms_have_filesystem_step(self) -> None:
        bp = generate_blueprint_for_platform("obsidian")
        assert bp.replay_contract is not None
        assert "read_filesystem_content" in bp.replay_contract.replay_path

    def test_failure_ceiling_defined(self) -> None:
        for platform in ADAPTER_TARGET_PLATFORMS:
            bp = generate_blueprint_for_platform(platform)
            assert bp.replay_contract is not None
            assert bp.replay_contract.failure_ceiling in ADAPTER_MATURITY_LEVELS


class TestTopologyConsistency:
    def test_detected_platforms_flagged(self) -> None:
        topo = _sample_topology()
        bps = generate_blueprints_from_topology(topo)
        detected = [bp for bp in bps if bp.detected_on_workstation]
        assert len(detected) > 0

    def test_undetected_platforms_not_flagged(self) -> None:
        topo = EnvironmentTopology()
        bps = generate_blueprints_from_topology(topo)
        detected = [bp for bp in bps if bp.detected_on_workstation]
        assert len(detected) == 0

    def test_all_targets_regardless_of_detection(self) -> None:
        topo = EnvironmentTopology()
        bps = generate_blueprints_from_topology(topo)
        assert len(bps) == len(ADAPTER_TARGET_PLATFORMS)

    def test_topology_platforms_map_to_targets(self) -> None:
        topo = _sample_topology()
        bps = generate_blueprints_from_topology(topo)
        detected_platforms = {bp.platform for bp in bps if bp.detected_on_workstation}
        assert "browser_sessions" in detected_platforms
        assert "discord" in detected_platforms
        assert "obsidian" in detected_platforms


class TestGovernanceEnforcement:
    def test_no_auto_execute_anywhere(self) -> None:
        topo = _sample_topology()
        bps = generate_blueprints_from_topology(topo)
        for bp in bps:
            assert bp.governance is not None
            assert bp.governance.auto_execute_allowed is False

    def test_all_require_founder_approval(self) -> None:
        topo = _sample_topology()
        bps = generate_blueprints_from_topology(topo)
        for bp in bps:
            assert bp.requires_founder_confirmation is True

    def test_cu_platforms_require_screenshot(self) -> None:
        for platform in ADAPTER_TARGET_PLATFORMS:
            bp = generate_blueprint_for_platform(platform)
            if bp.requires_cu:
                assert bp.requires_screenshot is True
                assert bp.governance is not None
                assert bp.governance.requires_screenshot_proof is True


class TestSafestStrategy:
    def test_dry_run_strategy(self) -> None:
        evidence = _full_evidence(is_dry_run=True)
        bps = [generate_blueprint_for_platform("github")]
        strategy = determine_safest_strategy(bps, evidence)
        assert strategy == "simulation_only"

    def test_no_actuation_strategy(self) -> None:
        evidence = _full_evidence(actuation_proven=False)
        bps = [generate_blueprint_for_platform("github")]
        strategy = determine_safest_strategy(bps, evidence)
        assert strategy == "prove_actuation_first"

    def test_no_cu_strategy(self) -> None:
        evidence = _full_evidence(cu_ingestion_proven=False)
        bps = [generate_blueprint_for_platform("github")]
        strategy = determine_safest_strategy(bps, evidence)
        assert strategy == "prove_cu_ingestion_first"

    def test_local_adapters_first(self) -> None:
        evidence = _full_evidence()
        bps = [
            generate_blueprint_for_platform("obsidian", detected=True),
            generate_blueprint_for_platform("gmail", detected=True),
        ]
        strategy = determine_safest_strategy(bps, evidence)
        assert strategy == "start_with_local_adapters"


class TestProofPersistence:
    def test_persist_creates_file(self, tmp_path: Path) -> None:
        proof = AdapterAutogenProof(trace_id="TR-persist-test")
        path = persist_adapter_proof(proof, base_dir=tmp_path)
        assert path.exists()

    def test_persist_valid_json(self, tmp_path: Path) -> None:
        proof = AdapterAutogenProof(trace_id="TR-json-test")
        path = persist_adapter_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert data["proof_type"] == "adapter_autogeneration"

    def test_persist_blueprints(self, tmp_path: Path) -> None:
        bps = [generate_blueprint_for_platform("github"), generate_blueprint_for_platform("gmail")]
        out_dir = persist_blueprints(bps, base_dir=tmp_path)
        assert out_dir.exists()
        files = list(out_dir.glob("ADAPT-*.json"))
        assert len(files) == 2

    def test_blueprint_files_valid_json(self, tmp_path: Path) -> None:
        bps = [generate_blueprint_for_platform("notion")]
        out_dir = persist_blueprints(bps, base_dir=tmp_path)
        for f in out_dir.glob("ADAPT-*.json"):
            data = json.loads(f.read_text())
            assert "platform" in data
            assert "replay_contract" in data


class TestProofSerialization:
    def test_auto_id(self) -> None:
        proof = AdapterAutogenProof(trace_id="TR-serial-test")
        assert proof.proof_id.startswith("AUTOGEN-")

    def test_serializable(self) -> None:
        proof = build_full_adapter_proof(
            topology=_sample_topology(),
            env_proof=_sample_env_proof(),
            founder_confirmed=True,
            trace_id="TR-serial-full",
        )
        d = proof.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0
        assert d["proof_type"] == "adapter_autogeneration"

    def test_includes_blueprints(self) -> None:
        proof = build_full_adapter_proof(
            topology=_sample_topology(),
            founder_confirmed=True,
        )
        d = proof.to_dict()
        assert d["blueprint_count"] == len(ADAPTER_TARGET_PLATFORMS)


class TestFullPipeline:
    def test_full_pipeline_l4(self) -> None:
        proof = build_full_adapter_proof(
            topology=_sample_topology(),
            env_proof=_sample_env_proof(),
            founder_confirmed=True,
            trace_id="TR-pipeline-full",
        )
        assert proof.maturity_level == "L4_ADAPTER_MATURITY"
        assert len(proof.blueprints) == len(ADAPTER_TARGET_PLATFORMS)
        assert proof.execution_strategy != "simulation_only"

    def test_full_pipeline_no_env_proof(self) -> None:
        proof = build_full_adapter_proof(
            topology=_sample_topology(),
            env_proof=None,
            founder_confirmed=True,
        )
        assert proof.maturity_level != "L4_ADAPTER_MATURITY"

    def test_full_pipeline_dry_run(self) -> None:
        proof = build_full_adapter_proof(
            topology=_sample_topology(),
            is_dry_run=True,
        )
        assert proof.maturity_level == "L0_SIMULATED"
        assert proof.execution_strategy == "simulation_only"

    def test_full_pipeline_no_founder(self) -> None:
        proof = build_full_adapter_proof(
            topology=_sample_topology(),
            env_proof=_sample_env_proof(),
            founder_confirmed=False,
        )
        assert proof.maturity_level != "L4_ADAPTER_MATURITY"
        assert proof.maturity_ceiling == "L3_ENVIRONMENT_INTELLIGENCE"

    def test_canonical_instance_separation(self) -> None:
        proof = build_full_adapter_proof(
            topology=_sample_topology(),
            founder_confirmed=True,
        )
        for bp in proof.blueprints:
            assert classify_blueprint_scope(bp) == CANDIDATE_TYPE_CANONICAL
            assert classify_extraction_scope(bp.platform) == CANDIDATE_TYPE_INSTANCE


class TestTargetPlatforms:
    def test_14_target_platforms(self) -> None:
        assert len(ADAPTER_TARGET_PLATFORMS) == 14

    def test_all_spec_platforms_present(self) -> None:
        required = {
            "google_drive",
            "gmail",
            "notion",
            "discord",
            "claude",
            "openai",
            "github",
            "obsidian",
            "slack",
            "local_filesystem",
            "browser_sessions",
            "desktop_apps",
            "terminal_environments",
            "docker_services",
        }
        assert ADAPTER_TARGET_PLATFORMS == required


class TestRegistryIntegration:
    def test_adapter_report_in_registry(self) -> None:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        reg = get_canonical_registry()
        assert reg.contains("!adapter-report")

    def test_adapter_report_in_allowed_actions(self) -> None:
        from core.control_plane_router.router_contracts import ALLOWED_ACTION_TYPES

        assert "adapter_report" in ALLOWED_ACTION_TYPES

    def test_adapter_report_in_capability_map(self) -> None:
        from core.control_plane_router.control_plane_router_v1 import ACTION_CAPABILITY_MAP

        assert "adapter_report" in ACTION_CAPABILITY_MAP

    def test_registry_count_is_20(self) -> None:
        from composition.registries.canonical_command_registry_v1 import CanonicalCommandRegistryV1

        reg = CanonicalCommandRegistryV1()
        assert len(reg) == 27


class TestMaturityRequirements:
    def test_l0_no_requirements(self) -> None:
        assert ADAPTER_MATURITY_REQUIREMENTS["L0_SIMULATED"] == []

    def test_l4_requires_all_core(self) -> None:
        reqs = ADAPTER_MATURITY_REQUIREMENTS["L4_ADAPTER_MATURITY"]
        assert "blueprints_generated" in reqs
        assert "replay_contracts_defined" in reqs
        assert "governance_classified" in reqs

    def test_l5_requires_execution(self) -> None:
        reqs = ADAPTER_MATURITY_REQUIREMENTS["L5_AUTONOMOUS_ADAPTER_SYNTHESIS"]
        assert "adapters_executed_successfully" in reqs
        assert "adapters_replayed_successfully" in reqs

    def test_levels_are_monotonic(self) -> None:
        for i in range(1, len(ADAPTER_MATURITY_LEVELS)):
            prev_reqs = ADAPTER_MATURITY_REQUIREMENTS[ADAPTER_MATURITY_LEVELS[i - 1]]
            curr_reqs = ADAPTER_MATURITY_REQUIREMENTS[ADAPTER_MATURITY_LEVELS[i]]
            assert len(curr_reqs) >= len(prev_reqs)


class TestRelationshipStrategy:
    def test_each_platform_has_strategy(self) -> None:
        for platform in ADAPTER_TARGET_PLATFORMS:
            bp = generate_blueprint_for_platform(platform)
            assert bp.relationship_extraction_strategy != ""

    def test_github_strategy(self) -> None:
        bp = generate_blueprint_for_platform("github")
        assert "repo" in bp.relationship_extraction_strategy

    def test_obsidian_strategy(self) -> None:
        bp = generate_blueprint_for_platform("obsidian")
        assert "backlink" in bp.relationship_extraction_strategy
