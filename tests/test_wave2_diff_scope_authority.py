"""Wave 2 C-1 — diff-scope authority is real, sourced, and CAN fail.

The repaired check is exercised against a REAL git worktree with REAL changes,
because the defect it replaces was invisible to every stub-based test: the lease
recorded ``writable_paths=[<absolute worktree>]``, which normalized to ``"."`` →
``whole_worktree=True`` → ``scope_ok=True`` unconditionally. The computed
``outside`` list was discarded. A worker rewriting the fixture's own tests earned
a valid AttemptProof.

MUTATION DISCIPLINE: each rejection test is paired with a control proving the
same harness passes for in-scope work. Without the control, a check that rejects
EVERYTHING would look identical to a correct one.
"""

from __future__ import annotations

import os
import subprocess
from types import SimpleNamespace

import pytest

from substrate.execution.attempts.field_task_scope import (
    BACKEND,
    VERIFICATION,
    ScopeResolutionError,
    allowed_paths_for,
    normalize_allowed_paths,
    paths_outside,
    resolve_scenario_map,
)
from substrate.execution.attempts.verification import verify_attempt


def _git(*args: str, cwd: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture()
def worktree(tmp_path):
    """A real git repo with the fixture's shape and one base commit."""
    root = tmp_path / "wt"
    (root / "app" / "static").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "app" / "main.py").write_text("# base\n", encoding="utf-8")
    (root / "app" / "store.py").write_text("# base\n", encoding="utf-8")
    (root / "tests" / "test_api.py").write_text("def test_base(): pass\n", encoding="utf-8")
    _git("init", "-q", cwd=str(root))
    _git("config", "user.email", "t@example.com", cwd=str(root))
    _git("config", "user.name", "t", cwd=str(root))
    _git("add", "-A", cwd=str(root))
    _git("commit", "-q", "-m", "base", cwd=str(root))
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(root), capture_output=True, text=True
    ).stdout.strip()
    return SimpleNamespace(path=str(root), base=base)


def _lease(worktree):
    return SimpleNamespace(
        worktree_path=worktree.path,
        snapshot_ref=worktree.base,
        # Deliberately the OLD self-nullifying value: the repair must ignore it.
        writable_paths=[worktree.path],
    )


def _packet(allowed):
    return SimpleNamespace(
        packet_id="wp-abc123def456",
        requirements={"writable_path_scope": allowed, "scope_declared": True},
    )


def _verify(worktree, *, packet, files=("app/main.py",)):
    return verify_attempt(
        attempt=SimpleNamespace(
            attempt_id="ea-1",
            task_id="wp-abc123def456",
            instruction_package_hash="h1",
            worker_identity="worker-1",
            tenant_id="t",
            plan_record_id="opr-1",
            plan_version=1,
            attempt_number=1,
            assignment_id="asn-1",
            lease_id="l-1",
        ),
        assignment=SimpleNamespace(worker_identity="worker-1"),
        lease=_lease(worktree),
        worker_result=SimpleNamespace(files_changed=list(files), commits=["abc in-scope"]),
        package_hash="h1",
        verifier_identity="verifier:v1",
        verifier_role_id="role-verify",
        packet=packet,
    )


def _scope_check(verdict):
    return next(c for c in verdict.checks if c["check_id"] == "diff_scope")


# ── the control: in-scope work passes ───────────────────────────────────────


def test_in_scope_change_passes(worktree):
    """CONTROL. Without this, the rejection tests below prove nothing — a check
    that fails everything would satisfy them all."""
    with open(os.path.join(worktree.path, "app", "main.py"), "a", encoding="utf-8") as f:
        f.write("# search endpoint\n")
    verdict = _verify(worktree, packet=_packet(["app/main.py", "app/store.py"]))
    check = _scope_check(verdict)
    assert check["ok"] is True, check["detail"]


# ── the defect: out-of-scope work must FAIL ─────────────────────────────────


def test_rewriting_the_fixtures_own_tests_fails(worktree):
    """The exact C-1 exploit: a worker edits the pre-existing test to make its
    own change pass. Under the old code this earned a valid AttemptProof."""
    with open(os.path.join(worktree.path, "tests", "test_api.py"), "w", encoding="utf-8") as f:
        f.write("def test_base(): assert True  # neutered\n")
    verdict = _verify(worktree, packet=_packet(["app/main.py", "app/store.py"]))
    check = _scope_check(verdict)
    assert check["ok"] is False
    assert "tests/test_api.py" in check["detail"]
    assert verdict.passed is False
    assert verdict.proof_id == "", "a scope violation must never mint a Proof"


