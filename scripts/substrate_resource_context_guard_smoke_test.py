#!/usr/bin/env python3
"""
Resource Guard, Workload Classification & Context Lifecycle — smoke test.

Proves that:
  1.  "what backend are you using" → lightweight.
  2.  "fix this bug in the auth system" → heavyweight.
  3.  "draft a short post about AI trends" → standard.
  4.  builder_dev workflow_kind → heavyweight regardless of text.
  5.  "hello" → lightweight.
  6.  Short text (<30 chars, no heavyweight keywords) → lightweight.
  7.  Force override via metadata["force_workload"] = "heavyweight".
  8.  workload_weight_order comparisons.
  9.  current_resource_snapshot() returns valid dict with required keys.
 10.  Guard disabled (default) → always allowed, pressure "low".
 11.  Guard enabled + synthetic high pressure + heavyweight → not allowed,
      recommend local.
 12.  Guard enabled + high pressure + product mode → always allowed
      (never block product).
 13.  Guard enabled + moderate pressure + heavyweight +
      HEAVYWORK_FORCE_LOCAL → recommend local.
 14.  Guard enabled + low pressure → allowed on current target.
 15.  Low message count → low pressure, should_clear False.
 16.  High message count + degradation markers → high pressure,
      should_clear True.
 17.  Very high pressure with all signals → pressure_score near 1.0.
 18.  Checkpoint builds correctly with restore_prompt under 500 chars.
 19.  restore_from_checkpoint returns correct session data.
 20.  No hot-path imports in any of the 3 new modules.
 21.  No daemon/background thread created.
 22.  One router still used (no new router class).
 23.  No second cognition pipeline.
 24.  All modules have __all__ exports.
 25.  session_control.maybe_auto_clear still functional.
 26.  EOS_RESOURCE_GUARD_ENABLED toggle works.
 27.  EOS_CONTEXT_GUARD_ENABLED toggle works.

Runs in-process. No tmux/Claude CLI needed.
Returns 0 on success, non-zero on failure.
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


# ── env vars we touch ──────────────────────────────────────────────────────

_GUARD_ENVS = (
    "EOS_RESOURCE_GUARD_ENABLED",
    "EOS_MAX_MEM_PCT",
    "EOS_MAX_SWAP_PCT",
    "EOS_MAX_LOAD_PER_CPU",
    "EOS_HEAVYWORK_FORCE_LOCAL",
    "EOS_CONTEXT_PRESSURE_THRESHOLD",
    "EOS_CONTEXT_GUARD_ENABLED",
    "EOS_SESSION_AUTO_CLEAR_MESSAGES",
)


def _reset_env() -> None:
    for k in _GUARD_ENVS:
        os.environ.pop(k, None)


# ══════════════════════════════════════════════════════════════════════════════
# Section 1 — Workload Classification (workload_policy.py)
# ══════════════════════════════════════════════════════════════════════════════


def test_workload_lightweight_question() -> None:
    _header("1. 'what backend are you using' → lightweight")
    from eos_ai.substrate.workload_policy import classify_workload

    r = classify_workload("what backend are you using", mode="builder")
    check(
        "question → lightweight",
        r["workload_class"] == "lightweight",
        f"got {r['workload_class']!r}",
    )


def test_workload_heavyweight_fix() -> None:
    _header("2. 'fix this bug in the auth system' → heavyweight")
    from eos_ai.substrate.workload_policy import classify_workload

    r = classify_workload("fix this bug in the auth system", mode="builder")
    check(
        "fix keyword → heavyweight",
        r["workload_class"] == "heavyweight",
        f"got {r['workload_class']!r}",
    )


def test_workload_standard_draft() -> None:
    _header("3. 'draft a short post about AI trends' → standard")
    from eos_ai.substrate.workload_policy import classify_workload

    r = classify_workload("draft a short post about AI trends", mode="builder")
    check(
        "no heavy/light keyword → standard",
        r["workload_class"] == "standard",
        f"got {r['workload_class']!r}",
    )


def test_workload_workflow_kind_override() -> None:
    _header("4. builder_dev workflow_kind → heavyweight regardless of text")
    from eos_ai.substrate.workload_policy import classify_workload

    r = classify_workload(
        "hello", mode="builder", workflow_kind="builder_dev"
    )
    check(
        "builder_dev → heavyweight",
        r["workload_class"] == "heavyweight",
        f"got {r['workload_class']!r}",
    )
    check(
        "matched_rule is workflow_kind_heavyweight",
        r["matched_rule"] == "workflow_kind_heavyweight",
        f"got {r['matched_rule']!r}",
    )


def test_workload_hello_lightweight() -> None:
    _header("5. 'hello' → lightweight")
    from eos_ai.substrate.workload_policy import classify_workload

    r = classify_workload("hello", mode="product")
    check(
        "hello → lightweight",
        r["workload_class"] == "lightweight",
        f"got {r['workload_class']!r}",
    )


def test_workload_short_text_lightweight() -> None:
    _header("6. Short text (<30 chars, no keywords) → lightweight")
    from eos_ai.substrate.workload_policy import classify_workload

    r = classify_workload("sup", mode="builder")
    check(
        "short text → lightweight",
        r["workload_class"] == "lightweight",
        f"got {r['workload_class']!r}",
    )
    check(
        "matched_rule mentions short or keyword",
        "short_text" in r["matched_rule"] or "keyword_lightweight" in r["matched_rule"],
        f"got {r['matched_rule']!r}",
    )


def test_workload_force_override() -> None:
    _header("7. metadata force_workload → heavyweight override")
    from eos_ai.substrate.workload_policy import classify_workload

    r = classify_workload(
        "hello", mode="builder", metadata={"force_workload": "heavyweight"}
    )
    check(
        "force → heavyweight",
        r["workload_class"] == "heavyweight",
        f"got {r['workload_class']!r}",
    )
    check(
        "matched_rule is metadata_force_workload",
        r["matched_rule"] == "metadata_force_workload",
        f"got {r['matched_rule']!r}",
    )


def test_workload_weight_order() -> None:
    _header("8. workload_weight_order comparisons")
    from eos_ai.substrate.workload_policy import workload_weight_order

    check(
        "lightweight < standard",
        workload_weight_order("lightweight") < workload_weight_order("standard"),
    )
    check(
        "standard < heavyweight",
        workload_weight_order("standard") < workload_weight_order("heavyweight"),
    )
    check(
        "lightweight == 0",
        workload_weight_order("lightweight") == 0,
    )
    check(
        "heavyweight == 2",
        workload_weight_order("heavyweight") == 2,
    )

    # Invalid value should raise
    raised = False
    try:
        workload_weight_order("bogus")
    except ValueError:
        raised = True
    check("bogus value raises ValueError", raised)


# ══════════════════════════════════════════════════════════════════════════════
# Section 2 — Resource Guard (resource_guard.py)
# ══════════════════════════════════════════════════════════════════════════════


def test_resource_snapshot_keys() -> None:
    _header("9. current_resource_snapshot returns valid dict")
    from eos_ai.substrate.resource_guard import current_resource_snapshot

    snap = current_resource_snapshot()
    check("snapshot is dict", isinstance(snap, dict))
    check("snapshot_at present", "snapshot_at" in snap)
    check("cpu_count present", "cpu_count" in snap)
    # On Linux /proc/meminfo should be readable
    check("mem_used_pct present", "mem_used_pct" in snap)


def test_guard_disabled_default() -> None:
    _header("10. Guard disabled (default) → always allowed, pressure low")
    from eos_ai.substrate.resource_guard import evaluate_resource_guard

    _reset_env()
    # Default is disabled
    r = evaluate_resource_guard(
        mode="builder",
        target="vps",
        workload_class="heavyweight",
        snapshot={"mem_used_pct": 99.0, "swap_used_pct": 50.0, "load_per_cpu": 5.0},
    )
    check("allowed when disabled", r["allowed"] is True)
    check("pressure low when disabled", r["pressure_level"] == "low")
    check("reason is guard_disabled", r["guard_reason"] == "guard_disabled")


def test_guard_enabled_high_pressure_heavyweight() -> None:
    _header("11. Guard enabled + high pressure + heavyweight → not allowed")
    from eos_ai.substrate.resource_guard import evaluate_resource_guard

    _reset_env()
    os.environ["EOS_RESOURCE_GUARD_ENABLED"] = "1"

    r = evaluate_resource_guard(
        mode="builder",
        target="vps",
        workload_class="heavyweight",
        snapshot={"mem_used_pct": 90.0, "swap_used_pct": 30.0, "load_per_cpu": 2.0},
    )
    check("not allowed", r["allowed"] is False)
    check("recommend local", r["recommended_target"] == "local")
    check("pressure high", r["pressure_level"] == "high")
    _reset_env()


def test_guard_product_mode_override() -> None:
    _header("12. Guard enabled + high pressure + product → always allowed")
    from eos_ai.substrate.resource_guard import evaluate_resource_guard

    _reset_env()
    os.environ["EOS_RESOURCE_GUARD_ENABLED"] = "1"

    r = evaluate_resource_guard(
        mode="product",
        target="vps",
        workload_class="heavyweight",
        snapshot={"mem_used_pct": 90.0, "swap_used_pct": 30.0, "load_per_cpu": 2.0},
    )
    check("product always allowed", r["allowed"] is True)
    check(
        "reason contains product_mode_override",
        "product_mode_override" in r["guard_reason"],
        f"got {r['guard_reason']!r}",
    )
    _reset_env()


def test_guard_moderate_force_local() -> None:
    _header("13. Moderate pressure + heavyweight + HEAVYWORK_FORCE_LOCAL → local")
    from eos_ai.substrate.resource_guard import evaluate_resource_guard

    _reset_env()
    os.environ["EOS_RESOURCE_GUARD_ENABLED"] = "1"
    os.environ["EOS_HEAVYWORK_FORCE_LOCAL"] = "1"

    # Moderate: above 80% of threshold but below threshold
    # Defaults: max_mem=75, max_swap=20, max_load=1.5
    # 80% of 75 = 60, so mem=65 is moderate
    r = evaluate_resource_guard(
        mode="builder",
        target="vps",
        workload_class="heavyweight",
        snapshot={"mem_used_pct": 65.0, "swap_used_pct": 10.0, "load_per_cpu": 0.5},
    )
    check("allowed (moderate, not blocked)", r["allowed"] is True)
    check(
        "recommend local",
        r["recommended_target"] == "local",
        f"got {r['recommended_target']!r}",
    )
    check("pressure moderate", r["pressure_level"] == "moderate")
    _reset_env()


def test_guard_low_pressure_allowed() -> None:
    _header("14. Guard enabled + low pressure → allowed on current target")
    from eos_ai.substrate.resource_guard import evaluate_resource_guard

    _reset_env()
    os.environ["EOS_RESOURCE_GUARD_ENABLED"] = "1"

    r = evaluate_resource_guard(
        mode="builder",
        target="vps",
        workload_class="heavyweight",
        snapshot={"mem_used_pct": 30.0, "swap_used_pct": 5.0, "load_per_cpu": 0.3},
    )
    check("allowed on low pressure", r["allowed"] is True)
    check(
        "recommended target unchanged",
        r["recommended_target"] == "vps",
        f"got {r['recommended_target']!r}",
    )
    check("pressure low", r["pressure_level"] == "low")
    _reset_env()


# ══════════════════════════════════════════════════════════════════════════════
# Section 3 — Context Pressure (context_lifecycle.py)
# ══════════════════════════════════════════════════════════════════════════════


def test_low_message_count_low_pressure() -> None:
    _header("15. Low message count → low pressure, should_clear False")
    from eos_ai.substrate.context_lifecycle import detect_context_pressure

    _reset_env()
    r = detect_context_pressure(
        "dex_builder_main",
        message_count=3,
    )
    check("pressure low", r["pressure_level"] == "low")
    check("should_clear False", r["should_clear"] is False)
    check("pressure_score < 0.4", r["pressure_score"] < 0.4)


def test_high_count_degradation_high_pressure() -> None:
    _header("16. High message count + degradation → high pressure, should_clear True")
    from eos_ai.substrate.context_lifecycle import detect_context_pressure

    _reset_env()
    r = detect_context_pressure(
        "dex_builder_main",
        message_count=50,
        reply_text="I don't have context for what you're referring to.",
        metadata={"total_chars_sent": 80_000, "session_age_minutes": 90},
    )
    check("pressure high", r["pressure_level"] == "high")
    check("should_clear True", r["should_clear"] is True)
    check("pressure_score >= 0.75", r["pressure_score"] >= 0.75)


def test_all_signals_max_pressure() -> None:
    _header("17. All signals maxed → pressure_score near 1.0")
    from eos_ai.substrate.context_lifecycle import detect_context_pressure

    _reset_env()
    r = detect_context_pressure(
        "dex_builder_main",
        message_count=100,
        reply_text="I don't have context for that. Could you clarify?",
        metadata={
            "total_chars_sent": 200_000,
            "session_age_minutes": 300,
        },
    )
    check(
        "pressure_score >= 0.9",
        r["pressure_score"] >= 0.9,
        f"got {r['pressure_score']}",
    )
    check("should_clear True", r["should_clear"] is True)
    # Check all signal keys present
    sigs = r["signals"]
    check("message_count signal", "message_count" in sigs)
    check("total_chars signal", "total_chars" in sigs)
    check("degradation signal", "degradation" in sigs)
    check("session_age signal", "session_age" in sigs)


def test_checkpoint_builds_correctly() -> None:
    _header("18. Checkpoint builds with restore_prompt under 500 chars")
    from eos_ai.substrate.context_lifecycle import build_context_checkpoint

    cp = build_context_checkpoint(
        "dex_builder_main",
        mode="builder",
        target="local",
        active_objective="refactor gateway module",
        workflow_kind="builder_dev",
        task_summary="splitting gateway into sub-modules",
    )
    check("session_name correct", cp["session_name"] == "dex_builder_main")
    check("mode correct", cp["mode"] == "builder")
    check("target correct", cp["target"] == "local")
    check("restore_prompt present", "restore_prompt" in cp)
    check(
        "restore_prompt under 500 chars",
        len(cp["restore_prompt"]) <= 500,
        f"got {len(cp['restore_prompt'])} chars",
    )
    check("checkpoint_at present", "checkpoint_at" in cp)
    check("checkpoint_version present", cp["checkpoint_version"] == "1.0")


def test_restore_from_checkpoint() -> None:
    _header("19. restore_from_checkpoint returns correct session data")
    from eos_ai.substrate.context_lifecycle import (
        build_context_checkpoint,
        restore_from_checkpoint,
    )

    cp = build_context_checkpoint(
        "dex_product_main",
        mode="product",
        target="vps",
        active_objective="onboarding flow",
    )
    restored = restore_from_checkpoint(cp)
    check("restore_prompt preserved", restored["restore_prompt"] == cp["restore_prompt"])
    check("session_name preserved", restored["session_name"] == "dex_product_main")
    check("mode preserved", restored["mode"] == "product")
    check("target preserved", restored["target"] == "vps")
    check("restored_at present", "restored_at" in restored)
    check("lifecycle_version present", restored["lifecycle_version"] == "1.0")


# ══════════════════════════════════════════════════════════════════════════════
# Section 4 — Integration Assertions (tripwires)
# ══════════════════════════════════════════════════════════════════════════════


def test_no_hot_path_imports() -> None:
    _header("20. No hot-path imports in 3 new modules")
    import ast

    hot_path_modules = {
        "gateway",
        "cognitive_loop",
        "model_router",
        "agent_runtime",
        "primitives",
    }

    for modpath in (
        "/opt/OS/eos_ai/substrate/workload_policy.py",
        "/opt/OS/eos_ai/substrate/resource_guard.py",
        "/opt/OS/eos_ai/substrate/context_lifecycle.py",
    ):
        basename = os.path.basename(modpath)
        with open(modpath) as f:
            tree = ast.parse(f.read())

        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

        violation = {
            m
            for m in imported
            for hp in hot_path_modules
            if hp in m
        }
        check(
            f"no hot-path imports in {basename}",
            not violation,
            f"found: {violation}",
        )


def test_no_daemon_or_background_thread() -> None:
    _header("21. No daemon/background thread created")
    import ast

    for modpath in (
        "/opt/OS/eos_ai/substrate/workload_policy.py",
        "/opt/OS/eos_ai/substrate/resource_guard.py",
        "/opt/OS/eos_ai/substrate/context_lifecycle.py",
    ):
        basename = os.path.basename(modpath)
        with open(modpath) as f:
            source = f.read()

        tree = ast.parse(source)
        # Check for Thread() or .start() calls, daemon references
        # Simple text check on non-comment/non-docstring lines
        lines = source.splitlines()
        docstring_lines: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str):
                    for ln in range(node.value.lineno, node.value.end_lineno + 1):
                        docstring_lines.add(ln)

        code_lines = []
        for i, line in enumerate(lines, 1):
            if i in docstring_lines:
                continue
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            code_lines.append(stripped.split("#")[0])
        code_only = "\n".join(code_lines).lower()

        for pattern in ("threading.thread(", ".daemon", "thread(target="):
            check(
                f"no '{pattern}' in {basename}",
                pattern not in code_only,
                f"found '{pattern}' in executable code",
            )


def test_one_router_no_new_class() -> None:
    _header("22. One router still used (no new router class)")
    import ast

    for modpath in (
        "/opt/OS/eos_ai/substrate/workload_policy.py",
        "/opt/OS/eos_ai/substrate/resource_guard.py",
        "/opt/OS/eos_ai/substrate/context_lifecycle.py",
    ):
        basename = os.path.basename(modpath)
        with open(modpath) as f:
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
            f"no call_with_fallback import in {basename}",
            "call_with_fallback" not in imported_names,
            f"found import: {imported_names & {'call_with_fallback'}}",
        )


def test_no_second_cognition_pipeline() -> None:
    _header("23. No second cognition pipeline")
    import ast

    for modpath in (
        "/opt/OS/eos_ai/substrate/workload_policy.py",
        "/opt/OS/eos_ai/substrate/resource_guard.py",
        "/opt/OS/eos_ai/substrate/context_lifecycle.py",
    ):
        basename = os.path.basename(modpath)
        with open(modpath) as f:
            source = f.read()

        tree = ast.parse(source)
        docstring_lines: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str):
                    for ln in range(node.value.lineno, node.value.end_lineno + 1):
                        docstring_lines.add(ln)

        lines = source.splitlines()
        code_lines = []
        for i, line in enumerate(lines, 1):
            if i in docstring_lines:
                continue
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            code_lines.append(stripped.split("#")[0])
        code_only = "\n".join(code_lines).lower()

        for forbidden in ("autonomous", "planner", "multi_agent", "swarm"):
            check(
                f"no '{forbidden}' in {basename}",
                forbidden not in code_only,
                f"found '{forbidden}' in executable code",
            )


def test_all_modules_have_all_exports() -> None:
    _header("24. All modules have __all__ exports")
    import eos_ai.substrate.workload_policy as wp
    import eos_ai.substrate.resource_guard as rg
    import eos_ai.substrate.context_lifecycle as cl

    check("workload_policy has __all__", hasattr(wp, "__all__") and len(wp.__all__) > 0)
    check("resource_guard has __all__", hasattr(rg, "__all__") and len(rg.__all__) > 0)
    check("context_lifecycle has __all__", hasattr(cl, "__all__") and len(cl.__all__) > 0)


def test_session_control_maybe_auto_clear_functional() -> None:
    _header("25. session_control.maybe_auto_clear still functional")
    from eos_ai.substrate.session_control import (
        get_message_count,
        maybe_auto_clear,
        reset_counters_for_tests,
    )

    reset_counters_for_tests()

    # With a very high threshold, auto-clear should not trigger
    os.environ["EOS_SESSION_AUTO_CLEAR_MESSAGES"] = "999"
    r = maybe_auto_clear("test_session_smoke", target="vps")
    check("auto_cleared False (below threshold)", r["auto_cleared"] is False)
    check(
        "counter incremented to 1",
        get_message_count("test_session_smoke") == 1,
    )

    # Disabled
    os.environ["EOS_SESSION_AUTO_CLEAR_MESSAGES"] = "0"
    r2 = maybe_auto_clear("test_session_smoke", target="vps")
    check("auto_cleared False (disabled)", r2["auto_cleared"] is False)
    check("reason is disabled", r2["reason"] == "disabled")

    reset_counters_for_tests()
    _reset_env()


# ══════════════════════════════════════════════════════════════════════════════
# Section 5 — Env var behavior
# ══════════════════════════════════════════════════════════════════════════════


def test_resource_guard_enabled_toggle() -> None:
    _header("26. EOS_RESOURCE_GUARD_ENABLED toggle")
    from eos_ai.substrate.resource_guard import evaluate_resource_guard

    synthetic = {"mem_used_pct": 90.0, "swap_used_pct": 30.0, "load_per_cpu": 2.0}

    # Disabled (default)
    _reset_env()
    r1 = evaluate_resource_guard(
        mode="builder", target="vps", workload_class="heavyweight", snapshot=synthetic
    )
    check("disabled → allowed", r1["allowed"] is True)
    check("disabled → guard_disabled reason", r1["guard_reason"] == "guard_disabled")

    # Enabled
    os.environ["EOS_RESOURCE_GUARD_ENABLED"] = "1"
    r2 = evaluate_resource_guard(
        mode="builder", target="vps", workload_class="heavyweight", snapshot=synthetic
    )
    check("enabled → not allowed (high pressure)", r2["allowed"] is False)

    # Disabled again
    os.environ["EOS_RESOURCE_GUARD_ENABLED"] = "0"
    r3 = evaluate_resource_guard(
        mode="builder", target="vps", workload_class="heavyweight", snapshot=synthetic
    )
    check("disabled again → allowed", r3["allowed"] is True)
    _reset_env()


def test_context_guard_enabled_toggle() -> None:
    _header("27. EOS_CONTEXT_GUARD_ENABLED toggle")
    from eos_ai.substrate.context_lifecycle import detect_context_pressure

    # Default is enabled — use enough signals to exceed 0.75 threshold
    _reset_env()
    _high_meta = {"total_chars_sent": 80_000, "session_age_minutes": 90}
    r1 = detect_context_pressure(
        "dex_test",
        message_count=50,
        reply_text="I don't have context for that.",
        metadata=_high_meta,
    )
    check("default enabled → should_clear True", r1["should_clear"] is True)
    check("guard_enabled True", r1["guard_enabled"] is True)

    # Disable
    os.environ["EOS_CONTEXT_GUARD_ENABLED"] = "0"
    r2 = detect_context_pressure(
        "dex_test",
        message_count=50,
        reply_text="I don't have context for that.",
        metadata=_high_meta,
    )
    check("disabled → should_clear False", r2["should_clear"] is False)
    check("guard_enabled False", r2["guard_enabled"] is False)
    # Score should still be computed even when guard disabled
    check("score still computed", r2["pressure_score"] > 0)

    # Re-enable
    os.environ["EOS_CONTEXT_GUARD_ENABLED"] = "1"
    r3 = detect_context_pressure(
        "dex_test",
        message_count=50,
        reply_text="I don't have context for that.",
        metadata=_high_meta,
    )
    check("re-enabled → should_clear True", r3["should_clear"] is True)
    _reset_env()


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════


def main() -> int:
    print("=" * 70)
    print("  Resource Guard, Workload Classification & Context Lifecycle")
    print("  Smoke Test")
    print("=" * 70)

    # Section 1 — Workload Classification
    test_workload_lightweight_question()
    test_workload_heavyweight_fix()
    test_workload_standard_draft()
    test_workload_workflow_kind_override()
    test_workload_hello_lightweight()
    test_workload_short_text_lightweight()
    test_workload_force_override()
    test_workload_weight_order()

    # Section 2 — Resource Guard
    test_resource_snapshot_keys()
    test_guard_disabled_default()
    test_guard_enabled_high_pressure_heavyweight()
    test_guard_product_mode_override()
    test_guard_moderate_force_local()
    test_guard_low_pressure_allowed()

    # Section 3 — Context Pressure
    test_low_message_count_low_pressure()
    test_high_count_degradation_high_pressure()
    test_all_signals_max_pressure()
    test_checkpoint_builds_correctly()
    test_restore_from_checkpoint()

    # Section 4 — Integration Assertions
    test_no_hot_path_imports()
    test_no_daemon_or_background_thread()
    test_one_router_no_new_class()
    test_no_second_cognition_pipeline()
    test_all_modules_have_all_exports()
    test_session_control_maybe_auto_clear_functional()

    # Section 5 — Env var behavior
    test_resource_guard_enabled_toggle()
    test_context_guard_enabled_toggle()

    print(f"\n{'=' * 70}")
    if FAILURES:
        print(f"  FAILED: {len(FAILURES)}")
        for f in FAILURES:
            print(f"    - {f}")
        print("=" * 70)
        return 1

    total = sum(
        1
        for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    )
    print(f"  ALL PASS ({total} test functions)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
