from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_mesh_runtime_release.py"


def _builder_module():
    spec = importlib.util.spec_from_file_location("build_mesh_runtime_release_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_minimal_source(root: Path) -> None:
    (root / "transports/node_mesh").mkdir(parents=True)
    for rel in (
        "transports/node_mesh/run.py",
        "transports/node_mesh/server.py",
        "transports/node_mesh/__init__.py",
        "transports/node_mesh/config.py",
        "transports/node_mesh/metrics_buffer.py",
        "transports/node_mesh/registry.py",
    ):
        (root / rel).write_text("# runtime file\n", encoding="utf-8")
    (root / "transports/node_mesh/integration").mkdir(parents=True)
    (root / "transports/node_mesh/integration/types.py").write_text(
        "# runtime file\n", encoding="utf-8"
    )
    for rel in (
        "substrate/__init__.py",
        "substrate/types.py",
        "substrate/execution/__init__.py",
        "substrate/execution/cpu_gate.py",
        "substrate/execution/durable_remote_transport.py",
        "substrate/execution/executor.py",
        "substrate/execution/mesh_verdict.py",
        "substrate/execution/proof_generator.py",
        "substrate/governance/__init__.py",
        "substrate/governance/risk_classes.py",
        "substrate/sockets/__init__.py",
        "substrate/sockets/capability_socket.py",
        "substrate/sockets/envelopes.py",
        "substrate/sockets/outcome_socket.py",
        "substrate/sockets/protocols.py",
        "substrate/sockets/registry.py",
        "substrate/sockets/signal_socket.py",
        "substrate/sockets/view_socket.py",
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# runtime file\n", encoding="utf-8")
    (root / "transports/__init__.py").write_text("", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts/op_run.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (root / "services").mkdir()
    (root / "services/mesh.env.tpl").write_text(
        "UMH_MESH_RELAY_SECRET=op://vault/item/password\n", encoding="utf-8"
    )
    (root / "pyproject.toml").write_text("[project]\nname='umh-test'\n", encoding="utf-8")


def test_mesh_runtime_release_excludes_mutable_runtime_state(tmp_path):
    module = _builder_module()
    source = tmp_path / "source"
    output = tmp_path / "runtime" / "releases"
    source.mkdir()
    _write_minimal_source(source)
    mutable = source / "data/runtime/organism/learning/signal_feed.jsonl"
    mutable.parent.mkdir(parents=True)
    mutable.write_text("x" * (2 * 1024 * 1024), encoding="utf-8")
    (source / ".codex").mkdir()
    (source / ".codex/auth.json").write_text('{"secret":true}', encoding="utf-8")

    release = module.build_release(
        source_root=source,
        output_root=output,
        source_sha="abc123",
        max_bytes=1024 * 1024,
    )

    assert release.name.startswith("abc123-")
    assert not (release / "data").exists()
    assert not (release / ".codex").exists()
    manifest = json.loads((release / "MANIFEST.json").read_text(encoding="utf-8"))
    included = {item["path"] for item in manifest["files"]}
    assert "scripts/op_run.sh" in included
    assert "services/mesh.env.tpl" in included
    assert "transports/node_mesh/run.py" in included
    assert "substrate/execution/durable_remote_transport.py" in included
    assert "data/runtime/organism/learning/signal_feed.jsonl" not in included
    assert manifest["total_bytes"] < 1024 * 1024


def test_mesh_runtime_release_size_ceiling_fails_closed_for_allowlisted_growth(tmp_path):
    module = _builder_module()
    source = tmp_path / "source"
    output = tmp_path / "runtime" / "releases"
    source.mkdir()
    _write_minimal_source(source)
    (source / "transports/node_mesh/huge.py").write_text("x" * 2048, encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        module.build_release(
            source_root=source,
            output_root=output,
            source_sha="abc123",
            max_bytes=1024,
        )

    assert "exceeding ceiling" in str(exc.value)
    assert not list(output.glob("abc123-*")) if output.exists() else True


def test_mesh_runtime_release_rejects_symlink_escape(tmp_path):
    module = _builder_module()
    source = tmp_path / "source"
    output = tmp_path / "runtime" / "releases"
    source.mkdir()
    _write_minimal_source(source)
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")
    (source / "transports/node_mesh/secret_link.py").symlink_to(outside)

    with pytest.raises(SystemExit) as exc:
        module.build_release(
            source_root=source,
            output_root=output,
            source_sha="abc123",
            max_bytes=1024 * 1024,
        )

    assert "refusing symlink" in str(exc.value)


def test_mesh_runtime_release_excludes_generic_mutable_state_dirs(tmp_path):
    module = _builder_module()
    source = tmp_path / "source"
    output = tmp_path / "runtime" / "releases"
    source.mkdir()
    _write_minimal_source(source)
    for dirname in ("cache", "runtime", "credentials"):
        path = source / "transports/node_mesh" / dirname / "state.json"
        path.parent.mkdir(parents=True)
        path.write_text('{"mutable":true}', encoding="utf-8")

    release = module.build_release(
        source_root=source,
        output_root=output,
        source_sha="abc123",
        max_bytes=1024 * 1024,
    )

    manifest = json.loads((release / "MANIFEST.json").read_text(encoding="utf-8"))
    included = {item["path"] for item in manifest["files"]}
    assert not any("/cache/" in path for path in included)
    assert not any("/runtime/" in path for path in included)
    assert not any("/credentials/" in path for path in included)


def test_mesh_runtime_release_uses_tracked_source_closure(tmp_path):
    module = _builder_module()
    source = tmp_path / "source"
    output = tmp_path / "runtime" / "releases"
    source.mkdir()
    _write_minimal_source(source)
    subprocess.run(["git", "init"], cwd=source, check=True, stdout=subprocess.PIPE)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=source,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=source,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=source, check=True, stdout=subprocess.PIPE)
    (source / "substrate/tmp_token.txt").write_text("untracked-secret-like", encoding="utf-8")
    (source / "substrate/state/session/live.json").parent.mkdir(parents=True, exist_ok=True)
    (source / "substrate/state/session/live.json").write_text('{"mutable":true}', encoding="utf-8")

    release = module.build_release(
        source_root=source,
        output_root=output,
        source_sha="abc123",
        max_bytes=1024 * 1024,
    )

    manifest = json.loads((release / "MANIFEST.json").read_text(encoding="utf-8"))
    included = {item["path"] for item in manifest["files"]}
    assert "substrate/tmp_token.txt" not in included
    assert "substrate/state/session/live.json" not in included
    assert "substrate/execution/durable_remote_transport.py" in included


def test_mesh_runtime_release_builds_against_real_worktree(tmp_path):
    module = _builder_module()
    source = SCRIPT.parents[1]

    release = module.build_release(
        source_root=source,
        output_root=tmp_path / "releases",
        source_sha="realsha",
        max_bytes=128 * 1024 * 1024,
    )

    manifest = json.loads((release / "MANIFEST.json").read_text(encoding="utf-8"))
    included = {item["path"] for item in manifest["files"]}
    assert "transports/node_mesh/run.py" in included
    assert "transports/node_mesh/server.py" in included
    assert "substrate/execution/durable_remote_transport.py" in included
    assert "substrate/self_model.py" in included
    assert "substrate/execution/runtime/execution_spine.py" in included
    assert "scripts/op_run.sh" in included
    assert "services/mesh.env.tpl" in included
    assert "services/cost_log.json" not in included
    assert not any(path.startswith("data/") for path in included)

    env = {**os.environ, "PYTHONPATH": str(release), "UMH_ROOT": str(release)}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from substrate.execution.durable_remote_transport import DurableRemoteStore; "
                "from transports.node_mesh.server import NodeMeshServer; "
                "print(DurableRemoteStore.__name__, NodeMeshServer.__name__)"
            ),
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "DurableRemoteStore NodeMeshServer" in result.stdout
