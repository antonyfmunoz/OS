"""
Discord Output Policy — presentation boundary for all Discord-bound output.

This module is the single source of truth for:
  - What events are allowed to reach Discord
  - How session identities are displayed
  - What content is filtered/suppressed before Discord delivery

Design invariants:
  - No hot-path imports (gateway, cognitive_loop, model_router)
  - Pure functions: no Discord API calls, no side effects
  - All formatting decisions centralized here
  - Internal traceability preserved — raw text available in logs
  - NEVER silently suppress valid final reports — log every drop with reason

v1 — initial output governance layer
v2 — delivery forensics: structured logging at every drop point,
      conservative extraction that preserves valid content
"""

from __future__ import annotations

import enum
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ─── Event Visibility ──────────────────────────────────────────────────────


class EventVisibility(enum.Enum):
    """Controls whether an event reaches Discord."""

    USER_FACING = "user_facing"  # normal Discord delivery
    ADMIN_DEBUG = "admin_debug"  # only in admin/debug channels
    INTERNAL_ONLY = "internal_only"  # logs only, never Discord


# ─── Display Identity ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class DisplayIdentity:
    """Canonical user-facing identity for a session."""

    display_name: str  # "DEX", "Builder"
    role: str  # "ea_product", "builder"
    ownership: str  # "product", "infrastructure"


# The ONLY mapping from raw session names to user-facing labels.
# If a session is not here, it gets a sanitized fallback — never raw.
_DISPLAY_IDENTITIES: dict[str, DisplayIdentity] = {
    "dex_product_main": DisplayIdentity("DEX", "ea_product", "product"),
    "dex_builder_main": DisplayIdentity("Builder", "builder", "infrastructure"),
}


def get_display_name(session_name: str) -> str:
    """Get the canonical user-facing display name for a session.

    Never returns raw session names. Unknown sessions get a cleaned label.
    """
    identity = _DISPLAY_IDENTITIES.get(session_name)
    if identity:
        return identity.display_name
    # Fallback: clean the session name into a readable label
    return session_name.replace("_", " ").title()


def get_display_identity(session_name: str) -> DisplayIdentity:
    """Full display identity for a session."""
    identity = _DISPLAY_IDENTITIES.get(session_name)
    if identity:
        return identity
    return DisplayIdentity(
        display_name=session_name.replace("_", " ").title(),
        role="unknown",
        ownership="unknown",
    )


# ─── Content Filtering ────────────────────────────────────────────────────

# Patterns that indicate internal reasoning / thought content.
# These should be stripped from user-facing output.
_REASONING_PATTERNS: list[re.Pattern[str]] = [
    # Claude thinking tags
    re.compile(r"<thinking>.*?</thinking>", re.DOTALL),
    re.compile(r"<reflection>.*?</reflection>", re.DOTALL),
    re.compile(r"<internal>.*?</internal>", re.DOTALL),
    # Explicit reasoning blocks (★ Insight is allowed — it's user-facing)
    re.compile(r"<reasoning>.*?</reasoning>", re.DOTALL),
    # Claude Code internal tool output markers (⎿ indented blocks)
    re.compile(r"^⎿\s.*$", re.MULTILINE),
]

# Patterns that indicate internal/operational noise — suppress these lines.
_NOISE_PATTERNS: list[re.Pattern[str]] = [
    # Raw tmux state machine transitions
    re.compile(r"^\[SessionWatcher\]", re.MULTILINE),
    re.compile(r"^\[SessionDiscordBridge\]", re.MULTILINE),
    # Internal debug prints
    re.compile(r"^\[DEBUG\]", re.MULTILINE),
    re.compile(r"^\[TRACE\]", re.MULTILINE),
    # CC tool call headers that sometimes leak
    re.compile(r"^(?:Running|Bash|Read|Write|Edit|Glob|Grep|Agent)\s*\(", re.MULTILINE),
]

# ─── Hard-Drop Lines (CC UI artifacts) ──────────────────────────────────────
# Lines containing ANY of these substrings are NEVER user output.
# Applied BEFORE formatting — this is the first line of defense.
#
# CRITICAL: only patterns that are UNAMBIGUOUSLY CC UI noise belong here.
# Patterns that match legitimate report content (bullets, blockquotes,
# box-drawing, prose starting with tool names) were removed in v2 after
# they silently stripped valid final reports.
_HARD_DROP_SUBSTRINGS: list[str] = [
    "tokens)",
    "Tip:",
    "Boondoggling",
    "Reading file",
    "Use /btw",
    "/btw ",
    "ctrl+o",
    "ctrl+r",
    "ctrl+c",
    "shift+tab",
    "Compressing conversation",
    "Cost: $",
    "Total cost:",
    "Total duration:",
    # CC CLI UI artifacts — never user output
    "accept edits on",
    "(shift+tab to cycle)",
    "/effort",
    "to expand",
    "to collapse",
    "to cycle",
    "Auto-updated",
    "Permission mode:",
    "Streaming:",
    "[rerun:",
    "claude-opus",
    "claude-sonnet",
    "claude-haiku",
    "sonnet-4",
    "opus-4",
    "haiku-4",
]

# Line-start prefixes that indicate CC operational chatter.
# ONLY tool-call invocation syntax (with parens), not prose that
# happens to start with a tool name.
_HARD_DROP_PREFIXES: list[str] = [
    "Running ",
    "Bash(",
    "Read(",
    "Write(",
    "Edit(",
    "Glob(",
    "Grep(",
    "Agent(",
    "TaskCreate(",
    "TaskUpdate(",
    "Skill(",
    "ToolSearch(",
    "Monitor(",
]


def _is_hard_drop_line(line: str) -> bool:
    """Return True if line is CC UI noise that must never reach Discord."""
    stripped = line.strip()
    if not stripped:
        return False
    for sub in _HARD_DROP_SUBSTRINGS:
        if sub in stripped:
            return True
    for prefix in _HARD_DROP_PREFIXES:
        if stripped.startswith(prefix):
            return True
    return False


def hard_drop_filter(text: str) -> str:
    """Remove all CC UI artifact lines. First line of defense."""
    lines = text.splitlines()
    kept = [line for line in lines if not _is_hard_drop_line(line)]
    dropped = len(lines) - len(kept)
    if dropped > 0:
        logger.debug(
            "[OutputPolicy] hard_drop_filter: %d/%d lines dropped, "
            "input=%d chars, output=%d chars",
            dropped,
            len(lines),
            len(text),
            sum(len(l) for l in kept),
        )
    return "\n".join(kept)


