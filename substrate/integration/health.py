"""Health aggregator — dashboard endpoint combining all service health signals.

Checks backend API, frontend dev server, existing operator services,
and Ollama availability in one call.
"""

from __future__ import annotations

import os
import time
from typing import Any

import urllib.request
import json


BACKEND_URL = os.environ.get("UMH_BACKEND_URL", "http://localhost:8093")
FRONTEND_URL = os.environ.get("UMH_FRONTEND_URL", "http://localhost:5173")
OPERATOR_URL = os.environ.get("OPERATOR_API_URL", "http://localhost:8091")
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


def _probe(url: str, timeout: float = 3.0) -> dict[str, Any]:
    """HTTP GET with timeout. Returns status dict."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {"raw": body[:500]}
            return {"status": "up", "code": resp.status, "data": data}
    except urllib.error.HTTPError as e:
        return {"status": "error", "code": e.code, "error": str(e.reason)}
    except Exception as e:
        return {"status": "down", "error": str(e)}


class HealthAggregator:
    """Aggregates health from all UMH-related services."""

    def __init__(
        self,
        backend_url: str = BACKEND_URL,
        frontend_url: str = FRONTEND_URL,
        operator_url: str = OPERATOR_URL,
        ollama_url: str = OLLAMA_URL,
    ) -> None:
        self._backend = backend_url
        self._frontend = frontend_url
        self._operator = operator_url
        self._ollama = ollama_url

    def check_all(self) -> dict[str, Any]:
        """Run all health checks and return aggregated result."""
        checks = {
            "backend": _probe(f"{self._backend}/api/umh/health"),
            "frontend": _probe(self._frontend),
            "operator_api": _probe(f"{self._operator}/health"),
            "ollama": _probe(f"{self._ollama}/api/tags"),
        }

        all_up = all(c["status"] == "up" for c in checks.values())
        critical_up = checks["backend"]["status"] == "up"

        return {
            "timestamp": int(time.time()),
            "healthy": all_up,
            "critical_healthy": critical_up,
            "services": checks,
        }

    def check_backend(self) -> dict[str, Any]:
        return _probe(f"{self._backend}/api/umh/health")

    def check_frontend(self) -> dict[str, Any]:
        return _probe(self._frontend)

    def check_ollama(self) -> dict[str, Any]:
        return _probe(f"{self._ollama}/api/tags")
