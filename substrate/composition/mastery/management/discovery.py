"""Tool discovery for the Tool Mastery Manager.

Four deterministic sources, in priority order:

    (i)   skills_dir   — /opt/OS/skills/tools/ existing slugs
    (ii)  explicit     — tool names passed directly by caller / CLI
    (iii) seed_list    — /opt/OS/config/tool_mastery_seeds.yaml
    (iv)  claude_json  — mcpServers block of ~/.claude.json

Each discovered tool is normalised to snake_case and merged by slug. If
the same tool shows up in multiple sources its `sources` list is unioned
so reports can explain provenance.

Non-goals (v1): we deliberately do NOT infer tools from arbitrary file
contents or Python imports. Discovery is deterministic and explainable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from .models import DiscoverySource, ToolRef
from .paths import CLAUDE_JSON, EXCLUDE_LIST_PATH, SEED_LIST_PATH, SKILLS_TOOLS_DIR

# Same rule as scaffold_tool_skill.py normalize_to_snake_case — kept local
# so discovery has no import-time coupling to that script.
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def normalise_slug(raw: str) -> str:
    s = raw.strip().lower()
    s = _SLUG_RE.sub("_", s)
    return s.strip("_")


def _title_case(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.split("_") if w)


def discover_skills_dir(tools_dir: Path = SKILLS_TOOLS_DIR) -> list[ToolRef]:
    """Source (i): every directory under skills/tools/ that has a SKILL.md.

    This is not "tools we know about" in an abstract sense — it is the
    concrete set of tools that already have *some* coverage (valid or
    not). The coverage evaluator decides READY vs INVALID.
    """
    if not tools_dir.is_dir():
        return []
    refs: list[ToolRef] = []
    for d in sorted(tools_dir.iterdir()):
        if not d.is_dir():
            continue
        if not (d / "SKILL.md").is_file():
            continue
        refs.append(
            ToolRef(
                slug=d.name,
                display_name=_title_case(d.name),
                sources=[DiscoverySource.SKILLS_DIR],
            )
        )
    return refs


def discover_explicit(names: Iterable[str]) -> list[ToolRef]:
    """Source (ii): caller-provided names."""
    refs: list[ToolRef] = []
    for raw in names:
        slug = normalise_slug(raw)
        if not slug:
            continue
        refs.append(
            ToolRef(
                slug=slug,
                display_name=_title_case(slug),
                sources=[DiscoverySource.EXPLICIT],
            )
        )
    return refs


def discover_seed_list(path: Path = SEED_LIST_PATH) -> list[ToolRef]:
    """Source (iii): config/tool_mastery_seeds.yaml.

    Format (intentionally simple — portability > cleverness):

        tools:
          - slack
          - stripe
          - name: openai
            display_name: OpenAI
            note: "core LLM provider"
    """
    if not path.is_file():
        return []
    try:
        import yaml  # local import — keeps discovery lazy
    except Exception:
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    items = data.get("tools") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    refs: list[ToolRef] = []
    for entry in items:
        if isinstance(entry, str):
            slug = normalise_slug(entry)
            if slug:
                refs.append(
                    ToolRef(
                        slug=slug,
                        display_name=_title_case(slug),
                        sources=[DiscoverySource.SEED_LIST],
                    )
                )
        elif isinstance(entry, dict):
            raw = entry.get("name") or entry.get("slug")
            if not raw:
                continue
            slug = normalise_slug(str(raw))
            if not slug:
                continue
            display = str(entry.get("display_name") or _title_case(slug))
            meta = {k: v for k, v in entry.items() if k not in ("name", "slug", "display_name")}
            refs.append(
                ToolRef(
                    slug=slug,
                    display_name=display,
                    sources=[DiscoverySource.SEED_LIST],
                    metadata=meta,
                )
            )
    return refs


def discover_claude_json(path: Path = CLAUDE_JSON) -> list[ToolRef]:
    """Source (iv): MCP servers declared in ~/.claude.json.

    Reads both the top-level `mcpServers` block AND the union of
    per-project `mcpServers` blocks. MCP server names may contain
    hyphens and mixed case; we normalise to snake_case the same way as
    the scaffold script, so `notebooklm-mcp` becomes `notebooklm_mcp`.

    This is Claude Code-specific on purpose — it's the only "real env
    scan" discovery source we implement in v1, and it degrades silently
    if the file is missing (fresh install on a non-CC host).
    """
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    found: dict[str, dict] = {}

    def _collect(block: dict | None) -> None:
        if not isinstance(block, dict):
            return
        for raw_name, cfg in block.items():
            slug = normalise_slug(raw_name)
            if not slug:
                continue
            meta = found.setdefault(slug, {"raw_names": set(), "kinds": set()})
            meta["raw_names"].add(raw_name)
            if isinstance(cfg, dict):
                if "command" in cfg:
                    meta["kinds"].add("stdio")
                if "url" in cfg:
                    meta["kinds"].add("http")

    _collect(data.get("mcpServers"))
    projects = data.get("projects")
    if isinstance(projects, dict):
        for proj in projects.values():
            if isinstance(proj, dict):
                _collect(proj.get("mcpServers"))

    refs: list[ToolRef] = []
    for slug, meta in sorted(found.items()):
        refs.append(
            ToolRef(
                slug=slug,
                display_name=_title_case(slug),
                sources=[DiscoverySource.CLAUDE_JSON],
                metadata={
                    "mcp_raw_names": sorted(meta["raw_names"]),
                    "mcp_kinds": sorted(meta["kinds"]),
                },
            )
        )
    return refs


def _merge(refs_lists: list[list[ToolRef]]) -> list[ToolRef]:
    """Merge by slug, unioning sources and metadata."""
    merged: dict[str, ToolRef] = {}
    for refs in refs_lists:
        for r in refs:
            if r.slug not in merged:
                merged[r.slug] = ToolRef(
                    slug=r.slug,
                    display_name=r.display_name,
                    sources=list(r.sources),
                    metadata=dict(r.metadata),
                )
                continue
            existing = merged[r.slug]
            for s in r.sources:
                if s not in existing.sources:
                    existing.sources.append(s)
            # metadata merge: existing wins on conflict, union otherwise
            for k, v in r.metadata.items():
                existing.metadata.setdefault(k, v)
            if not existing.display_name and r.display_name:
                existing.display_name = r.display_name
    return sorted(merged.values(), key=lambda t: t.slug)


def load_exclude_slugs(path: Path = EXCLUDE_LIST_PATH) -> dict[str, str]:
    """Load the exclusion list from config/tool_mastery_exclude.yaml.

    Returns a dict mapping normalised slug -> reason string. Reasons are
    retained so the Manager can log *why* a slug was excluded when it
    filters discovery output.

    Format (see config/tool_mastery_exclude.yaml for the full contract):

        exclude_slugs:
          - slug: goviralbitch
            reason: "ghost mcpServers entry from uninstalled plugin"
            audit: docs/audits/...md

    Degrades silently if the file is missing or malformed — an exclusion
    list failure must never break discovery.
    """
    if not path.is_file():
        return {}
    try:
        import yaml  # local import — keeps discovery lazy
    except Exception:
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    items = data.get("exclude_slugs") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return {}
    out: dict[str, str] = {}
    for entry in items:
        if isinstance(entry, str):
            slug = normalise_slug(entry)
            if slug:
                out[slug] = "(no reason given)"
        elif isinstance(entry, dict):
            raw = entry.get("slug") or entry.get("name")
            if not raw:
                continue
            slug = normalise_slug(str(raw))
            if not slug:
                continue
            out[slug] = str(entry.get("reason") or "(no reason given)").strip()
    return out


def _apply_exclusions(
    refs: list[ToolRef],
    exclusions: dict[str, str],
    *,
    log: bool = True,
) -> list[ToolRef]:
    """Drop any ToolRef whose slug is in the exclusions dict.

    Logs each dropped slug to stderr when `log=True` so operators can
    see exactly what was filtered and why. This is the self-cleaning
    signal: the Manager is loud about what it's ignoring.
    """
    if not exclusions:
        return refs
    kept: list[ToolRef] = []
    for r in refs:
        if r.slug in exclusions:
            if log:
                import sys
                reason = exclusions[r.slug]
                sources = ",".join(s.value for s in r.sources)
                print(
                    f"[tool_mastery_manager] excluded slug={r.slug} "
                    f"sources={sources} reason={reason!r}",
                    file=sys.stderr,
                )
            continue
        kept.append(r)
    return kept


def discover_all(
    *,
    explicit: Iterable[str] | None = None,
    include_skills_dir: bool = True,
    include_seed_list: bool = True,
    include_claude_json: bool = True,
    apply_exclusions: bool = True,
) -> list[ToolRef]:
    """Run every enabled discovery source and return a merged ToolRef list.

    When `apply_exclusions=True` (default), slugs declared in
    `config/tool_mastery_exclude.yaml` are filtered out after the merge.
    This is how the Manager suppresses ghost MCP entries (uninstalled
    plugins, abandoned per-project mcpServers blocks, etc.) without
    mutating the underlying discovery sources.
    """
    buckets: list[list[ToolRef]] = []
    if include_skills_dir:
        buckets.append(discover_skills_dir())
    if explicit:
        buckets.append(discover_explicit(explicit))
    if include_seed_list:
        buckets.append(discover_seed_list())
    if include_claude_json:
        buckets.append(discover_claude_json())
    merged = _merge(buckets)
    if apply_exclusions:
        merged = _apply_exclusions(merged, load_exclude_slugs())
    return merged