# ─── Section header patterns for final-answer extraction ────────────────────
_SECTION_HEADER_RE = re.compile(
    r"^#{1,3}\s+"  # markdown headers
    r"|^\*\*(?:Summary|Conclusion|Output|Report|Result|Status|Overview|"
    r"Changes|Updated|What changed|Files changed|Verification|Done|"
    r"Completed|Final)"  # bold section headers
    r"|^(?:Summary|Conclusion|Output|Report|Result|Status|Overview)[:\s]",
    re.IGNORECASE | re.MULTILINE,
)

# Raw session names that must never appear in user-facing text.
# We replace them with canonical display names.
# Ordered longest-first so prefixed variants (claude_cli/...) are replaced
# before the bare session name, preventing partial replacements.
_RAW_SESSION_NAMES: list[tuple[str, str]] = [
    ("claude_cli/dex_builder_main", "Builder"),
    ("claude_cli/dex_product_main", "DEX"),
    ("Dex Builder Main", "Builder"),
    ("Dex Product Main", "DEX"),
    ("dex_builder_main", "Builder"),
    ("dex_product_main", "DEX"),
]


def filter_reasoning(text: str) -> str:
    """Remove internal reasoning/thought content from text.

    Preserves the text structure but strips tagged reasoning blocks
    and tool-call output markers. Safe to call on any text.
    """
    result = text
    for pattern in _REASONING_PATTERNS:
        result = pattern.sub("", result)
    # Clean up multiple blank lines left by removals
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def filter_noise(text: str) -> str:
    """Remove operational noise lines from text.

    Strips lines that start with internal debug/trace prefixes.
    """
    lines = text.splitlines()
    clean_lines: list[str] = []
    for line in lines:
        is_noise = False
        for pattern in _NOISE_PATTERNS:
            if pattern.match(line):
                is_noise = True
                break
        if not is_noise:
            clean_lines.append(line)
    return "\n".join(clean_lines)


def sanitize_session_names(text: str) -> str:
    """Replace raw session names with canonical display names.

    Handles both plain text and backtick-quoted references.
    """
    result = text
    for raw, display in _RAW_SESSION_NAMES:
        # Replace backtick-quoted: `dex_builder_main` → Builder
        result = result.replace(f"`{raw}`", display)
        # Replace plain: dex_builder_main → Builder
        result = result.replace(raw, display)
    return result


def clean_for_discord(text: str) -> str:
    """Full pipeline: hard-drop, filter reasoning, noise, and raw session names.

    This is the single entry point for cleaning any text before
    it reaches Discord. Preserves the text for logging separately.
    """
    input_len = len(text)
    result = hard_drop_filter(text)
    result = filter_reasoning(result)
    result = filter_noise(result)
    result = sanitize_session_names(result)
    result = result.strip()
    output_len = len(result)
    if input_len > 0 and output_len == 0:
        logger.warning(
            "[OutputPolicy] clean_for_discord: ALL content removed — "
            "input=%d chars, first 200 chars: %.200s",
            input_len,
            text[:200],
        )
    elif input_len > 0:
        logger.debug(
            "[OutputPolicy] clean_for_discord: %d→%d chars (%.0f%% kept)",
            input_len,
            output_len,
            (output_len / input_len) * 100,
        )
    return result


# ─── Final Answer Extraction ─────────────────────────────────────────────────


# Regex for CC CLI artifact lines that sometimes survive the hard-drop
# filter (e.g. they appear mid-line or in a short block).
_CLI_ARTIFACT_RE = re.compile(
    r"accept edits on"
    r"|shift\+tab to cycle"
    r"|/effort"
    r"|ctrl\+[a-z]"
    r"|tokens?\)"
    r"|Boondoggling"
    r"|Compressing conversation"
    r"|Cost: \$"
    r"|Total cost:"
    r"|Permission mode:"
    r"|Model:"
    r"|\[rerun:"
    r"|claude-opus"
    r"|claude-sonnet"
    r"|claude-haiku",
    re.IGNORECASE,
)


def _post_validate_final_answer(text: str) -> str:
    """Hard validation gate after extraction — reject if still junk.

    Returns the text if valid, empty string if it should be suppressed.
    Applied AFTER extract_final_answer's strategy selection.
    """
    if not text or not text.strip():
        logger.debug("[OutputPolicy] _post_validate: empty input")
        return ""

    stripped = text.strip()

    # Reject if >50% of lines are CLI artifacts
    lines = [l for l in stripped.splitlines() if l.strip()]
    if not lines:
        logger.debug("[OutputPolicy] _post_validate: no non-blank lines")
        return ""
    artifact_lines = sum(1 for l in lines if _CLI_ARTIFACT_RE.search(l))
    artifact_ratio = artifact_lines / max(1, len(lines))
    if artifact_ratio > 0.5:
        logger.info(
            "[OutputPolicy] _post_validate: REJECTED — %.0f%% CLI artifacts "
            "(%d/%d lines), first 200 chars: %.200s",
            artifact_ratio * 100,
            artifact_lines,
            len(lines),
            stripped[:200],
        )
        return ""

    # Reject if the entire text is shorter than 20 meaningful chars
    # after stripping whitespace (header-only COMPLETE events)
    if len(stripped) < 20:
        logger.debug(
            "[OutputPolicy] _post_validate: REJECTED — only %d chars",
            len(stripped),
        )
        return ""

    return stripped


