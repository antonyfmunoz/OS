"""Canonical resolution of a field run's semantic Tasks and their path scope.

Two Wave-2 CRITICALs (C-1 diff-scope, C-3 failure injection) had the SAME root
cause: the harness needed to say "the backend Task" and "the paths the backend
Task may write", but nothing structured carried either. The path scope existed
only as English prose in ``OBJECTIVE.md``, and the semantic labels existed only
in the reviewer's head — so the diff-scope check degenerated to
``whole_worktree=True`` and the injection targeted an id that never existed.

This module supplies both from ONE canonical derivation, with no pattern
matching anywhere:

    plan node (ObjectivePlanNode.node_id)
        → WorkPacket.source_evidence[{"type": "plan_node", "node_id": …}]
        → packet_id (the real ``wp-<hex12>``)

``resolve_scenario_map`` walks that lineage and returns
``{semantic_label: packet_id}``. ``allowed_paths_for`` returns the packet's
declared writable paths. Both fail CLOSED: an unresolvable or ambiguous mapping
raises rather than degrading to a permissive default, because every softening in
this campaign has been exactly such a default.

Scope: the Wave-2 qualification fixture. This is not a general capability.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

# ── the fixture's semantic Tasks ────────────────────────────────────────────
# Keys are the SEMANTIC labels the harness reasons about; values are the plan
# node titles the fixture plan uses. Titles are matched EXACTLY (casefolded and
# stripped) — never by substring or regex, so a title drift fails closed rather
# than silently binding the wrong Task.
BACKEND = "backend_task_id"
FRONTEND = "frontend_task_id"
INTEGRATION = "integration_task_id"
VERIFICATION = "verification_task_id"

SEMANTIC_LABELS: tuple[str, ...] = (BACKEND, FRONTEND, INTEGRATION, VERIFICATION)

# The exact node titles the fixture plan materializes, per semantic label.
FIXTURE_NODE_TITLES: dict[str, str] = {
    BACKEND: "add note search backend endpoint",
    FRONTEND: "add note search frontend ui",
    INTEGRATION: "integrate and reconcile search branches",
    VERIFICATION: "independently verify note search",
}

# Declared writable paths per semantic Task, WORKTREE-RELATIVE.
#
# These mirror the contract in the fixture's OBJECTIVE.md and are the authority
# the diff-scope check enforces. They are deliberately NARROW: a worker that
# rewrites the fixture's pre-existing tests (``tests/test_api.py``) to make its
# own change pass is outside scope and must fail verification.
#
# NOTE the frontend paths are ``app/static/*`` — the generator writes
# ``app/static/index.html`` while an earlier OBJECTIVE.md draft said
# ``static/index.html``. The generator is the ground truth; the contract text was
# corrected to match it rather than the reverse.
FIXTURE_ALLOWED_PATHS: dict[str, list[str]] = {
    BACKEND: ["app/main.py", "app/store.py", "tests/test_search_api.py"],
    FRONTEND: ["app/static", "tests/test_ui_search.py"],
    # Integration reconciles both lanes, so it may touch either lane's files
    # plus the merge itself — but still NOT the fixture's seed data or config.
    INTEGRATION: [
        "app/main.py",
        "app/store.py",
        "app/static",
        "tests/test_search_api.py",
        "tests/test_ui_search.py",
    ],
    # The verifier must produce ZERO diff. An empty allowlist means "no path may
    # change" — enforced, not merely declared.
    VERIFICATION: [],
}


class ScopeResolutionError(RuntimeError):
    """A semantic Task or its path scope could not be resolved. Fail closed."""


# ── plan-node → packet lineage ──────────────────────────────────────────────
def _node_id_for_packet(packet: Any) -> str:
    """The plan ``node_id`` a packet was materialized from ('' if none).

    Reads the canonical ``source_evidence`` entry the compiler writes:
    ``{"type": "plan_node", "node_id": "node-…"}``. This is the durable lineage
    link — there is no id-shape guessing on this path.
    """
    evidence = getattr(packet, "source_evidence", None)
    if evidence is None and isinstance(packet, dict):
        evidence = packet.get("source_evidence")
    for entry in evidence or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") == "plan_node" and entry.get("node_id"):
            return str(entry["node_id"])
    return ""


def _packet_id(packet: Any) -> str:
    if isinstance(packet, dict):
        return str(packet.get("packet_id", "") or "")
    return str(getattr(packet, "packet_id", "") or "")


def _node_title(node: Any) -> str:
    raw = node.get("title", "") if isinstance(node, dict) else getattr(node, "title", "")
    return str(raw or "").strip().casefold()


def _node_id(node: Any) -> str:
    raw = node.get("node_id", "") if isinstance(node, dict) else getattr(node, "node_id", "")
    return str(raw or "")


def resolve_scenario_map(
    *,
    plan_nodes: list[Any],
    packets: list[Any],
    node_titles: dict[str, str] | None = None,
) -> dict[str, str]:
    """Map each semantic label to the EXACT canonical ``wp-*`` packet id.

    Walks plan node title → node_id → packet.source_evidence → packet_id. Raises
    ``ScopeResolutionError`` when a label resolves to zero or more than one node
    or packet: an ambiguous mapping must never be resolved by picking the first
    match, because targeting the wrong Task produces a green run that proved
    nothing.
    """
    titles = dict(node_titles or FIXTURE_NODE_TITLES)

    # node_id → packet_id, rejecting a node that materialized twice.
    by_node: dict[str, str] = {}
    for packet in packets or []:
        node_id = _node_id_for_packet(packet)
        pid = _packet_id(packet)
        if not node_id or not pid:
            continue
        if node_id in by_node and by_node[node_id] != pid:
            raise ScopeResolutionError(
                f"plan node {node_id!r} materialized more than one packet "
                f"({by_node[node_id]!r}, {pid!r}) — ambiguous lineage"
            )
        by_node[node_id] = pid

    resolved: dict[str, str] = {}
    for label in SEMANTIC_LABELS:
        wanted = titles.get(label, "").strip().casefold()
        if not wanted:
            raise ScopeResolutionError(f"no node title configured for {label!r}")
        matches = [n for n in (plan_nodes or []) if _node_title(n) == wanted]
        if len(matches) != 1:
            raise ScopeResolutionError(
                f"{label!r} (title {wanted!r}) matched {len(matches)} plan nodes — "
                f"expected exactly 1; refusing an ambiguous target"
            )
        node_id = _node_id(matches[0])
        packet_id = by_node.get(node_id, "")
        if not packet_id:
            raise ScopeResolutionError(
                f"{label!r} resolved to plan node {node_id!r} which materialized no "
                f"WorkPacket — the injection would target a nonexistent Task"
            )
        resolved[label] = packet_id
    return resolved


def scenario_map_digest(mapping: dict[str, str], *, run_id: str) -> str:
    """Stable digest binding a scenario map to its run.

    Recorded alongside the map so a map copied between runs is detectable — a
    stale map would target another run's packet ids.
    """
    payload = json.dumps(
        {"run_id": run_id, "mapping": {k: mapping.get(k, "") for k in SEMANTIC_LABELS}},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── path scope ──────────────────────────────────────────────────────────────
def normalize_allowed_paths(raw_paths: list[str], *, lease_root: str) -> list[str]:
    """Normalize declared paths to worktree-relative, rejecting unsafe policies.

    Rejects, rather than silently widening (the C-1 defect):

    - ``""`` and ``"."`` — a whole-worktree policy is NOT a scope;
    - absolute paths — scope is expressed relative to the lease root;
    - parent traversal (``..``) escaping the lease root.

    An EMPTY input list is legal and means "no path may change" (the verifier's
    zero-diff requirement). It is distinct from ``["."]``, which is refused.
    """
    root = os.path.realpath(lease_root) if lease_root else ""
    out: list[str] = []
    for raw in raw_paths or []:
        path = str(raw or "").strip()
        if not path:
            raise ScopeResolutionError("empty allowed path is not a scope — refusing")
        if os.path.isabs(path):
            raise ScopeResolutionError(
                f"absolute allowed path {path!r} — scope must be lease-root relative"
            )
        normalized = os.path.normpath(path).replace(os.sep, "/").strip("/")
        if normalized in (".", ""):
            raise ScopeResolutionError(
                "whole-worktree scope ('.') is not a scope — the sandbox mount is a "
                "containment boundary, not a diff-scope authority"
            )
        if normalized == ".." or normalized.startswith("../"):
            raise ScopeResolutionError(f"allowed path {path!r} escapes the lease root — refusing")
        if root:
            resolved = os.path.realpath(os.path.join(root, normalized))
            if resolved != root and not resolved.startswith(root + os.sep):
                raise ScopeResolutionError(
                    f"allowed path {path!r} resolves outside the lease root — refusing"
                )
        out.append(normalized)
    return out


def allowed_paths_for(packet: Any, *, semantic_label: str = "") -> list[str]:
    """The declared writable paths for a Task, from canonical packet state.

    Order of authority:

    1. ``packet.requirements['allowed_paths']`` — the canonical carrier written
       at materialization;
    2. the fixture default for ``semantic_label`` — used when the harness seeds
       a packet it did not compile.

    Raises when neither resolves, so a Task with no declared scope can never
    execute under an implicit "everything" policy.
    """
    requirements = getattr(packet, "requirements", None)
    if requirements is None and isinstance(packet, dict):
        requirements = packet.get("requirements")
    if isinstance(requirements, dict):
        declared = requirements.get("allowed_paths")
        if isinstance(declared, list):
            # An explicitly empty list is a REAL policy (zero-diff), so accept it
            # here rather than falling through to the default.
            return [str(p) for p in declared]
    if semantic_label and semantic_label in FIXTURE_ALLOWED_PATHS:
        return list(FIXTURE_ALLOWED_PATHS[semantic_label])
    raise ScopeResolutionError(
        f"packet {_packet_id(packet)!r} declares no allowed_paths and no fixture "
        f"default applies (label={semantic_label!r}) — refusing an implicit "
        f"whole-worktree scope"
    )


def paths_outside(changed: list[str], allowed: list[str]) -> list[str]:
    """Changed paths not under any allowed prefix (both worktree-relative).

    An empty ``allowed`` means NOTHING may change, so every changed path is
    outside. This is the verifier's zero-diff enforcement.
    """
    outside: list[str] = []
    for raw in changed or []:
        path = str(raw or "").strip()
        if not path:
            continue
        normalized = os.path.normpath(path).replace(os.sep, "/").strip("/")
        if not any(normalized == a or normalized.startswith(a + "/") for a in allowed):
            outside.append(path)
    return outside


def write_scenario_map_file(
    targets_dir: str | os.PathLike[str], mapping: dict[str, str], *, run_id: str
) -> Path:
    """Persist the resolved map plus its run-bound digest."""
    from substrate.execution.attempts.field_failure_policy import scenario_map_path

    path = scenario_map_path(targets_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: str(mapping.get(k, "") or "") for k in SEMANTIC_LABELS}
    payload["run_id"] = run_id
    payload["digest"] = scenario_map_digest(mapping, run_id=run_id)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


__all__ = [
    "BACKEND",
    "FRONTEND",
    "INTEGRATION",
    "VERIFICATION",
    "SEMANTIC_LABELS",
    "FIXTURE_NODE_TITLES",
    "FIXTURE_ALLOWED_PATHS",
    "ScopeResolutionError",
    "resolve_scenario_map",
    "scenario_map_digest",
    "normalize_allowed_paths",
    "allowed_paths_for",
    "paths_outside",
    "write_scenario_map_file",
]
