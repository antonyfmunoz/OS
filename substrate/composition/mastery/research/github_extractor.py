"""GitHub repo extractor for the Tool Mastery Research Agent.

Phase 1 unlock: when source discovery yields a ``github.com/owner/repo``
URL, that URL alone is almost worthless — the landing page is a
JS-heavy SPA shell that the signal gate correctly drops. The *actual*
high-signal technical material lives inside the repo as files:

    README.md         — usage, install, overview, SDK idioms
    /docs/**/*.md     — long-form docs
    /examples/**      — concrete usage patterns
    package.json      — SDK version pinning, entry points
    pyproject.toml    — Python package metadata
    setup.py          — legacy Python metadata

This module expands a single repo SourceRef into a prioritised list of
``raw.githubusercontent.com`` SourceRefs pinned to the repo's current
default-branch commit SHA, so the fetcher can pull the raw file bytes
directly. The sanitizer + mapper see plain markdown / JSON, which
passes the signal gate cleanly.

Honest boundaries:
    - We use the public, unauthenticated GitHub REST API (60 req/hr
      per IP). No PAT, no secrets.
    - If the API fails (rate limit, 404, network), we return an empty
      expansion list plus a note — we do NOT guess file paths.
    - We pin raw URLs to a commit SHA, not to HEAD, so re-runs are
      reproducible even if the upstream default branch advances.
    - We cap total expanded files per repo to keep the fetch budget
      honest. Deeper exploration is a Phase 2+ concern.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

from .models import SourceRef, SourceTier

USER_AGENT = "EOS-ToolMasteryResearchAgent/1.0 (+https://github.com/antonyfmunoz/OS)"
TIMEOUT_SECONDS = 15

# Cap expanded file count per repo. The fetcher's default budget is 20;
# we want repo expansion to occupy the bulk of a research run without
# completely crowding out non-repo sources.
MAX_FILES_PER_REPO = 12

# README variants in preference order.
_README_NAMES: tuple[str, ...] = (
    "README.md",
    "README.MD",
    "Readme.md",
    "readme.md",
    "README.rst",
    "README.mdx",
    "README",
)

# Prefix directories considered high-signal inside a repo.
_DOC_DIR_PREFIXES: tuple[str, ...] = (
    "docs/",
    "doc/",
    "documentation/",
)
_EXAMPLE_DIR_PREFIXES: tuple[str, ...] = (
    "examples/",
    "example/",
    "sample/",
    "samples/",
)

# File extensions considered prose-bearing.
_DOC_EXTENSIONS: tuple[str, ...] = (".md", ".mdx", ".rst", ".txt")
_EXAMPLE_EXTENSIONS: tuple[str, ...] = (".md", ".mdx", ".rst", ".txt")

# Root config files that carry SDK idiom / version signal.
_ROOT_CONFIG_FILES: frozenset[str] = frozenset(
    {
        "package.json",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "Cargo.toml",
        "go.mod",
    }
)


@dataclass
class RepoCoordinates:
    """Parsed ``github.com/owner/repo`` coordinates."""

    owner: str
    repo: str


def parse_github_url(url: str) -> RepoCoordinates | None:
    """Return ``(owner, repo)`` if ``url`` points at a GitHub repo.

    Accepts common variants:
        https://github.com/owner/repo
        https://github.com/owner/repo.git
        https://github.com/owner/repo/tree/main/...
        https://github.com/owner/repo/blob/main/README.md

    Returns ``None`` for non-GitHub URLs and for surfaces that are not
    a concrete repo (e.g. ``github.com/search``, ``github.com/owner``).
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    host = (parsed.netloc or "").lower()
    if host not in ("github.com", "www.github.com"):
        return None
    segments = [s for s in (parsed.path or "").split("/") if s]
    if len(segments) < 2:
        return None
    owner, repo = segments[0], segments[1]
    if owner in ("search", "orgs", "topics", "collections", "settings"):
        return None
    # Strip a trailing .git suffix if present.
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo:
        return None
    return RepoCoordinates(owner=owner, repo=repo)