def extract_final_answer(text: str) -> str:
    """Extract ONLY the final answer / report from CC output.

    This is the hard boundary: Discord receives ONLY what this function
    returns. If it returns empty string, nothing is sent to Discord.

    Strategy (in priority order):
      1. Find the last section-header block (Summary, Report, etc.)
         and return everything from there to the end.
      2. Find the last large paragraph block (>200 chars of contiguous
         prose) and return it.
      3. If the entire cleaned text is a short coherent answer (<1500
         chars with no noise markers), return it as-is.
      4. Longer content that passed clean_for_discord — preserve it.
         If the text survived cleaning and is >=20 chars with <50%
         CLI artifacts, it is valid content. Never silently drop a
         report that survived the cleaning pipeline.
      5. Otherwise return empty — nothing goes to Discord.

    Post-validation: even after strategy selection, the result is checked
    by _post_validate_final_answer() which rejects CLI artifacts, empty
    content, and header-only junk.

    Input should already be through clean_for_discord().
    """
    if not text or not text.strip():
        logger.debug("[OutputPolicy] extract_final_answer: empty input")
        return ""

    cleaned = text.strip()

    # Strategy 1: Find section headers. If present, take from the FIRST
    # header to the end — this captures the full report including all
    # sections. But also check if there's substantial prose BEFORE the
    # first header (context/analysis) — if so, include it.
    header_positions: list[int] = []
    for match in _SECTION_HEADER_RE.finditer(cleaned):
        header_positions.append(match.start())

    if header_positions:
        first_header = header_positions[0]
        # Check for substantial prose before the first header
        pre_header = cleaned[:first_header].strip()
        if len(pre_header) >= 100:
            # Include the prose context + all sections
            candidate = cleaned.strip()
        else:
            # Start from the first section header
            candidate = cleaned[first_header:].strip()
        if len(candidate) >= 50:
            result = _post_validate_final_answer(candidate)
            if result:
                logger.debug(
                    "[OutputPolicy] extract_final_answer: strategy=section_header, "
                    "output=%d chars",
                    len(result),
                )
                return result
            logger.debug(
                "[OutputPolicy] extract_final_answer: strategy=section_header "
                "found %d chars but post-validation rejected",
                len(candidate),
            )

    # Strategy 2: Find the last large paragraph block (>200 chars).
    # Split on double-newlines, find the last substantial block.
    paragraphs = cleaned.split("\n\n")
    # Walk backwards to find the last substantial paragraph cluster
    substantial_start = -1
    for i in range(len(paragraphs) - 1, -1, -1):
        p = paragraphs[i].strip()
        if len(p) >= 200:
            substantial_start = i
            break

    if substantial_start >= 0:
        # Take from the substantial paragraph to the end
        candidate = "\n\n".join(paragraphs[substantial_start:]).strip()
        if candidate:
            result = _post_validate_final_answer(candidate)
            if result:
                logger.debug(
                    "[OutputPolicy] extract_final_answer: strategy=last_paragraph, "
                    "output=%d chars",
                    len(result),
                )
                return result
            logger.debug(
                "[OutputPolicy] extract_final_answer: strategy=last_paragraph "
                "found %d chars but post-validation rejected",
                len(candidate),
            )

    # Strategy 3: Short coherent answer — the whole thing is the answer.
    # Only if it's short enough to be a direct reply, not a dump of tool output.
    if len(cleaned) < 1500 and len(cleaned) >= 20:
        # Final sanity: reject if it still looks like tool chatter
        noise_ratio = sum(
            1
            for line in cleaned.splitlines()
            if line.strip().startswith(("⎿", "│", "└"))
        ) / max(1, len(cleaned.splitlines()))
        if noise_ratio < 0.3:
            result = _post_validate_final_answer(cleaned)
            if result:
                logger.debug(
                    "[OutputPolicy] extract_final_answer: strategy=short_coherent, "
                    "output=%d chars",
                    len(result),
                )
                return result

    # Strategy 4: Preserve longer valid content.
    # If the text survived clean_for_discord and is substantial, it is
    # real content — not UI noise. Never silently drop a valid report.
    # This closes the gap where reports with short list items and no
    # section headers were silently suppressed.
    if len(cleaned) >= 20:
        result = _post_validate_final_answer(cleaned)
        if result:
            logger.info(
                "[OutputPolicy] extract_final_answer: strategy=preserve_valid "
                "(fallback), output=%d chars — strategies 1-3 missed, "
                "content preserved via strategy 4",
                len(result),
            )
            return result

    logger.warning(
        "[OutputPolicy] extract_final_answer: ALL strategies failed — "
        "input=%d chars, first 300 chars: %.300s",
        len(cleaned),
        cleaned[:300],
    )
    return ""


# ─── Permission Visibility Policy ──────────────────────────────────────────


class PermissionOrigin(enum.Enum):
    """Classifies where a permission event originated."""

    USER_FACING = "user_facing"  # operator must decide — surface in Discord
    INTERNAL_AUTO = "internal_auto"  # autonomous session — suppress from Discord


class PermissionResolution(enum.Enum):
    """Canonical resolution for a permission event.

    Every permission event resolves to exactly one of these outcomes.
    The resolution drives both the Discord visibility and the watcher
    response path.
    """

    SURFACE_AND_WAIT = "surface_and_wait"  # show in Discord, wait for human
    AUTO_APPROVE_AND_SUPPRESS = "auto_approve_and_suppress"  # send "y", no Discord
    AUTO_DENY_AND_SUPPRESS = (
        "auto_deny_and_suppress"  # future-safe: send "n", no Discord
    )


# Sessions that are autonomous background CC sessions.
# Permission prompts from these sessions are internal operational events
# and should NOT be surfaced to Discord for human interaction.
_AUTONOMOUS_SESSIONS: frozenset[str] = frozenset(_DISPLAY_IDENTITIES.keys())


def classify_permission_origin(session_name: str) -> PermissionOrigin:
    """Classify whether a permission event needs human attention.

    Autonomous tmux CC sessions (dex_builder_main, dex_product_main) are
    background sessions — their permission prompts are internal operational
    events. Only sessions NOT in the autonomous set require operator action.
    """
    if session_name in _AUTONOMOUS_SESSIONS:
        return PermissionOrigin.INTERNAL_AUTO
    return PermissionOrigin.USER_FACING


# ─── Intent Extraction ────────────────────────────────────────────────────


class IntentType(enum.Enum):
    """Categorizes what a permission request is asking to do."""

    COMMAND = "command"  # shell command execution
    FILE_WRITE = "file_write"  # writing/editing files
    FILE_READ = "file_read"  # reading/globbing/grepping files
    NETWORK_CALL = "network_call"  # external network access
    BROWSER_NAVIGATION = "browser_navigation"  # open URL in operator's local browser
    PROCESS_EXEC = "process_exec"  # process/script execution
    UNKNOWN = "unknown"  # could not determine — treat as high risk


@dataclass(frozen=True)
class PermissionIntent:
    """Structured representation of what a permission event is requesting.

    Extracted from the raw permission prompt text via deterministic parsing.
    """

    type: IntentType
    raw: str  # original permission text
    command: str  # parsed command if applicable, else empty
    target: str  # file/path/endpoint if applicable, else empty
    playwright_suppressed: bool = False  # True when simple nav should use OPEN_URL


# Patterns for extracting tool name and arguments from CC permission prompts.
# CC formats: "Bash(command)" or "Read(/path/to/file)" etc.
_TOOL_CALL_RE = re.compile(
    r"(Bash|Read|Write|Edit|Glob|Grep|Agent|WebFetch|WebSearch)\s*\((.+?)\)",
    re.DOTALL,
)

# MCP tool call pattern — matches mcp__server__tool_name(args)
_MCP_TOOL_RE = re.compile(
    r"(mcp__[a-zA-Z0-9_]+__[a-zA-Z0-9_]+)\s*\((.+?)\)",
    re.DOTALL,
)

