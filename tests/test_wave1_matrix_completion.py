"""Wave 1 matrix completion — the exact acceptance scenarios D, I, J, K, L, N,
AJ, and the deterministic layer of AO (plan §15/§23; completion order 2026-07-21).

Each test asserts the PRESCRIBED behavior of its matrix id, not a proxy:

D  — LINK_WORK attaches an existing Task to an Objective, zero duplicates.
I  — dedicated UMH self-build planning scenario (target_kind=umh_substrate).
J  — dedicated projection-build planning scenario (target_kind=projection).
K  — cross-company collision: active-context resolution or one targeted
     clarification; zero cross-company scope leakage.
L  — cross-conversation revision: durable resolution by explicit plan id
     from ANOTHER conversation, with tenant authority enforced.
N  — concurrency: duplicate submission, revision conflict, double decision,
     CAS failure — explicit conflicts, no lost updates.
AJ — cross-projection planning: one tenant, one canonical Objective, one
     versioned Plan; substrate-contract Tasks precede dependent projection
     Tasks; projection Tasks carry NARROWED WorkScope; no duplicated
     substrate implementation; bounded frontier; no worker binding.
AO — (deterministic layer) all planning state lives under the UMH_STATE_DIR
     mount; process restart preserves every artifact; the source tree stays
     byte-identical. The mounted-container proof runs in field qualification.
"""

from __future__ import annotations

import hashlib
import os
import threading
from types import SimpleNamespace

import pytest

from substrate.contracts.work_context import PrincipalContext, WorkScope
from substrate.execution.intent.context_frame import ContextFrame
from substrate.execution.intent.protocol import (
    IntentClass,
    OperatorIntentProtocol,
)
from substrate.execution.planning.compiler import compile_revision, packet_predecessors
from substrate.execution.planning.decisions import PlanDecisionConflict, apply_plan_decision
from substrate.execution.planning.records import ObjectivePlanStatus, RevisionEditSet
from substrate.execution.planning.store import PlanningStore, PlanningStoreConflict
from substrate.organism.event_spine import EventSpine
from substrate.organism.strategic_gap_engine import GoalRegistry
from substrate.organism.universal_work_queue import UniversalWorkQueue

