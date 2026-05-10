#!/usr/bin/env python3
"""
Substrate Claude Code Session Bridge v1 — smoke test.

Validates the bridge end-to-end without depending on the claude CLI itself.
Sessions are created with launch_claude=False so the test runs against a
plain shell pane; message injection and capture are exercised using shell
echoes, which is enough to prove the bridge contract.

Degrades safely if tmux is not installed on the host: all shape checks still
run, degraded-path responses are verified, and exit code stays 0 when the
tmux-dependent checks are correctly skipped.
"""

from __future__ import annotations

import json
import sys
import time
import uuid

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate import claude_session_bridge as csb  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    tail = f" — {detail}" if detail and not cond else ""
    print(f"  [{status}] {name}{tail}")
    if not cond:
        FAILURES.append(name)


def _hotpath_clean() -> bool:
    """Verify the bridge module does NOT import any hot-path module."""
    import eos_ai.substrate.claude_session_bridge as m

    forbidden = {
        "eos_ai.gateway",
        "eos_ai.cognitive_loop",
        "eos_ai.model_router",
        "eos_ai.agent_runtime",
        "eos_ai.primitives",
    }
    mod_globals = set(getattr(m, "__dict__", {}).keys())
    # Look at actually imported module names in sys.modules that the module referenced.
    source_text = open(m.__file__).read()
    return not any(f in source_text for f in forbidden)


