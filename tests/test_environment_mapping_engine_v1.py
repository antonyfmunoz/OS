"""Tests for Phase 96.8AT — Environment Mapping Engine.

Verifies:
  1. DiscoveredPlatform/Account/Workspace creation and serialization
  2. RelationshipEdge deduplication via canonical_key
  3. Duplicate relationship suppression
  4. Canonical/instance platform classification
  5. Canonical leakage prevention (platforms default instance)
  6. Instance leakage prevention (no accidental canonical promotion)
  7. Graph integrity validation (topology consistency)
  8. Ingestion lane planner correctness
  9. Replay determinism (canonical_key stable)
  10. Stale relay blocking
  11. Maturity classification (L0-L3)
  12. Hard ceilings (no screenshots, no graph, no relationships, no lanes)
  13. Dry run always L0
  14. Evidence extraction from relay result
  15. Proof persistence
  16. Full pipeline E2E
  17. Transport integration
"""

import json
import sys
from pathlib import Path

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.workstation.environment_mapping_engine_v1 import (
    CANDIDATE_TYPE_CANONICAL,
    CANDIDATE_TYPE_INSTANCE,
    DISCOVERY_DOMAINS,
    ENVIRONMENT_MATURITY_REQUIREMENTS,
    DiscoveredAccount,
    DiscoveredPlatform,
    DiscoveredWorkspace,
    EnvironmentMappingEvidence,
    EnvironmentMappingProof,
    EnvironmentTopology,
    IngestionLane,
    RelationshipEdge,
    build_environment_topology,
    build_full_environment_proof,
    classify_environment_mapping,
    classify_platform_type,
    compute_environment_maturity,
    environment_maturity_ceiling,
    extract_accounts_from_browser_sessions,
    extract_accounts_from_chrome_profiles,
    extract_mapping_evidence,
    extract_platforms_from_installed_apps,
    extract_platforms_from_process_list,
    persist_environment_mapping_proof,
    plan_ingestion_lanes,
    synthesize_relationships,
)
from core.actuation.actuator_maturity_v1 import ActuatorMaturityLevel


def _full_evidence(**overrides: object) -> EnvironmentMappingEvidence:
    defaults = {
        "process_list_captured": True,
        "platforms_identified": True,
        "platform_count": 5,
        "accounts_linked": True,
        "account_count": 3,
        "workspaces_discovered": True,
        "workspace_count": 2,
        "relationships_synthesized": True,
        "relationship_count": 4,
        "lanes_planned": True,
        "lane_count": 5,
        "screenshots_captured": True,
        "screenshot_count": 2,
        "screenshot_paths": ["/proof/desktop.png", "/proof/taskbar.png"],
        "screenshot_hashes": ["abc123"],
        "graph_generated": True,
        "canonical_separated": True,
        "canonical_count": 1,
        "instance_count": 4,
        "founder_confirmed": True,
        "desktop_unlocked": True,
        "desktop_session_active": True,
        "is_dry_run": False,
        "trace_id": "TR-test-env-001",
        "request_id": "REQ-test-env-001",
        "relay_node_id": "WRN-test",
        "relay_machine": "DESKTOP-TEST",
    }
    defaults.update(overrides)
    return EnvironmentMappingEvidence(**defaults)


