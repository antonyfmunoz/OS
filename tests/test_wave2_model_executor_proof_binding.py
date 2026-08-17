from __future__ import annotations

import os
import subprocess
from types import SimpleNamespace

from substrate.execution.attempts.verification import verify_attempt
from substrate.organism.proof_runtime import ProofRuntime


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def test_executor_metadata_is_persisted_in_attempt_proof(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "proof@umh.local")
    _git(repo, "config", "user.name", "proof")
    (repo / "app.py").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    (repo / "app.py").write_text("base\nchange\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-qm", "worker")

    attempt = SimpleNamespace(
        attempt_id="ea-proof",
        task_id="wp-proof",
        instruction_package_hash="pkg",
        worker_identity="model-executor@vps-host",
        tenant_id="tenant",
        plan_record_id="opr",
        plan_version=1,
        attempt_number=1,
        assignment_id="asn",
        lease_id="lease",
    )
    worker_result = SimpleNamespace(
        files_changed=["app.py"],
        commits=["worker"],
        executor={
            "provider": "codex",
            "model": "gpt-5.5",
            "version": "codex-cli 0.test",
            "adapter": "CodexModelExecutor",
        },
        usage={"input_tokens": 10, "output_tokens": 20},
        proof_binding={
            "attempt_id": "ea-proof",
            "task_id": "wp-proof",
            "package_hash": "pkg",
            "authorized_base": base,
            "executor_provider": "codex",
        },
        retry_class="not_retryable",
    )
    verdict = verify_attempt(
        attempt=attempt,
        assignment=SimpleNamespace(worker_identity="model-executor@vps-host"),
        lease=SimpleNamespace(worktree_path=str(repo), snapshot_ref=base),
        worker_result=worker_result,
        package_hash="pkg",
        verifier_identity="verifier:v1",
        verifier_role_id="role-verify",
        packet=SimpleNamespace(
            packet_id="wp-proof",
            requirements={"writable_path_scope": ["app.py"], "scope_declared": True},
        ),
        proof_runtime=ProofRuntime(store_path=str(tmp_path / "proofs.jsonl")),
    )

    assert verdict.passed
    proof = ProofRuntime(store_path=str(tmp_path / "proofs.jsonl")).reread_durable(verdict.proof_id)
    artifact = next(e for e in proof.evidence if e.evidence_type == "worker_artifacts")
    assert artifact.data["executor"]["provider"] == "codex"
    assert artifact.data["executor"]["adapter"] == "CodexModelExecutor"
    assert artifact.data["usage"] == {"input_tokens": 10, "output_tokens": 20}
    assert artifact.data["proof_binding"]["authorized_base"] == base
    assert artifact.data["retry_class"] == "not_retryable"
