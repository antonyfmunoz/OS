#!/usr/bin/env python3
"""
Workflow Delegation Layer v1 — smoke test.

Proves that:
  1.  Builder-dev language → classified as workflow/builder_dev.
  2.  Product-runtime language → classified as workflow/product_runtime.
  3.  Ordinary chat → conversation.
  4.  Builder mode allows builder_dev.
  5.  Product mode does NOT become builder mode (builder_dev blocked).
  6.  Product local delegation + workflow metadata can coexist.
  7.  Metadata is attached cleanly via enrich_metadata().
  8.  Shared router still used (no new router import).
  9.  No second cognition pipeline (no cognitive_loop import).
 10.  TTS/body-only behavior preserved (no import interference).
 11.  Hot-path imports remain clean.
 12.  Skill/tool patterns classified correctly.
 13.  Content ops patterns classified correctly.
 14.  Analysis patterns classified correctly.
 15.  System ops patterns classified correctly.
 16.  Empty input → conversation.
 17.  Unknown mode restricts workflow kinds.
 18.  Extra keyword env vars work.
 19.  Classification is deterministic (same input → same output).
 20.  Policy dict shape is complete and correct.

Runs in-process. No external deps. Returns 0 on success, non-zero on failure.
"""

from __future__ import annotations

import os
import sys

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


def _reset_env() -> None:
    for k in (
        "EOS_WORKFLOW_EXTRA_BUILDER_KEYWORDS",
        "EOS_WORKFLOW_EXTRA_PRODUCT_KEYWORDS",
    ):
        os.environ.pop(k, None)


# ── test: classification ────────────────────────────────────────────────────


def test_builder_dev_classification() -> None:
    _header("Builder-dev classification")
    from runtime.substrate.workflow_delegation import classify_workflow_intent

    cases = [
        ("fix the bug in the router", "workflow", "builder_dev"),
        ("update the code in gateway.py", "workflow", "builder_dev"),
        ("add a new endpoint for users", "workflow", "builder_dev"),
        ("deploy the latest build", "workflow", "builder_dev"),
        ("run the smoke tests", "workflow", "builder_dev"),
        ("check the logs for errors", "workflow", "builder_dev"),
        ("install the new package", "workflow", "builder_dev"),
        ("merge the feature branch", "workflow", "builder_dev"),
        ("rebuild the docker container", "workflow", "builder_dev"),
    ]
    for text, expected_intent, expected_kind in cases:
        r = classify_workflow_intent(text, "builder")
        check(
            f"builder_dev: {text[:40]}",
            r["intent"] == expected_intent and r["workflow_kind"] == expected_kind,
            f"got intent={r['intent']} kind={r['workflow_kind']}",
        )


def test_product_runtime_classification() -> None:
    _header("Product-runtime classification")
    from runtime.substrate.workflow_delegation import classify_workflow_intent

    cases = [
        ("run the onboarding workflow for this user", "workflow", "product_runtime"),
        ("send the weekly report to the team", "workflow", "product_runtime"),
        ("schedule a daily check on pipeline health", "workflow", "product_runtime"),
        ("process the new lead from the form", "workflow", "product_runtime"),
    ]
    for text, expected_intent, expected_kind in cases:
        r = classify_workflow_intent(text, "product")
        check(
            f"product_runtime: {text[:40]}",
            r["intent"] == expected_intent and r["workflow_kind"] == expected_kind,
            f"got intent={r['intent']} kind={r['workflow_kind']}",
        )


def test_conversation_classification() -> None:
    _header("Conversation classification")
    from runtime.substrate.workflow_delegation import classify_workflow_intent

    cases = [
        "what backend are you using",
        "tell me about the project",
        "how are you doing today",
        "what time is it",
        "hello",
        "thanks for the help",
        "can you explain that again",
    ]
    for text in cases:
        r = classify_workflow_intent(text, "builder")
        check(
            f"conversation: {text[:40]}",
            r["intent"] == "conversation",
            f"got intent={r['intent']} kind={r['workflow_kind']}",
        )


