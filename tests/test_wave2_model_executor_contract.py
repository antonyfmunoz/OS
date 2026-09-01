from __future__ import annotations

import json
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
from substrate.execution.attempts.model_executors.codex import (
    CodexModelExecutor,
    _file_sha256,
)
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
    assert selected_codex_model() == "gpt-5.6-sol"
    assert type(build_model_executor()).__name__ == "CodexModelExecutor"

    monkeypatch.setenv("UMH_MODEL_EXECUTOR_PROVIDER", "deterministic")
    try:
        build_model_executor()
    except ValueError as exc:
        assert "test-only" in str(exc)
    else:
        raise AssertionError(
            "deterministic executor must not be selectable without a test-only gate"
        )
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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


def test_governed_sol_binds_success_to_approved_exact_codex_executable(
    tmp_path, monkeypatch
):
    executable = tmp_path / "codex"
    executable.write_bytes(b"approved-codex-binary")
    executable.chmod(0o755)
    executable_hash = _file_sha256(str(executable))
    monkeypatch.setenv(
        "UMH_CODEX_APPROVED_EXECUTABLES_JSON",
        json.dumps({str(executable.resolve()): executable_hash}),
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: str(executable),
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._run_codex_metadata_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout="codex-cli 0.approved\n", stderr=""
        ),
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"text":"real Sol content"}}\n'
                '{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":2},'
                '"model":"gpt-5.6-sol"}\n'
            ),
            stderr="",
        ),
    )

    result = CodexModelExecutor(model="gpt-5.6-sol").invoke(_packet(tmp_path), env={})

    assert result.ok is True
    assert result.execution_identity["codex_executable_approved"] is True
    assert result.execution_identity["codex_executable_path"] == str(executable.resolve())
    assert result.execution_identity["codex_executable_sha256"] == executable_hash


def test_governed_sol_rejects_tampered_or_unapproved_codex_executable(tmp_path, monkeypatch):
    executable = tmp_path / "codex"
    executable.write_bytes(b"approved-before-tamper")
    approved_hash = _file_sha256(str(executable))
    executable.write_bytes(b"tampered-wrapper")
    executable.chmod(0o755)
    monkeypatch.setenv(
        "UMH_CODEX_APPROVED_EXECUTABLES_JSON",
        json.dumps({str(executable.resolve()): approved_hash}),
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: str(executable),
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._run_codex_metadata_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout="codex-cli fake\n", stderr=""
        ),
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"text":"claimed Sol content"}}\n'
                '{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":2},'
                '"model":"gpt-5.6-sol"}\n'
            ),
            stderr="",
        ),
    )

    result = CodexModelExecutor(model="gpt-5.6-sol").invoke(_packet(tmp_path), env={})

    assert result.ok is False
    assert result.execution_identity["codex_executable_approved"] is False
    assert "not approved by realpath/hash policy" in result.stderr


def test_governed_sol_rejects_byte_identical_copy_at_unapproved_realpath(
    tmp_path, monkeypatch
):
    approved = tmp_path / "approved" / "codex"
    copied = tmp_path / "copied" / "codex"
    approved.parent.mkdir()
    copied.parent.mkdir()
    approved.write_bytes(b"same-codex-binary")
    copied.write_bytes(approved.read_bytes())
    approved.chmod(0o755)
    copied.chmod(0o755)
    executable_hash = _file_sha256(str(approved))
    monkeypatch.setenv(
        "UMH_CODEX_APPROVED_EXECUTABLES_JSON",
        json.dumps({str(approved.resolve()): executable_hash}),
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: str(copied),
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._run_codex_metadata_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout="codex-cli copied\n", stderr=""
        ),
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"text":"claimed Sol content"}}\n'
                '{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":2},'
                '"model":"gpt-5.6-sol"}\n'
            ),
            stderr="",
        ),
    )

    result = CodexModelExecutor(model="gpt-5.6-sol").invoke(_packet(tmp_path), env={})

    assert result.ok is False
    assert result.execution_identity["codex_executable_path"] == str(copied.resolve())
    assert result.execution_identity["codex_executable_approved"] is False


def test_codex_adapter_rejects_empty_output(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
        lambda *a, **k: SimpleNamespace(
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"text":"real content"}}\n'
                "not-json\n"
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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


