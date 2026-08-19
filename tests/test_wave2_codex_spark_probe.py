from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "wave2_codex_spark_probe.py"


def _probe_module():
    spec = importlib.util.spec_from_file_location("wave2_codex_spark_probe_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_uses_provider_policy_and_spark_model_without_fallback() -> None:
    body = SCRIPT.read_text(encoding="utf-8")

    assert "sys.path.insert(0, str(_WORKTREE))" in body
    assert 'UMH_MODEL_EXECUTOR_PROVIDER"] = "codex"' in body
    assert 'UMH_CODEX_MODEL"] = model' in body
    assert "gpt-5.3-codex-spark" in body
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
        "model": "gpt-5.3-codex-spark",
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
        "attempt_private_codex_home": True,
        "credential_paths_inside_attempt_home": True,
        "attempt_home_exists_after_close": False,
        "run_root_exists_after_cleanup": False,
    }


def test_probe_validation_requires_exact_codex_spark_identity() -> None:
    module = _probe_module()
    result = _valid_probe_result()
    assert module._validate_probe_result(
        result,
        expected_model="gpt-5.3-codex-spark",
        expected_version="codex-cli 0.147.0",
    ) == []

    result["result_identity"]["model"] = "gpt-5.5"
    failures = module._validate_probe_result(
        result,
        expected_model="gpt-5.3-codex-spark",
        expected_version="codex-cli 0.147.0",
    )
    assert any("result_identity.model" in item for item in failures)


def test_probe_validation_fails_closed_on_readiness_or_cleanup_gap() -> None:
    module = _probe_module()
    result = _valid_probe_result()
    result["readiness_authenticated"] = False
    result["run_root_exists_after_cleanup"] = True
    failures = module._validate_probe_result(
        result,
        expected_model="gpt-5.3-codex-spark",
        expected_version="codex-cli 0.147.0",
    )
    assert "readiness_authenticated is not true" in failures
    assert "run_root_exists_after_cleanup is not false" in failures


def test_probe_main_exits_nonzero_when_exact_model_validation_fails(monkeypatch, capsys) -> None:
    module = _probe_module()
    result = _valid_probe_result()
    result["result_identity"]["model"] = "gpt-5.5"
    failures = module._validate_probe_result(
        result,
        expected_model="gpt-5.3-codex-spark",
        expected_version="codex-cli 0.147.0",
    )
    result["ok"] = not failures
    result["failure_reasons"] = failures
    monkeypatch.setattr(module, "run_probe", lambda **_kwargs: result)

    code = module.main(["--sha", "abc", "--worktree", "C:\\dev\\wave2_wt"])
    printed = capsys.readouterr().out
    assert code == 2
    assert "result_identity.model" in printed


def test_attempt_runner_pins_codex_spark_policy_before_worker_admission() -> None:
    body = (SCRIPT.parents[1] / "scripts" / "wave2_attempt_runner.py").read_text(encoding="utf-8")

    assert 'os.environ.setdefault("UMH_MODEL_EXECUTOR_PROVIDER", "codex")' in body
    assert 'os.environ.setdefault("UMH_CODEX_MODEL", "gpt-5.3-codex-spark")' in body
