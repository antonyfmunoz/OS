"""Phase 87A Distributed Node Registry + Runtime Routing — comprehensive test suite.

Tests (118+):
  - Contracts: all 8 enums, 8 normalizers, 5 dataclasses, to_dict/from_dict round-trips
  - Registry: 8 default node profiles, classify_node, active/future filters
  - Capabilities: 15 default capabilities, source-to-capability mapping, classify_capability
  - Routing: route_task_advisory, affinity enforcement, capability matching, fallback
  - Artifacts: 8 default sync policies, credential safety, classify_artifact
  - Views: 6 view types, converters, dashboard builder
  - Safety: AST module checks, recommendation safety
  - Integration: Phase 86/87 import compat, additive-only verification
  - Layering: forbidden import checks per file
  - Regression: Phase 80-87A import smoke tests
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import ast
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════════
# 1. Contract Enums + Normalizers
# ═══════════════════════════════════════════════════════════════════════

from umh.distributed.contracts import (
    ArtifactSyncDirection,
    ArtifactSyncPolicy,
    ArtifactType,
    CapabilityDomain,
    NodeAvailability,
    NodeCapability,
    NodeRole,
    RoutingDecision,
    RoutingPolicy,
    RoutingPriority,
    RuntimeNodeProfile,
    RuntimeNodeType,
    SourceAffinity,
    _dist_id,
    clamp_score,
    normalize_artifact_type,
    normalize_availability,
    normalize_capability_domain,
    normalize_node_role,
    normalize_node_type,
    normalize_routing_priority,
    normalize_source_affinity,
    normalize_sync_direction,
)


class TestContractEnums:
    def test_runtime_node_type_has_unknown(self):
        assert RuntimeNodeType.UNKNOWN.value == "unknown"

    def test_runtime_node_type_count(self):
        assert len(RuntimeNodeType) == 9

    def test_node_role_has_unknown(self):
        assert NodeRole.UNKNOWN.value == "unknown"

    def test_node_role_count(self):
        assert len(NodeRole) == 9

    def test_node_availability_has_unknown(self):
        assert NodeAvailability.UNKNOWN.value == "unknown"

    def test_node_availability_count(self):
        assert len(NodeAvailability) == 6

    def test_capability_domain_has_unknown(self):
        assert CapabilityDomain.UNKNOWN.value == "unknown"

    def test_capability_domain_count(self):
        assert len(CapabilityDomain) == 16

    def test_source_affinity_has_unknown(self):
        assert SourceAffinity.UNKNOWN.value == "unknown"

    def test_source_affinity_count(self):
        assert len(SourceAffinity) == 8

    def test_routing_priority_has_unknown(self):
        assert RoutingPriority.UNKNOWN.value == "unknown"

    def test_artifact_sync_direction_has_unknown(self):
        assert ArtifactSyncDirection.UNKNOWN.value == "unknown"

    def test_artifact_type_has_unknown(self):
        assert ArtifactType.UNKNOWN.value == "unknown"

    def test_artifact_type_count(self):
        assert len(ArtifactType) == 9


class TestContractNormalizers:
    def test_normalize_node_type_from_string(self):
        assert normalize_node_type("vps") == RuntimeNodeType.VPS

    def test_normalize_node_type_from_enum(self):
        assert normalize_node_type(RuntimeNodeType.LOCAL_PC) == RuntimeNodeType.LOCAL_PC

    def test_normalize_node_type_unknown_fallback(self):
        assert normalize_node_type("nonexistent") == RuntimeNodeType.UNKNOWN

    def test_normalize_node_role_from_string(self):
        assert normalize_node_role("primary_compute") == NodeRole.PRIMARY_COMPUTE

    def test_normalize_availability_from_string(self):
        assert normalize_availability("always_on") == NodeAvailability.ALWAYS_ON

    def test_normalize_capability_domain(self):
        assert normalize_capability_domain("gpu") == CapabilityDomain.GPU

    def test_normalize_source_affinity(self):
        assert normalize_source_affinity("local_only") == SourceAffinity.LOCAL_ONLY

    def test_normalize_routing_priority(self):
        assert normalize_routing_priority("latency") == RoutingPriority.LATENCY

    def test_normalize_sync_direction(self):
        assert normalize_sync_direction("bidirectional") == ArtifactSyncDirection.BIDIRECTIONAL

    def test_normalize_artifact_type(self):
        assert normalize_artifact_type("code") == ArtifactType.CODE

    def test_all_normalizers_degrade_to_unknown(self):
        assert normalize_node_type("x") == RuntimeNodeType.UNKNOWN
        assert normalize_node_role("x") == NodeRole.UNKNOWN
        assert normalize_availability("x") == NodeAvailability.UNKNOWN
        assert normalize_capability_domain("x") == CapabilityDomain.UNKNOWN
        assert normalize_source_affinity("x") == SourceAffinity.UNKNOWN
        assert normalize_routing_priority("x") == RoutingPriority.UNKNOWN
        assert normalize_sync_direction("x") == ArtifactSyncDirection.UNKNOWN
        assert normalize_artifact_type("x") == ArtifactType.UNKNOWN


class TestContractHelpers:
    def test_dist_id_format(self):
        id_ = _dist_id("test")
        assert id_.startswith("test_")
        assert len(id_) == 5 + 12

    def test_dist_id_unique(self):
        ids = {_dist_id("x") for _ in range(100)}
        assert len(ids) == 100

    def test_clamp_score_in_range(self):
        assert clamp_score(0.5) == 0.5

    def test_clamp_score_below(self):
        assert clamp_score(-1.0) == 0.0

    def test_clamp_score_above(self):
        assert clamp_score(2.0) == 1.0


class TestContractSerialization:
    def test_runtime_node_profile_round_trip(self):
        p = RuntimeNodeProfile(
            node_id="n1",
            name="Test",
            node_type=RuntimeNodeType.VPS,
            roles=[NodeRole.PRIMARY_COMPUTE],
            availability=NodeAvailability.ALWAYS_ON,
            capabilities=[CapabilityDomain.COMPUTE],
            cpu_cores=4.0,
            memory_gb=8.0,
        )
        d = p.to_dict()
        p2 = RuntimeNodeProfile.from_dict(d)
        assert p2.node_id == "n1"
        assert p2.node_type == RuntimeNodeType.VPS
        assert p2.roles == [NodeRole.PRIMARY_COMPUTE]
        assert p2.capabilities == [CapabilityDomain.COMPUTE]

    def test_node_capability_round_trip(self):
        c = NodeCapability(
            capability_id="c1",
            domain=CapabilityDomain.GPU,
            name="GPU Compute",
            source_affinity=SourceAffinity.GPU_REQUIRED,
        )
        d = c.to_dict()
        c2 = NodeCapability.from_dict(d)
        assert c2.domain == CapabilityDomain.GPU
        assert c2.source_affinity == SourceAffinity.GPU_REQUIRED

    def test_routing_policy_round_trip(self):
        rp = RoutingPolicy(
            policy_id="p1",
            name="Test",
            priority=RoutingPriority.LATENCY,
            requires_gpu=True,
        )
        d = rp.to_dict()
        rp2 = RoutingPolicy.from_dict(d)
        assert rp2.priority == RoutingPriority.LATENCY
        assert rp2.requires_gpu is True

    def test_artifact_sync_policy_round_trip(self):
        sp = ArtifactSyncPolicy(
            policy_id="s1",
            name="Code",
            artifact_type=ArtifactType.CODE,
            direction=ArtifactSyncDirection.BIDIRECTIONAL,
        )
        d = sp.to_dict()
        sp2 = ArtifactSyncPolicy.from_dict(d)
        assert sp2.artifact_type == ArtifactType.CODE
        assert sp2.direction == ArtifactSyncDirection.BIDIRECTIONAL

    def test_routing_decision_to_dict(self):
        rd = RoutingDecision(
            decision_id="d1",
            task_description="test",
            selected_node_type=RuntimeNodeType.VPS,
            confidence=0.85,
        )
        d = rd.to_dict()
        assert d["confidence"] == 0.85
        assert d["selected_node_type"] == "vps"


# ═══════════════════════════════════════════════════════════════════════
# 2. Registry
# ═══════════════════════════════════════════════════════════════════════

from umh.distributed.registry import (
    build_default_node_profiles,
    classify_node,
    create_node_profile,
    get_active_nodes,
    get_future_nodes,
    node_profile_from_dict,
    node_profile_to_dict,
)


class TestRegistry:
    def test_default_node_count(self):
        nodes = build_default_node_profiles()
        assert len(nodes) == 8

    def test_default_vps_exists(self):
        nodes = build_default_node_profiles()
        vps = [n for n in nodes if n.node_type == RuntimeNodeType.VPS]
        assert len(vps) >= 1
        assert vps[0].name == "Primary VPS"

    def test_default_local_pc_exists(self):
        nodes = build_default_node_profiles()
        local = [n for n in nodes if n.node_type == RuntimeNodeType.LOCAL_PC]
        assert len(local) >= 1
        assert local[0].name == "Local PC (Windows)"

    def test_vps_is_always_on(self):
        nodes = build_default_node_profiles()
        vps = [n for n in nodes if n.node_type == RuntimeNodeType.VPS][0]
        assert vps.availability == NodeAvailability.ALWAYS_ON

    def test_local_pc_has_browser_and_accounts(self):
        nodes = build_default_node_profiles()
        local = [n for n in nodes if n.node_type == RuntimeNodeType.LOCAL_PC][0]
        assert CapabilityDomain.BROWSER in local.capabilities
        assert CapabilityDomain.LOCAL_ACCOUNTS in local.capabilities

    def test_local_pc_has_gpu(self):
        nodes = build_default_node_profiles()
        local = [n for n in nodes if n.node_type == RuntimeNodeType.LOCAL_PC][0]
        assert local.gpu is True

    def test_vps_has_docker(self):
        nodes = build_default_node_profiles()
        vps = [n for n in nodes if n.node_type == RuntimeNodeType.VPS][0]
        assert CapabilityDomain.DOCKER in vps.capabilities

    def test_mobile_exists(self):
        nodes = build_default_node_profiles()
        mobile = [n for n in nodes if n.node_type == RuntimeNodeType.MOBILE]
        assert len(mobile) >= 1

    def test_tablet_exists(self):
        nodes = build_default_node_profiles()
        tablet = [n for n in nodes if n.node_type == RuntimeNodeType.TABLET]
        assert len(tablet) >= 1

    def test_future_nodes_exist(self):
        nodes = build_default_node_profiles()
        future = [n for n in nodes if n.availability == NodeAvailability.FUTURE]
        assert len(future) >= 3

    def test_active_nodes_filter(self):
        active = get_active_nodes()
        for n in active:
            assert n.availability != NodeAvailability.FUTURE
            assert n.availability != NodeAvailability.UNKNOWN

    def test_future_nodes_filter(self):
        future = get_future_nodes()
        for n in future:
            assert n.availability == NodeAvailability.FUTURE

    def test_classify_node_vps(self):
        assert classify_node("Hetzner VPS") == RuntimeNodeType.VPS

    def test_classify_node_local(self):
        assert classify_node("My Desktop PC") == RuntimeNodeType.LOCAL_PC

    def test_classify_node_mobile(self):
        assert classify_node("iPhone") == RuntimeNodeType.MOBILE

    def test_classify_node_gpu(self):
        assert classify_node("CUDA GPU server") == RuntimeNodeType.CLOUD_GPU

    def test_classify_node_unknown(self):
        assert classify_node("zzzzz") == RuntimeNodeType.UNKNOWN

    def test_create_node_profile(self):
        p = create_node_profile("Test Node", RuntimeNodeType.VPS)
        assert p.name == "Test Node"
        assert p.node_type == RuntimeNodeType.VPS
        assert p.node_id.startswith("node_")

    def test_node_profile_round_trip_via_helpers(self):
        p = create_node_profile("RT", "vps")
        d = node_profile_to_dict(p)
        p2 = node_profile_from_dict(d)
        assert p2.name == "RT"
        assert p2.node_type == RuntimeNodeType.VPS

    def test_all_node_ids_unique(self):
        nodes = build_default_node_profiles()
        ids = [n.node_id for n in nodes]
        assert len(ids) == len(set(ids))


# ═══════════════════════════════════════════════════════════════════════
# 3. Capabilities
# ═══════════════════════════════════════════════════════════════════════

from umh.distributed.capabilities import (
    build_default_capabilities,
    classify_capability,
    get_source_affinity,
    get_source_capabilities,
    list_source_names,
    map_sources_to_nodes,
)


class TestCapabilities:
    def test_default_capability_count(self):
        caps = build_default_capabilities()
        assert len(caps) == 15

    def test_gpu_capability_exists(self):
        caps = build_default_capabilities()
        gpu = [c for c in caps if c.domain == CapabilityDomain.GPU]
        assert len(gpu) >= 1

    def test_browser_capability_is_local(self):
        caps = build_default_capabilities()
        browser = [c for c in caps if c.domain == CapabilityDomain.BROWSER][0]
        assert browser.source_affinity == SourceAffinity.LOCAL_ONLY

    def test_local_accounts_is_local_only(self):
        caps = build_default_capabilities()
        la = [c for c in caps if c.domain == CapabilityDomain.LOCAL_ACCOUNTS][0]
        assert la.source_affinity == SourceAffinity.LOCAL_ONLY

    def test_source_instagram_needs_browser(self):
        caps = get_source_capabilities("instagram")
        assert CapabilityDomain.BROWSER in caps
        assert CapabilityDomain.LOCAL_ACCOUNTS in caps

    def test_source_instagram_is_local_only(self):
        assert get_source_affinity("instagram") == SourceAffinity.LOCAL_ONLY

    def test_source_youtube_is_any_node(self):
        assert get_source_affinity("youtube") == SourceAffinity.ANY_NODE

    def test_source_discord_is_vps_preferred(self):
        assert get_source_affinity("discord") == SourceAffinity.VPS_PREFERRED

    def test_source_docker_logs_is_vps_only(self):
        assert get_source_affinity("docker_logs") == SourceAffinity.VPS_ONLY

    def test_source_model_training_is_gpu_required(self):
        assert get_source_affinity("model_training") == SourceAffinity.GPU_REQUIRED

    def test_unknown_source_returns_empty(self):
        assert get_source_capabilities("nonexistent") == []

    def test_unknown_source_affinity_is_unknown(self):
        assert get_source_affinity("nonexistent") == SourceAffinity.UNKNOWN

    def test_list_source_names(self):
        names = list_source_names()
        assert "instagram" in names
        assert "github" in names
        assert len(names) >= 20

    def test_classify_capability_gpu(self):
        assert classify_capability("CUDA tensor processing") == CapabilityDomain.GPU

    def test_classify_capability_browser(self):
        assert classify_capability("Chrome browser") == CapabilityDomain.BROWSER

    def test_classify_capability_unknown(self):
        assert classify_capability("zzzzz") == CapabilityDomain.UNKNOWN

    def test_map_sources_to_nodes_instagram(self):
        mapping = map_sources_to_nodes(["instagram"])
        assert "Local PC (Windows)" in mapping.get("instagram", [])

    def test_map_sources_to_nodes_docker_logs(self):
        mapping = map_sources_to_nodes(["docker_logs"])
        assert "Primary VPS" in mapping.get("docker_logs", [])

    def test_map_sources_to_nodes_youtube(self):
        mapping = map_sources_to_nodes(["youtube"])
        nodes = mapping.get("youtube", [])
        assert len(nodes) >= 1

    def test_map_sources_excludes_vps_for_local_only(self):
        mapping = map_sources_to_nodes(["instagram"])
        nodes = mapping.get("instagram", [])
        assert "Primary VPS" not in nodes


# ═══════════════════════════════════════════════════════════════════════
# 4. Routing
# ═══════════════════════════════════════════════════════════════════════

from umh.distributed.routing import (
    build_default_routing_policies,
    route_task_advisory,
)


class TestRouting:
    def _get_nodes(self):
        return get_active_nodes()

    def test_route_empty_nodes_returns_no_node(self):
        r = route_task_advisory("test", [])
        assert r.selected_node_id == ""
        assert "no nodes" in r.reason

    def test_route_instagram_to_local_pc(self):
        r = route_task_advisory("scrape instagram", self._get_nodes(), source_name="instagram")
        assert r.selected_node_type == RuntimeNodeType.LOCAL_PC

    def test_route_docker_service_to_vps(self):
        r = route_task_advisory("restart docker service", self._get_nodes())
        assert r.selected_node_type == RuntimeNodeType.VPS

    def test_route_api_call_to_vps(self):
        r = route_task_advisory("call Stripe API", self._get_nodes(), source_name="stripe")
        assert r.selected_node_type in (RuntimeNodeType.VPS, RuntimeNodeType.LOCAL_PC)

    def test_route_browser_task_to_local(self):
        r = route_task_advisory("open browser and login to account", self._get_nodes())
        assert r.selected_node_type == RuntimeNodeType.LOCAL_PC

    def test_route_gpu_task(self):
        r = route_task_advisory("train ML model", self._get_nodes(), source_name="model_training")
        assert r.selected_node_type == RuntimeNodeType.LOCAL_PC
        assert r.selected_node_id != ""

    def test_route_returns_alternatives(self):
        r = route_task_advisory("general compute task", self._get_nodes())
        assert isinstance(r.alternatives, list)

    def test_route_returns_confidence(self):
        r = route_task_advisory("test", self._get_nodes())
        assert 0.0 <= r.confidence <= 1.0

    def test_route_returns_reason(self):
        r = route_task_advisory("test", self._get_nodes())
        assert r.reason != ""

    def test_route_with_policy(self):
        policies = build_default_routing_policies()
        local_policy = [p for p in policies if "Local Embodiment" in p.name][0]
        r = route_task_advisory("browse social media", self._get_nodes(), policy=local_policy)
        assert r.selected_node_type == RuntimeNodeType.LOCAL_PC

    def test_default_policies_count(self):
        policies = build_default_routing_policies()
        assert len(policies) >= 6

    def test_route_future_only_nodes_warns(self):
        future = get_future_nodes()
        r = route_task_advisory("test", future)
        assert "no available nodes" in r.reason or "no nodes" in r.reason

    def test_route_decision_has_metadata(self):
        r = route_task_advisory("test instagram", self._get_nodes(), source_name="instagram")
        assert "source_name" in r.metadata
        assert r.metadata["source_name"] == "instagram"

    def test_route_docker_logs_to_vps(self):
        r = route_task_advisory("read docker logs", self._get_nodes(), source_name="docker_logs")
        assert r.selected_node_type == RuntimeNodeType.VPS

    def test_route_file_processing(self):
        r = route_task_advisory("read local files", self._get_nodes(), source_name="local_files")
        assert r.selected_node_id != ""

    def test_route_intermittent_node_warning(self):
        nodes = self._get_nodes()
        intermittent = [n for n in nodes if n.availability == NodeAvailability.INTERMITTENT]
        if intermittent:
            r = route_task_advisory(
                "scrape tiktok",
                intermittent,
                source_name="tiktok",
            )
            if r.selected_node_id:
                found_warning = any("intermittent" in w for w in r.warnings)
                assert found_warning or r.selected_node_type != RuntimeNodeType.LOCAL_PC


# ═══════════════════════════════════════════════════════════════════════
# 5. Artifacts
# ═══════════════════════════════════════════════════════════════════════

from umh.distributed.artifacts import (
    build_default_sync_policies,
    classify_artifact,
    get_credential_policy,
    get_sync_policy_for_artifact,
    should_sync,
    sync_policy_from_dict,
    sync_policy_to_dict,
)


class TestArtifacts:
    def test_default_sync_policy_count(self):
        policies = build_default_sync_policies()
        assert len(policies) == 8

    def test_code_sync_is_bidirectional(self):
        p = get_sync_policy_for_artifact("code")
        assert p is not None
        assert p.direction == ArtifactSyncDirection.BIDIRECTIONAL

    def test_credential_no_sync(self):
        p = get_credential_policy()
        assert p is not None
        assert p.direction == ArtifactSyncDirection.NO_SYNC

    def test_cache_no_sync(self):
        p = get_sync_policy_for_artifact("cache")
        assert p is not None
        assert p.direction == ArtifactSyncDirection.NO_SYNC

    def test_should_sync_code(self):
        assert should_sync("code") is True

    def test_should_not_sync_credential(self):
        assert should_sync("credential") is False

    def test_should_not_sync_cache(self):
        assert should_sync("cache") is False

    def test_data_sync_is_local_to_vps(self):
        p = get_sync_policy_for_artifact("data")
        assert p is not None
        assert p.direction == ArtifactSyncDirection.LOCAL_TO_VPS

    def test_media_sync_is_local_to_vps(self):
        p = get_sync_policy_for_artifact("media")
        assert p is not None
        assert p.direction == ArtifactSyncDirection.LOCAL_TO_VPS

    def test_model_sync_is_vps_to_local(self):
        p = get_sync_policy_for_artifact("model")
        assert p is not None
        assert p.direction == ArtifactSyncDirection.VPS_TO_LOCAL

    def test_classify_artifact_credential(self):
        assert classify_artifact(".env file") == ArtifactType.CREDENTIAL

    def test_classify_artifact_code(self):
        assert classify_artifact("python source") == ArtifactType.CODE

    def test_classify_artifact_media(self):
        assert classify_artifact("video thumbnail") == ArtifactType.MEDIA

    def test_classify_artifact_unknown(self):
        assert classify_artifact("zzzzz") == ArtifactType.UNKNOWN

    def test_sync_policy_round_trip(self):
        p = build_default_sync_policies()[0]
        d = sync_policy_to_dict(p)
        p2 = sync_policy_from_dict(d)
        assert p2.name == p.name
        assert p2.artifact_type == p.artifact_type


# ═══════════════════════════════════════════════════════════════════════
# 6. Views
# ═══════════════════════════════════════════════════════════════════════

from umh.distributed.views import (
    build_distributed_dashboard_view,
    capability_to_view,
    node_to_view,
    routing_decision_to_view,
    routing_policy_to_view,
    sync_policy_to_view,
)


class TestViews:
    def test_node_to_view(self):
        nodes = build_default_node_profiles()
        v = node_to_view(nodes[0])
        assert v.name == "Primary VPS"
        assert v.node_type == "vps"

    def test_capability_to_view(self):
        caps = build_default_capabilities()
        v = capability_to_view(caps[0])
        assert v.domain != ""
        assert v.name != ""

    def test_routing_policy_to_view(self):
        policies = build_default_routing_policies()
        v = routing_policy_to_view(policies[0])
        assert v.name != ""
        assert v.policy_id != ""

    def test_sync_policy_to_view(self):
        policies = build_default_sync_policies()
        v = sync_policy_to_view(policies[0])
        assert v.artifact_type != ""
        assert v.direction != ""

    def test_routing_decision_to_view(self):
        r = route_task_advisory("test", get_active_nodes())
        v = routing_decision_to_view(r)
        assert v.decision_id != ""
        assert v.selected_node_type != ""

    def test_dashboard_view(self):
        nodes = build_default_node_profiles()
        caps = build_default_capabilities()
        policies = build_default_routing_policies()
        sync = build_default_sync_policies()
        dv = build_distributed_dashboard_view(nodes, caps, policies, sync)
        assert dv.node_count == 8
        assert dv.active_node_count >= 4
        assert dv.future_node_count >= 3
        assert dv.capability_count == 15
        assert dv.routing_policy_count >= 6
        assert dv.sync_policy_count == 8

    def test_view_to_dict_no_sensitive_data(self):
        nodes = build_default_node_profiles()
        v = node_to_view(nodes[0])
        d = v.to_dict()
        for key in d:
            assert "secret" not in key.lower()
            assert "password" not in key.lower()
            assert "credential" not in key.lower()


# ═══════════════════════════════════════════════════════════════════════
# 7. Safety
# ═══════════════════════════════════════════════════════════════════════

from umh.distributed.safety import (
    check_all_distributed_modules,
    check_module_safety,
    check_recommendation_safety,
)


class TestSafety:
    def test_all_modules_safe(self):
        result = check_all_distributed_modules()
        assert result["all_safe"] is True, f"violations: {result}"

    def test_module_count(self):
        result = check_all_distributed_modules()
        assert result["modules_checked"] >= 6

    def test_individual_contracts_safe(self):
        r = check_module_safety(Path("/opt/OS/umh/distributed/contracts.py"))
        assert r["safe"] is True

    def test_individual_routing_safe(self):
        r = check_module_safety(Path("/opt/OS/umh/distributed/routing.py"))
        assert r["safe"] is True

    def test_detect_forbidden_import_in_fixture(self):
        import tempfile

        code = "import subprocess\nimport requests\n"
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            f.flush()
            r = check_module_safety(f.name)
        assert r["safe"] is False
        assert "subprocess" in r["forbidden_imports"]
        assert "requests" in r["forbidden_imports"]

    def test_detect_execution_pattern_in_fixture(self):
        import tempfile

        code = "def execute(task): pass\ndef send_message(msg): pass\n"
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            f.flush()
            r = check_module_safety(f.name)
        assert r["safe"] is False
        assert "execute" in r["execution_patterns"]
        assert "send_message" in r["execution_patterns"]

    def test_detect_network_listener_in_fixture(self):
        import tempfile

        code = "def listen(): pass\ndef start_server(): pass\n"
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            f.flush()
            r = check_module_safety(f.name)
        assert r["safe"] is False
        assert "listen" in r["network_listener_patterns"]

    def test_detect_secret_pattern_in_fixture(self):
        import tempfile

        code = "import os\nx = os.getenv('SECRET')\n"
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            f.flush()
            r = check_module_safety(f.name)
        assert r["safe"] is False
        assert "os.getenv" in r["secret_patterns"]

    def test_recommendation_safety_ok(self):
        r = route_task_advisory("test", get_active_nodes())
        s = check_recommendation_safety(r)
        assert s["safe"] is True

    def test_recommendation_safety_low_confidence(self):
        rd = RoutingDecision(
            decision_id="d1",
            confidence=0.1,
        )
        s = check_recommendation_safety(rd)
        assert s["safe"] is False
        assert any("low confidence" in w for w in s["warnings"])


# ═══════════════════════════════════════════════════════════════════════
# 8. Layering
# ═══════════════════════════════════════════════════════════════════════


class TestLayering:
    _DISTRIBUTED_DIR = Path("/opt/OS/umh/distributed")
    _FORBIDDEN = {
        "subprocess",
        "requests",
        "httpx",
        "aiohttp",
        "socket",
        "selenium",
        "playwright",
        "smtplib",
        "telegram",
        "discord",
        "paramiko",
    }
    _FORBIDDEN_PREFIXES = (
        "umh.adapters",
        "umh.execution",
        "umh.governance",
        "umh.memory",
        "umh.storage",
    )

    def _check_file(self, filename: str) -> None:
        fp = self._DISTRIBUTED_DIR / filename
        source = fp.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top not in self._FORBIDDEN, f"{filename} imports {alias.name}"
                    for prefix in self._FORBIDDEN_PREFIXES:
                        assert not alias.name.startswith(prefix), f"{filename} imports {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    assert top not in self._FORBIDDEN, f"{filename} imports from {node.module}"
                    for prefix in self._FORBIDDEN_PREFIXES:
                        assert not node.module.startswith(prefix), (
                            f"{filename} imports from {node.module}"
                        )

    def test_contracts_layering(self):
        self._check_file("contracts.py")

    def test_registry_layering(self):
        self._check_file("registry.py")

    def test_capabilities_layering(self):
        self._check_file("capabilities.py")

    def test_routing_layering(self):
        self._check_file("routing.py")

    def test_artifacts_layering(self):
        self._check_file("artifacts.py")

    def test_views_layering(self):
        self._check_file("views.py")

    def test_safety_layering(self):
        self._check_file("safety.py")

    def test_no_model_router_imports(self):
        for py_file in self._DISTRIBUTED_DIR.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            source = py_file.read_text()
            assert "model_router" not in source, f"{py_file.name} imports model_router"

    def test_no_llm_calls(self):
        for py_file in self._DISTRIBUTED_DIR.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            source = py_file.read_text()
            for pattern in ["call_with_fallback", "anthropic", "openai", "google.genai"]:
                assert pattern not in source, f"{py_file.name} contains {pattern}"


# ═══════════════════════════════════════════════════════════════════════
# 9. Integration
# ═══════════════════════════════════════════════════════════════════════


class TestIntegration:
    def test_phase86_imports_still_work(self):
        from umh.tomorrow.views import DailyBriefView, enrich_brief_with_leverage

        brief = DailyBriefView(date="2026-05-03")
        assert brief.date == "2026-05-03"

    def test_phase87_imports_still_work(self):
        from umh.leverage.contracts import LeverageType
        from umh.leverage.recommendations import build_initiate_arena_leverage_recommendations

        recs = build_initiate_arena_leverage_recommendations()
        assert len(recs) == 9
        assert LeverageType.CONTENT_MEDIA is not None

    def test_distributed_does_not_modify_existing_nodes(self):
        from umh.nodes.registry import DeviceNodeRegistry

        reg = DeviceNodeRegistry()
        assert hasattr(reg, "register_node")

    def test_distributed_does_not_modify_workstation(self):
        from umh.workstation.device_registry import DeviceRegistry

        reg = DeviceRegistry()
        assert hasattr(reg, "register_device")

    def test_leverage_enrichment_still_works(self):
        from umh.tomorrow.views import DailyBriefView, enrich_brief_with_leverage

        brief = DailyBriefView(date="2026-05-03")
        enriched = enrich_brief_with_leverage(brief, ["rec1", "rec2"])
        assert "leverage" in enriched.metadata
        assert enriched.metadata["leverage"]["recommendation_count"] == 2


# ═══════════════════════════════════════════════════════════════════════
# 10. Regression
# ═══════════════════════════════════════════════════════════════════════


class TestPhase87ARegression:
    def test_phase80_import(self):
        from umh.registry.contracts import RegistryType

        assert RegistryType is not None

    def test_phase81_import(self):
        from umh.ontology.laws import UniversalLaw

        assert UniversalLaw is not None

    def test_phase82_import(self):
        from umh.storage.contracts import StorageRecordType

        assert StorageRecordType is not None

    def test_phase84_import(self):
        from umh.interface.contracts import InterfaceType

        assert InterfaceType is not None

    def test_phase85_import(self):
        from umh.council.contracts import CouncilStatus

        assert CouncilStatus is not None

    def test_phase85b_import(self):
        from umh.council.archetypes import get_all_thinker_profiles

        profiles = get_all_thinker_profiles()
        assert len(profiles) >= 1

    def test_phase86_import(self):
        from umh.tomorrow.contracts import LoopPhase, TomorrowLoopState

        assert LoopPhase is not None
        assert TomorrowLoopState is not None

    def test_phase87_import(self):
        from umh.leverage.contracts import LeverageAction, LeverageType

        assert LeverageAction is not None
        assert LeverageType is not None

    def test_phase87a_import(self):
        from umh.distributed.contracts import RuntimeNodeType, SourceAffinity
        from umh.distributed.registry import build_default_node_profiles
        from umh.distributed.routing import route_task_advisory

        assert RuntimeNodeType is not None
        assert SourceAffinity is not None
        nodes = build_default_node_profiles()
        assert len(nodes) >= 1
        r = route_task_advisory("test", nodes[:2])
        assert r is not None
