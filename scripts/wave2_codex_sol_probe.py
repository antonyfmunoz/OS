#!/usr/bin/env python3
"""Bounded real Codex/Sol production-path probe for Wave 2 pre-field gates."""

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
from datetime import UTC, datetime
from pathlib import Path

_PHASE_SCHEMA_VERSION = "wave2_codex_sol_probe.phase.v1"
_PHASE_EVENTS: list[dict[str, object]] = []


def _initial_arg_value(name: str) -> str:
    try:
        idx = sys.argv.index(name)
    except ValueError:
        return ""
    if idx + 1 >= len(sys.argv):
        return ""
    return sys.argv[idx + 1]


def _initial_timeout() -> float | None:
    raw = _initial_arg_value("--timeout")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _phase_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _redact_phase_value(value: object) -> object:
    if isinstance(value, str):
        lowered = value.lower()
        if any(
            marker in lowered
            for marker in (
                "authorization",
                "api_key",
                "apikey",
                "password",
                "secret",
                "credential",
                "token",
                "op://",
            )
        ):
            return "[redacted]"
    return value


def _emit_phase(
    phase: str,
    *,
    request_id: str = "",
    configured_inner_timeout: float | None = None,
    deadline_monotonic: float | None = None,
    **extra: object,
) -> dict[str, object]:
    now = time.monotonic()
    rid = request_id or _initial_arg_value("--request-id")
    timeout_value = configured_inner_timeout
    if timeout_value is None:
        timeout_value = _initial_timeout()
    event: dict[str, object] = {
        "schema": _PHASE_SCHEMA_VERSION,
        "version": 1,
        "request_id": rid,
        "correlation_id": rid,
        "probe_id": rid,
        "phase": phase,
        "timestamp_utc": _phase_timestamp(),
        "monotonic": now,
        "configured_inner_timeout": timeout_value,
        "remaining_inner_budget": max(0.0, deadline_monotonic - now)
        if deadline_monotonic is not None
        else None,
        "pid": os.getpid(),
    }
    event.update({k: _redact_phase_value(v) for k, v in extra.items()})
    _PHASE_EVENTS.append(event)
    print(json.dumps(event, ensure_ascii=True, separators=(",", ":")), file=sys.stderr, flush=True)
    return event


_emit_phase("interpreter_entered")

_WORKTREE = Path(__file__).resolve().parent.parent
if str(_WORKTREE) not in sys.path:
    sys.path.insert(0, str(_WORKTREE))