def _full_relay_result(**overrides: object) -> dict:
    result = {
        "request_id": "REQ-W0-EXPLORE-ENV-test001",
        "trace_id": "W0-explore-env-test001",
        "action_type": "explore_environment",
        "adapter_status": "completed",
        "dry_run": False,
        "node_id": "WRN-test",
        "machine_name": "DESKTOP-TEST",
        "observed_desktop_state": {
            "desktop_unlocked": True,
            "active_user_session": True,
            "monitor_detected": True,
            "screenshot_path": "/proof/desktop.png",
            "screenshot_hash": "hash123",
        },
        "discovery_result": {
            "processes": [
                {
                    "name": "chrome.exe",
                    "pid": 1234,
                    "has_window": True,
                    "window_title": "Google - Google Chrome",
                },
                {"name": "Discord.exe", "pid": 2345, "has_window": True, "window_title": "Discord"},
                {"name": "Code.exe", "pid": 3456, "has_window": True, "window_title": "VS Code"},
                {
                    "name": "explorer.exe",
                    "pid": 4567,
                    "has_window": True,
                    "window_title": "File Explorer",
                },
                {
                    "name": "Obsidian.exe",
                    "pid": 5678,
                    "has_window": True,
                    "window_title": "Obsidian",
                },
            ],
            "installed_apps": [
                {
                    "name": "Google Chrome",
                    "publisher": "Google LLC",
                    "path": "C:\\Program Files\\Google",
                },
                {
                    "name": "Notion",
                    "publisher": "Notion Labs",
                    "path": "C:\\Users\\test\\AppData\\Local\\Notion",
                },
                {"name": "Slack", "publisher": "Slack Technologies", "path": ""},
            ],
            "chrome_profiles": [
                {"name": "Antony", "email": "antonyfm@empyreanstudios.co", "is_default": True},
                {"name": "Personal", "email": "antony@personal.com", "is_default": False},
            ],
            "browser_sessions": [
                {
                    "platform": "gmail",
                    "window_title": "Gmail - antonyfm@empyreanstudios.co",
                    "email": "antonyfm@empyreanstudios.co",
                    "username": "",
                },
                {
                    "platform": "github",
                    "window_title": "GitHub - antonyfmunoz",
                    "email": "",
                    "username": "antonyfmunoz",
                },
            ],
            "workspaces": [
                {
                    "name": "EOS Vault",
                    "platform": "Obsidian",
                    "type": "vault",
                    "path": "C:\\Users\\test\\vault",
                    "detected_via": "obsidian_config",
                },
                {
                    "name": "OS",
                    "platform": "git",
                    "type": "repository",
                    "path": "C:\\Users\\test\\repos\\OS",
                    "detected_via": "filesystem_scan",
                },
            ],
            "workspaces_discovered": True,
            "screenshots": {
                "paths": ["/proof/desktop.png", "/proof/taskbar.png"],
                "hashes": ["hash123"],
            },
        },
        "stages_completed": [
            "relay_dispatched",
            "processes_enumerated",
            "apps_enumerated",
            "chrome_profiles_discovered",
            "browser_sessions_discovered",
            "workspaces_discovered",
            "screenshot_captured",
        ],
    }
    result.update(overrides)
    return result


class TestDiscoveredPlatform:
    def test_default_creation(self) -> None:
        p = DiscoveredPlatform(name="Chrome", domain="google.com")
        assert p.platform_id.startswith("PLAT-")
        assert p.candidate_type == CANDIDATE_TYPE_INSTANCE

    def test_to_dict_serializable(self) -> None:
        p = DiscoveredPlatform(name="Chrome", domain="google.com", running=True)
        d = p.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0
        assert d["running"] is True


class TestDiscoveredAccount:
    def test_default_creation(self) -> None:
        a = DiscoveredAccount(email="test@test.com", platform="chrome")
        assert a.account_id.startswith("ACCT-")
        assert a.candidate_type == CANDIDATE_TYPE_INSTANCE

    def test_to_dict_serializable(self) -> None:
        a = DiscoveredAccount(email="test@test.com", platform="chrome")
        d = a.to_dict()
        assert d["email"] == "test@test.com"


class TestDiscoveredWorkspace:
    def test_default_creation(self) -> None:
        w = DiscoveredWorkspace(name="My Vault", platform="Obsidian")
        assert w.workspace_id.startswith("WKSP-")

    def test_to_dict_serializable(self) -> None:
        w = DiscoveredWorkspace(name="My Vault", platform="Obsidian")
        d = w.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0


