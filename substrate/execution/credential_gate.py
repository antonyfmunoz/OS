"""Credential injection gate — validates credentials flow through 1Password.

Single choke point. Any computer use module that needs authentication
must call validate_credential_source() before proceeding.

Pattern: op run --env-file=<tpl> wraps collector commands on the executor
side. Env vars don't transit SSH — op resolves op:// URIs on the executor.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"


@dataclass
class CredentialGateResult:
    """Result of credential injection validation."""

    op_available: bool
    env_tpl_path: str
    env_tpl_exists: bool
    injection_ready: bool
    fallback_reason: str = ""


def validate_credential_source(
    env_tpl_name: str = ".env.beast.tpl",
) -> CredentialGateResult:
    """Check that 1Password credential injection is available.

    Returns CredentialGateResult. Callers check .injection_ready
    and decide whether to proceed with op run wrapping or fall back.
    """
    op_available = shutil.which("op") is not None
    env_tpl_path = os.path.join(_ROOT, "scripts", env_tpl_name)
    env_tpl_exists = os.path.exists(env_tpl_path)

    if not op_available:
        reason = "op CLI not found — install 1Password CLI or set OP_SERVICE_ACCOUNT_TOKEN"
        logger.warning("credential_gate: %s", reason)
        return CredentialGateResult(
            op_available=False,
            env_tpl_path=env_tpl_path,
            env_tpl_exists=env_tpl_exists,
            injection_ready=False,
            fallback_reason=reason,
        )

    if not env_tpl_exists:
        reason = f"env template not found: {env_tpl_path}"
        logger.warning("credential_gate: %s", reason)
        return CredentialGateResult(
            op_available=True,
            env_tpl_path=env_tpl_path,
            env_tpl_exists=False,
            injection_ready=False,
            fallback_reason=reason,
        )

    return CredentialGateResult(
        op_available=True,
        env_tpl_path=env_tpl_path,
        env_tpl_exists=True,
        injection_ready=True,
    )


def build_op_wrapped_command(
    inner_cmd: list[str],
    env_tpl_name: str = ".env.beast.tpl",
) -> tuple[list[str], CredentialGateResult]:
    """Wrap a command with op run for credential injection.

    Returns (wrapped_cmd, gate_result). If injection not ready,
    returns the original command unwrapped with gate_result explaining why.

    NOTE: this is the legacy fail-OPEN path (browser evidence collection
    falls back to cached auth). Provider-backed governed actions MUST use
    the fail-CLOSED seam below: resolve_provider_token_injection() /
    require_provider_token_injection().
    """
    gate = validate_credential_source(env_tpl_name)
    if gate.injection_ready:
        return (
            ["op", "run", f"--env-file={gate.env_tpl_path}", "--"] + inner_cmd,
            gate,
        )
    return inner_cmd, gate


# ── Provider-token seam (WP-P4-ADAPTERCALL-TOKEN-SEAM-001) ──────────────────
# Fail-closed credential resolution for provider-backed AdapterCalls
# (Gmail send, GitHub writes, Notion writes, Discord posts, ...).
#
# Contract:
#   - Token VALUES live only in 1Password. This module resolves injection
#     PRECONDITIONS (op CLI present, op env template present and complete)
#     and hands back an `op run` command prefix. It never reads, holds,
#     logs, or returns a token value.
#   - FAIL CLOSED: any missing precondition -> allowed=False with a typed,
#     non-secret refusal. Callers refuse the AdapterCall; they never degrade
#     to plaintext env or stored-token fallbacks.
#   - Provider tokens are NEVER stored in a projection DB (the EOS
#     `oauth_tokens` plaintext table pattern is banned) and never appear in
#     EOS DB responses.


@dataclass(frozen=True)
class ProviderTokenRequirement:
    """What credential material a provider-backed AdapterCall needs.

    Carries NAMES only — env var names and the op template filename.
    Values resolve inside `op run` on the executing node and never
    transit this type.
    """

    provider: str
    env_var_names: tuple[str, ...]
    tpl_name: str
    purpose: str = ""


@dataclass(frozen=True)
class AdapterCallCredentialDecision:
    """Fail-closed decision for one provider-backed AdapterCall.

    allowed=True  -> op_command_prefix is the exact `op run` prefix to
                     prepend to the adapter subprocess command.
    allowed=False -> refusal_code is one of REFUSAL_CODES and
                     refusal_reason is a human explanation. Both are
                     non-secret by construction (names and paths only).
    """

    allowed: bool
    provider: str
    op_command_prefix: tuple[str, ...] = ()
    refusal_code: str = ""
    refusal_reason: str = ""
    missing_env_var_names: tuple[str, ...] = ()


class ProviderTokenUnavailableError(RuntimeError):
    """Typed refusal for a provider-backed AdapterCall without injectable tokens.

    Message carries provider name + refusal code/reason only — never a
    secret value, never an op:// URI, never file contents.
    """

    def __init__(self, decision: AdapterCallCredentialDecision) -> None:
        self.decision = decision
        super().__init__(
            f"provider token injection refused for '{decision.provider}': "
            f"{decision.refusal_code} — {decision.refusal_reason}"
        )


REFUSAL_CODES = frozenset(
    {
        "unknown_provider",
        "op_cli_unavailable",
        "env_template_missing",
        "env_template_incomplete",
    }
)

# Provider requirement map. Keys are the provider ids adapter callers pass.
# Env var names document the material each adapter binary/SDK expects to
# find injected; the .tpl file (scripts/<tpl_name>) maps each name to an
# op:// URI. Templates are provisioned per node — absence = refusal.
PROVIDER_TOKEN_REQUIREMENTS: dict[str, ProviderTokenRequirement] = {
    "google_workspace": ProviderTokenRequirement(
        provider="google_workspace",
        env_var_names=(
            "GWS_OAUTH_CLIENT_ID",
            "GWS_OAUTH_CLIENT_SECRET",
            "GWS_OAUTH_REFRESH_TOKEN",
        ),
        tpl_name=".env.gws.tpl",
        purpose="Gmail send + Workspace write actions (future send_email)",
    ),
    "github": ProviderTokenRequirement(
        provider="github",
        env_var_names=("GITHUB_TOKEN",),
        tpl_name=".env.github.tpl",
        purpose="gh CLI writes (PR create/merge, branch ops)",
    ),
    "notion": ProviderTokenRequirement(
        provider="notion",
        env_var_names=("NOTION_API_KEY",),
        tpl_name=".env.notion.tpl",
        purpose="Notion API writes",
    ),
    "discord": ProviderTokenRequirement(
        provider="discord",
        env_var_names=("DISCORD_BOT_TOKEN",),
        tpl_name=".env.discord.tpl",
        purpose="Discord bot posts outside the resident bot service",
    ),
}


def _tpl_declared_env_var_names(tpl_path: str) -> frozenset[str]:
    """Return the env var NAMES declared in an op template.

    Reads only the left side of NAME=... lines — op:// references and any
    values on the right side are never parsed, stored, or returned.
    """
    names: set[str] = set()
    try:
        with open(tpl_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                names.add(line.split("=", 1)[0].strip())
    except OSError as exc:
        logger.debug("credential_gate: unreadable template %s: %s", tpl_path, exc)
    return frozenset(names)


def resolve_provider_token_injection(
    provider: str,
    scripts_dir: str = "",
) -> AdapterCallCredentialDecision:
    """Resolve 1Password injection for a provider-backed AdapterCall. FAIL CLOSED.

    Every failure path returns allowed=False with a typed refusal — this
    function never raises, never degrades to unwrapped execution, and never
    touches a secret value.
    """
    requirement = PROVIDER_TOKEN_REQUIREMENTS.get(provider)
    if requirement is None:
        return AdapterCallCredentialDecision(
            allowed=False,
            provider=provider,
            refusal_code="unknown_provider",
            refusal_reason=(
                "provider is not registered in PROVIDER_TOKEN_REQUIREMENTS; "
                "register its token requirements before any AdapterCall"
            ),
        )

    if shutil.which("op") is None:
        return AdapterCallCredentialDecision(
            allowed=False,
            provider=provider,
            refusal_code="op_cli_unavailable",
            refusal_reason="1Password CLI (op) not found on this node",
        )

    tpl_dir = scripts_dir or os.path.join(_ROOT, "scripts")
    tpl_path = os.path.join(tpl_dir, requirement.tpl_name)
    if not os.path.exists(tpl_path):
        return AdapterCallCredentialDecision(
            allowed=False,
            provider=provider,
            refusal_code="env_template_missing",
            refusal_reason=f"op env template not provisioned: {tpl_path}",
        )

    declared = _tpl_declared_env_var_names(tpl_path)
    missing = tuple(n for n in requirement.env_var_names if n not in declared)
    if missing:
        return AdapterCallCredentialDecision(
            allowed=False,
            provider=provider,
            refusal_code="env_template_incomplete",
            refusal_reason=(
                f"op env template {requirement.tpl_name} does not declare "
                f"required env vars: {', '.join(missing)}"
            ),
            missing_env_var_names=missing,
        )

    return AdapterCallCredentialDecision(
        allowed=True,
        provider=provider,
        op_command_prefix=("op", "run", f"--env-file={tpl_path}", "--"),
    )


def require_provider_token_injection(
    provider: str,
    scripts_dir: str = "",
) -> AdapterCallCredentialDecision:
    """Like resolve_provider_token_injection(), but raises on refusal.

    Raises ProviderTokenUnavailableError (typed, non-secret) when injection
    is not ready. For adapter boundaries that prefer exception flow.
    """
    decision = resolve_provider_token_injection(provider, scripts_dir=scripts_dir)
    if not decision.allowed:
        logger.warning(
            "credential_gate: refusing AdapterCall for provider=%s code=%s",
            decision.provider,
            decision.refusal_code,
        )
        raise ProviderTokenUnavailableError(decision)
    return decision