# Playwright/browser MCP tools that represent local browser navigation.
# These open URLs, navigate, or interact with the operator's browser —
# NOT headless scraping. Classified as BROWSER_NAVIGATION, not NETWORK_CALL.
_BROWSER_NAV_MCP_TOOLS: frozenset[str] = frozenset(
    {
        "mcp__plugin_playwright_playwright__browser_navigate",
        "mcp__plugin_playwright_playwright__browser_navigate_back",
        "mcp__plugin_playwright_playwright__browser_click",
        "mcp__plugin_playwright_playwright__browser_type",
        "mcp__plugin_playwright_playwright__browser_fill_form",
        "mcp__plugin_playwright_playwright__browser_press_key",
        "mcp__plugin_playwright_playwright__browser_hover",
        "mcp__plugin_playwright_playwright__browser_select_option",
        "mcp__plugin_playwright_playwright__browser_snapshot",
        "mcp__plugin_playwright_playwright__browser_tabs",
        "mcp__plugin_playwright_playwright__browser_take_screenshot",
        "mcp__plugin_playwright_playwright__browser_run_code",
        "mcp__plugin_playwright_playwright__browser_wait_for",
        # Chrome DevTools MCP equivalents
        "mcp__plugin_chrome_devtools_mcp_chrome_devtools__navigate_page",
        "mcp__plugin_chrome_devtools_mcp_chrome_devtools__click",
        "mcp__plugin_chrome_devtools_mcp_chrome_devtools__fill",
        "mcp__plugin_chrome_devtools_mcp_chrome_devtools__take_screenshot",
        "mcp__plugin_chrome_devtools_mcp_chrome_devtools__take_snapshot",
        "mcp__plugin_chrome_devtools_mcp_chrome_devtools__press_key",
        "mcp__plugin_chrome_devtools_mcp_chrome_devtools__hover",
    }
)

# Commands that are destructive or system-altering.
_DESTRUCTIVE_COMMAND_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brm\s+(-[rfR]+\s+|)"),  # rm, rm -rf
    re.compile(r"\bgit\s+push\b"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
    re.compile(r"\bgit\s+checkout\s+--"),
    re.compile(r"\bgit\s+branch\s+-[dD]\b"),
    re.compile(r"\bkill\b"),
    re.compile(r"\bpkill\b"),
    re.compile(r"\bdrop\s+(?:table|database)\b", re.IGNORECASE),
    re.compile(r"\btruncate\s+table\b", re.IGNORECASE),
    re.compile(r"^format\b"),  # standalone format command (disk), not args to ruff etc
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bdd\s+if="),
    re.compile(r"\bchmod\s+777\b"),
    re.compile(r"\bsudo\b"),
    re.compile(r"\bdocker\s+(?:rm|rmi|prune|system\s+prune)\b"),
]

# Network-related command prefixes.
_NETWORK_COMMAND_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bcurl\b"),
    re.compile(r"\bwget\b"),
    re.compile(r"\bhttp[s]?://"),
    re.compile(r"\bssh\b"),
    re.compile(r"\bscp\b"),
    re.compile(r"\brsync\b.*:"),
    re.compile(r"\bnpm\s+publish\b"),
    re.compile(r"\bpip\s+install\b"),
    re.compile(r"\bgit\s+clone\b"),
]

# Safe read-only commands that are always low risk.
_SAFE_COMMAND_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^python3?\s+-c\s+['\"](?:from|import)\b"),  # import checks
    re.compile(r"^python3?\s+-m\s+py_compile\b"),
    re.compile(r"^ruff\s+(?:check|format)\b"),
    re.compile(r"^git\s+(?:status|log|diff|branch|show)\b"),
    re.compile(r"^ls\b"),
    re.compile(r"^cat\b"),
    re.compile(r"^head\b"),
    re.compile(r"^tail\b"),
    re.compile(r"^wc\b"),
    re.compile(r"^echo\b"),
    re.compile(r"^pwd\b"),
    re.compile(r"^date\b"),
    re.compile(r"^uname\b"),
]


def extract_intent(permission_text: str) -> PermissionIntent:
    """Parse permission event text into a structured intent.

    Uses deterministic pattern matching — no NLP, no heuristics.
    Falls back to IntentType.UNKNOWN if parsing fails, which biases
    risk classification upward (safe default).
    """
    raw = permission_text.strip()
    if not raw:
        return PermissionIntent(type=IntentType.UNKNOWN, raw=raw, command="", target="")

    match = _TOOL_CALL_RE.search(raw)
    if not match:
        # Try MCP tool pattern before falling back to UNKNOWN
        mcp_intent = _extract_mcp_intent(raw)
        if mcp_intent is not None:
            return mcp_intent
        return PermissionIntent(type=IntentType.UNKNOWN, raw=raw, command="", target="")

    tool_name = match.group(1)
    tool_arg = match.group(2).strip().strip("'\"")

    if tool_name == "Bash":
        # Determine if it's a network call, process exec, or general command
        for pat in _NETWORK_COMMAND_PATTERNS:
            if pat.search(tool_arg):
                return PermissionIntent(
                    type=IntentType.NETWORK_CALL,
                    raw=raw,
                    command=tool_arg,
                    target="",
                )
        return PermissionIntent(
            type=IntentType.COMMAND, raw=raw, command=tool_arg, target=""
        )

    if tool_name in ("Write", "Edit"):
        return PermissionIntent(
            type=IntentType.FILE_WRITE,
            raw=raw,
            command=tool_name.lower(),
            target=tool_arg,
        )

    if tool_name in ("Read", "Glob", "Grep"):
        return PermissionIntent(
            type=IntentType.FILE_READ,
            raw=raw,
            command=tool_name.lower(),
            target=tool_arg,
        )

    if tool_name in ("WebFetch", "WebSearch"):
        return PermissionIntent(
            type=IntentType.NETWORK_CALL,
            raw=raw,
            command=tool_name.lower(),
            target=tool_arg,
        )

    if tool_name == "Agent":
        return PermissionIntent(
            type=IntentType.PROCESS_EXEC,
            raw=raw,
            command="agent",
            target=tool_arg,
        )

    return PermissionIntent(type=IntentType.UNKNOWN, raw=raw, command="", target="")