class TestRelationshipEdge:
    def test_canonical_key_stable(self) -> None:
        e1 = RelationshipEdge(source_id="A", target_id="B", relationship="same_email")
        e2 = RelationshipEdge(source_id="B", target_id="A", relationship="same_email")
        assert e1.canonical_key == e2.canonical_key

    def test_different_relationships_different_keys(self) -> None:
        e1 = RelationshipEdge(source_id="A", target_id="B", relationship="same_email")
        e2 = RelationshipEdge(source_id="A", target_id="B", relationship="same_domain")
        assert e1.canonical_key != e2.canonical_key

    def test_to_dict_serializable(self) -> None:
        e = RelationshipEdge(source_id="A", target_id="B", relationship="test", confidence=0.95)
        d = e.to_dict()
        assert d["confidence"] == 0.95


class TestDuplicateRelationshipSuppression:
    def test_synthesize_deduplicates_same_email(self) -> None:
        acct1 = DiscoveredAccount(account_id="ACCT-1", email="test@test.com", platform="chrome")
        acct2 = DiscoveredAccount(account_id="ACCT-2", email="test@test.com", platform="gmail")
        plat = DiscoveredPlatform(platform_id="PLAT-1", name="Google Chrome", domain="google.com")
        edges = synthesize_relationships([plat], [acct1, acct2], [])
        same_email_edges = [e for e in edges if e.relationship == "same_email"]
        assert len(same_email_edges) == 1

    def test_no_duplicate_canonical_keys(self) -> None:
        acct1 = DiscoveredAccount(account_id="A1", email="a@b.com", platform="chrome")
        acct2 = DiscoveredAccount(account_id="A2", email="a@b.com", platform="gmail")
        edges = synthesize_relationships([], [acct1, acct2], [])
        keys = [e.canonical_key for e in edges]
        assert len(keys) == len(set(keys))


class TestCanonicalLeakagePrevention:
    def test_platforms_default_to_instance(self) -> None:
        p = DiscoveredPlatform(name="Discord", domain="discord.com")
        assert p.candidate_type == CANDIDATE_TYPE_INSTANCE

    def test_accounts_always_instance(self) -> None:
        a = DiscoveredAccount(email="test@test.com", platform="chrome")
        assert a.candidate_type == CANDIDATE_TYPE_INSTANCE

    def test_classify_personal_account_is_instance(self) -> None:
        result = classify_platform_type("Personal Account", "inbox.com")
        assert result == CANDIDATE_TYPE_INSTANCE

    def test_classify_workspace_is_instance(self) -> None:
        result = classify_platform_type("Team Workspace", "company.com")
        assert result == CANDIDATE_TYPE_INSTANCE


class TestInstanceLeakagePrevention:
    def test_canonical_requires_explicit_indicators(self) -> None:
        result = classify_platform_type("My App", "myapp.com")
        assert result == CANDIDATE_TYPE_INSTANCE

    def test_canonical_only_with_strong_signal(self) -> None:
        result = classify_platform_type("Protocol Framework", "framework.dev")
        assert result == CANDIDATE_TYPE_CANONICAL

    def test_mixed_signals_instance_wins(self) -> None:
        result = classify_platform_type("Personal Template Workspace", "")
        assert result == CANDIDATE_TYPE_INSTANCE


class TestPlatformClassification:
    def test_framework_is_canonical(self) -> None:
        assert classify_platform_type("React Framework", "") == CANDIDATE_TYPE_CANONICAL

    def test_open_source_is_canonical(self) -> None:
        assert classify_platform_type("open_source tool", "") == CANDIDATE_TYPE_CANONICAL

    def test_subscription_is_instance(self) -> None:
        assert classify_platform_type("Subscription Service", "") == CANDIDATE_TYPE_INSTANCE

    def test_inbox_is_instance(self) -> None:
        assert classify_platform_type("My Inbox", "") == CANDIDATE_TYPE_INSTANCE


