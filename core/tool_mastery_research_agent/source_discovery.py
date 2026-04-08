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

from .models import SourcePlan, SourceRef, SourceTier
from .paths import CLAUDE_JSON, TOOL_DOC_REGISTRY


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

    if plan.is_empty:
        plan.notes.append(
            "no primary sources found — request likely needs explicit "
            "--official-url or a registry entry before research can proceed"
        )

    # de-duplicate by URL while preserving order
    seen: set[str] = set()
    unique: list[SourceRef] = []
    for ref in plan.sources:
        if ref.url in seen:
            continue
        seen.add(ref.url)
        unique.append(ref)
    plan.sources = unique

    return plan
