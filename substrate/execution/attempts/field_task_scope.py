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
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ScopeResolutionError(RuntimeError):
    """A semantic Task or its path scope could not be resolved. Fail closed.

    Defined BEFORE its first use: the accessors below reference it at module
    scope, and a definition placed after them would raise ``NameError`` (masking
    the real fail-closed error) if any accessor ran during module import.
    """


# ── the fixture's semantic Tasks ────────────────────────────────────────────
# Keys are the SEMANTIC labels the harness reasons about. These labels are the
# CANONICAL machine identity: the planner persists `semantic_label` on each plan
# node alongside `writable_path_scope`, so role resolution never depends on
# display text.
#
# FIXTURE_NODE_TITLES below is a LEGACY-COMPATIBILITY fallback only, consulted
# solely when a plan record carries no canonical label at all. Field run
# 20260805T172351Z-p1 failed because titles were the primary key: the planner
# emitted "Add the note-search backend endpoint" where the constant said
# "add note search backend endpoint", and exact equality matched 0 nodes. A
# machine role must not hinge on an article or a hyphen an LLM chose.
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


def _node_semantic_label(node: Any) -> str:
    """The node's CANONICAL machine role, or '' when the record predates it.

    This is the authority for role resolution. Titles are LLM-authored display
    text and must never decide which Task an injection targets.
    """
    raw = (
        node.get("semantic_label", "")
        if isinstance(node, dict)
        else getattr(node, "semantic_label", "")
    )
    return str(raw or "").strip()


_ARTICLES = frozenset({"the", "a", "an"})


