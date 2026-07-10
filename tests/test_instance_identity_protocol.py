"""Instance Identity Protocol — multi-tenant safety tests.

UMH is multi-tenant. Instance identity (AI name, founder, ventures, repo, active
venture) must resolve PER TENANT from context/BIS/env at runtime — never a
hardcoded literal. The canonical resolvers below are the ONE surface every layer
calls instead of embedding a tenant's values in code.

The multi-tenant contract these tests lock:
  1. With NO tenant context/env, every resolver returns a NEUTRAL fallback
     (empty / caller-supplied default) — NEVER a named tenant value. A named
     default would hand one seat another tenant's identity (cross-tenant leak).
  2. Resolvers are tenant-scoped: given an org_id/ctx they read only that
     tenant's state.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.state.business.business_instance import (  # noqa: E402
    get_active_venture_id,
    get_ai_name,
    get_founder_name,
    get_github_repo,
    get_ventures,
)


def _clear_instance_env(monkeypatch) -> None:
    for var in (
        "AI_NAME",
        "FOUNDER_NAME",
        "UMH_GITHUB_REPO",
        "GITHUB_REPO",
        "UMH_ACTIVE_VENTURE_ID",
        "UMH_ORG_ID",
        "EOS_ORG_ID",
    ):
        monkeypatch.delenv(var, raising=False)


def test_no_context_returns_neutral_not_named(monkeypatch):
    """With no tenant context/env, resolvers must NOT invent a tenant value."""
    _clear_instance_env(monkeypatch)

    # AI name: neutral empty, never "DEX"
    assert get_ai_name() == ""

    # Founder: caller-supplied neutral default, never "Antony"/"Munoz"
    assert get_founder_name(default="the founder") == "the founder"
    assert get_founder_name() == ""

    # Repo: neutral empty, never "antonyfmunoz/OS"
    assert get_github_repo() == ""

    # Active venture: neutral, never "lyfe_institute"
    assert get_active_venture_id(default="") == ""

    # Ventures: empty roster, never this tenant's hardcoded list
    assert get_ventures() == []


def test_named_tenant_values_never_leak_as_defaults(monkeypatch):
    """Guard: no resolver may return a known instance literal absent real config."""
    _clear_instance_env(monkeypatch)
    banned = {"dex", "antony", "munoz", "lyfe_institute", "empyrean_creative",
              "personal_brand", "antonyfmunoz/os", "initiate arena"}

    values = [
        get_ai_name(),
        get_founder_name(),
        get_github_repo(),
        get_active_venture_id(),
    ]
    for v in values:
        assert v.lower() not in banned, f"resolver leaked a tenant literal: {v!r}"

    for venture in get_ventures():
        assert venture["id"].lower() not in banned


def test_env_scopes_to_tenant(monkeypatch):
    """Env-supplied values resolve — proving the value FLOWS when configured."""
    _clear_instance_env(monkeypatch)
    monkeypatch.setenv("AI_NAME", "Aria")
    monkeypatch.setenv("FOUNDER_NAME", "Jordan Lee")
    monkeypatch.setenv("UMH_GITHUB_REPO", "acme/platform")
    monkeypatch.setenv("UMH_ACTIVE_VENTURE_ID", "acme_labs")

    assert get_ai_name() == "Aria"
    assert get_founder_name() == "Jordan Lee"
    assert get_github_repo() == "acme/platform"
    assert get_active_venture_id() == "acme_labs"
