"""Plan compiler — grounded states → versioned plan → canonical WorkPackets.

Plan §6 (Wave 1). The deterministic spine of planning composition:

    GroundingSnapshot → CurrentStateRecord / DesiredStateRecord /
    GapAssessmentSnapshot (kept separate by construction)
    → WorkArchetypeResolution (+ optional DevelopmentPlanningProfile)
    → ObjectivePlanRecord (Kahn-validated DAG, bounded decomposition,
      explicit frontier — NEVER a giant flat graph)
    → canonical WorkPackets (via UniversalWorkQueue lifecycle: DRAFTED →
      CLASSIFIED → PLANNED, never further; non-empty approval_gates)
    → DecisionReadinessAssessment.

Non-execution invariant: nothing this module produces is executable.
Packets top out at PLANNED with approval gates; ``is_execution_ready()`` is
False for every materialized packet; the orchestration drain cannot pick
them up. Plan acceptance later flips ONLY the plan record.

UMH substrate subsystem. Instance-agnostic. Deterministic-first — the only
model-call seam is instruction_compilation, and it is optional enhancement.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from substrate.contracts.work_context import (
    WorkLineageContext,
    WorkRequirements,
    WorkScope,
)
from substrate.execution.planning.archetypes import (
    WorkArchetypeResolution,
    resolve_archetype,
    validate_skill_requirements,
)
from substrate.execution.planning.dev_profile import build_development_profile
from substrate.execution.planning.readiness import (
    DecisionReadiness,
    evaluate_decision_readiness,
)
from substrate.execution.planning.records import (
    CurrentStateRecord,
    DesiredStateRecord,
    GapAssessmentSnapshot,
    GroundingSnapshot,
    ObjectivePlanNode,
    ObjectivePlanRecord,
    ObjectivePlanStatus,
    PlanningSession,
    PlanningStageMarker,
    RevisionEditSet,
)
from substrate.execution.planning.store import PlanningStore

logger = logging.getLogger(__name__)

COMPILE_MUTATION_NAME = "objective_plan_compile"
REVISE_MUTATION_NAME = "objective_plan_revise"

# Bounded decomposition (§6): a single plan never exceeds this many packet
# nodes — larger scales defer children instead of flattening.
PACKET_NODE_CAP = 12
_FRONTIER_CAP = 5  # actionable child objectives surfaced per larger-scale plan


class PlanCompilationError(RuntimeError):
    """Deterministic compilation failed — the plan is not created."""


# ── State derivation (current ≠ desired by construction) ─────────────────────


def derive_state_records(
    objective_text: str,
    snapshot: GroundingSnapshot,
    tenant_id: str = "",
    scope: WorkScope | None = None,
) -> tuple[CurrentStateRecord, DesiredStateRecord, GapAssessmentSnapshot]:
    """Derive the three planning records from evidence + the objective."""
    current = CurrentStateRecord(
        intent_id=snapshot.intent_id,
        grounding_snapshot_id=snapshot.grounding_snapshot_id,
    )
    for source in snapshot.sources:
        current.statements.append(
            {
                "statement": str(source.get("summary", ""))[:300],
                "evidence_ref": snapshot.evidence_ref(str(source.get("source", ""))),
                "epistemic_status": "observed" if source.get("status") == "ok" else "unknown",
            }
        )
    current.unknowns = list(snapshot.unknown_sources)

    desired = DesiredStateRecord(intent_id=snapshot.intent_id)
    desired.statements.append(
        {"statement": objective_text.strip()[:600], "source": "operator_objective"}
    )

    if current.current_state_id == desired.desired_state_id:  # impossible by id scheme
        raise PlanCompilationError("current and desired state records collided")

    gap_snapshot = GapAssessmentSnapshot(
        current_state_id=current.current_state_id,
        desired_state_id=desired.desired_state_id,
    )
    # Deterministic gap derivation: each legacy-pending subsystem probe and
    # each unknown becomes an explicit gap/unknown; the objective itself is
    # the umbrella transformation when evidence names nothing finer.
    for source in snapshot.sources:
        evidence = source.get("evidence", {}) if isinstance(source.get("evidence"), dict) else {}
        for name in evidence.get("legacy_pending", []) or []:
            gap_snapshot.gaps.append(
                {
                    "gap_key": f"gap-{name}",
                    "title": f"Migrate subsystem '{name}' to the runtime-state boundary",
                    "evidence_ref": snapshot.evidence_ref(str(source.get("source", ""))),
                    "dependencies": [],
                }
            )
    # Cross-projection objective (§23.6): scope declares 2+ projection
    # targets → one shared substrate-contract gap that every projection gap
    # depends on (substrate Tasks precede dependent projection Tasks), each
    # projection gap tagged for scope narrowing at materialization. No
    # duplicated substrate implementation.
    if scope is not None and len(scope.projection_ids) >= 2:
        substrate_key = "gap-substrate-contract"
        gap_snapshot.gaps.append(
            {
                "gap_key": substrate_key,
                "title": "Establish the shared substrate contract for this objective",
                "evidence_ref": "",
                "dependencies": [],
                "target": "substrate",
            }
        )
        for projection_id in scope.projection_ids:
            gap_snapshot.gaps.append(
                {
                    "gap_key": f"gap-projection-{projection_id}",
                    "title": f"Apply the objective in projection {projection_id}",
                    "evidence_ref": "",
                    "dependencies": [substrate_key],
                    "target": f"projection:{projection_id}",
                }
            )
    if not gap_snapshot.gaps:
        gap_snapshot.gaps.append(
            {
                "gap_key": "gap-objective",
                "title": objective_text.strip()[:160] or "Realize the stated objective",
                "evidence_ref": "",
                "dependencies": [],
            }
        )
    gap_snapshot.unknowns = list(snapshot.unknown_sources)
    if snapshot.truncated:
        gap_snapshot.assumptions.append(
            "grounding was budget-clipped — evidence beyond the budget not considered"
        )
    return current, desired, gap_snapshot


# ── Graph validation ─────────────────────────────────────────────────────────


def _kahn_validate(nodes: list[dict[str, Any]], edges: list[dict[str, str]]) -> None:
    """DAG check + orphan prevention. Raises PlanCompilationError."""
    node_ids = {n["node_id"] for n in nodes}
    indegree: dict[str, int] = {nid: 0 for nid in node_ids}
    adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for edge in edges:
        src, dst = edge.get("from", ""), edge.get("to", "")
        if src not in node_ids or dst not in node_ids:
            raise PlanCompilationError(f"edge references unknown node: {edge}")
        adjacency[src].append(dst)
        indegree[dst] += 1
    queue = [nid for nid, deg in indegree.items() if deg == 0]
    visited = 0
    while queue:
        nid = queue.pop()
        visited += 1
        for nxt in adjacency[nid]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if visited != len(node_ids):
        raise PlanCompilationError("plan graph contains a cycle")
    if len(node_ids) > 1:
        connected = {e.get("from") for e in edges} | {e.get("to") for e in edges}
        orphans = node_ids - connected
        if orphans:
            raise PlanCompilationError(f"orphan nodes with no edges: {sorted(orphans)}")


def packet_predecessors(plan: ObjectivePlanRecord, node_id: str) -> list[str]:
    """Packet-node predecessors with transitive closure through non-packet
    nodes — the ONLY dependency translation packets receive."""
    by_id = {n["node_id"]: n for n in plan.nodes}
    incoming: dict[str, list[str]] = {}
    for edge in plan.edges:
        incoming.setdefault(edge["to"], []).append(edge["from"])
    result: list[str] = []
    stack = list(incoming.get(node_id, []))
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        node = by_id.get(current)
        if node is None:
            continue
        if node.get("kind") == "packet":
            result.append(current)
        else:
            stack.extend(incoming.get(current, []))
    return sorted(result)


# ── Plan compilation ─────────────────────────────────────────────────────────


def compile_plan(
    session: PlanningSession,
    scope: WorkScope,
    planning_scale: str,
    current: CurrentStateRecord,
    desired: DesiredStateRecord,
    gap_snapshot: GapAssessmentSnapshot,
    grounding_snapshot_id: str,
    archetype: WorkArchetypeResolution,
) -> ObjectivePlanRecord:
    """Compile the versioned plan record. Deterministic; raises on violation."""
    if not session.objective_id:
        raise PlanCompilationError("session has no canonical objective_id — cannot compile")
    scope.validate()

    plan = ObjectivePlanRecord(
        objective_id=session.objective_id,
        status=ObjectivePlanStatus.DRAFT.value,
        conversation_id=session.conversation_id,
        message_id=session.message_id,
        client_message_id=session.client_message_id,
        intent_id=session.intent_id,
        grounding_snapshot_id=grounding_snapshot_id,
        current_state_id=current.current_state_id,
        desired_state_id=desired.desired_state_id,
        gap_model_id=gap_snapshot.gap_model_id,
        objective_text=session.objective_text,
        work_scope=scope.to_dict(),
        planning_scale=planning_scale,
        archetype_resolution=archetype.to_dict(),
    )

    gaps = list(gap_snapshot.gaps)
    deferred: list[dict[str, Any]] = []
    stop_reason = "all gaps materialized as Tasks"
    if planning_scale in ("program_objective", "portfolio_objective", "institution_objective"):
        # Larger scales keep a bounded actionable frontier; the rest become
        # deferred child objectives — never a giant flat graph.
        frontier = gaps[:_FRONTIER_CAP]
        for gap in gaps[_FRONTIER_CAP:]:
            deferred.append({"title": gap["title"], "gap_key": gap["gap_key"]})
        gaps = frontier
        stop_reason = (
            f"scale {planning_scale}: bounded frontier of {_FRONTIER_CAP}; "
            f"{len(deferred)} child objective(s) deferred"
        )
    elif len(gaps) > PACKET_NODE_CAP:
        for gap in gaps[PACKET_NODE_CAP:]:
            deferred.append({"title": gap["title"], "gap_key": gap["gap_key"]})
        gaps = gaps[:PACKET_NODE_CAP]
        stop_reason = f"packet-node cap {PACKET_NODE_CAP} reached; remainder deferred"

    lane = archetype.archetype_id or "work"
    plan.lanes = [lane, "verification"]
    packet_nodes: list[ObjectivePlanNode] = []
    for gap in gaps:
        node = ObjectivePlanNode(
            kind="packet",
            title=gap["title"][:160],
            lane=lane,
            evidence_refs=[gap.get("evidence_ref", "")] if gap.get("evidence_ref") else [],
            gap_id=gap["gap_key"],
            target=gap.get("target", ""),
        )
        packet_nodes.append(node)
        plan.nodes.append(node.to_dict())

    verification = ObjectivePlanNode(
        kind="verification",
        title="Verify objective outcomes against desired state",
        lane="verification",
        depends_on=[n.node_id for n in packet_nodes],
    )
    plan.nodes.append(verification.to_dict())
    milestone = ObjectivePlanNode(
        kind="milestone",
        title="Objective outcome accepted",
        lane="verification",
        depends_on=[verification.node_id],
    )
    plan.nodes.append(milestone.to_dict())

    for node in packet_nodes:
        plan.edges.append({"from": node.node_id, "to": verification.node_id})
    plan.edges.append({"from": verification.node_id, "to": milestone.node_id})
    # Gap-declared dependencies become packet→packet edges (predecessor-only).
    key_to_node = {n.gap_id: n.node_id for n in packet_nodes}
    for gap in gaps:
        for dep_key in gap.get("dependencies", []):
            if dep_key in key_to_node and dep_key != gap["gap_key"]:
                plan.edges.append({"from": key_to_node[dep_key], "to": key_to_node[gap["gap_key"]]})

    _kahn_validate(plan.nodes, plan.edges)

    plan.decomposition = {
        "decomposition_depth": 1,
        "decomposition_budget": PACKET_NODE_CAP,
        "decomposition_frontier": [n.title for n in packet_nodes],
        "deferred_child_objectives": deferred,
        "unresolved_branches": list(gap_snapshot.unknowns),
        "stop_reason": stop_reason,
    }
    return plan


# ── Packet materialization (canonical, non-executable) ──────────────────────


def materialize_packets(
    plan: ObjectivePlanRecord,
    scope: WorkScope,
    archetype: WorkArchetypeResolution,
    session: PlanningSession,
    work_queue: Any,
) -> list[str]:
    """Materialize each active packet node as one canonical WorkPacket.

    Non-execution invariant: DRAFTED → CLASSIFIED → PLANNED and NO further;
    approval_gates are always non-empty; is_execution_ready() must be False.
    """
    from substrate.organism.work_packet import PacketLifecycleStatus, WorkPacket

    requirement_gaps = validate_skill_requirements(
        archetype.required_skill_refs,
        _load_role(archetype.default_role_contract_id),
        archetype.verification_role_contract_id,
    )
    requirements = WorkRequirements(
        work_archetype_ref=f"{archetype.archetype_id}@v{archetype.archetype_version}",
        required_skill_refs=[dict(r) for r in archetype.required_skill_refs],
        environment_requirements={"class": archetype.environment_class},
        governance_requirements=dict(archetype.governance_policy),
        independent_verification_role_refs=[archetype.verification_role_contract_id],
        proof_contract=dict(archetype.proof_contract),
    )

    packet_ids: list[str] = []
    for index, raw in enumerate(plan.nodes):
        if raw.get("kind") != "packet" or raw.get("status") != "active":
            continue
        lineage = WorkLineageContext(
            goal_refs=[plan.objective_id],
            objective_id=plan.objective_id,
            plan_record_id=plan.plan_record_id,
            decomposition_level=1,
            end_state_contribution=raw.get("title", ""),
            originating_intent_id=plan.intent_id,
            originating_conversation_id=plan.conversation_id,
        )
        # §23.6: projection-target nodes get a NARROWED WorkScope (that one
        # projection, target_kind=projection); substrate nodes keep the plan
        # scope. Never a cross-tenant scope.
        node_scope = scope
        node_target = raw.get("target", "")
        if node_target.startswith("projection:"):
            projection_id = node_target.split(":", 1)[1]
            node_scope = WorkScope.from_dict(scope.to_dict())
            node_scope.projection_ids = [projection_id]
            node_scope.target_kind = "projection"
        packet = WorkPacket(
            title=raw.get("title", ""),
            # user_intent must be UNIQUE per node: UniversalWorkQueue dedupes
            # ingests by user_intent, and a shared objective text would
            # collapse a multi-Task plan into one packet (caught by test AJ).
            user_intent=f"{raw.get('title', '')[:160]} — {plan.objective_text[:120]}",
            desired_end_state=raw.get("title", ""),
            intent_summary=f"{archetype.archetype_id} node of plan {plan.plan_record_id}",
            domain=archetype.archetype_id,
            source_type="objective_plan",
            source_id=plan.plan_record_id,
            source_evidence=[
                {
                    "type": "plan_node",
                    "node_id": raw.get("node_id", ""),
                    "evidence_refs": raw.get("evidence_refs", []),
                }
            ],
            risk_class="low",
            priority=60,
            required_role_contracts=[archetype.default_role_contract_id],
            required_workflows=[archetype.workflow_template],
            required_tools=list(archetype.tool_policy),
            approval_gates=["execution_authorization_required"],  # never empty
            validation_plan="verification node of the owning plan",
            output_contracts=[f"contributes: {raw.get('title', '')[:120]}"],
            work_scope=node_scope.to_dict(),
            lineage=lineage.to_dict(),
            requirements=requirements.to_dict(),
        )
        if requirement_gaps:
            packet.blockers = [f"requirement gap: {g}" for g in requirement_gaps]
        work_queue.ingest_work_packet(packet)
        work_queue.update_packet_status(
            packet.packet_id, PacketLifecycleStatus.CLASSIFIED, "plan compiled"
        )
        work_queue.update_packet_status(
            packet.packet_id,
            PacketLifecycleStatus.PLANNED,
            "materialized from approved-pending plan — execution NOT authorized",
        )
        raw["workpacket_id"] = packet.packet_id
        packet_ids.append(packet.packet_id)
        _ = index

    plan.workpacket_ids = packet_ids
    return packet_ids


def _load_role(role_contract_id: str) -> Any:
    try:
        from substrate.organism.role_contracts import SEED_ROLE_CONTRACTS, RoleContract

        for seed in SEED_ROLE_CONTRACTS:
            if seed.get("role_id") == role_contract_id:
                return RoleContract.from_dict(seed)
    except Exception as exc:
        logger.debug("role contract load failed for %s: %s", role_contract_id, exc)
    return None


# ── Full composition pipeline (§22.2 stages after OBJECTIVE_RESOLVED) ────────


def compose_plan_for_session(
    session: PlanningSession,
    scope: WorkScope,
    planning_scale: str,
    snapshot: GroundingSnapshot,
    store: PlanningStore,
    work_queue: Any,
    mutation_runner: Callable[..., Any],
    event_emit: Callable[[str, dict[str, Any]], None] | None = None,
    dev_profile_enabled: bool | None = None,
) -> ObjectivePlanRecord:
    """Run compile → materialize → readiness as the recoverable unit of work.

    Idempotent: a session that already committed a plan version returns it
    unchanged (no duplicate plans/Tasks/events on retry).
    """
    if session.active_plan_record_id:
        existing = store.get_plan(session.active_plan_record_id)
        if existing is not None and session.operation_stage in (
            PlanningStageMarker.COMMITTED.value,
            PlanningStageMarker.DECISION_EVALUATED.value,
        ):
            return existing

    def _emit(event_type: str, data: dict[str, Any]) -> None:
        if event_emit is not None:
            try:
                event_emit(event_type, data)
            except Exception as exc:
                logger.debug("compose emit failed: %s", exc)

    try:
        current, desired, gap_snapshot = derive_state_records(
            session.objective_text, snapshot, tenant_id=scope.tenant_id, scope=scope
        )
        archetype = resolve_archetype(session.objective_text, scope)
        plan = compile_plan(
            session,
            scope,
            planning_scale,
            current,
            desired,
            gap_snapshot,
            snapshot.grounding_snapshot_id,
            archetype,
        )
        if dev_profile_enabled or (
            dev_profile_enabled is None and archetype.archetype_id == "development"
        ):
            profile = build_development_profile(
                session.objective_text,
                scope,
                governance_profile=str(archetype.governance_policy.get("profile", "")),
            )
            completeness = profile.assert_complete()
            if completeness:
                raise PlanCompilationError(f"development profile incomplete: {completeness[:3]}")
            plan.development_profile = profile.to_dict()

        def _write_plan() -> tuple[str, bool]:
            store.append_grounding(snapshot)
            store.append_current_state(current)
            store.append_desired_state(desired)
            store.append_gap_model(gap_snapshot)
            store.append_plan(plan)
            return (f"plan compiled: {plan.plan_record_id} v{plan.graph_version}", True)

        response = mutation_runner(
            mutation_name=COMPILE_MUTATION_NAME,
            intent=f"compile objective plan for: {session.objective_text[:80]}",
            execute_fn=_write_plan,
            source="plan_compiler",
            metadata={
                "session_id": session.session_id,
                "objective_id": session.objective_id,
                "tenant_id": scope.tenant_id,
            },
        )
        if not bool(getattr(response, "success", False)):
            raise PlanCompilationError(
                f"governed compile rejected: {getattr(response, 'output', '')}"
            )

        session.active_plan_record_id = plan.plan_record_id
        session.operation_stage = PlanningStageMarker.PLAN_COMPILED.value
        session.stage = "compiled"
        session.updated_at = time.time()
        store.update_session(session)
        _emit(
            "planning.plan_compiled",
            {
                "plan_record_id": plan.plan_record_id,
                "objective_id": plan.objective_id,
                "graph_version": plan.graph_version,
                "tenant_id": scope.tenant_id,
            },
        )

        # Task materialization writes (packet store + plan CAS) run INSIDE the
        # governed mutation, same as every other planning write — the packet
        # ingest is never an ungoverned side effect of a returned compile.
        def _materialize() -> tuple[str, bool]:
            materialize_packets(plan, scope, archetype, session, work_queue)
            store.update_plan_cas(plan, expected_current_version=plan.graph_version)
            return (f"{len(plan.workpacket_ids)} task(s) materialized (max PLANNED)", True)

        response = mutation_runner(
            mutation_name=COMPILE_MUTATION_NAME,
            intent=f"materialize tasks for plan {plan.plan_record_id}",
            execute_fn=_materialize,
            source="plan_compiler",
            metadata={
                "session_id": session.session_id,
                "plan_record_id": plan.plan_record_id,
                "tenant_id": scope.tenant_id,
            },
        )
        if not bool(getattr(response, "success", False)):
            raise PlanCompilationError(
                f"governed materialization rejected: {getattr(response, 'output', '')}"
            )
        requirement_gaps = validate_skill_requirements(
            archetype.required_skill_refs,
            _load_role(archetype.default_role_contract_id),
            archetype.verification_role_contract_id,
        )
        session.operation_stage = PlanningStageMarker.TASKS_MATERIALIZED.value
        session.updated_at = time.time()
        store.update_session(session)
        _emit(
            "planning.tasks_materialized",
            {
                "plan_record_id": plan.plan_record_id,
                "objective_id": plan.objective_id,
                "task_ids": list(plan.workpacket_ids),
                "tenant_id": scope.tenant_id,
            },
        )

        assessment = evaluate_decision_readiness(plan, session, gap_snapshot, requirement_gaps)
        plan.readiness_assessment = assessment.to_dict()
        if assessment.state == DecisionReadiness.DECISION_READY.value:
            plan.status = ObjectivePlanStatus.AWAITING_APPROVAL.value

        def _record_readiness() -> tuple[str, bool]:
            store.update_plan_cas(plan, expected_current_version=plan.graph_version)
            return (f"readiness recorded: {assessment.state}", True)

        response = mutation_runner(
            mutation_name=COMPILE_MUTATION_NAME,
            intent=f"record decision readiness for plan {plan.plan_record_id}",
            execute_fn=_record_readiness,
            source="plan_compiler",
            metadata={"plan_record_id": plan.plan_record_id, "tenant_id": scope.tenant_id},
        )
        if not bool(getattr(response, "success", False)):
            raise PlanCompilationError(
                f"governed readiness write rejected: {getattr(response, 'output', '')}"
            )
        session.operation_stage = PlanningStageMarker.DECISION_EVALUATED.value
        session.updated_at = time.time()
        store.update_session(session)
        _emit(
            "planning.decision_ready",
            {
                "plan_record_id": plan.plan_record_id,
                "objective_id": plan.objective_id,
                "readiness": assessment.state,
                "tenant_id": scope.tenant_id,
            },
        )

        session.operation_stage = PlanningStageMarker.COMMITTED.value
        session.updated_at = time.time()
        store.update_session(session)
        return plan
    except Exception as exc:
        session.operation_stage = PlanningStageMarker.FAILED.value
        session.operation_error = str(exc)
        session.updated_at = time.time()
        try:
            store.update_session(session)
        except Exception as store_exc:
            logger.error("failed to persist FAILED planning stage: %s", store_exc)
        raise


# ── Revision (append-only versions) ──────────────────────────────────────────


def compile_revision(
    plan: ObjectivePlanRecord,
    edit_set: RevisionEditSet,
    store: PlanningStore,
    mutation_runner: Callable[..., Any],
) -> ObjectivePlanRecord:
    """Apply a validated edit set as version v(n+1); v(n) → SUPERSEDED."""
    errors = edit_set.validate_ops()
    if errors:
        raise PlanCompilationError(f"invalid revision ops: {errors}")

    new_plan = ObjectivePlanRecord.from_dict(plan.to_dict())
    new_plan.plan_record_id = ObjectivePlanRecord().plan_record_id  # fresh id
    new_plan.graph_version = plan.graph_version + 1
    new_plan.supersedes_plan_record_id = plan.plan_record_id
    new_plan.status = ObjectivePlanStatus.DRAFT.value
    new_plan.created_at = time.time()
    new_plan.updated_at = time.time()

    by_id = {n["node_id"]: n for n in new_plan.nodes}
    for edit in edit_set.edits:
        op = edit.get("op")
        if op == "remove_node" and edit.get("node_id") in by_id:
            by_id[edit["node_id"]]["status"] = "removed"
            new_plan.edges = [
                e
                for e in new_plan.edges
                if e.get("from") != edit["node_id"] and e.get("to") != edit["node_id"]
            ]
        elif op == "add_node":
            node = ObjectivePlanNode(
                kind=edit.get("kind", "packet"),
                title=edit.get("title", ""),
                lane=edit.get("lane", new_plan.lanes[0] if new_plan.lanes else ""),
                depends_on=list(edit.get("depends_on", [])),
            )
            new_plan.nodes.append(node.to_dict())
            by_id[node.node_id] = new_plan.nodes[-1]
            for dep in node.depends_on:
                if dep in by_id:
                    new_plan.edges.append({"from": dep, "to": node.node_id})
            if not node.depends_on and node.kind == "packet":
                # Orphan prevention: an unwired packet node still feeds the
                # plan's verification node.
                verification = next(
                    (
                        n
                        for n in new_plan.nodes
                        if n.get("kind") == "verification" and n.get("status") == "active"
                    ),
                    None,
                )
                if verification is not None:
                    new_plan.edges.append({"from": node.node_id, "to": verification["node_id"]})
        elif op == "add_edge":
            new_plan.edges.append({"from": edit.get("from", ""), "to": edit.get("to", "")})
        elif op == "remove_edge":
            new_plan.edges = [
                e
                for e in new_plan.edges
                if not (e.get("from") == edit.get("from") and e.get("to") == edit.get("to"))
            ]
        elif op == "retitle" and edit.get("node_id") in by_id:
            by_id[edit["node_id"]]["title"] = edit.get("title", "")
        elif op == "move_lane" and edit.get("node_id") in by_id:
            by_id[edit["node_id"]]["lane"] = edit.get("lane", "")

    active_nodes = [n for n in new_plan.nodes if n.get("status") == "active"]
    _kahn_validate(
        active_nodes,
        [
            e
            for e in new_plan.edges
            if any(n["node_id"] == e.get("from") for n in active_nodes)
            and any(n["node_id"] == e.get("to") for n in active_nodes)
        ],
    )

    def _write() -> tuple[str, bool]:
        store.append_revision_cas(new_plan, plan, plan.graph_version)
        return (f"plan revised: v{new_plan.graph_version}", True)

    response = mutation_runner(
        mutation_name=REVISE_MUTATION_NAME,
        intent=f"revise plan {plan.plan_record_id} → v{new_plan.graph_version}",
        execute_fn=_write,
        source="plan_compiler",
        metadata={"plan_record_id": plan.plan_record_id, "objective_id": plan.objective_id},
    )
    if not bool(getattr(response, "success", False)):
        raise PlanCompilationError(f"governed revision rejected: {getattr(response, 'output', '')}")
    return new_plan


__all__ = [
    "COMPILE_MUTATION_NAME",
    "PACKET_NODE_CAP",
    "REVISE_MUTATION_NAME",
    "PlanCompilationError",
    "compile_plan",
    "compile_revision",
    "compose_plan_for_session",
    "derive_state_records",
    "materialize_packets",
    "packet_predecessors",
]
