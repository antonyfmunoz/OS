"""Tests for Phase 96.8BU — Live Runtime Ingress Integration.

Validates all 8 contracts, 4 enums, ingress router,
Discord adapter, CLI adapter, session manager,
continuity bridge, observability pipeline,
replay validator, boundary policies, and lifecycle engine.

15+ constraint tests proving:
  - Single-spine ingress enforcement
  - Discord normalization determinism
  - CLI normalization determinism
  - Ingress replay determinism
  - Ingress continuity preservation
  - Ingress cognition preservation
  - Ingress workflow preservation
  - Ingress observability preservation
  - Ingress lineage completeness
  - No direct Discord execution
  - No direct CLI execution
  - No ingress orchestration bypass
  - No hidden ingress state mutation
  - Cross-session continuity restoration
  - Multi-interface continuity consistency

UMH substrate subsystem. Phase 96.8BU.
"""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.ingress.live_runtime_ingress_contracts_v1 import (
    IngressEventType,
    IngressPhase,
    IngressSessionState,
    IngressSource,
    RuntimeIngressBoundary,
    RuntimeIngressContext,
    RuntimeIngressIdentity,
    RuntimeIngressLineage,
    RuntimeIngressReceipt,
    RuntimeIngressResponse,
    RuntimeIngressSession,
    RuntimeIngressSignal,
    _content_hash,
)
from core.ingress.live_runtime_ingress_router_v1 import (
    SOURCE_TO_SPINE_SOURCE,
    LiveRuntimeIngressRouter,
)
from core.ingress.discord_runtime_ingress_adapter_v1 import (
    DiscordRuntimeIngressAdapter,
)
from core.ingress.cli_runtime_ingress_adapter_v1 import (
    CLIRuntimeIngressAdapter,
)
from core.ingress.runtime_ingress_session_manager_v1 import (
    RuntimeIngressSessionManager,
    VALID_SESSION_TRANSITIONS,
)
from core.ingress.runtime_ingress_continuity_bridge_v1 import (
    RuntimeIngressContinuityBridge,
)
from core.ingress.runtime_ingress_observability_pipeline_v1 import (
    EVENT_FILE_MAP,
    RuntimeIngressObservabilityPipeline,
)
from core.ingress.runtime_ingress_replay_validator_v1 import (
    RuntimeIngressReplayValidator,
)
from core.ingress.runtime_ingress_boundary_policies_v1 import (
    DEFAULT_INGRESS_BOUNDARIES,
    FORBIDDEN_DIRECT_EXECUTION,
    RuntimeIngressBoundaryEnforcer,
)
from core.ingress.runtime_ingress_lifecycle_engine_v1 import (
    VALID_INGRESS_TRANSITIONS,
    RuntimeIngressLifecycleEngine,
)


# =========================================================================
# Contract Tests
# =========================================================================


class TestIngressContracts:
    """Validates all 8 contracts and 4 enums."""

    def test_enum_ingress_source(self):
        assert len(IngressSource) == 6
        assert IngressSource.DISCORD.value == "discord"
        assert IngressSource.CLI.value == "cli"

    def test_enum_ingress_phase(self):
        assert len(IngressPhase) == 9

    def test_enum_ingress_session_state(self):
        assert len(IngressSessionState) == 7

    def test_enum_ingress_event_type(self):
        assert len(IngressEventType) == 8

    def test_ingress_signal(self):
        sig = RuntimeIngressSignal(
            source=IngressSource.DISCORD, raw_input="!status",
        )
        assert sig.signal_id.startswith("ingsig-")
        assert sig.correlation_id.startswith("ingcorr-")
        d = sig.to_dict()
        assert "content_hash" in d

    def test_ingress_session(self):
        sess = RuntimeIngressSession(operator_id="op-1")
        assert sess.session_id.startswith("ingsess-")
        assert sess.state == IngressSessionState.INITIALIZED

    def test_ingress_context(self):
        ctx = RuntimeIngressContext(session_id="s1", open_loop_count=3)
        assert ctx.context_id.startswith("ingctx-")
        assert ctx.open_loop_count == 3

    def test_ingress_identity(self):
        ident = RuntimeIngressIdentity(
            operator_id="op-1", source=IngressSource.DISCORD,
            authenticated=True,
        )
        assert ident.identity_id.startswith("ingid-")
        assert ident.authenticated

    def test_ingress_receipt(self):
        rcpt = RuntimeIngressReceipt(signal_id="sig-1", approved=True)
        assert rcpt.receipt_id.startswith("ingrcpt-")

    def test_ingress_response(self):
        resp = RuntimeIngressResponse(
            signal_id="sig-1", status="success", command_name="status",
        )
        assert resp.response_id.startswith("ingresp-")

    def test_ingress_boundary(self):
        bnd = RuntimeIngressBoundary(
            check_type="signal_count", passed=True,
        )
        assert bnd.boundary_id.startswith("ingbnd-")

    def test_ingress_lineage(self):
        lin = RuntimeIngressLineage(
            signal_id="sig-1", spine_outcome_id="out-1",
        )
        assert lin.lineage_id.startswith("inglin-")

    def test_all_contracts_serialize_deterministically(self):
        contracts = [
            RuntimeIngressSignal, RuntimeIngressSession,
            RuntimeIngressContext, RuntimeIngressIdentity,
            RuntimeIngressReceipt, RuntimeIngressResponse,
            RuntimeIngressBoundary, RuntimeIngressLineage,
        ]
        for cls in contracts:
            obj = cls()
            d1 = obj.to_dict()
            d2 = obj.to_dict()
            h1 = obj.content_hash()
            h2 = obj.content_hash()
            assert d1 == d2, f"{cls.__name__} non-deterministic to_dict"
            assert h1 == h2, f"{cls.__name__} non-deterministic hash"
            assert isinstance(h1, str) and len(h1) == 24

    def test_content_hash_changes_with_data(self):
        s1 = RuntimeIngressSignal(source=IngressSource.DISCORD, raw_input="a")
        s2 = RuntimeIngressSignal(source=IngressSource.CLI, raw_input="b")
        assert s1.content_hash() != s2.content_hash()


