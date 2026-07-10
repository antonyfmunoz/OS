"""HTTP client for UMH API — transport layer, no substrate imports."""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Raised on non-2xx HTTP responses with structured detail."""

    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"HTTP {status}: {detail}")


class UMHClient:
    """Synchronous HTTP client for UMH API."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (
            base_url
            or os.environ.get("UMH_API_URL")
            or "http://localhost:8000/api/umh"
        )
        self.api_key = api_key or os.environ.get("UMH_API_KEY", "")
        self._conversation_id = ""
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers=self._build_headers(),
        )

    def _build_headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        return h

    def _request(self, method: str, path: str, **kwargs) -> dict | list:
        """Central request handler with structured error handling."""
        try:
            r = self._client.request(method, path, **kwargs)
        except httpx.ConnectError:
            raise APIError(0, f"Connection refused — is the API running at {self.base_url}?")
        except httpx.ConnectTimeout:
            raise APIError(0, f"Connection timed out — {self.base_url} not reachable")
        except httpx.ReadTimeout:
            raise APIError(0, "Request timed out — API may be overloaded")

        if r.status_code == 401:
            raise APIError(401, "Authentication failed — check UMH_API_KEY")
        if r.status_code == 403:
            raise APIError(403, "Forbidden — insufficient permissions")

        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text[:200])
            except Exception:
                detail = r.text[:200] or f"status {r.status_code}"
            raise APIError(r.status_code, str(detail))

        try:
            return r.json()
        except Exception:
            raise APIError(0, "Invalid JSON response from API")

    def ping(self) -> dict:
        """GET /pulse — connection test + system health."""
        result = self._request("GET", "/pulse")
        return result if isinstance(result, dict) else {}

    def converse(self, content: str, media: list[dict] | None = None) -> dict:
        """POST /advisor/converse — chat with advisor.

        ``media`` is a list of MediaAttachment descriptors (from ``upload_media``)
        whose CONTENT the assistant understands — image/video/pdf via free Gemini
        vision, audio via local Whisper. Same seam as browser/desktop/mobile.
        """
        payload: dict = {
            "content": content,
            "conversation_id": self._conversation_id,
            "source": "cli",
        }
        if media:
            payload["media"] = media
        data = self._request("POST", "/advisor/converse", json=payload)
        if isinstance(data, dict) and data.get("conversation_id"):
            self._conversation_id = data["conversation_id"]
        return data if isinstance(data, dict) else {}

    def upload_media(self, path: str) -> dict | None:
        """Upload a local file to /chat/upload and return its MediaAttachment dict.

        Reuses the SAME upload seam the cockpit uses, so a CLI attachment is
        understood by the assistant identically to a browser one
        (image/video/audio/pdf/file).
        """
        import mimetypes
        import os as _os

        if not _os.path.isfile(path):
            return None
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        fname = _os.path.basename(path)
        try:
            with open(path, "rb") as fh:
                # multipart upload — do NOT send the JSON content-type header
                r = self._client.post(
                    "/chat/upload",
                    files={"file": (fname, fh, ctype)},
                    headers={k: v for k, v in self._build_headers().items() if k != "Content-Type"},
                )
            if r.status_code != 200:
                return None
            return r.json()
        except Exception:
            return None

    def history(self, limit: int = 20) -> list:
        """GET /advisor/history — recent messages."""
        result = self._request("GET", "/advisor/history", params={"limit": limit})
        return result if isinstance(result, list) else []

    def agents(self) -> list:
        """GET /agents — agent list."""
        result = self._request("GET", "/agents")
        return result if isinstance(result, list) else []

    def loops(self) -> list:
        """GET /loops — loop status."""
        result = self._request("GET", "/loops")
        return result if isinstance(result, list) else []

    def execution_overview(self) -> dict:
        """GET /execution/overview — execution status."""
        result = self._request("GET", "/execution/overview")
        return result if isinstance(result, dict) else {}

    def approvals(self) -> list:
        """GET /approvals/pending — pending approvals."""
        result = self._request("GET", "/approvals/pending")
        return result if isinstance(result, list) else []

    def nodes(self) -> list:
        """GET /mesh/nodes — mesh node list."""
        result = self._request("GET", "/mesh/nodes")
        return result if isinstance(result, list) else []

    def providers_health(self) -> dict:
        """GET /providers/health — model provider status."""
        result = self._request("GET", "/providers/health")
        return result if isinstance(result, dict) else {}

    def close(self) -> None:
        self._client.close()
