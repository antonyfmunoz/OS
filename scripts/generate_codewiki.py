#!/usr/bin/env python3
"""CodeWiki inventory generator — deterministic backbone of docs/codewiki/.

Walks the entire repository and emits:
  - docs/codewiki/inventory/<dir>.md   — complete per-file tables (CODE dirs),
    per-skill tables + file appendix (skills/), or subdir rollups (DATA dirs)
  - docs/codewiki/inventory/_census.md — full-accounting census (every file
    under ROOT lands in exactly one category; totals reconcile to raw find)
  - docs/codewiki/_manifest.json       — machine-readable census + git SHA

Design rules (see docs/codewiki/index.md):
  - Deterministic: output is a pure function of (tree, node_summaries,
    _overrides.json). No LLM calls. Timestamps live ONLY in _manifest.json
    so inventory pages are diff-stable across regenerations.
  - Full accounting: every file under ROOT is inventoried, rolled up, or
    counted in a named excluded category. scripts/verify_codewiki.py asserts
    the sum matches a raw `find -type f` count.
  - Exclusion checks use paths RELATIVE to ROOT (never absolute parts —
    an absolute check nukes the tree when ROOT is a worktree under
    .claude/worktrees/).
  - Symlinks: counted as rows (type `link`, target shown), never followed.

Usage:
    UMH_ROOT=/opt/OS python3 scripts/generate_codewiki.py \
        [--out /path/to/docs/codewiki] [--summaries /path/to/node_summaries.json]
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(
    os.environ.get("UMH_ROOT")
    or os.environ.get("OS_ROOT")
    or os.environ.get("EOS_ROOT")
    or "/opt/OS"
)

# ─── Directory classification (fail-closed: unknown top-level dirs error) ────

CODE_DIRS = [
    "substrate",
    "adapters",
    "transports",
    "projections",
    "services",
    "scripts",
    "tests",
    "nodes",
    "umh",
    "saas",
    "cockpit",
    "agents",
    "docs",
    "knowledge",
    "infra",
    "config",
    "docker",
    ".agents",
    ".github",
    ".planning",
    ".obsidian",
    ".vscode",
    ".claire",
    ".claude",
]
SKILL_DIRS = ["skills"]
ROLLUP_DIRS = ["data", "logs", "vault", "runtime", "graphify-out", "media", ".playwright-mcp"]
# Pseudo-directory for top-level regular files (README.md, Dockerfile, …)
ROOT_FILES = "_root-files"

# Subtrees counted but never inventoried (named excluded categories).
# Keys are category names; values are matchers over ROOT-relative parts.
EXCLUDED_TOP = {".git", ".mypy_cache", ".ruff_cache", ".pytest_cache", "__pycache__"}
EXCLUDED_ANYWHERE = {"node_modules", "__pycache__"}
EXCLUDED_SUBTREES = [
    (".claude", "worktrees"),
    (".claire", "worktrees"),
    # cockpit build outputs — artifacts of `npm run build`, like node_modules
    ("cockpit", "dist"),
    ("cockpit", "dist-web"),
    ("cockpit", "out"),
]

BINARY_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".wav",
    ".mp3",
    ".mp4",
    ".webm",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".pyc",
    ".so",
    ".jar",
    ".keystore",
    ".db",
    ".sqlite",
    ".bin",
    ".webp",
}

MAX_LINECOUNT_BYTES = 4 * 1024 * 1024  # don't line-count files above this

# Summaries whose text is the generator's own "no docstring" fallback.
JUNK_SUMMARY_RE = re.compile(r"^(Python|TypeScript|JavaScript|SQL) (file|module) ", re.IGNORECASE)

WELL_KNOWN_FILES = {
    "package.json": "npm package manifest",
    "package-lock.json": "npm dependency lockfile",
    "tsconfig.json": "TypeScript compiler configuration",
    "tsconfig.node.json": "TypeScript compiler configuration (node context)",
    "tsconfig.web.json": "TypeScript compiler configuration (web context)",
    "pyproject.toml": "Python package/build configuration",
    "requirements.txt": "Python pip dependencies",
    "Dockerfile": "Container image build definition",
    "docker-compose.yml": "Docker Compose service orchestration",
    "Makefile": "Make build targets",
    ".gitignore": "Git ignore patterns",
    ".dockerignore": "Docker build ignore patterns",
    ".env.example": "Environment variable template (no secrets)",
    ".gitkeep": "Placeholder to keep empty directory in git",
    "fly.toml": "Fly.io deployment configuration",
    "capacitor.config.ts": "Capacitor mobile app configuration",
    "vitest.config.ts": "Vitest test runner configuration",
    "components.json": "shadcn/ui component configuration",
    "LICENSE": "License text",
    "CNAME": "GitHub Pages custom domain",
}


# ─── Data model ───────────────────────────────────────────────────────────────


@dataclass
class FileRow:
    relpath: str  # ROOT-relative POSIX path
    kind: str  # "file" | "link"
    lines: int | None  # None for binary / unreadable / links
    size: int
    purpose: str
    link_target: str = ""


@dataclass
class DirReport:
    name: str  # top-level dir name (or _root-files)
    treatment: str  # "code" | "skill" | "rollup"
    rows: list[FileRow] = field(default_factory=list)
    n_files: int = 0
    n_links: int = 0
    n_bytes: int = 0
    # rollup-only: first-level-subdir → (files, links, bytes, newest_mtime_iso)
    rollup: dict[str, list] = field(default_factory=dict)


# ─── Walk ─────────────────────────────────────────────────────────────────────


def _is_excluded(rel_parts: tuple[str, ...]) -> str | None:
    """Return excluded-category name if this ROOT-relative path is excluded."""
    if rel_parts[0] in EXCLUDED_TOP:
        return rel_parts[0]
    for top, sub in EXCLUDED_SUBTREES:
        if len(rel_parts) >= 2 and rel_parts[0] == top and rel_parts[1] == sub:
            return f"{top}/{sub}"
    for part in rel_parts:
        if part in EXCLUDED_ANYWHERE:
            return part if part != "__pycache__" else "__pycache__"
    return None


def walk_repo() -> tuple[dict[str, DirReport], dict[str, dict], list[str]]:
    """Walk ROOT once. Returns (dir_reports, excluded_counts, unknown_dirs).

    excluded_counts: category → {"files": n, "links": n, "bytes": n}
    Every regular file and symlink under ROOT lands in exactly one bucket.
    """
    reports: dict[str, DirReport] = {}
    excluded: dict[str, dict] = {}
    unknown: list[str] = []

    known = set(CODE_DIRS) | set(SKILL_DIRS) | set(ROLLUP_DIRS)

    for entry in sorted(os.scandir(ROOT), key=lambda e: e.name):
        name = entry.name
        if entry.is_file(follow_symlinks=False) or entry.is_symlink():
            reports.setdefault(ROOT_FILES, DirReport(ROOT_FILES, "code"))
            _add_path(reports[ROOT_FILES], Path(entry.path))
            continue
        if not entry.is_dir(follow_symlinks=False):
            continue
        if name in EXCLUDED_TOP:
            _count_subtree(Path(entry.path), excluded, name)
            continue
        if name not in known:
            unknown.append(name)
            continue
        treatment = "skill" if name in SKILL_DIRS else "rollup" if name in ROLLUP_DIRS else "code"
        rep = DirReport(name, treatment)
        reports[name] = rep
        _walk_dir(Path(entry.path), rep, excluded)

    return reports, excluded, unknown


def _count_subtree(base: Path, excluded: dict, category: str) -> None:
    bucket = excluded.setdefault(category, {"files": 0, "links": 0, "bytes": 0})
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        dp = Path(dirpath)
        for fn in filenames:
            p = dp / fn
            if p.is_symlink():
                bucket["links"] += 1
            else:
                bucket["files"] += 1
                try:
                    bucket["bytes"] += p.stat().st_size
                except OSError:
                    pass
        # symlinked dirs appear in dirnames; count as links, don't descend
        for dn in list(dirnames):
            if (dp / dn).is_symlink():
                dirnames.remove(dn)
                bucket["links"] += 1


def _walk_dir(base: Path, rep: DirReport, excluded: dict) -> None:
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        dp = Path(dirpath)
        rel_parts = dp.relative_to(ROOT).parts

        cat = _is_excluded(rel_parts)
        if cat:
            # Whole subtree is excluded: count it, stop descending.
            dirnames.clear()
            bucket = excluded.setdefault(cat, {"files": 0, "links": 0, "bytes": 0})
            for fn in filenames:
                p = dp / fn
                if p.is_symlink():
                    bucket["links"] += 1
                else:
                    bucket["files"] += 1
                    try:
                        bucket["bytes"] += p.stat().st_size
                    except OSError:
                        pass
            continue

        # prune excluded children before descending; symlinked dirs → link rows
        for dn in list(dirnames):
            child = dp / dn
            child_rel = child.relative_to(ROOT).parts
            if child.is_symlink():
                dirnames.remove(dn)
                _add_link_row(rep, child)
            elif _is_excluded(child_rel):
                dirnames.remove(dn)
                _count_subtree(child, excluded, _is_excluded(child_rel) or "excluded")

        for fn in sorted(filenames):
            _add_path(rep, dp / fn)


def _add_link_row(rep: DirReport, p: Path) -> None:
    try:
        target = os.readlink(p)
    except OSError:
        target = "?"
    rep.n_links += 1
    if rep.treatment != "rollup":
        rep.rows.append(
            FileRow(
                relpath=str(p.relative_to(ROOT)),
                kind="link",
                lines=None,
                size=0,
                purpose="",
                link_target=target,
            )
        )
    else:
        _rollup_touch(rep, p, 0, None, is_link=True)


def _add_path(rep: DirReport, p: Path) -> None:
    if p.is_symlink():
        _add_link_row(rep, p)
        return
    try:
        st = p.stat()
    except OSError:
        return
    rep.n_files += 1
    rep.n_bytes += st.st_size
    if rep.treatment == "rollup":
        _rollup_touch(rep, p, st.st_size, st.st_mtime)
        return
    rep.rows.append(
        FileRow(
            relpath=str(p.relative_to(ROOT)),
            kind="file",
            lines=_count_lines(p, st.st_size),
            size=st.st_size,
            purpose="",
        )
    )


def _rollup_touch(
    rep: DirReport, p: Path, size: int, mtime: float | None, is_link: bool = False
) -> None:
    rel = p.relative_to(ROOT)
    sub = (
        rel.parts[1] if len(rel.parts) > 2 else (rel.parts[1] if len(rel.parts) == 2 else "(root)")
    )
    row = rep.rollup.setdefault(sub, [0, 0, 0, 0.0])
    if is_link:
        row[1] += 1
    else:
        row[0] += 1
        row[2] += size
        if mtime and mtime > row[3]:
            row[3] = mtime


def _count_lines(p: Path, size: int) -> int | None:
    if p.suffix.lower() in BINARY_EXTS or size > MAX_LINECOUNT_BYTES:
        return None
    try:
        with open(p, "rb") as fh:
            data = fh.read()
        if b"\x00" in data[:8192]:
            return None
        return data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
    except OSError:
        return None


# ─── One-liner resolution ─────────────────────────────────────────────────────


def _clean(text: str, limit: int = 140) -> str:
    text = " ".join(text.split()).replace("|", "\\|")
    return text[: limit - 1] + "…" if len(text) > limit else text


def _py_docstring(p: Path) -> str:
    try:
        tree = ast.parse(p.read_text(errors="replace"))
        doc = ast.get_docstring(tree)
        if doc:
            return doc.strip().splitlines()[0]
    except (SyntaxError, OSError, ValueError):
        pass
    return ""


def _leading_comment(p: Path, markers: tuple[str, ...]) -> str:
    try:
        for i, line in enumerate(p.read_text(errors="replace").splitlines()):
            if i > 30:
                break
            s = line.strip()
            if not s or s.startswith("#!"):
                continue
            for m in markers:
                if s.startswith(m):
                    body = s[len(m) :].strip().strip("*/ ").strip()
                    if len(body) > 3 and not body.startswith(
                        ("eslint", "prettier", "@ts-", "type:", "-*-")
                    ):
                        return body
                    break
            else:
                return ""  # first code line reached, no leading comment
    except OSError:
        pass
    return ""


def _has_shebang(p: Path) -> bool:
    try:
        with open(p, "rb") as fh:
            return fh.read(2) == b"#!"
    except OSError:
        return False


def _md_title(p: Path) -> str:
    try:
        lines = p.read_text(errors="replace").splitlines()
    except OSError:
        return ""
    in_fm = False
    fm_desc = ""
    for i, line in enumerate(lines):
        s = line.strip()
        if i == 0 and s == "---":
            in_fm = True
            continue
        if in_fm:
            if s == "---":
                in_fm = False
                continue
            if s.startswith("description:"):
                fm_desc = s.split(":", 1)[1].strip().strip("\"'")
            continue
        if s.startswith("# "):
            return s[2:].strip()
        if s and not s.startswith(("<!--", "---")):
            return s if len(s) < 120 else ""
    return fm_desc


class PurposeResolver:
    """Deterministic one-liner chain: overrides → node_summaries → parse →
    well-known map → type label."""

    def __init__(self, overrides: dict[str, str], summaries: dict[str, dict]):
        self.overrides = overrides
        self.summaries = summaries

    def resolve(self, row: FileRow) -> str:
        if row.kind == "link":
            return f"symlink → `{_clean(row.link_target, 90)}`"
        rel = row.relpath
        if rel in self.overrides:
            return _clean(self.overrides[rel])
        if Path(rel).name == "__init__.py" and not row.lines:
            return "package marker (empty)"
        node = self.summaries.get(f"file::{rel}")
        if node:
            summary = (node.get("current") or {}).get("summary") or ""
            if summary and not JUNK_SUMMARY_RE.match(summary):
                return _clean(summary)
        p = ROOT / rel
        name, ext = p.name, p.suffix.lower()
        if name in WELL_KNOWN_FILES:
            return WELL_KNOWN_FILES[name]
        text = ""
        if ext == ".py":
            text = _py_docstring(p)
        elif ext in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".css"}:
            text = _leading_comment(p, ("//", "/*", "/**", "*"))
        elif ext in {
            ".sh",
            ".bash",
            ".ps1",
            ".tpl",
            ".yml",
            ".yaml",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".env",
        }:
            text = _leading_comment(p, ("#",))
        elif ext in {".md", ".mdx", ".txt"}:
            text = _md_title(p)
        elif ext == ".sql":
            text = _leading_comment(p, ("--", "/*"))
        elif not ext and _has_shebang(p):
            text = _leading_comment(p, ("#",))
        if text:
            return _clean(text)
        conv = _path_convention(rel, ext)
        if conv:
            return conv
        if ext in BINARY_EXTS:
            return f"{ext.lstrip('.')} asset ({row.size:,} B)"
        return "—"


# Path-convention labels — deterministic fallbacks for comment-less files in
# directories whose structure implies the file's role (React/Capacitor app
# conventions, mobile build scaffolding). Names stay honest: they state the
# structural role, never invented behavior.
_STEM_WORDS_RE = re.compile(r"(?<!^)(?=[A-Z])|[-_]")


def _humanize_stem(stem: str) -> str:
    return " ".join(w for w in _STEM_WORDS_RE.split(stem) if w).lower()


def _path_convention(rel: str, ext: str) -> str:
    parts = rel.split("/")
    stem = Path(rel).stem
    nice = _humanize_stem(stem)
    if parts[0] == ".obsidian":
        return "Obsidian vault configuration"
    if len(parts) >= 2 and parts[:2] == [".github", "workflows"]:
        return f"GitHub Actions workflow — {nice}"
    if ".claude" in parts[:1] and "commands" in parts:
        return f"Claude Code slash command — {nice}"
    if (
        "skills" in parts
        and ext in {".mjs", ".cjs", ".js", ".json"}
        and ("scripts" in parts or "detector" in parts)
    ):
        return f"skill support script — {nice}"
    if "skills" in parts and "reference" in parts and ext == ".md":
        return f"skill reference doc — {nice}"
    if ext in {".bat", ".cmd"}:
        return f"Windows batch script — {nice}"
    if ext == ".log":
        return "runtime log file"
    if ext in {".lock", ".tsbuildinfo"}:
        return "build/lock artifact"
    if ext == ".cron":
        return "crontab fragment"
    if "android" in parts:
        return "Android (Capacitor) build scaffolding"
    if "ios" in parts and ("App" in parts or "App.xcodeproj" in rel):
        return "iOS (Capacitor) Xcode project scaffolding"
    if ext in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
        conv_map = [
            ("components", f"React component — {nice}"),
            ("panels", f"Cockpit panel component — {nice}"),
            ("stores", f"Zustand store — {nice}"),
            ("hooks", f"React hook — {nice}"),
            ("api", f"API/WS client module — {nice}"),
            ("utils", f"utility module — {nice}"),
            ("lib", f"library module — {nice}"),
            ("constants", f"constants module — {nice}"),
            ("types", f"type definitions — {nice}"),
            ("__tests__", f"test suite — {nice}"),
            ("tests", f"test suite — {nice}"),
            ("styles", f"style module — {nice}"),
        ]
        for marker, label in conv_map:
            if marker in parts:
                return label
        if parts[-1].endswith((".test.ts", ".test.tsx", ".spec.ts")):
            return f"test suite — {nice}"
    if ext == ".css":
        return f"stylesheet — {nice}"
    if ext == ".svg":
        return "svg asset"
    return ""


# ─── Emit ─────────────────────────────────────────────────────────────────────


def _fmt_lines(n: int | None) -> str:
    return f"{n:,}" if n is not None else "—"


def _page_header(dirname: str, sha: str) -> str:
    return f"---\ntype: codewiki-inventory\ndir: {dirname}\nsource_sha: {sha}\n---\n\n"


def emit_code_page(rep: DirReport, resolver: PurposeResolver, out: Path, sha: str) -> None:
    title = "Repository root files" if rep.name == ROOT_FILES else f"`{rep.name}/`"
    parts = [
        _page_header(rep.name, sha),
        f"# {title} — File Inventory\n\n",
        f"**Files:** {rep.n_files:,} regular + {rep.n_links:,} symlinks"
        f" · **Bytes:** {rep.n_bytes:,}\n\n",
        f"[Narrative page](../dirs/{_slug(rep.name)}.md)\n\n",
    ]
    # group rows by immediate subdirectory for readability
    groups: dict[str, list[FileRow]] = {}
    for row in sorted(rep.rows, key=lambda r: r.relpath):
        rel = Path(row.relpath)
        key = "/".join(rel.parts[1:2]) if rep.name != ROOT_FILES else ""
        if len(rel.parts) <= (2 if rep.name != ROOT_FILES else 1):
            key = "(root)" if rep.name != ROOT_FILES else ""
        groups.setdefault(key, []).append(row)

    ordered = sorted(groups, key=lambda k: "" if k in ("(root)", "") else k)
    for key in ordered:
        rows = groups[key]
        if key not in ("", "(root)"):
            n = sum(1 for r in rows if r.kind == "file")
            parts.append(f"\n## {rep.name}/{key}/ ({n:,} files)\n\n")
        elif key == "(root)":
            parts.append(f"\n## {rep.name}/ (root)\n\n")
        parts.append("| Path | Lines | Purpose |\n|---|---|---|\n")
        for r in rows:
            parts.append(f"| `{r.relpath}` | {_fmt_lines(r.lines)} | {resolver.resolve(r)} |\n")
    (out / "inventory" / f"{_slug(rep.name)}.md").write_text("".join(parts))


def emit_skill_page(rep: DirReport, resolver: PurposeResolver, out: Path, sha: str) -> None:
    parts = [
        _page_header(rep.name, sha),
        f"# `{rep.name}/` — Skill Library Inventory\n\n",
        f"**Files:** {rep.n_files:,} regular + {rep.n_links:,} symlinks"
        f" · **Bytes:** {rep.n_bytes:,}\n\n",
        f"[Narrative page](../dirs/{_slug(rep.name)}.md)\n\n",
        "## Skills Overview\n\n",
        "| Skill | Kind | Files | Description |\n|---|---|---|---|\n",
    ]
    by_skill: dict[str, list[FileRow]] = {}
    for row in sorted(rep.rows, key=lambda r: r.relpath):
        rel = Path(row.relpath)
        skill = rel.parts[1] if len(rel.parts) > 1 else "(root)"
        by_skill.setdefault(skill, []).append(row)

    for skill in sorted(by_skill):
        rows = by_skill[skill]
        if len(rows) == 1 and rows[0].kind == "link":
            parts.append(f"| `{skill}` | symlink | — | → `{_clean(rows[0].link_target, 80)}` |\n")
            continue
        if len(rows) == 1 and not (ROOT / rep.name / skill).is_dir():
            parts.append(f"| `{skill}` | file | 1 | {resolver.resolve(rows[0])} |\n")
            continue
        desc = ""
        for cand in ("SKILL.md", "skill.md", "README.md"):
            sp = ROOT / rep.name / skill / cand
            if sp.is_file():
                desc = _skill_description(sp) or _md_title(sp)
                if desc:
                    break
        nf = sum(1 for r in rows if r.kind == "file")
        parts.append(f"| `{skill}` | dir | {nf:,} | {_clean(desc) or '—'} |\n")

    parts.append("\n## Complete File Appendix\n\n")
    for skill in sorted(by_skill):
        rows = by_skill[skill]
        parts.append(
            f"\n### skills/{skill} ({sum(1 for r in rows if r.kind == 'file'):,} files)\n\n"
        )
        parts.append("| Path | Lines | Purpose |\n|---|---|---|\n")
        for r in rows:
            parts.append(f"| `{r.relpath}` | {_fmt_lines(r.lines)} | {resolver.resolve(r)} |\n")
    (out / "inventory" / f"{_slug(rep.name)}.md").write_text("".join(parts))


def _skill_description(p: Path) -> str:
    try:
        lines = p.read_text(errors="replace").splitlines()
    except OSError:
        return ""
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:40]:
        s = line.strip()
        if s == "---":
            break
        if s.startswith("description:"):
            return s.split(":", 1)[1].strip().strip("\"'")
    return ""


def emit_rollup_page(rep: DirReport, out: Path, sha: str) -> None:
    parts = [
        _page_header(rep.name, sha),
        f"# `{rep.name}/` — Runtime Data Rollup\n\n",
        f"**Files:** {rep.n_files:,} regular + {rep.n_links:,} symlinks"
        f" · **Bytes:** {rep.n_bytes:,}\n\n",
        f"[Narrative page](../dirs/{_slug(rep.name)}.md)\n\n",
        "Runtime/artifact directory — inventoried at subdirectory "
        "level. Counts reconcile in `_manifest.json`.\n\n",
        "| Subdirectory | Files | Symlinks | Bytes | Newest mtime |\n|---|---|---|---|---|\n",
    ]
    for sub in sorted(rep.rollup):
        f, l, b, m = rep.rollup[sub]
        mt = datetime.fromtimestamp(m, tz=timezone.utc).strftime("%Y-%m-%d") if m else "—"
        parts.append(f"| `{rep.name}/{sub}` | {f:,} | {l:,} | {b:,} | {mt} |\n")
    parts.append(
        f"| **Total** | **{rep.n_files:,}** | **{rep.n_links:,}** | **{rep.n_bytes:,}** | |\n"
    )
    (out / "inventory" / f"{_slug(rep.name)}.md").write_text("".join(parts))


def emit_census(
    reports: dict[str, DirReport], excluded: dict, out: Path, sha: str, raw_total: int
) -> dict:
    inv_files = sum(r.n_files for r in reports.values() if r.treatment in ("code", "skill"))
    inv_links = sum(r.n_links for r in reports.values() if r.treatment in ("code", "skill"))
    roll_files = sum(r.n_files for r in reports.values() if r.treatment == "rollup")
    roll_links = sum(r.n_links for r in reports.values() if r.treatment == "rollup")
    exc_files = sum(v["files"] for v in excluded.values())
    exc_links = sum(v["links"] for v in excluded.values())
    accounted = inv_files + roll_files + exc_files

    parts = [
        _page_header("_census", sha),
        "# Repository Census — Full Accounting\n\n",
        f"Raw total (regular files, no excludes): **{raw_total:,}**\n\n",
        "| Category | Regular files | Symlinks |\n|---|---|---|\n",
        f"| Inventoried per-file (code + skills) | {inv_files:,} | {inv_links:,} |\n",
        f"| Rolled up (runtime data) | {roll_files:,} | {roll_links:,} |\n",
        f"| Excluded categories (counted below) | {exc_files:,} | {exc_links:,} |\n",
        f"| **Accounted total** | **{accounted:,}** |"
        f" **{inv_links + roll_links + exc_links:,}** |\n\n",
        "## Per-directory census\n\n",
        "| Directory | Treatment | Files | Symlinks | Bytes |\n|---|---|---|---|---|\n",
    ]
    for name in sorted(reports, key=lambda n: (-reports[n].n_files, n)):
        r = reports[name]
        parts.append(
            f"| [`{name}`]({_slug(name)}.md) | {r.treatment} |"
            f" {r.n_files:,} | {r.n_links:,} | {r.n_bytes:,} |\n"
        )
    parts.append(
        "\n## Excluded categories (counted, not inventoried)\n\n"
        "| Category | Files | Symlinks | Bytes |\n|---|---|---|---|\n"
    )
    for cat in sorted(excluded):
        v = excluded[cat]
        parts.append(f"| `{cat}` | {v['files']:,} | {v['links']:,} | {v['bytes']:,} |\n")
    (out / "inventory" / "_census.md").write_text("".join(parts))

    return {
        "raw_total_files": raw_total,
        "accounted_files": accounted,
        "inventoried": {"files": inv_files, "links": inv_links},
        "rollup": {"files": roll_files, "links": roll_links},
        "excluded": excluded,
        "dirs": {
            name: {
                "treatment": r.treatment,
                "files": r.n_files,
                "links": r.n_links,
                "bytes": r.n_bytes,
            }
            for name, r in reports.items()
        },
    }


def _slug(name: str) -> str:
    # ".agents" → "dot-agents" (a bare lstrip would collide with "agents/")
    if name.startswith("."):
        return "dot-" + name[1:].replace(".", "-")
    return name.replace(".", "-")


def _raw_total() -> int:
    """Raw regular-file count under ROOT — the reconciliation target."""
    n = 0
    for _dirpath, _dirnames, filenames in os.walk(ROOT, followlinks=False):
        dp = Path(_dirpath)
        n += sum(1 for fn in filenames if not (dp / fn).is_symlink())
    return n


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs" / "codewiki",
        help="docs/codewiki output directory",
    )
    ap.add_argument(
        "--summaries",
        type=Path,
        default=ROOT / "data" / "node_summaries.json",
        help="node_summaries.json for one-liner enrichment",
    )
    args = ap.parse_args()

    out: Path = args.out
    (out / "inventory").mkdir(parents=True, exist_ok=True)

    overrides_path = out / "_overrides.json"
    overrides = json.loads(overrides_path.read_text()) if overrides_path.is_file() else {}
    summaries = {}
    if args.summaries.is_file():
        summaries = json.loads(args.summaries.read_text()).get("nodes", {})
    else:
        print(
            f"[warn] no node_summaries at {args.summaries}; falling back to parse heuristics only"
        )
    resolver = PurposeResolver(overrides, summaries)

    try:
        sha = (
            subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout.strip()
            or "unknown"
        )
    except Exception:
        sha = "unknown"

    print(f"[codewiki] scanning {ROOT} …")
    reports, excluded, unknown = walk_repo()
    if unknown:
        print(
            f"[codewiki] FATAL: unclassified top-level dirs: {unknown}\n"
            "Add them to CODE_DIRS / SKILL_DIRS / ROLLUP_DIRS / EXCLUDED_TOP "
            "in scripts/generate_codewiki.py (fail-closed by design)."
        )
        return 2

    print("[codewiki] counting raw total …")
    raw_total = _raw_total()

    for rep in reports.values():
        if rep.treatment == "rollup":
            emit_rollup_page(rep, out, sha)
        elif rep.treatment == "skill":
            emit_skill_page(rep, resolver, out, sha)
        else:
            emit_code_page(rep, resolver, out, sha)

    manifest = emit_census(reports, excluded, out, sha, raw_total)
    manifest.update(
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "git_sha": sha,
            "scan_root": str(ROOT),
        }
    )
    (out / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    if not overrides_path.is_file():
        overrides_path.write_text("{}\n")

    acc = manifest["accounted_files"]
    delta = raw_total - acc
    print(
        f"[codewiki] dirs: {len(reports)} · raw total {raw_total:,} · "
        f"accounted {acc:,} · delta {delta:,}"
    )
    print(f"[codewiki] wrote {out}/inventory/*.md + _manifest.json")
    # The walk and the raw count are two passes over a LIVE tree — logs/ churns
    # between them, so a handful of files can appear/vanish. Small deltas are
    # live-system noise; anything larger means real missing coverage.
    return 0 if abs(delta) <= 50 else 1


if __name__ == "__main__":
    sys.exit(main())
