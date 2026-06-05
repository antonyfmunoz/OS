"""Phase 14.8C Wave 3 tests — outcome recording, cadence enforcement,
verification pipeline, projection routing.

Tests are organized by work packet:
  WP-3.1: Outcome recording to reality model
  WP-3.2: Self-improvement cadence enforcement
  WP-3.3: Verification pipeline integration
  WP-3.4: Projection build loop

Phase 14.8C. UMH transport/substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import os
import sys
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


# ── WP-3.1: Outcome Recording ──────────────────────────────────────────────────


class TestOutcomeRecordingHook:
    """WP-3.1: update_packet_status fires outcome recording on terminal states."""

    def _make_engine(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        with tempfile.TemporaryDirectory() as td:
            pkt_path = os.path.join(td, "packets.jsonl")
            wc_path = os.path.join(td, "workcells.jsonl")
            engine = WorkPacketEngine(
                packets_path=pkt_path,
                workcells_path=wc_path,
            )
            yield engine

    def test_record_outcome_fires_on_completed(self):
        """Transitioning to COMPLETED triggers _record_outcome."""
        for engine in self._make_engine():
            pkt = engine.create_packet_from_intent("test outcome recording")
            pid = pkt.packet_id
            from substrate.organism.work_packet import PacketLifecycleStatus as PLS
            for status in [PLS.PLANNED, PLS.READY_FOR_REVIEW, PLS.APPROVAL_PENDING,
                           PLS.APPROVED, PLS.DELEGATED, PLS.EXECUTING, PLS.VALIDATING]:
                assert engine.update_packet_status(pid, status)

            with patch.object(engine, "_record_outcome") as mock_record:
                assert engine.update_packet_status(pid, PLS.COMPLETED, "done")
                mock_record.assert_called_once()
                args = mock_record.call_args[0]
                assert args[1] == PLS.COMPLETED
                assert args[2] == "done"

    def test_record_outcome_fires_on_failed(self):
        """Transitioning to FAILED triggers _record_outcome."""
        for engine in self._make_engine():
            pkt = engine.create_packet_from_intent("test failure recording")
            pid = pkt.packet_id
            from substrate.organism.work_packet import PacketLifecycleStatus as PLS
            for status in [PLS.PLANNED, PLS.READY_FOR_REVIEW, PLS.APPROVAL_PENDING,
                           PLS.APPROVED, PLS.DELEGATED, PLS.EXECUTING]:
                assert engine.update_packet_status(pid, status)

            with patch.object(engine, "_record_outcome") as mock_record:
                assert engine.update_packet_status(pid, PLS.FAILED, "broken")
                mock_record.assert_called_once()
                args = mock_record.call_args[0]
                assert args[1] == PLS.FAILED

    def test_record_outcome_not_fired_on_non_terminal(self):
        """Non-terminal transitions do NOT trigger _record_outcome."""
        for engine in self._make_engine():
            pkt = engine.create_packet_from_intent("test non-terminal")
            pid = pkt.packet_id
            from substrate.organism.work_packet import PacketLifecycleStatus as PLS
            with patch.object(engine, "_record_outcome") as mock_record:
                assert engine.update_packet_status(pid, PLS.PLANNED)
                mock_record.assert_not_called()

    def test_record_outcome_writes_to_instance_model(self):
        """_record_outcome creates an InstanceObservation via record()."""
        for engine in self._make_engine():
            pkt = engine.create_packet_from_intent("write to reality model")
            from substrate.organism.work_packet import PacketLifecycleStatus as PLS

            with tempfile.TemporaryDirectory() as obs_dir:
                obs_path = Path(obs_dir) / "instance.jsonl"
                with patch(
                    "substrate.reality_model.instance.InstanceRealityModel"
                ) as MockModel:
                    mock_instance = MagicMock()
                    mock_instance.record.return_value = "obs-123"
                    MockModel.return_value = mock_instance

                    engine._record_outcome(pkt, PLS.COMPLETED, "test complete")

                    MockModel.assert_called_once_with(user_id="system", org_id="system")
                    mock_instance.record.assert_called_once()
                    obs = mock_instance.record.call_args[0][0]
                    assert "completed" in obs.content.lower()
                    assert pkt.packet_id in obs.content
                    assert "outcome:success" in obs.tags

    def test_record_outcome_failure_tags(self):
        """Failed outcomes get outcome:failure tag."""
        for engine in self._make_engine():
            pkt = engine.create_packet_from_intent("failure tags test")
            from substrate.organism.work_packet import PacketLifecycleStatus as PLS

            with patch(
                "substrate.reality_model.instance.InstanceRealityModel"
            ) as MockModel:
                mock_instance = MagicMock()
                mock_instance.record.return_value = "obs-456"
                MockModel.return_value = mock_instance

                engine._record_outcome(pkt, PLS.FAILED, "broken code")

                obs = mock_instance.record.call_args[0][0]
                assert "outcome:failure" in obs.tags
                assert obs.confidence == 0.6

    def test_record_outcome_sets_packet_fields(self):
        """After recording, pkt.outcome_observation_id and outcome_summary are set."""
        for engine in self._make_engine():
            pkt = engine.create_packet_from_intent("packet field update test")
            from substrate.organism.work_packet import PacketLifecycleStatus as PLS

            with patch(
                "substrate.reality_model.instance.InstanceRealityModel"
            ) as MockModel:
                mock_instance = MagicMock()
                mock_instance.record.return_value = "obs-789"
                MockModel.return_value = mock_instance

                engine._record_outcome(pkt, PLS.COMPLETED, "all good")

                assert pkt.outcome_observation_id == "obs-789"
                assert "all good" in pkt.outcome_summary


class TestOutcomeEndpoints:
    """WP-3.1: execution_complete and execution_fail endpoint contracts."""

    def test_execution_complete_endpoint_registered(self):
        from transports.api.cockpit import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/umh/execution/complete" in paths

    def test_execution_fail_endpoint_registered(self):
        from transports.api.cockpit import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/umh/execution/fail" in paths

    def test_execution_complete_is_post(self):
        from transports.api.cockpit import router
        for r in router.routes:
            if hasattr(r, "path") and r.path == "/api/umh/execution/complete":
                assert "POST" in r.methods
                break

    def test_execution_fail_is_post(self):
        from transports.api.cockpit import router
        for r in router.routes:
            if hasattr(r, "path") and r.path == "/api/umh/execution/fail":
                assert "POST" in r.methods
                break

    def test_execution_complete_has_auth(self):
        from transports.api.cockpit import router
        for r in router.routes:
            if hasattr(r, "path") and r.path == "/api/umh/execution/complete":
                assert r.dependencies, "execution_complete must require auth"
                break


class TestOutcomeVisibilityRoutes:
    """WP-3.1: outcome visibility via universal work routes."""

    def test_outcomes_route_registered(self):
        from transports.api.cockpit_universal_work_routes import universal_work_router
        from transports.api import cockpit_universal_work_routes as mod
        mod.configure(lambda: None)
        r = mod.universal_work_router
        paths = [route.path for route in r.routes if hasattr(route, "path")]
        assert any("outcomes" in p for p in paths)

    def test_verification_route_registered(self):
        from transports.api import cockpit_universal_work_routes as mod
        mod.configure(lambda: None)
        r = mod.universal_work_router
        paths = [route.path for route in r.routes if hasattr(route, "path")]
        assert any("verification" in p for p in paths)


# ── WP-3.2: Self-Improvement Cadence Enforcement ────────────────────────────────


class TestCadenceDryRunEnforcement:
    """WP-3.2: dry_run_only enforcement cannot be bypassed via API."""

    def test_safe_api_modes_defined(self):
        from transports.api.cockpit_autonomous_routes import _SAFE_API_MODES
        assert "off" in _SAFE_API_MODES
        assert "dry_run_only" in _SAFE_API_MODES
        assert "production_verify_only" in _SAFE_API_MODES

    def test_propose_pr_blocked_by_api(self):
        from transports.api.cockpit_autonomous_routes import _SAFE_API_MODES
        assert "propose_pr" not in _SAFE_API_MODES

    def test_create_pr_blocked_by_api(self):
        from transports.api.cockpit_autonomous_routes import _SAFE_API_MODES
        assert "create_pr_with_operator_policy" not in _SAFE_API_MODES

    def test_cadence_mode_enum_exists(self):
        from substrate.organism.autonomous_cadence import CadenceMode
        assert CadenceMode.DRY_RUN_ONLY.value == "dry_run_only"
        assert CadenceMode.OFF.value == "off"

    def test_cadence_policy_defaults_safe(self):
        from substrate.organism.autonomous_cadence import CadencePolicy, CadenceMode
        policy = CadencePolicy()
        assert policy.mode == CadenceMode.OFF
        assert policy.require_operator_enable_for_pr_creation is True
        assert policy.no_auto_merge is True

    def test_cadence_run_cycle_returns_result(self):
        from substrate.organism.autonomous_cadence import AutonomousCadence, CadencePolicy, CadenceMode
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY)
        cadence = AutonomousCadence(policy=policy)
        result = cadence.run_cycle()
        assert result.mode == CadenceMode.DRY_RUN_ONLY
        assert result.completed_at > 0

    def test_cadence_status_returns_policy(self):
        from substrate.organism.autonomous_cadence import AutonomousCadence, CadencePolicy, CadenceMode
        policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY)
        cadence = AutonomousCadence(policy=policy)
        status = cadence.status()
        assert status["mode"] == "dry_run_only"
        assert "policy" in status
        assert status["policy"]["no_auto_merge"] is True

    def test_cadence_set_mode_route_registered(self):
        from transports.api import cockpit_autonomous_routes as mod
        mod.configure(lambda: None, lambda: None)
        r = mod.autonomous_router
        paths = [route.path for route in r.routes if hasattr(route, "path")]
        assert any("set-mode" in p for p in paths)


class TestCadenceDataFlow:
    """WP-3.2: end-to-end cadence data flow."""

    def test_self_build_routes_registered(self):
        from transports.api import cockpit_self_build_routes as mod
        mod.configure(lambda: None, lambda: None)
        r = mod.self_build_router
        paths = [route.path for route in r.routes if hasattr(route, "path")]
        assert any("self-build" in p for p in paths)

    def test_cadence_dry_run_route_registered(self):
        from transports.api import cockpit_autonomous_routes as mod
        mod.configure(lambda: None, lambda: None)
        r = mod.autonomous_router
        paths = [route.path for route in r.routes if hasattr(route, "path")]
        assert any("run-dry-run" in p for p in paths)

    def test_template_registry_route_registered(self):
        from transports.api import cockpit_autonomous_routes as mod
        mod.configure(lambda: None, lambda: None)
        r = mod.autonomous_router
        paths = [route.path for route in r.routes if hasattr(route, "path")]
        assert any("template-registry" in p for p in paths)


# ── WP-3.3: Verification Pipeline ──────────────────────────────────────────────


class TestVerificationPipeline:
    """WP-3.3: gate script execution and result attachment."""

    def test_gate_scripts_list_defined(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        assert len(WorkPacketEngine._GATE_SCRIPTS) == 4
        for script in WorkPacketEngine._GATE_SCRIPTS:
            assert script.startswith("scripts/check_")
            assert script.endswith(".py")

    def test_gate_scripts_exist_on_disk(self):
        repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
        from substrate.organism.work_packet_engine import WorkPacketEngine
        for script_rel in WorkPacketEngine._GATE_SCRIPTS:
            path = os.path.join(repo_root, script_rel)
            assert os.path.isfile(path), f"gate script missing: {path}"

    def test_run_verification_requires_validating_status(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        from substrate.organism.work_packet import PacketLifecycleStatus as PLS
        with tempfile.TemporaryDirectory() as td:
            engine = WorkPacketEngine(
                packets_path=os.path.join(td, "p.jsonl"),
                workcells_path=os.path.join(td, "w.jsonl"),
            )
            pkt = engine.create_packet_from_intent("verify test")
            results = engine.run_verification(pkt.packet_id)
            assert any("validating" in str(r.get("error", "")).lower() for r in results)

    def test_run_verification_returns_per_gate_results(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        from substrate.organism.work_packet import PacketLifecycleStatus as PLS
        with tempfile.TemporaryDirectory() as td:
            engine = WorkPacketEngine(
                packets_path=os.path.join(td, "p.jsonl"),
                workcells_path=os.path.join(td, "w.jsonl"),
            )
            pkt = engine.create_packet_from_intent("verify gate results")
            pid = pkt.packet_id
            for s in [PLS.PLANNED, PLS.READY_FOR_REVIEW, PLS.APPROVAL_PENDING,
                       PLS.APPROVED, PLS.DELEGATED, PLS.EXECUTING, PLS.VALIDATING]:
                assert engine.update_packet_status(pid, s)

            results = engine.run_verification(pid)
            assert len(results) == 4
            gate_names = [r["gate"] for r in results]
            assert "dependency_direction" in gate_names
            assert "type_divergence" in gate_names
            assert "instance_leak" in gate_names
            assert "projection_leak" in gate_names

    def test_verification_results_attached_to_packet(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        from substrate.organism.work_packet import PacketLifecycleStatus as PLS
        with tempfile.TemporaryDirectory() as td:
            engine = WorkPacketEngine(
                packets_path=os.path.join(td, "p.jsonl"),
                workcells_path=os.path.join(td, "w.jsonl"),
            )
            pkt = engine.create_packet_from_intent("verify attach results")
            pid = pkt.packet_id
            for s in [PLS.PLANNED, PLS.READY_FOR_REVIEW, PLS.APPROVAL_PENDING,
                       PLS.APPROVED, PLS.DELEGATED, PLS.EXECUTING, PLS.VALIDATING]:
                assert engine.update_packet_status(pid, s)

            engine.run_verification(pid)
            updated_pkt = engine.get_packet(pid)
            assert updated_pkt.verification_results is not None
            assert len(updated_pkt.verification_results) == 4
            assert updated_pkt.verification_passed is not None

    def test_verification_unknown_packet_returns_error(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        with tempfile.TemporaryDirectory() as td:
            engine = WorkPacketEngine(
                packets_path=os.path.join(td, "p.jsonl"),
                workcells_path=os.path.join(td, "w.jsonl"),
            )
            results = engine.run_verification("wp-nonexistent")
            assert len(results) == 1
            assert "not found" in results[0].get("error", "")


class TestVerificationFields:
    """WP-3.3: verification fields on WorkPacket."""

    def test_verification_results_field_exists(self):
        from substrate.organism.work_packet import WorkPacket
        pkt = WorkPacket()
        assert pkt.verification_results == []
        assert pkt.verification_passed is None

    def test_verification_fields_in_to_dict(self):
        from substrate.organism.work_packet import WorkPacket
        pkt = WorkPacket()
        pkt.verification_results = [{"gate": "test", "passed": True}]
        pkt.verification_passed = True
        d = pkt.to_dict()
        assert "verification_results" in d
        assert "verification_passed" in d
        assert d["verification_passed"] is True

    def test_verification_fields_roundtrip(self):
        from substrate.organism.work_packet import WorkPacket
        pkt = WorkPacket()
        pkt.verification_results = [{"gate": "dep", "passed": True}]
        pkt.verification_passed = True
        d = pkt.to_dict()
        restored = WorkPacket.from_dict(d)
        assert restored.verification_results == [{"gate": "dep", "passed": True}]
        assert restored.verification_passed is True


# ── WP-3.4: Projection Build Loop ──────────────────────────────────────────────


class TestProjectionDetection:
    """WP-3.4: detect_target_projection routes intent to correct projection."""

    def _engine(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        with tempfile.TemporaryDirectory() as td:
            return WorkPacketEngine(
                packets_path=os.path.join(td, "p.jsonl"),
                workcells_path=os.path.join(td, "w.jsonl"),
            )

    def test_detect_eos_signals(self):
        engine = self._engine()
        assert engine.detect_target_projection("build entrepreneur features") == "eos"
        assert engine.detect_target_projection("update eos venture dashboard") == "eos"
        assert engine.detect_target_projection("fix client pipeline bug") == "eos"

    def test_detect_creatoros_signals(self):
        engine = self._engine()
        assert engine.detect_target_projection("add creator dashboard widget") == "creatoros"
        assert engine.detect_target_projection("creatoros content tool") == "creatoros"
        assert engine.detect_target_projection("content creation pipeline") == "creatoros"

    def test_detect_lyfeos_signals(self):
        engine = self._engine()
        assert engine.detect_target_projection("update lyfeos personal system") == "lyfeos"

    def test_detect_no_projection(self):
        engine = self._engine()
        assert engine.detect_target_projection("refactor substrate types") == ""
        assert engine.detect_target_projection("fix a generic bug") == ""

    def test_known_projections_list(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        assert "eos" in WorkPacketEngine._KNOWN_PROJECTIONS
        assert "creatoros" in WorkPacketEngine._KNOWN_PROJECTIONS
        assert "lyfeos" in WorkPacketEngine._KNOWN_PROJECTIONS

    def test_projection_directories_exist(self):
        repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
        from substrate.organism.work_packet_engine import WorkPacketEngine
        for proj in WorkPacketEngine._KNOWN_PROJECTIONS:
            proj_path = os.path.join(repo_root, "projections", proj)
            assert os.path.isdir(proj_path), f"projection dir missing: {proj_path}"


class TestProjectionRouting:
    """WP-3.4: projection-aware packet creation and routing."""

    def test_create_packet_sets_target_projection(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        with tempfile.TemporaryDirectory() as td:
            engine = WorkPacketEngine(
                packets_path=os.path.join(td, "p.jsonl"),
                workcells_path=os.path.join(td, "w.jsonl"),
            )
            pkt = engine.create_packet_from_intent("build entrepreneur onboarding flow")
            assert pkt.target_projection == "eos"

    def test_create_packet_no_projection_for_generic(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        with tempfile.TemporaryDirectory() as td:
            engine = WorkPacketEngine(
                packets_path=os.path.join(td, "p.jsonl"),
                workcells_path=os.path.join(td, "w.jsonl"),
            )
            pkt = engine.create_packet_from_intent("add logging to the system")
            assert pkt.target_projection == ""

    def test_target_projection_in_to_dict(self):
        from substrate.organism.work_packet import WorkPacket
        pkt = WorkPacket()
        pkt.target_projection = "eos"
        d = pkt.to_dict()
        assert d["target_projection"] == "eos"

    def test_target_projection_roundtrip(self):
        from substrate.organism.work_packet import WorkPacket
        pkt = WorkPacket(target_projection="creatoros")
        d = pkt.to_dict()
        restored = WorkPacket.from_dict(d)
        assert restored.target_projection == "creatoros"

    def test_get_projection_root_valid(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        with tempfile.TemporaryDirectory() as td:
            engine = WorkPacketEngine(
                packets_path=os.path.join(td, "p.jsonl"),
                workcells_path=os.path.join(td, "w.jsonl"),
            )
            root = engine.get_projection_root("eos")
            assert root is not None
            assert root.endswith("projections/eos")

    def test_get_projection_root_unknown(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        with tempfile.TemporaryDirectory() as td:
            engine = WorkPacketEngine(
                packets_path=os.path.join(td, "p.jsonl"),
                workcells_path=os.path.join(td, "w.jsonl"),
            )
            assert engine.get_projection_root("unknown_projection") is None

    def test_target_projection_in_safe_dict(self):
        from substrate.organism.work_packet import WorkPacket
        pkt = WorkPacket(target_projection="lyfeos")
        d = pkt.to_safe_dict()
        assert d["target_projection"] == "lyfeos"


class TestProjectionBoundaryCompliance:
    """WP-3.4: projection routing is projection-agnostic in substrate."""

    def test_no_hardcoded_projection_in_engine(self):
        """_KNOWN_PROJECTIONS is a data list, not hardcoded logic."""
        import inspect
        from substrate.organism.work_packet_engine import WorkPacketEngine
        source = inspect.getsource(WorkPacketEngine.detect_target_projection)
        assert "EntrepreneurOS" not in source
        assert "CreatorOS" not in source
        assert "LyfeOS" not in source

    def test_projection_signals_are_content_based(self):
        """Signals are content strings, not import paths or class names."""
        from substrate.organism.work_packet_engine import WorkPacketEngine
        with tempfile.TemporaryDirectory() as td:
            engine = WorkPacketEngine(
                packets_path=os.path.join(td, "p.jsonl"),
                workcells_path=os.path.join(td, "w.jsonl"),
            )
            result = engine.detect_target_projection("import from projections.eos")
            assert result == "eos" or result == ""


# ── Cross-Wave Regression ───────────────────────────────────────────────────────


class TestWave1NoRegression:
    """Wave 1 sealed surfaces are untouched."""

    def test_world_model_panel_not_imported_in_work_routes(self):
        import inspect
        from transports.api import cockpit_universal_work_routes
        source = inspect.getsource(cockpit_universal_work_routes)
        assert "WorldModelPanel" not in source
        assert "worldModelStore" not in source

    def test_reality_model_routes_not_modified(self):
        """cockpit_reality_model_routes still has its own router."""
        from transports.api.cockpit_reality_model_routes import reality_model_router
        assert reality_model_router is not None


class TestWave2NoRegression:
    """Wave 2 sealed endpoints are untouched."""

    def test_intent_classify_still_registered(self):
        from transports.api.cockpit import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/umh/intent/classify" in paths

    def test_execution_start_still_registered(self):
        from transports.api.cockpit import router
        paths = [r.path for r in router.routes if hasattr(r, "path")]
        assert "/api/umh/execution/start" in paths

    def test_generate_route_still_registered(self):
        from transports.api import cockpit_universal_work_routes as mod
        mod.configure(lambda: None)
        r = mod.universal_work_router
        paths = [route.path for route in r.routes if hasattr(route, "path")]
        assert any("generate" in p for p in paths)


class TestWorkPacketFieldIntegrity:
    """New fields don't break existing serialization."""

    def test_new_fields_default_values(self):
        from substrate.organism.work_packet import WorkPacket
        pkt = WorkPacket()
        assert pkt.outcome_observation_id == ""
        assert pkt.outcome_summary == ""
        assert pkt.verification_results == []
        assert pkt.verification_passed is None
        assert pkt.target_projection == ""

    def test_existing_packet_without_new_fields_deserializes(self):
        """Packets serialized before Wave 3 can still be loaded."""
        from substrate.organism.work_packet import WorkPacket
        old_dict = {
            "packet_id": "wp-old123",
            "title": "old packet",
            "user_intent": "do stuff",
            "status": "classified",
        }
        pkt = WorkPacket.from_dict(old_dict)
        assert pkt.packet_id == "wp-old123"
        assert pkt.outcome_observation_id == ""
        assert pkt.verification_results == []
        assert pkt.verification_passed is None
        assert pkt.target_projection == ""