from substrate.execution.attempts.host_isolation import scrub_worker_env  # noqa: E402
from substrate.execution.attempts.model_executor_contract import ModelWorkPacketInput  # noqa: E402
from substrate.execution.attempts.model_executor_selection import build_model_executor  # noqa: E402
from substrate.execution.attempts.model_executors.codex import (  # noqa: E402
    _run_codex_process_tree,
    _sanitize,
)
from substrate.execution.attempts.worker_credential_boundary import (  # noqa: E402
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
    trusted_model_source = str(contract.get("trusted_model_resolution_source") or "")
    if not trusted_model or not trusted_model_source:
        failures.append("trusted resolved model identity is unavailable")
    elif trusted_model != expected_model:
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
    timeline: list[dict[str, object]] = []

    def mark(phase: str, **extra: object) -> None:
        timeline.append({"phase": phase, "monotonic": time.monotonic(), **extra})

    def phase(phase_name: str, **extra: object) -> None:
        _emit_phase(
            phase_name,
            request_id=request_id,
            configured_inner_timeout=float(timeout),
            **extra,
        )

    run_parent = Path(os.environ.get("UMH_RUN_ROOT", tempfile.gettempdir()))
    run_parent.mkdir(parents=True, exist_ok=True)
    run_root = tempfile.mkdtemp(prefix="umh_codex_sol_probe_", dir=str(run_parent))
    out: dict = {}
    home = None
    try:
        mark("executor_construct_start")
        executor = build_model_executor()
        phase(
            "executor_constructed",
            provider=executor.identity.provider,
            adapter=executor.identity.adapter,
            version=executor.identity.version,
        )
        mark(
            "executor_construct_end",
            provider=executor.identity.provider,
            adapter=executor.identity.adapter,
            version=executor.identity.version,
        )
        home = open_attempt_credential_home(
            attempt_id="beast-sol-production-probe",
            run_root=run_root,
            provider=executor.identity.provider,
        )
        mark("credential_home_opened", codex_home=home.codex_dir)
        env = scrub_worker_env(dict(os.environ))
        env.update(home.env_overrides())
        mark("readiness_start")
        phase("readiness_started")
        try:
            ready = executor.readiness(env=env)
        except Exception as exc:  # noqa: BLE001
            mark("readiness_exception", exception=type(exc).__name__)
            exc_text = _sanitize(
                getattr(exc, "stderr", "") or getattr(exc, "output", "") or str(exc)
            )
            out = {
                "ok": False,
                "status": "failed",
                "failure_reasons": [f"readiness raised {type(exc).__name__}: {exc_text}"],
                "readiness_ok": False,
                "readiness_authenticated": False,
                "request_id": request_id,
                "executor_identity": executor.identity.proof_metadata(),
                "result_ok": False,
                "result_identity": executor.identity.proof_metadata(),
                "exit_code": None,
                "timed_out": isinstance(exc, subprocess.TimeoutExpired),
                "retry_class": "external_transient"
                if isinstance(exc, subprocess.TimeoutExpired)
                else "adapter_or_worker",
                "execution_identity": {
                    "provider_requested": "codex",
                    "provider_adapter": type(executor).__name__,
                    "model_requested": model,
                    "model_selector_source": "explicit_argument",
                    "executable_version": executor.identity.version,
                    "invocation_accepted": False,
                    "terminal_status": "readiness_failed",
                    "credential_isolation_verified": env.get("CODEX_HOME") == home.codex_dir,
                    "workspace_integrity_verified": True,
                },
                "identity_field_classification": _identity_field_classification(),
                "raw_stdout_jsonl": "",
                "raw_stdout_sha256": _sha256_text(""),
                "raw_stderr": exc_text,
                "raw_stderr_sha256": _sha256_text(exc_text),
                "raw_event_summary": _event_summary(""),
                "stdout_excerpt": "",
                "stderr_excerpt": exc_text[:220],
                "attempt_private_codex_home": env.get("CODEX_HOME") == home.codex_dir,
                "credential_file_count": len(home.credential_files),
                "credential_paths_inside_attempt_home": all(
                    str(p).startswith(home.home_path) for p in home.credential_files
                ),
            }
            return out
        phase("readiness_completed", ok=ready.ok, authenticated=ready.authenticated)
        mark(
            "readiness_end",
            ok=ready.ok,
            authenticated=ready.authenticated,
            reason=ready.reason[-120:] if ready.reason else "",
        )
        packet = ModelWorkPacketInput(
            prompt=(
                "Return a compact JSON object with keys probe and content. "
                "The content value must be the phrase UMH Sol production path live."
            ),
            worktree_path=worktree,
            timeout_seconds=timeout,
            max_turns=1,
            attempt_id="beast-sol-production-probe",
            package_hash="pre-field-probe",
            proof_binding={
                "candidate_sha": sha,
                "probe": "beast_codex_sol_production_path",
                "request_id": request_id,
            },
        )
        if not ready.ok or not ready.authenticated:
            out = {
                "ok": False,
                "status": "failed",
                "failure_reasons": [f"readiness failed: {_sanitize(ready.reason)}"],
                "readiness_ok": ready.ok,
                "readiness_authenticated": ready.authenticated,
                "request_id": request_id,
                "executor_identity": ready.identity.proof_metadata(),
                "result_ok": False,
                "result_identity": ready.identity.proof_metadata(),
                "exit_code": None,
                "timed_out": "timed out" in (ready.reason or "").lower(),
                "retry_class": "external_transient"
                if "timed out" in (ready.reason or "").lower()
                else "owner_auth_or_provider",
                "usage": {},
                "proof_binding": packet.proof_binding,
                "execution_identity": {
                    "provider_requested": "codex",
                    "provider_adapter": type(executor).__name__,
                    "model_requested": model,
                    "model_selector_source": "explicit_argument",
                    "executable_version": executor.identity.version,
                    "invocation_accepted": False,
                    "terminal_status": "readiness_failed",
                    "credential_isolation_verified": env.get("CODEX_HOME") == home.codex_dir,
                    "workspace_integrity_verified": True,
                },
                "identity_field_classification": _identity_field_classification(),
                "raw_stdout_jsonl": "",
                "raw_stdout_sha256": _sha256_text(""),
                "raw_stderr": _sanitize(ready.reason),
                "raw_stderr_sha256": _sha256_text(_sanitize(ready.reason)),
                "raw_event_summary": _event_summary(""),
                "stdout_excerpt": "",
                "stderr_excerpt": _sanitize(ready.reason)[:220],
                "attempt_private_codex_home": env.get("CODEX_HOME") == home.codex_dir,
                "credential_file_count": len(home.credential_files),
                "credential_paths_inside_attempt_home": all(
                    str(p).startswith(home.home_path) for p in home.credential_files
                ),
            }
            return out
        mark("invocation_build_start")
        invocation = executor.build_invocation(packet)
        mark("invocation_build_end", argv_digest=_argv_digest(invocation.argv), cwd=invocation.cwd)
        phase(
            "invocation_prepared",
            argv_digest=_argv_digest(invocation.argv),
            cwd=invocation.cwd,
        )
        start = time.monotonic()
        timed_out = False
        try:
            mark("cli_process_start", timeout_seconds=packet.timeout_seconds)
            deadline_monotonic = time.monotonic() + float(packet.timeout_seconds)

            def _process_phase(phase_name: str, extra: dict[str, object]) -> None:
                _emit_phase(
                    phase_name,
                    request_id=request_id,
                    configured_inner_timeout=float(packet.timeout_seconds),
                    deadline_monotonic=float(extra.get("deadline_monotonic") or deadline_monotonic),
                    **{k: v for k, v in extra.items() if k != "deadline_monotonic"},
                )

            completed = _run_codex_process_tree(
                invocation.argv,
                caller="wave2_codex_sol_probe",
                timeout=packet.timeout_seconds,
                cwd=invocation.cwd,
                env=env,
                input=invocation.stdin,
                capture_output=True,
                text=True,
                phase_callback=_process_phase,
            )
        except subprocess.TimeoutExpired as exc:
            mark("executor_timeout", timeout_seconds=packet.timeout_seconds)
            completed = None
            timed_out = True
            raw_stdout = _sanitize(
                exc.output.decode("utf-8", errors="replace")
                if isinstance(exc.output, bytes)
                else str(exc.output or "")
            )
            raw_stderr = _sanitize(
                exc.stderr.decode("utf-8", errors="replace")
                if isinstance(exc.stderr, bytes)
                else str(exc.stderr or exc)
            )
        duration = time.monotonic() - start
        if completed is None:
            mark("collect_timeout_result_start")
            result = executor.collect_result(packet, None, duration_seconds=duration)
            if timed_out:
                result.timed_out = True
                result.stderr = raw_stderr
                result.retry_class = "external_transient"
            if not timed_out:
                raw_stdout = ""
                raw_stderr = "subprocess skipped by CPU gate or unavailable"
            mark("collect_timeout_result_end", duration_seconds=duration)
        else:
            raw_stdout = _sanitize(completed.stdout or "")
            raw_stderr = _sanitize(completed.stderr or "")
            mark("collect_result_start", returncode=completed.returncode)
            result = executor.collect_result(packet, completed, duration_seconds=duration)
            mark("collect_result_end", duration_seconds=duration, ok=result.ok)
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
            "timeline": timeline,
            "attempt_private_codex_home": env.get("CODEX_HOME") == home.codex_dir,
            "credential_file_count": len(home.credential_files),
            "credential_paths_inside_attempt_home": all(
                str(p).startswith(home.home_path) for p in home.credential_files
            ),
        }
    except Exception as exc:  # noqa: BLE001
        mark("probe_exception", exception=type(exc).__name__)
        out = {
            "ok": False,
            "status": "failed",
            "failure_reasons": [f"probe failed before terminal result: {type(exc).__name__}: {_sanitize(str(exc))}"],
            "readiness_ok": False,
            "readiness_authenticated": False,
            "request_id": request_id,
            "executor_identity": None,
            "result_ok": False,
            "result_identity": None,
            "exit_code": None,
            "timed_out": isinstance(exc, subprocess.TimeoutExpired),
            "retry_class": "external_transient"
            if isinstance(exc, subprocess.TimeoutExpired)
            else "adapter_or_worker",
            "usage": {},
            "proof_binding": {"candidate_sha": sha, "request_id": request_id},
            "execution_identity": {
                "provider_requested": "codex",
                "provider_adapter": "",
                "model_requested": model,
                "model_selector_source": "explicit_argument",
                "invocation_accepted": False,
                "terminal_status": "probe_exception",
                "credential_isolation_verified": False,
                "workspace_integrity_verified": True,
            },
            "identity_field_classification": _identity_field_classification(),
            "raw_stdout_jsonl": "",
            "raw_stdout_sha256": _sha256_text(""),
            "raw_stderr": _sanitize(str(exc)),
            "raw_stderr_sha256": _sha256_text(_sanitize(str(exc))),
            "raw_event_summary": _event_summary(""),
            "stdout_excerpt": "",
            "stderr_excerpt": _sanitize(str(exc))[:220],
            "timeline": timeline,
            "attempt_private_codex_home": False,
            "credential_file_count": 0,
            "credential_paths_inside_attempt_home": False,
        }
    finally:
        if home is not None:
            close_attempt_credential_home(home)
            residue_before_root_cleanup = Path(home.home_path).exists()
        else:
            residue_before_root_cleanup = False
        shutil.rmtree(run_root, ignore_errors=True)
        out["attempt_home_exists_after_close"] = residue_before_root_cleanup
        out["run_root_exists_after_cleanup"] = Path(run_root).exists()
        out.setdefault("timeline", timeline)
        out["phase_events"] = list(_PHASE_EVENTS)
    failures = _validate_probe_result(out, expected_model=model, expected_version=expected_version)
    out["ok"] = not failures
    out["failure_reasons"] = failures
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--worktree", default=str(Path.cwd()))
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--expected-version", default="codex-cli 0.147.0")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--request-id", default="")
    args = parser.parse_args(argv)
    _emit_phase(
        "arguments_parsed",
        request_id=args.request_id,
        configured_inner_timeout=float(args.timeout),
        sha=args.sha,
        worktree=args.worktree,
        model=args.model,
    )

    result = run_probe(
        sha=args.sha,
        worktree=args.worktree,
        model=args.model,
        timeout=args.timeout,
        expected_version=args.expected_version,
        request_id=args.request_id,
    )
    _emit_phase(
        "terminal_result_serialization_started",
        request_id=args.request_id,
        configured_inner_timeout=float(args.timeout),
    )
    result["phase_events"] = list(_PHASE_EVENTS)
    payload = json.dumps(result, indent=2)
    _emit_phase(
        "terminal_result_serialized",
        request_id=args.request_id,
        configured_inner_timeout=float(args.timeout),
    )
    result["phase_events"] = list(_PHASE_EVENTS)
    payload = json.dumps(result, indent=2)
    _emit_phase(
        "terminal_result_flush_started",
        request_id=args.request_id,
        configured_inner_timeout=float(args.timeout),
    )
    result["phase_events"] = list(_PHASE_EVENTS)
    payload = json.dumps(result, indent=2)
    print(payload, flush=True)
    _emit_phase(
        "terminal_result_flushed",
        request_id=args.request_id,
        configured_inner_timeout=float(args.timeout),
    )
    _emit_phase("probe_exit", request_id=args.request_id, configured_inner_timeout=float(args.timeout))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
