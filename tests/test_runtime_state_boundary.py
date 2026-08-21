"""Wave 0 — runtime-state boundary tests.

Covers the three mechanisms of the runtime/source separation:
  1. substrate/state/runtime_paths.py — resolution + Amendment B containment
  2. scripts/migrate_runtime_state.py — Amendment E migration semantics
  3. scripts/check_runtime_state_boundary.py — Gate 15 self-test
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# the repo under test is the one THIS file lives in (worktree-safe — never
# the UMH_ROOT deployment checkout; review finding C5)
REPO_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, REPO_ROOT)

from substrate.state.runtime_paths import (  # noqa: E402
    runtime_state_dir,
    runtime_state_path,
    runtime_state_root,
)


class TestRuntimePathResolver:
    def test_default_root_under_umh_root(self, monkeypatch):
        monkeypatch.delenv("UMH_STATE_DIR", raising=False)
        monkeypatch.setenv("UMH_ROOT", "/some/repo")
        assert runtime_state_root() == Path("/some/repo/data/runtime/umh")

    def test_state_dir_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
        assert runtime_state_root() == tmp_path / "state"

    def test_required_state_dir_fails_closed_without_override(self, monkeypatch):
        monkeypatch.delenv("UMH_STATE_DIR", raising=False)
        monkeypatch.setenv("UMH_REQUIRE_STATE_DIR", "1")
        monkeypatch.setenv("UMH_ROOT", "/app")
        with pytest.raises(ValueError, match="UMH_STATE_DIR is required"):
            runtime_state_root()

    def test_empty_state_dir_rejected(self, monkeypatch):
        monkeypatch.setenv("UMH_STATE_DIR", "   ")
        with pytest.raises(ValueError):
            runtime_state_root()

    def test_relative_state_dir_rejected(self, monkeypatch):
        monkeypatch.setenv("UMH_STATE_DIR", "relative/state")
        with pytest.raises(ValueError):
            runtime_state_root()

    def test_nested_subsystem_allowed(self, monkeypatch, tmp_path):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path))
        d = runtime_state_dir("operator/intent_loop")
        assert d == tmp_path / "operator" / "intent_loop"
        assert d.is_dir()

    @pytest.mark.parametrize("bad", ["../x", "/abs", "a//b", ".", "..", "a/./b", "", "  "])
    def test_traversal_subsystems_rejected(self, monkeypatch, tmp_path, bad):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path))
        with pytest.raises(ValueError):
            runtime_state_dir(bad, create=False)

    @pytest.mark.parametrize("bad", ["../../etc/passwd", "/abs.jsonl", "a/../../b"])
    def test_traversal_filenames_rejected(self, monkeypatch, tmp_path, bad):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path))
        with pytest.raises(ValueError):
            runtime_state_path("organism", bad, create_parent=False)

    def test_no_mkdir_without_request(self, monkeypatch, tmp_path):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path))
        d = runtime_state_dir("neversee", create=False)
        assert not d.exists()

    def test_returns_path_objects(self, monkeypatch, tmp_path):
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path))
        assert isinstance(runtime_state_dir("organism"), Path)
        assert isinstance(runtime_state_path("organism", "x.jsonl"), Path)

    def test_caller_injected_paths_still_win(self, monkeypatch, tmp_path):
        """Constructors must preserve explicitly passed store paths."""
        monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path))
        from substrate.organism.store import OrganismStore

        custom = tmp_path / "custom"
        store = OrganismStore(store_dir=custom)
        assert store._dir == custom

    def test_default_runtime_writers_resolve_under_state_dir(self, monkeypatch, tmp_path):
        """Default runtime writers must not target the source checkout.

        This pins the production-container failure where OrganismDaemon startup
        tried to create ``data/runtime/canonical_memory_store`` under read-only
        ``UMH_ROOT=/app`` before the governed spine could register.
        """
        app_root = tmp_path / "app"
        state_dir = tmp_path / "state" / "umh"
        app_root.mkdir()
        state_dir.mkdir(parents=True)
        monkeypatch.setenv("UMH_ROOT", str(app_root))
        monkeypatch.setenv("UMH_STATE_DIR", str(state_dir))

        cms = importlib.reload(
            importlib.import_module("substrate.state.memory.contracts.canonical_memory_store_v1")
        )
        cre = importlib.reload(
            importlib.import_module(
                "substrate.state.memory.contracts.canonical_memory_reconciliation_engine_v1"
            )
        )
        mcg = importlib.reload(
            importlib.import_module("substrate.state.memory.contracts.memory_conflict_governance_v1")
        )
        proof = importlib.reload(importlib.import_module("substrate.organism.proof_store"))
        ledger = importlib.reload(importlib.import_module("substrate.organism.execution_ledger"))
        audit = importlib.reload(importlib.import_module("transports.api.cockpit_audit"))
        signals = importlib.reload(
            importlib.import_module("substrate.control_plane.runtime.orchestrator.signals")
        )
        loop = importlib.reload(
            importlib.import_module("substrate.control_plane.runtime.orchestrator.loop")
        )

        assert cms.CanonicalMemoryStore().store_dir == (
            state_dir / "memory" / "canonical_memory_store"
        )
        assert cre.ReconciliationEngine().store_dir == (
            state_dir / "memory" / "canonical_memory_store"
        )
        assert mcg.ConflictGovernance().store_dir == state_dir / "memory" / "memory_conflicts"
        assert proof._STORE_PATH == state_dir / "organism" / "proof_packages.jsonl"
        assert ledger._LEDGER_PATH == state_dir / "organism" / "execution_ledger.jsonl"
        assert audit._MUTATION_LEDGER_PATH == str(state_dir / "audit" / "mutation_ledger.jsonl")
        assert signals.SIGNALS_ROOT == str(state_dir / "logs" / "signals")
        assert loop.HEARTBEAT_PATH == str(state_dir / "logs" / "orchestrator_heartbeat.json")
        assert not (app_root / "data" / "runtime" / "canonical_memory_store").exists()

    def test_operator_api_mutable_paths_resolve_under_state_dir(self, tmp_path):
        """The live os-operator entrypoint must not write into read-only source."""
        app_root = tmp_path / "immutable-app"
        state_dir = tmp_path / "state" / "umh"
        app_root.mkdir()
        state_dir.mkdir(parents=True)
        env = dict(os.environ)
        env["PYTHONPATH"] = REPO_ROOT
        env["UMH_ROOT"] = str(app_root)
        env["UMH_STATE_DIR"] = str(state_dir)
        script = """
