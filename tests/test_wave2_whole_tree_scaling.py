"""Regressions for the operation-scoped WorkGraph read (whole-tree blocker).

The defect: ``WorkReadinessRuntime.assess_all()`` classified N nodes, and each
node's dependency lookup called ``WorkGraph.dependencies_of()``, which performed
a COMPLETE re-read of every source store. A pass over N nodes therefore did
O(N) full-store collections (and another per dependency). Measured against the
live ~1,132-packet / 2.8 MB store, one ``strategic_context.health()`` operation
parsed 1,395,756 packet records in 150s WITHOUT completing a single readiness
pass — which is what left whole-tree shard_04 unable to finish.

The correction is operation-scoped consistency, NOT caching: ``assess_all()``
reads once at the start of the pass and threads that immutable view down through
classification. The view is a local, never stored on the instance, and dropped
when the call returns.

These tests pin BEHAVIOUR — collection counts observed from a real
``WorkReadinessRuntime`` driving a counting graph double — rather than source
text, which would survive the logic being reverted.
"""

from __future__ import annotations

from substrate.organism.work_readiness_runtime import WorkReadinessRuntime


class _Node:
    def __init__(self, node_id: str, dependencies: list[str], status: str = "in_progress"):
        self.node_id = node_id
        self.dependencies = dependencies
        self.status = status
        self.description = f"node {node_id}"


class _CountingGraph:
    """A WorkGraph-shaped double that counts full-store collections.

    Mirrors the real contract: ``dependencies_of`` resolves against an explicit
    snapshot when given one, and otherwise performs its own fresh collection.
    """

    def __init__(self, nodes: list[_Node]):
        self._nodes = nodes
        self.collect_count = 0

    def _collect(self) -> list[_Node]:
        self.collect_count += 1
        return list(self._nodes)

    def all_work(self) -> list[_Node]:
        return self._collect()

    def operation_snapshot(self) -> dict[str, _Node]:
        return {n.node_id: n for n in self._collect()}

    def dependencies_of(self, node_id: str, snapshot=None):
        all_nodes = snapshot if snapshot is not None else {n.node_id: n for n in self._collect()}
        target = all_nodes.get(node_id)
        if not target:
            return []
        return [all_nodes[d] for d in target.dependencies if d in all_nodes]


def _chain(n: int) -> list[_Node]:
    """A dependency chain — every node after the first has one dependency."""
    return [_Node(f"n{i}", [f"n{i - 1}"] if i else []) for i in range(n)]


def _runtime(nodes: list[_Node]) -> tuple[WorkReadinessRuntime, _CountingGraph]:
    graph = _CountingGraph(nodes)
    return WorkReadinessRuntime(work_graph=graph), graph


# ── the scaling property ─────────────────────────────────────────────


def test_collections_do_not_grow_with_node_count():
    """The load-bearing assertion: collections must be flat in N, not linear.

    Pre-correction this was 2N (50 / 100 / 200 / 400 for N = 25 / 50 / 100 /
    200). Any regression that re-reads per node reintroduces that growth and
    fails here.
    """
    counts = {}
    for n in (25, 50, 100, 200):
        runtime, graph = _runtime(_chain(n))
        runtime.assess_all()
        counts[n] = graph.collect_count

    assert counts[200] == counts[25], (
        f"collections grew with node count — per-node store reads are back: {counts}"
    )
    # Generous absolute ceiling: the pass needs a node list plus a snapshot.
    assert counts[200] <= 4, f"unexpected number of full-store collections: {counts}"


def test_one_pass_over_many_nodes_stays_bounded():
    runtime, graph = _runtime(_chain(300))
    runtime.assess_all()
    assert graph.collect_count <= 4, (
        f"300 nodes cost {graph.collect_count} full-store collections"
    )


# ── freshness: this is not a cache ───────────────────────────────────


def test_a_second_call_rereads_current_state():
    """No snapshot may survive a call — the next one must re-collect."""
    runtime, graph = _runtime(_chain(20))
    runtime.assess_all()
    after_first = graph.collect_count
    runtime.assess_all()
    assert graph.collect_count > after_first, (
        "second assess_all() did not re-read — a snapshot leaked across calls"
    )


