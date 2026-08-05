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


def test_normalize_drops_articles_as_whole_words_only():
    """Articles are folded wherever they appear, but only as WHOLE words."""
    assert normalize_title("Add the note-search backend endpoint") == (
        "add note search backend endpoint"
    )
    # a word that merely BEGINS with an article is substantive and survives
    assert normalize_title("theme announcer analysis") == "theme announcer analysis"
    assert normalize_title("the theme") == "theme"
