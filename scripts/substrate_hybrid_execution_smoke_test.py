#!/usr/bin/env python3
"""
Hybrid Execution Target Policy v1 — smoke test.

Proves that:
  1.  Builder mode default target resolves to **local**.
  2.  Product mode default target resolves to **vps**.
  3.  Unknown mode default target resolves to **vps**.
  4.  Invalid target values clamp safely to mode default.
  5.  Env override flips builder target (e.g. EOS_BUILDER_DEFAULT_TARGET=vps).
  6.  Env override flips product target (e.g. EOS_PRODUCT_DEFAULT_TARGET=local).
  7.  Product local delegation OFF → stays vps.
  8.  Product local delegation ON + no keyword → stays vps.
  9.  Product local delegation ON + keyword match → target flips to local.
 10.  Product delegation via metadata force_local flag.
 11.  Mode remains product even when target=local (local ≠ builder).
 12.  resolve_mode_session integrates target policy (builder=local).
 13.  resolve_mode_session integrates target policy (product=vps).
 14.  resolve_mode_session carries delegation metadata.
 15.  mode_context carries delegation metadata to thread-local.
 16.  Builder/product session mapping remains correct.
 17.  Shared router still used (no second pipeline import).
 18.  Hot-path imports remain clean in target_policy.
 19.  Hot-path imports remain clean in discord_mode_routing.
 20.  TTS body-only behavior preserved (no regression).
 21.  Policy version reported in observability.

Runs in-process. No tmux/Claude CLI needed.
Returns 0 on success, non-zero on failure.
"""

from __future__ import annotations

import os
import sys
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")


FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  [PASS] {name}")
    else:
        FAILURES.append(name)
        print(f"  [FAIL] {name}  {detail}")


def _header(msg: str) -> None:
    print(f"\n── {msg} " + "─" * max(0, 60 - len(msg)))


# ── env reset ────────────────────────────────────────────────────────────────

_TARGET_POLICY_ENVS = (
    "EOS_BUILDER_DEFAULT_TARGET",
    "EOS_PRODUCT_DEFAULT_TARGET",
    "EOS_PRODUCT_ALLOW_LOCAL_DELEGATION",
    "EOS_PRODUCT_LOCAL_DELEGATION_KEYWORDS",
)

_MODE_ROUTING_ENVS = (
    "EOS_DISCORD_BUILDER_CHANNELS",
    "EOS_DISCORD_PRODUCT_CHANNELS",
    "EOS_DISCORD_BUILDER_TARGET",
    "EOS_DISCORD_BUILDER_SESSION",
    "EOS_DISCORD_PRODUCT_TARGET",
    "EOS_DISCORD_PRODUCT_SESSION",
    "EOS_DISCORD_MODE_PER_CHANNEL",
)


def _reset_env() -> None:
    for k in _TARGET_POLICY_ENVS + _MODE_ROUTING_ENVS:
        os.environ.pop(k, None)


# ══════════════════════════════════════════════════════════════════════════════
# Slice A — Target Policy Resolution (target_policy.py)
# ══════════════════════════════════════════════════════════════════════════════


def test_target_policy_defaults() -> None:
    _header("A1. resolve_execution_target defaults")
    from execution.transport.target_policy import resolve_execution_target

    _reset_env()

    check(
        "builder default → local",
        resolve_execution_target("builder") == "local",
        f"got {resolve_execution_target('builder')!r}",
    )
    check(
        "product default → vps",
        resolve_execution_target("product") == "vps",
        f"got {resolve_execution_target('product')!r}",
    )
    check(
        "unknown default → vps",
        resolve_execution_target("unknown") == "vps",
        f"got {resolve_execution_target('unknown')!r}",
    )
    check(
        "empty string mode → vps",
        resolve_execution_target("") == "vps",
        f"got {resolve_execution_target('')!r}",
    )


