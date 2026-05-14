#!/usr/bin/env python3
"""Smoke test for Execution Trace Layer v1.

Validates:
  1-14: trace object, history, thread-local, scenarios
  15-18: architectural tripwires (one router, no daemon, clean imports, no leak)
"""

from __future__ import annotations

import importlib
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


def main() -> int:
    from runtime.transport.execution_trace import (
        _TraceHistory,
        clear_current_trace,
        finalize_trace,
        format_trace_compact,
        get_current_trace,
        get_trace_history,
        new_trace,
        set_current_trace,
        trace_context,
        update_trace,
    )

    # ── 1. new_trace returns dict with all expected keys ─────────────────
    _header("1. new_trace basics")
    t = new_trace("discord_text", "builder", "dev-session")
    expected_keys = {
        "trace_id",
        "source",
        "mode",
        "target_initial",
        "target_final",
        "session_name",
        "workflow_intent",
        "workflow_kind",
        "workflow_allowed",
        "workflow_executed",
        "workflow_handler",
        "workload_class",
        "resource_pressure",
        "resource_guard_allowed",
        "resource_guard_reason",
        "context_pressure_score",
        "context_checkpoint_used",
        "context_restore_used",
        "execution_path",
        "provider",
        "model",
        "latency_ms",
        "result",
        "timestamp",
    }
    has_keys = expected_keys.issubset(set(t.keys()))
    check(
        "1. new_trace has all expected keys + non-None trace_id",
        has_keys and t["trace_id"] is not None,
        f"missing={expected_keys - set(t.keys())}, trace_id={t.get('trace_id')}",
    )

    # ── 2. update_trace merges known, ignores unknown ────────────────────
    _header("2. update_trace")
    t2 = new_trace("discord_voice", "product", "prod-session")
    update_trace(t2, provider="gemini", bogus_key="should_be_ignored")
    check(
        "2. update_trace merges known keys, ignores unknown",
        t2["provider"] == "gemini" and "bogus_key" not in t2,
        f"provider={t2.get('provider')}, has_bogus={'bogus_key' in t2}",
    )

    # ── 3. finalize_trace sets expected fields ───────────────────────────
    _header("3. finalize_trace")
    t3 = new_trace("discord_text", "builder", "fin-session")
    finalize_trace(
        t3, provider="anthropic", model="opus", latency_ms=420, result="success"
    )
    check(
        "3. finalize_trace sets provider/model/result/latency + finalized_at",
        t3["provider"] == "anthropic"
        and t3["model"] == "opus"
        and t3["result"] == "success"
        and t3["latency_ms"] == 420
        and "finalized_at" in t3,
        f"provider={t3.get('provider')}, finalized_at={t3.get('finalized_at')}",
    )

    # ── 4. format_trace_compact ──────────────────────────────────────────
    _header("4. format_trace_compact")
    t4 = new_trace("discord_text", "builder", "fmt-session")
    finalize_trace(
        t4, provider="ollama", model="gemma3", latency_ms=100, result="success"
    )
    compact = format_trace_compact(t4)
    tid_prefix = t4["trace_id"][:8]
    check(
        "4. format_trace_compact returns non-empty string with trace_id[:8]",
        len(compact) > 0 and tid_prefix in compact,
        f"compact={compact!r}",
    )

    # ── 5. history record + latest ───────────────────────────────────────
    _header("5. history record + latest")
    hist = _TraceHistory(maxlen=200)
    for i in range(3):
        tr = new_trace("test", "builder", f"s{i}")
        finalize_trace(tr, provider="test", model="m", latency_ms=i, result="ok")
        hist.record(tr)
    latest = hist.latest(limit=10)
    check(
        "5. record() + latest() returns recorded traces",
        len(latest) == 3 and latest[-1]["latency_ms"] == 2,
        f"len={len(latest)}",
    )

    # ── 6. by_mode filters ───────────────────────────────────────────────
    _header("6. by_mode")
    hist2 = _TraceHistory(maxlen=200)
    for mode in ("builder", "product", "builder", "product", "builder"):
        tr = new_trace("test", mode, "filter-test")
        hist2.record(tr)
    builders = hist2.by_mode("builder")
    products = hist2.by_mode("product")
    check(
        "6. by_mode filters correctly",
        len(builders) == 3 and len(products) == 2,
        f"builders={len(builders)}, products={len(products)}",
    )

    # ── 7. by_session filters ────────────────────────────────────────────
    _header("7. by_session")
    hist3 = _TraceHistory(maxlen=200)
    for sess in ("alpha", "beta", "alpha"):
        tr = new_trace("test", "builder", sess)
        hist3.record(tr)
    alpha = hist3.by_session("alpha")
    beta = hist3.by_session("beta")
    check(
        "7. by_session filters correctly",
        len(alpha) == 2 and len(beta) == 1,
        f"alpha={len(alpha)}, beta={len(beta)}",
    )

    # ── 8. clear empties buffer ──────────────────────────────────────────
    _header("8. clear")
    hist4 = _TraceHistory(maxlen=200)
    hist4.record(new_trace("test", "builder", "x"))
    hist4.clear()
    check(
        "8. clear() empties buffer",
        len(hist4.latest()) == 0,
        f"len={len(hist4.latest())}",
    )

    # ── 9. ring bounded ─────────────────────────────────────────────────
    _header("9. ring bounded")
    hist5 = _TraceHistory(maxlen=200)
    for i in range(250):
        hist5.record(new_trace("test", "builder", f"ring-{i}"))
    all_items = hist5.latest(limit=300)
    check(
        "9. ring bounded (250 inserts → max 200 returned)",
        len(all_items) == 200,
        f"len={len(all_items)}",
    )

    # ── 10. trace_context sets/clears ────────────────────────────────────
    _header("10. trace_context")
    t10 = new_trace("test", "builder", "ctx-test")
    with trace_context(t10) as active:
        inside = get_current_trace()
    after = get_current_trace()
    check(
        "10. trace_context sets/clears correctly",
        inside is t10 and active is t10 and after is None,
        f"inside_match={inside is t10}, after_none={after is None}",
    )

    # ── 11. get_current_trace None when not set ──────────────────────────
    _header("11. get_current_trace default")
    clear_current_trace()
    check(
        "11. get_current_trace returns None when no trace set",
        get_current_trace() is None,
    )

    # ── 12. workflow-executed trace ──────────────────────────────────────
    _header("12. workflow-executed trace")
    t12 = new_trace("discord_text", "builder", "wf-session")
    update_trace(t12, workflow_executed=True, execution_path="workflow")
    check(
        "12. workflow_executed=True, execution_path='workflow'",
        t12["workflow_executed"] is True and t12["execution_path"] == "workflow",
    )

    # ── 13. conversation trace ───────────────────────────────────────────
    _header("13. conversation trace")
    t13 = new_trace("discord_text", "product", "conv-session")
    update_trace(t13, execution_path="conversation")
    check("13. execution_path='conversation'", t13["execution_path"] == "conversation")

    # ── 14. resource_guard reroute ───────────────────────────────────────
    _header("14. resource_guard reroute")
    t14 = new_trace("discord_text", "builder", "guard-session")
    update_trace(
        t14,
        target_initial="cloud",
        target_final="local",
        resource_guard_allowed=False,
        resource_guard_reason="high_pressure",
    )
    check(
        "14. target_initial != target_final after reroute",
        t14["target_initial"] == "cloud"
        and t14["target_final"] == "local"
        and t14["target_initial"] != t14["target_final"],
        f"initial={t14['target_initial']}, final={t14['target_final']}",
    )

    # ────────────────────────────────────────────────────────────────────
    # ARCHITECTURAL TRIPWIRES
    # ────────────────────────────────────────────────────────────────────

    # ── 15. No second router ─────────────────────────────────────────────
    _header("15. no second router")
    router_path = os.path.join(_ROOT, "runtime", "model_router.py")
    with open(router_path) as f:
        router_lines = f.readlines()
    # Count module-level call_with_fallback (not indented = not a method)
    cwf_module = sum(
        1 for ln in router_lines if ln.startswith("def call_with_fallback")
    )
    check(
        "15. one module-level call_with_fallback in model_router.py",
        cwf_module == 1,
        f"count={cwf_module}",
    )

    # ── 16. No daemon in execution_trace ─────────────────────────────────
    _header("16. no daemon")
    trace_path = os.path.join(_ROOT, "runtime", "substrate", "execution_trace.py")
    with open(trace_path) as f:
        trace_src = f.read()
    has_subprocess = "subprocess" in trace_src
    has_thread_start = "Thread(" in trace_src and ".start()" in trace_src
    check(
        "16. no subprocess/threading.Thread launch in execution_trace.py",
        not has_subprocess and not has_thread_start,
        f"subprocess={has_subprocess}, thread_start={has_thread_start}",
    )

    # ── 17. Hot-path import clean ────────────────────────────────────────
    _header("17. hot-path import")
    try:
        mod = importlib.import_module("runtime.transport.execution_trace")
        import_ok = mod is not None
    except Exception as exc:
        import_ok = False
        _header(f"import error: {exc}")
    check("17. importlib.import_module succeeds", import_ok)

    # ── 18. No user-visible trace leak ───────────────────────────────────
    _header("18. no sensitive data leak")
    t18 = new_trace("discord_text", "builder", "leak-check")
    # Simulate sensitive-ish fields that should NOT appear in compact output
    update_trace(t18, provider="anthropic", model="opus")
    finalize_trace(
        t18, provider="anthropic", model="opus", latency_ms=50, result="success"
    )
    compact18 = format_trace_compact(t18)
    # format_trace_compact should not contain env vars, API keys, or full UUIDs
    full_uuid = t18["trace_id"]
    # Compact uses [:8] truncation — full UUID should NOT appear
    check(
        "18. format_trace_compact doesn't contain full trace_id (truncates to 8)",
        full_uuid not in compact18 and t18["trace_id"][:8] in compact18,
        f"full_in_compact={full_uuid in compact18}",
    )

    # ── 19. by_provider filter ──────────────────────────────────────────
    _header("19. by_provider filter")
    hist19 = _TraceHistory(maxlen=200)
    for prov in ("gemini", "claude_cli", "gemini", "ollama", "gemini"):
        tr = new_trace("test", "builder", "prov-test")
        finalize_trace(tr, provider=prov, model="m", latency_ms=1, result="ok")
        hist19.record(tr)
    gemini_traces = hist19.by_provider("gemini")
    ollama_traces = hist19.by_provider("ollama")
    check(
        "19. by_provider filters correctly",
        len(gemini_traces) == 3 and len(ollama_traces) == 1,
        f"gemini={len(gemini_traces)}, ollama={len(ollama_traces)}",
    )

    # ── 20. by_execution_path filter ────────────────────────────────────
    _header("20. by_execution_path filter")
    hist20 = _TraceHistory(maxlen=200)
    for ep in ("conversation", "workflow", "conversation", "rerouted"):
        tr = new_trace("test", "builder", "path-test")
        update_trace(tr, execution_path=ep)
        hist20.record(tr)
    conv = hist20.by_execution_path("conversation")
    wf = hist20.by_execution_path("workflow")
    rr = hist20.by_execution_path("rerouted")
    check(
        "20. by_execution_path filters correctly",
        len(conv) == 2 and len(wf) == 1 and len(rr) == 1,
        f"conv={len(conv)}, wf={len(wf)}, rerouted={len(rr)}",
    )

    # ── 21. workflow-deferred vs workflow-executed ───────────────────────
    _header("21. workflow-deferred vs executed")
    t21a = new_trace("discord_text", "builder", "wf-deferred")
    update_trace(
        t21a,
        workflow_intent="workflow",
        workflow_kind="builder_dev",
        workflow_allowed=True,
        workflow_executed=False,
        execution_path="conversation",
    )
    t21b = new_trace("discord_text", "builder", "wf-executed")
    update_trace(
        t21b,
        workflow_intent="workflow",
        workflow_kind="builder_dev",
        workflow_allowed=True,
        workflow_executed=True,
        workflow_handler="_handle_builder_dev",
        execution_path="workflow",
    )
    check(
        "21. deferred vs executed distinguished",
        t21a["workflow_executed"] is False
        and t21a["execution_path"] == "conversation"
        and t21b["workflow_executed"] is True
        and t21b["execution_path"] == "workflow"
        and t21b["workflow_handler"] == "_handle_builder_dev",
    )

    # ── 22. product mode trace has correct mode ─────────────────────────
    _header("22. product mode trace")
    t22 = new_trace("discord_text", "product", "prod-session")
    check("22. product trace mode is 'product'", t22["mode"] == "product")

    # ── 23. conversation fallthrough sets workflow_executed=False ────────
    _header("23. conversation fallthrough")
    t23 = new_trace("discord_text", "builder", "conv-ft")
    update_trace(t23, execution_path="conversation", workflow_executed=False)
    check(
        "23. conversation fallthrough has workflow_executed=False",
        t23["workflow_executed"] is False and t23["execution_path"] == "conversation",
    )

    # ── 24. No second cognition pipeline ────────────────────────────────
    _header("24. no second cognition pipeline")
    transport_path = os.path.join(
        _ROOT, "runtime", "substrate", "discord_text_transport.py"
    )
    with open(transport_path) as f:
        transport_src = f.read()
    # Must not import cognitive_loop directly
    has_cognitive_import = "from control_plane.runtime.cognitive_loop" in transport_src
    # Must not import gateway directly
    has_gateway_import = "from control_plane.runtime.gateway" in transport_src
    check(
        "24. discord_text_transport does not import cognitive_loop or gateway",
        not has_cognitive_import and not has_gateway_import,
        f"cognitive_loop={has_cognitive_import}, gateway={has_gateway_import}",
    )

    # ── 25. No hidden planner in execution_trace ────────────────────────
    _header("25. no hidden planner")
    planner_terms = ["schedule", "cron", "celery", "asyncio.create_task"]
    found_planner = [t for t in planner_terms if t in trace_src]
    check(
        "25. no planner/scheduler terms in execution_trace.py",
        len(found_planner) == 0,
        f"found={found_planner}",
    )

    # ── 26. No user-visible trace leak in product mode (schema check) ──
    _header("26. product mode leak protection")
    # Verify that format_trace_compact output does not contain API keys or env values
    t26 = new_trace("discord_text", "product", "prod-leak-test")
    finalize_trace(
        t26, provider="gemini", model="flash", latency_ms=10, result="success"
    )
    compact26 = format_trace_compact(t26)
    # Should only contain bounded operator-safe fields
    check(
        "26. compact output has no env/key/secret content",
        "ANTHROPIC_API_KEY" not in compact26
        and "DISCORD_BOT_TOKEN" not in compact26
        and len(compact26) < 200,
        f"len={len(compact26)}",
    )

    # ── 27. target reroute captured correctly ───────────────────────────
    _header("27. target reroute")
    t27 = new_trace("discord_text", "builder", "reroute-test")
    update_trace(t27, target_initial="vps", target_final="local")
    check(
        "27. target reroute: initial=vps, final=local",
        t27["target_initial"] == "vps" and t27["target_final"] == "local",
    )

    # ── 28. Trace history singleton is consistent ───────────────────────
    _header("28. singleton consistency")
    h1 = get_trace_history()
    h2 = get_trace_history()
    check("28. get_trace_history returns same instance", h1 is h2)

    # ── Summary ──────────────────────────────────────────────────────────
    _header("Summary")
    total = 28
    passed = total - len(FAILURES)
    print(f"\n  {passed}/{total} passed")
    if FAILURES:
        print(f"  FAILED: {', '.join(FAILURES)}")
        return 1
    print("  All assertions passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
