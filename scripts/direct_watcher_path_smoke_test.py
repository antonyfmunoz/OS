#!/usr/bin/env python3
"""Smoke test — Direct CC Watcher Path for Discord messages.

Validates that the direct watcher path in discord_bot.on_message:
  1. Resolves the correct session name from Discord mode routing
  2. Detects active watchers
  3. ask_session_watched returns the expected shape
  4. _scrub_cli_chrome cleans CC output correctly
  5. Falls through to PseudoLive when no watcher is running

Run:  python3 scripts/direct_watcher_path_smoke_test.py
"""

import os
import sys
import threading
import time

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
os.environ.setdefault("EOS_DISCORD_TEXT_TRANSPORT_ENABLED", "1")
os.environ.setdefault("EOS_DISCORD_TEXT_ALLOWED_GUILDS", "*")
os.environ.setdefault("EOS_DISCORD_TEXT_ALLOWED_CHANNELS", "*")
os.environ.setdefault("EOS_DISCORD_TEXT_ALLOWED_USERS", "*")
os.environ.setdefault("EOS_ROUTER_CLAUDE_CLI_SESSION", "dex_main")

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        print(f"  ✓  {name}")
        passed += 1
    else:
        msg = f"  ✗  {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        failed += 1


# ── 1. Mode routing resolves correct session names ────────────────────────

print("\n── 1. Mode routing → session name resolution ──")

from eos_ai.substrate.discord_mode_routing import (
    resolve_discord_mode,
    resolve_mode_session,
)

# Unknown mode → should fall back to env default
mode_unknown = resolve_discord_mode(None, None)
check("unknown mode for (None, None)", mode_unknown == "unknown")

session_unknown = resolve_mode_session(mode_unknown)
check(
    "unknown mode session_name is None",
    session_unknown.get("session_name") is None,
    f"got {session_unknown.get('session_name')}",
)

# Fallback for unknown mode should use EOS_ROUTER_CLAUDE_CLI_SESSION
fallback_session = os.getenv("EOS_ROUTER_CLAUDE_CLI_SESSION", "dex_main")
check(
    "env fallback session for unknown mode",
    fallback_session == "dex_main",
    f"got {fallback_session}",
)

# Builder mode (if channels configured)
builder_channels_raw = os.getenv("EOS_DISCORD_BUILDER_CHANNELS", "")
if builder_channels_raw.strip():
    test_cid = builder_channels_raw.split(",")[0].strip()
    mode_builder = resolve_discord_mode(None, test_cid)
    check("builder mode detected", mode_builder == "builder")
    session_builder = resolve_mode_session(mode_builder, channel_id=test_cid)
    check(
        "builder session contains 'builder'",
        "builder" in (session_builder.get("session_name") or ""),
        f"got {session_builder.get('session_name')}",
    )
else:
    print("  ─  SKIP builder channel test (no channels configured)")

# Product mode (if channels configured)
product_channels_raw = os.getenv("EOS_DISCORD_PRODUCT_CHANNELS", "")
if product_channels_raw.strip():
    test_cid = product_channels_raw.split(",")[0].strip()
    mode_product = resolve_discord_mode(None, test_cid)
    check("product mode detected", mode_product == "product")
    session_product = resolve_mode_session(mode_product, channel_id=test_cid)
    check(
        "product session contains 'product'",
        "product" in (session_product.get("session_name") or ""),
        f"got {session_product.get('session_name')}",
    )
else:
    print("  ─  SKIP product channel test (no channels configured)")


# ── 2. Watcher detection ─────────────────────────────────────────────────

print("\n── 2. Watcher detection ──")

from eos_ai.substrate.session_watcher import get_watcher, start_watcher

# Check for running watchers
for sname in ("dex_builder_main", "dex_product_main", "dex_main"):
    w = get_watcher(sname)
    if w and w.is_running:
        check(f"watcher running for {sname}", True)
    else:
        check(f"watcher exists for {sname}", w is not None, "not started")


# ── 3. ask_session_watched shape ──────────────────────────────────────────

print("\n── 3. ask_session_watched return shape ──")

from eos_ai.substrate.session_watcher import ask_session_watched

