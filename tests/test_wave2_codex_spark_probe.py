from __future__ import annotations

from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "wave2_codex_spark_probe.py"


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
