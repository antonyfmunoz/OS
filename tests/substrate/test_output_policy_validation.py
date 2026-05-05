"""
End-to-end validation of the Discord output policy.

Tests the complete filtering pipeline with REAL-WORLD CC output patterns
to verify:
  1. No raw session names leak through
  2. No CLI artifacts leak through
  3. Final answer extraction works correctly
  4. Header-only / empty COMPLETE events are suppressed
  5. Builder and DEX outputs are correctly separated and labeled
  6. Permission and plan formatting is clean
  7. Sanitization of all known session name variants
"""

import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.discord_output_policy import (
    PermissionOrigin,
    classify_permission_origin,
    clean_for_discord,
    extract_final_answer,
    format_completion_header,
    format_permission_granted,
    format_permission_request,
    format_plan_proposal,
    format_question_with_answer_hint,
    get_display_identity,
    get_display_name,
    hard_drop_filter,
    sanitize_session_names,
    should_show_in_discord,
    should_surface_permission,
)

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        msg = f"  FAIL  {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Display name mapping
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 1. Display Name Mapping ═══")

check(
    "builder display name",
    get_display_name("dex_builder_main") == "Builder",
    f"got: {get_display_name('dex_builder_main')}",
)

check(
    "product display name",
    get_display_name("dex_product_main") == "DEX",
    f"got: {get_display_name('dex_product_main')}",
)

check(
    "unknown session gets cleaned fallback",
    get_display_name("some_other_session") == "Some Other Session",
    f"got: {get_display_name('some_other_session')}",
)

identity = get_display_identity("dex_builder_main")
check("builder identity role", identity.role == "builder", f"got: {identity.role}")
check(
    "builder identity ownership",
    identity.ownership == "infrastructure",
    f"got: {identity.ownership}",
)

identity = get_display_identity("dex_product_main")
check("product identity role", identity.role == "ea_product", f"got: {identity.role}")
check(
    "product identity ownership",
    identity.ownership == "product",
    f"got: {identity.ownership}",
)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Raw session name sanitization
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 2. Session Name Sanitization ═══")

RAW_NAME_TESTS = [
    ("dex_builder_main is working", "Builder is working"),
    ("dex_product_main completed", "DEX completed"),
    ("`dex_builder_main` session", "Builder session"),
    ("`dex_product_main` session", "DEX session"),
    ("Dex Builder Main completed", "Builder completed"),
    ("Dex Product Main completed", "DEX completed"),
    ("claude_cli/dex_builder_main", "Builder"),
    ("claude_cli/dex_product_main", "DEX"),
    ("No raw names here", "No raw names here"),
]

for raw, expected in RAW_NAME_TESTS:
    result = sanitize_session_names(raw)
    check(
        f"sanitize: '{raw[:40]}...'",
        result == expected,
        f"expected '{expected}', got '{result}'",
    )


# ═══════════════════════════════════════════════════════════════════════════
# 3. Hard-drop filter (CLI artifacts)
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 3. Hard-Drop Filter (CLI Artifacts) ═══")

CLI_ARTIFACT_LINES = [
    "  (12,345 tokens)",
    "Tip: Use /btw for side questions",
    "  Boondoggling for 3.2s",
    "  Thinking for 2.1s",
    "  Cost: $0.15",
    "  Duration: 15s",
    "  Total cost: $1.20",
    "  Total duration: 45s",
    "  • Read file.py",
    "  └ Done",
    "  │ processing",
    "  accept edits on all files",
    "  (shift+tab to cycle)",
    "  /effort high",
    "  Model: claude-opus-4-20250514",
    "  Permission mode: default",
    "  [rerun: b3]",
    "  claude-opus-4-20250514",
    "  claude-sonnet-4-20250514",
    "Running python3 test.py",
    "Bash(python3 test.py)",
    "Read(/opt/OS/file.py)",
    "Write(/opt/OS/file.py)",
    "Edit(/opt/OS/file.py)",
    "Glob(**/*.py)",
    "Grep(pattern)",
    "Agent(description)",
    "TaskCreate(subject)",
    "python3 -c 'import sys'",
    "git status",
    "npm install",
    "pip install requests",
    "docker restart os-bot",
    "ruff format file.py",
    "> output from tool call",
]