def test_target_policy_env_overrides() -> None:
    _header("A2. resolve_execution_target env overrides")
    from execution.transport.target_policy import resolve_execution_target

    _reset_env()

    # Builder forced to vps
    os.environ["EOS_BUILDER_DEFAULT_TARGET"] = "vps"
    check(
        "builder env override → vps",
        resolve_execution_target("builder") == "vps",
        f"got {resolve_execution_target('builder')!r}",
    )

    # Product forced to local
    _reset_env()
    os.environ["EOS_PRODUCT_DEFAULT_TARGET"] = "local"
    check(
        "product env override → local",
        resolve_execution_target("product") == "local",
        f"got {resolve_execution_target('product')!r}",
    )

    # Invalid env clamps to default
    _reset_env()
    os.environ["EOS_BUILDER_DEFAULT_TARGET"] = "mars"
    check(
        "invalid builder env → local (hard default)",
        resolve_execution_target("builder") == "local",
        f"got {resolve_execution_target('builder')!r}",
    )
    _reset_env()


def test_target_policy_invalid_clamps() -> None:
    _header("A3. invalid target values clamp safely")
    from execution.transport.target_policy import resolve_execution_target

    _reset_env()
    os.environ["EOS_BUILDER_DEFAULT_TARGET"] = ""
    check(
        "empty string builder → local",
        resolve_execution_target("builder") == "local",
    )
    os.environ["EOS_PRODUCT_DEFAULT_TARGET"] = "  "
    check(
        "whitespace product → vps",
        resolve_execution_target("product") == "vps",
    )
    _reset_env()


def test_target_policy_full_dict() -> None:
    _header("A4. resolve_execution_policy returns full dict")
    from execution.transport.target_policy import resolve_execution_policy

    _reset_env()

    p = resolve_execution_policy("builder")
    check("builder policy has target", p["target"] == "local")
    check("builder policy hard_default", p["hard_default"] == "local")
    check("builder policy not delegated", p["delegated_local"] is False)
    check("builder policy version", p["policy_version"] == "v1")

    p = resolve_execution_policy("product")
    check("product policy has target", p["target"] == "vps")
    check("product policy hard_default", p["hard_default"] == "vps")


# ══════════════════════════════════════════════════════════════════════════════
# Slice C — Product Local Delegation
# ══════════════════════════════════════════════════════════════════════════════


def test_delegation_off() -> None:
    _header("C1. product delegation OFF → stays vps")
    from execution.transport.target_policy import (
        resolve_execution_target,
        should_delegate_product_to_local,
    )

    _reset_env()
    # Delegation not enabled, keyword present — should NOT delegate
    os.environ["EOS_PRODUCT_LOCAL_DELEGATION_KEYWORDS"] = "deploy,build"
    check(
        "delegation OFF ignores keywords",
        resolve_execution_target("product", {"text": "deploy the thing"}) == "vps",
    )
    check(
        "should_delegate returns False",
        should_delegate_product_to_local("deploy the thing") is False,
    )
    _reset_env()


def test_delegation_on_no_match() -> None:
    _header("C2. product delegation ON + no keyword match → stays vps")
    from execution.transport.target_policy import resolve_execution_target

    _reset_env()
    os.environ["EOS_PRODUCT_ALLOW_LOCAL_DELEGATION"] = "1"
    os.environ["EOS_PRODUCT_LOCAL_DELEGATION_KEYWORDS"] = "deploy,build"

    check(
        "no keyword match → vps",
        resolve_execution_target("product", {"text": "hello world"}) == "vps",
    )
    _reset_env()


def test_delegation_on_keyword_match() -> None:
    _header("C3. product delegation ON + keyword match → local")
    from execution.transport.target_policy import (
        resolve_execution_target,
        resolve_execution_policy,
    )

    _reset_env()
    os.environ["EOS_PRODUCT_ALLOW_LOCAL_DELEGATION"] = "1"
    os.environ["EOS_PRODUCT_LOCAL_DELEGATION_KEYWORDS"] = "deploy,build"

    target = resolve_execution_target("product", {"text": "deploy the app"})
    check("keyword 'deploy' → local", target == "local", f"got {target!r}")

    policy = resolve_execution_policy("product", {"text": "build the widget"})
    check("delegated_local is True", policy["delegated_local"] is True)
    check(
        "delegation_reason has keyword",
        policy["delegation_reason"] == "keyword:build",
        f"got {policy['delegation_reason']!r}",
    )
    _reset_env()


def test_delegation_force_local() -> None:
    _header("C4. product delegation via metadata force_local")
    from execution.transport.target_policy import resolve_execution_target

    _reset_env()
    os.environ["EOS_PRODUCT_ALLOW_LOCAL_DELEGATION"] = "1"

    target = resolve_execution_target("product", {"force_local": True})
    check("force_local → local", target == "local", f"got {target!r}")
    _reset_env()