def _extract_mcp_intent(raw: str) -> PermissionIntent | None:
    """Try to parse an MCP tool call and classify it.

    Returns None if the text doesn't match MCP tool pattern.
    """
    match = _MCP_TOOL_RE.search(raw)
    if not match:
        return None

    tool_name = match.group(1)
    tool_arg = match.group(2).strip().strip("'\"")

    # Browser navigation MCP tools → BROWSER_NAVIGATION intent.
    # For simple navigation (Playwright browser_navigate with just a URL),
    # mark playwright_suppressed=True so callers route through OPEN_URL
    # SafeAction path instead of Playwright MCP.
    if tool_name in _BROWSER_NAV_MCP_TOOLS:
        suppressed = False
        if tool_name in (
            "mcp__plugin_playwright_playwright__browser_navigate",
            "mcp__plugin_chrome_devtools_mcp_chrome_devtools__navigate_page",
        ):
            try:
                from umh.substrate.browser_policy import (
                    is_playwright_suppressed_for_intent,
                )

                suppressed = is_playwright_suppressed_for_intent(tool_arg)
            except ImportError:
                pass

        return PermissionIntent(
            type=IntentType.BROWSER_NAVIGATION,
            raw=raw,
            command=tool_name,
            target=tool_arg,
            playwright_suppressed=suppressed,
        )

    # Other MCP tools → NETWORK_CALL (conservative default)
    return PermissionIntent(
        type=IntentType.NETWORK_CALL,
        raw=raw,
        command=tool_name,
        target=tool_arg,
    )


# ─── Risk Classification ─────────────────────────────────────────────────