# =========================================================================
# Ingress Router Tests
# =========================================================================


class TestIngressRouter:

    def test_route_without_spine_denied(self, tmp_path):
        router = LiveRuntimeIngressRouter(spine=None, state_dir=tmp_path)
        sig = RuntimeIngressSignal(raw_input="!status")
        resp = router.route(sig)
        assert resp.status == "denied"

    def test_source_to_spine_mapping(self):
        assert SOURCE_TO_SPINE_SOURCE["discord"] == "discord"
        assert SOURCE_TO_SPINE_SOURCE["cli"] == "manual"
        assert SOURCE_TO_SPINE_SOURCE["api"] == "api"

    def test_normalize_command(self, tmp_path):
        router = LiveRuntimeIngressRouter(state_dir=tmp_path)
        assert router._normalize_command("!runtime-status") == "runtime-status"
        assert router._normalize_command("  !STATUS  ") == "status"
        assert router._normalize_command("hello world") == "hello"
        assert router._normalize_command("") == ""

    def test_route_with_mock_spine(self, tmp_path):
        class MockOutcome:
            outcome_id = "out-1"
            succeeded = True
            command_name = "runtime-status"
            result_data = {"status": "ok"}
            error_message = ""
            governance_verdict = "approved"

        class MockSpine:
            def process(self, **kwargs):
                return MockOutcome()

        router = LiveRuntimeIngressRouter(
            spine=MockSpine(), state_dir=tmp_path,
        )
        sig = RuntimeIngressSignal(
            source=IngressSource.DISCORD,
            raw_input="!runtime-status",
            operator_id="op-1",
        )
        resp = router.route(sig)
        assert resp.status == "success"
        assert resp.result_data["status"] == "ok"
        assert resp.receipt_id.startswith("ingrcpt-")

    def test_receipt_persisted(self, tmp_path):
        router = LiveRuntimeIngressRouter(spine=None, state_dir=tmp_path)
        sig = RuntimeIngressSignal(raw_input="!test")
        router.route(sig)
        path = tmp_path / "ingress_receipts.jsonl"
        assert path.exists()

    def test_stats(self, tmp_path):
        router = LiveRuntimeIngressRouter(spine=None, state_dir=tmp_path)
        sig = RuntimeIngressSignal(raw_input="!test")
        router.route(sig)
        stats = router.get_stats()
        assert stats["total_denied"] >= 1


# =========================================================================
# Discord Adapter Tests
# =========================================================================


