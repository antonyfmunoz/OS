"""Tests for Phase 96.8CD — Substrate Application Projection Coordination.

Covers: contracts, enums, lifecycle, registry, capability projection,
domain contexts, continuity, observability, replay, boundary policies,
topology, bridges, coordinator, constraint verification.
"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Contracts ──────────────────────────────────────────


class TestContracts:
    def test_application_projection_defaults(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationProjection,
        )
        p = ApplicationProjection()
        assert p.projection_id.startswith("aproj-")
        assert p.projection_hash != ""

    def test_application_capability_surface(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationCapabilitySurface,
        )
        s = ApplicationCapabilitySurface(
            application_id="eos", capability_category="workflows",
        )
        d = s.to_dict()
        assert d["application_id"] == "eos"
        assert d["capability_category"] == "workflows"

    def test_application_runtime_context(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationRuntimeContext,
        )
        c = ApplicationRuntimeContext(
            application_id="eos", domain_context="business",
        )
        assert c.context_id.startswith("actx-")
        assert c.context_hash != ""

    def test_application_boundary_state(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationBoundaryState,
        )
        b = ApplicationBoundaryState(application_id="eos")
        d = b.to_dict()
        assert d["boundary_id"].startswith("abnd-")

    def test_application_execution_surface(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationExecutionSurface,
        )
        e = ApplicationExecutionSurface(governed=True)
        assert e.to_dict()["governed"] is True

    def test_application_workflow_surface(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationWorkflowSurface,
        )
        w = ApplicationWorkflowSurface()
        assert w.surface_id.startswith("awfs-")

    def test_application_continuity_state(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationContinuityState,
        )
        c = ApplicationContinuityState(application_id="eos")
        assert c.to_dict()["session_chain"] == []

    def test_application_projection_receipt(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationProjectionReceipt,
        )
        r = ApplicationProjectionReceipt(action="register")
        assert r.receipt_id.startswith("arcpt-")

    def test_application_capability_binding(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationCapabilityBinding,
        )
        b = ApplicationCapabilityBinding(
            application_id="eos", capability_category="workflows",
        )
        assert b.binding_hash != ""

    def test_domain_projection_state(self):
        from core.applications.application_projection_contracts_v1 import (
            DomainProjectionState,
        )
        d = DomainProjectionState(domain_context="business")
        assert d.to_dict()["domain_context"] == "business"

    def test_projection_replay_state(self):
        from core.applications.application_projection_contracts_v1 import (
            ProjectionReplayState,
        )
        r = ProjectionReplayState(check_name="test", deterministic=True)
        assert r.to_dict()["deterministic"] is True

    def test_projection_governance_state(self):
        from core.applications.application_projection_contracts_v1 import (
            ProjectionGovernanceState,
        )
        g = ProjectionGovernanceState(permitted=False, reason="denied")
        assert g.to_dict()["permitted"] is False

    def test_application_lifecycle_state_contract(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationLifecycleStateContract,
        )
        l = ApplicationLifecycleStateContract(application_id="eos")
        assert l.to_dict()["current_state"] == "registered"

    def test_application_topology_state(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationTopologyState,
        )
        t = ApplicationTopologyState(applications=["eos", "lyfeos"])
        assert t.topology_hash != ""

    def test_application_observability_state(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationObservabilityState,
        )
        o = ApplicationObservabilityState(application_id="eos")
        assert o.observability_id.startswith("aobs-")

    def test_all_contracts_have_to_dict(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationProjection, ApplicationCapabilitySurface,
            ApplicationRuntimeContext, ApplicationBoundaryState,
            ApplicationExecutionSurface, ApplicationWorkflowSurface,
            ApplicationContinuityState, ApplicationProjectionReceipt,
            ApplicationCapabilityBinding, DomainProjectionState,
            ProjectionReplayState, ProjectionGovernanceState,
            ApplicationLifecycleStateContract, ApplicationTopologyState,
            ApplicationObservabilityState,
        )
        for cls in [
            ApplicationProjection, ApplicationCapabilitySurface,
            ApplicationRuntimeContext, ApplicationBoundaryState,
            ApplicationExecutionSurface, ApplicationWorkflowSurface,
            ApplicationContinuityState, ApplicationProjectionReceipt,
            ApplicationCapabilityBinding, DomainProjectionState,
            ProjectionReplayState, ProjectionGovernanceState,
            ApplicationLifecycleStateContract, ApplicationTopologyState,
            ApplicationObservabilityState,
        ]:
            d = cls().to_dict()
            assert isinstance(d, dict)


# ── Enums ──────────────────────────────────────────────


class TestEnums:
    def test_lifecycle_states_count(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationLifecycleState,
        )
        assert len(ApplicationLifecycleState) == 6

    def test_event_types_count(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationEventType,
        )
        assert len(ApplicationEventType) == 8

    def test_domain_context_types_count(self):
        from core.applications.application_projection_contracts_v1 import (
            DomainContextType,
        )
        assert len(DomainContextType) == 6

    def test_trust_tiers_count(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationTrustTier,
        )
        assert len(ApplicationTrustTier) == 4

    def test_capability_categories_count(self):
        from core.applications.application_projection_contracts_v1 import (
            CapabilityCategory,
        )
        assert len(CapabilityCategory) == 9

    def test_lifecycle_values(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationLifecycleState,
        )
        values = {s.value for s in ApplicationLifecycleState}
        assert "registered" in values
        assert "projected" in values
        assert "active" in values
        assert "suspended" in values
        assert "restored" in values
        assert "archived" in values

    def test_trust_tier_values(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationTrustTier,
        )
        values = {t.value for t in ApplicationTrustTier}
        assert "core" in values
        assert "governed" in values
        assert "restricted" in values
        assert "sandboxed" in values


# ── Lifecycle Engine ───────────────────────────────────


class TestLifecycleEngine:
    def test_initial_state(self):
        from core.applications.application_lifecycle_engine_v1 import (
            ApplicationLifecycleEngine,
        )
        le = ApplicationLifecycleEngine()
        assert le.current_state == "registered"

    def test_valid_transition(self):
        from core.applications.application_lifecycle_engine_v1 import (
            ApplicationLifecycleEngine,
        )
        le = ApplicationLifecycleEngine()
        result = le.transition("projected")
        assert result["from_state"] == "registered"
        assert result["to_state"] == "projected"

    def test_invalid_transition_raises(self):
        from core.applications.application_lifecycle_engine_v1 import (
            ApplicationLifecycleEngine,
        )
        le = ApplicationLifecycleEngine()
        with pytest.raises(ValueError, match="Invalid transition"):
            le.transition("active")

    def test_full_lifecycle(self):
        from core.applications.application_lifecycle_engine_v1 import (
            ApplicationLifecycleEngine,
        )
        le = ApplicationLifecycleEngine()
        le.transition("projected")
        le.transition("active")
        le.transition("suspended")
        le.transition("restored")
        le.transition("active")
        le.transition("archived")
        assert le.current_state == "archived"

    def test_terminal_state_no_transition(self):
        from core.applications.application_lifecycle_engine_v1 import (
            ApplicationLifecycleEngine,
        )
        le = ApplicationLifecycleEngine()
        le.transition("projected")
        le.transition("archived")
        with pytest.raises(ValueError):
            le.transition("active")

    def test_terminal_states_set(self):
        from core.applications.application_lifecycle_engine_v1 import (
            TERMINAL_STATES,
        )
        assert TERMINAL_STATES == {"archived"}

    def test_transitions_recorded(self):
        from core.applications.application_lifecycle_engine_v1 import (
            ApplicationLifecycleEngine,
        )
        le = ApplicationLifecycleEngine()
        le.transition("projected")
        le.transition("active")
        assert len(le.get_transitions()) == 2

    def test_stats(self):
        from core.applications.application_lifecycle_engine_v1 import (
            ApplicationLifecycleEngine,
        )
        le = ApplicationLifecycleEngine()
        le.transition("projected")
        s = le.get_stats()
        assert s["current_state"] == "projected"
        assert s["total_transitions"] == 1

    def test_valid_transitions_all_states_covered(self):
        from core.applications.application_lifecycle_engine_v1 import (
            VALID_TRANSITIONS,
        )
        from core.applications.application_projection_contracts_v1 import (
            ApplicationLifecycleState,
        )
        for state in ApplicationLifecycleState:
            assert state.value in VALID_TRANSITIONS

    def test_suspend_from_active(self):
        from core.applications.application_lifecycle_engine_v1 import (
            ApplicationLifecycleEngine,
        )
        le = ApplicationLifecycleEngine()
        le.transition("projected")
        le.transition("active")
        le.transition("suspended")
        assert le.current_state == "suspended"


# ── Registry Engine ────────────────────────────────────


class TestRegistryEngine:
    def test_register_known_app(self):
        from core.applications.application_registry_engine_v1 import (
            ApplicationRegistryEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = ApplicationRegistryEngine(state_dir=td)
            app = re.register("eos")
            assert app["name"] == "EntrepreneurOS"
            assert app["trust_tier"] == "core"
            assert app["default_domain"] == "business"

    def test_register_lyfeos(self):
        from core.applications.application_registry_engine_v1 import (
            ApplicationRegistryEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = ApplicationRegistryEngine(state_dir=td)
            app = re.register("lyfeos")
            assert app["name"] == "LyfeOS"
            assert app["trust_tier"] == "governed"

    def test_register_creatoros(self):
        from core.applications.application_registry_engine_v1 import (
            ApplicationRegistryEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = ApplicationRegistryEngine(state_dir=td)
            app = re.register("creatoros")
            assert app["name"] == "CreatorOS"
            assert app["trust_tier"] == "governed"

    def test_register_unknown_app(self):
        from core.applications.application_registry_engine_v1 import (
            ApplicationRegistryEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = ApplicationRegistryEngine(state_dir=td)
            app = re.register("custom_app", name="Custom", trust_tier="sandboxed")
            assert app["name"] == "Custom"
            assert app["trust_tier"] == "sandboxed"

    def test_duplicate_register_returns_existing(self):
        from core.applications.application_registry_engine_v1 import (
            ApplicationRegistryEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = ApplicationRegistryEngine(state_dir=td)
            app1 = re.register("eos")
            app2 = re.register("eos")
            assert app1 is app2

    def test_get_all(self):
        from core.applications.application_registry_engine_v1 import (
            ApplicationRegistryEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = ApplicationRegistryEngine(state_dir=td)
            re.register("eos")
            re.register("lyfeos")
            re.register("creatoros")
            assert len(re.get_all()) == 3

    def test_get_by_trust_tier(self):
        from core.applications.application_registry_engine_v1 import (
            ApplicationRegistryEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = ApplicationRegistryEngine(state_dir=td)
            re.register("eos")
            re.register("lyfeos")
            re.register("creatoros")
            core = re.get_by_trust_tier("core")
            assert len(core) == 1
            governed = re.get_by_trust_tier("governed")
            assert len(governed) == 2

    def test_add_capability(self):
        from core.applications.application_registry_engine_v1 import (
            ApplicationRegistryEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = ApplicationRegistryEngine(state_dir=td)
            re.register("eos")
            assert re.add_capability("eos", "workflows") is True
            app = re.get("eos")
            assert "workflows" in app["capabilities"]

    def test_add_binding(self):
        from core.applications.application_registry_engine_v1 import (
            ApplicationRegistryEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = ApplicationRegistryEngine(state_dir=td)
            re.register("eos")
            assert re.add_binding("eos", "continuity", "cont-1") is True
            app = re.get("eos")
            assert "cont-1" in app["continuity_bindings"]

    def test_known_applications_count(self):
        from core.applications.application_registry_engine_v1 import (
            KNOWN_APPLICATIONS,
        )
        assert len(KNOWN_APPLICATIONS) == 3

    def test_stats(self):
        from core.applications.application_registry_engine_v1 import (
            ApplicationRegistryEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            re = ApplicationRegistryEngine(state_dir=td)
            re.register("eos")
            s = re.get_stats()
            assert s["total_applications"] == 1


# ── Capability Projection Engine ───────────────────────


class TestCapabilityProjectionEngine:
    def test_core_gets_all_capabilities(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine, TRUST_TIER_CAPABILITIES,
        )
        from core.applications.application_projection_contracts_v1 import (
            CapabilityCategory,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = CapabilityProjectionEngine(state_dir=td)
            for cat in CapabilityCategory:
                s = ce.project_capability("eos", cat.value, "core")
                assert s is not None, f"Core should get {cat.value}"

    def test_governed_denied_cognition(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = CapabilityProjectionEngine(state_dir=td)
            s = ce.project_capability("lyfeos", "cognition", "governed")
            assert s is None

    def test_governed_allowed_workflows(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = CapabilityProjectionEngine(state_dir=td)
            s = ce.project_capability("lyfeos", "workflows", "governed")
            assert s is not None

    def test_restricted_denied_learning(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = CapabilityProjectionEngine(state_dir=td)
            s = ce.project_capability("app", "learning", "restricted")
            assert s is None

    def test_sandboxed_minimal_capabilities(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine, TRUST_TIER_CAPABILITIES,
        )
        sandboxed = TRUST_TIER_CAPABILITIES["sandboxed"]
        assert len(sandboxed) == 2
        assert "sessions" in sandboxed
        assert "observability" in sandboxed

    def test_is_capability_allowed(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = CapabilityProjectionEngine(state_dir=td)
            assert ce.is_capability_allowed("cognition", "core") is True
            assert ce.is_capability_allowed("cognition", "governed") is False

    def test_is_forbidden(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = CapabilityProjectionEngine(state_dir=td)
            assert ce.is_forbidden("direct_adapter_execution") is True
            assert ce.is_forbidden("safe_action") is False

    def test_forbidden_direct_capabilities(self):
        from core.applications.capability_projection_engine_v1 import (
            FORBIDDEN_DIRECT_CAPABILITIES,
        )
        assert len(FORBIDDEN_DIRECT_CAPABILITIES) == 6

    def test_binding_hash_deterministic(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = CapabilityProjectionEngine(state_dir=td)
            ce.project_capability("eos", "workflows", "core")
            ce.project_capability("eos", "sessions", "core")
            h1 = ce.get_binding_hash("eos")
            h2 = ce.get_binding_hash("eos")
            assert h1 == h2

    def test_stats(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = CapabilityProjectionEngine(state_dir=td)
            ce.project_capability("eos", "workflows", "core")
            s = ce.get_stats()
            assert s["total_surfaces"] == 1
            assert s["total_bindings"] == 1


# ── Domain Runtime Context Engine ──────────────────────


class TestDomainRuntimeContextEngine:
    def test_start_context(self):
        from core.applications.domain_runtime_context_engine_v1 import (
            DomainRuntimeContextEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            dc = DomainRuntimeContextEngine(state_dir=td)
            ctx = dc.start_context("eos", "business", "sess1")
            assert ctx is not None
            assert ctx.domain_context == "business"

    def test_unknown_domain_rejected(self):
        from core.applications.domain_runtime_context_engine_v1 import (
            DomainRuntimeContextEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            dc = DomainRuntimeContextEngine(state_dir=td)
            ctx = dc.start_context("eos", "unknown_domain")
            assert ctx is None

    def test_known_contexts_count(self):
        from core.applications.domain_runtime_context_engine_v1 import (
            KNOWN_CONTEXTS,
        )
        assert len(KNOWN_CONTEXTS) == 6

    def test_all_domain_types_valid(self):
        from core.applications.domain_runtime_context_engine_v1 import (
            DomainRuntimeContextEngine, KNOWN_CONTEXTS,
        )
        with tempfile.TemporaryDirectory() as td:
            dc = DomainRuntimeContextEngine(state_dir=td)
            for domain in KNOWN_CONTEXTS:
                ctx = dc.start_context("eos", domain)
                assert ctx is not None, f"Domain {domain} should be valid"

    def test_domain_state_tracked(self):
        from core.applications.domain_runtime_context_engine_v1 import (
            DomainRuntimeContextEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            dc = DomainRuntimeContextEngine(state_dir=td)
            dc.start_context("eos", "business")
            state = dc.get_domain_state("business")
            assert state is not None
            assert "eos" in state["active_applications"]

    def test_isolation_verified(self):
        from core.applications.domain_runtime_context_engine_v1 import (
            DomainRuntimeContextEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            dc = DomainRuntimeContextEngine(state_dir=td)
            dc.start_context("eos", "business")
            assert dc.verify_isolation("business") is True

    def test_restore_context(self):
        from core.applications.domain_runtime_context_engine_v1 import (
            DomainRuntimeContextEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            dc = DomainRuntimeContextEngine(state_dir=td)
            ctx = dc.start_context("eos", "business")
            restored = dc.restore_context(ctx.context_id)
            assert restored is not None
            assert restored.context_id == ctx.context_id

    def test_context_hash_deterministic(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationRuntimeContext,
        )
        c1 = ApplicationRuntimeContext(
            application_id="eos", domain_context="business", session_id="s1",
        )
        c2 = ApplicationRuntimeContext(
            application_id="eos", domain_context="business", session_id="s1",
        )
        assert c1.context_hash == c2.context_hash

    def test_stats(self):
        from core.applications.domain_runtime_context_engine_v1 import (
            DomainRuntimeContextEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            dc = DomainRuntimeContextEngine(state_dir=td)
            dc.start_context("eos", "business")
            s = dc.get_stats()
            assert s["total_contexts"] == 1
            assert s["active_domains"] == 1


# ── Application Continuity Engine ──────────────────────


class TestApplicationContinuityEngine:
    def test_create_checkpoint(self):
        from core.applications.application_continuity_engine_v1 import (
            ApplicationContinuityEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = ApplicationContinuityEngine(state_dir=td)
            cp = ce.create_checkpoint("eos", "sess1", "state")
            assert "content_hash" in cp
            assert cp["app_id"] == "eos"

    def test_restore(self):
        from core.applications.application_continuity_engine_v1 import (
            ApplicationContinuityEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = ApplicationContinuityEngine(state_dir=td)
            ce.create_checkpoint("eos", "sess1", "state")
            restored = ce.restore("eos")
            assert restored is not None
            assert restored["application_id"] == "eos"

    def test_restore_nonexistent(self):
        from core.applications.application_continuity_engine_v1 import (
            ApplicationContinuityEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = ApplicationContinuityEngine(state_dir=td)
            assert ce.restore("nonexistent") is None

    def test_session_chain_tracked(self):
        from core.applications.application_continuity_engine_v1 import (
            ApplicationContinuityEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = ApplicationContinuityEngine(state_dir=td)
            ce.create_checkpoint("eos", "sess1", "s1")
            ce.create_checkpoint("eos", "sess2", "s2")
            chain = ce.get_session_chain("eos")
            assert chain == ["sess1", "sess2"]

    def test_get_checkpoints(self):
        from core.applications.application_continuity_engine_v1 import (
            ApplicationContinuityEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = ApplicationContinuityEngine(state_dir=td)
            ce.create_checkpoint("eos", "s1", "d1")
            ce.create_checkpoint("eos", "s2", "d2")
            cps = ce.get_checkpoints("eos")
            assert len(cps) == 2

    def test_checkpoint_hash_deterministic(self):
        from core.applications.application_continuity_engine_v1 import (
            ApplicationContinuityEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = ApplicationContinuityEngine(state_dir=td)
            cp1 = ce.create_checkpoint("eos", "s1", "data")
            cp2 = ce.create_checkpoint("eos", "s1", "data")
            assert cp1["content_hash"] == cp2["content_hash"]

    def test_stats(self):
        from core.applications.application_continuity_engine_v1 import (
            ApplicationContinuityEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = ApplicationContinuityEngine(state_dir=td)
            ce.create_checkpoint("eos", "s1", "d1")
            s = ce.get_stats()
            assert s["total_checkpoints"] == 1


# ── Observability Pipeline ─────────────────────────────


class TestObservabilityPipeline:
    def test_event_file_map_count(self):
        from core.applications.application_observability_pipeline_v1 import (
            EVENT_FILE_MAP,
        )
        assert len(EVENT_FILE_MAP) == 8

    def test_event_file_map_matches_enum(self):
        from core.applications.application_observability_pipeline_v1 import (
            EVENT_FILE_MAP,
        )
        from core.applications.application_projection_contracts_v1 import (
            ApplicationEventType,
        )
        for et in ApplicationEventType:
            assert et.value in EVENT_FILE_MAP

    def test_emit_application_registered(self):
        with tempfile.TemporaryDirectory() as td:
            from core.applications.application_observability_pipeline_v1 import (
                ApplicationObservabilityPipeline,
            )
            op = ApplicationObservabilityPipeline(state_dir=td)
            e = op.emit_application_registered("eos", "core")
            assert e["event_type"] == "application_registered"

    def test_emit_capability_bound(self):
        with tempfile.TemporaryDirectory() as td:
            from core.applications.application_observability_pipeline_v1 import (
                ApplicationObservabilityPipeline,
            )
            op = ApplicationObservabilityPipeline(state_dir=td)
            e = op.emit_capability_bound("eos", "workflows")
            assert e["capability"] == "workflows"

    def test_emit_projection_created(self):
        with tempfile.TemporaryDirectory() as td:
            from core.applications.application_observability_pipeline_v1 import (
                ApplicationObservabilityPipeline,
            )
            op = ApplicationObservabilityPipeline(state_dir=td)
            e = op.emit_projection_created("eos", "proj-1")
            assert e["projection_id"] == "proj-1"

    def test_emit_projection_denied(self):
        with tempfile.TemporaryDirectory() as td:
            from core.applications.application_observability_pipeline_v1 import (
                ApplicationObservabilityPipeline,
            )
            op = ApplicationObservabilityPipeline(state_dir=td)
            e = op.emit_projection_denied("lyfeos", "not allowed")
            assert e["event_type"] == "projection_denied"

    def test_emit_application_context_started(self):
        with tempfile.TemporaryDirectory() as td:
            from core.applications.application_observability_pipeline_v1 import (
                ApplicationObservabilityPipeline,
            )
            op = ApplicationObservabilityPipeline(state_dir=td)
            e = op.emit_application_context_started("eos", "business")
            assert e["domain_context"] == "business"

    def test_emit_application_boundary_denied(self):
        with tempfile.TemporaryDirectory() as td:
            from core.applications.application_observability_pipeline_v1 import (
                ApplicationObservabilityPipeline,
            )
            op = ApplicationObservabilityPipeline(state_dir=td)
            e = op.emit_application_boundary_denied("eos", "execute", "forbidden")
            assert e["event_type"] == "application_boundary_denied"

    def test_emit_application_replay_validated(self):
        with tempfile.TemporaryDirectory() as td:
            from core.applications.application_observability_pipeline_v1 import (
                ApplicationObservabilityPipeline,
            )
            op = ApplicationObservabilityPipeline(state_dir=td)
            e = op.emit_application_replay_validated("eos", "routing", True)
            assert e["deterministic"] is True

    def test_total_events(self):
        with tempfile.TemporaryDirectory() as td:
            from core.applications.application_observability_pipeline_v1 import (
                ApplicationObservabilityPipeline,
            )
            op = ApplicationObservabilityPipeline(state_dir=td)
            op.emit_application_registered("eos", "core")
            op.emit_capability_bound("eos", "workflows")
            assert len(op.get_events()) == 2

    def test_events_written_to_file(self):
        with tempfile.TemporaryDirectory() as td:
            from core.applications.application_observability_pipeline_v1 import (
                ApplicationObservabilityPipeline,
            )
            op = ApplicationObservabilityPipeline(state_dir=td)
            op.emit_application_registered("eos", "core")
            p = Path(td) / "application_registered.jsonl"
            assert p.exists()


# ── Replay Validator ───────────────────────────────────


class TestReplayValidator:
    def test_replay_checks_count(self):
        from core.applications.application_replay_validator_v1 import (
            REPLAY_CHECKS,
        )
        assert len(REPLAY_CHECKS) == 5

    def test_validate_determinism(self):
        from core.applications.application_replay_validator_v1 import (
            ApplicationReplayValidator,
        )
        rv = ApplicationReplayValidator()
        r = rv.validate_determinism("projection_routing", "in", "out")
        assert r["deterministic"] is True

    def test_unknown_check_rejected(self):
        from core.applications.application_replay_validator_v1 import (
            ApplicationReplayValidator,
        )
        rv = ApplicationReplayValidator()
        with pytest.raises(ValueError, match="Unknown check"):
            rv.validate_determinism("unknown_check", "in", "out")

    def test_replay_pair_same_output(self):
        from core.applications.application_replay_validator_v1 import (
            ApplicationReplayValidator,
        )
        rv = ApplicationReplayValidator()
        r = rv.validate_replay_pair("capability_binding", "in", "same", "same")
        assert r["deterministic"] is True

    def test_replay_pair_different_output(self):
        from core.applications.application_replay_validator_v1 import (
            ApplicationReplayValidator,
        )
        rv = ApplicationReplayValidator()
        r = rv.validate_replay_pair("capability_binding", "in", "a", "b")
        assert r["deterministic"] is False

    def test_all_checks_valid(self):
        from core.applications.application_replay_validator_v1 import (
            ApplicationReplayValidator, REPLAY_CHECKS,
        )
        rv = ApplicationReplayValidator()
        for check in REPLAY_CHECKS:
            r = rv.validate_determinism(check, "in", "out")
            assert r["deterministic"] is True

    def test_stats(self):
        from core.applications.application_replay_validator_v1 import (
            ApplicationReplayValidator,
        )
        rv = ApplicationReplayValidator()
        rv.validate_determinism("projection_routing", "in", "out")
        rv.validate_replay_pair("capability_binding", "in", "a", "b")
        s = rv.get_stats()
        assert s["total_checks"] == 2
        assert s["deterministic_count"] == 1
        assert s["non_deterministic_count"] == 1


# ── Boundary Policies ─────────────────────────────────


class TestBoundaryPolicies:
    def test_limits_count(self):
        from core.applications.application_boundary_policies_v1 import (
            APPLICATION_LIMITS,
        )
        assert len(APPLICATION_LIMITS) == 8

    def test_forbidden_count(self):
        from core.applications.application_boundary_policies_v1 import (
            FORBIDDEN_APPLICATION_ACTIONS,
        )
        assert len(FORBIDDEN_APPLICATION_ACTIONS) == 8

    def test_enforce_limit_default(self):
        from core.applications.application_boundary_policies_v1 import (
            enforce_limit,
        )
        assert enforce_limit("max_applications") == 20

    def test_enforce_limit_override_lower(self):
        from core.applications.application_boundary_policies_v1 import (
            enforce_limit,
        )
        assert enforce_limit("max_applications", 10) == 10

    def test_enforce_limit_override_higher_capped(self):
        from core.applications.application_boundary_policies_v1 import (
            enforce_limit,
        )
        assert enforce_limit("max_applications", 100) == 20

    def test_enforce_limit_unknown_raises(self):
        from core.applications.application_boundary_policies_v1 import (
            enforce_limit,
        )
        with pytest.raises(ValueError, match="Unknown limit"):
            enforce_limit("unknown_limit")

    def test_is_forbidden_true(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("application_owned_orchestration") is True

    def test_is_forbidden_false(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("safe_projection") is False

    def test_get_all_limits(self):
        from core.applications.application_boundary_policies_v1 import (
            get_all_limits,
        )
        limits = get_all_limits()
        assert isinstance(limits, dict)
        assert len(limits) == 8

    def test_get_all_forbidden(self):
        from core.applications.application_boundary_policies_v1 import (
            get_all_forbidden,
        )
        forbidden = get_all_forbidden()
        assert isinstance(forbidden, list)
        assert len(forbidden) == 8

    def test_validate_boundaries(self):
        from core.applications.application_boundary_policies_v1 import (
            validate_boundaries,
        )
        v = validate_boundaries()
        assert v["limits_count"] == 8
        assert v["forbidden_count"] == 8

    def test_application_owned_orchestration_forbidden(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("application_owned_orchestration") is True

    def test_application_owned_cognition_forbidden(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("application_owned_cognition") is True

    def test_application_owned_governance_forbidden(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("application_owned_governance") is True

    def test_application_owned_canonical_memory_forbidden(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("application_owned_canonical_memory") is True

    def test_application_owned_learning_mutation_forbidden(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("application_owned_learning_mutation") is True

    def test_direct_adapter_execution_forbidden(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("direct_adapter_execution") is True

    def test_substrate_bypass_forbidden(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("substrate_bypass") is True

    def test_hidden_domain_escalation_forbidden(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("hidden_domain_escalation") is True


# ── Topology Engine ────────────────────────────────────


class TestTopologyEngine:
    def test_register_node(self):
        from core.applications.application_topology_engine_v1 import (
            ApplicationTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = ApplicationTopologyEngine(state_dir=td)
            node = te.register_node("eos", "business")
            assert node is not None
            assert node["app_id"] == "eos"

    def test_duplicate_node_returns_existing(self):
        from core.applications.application_topology_engine_v1 import (
            ApplicationTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = ApplicationTopologyEngine(state_dir=td)
            n1 = te.register_node("eos", "business")
            n2 = te.register_node("eos", "business")
            assert n1 is n2

    def test_add_edge(self):
        from core.applications.application_topology_engine_v1 import (
            ApplicationTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = ApplicationTopologyEngine(state_dir=td)
            te.register_node("eos", "business")
            te.register_node("lyfeos", "personal")
            edge = te.add_edge("eos", "lyfeos")
            assert edge is not None

    def test_self_edge_denied(self):
        from core.applications.application_topology_engine_v1 import (
            ApplicationTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = ApplicationTopologyEngine(state_dir=td)
            te.register_node("eos", "business")
            edge = te.add_edge("eos", "eos")
            assert edge is None

    def test_edge_requires_nodes(self):
        from core.applications.application_topology_engine_v1 import (
            ApplicationTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = ApplicationTopologyEngine(state_dir=td)
            edge = te.add_edge("eos", "lyfeos")
            assert edge is None

    def test_domain_isolation_verified(self):
        from core.applications.application_topology_engine_v1 import (
            ApplicationTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = ApplicationTopologyEngine(state_dir=td)
            te.register_node("eos", "business")
            te.register_node("lyfeos", "personal")
            assert te.verify_domain_isolation("business", "personal") is True

    def test_domain_isolation_shared_domain(self):
        from core.applications.application_topology_engine_v1 import (
            ApplicationTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = ApplicationTopologyEngine(state_dir=td)
            te.register_node("eos", "business")
            te.register_node("lyfeos", "business")
            assert te.verify_domain_isolation("business", "personal") is True
            assert te.verify_domain_isolation("business", "business") is False

    def test_topology_snapshot(self):
        from core.applications.application_topology_engine_v1 import (
            ApplicationTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = ApplicationTopologyEngine(state_dir=td)
            te.register_node("eos", "business")
            te.register_node("lyfeos", "personal")
            snap = te.get_topology_snapshot()
            assert len(snap.applications) == 2

    def test_topology_hash_deterministic(self):
        from core.applications.application_topology_engine_v1 import (
            ApplicationTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = ApplicationTopologyEngine(state_dir=td)
            te.register_node("eos", "business")
            te.register_node("lyfeos", "personal")
            h1 = te.get_topology_hash()
            h2 = te.get_topology_hash()
            assert h1 == h2

    def test_get_edges_for_app(self):
        from core.applications.application_topology_engine_v1 import (
            ApplicationTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = ApplicationTopologyEngine(state_dir=td)
            te.register_node("eos", "business")
            te.register_node("lyfeos", "personal")
            te.add_edge("eos", "lyfeos")
            edges = te.get_edges_for_app("eos")
            assert len(edges) == 1

    def test_stats(self):
        from core.applications.application_topology_engine_v1 import (
            ApplicationTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = ApplicationTopologyEngine(state_dir=td)
            te.register_node("eos", "business")
            s = te.get_stats()
            assert s["total_nodes"] == 1


# ── Continuity Bridges ─────────────────────────────────


class TestContinuityBridges:
    def test_all_bridges_count(self):
        from core.applications.application_continuity_bridges_v1 import (
            ALL_BRIDGES,
        )
        assert len(ALL_BRIDGES) == 9

    def test_sessions_bridge(self):
        from core.applications.application_continuity_bridges_v1 import (
            SessionsApplicationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = SessionsApplicationBridge(state_dir=td)
            e = b.record("test", {"key": "value"})
            assert e["bridge"] == "sessions_application"

    def test_workflows_bridge(self):
        from core.applications.application_continuity_bridges_v1 import (
            WorkflowsApplicationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = WorkflowsApplicationBridge(state_dir=td)
            e = b.record("test", {"key": "value"})
            assert e["bridge"] == "workflows_application"

    def test_knowledge_bridge(self):
        from core.applications.application_continuity_bridges_v1 import (
            KnowledgeApplicationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = KnowledgeApplicationBridge(state_dir=td)
            e = b.record("test", {"key": "value"})
            assert e["bridge"] == "knowledge_application"

    def test_learning_bridge(self):
        from core.applications.application_continuity_bridges_v1 import (
            LearningApplicationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = LearningApplicationBridge(state_dir=td)
            e = b.record("test", {"key": "value"})
            assert e["bridge"] == "learning_application"

    def test_cognition_bridge(self):
        from core.applications.application_continuity_bridges_v1 import (
            CognitionApplicationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = CognitionApplicationBridge(state_dir=td)
            e = b.record("test", {"key": "value"})
            assert e["bridge"] == "cognition_application"

    def test_ingress_bridge(self):
        from core.applications.application_continuity_bridges_v1 import (
            IngressApplicationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = IngressApplicationBridge(state_dir=td)
            e = b.record("test", {"key": "value"})
            assert e["bridge"] == "ingress_application"

    def test_environments_bridge(self):
        from core.applications.application_continuity_bridges_v1 import (
            EnvironmentsApplicationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = EnvironmentsApplicationBridge(state_dir=td)
            e = b.record("test", {"key": "value"})
            assert e["bridge"] == "environments_application"

    def test_scaling_bridge(self):
        from core.applications.application_continuity_bridges_v1 import (
            ScalingApplicationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = ScalingApplicationBridge(state_dir=td)
            e = b.record("test", {"key": "value"})
            assert e["bridge"] == "scaling_application"

    def test_resilience_bridge(self):
        from core.applications.application_continuity_bridges_v1 import (
            ResilienceApplicationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = ResilienceApplicationBridge(state_dir=td)
            e = b.record("test", {"key": "value"})
            assert e["bridge"] == "resilience_application"

    def test_bridge_events_tracked(self):
        from core.applications.application_continuity_bridges_v1 import (
            SessionsApplicationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = SessionsApplicationBridge(state_dir=td)
            b.record("e1", {"a": 1})
            b.record("e2", {"b": 2})
            assert len(b.get_events()) == 2

    def test_bridge_stats(self):
        from core.applications.application_continuity_bridges_v1 import (
            SessionsApplicationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = SessionsApplicationBridge(state_dir=td)
            b.record("test", {})
            s = b.get_stats()
            assert s["total_events"] == 1

    def test_bridge_writes_to_file(self):
        from core.applications.application_continuity_bridges_v1 import (
            SessionsApplicationBridge,
        )
        with tempfile.TemporaryDirectory() as td:
            b = SessionsApplicationBridge(state_dir=td)
            b.record("test", {"key": "value"})
            p = Path(td) / "sessions_application.jsonl"
            assert p.exists()


# ── Coordinator ────────────────────────────────────────


class TestCoordinator:
    def _make_coordinator(self, td):
        from core.applications.canonical_application_projection_coordinator_v1 import (
            CanonicalApplicationProjectionCoordinator,
        )
        return CanonicalApplicationProjectionCoordinator(state_dir=td)

    def test_register_application(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            app = coord.register_application("eos")
            assert app["name"] == "EntrepreneurOS"
            assert app["trust_tier"] == "core"

    def test_bind_capability(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("eos")
            bind = coord.bind_capability("eos", "cognition")
            assert bind is not None

    def test_bind_capability_denied_for_governed(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("lyfeos")
            bind = coord.bind_capability("lyfeos", "cognition")
            assert bind is None

    def test_bind_capability_unknown_app(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            bind = coord.bind_capability("unknown", "workflows")
            assert bind is None

    def test_create_projection(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("eos")
            proj = coord.create_projection("eos")
            assert proj is not None
            assert proj["application_id"] == "eos"

    def test_create_projection_unknown_app(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            proj = coord.create_projection("unknown")
            assert proj is None

    def test_start_context(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("eos")
            ctx = coord.start_context("eos", "business", "sess1")
            assert ctx is not None

    def test_start_context_default_domain(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("eos")
            ctx = coord.start_context("eos", session_id="sess1")
            assert ctx is not None
            assert ctx["domain_context"] == "business"

    def test_restore_context(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("eos")
            ctx = coord.start_context("eos", "business", "sess1")
            restored = coord.restore_context("eos", ctx["context_id"])
            assert restored is not None

    def test_create_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("eos")
            cp = coord.create_checkpoint("eos", "sess1", "state")
            assert "content_hash" in cp

    def test_restore_continuity(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("eos")
            coord.create_checkpoint("eos", "sess1", "state")
            restored = coord.restore_continuity("eos")
            assert restored is not None

    def test_get_all_applications(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("eos")
            coord.register_application("lyfeos")
            coord.register_application("creatoros")
            assert len(coord.get_all_applications()) == 3

    def test_get_capability_surfaces(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("eos")
            coord.bind_capability("eos", "workflows")
            surfaces = coord.get_capability_surfaces("eos")
            assert len(surfaces) == 1

    def test_get_domain_state(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("eos")
            coord.start_context("eos", "business")
            state = coord.get_domain_state("business")
            assert state is not None

    def test_topology_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("eos")
            coord.register_application("lyfeos")
            snap = coord.get_topology_snapshot()
            assert len(snap["applications"]) == 2

    def test_topology_edge(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("eos")
            coord.register_application("lyfeos")
            edge = coord.add_topology_edge("eos", "lyfeos")
            assert edge is not None

    def test_verify_domain_isolation(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            coord.register_application("eos")
            coord.register_application("lyfeos")
            assert coord.verify_domain_isolation("business", "personal") is True

    def test_get_health(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            h = coord.get_health()
            assert "lifecycle_state" in h
            assert "registry" in h
            assert "capabilities" in h
            assert "contexts" in h
            assert "topology" in h

    def test_get_stats_seven_subsystems(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            s = coord.get_stats()
            assert len(s) == 7
            for key in ["lifecycle", "registry", "capabilities", "contexts",
                        "continuity", "observability", "topology"]:
                assert key in s

    def test_no_forbidden_methods(self):
        with tempfile.TemporaryDirectory() as td:
            coord = self._make_coordinator(td)
            methods = [m for m in dir(coord) if not m.startswith("_")]
            forbidden = [
                "execute", "dispatch", "run_adapter", "orchestrate",
                "govern", "mutate_canonical", "write_policy",
                "inject_cognition", "mutate_learning", "bypass_spine",
            ]
            for fm in forbidden:
                assert fm not in methods, f"Found forbidden method: {fm}"


# ── Constraint Verification ────────────────────────────


class TestConstraintVerification:
    def test_no_application_owned_orchestration(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("application_owned_orchestration") is True

    def test_no_application_owned_cognition(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("application_owned_cognition") is True

    def test_no_application_owned_governance(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("application_owned_governance") is True

    def test_no_application_owned_memory_canon(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("application_owned_canonical_memory") is True

    def test_no_application_owned_learning_mutation(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("application_owned_learning_mutation") is True

    def test_no_substrate_bypass(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("substrate_bypass") is True

    def test_no_direct_adapter_execution(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("direct_adapter_execution") is True

    def test_no_hidden_domain_escalation(self):
        from core.applications.application_boundary_policies_v1 import (
            is_forbidden,
        )
        assert is_forbidden("hidden_domain_escalation") is True

    def test_deterministic_projection_replay(self):
        from core.applications.application_projection_contracts_v1 import (
            ApplicationProjection,
        )
        p1 = ApplicationProjection(
            application_id="eos", domain_context="business",
            capabilities_bound=["workflows", "sessions"],
        )
        p2 = ApplicationProjection(
            application_id="eos", domain_context="business",
            capabilities_bound=["workflows", "sessions"],
        )
        assert p1.projection_hash == p2.projection_hash

    def test_deterministic_capability_routing(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = CapabilityProjectionEngine(state_dir=td)
            ce.project_capability("eos", "workflows", "core")
            ce.project_capability("eos", "sessions", "core")
            h1 = ce.get_binding_hash("eos")
            h2 = ce.get_binding_hash("eos")
            assert h1 == h2

    def test_domain_isolation_preserved(self):
        from core.applications.application_topology_engine_v1 import (
            ApplicationTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = ApplicationTopologyEngine(state_dir=td)
            te.register_node("eos", "business")
            te.register_node("lyfeos", "personal")
            te.register_node("creatoros", "creator_media")
            assert te.verify_domain_isolation("business", "personal") is True
            assert te.verify_domain_isolation("business", "creator_media") is True
            assert te.verify_domain_isolation("personal", "creator_media") is True

    def test_trust_tier_enforcement_core(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine,
        )
        from core.applications.application_projection_contracts_v1 import (
            CapabilityCategory,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = CapabilityProjectionEngine(state_dir=td)
            for cat in CapabilityCategory:
                assert ce.is_capability_allowed(cat.value, "core") is True

    def test_trust_tier_enforcement_governed(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = CapabilityProjectionEngine(state_dir=td)
            assert ce.is_capability_allowed("cognition", "governed") is False
            assert ce.is_capability_allowed("learning", "governed") is False
            assert ce.is_capability_allowed("workflows", "governed") is True

    def test_trust_tier_enforcement_restricted(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = CapabilityProjectionEngine(state_dir=td)
            assert ce.is_capability_allowed("cognition", "restricted") is False
            assert ce.is_capability_allowed("knowledge", "restricted") is False
            assert ce.is_capability_allowed("workflows", "restricted") is True

    def test_trust_tier_enforcement_sandboxed(self):
        from core.applications.capability_projection_engine_v1 import (
            CapabilityProjectionEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = CapabilityProjectionEngine(state_dir=td)
            assert ce.is_capability_allowed("cognition", "sandboxed") is False
            assert ce.is_capability_allowed("workflows", "sandboxed") is False
            assert ce.is_capability_allowed("sessions", "sandboxed") is True
            assert ce.is_capability_allowed("observability", "sandboxed") is True

    def test_replay_lineage_preserved(self):
        from core.applications.application_replay_validator_v1 import (
            ApplicationReplayValidator, REPLAY_CHECKS,
        )
        rv = ApplicationReplayValidator()
        for check in REPLAY_CHECKS:
            r = rv.validate_determinism(check, "test_input", "test_output")
            assert r["deterministic"] is True

    def test_continuity_restoration_deterministic(self):
        from core.applications.application_continuity_engine_v1 import (
            ApplicationContinuityEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            ce = ApplicationContinuityEngine(state_dir=td)
            cp1 = ce.create_checkpoint("eos", "s1", "data")
            cp2 = ce.create_checkpoint("eos", "s1", "data")
            assert cp1["content_hash"] == cp2["content_hash"]

    def test_override_capping(self):
        from core.applications.application_boundary_policies_v1 import (
            enforce_limit, APPLICATION_LIMITS,
        )
        for name, default in APPLICATION_LIMITS.items():
            assert enforce_limit(name, default + 100) == default
            assert enforce_limit(name, default - 1) == default - 1

    def test_coordinator_cannot_execute(self):
        with tempfile.TemporaryDirectory() as td:
            from core.applications.canonical_application_projection_coordinator_v1 import (
                CanonicalApplicationProjectionCoordinator,
            )
            coord = CanonicalApplicationProjectionCoordinator(state_dir=td)
            methods = dir(coord)
            assert "execute" not in methods
            assert "dispatch" not in methods
            assert "run" not in methods

    def test_coordinator_cannot_orchestrate(self):
        with tempfile.TemporaryDirectory() as td:
            from core.applications.canonical_application_projection_coordinator_v1 import (
                CanonicalApplicationProjectionCoordinator,
            )
            coord = CanonicalApplicationProjectionCoordinator(state_dir=td)
            methods = dir(coord)
            assert "orchestrate" not in methods
            assert "govern" not in methods

    def test_topology_hash_deterministic(self):
        from core.applications.application_topology_engine_v1 import (
            ApplicationTopologyEngine,
        )
        with tempfile.TemporaryDirectory() as td:
            te = ApplicationTopologyEngine(state_dir=td)
            te.register_node("eos", "business")
            te.register_node("lyfeos", "personal")
            te.add_edge("eos", "lyfeos")
            h1 = te.get_topology_hash()
            h2 = te.get_topology_hash()
            assert h1 == h2

    def test_known_apps_trust_tiers_correct(self):
        from core.applications.application_registry_engine_v1 import (
            KNOWN_APPLICATIONS,
        )
        assert KNOWN_APPLICATIONS["eos"]["trust_tier"] == "core"
        assert KNOWN_APPLICATIONS["lyfeos"]["trust_tier"] == "governed"
        assert KNOWN_APPLICATIONS["creatoros"]["trust_tier"] == "governed"