def test_untracked_file_outside_scope_fails(worktree):
    """A NEW file leaves no trace in `git diff <base>` — it must still count."""
    with open(os.path.join(worktree.path, "app", "backdoor.py"), "w", encoding="utf-8") as f:
        f.write("# not authorized\n")
    check = _scope_check(_verify(worktree, packet=_packet(["app/main.py"])))
    assert check["ok"] is False
    assert "backdoor" in check["detail"]


def test_whole_worktree_lease_entry_does_not_authorize_anything(worktree):
    """The regression itself: the lease's absolute worktree path must NOT be
    read as a scope. The packet is the authority."""
    with open(os.path.join(worktree.path, "tests", "test_api.py"), "a", encoding="utf-8") as f:
        f.write("# touched\n")
    # lease.writable_paths == [<absolute worktree>] (see _lease) — the old
    # normalization turned exactly this into a blanket pass.
    check = _scope_check(_verify(worktree, packet=_packet(["app/main.py"])))
    assert check["ok"] is False


def test_verifier_zero_diff_is_enforced(worktree):
    """An EMPTY allowlist means no path may change — distinct from '.'."""
    with open(os.path.join(worktree.path, "app", "main.py"), "a", encoding="utf-8") as f:
        f.write("# verifier must not write\n")
    check = _scope_check(_verify(worktree, packet=_packet([])))
    assert check["ok"] is False, "the verifier's zero-diff requirement must be enforced"


def test_clean_worktree_with_empty_allowlist_passes(worktree):
    """CONTROL for the zero-diff rule: an untouched worktree satisfies it."""
    check = _scope_check(_verify(worktree, packet=_packet([])))
    assert check["ok"] is True, check["detail"]


# ── fail-closed on unusable inputs ──────────────────────────────────────────


def test_absent_packet_fails_closed(worktree):
    check = _scope_check(_verify(worktree, packet=None))
    assert check["ok"] is False
    assert "cannot be resolved" in check["detail"] or "unverifiable" in check["detail"]


def test_uninspectable_worktree_cannot_pass_on_worker_self_report(tmp_path):
    """A verdict may never rest on the worker's own file list."""
    lease = SimpleNamespace(
        worktree_path=str(tmp_path / "gone"), snapshot_ref="", writable_paths=[]
    )
    verdict = verify_attempt(
        attempt=SimpleNamespace(
            attempt_id="ea-1",
            task_id="wp-x",
            instruction_package_hash="h1",
            worker_identity="w",
            tenant_id="t",
            plan_record_id="opr-1",
            plan_version=1,
            attempt_number=1,
            assignment_id="a",
            lease_id="l",
        ),
        assignment=SimpleNamespace(worker_identity="w"),
        lease=lease,
        worker_result=SimpleNamespace(files_changed=["app/main.py"], commits=["c"]),
        package_hash="h1",
        verifier_identity="verifier:v1",
        verifier_role_id="r",
        packet=_packet(["app/main.py"]),
    )
    check = _scope_check(verdict)
    assert check["ok"] is False
    assert "independently" in check["detail"]


# ── path-policy normalization rejects unsafe scopes ─────────────────────────


@pytest.mark.parametrize("bad", [".", "", "/etc/passwd", "..", "../escape"])
def test_unsafe_path_policies_are_rejected(bad, tmp_path):
    with pytest.raises(ScopeResolutionError):
        normalize_allowed_paths([bad], lease_root=str(tmp_path))


def test_normalization_keeps_legitimate_relative_paths(tmp_path):
    """CONTROL: the rejections above are not simply rejecting everything."""
    assert normalize_allowed_paths(
        ["app/main.py", "app/static/", "./tests/test_x.py"], lease_root=str(tmp_path)
    ) == ["app/main.py", "app/static", "tests/test_x.py"]


def test_packet_without_declared_scope_refuses_implicit_everything():
    with pytest.raises(ScopeResolutionError):
        allowed_paths_for(SimpleNamespace(packet_id="wp-1", requirements={}), semantic_label="")


def test_prefix_match_does_not_leak_sibling_directories():
    """`app/static` must not authorize `app/static_secrets`."""
    assert paths_outside(["app/static_secrets/k.txt"], ["app/static"]) == [
        "app/static_secrets/k.txt"
    ]
    assert paths_outside(["app/static/app.js"], ["app/static"]) == []


# ── C-3: scenario map resolves through canonical plan-node lineage ──────────


def _node(node_id, title):
    return {"node_id": node_id, "title": title, "kind": "packet"}


def _pkt(pid, node_id):
    return {
        "packet_id": pid,
        "source_evidence": [{"type": "plan_node", "node_id": node_id}],
    }


