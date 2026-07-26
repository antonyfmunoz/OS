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
    DecompositionMode,
    GroundingSnapshot,
    ObjectiveLane,
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
# Scales that keep a bounded actionable frontier and defer the remainder.
_LARGER_SCALES = ("program_objective", "portfolio_objective", "institution_objective")


class PlanCompilationError(RuntimeError):
    """Deterministic compilation failed — the plan is not created."""


# ── Caller-declared lane decomposition ───────────────────────────────────────


def _lane_gaps(lanes: list[Any]) -> list[dict[str, Any]]:
    """Turn a caller's declared lanes into gaps with resolved dependencies.

    Fail-closed on every malformed declaration: a bad decomposition must stop
    planning, never silently degrade to one umbrella Task (which is what the
    multi-lane protocol would then fail to satisfy at execution time).

    ``lane_key`` → ``gap-lane-<key>`` is the ONLY identity a caller influences.
    Node ids and packet ids remain minted by canonical materialization alone.
    """
    normalized: list[ObjectiveLane] = []
    for raw in lanes:
        lane = raw if isinstance(raw, ObjectiveLane) else ObjectiveLane.from_dict(dict(raw))
        # lane_key comes from arbitrary caller JSON; a non-string would escape
        # as a bare AttributeError from .strip(), which callers catching
        # PlanCompilationError never handle.
        if lane.lane_key is not None and not isinstance(lane.lane_key, str):
            raise PlanCompilationError(
                f"lane_key must be a string, got {type(lane.lane_key).__name__}"
            )
        key = (lane.lane_key or "").strip()
        if not key:
            raise PlanCompilationError("declared lane has no lane_key — refusing to compile")
        if lane.writable_path_scope is None:
            raise PlanCompilationError(
                f"lane {key!r} declares no writable_path_scope — an undeclared authority is "
                "never whole-repository permission"
            )
        # TYPE-CHECK the declaration. A bare string is the dangerous case: it is
        # iterable, so it silently becomes one-character "paths" ("app/main.py"
        # → ['a','p','p',…]) which are VALID relative paths and pass every
        # downstream check, yielding a Task whose scope is nonsense. A string
        # depends_on would likewise be iterated into single characters that
        # resolve to no lane.
        if isinstance(lane.writable_path_scope, (str, bytes)) or not isinstance(
            lane.writable_path_scope, (list, tuple)
        ):
            raise PlanCompilationError(
                f"lane {key!r} writable_path_scope must be a list of paths, got "
                f"{type(lane.writable_path_scope).__name__}"
            )
        if lane.depends_on is None:
            # JSON `null` plainly means "no dependencies" — normalize rather
            # than refusing a legitimate declaration.
            lane.depends_on = []
        if isinstance(lane.depends_on, (str, bytes)) or not isinstance(
            lane.depends_on, (list, tuple)
        ):
            raise PlanCompilationError(
                f"lane {key!r} depends_on must be a list of lane keys, got "
                f"{type(lane.depends_on).__name__}"
            )
        # Reject non-string ENTRIES rather than str()-coercing them: [1, 2]
        # would become writable paths "1" and "2", which are valid relative
        # paths and pass every downstream check — a Task with scope_declared=True
        # and a nonsense authority.
        non_strings = [p for p in lane.writable_path_scope if not isinstance(p, str)]
        if non_strings:
            raise PlanCompilationError(
                f"lane {key!r} writable_path_scope has non-string entries: {non_strings}"
            )
        bad_deps = [d for d in lane.depends_on if not isinstance(d, str)]
        if bad_deps:
            raise PlanCompilationError(
                f"lane {key!r} depends_on has non-string entries: {bad_deps}"
            )
        # Least privilege at the DECLARATION boundary, using the contract's own
        # validator — the same authority materialization enforces.
        probe = WorkRequirements()
        probe.declare_writable_paths([str(p) for p in lane.writable_path_scope])
        scope_errors = probe.validate_writable_path_scope()
        if scope_errors:
            raise PlanCompilationError(
                f"lane {key!r} declares an invalid writable_path_scope: {scope_errors}"
            )
        lane.lane_key = key
        normalized.append(lane)

    keys = [lane.lane_key for lane in normalized]
    duplicates = {k for k in keys if keys.count(k) > 1}
    if duplicates:
        raise PlanCompilationError(f"duplicate lane_key(s) declared: {sorted(duplicates)}")
    known = set(keys)

    gaps: list[dict[str, Any]] = []
    for lane in normalized:
        unknown = [d for d in lane.depends_on if d not in known]
        if unknown:
            raise PlanCompilationError(
                f"lane {lane.lane_key!r} depends on undeclared lane(s): {sorted(unknown)}"
            )
        if lane.lane_key in lane.depends_on:
            raise PlanCompilationError(f"lane {lane.lane_key!r} depends on itself")
        gaps.append(
            {
                "gap_key": f"gap-lane-{lane.lane_key}",
                "title": (lane.title or lane.lane_key)[:160],
                "evidence_ref": "",
                "dependencies": [f"gap-lane-{d}" for d in lane.depends_on],
                "writable_path_scope": [str(p) for p in lane.writable_path_scope],
                "semantic_label": lane.semantic_label,
            }
        )
    return gaps