class TestGraphIntegrity:
    def test_topology_counts_consistent(self) -> None:
        relay = _full_relay_result()
        topo = build_environment_topology(relay)
        assert topo.platform_count == len(topo.platforms)
        assert topo.account_count == len(topo.accounts)
        assert topo.workspace_count == len(topo.workspaces)
        assert topo.relationship_count == len(topo.relationships)
        assert topo.lane_count == len(topo.ingestion_lanes)

    def test_all_relationship_entities_exist(self) -> None:
        relay = _full_relay_result()
        topo = build_environment_topology(relay)
        all_ids = set()
        for p in topo.platforms:
            all_ids.add(p.platform_id)
        for a in topo.accounts:
            all_ids.add(a.account_id)
        for w in topo.workspaces:
            all_ids.add(w.workspace_id)
        for edge in topo.relationships:
            assert edge.source_id in all_ids, f"source {edge.source_id} not in graph"
            assert edge.target_id in all_ids, f"target {edge.target_id} not in graph"

    def test_no_self_referencing_edges(self) -> None:
        relay = _full_relay_result()
        topo = build_environment_topology(relay)
        for edge in topo.relationships:
            assert edge.source_id != edge.target_id

    def test_topology_serializable(self) -> None:
        relay = _full_relay_result()
        topo = build_environment_topology(relay)
        d = topo.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0

    def test_deduplicated_platforms(self) -> None:
        relay = _full_relay_result()
        relay["discovery_result"]["installed_apps"].append(
            {"name": "Google Chrome", "publisher": "Google", "path": ""}
        )
        topo = build_environment_topology(relay)
        chrome_platforms = [p for p in topo.platforms if "Chrome" in p.name]
        assert len(chrome_platforms) == 1


class TestLanePlannerCorrectness:
    def test_lanes_generated_for_platforms(self) -> None:
        platforms = [
            DiscoveredPlatform(name="Google Chrome", domain="google.com"),
            DiscoveredPlatform(name="Discord", domain="discord.com"),
        ]
        lanes = plan_ingestion_lanes(platforms, [])
        assert len(lanes) >= 2

    def test_local_methods_dont_require_cu(self) -> None:
        platforms = [
            DiscoveredPlatform(name="Obsidian", domain="obsidian.md"),
        ]
        lanes = plan_ingestion_lanes(platforms, [])
        obsidian_lanes = [l for l in lanes if l.platform == "Obsidian"]
        assert len(obsidian_lanes) == 1
        assert obsidian_lanes[0].requires_cu is False
        assert obsidian_lanes[0].requires_foreground is False

    def test_web_methods_require_cu(self) -> None:
        platforms = [
            DiscoveredPlatform(name="Google Chrome", domain="google.com"),
        ]
        lanes = plan_ingestion_lanes(platforms, [])
        assert all(l.requires_cu for l in lanes)

    def test_all_lanes_require_founder_confirmation(self) -> None:
        platforms = [
            DiscoveredPlatform(name="Google Chrome", domain="google.com"),
            DiscoveredPlatform(name="Obsidian", domain="obsidian.md"),
        ]
        lanes = plan_ingestion_lanes(platforms, [])
        assert all(l.requires_founder_confirmation for l in lanes)

    def test_lane_serializable(self) -> None:
        lane = IngestionLane(platform="Chrome", extraction_method="foreground_cu_clipboard")
        d = lane.to_dict()
        assert d["requires_cu"] is True
        assert d["safety_rating"] == "safe"


class TestReplayDeterminism:
    def test_canonical_key_deterministic(self) -> None:
        e1 = RelationshipEdge(edge_id="E1", source_id="X", target_id="Y", relationship="same_email")
        e2 = RelationshipEdge(edge_id="E2", source_id="X", target_id="Y", relationship="same_email")
        assert e1.canonical_key == e2.canonical_key

    def test_canonical_key_order_independent(self) -> None:
        e1 = RelationshipEdge(source_id="A", target_id="B", relationship="r")
        e2 = RelationshipEdge(source_id="B", target_id="A", relationship="r")
        assert e1.canonical_key == e2.canonical_key