import json
import services.operator_api as api
print(json.dumps({
    "memories": str(api.MEMORIES_PATH),
    "cost_log": str(api.COST_LOG_PATH),
    "voice_ack_dir": str(api._VOICE_ACK_DIR),
}))
"""
        res = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        assert res.returncode == 0, res.stdout + res.stderr
        paths = json.loads(res.stdout.strip().splitlines()[-1])
        assert paths == {
            "memories": str(state_dir / "memory" / "canonical_memory_store" / "memories.jsonl"),
            "cost_log": str(state_dir / "logs" / "cost_log.json"),
            "voice_ack_dir": str(state_dir / "voice_acks"),
        }
        assert not (app_root / "data").exists()
        assert not (app_root / "services" / "cost_log.json").exists()

    def test_operator_startup_dependency_defaults_resolve_under_state_dir(self, monkeypatch, tmp_path):
        """Default operator-startup stores must not create checkout-relative data.

        This pins the immutable operator cutover failure where the running
        source was mounted read-only and a startup dependency attempted to
        create ``data/umh/intelligence`` under the application root.
        """
        app_root = tmp_path / "immutable-app"
        state_dir = tmp_path / "state" / "umh"
        app_root.mkdir()
        state_dir.mkdir(parents=True)
        monkeypatch.setenv("UMH_ROOT", str(app_root))
        monkeypatch.setenv("UMH_STATE_DIR", str(state_dir))

        config_store = importlib.reload(
            importlib.import_module("substrate.state.config.config_store")
        )
        intelligence = importlib.reload(importlib.import_module("substrate.intelligence.runtime"))
        discovery = importlib.reload(
            importlib.import_module("substrate.organism.tailscale_discovery")
        )
        daemon_mod = importlib.reload(importlib.import_module("substrate.organism.daemon"))

        cfg = config_store.ConfigStore()
        cfg.set("ai_name", "BoundaryTest", layer="system")
        patterns = intelligence.PatternIntelligence()
        decisions = intelligence.DecisionIntelligence()
        tailscale = discovery.TailscaleDiscoveryTick()
        daemon = daemon_mod.OrganismDaemon(graph=None)

        assert cfg._layer_path("system") == state_dir / "config" / "system.json"
        assert patterns._store_path == state_dir / "intelligence" / "patterns.json"
        assert decisions._store_path == state_dir / "intelligence" / "decisions.jsonl"
        assert (
            Path(tailscale._discovered_peers_path)
            == state_dir / "discovery" / "discovered_peers.json"
        )
        assert (
            Path(daemon._tailscale_discovery._discovered_peers_path)
            == state_dir / "discovery" / "discovered_peers.json"
        )
        assert not (app_root / "data").exists()

    def test_intelligence_runtime_records_under_state_dir(self, monkeypatch, tmp_path):
        app_root = tmp_path / "immutable-app"
        state_dir = tmp_path / "state" / "umh"
        app_root.mkdir()
        monkeypatch.setenv("UMH_ROOT", str(app_root))
        monkeypatch.setenv("UMH_STATE_DIR", str(state_dir))

        intelligence = importlib.reload(importlib.import_module("substrate.intelligence.runtime"))
        runtime = intelligence.IntelligenceRuntime()
        runtime.learn_from_execution(
            content="operator source-state boundary test",
            action="route mutable state",
            outcome="success",
            success=True,
            domain="wave2",
        )

        assert (state_dir / "intelligence" / "patterns.json").is_file()
        assert (state_dir / "intelligence" / "decisions.jsonl").is_file()
        assert not (app_root / "data").exists()

    def test_os_operator_compose_declares_external_state_boundary(self):
        compose = (Path(REPO_ROOT) / "docker-compose.yml").read_text()
        start = compose.index("  os-operator:")
        block = compose[start:]

        assert "${UMH_ROOT:-/opt/OS}:/app:ro" in block
        assert "${UMH_OPERATOR_STATE_DIR:-/var/lib/umh/operator/state/live}:/state/umh" in block
        assert "UMH_ROOT=/app" in block
        assert "UMH_STATE_DIR=/state/umh" in block
        assert "UMH_REQUIRE_STATE_DIR=1" in block
        assert "PYTHONDONTWRITEBYTECODE=1" in block


def _run_migrate(args: list[str], repo: Path, backup: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["UMH_ROOT"] = str(repo)
    env.pop("UMH_STATE_DIR", None)
    return subprocess.run(
        [
            sys.executable,
            os.path.join(REPO_ROOT, "scripts", "migrate_runtime_state.py"),
            "--repo",
            str(repo),
            "--backup-dir",
            str(backup),
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def _build_legacy_tree(repo: Path) -> None:
    org = repo / "data" / "umh" / "organism"
    org.mkdir(parents=True)
    (org / "events.jsonl").write_text('{"e":1}\n{"e":2}\n')
    (org / "daemon_state.json").write_text('{"tick_count": 7}')
    wc = org / "workcells" / "advisor"
    wc.mkdir(parents=True)
    (wc / "heartbeat.json").write_text('{"status":"idle"}')
    uw = repo / "data" / "umh" / "universal_work"
    uw.mkdir(parents=True)
    (uw / "work_packets.jsonl").write_text('{"id":"wp1"}\n')
    (uw / "phase11_1_preflight.json").write_text('{"static":"proof"}')
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, timeout=60)


class TestMigrationScript:
    def test_plan_mode_no_mutation(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as b:
            repo = Path(d)
            _build_legacy_tree(repo)
            before = sorted(p.as_posix() for p in repo.rglob("*") if ".git" not in p.parts)
            res = _run_migrate(["--plan"], repo, Path(b) / "cut")
            assert res.returncode == 0, res.stderr
            after = sorted(p.as_posix() for p in repo.rglob("*") if ".git" not in p.parts)
            assert before == after
            plan = json.loads(res.stdout)
            modes = {e["old_rel"]: e["mode"] for e in plan["entries"]}
            assert modes["data/umh/organism/events.jsonl"] == "append_jsonl"
            assert modes["data/umh/organism/daemon_state.json"] == "snapshot_json"
            assert modes["data/umh/organism/workcells/advisor/heartbeat.json"] == "ephemeral"
            assert (
                modes["data/umh/universal_work/phase11_1_preflight.json"] == "keep_tracked_static"
            )

    def test_snapshot_finalize_append_delta_byte_identical(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as b:
            repo = Path(d)
            backup = Path(b) / "cut"
            _build_legacy_tree(repo)
            res = _run_migrate(["--snapshot"], repo, backup)
            assert res.returncode == 0, res.stdout + res.stderr
            # a late write lands between snapshot and quiescence
            src = repo / "data" / "umh" / "organism" / "events.jsonl"
            with open(src, "a") as f:
                f.write('{"e":3,"late":true}\n')
            res = _run_migrate(["--finalize"], repo, backup)
            assert res.returncode == 0, res.stdout + res.stderr
            new = repo / "data" / "runtime" / "umh" / "organism" / "events.jsonl"
            assert new.read_bytes() == src.read_bytes()
            manifest = json.loads((backup / "manifest_finalize.json").read_text())
            ev = next(
                e for e in manifest["entries"] if e["old_rel"] == "data/umh/organism/events.jsonl"
            )
            assert ev["finalize_status"] == "verified"
            assert ev["delta_bytes"] == len('{"e":3,"late":true}\n')
            # verify passes read-only
            res = _run_migrate(["--verify"], repo, backup)
            assert res.returncode == 0, res.stdout

    def test_write_landing_during_snapshot_copy_never_lost(self):
        """C3 regression: the append offset is the byte count captured in DST.
        A record appended to src after the copy must arrive via the finalize
        delta — verified by corrupting-free byte identity at the end."""
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as b:
            repo = Path(d)
            backup = Path(b) / "cut"
            _build_legacy_tree(repo)
            src = repo / "data" / "umh" / "organism" / "events.jsonl"
            _run_migrate(["--snapshot"], repo, backup)
            manifest = json.loads((backup / "manifest_snapshot.json").read_text())
            ev = next(
                e for e in manifest["entries"] if e["old_rel"] == "data/umh/organism/events.jsonl"
            )
            dst = Path(ev["new_abs"])
            # the recorded offset equals bytes actually captured in dst
            assert ev["snapshot_offset"] == dst.stat().st_size
            # simulate two post-snapshot appends, then finalize
            with open(src, "a") as f:
                f.write('{"e":"during"}\n{"e":"after"}\n')
            res = _run_migrate(["--finalize"], repo, backup)
            assert res.returncode == 0, res.stdout
            assert dst.read_bytes() == src.read_bytes()

    def test_rename_map_carries_history_to_new_name(self):
        """C4 regression: dex_conversations.jsonl must land as
        advisor_conversations.jsonl at the new home."""
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as b:
            repo = Path(d)
            backup = Path(b) / "cut"
            _build_legacy_tree(repo)
            oe = repo / "data" / "umh" / "operator_experience"
            oe.mkdir(parents=True)
            (oe / "dex_conversations.jsonl").write_text('{"turn":"history"}\n')
            _run_migrate(["--snapshot"], repo, backup)
            _run_migrate(["--finalize"], repo, backup)
            new = (
                repo
                / "data"
                / "runtime"
                / "umh"
                / "operator_experience"
                / "advisor_conversations.jsonl"
            )
            assert new.exists()
            assert new.read_text() == '{"turn":"history"}\n'
            assert not (
                repo
                / "data"
                / "runtime"
                / "umh"
                / "operator_experience"
                / "dex_conversations.jsonl"
            ).exists()

    def test_ephemeral_not_migrated(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as b:
            repo = Path(d)
            backup = Path(b) / "cut"
            _build_legacy_tree(repo)
            _run_migrate(["--snapshot"], repo, backup)
            _run_migrate(["--finalize"], repo, backup)
            hb_new = (
                repo
                / "data"
                / "runtime"
                / "umh"
                / "organism"
                / "workcells"
                / "advisor"
                / "heartbeat.json"
            )
            assert not hb_new.exists()

    def test_static_proofs_kept_in_place(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as b:
            repo = Path(d)
            backup = Path(b) / "cut"
            _build_legacy_tree(repo)
            _run_migrate(["--snapshot"], repo, backup)
            _run_migrate(["--finalize"], repo, backup)
            assert (repo / "data" / "umh" / "universal_work" / "phase11_1_preflight.json").exists()
            assert not (
                repo / "data" / "runtime" / "umh" / "universal_work" / "phase11_1_preflight.json"
            ).exists()

    def test_unknown_mode_stops_snapshot(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as b:
            repo = Path(d)
            backup = Path(b) / "cut"
            _build_legacy_tree(repo)
            (repo / "data" / "umh" / "organism" / "mystery.bin").write_bytes(b"\x00")
            res = _run_migrate(["--snapshot"], repo, backup)
            assert res.returncode == 2
            assert "unknown" in res.stdout.lower()
            # nothing was copied
            assert not (repo / "data" / "runtime").exists()

    def test_backup_dir_inside_repo_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            _build_legacy_tree(repo)
            res = _run_migrate(["--plan"], repo, repo / "backups")
            assert res.returncode == 2
            assert "OUTSIDE" in res.stdout


class TestBoundaryGate:
    def test_gate_self_test_passes(self):
        res = subprocess.run(
            [
                sys.executable,
                os.path.join(REPO_ROOT, "scripts", "check_runtime_state_boundary.py"),
                "--self-test",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert res.returncode == 0, res.stdout + res.stderr
