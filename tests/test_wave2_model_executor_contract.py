from __future__ import annotations

import os
import subprocess
import time
from types import SimpleNamespace

import pytest

from substrate.execution.attempts.host_isolation import scrub_worker_env
from substrate.execution.attempts.model_executor_contract import (
    ModelExecutorIdentity,
    ModelExecutorReadiness,
    ModelInvocation,
    ModelTerminalResult,
    ModelWorkPacketInput,
)
from substrate.execution.attempts.model_executor_selection import (
    build_model_executor,
    selected_codex_model,
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
    monkeypatch.delenv("UMH_CODEX_MODEL", raising=False)
    monkeypatch.delenv("UMH_ALLOW_TEST_MODEL_EXECUTOR", raising=False)
    assert selected_provider_name() == "codex"
    assert selected_codex_model() == "gpt-5.3-codex-spark"
    assert type(build_model_executor()).__name__ == "CodexModelExecutor"

    monkeypatch.setenv("UMH_MODEL_EXECUTOR_PROVIDER", "deterministic")
    try:
        build_model_executor()
    except ValueError as exc:
        assert "test-only" in str(exc)
    else:
        raise AssertionError("deterministic executor must not be selectable without a test-only gate")
    monkeypatch.setenv("UMH_ALLOW_TEST_MODEL_EXECUTOR", "1")
    assert isinstance(build_model_executor(), DeterministicConformanceExecutor)
    monkeypatch.setenv("UMH_CODEX_MODEL", "gpt-local-policy")
    assert selected_codex_model() == "gpt-local-policy"


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

    home = open_attempt_credential_home(
        attempt_id="ea-1", run_root=str(tmp_path / "run"), provider="codex"
    )
    try:
        assert home.codex_dir.endswith(".codex")
        assert home.env_overrides()["CODEX_HOME"] == home.codex_dir
        for path in home.credential_files:
            if path.endswith(("auth.json", "config.toml")):
                assert os.stat(path).st_mode & 0o177 == 0
    finally:
        close_attempt_credential_home(home)
    assert not os.path.exists(home.home_path)


def test_codex_attempt_home_does_not_copy_claude_credentials(tmp_path, monkeypatch):
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "auth.json").write_text('{"redacted":true}', encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / ".credentials.json").write_text("CLAUDE-SECRET", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))

    home = open_attempt_credential_home(
        attempt_id="ea-codex-only", run_root=str(tmp_path / "run"), provider="codex"
    )
    try:
        assert os.path.isfile(os.path.join(home.codex_dir, "auth.json"))
        assert not os.listdir(home.claude_dir)
        for dirpath, _dirs, files in os.walk(home.home_path):
            for name in files:
                body = open(os.path.join(dirpath, name), encoding="utf-8").read()
                assert "CLAUDE-SECRET" not in body
    finally:
        close_attempt_credential_home(home)


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
    assert "--ignore-user-config" in cmd
    assert cmd[cmd.index("--sandbox") + 1] == "danger-full-access"
    assert cmd[cmd.index("-m") + 1] == "gpt-test"
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


def test_codex_adapter_rejects_malformed_jsonl_even_with_content(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"text":"real content"}}\n'
                'not-json\n'
                '{"type":"turn.completed","usage":{},"model":"gpt-test"}\n'
            ),
            stderr="",
        ),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert not result.ok
    assert result.retry_class == "malformed_output"
    assert "malformed json" in result.stderr


def test_codex_adapter_rejects_truncated_jsonl_without_terminal_event(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout='{"type":"item.completed","item":{"text":"real content"}}\n',
            stderr="",
        ),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert not result.ok
    assert result.retry_class == "malformed_output"
    assert "missing terminal" in result.stderr


def test_codex_adapter_rejects_multiple_terminal_events(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"text":"real content"}}\n'
                '{"type":"turn.completed","usage":{},"model":"gpt-test"}\n'
                '{"type":"turn.completed","usage":{},"model":"gpt-test"}\n'
            ),
            stderr="",
        ),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert not result.ok
    assert result.retry_class == "malformed_output"
    assert "multiple terminal" in result.stderr