class RiskLevel(enum.Enum):
    """Deterministic risk classification for permission events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def classify_risk(intent: PermissionIntent) -> RiskLevel:
    """Classify risk level from a structured intent.

    Rules are deterministic and explicit. When uncertain, defaults UP
    to the next higher risk level (safe bias).

    LOW:  read-only operations, safe internal scripts, non-destructive commands
    MEDIUM: local file writes, non-critical process execution, repeatable actions
    HIGH: destructive commands, system-level changes, external network calls, ambiguous
    """
    # Unknown intent → always high (safe default)
    if intent.type == IntentType.UNKNOWN:
        return RiskLevel.HIGH

    # Read-only operations are always low risk
    if intent.type == IntentType.FILE_READ:
        return RiskLevel.LOW

    # Browser navigation (local browser open) is low risk — it's a local action
    if intent.type == IntentType.BROWSER_NAVIGATION:
        return RiskLevel.LOW

    # Network calls are always high risk
    if intent.type == IntentType.NETWORK_CALL:
        return RiskLevel.HIGH

    # File writes are medium risk
    if intent.type == IntentType.FILE_WRITE:
        return RiskLevel.MEDIUM

    # Agent subprocesses are medium risk
    if intent.type == IntentType.PROCESS_EXEC:
        return RiskLevel.MEDIUM

    # Commands: check against known safe/destructive patterns
    if intent.type == IntentType.COMMAND:
        cmd = intent.command.strip()

        # Check destructive patterns first — these are always high
        for pat in _DESTRUCTIVE_COMMAND_PATTERNS:
            if pat.search(cmd):
                return RiskLevel.HIGH

        # Check safe patterns — these are always low
        for pat in _SAFE_COMMAND_PATTERNS:
            if pat.search(cmd):
                return RiskLevel.LOW

        # Everything else is medium (repeatable, local, non-destructive)
        return RiskLevel.MEDIUM

    # Fallback: high (should not reach here, but safe default)
    return RiskLevel.HIGH


# ─── Tool Execution Policy ─────────────────────────────────────────────────


class ToolPolicyDecision(enum.Enum):
    """What the tool execution policy says about a role/action combination.

    ALLOW:    proceed without human intervention.
    ESCALATE: surface to operator (Discord) and wait for approval.
    DENY:     do not execute; emit denied event, optionally notify operator.
    """

    ALLOW = "allow"
    ESCALATE = "escalate"
    DENY = "deny"


# ─── Final Resolution & Execution Mode ────────────────────────────────────


class FinalResolution(str, enum.Enum):
    """Semantic outcome of the combined permission decision.

    Priority ordering: DENY > ESCALATE > ALLOW.
    Used by _combine_decisions() via max() over priority values.
    """

    ALLOW = "allow"
    ESCALATE = "escalate"
    DENY = "deny"


_FINAL_PRIORITY: dict[FinalResolution, int] = {
    FinalResolution.ALLOW: 0,
    FinalResolution.ESCALATE: 1,
    FinalResolution.DENY: 2,
}


class ExecutionMode(str, enum.Enum):
    """Whether the session is autonomous or user-interactive.

    Derived once from session classification. Determines how
    FinalResolution maps to transport-level PermissionResolution.
    """

    AUTO = "auto"
    INTERACTIVE = "interactive"


# ─── Permission Decision (Enriched Return Type) ──────────────────────────


def _derive_resolution(
    final: FinalResolution,
    mode: ExecutionMode,
) -> PermissionResolution:
    """Derive transport-level PermissionResolution from semantic decision.

    PermissionResolution = f(FinalResolution, ExecutionMode).
    This is the ONLY place this derivation happens.
    """
    if mode == ExecutionMode.INTERACTIVE:
        return PermissionResolution.SURFACE_AND_WAIT
    # AUTO mode
    if final == FinalResolution.ALLOW:
        return PermissionResolution.AUTO_APPROVE_AND_SUPPRESS
    if final == FinalResolution.DENY:
        return PermissionResolution.AUTO_DENY_AND_SUPPRESS
    # ESCALATE in auto mode → surface to operator
    return PermissionResolution.SURFACE_AND_WAIT


@dataclass(frozen=True)
class PermissionDecision:
    """Complete, non-bypassable permission decision.

    This is the ONLY object that callers consume from resolve_permission().
    No caller implements additional decision logic.

    Invariant: resolution is always derived from (final_resolution, execution_mode)
    via _derive_resolution(). The __post_init__ enforces this.
    """

    final_resolution: FinalResolution
    execution_mode: ExecutionMode
    origin: PermissionOrigin
    tool_policy_decision: ToolPolicyDecision | None
    constraint_evaluated: bool
    constraint_result: "ConstraintDecision | None"
    constraint_type: "ConstraintType | None"
    constraint_reason: str | None
    # Execution control fields (populated when execution control is applied)
    execution_control_applied: bool = False
    execution_control_type: str | None = None
    execution_control_reason: str | None = None
    rewritten_command: str | None = None
    timeout_seconds: int | None = None
    execution_controls_applied: tuple[str, ...] = ()
    # Scope fields (populated when execution scope is evaluated)
    within_scope: bool = False
    scope_id: str | None = None
    escalation_reason: str | None = None
    resolution: PermissionResolution = field(init=False)

    def __post_init__(self) -> None:
        """Enforce derivation invariant: resolution = f(final, mode, scope).

        When within_scope is True and final_resolution is ALLOW,
        the resolution is forced to AUTO_APPROVE_AND_SUPPRESS regardless
        of execution mode. This is the silent execution path for
        scoped task approval.
        """
        if self.within_scope and self.final_resolution == FinalResolution.ALLOW:
            object.__setattr__(
                self,
                "resolution",
                PermissionResolution.AUTO_APPROVE_AND_SUPPRESS,
            )
        else:
            object.__setattr__(
                self,
                "resolution",
                _derive_resolution(self.final_resolution, self.execution_mode),
            )


# ─── Decision Composition ────────────────────────────────────────────────

# Lazy import to avoid circular dependency at module level.
# evaluate_execution_constraints is imported inside resolve_permission().

_TOOL_POLICY_TO_FINAL: dict[ToolPolicyDecision, FinalResolution] = {
    ToolPolicyDecision.ALLOW: FinalResolution.ALLOW,
    ToolPolicyDecision.ESCALATE: FinalResolution.ESCALATE,
    ToolPolicyDecision.DENY: FinalResolution.DENY,
}


def _combine_decisions(
    tool_policy: ToolPolicyDecision,
    constraint_result: "ConstraintDecision",
) -> FinalResolution:
    """Combine tool policy + constraint into FinalResolution.

    Uses max() over priority: DENY(2) > ESCALATE(1) > ALLOW(0).
    Constraints can tighten but never loosen. DENY is terminal.
    """
    from umh.substrate.execution_constraints import ConstraintDecision

    _constraint_to_final: dict[ConstraintDecision, FinalResolution] = {
        ConstraintDecision.ALLOWED: FinalResolution.ALLOW,
        ConstraintDecision.ESCALATE: FinalResolution.ESCALATE,
        ConstraintDecision.BLOCKED: FinalResolution.DENY,
    }

    tp_final = _TOOL_POLICY_TO_FINAL[tool_policy]
    ct_final = _constraint_to_final[constraint_result]

    if _FINAL_PRIORITY[tp_final] >= _FINAL_PRIORITY[ct_final]:
        return tp_final
    return ct_final


# ─── Role Policy Matrix ───────────────────────────────────────────────────
#
# Keyed by (role, intent_type, risk_level).  Missing entries fall through
# to _ROLE_DEFAULTS which is keyed by (role, intent_type) only.
# If still no match, the global fallback is ESCALATE (safe bias).
#
# Explicit > implicit.  Every entry is a conscious decision.

_ROLE_POLICY_TABLE: dict[tuple[str, IntentType, RiskLevel], ToolPolicyDecision] = {
    # ── Builder (autonomous infrastructure sessions) ──────────────────
    # Reads: always allowed regardless of risk
    ("builder", IntentType.FILE_READ, RiskLevel.LOW): ToolPolicyDecision.ALLOW,
    ("builder", IntentType.FILE_READ, RiskLevel.MEDIUM): ToolPolicyDecision.ALLOW,
    ("builder", IntentType.FILE_READ, RiskLevel.HIGH): ToolPolicyDecision.ALLOW,
    # Writes: allowed at low/medium, escalate at high
    ("builder", IntentType.FILE_WRITE, RiskLevel.LOW): ToolPolicyDecision.ALLOW,
    ("builder", IntentType.FILE_WRITE, RiskLevel.MEDIUM): ToolPolicyDecision.ALLOW,
    ("builder", IntentType.FILE_WRITE, RiskLevel.HIGH): ToolPolicyDecision.ESCALATE,
    # Commands: safe commands allowed, general commands allowed,
    # destructive commands escalated
    ("builder", IntentType.COMMAND, RiskLevel.LOW): ToolPolicyDecision.ALLOW,
    ("builder", IntentType.COMMAND, RiskLevel.MEDIUM): ToolPolicyDecision.ALLOW,
    ("builder", IntentType.COMMAND, RiskLevel.HIGH): ToolPolicyDecision.ESCALATE,
    # Process exec (Agent subprocesses): allowed at low/medium, escalate at high
    ("builder", IntentType.PROCESS_EXEC, RiskLevel.LOW): ToolPolicyDecision.ALLOW,
    ("builder", IntentType.PROCESS_EXEC, RiskLevel.MEDIUM): ToolPolicyDecision.ALLOW,
    ("builder", IntentType.PROCESS_EXEC, RiskLevel.HIGH): ToolPolicyDecision.ESCALATE,
    # Browser navigation: local browser open — always allowed (operator's own machine)
    ("builder", IntentType.BROWSER_NAVIGATION, RiskLevel.LOW): ToolPolicyDecision.ALLOW,
    (
        "builder",
        IntentType.BROWSER_NAVIGATION,
        RiskLevel.MEDIUM,
    ): ToolPolicyDecision.ALLOW,
    (
        "builder",
        IntentType.BROWSER_NAVIGATION,
        RiskLevel.HIGH,
    ): ToolPolicyDecision.ESCALATE,
    # Network calls: always escalate
    ("builder", IntentType.NETWORK_CALL, RiskLevel.LOW): ToolPolicyDecision.ESCALATE,
    ("builder", IntentType.NETWORK_CALL, RiskLevel.MEDIUM): ToolPolicyDecision.ESCALATE,
    ("builder", IntentType.NETWORK_CALL, RiskLevel.HIGH): ToolPolicyDecision.ESCALATE,
    # Unknown intent: always escalate (safe default)
    ("builder", IntentType.UNKNOWN, RiskLevel.LOW): ToolPolicyDecision.ESCALATE,
    ("builder", IntentType.UNKNOWN, RiskLevel.MEDIUM): ToolPolicyDecision.ESCALATE,
    ("builder", IntentType.UNKNOWN, RiskLevel.HIGH): ToolPolicyDecision.ESCALATE,
    # ── EA Product (autonomous product/operating sessions) ────────────
    # Reads: always allowed
    ("ea_product", IntentType.FILE_READ, RiskLevel.LOW): ToolPolicyDecision.ALLOW,
    ("ea_product", IntentType.FILE_READ, RiskLevel.MEDIUM): ToolPolicyDecision.ALLOW,
    ("ea_product", IntentType.FILE_READ, RiskLevel.HIGH): ToolPolicyDecision.ALLOW,
    # Writes: escalate by default (product sessions shouldn't mutate freely)
    ("ea_product", IntentType.FILE_WRITE, RiskLevel.LOW): ToolPolicyDecision.ESCALATE,
    (
        "ea_product",
        IntentType.FILE_WRITE,
        RiskLevel.MEDIUM,
    ): ToolPolicyDecision.ESCALATE,
    ("ea_product", IntentType.FILE_WRITE, RiskLevel.HIGH): ToolPolicyDecision.ESCALATE,
    # Commands: safe commands allowed, others escalate
    ("ea_product", IntentType.COMMAND, RiskLevel.LOW): ToolPolicyDecision.ALLOW,
    ("ea_product", IntentType.COMMAND, RiskLevel.MEDIUM): ToolPolicyDecision.ESCALATE,
    ("ea_product", IntentType.COMMAND, RiskLevel.HIGH): ToolPolicyDecision.ESCALATE,
    # Process exec: escalate (product sessions don't spawn agents freely)
    ("ea_product", IntentType.PROCESS_EXEC, RiskLevel.LOW): ToolPolicyDecision.ESCALATE,
    (
        "ea_product",
        IntentType.PROCESS_EXEC,
        RiskLevel.MEDIUM,
    ): ToolPolicyDecision.ESCALATE,
    (
        "ea_product",
        IntentType.PROCESS_EXEC,
        RiskLevel.HIGH,
    ): ToolPolicyDecision.ESCALATE,
    # Browser navigation: local browser open — allowed at low/medium for product
    (
        "ea_product",
        IntentType.BROWSER_NAVIGATION,
        RiskLevel.LOW,
    ): ToolPolicyDecision.ALLOW,
    (
        "ea_product",
        IntentType.BROWSER_NAVIGATION,
        RiskLevel.MEDIUM,
    ): ToolPolicyDecision.ALLOW,
    (
        "ea_product",
        IntentType.BROWSER_NAVIGATION,
        RiskLevel.HIGH,
    ): ToolPolicyDecision.ESCALATE,
    # Network calls: always escalate
    ("ea_product", IntentType.NETWORK_CALL, RiskLevel.LOW): ToolPolicyDecision.ESCALATE,
    (
        "ea_product",
        IntentType.NETWORK_CALL,
        RiskLevel.MEDIUM,
    ): ToolPolicyDecision.ESCALATE,
    (
        "ea_product",
        IntentType.NETWORK_CALL,
        RiskLevel.HIGH,
    ): ToolPolicyDecision.ESCALATE,
    # Unknown intent: always escalate
    ("ea_product", IntentType.UNKNOWN, RiskLevel.LOW): ToolPolicyDecision.ESCALATE,
    ("ea_product", IntentType.UNKNOWN, RiskLevel.MEDIUM): ToolPolicyDecision.ESCALATE,
    ("ea_product", IntentType.UNKNOWN, RiskLevel.HIGH): ToolPolicyDecision.ESCALATE,
}

# Global fallback: if a role/intent/risk combo is not in the table,
# ESCALATE. This is the safe default for unknown roles or future roles.
_TOOL_POLICY_FALLBACK = ToolPolicyDecision.ESCALATE


def resolve_tool_policy(
    role: str,
    intent: PermissionIntent,
    risk_level: RiskLevel,
) -> ToolPolicyDecision:
    """Look up the tool execution policy for a role/intent/risk combination.

    Deterministic table lookup. No heuristics.

    Args:
        role: Operating context slug (builder, ea_product, unknown).
        intent: Structured permission intent from extract_intent().
        risk_level: Risk classification from classify_risk().

    Returns:
        ToolPolicyDecision: ALLOW, ESCALATE, or DENY.
    """
    key = (role, intent.type, risk_level)
    return _ROLE_POLICY_TABLE.get(key, _TOOL_POLICY_FALLBACK)


# ─── Permission Resolution (Intent + Risk + Tool Policy Aware) ───────────


def resolve_permission(
    session_name: str,
    intent: PermissionIntent | None = None,
    risk_level: RiskLevel | None = None,
    task_id: str = "",
) -> PermissionDecision:
    """Single authoritative decision boundary for permission events.

    Decision = f(session_role, intent, risk_level, tool_policy,
                  execution_constraints, execution_scope).

    This function is the ONLY place that produces a PermissionDecision.
    No caller implements additional decision logic.

    Flow:
      1. Classify origin → execution_mode
      2. If no intent/risk → legacy path (constraint_evaluated=False)
      3. Resolve tool policy
      4. If tool policy DENY → skip constraints (DENY is terminal)
      5. Evaluate execution constraints
      6. Combine via _combine_decisions() (max priority)
      7. Evaluate execution scope (if task_id provided)
      8. If within scope: override ESCALATE → ALLOW (silent execution)
      9. Apply execution controls (for ALLOW/ESCALATE — DENY skips)
     10. Return PermissionDecision with full trace

    Args:
        session_name: Session identifier for role/origin classification.
        intent: Structured permission intent, or None for legacy path.
        risk_level: Risk classification, or None for legacy path.
        task_id: Optional task ID. When provided, checks for an active
            ExecutionScope and applies scoped trust rules.
    """
    from umh.substrate.execution_constraints import (
        ConstraintDecision,
        ConstraintType,
        evaluate_execution_constraints,
    )
    from umh.substrate.execution_control import apply_execution_controls
    from umh.substrate.execution_scope import (
        ScopeRegistry,
        ScopeVerdict,
        evaluate_scope,
    )

    origin = classify_permission_origin(session_name)
    execution_mode = (
        ExecutionMode.AUTO
        if origin == PermissionOrigin.INTERNAL_AUTO
        else ExecutionMode.INTERACTIVE
    )

    # Legacy path: no intent/risk provided → preserve original behavior
    if intent is None or risk_level is None:
        return PermissionDecision(
            final_resolution=FinalResolution.ALLOW,
            execution_mode=execution_mode,
            origin=origin,
            tool_policy_decision=None,
            constraint_evaluated=False,
            constraint_result=None,
            constraint_type=None,
            constraint_reason=None,
        )

    # Full evaluation path
    role = get_display_identity(session_name).role
    tool_decision = resolve_tool_policy(role, intent, risk_level)

    # Tool policy DENY is terminal — skip constraint + scope + execution control
    if tool_decision == ToolPolicyDecision.DENY:
        return PermissionDecision(
            final_resolution=FinalResolution.DENY,
            execution_mode=execution_mode,
            origin=origin,
            tool_policy_decision=tool_decision,
            constraint_evaluated=False,
            constraint_result=None,
            constraint_type=None,
            constraint_reason=None,
        )

    # Evaluate execution constraints
    constraint = evaluate_execution_constraints(intent, risk_level, intent.target)

    # Combine: max priority wins (DENY > ESCALATE > ALLOW)
    final = _combine_decisions(tool_decision, constraint.result)

    # ── Scope evaluation ──────────────────────────────────────────────
    # If a task_id is provided, check for an active execution scope.
    # Scope can override ESCALATE → ALLOW (silent execution) but
    # NEVER overrides DENY (hard policy boundary).
    scope_eval = None
    if task_id:
        active_scope = ScopeRegistry().get_by_task(task_id)
        scope_eval = evaluate_scope(
            active_scope,
            intent.type.value,
            target_path=intent.target,
            command=intent.command,
        )
        # Scope override: WITHIN_SCOPE + non-DENY → force ALLOW
        if scope_eval.within_scope and final != FinalResolution.DENY:
            final = FinalResolution.ALLOW

    scope_fields = {
        "within_scope": scope_eval.within_scope if scope_eval else False,
        "scope_id": scope_eval.scope_id if scope_eval else None,
        "escalation_reason": scope_eval.escalation_reason if scope_eval else None,
    }

    # Apply execution controls (only for ALLOW/ESCALATE — DENY skips)
    if final != FinalResolution.DENY:
        ec = apply_execution_controls(role, intent, risk_level, final)
        return PermissionDecision(
            final_resolution=final,
            execution_mode=execution_mode,
            origin=origin,
            tool_policy_decision=tool_decision,
            constraint_evaluated=True,
            constraint_result=constraint.result,
            constraint_type=constraint.constraint_type,
            constraint_reason=constraint.reason,
            execution_control_applied=True,
            execution_control_type=ec.control_type.value,
            execution_control_reason=ec.control_reason,
            rewritten_command=ec.rewritten_command,
            timeout_seconds=ec.timeout_seconds,
            execution_controls_applied=ec.controls_applied,
            **scope_fields,
        )

    # DENY from constraint composition — no execution control
    return PermissionDecision(
        final_resolution=final,
        execution_mode=execution_mode,
        origin=origin,
        tool_policy_decision=tool_decision,
        constraint_evaluated=True,
        constraint_result=constraint.result,
        constraint_type=constraint.constraint_type,
        constraint_reason=constraint.reason,
        **scope_fields,
    )


def should_surface_permission(
    session_name: str,
    intent: PermissionIntent | None = None,
    risk_level: RiskLevel | None = None,
    task_id: str = "",
) -> bool:
    """Quick check: should this session's permission events reach Discord?

    Returns True only for sessions that genuinely need operator approval.
    Autonomous background sessions return False for low/medium risk,
    True for high risk. Actions within an active execution scope
    return False (silent execution).
    """
    decision = resolve_permission(session_name, intent, risk_level, task_id)
    return decision.resolution == PermissionResolution.SURFACE_AND_WAIT


# ─── Event Type Classification ─────────────────────────────────────────────

# Map of (state_value) → EventVisibility.
# States not listed default to USER_FACING.
_EVENT_VISIBILITY: dict[str, EventVisibility] = {
    "complete": EventVisibility.USER_FACING,
    "plan_mode": EventVisibility.USER_FACING,
    "permission_request": EventVisibility.USER_FACING,
    "waiting_question": EventVisibility.USER_FACING,
    "idle": EventVisibility.INTERNAL_ONLY,
    "responding": EventVisibility.INTERNAL_ONLY,
    "working": EventVisibility.INTERNAL_ONLY,
}


def get_event_visibility(state_value: str) -> EventVisibility:
    """Determine if an event state should reach Discord."""
    return _EVENT_VISIBILITY.get(state_value, EventVisibility.USER_FACING)


def should_show_in_discord(state_value: str) -> bool:
    """Quick check: should this event state be shown in Discord?"""
    vis = get_event_visibility(state_value)
    return vis == EventVisibility.USER_FACING


# ─── Message Formatting ───────────────────────────────────────────────────


def format_completion_header(session_name: str, text: str) -> str:
    """Format a clean completion header for a session."""
    display = get_display_name(session_name)
    return f"✅ **{display} completed:**"


def format_permission_request(session_name: str, text: str) -> str:
    """Format a clean permission request message."""
    display = get_display_name(session_name)
    return f"🔐 **{display} needs permission:**\n```\n{text}\n```"


def format_permission_granted(session_name: str) -> str:
    """Format permission granted confirmation."""
    display = get_display_name(session_name)
    return f"✅ **{display} permission granted.**"


def format_permission_denied(session_name: str) -> str:
    """Format permission denied confirmation."""
    display = get_display_name(session_name)
    return f"❌ **{display} permission denied.**"


def format_plan_approved(session_name: str) -> str:
    """Format plan approved confirmation."""
    display = get_display_name(session_name)
    return f"✅ **{display} plan approved.**"


def format_plan_rejected(session_name: str) -> str:
    """Format plan rejected confirmation."""
    display = get_display_name(session_name)
    return f"❌ **{display} plan rejected.**"


def format_plan_editing(session_name: str) -> str:
    """Format plan editing instruction."""
    display = get_display_name(session_name)
    return (
        f"✏️ **Editing {display} plan**\n"
        f"Reply with `!answer {session_name} <your instructions>`"
    )


def format_question(session_name: str, text: str) -> str:
    """Format a question from a session."""
    display = get_display_name(session_name)
    return f"🤔 **{display} is asking:**\n```\n{text}\n```"


def format_question_with_answer_hint(session_name: str, text: str) -> str:
    """Format a question with answer instructions."""
    display = get_display_name(session_name)
    return (
        f"🤔 **{display} is asking:**\n"
        f"```\n{text}\n```\n"
        f"*Reply with* `!answer {session_name} <your response>`"
    )


def format_option_selected(session_name: str, label: str) -> str:
    """Format option selection confirmation."""
    display = get_display_name(session_name)
    return f"Selected: **{label}** for {display}"


def format_plan_proposal(session_name: str, text: str) -> str:
    """Format a plan proposal."""
    display = get_display_name(session_name)
    return f"📋 **{display} proposes a plan:**\n```\n{text}\n```"


def format_answer_sent(session_name: str, answer_preview: str) -> str:
    """Format confirmation that an answer was sent."""
    display = get_display_name(session_name)
    return f"Sent to {display}: {answer_preview}"


def format_no_watcher(session_name: str) -> str:
    """Format error when no watcher exists."""
    display = get_display_name(session_name)
    return f"No active watcher for {display}"


__all__ = [
    "DisplayIdentity",
    "EventVisibility",
    "ExecutionMode",
    "FinalResolution",
    "IntentType",
    "PermissionDecision",
    "PermissionIntent",
    "PermissionOrigin",
    "PermissionResolution",
    "RiskLevel",
    "ToolPolicyDecision",
    "classify_permission_origin",
    "classify_risk",
    "clean_for_discord",
    "extract_final_answer",
    "extract_intent",
    "filter_noise",
    "filter_reasoning",
    "format_answer_sent",
    "format_completion_header",
    "format_no_watcher",
    "format_option_selected",
    "format_permission_denied",
    "format_permission_granted",
    "format_permission_request",
    "format_plan_approved",
    "format_plan_editing",
    "format_plan_proposal",
    "format_plan_rejected",
    "format_question",
    "format_question_with_answer_hint",
    "get_display_identity",
    "get_display_name",
    "get_event_visibility",
    "hard_drop_filter",
    "resolve_permission",
    "resolve_tool_policy",
    "sanitize_session_names",
    "should_show_in_discord",
    "should_surface_permission",
]
