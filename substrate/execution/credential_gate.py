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
    """
    gate = validate_credential_source(env_tpl_name)
    if gate.injection_ready:
        return (
            ["op", "run", f"--env-file={gate.env_tpl_path}", "--"] + inner_cmd,
            gate,
        )
    return inner_cmd, gate