def test_codex_adapter_rejects_unobservable_terminal_model_even_with_exact_selector(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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
    assert not result.ok
    assert "missing trusted terminal model identity" in result.stderr
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
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


def test_codex_version_uses_owned_tree_timeout_and_fails_closed(monkeypatch):
    calls: list[tuple[list[str], str, float]] = []

    def timeout(cmd, *, caller, timeout, **_kwargs):
        calls.append((cmd, caller, timeout))
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout, stderr="wrapper hung")

    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
        timeout,
    )

    adapter = CodexModelExecutor(model="gpt-test")

    assert adapter.identity.version == ""
    assert calls == [(["/usr/bin/codex", "--version"], "codex_executor_version", 10.0)]


def test_codex_readiness_uses_owned_tree_timeout_and_fails_closed(monkeypatch):
    calls: list[tuple[list[str], str, float]] = []

    def run(cmd, *, caller, timeout, **_kwargs):
        calls.append((cmd, caller, timeout))
        if cmd[-1:] == ["--version"]:
            return SimpleNamespace(returncode=0, stdout="codex-cli 0.test\n", stderr="")
        raise subprocess.TimeoutExpired(
            cmd=cmd,
            timeout=timeout,
            output="",
            stderr="codex.cmd descendant retained stdio",
        )

    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._resolve_codex",
        lambda: "/usr/bin/codex",
    )
    monkeypatch.setattr(
        "substrate.execution.attempts.model_executors.codex._run_codex_process_tree",
        run,
    )

    ready = CodexModelExecutor(model="gpt-test").readiness(env={"CODEX_HOME": "attempt-home"})

    assert not ready.ok
    assert not ready.authenticated
    assert "timed out after 20s" in ready.reason
    assert "descendant retained stdio" in ready.reason
    assert calls == [
        (["/usr/bin/codex", "--version"], "codex_executor_version", 10.0),
        (["/usr/bin/codex", "login", "status"], "codex_executor_readiness", 20.0),
    ]


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


def test_codex_windows_timeout_returns_after_forced_drain_stays_blocked(monkeypatch):
    from substrate.execution.attempts.model_executors import codex as codex_mod

    calls: list[tuple[int, bool]] = []

    class FakeProc:
        pid = 4321
        returncode = None

        def communicate(self, *, input=None, timeout=None):
            raise subprocess.TimeoutExpired(
                cmd=["codex"],
                timeout=timeout,
                output="partial jsonl",
                stderr="stdio handle retained",
            )

        def poll(self):
            return None

    monkeypatch.setattr(codex_mod.os, "name", "nt")
    monkeypatch.setattr(codex_mod, "gated_popen", lambda *_args, **_kwargs: FakeProc())
    monkeypatch.setattr(codex_mod, "_owned_process_tree_pids", lambda pid: [pid])
    monkeypatch.setattr(codex_mod, "_alive_owned_pids", lambda _pids: [])

    def fake_taskkill(pid: int, *, force: bool):
        calls.append((pid, force))
        return SimpleNamespace(returncode=0, stdout=f"killed {pid} force={force}", stderr="")

    monkeypatch.setattr(codex_mod, "_taskkill_tree", fake_taskkill)

    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired) as exc:
        codex_mod._run_codex_process_tree(
            ["codex", "exec"],
            caller="unit",
            timeout=0.01,
            cwd=".",
            env={},
            input="prompt",
            capture_output=True,
            text=True,
        )

    assert time.monotonic() - started < 10
    assert calls == [(4321, False), (4321, True)]
    assert exc.value.output == "partial jsonl"
    assert "post-force drain timed out" in str(exc.value.stderr)
    assert "codex process still alive" in str(exc.value.stderr)


