"""Docs site discovery for the Tool Mastery Research Agent.

Phase 2 unlock: many vendor docs sites are JS-rendered SPAs whose root
HTML contains nothing but a bootstrap <script>. Phase 1's GitHub repo
extractor solved the repo case, but sites like clo3d.com, higgsfield.ai,
or remotion.dev expose most of their prose through a sitemap we never
probed. This module fixes that by probing two well-defined discovery
surfaces per candidate host:

    /sitemap.xml        — RFC / sitemaps.org URL set or sitemap index
    /sitemap_index.xml  — common variant used by WordPress / Mintlify
    /llms.txt           — recently adopted convention: a curated, flat
                          list of the highest-signal doc URLs the site
                          authors explicitly want LLMs to read

Honest boundaries:
    - No HTML parsing. We do not scrape HREFs out of landing pages —
      that's Phase 3 (structured crawl). This module only consumes
      sources the site itself publishes in machine-readable form.
    - No guessing. If neither surface exists we emit an explanatory
      note and return an empty expansion list.
    - No fabricated URLs. Every emitted SourceRef comes verbatim from
      the sitemap or llms.txt file, with provenance back to the
      exact discovery method and parent host.
    - Doc-like filter. We only keep URLs whose path looks like a
      documentation page (``/docs``, ``/api``, ``/reference``,
      ``/guide``, ``/tutorial``, ``/manual``, ``/handbook``, or a
      ``.md`` / ``.mdx`` / ``.html`` under those). Homepages, login
      routes, pricing pages, blog marketing posts are dropped.
    - Budget cap. At most ``MAX_URLS_PER_SITE`` URLs per host so a
      huge sitemap can't drown the fetch budget.
"""

from __future__ import annotations

import re
import socket
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .models import SourceRef, SourceTier

USER_AGENT = "EOS-ToolMasteryResearchAgent/1.0 (+https://github.com/antonyfmunoz/OS)"
TIMEOUT_SECONDS = 15
MAX_BYTES = 2_000_000  # cap per discovery file

# How many URLs we'll surface from a single host's sitemap or llms.txt.
# Phase 2 is about unblocking, not flooding. The fetcher's budget
# (DEFAULT_MAX_FETCHES=20) still gets the final word; this cap just
# keeps one site from crowding every other source out of the plan.
MAX_URLS_PER_SITE = 12

# When resolving a sitemap index, limit how many child sitemaps we
# actually descend into. A huge index shouldn't stall discovery.
MAX_CHILD_SITEMAPS = 3

# Sitemap discovery probe paths. Order matters — first hit wins.
_SITEMAP_PROBES: tuple[str, ...] = (
    "/sitemap.xml",
    "/sitemap_index.xml",
)
_LLMS_TXT_PROBE = "/llms.txt"

# Path fragments that mark a URL as "documentation-shaped".
# These match the same spirit as source_quality._HIGH_PATH_HINTS so
# the signal scorer will also tag them HIGH once they land on the plan.
_DOC_PATH_HINTS: tuple[str, ...] = (
    "/docs",
    "/doc/",
    "/documentation",
    "/reference",
    "/api",
    "/sdk",
    "/guide",
    "/guides",
    "/tutorial",
    "/tutorials",
    "/manual",
    "/handbook",
    "/learn",
    "/getting-started",
    "/quickstart",
    "/how-to",
    "/howto",
    "/cookbook",
    "/examples",
)

# Path fragments we explicitly reject even if the sitemap lists them.
# These mirror source_quality._LOW_PATH_HINTS.
_REJECT_PATH_HINTS: tuple[str, ...] = (
    "/login",
    "/signup",
    "/signin",
    "/sign-up",
    "/sign-in",
    "/register",
    "/auth",
    "/account",
    "/pricing",
    "/plans",
    "/checkout",
    "/billing",
    "/contact",
    "/about",
    "/careers",
    "/jobs",
    "/press",
    "/legal",
    "/privacy",
    "/terms",
    "/blog/",  # marketing blog posts — not tool mastery material
    "/news/",
    "/changelog",  # keep off by default; release notes live elsewhere
    "/download",
    "/downloads",
    "/cart",
    "/search",
)

