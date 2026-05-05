#!/usr/bin/env python3
"""
substrate_session_soul_doc_smoke_test.py

Verifies that claude_session_bridge launches claude with the correct
--append-system-prompt for persona-bound sessions (dex_product_main) and
without any override for developer sessions (dex_builder_main).

Runs entirely in-process. No tmux calls, no claude CLI invocation, no
network. Exercises the pure helpers:
  - _resolve_soul_doc()
  - _build_claude_launch_cmd()

Exit code: 0 on pass, 1 on any failure.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.substrate import claude_session_bridge as csb  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    _results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f"  — {detail}" if detail and not ok else ""))


def main() -> int:
    print("=== substrate session soul-doc smoke test ===\n")

    # ─── Sanity: the real EA soul doc must exist ────────────────────────
    ea_path = "/opt/OS/agents/executive_assistant.md"
    check(
        "ea_soul_doc_exists",
        os.path.isfile(ea_path),
        detail=f"missing: {ea_path}",
    )

    # ─── 1. Builder session → bare claude, no soul doc ───────────────────

    cmd, soul = csb._build_claude_launch_cmd("dex_builder_main")
    check("builder_cmd_is_bare", cmd == "claude", detail=cmd)
    check("builder_no_soul_doc", soul is None, detail=str(soul))

    # ─── 2. Product session → EA soul doc injected ───────────────────────

    cmd, soul = csb._build_claude_launch_cmd("dex_product_main")
    check("product_uses_ea_soul_doc", soul == ea_path, detail=str(soul))
    check(
        "product_cmd_has_append_flag",
        "--append-system-prompt" in cmd,
        detail=cmd,
    )
    check(
        "product_cmd_uses_cat_substitution",
        "$(cat '" in cmd and ea_path in cmd,
        detail=cmd,
    )
    check(
        "product_cmd_starts_with_claude",
        cmd.startswith("claude --append-system-prompt "),
        detail=cmd,
    )

    # ─── 3. Per-channel variant (EOS_DISCORD_MODE_PER_CHANNEL) ───────────
    # Session name becomes "dex_product_main_1234567890" — the resolver
    # must prefix-match back to dex_product_main.

    cmd, soul = csb._build_claude_launch_cmd("dex_product_main_1234567890")
    check(
        "per_channel_product_resolves_to_ea",
        soul == ea_path,
        detail=str(soul),
    )
    check(
        "per_channel_cmd_has_append_flag",
        "--append-system-prompt" in cmd,
        detail=cmd,
    )

    # Builder per-channel variant must still be bare
    cmd, soul = csb._build_claude_launch_cmd("dex_builder_main_9876543210")
    check(
        "per_channel_builder_stays_bare",
        cmd == "claude" and soul is None,
        detail=cmd,
    )

    # ─── 4. Unknown session → bare claude ────────────────────────────────

    cmd, soul = csb._build_claude_launch_cmd("some_random_session")
    check("unknown_session_bare", cmd == "claude" and soul is None, detail=cmd)

    # ─── 5. Env override works ───────────────────────────────────────────
    # Create a temp soul doc and point the override at it.

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, prefix="soul_override_"
    ) as tf:
        tf.write("# Override Persona\nYou are a test persona.\n")
        override_path = tf.name

    try:
        os.environ[f"{csb._SOUL_DOC_ENV_PREFIX}dex_product_main"] = override_path
        cmd, soul = csb._build_claude_launch_cmd("dex_product_main")
        check(
            "env_override_wins_over_default",
            soul == override_path,
            detail=f"soul={soul} override={override_path}",
        )
        check(
            "env_override_cmd_uses_override_path",
            override_path in cmd,
            detail=cmd,
        )
    finally:
        os.environ.pop(f"{csb._SOUL_DOC_ENV_PREFIX}dex_product_main", None)
        Path(override_path).unlink(missing_ok=True)

    # ─── 6. Env override with bad path → falls through to None ───────────
    # This verifies that a broken override does NOT silently fall back to
    # the default mapping — that would mask bugs in operator configs.

    os.environ[
        f"{csb._SOUL_DOC_ENV_PREFIX}dex_product_main"
    ] = "/nonexistent/path/to/nothing.md"
    try:
        cmd, soul = csb._build_claude_launch_cmd("dex_product_main")
        check(
            "broken_env_override_returns_none",
            soul is None and cmd == "claude",
            detail=f"cmd={cmd!r} soul={soul!r}",
        )
    finally:
        os.environ.pop(f"{csb._SOUL_DOC_ENV_PREFIX}dex_product_main", None)

    # ─── 7. Shell safety: quoted path with single quote in it ────────────
    # Synthesize a fake mapping to confirm the escaping path is reachable.

    orig_map = csb._SESSION_SOUL_DOCS.copy()
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, prefix="quoted'path_"
        ) as tf:
            tf.write("# persona\n")
            quoted_path = tf.name

        csb._SESSION_SOUL_DOCS["dex_quoted_test"] = quoted_path
        cmd, soul = csb._build_claude_launch_cmd("dex_quoted_test")
        check(
            "quoted_path_escaped_in_cmd",
            soul == quoted_path and "'\\''" in cmd,
            detail=cmd,
        )
        Path(quoted_path).unlink(missing_ok=True)
    finally:
        csb._SESSION_SOUL_DOCS.clear()
        csb._SESSION_SOUL_DOCS.update(orig_map)

    # ─── 8. Ensure the public mapping is unchanged after all tests ───────

    check(
        "default_mapping_unchanged",
        csb._SESSION_SOUL_DOCS.get("dex_product_main") == ea_path,
        detail=str(csb._SESSION_SOUL_DOCS),
    )
    check(
        "builder_not_in_mapping",
        "dex_builder_main" not in csb._SESSION_SOUL_DOCS,
        detail="builder must stay bare",
    )

    # ─── Summary ─────────────────────────────────────────────────────────

    total = len(_results)
    failed = [r for r in _results if not r[1]]
    print(f"\n{total - len(failed)}/{total} checks passed")
    if failed:
        print("\nFAILURES:")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
