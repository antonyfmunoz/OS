"""Canonical resolution of a field run's semantic Tasks and their path scope.

Two Wave-2 CRITICALs (C-1 diff-scope, C-3 failure injection) had the SAME root
cause: the harness needed to say "the backend Task" and "the paths the backend
Task may write", but nothing structured carried either. The path scope existed
only as English prose in ``OBJECTIVE.md``, and the semantic labels existed only
in the reviewer's head — so the diff-scope check degenerated to
``whole_worktree=True`` and the injection targeted an id that never existed.

TWO DIFFERENT CONCERNS — do not conflate them
---------------------------------------------
1. **Identity / correspondence** (``resolve_scenario_map``). Which canonical
   ``wp-<hex12>`` is "the backend Task"? Resolved by walking plan-node lineage:

       plan node (ObjectivePlanNode.node_id)
           → WorkPacket.source_evidence[{"type": "plan_node", "node_id": …}]
           → packet_id

   Evidence is a legitimate source here: this asks "which record corresponds to
   which planned node", a provenance question.

2. **Mutation authority** (``allowed_paths_for``). Which paths may this Task
   write? Resolved ONLY from the first-class typed contract fields
   ``WorkRequirements.writable_path_scope`` + ``scope_declared``.

   Evidence is NEVER consulted for this. ``EvidenceRef`` states the rule
   directly: "Evidence is provenance — it can never be a mutation authority."
   If write permission were derived through ``source_evidence``, editing a
   descriptive evidence entry would widen what a worker may write, letting
   descriptive data control execution permissions.

The fixture defaults below are a **seeding** input consumed at materialization
(``seed_scope_from_label``), which persists the authority onto the Task
contract. They are never a verification-time fallback: a Task that reaches
verification with no declared scope is a governance failure and blocks.

Both paths fail CLOSED — an unresolvable, ambiguous or undeclared value raises
rather than degrading to a permissive default, because every softening in this
campaign has been exactly such a default.

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


# ── Task-LOCAL instruction contracts ─────────────────────────────────────────
#
# Field run 20260803T002300Z-p1 failed at ``w16_ab_running_concurrent``: BOTH
# workers changed the SAME six files (the complete objective) and BOTH were
# correctly refused with ``diff_scope``. The scopes above were already declared
# correctly and ``render_prompt`` already named them — the defect was the task
# CONTENT the worker received.
#
# Each lane carried only a short TITLE ("Add the note-search backend endpoint"),
# so the only substantive specification available to the worker was the fixture
# repo's ``OBJECTIVE.md`` — a single document containing the full contracts for
# Tasks A, B, C AND D. A narrow title cannot compete with a detailed four-task
# spec sitting in the working tree, so each worker read all four contracts and
# implemented the whole objective.
#
# The correction is to give each Task its own COMPLETE, self-sufficient contract
# and to state precedence explicitly, so the worker never has to infer its slice
# from file names, titles, repo structure, another Task, or the global objective.
# Nothing about scheduler, grant, WorkPacket, verification, diff-scope, retry, or
# Proof semantics changes — this is instruction content only.
FIXTURE_TASK_INTENT: dict[str, str] = {
    BACKEND: (
        "Implement the note-search BACKEND endpoint ONLY. This Task is the "
        "backend slice of a larger objective; another Task owns the frontend and "
        "is being implemented CONCURRENTLY by a different worker."
    ),
    FRONTEND: (
        "Implement the note-search FRONTEND UI ONLY. This Task is the frontend "
        "slice of a larger objective; another Task owns the backend endpoint and "
        "is being implemented CONCURRENTLY by a different worker."
    ),
    INTEGRATION: (
        "Reconcile the already-verified backend and frontend branches. Do not "
        "re-implement either slice; both are complete and verified."
    ),
    VERIFICATION: (
        "Independently verify the integrated result. You are a VERIFIER, not an "
        "implementer. Produce ZERO file changes."
    ),
}

# The exact, self-sufficient contract for each Task. Written so a worker can
# complete its slice WITHOUT reading OBJECTIVE.md — the necessary context is
# here, so subordinating the global objective hides nothing the worker needs.
FIXTURE_TASK_CONTRACT: dict[str, str] = {
    BACKEND: (
        "Implement `GET /api/notes/search?q=<str>` in `app/main.py` (helper logic "
        "may go in `app/store.py`):\n"
        "- case-insensitive substring match over each note's `title` AND `body`;\n"
        '- response JSON: `{"query": "<q>", "results": [<note>, ...]}` where each '
        "note is the full `{id, title, body}` object;\n"
        "- an empty or missing `q` returns HTTP 400.\n"
        "Add tests in `tests/test_search_api.py`.\n"
        "Do NOT create or edit any frontend file. Do NOT touch `app/static/` or "
        "`tests/test_ui_search.py` — another Task owns them. Do NOT implement the "
        "search box, the UI, or the end-to-end integration."
    ),
    FRONTEND: (
        "Add to `app/static/index.html`:\n"
        '- a search input with `data-testid="note-search-input"`;\n'
        '- a results list with `data-testid="note-search-results"`.\n'
        "Wire `app/static/app.js` to call `GET /api/notes/search?q=<value>` on "
        "input and render the results. The backend endpoint is being implemented "
        "concurrently by another Task — code against this contract, do NOT wait "
        "for it and do NOT implement it yourself.\n"
        "Add `tests/test_ui_search.py` asserting the served HTML contains BOTH "
        "testids (this test must NOT require the backend endpoint to exist).\n"
        "Do NOT create or edit any backend file. Do NOT touch `app/main.py`, "
        "`app/store.py`, or `tests/test_search_api.py` — another Task owns them."
    ),
    INTEGRATION: (
        "Reconcile the backend and frontend branches into one integration branch, "
        "resolve any conflicts, and make the FULL test suite pass (base + backend "
        "tests + frontend tests). Do NOT re-implement either slice."
    ),
    VERIFICATION: (
        "Validate the API contract, the served UI testids, the live browser check, "
        "and the source diff scope, then produce Proof. Inspect and report ONLY: "
        "you must not create, edit, or delete any file."
    ),
}

# Precedence, rendered into every generated package. Lower-priority material may
# never authorize a broader edit than the WorkPacket allows.
FIXTURE_PRECEDENCE_NOTE: str = (
    "## Authorization Precedence (binding)\n"
    "1. The grant and WorkPacket authorization for THIS Task.\n"
    "2. This Task's instructions and its declared writable file scope.\n"
    "3. Shared architectural context.\n"
    "4. `OBJECTIVE.md` and any other repository document — INFORMATIONAL ONLY.\n"
    "\n"
    "`OBJECTIVE.md` in this repository describes the COMPLETE multi-task "
    "objective, including contracts owned by OTHER Tasks being executed "
    "concurrently by other workers. It is background context and it does NOT "
    "authorize you to widen your change surface. It cannot grant permission to "
    "edit a file outside your declared writable scope.\n"
    "\n"
    "Implement ONLY your Task's slice. Do NOT solve the complete objective. If "
    "completing your slice appears to require editing a file outside your "
    "declared writable scope, STOP and report that instead of editing it — an "
    "out-of-scope edit fails verification and wastes the attempt."
)


def task_intent_for(semantic_label: str) -> str:
    """Task-local intent line for one semantic Task. Fail closed on unknown."""
    if semantic_label not in FIXTURE_TASK_INTENT:
        raise ScopeResolutionError(f"no task intent for semantic label {semantic_label!r}")
    return FIXTURE_TASK_INTENT[semantic_label]


def task_contract_for(semantic_label: str) -> str:
    """Self-sufficient contract text for one semantic Task. Fail closed."""
    if semantic_label not in FIXTURE_TASK_CONTRACT:
        raise ScopeResolutionError(f"no task contract for semantic label {semantic_label!r}")
    return FIXTURE_TASK_CONTRACT[semantic_label]


def forbidden_paths_for(semantic_label: str) -> list[str]:
    """Paths owned by OTHER Tasks — named explicitly so the boundary is stated,
    never inferred from file names or repository structure."""
    if semantic_label not in FIXTURE_ALLOWED_PATHS:
        raise ScopeResolutionError(f"no path scope for semantic label {semantic_label!r}")
    mine = set(FIXTURE_ALLOWED_PATHS[semantic_label])
    others: list[str] = []
    for label in (BACKEND, FRONTEND):
        if label == semantic_label:
            continue
        for path in FIXTURE_ALLOWED_PATHS[label]:
            if path not in mine and path not in others:
                others.append(path)
    return others


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

    # node_id → packet_id, rejecting a node that materialized twice. ANY second
    # record for the same node_id is ambiguous lineage — including a byte-identical
    # duplicate packet_id: a duplicate current-truth record is corruption even when
    # the payloads match, so cardinality is proven, never collapsed by record order.
    by_node: dict[str, str] = {}
    for packet in packets or []:
        node_id = _node_id_for_packet(packet)
        pid = _packet_id(packet)
        if not node_id or not pid:
            continue
        if node_id in by_node:
            raise ScopeResolutionError(
                f"plan node {node_id!r} materialized more than one packet record "
                f"({by_node[node_id]!r}, {pid!r}) — ambiguous lineage (duplicate "
                f"current-truth records are corruption even when payloads match)"
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
    """The AUTHORITATIVE writable paths for a Task.

    Reads exactly ONE source: the first-class ``WorkRequirements`` fields
    ``writable_path_scope`` + ``scope_declared``, persisted on the Task contract.

    It deliberately does NOT read ``source_evidence``. Evidence is provenance
    (``EvidenceRef``: "Evidence is provenance, it can never be a mutation
    authority"); the plan-node lineage in ``resolve_scenario_map`` is used to
    establish Task IDENTITY and to SEED the contract at materialization, never to
    grant write permission at verification time. If scope were read through
    evidence, editing a descriptive evidence entry would widen what a worker may
    write — descriptive data controlling execution permission.

    ``semantic_label`` is accepted for diagnostics only; the fixture defaults are
    a SEEDING input (see ``seed_scope_from_label``), never a verification-time
    fallback. A Task that reaches verification with no declared scope is a
    governance failure and raises.
    """
    requirements = getattr(packet, "requirements", None)
    if requirements is None and isinstance(packet, dict):
        requirements = packet.get("requirements")
    if isinstance(requirements, dict):
        declared_flag = bool(requirements.get("scope_declared", False))
        scope = requirements.get("writable_path_scope")
        if declared_flag and isinstance(scope, list):
            # An explicitly declared EMPTY scope is a real policy (zero-diff).
            return [str(p) for p in scope]
    raise ScopeResolutionError(
        f"packet {_packet_id(packet)!r} carries no first-class writable_path_scope "
        f"(scope_declared is False) — the Task contract never recorded a mutation "
        f"authority, so execution cannot be verified as contained "
        f"(label={semantic_label!r}; evidence is NEVER consulted for scope)"
    )


def seed_scope_from_label(requirements: Any, semantic_label: str) -> Any:
    """SEED a Task contract's writable-path authority from the fixture role.

    This is the ONLY place fixture defaults enter, and it happens at
    MATERIALIZATION — writing the authority onto the persisted Task contract —
    not at verification. Once seeded, verification reads the contract alone, so
    the resulting authority is first-class and auditable rather than recomputed
    from a label every time a diff is checked.
    """
    if semantic_label not in FIXTURE_ALLOWED_PATHS:
        raise ScopeResolutionError(
            f"no fixture writable-path scope for {semantic_label!r} — refusing to "
            f"materialize a Task with no mutation authority"
        )
    paths = list(FIXTURE_ALLOWED_PATHS[semantic_label])
    declare = getattr(requirements, "declare_writable_paths", None)
    if callable(declare):
        declare(paths)
        errors = requirements.validate_writable_path_scope()
        if errors:
            raise ScopeResolutionError(f"invalid seeded scope for {semantic_label!r}: {errors}")
        return requirements
    if isinstance(requirements, dict):
        requirements["writable_path_scope"] = paths
        requirements["scope_declared"] = True
        return requirements
    raise ScopeResolutionError(
        f"cannot seed writable-path scope onto {type(requirements).__name__}"
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