for line in CLI_ARTIFACT_LINES:
    result = hard_drop_filter(line)
    check(
        f"drops: '{line[:50]}...'",
        result.strip() == "",
        f"leaked: '{result.strip()[:80]}'",
    )

# Lines that SHOULD survive
KEEP_LINES = [
    "The deployment is complete.",
    "Here is the summary of changes:",
    "## Changes Made",
    "I've updated the authentication module.",
    "The bug was in line 42 of gateway.py.",
]

for line in KEEP_LINES:
    result = hard_drop_filter(line)
    check(
        f"keeps: '{line[:50]}...'",
        result.strip() == line.strip(),
        f"got: '{result.strip()[:80]}'",
    )


# ═══════════════════════════════════════════════════════════════════════════
# 4. Full clean_for_discord pipeline
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 4. Full clean_for_discord Pipeline ═══")

# Simulated CC output with mixed content
MIXED_CC_OUTPUT = """<thinking>
Let me think about this carefully...
The user wants to update the auth module.
</thinking>

I've completed the authentication update.

## Changes Made
- Updated the session handler
- Fixed the token validation

## Verification
All tests pass.

⎿ Running tests...
  ✓ 12 passed

  (2,345 tokens)
  Cost: $0.08
  Duration: 12s"""

cleaned = clean_for_discord(MIXED_CC_OUTPUT)

check(
    "strips thinking block",
    "<thinking>" not in cleaned,
    f"found <thinking> in cleaned output",
)
check(
    "strips tool output (⎿)",
    "⎿" not in cleaned,
    f"found ⎿ in cleaned output",
)
check(
    "strips token count",
    "tokens)" not in cleaned,
    f"found tokens) in cleaned output",
)
check(
    "strips cost",
    "Cost: $" not in cleaned,
    f"found Cost: $ in cleaned output",
)
check(
    "preserves section header",
    "## Changes Made" in cleaned,
    f"section header missing from output",
)
check(
    "preserves meaningful content",
    "authentication update" in cleaned,
    f"meaningful content missing",
)


# Test with raw session names embedded
SESSION_NAME_OUTPUT = """
I've checked the dex_builder_main session and the dex_product_main session.
The `dex_builder_main` is responding normally.
Dex Builder Main completed its task.
"""

cleaned_names = clean_for_discord(SESSION_NAME_OUTPUT)
check(
    "no raw dex_builder_main",
    "dex_builder_main" not in cleaned_names,
    f"raw name leaked: {cleaned_names[:200]}",
)
check(
    "no raw dex_product_main",
    "dex_product_main" not in cleaned_names,
    f"raw name leaked: {cleaned_names[:200]}",
)
check(
    "no raw Dex Builder Main",
    "Dex Builder Main" not in cleaned_names,
    f"raw name leaked: {cleaned_names[:200]}",
)
check(
    "Builder present after sanitization",
    "Builder" in cleaned_names,
    f"display name missing",
)
check(
    "DEX present after sanitization",
    "DEX" in cleaned_names,
    f"display name missing",
)


# ═══════════════════════════════════════════════════════════════════════════
# 5. Final answer extraction
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 5. Final Answer Extraction ═══")

# Good final answer with section headers
GOOD_REPORT = """## Summary
Updated the authentication module to support OAuth2.

## Changes
- Added OAuth2 provider
- Updated session handler
- Fixed token refresh logic

## Verification
All 15 tests pass. Import check clean."""

final = extract_final_answer(GOOD_REPORT)
check(
    "extracts report with headers",
    len(final) > 100,
    f"extracted {len(final)} chars",
)
check(
    "includes Summary section",
    "Summary" in final,
    f"Summary missing from extracted answer",
)