def test_skill_tool_classification() -> None:
    _header("Skill/tool classification")
    from runtime.substrate.workflow_delegation import classify_workflow_intent

    cases = [
        "use the brave search tool to find competitors",
        "search the web for pricing data",
        "transcribe this audio file",
        "scrape the homepage of that website",
    ]
    for text in cases:
        r = classify_workflow_intent(text, "builder")
        check(
            f"skill_tool: {text[:40]}",
            r["intent"] == "skill_tool",
            f"got intent={r['intent']} kind={r['workflow_kind']}",
        )


def test_content_ops_classification() -> None:
    _header("Content ops classification")
    from runtime.substrate.workflow_delegation import classify_workflow_intent

    cases = [
        ("create a new post about the launch", "workflow", "content_ops"),
        ("publish the draft to instagram", "workflow", "content_ops"),
        ("edit the script for the video", "workflow", "content_ops"),
    ]
    for text, expected_intent, expected_kind in cases:
        r = classify_workflow_intent(text, "builder")
        check(
            f"content_ops: {text[:40]}",
            r["intent"] == expected_intent and r["workflow_kind"] == expected_kind,
            f"got intent={r['intent']} kind={r['workflow_kind']}",
        )


def test_analysis_classification() -> None:
    _header("Analysis classification")
    from runtime.substrate.workflow_delegation import classify_workflow_intent

    cases = [
        ("analyze the funnel data from last week", "workflow", "analysis"),
        ("compare these two approaches", "workflow", "analysis"),
        ("break down the revenue numbers", "workflow", "analysis"),
    ]
    for text, expected_intent, expected_kind in cases:
        r = classify_workflow_intent(text, "builder")
        check(
            f"analysis: {text[:40]}",
            r["intent"] == expected_intent and r["workflow_kind"] == expected_kind,
            f"got intent={r['intent']} kind={r['workflow_kind']}",
        )


def test_system_ops_classification() -> None:
    _header("System ops classification")
    from runtime.substrate.workflow_delegation import classify_workflow_intent

    cases = [
        ("check the system status", "workflow", "system_ops"),
        ("show the health metrics", "workflow", "system_ops"),
        ("clear the cache", "workflow", "system_ops"),
    ]
    for text, expected_intent, expected_kind in cases:
        r = classify_workflow_intent(text, "builder")
        check(
            f"system_ops: {text[:40]}",
            r["intent"] == expected_intent and r["workflow_kind"] == expected_kind,
            f"got intent={r['intent']} kind={r['workflow_kind']}",
        )


def test_planning_only_exclusion() -> None:
    _header("Planning-only exclusion (pass through to CC session)")
    from runtime.substrate.workflow_delegation import classify_workflow_intent

    cases = [
        "plan out how you would add a health check endpoint to the EOS API",
        "Plan out (but don't execute) how you would add a new agent",
        "outline how to add a feature for user auth",
        "sketch out steps to build the new handler",
        "just plan how to fix the bug in the router",
        "how would you add a new endpoint for webhooks",
        "walk me through adding a test for the pipeline",
        "think through how to implement the new module",
        "draft a plan for the deployment feature",
        "plan only — add the health check endpoint",
        "without executing, create a new route handler",
    ]
    for text in cases:
        r = classify_workflow_intent(text, "builder")
        check(
            f"planning_excluded: {text[:45]}",
            r["intent"] == "conversation" and r["workflow_kind"] == "none",
            f"got intent={r['intent']} kind={r['workflow_kind']} reason={r['reason']}",
        )

    # Verify that non-planning builder_dev messages still match
    still_builder = [
        "fix the bug in the router",
        "add a new endpoint for users",
        "deploy the latest build",
    ]
    for text in still_builder:
        r = classify_workflow_intent(text, "builder")
        check(
            f"still_builder_dev: {text[:40]}",
            r["intent"] == "workflow" and r["workflow_kind"] == "builder_dev",
            f"got intent={r['intent']} kind={r['workflow_kind']}",
        )


