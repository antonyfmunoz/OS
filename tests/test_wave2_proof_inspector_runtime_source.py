"""Wave 2 — proof-inspector reads the canonical execution proof runtime.

Root cause (invocation #53, w16): the proof-inspector routes read the legacy
organism ProofStore (``UMH_ROOT/data/runtime/proof_packages.jsonl``) while the
governed execution system persists proofs through ProofRuntime into the
runtime state dir (``UMH_STATE_DIR/organism/proof_packages.jsonl``). Inside a
candidate container (``UMH_ROOT=/app`` read-only, ``UMH_STATE_DIR=/state/umh``)
the legacy file does not exist, so every execution proof 404'd and the field
collector could not observe the composition proof.

These tests pin the corrected wiring:
  - a proof written through ProofRuntime is served by the endpoint;
  - the candidate-container shape (no legacy file, read-only UMH_ROOT)
    observes a real execution proof from the canonical state dir;
  - legacy ProofStore packages are still served (fallback preserved);
  - reverting the route to ProofStore-only fails these tests (mutation kill).
"""

from __future__ import annotations

import os
import stat

import pytest

pytest.importorskip("fastapi")
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Candidate-container-shaped env: worktree root + separate state dir."""
    import substrate.organism.proof_store as ps_mod

    app_root = tmp_path / "app"
    state_dir = tmp_path / "state" / "umh"
    app_root.mkdir()
    state_dir.mkdir(parents=True)

    monkeypatch.setenv("UMH_ROOT", str(app_root))
    monkeypatch.setenv("UMH_STATE_DIR", str(state_dir))
    # ProofStore resolves its paths at import time — repoint the module
    # constants at the candidate-shaped location and drop the singleton so
    # each test observes the env it configured.
    monkeypatch.setattr(
        ps_mod, "_STORE_PATH", app_root / "data" / "runtime" / "proof_packages.jsonl"
    )
    monkeypatch.setattr(ps_mod, "_EVIDENCE_DIR", app_root / "data" / "runtime" / "proof_evidence")
    monkeypatch.setattr(ps_mod, "_store_instance", None)
    return app_root, state_dir


@pytest.fixture()
def client(env):
    import transports.api.cockpit_proof_inspector_routes as pir

    app = FastAPI()
    pir.configure(require_operator_dep=lambda: None)
    app.include_router(pir.proof_inspector_router, prefix="/api/umh")
    return TestClient(app)


def _write_runtime_proof():
    from substrate.organism.proof_runtime import ProofRuntime

    rt = ProofRuntime()
    return rt.create_direct(
        work_id="wp-f0e194753775",
        action={
            "attempt_id": "ea-68f8be51abfe",
            "predecessor_commits": {"wp-a": "a" * 40, "wp-b": "b" * 40},
            "composed_commit": "c" * 40,
        },
        outcome="success",
    )


def test_runtime_proof_served_by_package_detail(env, client):
    """A proof persisted through ProofRuntime is returned by the endpoint.

    Mutation kill: reverting _get_proof_store() to the legacy ProofStore makes
    this 404 — the legacy file does not exist in this env.
    """
    pkg = _write_runtime_proof()
    resp = client.get(f"/api/umh/proof-inspector/packages/{pkg.proof_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["proof_id"] == pkg.proof_id
    # The exact field the field collector's w16 composition check reads.
    assert body["action"]["predecessor_commits"] == {"wp-a": "a" * 40, "wp-b": "b" * 40}
    assert body["outcome"] == "success"


def test_candidate_container_shape_observes_execution_proof(env, client):
    """Read-only UMH_ROOT with no legacy file: proof still observable.

    This is the exact shape that failed in the field: the worktree mount has
    no data/runtime/proof_packages.jsonl and cannot be written.
    """
    app_root, state_dir = env
    pkg = _write_runtime_proof()

    # The proof landed in the canonical runtime state dir, not under UMH_ROOT.
    assert (state_dir / "organism" / "proof_packages.jsonl").exists()
    assert not (app_root / "data" / "runtime" / "proof_packages.jsonl").exists()

    # Make the worktree root read-only like the container's /app:ro mount.
    app_root.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        resp = client.get(f"/api/umh/proof-inspector/packages/{pkg.proof_id}")
        assert resp.status_code == 200
        assert resp.json()["action"]["composed_commit"] == "c" * 40
    finally:
        app_root.chmod(stat.S_IRWXU)


def test_runtime_proof_visible_across_processes(env, client):
    """A proof written by ANOTHER ProofRuntime instance (another process, in
    the field) is served without a restart — the route re-reads the durable
    store per request instead of caching a stale singleton."""
    first = client.get("/api/umh/proof-inspector/summary")
    assert first.status_code == 200
    pkg = _write_runtime_proof()  # separate ProofRuntime instance
    resp = client.get(f"/api/umh/proof-inspector/packages/{pkg.proof_id}")
    assert resp.status_code == 200


def test_legacy_proof_store_fallback_preserved(env, client):
    """Legacy organism proofs remain readable through the same endpoint."""
    import substrate.organism.proof_store as ps_mod

    legacy = ps_mod.get_proof_store()
    pkg = legacy.create(execution_id="exec-1", description="legacy proof")
    resp = client.get(f"/api/umh/proof-inspector/packages/{pkg.proof_id}")
    assert resp.status_code == 200
    assert resp.json()["execution_id"] == "exec-1"

    # Review mutation path still resolves legacy proofs.
    import transports.api.cockpit_proof_inspector_routes as pir

    source = pir._get_proof_store()
    assert source.approve(pkg.proof_id, notes="ok") is not None


def test_listing_and_summary_remain_legacy_only(env, client):
    """Scope bound: runtime proofs resolve by id ONLY. The listing and summary
    keep the legacy wire shape (status/created_at) the cockpit panel renders —
    merging runtime packages (outcome/timestamp) corrupts it (Invalid Date,
    unfilterable rows, irreconcilable totals)."""
    import substrate.organism.proof_store as ps_mod

    runtime_pkg = _write_runtime_proof()
    legacy_pkg = ps_mod.get_proof_store().create(description="legacy")

    listing = client.get("/api/umh/proof-inspector/packages")
    assert listing.status_code == 200
    ids = [p["proof_id"] for p in listing.json()["packages"]]
    assert legacy_pkg.proof_id in ids
    assert runtime_pkg.proof_id not in ids
    for row in listing.json()["packages"]:
        assert "status" in row and "created_at" in row  # panel contract

    summary = client.get("/api/umh/proof-inspector/summary").json()
    assert summary["total"] == 1  # legacy only — totals reconcile with panel
    assert "success" not in summary["by_status"]

    # But the runtime proof still resolves by id — the w16 read.
    assert (
        client.get(f"/api/umh/proof-inspector/packages/{runtime_pkg.proof_id}").status_code == 200
    )


def test_runtime_wins_on_proof_id_collision(env, client):
    """Pins the class's load-bearing ordering claim: get() consults the
    canonical runtime FIRST. Plant the same proof_id in both stores and assert
    the runtime shape (action present, no legacy execution_id) is returned —
    an inverted lookup order would serve the legacy shadow instead."""
    import substrate.organism.proof_store as ps_mod

    pkg = _write_runtime_proof()
    legacy = ps_mod.get_proof_store()
    shadow = ps_mod.ProofPackage(
        proof_id=pkg.proof_id, execution_id="exec-shadow", description="legacy shadow"
    )
    legacy._packages.append(shadow)
    legacy._by_id[pkg.proof_id] = shadow

    body = client.get(f"/api/umh/proof-inspector/packages/{pkg.proof_id}").json()
    assert body["action"]["composed_commit"] == "c" * 40  # runtime package
    assert "execution_id" not in body  # not the legacy shadow's shape


def test_read_path_serves_proof_even_when_mkdir_impossible(env, client, monkeypatch):
    """The read path must never depend on a directory write. Forces every
    Path.mkdir to raise (chmod is unreliable: the suite may run as root, which
    bypasses mode bits) and asserts an already-durable execution proof is
    still served — a failed mkdir must not silently degrade to legacy-only,
    which is the exact invocation-#53 failure shape."""
    from pathlib import Path

    pkg = _write_runtime_proof()  # durable before writes are forbidden

    def _forbidden(self, *a, **kw):
        raise OSError(30, "Read-only file system", str(self))

    monkeypatch.setattr(Path, "mkdir", _forbidden)
    resp = client.get(f"/api/umh/proof-inspector/packages/{pkg.proof_id}")
    assert resp.status_code == 200
    assert resp.json()["action"]["predecessor_commits"]["wp-a"] == "a" * 40