def test_codex_process_tree_emits_timeout_authority_phases(monkeypatch):
    from substrate.execution.attempts.model_executors import codex as codex_mod

    phases: list[tuple[str, dict[str, object]]] = []
    calls: list[tuple[int, bool]] = []

    class FakeProc:
        pid = 24601
        returncode = None

        def __init__(self):
            self.communicate_calls = 0

        def communicate(self, *, input=None, timeout=None):
            self.communicate_calls += 1
            if self.communicate_calls == 1:
                raise subprocess.TimeoutExpired(
                    cmd=["codex"],
                    timeout=timeout,
                    output='{"schema":"phase","phase":"fake_cli_started"}\n',
                    stderr="partial stderr",
                )
            self.returncode = -15
            return "", ""

        def poll(self):
            return self.returncode

    monkeypatch.setattr(codex_mod.os, "name", "nt")
    monkeypatch.setattr(codex_mod, "gated_popen", lambda *_args, **_kwargs: FakeProc())

    def fake_taskkill(pid: int, *, force: bool):
        calls.append((pid, force))
        return SimpleNamespace(returncode=0, stdout=f"killed {pid} force={force}", stderr="")

    monkeypatch.setattr(codex_mod, "_taskkill_tree", fake_taskkill)

    with pytest.raises(subprocess.TimeoutExpired) as exc:
        codex_mod._run_codex_process_tree(
            ["codex", "exec"],
            caller="unit",
            timeout=0.01,
            input="prompt",
            capture_output=True,
            text=True,
            phase_callback=lambda phase, extra: phases.append((phase, dict(extra))),
        )

    names = [phase for phase, _extra in phases]
    assert names[:3] == [
        "codex_process_spawn_started",
        "codex_process_spawned",
        "inner_deadline_armed",
    ]
    assert "inner_timeout_fired" in names
    assert "process_tree_termination_started" in names
    assert "process_tree_termination_completed" in names
    assert "stream_drain_started" in names
    assert "stream_drain_completed" in names
    assert phases[1][1]["pid"] == 24601
    assert phases[2][1]["timeout_seconds"] == 0.01
    assert calls == [(24601, False)]
    assert exc.value.output == '{"schema":"phase","phase":"fake_cli_started"}\n'


def test_codex_timeout_rejects_invalid_budget_before_spawn(monkeypatch):
    from substrate.execution.attempts.model_executors import codex as codex_mod

    spawned = False

    def fake_popen(*_args, **_kwargs):
        nonlocal spawned
        spawned = True
        raise AssertionError("popen must not run for invalid timeout")

    monkeypatch.setattr(codex_mod, "gated_popen", fake_popen)

    with pytest.raises(ValueError):
        codex_mod._run_codex_process_tree(
            ["codex", "exec"],
            caller="unit",
            timeout=0,
            capture_output=True,
            text=True,
        )

    assert spawned is False


def test_codex_watchdog_owns_deadline_when_phase_sink_blocks(monkeypatch):
    from substrate.execution.attempts.model_executors import codex as codex_mod

    calls: list[tuple[int, bool]] = []

    class FakeProc:
        pid = 3456
        returncode = None

        def __init__(self):
            self.communicate_calls = 0

        def communicate(self, *, input=None, timeout=None):
            self.communicate_calls += 1
            self.returncode = 0
            return "late success", ""
            return "", ""

        def poll(self):
            return self.returncode

    monkeypatch.setattr(codex_mod.os, "name", "nt")
    monkeypatch.setattr(codex_mod, "gated_popen", lambda *_args, **_kwargs: FakeProc())

    def fake_taskkill(pid: int, *, force: bool):
        calls.append((pid, force))
        return SimpleNamespace(returncode=0, stdout=f"killed {pid} force={force}", stderr="")

    monkeypatch.setattr(codex_mod, "_taskkill_tree", fake_taskkill)

    def blocking_phase(phase, extra):
        if phase == "codex_process_spawned":
            time.sleep(0.12)

    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired) as exc:
        codex_mod._run_codex_process_tree(
            ["codex", "exec"],
            caller="unit",
            timeout=0.02,
            input="prompt",
            capture_output=True,
            text=True,
            phase_callback=blocking_phase,
        )

    assert time.monotonic() - started < 5
    assert calls and calls[0] == (3456, False)
    assert "owner=watchdog" in str(exc.value.stderr)
    assert "late success" in str(exc.value.output)


