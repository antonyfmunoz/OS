"""Hermes adapter — wraps Hermes CLI on the Beast machine.

Hermes is a model-agnostic agent that routes to whatever provider
is configured inside it (OpenRouter, OpenAI, Ollama, etc.).
This adapter runs on Beast where the hermes binary actually exists.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)

_ERROR_SIGNATURES = (
    "autherror",
    "no inference provider configured",
    "rate limit",
    "api key",
    "authentication",
    "billing",
    "quota",
)


def _is_error_leak(content: str) -> bool:
    lowered = content.lower()
    return any(sig in lowered for sig in _ERROR_SIGNATURES)


class HermesAdapter:
    """Executes Hermes CLI commands on Beast."""

    def __init__(self) -> None:
        self._available = shutil.which("hermes") is not None

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._available:
            return {"success": False, "error": "hermes binary not found on PATH"}

        if operation == "hermes.generate":
            return self._generate(params)
        elif operation == "hermes.probe":
            return self._probe()
        elif operation == "hermes.info":
            return self._info()
        else:
            return {"success": False, "error": f"unknown operation: {operation}"}

    def _generate(self, params: dict[str, Any]) -> dict[str, Any]:
        prompt = params.get("prompt", "")
        timeout = params.get("timeout", 120)

        if not prompt:
            return {"success": False, "error": "no prompt provided"}

        start = time.monotonic()
        try:
            result = subprocess.run(
                ["hermes", "-z", prompt],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            output = result.stdout.strip()

            if result.returncode != 0:
                stderr = result.stderr.strip()[:500]
                return {
                    "success": False,
                    "error": f"hermes exited {result.returncode}: {stderr}",
                    "latency_ms": elapsed_ms,
                }

            if not output or _is_error_leak(output):
                return {
                    "success": False,
                    "error": "hermes returned error or empty output",
                    "latency_ms": elapsed_ms,
                }

            return {
                "success": True,
                "output": output[:10000],
                "latency_ms": elapsed_ms,
                "provider": "hermes",
            }
        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return {
                "success": False,
                "error": f"hermes timed out after {timeout}s",
                "latency_ms": elapsed_ms,
            }
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return {
                "success": False,
                "error": f"{type(exc).__name__}: {exc}",
                "latency_ms": elapsed_ms,
            }

    def _probe(self) -> dict[str, Any]:
        return self._generate({"prompt": "Respond with exactly: HERMES_OK", "timeout": 30})

    def _info(self) -> dict[str, Any]:
        """Return configured provider name without leaking secrets."""
        try:
            result = subprocess.run(
                ["hermes", "config", "get", "provider"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            provider = result.stdout.strip() if result.returncode == 0 else "unknown"
            for sig in ("key", "token", "secret", "password"):
                if sig in provider.lower():
                    provider = "redacted"
                    break
            return {"success": True, "provider": provider}
        except Exception:
            return {"success": True, "provider": "unknown"}