def test_read_path_creates_no_directories(env, client):
    """GET requests must leave the state dir untouched — a read surface that
    mkdirs on every request mutates runtime state as a side effect."""
    _, state_dir = env
    organism_dir = state_dir / "organism"
    assert not organism_dir.exists()
    for path in (
        "/api/umh/proof-inspector/summary",
        "/api/umh/proof-inspector/packages",
        "/api/umh/proof-inspector/packages/proof-nope",
        "/api/umh/proof-inspector/artifacts",
    ):
        client.get(path)
    assert not organism_dir.exists()


def test_runtime_proof_sub_routes_never_500(env, client):
    """timeline/evidence/raw tolerate runtime packages, which lack the legacy
    attributes (execution_id, evidence_dir, browser_evidence)."""
    pkg = _write_runtime_proof()
    for sub in ("timeline", "evidence", "raw"):
        resp = client.get(f"/api/umh/proof-inspector/packages/{pkg.proof_id}/{sub}")
        assert resp.status_code == 200, sub
    evidence = client.get(f"/api/umh/proof-inspector/packages/{pkg.proof_id}/evidence").json()
    assert evidence["browser_evidence"] == []
    assert evidence["verification_results"] == []


def test_missing_proof_still_404(env, client):
    resp = client.get("/api/umh/proof-inspector/packages/proof-does-not-exist")
    assert resp.status_code == 404


def test_route_reads_canonical_state_dir_not_umh_root(env, client):
    """Direct wrong-source guard: a proof planted ONLY in the legacy location
    is served via fallback, and a proof ONLY in the state dir is served via
    the runtime — both sources resolve, runtime first."""
    import transports.api.cockpit_proof_inspector_routes as pir

    source = pir._get_proof_store()
    assert source is not None
    assert source._runtime is not None, "canonical ProofRuntime must be wired"
    assert os.environ["UMH_STATE_DIR"] in str(source._runtime._store_path)
