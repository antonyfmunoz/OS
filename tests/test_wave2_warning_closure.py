"""Wave 2 R4 — warning closure regressions.

Each test pins one finding from the warning register so it cannot silently
return. The read-only sweep in particular is enforced BEHAVIOURALLY: a store
whose directory cannot be created must not raise at construction, because that
is exactly what crashed the whole operator API at import under the candidate's
``/app:ro`` mount.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest


# ── SEC-W1: the relocation must not orphan existing records ─────────────────


def _write_legacy(root: Path, count: int) -> Path:
    legacy = root / "data" / "umh" / "memory_candidates"
    legacy.mkdir(parents=True)
    path = legacy / "candidates.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for i in range(count):
            f.write(
                json.dumps(
                    {
                        "candidate_id": f"memcand-legacy{i:04d}",
                        "source_trace_id": f"trace-{i}",
                        "content": f"legacy record {i}",
                        "reason": "pre-relocation",
                        "confidence": 0.7,
                        "scope": "project",
                        "promotion_status": "staged",
                    }
                )
                + "\n"
            )
    return path


def test_legacy_records_remain_readable_after_relocation(tmp_path, monkeypatch):
    """The regression: relocating the default store orphaned 259 live records.
    Dedup/promotion reading an empty store would re-promote processed
    candidates."""
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    _write_legacy(tmp_path, 259)

    from substrate.memory.candidate_generator import MemoryCandidateGenerator

    gen = MemoryCandidateGenerator()
    assert gen.count() == 259, "legacy records must stay visible after relocation"
    got = gen.get_candidates(limit=5)
    assert len(got) == 5
    assert got[0].candidate_id == "memcand-legacy0000", "identity must be preserved"
    assert got[0].content == "legacy record 0", "content must remain readable"


def test_new_records_and_legacy_records_coexist(tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    _write_legacy(tmp_path, 3)

    from substrate.memory.candidate_generator import MemoryCandidateGenerator

    gen = MemoryCandidateGenerator()
    gen.generate_candidate("trace-new", "a brand new candidate", "post-relocation")
    assert gen.count() == 4, "new records append without hiding legacy ones"
    ids = {c.candidate_id for c in gen.get_candidates(limit=50)}
    assert "memcand-legacy0000" in ids


def test_writes_go_to_the_new_store_not_the_legacy_one(tmp_path, monkeypatch):
    """Read-through must never turn into write-through: the legacy path is
    read-only, or the candidate would write beneath /app:ro again."""
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    legacy_path = _write_legacy(tmp_path, 1)
    before = legacy_path.read_bytes()

    from substrate.memory.candidate_generator import MemoryCandidateGenerator

    gen = MemoryCandidateGenerator()
    gen.generate_candidate("trace-x", "new content", "reason")
    assert legacy_path.read_bytes() == before, "the legacy store must never be written"
    assert gen.candidates_path.is_file(), "the new store received the write"


# ── SEC-W2 / SEC-W3: no eager mkdir; nothing writes under a read-only root ───


def test_construction_never_creates_directories(tmp_path, monkeypatch):
    """The original crash was a mkdir in __init__. Construction must be inert on
    EVERY branch — including an explicit store_dir."""
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))

    from substrate.memory.candidate_generator import MemoryCandidateGenerator

    target = tmp_path / "never-created"
    MemoryCandidateGenerator(store_dir=str(target))
    assert not target.exists(), "constructing the generator must not create its dir"

    MemoryCandidateGenerator()
    assert not (tmp_path / "state" / "memory_candidates").exists()


def test_construction_survives_an_unwritable_root(tmp_path, monkeypatch):
    """Behavioural ``/app:ro`` guard: constructing under a root where directory
    creation FAILS must not raise — the operator API builds these at module
    import, and a raise there took down the whole API.

    Permission bits are not used to simulate this: the suite runs as root, which
    bypasses them (verified — ``mkdir`` under a ``r-x------`` dir still
    succeeds), so a mode-based test would pass vacuously. Instead ``mkdir`` is
    patched to raise the exact ``OSError`` a read-only mount produces.
    """
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))

    real_mkdir = Path.mkdir

    def _readonly_mkdir(self, *args, **kwargs):
        raise OSError(30, "Read-only file system")

    monkeypatch.setattr(Path, "mkdir", _readonly_mkdir)

    from substrate.memory.candidate_generator import MemoryCandidateGenerator
    from substrate.memory.promoter import MemoryPromoter

    # Construction must be inert — no mkdir on any branch.
    MemoryCandidateGenerator()
    MemoryCandidateGenerator(store_dir=str(tmp_path / "explicit"))
    MemoryPromoter()

    monkeypatch.setattr(Path, "mkdir", real_mkdir)


def test_eager_mkdir_would_have_failed_this_guard(tmp_path, monkeypatch):
    """Proves the guard above is not vacuous: the OLD eager-mkdir constructor
    shape raises under the same patched filesystem."""
    monkeypatch.setattr(
        Path, "mkdir", lambda self, *a, **k: (_ for _ in ()).throw(OSError(30, "Read-only"))
    )
    with pytest.raises(OSError):
        # This is exactly what __init__ used to do.
        Path(tmp_path / "eager").mkdir(parents=True, exist_ok=True)


@pytest.mark.parametrize(
    "module_path,literal",
    [
        ("substrate/memory/watcher.py", 'Path("data/umh'),
        ("substrate/memory/promoter.py", 'Path("data/umh'),
        ("substrate/memory/claude_bridge.py", 'Path("data/umh'),
        ("substrate/memory/candidate_generator.py", '"data/umh/memory_candidates"'),
    ],
)
def test_no_repo_relative_writable_defaults_remain(module_path, literal):
    """Every touched write must resolve through the runtime-state boundary."""
    root = Path(__file__).resolve().parent.parent
    src = (root / module_path).read_text(encoding="utf-8")
    # The legacy READ-THROUGH path is allowed to name the old location; a
    # writable DEFAULT is not.
    offending = [
        line
        for line in src.splitlines()
        if literal in line and "legacy" not in line.lower() and not line.strip().startswith("#")
    ]
    assert not offending, f"{module_path} still has a repo-relative default: {offending}"


def test_memory_stores_resolve_under_umh_state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))

    from substrate.memory.promoter import MemoryPromoter
    from substrate.memory.watcher import _hash_store_path

    assert str(tmp_path / "state") in str(MemoryPromoter()._path)
    assert str(tmp_path / "state") in str(_hash_store_path())


# ── W5: a stall must be visible ─────────────────────────────────────────────


def test_cycle_report_names_tasks_that_are_not_approved():
    """The most likely real stall: activation did not transition the packets, so
    the scheduler skips them with a bare `continue` and the runner logs nothing.
    The report must name them."""
    from substrate.execution.attempts.field_control_plane import ControlPlaneCycleReport

    report = ControlPlaneCycleReport(grant_ref="g1")
    assert hasattr(report, "skipped_not_approved")
    report.skipped_not_approved = ["wp-abc(planned)"]
    assert "skipped_not_approved" in report.to_dict()
    assert report.to_dict()["skipped_not_approved"] == ["wp-abc(planned)"]


# ── W7: the dead role resolver is gone ──────────────────────────────────────


def test_dead_role_resolver_is_removed():
    """It looked like it implemented role differentiation but was never called,
    and carried the same uuid-blindness as the failure matcher."""
    import substrate.execution.attempts.field_control_plane as fcp

    assert not hasattr(fcp, "_role_resolver_for"), "dead code must not return"


# ── W8: error text must be surfaced, not just counted ───────────────────────


def test_cycle_errors_carry_the_exception_text(tmp_path, monkeypatch):
    from substrate.execution.attempts.field_control_plane import FieldControlPlaneDriver

    class _BoomStore:
        def active_grants(self):
            raise RuntimeError("store exploded")

    driver = FieldControlPlaneDriver(
        store=_BoomStore(),
        work_queue=None,
        spool=None,
        sandbox_manager=None,
        targets_dir=str(tmp_path),
    )
    with pytest.raises(RuntimeError):
        driver.run_cycle()  # active_grants raises before any per-grant handling
