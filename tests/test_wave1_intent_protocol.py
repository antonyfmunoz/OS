"""Wave 1 canonical Operator Intent Protocol tests.

Covers: test A (communication-only, zero artifacts), classification +
planning-scale determinism, test G (ambiguous reference → one targeted
clarification), test C core (restatement resolves existing work, alternatives
by confidence), test P (work mutations fail closed without identity), test AL
(operation idempotency vs objective reuse), test AM/AF core (planning
unit-of-work recovery — no duplicates, Goal stays DRAFT), test AN (zero legacy
IntentLoop mutation calls), test AC core (one correlation chain, no duplicate
creation events), source correspondence (test U core), claim-sensitive
grounding adjudication, and EvidenceRef grounding projection.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from substrate.contracts.work_context import (
    EpistemicStatus,
    EvidenceRef,
    PrincipalContext,
    WorkAuthorityError,
    WorkScope,
)
from substrate.execution.intent.context_frame import ContextFrame, build_context_frame
from substrate.execution.intent.correspondence import (
    adjudicate_claim,
    resolve_source_correspondence,
)
from substrate.execution.intent.protocol import (
    DecisionRequirement,
    IntentClass,
    OperatorIntentProtocol,
    PlanningScale,
    planning_operation_key,
)
from substrate.execution.planning.records import PlanningStageMarker
from substrate.execution.planning.store import PlanningStore
from substrate.organism.event_spine import EventSpine
from substrate.organism.strategic_gap_engine import GoalRegistry, GoalStatus

DOGFOOD_OBJECTIVE = (
    "Migrate the remaining nine legacy runtime subsystems under data/umh "
    "to the runtime-state boundary: heartbeats, queues, snapshots, journals, "
    "receipts, consent_grants, sessions, traces, approvals"
)


class RunnerSpy:
    """Governed-mutation runner test double. Records every mutation name."""

    def __init__(
        self, fail_names: tuple[str, ...] = (), reject_after_execute: tuple[str, ...] = ()
    ):
        self.calls: list[str] = []
        self._fail_names = fail_names
        self._reject_after = reject_after_execute

    def __call__(self, mutation_name, intent, execute_fn, source="", metadata=None):
        self.calls.append(mutation_name)
        if mutation_name in self._fail_names:
            raise RuntimeError(f"injected failure for {mutation_name}")
        output, ok = execute_fn()
        if mutation_name in self._reject_after:
            return SimpleNamespace(
                success=False, output="injected post-execute rejection", envelope_id="env-x"
            )
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
    spine = EventSpine()
    runner = RunnerSpy()
    protocol = OperatorIntentProtocol(
        store=store, goal_registry=goals, event_spine=spine, mutation_runner=runner
    )
    principal = PrincipalContext(
        principal_id="user-1", tenant_id="tenant-a", membership_id="mem-abc123"
    )
    scope = WorkScope(tenant_id="tenant-a", conversation_id="conv-1")
    return SimpleNamespace(
        store=store,
        goals=goals,
        spine=spine,
        runner=runner,
        protocol=protocol,
        principal=principal,
        scope=scope,
        tmp=tmp_path,
    )


def _frame(conversation_id: str = "conv-1", plans: list | None = None) -> ContextFrame:
    return ContextFrame(
        tenant_id="tenant-a",
        principal_id="user-1",
        conversation_id=conversation_id,
        current_plans=plans or [],
    )


def _resolve(env, text: str, frame: ContextFrame | None = None, cmid: str = "m1"):
    return env.protocol.resolve(
        text, env.principal, env.scope, frame or _frame(), client_message_id=cmid
    )


# ── Test A: communication-only ───────────────────────────────────────────────


class TestCommunicationOnly:
    def test_communicate_produces_zero_artifacts(self, env):
        resolution = _resolve(env, "Thanks, that looks great — appreciate it.")
        assert resolution.intent_class == IntentClass.COMMUNICATE.value
        assert resolution.planning_scale == PlanningScale.NONE.value
        assert resolution.decision_requirement == DecisionRequirement.NOT_REQUIRED.value
        assert not resolution.creates_work
        assert env.store.load_sessions() == []
        assert env.store.load_plans() == []
        assert env.goals.all_goals() == []
        # No mutation ever submitted for pure communication.
        assert env.runner.calls == []

    def test_query_state_produces_zero_artifacts(self, env):
        resolution = _resolve(env, "What's the status of the migration work?")
        assert resolution.intent_class == IntentClass.QUERY_STATE.value
        assert env.store.load_sessions() == []
        assert env.runner.calls == []


# ── Classification + scale determinism ───────────────────────────────────────


class TestClassification:
    def test_atomic_task(self, env):
        r = _resolve(env, "Fix the failing import in transports/api/voice.py")
        assert r.intent_class == IntentClass.CREATE_TASK.value
        assert r.planning_scale == PlanningScale.ATOMIC_TASK.value
        assert r.decision_requirement == DecisionRequirement.NOT_REQUIRED.value

    def test_objective_dogfood(self, env):
        r = _resolve(env, DOGFOOD_OBJECTIVE)
        assert r.intent_class == IntentClass.CREATE_OBJECTIVE.value
        assert r.planning_scale == PlanningScale.PROJECT_OBJECTIVE.value
        assert r.decision_requirement == DecisionRequirement.REQUIRED.value

    def test_portfolio_scale(self, env):
        r = _resolve(
            env, "Build a company-wide onboarding objective covering all ventures and projections"
        )
        assert r.intent_class == IntentClass.CREATE_OBJECTIVE.value
        assert r.planning_scale == PlanningScale.PORTFOLIO_OBJECTIVE.value

    def test_provide_decision(self, env):
        plan = {
            "plan_record_id": "opr-abc",
            "objective_id": "goal-1",
            "objective_text": "Migrate subsystems",
            "status": "awaiting_approval",
            "graph_version": 1,
        }
        r = _resolve(env, "Approve that plan.", _frame(plans=[plan]))
        assert r.intent_class == IntentClass.PROVIDE_DECISION.value

    def test_provide_decision_resolves_pending_plan_from_fresh_conversation(self, env):
        """A pending-decision (awaiting_approval) plan is tenant-visible frame
        context regardless of conversation (§5 "pending Decisions"): "Approve
        that plan." in a NEW thread resolves the single decidable plan instead
        of asking which one (field run 20260722T205034Z regression)."""
        from substrate.execution.intent.context_frame import build_context_frame
        from substrate.execution.planning.records import ObjectivePlanRecord

        env.store.append_plan(
            ObjectivePlanRecord(
                plan_record_id="opr-pending1",
                objective_id="goal-p1",
                objective_text="Migrate the nine legacy subsystems",
                status="awaiting_approval",
                graph_version=2,
                conversation_id="conv-ORIGINAL",
                work_scope={"tenant_id": "tenant-a"},
            )
        )
        frame = build_context_frame("tenant-a", "user-1", "conv-FRESH", planning_store=env.store)
        assert any(p.get("plan_record_id") == "opr-pending1" for p in frame.current_plans), (
            "pending-decision plan must enter a fresh conversation's frame"
        )
        r = _resolve(env, "Approve that plan.", frame, cmid="m-fresh-approve")
        assert r.intent_class == IntentClass.PROVIDE_DECISION.value
        assert not r.clarification_required, "single pending decision must not re-ask"
        assert r.reference_resolution["selected"]["plan_record_id"] == "opr-pending1"

    def test_request_execution(self, env):
        r = _resolve(env, "Run the plan now please")
        assert r.intent_class == IntentClass.REQUEST_EXECUTION.value

    def test_cancel_work(self, env):
        plan = {
            "plan_record_id": "opr-abc",
            "objective_id": "goal-1",
            "objective_text": "Migrate subsystems",
            "status": "approved",
            "graph_version": 1,
        }
        r = _resolve(env, "Cancel that plan", _frame(plans=[plan]))
        assert r.intent_class == IntentClass.CANCEL_WORK.value

    def test_deterministic_same_input_same_class(self, env):
        a = _resolve(env, DOGFOOD_OBJECTIVE, cmid="m1")
        b = _resolve(env, DOGFOOD_OBJECTIVE, cmid="m1")
        assert a.intent_class == b.intent_class
        assert a.planning_scale == b.planning_scale
        assert a.correlation_id == b.correlation_id


# ── Test G: ambiguous reference ──────────────────────────────────────────────


class TestAmbiguousReference:
    PLAN_A = {
        "plan_record_id": "opr-aaa",
        "objective_id": "goal-a",
        "objective_text": "Migrate voice runtime subsystems",
        "status": "awaiting_approval",
        "graph_version": 1,
    }
    PLAN_B = {
        "plan_record_id": "opr-bbb",
        "objective_id": "goal-b",
        "objective_text": "Migrate discord runtime subsystems",
        "status": "awaiting_approval",
        "graph_version": 1,
    }

    def test_two_candidates_one_targeted_clarification(self, env):
        r = _resolve(
            env,
            "Approve the migrate runtime subsystems plan",
            _frame(plans=[self.PLAN_A, self.PLAN_B]),
        )
        assert r.clarification_required is True
        assert len(r.clarification_questions) == 1
        assert "which plan" in r.clarification_questions[0]["question"].lower()

    def test_single_live_plan_resolves_without_clarification(self, env):
        r = _resolve(env, "Approve that plan.", _frame(plans=[self.PLAN_A]))
        assert r.clarification_required is False
        assert r.reference_resolution["selected"]["plan_record_id"] == "opr-aaa"

    def test_vague_reference_with_nothing_matching(self, env):
        r = _resolve(env, "Cancel it", _frame(plans=[]))
        assert r.clarification_required is True
        assert len(r.clarification_questions) == 1


# ── Test C core: duplicate detection ─────────────────────────────────────────


class TestExistingWorkResolution:
    LIVE_PLAN = {
        "plan_record_id": "opr-live",
        "objective_id": "goal-live",
        "objective_text": DOGFOOD_OBJECTIVE,
        "status": "awaiting_approval",
        "graph_version": 1,
    }

    def test_restatement_resolves_existing_not_new(self, env):
        r = _resolve(env, DOGFOOD_OBJECTIVE, _frame(plans=[self.LIVE_PLAN]))
        assert r.existing_work_resolution["relationship"] == "restatement_of_existing"
        assert r.existing_work_resolution["matched_plan_record_id"] == "opr-live"
        assert not r.creates_work

    def test_alternatives_ranked_by_confidence(self, env):
        similar = {
            **self.LIVE_PLAN,
            "plan_record_id": "opr-sim",
            "objective_id": "goal-sim",
            "objective_text": "Migrate the legacy runtime subsystems to the boundary",
        }
        r = _resolve(env, DOGFOOD_OBJECTIVE, _frame(plans=[similar, self.LIVE_PLAN]))
        alts = r.existing_work_resolution["alternatives"]
        assert len(alts) >= 2
        assert alts[0]["confidence"] >= alts[1]["confidence"]

    def test_revision_verbs_yield_modify_plan(self, env):
        r = _resolve(
            env, "Add a rollback verification step to the plan", _frame(plans=[self.LIVE_PLAN])
        )
        assert r.intent_class == IntentClass.MODIFY_PLAN.value
        assert r.existing_work_resolution["relationship"] == "revision_of_plan"

    def test_unrelated_objective_is_new_work(self, env):
        r = _resolve(
            env,
            "Ship a customer referral rewards program for the arena product",
            _frame(plans=[self.LIVE_PLAN]),
        )
        assert r.intent_class == IntentClass.CREATE_OBJECTIVE.value
        assert r.existing_work_resolution["relationship"] == "new_work"


# ── Test P: fail-closed identity ─────────────────────────────────────────────


class TestFailClosedIdentity:
    def test_work_mutation_without_membership_fails_closed(self, env):
        resolution = _resolve(env, DOGFOOD_OBJECTIVE)
        resolution.principal_context = PrincipalContext(
            principal_id="user-1", tenant_id="tenant-a", membership_id=""
        ).to_dict()
        with pytest.raises(WorkAuthorityError):
            env.protocol.begin_planning_operation(
                resolution, DOGFOOD_OBJECTIVE, "conv-1", client_message_id="m1"
            )
        assert env.store.load_sessions() == []
        assert env.goals.all_goals() == []

    def test_communication_needs_no_identity(self, env):
        anonymous = PrincipalContext()
        r = env.protocol.resolve(
            "hello there", anonymous, WorkScope(tenant_id="tenant-a"), _frame()
        )
        assert r.intent_class == IntentClass.COMMUNICATE.value


# ── Tests AL / AM / AC: unit of work, idempotency, attribution ───────────────


class TestPlanningUnitOfWork:
    def test_operation_creates_session_and_canonical_objective(self, env):
        resolution = _resolve(env, DOGFOOD_OBJECTIVE)
        session = env.protocol.begin_planning_operation(
            resolution, DOGFOOD_OBJECTIVE, "conv-1", client_message_id="m1"
        )
        assert session.objective_id.startswith("goal-")
        assert session.operation_stage == PlanningStageMarker.OBJECTIVE_RESOLVED.value
        assert session.tenant_id == "tenant-a"
        goal = env.goals.get(session.objective_id)
        assert goal is not None
        assert goal.status == GoalStatus.DRAFT
        assert "objective_goal_write" in env.runner.calls
        assert "objective_plan_assess" in env.runner.calls

    def test_al_retry_reuses_exact_objective(self, env):
        resolution = _resolve(env, DOGFOOD_OBJECTIVE)
        s1 = env.protocol.begin_planning_operation(
            resolution, DOGFOOD_OBJECTIVE, "conv-1", client_message_id="m1"
        )
        s2 = env.protocol.begin_planning_operation(
            resolution, DOGFOOD_OBJECTIVE, "conv-1", client_message_id="m1"
        )
        assert s1.session_id == s2.session_id
        assert s1.objective_id == s2.objective_id
        assert len(env.store.load_sessions()) == 1
        assert len([g for g in env.goals.all_goals()]) == 1

    def test_al_similar_but_distinct_not_merged(self, env):
        r1 = _resolve(env, DOGFOOD_OBJECTIVE, cmid="m1")
        s1 = env.protocol.begin_planning_operation(
            r1, DOGFOOD_OBJECTIVE, "conv-1", client_message_id="m1"
        )
        other_text = DOGFOOD_OBJECTIVE + " and also add integrity verification"
        r2 = _resolve(env, other_text, cmid="m2")
        s2 = env.protocol.begin_planning_operation(r2, other_text, "conv-1", client_message_id="m2")
        assert s1.objective_id != s2.objective_id

    def test_am_failure_leaves_recoverable_state_and_valid_goal(self, env):
        # Governance rejects AFTER the goal write executed: session lands at
        # FAILED (recoverable), the created Goal remains in valid DRAFT state,
        # and retry reuses the same goal — no duplicates anywhere.
        env.protocol._mutation_runner = RunnerSpy(reject_after_execute=("objective_goal_write",))
        resolution = _resolve(env, DOGFOOD_OBJECTIVE)
        with pytest.raises(RuntimeError):
            env.protocol.begin_planning_operation(
                resolution, DOGFOOD_OBJECTIVE, "conv-1", client_message_id="m1"
            )

        sessions = env.store.load_sessions()
        assert len(sessions) == 1
        assert sessions[0].operation_stage == PlanningStageMarker.FAILED.value
        goals = env.goals.all_goals()
        assert len(goals) == 1 and goals[0].status == GoalStatus.DRAFT
        assert sessions[0].objective_id == ""  # never rendered as planned

        env.protocol._mutation_runner = RunnerSpy()
        retry = env.protocol.begin_planning_operation(
            resolution, DOGFOOD_OBJECTIVE, "conv-1", client_message_id="m1"
        )
        assert retry.operation_stage == PlanningStageMarker.OBJECTIVE_RESOLVED.value
        assert retry.objective_id == goals[0].goal_id
        assert len(env.goals.all_goals()) == 1
        assert len(env.store.load_sessions()) == 1

    def test_ac_correlation_chain_and_no_duplicate_creation_events(self, env):
        resolution = _resolve(env, DOGFOOD_OBJECTIVE)
        env.protocol.begin_planning_operation(
            resolution, DOGFOOD_OBJECTIVE, "conv-1", client_message_id="m1"
        )
        env.protocol.begin_planning_operation(
            resolution, DOGFOOD_OBJECTIVE, "conv-1", client_message_id="m1"
        )

        events = env.spine.recent(100)
        correlation = planning_operation_key("tenant-a", "conv-1", "m1")
        chain = [e for e in events if e.correlation_id == correlation]
        types = [e.event_type for e in chain]
        assert "planning.intent_resolved" in types
        assert types.count("planning.objective_created") == 1  # retry emits none
        created = next(e for e in chain if e.event_type == "planning.objective_created")
        for key in (
            "tenant_id",
            "principal_id",
            "membership_id",
            "conversation_id",
            "intent_id",
            "objective_id",
        ):
            assert created.data.get(key), key


# ── Test AN: zero legacy IntentLoop mutation calls ───────────────────────────


class TestLegacyIntentLoopIsolation:
    def test_no_legacy_mutation_calls_across_scenarios(self, env, monkeypatch):
        import substrate.execution.intent.loop as legacy_loop

        legacy_calls: list[str] = []
        monkeypatch.setattr(
            legacy_loop.IntentLoop,
            "submit",
            lambda self, *a, **k: legacy_calls.append("submit"),
        )
        monkeypatch.setattr(
            legacy_loop.IntentLoop,
            "decide",
            lambda self, *a, **k: legacy_calls.append("decide"),
        )

        scenarios = [
            "Thanks!",
            "What's the current runtime status?",
            "Fix the flaky voice test in tests/test_voice.py",
            DOGFOOD_OBJECTIVE,
            "Approve that plan.",
            "Cancel that plan",
        ]
        for i, text in enumerate(scenarios):
            resolution = _resolve(env, text, cmid=f"m{i}")
            if resolution.intent_class == IntentClass.CREATE_OBJECTIVE.value:
                env.protocol.begin_planning_operation(
                    resolution, text, "conv-1", client_message_id=f"m{i}"
                )

        assert legacy_calls == []
        legacy_names = [c for c in env.runner.calls if c.startswith("intent_loop")]
        assert legacy_names == []

    def test_read_adapter_is_marked_compatibility(self, env):
        from substrate.execution.intent.protocol import read_legacy_intent_loops

        rows = read_legacy_intent_loops(limit=5)
        for row in rows:
            assert row["source_type"] == "intent_loop"
            assert row["compatibility"] is True


# ── Test U core: source correspondence ───────────────────────────────────────


class TestSourceCorrespondence:
    def _github_review(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id="ev-gh-1",
            source_system="repository",
            source_object_type="review_comment",
            source_object_id="pr-42#rc-1",
            tenant_id="tenant-a",
            epistemic_status=EpistemicStatus.DECLARED.value,
            extraction_summary="voice websocket reconnect storm when token refresh fails on mobile safari",
        )

    def _email(self) -> EvidenceRef:
        return EvidenceRef(
            evidence_id="ev-mail-1",
            source_system="email",
            source_object_type="message",
            source_object_id="msg-777",
            tenant_id="tenant-a",
            epistemic_status=EpistemicStatus.DECLARED.value,
            extraction_summary="mobile safari voice reconnect storm — websocket token refresh failure reported by tester",
        )

    def test_same_finding_grouped_once(self, env):
        resolution = resolve_source_correspondence([self._github_review(), self._email()])
        assert len(resolution.groups) == 1
        assert set(resolution.groups[0]["member_evidence_ids"]) == {"ev-gh-1", "ev-mail-1"}

    def test_distinct_findings_not_merged(self):
        other = EvidenceRef(
            evidence_id="ev-other",
            source_system="email",
            tenant_id="tenant-a",
            extraction_summary="invoice branding footer misaligned in dark mode",
        )
        resolution = resolve_source_correspondence([self._github_review(), other])
        assert len(resolution.groups) == 2

    def test_cross_tenant_never_grouped(self):
        a = self._github_review()
        b = self._email()
        b.tenant_id = "tenant-b"
        resolution = resolve_source_correspondence([a, b])
        assert len(resolution.groups) == 2

    def test_canonical_entity_id_is_explicit_correspondence(self):
        a = EvidenceRef(
            evidence_id="e1",
            canonical_entity_id="finding-x",
            tenant_id="t1",
            extraction_summary="alpha",
        )
        b = EvidenceRef(
            evidence_id="e2",
            canonical_entity_id="finding-x",
            tenant_id="t1",
            extraction_summary="completely different words entirely",
        )
        resolution = resolve_source_correspondence([a, b])
        assert len(resolution.groups) == 1


# ── Claim-sensitive adjudication ─────────────────────────────────────────────


class TestGroundingAdjudication:
    RUNTIME = EvidenceRef(
        evidence_id="ev-rt",
        source_system="umh_runtime",
        epistemic_status=EpistemicStatus.OBSERVED.value,
        observed_at=100.0,
        extraction_summary="service responds on port 8091 with healthy status",
    )
    DOCS = EvidenceRef(
        evidence_id="ev-doc",
        source_system="docs",
        epistemic_status=EpistemicStatus.DECLARED.value,
        observed_at=200.0,
        extraction_summary="documentation says the service listens on port 8080",
    )
    CODE = EvidenceRef(
        evidence_id="ev-code",
        source_system="repository",
        epistemic_status=EpistemicStatus.OBSERVED.value,
        observed_at=150.0,
        extraction_summary="uvicorn bind configured for port 8091 in service entrypoint",
    )

    def test_running_behavior_prefers_runtime_observation(self):
        adjudication = adjudicate_claim(
            "which port is live", "running_behavior", [self.DOCS, self.RUNTIME]
        )
        assert adjudication.selected_evidence_ids[0] == "ev-rt"
        assert any(r["evidence_id"] == "ev-doc" for r in adjudication.rejected_evidence)

    def test_source_implementation_prefers_code(self):
        adjudication = adjudicate_claim(
            "what does the entrypoint bind", "source_implementation", [self.DOCS, self.CODE]
        )
        assert adjudication.selected_evidence_ids[0] == "ev-code"

    def test_no_global_ranking_for_unknown_claim_kind(self):
        adjudication = adjudicate_claim("misc", "some_new_kind", [self.DOCS, self.RUNTIME])
        assert "no global source ranking" in adjudication.authority_reasoning

    def test_empty_evidence_is_recorded_uncertainty(self):
        adjudication = adjudicate_claim("anything", "running_behavior", [])
        assert adjudication.unresolved_uncertainty


# ── EvidenceRef grounding projection ─────────────────────────────────────────


class TestGroundingEvidenceRefs:
    def test_snapshot_projects_to_typed_refs(self):
        from substrate.execution.planning.grounding import snapshot_to_evidence_refs
        from substrate.execution.planning.records import GroundingSnapshot

        snapshot = GroundingSnapshot(intent_id="i1", conversation_id="c1")
        snapshot.sources.append(
            {
                "source": "work_packets",
                "status": "ok",
                "summary": "3 packets active",
                "collected_at": 10.0,
            }
        )
        snapshot.unknown_sources.append("docker")
        refs = snapshot_to_evidence_refs(snapshot, tenant_id="tenant-a")
        by_id = {r["source_object_id"]: r for r in refs}
        assert by_id["work_packets"]["epistemic_status"] == EpistemicStatus.OBSERVED.value
        assert by_id["docker"]["epistemic_status"] == EpistemicStatus.UNKNOWN.value
        assert all(r["tenant_id"] == "tenant-a" for r in refs)


# ── ContextFrame bounds ──────────────────────────────────────────────────────


class TestContextFrame:
    def test_bounded_sections_record_truncation(self, env):
        frame = build_context_frame(
            "tenant-a",
            "user-1",
            "conv-1",
            recent_turns=[{"n": i} for i in range(40)],
            planning_store=env.store,
        )
        assert len(frame.recent_turns) == 12
        assert "recent_turns" in frame.truncated_sections

    def test_plan_section_from_store(self, env):
        from substrate.execution.planning.records import ObjectivePlanRecord

        env.store.append_plan(
            ObjectivePlanRecord(conversation_id="conv-1", objective_text="Migrate things")
        )
        frame = build_context_frame("tenant-a", "user-1", "conv-1", planning_store=env.store)
        assert len(frame.current_plans) == 1
        assert frame.current_plans[0]["objective_text"] == "Migrate things"
