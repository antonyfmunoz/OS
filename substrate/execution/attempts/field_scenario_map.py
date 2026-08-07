"""Field-pipeline scenario map: real materialized wp-* ids, run+plan bound (C-3).

C-3 was NOT "a scenario-map capability is missing" — ``resolve_scenario_map``
already resolves plan-node lineage to exact packet ids. C-3 was that **nothing in
the real field pipeline ever wrote the map**: ``write_scenario_map`` had one
non-test occurrence, inside a remediation *string*. So ``inject-failure`` always
read ``{}`` → ``armed:False`` → exit 3, and the failure-qualification pass was
unrunnable — the injection could never fire, and an operator hitting exit 3
repeatedly would hand-write the map with guessed ids or delete the check,
restoring the original defect.

This module is the field consumer. It reads the ACTUAL materialized plan +
WorkPacket records from candidate state, resolves each semantic role to its exact
canonical ``wp-<hex12>`` through plan-node lineage (never a title/regex/id-shape
guess), and writes a scenario map BOUND to this run's identity:

    run_id + plan_record_id + plan_version + a digest over the resolved ids

The binding is what makes staleness detectable: a map copied from another run, or
left over from a superseded plan version, no longer matches and is rejected. The
map establishes IDENTITY CORRESPONDENCE only — which packet is "the backend
Task". It is NEVER a mutation authority: allowed tools, writable scope and
execution constraints stay on the canonical WorkPacket requirements (the C-1
boundary, applied here too).

Fail closed on every ambiguity: absent map, stale map, a role that resolves to a
nonexistent Task, a Task not in the authorized frontier, a role that resolves to
more than one Task, a wrong run/plan binding. None of these may be papered over
with a default — a run that cannot inject the intended failure is INVALID, never
green.

Run binding is by CAPTURED JOURNEY IDENTITY, never "the only ACTIVE grant"
--------------------------------------------------------------------------
The prior implementation resolved the target through "the ONE ACTIVE grant in all
candidate state". That is not a run binding: a legitimate ACTIVE grant left by a
prior green pass, a parallel run, or another Objective would break it (0 or 2
matches), and it discarded identifiers already on
``ExecutionAuthorizationGrant`` (grant_id, decision_ref, conversation_id,
correlation_id, tenant/principal/membership).

The run's identity is captured at the moment the collector drives HUD execution
authorization and observes the resulting state, and persisted as
``execution_binding.json`` (identifiers + observed versions ONLY — see
``ExecutionBinding``). Both map writing and arming validation load that binding
and resolve EXACTLY one canonical grant matching every binding field through the
single ``resolve_canonical_grant`` authority below. Other ACTIVE grants are
irrelevant and never block the exact match; zero or more than one exact match
fails closed.

The map's claimed authorization binding is VERIFIABLE, not asserted: the digest
covers the full binding, and at arming time the persisted
``execution_authorization_ref`` must equal the canonical grant's ``decision_ref``
and the persisted ``grant_id`` must equal the canonical ``grant_id`` before the
recomputed digest is compared. The map is still correspondence evidence only — it
never grants eligibility, scope, tools or authority.
"""

from __future__ import annotations

import json
import logging
import os
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from substrate.execution.attempts.field_task_scope import (
    INTEGRATION,
    SEMANTIC_LABELS,
    ScopeResolutionError,
    _node_id_for_packet,
    resolve_scenario_map,
    scenario_map_digest,
)
from substrate.execution.planning.records import ObjectivePlanStatus

logger = logging.getLogger(__name__)

_SCENARIO_NAME = "scenario_map.json"
_BINDING_NAME = "execution_binding.json"

# A live execution-authorized Plan version must be EXACTLY APPROVED — an allowlist,
# never a denylist. A denylist lets AWAITING_APPROVAL and unknown/malformed
# statuses pass as "live accepted". ObjectivePlanStatus is the canonical status
# owner (substrate.execution.planning.records) — never a duplicated literal.
_PLAN_APPROVED = ObjectivePlanStatus.APPROVED.value

# Plan states in which a plan VERSION legitimately describes a run's immutable
# execution structure. Deliberately WIDER than the grant path's APPROVED-only
# allowlist (a plan may be structurally authoritative without being currently
# execution-authorized) and deliberately EXCLUDING the states a decision has
# positively rejected. See build_verified_declaration for the full rationale.
_DECLARATION_PLAN_STATES = frozenset(
    {
        ObjectivePlanStatus.APPROVED.value,
        ObjectivePlanStatus.AWAITING_APPROVAL.value,
        ObjectivePlanStatus.DRAFT.value,
    }
)

# The identifier fields that constitute a run's exact grant binding. Every one
# must match between the captured binding and the canonical grant record.
_BINDING_MATCH_FIELDS = (
    "grant_id",
    "decision_ref",
    "plan_record_id",
    "plan_version",
    "tenant_id",
    "principal_id",
    "membership_id",
    "conversation_id",
    "correlation_id",
)


class ScenarioMapError(RuntimeError):
    """The scenario map could not be built or validated. Fail closed."""


@dataclass(frozen=True)
class ExecutionBinding:
    """A run's captured execution-authorization identity (identifiers only).

    Populated from the REAL API/UI/state transition of THIS journey — never
    inferred from "the only active grant". It carries only ids and observed
    versions; no scope, tools, risk, or other authority (those stay on the
    canonical grant + WorkPacket requirements). Persisted at
    ``<targets>/<run-id>/execution_binding.json`` and reread at every consuming
    step so the exact grant can be resolved unambiguously among any number of
    other ACTIVE grants.
    """

    run_id: str
    candidate_sha: str
    plan_record_id: str
    plan_version: int
    grant_id: str
    decision_ref: str
    tenant_id: str = ""
    principal_id: str = ""
    membership_id: str = ""
    conversation_id: str = ""
    correlation_id: str = ""

    def match_fields(self) -> dict[str, Any]:
        """The subset that must equal the canonical grant record exactly."""
        return {
            "grant_id": self.grant_id,
            "decision_ref": self.decision_ref,
            "plan_record_id": self.plan_record_id,
            "plan_version": int(self.plan_version),
            "tenant_id": self.tenant_id,
            "principal_id": self.principal_id,
            "membership_id": self.membership_id,
            "conversation_id": self.conversation_id,
            "correlation_id": self.correlation_id,
        }