def test_empty_input() -> None:
    _header("Empty input")
    from runtime.substrate.workflow_delegation import classify_workflow_intent

    for text in ("", "   ", None):
        r = classify_workflow_intent(text or "", "builder")
        check(
            f"empty_input: {repr(text)[:20]}",
            r["intent"] == "conversation" and r["workflow_kind"] == "none",
            f"got intent={r['intent']}",
        )


# ── test: policy ────────────────────────────────────────────────────────────


def test_builder_allows_builder_dev() -> None:
    _header("Builder mode allows builder_dev")
    from runtime.substrate.workflow_delegation import (
        classify_workflow_intent,
        resolve_workflow_policy,
    )

    intent = classify_workflow_intent("fix the bug in the router", "builder")
    policy = resolve_workflow_policy("builder", intent)
    check("builder_allows_builder_dev", policy["allowed"] is True, f"got {policy}")
    check("execution_class_is_workflow", policy["execution_class"] == "workflow")


def test_product_blocks_builder_dev() -> None:
    _header("Product mode blocks builder_dev")
    from runtime.substrate.workflow_delegation import (
        classify_workflow_intent,
        resolve_workflow_policy,
    )

    intent = classify_workflow_intent("fix the bug in the router", "product")
    policy = resolve_workflow_policy("product", intent)
    check("product_blocks_builder_dev", policy["allowed"] is False, f"got {policy}")
    check(
        "blocked_reason_mentions_product",
        "product" in policy["policy_reason"],
        policy["policy_reason"],
    )
    check(
        "execution_class_falls_back_to_conversation",
        policy["execution_class"] == "conversation",
    )


def test_product_allows_product_runtime() -> None:
    _header("Product mode allows product_runtime")
    from runtime.substrate.workflow_delegation import (
        classify_workflow_intent,
        resolve_workflow_policy,
    )

    intent = classify_workflow_intent(
        "run the onboarding workflow for this user", "product"
    )
    policy = resolve_workflow_policy("product", intent)
    check("product_allows_product_runtime", policy["allowed"] is True, f"got {policy}")


def test_unknown_mode_restricts() -> None:
    _header("Unknown mode restricts workflow kinds")
    from runtime.substrate.workflow_delegation import (
        classify_workflow_intent,
        resolve_workflow_policy,
    )

    intent = classify_workflow_intent("fix the bug in the router", "unknown")
    policy = resolve_workflow_policy("unknown", intent)
    check("unknown_blocks_builder_dev", policy["allowed"] is False, f"got {policy}")

    intent2 = classify_workflow_intent("check system status", "unknown")
    policy2 = resolve_workflow_policy("unknown", intent2)
    check("unknown_allows_system_ops", policy2["allowed"] is True, f"got {policy2}")


def test_conversation_always_allowed() -> None:
    _header("Conversation always allowed in any mode")
    from runtime.substrate.workflow_delegation import (
        classify_workflow_intent,
        resolve_workflow_policy,
    )

    for mode in ("builder", "product", "unknown"):
        intent = classify_workflow_intent("hello how are you", mode)
        policy = resolve_workflow_policy(mode, intent)
        check(
            f"conversation_allowed_{mode}",
            policy["allowed"] is True,
            f"got {policy}",
        )


# ── test: metadata enrichment ──────────────────────────────────────────────


