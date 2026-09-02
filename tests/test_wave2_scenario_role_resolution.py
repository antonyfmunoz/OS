"""Scenario-map role resolution — canonical identity, not LLM display text.

THE DEFECT (field run 20260805T172351Z-p1): role resolution used exact
case-folded equality between hard-coded fixture titles and LLM-generated plan
node titles. The planner emitted "Add the note-search backend endpoint" where
the constant said "add note search backend endpoint" — an inserted article and
a hyphen — so `backend_task_id` matched 0 nodes and the run aborted before any
Attempt was created. The plan itself was correct: 6 nodes, 4 WorkPackets,
correct substantive roles.

THE FIX: resolve by the node's persisted canonical `semantic_label`. Fall back
to conservative cosmetic-only title normalization ONLY for legacy records that
carry no canonical label at all.

These tests pin the SECURITY-RELEVANT properties: a role must bind to exactly
one node, a conflicting canonical label outranks any title resemblance, and
normalization must never fold away substantive words.
"""

from __future__ import annotations

import pytest

from substrate.execution.attempts.field_task_scope import (
    BACKEND,
    FIXTURE_NODE_TITLES,
    FRONTEND,
    INTEGRATION,
    VERIFICATION,
    ScopeResolutionError,
    normalize_title,
    resolve_scenario_map,
)

_ROLE_TITLES = {
    BACKEND: "Add the note-search backend endpoint",
    FRONTEND: "Add the note-search frontend UI",
    INTEGRATION: "Integrate and reconcile the search branches",
    VERIFICATION: "Independently verify note search",
}


def _node(node_id: str, title: str, label: str | None = None) -> dict:
    n = {"node_id": node_id, "title": title, "kind": "packet"}
    if label is not None:
        n["semantic_label"] = label
    return n


def _packet(packet_id: str, node_id: str) -> dict:
    return {
        "packet_id": packet_id,
        "source_evidence": [{"type": "plan_node", "node_id": node_id}],
    }


def _canonical_plan() -> tuple[list[dict], list[dict]]:
    """A plan shaped exactly like the real failed run: labels + drifted titles."""
    roles = [BACKEND, FRONTEND, INTEGRATION, VERIFICATION]
    nodes = [_node(f"node-{i}", _ROLE_TITLES[r], r) for i, r in enumerate(roles)]
    # the two trailing non-task nodes the real plan also contains
    nodes.append(_node("node-x1", "Verify objective outcomes against desired state"))
    nodes.append(_node("node-x2", "Objective outcome accepted"))
    packets = [_packet(f"wp-{i}", f"node-{i}") for i in range(len(roles))]
    return nodes, packets