# ── State derivation (current ≠ desired by construction) ─────────────────────


def derive_state_records(
    objective_text: str,
    snapshot: GroundingSnapshot,
    tenant_id: str = "",
    scope: WorkScope | None = None,
    writable_path_scope: list[str] | None = None,
    lanes: list[Any] | None = None,
) -> tuple[CurrentStateRecord, DesiredStateRecord, GapAssessmentSnapshot]:
    """Derive the three planning records from evidence + the objective.

    ``writable_path_scope`` is the objective-derived mutation authority for the
    Tasks this objective will materialize, worktree-relative and least-privilege.
    It is supplied by the CALLER (the surface that knows the objective's target
    workspace) — substrate never infers it from titles, ids, or a worker's diff.
    Every derived gap inherits it, the plan node carries it, and the compiler
    seeds it onto each materialized WorkPacket's contract. ``None`` means the
    caller declared no authority: materialization then fails closed rather than
    persisting a Task whose diff can never be verified.

    ``lanes`` is the caller's optional DECLARED decomposition (``ObjectiveLane``
    or dicts). When supplied it takes precedence over every other gap producer:
    the objective becomes one Task PER LANE, each carrying that lane's own
    least-privilege authority and its resolved dependencies, instead of the
    single umbrella Task the fallback below produces. Substrate still infers
    nothing — lanes are declared by the runtime that owns the workspace, the
    same seam that already declares ``writable_path_scope``.
    """
    declared_scope = None if writable_path_scope is None else [str(p) for p in writable_path_scope]
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
                    "writable_path_scope": declared_scope,
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
                "writable_path_scope": declared_scope,
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
                    "writable_path_scope": declared_scope,
                }
            )
    # ── THE ONE DECOMPOSITION-SELECTION POINT ────────────────────────────────
    # Everything appended above is the DERIVED candidate set. Exactly one
    # producer may own the executable decomposition of a Plan version; two
    # producers both claiming Task authority is what compiled 11 Tasks where
    # the protocol requires 4 (field run 20260726T193442Z, layer 11).
    #
    # This selection is deterministic and typed. It NEVER infers authority from
    # evidence contents, titles, regexes, or packet-id shapes, and it happens
    # BEFORE any bounding cap — a cap may protect boundedness, but it must
    # never decide which semantic owner wins or hide executable Tasks. (At
    # program_objective scale the frontier cap of 5 silently truncated the 7
    # evidence siblings and produced an accidentally-correct 4-node graph:
    # right answer, wrong reason, and unreliable at any other scale.)
    derived_gaps = list(gap_snapshot.gaps)
    if lanes:
        # DECLARED_EXCLUSIVE — the declared lane set is the COMPLETE executable
        # decomposition. Lanes are DECLARED by the runtime that owns the target
        # workspace, never inferred; dependencies resolve lane_key → gap_key
        # here, so a caller can never supply a node or packet id and thereby
        # mint identity outside canonical materialization.
        gap_snapshot.decomposition_mode = DecompositionMode.DECLARED_EXCLUSIVE.value
        gap_snapshot.gaps = _lane_gaps(lanes)
        # PRESERVE, never delete: the derived gaps remain first-class planning
        # evidence (inspectable, available to later planning) while creating
        # ZERO sibling Tasks.
        gap_snapshot.derived_evidence_gaps = derived_gaps
        if derived_gaps:
            gap_snapshot.assumptions.append(
                f"declared decomposition is exclusive for this plan version: "
                f"{len(derived_gaps)} evidence-derived gap(s) preserved as "
                f"non-executable planning evidence"
            )
    elif gap_snapshot.gaps:
        # DERIVED — no declaration; the evidence/gap compiler owns it.
        gap_snapshot.decomposition_mode = DecompositionMode.DERIVED.value
    else:
        # UMBRELLA_FALLBACK — neither produced anything actionable.
        gap_snapshot.decomposition_mode = DecompositionMode.UMBRELLA_FALLBACK.value
        gap_snapshot.gaps.append(
            {
                "gap_key": "gap-objective",
                "title": objective_text.strip()[:160] or "Realize the stated objective",
                "evidence_ref": "",
                "dependencies": [],
                "writable_path_scope": declared_scope,
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
        # Stamp the selected owner onto the PLAN VERSION so every later
        # producer of a version (notably compile_revision) can enforce it.
        decomposition_mode=gap_snapshot.decomposition_mode,
    )

    gaps = list(gap_snapshot.gaps)
    deferred: list[dict[str, Any]] = []
    stop_reason = "all gaps materialized as Tasks"
    # A caller-DECLARED decomposition is ATOMIC: materialize every lane or none.
    # The generic caps below defer trailing gaps as child objectives, which for
    # lanes silently deletes them — and if a lane and its dependency are cut
    # together, even the fail-closed dependency check cannot see it. A declared
    # graph that lost its independent-verification lane would compile clean.
    _is_lane = [str(g.get("gap_key", "")).startswith("gap-lane-") for g in gaps]
    _lane_gaps_declared = [g for g, lane in zip(gaps, _is_lane) if lane]
    # Under DECLARED_EXCLUSIVE the gap set IS the declared lane set (selection
    # already ran), so no reordering is needed to protect lanes from the cap —
    # there is nothing else in the list. The cap now only bounds a DERIVED
    # decomposition, and a declared set that exceeds it fails closed rather
    # than being silently trimmed.
    if _lane_gaps_declared:
        _cap = _FRONTIER_CAP if planning_scale in _LARGER_SCALES else PACKET_NODE_CAP
        # Compare the LANE count against the cap. A declared decomposition is
        # ATOMIC: materialize every lane or none. The cap bounds work; it must
        # never silently defer part of a declared graph (that is how a plan
        # loses its independent-verification lane and still compiles clean).
        if len(_lane_gaps_declared) > _cap:
            raise PlanCompilationError(
                f"declared decomposition has {len(_lane_gaps_declared)} lane(s) but the "
                f"{planning_scale} cap is {_cap} — refusing to silently defer lanes from "
                "an atomic caller-declared graph"
            )
        # Selection ran BEFORE this cap, so the executable set is EXACTLY the
        # declared lanes — no evidence siblings remain to order around. Assert
        # that invariant instead of re-deriving it: a non-lane gap surviving
        # here means a second producer re-entered the executable set after
        # selection, which is the layer-11 defect.
        _intruders = [g["gap_key"] for g, lane in zip(gaps, _is_lane) if not lane]
        if _intruders:
            raise PlanCompilationError(
                "declared decomposition is exclusive, but evidence-derived gap(s) "
                f"{_intruders} entered the executable set — a second producer is "
                "claiming Task authority for this plan version"
            )
    if planning_scale in _LARGER_SCALES:
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
        # The gap carries the OBJECTIVE-DERIVED writable-path authority; the node
        # is its planning-time owner and the compiler seeds it onto the packet's
        # WorkRequirements at materialization. A gap that declares no scope
        # produces a node with scope_declared=False, which fails materialization
        # closed rather than persisting a Task no diff can ever satisfy.
        declared_scope = gap.get("writable_path_scope")
        node = ObjectivePlanNode(
            kind="packet",
            title=gap["title"][:160],
            lane=lane,
            evidence_refs=[gap.get("evidence_ref", "")] if gap.get("evidence_ref") else [],
            gap_id=gap["gap_key"],
            target=gap.get("target", ""),
            writable_path_scope=[str(p) for p in (declared_scope or [])],
            scope_declared=declared_scope is not None,
            semantic_label=str(gap.get("semantic_label", "") or ""),
        )
        packet_nodes.append(node)

    # Resolve gap-level dependencies onto real node ids. Without this a declared
    # graph (C after A∧B, D after C) flattens into independent nodes and the
    # scheduler admits every Task at once — the dependency would be documented
    # but not enforced. Keyed by gap id, so identity stays compiler-minted.
    node_by_gap = {n.gap_id: n for n in packet_nodes}
    for gap, node in zip(gaps, packet_nodes):
        for dep_gap in gap.get("dependencies", []) or []:
            dep_node = node_by_gap.get(dep_gap)
            if dep_node is None:
                # A dependency on a gap that was deferred by the caps above
                # would silently unblock the dependent Task.
                raise PlanCompilationError(
                    f"gap {gap['gap_key']!r} depends on {dep_gap!r}, which materialized no node"
                )
            node.depends_on.append(dep_node.node_id)
    for node in packet_nodes:
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
    # Unknown/self references already failed closed during node resolution
    # above, so anything reaching here resolves; the guard stays as a belt-and-
    # braces check rather than a silent skip.
    key_to_node = {n.gap_id: n.node_id for n in packet_nodes}
    for gap in gaps:
        for dep_key in gap.get("dependencies", []):
            if dep_key == gap["gap_key"]:
                raise PlanCompilationError(f"gap {dep_key!r} depends on itself")
            if dep_key not in key_to_node:
                raise PlanCompilationError(
                    f"gap {gap['gap_key']!r} depends on {dep_key!r}, which materialized no node"
                )
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

    # PRE-VALIDATE every packet node's declared authority BEFORE any queue write.
    # Raising mid-loop left already-ingested packets behind (an orphan PLANNED
    # Task plus a mutated node["workpacket_id"]) because the queue write is not
    # rolled back by the governed mutation's failure. Validate first so a plan
    # with any undeclared/invalid node persists NOTHING.
    for raw in plan.nodes:
        if raw.get("kind") != "packet" or raw.get("status") != "active":
            continue
        if not raw.get("scope_declared"):
            raise PlanCompilationError(
                f"plan node {raw.get('node_id', '')!r} declares no writable_path_scope — "
                "refusing to materialize a Task with undeclared mutation authority"
            )
        probe = WorkRequirements()
        probe.declare_writable_paths([str(p) for p in (raw.get("writable_path_scope") or [])])
        probe_errors = probe.validate_writable_path_scope()
        if probe_errors:
            raise PlanCompilationError(
                f"plan node {raw.get('node_id', '')!r} has an invalid writable_path_scope: "
                f"{probe_errors}"
            )

    packet_ids: list[str] = []
    # node_id → materialized packet, so a second pass can translate plan-node
    # depends_on edges into WorkPacket.dependencies (packet_id edges). Without
    # this, dependency-aware scheduling silently never blocks (Wave 2 gap).
    packet_by_node_id: dict[str, WorkPacket] = {}
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
        # PER-NODE mutation authority (field run 20260725T230726Z, ninth layer).
        # `requirements` above is shared archetype metadata; the writable-path
        # scope is NOT shared — it is the node's own objective-derived authority
        # and must be seeded onto THIS packet's contract before persistence, so
        # every later reread (attempt, lease, package, dispatch, verification)
        # reads one canonical scope. A packet node that declares no scope fails
        # CLOSED here: persisting scope_declared=False produced a Task whose
        # every legitimate diff was unverifiable, and an empty/undeclared scope
        # must never be read as whole-repository permission.
        node_requirements = WorkRequirements.from_dict(requirements.to_dict())
        if not raw.get("scope_declared"):
            raise PlanCompilationError(
                f"plan node {raw.get('node_id', '')!r} declares no writable_path_scope — "
                "refusing to materialize a Task with undeclared mutation authority"
            )
        node_requirements.declare_writable_paths(
            [str(p) for p in (raw.get("writable_path_scope") or [])]
        )
        scope_errors = node_requirements.validate_writable_path_scope()
        if scope_errors:
            raise PlanCompilationError(
                f"plan node {raw.get('node_id', '')!r} has an invalid writable_path_scope: "
                f"{scope_errors}"
            )
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
            requirements=node_requirements.to_dict(),
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
        packet_by_node_id[raw.get("node_id", "")] = packet
        packet_ids.append(packet.packet_id)
        _ = index

    # Second pass: translate each packet node's predecessor packet-nodes into
    # WorkPacket.dependencies (packet_id edges). packet_predecessors() gives the
    # transitive-through-non-packet-nodes packet predecessors — the only
    # dependency translation packets receive. This is what makes the Wave 2
    # dependency-aware scheduler able to hold a fan-in Task until its
    # predecessors' attempts have succeeded. Forward edges are handled correctly
    # because every packet node already has its packet minted by now.
    deps_changed = False
    for node_id, packet in packet_by_node_id.items():
        pred_node_ids = packet_predecessors(plan, node_id)
        dep_packet_ids = [
            packet_by_node_id[p].packet_id for p in pred_node_ids if p in packet_by_node_id
        ]
        if dep_packet_ids and packet.dependencies != dep_packet_ids:
            packet.dependencies = dep_packet_ids
            deps_changed = True
    if deps_changed:
        # Packets are held by reference in the queue; persist the mutated
        # dependency edges through the queue's own save path.
        try:
            work_queue._save()  # noqa: SLF001 - canonical persist for in-place packet edits
        except AttributeError:
            persist = getattr(work_queue, "persist", None)
            if callable(persist):
                persist()

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
    writable_path_scope: list[str] | None = None,
    lanes: list[Any] | None = None,
) -> ObjectivePlanRecord:
    """Run compile → materialize → readiness as the recoverable unit of work.

    ``writable_path_scope`` is the objective-derived, least-privilege mutation
    authority every Task of this plan is materialized with (see
    ``derive_state_records``). ``None`` fails materialization closed.

    ``lanes`` is the caller's declared decomposition: when supplied the
    objective materializes one Task per lane, each with that lane's own
    authority and resolved dependencies, instead of a single umbrella Task.

    Idempotent: a session that already committed a plan version returns it
    unchanged (no duplicate plans/Tasks/events on retry).
    """
    resumed_plan = None
    if session.active_plan_record_id:
        existing = store.get_plan(session.active_plan_record_id)
        if existing is not None and session.operation_stage in (
            PlanningStageMarker.COMMITTED.value,
            PlanningStageMarker.DECISION_EVALUATED.value,
        ):
            return existing
        if existing is not None:
            # Partial-failure recovery (adversarial-review MAJOR): the plan
            # record was already appended before the failure — RESUME it.
            # Re-compiling would mint a second v1 plan for the same objective
            # (a phantom on the surface). Skip compile/append and continue
            # from materialization with the persisted record.
            resumed_plan = existing

    def _emit(event_type: str, data: dict[str, Any]) -> None:
        if event_emit is not None:
            try:
                event_emit(event_type, data)
            except Exception as exc:
                logger.debug("compose emit failed: %s", exc)

    try:
        current, desired, gap_snapshot = derive_state_records(
            session.objective_text,
            snapshot,
            tenant_id=scope.tenant_id,
            scope=scope,
            writable_path_scope=writable_path_scope,
            lanes=lanes,
        )
        archetype = resolve_archetype(session.objective_text, scope)
        if resumed_plan is not None:
            plan = resumed_plan
            # RESUME: THE PERSISTED NODE IS AUTHORITATIVE. A node that already
            # carries scope_declared=True has a mutation authority that some
            # earlier call committed; re-deriving it here can only ever WIDEN or
            # narrow it behind the contract's back. Adversarial review found the
            # widening case live: with lanes=None (the only reachable production
            # state before lane wiring) the old code re-seeded EVERY node from
            # the single flat scope, so the zero-write independent verifier
            # silently gained write permission on the whole union — on every
            # retry, with scope_declared still True so nothing downstream
            # flagged it. That is exactly the "verification must not be
            # weakened" prohibition, so resume now never touches a declared
            # node.
            #
            # Re-seeding remains ONLY for legacy nodes persisted before Tasks
            # carried scope (scope_declared=False), which would otherwise fail
            # materialization forever — an unrecoverable poison record, since
            # every retry takes this same branch.
            lane_scope_by_gap: dict[str, list[str]] = {}
            for raw_lane in lanes or []:
                lane_obj = (
                    raw_lane
                    if isinstance(raw_lane, ObjectiveLane)
                    else ObjectiveLane.from_dict(dict(raw_lane))
                )
                lane_scope_by_gap[f"gap-lane-{lane_obj.lane_key}"] = [
                    str(p) for p in lane_obj.writable_path_scope
                ]
            for node in plan.nodes:
                if node.get("kind") != "packet":
                    continue
                if node.get("scope_declared"):
                    # Persisted authority is canonical — never re-derived.
                    continue
                gap_id = node.get("gap_id", "")
                if gap_id in lane_scope_by_gap:
                    node["writable_path_scope"] = list(lane_scope_by_gap[gap_id])
                    node["scope_declared"] = True
                    continue
                if str(gap_id).startswith("gap-lane-"):
                    # A lane-derived node whose lane this call did not declare
                    # cannot be re-seeded from the flat scope without widening
                    # it (the verifier lane is the dangerous case). Fail closed.
                    raise PlanCompilationError(
                        f"resumed plan node {node.get('node_id', '')!r} (gap {gap_id!r}) is "
                        "lane-derived but no matching lane was declared — refusing to re-seed "
                        "authority from the flat scope"
                    )
                if not gap_id:
                    # A node with no gap_id was minted OUTSIDE compilation (the
                    # revision path's add_node). Seeding it from the caller's
                    # flat scope hands an undeclared node the full workspace
                    # authority and makes it a new executable Task — a 5th
                    # Task with write access the operator never declared.
                    # Legacy re-seeding is for records compiled BEFORE Tasks
                    # carried scope; those always have a gap_id.
                    raise PlanCompilationError(
                        f"resumed plan node {node.get('node_id', '')!r} has no gap_id — "
                        "refusing to seed authority from the flat scope onto a node "
                        "minted outside compilation"
                    )
                node["writable_path_scope"] = list(writable_path_scope or [])
                node["scope_declared"] = writable_path_scope is not None
        else:
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
        if resumed_plan is None and (
            dev_profile_enabled
            or (dev_profile_enabled is None and archetype.archetype_id == "development")
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

        if resumed_plan is None:

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


def _edit_target_id(edit: dict[str, Any]) -> str:
    """Node reference of one revision edit — the ONE key-resolution authority.

    ``classify_revision`` (the production chat path) emits ``target_node_id``;
    direct/API edit sets use ``node_id``. Both the DECLARED_EXCLUSIVE guard and
    the applier below MUST resolve the reference through this single function.

    This is module-scope rather than a closure because the guard and the applier
    once parsed this field independently: the guard read ``node_id``/``target``
    while production sent ``target_node_id``, so the guard was invisible to every
    real caller and one chat sentence deleted the zero-write verification lane
    from a DECLARED_EXCLUSIVE plan (adversarial-review CRITICAL). A guard and the
    operation it guards may never disagree about which field names the target.
    """
    return str(edit.get("target_node_id") or edit.get("node_id") or edit.get("target") or "")


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

    # A plan VERSION is minted here too, so the decomposition authority chosen
    # at compile time must be enforced here as well. Without this, `add_node`
    # mints an executable packet node on a DECLARED_EXCLUSIVE plan without ever
    # consulting the mode, and `remove_node` deletes a declared lane — including
    # the zero-write independent-verification lane — from a plain chat sentence,
    # defeating the atomicity `compile_plan` refuses to break.
    if plan.decomposition_mode == DecompositionMode.DECLARED_EXCLUSIVE.value:
        lane_ids = {
            n["node_id"]
            for n in plan.nodes
            if n.get("kind") == "packet" and str(n.get("gap_id", "")).startswith("gap-lane-")
        }
        for edit in edit_set.edits:
            op = str(edit.get("op", ""))
            if op == "add_node" and str(edit.get("kind", "packet")) == "packet":
                raise PlanCompilationError(
                    "plan version is DECLARED_EXCLUSIVE — a revision may not add an "
                    "executable packet node; re-declare the lane set instead"
                )
            if op == "remove_node":
                target = _edit_target_id(edit)
                if target in lane_ids:
                    raise PlanCompilationError(
                        f"plan version is DECLARED_EXCLUSIVE — a revision may not remove "
                        f"declared lane {target!r}; a declared decomposition is atomic and "
                        "must be revised by re-declaration"
                    )

    new_plan = ObjectivePlanRecord.from_dict(plan.to_dict())
    new_plan.plan_record_id = ObjectivePlanRecord().plan_record_id  # fresh id
    new_plan.graph_version = plan.graph_version + 1
    new_plan.supersedes_plan_record_id = plan.plan_record_id
    new_plan.status = ObjectivePlanStatus.DRAFT.value
    new_plan.created_at = time.time()
    new_plan.updated_at = time.time()

    by_id = {n["node_id"]: n for n in new_plan.nodes}

    # ONE key-resolution authority, shared with the DECLARED_EXCLUSIVE guard
    # above — see _edit_target_id.
    _target_id = _edit_target_id

    unapplied: list[str] = []
    for edit in edit_set.edits:
        op = edit.get("op")
        target = _target_id(edit)
        if op == "remove_node" and target in by_id:
            # Removing a node that a surviving EXECUTABLE node depends on would
            # silently unblock that node: the edge list is cleaned below, but a
            # stale `depends_on` entry survived, so the materialized
            # WorkPacket.dependencies lost the predecessor (an integration Task
            # declared to fan in on A∧B shipped with one dependency, and the
            # scheduler admitted it once the survivor alone succeeded).
            orphaned = [
                n["node_id"]
                for n in new_plan.nodes
                if n.get("kind") == "packet"
                and n.get("status") == "active"
                and n["node_id"] != target
                and target in (n.get("depends_on") or [])
            ]
            if orphaned:
                raise PlanCompilationError(
                    f"removing {target!r} would silently unblock dependent node(s) "
                    f"{orphaned} — remove or re-point the dependents in the same revision"
                )
            by_id[target]["status"] = "removed"
            new_plan.edges = [
                e for e in new_plan.edges if e.get("from") != target and e.get("to") != target
            ]
            # Defensive: strip the reference from any non-executable node too,
            # so no dangling id survives into the persisted version.
            for node in new_plan.nodes:
                deps = node.get("depends_on") or []
                if target in deps:
                    node["depends_on"] = [d for d in deps if d != target]
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
        elif op == "retitle" and target in by_id:
            by_id[target]["title"] = edit.get("title", "")
        elif op == "move_lane" and target in by_id:
            by_id[target]["lane"] = edit.get("lane", "")
        else:
            # A targeted op whose node could not be resolved is a FAILED
            # revision, never a silent no-op version bump.
            if op in ("remove_node", "retitle", "move_lane"):
                unapplied.append(f"{op}: unresolved node {target!r}")

    if unapplied:
        raise PlanCompilationError(f"revision edits did not apply: {unapplied}")

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

    # A revision must be DECIDABLE: re-evaluate readiness for v(n+1) exactly
    # like the compose path, and transition to AWAITING_APPROVAL when ready —
    # inside the SAME governed write. Without this, v2 stayed in DRAFT with
    # no HUD decision while v1's decision was superseded: the revised plan
    # was permanently undecidable (field run 20260722T202203Z). The session
    # is None here — it is already COMMITTED by revision time (readiness.py
    # documents the None contract).
    assessment = evaluate_decision_readiness(new_plan, None)
    new_plan.readiness_assessment = assessment.to_dict()
    if assessment.state == DecisionReadiness.DECISION_READY.value:
        new_plan.status = ObjectivePlanStatus.AWAITING_APPROVAL.value

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
