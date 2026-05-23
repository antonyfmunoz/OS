"""Browser Operational Modes v1.

Defines operational modes that constrain browser and GUI capabilities.
Each mode specifies allowed actions, navigation scope, governance
thresholds, observability requirements, and screenshot requirements.

Modes:
  inspection_mode          — read-only browser/GUI inspection, no navigation
  research_mode            — approved external URL viewing, no mutation
  internal_navigation_mode — local/internal URL navigation, no external
  restricted_execution_mode — controlled visible actions on approved targets

UMH substrate subsystem. Phase 96.8BQ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .browser_gui_contracts_v1 import (
    BrowserActionType,
    BrowserOperationalMode,
    NavigationScope,
)


_INSPECT_ACTIONS = frozenset(
    {
        BrowserActionType.INSPECT_TABS,
        BrowserActionType.INSPECT_URL,
        BrowserActionType.INSPECT_DOM,
        BrowserActionType.WINDOW_INSPECT,
        BrowserActionType.UI_STATE_INSPECT,
        BrowserActionType.SCREENSHOT,
    }
)

_RESEARCH_ACTIONS = _INSPECT_ACTIONS | frozenset(
    {
        BrowserActionType.DOCUMENT_INSPECT,
    }
)

_NAVIGATION_ACTIONS = _RESEARCH_ACTIONS | frozenset(
    {
        BrowserActionType.NAVIGATE,
        BrowserActionType.SCROLL,
        BrowserActionType.WINDOW_FOCUS,
    }
)

_RESTRICTED_ACTIONS = _NAVIGATION_ACTIONS


@dataclass
class BrowserModeDefinition:
    """Complete definition of a browser operational mode."""

    mode: BrowserOperationalMode
    display_name: str
    description: str
    allowed_actions: frozenset[BrowserActionType] = field(default_factory=frozenset)
    navigation_scope: NavigationScope = NavigationScope.NONE
    allowed_domains: frozenset[str] = field(default_factory=frozenset)
    max_action_timeout: int = 15
    require_screenshot: bool = False
    require_visibility_confirmation: bool = False
    governance_threshold: str = "strict"
    allow_dom_mutation: bool = False
    allow_form_interaction: bool = False
    allow_external_navigation: bool = False

    def allows_action(self, action_type: BrowserActionType) -> bool:
        return action_type in self.allowed_actions

    def allows_navigation_to(self, url: str) -> bool:
        if self.navigation_scope == NavigationScope.NONE:
            return False
        if self.navigation_scope == NavigationScope.LOCAL_ONLY:
            return _is_local_url(url)
        if self.navigation_scope == NavigationScope.INTERNAL_ONLY:
            return _is_local_url(url) or _is_internal_url(url)
        if self.navigation_scope == NavigationScope.APPROVED_EXTERNAL:
            return (
                _is_local_url(url)
                or _is_internal_url(url)
                or _is_approved_domain(url, self.allowed_domains)
            )
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "display_name": self.display_name,
            "description": self.description,
            "allowed_actions": sorted(a.value for a in self.allowed_actions),
            "navigation_scope": self.navigation_scope.value,
            "allowed_domains": sorted(self.allowed_domains),
            "max_action_timeout": self.max_action_timeout,
            "require_screenshot": self.require_screenshot,
            "require_visibility_confirmation": self.require_visibility_confirmation,
            "governance_threshold": self.governance_threshold,
            "allow_dom_mutation": self.allow_dom_mutation,
            "allow_form_interaction": self.allow_form_interaction,
            "allow_external_navigation": self.allow_external_navigation,
        }


# ---------------------------------------------------------------------------
# URL classification helpers
# ---------------------------------------------------------------------------

_LOCAL_PREFIXES = (
    "http://localhost",
    "http://127.0.0.1",
    "https://localhost",
    "https://127.0.0.1",
    "http://0.0.0.0",
    "file://",
)

_INTERNAL_PREFIXES = (
    "http://100.",
    "https://100.",
    "http://10.",
    "https://10.",
    "http://192.168.",
    "https://192.168.",
)


def _is_local_url(url: str) -> bool:
    return any(url.startswith(p) for p in _LOCAL_PREFIXES)


def _is_internal_url(url: str) -> bool:
    return any(url.startswith(p) for p in _INTERNAL_PREFIXES)


def _is_approved_domain(url: str, allowed_domains: frozenset[str]) -> bool:
    if not allowed_domains:
        return False
    for domain in allowed_domains:
        if f"://{domain}" in url or f".{domain}" in url:
            return True
    return False


# ---------------------------------------------------------------------------
# Mode definitions
# ---------------------------------------------------------------------------

INSPECTION_MODE = BrowserModeDefinition(
    mode=BrowserOperationalMode.INSPECTION,
    display_name="Inspection Mode",
    description="Read-only browser/GUI inspection, no navigation",
    allowed_actions=_INSPECT_ACTIONS,
    navigation_scope=NavigationScope.NONE,
    max_action_timeout=10,
    require_screenshot=False,
    require_visibility_confirmation=False,
    governance_threshold="strict",
    allow_dom_mutation=False,
    allow_form_interaction=False,
    allow_external_navigation=False,
)

RESEARCH_MODE = BrowserModeDefinition(
    mode=BrowserOperationalMode.RESEARCH,
    display_name="Research Mode",
    description="Approved external URL viewing, read-only document inspection",
    allowed_actions=_RESEARCH_ACTIONS,
    navigation_scope=NavigationScope.APPROVED_EXTERNAL,
    allowed_domains=frozenset(
        {
            "github.com",
            "docs.python.org",
            "developer.mozilla.org",
            "stackoverflow.com",
            "pypi.org",
            "npmjs.com",
        }
    ),
    max_action_timeout=20,
    require_screenshot=False,
    require_visibility_confirmation=False,
    governance_threshold="standard",
    allow_dom_mutation=False,
    allow_form_interaction=False,
    allow_external_navigation=True,
)

INTERNAL_NAVIGATION_MODE = BrowserModeDefinition(
    mode=BrowserOperationalMode.INTERNAL_NAVIGATION,
    display_name="Internal Navigation Mode",
    description="Local and internal network URL navigation, no external access",
    allowed_actions=_NAVIGATION_ACTIONS,
    navigation_scope=NavigationScope.INTERNAL_ONLY,
    max_action_timeout=15,
    require_screenshot=True,
    require_visibility_confirmation=True,
    governance_threshold="standard",
    allow_dom_mutation=False,
    allow_form_interaction=False,
    allow_external_navigation=False,
)

RESTRICTED_EXECUTION_MODE = BrowserModeDefinition(
    mode=BrowserOperationalMode.RESTRICTED_EXECUTION,
    display_name="Restricted Execution Mode",
    description="Controlled visible actions on approved internal targets",
    allowed_actions=_RESTRICTED_ACTIONS,
    navigation_scope=NavigationScope.INTERNAL_ONLY,
    max_action_timeout=30,
    require_screenshot=True,
    require_visibility_confirmation=True,
    governance_threshold="maximum",
    allow_dom_mutation=False,
    allow_form_interaction=False,
    allow_external_navigation=False,
)

BROWSER_MODE_REGISTRY: dict[BrowserOperationalMode, BrowserModeDefinition] = {
    BrowserOperationalMode.INSPECTION: INSPECTION_MODE,
    BrowserOperationalMode.RESEARCH: RESEARCH_MODE,
    BrowserOperationalMode.INTERNAL_NAVIGATION: INTERNAL_NAVIGATION_MODE,
    BrowserOperationalMode.RESTRICTED_EXECUTION: RESTRICTED_EXECUTION_MODE,
}


def get_browser_mode_definition(mode: BrowserOperationalMode) -> BrowserModeDefinition:
    return BROWSER_MODE_REGISTRY[mode]


def get_all_browser_modes() -> list[BrowserModeDefinition]:
    return list(BROWSER_MODE_REGISTRY.values())
