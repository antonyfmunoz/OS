"""Structured crawl expansion for the Tool Mastery Research Agent.

Structured crawl unlock: some vendor docs sites expose almost no machine-
readable surface (no sitemap, no llms.txt, SPA shell, bot-walled
aggregator search). For those tools, registry and sitemap discovery cannot find
anything past a single landing page. The only remaining honest move
is to take an *already-approved* doc page and follow its in-page
links — ONE step, same host only, doc-shaped paths only — to see
whether the site exposes its documentation as ordinary HTML nav.

This is NOT a general web crawler. It is a bounded graph expansion
rooted exclusively in trusted entry points:

    - registry / official_url hints
    - accepted candidate approvals
    - GitHub extractor outputs
    - sitemap / llms.txt discoveries

Hard guardrails (intentional — the whole feature is the guardrails):

    * ``MAX_CRAWL_DEPTH``        — default 1, cap 2. Parent → child only.
    * ``MAX_SEEDS_PER_RUN``      — no more than N seeds crawled per run.
    * ``MAX_NEW_URLS_PER_RUN``   — global cap across all seeds.
    * ``MAX_NEW_URLS_PER_HOST``  — per-host cap so one chatty nav bar
                                   cannot crowd other tools out of budget.
    * Same host only             — no cross-origin link following, ever.
    * Doc-path allowlist         — inherits ``_DOC_PATH_HINTS`` from docs site discovery.
    * Reject list                — inherits ``_REJECT_PATH_HINTS`` from docs site discovery.
    * Topical relevance          — same ``_topically_relevant`` rule as
                                   slug must appear in host or path.
    * No querystring-heavy URLs  — if the query string is longer than
                                   the path, we treat it as an app route.
    * No fragment-only hits      — ``/foo#bar`` collapses to ``/foo``.
    * No fabricated URLs         — every emitted ref cites a real
                                   parent URL, depth, and matched rule.
    * Signal gate untouched      — crawled candidates still pay the
                                   same prose-density tax downstream.

HTML parsing is done with ``html.parser.HTMLParser`` from the stdlib.
No beautifulsoup, no lxml, no headless browser. We extract ``<a href>``
tags and discard everything else. This is deliberately dumb — a
smarter parser would be more tempting to over-trust.
"""

from __future__ import annotations

import os

import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlparse

from .docs_site_discovery import (
    _DISCOVERY_SKIP_HOSTS,
    _DOC_PATH_HINTS,
    _REJECT_PATH_HINTS,
    _topically_relevant,
)
from .models import SourceRef, SourceTier

USER_AGENT = f"UMH-ToolMasteryResearchAgent/1.0 (+https://github.com/{os.environ.get('GITHUB_USER', 'umh')}/OS)"
TIMEOUT_SECONDS = 15
MAX_BYTES = 2_000_000  # 2 MB cap per seed page fetch

# ---- Guardrail constants ----
MAX_CRAWL_DEPTH = 1  # default; overridable to 2 by caller w/ justification
MAX_CRAWL_DEPTH_CEILING = 2  # hard cap — never deeper than this
MAX_SEEDS_PER_RUN = 6  # how many approved parent pages we'll crawl
MAX_NEW_URLS_PER_RUN = 18  # global new-URL budget
MAX_NEW_URLS_PER_HOST = 10  # per-host cap within the global budget
MAX_LINKS_PER_PAGE = 250  # defensive cap against pathological nav trees


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class CrawlProvenance:
    """Why a particular URL was kept by the crawler.

    This is attached to each emitted SourceRef.origin string so that
    downstream debugging can trace the decision path without reading
    the crawl code.
    """

    parent_url: str
    depth: int
    match_reason: str  # e.g. "doc_path:/docs", "slug_in_host", "sibling_of_approved"

    def to_origin(self, host: str) -> str:
        return (
            f"structured_crawl:{host}:depth{self.depth}:"
            f"{self.match_reason}:parent={self.parent_url}"
        )


@dataclass
class CrawlReport:
    """Summary of a structured crawl pass, suitable for audit tables."""

    seeds: list[str] = field(default_factory=list)
    discovered: list[str] = field(default_factory=list)  # raw same-host links
    filtered_in: list[str] = field(default_factory=list)  # passed doc+topic filter
    emitted: list[SourceRef] = field(default_factory=list)  # after caps applied
    notes: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "seeds": len(self.seeds),
            "discovered": len(self.discovered),
            "filtered_in": len(self.filtered_in),
            "emitted": len(self.emitted),
        }


# ---------------------------------------------------------------------------
# Minimal HTML anchor extractor
# ---------------------------------------------------------------------------


