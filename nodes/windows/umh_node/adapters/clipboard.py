"""Clipboard adapter — read/write system clipboard."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ClipboardAdapter:
    """System clipboard access using pyperclip."""

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            import pyperclip
        except ImportError:
            return {"success": False, "error": "pyperclip not installed"}

        try:
            if operation == "clipboard.read":
                content = pyperclip.paste()
                return {"success": True, "content": content[:50000]}
            elif operation == "clipboard.write":
                text = params.get("text", "")
                pyperclip.copy(text)
                return {"success": True, "chars_written": len(text)}
            else:
                return {"success": False, "error": f"unknown operation: {operation}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