def _read_regular_authority_file(path: Path) -> str | None:
    """Read an authority file, or None — but NEVER block on a special file.

    An ``except OSError`` cannot fail closed on an operation that never returns.
    ``open()`` on a FIFO with no writer blocks in the kernel BEFORE any exception
    can be raised, so a named pipe called ``execution_binding.json`` hangs the
    production runner forever: it never seals, never reports, never dispatches.
    A hang is not fail-closed; it is no-answer-ever (reproduced, both reviewers).

    Authority files are regular files. Anything else — FIFO, socket, device,
    directory — is refused by type BEFORE opening, consistent with the
    ``lexists`` rule that a present-but-unusable name is evidence of a mutated
    run rather than absence. Symlinks are followed to their target and the
    TARGET must be regular, so a link to a FIFO is refused too.
    """
    try:
        st = os.stat(path)  # follows symlinks; the TARGET must be regular
    except (OSError, ValueError):
        return None
    if not stat.S_ISREG(st.st_mode):
        logger.warning(
            "authority file %s is not a regular file (mode %o) — refusing to read it; "
            "a special file cannot be read fail-closed",
            path,
            stat.S_IFMT(st.st_mode),
        )
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return None


def scenario_map_path(targets_dir: str | os.PathLike[str]) -> Path:
    return Path(targets_dir) / _SCENARIO_NAME


def execution_binding_path(targets_dir: str | os.PathLike[str]) -> Path:
    return Path(targets_dir) / _BINDING_NAME