# Short coherent answer
SHORT_ANSWER = "The bug was in the token validation logic. I've fixed it by checking expiry before refresh."
final_short = extract_final_answer(SHORT_ANSWER)
check(
    "extracts short coherent answer",
    len(final_short) > 20,
    f"short answer suppressed: got {len(final_short)} chars",
)

# Header-only junk — should be SUPPRESSED
HEADER_ONLY = "## Done"
final_header = extract_final_answer(HEADER_ONLY)
check(
    "suppresses header-only content",
    final_header == "",
    f"header-only leaked: '{final_header}'",
)

# Empty / trivial — should be SUPPRESSED
TRIVIAL = "ok"
final_trivial = extract_final_answer(TRIVIAL)
check(
    "suppresses trivial content",
    final_trivial == "",
    f"trivial leaked: '{final_trivial}'",
)

# CLI artifact contaminated — should be SUPPRESSED
CLI_JUNK = """accept edits on all files
(shift+tab to cycle)
/effort high
Model: claude-opus-4-20250514
Permission mode: default
[rerun: b3]"""
final_junk = extract_final_answer(CLI_JUNK)
check(
    "suppresses CLI artifact block",
    final_junk == "",
    f"CLI junk leaked: '{final_junk[:100]}'",
)

# Mixed: some real content + lots of artifacts
MIXED_QUALITY = """The deployment completed successfully.

Running python3 verify.py
Bash(python3 verify.py)
> All checks pass
  (1,234 tokens)
  Cost: $0.05

## Result
Everything is working as expected."""

# clean first, then extract
cleaned_mixed = clean_for_discord(MIXED_QUALITY)
final_mixed = extract_final_answer(cleaned_mixed)
check(
    "extracts from mixed content",
    len(final_mixed) > 20,
    f"mixed extraction got {len(final_mixed)} chars: '{final_mixed[:100]}'",
)
check(
    "no CLI artifacts in extracted",
    "tokens)" not in final_mixed and "Cost: $" not in final_mixed,
    f"artifacts in final: '{final_mixed[:200]}'",
)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Event visibility classification
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 6. Event Visibility ═══")

USER_FACING_STATES = ["complete", "plan_mode", "permission_request", "waiting_question"]
INTERNAL_STATES = ["idle", "responding", "working"]

for state in USER_FACING_STATES:
    check(
        f"{state} is user-facing",
        should_show_in_discord(state),
        f"{state} was not classified as user-facing",
    )

for state in INTERNAL_STATES:
    check(
        f"{state} is internal-only",
        not should_show_in_discord(state),
        f"{state} leaked to Discord",
    )


# ═══════════════════════════════════════════════════════════════════════════
# 7. Message formatting (no raw session names)
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 7. Message Formatting ═══")

SESSIONS = [
    ("dex_builder_main", "Builder"),
    ("dex_product_main", "DEX"),
]

for session, display in SESSIONS:
    header = format_completion_header(session, "test content")
    check(
        f"completion header shows '{display}'",
        display in header,
        f"got: {header}",
    )
    check(
        f"completion header hides raw name",
        session not in header,
        f"raw name in header: {header}",
    )

    perm = format_permission_request(session, "Run bash command")
    check(
        f"permission shows '{display}'",
        display in perm,
        f"got: {perm[:100]}",
    )
    check(
        f"permission hides raw name",
        session not in perm,
        f"raw name in perm: {perm[:100]}",
    )

    plan = format_plan_proposal(session, "Here is my plan")
    check(
        f"plan shows '{display}'",
        display in plan,
        f"got: {plan[:100]}",
    )

    question = format_question_with_answer_hint(session, "Which option?")
    check(
        f"question shows '{display}'",
        display in question,
        f"got: {question[:100]}",
    )
    # Note: the answer hint includes raw session name intentionally
    # (for the !answer command). Verify it's the ONLY place.

    granted = format_permission_granted(session)
    check(
        f"granted shows '{display}'",
        display in granted,
        f"got: {granted}",
    )