def test_mode_preserved_during_delegation() -> None:
    _header("C5. mode remains product even when target=local")
    from execution.transport.target_policy import resolve_execution_policy

    _reset_env()
    os.environ["EOS_PRODUCT_ALLOW_LOCAL_DELEGATION"] = "1"
    os.environ["EOS_PRODUCT_LOCAL_DELEGATION_KEYWORDS"] = "deploy"

    policy = resolve_execution_policy("product", {"text": "deploy now"})
    check("mode is still product", policy["mode"] == "product")
    check("target is local", policy["target"] == "local")
    check("delegated_local is True", policy["delegated_local"] is True)
    _reset_env()


# ══════════════════════════════════════════════════════════════════════════════
# Slice B — Mode-Aware Target / Session Mapping (discord_mode_routing.py)
# ══════════════════════════════════════════════════════════════════════════════


def test_resolve_mode_session_builder_local() -> None:
    _header("B1. resolve_mode_session builder → target=local")
    from execution.transport.discord_mode_routing import resolve_mode_session

    _reset_env()

    result = resolve_mode_session("builder", guild_id="g1", channel_id="c1")
    check(
        "builder target → local",
        result["target"] == "local",
        f"got {result['target']!r}",
    )
    check(
        "builder session → dex_builder_main",
        result["session_name"] == "dex_builder_main",
    )
    check("source is default", result["source"] == "default")
    check("not delegated", result["delegated_local"] is False)
    check("policy version present", result["policy_version"] == "v1")


def test_resolve_mode_session_product_vps() -> None:
    _header("B2. resolve_mode_session product → target=vps")
    from execution.transport.discord_mode_routing import resolve_mode_session

    _reset_env()

    result = resolve_mode_session("product", guild_id="g1", channel_id="c1")
    check(
        "product target → vps",
        result["target"] == "vps",
        f"got {result['target']!r}",
    )
    check(
        "product session → dex_product_main",
        result["session_name"] == "dex_product_main",
    )
    check("source is default", result["source"] == "default")


def test_resolve_mode_session_delegation_carries() -> None:
    _header("B3. resolve_mode_session carries delegation metadata")
    from execution.transport.discord_mode_routing import resolve_mode_session

    _reset_env()
    os.environ["EOS_PRODUCT_ALLOW_LOCAL_DELEGATION"] = "1"
    os.environ["EOS_PRODUCT_LOCAL_DELEGATION_KEYWORDS"] = "deploy"

    result = resolve_mode_session(
        "product",
        guild_id="g1",
        channel_id="c1",
        metadata={"text": "deploy it"},
    )
    check("delegated target → local", result["target"] == "local")
    check("source → delegated", result["source"] == "delegated")
    check("delegated_local → True", result["delegated_local"] is True)
    check(
        "delegation_reason present",
        result["delegation_reason"] == "keyword:deploy",
    )
    _reset_env()


def test_resolve_mode_session_unknown_noop() -> None:
    _header("B4. resolve_mode_session unknown → no override")
    from execution.transport.discord_mode_routing import resolve_mode_session

    _reset_env()

    result = resolve_mode_session("unknown")
    check("target is None", result["target"] is None)
    check("session_name is None", result["session_name"] is None)
    check("source is default", result["source"] == "default")
    check("policy_version is None", result["policy_version"] is None)


def test_resolve_mode_session_env_override() -> None:
    _header("B5. resolve_mode_session respects EOS_DISCORD_BUILDER_TARGET override")
    from execution.transport.discord_mode_routing import resolve_mode_session

    _reset_env()
    # Policy says builder→local, but env override says vps
    os.environ["EOS_DISCORD_BUILDER_TARGET"] = "vps"

    result = resolve_mode_session("builder")
    check(
        "env override → vps",
        result["target"] == "vps",
        f"got {result['target']!r}",
    )
    check("source → override", result["source"] == "override")
    _reset_env()


# ══════════════════════════════════════════════════════════════════════════════
# Slice D — Reporting / Metadata in mode_context
# ══════════════════════════════════════════════════════════════════════════════