class TestDiscordAdapter:

    def test_adapt_message(self):
        da = DiscordRuntimeIngressAdapter()
        sig = da.adapt_message(
            "!runtime-status",
            author_id="12345", author_name="Antony",
            channel_id="ch-1", guild_id="g-1",
        )
        assert sig.source == IngressSource.DISCORD
        assert sig.operator_id == "op-discord-12345"
        assert sig.channel_id == "ch-1"
        assert sig.payload["guild_id"] == "g-1"

    def test_adapt_command(self):
        da = DiscordRuntimeIngressAdapter()
        sig = da.adapt_command("runtime-status", author_id="12345")
        assert sig.raw_input == "!runtime-status"

    def test_identity_resolution_cached(self):
        da = DiscordRuntimeIngressAdapter()
        da.adapt_message("a", author_id="12345", author_name="Antony")
        da.adapt_message("b", author_id="12345", author_name="Antony Updated")
        identity = da.get_identity("12345")
        assert identity is not None
        assert identity.display_name == "Antony Updated"
        assert da.get_stats()["known_identities"] == 1

    def test_identity_authenticated(self):
        da = DiscordRuntimeIngressAdapter()
        da.adapt_message("a", author_id="12345")
        identity = da.get_identity("12345")
        assert identity.authenticated is True

    def test_no_execute_method(self):
        da = DiscordRuntimeIngressAdapter()
        assert not hasattr(da, "execute")
        assert not hasattr(da, "execute_workflow")
        assert not hasattr(da, "dispatch")


# =========================================================================
# CLI Adapter Tests
# =========================================================================


class TestCLIAdapter:

    def test_adapt_command(self):
        ca = CLIRuntimeIngressAdapter()
        sig = ca.adapt_command("!runtime-status")
        assert sig.source == IngressSource.CLI
        assert sig.payload["terminal_session"] == ca._terminal_session_id

    def test_command_history(self):
        ca = CLIRuntimeIngressAdapter()
        ca.adapt_command("!a")
        ca.adapt_command("!b")
        ca.adapt_command("!c")
        history = ca.get_command_history()
        assert len(history) == 3

    def test_identity_stable(self):
        ca = CLIRuntimeIngressAdapter()
        ca.adapt_command("!a", operator_name="antony")
        ca.adapt_command("!b")
        identity = ca.get_identity()
        assert identity.operator_id == "op-cli-antony"

    def test_no_execute_method(self):
        ca = CLIRuntimeIngressAdapter()
        assert not hasattr(ca, "execute")
        assert not hasattr(ca, "execute_workflow")


# =========================================================================
# Session Manager Tests
# =========================================================================


class TestSessionManager:

    def test_create_session(self, tmp_path):
        sm = RuntimeIngressSessionManager(state_dir=tmp_path)
        sess = sm.create_session(IngressSource.DISCORD, "op-1")
        assert sess.state == IngressSessionState.INITIALIZED

    def test_valid_transitions(self, tmp_path):
        sm = RuntimeIngressSessionManager(state_dir=tmp_path)
        sess = sm.create_session(IngressSource.DISCORD)
        assert sm.transition(sess.session_id, IngressSessionState.AUTHENTICATED)
        assert sm.transition(sess.session_id, IngressSessionState.ACTIVE)

    def test_invalid_transition(self, tmp_path):
        sm = RuntimeIngressSessionManager(state_dir=tmp_path)
        sess = sm.create_session(IngressSource.DISCORD)
        assert not sm.transition(sess.session_id, IngressSessionState.ACTIVE)

    def test_record_signal(self, tmp_path):
        sm = RuntimeIngressSessionManager(state_dir=tmp_path)
        sess = sm.create_session(IngressSource.DISCORD)
        sm.record_signal(sess.session_id)
        sm.record_signal(sess.session_id)
        assert sm.get_session(sess.session_id).signals_processed == 2

    def test_workflow_binding(self, tmp_path):
        sm = RuntimeIngressSessionManager(state_dir=tmp_path)
        sess = sm.create_session(IngressSource.DISCORD)
        sm.bind_workflow(sess.session_id, "wf-1")
        sm.bind_workflow(sess.session_id, "wf-1")  # dedup
        assert len(sm.get_session(sess.session_id).active_workflow_ids) == 1

    def test_get_or_create(self, tmp_path):
        sm = RuntimeIngressSessionManager(state_dir=tmp_path)
        s1 = sm.get_or_create_session(IngressSource.DISCORD, "op-1")
        s2 = sm.get_or_create_session(IngressSource.DISCORD, "op-1")
        assert s1.session_id == s2.session_id

    def test_sessions_by_source(self, tmp_path):
        sm = RuntimeIngressSessionManager(state_dir=tmp_path)
        sm.create_session(IngressSource.DISCORD)
        sm.create_session(IngressSource.CLI)
        assert len(sm.get_sessions_by_source(IngressSource.DISCORD)) == 1
        assert len(sm.get_sessions_by_source(IngressSource.CLI)) == 1

    def test_event_persistence(self, tmp_path):
        sm = RuntimeIngressSessionManager(state_dir=tmp_path)
        sm.create_session(IngressSource.DISCORD)
        path = tmp_path / "ingress_session_events.jsonl"
        assert path.exists()