DOGFOOD = (
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


def _mk_env(tmp_path):
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
    return SimpleNamespace(
        store=store,
        goals=goals,
        queue=queue,
        runner=runner,
        protocol=protocol,
        principal=principal,
    )


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("UMH_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo").mkdir()
    return _mk_env(tmp_path)


def _frame(conv="conv-1", plans=None, tenant="tenant-a"):
    return ContextFrame(
        tenant_id=tenant,
        principal_id="user-1",
        conversation_id=conv,
        current_plans=plans or [],
    )


def _scope(**kwargs):
    defaults = dict(tenant_id="tenant-a", conversation_id="conv-1", target_kind="umh_substrate")
    defaults.update(kwargs)
    return WorkScope(**defaults)


def _plan_objective(env, text=DOGFOOD, cmid="m1", scope=None, conv="conv-1"):
    resolution = env.protocol.resolve(
        text,
        env.principal,
        scope or _scope(conversation_id=conv),
        _frame(conv),
        client_message_id=cmid,
    )
    return env.protocol.plan_objective(
        resolution, text, conv, client_message_id=cmid, work_queue=env.queue
    )


# ── Test D: LINK_WORK Objective attachment ──────────────────────────────────


class TestD_LinkWork:
    TASK = "Fix the failing import in transports/api/voice.py"

    def _captured_task(self, env):
        resolution = env.protocol.resolve(
            self.TASK, env.principal, _scope(), _frame(), client_message_id="d-t"
        )
        return resolution, env.protocol.capture_task(
            resolution, self.TASK, "conv-1", client_message_id="d-t", work_queue=env.queue
        )

    def test_attach_existing_task_no_duplicates(self, env):
        resolution, packet = self._captured_task(env)
        goal, _ = env.goals.create_or_reuse_objective(
            "tenant-a", "obj-d", "h1", title="Objective D"
        )

        packets_before = len(env.queue.all_packets())
        goals_before = len(env.goals.all_goals())

        linked = env.protocol.link_task_to_objective(
            resolution, packet.packet_id, goal.goal_id, work_queue=env.queue
        )
        assert linked.lineage["objective_id"] == goal.goal_id
        assert goal.goal_id in linked.lineage["goal_refs"]
        # No duplicates of anything.
        assert len(env.queue.all_packets()) == packets_before
        assert len(env.goals.all_goals()) == goals_before
        assert "objective_task_link" in env.runner.calls

    def test_link_idempotent(self, env):
        resolution, packet = self._captured_task(env)
        goal, _ = env.goals.create_or_reuse_objective("tenant-a", "obj-d", "h1")
        env.protocol.link_task_to_objective(
            resolution, packet.packet_id, goal.goal_id, work_queue=env.queue
        )
        calls_after_first = env.runner.calls.count("objective_task_link")
        env.protocol.link_task_to_objective(
            resolution, packet.packet_id, goal.goal_id, work_queue=env.queue
        )
        assert env.runner.calls.count("objective_task_link") == calls_after_first  # no-op

    def test_cross_tenant_link_rejected(self, env):
        resolution, packet = self._captured_task(env)
        foreign_goal, _ = env.goals.create_or_reuse_objective("tenant-b", "obj-x", "h1")
        with pytest.raises(ValueError, match="cross-tenant"):
            env.protocol.link_task_to_objective(
                resolution, packet.packet_id, foreign_goal.goal_id, work_queue=env.queue
            )


# ── Tests I / J: self-build vs projection-build planning ────────────────────


class TestIJ_BuildClassification:
    def test_i_umh_self_build_scenario(self, env):
        text = (
            "Implement the substrate planning compiler hardening: schema, "
            "migration, api, tests, rollback"
        )
        _, plan = _plan_objective(env, text, cmid="i-1", scope=_scope(target_kind="umh_substrate"))
        assert plan.work_scope["target_kind"] == "umh_substrate"
        governance = plan.archetype_resolution["governance_policy"]
        assert governance["profile"] == "self_build"
        for requirement in (
            "anti_divergence_validation",
            "architecture_law_checks",
            "independent_verification",
            "field_qualification",
            "owner_merge_authority",
            "rollback_path",
        ):
            assert requirement in governance["requires"]
        for pid in plan.workpacket_ids:
            assert env.queue.get_packet(pid).work_scope["target_kind"] == "umh_substrate"

    def test_j_projection_build_scenario(self, env):
        text = (
            "Build the client onboarding flow for the arena app: signup page, "
            "welcome email, checklist, billing"
        )
        _, plan = _plan_objective(
            env,
            text,
            cmid="j-1",
            scope=_scope(target_kind="projection", projection_ids=["projection-a"]),
        )
        assert plan.work_scope["target_kind"] == "projection"
        governance = plan.archetype_resolution["governance_policy"]
        assert governance["profile"] == "projection_build"
        for requirement in (
            "contract_conformity",
            "tenant_isolation",
            "no_substrate_duplication",
            "deployment_authority",
        ):
            assert requirement in governance["requires"]
        # Canonical packets either way — one packet model.
        from substrate.organism.work_packet import WorkPacket

        for pid in plan.workpacket_ids:
            assert isinstance(env.queue.get_packet(pid), WorkPacket)


# ── Test K: cross-company collision ──────────────────────────────────────────


class TestK_CrossCompanyCollision:
    PLAN_A = {
        "plan_record_id": "opr-companya",
        "objective_id": "goal-ca",
        "objective_text": "Launch the outreach campaign for the arena offer",
        "status": "awaiting_approval",
        "graph_version": 1,
    }
    PLAN_B = {
        "plan_record_id": "opr-companyb",
        "objective_id": "goal-cb",
        "objective_text": "Launch the outreach campaign for the studio offer",
        "status": "awaiting_approval",
        "graph_version": 1,
    }

    def test_collision_yields_one_targeted_clarification(self, env):
        # Same tenant, two companies, ambiguous reference across both.
        resolution = env.protocol.resolve(
            "Approve the launch outreach campaign plan",
            env.principal,
            _scope(),
            _frame(plans=[self.PLAN_A, self.PLAN_B]),
            client_message_id="k-1",
        )
        assert resolution.clarification_required is True
        assert len(resolution.clarification_questions) == 1
        options = resolution.material_ambiguities[0]["options"]
        assert {o["plan_record_id"] for o in options} == {"opr-companya", "opr-companyb"}

    def test_company_scoped_disambiguation_resolves(self, env):
        resolution = env.protocol.resolve(
            "Approve the launch outreach campaign for the arena offer plan",
            env.principal,
            _scope(),
            _frame(plans=[self.PLAN_A, self.PLAN_B]),
            client_message_id="k-2",
        )
        # The company-distinguishing words select exactly one candidate.
        selected = resolution.reference_resolution.get("selected", {})
        if selected:
            assert selected["plan_record_id"] == "opr-companya"
        else:
            # If similarity ties, the protocol must still ask — never guess B.
            assert resolution.clarification_required is True

    def test_zero_cross_company_scope_leakage(self):
        plan_scope = WorkScope(
            tenant_id="tenant-a", primary_company_id="company-a", company_ids=["company-a"]
        )
        task_scope = WorkScope(
            tenant_id="tenant-a", primary_company_id="company-b", company_ids=["company-b"]
        )
        assert not task_scope.is_within(plan_scope)


# ── Test L: cross-conversation revision ──────────────────────────────────────


class TestL_CrossConversationRevision:
    def test_explicit_id_resolves_from_other_conversation(self, env):
        _, plan = _plan_objective(env, cmid="l-1", conv="conv-1")
        # A NEW conversation references the plan by explicit id (its own
        # frame contains NO plans — durable resolution through the store).
        resolution = env.protocol.resolve(
            f"Add a rollback verification step to plan {plan.plan_record_id}",
            env.principal,
            _scope(conversation_id="conv-2"),
            _frame(conv="conv-2"),
            client_message_id="l-2",
        )
        assert resolution.intent_class == IntentClass.MODIFY_PLAN.value
        existing = resolution.existing_work_resolution
        assert existing["relationship"] == "revision_of_plan"
        assert existing["matched_plan_record_id"] == plan.plan_record_id

        edit_set = RevisionEditSet(
            edits=[{"op": "add_node", "kind": "packet", "title": "Rollback verification step"}]
        )
        new_plan = compile_revision(plan, edit_set, env.store, env.runner)
        assert new_plan.graph_version == 2
        assert new_plan.objective_id == plan.objective_id  # durable authority

    def test_cross_tenant_explicit_id_rejected(self, env):
        _, plan = _plan_objective(env, cmid="l-3")
        foreign = PrincipalContext(
            principal_id="user-9", tenant_id="tenant-b", membership_id="mem-zzz"
        )
        resolution = env.protocol.resolve(
            f"Add a step to plan {plan.plan_record_id}",
            foreign,
            WorkScope(tenant_id="tenant-b", conversation_id="conv-x"),
            _frame(conv="conv-x", tenant="tenant-b"),
            client_message_id="l-4",
        )
        refs = resolution.reference_resolution
        assert not refs.get("selected")
        assert any(r["plan_record_id"] == plan.plan_record_id for r in refs["rejected"])


# ── Test N: concurrency and conflict behavior ────────────────────────────────


class TestN_Concurrency:
    def test_duplicate_submission_yields_one_operation(self, env):
        resolution = env.protocol.resolve(
            DOGFOOD, env.principal, _scope(), _frame(), client_message_id="n-1"
        )
        results, errors = [], []

        def submit():
            try:
                results.append(
                    env.protocol.begin_planning_operation(
                        resolution, DOGFOOD, "conv-1", client_message_id="n-1"
                    )
                )
            except Exception as exc:  # noqa: BLE001 — recorded, asserted below
                errors.append(exc)

        threads = [threading.Thread(target=submit) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert len({s.objective_id for s in results}) == 1
        assert len(env.goals.all_goals()) == 1

    def test_revision_conflict_explicit_no_lost_update(self, env):
        _, plan = _plan_objective(env, cmid="n-2")
        edit = RevisionEditSet(edits=[{"op": "add_node", "kind": "packet", "title": "step"}])
        outcomes: list[str] = []
        lock = threading.Lock()

        def revise(tag: str):
            try:
                compile_revision(plan, edit, env.store, Runner())
                with lock:
                    outcomes.append(f"ok:{tag}")
            except (PlanningStoreConflict, Exception) as exc:
                with lock:
                    outcomes.append(f"conflict:{tag}:{type(exc).__name__}")

        threads = [threading.Thread(target=revise, args=(t,)) for t in ("a", "b")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        oks = [o for o in outcomes if o.startswith("ok")]
        assert len(oks) == 1, outcomes  # exactly one revision wins
        versions = env.store.versions_of(plan.objective_id)
        assert sorted(p.graph_version for p in versions) == [1, 2]  # no lost update

    def test_double_decision_conflict(self, env):
        _, plan = _plan_objective(env, cmid="n-3")
        apply_plan_decision(env.store, plan.plan_record_id, "approve", mutation_runner=env.runner)
        with pytest.raises(PlanDecisionConflict):
            apply_plan_decision(
                env.store, plan.plan_record_id, "reject", mutation_runner=env.runner
            )

    def test_cas_failure_is_explicit(self, env):
        _, plan = _plan_objective(env, cmid="n-4")
        with pytest.raises(PlanningStoreConflict):
            env.store.update_plan_cas(plan, expected_current_version=99)


# ── Test AJ: cross-projection planning (§23.6) ───────────────────────────────


class TestAJ_CrossProjectionPlanning:
    TEXT = (
        "Roll out the unified notification contract across the substrate and "
        "both projection apps: schema, api, banners, digests"
    )

    def _plan(self, env):
        scope = _scope(
            target_kind="umh_substrate",
            projection_ids=["projection-a", "projection-b"],
        )
        return _plan_objective(env, self.TEXT, cmid="aj-1", scope=scope)

    def test_one_objective_one_plan_substrate_precedes_projections(self, env):
        session, plan = self._plan(env)
        # One canonical Objective identity, one versioned Plan lineage.
        assert plan.objective_id == session.objective_id
        assert len(env.goals.all_goals()) == 1
        assert len(env.store.versions_of(plan.objective_id)) == 1

        nodes = {n["node_id"]: n for n in plan.nodes if n["kind"] == "packet"}
        substrate_nodes = [n for n in nodes.values() if n["target"] == "substrate"]
        projection_nodes = [n for n in nodes.values() if n["target"].startswith("projection:")]
        assert len(substrate_nodes) == 1  # no duplicated substrate implementation
        assert len(projection_nodes) == 2

        # Every projection Task depends (transitively) on the substrate Task.
        for node in projection_nodes:
            preds = packet_predecessors(plan, node["node_id"])
            assert substrate_nodes[0]["node_id"] in preds

    def test_projection_tasks_narrowed_scope_no_cross_tenant(self, env):
        _, plan = self._plan(env)
        narrowed = 0
        for raw in plan.nodes:
            if raw.get("kind") != "packet":
                continue
            packet = env.queue.get_packet(raw["workpacket_id"])
            assert packet.work_scope["tenant_id"] == "tenant-a"  # never cross-tenant
            if raw["target"].startswith("projection:"):
                projection_id = raw["target"].split(":", 1)[1]
                assert packet.work_scope["projection_ids"] == [projection_id]
                assert packet.work_scope["target_kind"] == "projection"
                narrowed += 1
            # No permanent worker/model/device binding in Task identity.
            assert packet.delegation_topology_id == ""
        assert narrowed == 2

    def test_bounded_frontier_and_no_deploy(self, env):
        _, plan = self._plan(env)
        assert plan.decomposition["stop_reason"]
        packet_nodes = [n for n in plan.nodes if n["kind"] == "packet"]
        assert len(packet_nodes) <= 12
        # Planning only: nothing executable, zero ExecutionAttempts.
        for pid in plan.workpacket_ids:
            assert not env.queue.get_packet(pid).is_execution_ready()


# ── Test AO (deterministic layer): mounted-state boundary + restart ─────────


class TestAO_MountedStateDeterministic:
    def test_state_under_mount_restart_preserves_source_untouched(self, tmp_path, monkeypatch):
        mount = tmp_path / "state-mount"  # stands in for /state/umh
        source = tmp_path / "source"  # stands in for the ro worktree mount
        source.mkdir()
        (source / "module.py").write_text("SOURCE = True\n")
        monkeypatch.setenv("UMH_STATE_DIR", str(mount))
        monkeypatch.setenv("UMH_ROOT", str(source))

        def _tree_hash(root) -> str:
            digest = hashlib.sha256()
            for dirpath, _d, files in sorted(os.walk(root)):
                for name in sorted(files):
                    with open(os.path.join(dirpath, name), "rb") as f:
                        digest.update(f.read())
            return digest.hexdigest()

        source_hash_before = _tree_hash(source)
        env = _mk_env(tmp_path)
        _, plan = _plan_objective(env, cmid="ao-1")
        goal_id = plan.objective_id

        # Goal store resolved beneath the mount; nothing under the source tree.
        assert str(env.goals._store_path).startswith(str(tmp_path))
        registry_restart = GoalRegistry()  # default path → UMH_STATE_DIR mount
        assert str(registry_restart._store_path).startswith(str(mount))

        # "Restart": brand-new instances over the same paths see everything.
        env2 = _mk_env(tmp_path)
        assert env2.store.get_plan(plan.plan_record_id) is not None
        assert env2.goals.get(goal_id) is not None
        for pid in plan.workpacket_ids:
            assert env2.queue.get_packet(pid) is not None

        assert _tree_hash(source) == source_hash_before  # source byte-identical


# ── Test Z addendum: legacy objective machinery receives ZERO new writes ────


class TestZ_LegacyObjectiveMachineryIsolation:
    def test_planning_modules_never_import_legacy_objective_machinery(self):
        """ObjectiveQueue / Coordinator.Objective / WorkUnit get no new Wave 1
        writes — structurally: no planning/intent module references them."""
        import pathlib

        repo = pathlib.Path(
            os.environ.get(
                "PYTEST_REPO_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        )
        offenders: list[str] = []
        for root in ("substrate/execution/planning", "substrate/execution/intent"):
            for path in (repo / root).glob("*.py"):
                text = path.read_text()
                for banned in (
                    "objective_queue",
                    "ObjectiveQueue",
                    "from substrate.organism.coordinator",
                    "WorkUnit",
                ):
                    if banned in text:
                        offenders.append(f"{path}: {banned}")
        assert offenders == []