def _legacy_plan(titles: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """A pre-semantic_label plan: NO node carries a canonical label."""
    roles = [BACKEND, FRONTEND, INTEGRATION, VERIFICATION]
    nodes = [_node(f"node-{i}", titles[r]) for i, r in enumerate(roles)]
    packets = [_packet(f"wp-{i}", f"node-{i}") for i in range(len(roles))]
    return nodes, packets


# ── 1 + 5: canonical identity binds all four roles despite title drift ──────


def test_canonical_label_binds_all_four_roles_despite_title_drift():
    nodes, packets = _canonical_plan()
    m = resolve_scenario_map(plan_nodes=nodes, packets=packets)
    assert m == {
        BACKEND: "wp-0",
        FRONTEND: "wp-1",
        INTEGRATION: "wp-2",
        VERIFICATION: "wp-3",
    }


def test_canonical_label_ignores_capitalization_entirely():
    """Titles may be ANY case — the canonical key decides."""
    nodes, packets = _canonical_plan()
    for n in nodes:
        n["title"] = n["title"].upper()
    m = resolve_scenario_map(plan_nodes=nodes, packets=packets)
    assert m[BACKEND] == "wp-0"


def test_canonical_label_binds_even_with_completely_unrelated_titles():
    """The strongest form: titles carry no signal at all."""
    nodes, packets = _canonical_plan()
    for i, n in enumerate(nodes[:4]):
        n["title"] = f"zzz unrelated {i}"
    m = resolve_scenario_map(plan_nodes=nodes, packets=packets)
    assert m[BACKEND] == "wp-0" and m[VERIFICATION] == "wp-3"


# ── the canonical path is EXACT: near-miss labels must never bind ───────────
#
# Found by adversarial review: the primary path had no test distinguishing
# `==` from `in`/normalized comparison, so a substring mutant survived a green
# suite AND was exploitable — a decoy node labelled "legacy_backend_task_id_v2"
# would bind `backend_task_id`, targeting the wrong packet while reporting
# exactly one match. That is the threat model: a green run that proved nothing.


@pytest.mark.parametrize(
    "decoy_label,why",
    [
        ("legacy_backend_task_id_v2", "role is a SUBSTRING of the decoy label"),
        ("backend_task_id_v2", "decoy has the role as a prefix"),
        ("old_backend_task_id", "decoy has the role as a suffix"),
        ("BACKEND_TASK_ID", "case must NOT be folded on the canonical path"),
        ("backend task id", "spaces must NOT be folded on the canonical path"),
        ("backend-task-id", "hyphens must NOT be folded on the canonical path"),
        ("the backend_task_id", "articles must NOT be stripped on the canonical path"),
    ],
)
def test_near_miss_semantic_label_never_binds(decoy_label, why):
    """The canonical key is compared EXACTLY — never by substring or normalization."""
    nodes, packets = _canonical_plan()
    # remove the true backend node; leave a decoy carrying a near-miss label
    nodes = [n for n in nodes if n.get("semantic_label") != BACKEND]
    nodes.append(_node("node-decoy", "Decoy task", decoy_label))
    packets.append(_packet("wp-decoy", "node-decoy"))
    with pytest.raises(ScopeResolutionError) as exc:
        resolve_scenario_map(plan_nodes=nodes, packets=packets)
    msg = str(exc.value)
    assert "wp-decoy" not in msg, "the decoy packet must never be bound"
    assert BACKEND in msg, why


def test_semantic_label_whitespace_is_stripped_but_not_otherwise_folded():
    """`.strip()` is intended; any further folding is not."""
    nodes, packets = _canonical_plan()
    for n in nodes:
        if n.get("semantic_label") == BACKEND:
            n["semantic_label"] = f"  {BACKEND}  "
    m = resolve_scenario_map(plan_nodes=nodes, packets=packets)
    assert m[BACKEND] == "wp-0", "padded canonical labels must still bind"


# ── 2, 3, 4, 6: legacy fallback folds ONLY cosmetic variation ───────────────


@pytest.mark.parametrize(
    "variant,why",
    [
        ({k: v.title() for k, v in FIXTURE_NODE_TITLES.items()}, "capitalization"),
        (
            {
                BACKEND: "Add the note search backend endpoint",
                FRONTEND: "Add a note search frontend ui",
                INTEGRATION: "Integrate and reconcile search branches",
                VERIFICATION: "Independently verify note search",
            },
            "leading articles (the / a)",
        ),
        (
            {
                BACKEND: "add note-search backend endpoint",
                FRONTEND: "add note-search frontend-ui",
                INTEGRATION: "integrate and reconcile search-branches",
                VERIFICATION: "independently verify note-search",
            },
            "hyphen vs space",
        ),
        (
            {
                BACKEND: "  add   note  search   backend endpoint  ",
                FRONTEND: "add  note search frontend ui",
                INTEGRATION: "integrate  and reconcile search branches",
                VERIFICATION: "independently   verify note search",
            },
            "repeated whitespace",
        ),
        (
            {
                BACKEND: "Add note search backend endpoint.",
                FRONTEND: "'Add note search frontend ui'",
                INTEGRATION: "Integrate and reconcile search branches!",
                VERIFICATION: "(Independently verify note search)",
            },
            "surrounding punctuation",
        ),
        (FIXTURE_NODE_TITLES, "exact legacy titles still work"),
    ],
)
def test_legacy_fallback_folds_cosmetic_variation(variant, why):
    nodes, packets = _legacy_plan(variant)
    m = resolve_scenario_map(plan_nodes=nodes, packets=packets)
    assert m == {BACKEND: "wp-0", FRONTEND: "wp-1", INTEGRATION: "wp-2", VERIFICATION: "wp-3"}, why


# ── 7: a SUBSTANTIVE change must NOT match ──────────────────────────────────


@pytest.mark.parametrize(
    "bad_title,why",
    [
        ("add note search frontend endpoint", "backend->frontend is substantive"),
        ("add note search backend", "dropping 'endpoint' is substantive"),
        ("remove note search backend endpoint", "add->remove is substantive"),
        ("add note filter backend endpoint", "search->filter is substantive"),
    ],
)
def test_substantive_title_change_does_not_match(bad_title, why):
    titles = dict(FIXTURE_NODE_TITLES)
    nodes, packets = _legacy_plan(titles)
    nodes[0]["title"] = bad_title
    with pytest.raises(ScopeResolutionError) as exc:
        resolve_scenario_map(plan_nodes=nodes, packets=packets)
    assert "matched 0 plan nodes" in str(exc.value), why


def test_fallback_never_matches_by_substring():
    """A node whose title CONTAINS the wanted title must not bind the role.

    Substring matching is the most dangerous relaxation: the fixture title is a
    prefix of many plausible longer titles, so `in` would bind a role to a
    different, larger Task while still reporting exactly one match.
    """
    titles = dict(FIXTURE_NODE_TITLES)
    nodes, packets = _legacy_plan(titles)
    # The real backend node is REMOVED; a superset-titled node remains.
    nodes[0]["title"] = FIXTURE_NODE_TITLES[BACKEND] + " and also the frontend ui"
    with pytest.raises(ScopeResolutionError) as exc:
        resolve_scenario_map(plan_nodes=nodes, packets=packets)
    assert "matched 0 plan nodes" in str(exc.value), (
        "a superset title must NOT satisfy the role — that is substring matching"
    )


def test_fallback_never_matches_when_wanted_contains_node_title():
    """The reverse direction: a node title that is a substring of the wanted."""
    titles = dict(FIXTURE_NODE_TITLES)
    nodes, packets = _legacy_plan(titles)
    nodes[0]["title"] = "add note search"  # strict prefix of the wanted title
    with pytest.raises(ScopeResolutionError) as exc:
        resolve_scenario_map(plan_nodes=nodes, packets=packets)
    assert "matched 0 plan nodes" in str(exc.value)


# ── 8: two nodes collapsing to one normalized identity fails CLOSED ─────────


def test_normalized_collision_fails_closed():
    titles = dict(FIXTURE_NODE_TITLES)
    nodes, packets = _legacy_plan(titles)
    # a second node whose title normalizes identically to the backend title
    nodes.append(_node("node-dup", "The Add-Note-Search-Backend-Endpoint"))
    packets.append(_packet("wp-dup", "node-dup"))
    with pytest.raises(ScopeResolutionError) as exc:
        resolve_scenario_map(plan_nodes=nodes, packets=packets)
    msg = str(exc.value)
    assert "collapsed" in msg and "ambiguous" in msg
    assert "node-0" in msg and "node-dup" in msg, "collision must name both nodes"


# ── 9: a missing role fails closed ──────────────────────────────────────────


def test_missing_role_fails_closed():
    nodes, packets = _canonical_plan()
    nodes = [n for n in nodes if n.get("semantic_label") != VERIFICATION]
    with pytest.raises(ScopeResolutionError) as exc:
        resolve_scenario_map(plan_nodes=nodes, packets=packets)
    assert VERIFICATION in str(exc.value)


# ── 10: a conflicting canonical key can NEVER fall back to a title ──────────


def test_wrong_semantic_key_cannot_fall_back_to_title():
    """A plan that declares machine roles is never re-resolved by display text.

    The backend node is mislabeled; its TITLE still matches the fixture. Falling
    back would bind `backend_task_id` to a node the planner labelled otherwise —
    silently targeting the wrong Task.
    """
    nodes, packets = _canonical_plan()
    nodes[0]["semantic_label"] = "some_other_role"
    nodes[0]["title"] = FIXTURE_NODE_TITLES[BACKEND]  # exact legacy title
    with pytest.raises(ScopeResolutionError) as exc:
        resolve_scenario_map(plan_nodes=nodes, packets=packets)
    msg = str(exc.value)
    assert "refusing to fall back" in msg
    assert "declares machine roles" in msg


# ── 11: the map stores real packet ids, never display text ─────────────────


def test_map_stores_packet_ids_not_titles():
    nodes, packets = _canonical_plan()
    m = resolve_scenario_map(plan_nodes=nodes, packets=packets)
    for label, value in m.items():
        assert value.startswith("wp-"), f"{label} stored {value!r}, not a packet id"
        assert "note" not in value.lower(), "display text leaked into the map"


# ── 12: the designated failure stays bound to the intended backend Task ────


def test_failure_target_binds_to_the_intended_backend_task():
    nodes, packets = _canonical_plan()
    m = resolve_scenario_map(plan_nodes=nodes, packets=packets)
    backend_node = next(n for n in nodes if n.get("semantic_label") == BACKEND)
    expected = next(
        p["packet_id"]
        for p in packets
        if p["source_evidence"][0]["node_id"] == backend_node["node_id"]
    )
    assert m[BACKEND] == expected


# ── 13: no packet may be resolved without real lineage ─────────────────────


def test_role_without_materialized_packet_fails_closed():
    nodes, packets = _canonical_plan()
    packets = [p for p in packets if p["packet_id"] != "wp-0"]
    with pytest.raises(ScopeResolutionError) as exc:
        resolve_scenario_map(plan_nodes=nodes, packets=packets)
    assert "materialized no" in str(exc.value)


def test_duplicate_packet_for_one_node_still_fails_closed():
    """Pre-existing cardinality guarantee must survive the change."""
    nodes, packets = _canonical_plan()
    packets.append(_packet("wp-dupe", "node-0"))
    with pytest.raises(ScopeResolutionError) as exc:
        resolve_scenario_map(plan_nodes=nodes, packets=packets)
    assert "more than one packet record" in str(exc.value)


# ── normalization unit properties ──────────────────────────────────────────


@pytest.mark.parametrize(
    "a,b",
    [
        ("Add the note-search backend endpoint", "add note search backend endpoint"),
        ("  A  Note   Search ", "note search"),
        ("note_search-ui", "note search ui"),
        ("(Verify) note search!", "verify note search"),
    ],
)
def test_normalize_folds_only_cosmetics(a, b):
    assert normalize_title(a) == normalize_title(b)


@pytest.mark.parametrize(
    "a,b",
    [
        ("add backend endpoint", "add frontend endpoint"),
        ("verify note search", "verify note searches"),  # no stemming
        ("integrate branches", "integrate"),  # no substring
        # 'theme' merely STARTS with "the" — it is substantive and must survive
        ("theme parser", "parser"),
    ],
)
def test_normalize_keeps_substantive_differences(a, b):
    assert normalize_title(a) != normalize_title(b)


def test_vacuous_normalized_title_is_refused():
    """A configured title normalizing to '' must not bind by empty equality.

    Found by adversarial review: node_titles={BACKEND: "a"} against a node
    titled "The" made both sides normalize to "" — exactly one match, so the
    collision guard never fired, and two unrelated strings bound a role.
    """
    nodes, packets = _legacy_plan(dict(FIXTURE_NODE_TITLES))
    nodes[0]["title"] = "The"
    with pytest.raises(ScopeResolutionError) as exc:
        resolve_scenario_map(
            plan_nodes=nodes, packets=packets, node_titles={**FIXTURE_NODE_TITLES, BACKEND: "a"}
        )
    msg = str(exc.value)
    assert "empty string" in msg or "matched 0" in msg
    assert "wp-0" not in msg, "a vacuous match must never bind a packet"


def test_node_with_empty_normalized_title_is_never_a_candidate():
    """A node whose own title normalizes to '' must not satisfy any role."""
    nodes, packets = _legacy_plan(dict(FIXTURE_NODE_TITLES))
    nodes[0]["title"] = "the"  # normalizes to ""
    with pytest.raises(ScopeResolutionError) as exc:
        resolve_scenario_map(plan_nodes=nodes, packets=packets)
    assert "matched 0 plan nodes" in str(exc.value)


def test_every_bind_is_logged_with_all_required_fields(caplog):
    """Observability is a contract, not a courtesy — deleting it must fail."""
    import logging

    nodes, packets = _canonical_plan()
    with caplog.at_level(logging.INFO, logger="substrate.execution.attempts.field_task_scope"):
        resolve_scenario_map(plan_nodes=nodes, packets=packets)
    binds = [r.getMessage() for r in caplog.records if "scenario-map bind:" in r.getMessage()]
    assert len(binds) == 4, f"expected one log line per role, got {len(binds)}"
    for role, packet in ((BACKEND, "wp-0"), (VERIFICATION, "wp-3")):
        line = next(b for b in binds if f"role={role}" in b)
        for field in (
            "method=",
            "node_id=",
            "packet_id=",
            "candidates=",
            "raw_title=",
            "normalized=",
        ):
            assert field in line, f"{role} bind log missing {field}"
        assert f"packet_id={packet}" in line
        assert "candidates=1" in line


def test_logged_candidate_count_is_computed_not_hardcoded(caplog, monkeypatch):
    """Pin that the count comes from the real match list.

    Asserting `candidates=1` alone cannot distinguish a computed value from a
    literal, since every successful bind resolves exactly one node. Patch the
    formatter to capture the ARGUMENT actually passed.
    """
    import logging

    import substrate.execution.attempts.field_task_scope as fts

    seen: list[object] = []
    real_info = fts.logger.info

    def _spy(msg, *args, **kwargs):
        if isinstance(msg, str) and "scenario-map bind" in msg:
            seen.append(args)
        return real_info(msg, *args, **kwargs)

    monkeypatch.setattr(fts.logger, "info", _spy)
    nodes, packets = _canonical_plan()
    with caplog.at_level(logging.INFO):
        resolve_scenario_map(plan_nodes=nodes, packets=packets)

    assert len(seen) == 4, "one bind log per role"
    for args in seen:
        # (label, method, node_id, packet_id, candidates, raw_title, normalized)
        assert isinstance(args[4], int), (
            f"candidate count must be a computed int, got {type(args[4]).__name__}"
        )
        assert args[4] == 1


def test_normalize_drops_articles_as_whole_words_only():
    """Articles are folded wherever they appear, but only as WHOLE words."""
    assert normalize_title("Add the note-search backend endpoint") == (
        "add note search backend endpoint"
    )
    # a word that merely BEGINS with an article is substantive and survives
    assert normalize_title("theme announcer analysis") == "theme announcer analysis"
    assert normalize_title("the theme") == "theme"
