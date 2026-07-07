"""Tests — WP-P4-ADAPTERCALL-TOKEN-SEAM-001.

Fail-closed provider-token injection contract at the AdapterCall boundary
(substrate/execution/credential_gate.py). Every refusal path must be typed,
non-secret, and non-raising (resolve) or typed-raising (require). No test
touches a real token value or the 1Password CLI's real state beyond
presence detection, which is monkeypatched.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.execution import credential_gate
from substrate.execution.credential_gate import (
    PROVIDER_TOKEN_REQUIREMENTS,
    REFUSAL_CODES,
    AdapterCallCredentialDecision,
    ProviderTokenRequirement,
    ProviderTokenUnavailableError,
    require_provider_token_injection,
    resolve_provider_token_injection,
)

_OP_URI_PREFIX = "op" + "://"  # avoid a literal op:// URI in source


def _mock_op_present(monkeypatch):
    monkeypatch.setattr(
        credential_gate.shutil, "which", lambda name: "/usr/bin/op" if name == "op" else None
    )


def _mock_op_absent(monkeypatch):
    monkeypatch.setattr(credential_gate.shutil, "which", lambda name: None)


def _write_tpl(tmp_path, tpl_name: str, var_names: list[str]) -> str:
    lines = [f"{name}={_OP_URI_PREFIX}vault-placeholder/item/{name.lower()}" for name in var_names]
    tpl = tmp_path / tpl_name
    tpl.write_text("# test template\n" + "\n".join(lines) + "\n")
    return str(tmp_path)


class TestFailClosed:
    def test_unknown_provider_refuses(self):
        decision = resolve_provider_token_injection("no_such_provider")
        assert decision.allowed is False
        assert decision.refusal_code == "unknown_provider"
        assert decision.op_command_prefix == ()

    def test_blank_provider_refuses(self):
        decision = resolve_provider_token_injection("")
        assert decision.allowed is False
        assert decision.refusal_code == "unknown_provider"

    def test_op_cli_missing_refuses(self, monkeypatch, tmp_path):
        _mock_op_absent(monkeypatch)
        scripts_dir = _write_tpl(
            tmp_path,
            ".env.github.tpl",
            list(PROVIDER_TOKEN_REQUIREMENTS["github"].env_var_names),
        )
        decision = resolve_provider_token_injection("github", scripts_dir=scripts_dir)
        assert decision.allowed is False
        assert decision.refusal_code == "op_cli_unavailable"
        assert decision.op_command_prefix == ()

    def test_template_missing_refuses(self, monkeypatch, tmp_path):
        _mock_op_present(monkeypatch)
        decision = resolve_provider_token_injection("github", scripts_dir=str(tmp_path))
        assert decision.allowed is False
        assert decision.refusal_code == "env_template_missing"

    def test_template_incomplete_refuses_and_names_missing_vars(self, monkeypatch, tmp_path):
        _mock_op_present(monkeypatch)
        # Template declares only one of the three GWS vars.
        scripts_dir = _write_tpl(tmp_path, ".env.gws.tpl", ["GWS_OAUTH_CLIENT_ID"])
        decision = resolve_provider_token_injection("google_workspace", scripts_dir=scripts_dir)
        assert decision.allowed is False
        assert decision.refusal_code == "env_template_incomplete"
        assert set(decision.missing_env_var_names) == {
            "GWS_OAUTH_CLIENT_SECRET",
            "GWS_OAUTH_REFRESH_TOKEN",
        }

    def test_every_refusal_code_is_typed(self):
        assert {
            "unknown_provider",
            "op_cli_unavailable",
            "env_template_missing",
            "env_template_incomplete",
        } == set(REFUSAL_CODES)


class TestAllowedPath:
    def test_ready_provider_yields_op_prefix(self, monkeypatch, tmp_path):
        _mock_op_present(monkeypatch)
        req = PROVIDER_TOKEN_REQUIREMENTS["google_workspace"]
        scripts_dir = _write_tpl(tmp_path, req.tpl_name, list(req.env_var_names))
        decision = resolve_provider_token_injection("google_workspace", scripts_dir=scripts_dir)
        assert decision.allowed is True
        assert decision.refusal_code == ""
        assert decision.op_command_prefix == (
            "op",
            "run",
            f"--env-file={scripts_dir}/{req.tpl_name}",
            "--",
        )

    def test_extra_template_vars_are_fine(self, monkeypatch, tmp_path):
        _mock_op_present(monkeypatch)
        scripts_dir = _write_tpl(tmp_path, ".env.notion.tpl", ["NOTION_API_KEY", "SOMETHING_ELSE"])
        decision = resolve_provider_token_injection("notion", scripts_dir=scripts_dir)
        assert decision.allowed is True


class TestRequireRaisesTyped:
    def test_require_raises_on_refusal(self, monkeypatch, tmp_path):
        _mock_op_present(monkeypatch)
        with pytest.raises(ProviderTokenUnavailableError) as exc_info:
            require_provider_token_injection("github", scripts_dir=str(tmp_path))
        err = exc_info.value
        assert err.decision.provider == "github"
        assert err.decision.refusal_code == "env_template_missing"
        assert "github" in str(err)

    def test_require_returns_decision_when_ready(self, monkeypatch, tmp_path):
        _mock_op_present(monkeypatch)
        scripts_dir = _write_tpl(tmp_path, ".env.notion.tpl", ["NOTION_API_KEY"])
        decision = require_provider_token_injection("notion", scripts_dir=scripts_dir)
        assert decision.allowed is True

    def test_require_raises_for_unknown_provider(self):
        with pytest.raises(ProviderTokenUnavailableError):
            require_provider_token_injection("no_such_provider")


class TestNoSecretLeakage:
    def test_decision_never_carries_secret_material(self, monkeypatch, tmp_path):
        """Decisions carry names and paths only — never op URIs or values."""
        _mock_op_present(monkeypatch)
        req = PROVIDER_TOKEN_REQUIREMENTS["google_workspace"]
        scripts_dir = _write_tpl(tmp_path, req.tpl_name, list(req.env_var_names))
        for provider in ["google_workspace", "no_such_provider"]:
            decision = resolve_provider_token_injection(provider, scripts_dir=scripts_dir)
            assert _OP_URI_PREFIX not in repr(decision)
            assert "vault-placeholder" not in repr(decision)

    def test_error_message_is_non_secret(self, monkeypatch, tmp_path):
        _mock_op_present(monkeypatch)
        # Incomplete template — the refusal names missing VAR NAMES only.
        scripts_dir = _write_tpl(tmp_path, ".env.gws.tpl", ["GWS_OAUTH_CLIENT_ID"])
        with pytest.raises(ProviderTokenUnavailableError) as exc_info:
            require_provider_token_injection("google_workspace", scripts_dir=scripts_dir)
        message = str(exc_info.value)
        assert _OP_URI_PREFIX not in message
        assert "vault-placeholder" not in message

    def test_template_values_never_parsed(self, monkeypatch, tmp_path):
        """Even a template with a fake plaintext value never leaks it."""
        _mock_op_present(monkeypatch)
        tpl = tmp_path / ".env.notion.tpl"
        tpl.write_text("NOTION_API_KEY=fake-plaintext-value-should-never-appear\n")
        decision = resolve_provider_token_injection("notion", scripts_dir=str(tmp_path))
        assert decision.allowed is True
        assert "fake-plaintext-value" not in repr(decision)


class TestRequirementRegistry:
    def test_registry_rows_are_well_formed(self):
        for key, req in PROVIDER_TOKEN_REQUIREMENTS.items():
            assert isinstance(req, ProviderTokenRequirement)
            assert req.provider == key
            assert req.env_var_names, f"{key} declares no env vars"
            assert all(n.strip() for n in req.env_var_names)
            assert req.tpl_name.startswith(".env.") and req.tpl_name.endswith(".tpl")

    def test_google_workspace_registered_for_future_send_email(self):
        req = PROVIDER_TOKEN_REQUIREMENTS["google_workspace"]
        assert "GWS_OAUTH_REFRESH_TOKEN" in req.env_var_names

    def test_decision_is_frozen(self):
        decision = AdapterCallCredentialDecision(allowed=False, provider="x")
        with pytest.raises(Exception):
            decision.allowed = True  # type: ignore[misc]


class TestProvisionedGwsTemplate:
    """WP-P4-PROVIDER-TOKEN-VAULTING-001 — the committed google_workspace
    template must conform: declares exactly the required var names and
    carries op:// references ONLY (never a plaintext value)."""

    _REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _tpl_path(self) -> str:
        req = PROVIDER_TOKEN_REQUIREMENTS["google_workspace"]
        return os.path.join(self._REPO_ROOT, "scripts", req.tpl_name)

    def test_gws_template_is_provisioned(self):
        assert os.path.exists(self._tpl_path()), (
            "scripts/.env.gws.tpl must be committed (op references only) — "
            "it unblocks resolve_provider_token_injection('google_workspace')"
        )

    def test_gws_template_declares_exactly_required_vars(self):
        req = PROVIDER_TOKEN_REQUIREMENTS["google_workspace"]
        declared = {}
        with open(self._tpl_path(), "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                declared[name.strip()] = value.strip()
        assert set(declared) == set(req.env_var_names)

    def test_gws_template_values_are_op_references_only(self):
        with open(self._tpl_path(), "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                value = line.split("=", 1)[1].strip()
                assert value.startswith(_OP_URI_PREFIX), (
                    "template value must be an op reference, never a plaintext value"
                )

    def test_gws_seam_resolves_injectable_with_repo_scripts_dir(self, monkeypatch):
        """With the committed template, the seam returns injectable (op
        presence monkeypatched so the test is CI-node-agnostic)."""
        _mock_op_present(monkeypatch)
        scripts_dir = os.path.join(self._REPO_ROOT, "scripts")
        decision = resolve_provider_token_injection("google_workspace", scripts_dir=scripts_dir)
        assert decision.allowed is True
        assert decision.op_command_prefix[:2] == ("op", "run")