# =========================================================================
# Continuity Bridge Tests
# =========================================================================


class TestContinuityBridge:

    def test_capture_context(self, tmp_path):
        cb = RuntimeIngressContinuityBridge(state_dir=tmp_path)
        sig = RuntimeIngressSignal(source=IngressSource.DISCORD)
        ctx = cb.capture_ingress_context(sig, {
            "cognitive_state": {
                "active_focus_id": "f1",
                "open_loop_count": 3,
                "operator_mode": "focused_execution",
            }
        })
        assert ctx.active_focus_id == "f1"
        assert ctx.open_loop_count == 3

    def test_bridge_types(self, tmp_path):
        cb = RuntimeIngressContinuityBridge(state_dir=tmp_path)
        sig = RuntimeIngressSignal(source=IngressSource.DISCORD)
        cb.bridge_to_cognition(sig, "cog-1")
        cb.bridge_to_workflow(sig, "wf-1", "briefing")
        cb.bridge_to_continuity(sig, "cont-1", "checkpointed")
        cb.bridge_to_embodiment(sig, "workstation")
        stats = cb.get_stats()
        assert stats["total_bridges"] == 4
        assert stats["bridge_types"]["cognition"] == 1
        assert stats["bridge_types"]["workflow"] == 1
        assert stats["bridge_types"]["continuity"] == 1
        assert stats["bridge_types"]["embodiment"] == 1

    def test_bridges_for_signal(self, tmp_path):
        cb = RuntimeIngressContinuityBridge(state_dir=tmp_path)
        sig = RuntimeIngressSignal(source=IngressSource.DISCORD)
        cb.bridge_to_cognition(sig, "cog-1")
        cb.bridge_to_workflow(sig, "wf-1")
        bridges = cb.get_bridges_for_signal(sig.signal_id)
        assert len(bridges) == 2

    def test_persistence(self, tmp_path):
        cb = RuntimeIngressContinuityBridge(state_dir=tmp_path)
        sig = RuntimeIngressSignal()
        cb.bridge_to_cognition(sig, "cog-1")
        path = tmp_path / "ingress_continuity_bridges.jsonl"
        assert path.exists()


# =========================================================================
# Observability Pipeline Tests
# =========================================================================


class TestIngressObservability:

    def test_all_8_event_types(self, tmp_path):
        obs = RuntimeIngressObservabilityPipeline(obs_dir=tmp_path)
        obs.record_received("s1", "sig-1")
        obs.record_normalized("s1", "sig-1")
        obs.record_authenticated("s1", "sig-1")
        obs.record_routed("s1", "sig-1")
        obs.record_denied("s1", "sig-2")
        obs.record_completed("s1", "sig-1")
        obs.record_resumed("s1", "sig-3")
        obs.record_expired("s1", "sig-4")
        assert obs.get_stats()["total_events"] == 8
        files = list(tmp_path.iterdir())
        assert len(files) == 8

    def test_event_file_map_complete(self):
        for et in IngressEventType:
            assert et.value in EVENT_FILE_MAP

    def test_read_back(self, tmp_path):
        obs = RuntimeIngressObservabilityPipeline(obs_dir=tmp_path)
        obs.record_received("s1", "sig-1")
        obs.record_received("s1", "sig-2")
        events = obs.get_events_by_type(IngressEventType.INGRESS_RECEIVED)
        assert len(events) == 2

    def test_event_structure(self, tmp_path):
        obs = RuntimeIngressObservabilityPipeline(obs_dir=tmp_path)
        event = obs.record_received("s1", "sig-1", source="discord")
        assert "event_id" in event
        assert event["event_type"] == "ingress_received"


# =========================================================================
# Replay Validator Tests
# =========================================================================


