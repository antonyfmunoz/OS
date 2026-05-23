"""Source discovery for the Tool Mastery Research Agent.

Given a tool slug, build a prioritised list of primary sources. The
order of preference is:

    1. Explicit URL passed on the request (--official-url / hints)
    2. tool_doc_registry.md entries under TME
    3. ~/.claude.json mcpServers entry (for MCP-backed tools) — yields
       the MCP manifest URL if it is HTTP, or a synthetic "stdio://"
       ref otherwise so the provenance stays honest
    4. Derived guesses are NOT fabricated. If nothing is found, the
       plan is returned empty with explanatory notes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .candidate_approval import (
    approved_source_refs,
    latest_approval_file,
    load_approval_file,
)
from .docs_site_discovery import discover_docs_site_urls, parse_site_coordinates
from .github_extractor import expand_github_repo, parse_github_url
from .models import SourcePlan, SourceRef, SourceTier
from .paths import CLAUDE_JSON, TOOL_DOC_REGISTRY
from .source_quality import (
    SIGNAL_HIGH,
    SIGNAL_LOW,
    SIGNAL_MEDIUM,
    score_source,
    sort_sources_by_quality,
)
from .structured_crawl import crawl_approved_docs


_REGISTRY_ROW = re.compile(
    r"^\|\s*(?P<name>[^|]+?)\s*\|\s*(?P<docs>[^|]+?)\s*\|\s*(?P<api>[^|]+?)\s*\|"
)


def _slugify(name: str) -> str:
    """Match the manager's slug convention: lowercase snake_case."""

    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _from_registry(slug: str) -> list[SourceRef]:
    """Parse tool_doc_registry.md and emit SourceRefs for matching rows.

    The registry is human-maintained markdown; we do not import a
    markdown library to keep this dependency-free.
    """

    if not TOOL_DOC_REGISTRY.is_file():
        return []

    refs: list[SourceRef] = []
    target = slug
    for raw_line in TOOL_DOC_REGISTRY.read_text(encoding="utf-8").splitlines():
        m = _REGISTRY_ROW.match(raw_line)
        if not m:
            continue
        name = m.group("name")
        # skip header rows
        if name.lower().strip() in ("tool", "---"):
            continue
        if _slugify(name) != target and slug not in _slugify(name):
            continue

        docs = m.group("docs").strip()
        api = m.group("api").strip()
        if docs and docs.startswith("http"):
            refs.append(
                SourceRef(
                    url=docs,
                    tier=SourceTier.OFFICIAL_DOCS,
                    label=f"{name} — docs",
                    origin="tool_doc_registry",
                )
            )
        if api and api.startswith("http") and api != docs:
            refs.append(
                SourceRef(
                    url=api,
                    tier=SourceTier.OFFICIAL_API_REF,
                    label=f"{name} — API reference",
                    origin="tool_doc_registry",
                )
            )
        break
    return refs


