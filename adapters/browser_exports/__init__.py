"""Browser export adapters — autonomous data export from web services.

Provides deterministic Playwright scripts to trigger data exports from
Claude, ChatGPT, and Instagram using persistent browser profiles.

Usage:
    from adapters.browser_exports import (
        ExportRequest, ExportResult, ProfileManager,
        trigger_claude_export, trigger_chatgpt_export,
        trigger_instagram_export,
    )
"""

from adapters.browser_exports.contract import ExportRequest, ExportResult
from adapters.browser_exports.profile_manager import ProfileManager
from adapters.browser_exports.claude_export import trigger_claude_export
from adapters.browser_exports.chatgpt_export import trigger_chatgpt_export
from adapters.browser_exports.instagram_export import trigger_instagram_export

__all__ = [
    "ExportRequest",
    "ExportResult",
    "ProfileManager",
    "trigger_claude_export",
    "trigger_chatgpt_export",
    "trigger_instagram_export",
]