def test_an_append_between_calls_is_visible_to_the_second_call():
    """Operation-scoped, not process-scoped: new records appear next call."""
    nodes = _chain(5)
    runtime, graph = _runtime(nodes)
    runtime.assess_all()
    nodes.append(_Node("n_new", []))
    second = runtime.assess_all()
    assert any(a.work_id == "n_new" for a in second), (
        "a record committed between calls was not observed by the next call"
    )


def test_independent_dependencies_of_still_reads_fresh():
    """The default path for every other caller must stay uncached."""
    _, graph = _runtime(_chain(10))
    before = graph.collect_count
    graph.dependencies_of("n1")
    assert graph.collect_count > before, (
        "dependencies_of() without an explicit snapshot stopped reading fresh state"
    )


# ── the REAL WorkGraph, not a double ─────────────────────────────────
#
# The tests above drive a graph double, which is right for measuring what the
# READINESS runtime does. But a double also means a mutation to the real
# WorkGraph.dependencies_of() cannot reach them — one survived exactly that way.
# These exercise the shipped implementation directly.


def _real_graph(nodes: list[_Node]):
    """A real WorkGraph whose collection is redirected to a fixed node list."""
    from substrate.organism.work_graph import WorkGraph

    graph = WorkGraph()
    calls = {"n": 0}

    def _collect():
        calls["n"] += 1
        return list(nodes)

    graph._collect_all = _collect  # type: ignore[method-assign]
    return graph, calls


def test_real_workgraph_honors_an_explicit_snapshot():
    """Given a snapshot, the real dependencies_of() must NOT re-collect.

    Kills the mutant that ignores the supplied snapshot and always rebuilds one
    — the exact regression that would restore per-node full-store reads.
    """
    nodes = _chain(12)
    graph, calls = _real_graph(nodes)

    snapshot = graph.operation_snapshot()
    collections_after_snapshot = calls["n"]

    for node in nodes:
        graph.dependencies_of(node.node_id, snapshot)

    assert calls["n"] == collections_after_snapshot, (
        f"dependencies_of() re-collected despite being given a snapshot "
        f"({calls['n'] - collections_after_snapshot} extra full-store reads)"
    )


def test_real_workgraph_without_snapshot_reads_fresh_every_call():
    """The default contract is unchanged: no snapshot means a fresh read."""
    nodes = _chain(5)
    graph, calls = _real_graph(nodes)

    before = calls["n"]
    graph.dependencies_of("n1")
    graph.dependencies_of("n2")
    assert calls["n"] == before + 2, (
        "independent dependencies_of() calls stopped reading fresh state"
    )


def test_real_workgraph_snapshot_and_fresh_paths_agree():
    """Same inputs, same answer — the snapshot path changes cost, not meaning."""
    nodes = _chain(15)
    graph, _ = _real_graph(nodes)
    snapshot = graph.operation_snapshot()

    for node in nodes:
        via_snapshot = [n.node_id for n in graph.dependencies_of(node.node_id, snapshot)]
        via_fresh = [n.node_id for n in graph.dependencies_of(node.node_id)]
        assert via_snapshot == via_fresh, f"divergent dependencies for {node.node_id}"


def test_real_workgraph_snapshot_is_a_fresh_object_each_time():
    nodes = _chain(6)
    graph, _ = _real_graph(nodes)
    assert graph.operation_snapshot() is not graph.operation_snapshot()


def test_no_snapshot_is_retained_on_the_runtime():
    """Nothing may be stashed on the instance between operations."""
    runtime, _ = _runtime(_chain(10))
    runtime.assess_all()
    leaked = [
        name
        for name, value in vars(runtime).items()
        if isinstance(value, dict) and value and all(isinstance(k, str) for k in value)
    ]
    assert "snapshot" not in " ".join(leaked).lower(), (
        f"an operation snapshot appears to be retained on the runtime: {leaked}"
    )


# ── semantics are unchanged ──────────────────────────────────────────


def test_results_are_identical_regardless_of_snapshot_path():
    """Same store → same assessments, whatever the read strategy."""
    runtime_a, _ = _runtime(_chain(30))
    runtime_b, _ = _runtime(_chain(30))
    a = [(x.work_id, x.status, tuple(sorted(x.blocking_reasons))) for x in runtime_a.assess_all()]
    b = [(x.work_id, x.status, tuple(sorted(x.blocking_reasons))) for x in runtime_b.assess_all()]
    assert a == b