def test_enrich_metadata() -> None:
    _header("Metadata enrichment")
    from runtime.substrate.workflow_delegation import enrich_metadata

    meta: dict = {
        "transport": "discord",
        "discord_mode": "builder",
        "responder_target": "local",
    }
    result = enrich_metadata(meta, "fix the bug in the router", "builder")

    check("same_dict_returned", result is meta)
    check("has_workflow_intent", "workflow_intent" in meta)
    check("has_workflow_kind", "workflow_kind" in meta)
    check("has_workflow_allowed", "workflow_allowed" in meta)
    check("has_workflow_policy_reason", "workflow_policy_reason" in meta)
    check("has_workflow_confidence", "workflow_confidence" in meta)
    check("has_workflow_execution_class", "workflow_execution_class" in meta)
    check("has_workflow_delegation_version", "workflow_delegation_version" in meta)
    check("intent_is_workflow", meta["workflow_intent"] == "workflow")
    check("kind_is_builder_dev", meta["workflow_kind"] == "builder_dev")
    check("allowed_is_true", meta["workflow_allowed"] is True)
    check("version_is_v1", meta["workflow_delegation_version"] == "v1")


def test_enrich_preserves_existing() -> None:
    _header("Enrichment preserves existing metadata")
    from runtime.substrate.workflow_delegation import enrich_metadata

    meta: dict = {
        "transport": "discord",
        "guild_id": "g123",
        "channel_id": "c456",
        "discord_mode": "product",
        "responder_target": "vps",
        "delegated_local": False,
    }
    enrich_metadata(meta, "what is the weather", "product")
    check("transport_preserved", meta["transport"] == "discord")
    check("guild_preserved", meta["guild_id"] == "g123")
    check("channel_preserved", meta["channel_id"] == "c456")
    check("mode_preserved", meta["discord_mode"] == "product")
    check("target_preserved", meta["responder_target"] == "vps")


# ── test: extra keywords ───────────────────────────────────────────────────


def test_extra_keywords() -> None:
    _header("Extra keyword env vars")
    from runtime.substrate.workflow_delegation import classify_workflow_intent

    _reset_env()
    os.environ["EOS_WORKFLOW_EXTRA_BUILDER_KEYWORDS"] = "yolo,ship it"

    r = classify_workflow_intent("let's yolo this thing", "builder")
    check("extra_kw_matched", r["intent"] == "workflow", f"got {r['intent']}")
    check("extra_kw_low_confidence", r["confidence"] == "low")

    # Same text in product mode should NOT match builder keywords
    r2 = classify_workflow_intent("let's yolo this thing", "product")
    check(
        "extra_kw_mode_scoped",
        r2["intent"] == "conversation",
        f"got {r2['intent']}",
    )

    _reset_env()


# ── test: determinism ───────────────────────────────────────────────────────


def test_determinism() -> None:
    _header("Classification determinism")
    from runtime.substrate.workflow_delegation import classify_workflow_intent

    text = "deploy the latest build and check the logs"
    r1 = classify_workflow_intent(text, "builder")
    r2 = classify_workflow_intent(text, "builder")
    check("deterministic", r1 == r2, f"r1={r1} r2={r2}")


# ── test: policy dict shape ─────────────────────────────────────────────────


def test_policy_dict_shape() -> None:
    _header("Policy dict shape completeness")
    from runtime.substrate.workflow_delegation import (
        classify_workflow_intent,
        resolve_workflow_policy,
    )

    intent = classify_workflow_intent("fix the router", "builder")
    policy = resolve_workflow_policy("builder", intent)

    required_keys = {
        "allowed",
        "mode",
        "intent",
        "workflow_kind",
        "execution_class",
        "policy_reason",
        "delegation_version",
    }
    missing = required_keys - set(policy.keys())
    check("policy_has_all_keys", not missing, f"missing: {missing}")
    check("delegation_version_v1", policy["delegation_version"] == "v1")


# ── test: no hot-path imports ──────────────────────────────────────────────


def test_no_hotpath_imports() -> None:
    _header("No hot-path imports in workflow_delegation")
    import importlib
    import ast

    src = importlib.util.find_spec("runtime.substrate.workflow_delegation")
    assert src and src.origin
    with open(src.origin) as f:
        tree = ast.parse(f.read())

    hot_path = {
        "gateway",
        "cognitive_loop",
        "model_router",
        "agent_runtime",
        "primitives",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)

    violations = {m for m in imported if any(h in m for h in hot_path)}
    check("no_hotpath_imports", not violations, f"found: {violations}")


