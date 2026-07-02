"""Browser workflow — governed web scraping and research.

Wraps ScraplingConnector (sync HTTP fetcher) for web scraping and
research tasks through governed mutation. Browser-based evidence
collection dispatches to executor nodes via mesh relay.

Steps vary by operation:
- scrape: validate_url → fetch_page → extract_data
- research: validate_query → search_and_fetch → synthesize
- monitor: validate_url → fetch_current → compare_baseline
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from projections.eos.workflows.types import WorkflowStep

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_BROWSER_DATA_DIR = os.path.join(_REPO_ROOT, "data", "umh", "browser")


@dataclass
class ScrapeResult:
    url: str = ""
    title: str = ""
    text: str = ""
    links: list[str] = field(default_factory=list)
    status: str = ""


@dataclass
class MonitorResult:
    url: str = ""
    changed: bool = False
    title: str = ""
    status: str = ""


class BrowserWorkflow:
    """Browser task workflow through governed mutation."""

    def __init__(self, org_id: str = "", venture_id: str = "") -> None:
        self._org_id = org_id
        self._venture_id = venture_id
        self._scrape_result: ScrapeResult | None = None
        self._research_results: list[dict[str, Any]] = []
        self._monitor_result: MonitorResult | None = None
        self._query: str = ""
        self._extracted: str = ""

    def scrape_steps(self, url: str) -> list[WorkflowStep]:
        """Steps for scraping a single URL."""
        return [
            WorkflowStep(
                name="validate_url",
                mutation_name="command_submit",
                intent=f"Validate URL: {url[:80]}",
                execute_fn=lambda: self._validate_url(url),
            ),
            WorkflowStep(
                name="fetch_page",
                mutation_name="shell_execute",
                intent=f"Fetch page: {url[:80]}",
                execute_fn=lambda: self._fetch_page(url),
            ),
            WorkflowStep(
                name="extract_data",
                mutation_name="command_submit",
                intent=f"Extract data from: {url[:80]}",
                execute_fn=self._extract_data,
            ),
        ]

    def research_steps(self, query: str, num_results: int = 5) -> list[WorkflowStep]:
        """Steps for web research (search + fetch top results)."""
        self._query = query
        return [
            WorkflowStep(
                name="validate_query",
                mutation_name="command_submit",
                intent=f"Validate research query: {query[:80]}",
                execute_fn=lambda: self._validate_query(query),
            ),
            WorkflowStep(
                name="search_and_fetch",
                mutation_name="shell_execute",
                intent=f"Search and fetch: {query[:80]}",
                execute_fn=lambda: self._search_and_fetch(query, num_results),
            ),
            WorkflowStep(
                name="synthesize_results",
                mutation_name="command_submit",
                intent=f"Synthesize research: {query[:80]}",
                execute_fn=self._synthesize_research,
            ),
        ]

    def monitor_steps(self, url: str, baseline: str = "") -> list[WorkflowStep]:
        """Steps for monitoring a page for changes."""
        return [
            WorkflowStep(
                name="validate_url",
                mutation_name="command_submit",
                intent=f"Validate monitor URL: {url[:80]}",
                execute_fn=lambda: self._validate_url(url),
            ),
            WorkflowStep(
                name="fetch_current",
                mutation_name="shell_execute",
                intent=f"Fetch current state: {url[:80]}",
                execute_fn=lambda: self._monitor_page(url, baseline),
            ),
            WorkflowStep(
                name="compare_baseline",
                mutation_name="command_submit",
                intent=f"Compare against baseline: {url[:80]}",
                execute_fn=self._report_monitor,
            ),
        ]

    def _validate_url(self, url: str) -> tuple[str, bool]:
        if not url or not url.strip():
            return ("URL is empty", False)
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return (f"Invalid URL scheme: {parsed.scheme or 'none'}", False)
        if not parsed.netloc:
            return ("URL has no domain", False)
        return (f"URL valid: {url[:100]}", True)

    def _validate_query(self, query: str) -> tuple[str, bool]:
        if not query or not query.strip():
            return ("Query is empty", False)
        if len(query.strip()) < 3:
            return ("Query too short (minimum 3 characters)", False)
        return (f"Query valid: {query[:100]}", True)

    def _fetch_page(self, url: str) -> tuple[str, bool]:
        try:
            from adapters.scrapling.scrapling_connector import ScraplingConnector

            sc = ScraplingConnector()
            result = sc.fetch(url.strip(), stealth=False)

            if result.get("status", "").startswith("error"):
                return (f"Fetch failed: {result['status']}", False)

            self._scrape_result = ScrapeResult(
                url=result.get("url", url),
                title=result.get("title", ""),
                text=result.get("text", "")[:5000],
                links=result.get("links", []),
                status=result.get("status", "ok"),
            )
            return (
                f"Fetched: {self._scrape_result.title or url} "
                f"({len(self._scrape_result.text)} chars, "
                f"{len(self._scrape_result.links)} links)",
                True,
            )
        except ImportError:
            return ("scrapling not installed — cannot fetch", False)
        except Exception as exc:
            logger.debug("fetch failed: %s", exc)
            return (f"Fetch error: {exc}", False)

    def _extract_data(self) -> tuple[str, bool]:
        if not self._scrape_result:
            return ("no page fetched", False)

        parts = [f"# {self._scrape_result.title or self._scrape_result.url}\n"]
        if self._scrape_result.text:
            parts.append(self._scrape_result.text[:3000])
        if self._scrape_result.links:
            parts.append(f"\n## Links ({len(self._scrape_result.links)})")
            for link in self._scrape_result.links[:10]:
                parts.append(f"- {link}")

        self._extracted = "\n".join(parts)

        os.makedirs(_BROWSER_DATA_DIR, exist_ok=True)
        safe_name = re.sub(r"[^\w]", "_", self._scrape_result.url[:60])
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out_path = os.path.join(_BROWSER_DATA_DIR, f"{ts}_{safe_name}.md")

        try:
            with open(out_path, "w") as f:
                f.write(self._extracted)
        except OSError as exc:
            logger.debug("write failed: %s", exc)

        return (
            f"Extracted {len(self._extracted)} chars from "
            f"{self._scrape_result.title or self._scrape_result.url}",
            True,
        )

    def _search_and_fetch(
        self, query: str, num_results: int
    ) -> tuple[str, bool]:
        try:
            from adapters.scrapling.scrapling_connector import ScraplingConnector

            sc = ScraplingConnector()
            results = sc.search_and_fetch(query, num_results=num_results)
            self._research_results = results

            if not results:
                return (f"No results found for: {query}", False)

            return (
                f"Found {len(results)} results for: {query}",
                True,
            )
        except ImportError:
            return ("scrapling not installed — cannot search", False)
        except Exception as exc:
            logger.debug("search failed: %s", exc)
            return (f"Search error: {exc}", False)

    def _synthesize_research(self) -> tuple[str, bool]:
        if not self._research_results:
            return ("no research results to synthesize", False)

        parts = [f"# Web Research: {self._query}\n"]
        parts.append(f"**Results**: {len(self._research_results)}\n")

        for i, result in enumerate(self._research_results, 1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            text = result.get("text", "")[:500]
            parts.append(f"\n## {i}. {title}")
            parts.append(f"URL: {url}")
            parts.append(f"\n{text}\n")

        synthesis = "\n".join(parts)

        try:
            from adapters.models.model_router import call_with_fallback

            ai_result = call_with_fallback(
                prompt=(
                    f"Synthesize these web research results into key findings "
                    f"(3-5 bullet points):\n\n{synthesis[:3000]}"
                ),
                system="Research synthesizer. Be concise and specific.",
                task_type="fast_response",
            )
            if ai_result.output and len(ai_result.output.strip()) > 20:
                synthesis += f"\n\n## Key Findings\n{ai_result.output.strip()[:500]}"
        except Exception:
            synthesis += "\n\n## Key Findings\nAI synthesis unavailable. Review results above."

        os.makedirs(_BROWSER_DATA_DIR, exist_ok=True)
        safe_name = re.sub(r"[^\w]", "_", self._query[:40])
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        out_path = os.path.join(_BROWSER_DATA_DIR, f"research_{ts}_{safe_name}.md")

        try:
            with open(out_path, "w") as f:
                f.write(synthesis)
        except OSError as exc:
            logger.debug("write failed: %s", exc)

        return (f"Synthesized {len(self._research_results)} results for: {self._query}", True)

    def _monitor_page(self, url: str, baseline: str) -> tuple[str, bool]:
        try:
            from adapters.scrapling.scrapling_connector import ScraplingConnector

            sc = ScraplingConnector()
            result = sc.monitor_competitor(url, last_content=baseline)

            self._monitor_result = MonitorResult(
                url=result.get("url", url),
                changed=result.get("changed", False),
                title=result.get("title", ""),
                status=result.get("status", "ok"),
            )
            return (
                f"Monitor: {url} — {'CHANGED' if self._monitor_result.changed else 'no change'}",
                True,
            )
        except ImportError:
            return ("scrapling not installed — cannot monitor", False)
        except Exception as exc:
            logger.debug("monitor failed: %s", exc)
            return (f"Monitor error: {exc}", False)

    def _report_monitor(self) -> tuple[str, bool]:
        if not self._monitor_result:
            return ("no monitor result", False)

        status = "CHANGED" if self._monitor_result.changed else "unchanged"
        return (
            f"Monitor report: {self._monitor_result.url} is {status} "
            f"(title: {self._monitor_result.title or 'unknown'})",
            True,
        )