def test_codex_adapter_rejects_turn_failed_event(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout='{"type":"turn.failed","message":"provider refused"}\n',
            stderr="",
        ),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert not result.ok
    assert result.retry_class == "malformed_output"
    assert "turn.failed event" in result.stderr
    assert result.execution_identity["terminal_status"] == "failed"


def test_codex_adapter_rejects_terminal_error_event(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout='{"type":"error","message":"transport error"}\n',
            stderr="",
        ),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert not result.ok
    assert result.retry_class == "malformed_output"
    assert "error event" in result.stderr
    assert result.execution_identity["terminal_status"] == "error"


def test_codex_adapter_rejects_missing_usage_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"text":"real content"}}\n'
                '{"type":"turn.completed"}\n'
            ),
            stderr="",
        ),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert not result.ok
    assert result.retry_class == "malformed_output"
    assert "missing terminal usage metadata" in result.stderr
    assert result.execution_identity["usage_present"] is False


def test_codex_adapter_accepts_unobservable_terminal_model_when_exact_selector_passed(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"text":"real content"}}\n'
                '{"type":"turn.completed","usage":{}}\n'
            ),
            stderr="",
        ),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert result.ok
    assert result.identity is not None
    assert result.identity.model == "gpt-test"
    assert result.execution_identity["model_requested"] == "gpt-test"
    assert result.execution_identity["explicit_model_argument_present"] is True
    assert result.execution_identity["user_config_ignored"] is True
    assert result.execution_identity["model_resolution_observable"] is False
    assert result.execution_identity["trusted_model_resolved"] == ""
    assert result.execution_identity["invocation_accepted"] is True
    assert result.execution_identity["usage_present"] is True


def test_codex_adapter_rejects_terminal_model_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"text":"real content"}}\n'
                '{"type":"turn.completed","usage":{},"model":"gpt-other"}\n'
            ),
            stderr="",
        ),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert not result.ok
    assert result.retry_class == "malformed_output"
    assert "trusted terminal model identity mismatch" in result.stderr
    assert "gpt-other" in result.stderr
    assert result.identity is not None
    assert result.identity.model == "gpt-test"
    assert result.execution_identity["trusted_model_resolved"] == "gpt-other"
    assert result.execution_identity["model_resolution_observable"] is True


def test_codex_adapter_rejects_wrong_json_field_shapes_without_crashing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":"not-an-object"}\n'
                '{"type":"agent_message","message":"not-an-object"}\n'
                '{"type":"turn.completed","usage":"not-an-object","model":"gpt-test"}\n'
            ),
            stderr="",
        ),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert not result.ok
    assert result.retry_class == "malformed_output"
    assert "item is not an object" in result.stderr
    assert "message is not an object" in result.stderr
    assert "usage is not an object" in result.stderr


def test_codex_adapter_rejects_non_string_message_content(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"text":{"leak":"structured"}}}\n'
                '{"type":"agent_message","message":{"content":["not","text"]}}\n'
                '{"type":"turn.completed","usage":{},"model":"gpt-test"}\n'
            ),
            stderr="",
        ),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert not result.ok
    assert result.retry_class == "malformed_output"
    assert "item.text is not a string" in result.stderr
    assert "message.content is not a string" in result.stderr


def test_codex_adapter_sanitizes_credential_bearing_output(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="Authorization: Bearer secret-token\nordinary error",
        ),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert "secret-token" not in result.stderr
    assert "[redacted credential-bearing line]" in result.stderr
    assert "ordinary error" in result.stderr


def test_codex_adapter_sanitizes_successful_model_content(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"text":"OPENAI_API_KEY=sk-secretsecret"}}\n'
                '{"type":"turn.completed","usage":{},"model":"gpt-test"}\n'
            ),
            stderr="",
        ),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert result.ok
    assert "sk-secretsecret" not in result.stdout
    assert "[redacted credential-bearing line]" in result.stdout


@pytest.mark.parametrize(
    "secret_text",
    [
        "password=hunter2",
        "secret=my-secret-value",
        "credential=session-cookie",
        "op" + "://UMH-Production/Service/password",
    ],
)
def test_codex_adapter_sanitizes_common_secret_shapes(tmp_path, monkeypatch, secret_text):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout=(
                f'{{"type":"item.completed","item":{{"text":"{secret_text}"}}}}\n'
                '{"type":"turn.completed","usage":{},"model":"gpt-test"}\n'
            ),
            stderr="",
        ),
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})
    assert result.ok
    assert secret_text not in result.stdout
    assert "[redacted credential-bearing line]" in result.stdout


