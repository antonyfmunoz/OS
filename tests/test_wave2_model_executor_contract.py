from __future__ import annotations

import os
import subprocess
from types import SimpleNamespace

from substrate.execution.attempts.host_isolation import scrub_worker_env
from substrate.execution.attempts.model_executor_contract import ModelWorkPacketInput
from substrate.execution.attempts.model_executor_selection import (
    build_model_executor,
    selected_provider_name,
)
from substrate.execution.attempts.model_executors.codex import CodexModelExecutor
from substrate.execution.attempts.model_executors.deterministic import (
    DeterministicConformanceExecutor,
)
from substrate.execution.attempts.worker_credential_boundary import (
    close_attempt_credential_home,
    open_attempt_credential_home,
)
from substrate.execution.attempts.model_executor_contract import (
    ModelExecutorIdentity,
    ModelExecutorReadiness,
    ModelInvocation,
    ModelTerminalResult,
)


def _packet(tmp_path, *, prompt: str = "do work") -> ModelWorkPacketInput:
    return ModelWorkPacketInput(
        prompt=prompt,
        worktree_path=str(tmp_path),
        timeout_seconds=30,
        max_turns=2,
        attempt_id="ea-1",
        package_hash="ph",
        operation_identity={"task_id": "wp-a"},
        proof_binding={"attempt_id": "ea-1", "task_id": "wp-a", "authorized_base": "abc"},
    )


def test_deterministic_adapter_satisfies_terminal_contract(tmp_path):
    adapter = DeterministicConformanceExecutor()
    ready = adapter.readiness()
    assert ready.ok and ready.authenticated

    result = adapter.invoke(_packet(tmp_path), env={"PATH": os.environ.get("PATH", "")})
    assert result.ok
    assert result.has_real_content
    assert result.identity is not None
    assert result.identity.provider == "deterministic"
    assert result.proof_binding["task_id"] == "wp-a"


def test_provider_selection_defaults_to_codex_and_can_select_deterministic(monkeypatch):
    monkeypatch.delenv("UMH_MODEL_EXECUTOR_PROVIDER", raising=False)
    assert selected_provider_name() == "codex"
    assert type(build_model_executor()).__name__ == "CodexModelExecutor"

    monkeypatch.setenv("UMH_MODEL_EXECUTOR_PROVIDER", "deterministic")
    assert isinstance(build_model_executor(), DeterministicConformanceExecutor)


def test_scrub_worker_env_explicitly_denies_codex_credentials_by_default():
    dirty = {
        "PATH": "/usr/bin",
        "HOME": "/root",
        "CODEX_ACCESS_TOKEN": "secret",
        "CODEX_API_KEY": "secret",
        "OPENAI_API_KEY": "secret",
    }
    clean = scrub_worker_env(dirty)
    assert "CODEX_ACCESS_TOKEN" not in clean
    assert "CODEX_API_KEY" not in clean
    assert "OPENAI_API_KEY" not in clean

    allowed = scrub_worker_env(dirty, extra_allow={"CODEX_ACCESS_TOKEN": "scoped"})
    assert allowed["CODEX_ACCESS_TOKEN"] == "scoped"
    assert "CODEX_API_KEY" not in allowed


def test_attempt_home_has_private_codex_config_without_shared_home(tmp_path, monkeypatch):
    src = tmp_path / "src_codex"
    src.mkdir()
    (src / "auth.json").write_text('{"redacted":true}', encoding="utf-8")
    (src / "config.toml").write_text("model='test'\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))
    os.rename(src, tmp_path / ".codex")

    home = open_attempt_credential_home(attempt_id="ea-1", run_root=str(tmp_path / "run"))
    try:
        assert home.codex_dir.endswith(".codex")
        assert home.env_overrides()["CODEX_HOME"] == home.codex_dir
        for path in home.credential_files:
            if path.endswith(("auth.json", "config.toml")):
                assert os.stat(path).st_mode & 0o177 == 0
    finally:
        close_attempt_credential_home(home)
    assert not os.path.exists(home.home_path)


def test_codex_adapter_invokes_exec_with_prompt_on_stdin(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        if cmd[-1:] == ["--version"]:
            return SimpleNamespace(returncode=0, stdout="codex-cli 0.test\n", stderr="")
        if cmd[1:3] == ["login", "status"]:
            return SimpleNamespace(returncode=0, stdout="logged in\n", stderr="")
        return SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"text":"real implementation complete"}}\n'
                '{"type":"turn.completed","usage":{"input_tokens":7,"output_tokens":11},"model":"gpt-test"}\n'
            ),
            stderr="",
        )

    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        fake_run,
    )
    adapter = CodexModelExecutor(model="gpt-test")
    assert adapter.readiness().ok
    result = adapter.invoke(_packet(tmp_path, prompt="secret-free prompt"), env={"CODEX_HOME": "x"})

    cmd, kwargs = calls[-1]
    assert cmd[:3] == ["/usr/bin/codex", "exec", "--json"]
    assert cmd[-1] == "-"
    assert "secret-free prompt" not in cmd
    assert kwargs["input"] == "secret-free prompt"
    assert kwargs["cwd"] == str(tmp_path)
    assert result.ok
    assert result.identity.provider == "codex"
    assert result.usage["output_tokens"] == 11
    assert result.proof_binding["attempt_id"] == "ea-1"