# ═══════════════════════════════════════════════════════════════════════════
# 8. Edge cases — potential leak vectors
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 8. Edge Cases — Leak Vectors ═══")

# Reasoning block spanning multiple lines
MULTILINE_REASONING = """<reasoning>
This is internal reasoning
that spans multiple lines
and should never reach Discord.
</reasoning>

The actual answer is here."""

cleaned_reasoning = clean_for_discord(MULTILINE_REASONING)
check(
    "strips multiline reasoning",
    "<reasoning>" not in cleaned_reasoning,
    f"reasoning leaked",
)
check(
    "preserves content after reasoning",
    "actual answer" in cleaned_reasoning,
    f"content after reasoning was lost",
)

# Internal debug lines
DEBUG_OUTPUT = """[SessionWatcher] dex_builder_main: idle → responding
[SessionDiscordBridge] Event captured
[DEBUG] Processing event
[TRACE] Checking state
The real output is here."""

cleaned_debug = clean_for_discord(DEBUG_OUTPUT)
check(
    "strips SessionWatcher lines",
    "[SessionWatcher]" not in cleaned_debug,
    f"debug line leaked",
)
check(
    "strips SessionDiscordBridge lines",
    "[SessionDiscordBridge]" not in cleaned_debug,
    f"debug line leaked",
)
check(
    "strips DEBUG lines",
    "[DEBUG]" not in cleaned_debug,
    f"debug line leaked",
)
check(
    "preserves real output",
    "real output" in cleaned_debug,
    f"content lost",
)

# Insight blocks should SURVIVE (they're user-facing)
INSIGHT_BLOCK = """★ Insight ─────────────────────────────────────
Key point about the implementation
─────────────────────────────────────────────────

The code is updated."""

cleaned_insight = clean_for_discord(INSIGHT_BLOCK)
check(
    "preserves Insight blocks",
    "★ Insight" in cleaned_insight,
    f"Insight block was stripped",
)


# ═══════════════════════════════════════════════════════════════════════════
# 9. Permission Visibility Policy
# ═══════════════════════════════════════════════════════════════════════════
print("\n═══ 9. Permission Visibility Policy ═══")

# Autonomous sessions: permissions are INTERNAL_AUTO — suppressed from Discord
check(
    "builder session is internal_auto",
    classify_permission_origin("dex_builder_main") == PermissionOrigin.INTERNAL_AUTO,
    f"got: {classify_permission_origin('dex_builder_main')}",
)
check(
    "product session is internal_auto",
    classify_permission_origin("dex_product_main") == PermissionOrigin.INTERNAL_AUTO,
    f"got: {classify_permission_origin('dex_product_main')}",
)
check(
    "builder permission NOT surfaced",
    not should_surface_permission("dex_builder_main"),
    "builder permission was surfaced — should be suppressed",
)
check(
    "product permission NOT surfaced",
    not should_surface_permission("dex_product_main"),
    "product permission was surfaced — should be suppressed",
)

# Unknown/future interactive sessions: permissions ARE user-facing
check(
    "unknown session permission IS surfaced",
    should_surface_permission("user_interactive_session"),
    "unknown session permission was suppressed — should surface",
)
check(
    "unknown session is user_facing origin",
    classify_permission_origin("user_interactive_session")
    == PermissionOrigin.USER_FACING,
    f"got: {classify_permission_origin('user_interactive_session')}",
)

# Event visibility: permission_request state is still classified as user-facing
# at the EVENT level (the permission visibility policy adds the session-aware gate)
check(
    "permission_request event still user-facing type",
    should_show_in_discord("permission_request"),
    "permission_request event type was changed — policy is session-aware, not event-aware",
)


# ═══════════════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'═' * 60}")
print(f"RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
print(f"{'═' * 60}")

if FAIL > 0:
    print("\n⚠️  FAILURES DETECTED — fixes required")
    sys.exit(1)
else:
    print("\n✅ All checks passed — output policy is production-safe")
    sys.exit(0)