def test_terminal_result_binds_executor_identity_and_proof_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex.gated_subprocess_run",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"text":"real content"}}\n'
                '{"type":"turn.completed","usage":{"input_tokens":3,"output_tokens":5},'
                '"model":"gpt-proof"}\n'
            ),
            stderr="",
        ),
    )
    packet = _packet(tmp_path)
    result = CodexModelExecutor(model="gpt-proof").invoke(packet, env={})
    assert result.ok
    assert result.identity is not None
    assert result.identity.proof_metadata()["provider"] == "codex"
    assert result.identity.proof_metadata()["model"] == "gpt-proof"
    assert result.usage == {"input_tokens": 3, "output_tokens": 5}
    assert result.proof_binding == packet.proof_binding


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


def test_codex_adapter_preserves_timeout_stdout_stderr_evidence(tmp_path, monkeypatch):
    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(
            cmd=["codex"],
            timeout=1,
            output='{"type":"thread.started"}\n',
            stderr="provider reported not logged in before timeout",
        )

    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
        timeout,
    )
    result = CodexModelExecutor(model="gpt-test").invoke(_packet(tmp_path), env={})

    assert result.timed_out
    assert result.retry_class == "external_transient"
    assert result.stdout == '{"type":"thread.started"}'
    assert "not logged in" in result.stderr


def test_codex_windows_timeout_terminates_complete_process_tree(monkeypatch):
    from substrate.execution.attempts.model_executors import codex as codex_mod

    calls: list[tuple[int, bool]] = []

    class FakeProc:
        pid = 1234
        returncode = None

        def __init__(self):
            self.communicate_calls = 0

        def communicate(self, *, input=None, timeout=None):
            self.communicate_calls += 1
            if self.communicate_calls <= 2:
                raise subprocess.TimeoutExpired(
                    cmd=["codex"],
                    timeout=timeout,
                    output="partial jsonl",
                    stderr="stdio still open",
                )
            return "", ""

    proc = FakeProc()
    monkeypatch.setattr(codex_mod.os, "name", "nt")
    popen_kwargs = {}

    def fake_popen(*_args, **kwargs):
        popen_kwargs.update(kwargs)
        return proc

    monkeypatch.setattr(codex_mod, "gated_popen", fake_popen)

    def fake_taskkill(pid: int, *, force: bool):
        calls.append((pid, force))
        return SimpleNamespace(returncode=0, stdout=f"killed {pid} force={force}", stderr="")

    monkeypatch.setattr(codex_mod, "_taskkill_tree", fake_taskkill)

    with pytest.raises(subprocess.TimeoutExpired) as exc:
        codex_mod._run_codex_process_tree(
            ["codex", "exec"],
            caller="unit",
            timeout=1,
            cwd=".",
            env={},
            input="prompt",
            capture_output=True,
            text=True,
        )

    assert calls == [(1234, False), (1234, True)]
    assert "stdio still open" in str(exc.value.stderr)
    assert "force=True" in str(exc.value.stderr)
    assert popen_kwargs["stdin"] is codex_mod.subprocess.PIPE