# XML sitemap namespace. sitemaps.org dictates this URI.
_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

# Hosts whose sitemaps index the *entire universe* of packages / repos
# rather than a single tool's documentation. Probing these produces
# thousands of topically-irrelevant URLs per tool. The specific
# package page (e.g. pypi.org/project/<slug>) is already surfaced as
# a registry / search-discovery entry; we don't need the sitemap.
#
# github.com and raw.githubusercontent.com are covered by the Phase 1
# extractor and also skipped here to avoid double work.
_DISCOVERY_SKIP_HOSTS: frozenset[str] = frozenset(
    {
        "github.com",
        "www.github.com",
        "raw.githubusercontent.com",
        "pypi.org",
        "www.pypi.org",
        "npmjs.com",
        "www.npmjs.com",
        "crates.io",
        "pkg.go.dev",
        "rubygems.org",
        "hexdocs.pm",
    }
)


@dataclass
class SiteCoordinates:
    """Parsed scheme+host for a candidate docs site."""

    scheme: str
    host: str

    @property
    def root(self) -> str:
        return f"{self.scheme}://{self.host}"


def parse_site_coordinates(url: str) -> SiteCoordinates | None:
    """Return the scheme+host of ``url`` if it's usable, else None.

    We deliberately ignore the path — sitemap/llms.txt discovery runs
    against the HOST ROOT only. Passing in ``https://vendor.com/docs/x``
    still probes ``https://vendor.com/sitemap.xml``.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    host = (parsed.netloc or "").lower()
    if not host:
        return None
    return SiteCoordinates(scheme=parsed.scheme, host=host)


def _http_get(url: str) -> tuple[bytes | None, str | None, str | None]:
    """GET a URL and return (body, content_type, error).

    Dependency-free, matches the fetcher's conservative defaults.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/xml,text/xml,text/plain,*/*;q=0.5",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read(MAX_BYTES + 1)
            content_type = resp.headers.get("Content-Type", "") or ""
    except urllib.error.HTTPError as err:
        return None, None, f"HTTP {err.code}: {err.reason}"
    except socket.timeout:
        return None, None, f"timeout after {TIMEOUT_SECONDS}s"
    except (urllib.error.URLError, OSError) as err:
        return None, None, f"network error: {err}"
    return body[:MAX_BYTES], content_type, None


