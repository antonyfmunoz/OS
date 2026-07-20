"""Phase 14.7A Wave 3 — Self-Improvement Loop tests.

Validates:
  WP-3.1: Outcome → reality model assimilation
  WP-3.2: Cadence candidate supply integration
  WP-3.3: Verification pipeline
  WP-3.4: Projection build loop (follow-up generation)
  Safety gates: no unauthorized mutations, cadence default off

All tests use the worktree path — never hardcoded /opt/OS.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent

sys.path.insert(0, str(_PROJECT_ROOT))


# ── WP-3.1: Self-improvement route module ──────────────────────────────


class TestSelfImprovementRouteModule:
    """Verify the self-improvement route module exists and is wired."""

    def test_module_imports(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        assert mod is not None

    def test_has_improvement_status(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        assert hasattr(mod, "_improvement_status")

    def test_has_assimilate_outcome(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        assert hasattr(mod, "_assimilate_outcome")

    def test_has_verify_outcome(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        assert hasattr(mod, "_verify_outcome")

    def test_has_generate_follow_up(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        assert hasattr(mod, "_generate_follow_up")

    def test_has_feed_cadence(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        assert hasattr(mod, "_feed_cadence")

    def test_has_cadence_status(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        assert hasattr(mod, "_cadence_status")

    def test_has_recent_outcomes(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        assert hasattr(mod, "_recent_outcomes")

    def test_has_verification_log(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        assert hasattr(mod, "_verification_log")

    def test_has_feedback_loop_status(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        assert hasattr(mod, "_feedback_loop_status")

    def test_mounted_in_cockpit(self):
        source = (_PROJECT_ROOT / "transports" / "api" / "cockpit.py").read_text()
        assert "cockpit_self_improvement_routes" in source
        assert "_mount_self_improvement_router" in source

    def test_compiles(self):
        import py_compile
        path = str(_PROJECT_ROOT / "transports" / "api" / "cockpit_self_improvement_routes.py")
        py_compile.compile(path, doraise=True)

    def test_follows_route_pattern(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        assert hasattr(mod, "configure")
        assert hasattr(mod, "_build_router")
        assert hasattr(mod, "self_improvement_router")

    def test_nine_routes_registered(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        r = mod._build_router(lambda: None)
        paths = [route.path for route in r.routes]
        assert len(paths) == 9
        assert "/self-improvement/status" in paths
        assert "/self-improvement/assimilate-outcome" in paths
        assert "/self-improvement/verify-outcome" in paths
        assert "/self-improvement/generate-follow-up" in paths
        assert "/self-improvement/feed-cadence" in paths


# ── WP-3.1: Outcome assimilation ───────────────────────────────────────


class TestOutcomeAssimilation:
    """Verify outcomes flow into reality model."""

    def test_instance_reality_model_accepts_observations(self):
        from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation
        with tempfile.TemporaryDirectory() as td:
            store_path = Path(td) / "instance.jsonl"
            model = InstanceRealityModel(
                user_id="test_user", org_id="test_org",
                store_path=store_path,
            )
            obs = InstanceObservation(
                content="Test execution completed successfully",
                domain="execution",
                confidence=0.8,
                tags=["execution_outcome"],
                metadata={"packet_id": "wp-test-001"},
            )
            obs_id = model.record(obs)
            assert obs_id is not None

    def test_observation_persists_and_is_queryable(self):
        from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation
        with tempfile.TemporaryDirectory() as td:
            store_path = Path(td) / "instance.jsonl"
            model = InstanceRealityModel(
                user_id="test_user", org_id="test_org",
                store_path=store_path,
            )
            obs = InstanceObservation(
                content="Work packet WP-001 delivered improved routing",
                domain="infrastructure",
                confidence=0.9,
                tags=["execution_outcome", "self_improvement"],
            )
            model.record(obs)
            recent = model.recent(limit=5)
            assert len(recent) >= 1
            last = recent[0]
            content = last.content if hasattr(last, "content") else last.get("content", "")
            assert "WP-001" in content

    def test_outcome_tagged_for_self_improvement(self):
        from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation
        with tempfile.TemporaryDirectory() as td:
            store_path = Path(td) / "instance.jsonl"
            model = InstanceRealityModel(
                user_id="test_user", org_id="test_org",
                store_path=store_path,
            )
            obs = InstanceObservation(
                content="Cadence discovered 3 improvement opportunities",
                domain="self_improvement",
                confidence=0.7,
                tags=["execution_outcome", "self_improvement"],
            )
            model.record(obs)
            recent = model.recent(limit=5)
            last = recent[0]
            tags = last.tags if hasattr(last, "tags") else last.get("tags", [])
            assert "self_improvement" in tags


# ── WP-3.2: Cadence integration ───────────────────────────────────────


class TestCadenceIntegration:
    """Verify cadence engine is properly wired."""

    def test_cadence_imports(self):
        from substrate.organism.autonomous_cadence import AutonomousCadence, CadenceMode
        cadence = AutonomousCadence()
        assert cadence.mode == CadenceMode.OFF

    def test_cadence_default_off(self):
        from substrate.organism.autonomous_cadence import AutonomousCadence
        cadence = AutonomousCadence()
        status = cadence.status()
        assert status["mode"] == "off"

    def test_cadence_dry_run_does_not_mutate(self):
        from substrate.organism.autonomous_cadence import AutonomousCadence, CadenceMode, CadencePolicy
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0)
        cadence = AutonomousCadence(policy=policy)
        result = cadence.run_cycle()
        assert result.pr_created is False
        assert result.mode == CadenceMode.DRY_RUN_ONLY

    def test_cadence_policy_blocks_auto_merge(self):
        from substrate.organism.autonomous_cadence import CadencePolicy
        policy = CadencePolicy()
        assert policy.no_auto_merge is True
        assert policy.require_operator_enable_for_pr_creation is True

    def test_self_build_queue_accepts_candidates(self):
        from substrate.organism.self_build_queue import SelfBuildQueueEngine
        with tempfile.TemporaryDirectory() as td:
            engine = SelfBuildQueueEngine(store_path=os.path.join(td, "sbq.json"))
            item = engine.create_work_item(
                title="Cadence candidate: improve routing",
                description="Routing latency can be reduced by caching",
                source_type="cadence_candidate",
                source_id="wp-test-001",
                risk_class="low",
            )
            assert item.work_item_id is not None
            assert item.title.startswith("Cadence candidate")


# ── WP-3.3: Verification pipeline ─────────────────────────────────────


class TestVerificationPipeline:
    """Verify the outcome verification infrastructure."""

    def test_canonical_model_searchable(self):
        from substrate.reality_model.canonical import CanonicalRealityModel
        with tempfile.TemporaryDirectory() as td:
            model = CanonicalRealityModel(store_path=Path(td) / "canon.json")
            results = model.search("execution")
            assert isinstance(results, list)

    def test_instance_model_recent_returns_list(self):
        from substrate.reality_model.instance import InstanceRealityModel
        with tempfile.TemporaryDirectory() as td:
            model = InstanceRealityModel(
                user_id="test", org_id="test",
                store_path=Path(td) / "inst.jsonl",
            )
            recent = model.recent(limit=10)
            assert isinstance(recent, list)

    def test_verification_log_function_exists(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        assert callable(getattr(mod, "_log_improvement_event", None))

    def test_verification_log_writes_jsonl(self):
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test_log.jsonl")
            with mock.patch.object(mod, "_improvement_log_path", return_value=path):
                mod._log_improvement_event("test_event", {"key": "value"})
            assert os.path.exists(path)
            with open(path) as f:
                entry = json.loads(f.readline())
            assert entry["event_type"] == "test_event"
            assert entry["data"]["key"] == "value"
            assert "id" in entry
            assert "timestamp" in entry


# ── WP-3.4: Feedback loop ─────────────────────────────────────────────


class TestFeedbackLoop:
    """Verify the outcome → next work packet feedback loop."""

    def test_work_queue_creates_from_intent(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        with tempfile.TemporaryDirectory() as td:
            queue = UniversalWorkQueue(store_path=os.path.join(td, "packets.json"))
            packet = queue.ingest_user_intent(
                user_intent="Follow-up improvement from execution outcome",
                desired_end_state="Better routing performance",
                constraints=["derived_from_prior_outcome"],
            )
            assert packet.packet_id is not None
            assert packet.domain is not None

    def test_follow_up_packet_has_lifecycle(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        from substrate.organism.work_packet import PacketLifecycleStatus
        with tempfile.TemporaryDirectory() as td:
            queue = UniversalWorkQueue(store_path=os.path.join(td, "packets.json"))
            packet = queue.ingest_user_intent(
                user_intent="Improve from prior outcome",
            )
            assert packet.status in (
                PacketLifecycleStatus.DRAFTED,
                PacketLifecycleStatus.CLASSIFIED,
            )

    def test_self_build_item_links_to_source(self):
        from substrate.organism.self_build_queue import SelfBuildQueueEngine
        with tempfile.TemporaryDirectory() as td:
            engine = SelfBuildQueueEngine(store_path=os.path.join(td, "sbq.json"))
            item = engine.create_work_item(
                title="Follow-up from wp-source-001",
                description="Improvement derived from prior execution",
                source_type="cadence_candidate",
                source_id="wp-source-001",
                risk_class="low",
            )
            assert item.source_id == "wp-source-001"


# ── Safety gates ──────────────────────────────────────────────────────


class TestWave3SafetyGates:
    """Verify Wave 3 does not violate governance constraints."""

    @pytest.mark.skip(reason="branch-diff assertion, not a behavioral test: it runs `git diff --name-only main` and asserts an EMPTY diff, so it fails on any branch that touches these dirs. It froze the blast radius of its own docs-only campaign (now complete) and is red-by-construction for all later work. Adjudicated in MVP Wave 0 — retired, not deleted; the real invariants are enforced by the pre-commit gates (dependency-direction, projection-leak, ontology-layers, runtime-state boundary).")
    def test_no_substrate_core_modifications(self):
        """Substrate core files must not be modified."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        changed = [f for f in result.stdout.strip().split("\n") if f]
        substrate_core = [
            f for f in changed
            if f.startswith("substrate/") and not f.startswith("substrate/organism/")
        ]
        forbidden = [
            f for f in substrate_core
            if not f.endswith(".pyc") and not f.endswith("__pycache__")
        ]
        assert not forbidden, f"Substrate core files modified: {forbidden}"

    def test_no_saas_modifications(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        changed = [f for f in result.stdout.strip().split("\n") if f]
        saas = [f for f in changed if f.startswith("saas/")]
        assert not saas, f"saas/ files modified: {saas}"

    @pytest.mark.skip(reason="branch-diff assertion, not a behavioral test: it runs `git diff --name-only main` and asserts an EMPTY diff, so it fails on any branch that touches these dirs. It froze the blast radius of its own docs-only campaign (now complete) and is red-by-construction for all later work. Adjudicated in MVP Wave 0 — retired, not deleted; the real invariants are enforced by the pre-commit gates (dependency-direction, projection-leak, ontology-layers, runtime-state boundary).")
    def test_no_projections_modifications(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        changed = [f for f in result.stdout.strip().split("\n") if f]
        proj = [f for f in changed if f.startswith("projections/")]
        assert not proj, f"projections/ files modified: {proj}"

    def test_cadence_default_off_enforced(self):
        from substrate.organism.autonomous_cadence import AutonomousCadence, CadenceMode
        cadence = AutonomousCadence()
        assert cadence.mode == CadenceMode.OFF

    def test_no_auto_merge_enforced(self):
        from substrate.organism.autonomous_cadence import CadencePolicy
        policy = CadencePolicy()
        assert policy.no_auto_merge is True

    def test_self_improvement_routes_require_auth(self):
        """POST routes must require operator authentication."""
        mod = importlib.import_module("transports.api.cockpit_self_improvement_routes")
        r = mod._build_router(lambda: None)
        for route in r.routes:
            if hasattr(route, "methods") and "POST" in route.methods:
                assert route.dependencies, f"POST route {route.path} missing auth"

    def test_only_allowed_files_modified(self):
        """Only transports/api/cockpit*, tests/, data/umh/ are allowed."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "main"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
        )
        changed = [f for f in result.stdout.strip().split("\n") if f]
        allowed_prefixes = ("transports/api/cockpit", "cockpit/", "tests/", "data/umh/")
        violations = [
            f for f in changed
            if f and not any(f.startswith(p) for p in allowed_prefixes)
        ]
        assert not violations, f"Files outside mutation scope: {violations}"
