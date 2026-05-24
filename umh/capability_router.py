"""Capability invocation — deterministic pattern matching for local actions.

Detects capability-invocable commands in user input using keyword/regex
matching (no LLM). Routes through WorkstationCapabilityHandler with
properly constructed CapabilityRequest objects.

Supported patterns:
  "open <url>"              -> open_url
  "read clipboard"          -> clipboard_read
  "copy <text>"             -> clipboard_write
  "system info" / "sysinfo" -> system_info
  "say <text>"              -> speak_text
  "run <command>"           -> shell_execute

UMH workstation subsystem.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_CAPABILITY_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"^open\s+(https?://\S+)$", re.I), "open_url", "url"),
    (re.compile(r"^read\s+clipboard$", re.I), "clipboard_read", ""),
    (re.compile(r"^clipboard$", re.I), "clipboard_read", ""),
    (re.compile(r"^copy\s+(.+)$", re.I), "clipboard_write", "text"),
    (re.compile(r"^system\s+info$", re.I), "system_info", ""),
    (re.compile(r"^sysinfo$", re.I), "system_info", ""),
    (re.compile(r"^say\s+(.+)$", re.I), "speak_text", "text"),
    (re.compile(r"^run\s+(.+)$", re.I), "shell_execute", "command"),
]


def match_capability(text: str) -> tuple[str, dict[str, Any]] | None:
    """Match user input against capability patterns.

    Returns (capability_name, params) or None if no match.
    """
    text = text.strip()
    for pattern, capability_name, param_key in _CAPABILITY_PATTERNS:
        m = pattern.match(text)
        if m:
            params: dict[str, Any] = {}
            if param_key and m.lastindex and m.lastindex >= 1:
                params[param_key] = m.group(1)
            return (capability_name, params)
    return None


def invoke_capability(
    text: str,
    handler: Any = None,
) -> str | None:
    """Try to match and invoke a capability from user input.

    Returns response string if matched, None if no match.
    """
    matched = match_capability(text)
    if matched is None:
        return None

    capability_name, params = matched

    if handler is None:
        handler = _get_handler()
    if handler is None:
        return f"Capability '{capability_name}' matched but handler not available."

    try:
        from substrate.sockets.envelopes import CapabilityRequest

        request = CapabilityRequest(
            request_id=uuid4(),
            capability_name=capability_name,
            integration_id="workstation_local",
            params=params,
            governance_verdict_id=uuid4(),
            trace_id=uuid4(),
        )
        response = handler.handle_capability(request)

        if response.success:
            return _format_success(capability_name, response.result_data)
        return f"Capability '{capability_name}' failed: {response.error}"

    except ImportError:
        return _execute_fallback(capability_name, params)
    except Exception as exc:
        logger.debug("Capability invocation failed: %s", exc)
        return f"Capability error: {exc}"


_cached_handler: Any = None


def _get_handler() -> Any:
    """Lazy-load and cache the WorkstationCapabilityHandler."""
    global _cached_handler
    if _cached_handler is not None:
        return _cached_handler
    try:
        from umh.transport import WorkstationCapabilityHandler

        _cached_handler = WorkstationCapabilityHandler()
        return _cached_handler
    except ImportError:
        return None


def clear_module_state() -> None:
    """Reset cached handler for session teardown."""
    global _cached_handler
    _cached_handler = None


def _execute_fallback(capability_name: str, params: dict[str, Any]) -> str:
    """Execute capability without substrate CapabilityRequest envelope."""
    handler = _get_handler()
    if handler is None:
        return f"Capability handler not available for '{capability_name}'."

    handler_map = {
        "speak_text": handler._handle_speak,
        "shell_execute": handler._handle_shell,
        "open_url": handler._handle_open_url,
        "clipboard_read": handler._handle_clipboard_read,
        "clipboard_write": handler._handle_clipboard_write,
        "system_info": handler._handle_system_info,
    }

    fn = handler_map.get(capability_name)
    if fn is None:
        return f"No handler for capability '{capability_name}'."

    try:
        result = fn(params)
        return _format_success(capability_name, result)
    except Exception as exc:
        return f"Capability '{capability_name}' failed: {exc}"


def _format_success(capability_name: str, result: dict[str, Any]) -> str:
    """Format a successful capability result for display."""
    if capability_name == "open_url":
        url = result.get("url", "")
        if result.get("opened"):
            return f"Opened: {url}"
        return f"Failed to open URL: {result.get('reason', 'unknown')}"

    if capability_name == "clipboard_read":
        content = result.get("content", "")
        if content:
            preview = content[:200]
            if len(content) > 200:
                preview += "..."
            return f"Clipboard: {preview}"
        return "Clipboard is empty."

    if capability_name == "clipboard_write":
        if result.get("written"):
            return "Copied to clipboard."
        return f"Clipboard write failed: {result.get('error', 'unknown')}"

    if capability_name == "system_info":
        parts = []
        if result.get("platform"):
            parts.append(f"OS: {result['platform']}")
        if result.get("hostname"):
            parts.append(f"Host: {result['hostname']}")
        if result.get("cpu_percent") is not None:
            parts.append(f"CPU: {result['cpu_percent']}%")
        if result.get("memory_percent") is not None:
            parts.append(f"Memory: {result['memory_percent']}%")
        if result.get("disk_percent") is not None:
            parts.append(f"Disk: {result['disk_percent']}%")
        return " | ".join(parts) if parts else str(result)

    if capability_name == "speak_text":
        if result.get("spoken"):
            return f"Spoke: {result.get('text', '')[:80]}"
        return f"TTS failed: {result.get('reason', 'unknown')}"

    if capability_name == "shell_execute":
        exit_code = result.get("exit_code", -1)
        stdout = result.get("stdout", "").strip()
        stderr = result.get("stderr", "").strip()
        output = stdout or stderr
        if output:
            preview = output[:500]
            if len(output) > 500:
                preview += "..."
            return f"[exit {exit_code}]\n{preview}"
        return f"[exit {exit_code}]"

    return str(result)


def list_capabilities() -> list[dict[str, str]]:
    """List available capability patterns for help display."""
    return [
        {"pattern": "open <url>", "capability": "open_url", "description": "Open URL in browser"},
        {
            "pattern": "read clipboard",
            "capability": "clipboard_read",
            "description": "Read clipboard contents",
        },
        {
            "pattern": "copy <text>",
            "capability": "clipboard_write",
            "description": "Copy text to clipboard",
        },
        {
            "pattern": "system info",
            "capability": "system_info",
            "description": "Show system metrics",
        },
        {"pattern": "say <text>", "capability": "speak_text", "description": "Speak text via TTS"},
        {
            "pattern": "run <command>",
            "capability": "shell_execute",
            "description": "Execute shell command",
        },
    ]


def show_capabilities() -> int:
    """Display available capabilities for CLI."""
    print()
    print("Local Capabilities")
    print("=" * 40)

    caps = list_capabilities()
    for cap in caps:
        print(f"  {cap['pattern']:<25s} — {cap['description']}")

    handler = _get_handler()
    if handler is not None:
        try:
            health = handler.health()
            print(f"\n  Status: {health.status}")
        except Exception:
            pass

    print()
    return 0
