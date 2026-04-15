"""
environments.py — Environment policy layer for the security module.

`core.environment` already provides full prod/sandbox/playground
isolation with path resolution, copy-on-write workspaces, and a
forbidden-writes list. This module adds the *policy* wrapper:

    - "which environments can this role see/touch?"
    - "which environment name corresponds to this logical tier?"
    - "at what risk does each environment gate auto-approve?"

Rather than re-implement what core.environment already does, this
module defers to it for path + guard logic and only adds the security
envelope.

Standard tiers
--------------
    prod      — production (core.environment.Environment.production)
                Strictest gate. Every HIGH or CRITICAL action requires
                an approval record.
    sandbox   — persistent sandbox (core.environment.make_sandbox)
                Auto-approves up to HIGH (risk still evaluated, still
                logged, but no human gate).
    dev       — ephemeral playground (core.environment.make_playground)
                Auto-approves everything except CRITICAL. Treated as a
                scratchpad — no destructive blast radius because the
                whole tree is thrown away on exit.

Usage
-----
    from core.security.environments import env_for_name, SecurityEnv

    sec_env = env_for_name("prod")
    sec_env.is_production       # True
    sec_env.env                 # → core.environment.Environment
    sec_env.auto_risk_ceiling   # → RiskTier.MEDIUM for prod
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core.capability import RiskTier, coerce_risk
from core.environment import (
    Environment,
    EnvMode,
    make_playground,
    make_sandbox,
)

EnvTier = Literal["prod", "sandbox", "dev"]


@dataclass
class EnvironmentPolicy:
    """Per-tier policy: what risk the environment auto-approves.

    `auto_risk_ceiling` — any action at or below this tier runs without
                          human approval (RBAC still applies).
    `allow_critical`    — if False, CRITICAL actions are hard-blocked
                          regardless of approvals.
    """

    tier: EnvTier
    auto_risk_ceiling: RiskTier
    allow_critical: bool
    description: str


_PROD_POLICY = EnvironmentPolicy(
    tier="prod",
    auto_risk_ceiling=RiskTier.MEDIUM,
    allow_critical=True,
    description="Production — HIGH/CRITICAL require approval",
)
_SANDBOX_POLICY = EnvironmentPolicy(
    tier="sandbox",
    auto_risk_ceiling=RiskTier.HIGH,
    allow_critical=True,
    description="Sandbox — auto-approves up to HIGH; CRITICAL still gated",
)
_DEV_POLICY = EnvironmentPolicy(
    tier="dev",
    auto_risk_ceiling=RiskTier.HIGH,
    allow_critical=False,
    description="Dev playground — auto-approves HIGH, CRITICAL blocked outright",
)


POLICY_BY_TIER: dict[EnvTier, EnvironmentPolicy] = {
    "prod": _PROD_POLICY,
    "sandbox": _SANDBOX_POLICY,
    "dev": _DEV_POLICY,
}


@dataclass
class SecurityEnv:
    """Wraps a core.environment.Environment with a security policy.

    All path operations delegate to `self.env` — this object never
    duplicates path logic. It only adds policy metadata and the
    `authorize_risk(risk)` helper the SecurityContext uses.
    """

    tier: EnvTier
    policy: EnvironmentPolicy
    env: Environment

    # ── Classification ────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        return self.tier == "prod"

    @property
    def is_isolated(self) -> bool:
        return self.tier in ("sandbox", "dev")

    @property
    def label(self) -> str:
        return f"{self.tier}:{self.env.name}"

    # ── Policy ────────────────────────────────────────────────────────

    def needs_approval(self, risk: str | RiskTier) -> bool:
        """True if the policy gates this risk behind a human approval."""
        r = coerce_risk(risk)
        if r == RiskTier.CRITICAL and not self.policy.allow_critical:
            # allow_critical=False means CRITICAL is blocked outright — the
            # SecurityContext will reject it. needs_approval returns True so
            # no caller tries to auto-run it anyway.
            return True
        return r.rank > self.policy.auto_risk_ceiling.rank

    def blocks(self, risk: str | RiskTier) -> bool:
        """Hard-block check. Returns True if the env refuses this risk
        entirely (dev blocks CRITICAL)."""
        r = coerce_risk(risk)
        return r == RiskTier.CRITICAL and not self.policy.allow_critical

    def guard_write(self, target: str) -> None:
        """Delegate to core.environment's write guard."""
        self.env.guard_write(target)

    def resolve(self, target: str) -> "object":
        """Delegate path resolution."""
        return self.env.resolve(target)

    def log_dir(self) -> "object":
        return self.env.log_dir

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "label": self.label,
            "policy": {
                "tier": self.policy.tier,
                "auto_risk_ceiling": self.policy.auto_risk_ceiling.value,
                "allow_critical": self.policy.allow_critical,
                "description": self.policy.description,
            },
            "environment": self.env.to_dict(),
        }


# ─── Factory ────────────────────────────────────────────────────────────────


def env_for_name(
    name: str,
    *,
    sandbox_name: str | None = None,
) -> SecurityEnv:
    """Resolve a tier name into a SecurityEnv.

    Accepted names:
        "prod" | "production"   → production
        "sandbox" | "sbx"       → persistent sandbox
        "dev" | "playground"    → ephemeral dev env

    `sandbox_name` lets callers pin a specific sandbox tree by name.
    """
    tier = _canon_tier(name)
    policy = POLICY_BY_TIER[tier]

    if tier == "prod":
        env = Environment.production()
    elif tier == "sandbox":
        env = make_sandbox(name=sandbox_name)
    else:
        env = make_playground(name=sandbox_name)

    return SecurityEnv(tier=tier, policy=policy, env=env)


def wrap_environment(env: Environment) -> SecurityEnv:
    """Take an existing core.environment.Environment and wrap it with
    the matching policy. Useful when the caller already has an env
    object (e.g., ActionSystem.env) and just needs the security view."""
    if env.mode == EnvMode.PRODUCTION:
        return SecurityEnv(tier="prod", policy=_PROD_POLICY, env=env)
    if env.mode == EnvMode.SANDBOX:
        return SecurityEnv(tier="sandbox", policy=_SANDBOX_POLICY, env=env)
    return SecurityEnv(tier="dev", policy=_DEV_POLICY, env=env)


def _canon_tier(name: str) -> EnvTier:
    n = (name or "").strip().lower()
    if n in ("prod", "production", ""):
        return "prod"
    if n in ("sandbox", "sbx"):
        return "sandbox"
    if n in ("dev", "playground", "play"):
        return "dev"
    raise ValueError(f"unknown environment tier: {name!r}")


__all__ = [
    "EnvironmentPolicy",
    "POLICY_BY_TIER",
    "SecurityEnv",
    "env_for_name",
    "wrap_environment",
]
