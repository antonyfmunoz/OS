from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

from substrate.execution.attempts.model_executor_contract import (
    ModelExecutorIdentity,
    ModelExecutorReadiness,
    ModelInvocation,
    ModelTerminalResult,
)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "wave2_codex_sol_probe.py"


def _probe_module():
    spec = importlib.util.spec_from_file_location("wave2_codex_sol_probe_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_uses_provider_policy_and_spark_model_without_fallback() -> None:
    body = SCRIPT.read_text(encoding="utf-8")

    assert "sys.path.insert(0, str(_WORKTREE))" in body
    assert 'UMH_MODEL_EXECUTOR_PROVIDER"] = "codex"' in body
    assert 'UMH_CODEX_MODEL"] = model' in body
    assert "gpt-5.6-sol" in body
    assert "build_model_executor()" in body
    assert "DeterministicConformanceExecutor" not in body
    assert "Claude" not in body


def test_probe_uses_attempt_private_codex_home_and_cleans_residue() -> None:
    body = SCRIPT.read_text(encoding="utf-8")

    assert "open_attempt_credential_home" in body
    assert 'provider=executor.identity.provider' in body
    assert "scrub_worker_env" in body
    assert "home.env_overrides()" in body
    assert '"attempt_private_codex_home"' in body
    assert "close_attempt_credential_home(home)" in body
    assert "shutil.rmtree(run_root" in body


def test_probe_binds_identity_usage_and_proof_metadata() -> None:
    body = SCRIPT.read_text(encoding="utf-8")

    assert '"executor_identity"' in body
    assert '"result_identity"' in body
    assert '"usage"' in body
    assert '"proof_binding"' in body
    assert '"candidate_sha": sha' in body


def _valid_probe_result() -> dict:
    identity = {
        "provider": "codex",
        "model": "gpt-5.6-sol",
        "version": "codex-cli 0.147.0",
        "adapter": "CodexModelExecutor",
    }
    return {
        "readiness_ok": True,
        "readiness_authenticated": True,
        "executor_identity": dict(identity),
        "result_ok": True,
        "status": "succeeded",
        "has_real_content": True,
        "result_identity": dict(identity),
        "exit_code": 0,
        "timed_out": False,
        "execution_identity": {
            "provider_requested": "codex",
            "provider_adapter": "CodexModelExecutor",
            "model_requested": "gpt-5.6-sol",
            "model_selector_source": "explicit_argument",
            "executable_path": "C:\\Users\\antonys beast pc\\AppData\\Local\\npm\\codex.cmd",
            "executable_version": "codex-cli 0.147.0",
            "invocation_argv_digest": "abc",
            "explicit_model_argument_present": True,
            "user_config_ignored": True,
            "invocation_accepted": True,
            "terminal_status": "completed",
            "trusted_model_resolved": "gpt-5.6-sol",
            "trusted_model_resolution_source": "turn.completed.model",
            "model_resolution_observable": True,
            "output_content_present": True,
            "usage_present": True,
            "credential_isolation_verified": True,
            "workspace_integrity_verified": True,
        },
        "attempt_private_codex_home": True,
        "credential_paths_inside_attempt_home": True,
        "attempt_home_exists_after_close": False,
        "run_root_exists_after_cleanup": False,
    }


def test_probe_validation_rejects_unobservable_resolved_model_identity() -> None:
    module = _probe_module()
    result = _valid_probe_result()
    result["execution_identity"]["trusted_model_resolved"] = ""
    result["execution_identity"]["trusted_model_resolution_source"] = ""
    result["execution_identity"]["model_resolution_observable"] = False
    failures = module._validate_probe_result(
        result,
        expected_model="gpt-5.6-sol",
        expected_version="codex-cli 0.147.0",
    )
    assert "trusted resolved model identity is unavailable" in failures


def test_probe_validation_rejects_wrong_requested_or_result_identity() -> None:
    module = _probe_module()
    result = _valid_probe_result()
    result["execution_identity"]["model_requested"] = "gpt-5.5"
    result["result_identity"]["model"] = "gpt-5.5"
    failures = module._validate_probe_result(
        result,
        expected_model="gpt-5.6-sol",
        expected_version="codex-cli 0.147.0",
    )
    assert any("execution_identity.model_requested" in item for item in failures)
    assert any("result_identity.model" in item for item in failures)


def test_probe_validation_rejects_missing_explicit_model_argument() -> None:
    module = _probe_module()
    result = _valid_probe_result()
    result["execution_identity"]["explicit_model_argument_present"] = False
    failures = module._validate_probe_result(
        result,
        expected_model="gpt-5.6-sol",
        expected_version="codex-cli 0.147.0",
    )
    assert "execution_identity.explicit_model_argument_present is not true" in failures


def test_probe_validation_rejects_trusted_resolved_model_conflict() -> None:
    module = _probe_module()
    result = _valid_probe_result()
    result["execution_identity"]["trusted_model_resolved"] = "gpt-5.5"
    result["execution_identity"]["trusted_model_resolution_source"] = "turn.completed.model"
    result["execution_identity"]["model_resolution_observable"] = True
    failures = module._validate_probe_result(
        result,
        expected_model="gpt-5.6-sol",
        expected_version="codex-cli 0.147.0",
    )
    assert any("trusted resolved model" in item for item in failures)


def test_probe_validation_allows_trusted_resolved_model_match() -> None:
    module = _probe_module()
    result = _valid_probe_result()
    result["execution_identity"]["trusted_model_resolved"] = "gpt-5.6-sol"
    result["execution_identity"]["trusted_model_resolution_source"] = "turn.completed.model"
    result["execution_identity"]["model_resolution_observable"] = True
    assert module._validate_probe_result(
        result,
        expected_model="gpt-5.6-sol",
        expected_version="codex-cli 0.147.0",
    ) == []


def test_probe_validation_ignores_model_generated_identity_claims() -> None:
    module = _probe_module()
    result = _valid_probe_result()
    result["stdout_excerpt"] = '{"probe":"ok","model":"gpt-5","content":"live"}'
    result["raw_stdout_jsonl"] = (
        '{"type":"item.completed","item":{"text":"{\\"model\\":\\"gpt-5\\"}"}}\n'
        '{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":1}}\n'
    )
    assert module._validate_probe_result(
        result,
        expected_model="gpt-5.6-sol",
        expected_version="codex-cli 0.147.0",
    ) == []


def test_probe_returns_structured_timeout_before_outer_transport(tmp_path, monkeypatch) -> None:
    module = _probe_module()
    identity = ModelExecutorIdentity(
        provider="codex",
        model="gpt-5.6-sol",
        version="codex-cli 0.147.0",
        adapter="CodexModelExecutor",
    )

    class FakeExecutor:
        def readiness(self, *, env=None):
            return ModelExecutorReadiness(True, identity, authenticated=True)

        def build_invocation(self, packet):
            return ModelInvocation(
                argv=["codex", "exec", "--json", "-m", identity.model, "-"],
                stdin=packet.prompt,
                cwd=packet.worktree_path,
            )

        def collect_result(self, packet, completed, *, duration_seconds):
            return ModelTerminalResult(
                ok=False,
                status="failed",
                identity=identity,
                duration_seconds=duration_seconds,
                proof_binding=packet.proof_binding,
            )

    FakeExecutor.identity = identity

    home_root = tmp_path / "home"
    codex_dir = home_root / ".codex"
    codex_dir.mkdir(parents=True)
    fake_home = SimpleNamespace(
        home_path=str(home_root),
        codex_dir=str(codex_dir),
        credential_files=[],
        env_overrides=lambda: {"CODEX_HOME": str(codex_dir)},
    )

    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(
            cmd=["codex"],
            timeout=3,
            output=(
                '{"type":"thread.started"}\n'
                '{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":2}}\n'
            ),
            stderr="Authorization: Bearer secret-token\ncodex process tree terminated",
        )

    monkeypatch.setattr(module, "build_model_executor", lambda: FakeExecutor())
    monkeypatch.setattr(module, "open_attempt_credential_home", lambda **_kw: fake_home)
    monkeypatch.setattr(
        module,
        "close_attempt_credential_home",
        lambda _home: __import__("shutil").rmtree(home_root, ignore_errors=True),
    )
    monkeypatch.setattr(module, "_run_codex_process_tree", timeout)

    result = module.run_probe(
        sha="sha",
        worktree=str(tmp_path),
        model=identity.model,
        timeout=3,
        expected_version=identity.version,
        request_id="probe-timeout",
    )

    assert result["ok"] is False
    assert result["timed_out"] is True
    assert result["retry_class"] == "external_transient"
    assert "codex process tree terminated" in result["raw_stderr"]
    assert "secret-token" not in result["raw_stderr"]
    assert "[redacted credential-bearing line]" in result["raw_stderr"]
    assert "input_tokens" in result["raw_stdout_jsonl"]
    assert "output_tokens" in result["raw_stdout_jsonl"]
    assert "[redacted credential-bearing line]" not in result["raw_stdout_jsonl"]
    assert result["raw_event_summary"]["event_types"] == ["thread.started", "turn.completed"]
    assert result["run_root_exists_after_cleanup"] is False


def test_probe_sanitizes_completed_raw_stderr(tmp_path, monkeypatch) -> None:
    module = _probe_module()
    identity = ModelExecutorIdentity(
        provider="codex",
        model="gpt-5.6-sol",
        version="codex-cli 0.147.0",
        adapter="CodexModelExecutor",
    )

    class FakeExecutor:
        def readiness(self, *, env=None):
            return ModelExecutorReadiness(True, identity, authenticated=True)

        def build_invocation(self, packet):
            return ModelInvocation(
                argv=["codex", "exec", "--json", "-m", identity.model, "-"],
                stdin=packet.prompt,
                cwd=packet.worktree_path,
            )

        def collect_result(self, packet, completed, *, duration_seconds):
            return ModelTerminalResult(
                ok=True,
                status="succeeded",
                stdout='{"probe":"ok","content":"UMH Sol production path live."}',
                stderr=module._sanitize(completed.stderr or ""),
                exit_code=0,
                duration_seconds=duration_seconds,
                retry_class="none",
                usage={"input_tokens": 1, "output_tokens": 2},
                identity=identity,
                execution_identity={
                    "provider_requested": "codex",
                    "provider_adapter": "CodexModelExecutor",
                    "model_requested": identity.model,
                    "model_selector_source": "explicit_argument",
                    "executable_version": identity.version,
                    "explicit_model_argument_present": True,
                    "user_config_ignored": True,
                    "invocation_accepted": True,
                    "terminal_status": "completed",
                    "output_content_present": True,
                    "usage_present": True,
                },
                proof_binding=packet.proof_binding,
            )

    FakeExecutor.identity = identity

    home_root = tmp_path / "home"
    codex_dir = home_root / ".codex"
    codex_dir.mkdir(parents=True)
    fake_home = SimpleNamespace(
        home_path=str(home_root),
        codex_dir=str(codex_dir),
        credential_files=[],
        env_overrides=lambda: {"CODEX_HOME": str(codex_dir)},
    )

    def completed(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            ["codex"],
            0,
            stdout='{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":2}}\n',
            stderr="Authorization: Bearer synthetic-secret-token\nordinary diagnostic\n",
        )

    monkeypatch.setattr(module, "build_model_executor", lambda: FakeExecutor())
    monkeypatch.setattr(module, "open_attempt_credential_home", lambda **_kw: fake_home)
    monkeypatch.setattr(
        module,
        "close_attempt_credential_home",
        lambda _home: __import__("shutil").rmtree(home_root, ignore_errors=True),
    )
    monkeypatch.setattr(module, "_run_codex_process_tree", completed)

    result = module.run_probe(
        sha="sha",
        worktree=str(tmp_path),
        model=identity.model,
        timeout=3,
        expected_version=identity.version,
        request_id="probe-completed-secret",
    )

    assert "synthetic-secret-token" not in result["raw_stderr"]
    assert "[redacted credential-bearing line]" in result["raw_stderr"]
    assert "ordinary diagnostic" in result["raw_stderr"]
    assert result["raw_stderr_sha256"] == module._sha256_text(result["raw_stderr"])


def test_probe_returns_structured_readiness_timeout(tmp_path, monkeypatch) -> None:
    module = _probe_module()
    identity = ModelExecutorIdentity(
        provider="codex",
        model="gpt-5.6-sol",
        version="codex-cli 0.147.0",
        adapter="CodexModelExecutor",
    )

    class FakeExecutor:
        def __init__(self):
            self.identity = identity

        def readiness(self, *, env=None):
            raise subprocess.TimeoutExpired(
                cmd=["codex", "login", "status"],
                timeout=20,
                stderr=(
                    "Authorization: Bearer synthetic-readiness-token\n"
                    "codex status pipe never closed"
                ),
            )

    home_root = tmp_path / "home"
    codex_dir = home_root / ".codex"
    codex_dir.mkdir(parents=True)
    fake_home = SimpleNamespace(
        home_path=str(home_root),
        codex_dir=str(codex_dir),
        credential_files=[],
        env_overrides=lambda: {"CODEX_HOME": str(codex_dir)},
    )

    monkeypatch.setattr(module, "build_model_executor", lambda: FakeExecutor())
    monkeypatch.setattr(module, "open_attempt_credential_home", lambda **_kw: fake_home)
    monkeypatch.setattr(
        module,
        "close_attempt_credential_home",
        lambda _home: __import__("shutil").rmtree(home_root, ignore_errors=True),
    )

    result = module.run_probe(
        sha="sha",
        worktree=str(tmp_path),
        model=identity.model,
        timeout=180,
        expected_version=identity.version,
        request_id="probe-readiness-timeout",
    )

    assert result["ok"] is False
    assert result["timed_out"] is True
    assert result["status"] == "failed"
    assert result["execution_identity"]["terminal_status"] == "readiness_failed"
    assert "codex status pipe never closed" in result["raw_stderr"]
    assert "synthetic-readiness-token" not in result["raw_stderr"]
    assert "[redacted credential-bearing line]" in result["raw_stderr"]
    assert result["raw_stderr_sha256"] == module._sha256_text(result["raw_stderr"])
    assert result["attempt_home_exists_after_close"] is False
    assert result["run_root_exists_after_cleanup"] is False
    assert [item["phase"] for item in result["timeline"]] == [
        "executor_construct_start",
        "executor_construct_end",
        "credential_home_opened",
        "readiness_start",
        "readiness_exception",
    ]


def test_probe_main_flushes_terminal_json() -> None:
    body = SCRIPT.read_text(encoding="utf-8")
    assert "payload = json.dumps(result, indent=2)" in body
    assert "print(payload, flush=True)" in body


def test_probe_main_emits_request_bound_phase_events_to_stderr(
    tmp_path, monkeypatch, capsys
) -> None:
    module = _probe_module()

    result = _valid_probe_result()
    result["ok"] = True
    monkeypatch.setattr(module, "run_probe", lambda **_kwargs: dict(result))

    code = module.main(
        [
            "--sha",
            "sha",
            "--worktree",
            str(tmp_path),
            "--model",
            "gpt-5.6-sol",
            "--expected-version",
            "codex-cli 0.147.0",
            "--timeout",
            "1",
            "--request-id",
            "probe-phase-test",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    stdout_payload = json.loads(captured.out)
    assert stdout_payload["ok"] is True
    stdout_phase_names = [event["phase"] for event in stdout_payload["phase_events"]]
    assert "terminal_result_serialization_started" in stdout_phase_names
    assert "terminal_result_serialized" in stdout_phase_names
    assert "terminal_result_flush_started" in stdout_phase_names
    phases = [json.loads(line) for line in captured.err.splitlines() if line.strip()]
    names = [event["phase"] for event in phases]
    assert "arguments_parsed" in names
    assert "terminal_result_serialization_started" in names
    assert "terminal_result_flushed" in names
    assert "probe_exit" in names
    for event in phases:
        assert event["schema"] == "wave2_codex_sol_probe.phase.v1"
        assert event["request_id"] in {"", "probe-phase-test"}
        assert event["configured_inner_timeout"] in {None, 1.0}
        assert "timestamp_utc" in event
        assert "monotonic" in event
        assert "pid" in event


def test_probe_validation_fails_closed_on_readiness_or_cleanup_gap() -> None:
    module = _probe_module()
    result = _valid_probe_result()
    result["readiness_authenticated"] = False
    result["run_root_exists_after_cleanup"] = True
    failures = module._validate_probe_result(
        result,
        expected_model="gpt-5.6-sol",
        expected_version="codex-cli 0.147.0",
    )
    assert "readiness_authenticated is not true" in failures
    assert "run_root_exists_after_cleanup is not false" in failures


def test_probe_main_exits_nonzero_when_exact_model_validation_fails(monkeypatch, capsys) -> None:
    module = _probe_module()
    result = _valid_probe_result()
    result["execution_identity"]["trusted_model_resolved"] = "gpt-5.5"
    failures = module._validate_probe_result(
        result,
        expected_model="gpt-5.6-sol",
        expected_version="codex-cli 0.147.0",
    )
    result["ok"] = not failures
    result["failure_reasons"] = failures
    monkeypatch.setattr(module, "run_probe", lambda **_kwargs: result)

    code = module.main(["--sha", "abc", "--worktree", "C:\\dev\\wave2_wt"])
    printed = capsys.readouterr().out
    assert code == 2
    assert "trusted resolved model" in printed


def test_attempt_runner_pins_codex_sol_policy_before_worker_admission(
    monkeypatch,
) -> None:
    body = (SCRIPT.parents[1] / "scripts" / "wave2_attempt_runner.py").read_text(encoding="utf-8")

    assert 'os.environ["UMH_MODEL_EXECUTOR_PROVIDER"] = "codex"' in body
    assert 'os.environ["UMH_CODEX_MODEL"] = "gpt-5.6-sol"' in body
    assert 'setdefault("UMH_CODEX_MODEL"' not in body

    runner_path = SCRIPT.parents[1] / "scripts" / "wave2_attempt_runner.py"
    spec = importlib.util.spec_from_file_location("wave2_attempt_runner_under_test", runner_path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    observed: dict[str, str] = {}

    def _run_loop(**_kwargs) -> int:
        observed["provider"] = os.environ["UMH_MODEL_EXECUTOR_PROVIDER"]
        observed["model"] = os.environ["UMH_CODEX_MODEL"]
        return 0

    monkeypatch.setattr(runner, "run_loop", _run_loop)
    monkeypatch.setenv("UMH_MODEL_EXECUTOR_PROVIDER", "deterministic")
    monkeypatch.setenv("UMH_CODEX_MODEL", "ambient-alternate-model")
    monkeypatch.setenv("UMH_W2_DISPATCH_SECRET", "test-secret")
    monkeypatch.setattr(
        "sys.argv",
        ["wave2_attempt_runner.py", "--spool-root", "/tmp/test-wave2-spool"],
    )

    assert runner.main() == 0
    assert observed == {"provider": "codex", "model": "gpt-5.6-sol"}
