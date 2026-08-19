#!/usr/bin/env python3
"""Bounded real Codex/Spark production-path probe for Wave 2 pre-field gates."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

_WORKTREE = Path(__file__).resolve().parent.parent
if str(_WORKTREE) not in sys.path:
    sys.path.insert(0, str(_WORKTREE))

from substrate.execution.attempts.host_isolation import scrub_worker_env
from substrate.execution.attempts.model_executor_contract import ModelWorkPacketInput
from substrate.execution.attempts.model_executor_selection import build_model_executor
from substrate.execution.attempts.worker_credential_boundary import (
    close_attempt_credential_home,
    open_attempt_credential_home,
)


def _validate_probe_result(result: dict, *, expected_model: str, expected_version: str) -> list[str]:
    failures: list[str] = []
    executor = result.get("executor_identity") or {}
    terminal = result.get("result_identity") or {}
    expected = {
        "provider": "codex",
        "model": expected_model,
        "version": expected_version,
        "adapter": "CodexModelExecutor",
    }
    for key, value in expected.items():
        if executor.get(key) != value:
            failures.append(f"executor_identity.{key}={executor.get(key)!r} expected {value!r}")
        if terminal.get(key) != value:
            failures.append(f"result_identity.{key}={terminal.get(key)!r} expected {value!r}")
    required_true = (
        "readiness_ok",
        "readiness_authenticated",
        "result_ok",
        "has_real_content",
        "attempt_private_codex_home",
        "credential_paths_inside_attempt_home",
    )
    for key in required_true:
        if result.get(key) is not True:
            failures.append(f"{key} is not true")
    required_false = ("attempt_home_exists_after_close", "run_root_exists_after_cleanup")
    for key in required_false:
        if result.get(key) is not False:
            failures.append(f"{key} is not false")
    if result.get("status") != "succeeded":
        failures.append(f"status={result.get('status')!r} expected 'succeeded'")
    if result.get("exit_code") != 0:
        failures.append(f"exit_code={result.get('exit_code')!r} expected 0")
    if result.get("timed_out"):
        failures.append("timed_out is true")
    if ("Deterministic" + "Conformance" + "Executor") in json.dumps(result, sort_keys=True):
        failures.append("deterministic conformance adapter appeared in probe evidence")
    if ("Clau" + "de") in json.dumps(result, sort_keys=True):
        failures.append("legacy provider fallback appeared in probe evidence")
    return failures


def run_probe(*, sha: str, worktree: str, model: str, timeout: int, expected_version: str) -> dict:
    os.environ["UMH_MODEL_EXECUTOR_PROVIDER"] = "codex"
    os.environ["UMH_CODEX_MODEL"] = model

    run_parent = Path(os.environ.get("UMH_RUN_ROOT", tempfile.gettempdir()))
    run_parent.mkdir(parents=True, exist_ok=True)
    run_root = tempfile.mkdtemp(prefix="umh_codex_spark_probe_", dir=str(run_parent))
    out: dict = {}
    executor = build_model_executor()
    home = open_attempt_credential_home(
        attempt_id="beast-spark-production-probe",
        run_root=run_root,
        provider=executor.identity.provider,
    )
    try:
        env = scrub_worker_env(dict(os.environ))
        env.update(home.env_overrides())
        ready = executor.readiness(env=env)
        packet = ModelWorkPacketInput(
            prompt=(
                "Return a compact JSON object with keys probe, model, and content. "
                "The content value must be the phrase UMH Spark production path live."
            ),
            worktree_path=worktree,
            timeout_seconds=timeout,
            max_turns=1,
            attempt_id="beast-spark-production-probe",
            package_hash="pre-field-probe",
            proof_binding={
                "candidate_sha": sha,
                "probe": "beast_codex_spark_production_path",
            },
        )
        result = executor.invoke(packet, env=env)
        out = {
            "readiness_ok": ready.ok,
            "readiness_authenticated": ready.authenticated,
            "executor_identity": ready.identity.proof_metadata(),
            "result_ok": result.ok,
            "status": result.status,
            "has_real_content": result.has_real_content,
            "result_identity": result.identity.proof_metadata() if result.identity else None,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "retry_class": result.retry_class,
            "usage": result.usage,
            "proof_binding": result.proof_binding,
            "stdout_excerpt": result.stdout[:220],
            "stderr_excerpt": result.stderr[:220],
            "attempt_private_codex_home": env.get("CODEX_HOME") == home.codex_dir,
            "credential_file_count": len(home.credential_files),
            "credential_paths_inside_attempt_home": all(
                str(p).startswith(home.home_path) for p in home.credential_files
            ),
        }
    finally:
        close_attempt_credential_home(home)
        residue_before_root_cleanup = Path(home.home_path).exists()
        shutil.rmtree(run_root, ignore_errors=True)
        out["attempt_home_exists_after_close"] = residue_before_root_cleanup
        out["run_root_exists_after_cleanup"] = Path(run_root).exists()
    failures = _validate_probe_result(out, expected_model=model, expected_version=expected_version)
    out["ok"] = not failures
    out["failure_reasons"] = failures
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--worktree", default=str(Path.cwd()))
    parser.add_argument("--model", default="gpt-5.3-codex-spark")
    parser.add_argument("--expected-version", default="codex-cli 0.147.0")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(argv)

    result = run_probe(
        sha=args.sha,
        worktree=args.worktree,
        model=args.model,
        timeout=args.timeout,
        expected_version=args.expected_version,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