def main() -> int:
    print("Claude Code Session Bridge v1 smoke test")

    # 1. Environment detection shape
    tmux_env = csb.detect_tmux_available()
    check("detect_tmux_shape", isinstance(tmux_env, dict) and "available" in tmux_env)
    cli_env = csb.detect_claude_cli_available()
    check("detect_claude_cli_shape", isinstance(cli_env, dict) and "available" in cli_env)

    # 2. Default target + node helpers
    target = csb.default_session_target()
    check("default_target_valid", target in csb.VALID_TARGETS, target)

    # 3. Naming helpers
    n1 = csb.make_session_name("main")
    n2 = csb.make_session_name("discord", "123", "456")
    n3 = csb.make_session_name("weird name: with.bad/chars")
    check("name_main", n1 == "dex_main", n1)
    check("name_discord_compound", n2 == "dex_discord_123_456", n2)
    check("name_sanitized_has_no_forbidden", ":" not in n3 and "." not in n3 and " " not in n3, n3)

    # 4. Validation: bad inputs return structured errors, never raise
    bad_target = csb.ensure_session("mars", "dex_test", launch_claude=False)
    check("bad_target_rejected", bad_target.get("ok") is False and "invalid_target" in bad_target.get("reason", ""))

    bad_name = csb.ensure_session("local", "bad:name.session", launch_claude=False)
    check("bad_session_name_rejected", bad_name.get("ok") is False)

    bad_send_text = csb.send_message("local", "dex_test", "")
    check("empty_text_rejected", bad_send_text.get("ok") is False and bad_send_text.get("reason") == "text_empty")

    bad_send_type = csb.send_message("local", "dex_test", 12345)  # type: ignore[arg-type]
    check("non_string_text_rejected", bad_send_type.get("ok") is False)

    huge = csb.send_message("local", "dex_test", "x" * 20000)
    check("oversized_text_rejected", huge.get("ok") is False and huge.get("reason") == "text_too_long")

    # 5. list_sessions always returns ok=True (degrades safely)
    listing = csb.list_sessions(target="local")
    check("list_sessions_shape", listing.get("ok") is True and isinstance(listing.get("sessions"), list))

    # 6. If tmux is unavailable, assert degraded path and exit.
    if not tmux_env.get("available"):
        print("  [INFO] tmux not available — verifying degraded paths only")
        deg_ensure = csb.ensure_session("local", "dex_smoke_degraded", launch_claude=False)
        check("degraded_ensure_ok", deg_ensure.get("ok") is True and deg_ensure.get("status") == "degraded")
        deg_status = csb.session_status("local", "dex_smoke_degraded")
        check("degraded_status_ok", deg_status.get("ok") is True and deg_status.get("status") == "degraded")
        deg_send = csb.send_message("local", "dex_smoke_degraded", "hello")
        check("degraded_send_rejected", deg_send.get("ok") is False and deg_send.get("degraded") is True)
        print("\n" + ("FAIL" if FAILURES else "ALL CHECKS PASSED (degraded)"))
        return 1 if FAILURES else 0

    # 7. Real tmux path — use an isolated dex_smoke_* session name.
    session = f"dex_smoke_{uuid.uuid4().hex[:8]}"

    try:
        # Ensure (no claude CLI launch — we test the bridge mechanics only)
        ens = csb.ensure_session("local", session, launch_claude=False)
        check(
            "ensure_new_session_ok",
            ens.get("ok") is True
            and ens.get("status") == "running"
            and ens.get("created") is True,
            json.dumps(ens),
        )

        # Idempotency
        ens2 = csb.ensure_session("local", session, launch_claude=False)
        check(
            "ensure_idempotent",
            ens2.get("ok") is True and ens2.get("already_existed") is True and ens2.get("created") is False,
            json.dumps(ens2),
        )

        # Status
        st = csb.session_status("local", session)
        check("status_running", st.get("ok") is True and st.get("status") == "running", json.dumps(st))

        # Listing finds it
        lst = csb.list_sessions(target="local")
        names = [s["session_name"] for s in lst.get("sessions") or []]
        check("session_appears_in_list", session in names)

        # Send a harmless shell command (not claude): "echo SMOKE_TOKEN_XYZ"
        token = f"SMOKE_TOKEN_{uuid.uuid4().hex[:8]}"
        send = csb.send_message("local", session, f"echo {token}")
        check("send_message_ok", send.get("ok") is True, json.dumps(send))

        # Wait briefly for shell to render
        time.sleep(0.4)

        # Capture tail
        cap = csb.capture_output("local", session, tail_lines=100)
        check(
            "capture_bounded_shape",
            cap.get("ok") is True
            and isinstance(cap.get("output"), str)
            and isinstance(cap.get("line_count"), int),
            json.dumps({k: v for k, v in cap.items() if k != "output"}),
        )
        check("capture_contains_token", token in (cap.get("output") or ""))

        # ask_session against the shell: we're just validating the mechanics
        # of ensure+before+send+poll+after+diff. The "reply" will be the
        # echo output of our token2.
        token2 = f"ASK_TOKEN_{uuid.uuid4().hex[:8]}"
        ask = csb.ask_session(
            "local",
            session,
            f"echo {token2}",
            ensure=False,  # session already up
            poll_interval_s=0.2,
            max_polls=8,
            settle_lines=100,
        )
        check(
            "ask_session_shape",
            ask.get("ok") is True
            and isinstance(ask.get("reply_text"), str)
            and isinstance(ask.get("polls_done"), int),
            json.dumps({k: v for k, v in ask.items() if k not in ("ensure",)}),
        )
        check(
            "ask_session_reply_contains_token",
            token2 in (ask.get("reply_text") or "") or token2 in (ask.get("reply_text") or ""),
        )

        # Target routing metadata is preserved
        check("ask_preserves_target", ask.get("target") == "local")
        check("ask_preserves_session_name", ask.get("session_name") == session)

        # Malformed inputs still safe
        bad_tail = csb.capture_output("local", session, tail_lines=-5)
        check("bad_tail_rejected", bad_tail.get("ok") is False)

    finally:
        # Teardown: kill the test session if it exists
        from eos_ai.substrate.claude_session_bridge import _run_tmux

        _run_tmux(["kill-session", "-t", session])

    # 8. Hot-path hygiene
    check("hotpath_clean", _hotpath_clean())

    if FAILURES:
        print(f"\nFAIL — {len(FAILURES)}: {FAILURES}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