def normalize_title(raw: str) -> str:
    """Fold ONLY cosmetic variation. Substantive words are never removed.

    Legacy-compatibility fallback for plan records written before nodes carried
    ``semantic_label``. Handles exactly the drift an LLM introduces in display
    text — capitalization, a leading article, hyphen-vs-space, repeated
    whitespace, surrounding punctuation, Unicode form.

    Deliberately NOT substring, fuzzy, stemmed, embedded, or token-overlap
    matching: every one of those can bind a role to the wrong Task, and a
    wrongly-targeted injection produces a green run that proved nothing.
    """
    import re
    import unicodedata

    text = unicodedata.normalize("NFKC", str(raw or "")).strip().casefold()
    text = text.replace("-", " ").replace("_", " ")
    text = re.sub(r"[^\w\s]", " ", text)  # drop punctuation, keep word chars
    # Drop articles as STANDALONE words. The planner inserts them anywhere
    # ("Add THE note-search backend endpoint"), not only in front, so a
    # leading-only rule cannot fold the drift that actually occurred. An article
    # is never a substantive distinguishing term for these roles; every other
    # word is preserved verbatim — no stemming, no stop-word list, no synonyms,
    # no substring or fuzzy matching.
    words = [w for w in text.split() if w and w not in _ARTICLES]
    return " ".join(words).strip()


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
        # ── 1. CANONICAL: the node's persisted machine role. ────────────────
        # semantic_label is written by the planner alongside writable_path_scope
        # and is not display text, so it cannot drift with LLM phrasing.
        matches = [n for n in (plan_nodes or []) if _node_semantic_label(n) == label]
        method = "semantic_label"
        raw_title = ""
        normalized = ""

        if not matches:
            # ── 2. LEGACY FALLBACK: cosmetic-only title normalization. ──────
            # Reached ONLY when no node carries the canonical key at all (a
            # pre-semantic_label plan record). A node that carries a DIFFERENT
            # canonical label is never eligible — a conflicting machine role
            # outranks any title resemblance.
            labelled = {_node_semantic_label(n) for n in (plan_nodes or [])} - {""}
            if labelled:
                raise ScopeResolutionError(
                    f"{label!r} matched 0 plan nodes by canonical semantic_label, and "
                    f"the plan DOES carry canonical labels {sorted(labelled)!r} — "
                    f"refusing to fall back to title matching against a plan that "
                    f"declares machine roles"
                )
            wanted_raw = titles.get(label, "").strip()
            if not wanted_raw:
                raise ScopeResolutionError(f"no node title configured for {label!r}")
            wanted = normalize_title(wanted_raw)
            if not wanted:
                # A configured title that normalizes to nothing (e.g. "a", "The")
                # would match every node that also normalizes to "" — binding a
                # role by vacuous equality. Refuse rather than resolve on emptiness.
                raise ScopeResolutionError(
                    f"configured title {wanted_raw!r} for {label!r} normalizes to the "
                    f"empty string — refusing to resolve a role by vacuous equality"
                )
            method = "normalized_title"
            normalized = wanted
            candidates = [
                n
                for n in (plan_nodes or [])
                if normalize_title(_node_title(n)) and normalize_title(_node_title(n)) == wanted
            ]
            if len(candidates) > 1:
                collided = sorted(_node_id(n) for n in candidates)
                raise ScopeResolutionError(
                    f"{label!r} (normalized title {wanted!r}) collapsed {len(candidates)} "
                    f"distinct plan nodes {collided!r} to one identity — refusing an "
                    f"ambiguous target"
                )
            matches = candidates

        if len(matches) != 1:
            raise ScopeResolutionError(
                f"{label!r} matched {len(matches)} plan nodes via {method} — "
                f"expected exactly 1; refusing an ambiguous target"
            )

        node = matches[0]
        node_id = _node_id(node)
        raw_title = str(
            node.get("title", "") if isinstance(node, dict) else getattr(node, "title", "")
        )
        packet_id = by_node.get(node_id, "")
        if not packet_id:
            raise ScopeResolutionError(
                f"{label!r} resolved to plan node {node_id!r} (via {method}) which "
                f"materialized no WorkPacket — the injection would target a "
                f"nonexistent Task"
            )
        logger.info(
            "scenario-map bind: role=%s method=%s node_id=%s packet_id=%s "
            "candidates=%d raw_title=%r normalized=%r",
            label,
            method,
            node_id,
            packet_id,
            len(matches),  # the REAL count, not a literal — a literal proves nothing
            raw_title,
            normalized,
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


def readonly_binds_for_scope(
    allowed_paths: list[str],
    *,
    lease_root: str,
    include_git_authority: bool = True,
) -> list[str]:
    """Absolute in-worktree paths to re-bind READ-ONLY for this Task.

    This is the EXECUTION half of the one canonical scope authority: the
    verifier calls ``allowed_paths_for`` + ``normalize_allowed_paths`` to judge a
    diff, and this function turns the SAME normalized list into the mount
    barrier that prevents the out-of-scope write in the first place. Both read
    the Task's persisted ``writable_path_scope``; neither derives its own.

    Why a mount barrier and not permissions: field run ``20260803T191345Z-fail``
    proved instruction text cannot enforce scope (both workers received correct,
    distinct, self-sufficient contracts naming their exact allowed and forbidden
    paths, and both wrote the complete six-file objective anyway). A chmod-based
    barrier is also insufficient — it still permits rename-over, delete-and-
    recreate, and parent-directory replacement. A read-only BIND denies those at
    the mount layer, before the target is modified.

    Returns every EXISTING top-level entry of the worktree that is not itself
    inside the allowed set, walking down into directories that partially
    overlap the scope so a permitted file is never masked by its own parent.
    ``.git`` is SKIPPED here and handled by ``git_readonly_subpaths()`` instead:
    it holds both authorization surfaces (hooks, config, refs) and the object/
    index storage a commit must write, so it needs per-subpath treatment rather
    than one verdict (finding F-1).

    An EMPTY ``allowed_paths`` (the zero-write verifier lane) makes every
    existing path read-only — the strongest form, not the weakest.
    """
    root = os.path.realpath(lease_root)
    if not os.path.isdir(root):
        raise ScopeResolutionError(f"lease root {lease_root!r} is not a directory — refusing")
    allowed = {p.strip("/") for p in allowed_paths if str(p).strip("/")}

    def _is_allowed(rel: str) -> bool:
        """True when ``rel`` is inside (or equal to) a declared allowed path."""
        return any(rel == a or rel.startswith(a + "/") for a in allowed)

    def _contains_allowed(rel: str) -> bool:
        """True when some allowed path lives BELOW ``rel`` (partial overlap)."""
        return any(a.startswith(rel + "/") for a in allowed)

    binds: list[str] = []

    def _walk(rel_dir: str) -> None:
        abs_dir = os.path.join(root, rel_dir) if rel_dir else root
        try:
            entries = sorted(os.listdir(abs_dir))
        except OSError as exc:  # unreadable dir — fail closed, never skip silently
            raise ScopeResolutionError(f"cannot enumerate {abs_dir!r}: {exc}") from exc
        for name in entries:
            rel = f"{rel_dir}/{name}" if rel_dir else name
            # `.git` is never task content, but it is NOT handled here: locking
            # it wholesale is what made `git add` impossible (finding F-1 —
            # `index.lock` is created inside `.git`, so a read-only `.git` means
            # no worker can ever commit). Its authority surfaces are re-locked
            # individually by `git_readonly_subpaths()`, which the launcher
            # applies alongside this list. Skipping it here — rather than
            # appending it — is deliberate: two functions must not both claim
            # authority over the same path with different verdicts.
            if rel == ".git":
                continue
            if _is_allowed(rel):
                continue  # authorized — leave it writable
            abs_path = os.path.join(abs_dir, name)
            if os.path.isdir(abs_path) and not os.path.islink(abs_path) and _contains_allowed(rel):
                # This directory holds an allowed path deeper down: descend so
                # the permitted child stays writable while its siblings do not.
                _walk(rel)
                continue
            binds.append(abs_path)

    _walk("")
    # The git authority surfaces are part of THE SAME barrier, returned by the
    # same call. They were briefly a separate function the caller had to remember
    # to add; a test that called only this one immediately proved the hazard by
    # letting `echo H > .git/config` succeed. A barrier that is only complete when
    # you remember a second call is not a barrier — so completeness is the
    # default and opting out is explicit.
    if include_git_authority:
        binds.extend(git_readonly_subpaths(root))
    return binds


ATTEMPT_REF_NAMESPACE = "refs/attempt"


def attempt_ref_name(attempt_id: str) -> str:
    """The one ref this attempt is allowed to move: ``refs/attempt/<id>/work``."""
    ident = str(attempt_id or "").strip().strip("/")
    if not ident or "/" in ident or ident in (".", ".."):
        raise ScopeResolutionError(f"attempt_id {attempt_id!r} is not a usable ref component")
    return f"{ATTEMPT_REF_NAMESPACE}/{ident}/work"


def prepare_attempt_git_capability(worktree_path: str, attempt_id: str) -> str:
    """Give this attempt a PRIVATE, writable ref namespace and point HEAD at it.

    Finding F-1. The write barrier made ``.git`` read-only, which is correct for
    every authorization surface but also made ``git add``/``git commit``
    impossible (``Unable to create '.git/index.lock': Read-only file system``,
    rc=128) — so no worker could ever succeed. A worker that cannot commit
    produces no artifacts and burns quota for nothing.

    Restoring commit capability WITHOUT restoring dangerous authority took four
    measured attempts (see the design note); the first three each failed:

    - re-binding only the FILES git writes fails, because git creates its
      ``*.lock`` beside the target, so it needs the *directory* writable;
    - leaving ``refs/heads`` writable is a real escape: a worker can create a
      LOOSE ref that shadows a packed one and thereby move any branch
      (measured: ``update-ref refs/heads/protected-main`` succeeded);
    - locking ``refs`` and re-binding only the attempt's own branch FILE fails
      again on ``<branch>.lock`` inside the locked directory.

    What works is a private namespace DIRECTORY per attempt: git writes its ref
    and its lock inside a directory that belongs to this attempt alone, while
    ``refs/heads``, ``packed-refs``, ``HEAD``, ``config`` and ``hooks`` all stay
    read-only. Commit identity is bound to the Attempt by construction — the ref
    name contains the attempt id, so an attempt cannot move another's ref even
    by name.

    Returns the absolute path of the writable ref directory. Raises
    ScopeResolutionError on any failure: a lease that cannot give the worker a
    private ref must fail closed rather than fall back to a writable ``.git``.
    """
    ref_name = attempt_ref_name(attempt_id)
    git_dir = os.path.join(worktree_path, ".git")
    if not os.path.isdir(git_dir):
        raise ScopeResolutionError(
            f"lease {worktree_path!r} has no .git DIRECTORY — the lease must be made "
            "self-contained before a private attempt ref can be prepared"
        )
    priv_dir = os.path.join(git_dir, *ref_name.split("/")[:-1])
    head_file = os.path.join(git_dir, "HEAD")
    try:
        from substrate.execution.cpu_gate import gated_subprocess_run

        resolved = gated_subprocess_run(
            ["git", "rev-parse", "HEAD"],
            caller="attempt_git_capability",
            timeout=30,
            cwd=worktree_path,
        )
        if resolved is None or resolved.returncode != 0:
            raise ScopeResolutionError(
                f"cannot resolve HEAD in lease {worktree_path!r}: "
                f"{getattr(resolved, 'stderr', 'cpu gate refused')}"
            )
        head_sha = (resolved.stdout or "").strip()
        if not head_sha:
            raise ScopeResolutionError(f"lease {worktree_path!r} resolved an empty HEAD")
        os.makedirs(priv_dir, exist_ok=True)
        with open(os.path.join(priv_dir, "work"), "w", encoding="utf-8") as fh:
            fh.write(head_sha + "\n")
        # Point HEAD at the private ref so the worker's commits land there. HEAD
        # itself is then mounted READ-ONLY, so the worker cannot re-point it at a
        # shared branch and commit onto that instead.
        with open(head_file, "w", encoding="utf-8") as fh:
            fh.write(f"ref: {ref_name}\n")
    except OSError as exc:
        raise ScopeResolutionError(
            f"cannot prepare attempt ref namespace in {worktree_path!r}: {exc}"
        ) from exc
    return priv_dir


def git_readonly_subpaths(worktree_path: str) -> list[str]:
    """Dangerous ``.git`` subpaths to re-lock READ-ONLY, given a writable ``.git``.

    Finding F-1. ``.git`` as a whole can no longer be read-only (the worker could
    not commit), so every surface inside it that confers AUTHORITY rather than
    holding task content is individually re-locked. Measured against real git:
    ``add`` + ``commit`` write only ``objects``, ``refs`` (its own), ``logs``,
    ``index`` and ``COMMIT_EDITMSG`` — and never touch any path below.

    - ``hooks``  — executable code git runs on the worker's behalf
    - ``config`` — ``core.hooksPath`` redirects hooks; aliases run commands
    - ``HEAD``   — re-pointing it would commit onto a shared branch
    - ``refs``   — every ref namespace; the attempt's own dir is re-opened ON TOP
    - ``packed-refs`` — the packed form of the same authority
    - ``info``, ``branches``, ``description`` — no task content, no reason to write

    The returned list is applied AFTER the writable bind, so these mask it; the
    attempt's private ref directory is bound after THESE, so it wins. Ordering is
    load-bearing and is asserted by the isolation tests.
    """
    git_dir = os.path.join(worktree_path, ".git")
    if not os.path.isdir(git_dir):
        return []
    out: list[str] = []
    for name in (
        "hooks",
        "config",
        "info",
        "branches",
        "description",
        "HEAD",
        "refs",
    ):
        path = os.path.join(git_dir, name)
        if os.path.exists(path):
            out.append(path)
    # `packed-refs` — CREATE-then-lock, exactly like `objects/info` and
    # `worktrees` below, NOT skip-if-absent. A freshly self-contained lease has
    # no packed-refs file, so a plain `if os.path.exists` skips it and leaves it
    # WRITABLE. Independent review (invocation-40 fix) measured the consequence:
    # a real bwrap worker appended one garbage line (rc=0), which made every
    # later `git rev-parse` in that lease return rc=128 ("unexpected line in
    # .git/packed-refs"). promote_attempt_objects then read that as "no HEAD" and
    # the attempt still SUCCEEDED with a durable Proof while its commit existed
    # only in the (now-corrupt) lease — the invocation-40 defect class, reached
    # by the sandboxed worker itself. An empty packed-refs file is inert for git;
    # `--ro-bind` needs it to exist, so create it or fail closed.
    packed_refs = os.path.join(git_dir, "packed-refs")
    if not os.path.exists(packed_refs):
        try:
            with open(packed_refs, "a", encoding="utf-8"):
                pass
        except OSError as exc:  # cannot create it -> cannot lock it -> fail closed
            raise ScopeResolutionError(
                f"cannot create {packed_refs!r} to lock it read-only: {exc}"
            ) from exc
    out.append(packed_refs)
    # `objects/` stays WRITABLE (a commit writes objects) but `objects/info/`
    # holds `alternates`, which names an EXTERNAL object store git resolves
    # objects from. A self-directed probe of the surface THIS correction opened
    # found it writable and measured the impact: inside the sandbox git could not
    # normalize the path (nothing outside the lease is bound, so isolation held),
    # but the FILE PERSISTED TO THE HOST, and on the host `git cat-file` then
    # read a blob out of an unrelated repository and printed its contents. That
    # is a persistence primitive — a worker plants a file during confinement that
    # changes how the HOST resolves objects afterwards, where the verifier and
    # every later git command run with the real filesystem visible. Denying the
    # write is the fix; a post-hoc check would be the "detect after the fact"
    # shape this barrier exists to replace.
    #
    # CREATED when absent rather than skipped: `--ro-bind` needs an existing
    # path, and "the directory does not exist yet" must never degrade into "the
    # worker may create it". An empty `objects/info` is inert for git.
    objects_info = os.path.join(git_dir, "objects", "info")
    if os.path.isdir(os.path.join(git_dir, "objects")):
        try:
            os.makedirs(objects_info, exist_ok=True)
        except OSError as exc:  # cannot create it -> cannot lock it -> fail closed
            raise ScopeResolutionError(
                f"cannot create {objects_info!r} to lock it read-only: {exc}"
            ) from exc
        out.append(objects_info)
    # `.git/worktrees` — the linked-worktree REGISTRY. `make_lease_selfcontained`
    # deliberately does not copy it, so it did not exist, so nothing locked it and
    # `git worktree add` inside the sandbox CREATED it: measured, the host's
    # `git worktree list` went 1 -> 2 and `.git/worktrees/` appeared on the host
    # even though the new worktree's own path (sandbox tmpfs) did not survive.
    # Registry pollution that outlives confinement violates the
    # zero-worktree-residue requirement. Created-then-locked for the same reason
    # as `objects/info` above.
    worktrees_dir = os.path.join(git_dir, "worktrees")
    try:
        os.makedirs(worktrees_dir, exist_ok=True)
    except OSError as exc:
        raise ScopeResolutionError(
            f"cannot create {worktrees_dir!r} to lock it read-only: {exc}"
        ) from exc
    out.append(worktrees_dir)
    # `.git/commondir` — the pointer to the COMMON git dir git reads refs (incl.
    # HEAD's target) from. Independent review (invocation-40 fix) proved the hole:
    # a self-contained lease has no commondir, so a skip-if-absent barrier leaves
    # it WRITABLE, and a worker can point it at an evil git dir it builds inside
    # its own writable lease. HEAD is a LOCKED symref, but refs are resolved
    # through the common dir, so `rev-parse HEAD` then follows the locked symref
    # into the redirected dir and returns a FRESHLY FABRICATED foreign commit —
    # brand-new to the durable repo, so it slips past even the authorship
    # pre-existence scan. Measured end-to-end with real bwrap: it promoted+pinned
    # the forged commit. Create-then-lock closes it — but the packed-refs recipe
    # (empty file) does NOT transfer: an EMPTY commondir is fatal ("failed to
    # read commondir"). The inert STANDALONE value is `.` (this dir is its own
    # common dir); with `.` written, rev-parse/status/commit all succeed and the
    # redirect is blocked. Verified.
    commondir = os.path.join(git_dir, "commondir")
    if not os.path.exists(commondir):
        try:
            with open(commondir, "w", encoding="utf-8") as fh:
                fh.write(".\n")
        except OSError as exc:  # cannot create it -> cannot lock it -> fail closed
            raise ScopeResolutionError(
                f"cannot create {commondir!r} to lock it read-only: {exc}"
            ) from exc
    out.append(commondir)
    # `.git/config.worktree` — the per-worktree config git reads WHEN
    # ``extensions.worktreeConfig`` is set. Independent review proved it writable
    # and host-persisting but BENIGN today: the main config (read-only above)
    # leaves that extension unset, so git never reads config.worktree, and it can
    # only set ``core.worktree`` (relocate the checkout), never the git-dir,
    # object store, or refs — so it forges/corrupts nothing. Locked create-then-
    # lock anyway, for defense-in-depth symmetry with the other honored-redirect
    # files: an empty config.worktree is inert. This closes the surface before a
    # future change that turns the extension on could make it load-bearing.
    config_worktree = os.path.join(git_dir, "config.worktree")
    if not os.path.exists(config_worktree):
        try:
            with open(config_worktree, "w", encoding="utf-8"):
                pass
        except OSError as exc:  # cannot create it -> cannot lock it -> fail closed
            raise ScopeResolutionError(
                f"cannot create {config_worktree!r} to lock it read-only: {exc}"
            ) from exc
    out.append(config_worktree)
    return out


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
    # Execution-side enforcement (finding F-6: these were public in practice —
    # the launcher imports them — but absent from __all__, so the module's
    # declared surface disagreed with its real one).
    "readonly_binds_for_scope",
    "git_readonly_subpaths",
    "prepare_attempt_git_capability",
    "attempt_ref_name",
    "ATTEMPT_REF_NAMESPACE",
]