def test_codex_adapter_rejects_empty_output(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert not result.ok
    assert result.retry_class == "malformed_output"


def test_codex_adapter_classifies_timeout(tmp_path, monkeypatch):
    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["codex"], timeout=1)

    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        timeout,
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert result.timed_out
    assert result.retry_class == "external_transient"


def test_neutral_worker_wraps_actual_provider_invocation_in_isolation(tmp_path, monkeypatch):
    from substrate.execution.attempts import worker_model_executor as worker

    class FakeExecutor:
        identity = ModelExecutorIdentity("fake", "model", "v", "FakeExecutor")

        def readiness(self):
            return ModelExecutorReadiness(True, self.identity, authenticated=True)

        def build_invocation(self, packet):
            return ModelInvocation(argv=["provider-cli", "--do-work", "-"], stdin=packet.prompt)

        def collect_result(self, packet, completed, *, duration_seconds):
            return ModelTerminalResult(
                ok=True,
                status="succeeded",
                stdout="real content",
                exit_code=getattr(completed, "returncode", None),
                duration_seconds=duration_seconds,
                identity=self.identity,
                proof_binding=packet.proof_binding,
            )

    class FakeHome:
        def __init__(self):
            self.home_path = str(tmp_path / "home")
            self.tmp_path = str(tmp_path / "tmp")
            self.claude_dir = str(tmp_path / "home" / ".claude")
            self.codex_dir = str(tmp_path / "home" / ".codex")

        def env_overrides(self):
            return {"HOME": self.home_path, "CODEX_HOME": self.codex_dir, "TMPDIR": self.tmp_path}

    seen = {}
    monkeypatch.setattr(worker, "build_model_executor", lambda provider=None: FakeExecutor())
    monkeypatch.setattr(worker, "make_lease_selfcontained", lambda path: None)
    monkeypatch.setattr(worker, "open_attempt_credential_home", lambda **kw: FakeHome())
    monkeypatch.setattr(worker, "close_attempt_credential_home", lambda home: None)
    monkeypatch.setattr(worker, "_close_home_or_fail", lambda home: None)
    monkeypatch.setattr(worker, "project_task_local_objective", lambda package, path: {"ok": True, "projected": True})
    monkeypatch.setattr(worker, "_mark_projection_execution_context", lambda path, projection: None)
    monkeypatch.setattr(worker, "prepare_attempt_git_capability", lambda path, attempt_id: str(tmp_path / "refs"))
    monkeypatch.setattr(worker, "readonly_binds_for_scope", lambda scope, lease_root: ["secret.txt"])
    monkeypatch.setattr(worker, "_capture_git", lambda path, base: (["app/main.py"], ["abc commit"], "diff"))

    def fake_wrap(inner, profile):
        seen["inner"] = list(inner)
        seen["readonly"] = list(profile.readonly_subpaths)
        return ["bwrap", "--", *inner]

    def fake_run(cmd, **kwargs):
        seen["cmd"] = list(cmd)
        seen["env"] = dict(kwargs["env"])
        seen["input"] = kwargs["input"]
        return SimpleNamespace(returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(worker, "build_isolated_command", fake_wrap)
    monkeypatch.setattr("substrate.execution.cpu_gate.gated_subprocess_run", fake_run)

    wt = tmp_path / "wt"
    wt.mkdir()
    package = SimpleNamespace(
        governance_constraints=["writable_path_scope=['app/main.py']"],
        operation_identity={"task_id": "A"},
        package_hash="ph",
    )
    lease = SimpleNamespace(worktree_path=str(wt), snapshot_ref="base")
    result = worker.run_worker_in_lease(
        package=package,
        lease=lease,
        attempt_id="ea-1",
        run_root=str(tmp_path / "run"),
    )

    assert result.ok
    assert seen["inner"] == ["provider-cli", "--do-work", "-"]
    assert seen["cmd"][:2] == ["bwrap", "--"]
    assert seen["cmd"][-3:] == ["provider-cli", "--do-work", "-"]
    assert seen["readonly"] == ["secret.txt"]
    assert seen["input"]
    assert "CODEX_HOME" in seen["env"]