class TestStaleRelayBlocked:
    def test_stale_heartbeat_blocks(self, tmp_path: Path) -> None:
        from datetime import datetime, timedelta, timezone
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from core.workstation.workstation_relay_self_heal_v1 import (
            should_allow_chrome_proof,
        )

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-stale",
            desktop_session_active=True,
            chrome_available=True,
            timestamp=(now - timedelta(seconds=300)).isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)
        allowed, reason = should_allow_chrome_proof(tmp_path)
        assert allowed is False


class TestDryRunBlocked:
    def test_dry_run_always_l0(self) -> None:
        e = _full_evidence(is_dry_run=True)
        proof = classify_environment_mapping(e)
        assert proof.maturity_level == "L0_NO_MAPPING"

    def test_dry_run_ceiling_l0(self) -> None:
        e = _full_evidence(is_dry_run=True)
        proof = classify_environment_mapping(e)
        assert proof.maturity_ceiling == "L0_NO_MAPPING"

    def test_dry_run_escalation_blocked(self) -> None:
        e = _full_evidence(is_dry_run=True)
        proof = classify_environment_mapping(e)
        assert proof.escalation_blocked is True
        assert "dry_run" in proof.escalation_reason


class TestMaturityClassification:
    def test_full_evidence_l3(self) -> None:
        e = _full_evidence()
        level = compute_environment_maturity(e)
        assert level == "L3_ENVIRONMENT_INTELLIGENCE"

    def test_processes_only_l1(self) -> None:
        e = EnvironmentMappingEvidence(process_list_captured=True)
        level = compute_environment_maturity(e)
        assert level == "L1_PROCESSES_ENUMERATED"

    def test_platforms_only_l2(self) -> None:
        e = EnvironmentMappingEvidence(process_list_captured=True, platforms_identified=True)
        level = compute_environment_maturity(e)
        assert level == "L2_PLATFORMS_IDENTIFIED"

    def test_empty_l0(self) -> None:
        e = EnvironmentMappingEvidence()
        level = compute_environment_maturity(e)
        assert level == "L0_NO_MAPPING"

    def test_full_proof_not_blocked(self) -> None:
        e = _full_evidence()
        proof = classify_environment_mapping(e)
        assert proof.escalation_blocked is False


class TestHardCeilings:
    def test_no_screenshots_caps_l1(self) -> None:
        e = _full_evidence(screenshots_captured=False, screenshot_count=0)
        ceiling = environment_maturity_ceiling(e)
        assert ceiling == "L1_PROCESSES_ENUMERATED"

    def test_no_graph_caps_l2(self) -> None:
        e = _full_evidence(graph_generated=False, platform_count=0)
        ceiling = environment_maturity_ceiling(e)
        assert ceiling == "L2_PLATFORMS_IDENTIFIED"

    def test_no_relationships_caps_l2(self) -> None:
        e = _full_evidence(relationships_synthesized=False, relationship_count=0)
        ceiling = environment_maturity_ceiling(e)
        assert ceiling == "L2_PLATFORMS_IDENTIFIED"

    def test_no_lanes_caps_l2(self) -> None:
        e = _full_evidence(lanes_planned=False, lane_count=0)
        ceiling = environment_maturity_ceiling(e)
        assert ceiling == "L2_PLATFORMS_IDENTIFIED"

    def test_no_founder_caps_l2(self) -> None:
        e = _full_evidence(founder_confirmed=False)
        ceiling = environment_maturity_ceiling(e)
        assert ceiling == "L2_PLATFORMS_IDENTIFIED"

    def test_full_evidence_ceiling_l3(self) -> None:
        e = _full_evidence()
        ceiling = environment_maturity_ceiling(e)
        assert ceiling == "L3_ENVIRONMENT_INTELLIGENCE"

    def test_ceiling_caps_level(self) -> None:
        e = _full_evidence(screenshots_captured=False, screenshot_count=0)
        proof = classify_environment_mapping(e)
        assert proof.maturity_level in ("L0_NO_MAPPING", "L1_PROCESSES_ENUMERATED")