def test_neutral_worker_wraps_actual_provider_invocation_in_isolation(tmp_path, monkeypatch):
    from substrate.execution.attempts import worker_model_executor as worker

    class FakeExecutor:
        identity = ModelExecutorIdentity("fake", "model", "v", "FakeExecutor")

        def readiness(self, *, env=None):
            seen["readiness_env"] = dict(env or {})
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
    seen_home = {}
    monkeypatch.setattr(
        worker,
        "open_attempt_credential_home",
        lambda **kw: seen_home.setdefault("kwargs", kw) and FakeHome(),
    )
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
        seen["input"] = kwargs["input_text"]
        return SimpleNamespace(returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(worker, "build_isolated_command", fake_wrap)
    monkeypatch.setattr(worker, "_run_isolated_with_tree_timeout", fake_run)

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
    assert seen["readiness_env"]["CODEX_HOME"] == str(tmp_path / "home" / ".codex")
    assert seen_home["kwargs"]["provider"] == "fake"


def test_worker_env_preserves_windows_process_runtime_without_user_profile() -> None:
    from substrate.execution.attempts.host_isolation import scrub_worker_env

    env = scrub_worker_env(
        {
            "PATH": "C:\\bin",
            "SystemRoot": "C:\\Windows",
            "WINDIR": "C:\\Windows",
            "ComSpec": "C:\\Windows\\System32\\cmd.exe",
            "PATHEXT": ".COM;.EXE;.BAT;.CMD",
            "SystemDrive": "C:",
            "ProgramData": "C:\\ProgramData",
            "ProgramFiles": "C:\\Program Files",
            "COMPUTERNAME": "DESKTOP-LVGUIQ9",
            "USERNAME": "antonys beast pc",
            "USERDOMAIN": "DESKTOP-LVGUIQ9",
            "USERPROFILE": "C:\\Users\\real",
            "APPDATA": "C:\\Users\\real\\AppData\\Roaming",
            "LOCALAPPDATA": "C:\\Users\\real\\AppData\\Local",
            "CODEX_HOME": "C:\\Users\\real\\.codex",
        }
    )

    assert env["SystemRoot"] == "C:\\Windows"
    assert env["WINDIR"] == "C:\\Windows"
    assert env["ComSpec"].endswith("cmd.exe")
    assert env["PATHEXT"]
    assert env["SystemDrive"] == "C:"
    assert env["ProgramData"] == "C:\\ProgramData"
    assert env["ProgramFiles"] == "C:\\Program Files"
    assert env["COMPUTERNAME"] == "DESKTOP-LVGUIQ9"
    assert env["USERNAME"] == "antonys beast pc"
    assert env["USERDOMAIN"] == "DESKTOP-LVGUIQ9"
    assert "USERPROFILE" not in env
    assert "APPDATA" not in env
    assert "LOCALAPPDATA" not in env
    assert "CODEX_HOME" not in env


def test_worker_env_keep_matching_is_case_insensitive_for_windows_keys() -> None:
    from substrate.execution.attempts.host_isolation import scrub_worker_env

    env = scrub_worker_env(
        {
            "SYSTEMROOT": "C:\\Windows",
            "COMSPEC": "C:\\Windows\\System32\\cmd.exe",
            "PROGRAMDATA": "C:\\ProgramData",
            "PROGRAMFILES": "C:\\Program Files",
            "systemdrive": "C:",
            "APPDATA": "C:\\Users\\real\\AppData\\Roaming",
            "codex_home": "C:\\Users\\real\\.codex",
        }
    )

    assert env["SYSTEMROOT"] == "C:\\Windows"
    assert env["COMSPEC"].endswith("cmd.exe")
    assert env["PROGRAMDATA"] == "C:\\ProgramData"
    assert env["PROGRAMFILES"] == "C:\\Program Files"
    assert env["systemdrive"] == "C:"
    assert "APPDATA" not in env
    assert "codex_home" not in env


def test_isolated_worker_timeout_terminates_child_process_tree(tmp_path):
    from substrate.execution.attempts.worker_model_executor import _run_isolated_with_tree_timeout

    pidfile = tmp_path / "child.pid"
    code = (
        "import os,subprocess,time\n"
        "p=subprocess.Popen(['sleep','60'])\n"
        f"open({str(pidfile)!r}, 'w').write(str(p.pid))\n"
        "time.sleep(60)\n"
    )
    started = time.monotonic()
    try:
        _run_isolated_with_tree_timeout(
            ["python3", "-c", code],
            caller="test_model_executor_timeout",
            timeout=0.2,
            cwd=str(tmp_path),
            env={"PATH": os.environ.get("PATH", "")},
            input_text="",
        )
    except subprocess.TimeoutExpired:
        pass
    else:
        raise AssertionError("timeout path did not raise")
    elapsed = time.monotonic() - started
    assert elapsed < 8, f"timeout cancellation waited for child lifetime: {elapsed:.2f}s"

    child_pid = int(pidfile.read_text(encoding="utf-8"))
    deadline = time.time() + 3
    while time.time() < deadline:
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        raise AssertionError(f"child process {child_pid} survived timeout cancellation")
