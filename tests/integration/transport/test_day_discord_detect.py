"""Smoke tests for Discord day command detection regex.

Tests the _detect_day_command function which recognizes ritual commands
like "start my day", "close day", "good morning", "good night".

Validates:
  1. test_open_day_triggers     — positive matches for open_day commands
  2. test_close_day_triggers    — positive matches for close_day commands
  3. test_no_match              — false positive rejection (non-matching strings)
  4. test_bang_prefix_skip      — all ! prefixed messages return None

Run directly:
    python3 tests/substrate/test_day_discord_detect.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

# ─── Regex patterns (inline for testing) ────────────────────────────────────

_OPEN_DAY_PHRASES = [
    r"start my day",
    r"open day",
    r"open my day",
    r"open session",
]

_CLOSE_DAY_PHRASES = [
    r"close day",
    r"end my day",
    r"close my day",
    r"close session",
    r"eod",
]

_OPEN_EXACT = [r"good morning"]
_CLOSE_EXACT = [r"good night"]

_OPEN_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_OPEN_DAY_PHRASES) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_CLOSE_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_CLOSE_DAY_PHRASES) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_OPEN_EXACT_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_OPEN_EXACT) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)
_CLOSE_EXACT_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(_CLOSE_EXACT) + r")\s*[.!]?\s*$",
    re.IGNORECASE,
)


def _detect_day_command(text: str) -> str | None:
    """Detect day ritual commands. Returns "open_day", "close_day", or None.

    Skips messages starting with '!' (bang commands handled separately).
    """
    if text.startswith("!"):
        return None
    if _OPEN_PATTERN.match(text):
        return "open_day"
    if _CLOSE_PATTERN.match(text):
        return "close_day"
    if _OPEN_EXACT_PATTERN.match(text):
        return "open_day"
    if _CLOSE_EXACT_PATTERN.match(text):
        return "close_day"
    return None


# ─── Test infrastructure ────────────────────────────────────────────────────

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL  # noqa: PLW0603
    tag = "PASS" if passed else "FAIL"
    if not passed:
        _FAIL += 1
    else:
        _PASS += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


# ─── Test 1: open_day triggers ──────────────────────────────────────────────


def test_open_day_triggers() -> None:
    print("\n── Test 1: open_day triggers ──")

    # Phrase-based open commands
    test_cases = [
        ("start my day", "open_day"),
        ("Start My Day", "open_day"),
        ("open day", "open_day"),
        ("Open Day", "open_day"),
        ("open my day", "open_day"),
        ("open session", "open_day"),
        ("  start my day  ", "open_day"),
        ("start my day.", "open_day"),
        ("open day!", "open_day"),
        # Exact-match open commands
        ("good morning", "open_day"),
        ("Good Morning", "open_day"),
        ("GOOD MORNING", "open_day"),
        ("good morning.", "open_day"),
        ("good morning!", "open_day"),
        ("  good morning  ", "open_day"),
    ]

    for text, expected in test_cases:
        result = _detect_day_command(text)
        passed = result == expected
        _report(
            f'"{text}" → {expected!r}',
            passed,
            f"got {result!r}" if not passed else "",
        )


# ─── Test 2: close_day triggers ─────────────────────────────────────────────


def test_close_day_triggers() -> None:
    print("\n── Test 2: close_day triggers ──")

    test_cases = [
        ("close day", "close_day"),
        ("Close Day", "close_day"),
        ("end my day", "close_day"),
        ("End My Day", "close_day"),
        ("close my day", "close_day"),
        ("close session", "close_day"),
        ("eod", "close_day"),
        ("EOD", "close_day"),
        ("Eod", "close_day"),
        ("  close day  ", "close_day"),
        ("close day.", "close_day"),
        ("close day!", "close_day"),
        # Exact-match close commands
        ("good night", "close_day"),
        ("Good Night", "close_day"),
        ("GOOD NIGHT", "close_day"),
        ("good night.", "close_day"),
        ("good night!", "close_day"),
        ("  good night  ", "close_day"),
    ]

    for text, expected in test_cases:
        result = _detect_day_command(text)
        passed = result == expected
        _report(
            f'"{text}" → {expected!r}',
            passed,
            f"got {result!r}" if not passed else "",
        )


# ─── Test 3: no match (false positive rejection) ─────────────────────────────


def test_no_match() -> None:
    print("\n── Test 3: no match (false positive rejection) ──")

    test_cases = [
        "I want to start my day planner project",
        "can you open day mode for the API",
        "let's close day trading logic",
        "what is eod price",
        "good morning everyone how are you",
        "say good night to the team",
        "deploy the webhook",
        "fix auth bug",
        "the session opens tomorrow",
        "we close the business day at 5pm",
        "my morning routine is great",
        "night time is for sleeping",
    ]

    for text in test_cases:
        result = _detect_day_command(text)
        passed = result is None
        _report(
            f'"{text}" → None',
            passed,
            f"got {result!r}" if not passed else "",
        )


# ─── Test 4: bang prefix skip ───────────────────────────────────────────────


def test_bang_prefix_skip() -> None:
    print("\n── Test 4: bang prefix skip ──")

    test_cases = [
        "!start my day",
        "!open day",
        "!close day",
        "!eod",
        "!openday",
        "!closeday",
        "!good morning",
        "!good night",
        "! start my day",
        "!  open day",
    ]

    for text in test_cases:
        result = _detect_day_command(text)
        passed = result is None
        _report(
            f'"{text}" → None (bang skip)',
            passed,
            f"got {result!r}" if not passed else "",
        )


# ─── Run ────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    print("Discord Day Command Detection — Regex Smoke Tests")
    print("=" * 60)

    test_open_day_triggers()
    test_close_day_triggers()
    test_no_match()
    test_bang_prefix_skip()

    print("\n" + "=" * 60)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All smoke tests passed.")
