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


def _latest_plan(records: list[dict[str, Any]], *, run_tag: str = "") -> dict[str, Any] | None:
    """The newest non-superseded plan record (optionally filtered by run tag).

    "Newest" = highest graph_version among records whose status is not SUPERSEDED.
    A stale/superseded plan must never seed a live injection.
    """
    plans = [r for r in records if _is_plan_record(r)]
    if run_tag:
        tagged = [p for p in plans if run_tag in json.dumps(p, sort_keys=True)]
        if tagged:
            plans = tagged
    live = [p for p in plans if str(p.get("status", "")).lower() != "superseded"]
    if not live:
        return None
    return max(live, key=lambda p: int(p.get("graph_version", 0)))


def build_from_records(
    records: list[dict[str, Any]],
    *,
    run_id: str,
    run_tag: str = "",
    node_titles: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Resolve the scenario map from REAL materialized records.

    Returns the persistable payload (semantic ids + run/plan binding + digest).
    Raises ``ScenarioMapError`` if no live plan exists or lineage is ambiguous.
    """
    plan = _latest_plan(records, run_tag=run_tag)
    if plan is None:
        raise ScenarioMapError(
            "no live (non-superseded) plan record found in candidate state — "
            "cannot resolve canonical task ids for the injection"
        )
    nodes = [n for n in (plan.get("nodes") or []) if isinstance(n, dict)]
    packets = [r for r in records if _is_packet_record(r)]

    # Also fold in the packets the plan records ON itself (plan.workpacket_ids +
    # node.workpacket_id). A packet node carries its materialized packet id
    # directly; synthesize a minimal packet view so a node whose packet lives
    # only on the plan record still resolves.
    node_packets: list[dict[str, Any]] = []
    for n in nodes:
        wp = str(n.get("workpacket_id", "") or "")
        if wp:
            node_packets.append(
                {
                    "packet_id": wp,
                    "source_evidence": [{"type": "plan_node", "node_id": n.get("node_id", "")}],
                }
            )

    try:
        mapping = resolve_scenario_map(
            plan_nodes=nodes, packets=packets + node_packets, node_titles=node_titles
        )
    except ScopeResolutionError as exc:
        raise ScenarioMapError(f"lineage resolution failed: {exc}") from exc

    plan_record_id = str(plan.get("plan_record_id", "") or "")
    plan_version = int(plan.get("graph_version", 0))
    payload: dict[str, Any] = {k: mapping[k] for k in SEMANTIC_LABELS}
    payload["run_id"] = run_id
    payload["plan_record_id"] = plan_record_id
    payload["plan_version"] = plan_version
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


# ── validate the map against live reality (staleness / frontier) ─────────────
def validate_against_run(
    targets_dir: str | os.PathLike[str],
    *,
    run_id: str,
    records: list[dict[str, Any]],
    authorized_frontier: list[str] | None = None,
    run_tag: str = "",
) -> tuple[bool, str]:
    """Is the persisted map valid for THIS run + THIS live plan? ``(ok, reason)``.

    Fails closed on every C-3 mode:
      * absent map;
      * wrong run (run_id mismatch);
      * stale map (plan_record_id / plan_version no longer the live plan, or the
        digest does not recompute from the live plan's lineage);
      * a role id that is not a real materialized packet;
      * a role id outside the authorized frontier;
      * ambiguity (surfaced by build_from_records raising).
    """
    persisted = read_scenario_map(targets_dir)
    if not persisted:
        return False, "scenario map absent — injection cannot target a real task"
    if str(persisted.get("run_id", "")) != run_id:
        return False, (
            f"scenario map is for run {persisted.get('run_id')!r}, not {run_id!r} "
            f"(stale map from another run)"
        )

    # Recompute from the CURRENT live records; the persisted map must match it
    # exactly. Any drift (superseded plan, re-materialized packet) fails.
    try:
        fresh = build_from_records(records, run_id=run_id, run_tag=run_tag)
    except ScenarioMapError as exc:
        return False, f"cannot recompute scenario map from live state: {exc}"

    for key in ("plan_record_id", "plan_version", "digest", *SEMANTIC_LABELS):
        if str(persisted.get(key, "")) != str(fresh.get(key, "")):
            return False, (
                f"scenario map is STALE: {key} persisted={persisted.get(key)!r} "
                f"live={fresh.get(key)!r} (plan superseded or ids drifted)"
            )

    # Every resolved id must be a REAL materialized packet AND inside the
    # authorized frontier (an injection may only target an authorized Task).
    real_ids = {str(r.get("packet_id", "")) for r in records if _is_packet_record(r)}
    # Packets recorded only on the plan node also count as materialized.
    plan = _latest_plan(records, run_tag=run_tag) or {}
    for n in plan.get("nodes") or []:
        if isinstance(n, dict) and n.get("workpacket_id"):
            real_ids.add(str(n["workpacket_id"]))
    frontier = set(authorized_frontier or [])
    for label in SEMANTIC_LABELS:
        tid = str(persisted.get(label, ""))
        if tid and tid not in real_ids:
            return False, f"{label} → {tid!r} is not a materialized WorkPacket"
        if frontier and tid and tid not in frontier:
            return False, f"{label} → {tid!r} is not in the authorized frontier {sorted(frontier)}"

    return (
        True,
        f"scenario map valid for run {run_id} plan {fresh['plan_record_id']} v{fresh['plan_version']}",
    )


__all__ = [
    "ScenarioMapError",
    "scenario_map_path",
    "build_from_records",
    "write_scenario_map",
    "read_scenario_map",
    "validate_against_run",
]
