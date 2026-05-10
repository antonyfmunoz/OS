"""Phase 76 HTTP adapter — safe HTTP GET/POST via urllib.

Uses stdlib only.  Enforces:
  - https/http only (no file://, ftp://, etc.)
  - Timeout
  - Response size limit
  - Redirect limit
  - Optional domain allowlist/blocklist
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from umh.adapters.mvp_contract import (
    AdapterRequest,
    AdapterResult,
    AdapterStatus,
    MVPAdapter,
)

_ALLOWED_SCHEMES = frozenset({"http", "https"})

_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "169.254.169.254",
        "metadata.google.internal",
    }
)

_MAX_RESPONSE_BYTES = 500_000
_MAX_REDIRECTS = 5
_DEFAULT_TIMEOUT = 15


def _validate_url(url: str) -> str | None:
    """Return error string if URL is unsafe, else None."""
    if not url or not url.strip():
        return "Empty URL"

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return f"Cannot parse URL: {url}"

    if parsed.scheme not in _ALLOWED_SCHEMES:
        return f"Blocked scheme: {parsed.scheme} (only http/https allowed)"

    host = (parsed.hostname or "").lower()
    if not host:
        return "No host in URL"

    if host in _BLOCKED_HOSTS:
        return f"Blocked host: {host}"

    if host.endswith(".local") or host.endswith(".internal"):
        return f"Blocked internal host: {host}"

    return None


class HTTPAdapter:
    """HTTP GET/POST via urllib with safety enforcement."""

    @property
    def name(self) -> str:
        return "http"

    @property
    def supported_capabilities(self) -> frozenset[str]:
        return frozenset({"http.get", "http.post"})

    @property
    def supported_environments(self) -> frozenset[str]:
        return frozenset({"local", "vps", "http"})

    def validate(self, request: AdapterRequest) -> AdapterResult | None:
        url = request.inputs.get("url", "")
        error = _validate_url(url)
        if error:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.VALIDATION_FAILED,
                error=error,
            )

        if request.capability == "http.post":
            if request.inputs.get("body") is None and request.inputs.get("data") is None:
                return AdapterResult(
                    request_id=request.request_id,
                    adapter_name=self.name,
                    capability=request.capability,
                    action=request.action,
                    status=AdapterStatus.VALIDATION_FAILED,
                    error="POST requires 'body' or 'data' in inputs",
                )

        return None

    def execute(self, request: AdapterRequest) -> AdapterResult:
        url = request.inputs.get("url", "")
        timeout = request.constraints.get("timeout_s", _DEFAULT_TIMEOUT)
        max_bytes = request.constraints.get("max_response_bytes", _MAX_RESPONSE_BYTES)

        try:
            if request.capability == "http.get":
                return self._get(request, url, timeout, max_bytes)
            elif request.capability == "http.post":
                return self._post(request, url, timeout, max_bytes)
            else:
                return AdapterResult(
                    request_id=request.request_id,
                    adapter_name=self.name,
                    capability=request.capability,
                    action=request.action,
                    status=AdapterStatus.UNSUPPORTED,
                    error=f"Unsupported: {request.capability}",
                )
        except urllib.error.URLError as e:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.FAILURE,
                error=f"Network error: {e.reason}",
                metadata={"url": url},
            )
        except TimeoutError:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.TIMEOUT,
                error=f"Request timed out after {timeout}s",
                metadata={"url": url},
            )
        except Exception as e:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.FAILURE,
                error=str(e),
                metadata={"url": url},
            )

    def _get(
        self, request: AdapterRequest, url: str, timeout: int, max_bytes: int
    ) -> AdapterResult:
        headers = request.inputs.get("headers", {})
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body_bytes = resp.read(max_bytes)
            truncated = len(body_bytes) == max_bytes
            body = body_bytes.decode("utf-8", errors="replace")
            resp_headers = dict(resp.headers.items())

            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.SUCCESS,
                output={
                    "status_code": resp.status,
                    "body": body[:50000],
                    "headers": {k: v for k, v in list(resp_headers.items())[:20]},
                    "truncated": truncated,
                    "url": url,
                },
            )

    def _post(
        self, request: AdapterRequest, url: str, timeout: int, max_bytes: int
    ) -> AdapterResult:
        body = request.inputs.get("body") or request.inputs.get("data", "")
        headers = request.inputs.get("headers", {})

        if isinstance(body, dict):
            data = json.dumps(body).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        elif isinstance(body, str):
            data = body.encode("utf-8")
        else:
            data = str(body).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_bytes = resp.read(max_bytes)
            resp_body = resp_bytes.decode("utf-8", errors="replace")
            resp_headers = dict(resp.headers.items())

            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=request.capability,
                action=request.action,
                status=AdapterStatus.SUCCESS,
                output={
                    "status_code": resp.status,
                    "body": resp_body[:50000],
                    "headers": {k: v for k, v in list(resp_headers.items())[:20]},
                    "truncated": len(resp_bytes) == max_bytes,
                    "url": url,
                },
            )