def _api_get_json(url: str) -> tuple[dict | list | None, str | None]:
    """GET a GitHub API URL and decode JSON. Returns (payload, error)."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read()
    except urllib.error.HTTPError as err:
        return None, f"HTTP {err.code}: {err.reason}"
    except socket.timeout:
        return None, f"timeout after {TIMEOUT_SECONDS}s"
    except (urllib.error.URLError, OSError) as err:
        return None, f"network error: {err}"
    try:
        return json.loads(body.decode("utf-8")), None
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        return None, f"json decode error: {err}"


def _get_default_branch_sha(
    coords: RepoCoordinates,
) -> tuple[str | None, str | None, str | None]:
    """Return (default_branch, commit_sha, error)."""
    url = f"https://api.github.com/repos/{coords.owner}/{coords.repo}"
    payload, err = _api_get_json(url)
    if err or not isinstance(payload, dict):
        return None, None, err or "unexpected payload"
    branch = payload.get("default_branch")
    if not branch:
        return None, None, "repo metadata missing default_branch"
    # Resolve branch -> commit sha via refs API
    ref_url = f"https://api.github.com/repos/{coords.owner}/{coords.repo}/git/ref/heads/{branch}"
    ref_payload, ref_err = _api_get_json(ref_url)
    if ref_err or not isinstance(ref_payload, dict):
        return branch, None, ref_err or "unexpected ref payload"
    sha = (ref_payload.get("object") or {}).get("sha")
    if not sha:
        return branch, None, "ref payload missing object.sha"
    return branch, sha, None


def _list_tree(coords: RepoCoordinates, sha: str) -> tuple[list[dict], str | None]:
    """Return the recursive tree for a commit. Each entry is a dict with at least 'path' and 'type'."""
    url = (
        f"https://api.github.com/repos/{coords.owner}/{coords.repo}"
        f"/git/trees/{sha}?recursive=1"
    )
    payload, err = _api_get_json(url)
    if err or not isinstance(payload, dict):
        return [], err or "unexpected tree payload"
    entries = payload.get("tree") or []
    if not isinstance(entries, list):
        return [], "tree payload missing list"
    # Honest truncation signal.
    if payload.get("truncated"):
        # Not fatal — we still have whatever entries the API returned.
        pass
    return [e for e in entries if isinstance(e, dict) and e.get("type") == "blob"], None


def _path_in_any_dir(path: str, prefixes: tuple[str, ...]) -> bool:
    """True if ``path`` sits under any of ``prefixes`` at any depth.

    Matches both top-level (``docs/foo.md``) and nested layouts
    (``packages/core/docs/foo.md``) so monorepos get picked up too.
    """
    lower = path
    for prefix in prefixes:
        if lower.startswith(prefix) or f"/{prefix}" in lower:
            return True
    return False


def _prioritise_files(entries: list[dict]) -> list[str]:
    """Rank blob paths by Phase 1 priority. Returns an ordered path list."""
    paths = [str(e.get("path") or "") for e in entries if e.get("path")]
    seen: set[str] = set()
    ordered: list[str] = []

    def _add(path: str) -> None:
        if path and path not in seen:
            seen.add(path)
            ordered.append(path)

    # 1. Top-level README variants.
    for name in _README_NAMES:
        if name in paths:
            _add(name)
            break  # one README is enough

    # 2. Root config files (SDK idioms / version pinning).
    for name in sorted(_ROOT_CONFIG_FILES):
        if name in paths:
            _add(name)

    # 3. Nested README.md files (monorepos put the real prose under
    # packages/<pkg>/README.md). Shallowest first, cap separately.
    nested_readmes = [p for p in paths if p.lower().endswith("readme.md") and "/" in p]
    nested_readmes.sort(key=lambda p: (p.count("/"), p.lower()))
    for p in nested_readmes[:4]:
        _add(p)

    # 4. docs/**/*.{md,mdx,rst,txt} — shallowest first, anywhere in
    # the tree (handles both docs/ and packages/*/docs/). Blog posts
    # are explicitly excluded — release notes are low-signal for
    # tool mastery, they live under their own section downstream.
    doc_hits = [
        p
        for p in paths
        if _path_in_any_dir(p, _DOC_DIR_PREFIXES)
        and p.lower().endswith(_DOC_EXTENSIONS)
        and "/blog/" not in p.lower()
        and not p.lower().startswith("blog/")
    ]
    doc_hits.sort(key=lambda p: (p.count("/"), p.lower()))
    for p in doc_hits:
        _add(p)

    # 5. examples/** text-bearing files (prose explanations, not code).
    example_hits = [
        p
        for p in paths
        if _path_in_any_dir(p, _EXAMPLE_DIR_PREFIXES)
        and p.lower().endswith(_EXAMPLE_EXTENSIONS)
    ]
    example_hits.sort(key=lambda p: (p.count("/"), p.lower()))
    for p in example_hits:
        _add(p)

    return ordered[:MAX_FILES_PER_REPO]


def _raw_url(coords: RepoCoordinates, sha: str, path: str) -> str:
    return (
        f"https://raw.githubusercontent.com/{coords.owner}/{coords.repo}/{sha}/{path}"
    )


def _classify_label(path: str) -> str:
    lower = path.lower()
    if lower.endswith("readme.md") or lower.startswith("readme"):
        return "README"
    if _path_in_any_dir(path, _DOC_DIR_PREFIXES):
        return "docs"
    if _path_in_any_dir(path, _EXAMPLE_DIR_PREFIXES):
        return "example"
    if path in _ROOT_CONFIG_FILES:
        return "config"
    return "file"


def expand_github_repo(
    ref: SourceRef,
) -> tuple[list[SourceRef], list[str]]:
    """Expand a GitHub repo SourceRef into raw.githubusercontent.com children.

    Returns ``(new_refs, notes)``. ``new_refs`` is empty if the URL is
    not a repo, the API call failed, or the repo has no prioritisable
    files. Every failure path writes an explanatory note — we never
    silently swallow an expansion error.
    """
    notes: list[str] = []
    coords = parse_github_url(ref.url)
    if coords is None:
        return [], notes  # not a repo URL — caller keeps original

    branch, sha, err = _get_default_branch_sha(coords)
    if err or not sha:
        notes.append(
            f"github_extractor: could not resolve default branch for "
            f"{coords.owner}/{coords.repo}: {err}"
        )
        return [], notes
    notes.append(
        f"github_extractor: pinned {coords.owner}/{coords.repo}@{branch} "
        f"to sha {sha[:12]}"
    )

    entries, tree_err = _list_tree(coords, sha)
    if tree_err:
        notes.append(
            f"github_extractor: tree listing failed for "
            f"{coords.owner}/{coords.repo}: {tree_err}"
        )
        return [], notes

    prioritised = _prioritise_files(entries)
    if not prioritised:
        notes.append(
            f"github_extractor: no README / docs / examples / config "
            f"files found in {coords.owner}/{coords.repo}"
        )
        return [], notes

    new_refs: list[SourceRef] = []
    for path in prioritised:
        kind = _classify_label(path)
        new_refs.append(
            SourceRef(
                url=_raw_url(coords, sha, path),
                tier=SourceTier.OFFICIAL_REPO,
                label=f"{coords.owner}/{coords.repo} — {kind}: {path}",
                origin=f"github_extractor:{ref.origin or 'repo'}",
            )
        )
    notes.append(
        f"github_extractor: expanded {coords.owner}/{coords.repo} into "
        f"{len(new_refs)} raw file(s)"
    )
    return new_refs, notes