def test_codex_phase_sink_exception_cannot_defeat_timeout(monkeypatch):
    from substrate.execution.attempts.model_executors import codex as codex_mod

    calls: list[tuple[int, bool]] = []

    class FakeProc:
        pid = 4567
        returncode = None

        def __init__(self):
            self.communicate_calls = 0

        def communicate(self, *, input=None, timeout=None):
            self.communicate_calls += 1
            if self.communicate_calls == 1:
                raise subprocess.TimeoutExpired(
                    cmd=["codex"],
                    timeout=timeout,
                    output="partial",
                    stderr="",
                )
            self.returncode = -15
            return "", ""

        def poll(self):
            return self.returncode

    monkeypatch.setattr(codex_mod.os, "name", "nt")
    monkeypatch.setattr(codex_mod, "gated_popen", lambda *_args, **_kwargs: FakeProc())
    monkeypatch.setattr(codex_mod, "_owned_process_tree_pids", lambda pid: [pid])
    monkeypatch.setattr(codex_mod, "_alive_owned_pids", lambda _pids: [])
    monkeypatch.setattr(
        codex_mod,
        "_taskkill_tree",
        lambda pid, *, force: (
            calls.append((pid, force))
            or SimpleNamespace(returncode=0, stdout="terminated", stderr="")
        ),
    )

    with pytest.raises(subprocess.TimeoutExpired) as exc:
        codex_mod._run_codex_process_tree(
            ["codex", "exec"],
            caller="unit",
            timeout=0.01,
            input="prompt",
            capture_output=True,
            text=True,
            phase_callback=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("sink failed")
            ),
        )

    assert exc.value.output == "partial"
    assert calls == [(4567, False)]


def test_codex_communicate_uses_remaining_deadline_after_spawn_observation(monkeypatch):
    from substrate.execution.attempts.model_executors import codex as codex_mod

    observed_timeouts: list[float] = []

    class FakeProc:
        pid = 5678
        returncode = 0

        def communicate(self, *, input=None, timeout=None):
            observed_timeouts.append(float(timeout))
            return "{}", ""

        def poll(self):
            return self.returncode

    monkeypatch.setattr(codex_mod, "gated_popen", lambda *_args, **_kwargs: FakeProc())

    def slow_observer(phase, extra):
        if phase == "codex_process_spawned":
            time.sleep(0.02)

    completed = codex_mod._run_codex_process_tree(
        ["codex", "exec"],
        caller="unit",
        timeout=0.2,
        input="prompt",
        capture_output=True,
        text=True,
        phase_callback=slow_observer,
    )

    assert completed is not None
    assert completed.returncode == 0
    assert observed_timeouts
    assert 0 < observed_timeouts[0] < 0.2


def test_codex_timeout_drain_preserves_later_stdout(monkeypatch):
    from substrate.execution.attempts.model_executors import codex as codex_mod

    class FakeProc:
        pid = 1357
        returncode = None

        def __init__(self):
            self.communicate_calls = 0

        def communicate(self, *, input=None, timeout=None):
            self.communicate_calls += 1
            if self.communicate_calls == 1:
                raise subprocess.TimeoutExpired(
                    cmd=["codex"],
                    timeout=timeout,
                    output="early phase\n",
                    stderr="early stderr",
                )
            self.returncode = -15
            return "late phase\n", "late stderr"

        def poll(self):
            return self.returncode

    monkeypatch.setattr(codex_mod.os, "name", "nt")
    monkeypatch.setattr(codex_mod, "gated_popen", lambda *_args, **_kwargs: FakeProc())
    monkeypatch.setattr(
        codex_mod,
        "_taskkill_tree",
        lambda pid, *, force: SimpleNamespace(returncode=0, stdout="terminated", stderr=""),
    )

    with pytest.raises(subprocess.TimeoutExpired) as exc:
        codex_mod._run_codex_process_tree(
            ["codex", "exec"],
            caller="unit",
            timeout=0.01,
            input="prompt",
            capture_output=True,
            text=True,
        )

    assert "early phase" in str(exc.value.output)
    assert "late phase" in str(exc.value.output)
    assert "early stderr" in str(exc.value.stderr)
    assert "late stderr" in str(exc.value.stderr)