class TestEvidenceExtraction:
    def test_extract_from_full_relay(self) -> None:
        relay = _full_relay_result()
        e = extract_mapping_evidence(relay, founder_confirmed=True)
        assert e.process_list_captured is True
        assert e.platforms_identified is True
        assert e.accounts_linked is True
        assert e.screenshots_captured is True
        assert e.founder_confirmed is True

    def test_extract_dry_run(self) -> None:
        relay = _full_relay_result(dry_run=True)
        relay["discovery_result"] = {}
        relay["observed_desktop_state"] = {}
        e = extract_mapping_evidence(relay)
        assert e.is_dry_run is True

    def test_extract_empty_discovery(self) -> None:
        relay = _full_relay_result()
        relay["discovery_result"] = {}
        e = extract_mapping_evidence(relay)
        assert e.process_list_captured is False
        assert e.accounts_linked is False


class TestProcessExtraction:
    def test_extract_known_processes(self) -> None:
        processes = [
            {"name": "chrome.exe", "pid": 1, "has_window": True, "window_title": "Chrome"},
            {"name": "Discord.exe", "pid": 2, "has_window": True, "window_title": "Discord"},
        ]
        platforms = extract_platforms_from_process_list(processes)
        names = [p.name for p in platforms]
        assert "Google Chrome" in names
        assert "Discord" in names

    def test_dedup_processes(self) -> None:
        processes = [
            {"name": "chrome.exe", "pid": 1, "has_window": True, "window_title": ""},
            {"name": "chrome.exe", "pid": 2, "has_window": True, "window_title": ""},
        ]
        platforms = extract_platforms_from_process_list(processes)
        assert len(platforms) == 1

    def test_unknown_process_ignored(self) -> None:
        processes = [
            {"name": "randomapp.exe", "pid": 1, "has_window": False, "window_title": ""},
        ]
        platforms = extract_platforms_from_process_list(processes)
        assert len(platforms) == 0


class TestAccountExtraction:
    def test_extract_chrome_profiles(self) -> None:
        profiles = [
            {"name": "Work", "email": "work@company.com", "is_default": True},
            {"name": "Personal", "email": "me@gmail.com", "is_default": False},
        ]
        accounts = extract_accounts_from_chrome_profiles(profiles)
        assert len(accounts) == 2
        assert accounts[0].is_primary is True

    def test_dedup_chrome_profiles(self) -> None:
        profiles = [
            {"name": "Work", "email": "same@email.com", "is_default": True},
            {"name": "Also Work", "email": "same@email.com", "is_default": False},
        ]
        accounts = extract_accounts_from_chrome_profiles(profiles)
        assert len(accounts) == 1

    def test_extract_browser_sessions(self) -> None:
        sessions = [
            {"platform": "gmail", "email": "me@gmail.com", "username": "", "window_title": ""},
            {"platform": "github", "email": "", "username": "testuser", "window_title": ""},
        ]
        accounts = extract_accounts_from_browser_sessions(sessions)
        assert len(accounts) == 1  # only one has email


class TestProofPersistence:
    def test_persist_creates_file(self, tmp_path: Path) -> None:
        e = _full_evidence()
        proof = classify_environment_mapping(e)
        path = persist_environment_mapping_proof(proof, base_dir=tmp_path)
        assert path.exists()

    def test_persist_valid_json(self, tmp_path: Path) -> None:
        e = _full_evidence()
        proof = classify_environment_mapping(e)
        path = persist_environment_mapping_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert data["proof_type"] == "environment_mapping"

    def test_persist_includes_evidence(self, tmp_path: Path) -> None:
        e = _full_evidence()
        proof = classify_environment_mapping(e)
        path = persist_environment_mapping_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert data["evidence"]["process_list_captured"] is True

    def test_persist_includes_topology(self, tmp_path: Path) -> None:
        relay = _full_relay_result()
        proof = build_full_environment_proof(relay, founder_confirmed=True)
        path = persist_environment_mapping_proof(proof, base_dir=tmp_path)
        data = json.loads(path.read_text())
        assert data["topology"]["platform_count"] > 0


