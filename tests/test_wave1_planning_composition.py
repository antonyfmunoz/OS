"""Wave 1 planning composition tests — compiler, archetypes, readiness, profile.

Covers: test B (atomic Task → one canonical WorkPacket, no Objective/Plan/HUD
Decision), test F (complex objective → grounded states, versioned Plan,
canonical Tasks, decision requirement, zero execution), test E (revision
v(n+1), v(n) preserved), test T (fractal decomposition bounded, no flat
list), test S (archetype determinism + attributed overrides), test R
(role-bound skill validation), test W (dev profile — no silent layer
omission, no infrastructure theater), tests X/AD (readiness semantics),
test V (instruction compilation), test Y (scope/provenance separation on
packets), test Z (canonical Goal reference, gap artifact snapshot-classified),
test AB core (packets never executable), test AH (versioned skill refs
pinned in plan artifacts).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from substrate.contracts.work_context import PrincipalContext, WorkScope
from substrate.execution.intent.context_frame import ContextFrame
from substrate.execution.intent.protocol import (
    DecisionRequirement,
    IntentClass,
    OperatorIntentProtocol,
)
from substrate.execution.planning.archetypes import (
    resolve_archetype,
    validate_skill_requirements,
)
from substrate.execution.planning.compiler import (
    PACKET_NODE_CAP,
    PlanCompilationError,
    compile_revision,
    packet_predecessors,
)
from substrate.execution.planning.dev_profile import (
    PRODUCTION_LAYERS,
    build_development_profile,
)
from substrate.execution.planning.instruction_compilation import (
    InstructionCompilationError,
    InstructionCompilationRequest,
    compile_instruction_package,
)
from substrate.execution.planning.readiness import (
    DecisionReadiness,
    evaluate_decision_readiness,
)
from substrate.execution.planning.records import (
    GapAssessmentSnapshot,
    ObjectivePlanRecord,
    ObjectivePlanStatus,
    PlanningSession,
    PlanningStageMarker,
    RevisionEditSet,
)
from substrate.execution.planning.store import PlanningStore
from substrate.organism.event_spine import EventSpine
from substrate.organism.strategic_gap_engine import GoalRegistry
from substrate.organism.universal_work_queue import UniversalWorkQueue
from substrate.organism.work_packet import PacketLifecycleStatus

DOGFOOD_OBJECTIVE = (
    "Migrate the remaining nine legacy runtime subsystems under data/umh "
    "to the runtime-state boundary: heartbeats, queues, snapshots, journals, "
    "receipts, consent_grants, sessions, traces, approvals"
)


class Runner:
    def __init__(self):
        self.calls: list[str] = []

    def __call__(self, mutation_name, intent, execute_fn, source="", metadata=None):
        self.calls.append(mutation_name)
        output, ok = execute_fn()
        return SimpleNamespace(success=ok, output=output, envelope_id="env-test")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("UMH_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo").mkdir()
    store = PlanningStore(
        sessions_path=str(tmp_path / "p" / "sessions.jsonl"),
        plans_path=str(tmp_path / "p" / "plans.jsonl"),
        grounding_path=str(tmp_path / "p" / "grounding.jsonl"),
        current_path=str(tmp_path / "p" / "current.jsonl"),
        desired_path=str(tmp_path / "p" / "desired.jsonl"),
        gaps_path=str(tmp_path / "p" / "gaps.jsonl"),
    )
    goals = GoalRegistry(store_path=str(tmp_path / "goals.jsonl"))
    queue = UniversalWorkQueue(store_path=str(tmp_path / "packets.jsonl"))
    runner = Runner()
    protocol = OperatorIntentProtocol(
        store=store, goal_registry=goals, event_spine=EventSpine(), mutation_runner=runner
    )
    principal = PrincipalContext(
        principal_id="user-1", tenant_id="tenant-a", membership_id="mem-abc"
    )
    scope = WorkScope(tenant_id="tenant-a", conversation_id="conv-1", target_kind="umh_substrate")
    return SimpleNamespace(
        store=store,
        goals=goals,
        queue=queue,
        runner=runner,
        protocol=protocol,
        principal=principal,
        scope=scope,
    )


def _frame() -> ContextFrame:
    return ContextFrame(tenant_id="tenant-a", principal_id="user-1", conversation_id="conv-1")


def _plan_objective(env, text: str = DOGFOOD_OBJECTIVE, cmid: str = "m1"):
    resolution = env.protocol.resolve(
        text, env.principal, env.scope, _frame(), client_message_id=cmid
    )
    assert resolution.intent_class == IntentClass.CREATE_OBJECTIVE.value
    return env.protocol.plan_objective(
        resolution, text, "conv-1", client_message_id=cmid, work_queue=env.queue
    )


# ── Test B: atomic Task capture ──────────────────────────────────────────────


class TestAtomicTaskCapture:
    TASK = "Fix the failing import in transports/api/voice.py"

    def test_one_canonical_packet_no_objective_no_plan_no_decision(self, env):
        resolution = env.protocol.resolve(
            self.TASK, env.principal, env.scope, _frame(), client_message_id="t1"
        )
        assert resolution.intent_class == IntentClass.CREATE_TASK.value
        assert resolution.decision_requirement == DecisionRequirement.NOT_REQUIRED.value
        packet = env.protocol.capture_task(
            resolution, self.TASK, "conv-1", client_message_id="t1", work_queue=env.queue
        )
        assert packet.status == PacketLifecycleStatus.PLANNED
        assert packet.work_scope["tenant_id"] == "tenant-a"
        assert packet.lineage["originating_conversation_id"] == "conv-1"
        assert packet.approval_gates  # never empty
        assert not packet.is_execution_ready()
        # No Objective, no Plan, no plan-acceptance decision surface.
        assert env.goals.all_goals() == []
        assert env.store.load_plans() == []
        assert "operator_task_capture" in env.runner.calls

    def test_ak_retry_is_idempotent(self, env):
        resolution = env.protocol.resolve(
            self.TASK, env.principal, env.scope, _frame(), client_message_id="t1"
        )
        p1 = env.protocol.capture_task(
            resolution, self.TASK, "conv-1", client_message_id="t1", work_queue=env.queue
        )
        p2 = env.protocol.capture_task(
            resolution, self.TASK, "conv-1", client_message_id="t1", work_queue=env.queue
        )
        assert p1.packet_id == p2.packet_id
        assert len(env.queue.all_packets()) == 1


# ── Test F: complex objective full pipeline ──────────────────────────────────


class TestComplexObjectivePipeline:
    def test_full_composition(self, env):
        session, plan = _plan_objective(env)

        # Unit of work committed; linkage complete.
        assert session.operation_stage == PlanningStageMarker.COMMITTED.value
        assert plan.objective_id == session.objective_id
        assert plan.objective_id.startswith("goal-")
        assert env.goals.get(plan.objective_id) is not None  # canonical Goal (test Z)
        assert plan.grounding_snapshot_id and plan.current_state_id and plan.desired_state_id
        assert plan.current_state_id != plan.desired_state_id
        assert plan.gap_model_id

        # Canonical Tasks at most PLANNED, never executable (test AB core).
        assert plan.workpacket_ids
        for pid in plan.workpacket_ids:
            packet = env.queue.get_packet(pid)
            assert packet.status == PacketLifecycleStatus.PLANNED
            assert packet.approval_gates
            assert not packet.is_execution_ready()
            # Test Y: scope is a first-class typed field, provenance survives.
            assert packet.work_scope["tenant_id"] == "tenant-a"
            assert packet.lineage["plan_record_id"] == plan.plan_record_id
            assert packet.lineage["objective_id"] == plan.objective_id
            assert packet.source_type == "objective_plan"

        # Decision required and readiness evaluated.
        assert plan.status == ObjectivePlanStatus.AWAITING_APPROVAL.value
        assert plan.readiness_assessment["state"] == DecisionReadiness.DECISION_READY.value
        package = plan.readiness_assessment["decision_package"]
        assert package["authorizes"] == "plan acceptance ONLY"
        assert "execution" in package["does_not_authorize"]

    def test_retry_returns_same_plan(self, env):
        _, plan1 = _plan_objective(env)
        _, plan2 = _plan_objective(env)
        assert plan1.plan_record_id == plan2.plan_record_id
        assert len(env.store.load_plans()) == 1
        assert len(env.goals.all_goals()) == 1

    def test_ah_skill_refs_pinned_in_plan(self, env):
        _, plan = _plan_objective(env)
        refs = plan.archetype_resolution["required_skill_refs"]
        assert refs
        for ref in refs:
            assert ref["version_constraint"]  # versioned, never bare
            assert ref["responsible_role_contract_id"]


# ── Test E: revision v(n+1) ──────────────────────────────────────────────────


class TestRevision:
    def test_revision_appends_new_version_preserving_old(self, env):
        _, plan = _plan_objective(env)
        edit_set = RevisionEditSet(
            edits=[{"op": "add_node", "kind": "packet", "title": "Add rollback verification step"}]
        )
        runner = Runner()
        new_plan = compile_revision(plan, edit_set, env.store, runner)
        assert new_plan.graph_version == plan.graph_version + 1
        assert new_plan.supersedes_plan_record_id == plan.plan_record_id
        assert "objective_plan_revise" in runner.calls

        old = env.store.get_plan(plan.plan_record_id)
        assert old is not None  # v(n) retained
        assert old.status == ObjectivePlanStatus.SUPERSEDED.value
        assert env.store.get_plan(new_plan.plan_record_id) is not None
        assert new_plan.objective_id == plan.objective_id  # same canonical Objective

    def test_invalid_op_rejected(self, env):
        _, plan = _plan_objective(env)
        with pytest.raises(PlanCompilationError):
            compile_revision(plan, RevisionEditSet(edits=[{"op": "explode"}]), env.store, Runner())


# ── Test T: fractal decomposition ────────────────────────────────────────────


class TestFractalDecomposition:
    def test_project_scale_bounded(self, env):
        _, plan = _plan_objective(env)
        packet_nodes = [n for n in plan.nodes if n["kind"] == "packet"]
        assert 0 < len(packet_nodes) <= PACKET_NODE_CAP
        assert plan.decomposition["stop_reason"]
        assert plan.planning_scale == "project_objective"

    def test_portfolio_scale_defers_children(self, env):
        text = (
            "Build a company-wide operations program covering all ventures: "
            "outreach, content, invoicing, onboarding, analytics, support, "
            "hiring, compliance, retention"
        )
        resolution = env.protocol.resolve(
            text, env.principal, env.scope, _frame(), client_message_id="m9"
        )
        assert resolution.planning_scale in ("portfolio_objective", "program_objective")
        session, plan = env.protocol.plan_objective(
            resolution, text, "conv-1", client_message_id="m9", work_queue=env.queue
        )
        packet_nodes = [n for n in plan.nodes if n["kind"] == "packet"]
        assert len(packet_nodes) <= 5  # bounded frontier, never a flat list
        assert plan.decomposition["decomposition_frontier"]
        # deferral is recorded explicitly, not silently dropped
        assert "stop_reason" in plan.decomposition

    def test_packet_predecessor_closure(self, env):
        _, plan = _plan_objective(env)
        verification = next(n for n in plan.nodes if n["kind"] == "verification")
        milestone = next(n for n in plan.nodes if n["kind"] == "milestone")
        # Milestone's packet predecessors resolve THROUGH the verification node.
        preds = packet_predecessors(plan, milestone["node_id"])
        packet_ids = {n["node_id"] for n in plan.nodes if n["kind"] == "packet"}
        assert set(preds) == packet_ids
        assert verification["node_id"] not in preds


# ── Test S: archetype determinism ────────────────────────────────────────────


class TestArchetypeDeterminism:
    def test_same_work_same_policy(self):
        scope = WorkScope(tenant_id="t1", target_kind="umh_substrate")
        a = resolve_archetype("Implement the billing API service", scope)
        b = resolve_archetype("Implement the billing API service", scope)
        assert a.to_dict() == b.to_dict()
        assert a.archetype_id == "development"
        assert a.governance_policy["profile"] == "self_build"

    def test_projection_target_gets_projection_governance(self):
        scope = WorkScope(tenant_id="t1", target_kind="projection")
        r = resolve_archetype("Build the client onboarding page", scope)
        assert r.governance_policy["profile"] == "projection_build"
        assert "tenant_isolation" in r.governance_policy["requires"]

    def test_override_requires_attribution_and_reason(self):
        scope = WorkScope(tenant_id="t1")
        good = {"field": "environment_class", "reason": "needs GPU", "attributed_to": "operator"}
        bad = {"field": "environment_class"}
        r = resolve_archetype("Research market pricing", scope, overrides=[good, bad])
        assert r.overrides == [good]
        assert any("override rejected" in g for g in r.unresolved_requirement_gaps)

    def test_research_archetype(self):
        r = resolve_archetype(
            "Investigate why the voice runtime drops sessions", WorkScope(tenant_id="t1")
        )
        assert r.archetype_id == "research"
        assert r.environment_class == "read_only"


# ── Test R: role-bound skill validation ──────────────────────────────────────


class TestRoleBoundSkills:
    def _role(self, **kwargs):
        from substrate.organism.role_contracts import RoleContract

        return RoleContract(role_id="role-impl-op", **kwargs)

    def _ref(self, skill_id="s1", **kwargs):
        from substrate.contracts.work_context import SkillRequirementRef

        defaults = dict(
            skill_id=skill_id,
            version_constraint=">=1",
            responsible_role_contract_id="role-impl-op",
            minimum_mastery="practitioner",
        )
        defaults.update(kwargs)
        return SkillRequirementRef(**defaults).to_dict()

    def test_prohibited_skill_rejected(self):
        gaps = validate_skill_requirements(
            [self._ref("dangerous-skill")], self._role(prohibited_skill_ids=["dangerous-skill"])
        )
        assert any("PROHIBITED" in g for g in gaps)

    def test_unpermitted_skill_rejected_when_role_restricts(self):
        gaps = validate_skill_requirements(
            [self._ref("other")], self._role(permitted_skill_ids=["only-this"])
        )
        assert any("not permitted" in g for g in gaps)

    def test_missing_mastery_flagged(self):
        gaps = validate_skill_requirements(
            [self._ref("s1", minimum_mastery="")],
            self._role(skill_mastery_requirements={"s1": "expert"}),
        )
        assert any("mastery" in g for g in gaps)

    def test_clean_requirements_pass(self):
        gaps = validate_skill_requirements([self._ref()], self._role())
        assert gaps == []

    def test_bare_ref_rejected(self):
        gaps = validate_skill_requirements(["bare-id"], self._role())  # type: ignore[list-item]
        assert any("bare skill reference" in g for g in gaps)


# ── Test W: development profile ──────────────────────────────────────────────


class TestDevelopmentProfile:
    def test_multi_tenant_app_assesses_every_layer(self):
        profile = build_development_profile(
            "Build a multi-tenant SaaS web app with API backend, postgres schema, "
            "auth, and production deploy",
            WorkScope(tenant_id="t1", target_kind="projection"),
        )
        assert profile.assert_complete() == []
        by_layer = {a["layer"]: a["status"] for a in profile.layer_assessments}
        # Tenancy/security/observability/recovery cannot vanish silently.
        assert by_layer["layer_04_authn_authz"] == "required"
        assert by_layer["layer_08_security_secrets_tenancy_rls"] == "required"
        assert by_layer["layer_12_observability"] == "required"
        assert by_layer["layer_13_availability_backup_recovery_rollback"] == "required"

    def test_static_prototype_no_infrastructure_theater(self):
        profile = build_development_profile(
            "Create a static landing page prototype for the arena offer",
            WorkScope(tenant_id="t1", target_kind="projection"),
        )
        assert profile.assert_complete() == []  # same layers, all assessed
        by_layer = {a["layer"]: a["status"] for a in profile.layer_assessments}
        assert by_layer["layer_05_hosting"] == "not_applicable"
        assert by_layer["layer_11_load_scaling"] == "not_applicable"
        assert len(profile.layer_assessments) == len(PRODUCTION_LAYERS)

    def test_ai_native_requirements_when_ai_in_scope(self):
        profile = build_development_profile(
            "Build an AI agent service with prompt routing and an LLM fallback chain",
            WorkScope(tenant_id="t1", target_kind="umh_substrate"),
        )
        assert profile.ai_native["fallback_behavior"] == "deterministic-first mandatory"
        assert profile.software_target.get("software_artifact_type") in ("service_api", "web_app")


# ── Tests X / AD: decision readiness ─────────────────────────────────────────


class TestDecisionReadiness:
    def _session(self, **kwargs):
        defaults = dict(
            conversation_id="conv-1",
            tenant_id="tenant-a",
            objective_id="goal-x",
            assessment={"state": "sufficiently_specified"},
            stage="compiled",
        )
        defaults.update(kwargs)
        return PlanningSession(**defaults)

    def _plan(self, **kwargs):
        defaults = dict(
            objective_id="goal-x",
            grounding_snapshot_id="gs-1",
            current_state_id="cur-1",
            desired_state_id="des-1",
            gap_model_id="gap-1",
            nodes=[{"node_id": "n1", "kind": "packet", "status": "active", "title": "work"}],
            workpacket_ids=["wp-1"],
        )
        defaults.update(kwargs)
        return ObjectivePlanRecord(**defaults)

    def test_missing_grounding_blocks(self):
        assessment = evaluate_decision_readiness(
            self._plan(grounding_snapshot_id=""), self._session()
        )
        assert assessment.state == DecisionReadiness.TECHNICAL_WORK_REMAINING.value
        assert not assessment.decision_package

    def test_clarification_blocks(self):
        assessment = evaluate_decision_readiness(
            self._plan(), self._session(stage="awaiting_clarification")
        )
        assert assessment.state == DecisionReadiness.CLARIFICATION_REQUIRED.value

    def test_ad_unknowns_do_not_block_but_contradictions_do(self):
        gaps_ok = GapAssessmentSnapshot(unknowns=["how many nodes exist"])
        ready = evaluate_decision_readiness(self._plan(), self._session(), gaps_ok)
        assert ready.state == DecisionReadiness.DECISION_READY.value
        assert any("investigation Tasks" in n for n in ready.non_blocking_notes)

        gaps_bad = GapAssessmentSnapshot(contradictions=[{"a": "b"}])
        blocked = evaluate_decision_readiness(self._plan(), self._session(), gaps_bad)
        assert blocked.state == DecisionReadiness.TECHNICAL_WORK_REMAINING.value

    def test_ready_package_separates_acceptance_from_execution(self):
        assessment = evaluate_decision_readiness(self._plan(), self._session())
        assert assessment.state == DecisionReadiness.DECISION_READY.value
        package = assessment.decision_package
        assert package["authorizes"] == "plan acceptance ONLY"
        assert "Wave 2" in package["does_not_authorize"]


# ── Test V: instruction compilation ──────────────────────────────────────────


class TestInstructionCompilation:
    def _request(self, **profile) -> InstructionCompilationRequest:
        return InstructionCompilationRequest(
            operation_identity={"operation": "plan_enhancement", "tenant_id": "tenant-a"},
            role_contract_id="role-impl-op",
            context_frame={"conversation_id": "conv-1"},
            evidence_refs=[{"evidence_id": "ev-1"}],
            model_profile={"model": "model-a", **profile},
            output_schema={"type": "object"},
            governance_constraints=["no scope change"],
            verification_requirements=["schema validation"],
        )

    def test_two_profiles_render_differently_identity_sealed(self):
        a = compile_instruction_package(self._request())
        b = compile_instruction_package(self._request(context_order="evidence_first"))
        assert [s["section"] for s in a.ordered_context] != [
            s["section"] for s in b.ordered_context
        ]
        assert a.operation_identity == b.operation_identity
        assert a.governance_constraints == b.governance_constraints
        assert a.package_hash and b.package_hash and a.package_hash != b.package_hash
        assert a.package_hash == a.compute_hash()  # sealed

    def test_compilation_failure_blocks_invocation(self):
        with pytest.raises(InstructionCompilationError):
            compile_instruction_package(
                InstructionCompilationRequest(
                    operation_identity={"operation": "x", "tenant_id": "t"},
                    model_profile={"model": "m"},
                    output_schema={},  # missing schema → no call
                )
            )

    def test_missing_tenant_blocks(self):
        with pytest.raises(InstructionCompilationError):
            compile_instruction_package(
                InstructionCompilationRequest(
                    operation_identity={"operation": "x"},
                    model_profile={"model": "m"},
                    output_schema={"type": "object"},
                )
            )


# ── Test Z addendum: gap artifact is snapshot-classified ─────────────────────


class TestGapAuthority:
    def test_gap_artifact_is_snapshot_not_strategic_gap(self, env):
        _, plan = _plan_objective(env)
        snapshot = env.store.get_gap_model(plan.gap_model_id)
        assert isinstance(snapshot, GapAssessmentSnapshot)
        from substrate.organism.strategic_gap_engine import Gap

        assert not isinstance(snapshot, Gap)
        assert hasattr(snapshot, "goal_refs")  # links to canonical Gaps/Goals