def test_codex_forces_recorded_descendant_after_graceful_root_exit(monkeypatch):
    from substrate.execution.attempts.model_executors import codex as codex_mod

    forced: list[int] = []
    alive_checks = [[2222], []]

    class FakeProc:
        pid = 1111
        returncode = None

        def __init__(self):
            self.communicate_calls = 0

        def communicate(self, *, input=None, timeout=None):
            self.communicate_calls += 1
            if self.communicate_calls == 1:
                raise subprocess.TimeoutExpired(
                    cmd=["codex"], timeout=timeout, output="", stderr=""
                )
            self.returncode = -15
            return "", ""

        def poll(self):
            return self.returncode

    monkeypatch.setattr(codex_mod.os, "name", "nt")
    monkeypatch.setattr(codex_mod, "gated_popen", lambda *_args, **_kwargs: FakeProc())
    monkeypatch.setattr(codex_mod, "_owned_process_tree_pids", lambda pid: [pid, 2222])
    monkeypatch.setattr(codex_mod, "_alive_owned_pids", lambda _pids: alive_checks.pop(0))

    def fake_taskkill(pid: int, *, force: bool):
        return SimpleNamespace(returncode=0, stdout=f"tree kill {pid} force={force}", stderr="")

    monkeypatch.setattr(codex_mod, "_taskkill_tree", fake_taskkill)
    monkeypatch.setattr(
        codex_mod,
        "_force_exact_owned_pids",
        lambda pids: forced.extend(pids) or [f"forced exact {','.join(map(str, pids))}"],
    )

    with pytest.raises(subprocess.TimeoutExpired) as exc:
        codex_mod._run_codex_process_tree(
            ["codex", "exec"],
            caller="unit",
            timeout=0.01,
            input="prompt",
            capture_output=True,
            text=True,
        )

    assert forced == [2222]
    stderr = str(exc.value.stderr)
    assert "post-graceful drain completed" in stderr
    assert "owned process residue after graceful cleanup=2222" in stderr
    assert "forced exact 2222" in stderr


def test_codex_timeout_sends_first_kill_before_tree_snapshot(monkeypatch):
    from substrate.execution.attempts.model_executors import codex as codex_mod

    order: list[str] = []

    class FakeProc:
        pid = 3333
        returncode = None

        def __init__(self):
            self.communicate_calls = 0

        def communicate(self, *, input=None, timeout=None):
            self.communicate_calls += 1
            if self.communicate_calls == 1:
                raise subprocess.TimeoutExpired(
                    cmd=["codex"], timeout=timeout, output="", stderr=""
                )
            self.returncode = -15
            return "", ""

        def poll(self):
            return self.returncode

    monkeypatch.setattr(codex_mod.os, "name", "nt")
    monkeypatch.setattr(codex_mod, "gated_popen", lambda *_args, **_kwargs: FakeProc())

    def fake_tree_pids(pid):
        order.append("snapshot")
        return [pid]

    def fake_taskkill(pid: int, *, force: bool):
        order.append("force" if force else "graceful")
        return SimpleNamespace(returncode=0, stdout="terminated", stderr="")

    monkeypatch.setattr(codex_mod, "_owned_process_tree_pids", fake_tree_pids)
    monkeypatch.setattr(codex_mod, "_alive_owned_pids", lambda _pids: [])
    monkeypatch.setattr(codex_mod, "_taskkill_tree", fake_taskkill)

    with pytest.raises(subprocess.TimeoutExpired):
        codex_mod._run_codex_process_tree(
            ["codex", "exec"],
            caller="unit",
            timeout=0.01,
            input="prompt",
            capture_output=True,
            text=True,
        )

    assert order[:2] == ["graceful", "snapshot"]