class _AnchorExtractor(HTMLParser):
    """Pull href values out of <a> tags. Nothing else."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for k, v in attrs:
            if k.lower() == "href" and v:
                self.hrefs.append(v.strip())
                if len(self.hrefs) >= MAX_LINKS_PER_PAGE:
                    # Defensive: stop feeding the parser.
                    raise StopIteration  # bubbles out of feed()


def _extract_anchors(body: bytes) -> list[str]:
    try:
        text = body.decode("utf-8", errors="replace")
    except (AttributeError, UnicodeDecodeError):
        return []
    parser = _AnchorExtractor()
    try:
        parser.feed(text)
    except StopIteration:
        pass
    except Exception:
        # html.parser is extremely forgiving but we still refuse to
        # crash the whole research run over a malformed page.
        pass
    return parser.hrefs


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def _http_get(url: str) -> tuple[bytes | None, str | None]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.5",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read(MAX_BYTES + 1)
            ctype = (resp.headers.get("Content-Type") or "").lower()
    except urllib.error.HTTPError as err:
        return None, f"HTTP {err.code}: {err.reason}"
    except socket.timeout:
        return None, f"timeout after {TIMEOUT_SECONDS}s"
    except (urllib.error.URLError, OSError) as err:
        return None, f"network error: {err}"
    if "html" not in ctype and "xml" not in ctype:
        # We only follow links out of HTML pages. XML (sitemaps) is
        # already handled by sitemap discovery; plain text, JSON, binaries are
        # not crawl surfaces.
        return None, f"non-html content-type: {ctype or 'unknown'}"
    return body[:MAX_BYTES], None


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def _same_host(url: str, host: str) -> bool:
    try:
        return (urlparse(url).netloc or "").lower() == host
    except ValueError:
        return False


def _looks_like_doc_path(url: str) -> tuple[bool, str]:
    """Return (accepted, reason). ``reason`` is used for provenance."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False, "unparseable"
    path = (parsed.path or "").lower()
    query = parsed.query or ""
    if not path or path == "/":
        return False, "root_or_empty"

    # Querystring heavier than the path? Treat as app route, drop.
    if query and len(query) > max(32, len(path)):
        return False, "querystring_heavy"

    for reject in _REJECT_PATH_HINTS:
        if reject in path:
            return False, f"rejected:{reject}"

    for hint in _DOC_PATH_HINTS:
        if hint in path:
            return True, f"doc_path:{hint}"

    if path.endswith((".md", ".mdx", ".rst", ".html")):
        return True, "doc_extension"

    return False, "no_doc_signal"


