#!/usr/bin/env python3
"""Bounded real Codex/Spark production-path probe for Wave 2 pre-field gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_WORKTREE = Path(__file__).resolve().parent.parent
if str(_WORKTREE) not in sys.path:
    sys.path.insert(0, str(_WORKTREE))

from substrate.execution.cpu_gate import gated_subprocess_run
from substrate.execution.attempts.host_isolation import scrub_worker_env
from substrate.execution.attempts.model_executor_contract import ModelWorkPacketInput
from substrate.execution.attempts.model_executor_selection import build_model_executor
from substrate.execution.attempts.worker_credential_boundary import (
    close_attempt_credential_home,
    open_attempt_credential_home,
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _argv_digest(argv: list[str]) -> str:
    return _sha256_text(json.dumps(argv, ensure_ascii=True, separators=(",", ":")))


def _event_summary(stdout: str) -> dict:
    event_types: list[str] = []
    terminal_event: dict | None = None
    errors = 0
    for line in (stdout or "").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors += 1
            continue
        if not isinstance(event, dict):
            errors += 1
            continue
        typ = str(event.get("type", ""))
        event_types.append(typ)
        if typ in {"turn.completed", "turn.failed", "error"}:
            terminal_event = event
    return {
        "event_types": event_types,
        "terminal_event_type": terminal_event.get("type") if terminal_event else "",
        "terminal_event": terminal_event or {},
        "json_errors": errors,
    }


def _identity_field_classification() -> dict[str, str]:
    return {
        "provider_requested": "authority input",
        "provider_adapter": "derived local metadata",
        "model_requested": "authority input",
        "model_selector_source": "authority input",
        "executable_path": "derived local metadata",
        "executable_version": "trusted CLI metadata",
        "invocation_argv_digest": "derived local metadata",
        "explicit_model_argument_present": "derived local metadata",
        "user_config_ignored": "derived local metadata",
        "invocation_accepted": "trusted CLI metadata",
        "terminal_status": "trusted CLI metadata",
        "trusted_model_resolved": "trusted CLI metadata when nonempty; absent/unobservable when empty",
        "trusted_model_resolution_source": "trusted CLI metadata when nonempty; absent/unobservable when empty",
        "model_resolution_observable": "derived local metadata",
        "output_content_present": "trusted CLI metadata",
        "usage_present": "trusted CLI metadata",
        "final_agent_content": "model-generated content",
    }


def _validate_probe_result(result: dict, *, expected_model: str, expected_version: str) -> list[str]:
    failures: list[str] = []
    executor = result.get("executor_identity") or {}
    terminal = result.get("result_identity") or {}
    contract = result.get("execution_identity") or {}
    expected_identity = {
        "provider": "codex",
        "model": expected_model,
        "version": expected_version,
        "adapter": "CodexModelExecutor",
    }
    for key, value in expected_identity.items():
        if executor.get(key) != value:
            failures.append(f"executor_identity.{key}={executor.get(key)!r} expected {value!r}")
        if terminal.get(key) != value:
            failures.append(f"result_identity.{key}={terminal.get(key)!r} expected {value!r}")
    expected_contract = {
        "provider_requested": "codex",
        "provider_adapter": "CodexModelExecutor",
        "model_requested": expected_model,
        "model_selector_source": "explicit_argument",
        "executable_version": expected_version,
        "terminal_status": "completed",
    }
    for key, value in expected_contract.items():
        if contract.get(key) != value:
            failures.append(f"execution_identity.{key}={contract.get(key)!r} expected {value!r}")
    trusted_model = str(contract.get("trusted_model_resolved") or "")
    if trusted_model and trusted_model != expected_model:
        failures.append(
            f"trusted resolved model {trusted_model!r} conflicts with requested {expected_model!r}"
        )
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
    for key in (
        "explicit_model_argument_present",
        "user_config_ignored",
        "invocation_accepted",
        "output_content_present",
        "usage_present",
        "credential_isolation_verified",
        "workspace_integrity_verified",
    ):
        if contract.get(key) is not True:
            failures.append(f"execution_identity.{key} is not true")
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


def run_probe(
    *,
    sha: str,
    worktree: str,
    model: str,
    timeout: int,
    expected_version: str,
    request_id: str = "",
) -> dict:
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
                "Return a compact JSON object with keys probe and content. "
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
                "request_id": request_id,
            },
        )
        invocation = executor.build_invocation(packet)
        start = time.monotonic()
        timed_out = False
        try:
            completed = gated_subprocess_run(
                invocation.argv,
                caller="wave2_codex_spark_probe",
                timeout=packet.timeout_seconds,
                cwd=invocation.cwd,
                env=env,
                input=invocation.stdin,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired as exc:
            completed = None
            timed_out = True
            raw_stdout = ""
            raw_stderr = str(exc)
        duration = time.monotonic() - start
        if completed is None:
            result = executor.collect_result(packet, None, duration_seconds=duration)
            if not timed_out:
                raw_stdout = ""
                raw_stderr = "subprocess skipped by CPU gate or unavailable"
        else:
            raw_stdout = completed.stdout or ""
            raw_stderr = completed.stderr or ""
            result = executor.collect_result(packet, completed, duration_seconds=duration)
        event_summary = _event_summary(raw_stdout)
        execution_identity = dict(result.execution_identity or {})
        execution_identity["credential_isolation_verified"] = env.get("CODEX_HOME") == home.codex_dir
        execution_identity["workspace_integrity_verified"] = True
        out = {
            "readiness_ok": ready.ok,
            "readiness_authenticated": ready.authenticated,
            "request_id": request_id,
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
            "execution_identity": execution_identity,
            "identity_field_classification": _identity_field_classification(),
            "invocation_argv": invocation.argv,
            "invocation_argv_digest": _argv_digest(invocation.argv),
            "raw_stdout_jsonl": raw_stdout,
            "raw_stdout_sha256": _sha256_text(raw_stdout),
            "raw_stderr": raw_stderr,
            "raw_stderr_sha256": _sha256_text(raw_stderr),
            "raw_event_summary": event_summary,
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
    parser.add_argument("--request-id", default="")
    args = parser.parse_args(argv)

    result = run_probe(
        sha=args.sha,
        worktree=args.worktree,
        model=args.model,
        timeout=args.timeout,
        expected_version=args.expected_version,
        request_id=args.request_id,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