def test_codex_nonwindows_timeout_owns_process_group(monkeypatch):
    from substrate.execution.attempts.model_executors import codex as codex_mod

    signaled: list[tuple[int, int]] = []
    popen_kwargs = {}

    class FakeProc:
        pid = 2468
        returncode = None

        def __init__(self):
            self.communicate_calls = 0

        def communicate(self, *, input=None, timeout=None):
            self.communicate_calls += 1
            if self.communicate_calls <= 2:
                raise subprocess.TimeoutExpired(
                    cmd=["codex"],
                    timeout=timeout,
                    output="partial",
                    stderr="open pipe",
                )
            self.returncode = -15
            return "", ""

        def poll(self):
            return self.returncode

    def fake_popen(*_args, **kwargs):
        popen_kwargs.update(kwargs)
        return FakeProc()

    monkeypatch.setattr(codex_mod.os, "name", "posix")
    monkeypatch.setattr(codex_mod, "gated_popen", fake_popen)
    monkeypatch.setattr(
        codex_mod.os,
        "killpg",
        lambda pid, sig: signaled.append((pid, sig)),
    )

    with pytest.raises(subprocess.TimeoutExpired) as exc:
        codex_mod._run_codex_process_tree(
            ["codex", "exec"],
            caller="unit",
            timeout=0.01,
            input="prompt",
            capture_output=True,
            text=True,
        )

    assert popen_kwargs["start_new_session"] is True
    assert signaled == [(2468, codex_mod.signal.SIGTERM), (2468, codex_mod.signal.SIGKILL)]
    assert "sent SIGTERM to process group 2468" in str(exc.value.stderr)


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
                usage={"input_tokens": 1, "output_tokens": 1},
                execution_identity={
                    "provider_requested": "codex",
                    "model_requested": "gpt-5.6-sol",
                    "trusted_model_resolved": "gpt-5.6-sol",
                    "trusted_model_resolution_source": "turn.completed.model",
                    "attempt_id": packet.attempt_id,
                    "package_hash": packet.package_hash,
                    "explicit_model_argument_present": True,
                    "user_config_ignored": True,
                    "invocation_accepted": True,
                    "model_resolution_observable": True,
                    "output_content_present": True,
                    "usage_present": True,
                    "codex_executable_approved": True,
                    "codex_executable_path": "/opt/codex/bin/codex",
                    "codex_executable_sha256": "a" * 64,
                    "codex_executable_version": "codex-cli 0.test",
                    "codex_executable_policy": "codex-executable-realpath-sha256-v1",
                    "codex_executable_policy_identity": "b" * 64,
                },
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
    monkeypatch.setattr(
        worker,
        "project_task_local_objective",
        lambda package, path: {"ok": True, "projected": True},
    )
    monkeypatch.setattr(worker, "_mark_projection_execution_context", lambda path, projection: None)
    monkeypatch.setattr(
        worker, "prepare_attempt_git_capability", lambda path, attempt_id: str(tmp_path / "refs")
    )
    monkeypatch.setattr(
        worker, "readonly_binds_for_scope", lambda scope, lease_root: ["secret.txt"]
    )
    monkeypatch.setattr(
        worker, "_capture_git", lambda path, base: (["app/main.py"], ["abc commit"], "diff")
    )

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


def test_codex_tools_revoked_a_becomes_enforced_readonly_policy(tmp_path, monkeypatch):
    from substrate.execution.attempts import worker_model_executor as worker

    seen = {}

    class FakeExecutor:
        identity = ModelExecutorIdentity("codex", "gpt-5.6-sol", "v", "FakeCodex")

        def readiness(self, *, env=None):
            return ModelExecutorReadiness(True, self.identity, authenticated=True)

        def build_invocation(self, packet):
            seen["packet_disallowed"] = list(packet.disallowed_tools)
            return ModelInvocation(argv=["codex", "exec"], stdin=packet.prompt)

        def collect_result(self, packet, completed, *, duration_seconds):
            code = getattr(completed, "returncode", 1)
            return ModelTerminalResult(
                ok=code == 0,
                status="succeeded" if code == 0 else "failed",
                stdout="real content",
                stderr=getattr(completed, "stderr", ""),
                exit_code=code,
                duration_seconds=duration_seconds,
                identity=self.identity,
                proof_binding=packet.proof_binding,
            )

    class FakeHome:
        def __init__(self):
            self.home_path = str(tmp_path / "home")
            self.tmp_path = str(tmp_path / "tmp")

        def env_overrides(self):
            return {"HOME": self.home_path, "CODEX_HOME": str(tmp_path / "home" / ".codex")}

    monkeypatch.setattr(worker, "build_model_executor", lambda provider=None: FakeExecutor())
    monkeypatch.setattr(worker, "make_lease_selfcontained", lambda path: None)
    monkeypatch.setattr(worker, "open_attempt_credential_home", lambda **kw: FakeHome())
    monkeypatch.setattr(worker, "close_attempt_credential_home", lambda home: None)
    monkeypatch.setattr(worker, "_close_home_or_fail", lambda home: None)
    monkeypatch.setattr(worker, "project_task_local_objective", lambda package, path: {"ok": True})
    monkeypatch.setattr(worker, "_mark_projection_execution_context", lambda path, projection: None)
    monkeypatch.setattr(
        worker, "prepare_attempt_git_capability", lambda path, attempt_id: str(tmp_path / "refs")
    )
    monkeypatch.setattr(
        worker,
        "readonly_binds_for_scope",
        lambda scope, lease_root: [str(tmp_path / "wt" / "secret.txt")],
    )
    monkeypatch.setattr(worker, "_capture_git", lambda path, base: ([], [], ""))

    def fake_wrap(inner, profile):
        seen["worktree_readonly"] = profile.worktree_readonly
        seen["readonly_subpaths"] = list(profile.readonly_subpaths)
        seen["writable_subpaths"] = list(profile.writable_subpaths)
        return ["sandbox", *inner]

    def fake_run(cmd, **kwargs):
        code = 1 if seen["worktree_readonly"] else 0
        return SimpleNamespace(returncode=code, stdout="", stderr="Read-only file system")

    monkeypatch.setattr(worker, "build_isolated_command", fake_wrap)
    monkeypatch.setattr(worker, "_run_isolated_with_tree_timeout", fake_run)

    wt = tmp_path / "wt"
    wt.mkdir()
    package = SimpleNamespace(
        governance_constraints=["writable_path_scope=['app/main.py']"],
        operation_identity={
            "run_id": "run-1",
            "task_id": "wp-a",
            "attempt_id": "ea-a1",
            "execution_authorization_ref": "objective_plan:opr:execution_authorization:v1",
        },
        package_hash="ph",
    )
    result = worker.run_worker_in_lease(
        package=package,
        lease=SimpleNamespace(worktree_path=str(wt), snapshot_ref="base"),
        attempt_id="ea-a1",
        run_root=str(tmp_path / "run"),
        provider="codex",
        disallowed_tools=["Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"],
    )

    assert result.ok is False
    assert result.status == "failed"
    assert result.commits == []
    assert result.files_changed == []
    assert result.capability_policy["mode"] == "source_mutation_denied"
    assert result.capability_policy["enforced"] is True
    assert result.capability_policy["run_id"] == "run-1"
    assert result.capability_policy["task_id"] == "wp-a"
    assert result.capability_policy["attempt_id"] == "ea-a1"
    assert seen["packet_disallowed"] == ["Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"]
    assert seen["worktree_readonly"] is True
    assert seen["readonly_subpaths"] == []
    assert seen["writable_subpaths"] == []


