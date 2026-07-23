"""Wave 1 test AE — GoalRegistry durability and the Objective runtime-state boundary.

§22.1: default durable path under the runtime-state boundary; bounded one-time
migration preserving IDs with the legacy source untouched; interprocess
locking; atomic replacement; version counter with CAS; idempotent Objective
create-or-reuse under tenant_id + objective_key + scope_hash.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading

import pytest

from substrate.organism.strategic_gap_engine import (
    Goal,
    GoalConflictError,
    GoalRegistry,
    GoalStatus,
    GoalType,
)


@pytest.fixture()
def isolated_roots(tmp_path, monkeypatch):
    """Isolated UMH_ROOT (legacy tree) + UMH_STATE_DIR (boundary)."""
    repo_root = tmp_path / "repo"
    state_dir = tmp_path / "state"
    repo_root.mkdir()
    state_dir.mkdir()
    monkeypatch.setenv("UMH_ROOT", str(repo_root))
    monkeypatch.setenv("UMH_STATE_DIR", str(state_dir))
    return repo_root, state_dir


def _tree_digest(root) -> dict[str, str]:
    digests: dict[str, str] = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            path = os.path.join(dirpath, fname)
            with open(path, "rb") as f:
                digests[os.path.relpath(path, root)] = hashlib.sha256(f.read()).hexdigest()
    return digests


class TestRuntimeStateBoundary:
    def test_default_store_under_state_dir(self, isolated_roots):
        repo_root, state_dir = isolated_roots
        reg = GoalRegistry()
        assert str(reg._store_path).startswith(str(state_dir))

    def test_writes_never_touch_source_tree(self, isolated_roots):
        # Test AE: all Objective writes land beneath UMH_STATE_DIR; the
        # (potentially read-only) source tree stays byte-identical.
        repo_root, state_dir = isolated_roots
        before = _tree_digest(repo_root)
        reg = GoalRegistry()
        goal, _ = reg.create_or_reuse_objective("tenant-a", "obj-1", "hash1", title="T")
        goal.description = "updated"
        reg.update(goal)
        assert _tree_digest(repo_root) == before
        assert os.path.exists(state_dir / "strategic_gaps" / "goals.jsonl")


class TestLegacyMigration:
    def _seed_legacy(self, repo_root, goals: list[dict]) -> str:
        legacy_dir = repo_root / "data" / "umh" / "strategic_gaps"
        legacy_dir.mkdir(parents=True)
        legacy_path = legacy_dir / "goals.jsonl"
        with open(legacy_path, "w") as f:
            for g in goals:
                f.write(json.dumps(g) + "\n")
        return str(legacy_path)

    def test_migration_preserves_ids_and_leaves_legacy_untouched(self, isolated_roots):
        repo_root, state_dir = isolated_roots
        legacy_goal = Goal(title="pre-wave goal", goal_type=GoalType.OBJECTIVE).to_dict()
        legacy_goal.pop("version", None)  # pre-Wave-1 records have no version
        legacy_path = self._seed_legacy(repo_root, [legacy_goal])
        with open(legacy_path, "rb") as f:
            legacy_bytes_before = f.read()

        reg = GoalRegistry()
        migrated = reg.get(legacy_goal["goal_id"])
        assert migrated is not None
        assert migrated.title == "pre-wave goal"
        assert migrated.version == 1  # backward-compatible default

        with open(legacy_path, "rb") as f:
            assert f.read() == legacy_bytes_before

    def test_migration_runs_once(self, isolated_roots):
        repo_root, state_dir = isolated_roots
        legacy_goal = Goal(title="legacy").to_dict()
        self._seed_legacy(repo_root, [legacy_goal])
        reg1 = GoalRegistry()
        reg1.remove(legacy_goal["goal_id"])
        # Second construction must NOT re-import the removed legacy record —
        # the durable store already exists.
        reg2 = GoalRegistry()
        assert reg2.get(legacy_goal["goal_id"]) is None


class TestVersioningAndCas:
    def test_versions_increment_on_write(self, isolated_roots):
        reg = GoalRegistry()
        goal = reg.add(Goal(title="v"))
        assert goal.version == 1
        goal = reg.update(goal)
        assert goal.version == 2

    def test_cas_mismatch_raises_explicit_conflict(self, isolated_roots):
        reg = GoalRegistry()
        goal = reg.add(Goal(title="v"))
        with pytest.raises(GoalConflictError) as exc:
            reg.update(goal, expected_version=99)
        assert exc.value.goal_id == goal.goal_id
        assert exc.value.actual == 1

    def test_cas_under_concurrency_single_winner(self, isolated_roots):
        # Two writers race the same expected_version: exactly one wins, the
        # other gets an explicit conflict — no lost update.
        reg = GoalRegistry()
        goal = reg.add(Goal(title="contended"))
        results: list[str] = []
        lock = threading.Lock()

        def writer(tag: str) -> None:
            g = Goal.from_dict(goal.to_dict())
            g.description = tag
            try:
                reg.update(g, expected_version=1)
                with lock:
                    results.append(f"ok:{tag}")
            except GoalConflictError:
                with lock:
                    results.append(f"conflict:{tag}")

        threads = [threading.Thread(target=writer, args=(t,)) for t in ("a", "b")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sorted(r.split(":")[0] for r in results) == ["conflict", "ok"]
        assert reg.get(goal.goal_id).version == 2

    def test_cross_process_truth_via_reload(self, isolated_roots):
        reg_a = GoalRegistry()
        reg_b = GoalRegistry()
        goal = reg_a.add(Goal(title="shared"))
        # reg_b was constructed before the write; its CAS write must still see
        # current disk truth (reload-before-write) and conflict correctly.
        stale = Goal.from_dict(goal.to_dict())
        with pytest.raises(GoalConflictError):
            reg_b.update(stale, expected_version=0)


class TestObjectiveCreateOrReuse:
    def test_idempotent_under_identity_key(self, isolated_roots):
        reg = GoalRegistry()
        g1, created1 = reg.create_or_reuse_objective("tenant-a", "ship-x", "h1", title="Ship X")
        g2, created2 = reg.create_or_reuse_objective("tenant-a", "ship-x", "h1", title="Ship X")
        assert created1 is True and created2 is False
        assert g1.goal_id == g2.goal_id

    def test_distinct_identity_not_merged(self, isolated_roots):
        # §23.2: similar-but-distinct objectives are never silently merged.
        reg = GoalRegistry()
        g1, _ = reg.create_or_reuse_objective("tenant-a", "ship-x", "h1")
        g2, _ = reg.create_or_reuse_objective("tenant-a", "ship-x", "h2")  # other scope
        g3, _ = reg.create_or_reuse_objective("tenant-b", "ship-x", "h1")  # other tenant
        assert len({g1.goal_id, g2.goal_id, g3.goal_id}) == 3

    def test_new_objective_starts_draft_objective_type(self, isolated_roots):
        # §23.3: canonical initial state is GoalStatus.DRAFT — no new states.
        reg = GoalRegistry()
        goal, _ = reg.create_or_reuse_objective("tenant-a", "obj", "h")
        assert goal.status == GoalStatus.DRAFT
        assert goal.goal_type == GoalType.OBJECTIVE

    def test_tenant_required(self, isolated_roots):
        reg = GoalRegistry()
        with pytest.raises(ValueError):
            reg.create_or_reuse_objective("", "obj", "h")

    def test_concurrent_create_single_objective(self, isolated_roots):
        reg = GoalRegistry()
        ids: list[str] = []
        lock = threading.Lock()

        def creator() -> None:
            g, _ = reg.create_or_reuse_objective("tenant-a", "same-obj", "h1")
            with lock:
                ids.append(g.goal_id)

        threads = [threading.Thread(target=creator) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(set(ids)) == 1

    def test_persisted_across_restart(self, isolated_roots):
        # Test AA-adjacent durability: the Objective identity survives restart.
        reg = GoalRegistry()
        g1, _ = reg.create_or_reuse_objective("tenant-a", "obj", "h")
        reg2 = GoalRegistry()
        g2, created = reg2.create_or_reuse_objective("tenant-a", "obj", "h")
        assert created is False and g2.goal_id == g1.goal_id


class TestGovernedSpecRegistration:
    def test_objective_mutation_specs_registered(self):
        from substrate.organism.mutation_registry import MutationRegistry

        reg = MutationRegistry()
        for name in (
            "objective_goal_write",
            "objective_plan_assess",
            "objective_plan_compile",
            "objective_plan_decision",
            "objective_plan_revise",
        ):
            spec = reg.lookup(name)
            assert spec is not None, name
            assert spec.risk_level == "low"
            assert spec.blast_radius.value == "local_file"
            assert spec.degraded_mode_allowed is True