def _from_claude_json(slug: str) -> tuple[list[SourceRef], list[str]]:
    """Extract provenance for MCP tools from ~/.claude.json.

    Returns (refs, notes). Notes capture anything worth recording even
    when a real URL isn't available (e.g. stdio-only MCP servers).
    """

    refs: list[SourceRef] = []
    notes: list[str] = []

    if not CLAUDE_JSON.is_file():
        return refs, notes

    try:
        data = json.loads(CLAUDE_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        notes.append(f"could not read {CLAUDE_JSON}: {err}")
        return refs, notes

    mcp = data.get("mcpServers", {}) or {}
    # slug may match either as-is or with dashes
    candidates = {
        slug,
        slug.replace("_", "-"),
        slug.replace("-", "_"),
    }
    key = next(
        (k for k in mcp.keys() if _slugify(k) in candidates or k in candidates), None
    )
    if not key:
        return refs, notes

    entry = mcp.get(key) or {}
    server_type = entry.get("type")
    if server_type == "http":
        url = entry.get("url")
        if url:
            refs.append(
                SourceRef(
                    url=url,
                    tier=SourceTier.MCP_MANIFEST,
                    label=f"{key} — MCP HTTP endpoint",
                    origin="claude_json",
                )
            )
            notes.append(
                f"MCP server {key!r} is HTTP; the endpoint itself is the manifest. "
                "Official vendor docs may still be required for usage patterns."
            )
        else:
            notes.append(f"MCP server {key!r} is HTTP but has no url field")
    elif server_type == "stdio":
        cmd = entry.get("command")
        notes.append(
            f"MCP server {key!r} is stdio-only (command={cmd!r}); no HTTP "
            "manifest available. Source discovery should fall back to the "
            "package registry (npm / pypi) for the command name."
        )
    else:
        notes.append(f"MCP server {key!r} has unknown type {server_type!r}")

    return refs, notes


def discover_sources(
    tool_slug: str,
    *,
    source_hints: list[str] | None = None,
    official_url: str | None = None,
) -> SourcePlan:
    """Build a SourcePlan for a single tool.

    Honest contract: if no primary source is found, the plan is empty
    and `notes` explains what was checked. Callers must handle the
    empty case rather than guessing.
    """

    plan = SourcePlan(tool_slug=tool_slug)

    if official_url:
        plan.sources.append(
            SourceRef(
                url=official_url,
                tier=SourceTier.OFFICIAL_DOCS,
                label=f"{tool_slug} — explicit official url",
                origin="request",
            )
        )

    for hint in source_hints or []:
        if hint and hint.startswith("http"):
            plan.sources.append(
                SourceRef(
                    url=hint,
                    tier=SourceTier.OFFICIAL_DOCS,
                    label=f"{tool_slug} — hint",
                    origin="request",
                )
            )

    plan.sources.extend(_from_registry(tool_slug))
    plan.notes.append(
        "checked tool_doc_registry.md"
        if TOOL_DOC_REGISTRY.is_file()
        else "tool_doc_registry.md not found"
    )

    mcp_refs, mcp_notes = _from_claude_json(tool_slug)
    plan.sources.extend(mcp_refs)
    plan.notes.extend(mcp_notes)

    # Fallback tier: operator-approved candidate sources.
    #
    # Only *accepted* candidates from the most recent candidates file
    # are pulled in. This is the gated bridge from search_discovery →
    # the fetcher. Unapproved candidates never reach this path.
    if plan.is_empty:
        approval_path = latest_approval_file(tool_slug)
        if approval_path is not None:
            try:
                approval = load_approval_file(approval_path)
                approved = approved_source_refs(approval)
                if approved:
                    plan.sources.extend(approved)
                    plan.notes.append(
                        f"loaded {len(approved)} operator-approved candidate "
                        f"source(s) from {approval_path.name}"
                    )
                else:
                    plan.notes.append(
                        f"candidate file {approval_path.name} exists but no "
                        "candidates are marked accepted — approval still pending"
                    )
            except (OSError, ValueError, KeyError) as err:
                plan.notes.append(
                    f"failed to load candidate approval file {approval_path}: {err}"
                )

    if plan.is_empty:
        plan.notes.append(
            "no primary sources found — run `--generate-candidates` to "
            "propose sources for approval, or re-run with --official-url / "
            "a registry entry before research can proceed"
        )

    # de-duplicate by URL while preserving order
    seen: set[str] = set()
    unique: list[SourceRef] = []
    for ref in plan.sources:
        if ref.url in seen:
            continue
        seen.add(ref.url)
        unique.append(ref)

    # GitHub repo expansion: any github.com/owner/repo
    # URL is replaced in-place with the prioritised set of raw files
    # inside that repo. The original repo URL is kept as a trailing
    # low-priority reference so provenance of *why* those raw files
    # were chosen remains on the plan. Non-repo GitHub URLs (search,
    # issues, gists) pass through untouched.
    expanded: list[SourceRef] = []
    for ref in unique:
        if parse_github_url(ref.url) is None:
            expanded.append(ref)
            continue
        new_refs, notes = expand_github_repo(ref)
        plan.notes.extend(notes)
        if new_refs:
            # De-duplicate expanded URLs against anything we've already seen.
            for nref in new_refs:
                if nref.url in seen:
                    continue
                seen.add(nref.url)
                expanded.append(nref)
            # Keep the original repo URL too — lets the author agent
            # link back to the canonical surface even though the raw
            # files carry the real signal. Signal scoring will push
            # it to the bottom of the plan automatically.
            expanded.append(ref)
        else:
            # Expansion failed — keep the original ref so the run is
            # still honest about what was attempted.
            expanded.append(ref)
    unique = expanded

    # Docs Site Discovery.
    #
    # For every unique non-raw-github host that landed on the plan,
    # probe /llms.txt and /sitemap.xml once. Any discovered doc-shaped
    # URLs are appended with explicit provenance. We never probe the
    # same host twice per run, and we skip hosts already owned by the
    # GitHub raw extractor (raw.githubusercontent.com) or the bare
    # github.com repo surface — repo expansion already covered those.
    probed_hosts: set[str] = set()
    discovered: list[SourceRef] = []
    for ref in list(unique):
        coords = parse_site_coordinates(ref.url)
        if coords is None:
            continue
        if coords.host in probed_hosts:
            continue
        probed_hosts.add(coords.host)
        new_refs, notes = discover_docs_site_urls(ref, tool_slug=tool_slug)
        plan.notes.extend(notes)
        for nref in new_refs:
            if nref.url in seen:
                continue
            seen.add(nref.url)
            discovered.append(nref)
    if discovered:
        plan.notes.append(
            f"docs_site_discovery: surfaced {len(discovered)} new URL(s) "
            f"across {len(probed_hosts)} probed host(s)"
        )
        unique.extend(discovered)

    # Structured Crawl Expansion.
    #
    # Take the already-approved doc pages (registry + github
    # expansion + sitemap/llms discoveries) and follow their
    # in-page links ONE hop, same host only, doc-shaped paths only,
    # under strict per-host and per-run caps. This exists for SPA
    # vendor sites that publish no sitemap and no llms.txt — clo3d
    # is the canonical target. Every new URL keeps full provenance
    # (parent URL, depth, match reason) on its origin field. Signal
    # scoring still runs after this step, so crawled candidates pay
    # the same prose-density tax as every other source.
    crawl_report = crawl_approved_docs(
        approved_refs=list(unique),
        tool_slug=tool_slug,
        already_seen=seen,
    )
    plan.notes.extend(crawl_report.notes)
    if crawl_report.emitted:
        for cref in crawl_report.emitted:
            if cref.url in seen:
                continue
            seen.add(cref.url)
            unique.append(cref)
        plan.notes.append(
            f"structured_crawl: added {len(crawl_report.emitted)} new "
            f"URL(s) from {len(crawl_report.seeds)} approved seed(s)"
        )

    # Quality-aware ordering: fetch high-signal sources first so the
    # fetch budget gets spent on URLs that actually contain technical
    # prose (official docs, API refs, real repos) before marketing
    # homepages or search aggregators.
    scored = sort_sources_by_quality(unique)
    plan.sources = [ref for ref, _score in scored]

    counts: dict[str, int] = {SIGNAL_HIGH: 0, SIGNAL_MEDIUM: 0, SIGNAL_LOW: 0}
    for _ref, score in scored:
        counts[score] = counts.get(score, 0) + 1
    if plan.sources:
        plan.notes.append(
            "source quality (pre-fetch): "
            f"{counts.get(SIGNAL_HIGH, 0)} high / "
            f"{counts.get(SIGNAL_MEDIUM, 0)} medium / "
            f"{counts.get(SIGNAL_LOW, 0)} low"
        )

    return plan
