from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from infra.candidate import make_candidate_env


def test_candidate_env_requires_operator_api_key(tmp_path: Path) -> None:
    source = tmp_path / "source.env"
    source.write_text("CLERK_JWKS_URL=https://example.test/jwks.json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="UMH_OPERATOR_API_KEY"):
        make_candidate_env.build_candidate_env(source)


@pytest.mark.parametrize("value", ["", "   ", "\"   \""])
def test_candidate_env_rejects_empty_operator_api_key(tmp_path: Path, value: str) -> None:
    source = tmp_path / "source.env"
    source.write_text(f"UMH_OPERATOR_API_KEY={value}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="UMH_OPERATOR_API_KEY"):
        make_candidate_env.build_candidate_env(source)


def test_candidate_env_materializes_required_secret_without_audit_leak(tmp_path: Path) -> None:
    secret = "candidate-secret-value"
    env, audit = make_candidate_env.build_candidate_env(
        {
            "UMH_OPERATOR_API_KEY": secret,
            "UMH_MESH_RELAY_SECRET": "must-not-copy",
            "DISCORD_BOT_TOKEN": "must-not-copy",
        },
        extra_umh={"UMH_STATE_DIR": "/state/umh"},
    )

    assert env["UMH_OPERATOR_API_KEY"] == secret
    assert env["UMH_STATE_DIR"] == "/state/umh"
    assert "UMH_MESH_RELAY_SECRET" not in env
    assert "DISCORD_BOT_TOKEN" not in env
    assert "UMH_OPERATOR_API_KEY" in audit["required_present"]
    encoded_audit = json.dumps(audit)
    assert secret not in encoded_audit
    assert "must-not-copy" not in encoded_audit


def test_candidate_env_cli_fails_closed_without_required_secret(tmp_path: Path) -> None:
    out = tmp_path / "candidate.env"
    audit = tmp_path / "candidate.audit.json"
    result = subprocess.run(
        [
            sys.executable,
            str(Path(make_candidate_env.__file__).resolve()),
            "--source",
            str(tmp_path / "missing.env"),
            "--out",
            str(out),
            "--audit-out",
            str(audit),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 2
    assert not out.exists()
    payload = json.loads(result.stdout)
    assert "UMH_OPERATOR_API_KEY" in payload["audit"]["required_missing"]


def test_candidate_env_reads_allowlisted_secret_from_docker_source(monkeypatch) -> None:
    def fake_run(cmd, **_kwargs):
        assert cmd[:3] == ["docker", "inspect", "os-operator"]
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps(
                [
                    "UMH_OPERATOR_API_KEY=from-live-runtime",
                    "UMH_MESH_RELAY_SECRET=must-not-copy",
                ]
            ),
            stderr="",
        )

    monkeypatch.setattr(make_candidate_env.subprocess, "run", fake_run)

    source = make_candidate_env._parse_docker_container_env("os-operator")
    env, audit = make_candidate_env.build_candidate_env(source)

    assert env == {"UMH_OPERATOR_API_KEY": "from-live-runtime"}
    assert audit["included"] == ["UMH_OPERATOR_API_KEY"]