def _looks_like_doc_path(url: str) -> bool:
    """True if ``url``'s path looks like a documentation page.

    Accepts either an explicit doc hint (``/docs/``, ``/api/``, …) or
    a static-site extension under a neutral path. Rejects any URL
    whose path contains a blocklist fragment.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    path = (parsed.path or "").lower()
    if not path or path == "/":
        return False

    for reject in _REJECT_PATH_HINTS:
        if reject in path:
            return False

    for hint in _DOC_PATH_HINTS:
        if hint in path:
            return True

    # Static-site builds: ``/something/foo.md`` or ``.mdx`` is almost
    # always a doc page regardless of the parent directory name.
    if path.endswith((".md", ".mdx", ".rst")):
        return True

    return False


def _parse_sitemap_xml(body: bytes) -> tuple[list[str], list[str], str | None]:
    """Parse a sitemap XML document.

    Returns ``(urls, child_sitemaps, error)``:
      - urls          — flat URLs from ``<urlset>``
      - child_sitemaps — nested sitemap refs from ``<sitemapindex>``
      - error         — parse error string, or None
    """
    try:
        root = ET.fromstring(body)
    except ET.ParseError as err:
        return [], [], f"sitemap parse error: {err}"

    tag = root.tag
    urls: list[str] = []
    child_sitemaps: list[str] = []

    # Note: ElementTree elements with no children are falsy, so we must
    # use explicit ``is not None`` checks instead of ``or`` chains when
    # falling back between namespaced and non-namespaced lookups.
    def _find_loc(entry: ET.Element) -> str | None:
        loc = entry.find(f"{_SITEMAP_NS}loc")
        if loc is None:
            loc = entry.find("loc")
        if loc is None:
            return None
        text = (loc.text or "").strip()
        return text or None

    if tag == f"{_SITEMAP_NS}urlset" or tag.endswith("urlset"):
        entries = root.findall(f"{_SITEMAP_NS}url")
        if not entries:
            entries = root.findall("url")
        for entry in entries:
            loc_text = _find_loc(entry)
            if loc_text:
                urls.append(loc_text)
    elif tag == f"{_SITEMAP_NS}sitemapindex" or tag.endswith("sitemapindex"):
        entries = root.findall(f"{_SITEMAP_NS}sitemap")
        if not entries:
            entries = root.findall("sitemap")
        for entry in entries:
            loc_text = _find_loc(entry)
            if loc_text:
                child_sitemaps.append(loc_text)
    else:
        return [], [], f"unexpected sitemap root element: {tag}"

    return urls, child_sitemaps, None


def _parse_llms_txt(body: bytes, base: str) -> list[str]:
    """Extract URLs from an llms.txt file.

    The llms.txt convention is loose: markdown-ish links mixed with
    bare URLs and prose. We take a permissive stance — any token that
    looks like an absolute ``http(s)://`` URL or a bracket-link target
    counts. Relative links are resolved against ``base``.
    """
    try:
        text = body.decode("utf-8", errors="replace")
    except (AttributeError, UnicodeDecodeError):
        return []

    urls: list[str] = []
    seen: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Markdown link form: [label](url)
        if "](" in line:
            # Cheap extraction — avoids bringing in a markdown parser.
            start = line.find("](")
            end = line.find(")", start + 2) if start != -1 else -1
            if start != -1 and end != -1:
                candidate = line[start + 2 : end].strip()
                if candidate:
                    resolved = (
                        candidate
                        if candidate.startswith(("http://", "https://"))
                        else urljoin(base, candidate)
                    )
                    if resolved not in seen:
                        seen.add(resolved)
                        urls.append(resolved)
                continue
        # Bare URL form.
        for token in line.split():
            if token.startswith(("http://", "https://")):
                clean = token.rstrip(").,;:\"'")
                if clean not in seen:
                    seen.add(clean)
                    urls.append(clean)

    return urls


def _same_host(url: str, host: str) -> bool:
    try:
        return (urlparse(url).netloc or "").lower() == host
    except ValueError:
        return False


def _discover_via_sitemap(
    coords: SiteCoordinates,
) -> tuple[list[str], list[str]]:
    """Probe sitemap.xml / sitemap_index.xml. Returns (urls, notes)."""
    notes: list[str] = []
    urls: list[str] = []

    for probe in _SITEMAP_PROBES:
        probe_url = f"{coords.root}{probe}"
        body, _ctype, err = _http_get(probe_url)
        if err or body is None:
            notes.append(f"docs_site_discovery: {probe_url} — {err}")
            continue

        flat_urls, child_sitemaps, parse_err = _parse_sitemap_xml(body)
        if parse_err:
            notes.append(f"docs_site_discovery: {probe_url} — {parse_err}")
            continue

        if flat_urls:
            notes.append(
                f"docs_site_discovery: {probe_url} → {len(flat_urls)} URLs in urlset"
            )
            urls.extend(flat_urls)

        if child_sitemaps:
            notes.append(
                f"docs_site_discovery: {probe_url} is a sitemap index with "
                f"{len(child_sitemaps)} child sitemap(s); descending into first "
                f"{min(len(child_sitemaps), MAX_CHILD_SITEMAPS)}"
            )
            for child in child_sitemaps[:MAX_CHILD_SITEMAPS]:
                # Resolve relative sitemap refs against the probe URL.
                child_url = (
                    child
                    if child.startswith(("http://", "https://"))
                    else urljoin(probe_url, child)
                )
                child_body, _c2, child_err = _http_get(child_url)
                if child_err or child_body is None:
                    notes.append(
                        f"docs_site_discovery: child sitemap {child_url} — {child_err}"
                    )
                    continue
                child_flat, _grand, child_parse_err = _parse_sitemap_xml(child_body)
                if child_parse_err:
                    notes.append(
                        f"docs_site_discovery: child sitemap {child_url} — {child_parse_err}"
                    )
                    continue
                notes.append(
                    f"docs_site_discovery: {child_url} → {len(child_flat)} URLs"
                )
                urls.extend(child_flat)

        if urls:
            # First successful probe wins — don't double-count sitemap_index + sitemap.
            return urls, notes

    if not urls:
        notes.append(f"docs_site_discovery: no sitemap found under {coords.root}")
    return urls, notes


def _discover_via_llms_txt(
    coords: SiteCoordinates,
) -> tuple[list[str], bool, list[str]]:
    """Probe /llms.txt. Returns ``(urls, is_instruction_form, notes)``.

    The llms.txt convention has forked into two shapes:

    1. **Index form** — a flat, curated list of doc URLs. We extract
       those links and treat them as high-signal discovered refs.
    2. **Instruction form** — the file IS the documentation, written
       in prose + code blocks for an LLM to read directly (Remotion,
       some vibecode frameworks do this). In that case the right
       move is to fetch the llms.txt URL itself as a source.

    We heuristically classify: if the body is substantial prose
    (>= 1000 bytes) AND fewer than 5 parseable links were found,
    the file is treated as instruction-form and ``is_instruction_form``
    is set True. The caller then emits the llms.txt URL as a single
    SourceRef.
    """
    notes: list[str] = []
    probe_url = f"{coords.root}{_LLMS_TXT_PROBE}"
    body, _ctype, err = _http_get(probe_url)
    if err or body is None:
        notes.append(f"docs_site_discovery: {probe_url} — {err}")
        return [], False, notes

    urls = _parse_llms_txt(body, base=probe_url)
    # Instruction-form detection: substantial body + few or no links.
    is_instruction_form = len(body) >= 1000 and len(urls) < 5
    if urls and not is_instruction_form:
        notes.append(f"docs_site_discovery: {probe_url} → {len(urls)} curated URL(s)")
    elif is_instruction_form:
        notes.append(
            f"docs_site_discovery: {probe_url} is instruction-form "
            f"({len(body)} bytes of prose, {len(urls)} stray links); "
            f"will fetch the llms.txt URL itself as a source"
        )
    else:
        notes.append(f"docs_site_discovery: {probe_url} exists but no URLs parsed")
    return urls, is_instruction_form, notes


def _topically_relevant(url: str, tool_slug: str | None) -> bool:
    """True if the URL plausibly relates to ``tool_slug``.

    If no slug is provided we keep the URL (legacy behaviour). When a
    slug is provided, we accept the URL if the slug (or any of its
    length>=3 tokens) appears in EITHER the host OR the path. Hosts
    count because vendor sites like ``www.remotion.dev`` make the slug
    structurally part of the origin rather than repeating it in every
    path; rejecting those would cripple the Phase 2 unlock.

    Tokens are slug-split on ``_`` / ``-`` so ``fl_studio`` matches
    both ``fl-studio`` and ``flstudio``.
    """
    if not tool_slug:
        return True
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    haystack = f"{host}{path}"
    slug = tool_slug.lower()
    if slug in haystack:
        return True
    tokens = [t for t in re.split(r"[_\-]+", slug) if len(t) >= 3]
    return any(t in haystack for t in tokens)


def _filter_and_rank(
    urls: list[str],
    host: str,
    *,
    tool_slug: str | None = None,
) -> list[str]:
    """Keep only same-host, doc-shaped, topically-relevant URLs.

    Ranking: shorter path depth first (those are usually overview /
    getting-started / index pages), then alphabetical for stability.
    """
    seen: set[str] = set()
    kept: list[str] = []
    for url in urls:
        if not _same_host(url, host):
            continue
        if not _looks_like_doc_path(url):
            continue
        if not _topically_relevant(url, tool_slug):
            continue
        if url in seen:
            continue
        seen.add(url)
        kept.append(url)

    kept.sort(key=lambda u: (urlparse(u).path.count("/"), u.lower()))
    return kept[:MAX_URLS_PER_SITE]


def discover_docs_site_urls(
    ref: SourceRef,
    *,
    method: str = "both",
    tool_slug: str | None = None,
) -> tuple[list[SourceRef], list[str]]:
    """Expand a SourceRef into sitemap/llms.txt-discovered doc URLs.

    Parameters
    ----------
    ref:
        The parent SourceRef whose host we probe. Path is ignored —
        discovery runs against the host root.
    method:
        ``"sitemap"``, ``"llms"``, or ``"both"`` (default). ``"both"``
        tries llms.txt first (curated, highest-signal) then falls back
        to sitemap.xml if llms.txt yielded nothing.

    Returns
    -------
    (new_refs, notes):
        ``new_refs`` are filtered, de-duplicated, capped SourceRefs
        tagged with ``tier=OFFICIAL_DOCS`` and an origin string that
        identifies the discovery method and parent host. ``notes``
        records every probe attempt and every failure, so the plan
        stays honest even on a site that publishes nothing.
    """
    notes: list[str] = []
    coords = parse_site_coordinates(ref.url)
    if coords is None:
        notes.append(f"docs_site_discovery: could not parse host from {ref.url!r}")
        return [], notes

    if coords.host in _DISCOVERY_SKIP_HOSTS:
        notes.append(
            f"docs_site_discovery: skipping {coords.host} "
            f"(aggregator / package registry — already covered by the "
            f"registry tier; sitemap is universe-scale noise)"
        )
        return [], notes

    all_urls: list[str] = []
    used_method = "none"
    instruction_form_ref: SourceRef | None = None

    if method in ("both", "llms"):
        llms_urls, is_instruction_form, llms_notes = _discover_via_llms_txt(coords)
        notes.extend(llms_notes)
        if is_instruction_form:
            # Treat the llms.txt file itself as a high-signal source.
            # It is curated prose written specifically for LLMs and
            # is already clean text — no HTML sanitisation needed.
            instruction_form_ref = SourceRef(
                url=f"{coords.root}{_LLMS_TXT_PROBE}",
                tier=SourceTier.OFFICIAL_DOCS,
                label=f"{coords.host} — llms.txt (instruction form)",
                origin=f"docs_site_discovery:llms_txt_instruction:{coords.host}",
            )
        elif llms_urls:
            used_method = "llms_txt"
            all_urls.extend(llms_urls)

    if method in ("both", "sitemap") and not all_urls and instruction_form_ref is None:
        sitemap_urls, sitemap_notes = _discover_via_sitemap(coords)
        notes.extend(sitemap_notes)
        if sitemap_urls:
            used_method = "sitemap"
            all_urls.extend(sitemap_urls)

    if not all_urls and instruction_form_ref is None:
        return [], notes

    # Instruction-form llms.txt: return just that one ref, no filtering.
    if instruction_form_ref is not None:
        return [instruction_form_ref], notes

    kept = _filter_and_rank(all_urls, coords.host, tool_slug=tool_slug)
    if not kept:
        notes.append(
            f"docs_site_discovery: {len(all_urls)} URL(s) probed from "
            f"{coords.host} but none passed the doc-path filter"
        )
        return [], notes

    new_refs: list[SourceRef] = []
    for url in kept:
        new_refs.append(
            SourceRef(
                url=url,
                tier=SourceTier.OFFICIAL_DOCS,
                label=f"{coords.host} — docs via {used_method}",
                origin=f"docs_site_discovery:{used_method}:{coords.host}",
            )
        )

    notes.append(
        f"docs_site_discovery: {coords.host} expanded via {used_method} → "
        f"{len(new_refs)} doc URL(s) after filter (from {len(all_urls)} raw)"
    )
    return new_refs, notes