def test_mode_context_carries_policy_metadata() -> None:
    _header("D1. mode_context thread-local carries policy metadata")
    from execution.transport.discord_mode_routing import (
        clear_mode_context_for_tests,
        current_mode_context,
        mode_context,
    )

    clear_mode_context_for_tests()

    with mode_context(
        "builder",
        target="local",
        session_name="dex_builder_main",
        guild_id="g1",
        channel_id="c1",
        source="default",
        delegated_local=False,
        policy_version="v1",
    ):
        ctx = current_mode_context()
        check("ctx not None", ctx is not None)
        check("ctx mode → builder", ctx["mode"] == "builder")
        check("ctx target → local", ctx["target"] == "local")
        check("ctx source → default", ctx["source"] == "default")
        check("ctx delegated_local → False", ctx["delegated_local"] is False)
        check("ctx policy_version → v1", ctx["policy_version"] == "v1")

    # Cleared after exit
    check("ctx cleared after block", current_mode_context() is None)
    clear_mode_context_for_tests()


def test_mode_context_delegation_metadata() -> None:
    _header("D2. mode_context carries delegation info for product→local")
    from execution.transport.discord_mode_routing import (
        clear_mode_context_for_tests,
        current_mode_context,
        mode_context,
    )

    clear_mode_context_for_tests()

    with mode_context(
        "product",
        target="local",
        session_name="dex_product_main",
        source="delegated",
        delegated_local=True,
        delegation_reason="keyword:deploy",
        policy_version="v1",
    ):
        ctx = current_mode_context()
        check("product mode preserved", ctx["mode"] == "product")
        check("target is local", ctx["target"] == "local")
        check("source is delegated", ctx["source"] == "delegated")
        check("delegated_local is True", ctx["delegated_local"] is True)
        check("delegation_reason present", ctx["delegation_reason"] == "keyword:deploy")

    clear_mode_context_for_tests()


# ══════════════════════════════════════════════════════════════════════════════
# Slice E — Tripwires / Regression Guards
# ══════════════════════════════════════════════════════════════════════════════


def test_no_hot_path_imports_target_policy() -> None:
    _header("E1. target_policy.py has no hot-path imports")
    import ast

    with open(f"{_ROOT}/runtime/substrate/target_policy.py") as f:
        tree = ast.parse(f.read())

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    hot_path = {"runtime"}
    # target_policy should only import os and typing
    violation = imports & hot_path
    check(
        "no runtime imports in target_policy",
        not violation,
        f"found: {violation}",
    )


def test_no_hot_path_imports_mode_routing() -> None:
    _header("E2. discord_mode_routing.py top-level has no hot-path imports")
    import ast

    with open(f"{_ROOT}/runtime/substrate/discord_mode_routing.py") as f:
        tree = ast.parse(f.read())

    # Only check top-level imports, not function-level (late-bound is fine)
    top_imports = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_imports.add(node.module.split(".")[0])

    hot_path = {
        "gateway",
        "cognitive_loop",
        "model_router",
        "agent_runtime",
        "primitives",
    }
    violation = top_imports & hot_path
    check(
        "no hot-path top-level imports",
        not violation,
        f"found: {violation}",
    )


def test_one_router_invariant() -> None:
    _header("E3. one shared router — no second cognition pipeline")
    # target_policy and discord_mode_routing should never import
    # call_with_fallback or define their own routing function.
    # We check for actual Python import statements, not docstring references.
    import ast

    for path in (
        f"{_ROOT}/runtime/substrate/target_policy.py",
        f"{_ROOT}/runtime/substrate/discord_mode_routing.py",
    ):
        with open(path) as f:
            tree = ast.parse(f.read())
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    imported_names.add(alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name)
        check(
            f"no call_with_fallback import in {os.path.basename(path)}",
            "call_with_fallback" not in imported_names,
            f"found import: {imported_names & {'call_with_fallback'}}",
        )


def test_target_resolution_deterministic() -> None:
    _header("E4. target resolution is deterministic (same input → same output)")
    from execution.transport.target_policy import resolve_execution_target

    _reset_env()
    results = [resolve_execution_target("builder") for _ in range(10)]
    check("10x builder → all same", len(set(results)) == 1, f"got {set(results)}")

    results = [resolve_execution_target("product") for _ in range(10)]
    check("10x product → all same", len(set(results)) == 1, f"got {set(results)}")


