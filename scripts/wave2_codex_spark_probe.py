#!/usr/bin/env python3
"""Bounded real Codex/Spark production-path probe for Wave 2 pre-field gates."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

from substrate.execution.attempts.host_isolation import scrub_worker_env
from substrate.execution.attempts.model_executor_contract import ModelWorkPacketInput
from substrate.execution.attempts.model_executor_selection import build_model_executor
from substrate.execution.attempts.worker_credential_boundary import (
    close_attempt_credential_home,
    open_attempt_credential_home,
)


def run_probe(*, sha: str, worktree: str, model: str, timeout: int) -> dict:
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
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--worktree", default=str(Path.cwd()))
    parser.add_argument("--model", default="gpt-5.3-codex-spark")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(argv)

    result = run_probe(
        sha=args.sha,
        worktree=args.worktree,
        model=args.model,
        timeout=args.timeout,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("result_ok") and result.get("has_real_content") else 2


if __name__ == "__main__":
    raise SystemExit(main())