class TestProofSerialization:
    def test_proof_id_auto_generated(self) -> None:
        proof = EnvironmentMappingProof(trace_id="test")
        assert proof.proof_id.startswith("ENVMAP-")

    def test_to_dict_serializable(self) -> None:
        e = _full_evidence()
        proof = classify_environment_mapping(e)
        d = proof.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0


class TestFullPipeline:
    def test_full_pipeline_success(self) -> None:
        relay = _full_relay_result()
        proof = build_full_environment_proof(relay, founder_confirmed=True)
        assert proof.maturity_level == "L3_ENVIRONMENT_INTELLIGENCE"
        assert proof.escalation_blocked is False
        assert proof.topology is not None
        assert proof.topology.platform_count > 0
        assert proof.topology.account_count > 0
        assert proof.topology.relationship_count > 0
        assert proof.topology.lane_count > 0

    def test_full_pipeline_dry_run(self) -> None:
        relay = _full_relay_result(dry_run=True)
        relay["discovery_result"] = {}
        relay["observed_desktop_state"] = {}
        proof = build_full_environment_proof(relay)
        assert proof.maturity_level == "L0_NO_MAPPING"
        assert proof.escalation_blocked is True

    def test_full_pipeline_no_founder(self) -> None:
        relay = _full_relay_result()
        proof = build_full_environment_proof(relay, founder_confirmed=False)
        assert proof.escalation_blocked is True
        assert "founder" in proof.escalation_reason

    def test_canonical_instance_separation(self) -> None:
        relay = _full_relay_result()
        proof = build_full_environment_proof(relay, founder_confirmed=True)
        topo = proof.topology
        assert topo is not None
        total = len(topo.canonical_candidates) + len(topo.instance_candidates)
        assert total == topo.platform_count


class TestDiscoveryDomains:
    def test_all_domains_defined(self) -> None:
        assert len(DISCOVERY_DOMAINS) == 20
        assert "chrome_profiles" in DISCOVERY_DOMAINS
        assert "notion" in DISCOVERY_DOMAINS
        assert "discord" in DISCOVERY_DOMAINS
        assert "github" in DISCOVERY_DOMAINS
        assert "obsidian" in DISCOVERY_DOMAINS
        assert "docker_containers" in DISCOVERY_DOMAINS
        assert "installed_desktop_apps" in DISCOVERY_DOMAINS


class TestTransportIntegration:
    def test_relay_transport_with_mapping(self) -> None:
        from core.workstation.relay_execution_transport_v1 import RelayTransportResult

        transport = RelayTransportResult(
            status="completed",
            request_id="REQ-W0-EXPLORE-ENV-e2e001",
            relay_result=_full_relay_result(),
            ssh_reachable=True,
            inbox_written=True,
            result_received=True,
            elapsed_seconds=8.5,
        )
        proof = build_full_environment_proof(transport.relay_result, founder_confirmed=True)
        assert proof.maturity_level == "L3_ENVIRONMENT_INTELLIGENCE"
        assert proof.topology is not None
        assert proof.topology.platform_count > 0


class TestRegistryIntegration:
    def test_explore_environment_in_registry(self) -> None:
        from core.registry.canonical_command_registry_v1 import get_canonical_registry

        registry = get_canonical_registry()
        assert registry.contains("!explore-environment")
        entry = registry.get("!explore-environment")
        assert entry is not None
        assert entry.canonical_action == "explore_environment"
        assert entry.foreground_required is True

    def test_explore_environment_in_allowed_actions(self) -> None:
        from core.control_plane_router.router_contracts import ALLOWED_ACTION_TYPES

        assert "explore_environment" in ALLOWED_ACTION_TYPES

    def test_explore_environment_in_capability_map(self) -> None:
        from core.control_plane_router.control_plane_router_v1 import (
            ACTION_CAPABILITY_MAP,
        )

        assert "explore_environment" in ACTION_CAPABILITY_MAP
        cap = ACTION_CAPABILITY_MAP["explore_environment"]
        assert cap.requires_gui is True