def test_codex_rejects_unsupported_capability_restrictions_before_invocation(tmp_path, monkeypatch):
    from substrate.execution.attempts import worker_model_executor as worker

    invoked = {"build": False}

    class FakeExecutor:
        identity = ModelExecutorIdentity("codex", "gpt-5.6-sol", "v", "FakeCodex")

        def readiness(self, *, env=None):
            return ModelExecutorReadiness(True, self.identity, authenticated=True)

        def build_invocation(self, packet):
            invoked["build"] = True
            return ModelInvocation(argv=["codex", "exec"], stdin=packet.prompt)

    class FakeHome:
        def __init__(self):
            self.home_path = str(tmp_path / "home")
            self.tmp_path = str(tmp_path / "tmp")

        def env_overrides(self):
            return {"HOME": self.home_path, "CODEX_HOME": self.home_path}

    monkeypatch.setattr(worker, "build_model_executor", lambda provider=None: FakeExecutor())
    monkeypatch.setattr(worker, "make_lease_selfcontained", lambda path: None)
    monkeypatch.setattr(worker, "open_attempt_credential_home", lambda **kw: FakeHome())
    monkeypatch.setattr(worker, "close_attempt_credential_home", lambda home: None)
    monkeypatch.setattr(worker, "_close_home_or_fail", lambda home: None)
    monkeypatch.setattr(worker, "project_task_local_objective", lambda package, path: {"ok": True})
    monkeypatch.setattr(worker, "_mark_projection_execution_context", lambda path, projection: None)
    monkeypatch.setattr(
        worker, "prepare_attempt_git_capability", lambda path, attempt_id: str(tmp_path / "refs")
    )
    monkeypatch.setattr(worker, "readonly_binds_for_scope", lambda scope, lease_root: [])

    wt = tmp_path / "wt"
    wt.mkdir()
    package = SimpleNamespace(
        governance_constraints=["writable_path_scope=['app/main.py']"],
        operation_identity={"run_id": "run-1", "task_id": "wp-a", "attempt_id": "ea-a1"},
        package_hash="ph",
    )
    result = worker.run_worker_in_lease(
        package=package,
        lease=SimpleNamespace(worktree_path=str(wt), snapshot_ref="base"),
        attempt_id="ea-a1",
        run_root=str(tmp_path / "run"),
        provider="codex",
        disallowed_tools=["Write"],
    )

    assert result.ok is False
    assert result.retry_class == "configuration"
    assert "unsupported execution capability restriction" in result.error
    assert invoked["build"] is False
    assert result.capability_policy["enforced"] is False