class TestIngressReplayValidator:

    def test_single_trace(self, tmp_path):
        rv = RuntimeIngressReplayValidator(proof_dir=tmp_path)
        trace = {
            "raw_input": "!runtime-status",
            "source": "discord",
            "user_id": "12345",
            "session_id": "sess-1",
        }
        proof = rv.validate_trace(trace)
        assert proof["all_passed"]
        assert proof["check_count"] == 5

    def test_proof_persisted(self, tmp_path):
        rv = RuntimeIngressReplayValidator(proof_dir=tmp_path)
        rv.validate_trace({"raw_input": "!test"})
        proofs = list(tmp_path.glob("ingress_replay_proof_*.json"))
        assert len(proofs) == 1

    def test_session_validation(self, tmp_path):
        rv = RuntimeIngressReplayValidator(proof_dir=tmp_path)
        traces = [
            {"raw_input": "!a", "source": "discord"},
            {"raw_input": "!b", "source": "cli"},
        ]
        result = rv.validate_session(traces)
        assert result["all_passed"]
        assert result["trace_count"] == 2

    def test_all_five_checks(self, tmp_path):
        rv = RuntimeIngressReplayValidator(proof_dir=tmp_path)
        proof = rv.validate_trace({"raw_input": "!test", "source": "discord"})
        check_names = {c["check"] for c in proof["checks"]}
        expected = {
            "normalization", "routing", "identity_binding",
            "continuity_binding", "cognition_linkage",
        }
        assert check_names == expected


# =========================================================================
# Boundary Policies Tests
# =========================================================================


class TestIngressBoundaryPolicies:

    def test_default_limits(self):
        for source in ["discord", "cli", "api"]:
            assert source in DEFAULT_INGRESS_BOUNDARIES

    def test_passing_check(self):
        be = RuntimeIngressBoundaryEnforcer(source=IngressSource.DISCORD)
        r = be.check_signal_count(10)
        assert r["passed"]

    def test_failing_check(self):
        be = RuntimeIngressBoundaryEnforcer(source=IngressSource.DISCORD)
        r = be.check_signal_count(1000)
        assert not r["passed"]

    def test_override_capping(self):
        be = RuntimeIngressBoundaryEnforcer(
            source=IngressSource.DISCORD,
            overrides={"max_signals_per_session": 10000},
        )
        assert be.limits["max_signals_per_session"] == 500

    def test_forbidden_direct_execution(self):
        be = RuntimeIngressBoundaryEnforcer()
        for action in FORBIDDEN_DIRECT_EXECUTION:
            r = be.check_no_direct_execution(action)
            assert not r["passed"]

    def test_normalization_required(self):
        be = RuntimeIngressBoundaryEnforcer()
        sig_ok = RuntimeIngressSignal(raw_input="!test")
        assert be.check_normalization_required(sig_ok)["passed"]
        sig_empty = RuntimeIngressSignal()
        assert not be.check_normalization_required(sig_empty)["passed"]

    def test_identity_anchored(self):
        be = RuntimeIngressBoundaryEnforcer()
        sig_ok = RuntimeIngressSignal(operator_id="op-1")
        assert be.check_identity_anchored(sig_ok)["passed"]
        sig_no = RuntimeIngressSignal()
        assert not be.check_identity_anchored(sig_no)["passed"]

    def test_bulk_check(self):
        be = RuntimeIngressBoundaryEnforcer(source=IngressSource.DISCORD)
        r = be.check_all(signal_count=10, active_sessions=1, command="!test")
        assert r["all_passed"]

    def test_cli_has_different_limits(self):
        be_d = RuntimeIngressBoundaryEnforcer(source=IngressSource.DISCORD)
        be_c = RuntimeIngressBoundaryEnforcer(source=IngressSource.CLI)
        assert be_c.limits["max_signals_per_session"] > be_d.limits["max_signals_per_session"]


# =========================================================================
# Lifecycle Engine Tests
# =========================================================================


class TestIngressLifecycleEngine:

    def test_register_session(self, tmp_path):
        lce = RuntimeIngressLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1", IngressSource.DISCORD)
        assert lce.get_state("s1") == "initialized"

    def test_full_lifecycle(self, tmp_path):
        lce = RuntimeIngressLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        assert lce.transition("s1", IngressSessionState.AUTHENTICATED)
        assert lce.transition("s1", IngressSessionState.ACTIVE)
        assert lce.transition("s1", IngressSessionState.SUSPENDED)
        assert lce.transition("s1", IngressSessionState.RESUMED)
        assert lce.transition("s1", IngressSessionState.ACTIVE)
        assert lce.transition("s1", IngressSessionState.EXPIRED)
        assert lce.transition("s1", IngressSessionState.TERMINATED)
        assert lce.is_terminal("s1")

    def test_invalid_transition(self, tmp_path):
        lce = RuntimeIngressLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        assert not lce.transition("s1", IngressSessionState.ACTIVE)

    def test_terminal_no_exit(self, tmp_path):
        lce = RuntimeIngressLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        lce.transition("s1", IngressSessionState.TERMINATED)
        assert not lce.transition("s1", IngressSessionState.ACTIVE)

    def test_lineage_persisted(self, tmp_path):
        lce = RuntimeIngressLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        lce.transition("s1", IngressSessionState.AUTHENTICATED)
        path = tmp_path / "ingress_lifecycle_lineage.jsonl"
        assert path.exists()

    def test_active_sessions(self, tmp_path):
        lce = RuntimeIngressLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        lce.register_session("s2")
        lce.transition("s1", IngressSessionState.TERMINATED)
        assert len(lce.get_active_sessions()) == 1

    def test_nonexistent(self, tmp_path):
        lce = RuntimeIngressLifecycleEngine(state_dir=tmp_path)
        assert not lce.transition("nope", IngressSessionState.ACTIVE)
        assert lce.get_state("nope") is None