def _fixture_plan():
    nodes = [
        _node("node-1", "Add note search backend endpoint"),
        _node("node-2", "Add note search frontend UI"),
        _node("node-3", "Integrate and reconcile search branches"),
        _node("node-4", "Independently verify note search"),
    ]
    packets = [
        _pkt("wp-aaaaaaaaaaaa", "node-1"),
        _pkt("wp-bbbbbbbbbbbb", "node-2"),
        _pkt("wp-cccccccccccc", "node-3"),
        _pkt("wp-dddddddddddd", "node-4"),
    ]
    return nodes, packets


def test_scenario_map_resolves_exact_packet_ids():
    nodes, packets = _fixture_plan()
    mapping = resolve_scenario_map(plan_nodes=nodes, packets=packets)
    assert mapping[BACKEND] == "wp-aaaaaaaaaaaa"
    assert mapping[VERIFICATION] == "wp-dddddddddddd"


def test_scenario_map_fails_closed_when_a_node_materialized_no_packet():
    nodes, packets = _fixture_plan()
    packets = [p for p in packets if p["packet_id"] != "wp-aaaaaaaaaaaa"]
    with pytest.raises(ScopeResolutionError, match="materialized no WorkPacket"):
        resolve_scenario_map(plan_nodes=nodes, packets=packets)


def test_scenario_map_fails_closed_on_ambiguous_titles():
    nodes, packets = _fixture_plan()
    nodes.append(_node("node-9", "Add note search backend endpoint"))
    with pytest.raises(ScopeResolutionError, match="matched 2 plan nodes"):
        resolve_scenario_map(plan_nodes=nodes, packets=packets)


def test_scenario_map_never_pattern_matches_ids():
    """The C-3 defect was `tid.endswith("-a")`. Real ids are `wp-<hex12>` and
    contain no such marker; resolution must work purely through lineage."""
    nodes, packets = _fixture_plan()
    mapping = resolve_scenario_map(plan_nodes=nodes, packets=packets)
    for packet_id in mapping.values():
        assert packet_id.startswith("wp-")
        assert "-" not in packet_id[3:], "a real wp-<hex12> id carries no suffix to match on"


# ── the fixture contract must name paths that actually exist ────────────────


def test_objective_contract_paths_match_the_generated_tree(tmp_path):
    """The OBJECTIVE.md contract is quoted verbatim into the worker's package.

    It said `static/index.html` while the generator writes `app/static/index.html`
    — so a worker obeying the contract would create a NEW top-level `static/`
    dir, which the served app never reads and which the authorized scope
    (`app/static`) rejects. The contract and the tree must agree.
    """
    import subprocess
    import sys

    dest = tmp_path / "fixture"
    subprocess.run(
        [
            sys.executable,
            "infra/fixture/make_fixture_app.py",
            "--dest",
            str(dest),
            "--variant",
            "clean",
        ],
        check=True,
        capture_output=True,
    )
    objective = (dest / "OBJECTIVE.md").read_text(encoding="utf-8")
    for declared in ("app/static/index.html", "app/static/app.js"):
        assert declared in objective, f"contract must name the real path {declared}"
        assert (dest / declared).exists(), f"generator must actually write {declared}"
    # The bare `static/...` spelling must not survive anywhere in the contract.
    for line in objective.splitlines():
        assert "`static/" not in line, f"stale bare-static path in contract: {line!r}"


def test_fixture_allowed_paths_exist_in_the_generated_tree(tmp_path):
    """Every authorized path prefix must correspond to something real, or the
    scope would authorize a location the app does not use."""
    import subprocess
    import sys

    from substrate.execution.attempts.field_task_scope import FIXTURE_ALLOWED_PATHS

    dest = tmp_path / "fixture"
    subprocess.run(
        [
            sys.executable,
            "infra/fixture/make_fixture_app.py",
            "--dest",
            str(dest),
            "--variant",
            "clean",
        ],
        check=True,
        capture_output=True,
    )
    for label, paths in FIXTURE_ALLOWED_PATHS.items():
        for p in paths:
            # A path is legitimate if it exists (app/main.py) or its parent dir
            # does (tests/test_search_api.py is created BY the worker).
            target = dest / p
            assert target.exists() or target.parent.is_dir(), (
                f"{label}: authorized path {p!r} has no home in the fixture tree"
            )


# ── BINDING: evidence is provenance, never mutation authority ───────────────
#
# Owner correction (R4c follow-up). WorkPacket.source_evidence may prove WHERE a
# scope came from; it must never CONTROL what a worker may write. Wave 1 fixed
# this split: `EvidenceRef` — "Evidence is provenance — it can never be a
# mutation authority"; `WorkScope` — "Always a typed field, never hidden in
# source_evidence". These tests pin that boundary for the writable-path scope.