def test_no_second_router() -> None:
    _header("No second router or cognition pipeline")
    import importlib
    import ast

    src = importlib.util.find_spec("runtime.substrate.workflow_delegation")
    assert src and src.origin
    with open(src.origin) as f:
        content = f.read()

    # Must not import or reference router/cognition
    for forbidden in ("call_with_fallback", "CognitiveLoop", "AgentRuntime"):
        check(
            f"no_reference_to_{forbidden}",
            forbidden not in content,
            f"found reference to {forbidden}",
        )


# ── test: product + local delegation coexistence ───────────────────────────


def test_product_local_delegation_coexists_with_workflow() -> None:
    _header("Product local delegation + workflow metadata coexistence")
    from runtime.substrate.workflow_delegation import enrich_metadata

    meta: dict = {
        "transport": "discord",
        "discord_mode": "product",
        "responder_target": "local",
        "delegated_local": True,
        "delegation_reason": "keyword:debug",
    }
    enrich_metadata(meta, "run the onboarding workflow", "product")

    check("delegation_preserved", meta["delegated_local"] is True)
    check("delegation_reason_preserved", meta["delegation_reason"] == "keyword:debug")
    check("workflow_intent_present", meta["workflow_intent"] == "workflow")
    check("workflow_kind_present", meta["workflow_kind"] == "product_runtime")
    check("workflow_allowed", meta["workflow_allowed"] is True)


# ── test: transport integration shape ───────────────────────────────────────


def test_transport_integration_returns_workflow_fields() -> None:
    _header("Transport integration returns workflow fields")
    # This verifies the return dict shape from ingest_text_message
    # includes workflow metadata (without actually calling the full pipeline)
    import ast
    import importlib

    src = importlib.util.find_spec("runtime.substrate.discord_text_transport")
    assert src and src.origin
    with open(src.origin) as f:
        content = f.read()

    check(
        "transport_calls_enrich_metadata",
        "enrich_metadata" in content,
        "enrich_metadata not found in discord_text_transport",
    )
    check(
        "transport_returns_workflow_intent",
        "workflow_intent" in content,
        "workflow_intent not in return dict",
    )
    check(
        "transport_returns_workflow_kind",
        "workflow_kind" in content,
        "workflow_kind not in return dict",
    )
    check(
        "transport_returns_workflow_allowed",
        "workflow_allowed" in content,
        "workflow_allowed not in return dict",
    )
    check(
        "transport_returns_workflow_execution_class",
        "workflow_execution_class" in content,
        "workflow_execution_class not in return dict",
    )


# ── main ────────────────────────────────────────────────────────────────────


def main() -> int:
    _reset_env()

    print("=" * 66)
    print("  Workflow Delegation Layer v1 — smoke test")
    print("=" * 66)

    test_builder_dev_classification()
    test_product_runtime_classification()
    test_conversation_classification()
    test_skill_tool_classification()
    test_content_ops_classification()
    test_analysis_classification()
    test_system_ops_classification()
    test_planning_only_exclusion()
    test_empty_input()
    test_builder_allows_builder_dev()
    test_product_blocks_builder_dev()
    test_product_allows_product_runtime()
    test_unknown_mode_restricts()
    test_conversation_always_allowed()
    test_enrich_metadata()
    test_enrich_preserves_existing()
    test_extra_keywords()
    test_determinism()
    test_policy_dict_shape()
    test_no_hotpath_imports()
    test_no_second_router()
    test_product_local_delegation_coexists_with_workflow()
    test_transport_integration_returns_workflow_fields()

    _reset_env()

    print("\n" + "=" * 66)
    if FAILURES:
        print(f"  FAILED: {len(FAILURES)}")
        for f in FAILURES:
            print(f"    - {f}")
        print("=" * 66)
        return 1

    print("  ALL PASSED")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