def test_codex_retry_without_denial_uses_normal_writable_policy(tmp_path, monkeypatch):
    from substrate.execution.attempts import worker_model_executor as worker

    seen = {}

    class FakeExecutor:
        identity = ModelExecutorIdentity("codex", "gpt-5.6-sol", "v", "FakeCodex")

        def readiness(self, *, env=None):
            return ModelExecutorReadiness(True, self.identity, authenticated=True)

        def build_invocation(self, packet):
            return ModelInvocation(argv=["codex", "exec"], stdin=packet.prompt)

        def collect_result(self, packet, completed, *, duration_seconds):
            return ModelTerminalResult(
                ok=True,
                status="succeeded",
                stdout="real content",
                exit_code=0,
                duration_seconds=duration_seconds,
                identity=self.identity,
                usage={"input_tokens": 1, "output_tokens": 1},
                execution_identity={
                    "provider_requested": "codex",
                    "model_requested": "gpt-5.6-sol",
                    "trusted_model_resolved": "gpt-5.6-sol",
                    "trusted_model_resolution_source": "turn.completed.model",
                    "attempt_id": packet.attempt_id,
                    "package_hash": packet.package_hash,
                    "explicit_model_argument_present": True,
                    "user_config_ignored": True,
                    "invocation_accepted": True,
                    "model_resolution_observable": True,
                    "output_content_present": True,
                    "usage_present": True,
                    "codex_executable_approved": True,
                    "codex_executable_path": "/opt/codex/bin/codex",
                    "codex_executable_sha256": "a" * 64,
                    "codex_executable_version": "codex-cli 0.test",
                    "codex_executable_policy": "codex-executable-realpath-sha256-v1",
                    "codex_executable_policy_identity": "b" * 64,
                },
                proof_binding=packet.proof_binding,
            )

    class FakeHome:
        def __init__(self):
            self.home_path = str(tmp_path / "home")
            self.tmp_path = str(tmp_path / "tmp")

        def env_overrides(self):
            return {"HOME": self.home_path, "CODEX_HOME": self.home_path}

    monkeypatch.setattr(worker, "build_model_executor", lambda provider=None: FakeExecutor())
    monkeypatch.setattr(worker, "validate_codex_executable_attestation", lambda _evidence: "")
    monkeypatch.setattr(worker, "make_lease_selfcontained", lambda path: None)
    monkeypatch.setattr(worker, "open_attempt_credential_home", lambda **kw: FakeHome())
    monkeypatch.setattr(worker, "close_attempt_credential_home", lambda home: None)
    monkeypatch.setattr(worker, "_close_home_or_fail", lambda home: None)
    monkeypatch.setattr(worker, "project_task_local_objective", lambda package, path: {"ok": True})
    monkeypatch.setattr(worker, "_mark_projection_execution_context", lambda path, projection: None)
    monkeypatch.setattr(
        worker, "prepare_attempt_git_capability", lambda path, attempt_id: str(tmp_path / "refs")
    )
    monkeypatch.setattr(
        worker,
        "readonly_binds_for_scope",
        lambda scope, lease_root: [str(tmp_path / "wt" / "secret.txt")],
    )
    monkeypatch.setattr(
        worker, "_capture_git", lambda path, base: (["app/main.py"], ["abc commit"], "diff")
    )
    monkeypatch.setattr(
        worker,
        "_run_isolated_with_tree_timeout",
        lambda cmd, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    def fake_wrap(inner, profile):
        seen["worktree_readonly"] = profile.worktree_readonly
        seen["writable_subpaths"] = list(profile.writable_subpaths)
        return ["sandbox", *inner]

    monkeypatch.setattr(worker, "build_isolated_command", fake_wrap)

    wt = tmp_path / "wt"
    wt.mkdir()
    package = SimpleNamespace(
        governance_constraints=["writable_path_scope=['app/main.py']"],
        operation_identity={"run_id": "run-1", "task_id": "wp-a", "attempt_id": "ea-a2"},
        package_hash="ph",
    )
    result = worker.run_worker_in_lease(
        package=package,
        lease=SimpleNamespace(worktree_path=str(wt), snapshot_ref="base"),
        attempt_id="ea-a2",
        run_root=str(tmp_path / "run"),
        provider="codex",
        disallowed_tools=[],
    )

    assert result.ok is True
    assert result.capability_policy["mode"] == "normal"
    assert result.capability_policy["enforced"] is False
    assert seen["worktree_readonly"] is False
    assert seen["writable_subpaths"], "normal workers retain their attempt-local git ref write bind"


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