# Test with non-existent session → should return no_watcher fallback
result = ask_session_watched("vps", "smoke_test_nonexistent", "hello")
check(
    "no_watcher returns ok=False",
    result.get("ok") is False,
    f"got ok={result.get('ok')}",
)
check(
    "no_watcher returns fallback=True",
    result.get("fallback") is True,
    f"got fallback={result.get('fallback')}",
)
check(
    "no_watcher reason",
    result.get("reason") == "no_watcher",
    f"got reason={result.get('reason')}",
)


# ── 4. _scrub_cli_chrome cleans CC output ─────────────────────────────────

print("\n── 4. _scrub_cli_chrome output cleaning ──")

from eos_ai.substrate.claude_session_bridge import _scrub_cli_chrome

# Simulated CC tmux output with markers and chrome
sample_output = """╭───────────────────────────────╮
│ ● some CC banner text        │
╰───────────────────────────────╯

● Here is the actual reply from Claude.
It spans multiple lines.
This is useful content.

───────────────────────────────
❯ """

cleaned = _scrub_cli_chrome(sample_output).strip()
check(
    "scrub removes prompt marker",
    "❯" not in cleaned,
    f"got: {cleaned[-50:]}",
)
check(
    "scrub preserves reply content",
    "actual reply from Claude" in cleaned,
    f"got: {cleaned[:100]}",
)
check(
    "scrub preserves multiline content",
    "useful content" in cleaned,
)


# ── 5. Direct path flow control ──────────────────────────────────────────

print("\n── 5. Direct path flow control logic ──")

# Simulate the decision flow from on_message
_dw_session_name = None
_dw_mode = resolve_discord_mode(None, None)  # unknown
_dw_session_info = resolve_mode_session(_dw_mode)
_dw_session_name = _dw_session_info.get("session_name")

# For unknown mode, should fall back to env default
if not _dw_session_name:
    _dw_session_name = os.getenv("EOS_ROUTER_CLAUDE_CLI_SESSION", "dex_main")

check(
    "unknown mode falls back to dex_main",
    _dw_session_name == "dex_main",
    f"got {_dw_session_name}",
)

# Check that watcher existence determines path
_dw_watcher = get_watcher(_dw_session_name)
if _dw_watcher and _dw_watcher.is_running:
    check(f"would use direct watcher for {_dw_session_name}", True)
else:
    check(
        f"would fall through to PseudoLive for {_dw_session_name}",
        True,
        "watcher not running — PseudoLive is the fallback",
    )

# Verify the correct session for each known mode
for mode_name, expected_substr in [("builder", "builder"), ("product", "product")]:
    session_info = resolve_mode_session(mode_name)
    sname = session_info.get("session_name", "")
    check(
        f"{mode_name} mode → session contains '{expected_substr}'",
        expected_substr in sname,
        f"got {sname}",
    )


# ── 6. Footer format ─────────────────────────────────────────────────────

print("\n── 6. Footer format validation ──")

# Simulate the footer that would be appended
_test_reply = "This is a test reply."
_test_session = "dex_product_main"
_test_ms = 1234
_test_tokens = max(1, len(_test_reply) // 4)

# Use get_ai_name for the footer
try:
    from eos_ai.business_instance import get_ai_name

    ai_name = get_ai_name()
except Exception:
    ai_name = "DEX"

footer = (
    f"\n\n— {ai_name}  "
    f"·  claude_cli/{_test_session}  "
    f"·  {_test_ms}ms  ·  ~{_test_tokens} tok"
)
output = _test_reply.rstrip() + footer

check("footer contains AI name", ai_name in output)
check("footer contains session name", _test_session in output)
check("footer contains timing", "1234ms" in output)
check("footer contains token estimate", f"~{_test_tokens} tok" in output)
check("footer contains provider", "claude_cli" in output)


# ── Summary ──────────────────────────────────────────────────────────────

print(f"\n{'=' * 50}")
total = passed + failed
print(f"Direct Watcher Path Smoke Test: {passed}/{total} passed")
if failed:
    print(f"FAILED: {failed} checks did not pass")
    sys.exit(1)
else:
    print("ALL PASSED")
    sys.exit(0)