# =========================================================================
# Critical Constraint Tests
# =========================================================================


class TestSingleSpineEnforcement:
    """All ingress must route through the spine."""

    def test_router_requires_spine(self, tmp_path):
        router = LiveRuntimeIngressRouter(spine=None, state_dir=tmp_path)
        sig = RuntimeIngressSignal(raw_input="!test")
        resp = router.route(sig)
        assert resp.status == "denied"

    def test_discord_adapter_cannot_execute(self):
        da = DiscordRuntimeIngressAdapter()
        assert not hasattr(da, "execute")
        assert not hasattr(da, "execute_workflow")
        assert not hasattr(da, "dispatch")
        assert not hasattr(da, "run_command")
        assert not hasattr(da, "process")

    def test_cli_adapter_cannot_execute(self):
        ca = CLIRuntimeIngressAdapter()
        assert not hasattr(ca, "execute")
        assert not hasattr(ca, "execute_workflow")
        assert not hasattr(ca, "dispatch")
        assert not hasattr(ca, "process")


class TestDiscordNormalizationDeterminism:
    """Same Discord input → same normalized signal."""

    def test_deterministic_signal(self):
        da = DiscordRuntimeIngressAdapter()
        s1 = da.adapt_message("!runtime-status", author_id="123", channel_id="ch-1")
        s2 = da.adapt_message("!runtime-status", author_id="123", channel_id="ch-1")
        assert s1.source == s2.source
        assert s1.raw_input == s2.raw_input
        assert s1.operator_id == s2.operator_id
        assert s1.channel_id == s2.channel_id

    def test_identity_deterministic(self):
        da = DiscordRuntimeIngressAdapter()
        da.adapt_message("a", author_id="123", author_name="A")
        da.adapt_message("b", author_id="123", author_name="A")
        assert da.get_stats()["known_identities"] == 1


class TestCLINormalizationDeterminism:
    """Same CLI input → same normalized signal."""

    def test_deterministic_signal(self):
        ca = CLIRuntimeIngressAdapter(terminal_session_id="fixed-term")
        s1 = ca.adapt_command("!runtime-status", operator_name="antony")
        s2 = ca.adapt_command("!runtime-status", operator_name="antony")
        assert s1.source == s2.source
        assert s1.raw_input == s2.raw_input
        assert s1.operator_id == s2.operator_id


class TestIngressReplayDeterminism:
    """Same ingress → same normalized traversal."""

    def test_all_five_checks_pass(self, tmp_path):
        rv = RuntimeIngressReplayValidator(proof_dir=tmp_path)
        trace = {
            "raw_input": "!runtime-status",
            "source": "discord",
            "user_id": "12345",
            "session_id": "sess-1",
        }
        proof = rv.validate_trace(trace)
        assert proof["all_passed"]
        for check in proof["checks"]:
            assert check["passed"], f"Check {check['check']} failed"

    def test_cli_trace_determinism(self, tmp_path):
        rv = RuntimeIngressReplayValidator(proof_dir=tmp_path)
        trace = {
            "raw_input": "!runtime-status",
            "source": "cli",
            "user_id": "antony",
            "session_id": "sess-cli-1",
        }
        proof = rv.validate_trace(trace)
        assert proof["all_passed"]


class TestIngressContinuityPreservation:
    """Ingress preserves continuity context."""

    def test_context_captures_cognition(self, tmp_path):
        cb = RuntimeIngressContinuityBridge(state_dir=tmp_path)
        sig = RuntimeIngressSignal(source=IngressSource.DISCORD)
        ctx = cb.capture_ingress_context(sig, {
            "cognitive_state": {
                "active_focus_id": "f1",
                "open_loop_count": 5,
                "continuity_chain_length": 3,
            }
        })
        assert ctx.active_focus_id == "f1"
        assert ctx.open_loop_count == 5
        assert ctx.continuity_chain_length == 3