def write_execution_binding(targets_dir: str | os.PathLike[str], binding: ExecutionBinding) -> Path:
    """Persist the run's captured execution binding atomically (identifiers only)."""
    path = execution_binding_path(targets_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(asdict(binding), indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    return path


def read_execution_binding(
    targets_dir: str | os.PathLike[str],
) -> ExecutionBinding | None:
    """Load the captured binding, or None when absent/unreadable/malformed.

    A missing binding is a hard failure at the call site (fail closed): without
    it there is no run identity to resolve the exact grant against.
    """
    raw = _read_regular_authority_file(execution_binding_path(targets_dir))
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    try:
        return ExecutionBinding(
            run_id=str(data.get("run_id", "")),
            candidate_sha=str(data.get("candidate_sha", "")),
            plan_record_id=str(data.get("plan_record_id", "")),
            plan_version=int(data.get("plan_version", -1)),
            grant_id=str(data.get("grant_id", "")),
            decision_ref=str(data.get("decision_ref", "")),
            tenant_id=str(data.get("tenant_id", "")),
            principal_id=str(data.get("principal_id", "")),
            membership_id=str(data.get("membership_id", "")),
            conversation_id=str(data.get("conversation_id", "")),
            correlation_id=str(data.get("correlation_id", "")),
        )
    except (TypeError, ValueError):
        return None


# ── read real candidate records ─────────────────────────────────────────────
def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue  # a malformed line is skipped, never fatal-by-crash
                if isinstance(rec, dict):
                    out.append(rec)
    except (FileNotFoundError, OSError):
        return []
    return out


def _is_plan_record(rec: dict[str, Any]) -> bool:
    return bool(rec.get("plan_record_id")) and "nodes" in rec


def _is_packet_record(rec: dict[str, Any]) -> bool:
    return bool(rec.get("packet_id")) and not rec.get("plan_record_id")


def select_plan(
    records: list[dict[str, Any]], *, plan_record_id: str, plan_version: int
) -> dict[str, Any]:
    """Select EXACTLY the plan (plan_record_id, plan_version). No fallback.

    There is no "latest available" and no run-tag substring search — those let a
    run adopt another run's or another Objective's plan. Zero matches or multiple
    matches fail closed: the caller must name the exact plan version it observed
    through the real Cockpit/API journey.
    """
    if not plan_record_id:
        raise ScenarioMapError("plan_record_id is required — no 'latest plan' fallback")
    matches = [
        p
        for p in records
        if _is_plan_record(p)
        and str(p.get("plan_record_id", "")) == plan_record_id
        and int(p.get("graph_version", -1)) == int(plan_version)
    ]
    if len(matches) != 1:
        raise ScenarioMapError(
            f"plan {plan_record_id!r} v{plan_version} matched {len(matches)} records "
            f"(need exactly 1) — refusing an ambiguous or absent plan selection"
        )
    plan = matches[0]
    if str(plan.get("status", "")).lower() == "superseded":
        raise ScenarioMapError(
            f"plan {plan_record_id!r} v{plan_version} is SUPERSEDED — a stale plan "
            f"may never seed a live injection"
        )
    return plan


def _canonical_packets(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """REAL persisted WorkPacket records only (packet_id + not a plan record).

    A plan node's ``workpacket_id`` is a REFERENCE, never proof that
    materialization succeeded. Only a record in the WorkPacket store counts."""
    return [r for r in records if _is_packet_record(r)]


def _packet_work_scope(packet: dict[str, Any]) -> dict[str, Any]:
    """The packet's first-class ``work_scope`` dict, or ``{}`` if malformed.

    WorkPacket has NO canonical top-level ``tenant_id`` — the authoritative tenant
    lives at ``work_scope.tenant_id`` (see ``substrate.contracts.work_context``).
    A packet whose work_scope is absent or not a dict has no ownership and fails
    closed at the call site.
    """
    ws = packet.get("work_scope")
    return ws if isinstance(ws, dict) else {}


def _packet_lineage(packet: dict[str, Any]) -> dict[str, Any]:
    """The packet's first-class ``lineage`` dict, or ``{}`` if malformed.

    Authoritative plan/objective correspondence lives at
    ``lineage.plan_record_id`` / ``lineage.objective_id`` (WorkLineageContext) —
    never top-level. A missing/non-dict lineage has no ownership and fails closed.
    """
    ln = packet.get("lineage")
    return ln if isinstance(ln, dict) else {}


def _index_packet_records(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Cardinality-PRESERVING index: packet_id → ALL persisted records with that id.

    The underlying WorkPacket JSONL can contain multiple current-truth records
    with the same ``packet_id``. A lossy ``{pid: packet}`` comprehension would
    collapse them by record order (last-write-wins) — so canonical identity
    ambiguity must be proven, not silently resolved. This keeps every record so
    the caller can require EXACTLY ONE before selecting it.
    """
    index: dict[str, list[dict[str, Any]]] = {}
    for p in _canonical_packets(records):
        pid = str(p.get("packet_id", ""))
        if not pid:
            continue
        index.setdefault(pid, []).append(p)
    return index


def _exactly_one_packet(
    packet_index: dict[str, list[dict[str, Any]]], pid: str, *, context: str
) -> dict[str, Any]:
    """Resolve ``pid`` to its ONE persisted canonical WorkPacket, or fail closed.

    Cardinality rule (order-invariant): zero records → fail; exactly one →
    return it; more than one → fail as canonical identity ambiguity. Both
    byte-identical and conflicting duplicates fail — a duplicate current-truth
    identity is corruption even when payloads match. Never selects first, last,
    newest, or "most complete".
    """
    recs = packet_index.get(pid) or []
    if len(recs) == 0:
        raise ScenarioMapError(
            f"{context}: packet {pid!r} has no persisted canonical WorkPacket record"
        )
    if len(recs) > 1:
        raise ScenarioMapError(
            f"{context}: packet {pid!r} resolves to {len(recs)} persisted WorkPacket "
            f"records — canonical identity ambiguity (duplicate current-truth ids are "
            f"corruption even when payloads match)"
        )
    return recs[0]


def _validate_plan_materialization_set(
    *,
    plan: dict[str, Any],
    plan_record_id: str,
    grant_tenant: str,
    packet_index: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """The Plan's FIRST-CLASS materialization record: ``workpacket_ids``.

    ``ObjectivePlanRecord.workpacket_ids`` is the Plan's authoritative record of
    which WorkPackets it materialized — NEVER inferred from nodes (which are
    correspondence records) as a fallback. Fails closed (raises) unless:

      * ``workpacket_ids`` exists as a LIST (missing / None → fail);
      * it is NONEMPTY (an execution-authorized Plan materialized ≥1 Task);
      * every declared id is nonempty and UNIQUE within the list;
      * every declared id resolves to EXACTLY ONE persisted canonical WorkPacket
        (zero → fail; >1 → fail as identity ambiguity) belonging to the same Plan
        and tenant.

    Returns a mapping ``{packet_id: the ONE resolved record}`` — the exact records
    threaded forward so no downstream code rebuilds a lossy id→record dict.
    """
    raw = plan.get("workpacket_ids")
    if not isinstance(raw, list):
        raise ScenarioMapError(
            f"plan {plan_record_id!r} has no workpacket_ids list — the Plan's "
            f"materialization record is absent (no node-inferred fallback)"
        )
    if not raw:
        raise ScenarioMapError(
            f"plan {plan_record_id!r} has an EMPTY workpacket_ids list — an "
            f"execution-authorized Plan must materialize at least one Task"
        )
    ids = [str(pid) for pid in raw]
    if any(not pid for pid in ids):
        raise ScenarioMapError(
            f"plan {plan_record_id!r} workpacket_ids contains an empty id — "
            f"every materialized WorkPacket id must be nonempty"
        )
    if len(set(ids)) != len(ids):
        raise ScenarioMapError(
            f"plan {plan_record_id!r} workpacket_ids contains duplicates {ids} — "
            f"the materialization set must be unique"
        )
    # Every declared id must resolve to EXACTLY ONE persisted canonical WorkPacket
    # of the same Plan + tenant. Cardinality is proven before selection.
    resolved: dict[str, dict[str, Any]] = {}
    for pid in ids:
        packet = _exactly_one_packet(
            packet_index, pid, context=f"plan {plan_record_id!r} materialized packet"
        )
        p_scope = _packet_work_scope(packet)
        p_tenant = str(p_scope.get("tenant_id", ""))
        if not p_tenant or (grant_tenant and p_tenant != grant_tenant):
            raise ScenarioMapError(
                f"plan {plan_record_id!r} materialized packet {pid!r} "
                f"work_scope.tenant_id {p_tenant!r} does not match grant tenant "
                f"{grant_tenant!r}"
            )
        p_lineage = _packet_lineage(packet)
        p_plan = str(p_lineage.get("plan_record_id", ""))
        if not p_plan or p_plan != plan_record_id:
            raise ScenarioMapError(
                f"plan {plan_record_id!r} materialized packet {pid!r} "
                f"lineage.plan_record_id {p_plan!r} does not match the Plan"
            )
        resolved[pid] = packet
    return resolved


def _validate_frontier_packet_ownership(
    packet: dict[str, Any],
    *,
    tid: str,
    grant: dict[str, Any],
    plan: dict[str, Any],
    plan_node_ids: set[str],
    plan_packet_ids: set[str],
) -> None:
    """Assert a frontier packet is a first-class-owned WorkPacket of THIS run.

    Every check reads the AUTHORITATIVE first-class contract fields, never a
    permissive empty-value or a fake top-level ``tenant_id``. Fails closed
    (raises ``ScenarioMapError``) on any missing/mismatched field:

      * ``work_scope`` is a dict;
      * ``work_scope.tenant_id`` is non-empty AND == ``grant.tenant_id`` exactly;
      * ``lineage`` is a dict;
      * ``grant.plan_record_id`` AND ``lineage.plan_record_id`` are BOTH non-empty
        and equal (two empty strings are never valid correspondence);
      * the referenced Plan's ``objective_id`` AND ``lineage.objective_id`` are
        BOTH non-empty and equal;
      * ``packet_id`` is UNCONDITIONALLY in the exact Plan's materialized WorkPacket
        set (``plan_packet_ids`` is already validated nonempty by the caller);
      * exactly one Plan node corresponds to it (its ``workpacket_id`` == packet_id);
      * ``source_evidence`` resolves to that same node.
    """
    grant_tenant = str(grant.get("tenant_id", ""))
    plan_record_id = str(grant.get("plan_record_id", ""))
    plan_objective_id = str(plan.get("objective_id", ""))

    scope = _packet_work_scope(packet)
    if not scope:
        raise ScenarioMapError(
            f"frontier packet {tid!r} has no work_scope — a packet without a "
            f"first-class scope has no ownership"
        )
    packet_tenant = str(scope.get("tenant_id", ""))
    if not packet_tenant:
        raise ScenarioMapError(
            f"frontier packet {tid!r} has an empty work_scope.tenant_id — ownership is unproven"
        )
    if packet_tenant != grant_tenant:
        raise ScenarioMapError(
            f"frontier packet {tid!r} work_scope.tenant_id {packet_tenant!r} does not "
            f"match grant tenant {grant_tenant!r}"
        )

    lineage = _packet_lineage(packet)
    if not lineage:
        raise ScenarioMapError(
            f"frontier packet {tid!r} has no lineage — plan/objective correspondence is unproven"
        )
    # Canonical plan/objective identity must be NONEMPTY on both sides — equality of
    # two empty strings is never valid correspondence.
    packet_plan = str(lineage.get("plan_record_id", ""))
    if not plan_record_id or not packet_plan:
        raise ScenarioMapError(
            f"frontier packet {tid!r} plan correspondence is unproven: grant "
            f"plan_record_id {plan_record_id!r} / lineage.plan_record_id {packet_plan!r} "
            f"(neither may be empty)"
        )
    if packet_plan != plan_record_id:
        raise ScenarioMapError(
            f"frontier packet {tid!r} lineage.plan_record_id {packet_plan!r} does not "
            f"match grant plan {plan_record_id!r}"
        )
    packet_objective = str(lineage.get("objective_id", ""))
    if not plan_objective_id or not packet_objective:
        raise ScenarioMapError(
            f"frontier packet {tid!r} objective correspondence is unproven: plan "
            f"objective_id {plan_objective_id!r} / lineage.objective_id {packet_objective!r} "
            f"(neither may be empty)"
        )
    if packet_objective != plan_objective_id:
        raise ScenarioMapError(
            f"frontier packet {tid!r} lineage.objective_id {packet_objective!r} does not "
            f"match plan objective {plan_objective_id!r}"
        )

    # packet_id must be UNCONDITIONALLY in the exact Plan's materialized WorkPacket
    # set (the caller has already proven that set exists and is nonempty).
    if tid not in plan_packet_ids:
        raise ScenarioMapError(
            f"frontier packet {tid!r} is not in plan {plan_record_id!r}'s materialized "
            f"WorkPacket set {sorted(plan_packet_ids)}"
        )

    # Exactly one Plan node must correspond, its workpacket_id must equal packet_id,
    # and the packet's source_evidence must resolve to that same node.
    node_id = _node_id_for_packet(packet)
    if not node_id:
        raise ScenarioMapError(
            f"frontier packet {tid!r} source_evidence names no plan node — node "
            f"correspondence is absent"
        )
    nodes = [n for n in (plan.get("nodes") or []) if isinstance(n, dict)]
    corresponding = [n for n in nodes if str(n.get("node_id", "")) == node_id]
    if len(corresponding) != 1:
        raise ScenarioMapError(
            f"frontier packet {tid!r} corresponds to {len(corresponding)} plan nodes "
            f"with node_id {node_id!r} (need exactly 1)"
        )
    if node_id not in plan_node_ids:
        raise ScenarioMapError(
            f"frontier packet {tid!r} names node {node_id!r} that is not in plan {plan_record_id!r}"
        )
    declared = str(corresponding[0].get("workpacket_id", "") or "")
    if declared != tid:
        raise ScenarioMapError(
            f"frontier packet {tid!r} corresponds to node {node_id!r} whose "
            f"workpacket_id is {declared!r} — packet and node disagree"
        )


def binding_digest(mapping: dict[str, str], binding: ExecutionBinding) -> str:
    """Digest over the resolved ids AND the full run+authorization binding.

    Unlike the id-only ``scenario_map_digest``, this covers run_id, candidate_sha,
    plan id/version, grant_id, decision_ref, tenant/conversation/correlation and
    the semantic Task-id mapping — so a map whose claimed binding was altered
    (e.g. a tampered ``execution_authorization_ref`` or grant_id) no longer
    matches, and arming rejects it.
    """
    import hashlib

    payload = json.dumps(
        {
            "binding": binding.match_fields()
            | {"run_id": binding.run_id, "candidate_sha": binding.candidate_sha},
            "mapping": {k: mapping.get(k, "") for k in SEMANTIC_LABELS},
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_from_records(
    records: list[dict[str, Any]],
    *,
    binding: ExecutionBinding,
    node_titles: dict[str, str] | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Resolve the scenario map from REAL materialized records for the run's EXACT
    captured binding.

    For every semantic role, resolution requires the full lineage to close on a
    REAL canonical WorkPacket record:

        exact plan node → node_id → exactly one persisted WorkPacket record whose
        source_evidence names that node_id AND whose packet_id == node.workpacket_id

    There is NO synthesized-node-packet path: a plan node claiming
    ``workpacket_id`` is not evidence the packet exists. Fails closed when a node
    names a packet with no canonical record, a packet carries no matching node
    lineage, node/packet ids disagree, a node resolves to multiple packets, or a
    packet claims multiple nodes.

    THE SINGLE AUTHORITY GATE: before producing any payload this calls
    ``resolve_canonical_grant(records, binding, now=now)`` — the SAME resolver
    arming uses. Map creation therefore fails closed on zero/multiple exact grants,
    non-ACTIVE status, unmet not_before, elapsed expires_at, empty frontier, an
    absent/non-live exact Plan version, and any invalid first-class frontier packet
    ownership. There is no second reduced validator: an expired or not-yet-valid
    grant cannot even produce ``scenario_map.json``.

    The plan is selected by the binding's exact (plan_record_id, plan_version) —
    never "latest". Returns the persistable payload (semantic ids + full run +
    authorization binding + binding digest). Correspondence evidence only — never
    mutation authority.
    """
    # THE authority gate — identical to arming. No payload is produced unless the
    # exact canonical grant validates (status/validity window/frontier ownership).
    resolve_canonical_grant(records, binding, now=now)

    plan = select_plan(
        records, plan_record_id=binding.plan_record_id, plan_version=binding.plan_version
    )
    nodes = [n for n in (plan.get("nodes") or []) if isinstance(n, dict)]
    packets = _canonical_packets(records)

    # resolve_scenario_map walks node title → node_id → packet.source_evidence →
    # packet_id over the REAL packets only. A node whose packet never
    # materialized therefore resolves to nothing and raises (fail closed).
    try:
        mapping = resolve_scenario_map(plan_nodes=nodes, packets=packets, node_titles=node_titles)
    except ScopeResolutionError as exc:
        raise ScenarioMapError(f"lineage resolution failed: {exc}") from exc

    # Additional cross-checks the title-based resolver does not enforce: for each
    # resolved role, the node's declared workpacket_id must EQUAL the packet id we
    # resolved through source_evidence (a node and its packet must agree).
    node_by_id = {str(n.get("node_id", "")): n for n in nodes}
    for label, packet_id in mapping.items():
        packet = next((p for p in packets if str(p.get("packet_id", "")) == packet_id), None)
        if packet is None:
            raise ScenarioMapError(
                f"{label}: resolved packet {packet_id!r} has no canonical record"
            )
        node_id = _node_id_for_packet(packet)
        node = node_by_id.get(node_id)
        if node is None:
            raise ScenarioMapError(
                f"{label}: packet {packet_id!r} names node {node_id!r} absent from the plan"
            )
        declared = str(node.get("workpacket_id", "") or "")
        if declared and declared != packet_id:
            raise ScenarioMapError(
                f"{label}: plan node {node_id!r} declares workpacket_id {declared!r} but "
                f"lineage resolved packet {packet_id!r} — node and packet disagree"
            )

    payload: dict[str, Any] = {k: mapping[k] for k in SEMANTIC_LABELS}
    payload["run_id"] = binding.run_id
    payload["candidate_sha"] = binding.candidate_sha
    payload["plan_record_id"] = str(plan.get("plan_record_id", "") or "")
    payload["plan_version"] = int(plan.get("graph_version", 0))
    payload["grant_id"] = binding.grant_id
    payload["execution_authorization_ref"] = binding.decision_ref
    payload["tenant_id"] = binding.tenant_id
    payload["conversation_id"] = binding.conversation_id
    payload["correlation_id"] = binding.correlation_id
    # id-only digest kept for backward-compatible staleness detection; the
    # authoritative binding digest additionally covers the full authorization
    # identity so a tampered ref/grant_id is detectable.
    payload["digest"] = scenario_map_digest(mapping, run_id=binding.run_id)
    payload["binding_digest"] = binding_digest(mapping, binding)
    return payload


def build_verified_declaration(
    records: list[dict[str, Any]],
    *,
    binding: ExecutionBinding,
    now: float | None = None,
) -> Any:
    """THE one constructor of a run's verified execution declaration.

    Derives the declaration by RECOMPUTING the semantic mapping from the
    canonical plan/packet/grant records (``build_from_records``, which gates on
    ``resolve_canonical_grant`` first), never by reading ``scenario_map.json``'s
    ``integration_task_id`` field. That distinction is the whole point: a
    retargeted field cannot move a declaration that was derived from lineage.

    The returned object is immutable and carries the ``binding_digest`` covering
    both the run/candidate/plan/grant binding and the full semantic mapping, so a
    consumer can prove the declaration belongs to the run it is executing.

    DECLARATION IS NOT AUTHORIZATION — and this function must never conflate
    them. It resolves the mapping from PLAN/PACKET LINEAGE only, and deliberately
    does NOT gate on ``resolve_canonical_grant``.

    That is not a weakened check; it is the correct separation. Lineage is
    durable — a plan node's WorkPacket is the integration Task for the whole run
    — while grant validity is transient: it expires, it can be revoked, it can be
    unreadable. An earlier version of this function called
    ``build_from_records`` (which gates on the grant) and was measured against
    the real field fixture: the grant was ACTIVE but 0.1 days past
    ``expires_at``, so declaration construction failed, the integration Task
    became UNDECLARED, and a ``C + worker`` row persisted — the identical end
    state as the original defect, reached through the expiry door.

    A transient authority failure must never be able to change a Task's durable
    execution CLASS. Composition still cannot RUN without a valid grant: the
    authority question is asked separately, and DENIED/UNRESOLVED yields no
    Attempt at all rather than a worker Attempt.

    Raises ``ScenarioMapError`` (fail closed) when the mapping cannot be
    recomputed — an unanswerable declaration is a refusal, never an empty one.
    """
    from substrate.execution.attempts.records import (
        AttemptExecutionKind,
        VerifiedExecutionDeclaration,
    )

    plan = select_plan(
        records, plan_record_id=binding.plan_record_id, plan_version=binding.plan_version
    )

    # DECLARATION-SIDE PLAN ACCEPTANCE — derived from source, not copied from the
    # grant path's allowlist.
    #
    # ``select_plan`` refuses only SUPERSEDED. The ``status == approved`` check
    # lived in ``resolve_canonical_grant``, and removing the grant gate (the
    # correct DECLARATION ≠ AUTHORIZATION fix) removed it too — so a binding
    # naming the fixture's REAL rejected prior revision built a declaration from
    # the WRONG plan, whose integration node is a DIFFERENT packet
    # (wp-5deae4d21c6a vs wp-7c7ffd5be3fc). The real Task C then read as
    # UNDECLARED and persisted as a worker (reproduced).
    #
    # The principle the owner set: a plan may be STRUCTURALLY AUTHORITATIVE
    # without being currently EXECUTION-AUTHORIZED. So this is NOT the grant's
    # allowlist. It is the set of states in which a plan version legitimately
    # describes this run's immutable structure:
    #
    #   APPROVED           — the live accepted structure. Accepted.
    #   AWAITING_APPROVAL  — a real revisable version (PlanningStore treats it as
    #                        revisable alongside APPROVED/DRAFT). Structurally
    #                        real; execution is separately gated by the grant.
    #   DRAFT              — same: a real version awaiting decision.
    #
    #   REJECTED / CANCELLED — a decision positively determined this structure is
    #                        NOT the run's. Never structural authority.
    #   SUPERSEDED         — a stale prior version; already refused by select_plan.
    #
    # This does not turn rejected/superseded history into executable authority:
    # execution still requires a valid grant bound to an APPROVED plan
    # (resolve_canonical_grant, unchanged).
    plan_status = str(plan.get("status", "")).lower()
    if plan_status not in _DECLARATION_PLAN_STATES:
        raise ScenarioMapError(
            f"plan {binding.plan_record_id!r} v{binding.plan_version} has status "
            f"{plan_status!r}, which is not a structurally authoritative state "
            f"{sorted(_DECLARATION_PLAN_STATES)} — a rejected/cancelled/unknown plan "
            f"version may not declare this run's execution structure"
        )

    nodes = [n for n in (plan.get("nodes") or []) if isinstance(n, dict)]
    packets = _canonical_packets(records)
    try:
        mapping = resolve_scenario_map(plan_nodes=nodes, packets=packets)
    except ScopeResolutionError as exc:
        raise ScenarioMapError(f"declaration lineage resolution failed: {exc}") from exc

    # Same node↔packet agreement cross-check build_from_records applies: a node
    # and the packet its lineage resolves to must name each other.
    node_by_id = {str(n.get("node_id", "")): n for n in nodes}
    for label, packet_id in mapping.items():
        packet = next((p for p in packets if str(p.get("packet_id", "")) == packet_id), None)
        if packet is None:
            raise ScenarioMapError(
                f"{label}: resolved packet {packet_id!r} has no canonical record"
            )
        node = node_by_id.get(_node_id_for_packet(packet))
        if node is None:
            raise ScenarioMapError(f"{label}: packet {packet_id!r} names a node absent from plan")
        declared_wp = str(node.get("workpacket_id", "") or "")
        if declared_wp and declared_wp != packet_id:
            raise ScenarioMapError(
                f"{label}: plan node declares workpacket_id {declared_wp!r} but lineage "
                f"resolved {packet_id!r} — node and packet disagree"
            )

    integration_task_id = str(mapping.get(INTEGRATION, "") or "")
    classes: tuple[tuple[str, str], ...] = ()
    if integration_task_id:
        classes = ((integration_task_id, AttemptExecutionKind.CONTROL_PLANE_COMPOSITION.value),)
    return VerifiedExecutionDeclaration(
        run_id=binding.run_id,
        candidate_sha=binding.candidate_sha,
        # Computed over the RECOMPUTED lineage mapping and the run's captured
        # binding — the same digest the authority path compares against, so the
        # declaration and the authority provably speak about the same mapping.
        digest=binding_digest(mapping, binding),
        execution_classes=classes,
    )


def write_scenario_map(targets_dir: str | os.PathLike[str], payload: dict[str, Any]) -> Path:
    """Persist the run+plan-bound scenario map atomically."""
    path = scenario_map_path(targets_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    return path


def read_scenario_map(targets_dir: str | os.PathLike[str]) -> dict[str, Any]:
    """Return the persisted map ({} when absent/unreadable)."""
    raw = _read_regular_authority_file(scenario_map_path(targets_dir))
    if raw is None:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


# ── canonical grant resolution: exact run binding, never "the only active" ───
def _is_grant_record(rec: dict[str, Any]) -> bool:
    return bool(rec.get("grant_id")) and "task_frontier" in rec


def resolve_canonical_grant(
    records: list[dict[str, Any]],
    binding: ExecutionBinding,
    *,
    now: float | None = None,
) -> dict[str, Any]:
    """The ONE canonical grant matching the run's EXACT captured binding.

    This is the single authority used by BOTH map writing and arming validation
    — there is no second, weaker preselection helper. It resolves the grant by
    matching EVERY binding identifier (grant_id, decision_ref, plan_record_id,
    plan_version, tenant_id, principal_id, membership_id, conversation_id,
    correlation_id), never "the only ACTIVE grant". Other ACTIVE grants from
    prior or parallel runs are irrelevant and never block the exact match.

    Fails closed unless ALL of the following hold:
      * exactly one grant record matches every binding field (0 or >1 → raise);
      * status == ACTIVE;
      * not_before satisfied (now >= not_before when set);
      * expires_at not elapsed (now < expires_at when set);
      * non-empty task_frontier;
      * the exact referenced Plan (plan_record_id, plan_version) exists;
      * that Plan version is a live accepted version (status not in
        draft/rejected/cancelled/superseded);
      * every frontier id is a persisted canonical WorkPacket belonging to that
        Plan and tenant.

    Returns the grant record dict. Callers derive the frontier from
    ``grant["task_frontier"]``.
    """
    import time as _time

    now = _time.time() if now is None else now
    want = binding.match_fields()

    grants = [g for g in records if _is_grant_record(g)]
    matches = [g for g in grants if all(str(g.get(k, "")) == str(v) for k, v in want.items())]
    if len(matches) != 1:
        raise ScenarioMapError(
            f"execution binding (grant_id={binding.grant_id!r}, "
            f"decision_ref={binding.decision_ref!r}, plan {binding.plan_record_id!r} "
            f"v{binding.plan_version}, conversation={binding.conversation_id!r}, "
            f"correlation={binding.correlation_id!r}) matched {len(matches)} grants "
            f"(need exactly 1) — refusing an ambiguous or absent authorization"
        )
    grant = matches[0]

    status = str(grant.get("status", "")).lower()
    if status != "active":
        raise ScenarioMapError(
            f"grant {grant.get('grant_id')!r} status is {status!r}, not ACTIVE — "
            f"an injection may only target an ACTIVE authorization"
        )
    not_before = float(grant.get("not_before", 0) or 0)
    if not_before and now < not_before:
        raise ScenarioMapError(
            f"grant {grant.get('grant_id')!r} not_before is {not_before} (now {now}) — "
            f"the authorization is not yet valid"
        )
    expires_at = float(grant.get("expires_at", 0) or 0)
    if expires_at and now >= expires_at:
        raise ScenarioMapError(
            f"grant {grant.get('grant_id')!r} expired at {expires_at} — refusing"
        )
    frontier = [str(t) for t in (grant.get("task_frontier") or []) if t]
    if not frontier:
        raise ScenarioMapError(
            f"grant {grant.get('grant_id')!r} has an EMPTY task_frontier — an empty "
            f"frontier is a failure, never 'skip the frontier check'"
        )

    # The exact referenced Plan must exist AND be EXACTLY APPROVED. This is an
    # allowlist, never a denylist: AWAITING_APPROVAL and unknown/malformed statuses
    # are NOT a live accepted plan version and must fail closed.
    plan = select_plan(
        records,
        plan_record_id=str(grant.get("plan_record_id", "")),
        plan_version=int(grant.get("plan_version", -1)),
    )
    plan_status = str(plan.get("status", "")).lower()
    if plan_status != _PLAN_APPROVED:
        raise ScenarioMapError(
            f"grant {grant.get('grant_id')!r} is bound to plan "
            f"{plan.get('plan_record_id')!r} v{plan.get('graph_version')} whose status is "
            f"{plan_status!r} — not an APPROVED (live accepted) plan version"
        )

    # The Plan's FIRST-CLASS materialization record: ObjectivePlanRecord.workpacket_ids
    # must exist as a nonempty list of unique nonempty ids. It is NEVER inferred from
    # nodes (correspondence records) as a fallback. Every declared id must resolve to
    # EXACTLY ONE persisted canonical WorkPacket of the same Plan and tenant.
    #
    # The packet index is CARDINALITY-PRESERVING (packet_id → [all records]) so a
    # duplicate current-truth id is proven ambiguous, never collapsed last-write-wins
    # by a lossy {pid: packet} comprehension. Bounded to the ids this run would trust
    # (the Plan materialization set ∪ the authorization frontier); unrelated duplicate
    # ids elsewhere in state do not block this run.
    plan_record_id = str(grant.get("plan_record_id", ""))
    grant_tenant = str(grant.get("tenant_id", ""))
    packet_index = _index_packet_records(records)
    plan_node_ids = {
        str(n.get("node_id", "")) for n in (plan.get("nodes") or []) if isinstance(n, dict)
    }
    materialized = _validate_plan_materialization_set(
        plan=plan,
        plan_record_id=plan_record_id,
        grant_tenant=grant_tenant,
        packet_index=packet_index,
    )
    plan_packet_ids = set(materialized)

    # Every frontier id must resolve to EXACTLY ONE persisted canonical WorkPacket
    # (order-invariant, duplicates fail) that is first-class-OWNED by THIS
    # plan+tenant AND unconditionally present in the materialization set. The exact
    # record threaded from the materialization map is reused when the frontier id is
    # in it; otherwise it is resolved (and cardinality-checked) from the same index.
    for tid in frontier:
        packet = materialized.get(tid) or _exactly_one_packet(
            packet_index, tid, context=f"grant {grant.get('grant_id')!r} frontier"
        )
        _validate_frontier_packet_ownership(
            packet,
            tid=tid,
            grant=grant,
            plan=plan,
            plan_node_ids=plan_node_ids,
            plan_packet_ids=plan_packet_ids,
        )
    return grant


def resolve_authorized_frontier(
    records: list[dict[str, Any]],
    binding: ExecutionBinding,
    *,
    now: float | None = None,
) -> tuple[list[str], str]:
    """The authorized frontier = the canonically-resolved grant's ``task_frontier``.

    Thin wrapper over ``resolve_canonical_grant`` — the frontier is that exact
    grant's frontier, never aggregated from all packets. ``(frontier, reason)``.
    """
    grant = resolve_canonical_grant(records, binding, now=now)
    frontier = [str(t) for t in (grant.get("task_frontier") or []) if t]
    return frontier, f"grant {grant.get('grant_id')} frontier={sorted(frontier)}"


# ── validate the map against live reality (identity + authorization) ─────────
def validate_against_run(
    targets_dir: str | os.PathLike[str],
    *,
    records: list[dict[str, Any]],
    now: float | None = None,
) -> tuple[bool, str]:
    """Is the persisted map valid for THIS run's captured binding + live grant?

    Rereads the run's captured ``execution_binding.json`` and the canonical stores
    (plan, WorkPackets, grant), resolves the ONE canonical grant matching every
    binding field, and validates the persisted map against live reality. Fails
    closed on every mode:
      * absent binding / absent map / wrong run binding;
      * stale map (recompute from the exact live plan version does not match, on
        either the id digest or the full binding digest);
      * a tampered ``execution_authorization_ref`` (≠ canonical grant.decision_ref)
        or ``grant_id`` (≠ canonical grant.grant_id);
      * a role id that is not a REAL persisted WorkPacket (node reference is not
        proof — enforced by build_from_records);
      * a role id outside the canonical grant's task_frontier;
      * no exact grant / multiple exact grants / non-ACTIVE / not-yet-valid /
        expired / empty frontier / draft-or-superseded plan / frontier packet
        outside the plan or tenant (all via resolve_canonical_grant).

    The map is NEVER trusted to grant eligibility — the authority (binding + grant)
    is reread here.
    """
    binding = read_execution_binding(targets_dir)
    if binding is None:
        return False, (
            f"execution binding ({_BINDING_NAME}) absent or malformed — no run "
            f"identity to resolve the exact grant against"
        )

    persisted = read_scenario_map(targets_dir)
    if not persisted:
        return False, "scenario map absent — injection cannot target a real task"
    if str(persisted.get("run_id", "")) != binding.run_id:
        return False, (
            f"scenario map is for run {persisted.get('run_id')!r}, not "
            f"{binding.run_id!r} (stale map from another run)"
        )

    # Resolve the ONE canonical grant by the exact captured binding BEFORE trusting
    # any map field. This is where a wrong grant_id/conversation/correlation/tenant,
    # a non-ACTIVE/expired grant, or a draft/superseded plan fails closed.
    try:
        grant = resolve_canonical_grant(records, binding, now=now)
    except ScenarioMapError as exc:
        return False, f"canonical grant unresolved: {exc}"

    # The map's claimed authorization binding must be REAL, not asserted: the
    # persisted ref must equal the canonical grant's decision_ref and the persisted
    # grant_id must equal the canonical grant_id. A tampered ref/grant_id fails here.
    if str(persisted.get("execution_authorization_ref", "")) != str(grant.get("decision_ref", "")):
        return False, (
            f"map execution_authorization_ref "
            f"{persisted.get('execution_authorization_ref')!r} ≠ canonical grant "
            f"decision_ref {grant.get('decision_ref')!r} (tampered or stale binding)"
        )
    if str(persisted.get("grant_id", "")) != str(grant.get("grant_id", "")):
        return False, (
            f"map grant_id {persisted.get('grant_id')!r} ≠ canonical grant_id "
            f"{grant.get('grant_id')!r} (tampered or stale binding)"
        )

    # Recompute from the EXACT live plan version bound by the binding; the persisted
    # map must match on identity, the id digest AND the full binding digest.
    try:
        fresh = build_from_records(records, binding=binding, now=now)
    except ScenarioMapError as exc:
        return False, f"cannot recompute scenario map from live state: {exc}"

    for key in ("plan_record_id", "plan_version", "digest", "binding_digest", *SEMANTIC_LABELS):
        if str(persisted.get(key, "")) != str(fresh.get(key, "")):
            return False, (
                f"scenario map is STALE: {key} persisted={persisted.get(key)!r} "
                f"live={fresh.get(key)!r} (plan superseded, binding altered, or ids drifted)"
            )

    frontier_set = {str(t) for t in (grant.get("task_frontier") or []) if t}
    real_ids = {str(r.get("packet_id", "")) for r in _canonical_packets(records)}
    for label in SEMANTIC_LABELS:
        tid = str(persisted.get(label, ""))
        if tid and tid not in real_ids:
            return False, f"{label} → {tid!r} is not a persisted WorkPacket record"
        if tid and tid not in frontier_set:
            return False, (
                f"{label} → {tid!r} is not in the authorized frontier {sorted(frontier_set)}"
            )

    return (
        True,
        f"scenario map valid for run {binding.run_id} plan {fresh['plan_record_id']} "
        f"v{fresh['plan_version']} grant {grant.get('grant_id')} (exact binding, "
        f"authorized frontier honored)",
    )


__all__ = [
    "ExecutionBinding",
    "ScenarioMapError",
    "scenario_map_path",
    "execution_binding_path",
    "write_execution_binding",
    "read_execution_binding",
    "select_plan",
    "binding_digest",
    "build_from_records",
    "build_verified_declaration",
    "resolve_canonical_grant",
    "resolve_authorized_frontier",
    "write_scenario_map",
    "read_scenario_map",
    "validate_against_run",
]