def _normalise(url: str) -> str:
    """Drop fragments, trim trailing slashes consistently."""
    clean, _frag = urldefrag(url)
    return clean


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def crawl_approved_docs(
    approved_refs: list[SourceRef],
    *,
    tool_slug: str,
    already_seen: set[str],
    max_depth: int = MAX_CRAWL_DEPTH,
    max_seeds: int = MAX_SEEDS_PER_RUN,
    max_new_urls: int = MAX_NEW_URLS_PER_RUN,
    max_per_host: int = MAX_NEW_URLS_PER_HOST,
) -> CrawlReport:
    """Expand outward from approved doc pages under strict caps.

    Parameters
    ----------
    approved_refs:
        SourceRefs from trusted upstream discovery (registry,
        GitHub expansion, sitemap/llms discovery). Non-HTTP refs and
        refs pointing at aggregator hosts in ``_DISCOVERY_SKIP_HOSTS``
        are skipped.
    tool_slug:
        Topical anchor. A discovered URL is only kept if the slug (or
        one of its >=3-char tokens) appears in the host or path, OR
        if the link sits under the approved parent's docs root.
    already_seen:
        URLs already on the source plan. We never re-emit these.
    max_depth:
        1 by default. Capped at ``MAX_CRAWL_DEPTH_CEILING``.

    Returns
    -------
    CrawlReport with seeds, raw discovered, filtered, emitted refs,
    and a chronological notes log documenting every probe.
    """
    report = CrawlReport()

    if max_depth < 1:
        report.notes.append(f"structured_crawl: max_depth={max_depth} < 1, skipping")
        return report
    if max_depth > MAX_CRAWL_DEPTH_CEILING:
        report.notes.append(
            f"structured_crawl: max_depth={max_depth} exceeds ceiling "
            f"{MAX_CRAWL_DEPTH_CEILING}, clamping"
        )
        max_depth = MAX_CRAWL_DEPTH_CEILING

    # Seed selection: take HTTP, non-aggregator, doc-shaped parents.
    seeds: list[SourceRef] = []
    for ref in approved_refs:
        try:
            parsed = urlparse(ref.url)
        except ValueError:
            continue
        if parsed.scheme not in ("http", "https"):
            continue
        host = (parsed.netloc or "").lower()
        if not host or host in _DISCOVERY_SKIP_HOSTS:
            continue
        # A seed must itself look like a doc page — we don't crawl
        # homepages. This keeps "approved entry" and "trusted doc
        # root" honest.
        ok, _why = _looks_like_doc_path(ref.url)
        if not ok:
            continue
        seeds.append(ref)
        if len(seeds) >= max_seeds:
            break

    if not seeds:
        report.notes.append(
            "structured_crawl: no eligible seeds (approved refs were all "
            "aggregators, non-HTTP, or non-doc-shaped)"
        )
        return report

    report.seeds = [s.url for s in seeds]
    report.notes.append(
        f"structured_crawl: {len(seeds)} seed(s) selected "
        f"(cap {max_seeds}, depth {max_depth})"
    )

    emitted_urls: set[str] = set()
    per_host_counts: dict[str, int] = {}
    total_emitted = 0

    # BFS frontier: (url, depth, parent_url, parent_host)
    frontier: list[tuple[str, int, str, str]] = [
        (s.url, 0, s.url, (urlparse(s.url).netloc or "").lower()) for s in seeds
    ]
    visited_pages: set[str] = set()

    while frontier and total_emitted < max_new_urls:
        url, depth, parent_url, parent_host = frontier.pop(0)
        if depth >= max_depth:
            continue
        norm = _normalise(url)
        if norm in visited_pages:
            continue
        visited_pages.add(norm)

        body, err = _http_get(norm)
        if err or body is None:
            report.notes.append(f"structured_crawl: GET {norm} — {err}")
            continue

        hrefs = _extract_anchors(body)
        report.notes.append(f"structured_crawl: {norm} → {len(hrefs)} raw anchor(s)")

        # Resolve each href, apply filters.
        for raw in hrefs:
            if not raw or raw.startswith(("#", "mailto:", "javascript:", "tel:")):
                continue
            resolved = _normalise(urljoin(norm, raw))
            if not resolved.startswith(("http://", "https://")):
                continue
            if not _same_host(resolved, parent_host):
                continue  # cross-origin — never follow
            if resolved in already_seen or resolved in emitted_urls:
                continue
            if resolved == norm:
                continue  # self-link

            report.discovered.append(resolved)

            ok, reason = _looks_like_doc_path(resolved)
            if not ok:
                continue

            # Topical relevance: slug must appear somewhere in host/path,
            # OR the link must live under the parent's path prefix
            # (sibling rule — a link discovered from an approved
            # /docs/foo page is trusted if it also sits under /docs/).
            relevant = _topically_relevant(resolved, tool_slug)
            if not relevant:
                try:
                    parent_path = urlparse(parent_url).path.rsplit("/", 1)[0] or "/"
                except ValueError:
                    parent_path = "/"
                child_path = urlparse(resolved).path or ""
                if (
                    parent_path
                    and parent_path != "/"
                    and child_path.startswith(parent_path)
                ):
                    relevant = True
                    reason = f"{reason}+sibling_of_approved"
            if not relevant:
                continue

            report.filtered_in.append(resolved)

            # Per-host cap
            host_ct = per_host_counts.get(parent_host, 0)
            if host_ct >= max_per_host:
                report.notes.append(
                    f"structured_crawl: per-host cap hit for {parent_host} "
                    f"({max_per_host}); dropping {resolved}"
                )
                continue

            prov = CrawlProvenance(
                parent_url=parent_url,
                depth=depth + 1,
                match_reason=reason,
            )
            new_ref = SourceRef(
                url=resolved,
                tier=SourceTier.OFFICIAL_DOCS,
                label=f"{parent_host} — docs via crawl (depth {depth + 1})",
                origin=prov.to_origin(parent_host),
            )
            report.emitted.append(new_ref)
            emitted_urls.add(resolved)
            per_host_counts[parent_host] = host_ct + 1
            total_emitted += 1

            if total_emitted >= max_new_urls:
                report.notes.append(
                    f"structured_crawl: global cap hit "
                    f"({max_new_urls} new URLs); stopping"
                )
                break

            # Optional depth-2: enqueue child for further expansion.
            if depth + 1 < max_depth:
                frontier.append((resolved, depth + 1, resolved, parent_host))

    report.notes.append(
        "structured_crawl: summary — "
        f"seeds={len(report.seeds)} "
        f"discovered={len(report.discovered)} "
        f"filtered_in={len(report.filtered_in)} "
        f"emitted={len(report.emitted)}"
    )
    return report