def test_a_graph_returning_nothing_degrades_without_raising():
    """An empty graph must yield no assessments and must not raise.

    Note this deliberately supplies an EMPTY graph rather than ``None``:
    ``WorkReadinessRuntime(work_graph=None)`` lazily constructs a real
    WorkGraph, which reads the LIVE runtime store (observed: 1,171 packets).
    A unit test must never depend on production state, so the null case is
    modelled with a double instead.
    """
    runtime, _ = _runtime([])
    assert runtime.assess_all() == []


def test_graph_without_operation_snapshot_still_works():
    """A graph predating operation_snapshot() must keep working.

    Test doubles and any external implementation of the interface do not have
    the new method; the runtime must fall back to the ORIGINAL fresh-read path
    rather than assuming an empty snapshot, which would misclassify every
    dependency as missing.
    """

    class _LegacyGraph(_CountingGraph):
        operation_snapshot = None  # not callable

    graph = _LegacyGraph(_chain(10))
    runtime = WorkReadinessRuntime(work_graph=graph)
    results = runtime.assess_all()
    assert isinstance(results, list)


def test_a_failing_snapshot_falls_back_rather_than_emptying():
    """If the snapshot read raises, behaviour must degrade to fresh reads."""

    class _AngryGraph(_CountingGraph):
        def operation_snapshot(self):
            raise RuntimeError("store unavailable")

    graph = _AngryGraph(_chain(10))
    runtime = WorkReadinessRuntime(work_graph=graph)
    results = runtime.assess_all()
    assert isinstance(results, list)


def test_a_bad_snapshot_never_becomes_an_empty_view():
    """A failed/invalid snapshot must NOT be replaced by an empty dict.

    An empty snapshot is worse than no snapshot: every dependency lookup would
    miss, silently reclassifying satisfied dependencies as unresolved and
    turning a read problem into a wrong governance answer. The contract is
    "fall back to the original fresh-read path", so the helper returns ``None``
    — never ``{}``.

    Kills the mutant that returns an empty dict on a non-dict snapshot.
    """

    class _BadSnapshotGraph(_CountingGraph):
        def operation_snapshot(self):
            return "not a mapping"  # invalid shape

    graph = _BadSnapshotGraph(_chain(6))
    runtime = WorkReadinessRuntime(work_graph=graph)
    assert runtime._operation_snapshot() is None, (
        "an invalid snapshot must degrade to None (fresh reads), never to an "
        "empty view that would fabricate 'no dependencies'"
    )
    # And the pass must still classify the real nodes.
    assert isinstance(runtime.assess_all(), list)


def test_a_raising_snapshot_also_degrades_to_none():
    class _AngryGraph(_CountingGraph):
        def operation_snapshot(self):
            raise RuntimeError("store unavailable")

    runtime = WorkReadinessRuntime(work_graph=_AngryGraph(_chain(6)))
    assert runtime._operation_snapshot() is None


def test_each_pass_builds_a_distinct_snapshot_object():
    """Two passes must not share one snapshot instance.

    Object identity is the sharpest available signal that no cache was
    introduced: a memoised snapshot would hand back the SAME mapping, and a
    later pass would then be reasoning about a stale generation.

    Kills the mutant that stashes the snapshot on the instance and reuses it.
    """
    nodes = _chain(8)
    graph = _CountingGraph(nodes)
    runtime = WorkReadinessRuntime(work_graph=graph)

    first = runtime._operation_snapshot()
    second = runtime._operation_snapshot()
    assert first is not second, "the same snapshot object was reused across calls"

    # A record committed between passes must appear in the later snapshot.
    nodes.append(_Node("n_later", []))
    third = runtime._operation_snapshot()
    assert "n_later" in third, "a later snapshot did not observe newly committed state"
    assert "n_later" not in first, "an earlier snapshot mutated after the fact"


def test_no_operation_snapshot_attribute_is_left_on_the_runtime():
    """Nothing snapshot-shaped may persist on the instance after a pass.

    Complements the identity test: that one proves a fresh object per call,
    this one proves none is retained to be reused later.
    """
    runtime, _ = _runtime(_chain(8))
    before = set(vars(runtime))
    runtime.assess_all()
    added = set(vars(runtime)) - before
    assert not added, f"assess_all() left state on the runtime: {added}"