class TestIngressObservabilityPreservation:
    """All 8 event types are recorded."""

    def test_all_event_types_have_files(self):
        assert len(EVENT_FILE_MAP) == 8
        for et in IngressEventType:
            assert et.value in EVENT_FILE_MAP

    def test_all_event_types_recordable(self, tmp_path):
        obs = RuntimeIngressObservabilityPipeline(obs_dir=tmp_path)
        for et in IngressEventType:
            obs.record_event(et, "test-sess", "sig-1")
        assert obs.get_stats()["total_events"] == 8


class TestNoDirectExecution:
    """No adapter or surface can execute directly."""

    def test_forbidden_actions_blocked(self):
        be = RuntimeIngressBoundaryEnforcer()
        for action in FORBIDDEN_DIRECT_EXECUTION:
            assert not be.check_no_direct_execution(action)["passed"]

    def test_safe_actions_allowed(self):
        be = RuntimeIngressBoundaryEnforcer()
        assert be.check_no_direct_execution("spine_route")["passed"]
        assert be.check_no_direct_execution("normalize")["passed"]


class TestNoHiddenIngressMutation:
    """No hidden state mutation in ingress path."""

    def test_receipts_persisted(self, tmp_path):
        router = LiveRuntimeIngressRouter(spine=None, state_dir=tmp_path)
        sig = RuntimeIngressSignal(raw_input="!test")
        router.route(sig)
        path = tmp_path / "ingress_receipts.jsonl"
        assert path.exists()
        with path.open() as f:
            lines = f.readlines()
        assert len(lines) >= 1

    def test_session_events_persisted(self, tmp_path):
        sm = RuntimeIngressSessionManager(state_dir=tmp_path)
        sm.create_session(IngressSource.DISCORD)
        path = tmp_path / "ingress_session_events.jsonl"
        assert path.exists()

    def test_lifecycle_persisted(self, tmp_path):
        lce = RuntimeIngressLifecycleEngine(state_dir=tmp_path)
        lce.register_session("s1")
        lce.transition("s1", IngressSessionState.AUTHENTICATED)
        path = tmp_path / "ingress_lifecycle_lineage.jsonl"
        assert path.exists()


class TestCrossSessionContinuity:
    """Cross-session continuity restoration works."""

    def test_continuity_chain(self, tmp_path):
        sm = RuntimeIngressSessionManager(state_dir=tmp_path)
        s1 = sm.create_session(IngressSource.DISCORD, "op-1")
        sm.add_continuity_chain(s1.session_id, "chain-1")
        sm.add_continuity_chain(s1.session_id, "chain-2")
        assert len(sm.get_session(s1.session_id).continuity_chain_ids) == 2

    def test_operator_sessions_tracked(self, tmp_path):
        sm = RuntimeIngressSessionManager(state_dir=tmp_path)
        sm.create_session(IngressSource.DISCORD, "op-1")
        sm.create_session(IngressSource.CLI, "op-1")
        sessions = sm.get_sessions_by_operator("op-1")
        assert len(sessions) == 2


class TestMultiInterfaceConsistency:
    """Discord and CLI produce consistent normalized signals."""

    def test_same_command_same_normalization(self, tmp_path):
        router = LiveRuntimeIngressRouter(state_dir=tmp_path)
        assert router._normalize_command("!runtime-status") == "runtime-status"
        assert router._normalize_command("!RUNTIME-STATUS") == "runtime-status"
        assert router._normalize_command("!runtime-status args") == "runtime-status"

    def test_different_sources_same_contract(self):
        da = DiscordRuntimeIngressAdapter()
        ca = CLIRuntimeIngressAdapter()
        ds = da.adapt_message("!runtime-status", author_id="123")
        cs = ca.adapt_command("!runtime-status")
        assert type(ds) is type(cs) is RuntimeIngressSignal
        assert ds.raw_input == cs.raw_input


class TestIngressLineageCompleteness:
    """Lineage tracks full ingress→spine path."""

    def test_lineage_record_structure(self):
        lin = RuntimeIngressLineage(
            signal_id="sig-1", spine_outcome_id="out-1",
            cognition_session_id="cog-1", workflow_id="wf-1",
        )
        d = lin.to_dict()
        assert d["signal_id"] == "sig-1"
        assert d["spine_outcome_id"] == "out-1"
        assert d["cognition_session_id"] == "cog-1"
        assert d["workflow_id"] == "wf-1"

    def test_lineage_persisted_on_route(self, tmp_path):
        class MockOutcome:
            outcome_id = "out-1"
            succeeded = True
            command_name = "test"
            result_data = {}
            error_message = ""
            governance_verdict = "approved"

        class MockSpine:
            def process(self, **kw):
                return MockOutcome()

        router = LiveRuntimeIngressRouter(
            spine=MockSpine(), state_dir=tmp_path,
        )
        sig = RuntimeIngressSignal(raw_input="!test", operator_id="op-1")
        router.route(sig)
        path = tmp_path / "ingress_lineage.jsonl"
        assert path.exists()