def test_scope_authority_is_a_first_class_typed_field():
    """The authority lives on WorkRequirements, not in a loose dict key."""
    import dataclasses

    from substrate.contracts.work_context import WorkRequirements

    names = {f.name for f in dataclasses.fields(WorkRequirements)}
    assert "writable_path_scope" in names, "writable-path authority must be first-class"
    assert "scope_declared" in names, (
        "an undeclared scope must be distinguishable from a declared-empty one"
    )


def test_evidence_alone_can_never_grant_writable_authority():
    """THE binding rule: a packet whose ONLY scope signal is source_evidence has
    no authority. Editing descriptive evidence must not widen write permission."""
    evidence_only = SimpleNamespace(
        packet_id="wp-evidence-only",
        requirements={},  # no first-class contract
        source_evidence=[
            {"type": "plan_node", "node_id": "node-1"},
            # A forged evidence entry attempting to grant scope:
            {"type": "writable_path_scope", "paths": ["/", "app", "tests", ".."]},
        ],
    )
    with pytest.raises(ScopeResolutionError):
        allowed_paths_for(evidence_only)


def test_forged_evidence_scope_does_not_widen_a_declared_contract(worktree):
    """Evidence claiming a broader scope must not expand the persisted contract.

    The contract authorizes only `app/main.py`; the evidence claims the whole
    tree. The worker writes outside the contract. Verification must still fail.
    """
    with open(os.path.join(worktree.path, "tests", "test_api.py"), "a", encoding="utf-8") as f:
        f.write("# touched under a forged evidence claim\n")
    packet = SimpleNamespace(
        packet_id="wp-forged",
        requirements={"writable_path_scope": ["app/main.py"], "scope_declared": True},
        source_evidence=[{"type": "writable_path_scope", "paths": ["."]}],
    )
    check = _scope_check(_verify(worktree, packet=packet))
    assert check["ok"] is False, "evidence must never widen the persisted contract"
    assert "tests/test_api.py" in check["detail"]


def test_declared_empty_scope_is_distinct_from_undeclared():
    """`[]` + declared = zero-diff policy (valid). `[]` + undeclared = blocked."""
    declared_empty = SimpleNamespace(
        packet_id="wp-1", requirements={"writable_path_scope": [], "scope_declared": True}
    )
    assert allowed_paths_for(declared_empty) == []

    undeclared = SimpleNamespace(
        packet_id="wp-2", requirements={"writable_path_scope": [], "scope_declared": False}
    )
    with pytest.raises(ScopeResolutionError, match="scope_declared is False"):
        allowed_paths_for(undeclared)


def test_scope_module_never_reads_evidence_for_authority():
    """Source-level: the authority function must not consult source_evidence.

    Asserted against CODE, not prose — the docstring legitimately *explains* that
    evidence is never read, and a raw substring scan would match that explanation.
    (Third time this trap has appeared in this campaign; strip commentary first.)
    """
    import ast
    import inspect

    from substrate.execution.attempts import field_task_scope as fts

    tree = ast.parse(inspect.getsource(fts.allowed_paths_for).lstrip())
    fn = tree.body[0]
    # Drop the docstring, then render only executable statements back to source.
    body = fn.body[1:] if isinstance(fn.body[0], ast.Expr) else fn.body
    code = "\n".join(ast.unparse(node) for node in body)
    assert "source_evidence" not in code, (
        "allowed_paths_for must never read evidence — that is a provenance channel"
    )
    # And it must read the first-class contract fields.
    assert "writable_path_scope" in code and "scope_declared" in code


def test_contract_rejects_unsafe_scope_at_declaration_time():
    """An unsafe scope is refused at the CONTRACT, so it can never be persisted
    onto a Task and discovered only later at verification."""
    from substrate.contracts.work_context import WorkRequirements

    for bad in (".", "/etc", "../escape", ""):
        req = WorkRequirements()
        req.declare_writable_paths([bad])
        assert req.validate_writable_path_scope(), f"{bad!r} must be rejected by the contract"

    ok = WorkRequirements().declare_writable_paths(["app/main.py", "tests"])
    assert ok.validate_writable_path_scope() == [], "legitimate scope must validate clean"


def test_seeding_writes_authority_onto_the_contract():
    """Fixture defaults enter ONLY at materialization, producing a persisted
    first-class contract — never a verification-time fallback."""
    from substrate.contracts.work_context import WorkRequirements
    from substrate.execution.attempts.field_task_scope import seed_scope_from_label

    req = seed_scope_from_label(WorkRequirements(), BACKEND)
    assert req.scope_declared is True
    assert "app/main.py" in req.writable_path_scope
    assert req.validate_writable_path_scope() == []

    verifier = seed_scope_from_label(WorkRequirements(), VERIFICATION)
    assert verifier.scope_declared is True and verifier.writable_path_scope == []
