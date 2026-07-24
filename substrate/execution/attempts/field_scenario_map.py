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
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from substrate.execution.attempts.field_task_scope import (
    SEMANTIC_LABELS,
    ScopeResolutionError,
    _node_id_for_packet,
    resolve_scenario_map,
    scenario_map_digest,
)

_SCENARIO_NAME = "scenario_map.json"


class ScenarioMapError(RuntimeError):
    """The scenario map could not be built or validated. Fail closed."""


def scenario_map_path(targets_dir: str | os.PathLike[str]) -> Path:
    return Path(targets_dir) / _SCENARIO_NAME


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


def build_from_records(
    records: list[dict[str, Any]],
    *,
    run_id: str,
    plan_record_id: str,
    plan_version: int,
    execution_authorization_ref: str = "",
    node_titles: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve the scenario map from REAL materialized records for an EXACT plan.

    For every semantic role, resolution requires the full lineage to close on a
    REAL canonical WorkPacket record:

        exact plan node → node_id → exactly one persisted WorkPacket record whose
        source_evidence names that node_id AND whose packet_id == node.workpacket_id

    There is NO synthesized-node-packet path: a plan node claiming
    ``workpacket_id`` is not evidence the packet exists. Fails closed when a node
    names a packet with no canonical record, a packet carries no matching node
    lineage, node/packet ids disagree, a node resolves to multiple packets, or a
    packet claims multiple nodes.

    Returns the persistable payload (semantic ids + run/plan/authorization
    binding + digest). Correspondence evidence only — never mutation authority.
    """
    plan = select_plan(records, plan_record_id=plan_record_id, plan_version=plan_version)
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
    payload["run_id"] = run_id
    payload["plan_record_id"] = str(plan.get("plan_record_id", "") or "")
    payload["plan_version"] = int(plan.get("graph_version", 0))
    payload["execution_authorization_ref"] = execution_authorization_ref
    payload["digest"] = scenario_map_digest(mapping, run_id=run_id)
    return payload


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
    try:
        data = json.loads(scenario_map_path(targets_dir).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


# ── authorized frontier: derived from the ONE active grant, never aggregated ─
def _is_grant_record(rec: dict[str, Any]) -> bool:
    return bool(rec.get("grant_id")) and "task_frontier" in rec


_GRANT_TERMINAL = frozenset({"expired", "revoked", "invalidated", "failed_activation"})


def resolve_authorized_frontier(
    records: list[dict[str, Any]],
    *,
    plan_record_id: str,
    plan_version: int,
    tenant_id: str = "",
    now: float | None = None,
) -> tuple[list[str], str]:
    """The authorized frontier = the ONE ACTIVE execution-authorization grant's
    ``task_frontier`` for EXACTLY this plan version. ``(frontier, reason)``.

    This is NOT "all packets I can find". Exactly one grant must satisfy:
      * status ACTIVE (not ACTIVATING/EXPIRED/REVOKED/INVALIDATED/FAILED_ACTIVATION);
      * decision_kind execution_authorization (the grant record IS that);
      * exact plan_record_id + plan_version;
      * matching tenant when supplied;
      * not past expires_at.
    Zero matches, multiple matches, an empty frontier, or an expired/terminal
    grant raises — injection arming then fails closed. An unrelated packet never
    enters the frontier merely because it lacks a plan_record_id.
    """
    import time as _time

    now = _time.time() if now is None else now
    grants = [g for g in records if _is_grant_record(g)]
    matches = [
        g
        for g in grants
        if str(g.get("plan_record_id", "")) == plan_record_id
        and int(g.get("plan_version", -1)) == int(plan_version)
        and (not tenant_id or str(g.get("tenant_id", "")) == tenant_id)
    ]
    if not matches:
        raise ScenarioMapError(
            f"no execution-authorization grant for plan {plan_record_id!r} v{plan_version} "
            f"(tenant={tenant_id!r}) — the injection has no authorized frontier"
        )
    if len(matches) > 1:
        raise ScenarioMapError(
            f"{len(matches)} grants match plan {plan_record_id!r} v{plan_version} — "
            f"ambiguous authorization; refusing"
        )
    grant = matches[0]
    status = str(grant.get("status", "")).lower()
    if status != "active":
        raise ScenarioMapError(
            f"grant {grant.get('grant_id')!r} status is {status!r}, not ACTIVE — "
            f"an injection may only target an ACTIVE authorization"
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
    return frontier, f"grant {grant.get('grant_id')} frontier={sorted(frontier)}"


# ── validate the map against live reality (identity + authorization) ─────────
def validate_against_run(
    targets_dir: str | os.PathLike[str],
    *,
    run_id: str,
    records: list[dict[str, Any]],
    plan_record_id: str,
    plan_version: int,
    tenant_id: str = "",
    now: float | None = None,
) -> tuple[bool, str]:
    """Is the persisted map valid for THIS run + THIS exact plan + authorization?

    Rereads the canonical stores (plan, WorkPackets, grant) and validates the
    persisted map against them. Fails closed on every mode:
      * absent map / wrong run binding;
      * stale map (recompute from the exact live plan version does not match);
      * a role id that is not a REAL persisted WorkPacket (node reference is not
        proof — enforced by build_from_records);
      * a role id outside the ACTIVE grant's task_frontier;
      * no grant / multiple grants / non-ACTIVE / expired / empty frontier /
        wrong plan version (all via resolve_authorized_frontier).

    The map is NEVER trusted to grant eligibility — the authority is reread here.
    """
    persisted = read_scenario_map(targets_dir)
    if not persisted:
        return False, "scenario map absent — injection cannot target a real task"
    if str(persisted.get("run_id", "")) != run_id:
        return False, (
            f"scenario map is for run {persisted.get('run_id')!r}, not {run_id!r} "
            f"(stale map from another run)"
        )

    # Recompute from the EXACT live plan version; the persisted map must match it
    # byte-for-byte on identity + binding.
    try:
        fresh = build_from_records(
            records,
            run_id=run_id,
            plan_record_id=plan_record_id,
            plan_version=plan_version,
            execution_authorization_ref=str(persisted.get("execution_authorization_ref", "")),
        )
    except ScenarioMapError as exc:
        return False, f"cannot recompute scenario map from live state: {exc}"

    for key in ("plan_record_id", "plan_version", "digest", *SEMANTIC_LABELS):
        if str(persisted.get(key, "")) != str(fresh.get(key, "")):
            return False, (
                f"scenario map is STALE: {key} persisted={persisted.get(key)!r} "
                f"live={fresh.get(key)!r} (plan superseded or ids drifted)"
            )

    # The authorized frontier is the ACTIVE grant's task_frontier — reread now,
    # never taken from the map or aggregated from all packets.
    try:
        frontier, _why = resolve_authorized_frontier(
            records,
            plan_record_id=plan_record_id,
            plan_version=plan_version,
            tenant_id=tenant_id,
            now=now,
        )
    except ScenarioMapError as exc:
        return False, f"authorization frontier unresolved: {exc}"

    frontier_set = set(frontier)
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
        f"scenario map valid for run {run_id} plan {fresh['plan_record_id']} "
        f"v{fresh['plan_version']} (authorized frontier honored)",
    )


__all__ = [
    "ScenarioMapError",
    "scenario_map_path",
    "select_plan",
    "build_from_records",
    "resolve_authorized_frontier",
    "write_scenario_map",
    "read_scenario_map",
    "validate_against_run",
]
