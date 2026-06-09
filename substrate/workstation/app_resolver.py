"""Native app resolver — Chrome-first browser policy, app vs website classification.

Deterministic resolution of operator app references to native launches vs
browser opens.  Uses PLATFORM_PROCESS_MAP from the environment mapping engine
as the ground truth for known apps.  No LLM dependency.

Chrome-first rule: web targets ALWAYS use Chrome.  Never Edge, never Explorer,
never the OS default browser.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


def _get_platform_process_map() -> dict[str, dict[str, str]]:
    """Runtime import of PLATFORM_PROCESS_MAP to avoid circular imports."""
    try:
        from substrate.execution.workers.workstation.environment_mapping_engine_v1 import (
            PLATFORM_PROCESS_MAP,
        )

        return PLATFORM_PROCESS_MAP
    except Exception:
        return {}


# Keys in PLATFORM_PROCESS_MAP that have real desktop processes.
# "chrome" is excluded — it IS the browser, not a native app target.
_NATIVE_APP_KEYS: frozenset[str] = frozenset(
    {
        "spotify",
        "discord",
        "slack",
        "code",
        "cursor",
        "obsidian",
        "notion",
        "steam",
        "explorer",
        "windowsterminal",
        "powershell",
        "github",
        "claude",
        "docker",
    }
)

_VERB_PREFIXES: list[str] = [
    "open ",
    "launch ",
    "pull up ",
    "start ",
    "search for ",
    "look up ",
    "find ",
    "go to ",
    "browse ",
]

_SEARCH_PATTERNS: list[str] = [
    "search for ",
    "look up ",
    "find ",
    "google ",
]


@dataclass
class AppTarget:
    """Resolved application target for workstation commands."""

    app_key: str
    display_name: str
    is_native: bool
    process_name: str
    launch_cmd: Optional[str]
    open_url: Optional[str]
    browser: str
    domain: str

    def to_dict(self) -> dict[str, object]:
        return {
            "app_key": self.app_key,
            "display_name": self.display_name,
            "is_native": self.is_native,
            "process_name": self.process_name,
            "launch_cmd": self.launch_cmd,
            "open_url": self.open_url,
            "browser": self.browser,
            "domain": self.domain,
        }


def _strip_verb_prefix(text: str) -> str:
    """Remove common verb prefixes from operator text."""
    t = text.lower().strip()
    for prefix in _VERB_PREFIXES:
        if t.startswith(prefix):
            return t[len(prefix) :].strip()
    return t


def classify_app_vs_website(text: str) -> str:
    """Classify operator text as native_app, website, or unknown.

    Deterministic keyword matching — no LLM.

    Returns:
        "native_app" | "website" | "unknown"
    """
    t = text.lower().strip()
    remainder = _strip_verb_prefix(t)

    # Check if remainder matches a known native app key
    pmap = _get_platform_process_map()
    if remainder in _NATIVE_APP_KEYS and remainder in pmap:
        return "native_app"

    # Also check against display names in the map
    for key, entry in pmap.items():
        if key in _NATIVE_APP_KEYS and entry.get("name", "").lower() == remainder:
            return "native_app"

    # Search/browse patterns indicate website
    web_indicators = ["search", "browse", "look up", "find on", "go to"]
    if any(ind in t for ind in web_indicators):
        return "website"

    # Domain-like pattern (contains a dot)
    if "." in remainder and " " not in remainder:
        return "website"

    return "unknown"


def resolve_app_target(name: str) -> AppTarget:
    """Resolve a name to a concrete app target for launch/open.

    Chrome-first rule: browser field is ALWAYS 'chrome' for web targets.
    Never edge. Never explorer.

    Args:
        name: App key or display name (e.g. 'spotify', 'reddit', 'code')

    Returns:
        AppTarget with resolution details.
    """
    normalized = name.lower().strip()
    pmap = _get_platform_process_map()

    entry = pmap.get(normalized)

    # Also search by display name if not found by key
    if entry is None:
        for key, val in pmap.items():
            if val.get("name", "").lower() == normalized:
                entry = val
                normalized = key
                break

    if entry is not None and normalized in _NATIVE_APP_KEYS:
        # Native app — launch directly, no URL
        process = entry.get("process", "")
        return AppTarget(
            app_key=normalized,
            display_name=entry.get("name", normalized),
            is_native=True,
            process_name=process,
            launch_cmd=f"start {process}",
            open_url=None,
            browser="",
            domain=entry.get("domain", ""),
        )

    if entry is not None:
        # Known in map but not a native app (e.g. "chrome" itself)
        domain = entry.get("domain", "")
        url = f"https://{domain}" if domain and domain != "terminal" and domain != "local" else None
        return AppTarget(
            app_key=normalized,
            display_name=entry.get("name", normalized),
            is_native=False,
            process_name=entry.get("process", ""),
            launch_cmd=None,
            open_url=url,
            browser="chrome",
            domain=domain,
        )

    # Unknown app — treat as website, Chrome-first
    url = None
    if normalized.isalpha() and len(normalized) <= 30:
        url = f"https://{normalized}.com"

    return AppTarget(
        app_key=normalized,
        display_name=normalized,
        is_native=False,
        process_name="",
        launch_cmd=None,
        open_url=url,
        browser="chrome",
        domain=f"{normalized}.com" if normalized.isalpha() else "",
    )


def resolve_search_url(text: str) -> Optional[str]:
    """Extract search query and return a Google search URL if applicable.

    Args:
        text: Operator text like "search for python tutorials"

    Returns:
        Google search URL or None if text is not a search query.
    """
    t = text.lower().strip()
    for pattern in _SEARCH_PATTERNS:
        if t.startswith(pattern):
            query = t[len(pattern) :].strip()
            if query:
                return f"https://www.google.com/search?q={quote_plus(query)}"
    return None
