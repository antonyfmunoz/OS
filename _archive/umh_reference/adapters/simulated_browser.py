"""Phase 76 simulated browser adapter — deterministic browser simulation.

No real browser automation.  Returns simulated results with
AdapterStatus.SIMULATED so callers know the data is synthetic.
Deterministic output seeded from input hash for reproducibility.
"""

from __future__ import annotations

import hashlib
from typing import Any

from umh.adapters.mvp_contract import (
    AdapterRequest,
    AdapterResult,
    AdapterStatus,
    MVPAdapter,
)

_BLOCKED_ACTIONS = frozenset(
    {
        "login",
        "submit_form",
        "purchase",
        "payment",
        "delete_account",
        "change_password",
        "oauth",
    }
)

_MAX_RESULTS = 10


def _seed_from(text: str) -> int:
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


class SimulatedBrowserAdapter:
    """Simulated browser — deterministic fake results, no real network."""

    @property
    def name(self) -> str:
        return "browser"

    @property
    def supported_capabilities(self) -> frozenset[str]:
        return frozenset({"browser.search", "browser.open", "browser.extract_text"})

    @property
    def supported_environments(self) -> frozenset[str]:
        return frozenset({"local", "browser", "simulation"})

    def validate(self, request: AdapterRequest) -> AdapterResult | None:
        cap = request.capability
        if cap not in self.supported_capabilities:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=cap,
                action=request.action,
                status=AdapterStatus.UNSUPPORTED,
                error=f"Unsupported capability: {cap}",
            )

        action = request.inputs.get("action", "")
        if action.lower() in _BLOCKED_ACTIONS:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=cap,
                action=request.action,
                status=AdapterStatus.DENIED,
                error=f"Blocked browser action: {action}",
            )

        if cap == "browser.search":
            query = request.inputs.get("query", "")
            if not query or not query.strip():
                return AdapterResult(
                    request_id=request.request_id,
                    adapter_name=self.name,
                    capability=cap,
                    action=request.action,
                    status=AdapterStatus.VALIDATION_FAILED,
                    error="Empty search query",
                )

        if cap in ("browser.open", "browser.extract_text"):
            url = request.inputs.get("url", "")
            if not url or not url.strip():
                return AdapterResult(
                    request_id=request.request_id,
                    adapter_name=self.name,
                    capability=cap,
                    action=request.action,
                    status=AdapterStatus.VALIDATION_FAILED,
                    error="No URL provided",
                )

        return None

    def execute(self, request: AdapterRequest) -> AdapterResult:
        cap = request.capability
        if cap == "browser.search":
            return self._search(request)
        elif cap == "browser.open":
            return self._open(request)
        elif cap == "browser.extract_text":
            return self._extract_text(request)
        else:
            return AdapterResult(
                request_id=request.request_id,
                adapter_name=self.name,
                capability=cap,
                action=request.action,
                status=AdapterStatus.UNSUPPORTED,
                error=f"Unsupported: {cap}",
            )

    def _search(self, request: AdapterRequest) -> AdapterResult:
        query = request.inputs.get("query", "")
        max_results = min(
            request.constraints.get("max_results", 5),
            _MAX_RESULTS,
        )
        seed = _seed_from(query)

        results = []
        for i in range(max_results):
            n = seed + i
            results.append(
                {
                    "title": f"Simulated result {i + 1} for: {query[:60]}",
                    "url": f"https://example.com/result/{n:08x}",
                    "snippet": f"This is a simulated search result for '{query[:40]}'. "
                    f"Result #{i + 1} of {max_results}.",
                }
            )

        return AdapterResult(
            request_id=request.request_id,
            adapter_name=self.name,
            capability=request.capability,
            action=request.action,
            status=AdapterStatus.SIMULATED,
            output={
                "query": query,
                "results": results,
                "result_count": len(results),
                "simulated": True,
            },
            observations=["Browser results are simulated — not from a real search engine"],
        )

    def _open(self, request: AdapterRequest) -> AdapterResult:
        url = request.inputs.get("url", "")
        seed = _seed_from(url)

        return AdapterResult(
            request_id=request.request_id,
            adapter_name=self.name,
            capability=request.capability,
            action=request.action,
            status=AdapterStatus.SIMULATED,
            output={
                "url": url,
                "title": f"Simulated page: {url[:80]}",
                "text_preview": f"Simulated page content for {url[:60]}. "
                f"Seed: {seed:08x}. "
                "This is not real page content.",
                "status_code": 200,
                "simulated": True,
            },
            observations=["Page content is simulated — not fetched from the real URL"],
        )

    def _extract_text(self, request: AdapterRequest) -> AdapterResult:
        url = request.inputs.get("url", "")
        seed = _seed_from(url)
        max_chars = request.constraints.get("max_chars", 5000)

        text = (
            f"Simulated text extraction from {url[:60]}.\n\n"
            f"This is deterministic simulated content (seed: {seed:08x}).\n"
            "The browser adapter does not perform real web requests.\n"
            "Replace with a real browser adapter for production use.\n\n"
            f"[Simulated content would continue up to {max_chars} characters]"
        )

        return AdapterResult(
            request_id=request.request_id,
            adapter_name=self.name,
            capability=request.capability,
            action=request.action,
            status=AdapterStatus.SIMULATED,
            output={
                "url": url,
                "title": f"Simulated: {url[:80]}",
                "text": text[:max_chars],
                "char_count": len(text[:max_chars]),
                "simulated": True,
            },
            observations=["Text extraction is simulated — not from real page content"],
        )