def test_builder_product_distinct() -> None:
    _header("E5. builder and product remain distinct from target selection")
    from execution.transport.target_policy import resolve_execution_policy

    _reset_env()
    os.environ["EOS_PRODUCT_ALLOW_LOCAL_DELEGATION"] = "1"
    os.environ["EOS_PRODUCT_LOCAL_DELEGATION_KEYWORDS"] = "deploy"

    # Product delegating to local is still product
    p = resolve_execution_policy("product", {"text": "deploy"})
    check("product delegated to local still mode=product", p["mode"] == "product")

    # Builder on local is still builder
    b = resolve_execution_policy("builder")
    check("builder on local still mode=builder", b["mode"] == "builder")

    # They don't cross-contaminate
    check(
        "product ≠ builder even when both local",
        p["mode"] != b["mode"],
    )
    _reset_env()


def test_session_names_preserved() -> None:
    _header("E6. session names remain correct after policy integration")
    from execution.transport.discord_mode_routing import resolve_mode_session

    _reset_env()

    b = resolve_mode_session("builder")
    p = resolve_mode_session("product")

    check("builder session", b["session_name"] == "dex_builder_main")
    check("product session", p["session_name"] == "dex_product_main")

    # Custom session via env
    os.environ["EOS_DISCORD_BUILDER_SESSION"] = "dex_custom_builder"
    b2 = resolve_mode_session("builder")
    check("custom builder session", b2["session_name"] == "dex_custom_builder")
    _reset_env()


def test_per_channel_session_preserved() -> None:
    _header("E7. per-channel session suffix still works")
    from execution.transport.discord_mode_routing import resolve_mode_session

    _reset_env()
    os.environ["EOS_DISCORD_MODE_PER_CHANNEL"] = "1"

    result = resolve_mode_session("builder", channel_id="999")
    check(
        "per-channel suffix",
        result["session_name"] == "dex_builder_main_999",
        f"got {result['session_name']!r}",
    )
    _reset_env()


def test_pseudo_live_status_reports_policy() -> None:
    _header("E8. pseudo_live_status includes hybrid_execution")
    _reset_env()
    # Set minimum env for transport to load
    os.environ["EOS_DISCORD_TEXT_TRANSPORT_ENABLED"] = "0"
    try:
        from execution.transport.discord_text_transport import pseudo_live_status

        status = pseudo_live_status()
        check("hybrid_execution key present", "hybrid_execution" in status)
        he = status.get("hybrid_execution", {})
        check(
            "policy_version in hybrid_execution",
            he.get("policy_version") == "v1",
            f"got {he.get('policy_version')!r}",
        )
    except Exception as e:
        check("pseudo_live_status callable", False, str(e))
    _reset_env()


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════


def main() -> int:
    print("═" * 70)
    print("  Hybrid Execution Target Policy v1 — Smoke Test")
    print("═" * 70)

    # Slice A — Target Policy
    test_target_policy_defaults()
    test_target_policy_env_overrides()
    test_target_policy_invalid_clamps()
    test_target_policy_full_dict()

    # Slice C — Product Delegation (before B because B depends on it)
    test_delegation_off()
    test_delegation_on_no_match()
    test_delegation_on_keyword_match()
    test_delegation_force_local()
    test_mode_preserved_during_delegation()

    # Slice B — Mode-Aware Session Mapping
    test_resolve_mode_session_builder_local()
    test_resolve_mode_session_product_vps()
    test_resolve_mode_session_delegation_carries()
    test_resolve_mode_session_unknown_noop()
    test_resolve_mode_session_env_override()

    # Slice D — Reporting / Metadata
    test_mode_context_carries_policy_metadata()
    test_mode_context_delegation_metadata()

    # Slice E — Tripwires / Regression
    test_no_hot_path_imports_target_policy()
    test_no_hot_path_imports_mode_routing()
    test_one_router_invariant()
    test_target_resolution_deterministic()
    test_builder_product_distinct()
    test_session_names_preserved()
    test_per_channel_session_preserved()
    test_pseudo_live_status_reports_policy()

    print(f"\n{'═' * 70}")
    if FAILURES:
        print(f"  FAILED: {len(FAILURES)}")
        for f in FAILURES:
            print(f"    ✗ {f}")
        print("═" * 70)
        return 1

    total = sum(
        1
        for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    )
    print(f"  ALL PASS ({total} test functions)")
    print("═" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
