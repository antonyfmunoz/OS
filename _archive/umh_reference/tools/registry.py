"""UMH Tool Registry — declares available tools and their properties.

Tools are typed definitions that map a high-level action name (e.g. "http_get")
to execution parameters: required inputs, domain allowlists, mutation flags,
and timeouts. The registry is the single source of truth for what tools exist
and how to validate requests against them.

Usage:
    from umh.tools.registry import get_tool, validate_tool_inputs, is_domain_allowed

    tool = get_tool("http_get")
    valid, err = validate_tool_inputs("http_get", {"url": "https://api.github.com/repos"})
    allowed = is_domain_allowed("https://api.github.com/repos", tool)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ALLOWED_DOMAINS: frozenset[str] = frozenset(
    {
        "api.github.com",
        "hooks.slack.com",
        "api.linear.app",
        "httpbin.org",
        "jsonplaceholder.typicode.com",
    }
)


# ---------------------------------------------------------------------------
# ToolDefinition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolDefinition:
    """Immutable declaration of a tool's interface and constraints."""

    name: str  # unique identifier (e.g. "http_get", "http_post", "webhook")
    operation: str  # maps to execution operation (e.g. "http_request")
    description: str  # human-readable
    required_inputs: list[str]  # required input keys
    optional_inputs: list[str] = field(default_factory=list)
    mutating: bool = False  # if True -> requires approval
    allowed_domains: frozenset[str] = frozenset()  # empty = use DEFAULT_ALLOWED_DOMAINS
    timeout_s: int = 30
    execution_class: str = "side_effect"


# ---------------------------------------------------------------------------
# Built-in tools
# ---------------------------------------------------------------------------

BUILT_IN_TOOLS: dict[str, ToolDefinition] = {
    "http_get": ToolDefinition(
        name="http_get",
        operation="http_request",
        description="Make an HTTP GET request",
        required_inputs=["url"],
        optional_inputs=["headers"],
        mutating=False,
        timeout_s=30,
    ),
    "http_post": ToolDefinition(
        name="http_post",
        operation="http_request",
        description="Make an HTTP POST request",
        required_inputs=["url"],
        optional_inputs=["headers", "body"],
        mutating=True,  # POST = mutation = requires approval
        timeout_s=30,
    ),
    "webhook": ToolDefinition(
        name="webhook",
        operation="http_request",
        description="Send a webhook notification",
        required_inputs=["url", "body"],
        optional_inputs=["headers"],
        mutating=True,
        timeout_s=15,
    ),
}

# Mutable registry — starts with built-ins, extensible via register_tool()
_TOOL_REGISTRY: dict[str, ToolDefinition] = dict(BUILT_IN_TOOLS)


# ---------------------------------------------------------------------------
# Registry API
# ---------------------------------------------------------------------------


def get_tool(name: str) -> ToolDefinition | None:
    """Look up a tool definition by name."""
    return _TOOL_REGISTRY.get(name)


def list_tools() -> list[ToolDefinition]:
    """Return all registered tool definitions."""
    return list(_TOOL_REGISTRY.values())


def register_tool(tool: ToolDefinition) -> None:
    """Register a custom tool definition.

    Overwrites any existing tool with the same name.
    """
    _TOOL_REGISTRY[tool.name] = tool
    _log.info("[ToolRegistry] registered tool '%s' (operation=%s)", tool.name, tool.operation)


def validate_tool_inputs(tool_name: str, inputs: dict) -> tuple[bool, str]:
    """Check whether inputs satisfy a tool's requirements.

    Returns:
        (True, "") if valid.
        (False, error_message) if tool not found or required inputs missing.
    """
    tool = get_tool(tool_name)
    if tool is None:
        return False, f"Unknown tool: {tool_name}"

    missing = [key for key in tool.required_inputs if key not in inputs]
    if missing:
        return False, f"Missing required inputs for '{tool_name}': {', '.join(missing)}"

    return True, ""


def is_domain_allowed(url: str, tool: ToolDefinition) -> bool:
    """Check whether a URL's hostname is in the tool's allowed domains.

    If the tool has explicit allowed_domains, use those.
    If allowed_domains is empty, fall back to DEFAULT_ALLOWED_DOMAINS.
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
    except Exception:
        _log.warning("[ToolRegistry] failed to parse URL for domain check: %r", url)
        return False

    if not hostname:
        return False

    domains = tool.allowed_domains if tool.allowed_domains else DEFAULT_ALLOWED_DOMAINS
    return hostname in domains