# =========================================================================
# Integration Tests
# =========================================================================


class TestIntegration:

    def test_full_discord_ingress_flow(self, tmp_path):
        """Discord message → adapter → router → response."""
        class MockOutcome:
            outcome_id = "out-1"
            succeeded = True
            command_name = "runtime-status"
            result_data = {"operational": True}
            error_message = ""
            governance_verdict = "approved"

        class MockSpine:
            def process(self, **kw):
                return MockOutcome()

        da = DiscordRuntimeIngressAdapter()
        router = LiveRuntimeIngressRouter(
            spine=MockSpine(), state_dir=tmp_path / "lineage",
        )
        sm = RuntimeIngressSessionManager(state_dir=tmp_path / "sessions")
        obs = RuntimeIngressObservabilityPipeline(
            obs_dir=tmp_path / "obs",
        )
        lce = RuntimeIngressLifecycleEngine(
            state_dir=tmp_path / "lifecycle",
        )

        sig = da.adapt_message(
            "!runtime-status", author_id="12345",
            author_name="Antony", channel_id="ch-1",
        )

        sess = sm.get_or_create_session(
            IngressSource.DISCORD, sig.operator_id,
        )
        sig.session_id = sess.session_id

        lce.register_session(sess.session_id, IngressSource.DISCORD)
        lce.transition(sess.session_id, IngressSessionState.AUTHENTICATED)
        lce.transition(sess.session_id, IngressSessionState.ACTIVE)

        obs.record_received(
            sess.session_id, sig.signal_id, source="discord",
        )

        resp = router.route(sig)
        assert resp.status == "success"

        sm.record_signal(sess.session_id)
        obs.record_completed(
            sess.session_id, sig.signal_id, outcome_id="out-1",
        )

        assert sm.get_session(sess.session_id).signals_processed == 1
        assert obs.get_stats()["total_events"] == 2

    def test_full_cli_ingress_flow(self, tmp_path):
        """CLI command → adapter → router → response."""
        class MockOutcome:
            outcome_id = "out-2"
            succeeded = True
            command_name = "runtime-context"
            result_data = {"context": "ok"}
            error_message = ""
            governance_verdict = "approved"

        class MockSpine:
            def process(self, **kw):
                return MockOutcome()

        ca = CLIRuntimeIngressAdapter()
        router = LiveRuntimeIngressRouter(
            spine=MockSpine(), state_dir=tmp_path / "lineage",
        )

        sig = ca.adapt_command("!runtime-context")
        resp = router.route(sig)
        assert resp.status == "success"
        assert resp.result_data["context"] == "ok"

    def test_multi_interface_session(self, tmp_path):
        """Same operator across Discord and CLI."""
        sm = RuntimeIngressSessionManager(state_dir=tmp_path)
        s1 = sm.create_session(IngressSource.DISCORD, "op-antony")
        s2 = sm.create_session(IngressSource.CLI, "op-antony")
        sessions = sm.get_sessions_by_operator("op-antony")
        assert len(sessions) == 2
        sources = {s.source for s in sessions}
        assert IngressSource.DISCORD in sources
        assert IngressSource.CLI in sources

    def test_boundary_enforcement_integration(self, tmp_path):
        be = RuntimeIngressBoundaryEnforcer(source=IngressSource.DISCORD)
        da = DiscordRuntimeIngressAdapter()
        sig = da.adapt_message("!test", author_id="123")
        assert be.check_normalization_required(sig)["passed"]
        assert be.check_identity_anchored(sig)["passed"]
        assert be.check_no_direct_execution("spine_route")["passed"]
        assert not be.check_no_direct_execution("discord_workflow_direct")["passed"]

    def test_replay_determinism_both_sources(self, tmp_path):
        rv = RuntimeIngressReplayValidator(proof_dir=tmp_path)
        traces = [
            {"raw_input": "!runtime-status", "source": "discord", "user_id": "123"},
            {"raw_input": "!runtime-status", "source": "cli", "user_id": "antony"},
        ]
        result = rv.validate_session(traces)
        assert result["all_passed"]
        assert result["trace_count"] == 2
