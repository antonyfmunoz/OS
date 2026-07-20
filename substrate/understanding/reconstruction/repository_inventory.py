"""Repository inventory acquisition for the reconstruction subsystem.

Walks a repository tree accounting for EVERY ENCOUNTERED FILE (os.walk visits
files; directory nodes, symlinked directories, and empty directories are not
inventoried as records), classifies exclusions (generated outputs, binary
assets, vendored deps, caches, runtime logs, virtualenvs, .git, worktrees),
and emits evidence for the inventoried surface:

  - one SourceRecord per inventoried file (modality by suffix),
  - aggregated ObservationRecords per top-level package (python-file counts),
  - per-file ``source_present`` observations for the decision-relevant Python
    surface (substrate/adapters/transports/services/scripts).

Excluded paths are COUNTED in accounting but never hashed or parsed.
SENSITIVE paths (.env / .env.* / *.pem / *.key / credentials* / secrets* /
vault subtrees) are classified BEFORE any stat or hash: they are recorded as
presence-only sources (no size, no mtime, no hash — no fingerprint of any
kind). Files are hashed only up to a bounded size; larger files record
size+mtime metadata and a note, never a fabricated hash. Existing artifacts
(codebase graph, codewiki manifest) are read ONLY behind a git-SHA freshness
check and, when stale, are recorded as claims-only inputs — never trusted as
observation counts.

All git access flows through the CPU gate (``gated_subprocess_run``); under CPU
overload the git call returns None and the walk records an explicit
``git_unavailable`` note rather than crashing.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from substrate.execution.cpu_gate import gated_subprocess_run
from substrate.understanding.reconstruction.contracts import (
    ObservationRecord,
    SourceRecord,
    ValidTime,
)
from substrate.understanding.reconstruction.provenance import content_hash

# Files larger than this are NOT hashed — size+mtime metadata + a note instead.
logger = logging.getLogger(__name__)

MAX_HASH_BYTES = 2 * 1024 * 1024  # 2 MB

# Top-level directories whose per-file .py observations are decision-relevant.
DECISION_SURFACE_DIRS: frozenset[str] = frozenset(
    {"substrate", "adapters", "transports", "services", "scripts"}
)

# Directory names that mark an excluded subtree (matched on any path segment).
# The value is the exclusion category recorded in accounting.
_EXCLUDED_DIR_CATEGORY: dict[str, str] = {
    ".git": "vcs",
    ".hg": "vcs",
    ".svn": "vcs",
    "node_modules": "vendored_dependency",
    "vendor": "vendored_dependency",
    "bower_components": "vendored_dependency",
    "__pycache__": "cache",
    ".mypy_cache": "cache",
    ".ruff_cache": "cache",
    ".pytest_cache": "cache",
    ".cache": "cache",
    ".venv": "virtualenv",
    "venv": "virtualenv",
    "env": "virtualenv",
    "site-packages": "virtualenv",
    "logs": "runtime_log",
    ".git-rewrite": "vcs",
    "worktrees": "worktree",
    ".ipynb_checkpoints": "cache",
    ".tox": "cache",
    ".gradle": "cache",
    "dist": "generated_output",
    "build": "generated_output",
    ".next": "generated_output",
    "coverage": "generated_output",
}

# Extra guard: a `.claude/worktrees` (or `.claire/worktrees`) subtree is a
# worktree even though `.claude` itself is not globally excluded.
_WORKTREE_PARENTS: frozenset[str] = frozenset({".claude", ".claire"})

# Self-ingestion guard: `data/world_models/` is the self-model's OWN output.
# Walking it would re-hash prior runs' artifacts as fresh repository evidence —
# a recursive evidence loop compounding with every run.
_SELF_MODEL_OUTPUT_PARENT = "data"
_SELF_MODEL_OUTPUT_SEGMENT = "world_models"

# Runtime-state boundary (Wave 0): `data/runtime/` is the live organism's
# mutable state root — journals, queues, heartbeats. It is operational state,
# not repository content: hashing it would make repository evidence
# nondeterministic between runs and could ingest operational metadata. Counted
# in exclusion accounting, never hashed/parsed/emitted as a SourceRecord.
# Positional (data/runtime) so ordinary `runtime` package dirs are unaffected.
_RUNTIME_STATE_PARENT = "data"
_RUNTIME_STATE_SEGMENT = "runtime"

# Sensitive-path classification — checked BEFORE any stat/hash so no
# fingerprint (size, mtime, hash) of secret material is ever recorded.
_SENSITIVE_DIR_SEGMENTS: frozenset[str] = frozenset({"vault", ".vault", ".op"})
_SENSITIVE_SUFFIXES: frozenset[str] = frozenset({".pem", ".key"})
_SENSITIVE_NAME_PREFIXES: tuple[str, ...] = ("credentials", "secrets", ".env")
# Code/doc suffixes are exempt from the NAME-PREFIX rule only: a module named
# secrets_manager.py is source code, not secret material, and silently dropping
# it from source_present would blind the self-model to its own inventory. The
# .pem/.key suffix rule and the vault-directory rule still always apply.
_PREFIX_RULE_EXEMPT_SUFFIXES: frozenset[str] = frozenset(
    {".py", ".pyi", ".ts", ".tsx", ".js", ".mjs", ".md", ".rst", ".sh"}
)


def _is_sensitive(rel_parts: tuple[str, ...], fname: str) -> bool:
    """True when a path must be recorded presence-only (no fingerprint)."""
    lower = fname.lower()
    if lower == ".env" or lower.startswith(".env."):
        return True
    suffix = ""
    dot = lower.rfind(".")
    if dot > 0:
        suffix = lower[dot:]
    if suffix not in _PREFIX_RULE_EXEMPT_SUFFIXES:
        for prefix in _SENSITIVE_NAME_PREFIXES:
            if lower.startswith(prefix):
                return True
    if any(lower.endswith(sfx) for sfx in _SENSITIVE_SUFFIXES):
        return True
    return any(part.lower() in _SENSITIVE_DIR_SEGMENTS for part in rel_parts[:-1])


# Suffix → (category, modality). Categories drive accounting; modality is the
# SourceRecord modality for inventoried files.
_CODE_SUFFIXES: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".rs": "rust",
    ".go": "go",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".java": "java",
    ".rb": "ruby",
    ".css": "css",
    ".scss": "css",
    ".html": "html",
    ".vue": "vue",
}
_CONFIG_SUFFIXES: dict[str, str] = {
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".env": "env",
    ".conf": "conf",
    ".lock": "lock",
    ".xml": "xml",
}
_DOC_SUFFIXES: dict[str, str] = {
    ".md": "markdown",
    ".mdx": "markdown",
    ".rst": "rst",
    ".txt": "text",
    ".adoc": "asciidoc",
}
# Binary/asset suffixes are inventoried as metadata sources but classified as a
# binary-asset category so their (often large) bodies are treated conservatively.
_BINARY_SUFFIXES: frozenset[str] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".svg",
        ".pdf",
        ".zip",
        ".gz",
        ".tar",
        ".tgz",
        ".whl",
        ".so",
        ".dylib",
        ".dll",
        ".bin",
        ".dat",
        ".model",
        ".pt",
        ".onnx",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".eot",
        ".mp3",
        ".mp4",
        ".mov",
        ".wav",
        ".pyc",
        ".pyd",
    }
)


def _classify_suffix(suffix: str) -> tuple[str, str]:
    """Return (category, modality) for a file suffix.

    category is one of: python|typescript|... (code langs) / config / document /
    binary_asset / other. modality is the SourceRecord modality:
    code | config | document (binary/other default to config-agnostic 'code'
    only for real code; assets/unknown → 'document' is wrong, so use 'config'
    for config, 'document' for docs, and 'code' for code; binary/other →
    'document' since they are non-parsed acquired artifacts).
    """
    s = suffix.lower()
    if s in _CODE_SUFFIXES:
        return _CODE_SUFFIXES[s], "code"
    if s in _CONFIG_SUFFIXES:
        return "config", "config"
    if s in _DOC_SUFFIXES:
        return "document", "document"
    if s in _BINARY_SUFFIXES:
        return "binary_asset", "document"
    return "other", "document"


def _excluded_category(rel_parts: tuple[str, ...]) -> Optional[str]:
    """Return the exclusion category if any path segment marks an excluded
    subtree, else None. Also handles the ``.claude/worktrees`` and
    ``data/world_models`` (self-model output — self-ingestion guard) cases.
    """
    for i, part in enumerate(rel_parts):
        # self-model output: never re-ingest prior runs' artifacts as evidence
        if (
            part == _SELF_MODEL_OUTPUT_SEGMENT
            and i > 0
            and rel_parts[i - 1] == _SELF_MODEL_OUTPUT_PARENT
        ):
            return "self_model_output"
        # runtime-state boundary: live mutable organism state, never evidence
        if part == _RUNTIME_STATE_SEGMENT and i > 0 and rel_parts[i - 1] == _RUNTIME_STATE_PARENT:
            return "runtime_state"
        cat = _EXCLUDED_DIR_CATEGORY.get(part)
        if cat is not None:
            # 'worktrees' only counts as an exclusion under a .claude/.claire parent
            if part == "worktrees":
                if i > 0 and rel_parts[i - 1] in _WORKTREE_PARENTS:
                    return "worktree"
                continue
            return cat
    return None


@dataclass(frozen=True)
class InventoryResult:
    """Result of a repository inventory pass — sources, observations, accounting."""

    sources: tuple[SourceRecord, ...]
    observations: tuple[ObservationRecord, ...]
    accounting: dict[str, Any] = field(default_factory=dict)


def _read_git_tracked(
    repo_root: Path, caller: str
) -> tuple[Optional[frozenset[str]], Optional[str]]:
    """Return (tracked_relpaths, note). tracked is None when git is unavailable.

    One ``git ls-files`` call — never per-file. Gate returns None under CPU
    overload or when git is missing; both surface as an explicit note.
    """
    proc = gated_subprocess_run(
        ["git", "-C", str(repo_root), "ls-files"],
        caller=caller,
        timeout=30.0,
    )
    if proc is None:
        return None, "git_unavailable:gate_returned_none_or_binary_missing"
    if proc.returncode != 0:
        return None, f"git_unavailable:ls_files_exit_{proc.returncode}"
    tracked = frozenset(line.strip() for line in (proc.stdout or "").splitlines() if line.strip())
    return tracked, None


def _git_head(repo_root: Path, caller: str) -> Optional[str]:
    proc = gated_subprocess_run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        caller=caller,
        timeout=15.0,
    )
    if proc is None or proc.returncode != 0:
        return None
    head = (proc.stdout or "").strip()
    return head or None


def resolve_repository_commit(
    repo_root: str | os.PathLike[str],
) -> tuple[Optional[str], str, Optional[bool]]:
    """Bounded preflight: (head_sha, status, dirty) BEFORE any record is created.

    status is "resolved" or "unavailable". dirty is None when git is
    unavailable — never guessed. The builder calls this first so every
    repository-backed SourceRecord carries the correct commit from record one
    (frozen records cannot be backfilled).
    """
    caller = "reconstruction.repository_inventory.preflight"
    head = _git_head(Path(repo_root), caller)
    if head is None:
        return None, "unavailable", None
    proc = gated_subprocess_run(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        caller=caller,
        timeout=15.0,
    )
    dirty: Optional[bool]
    if proc is None or proc.returncode != 0:
        dirty = None
    else:
        dirty = bool((proc.stdout or "").strip())
    return head, "resolved", dirty


def _artifact_freshness(repo_root: Path, head: Optional[str]) -> dict[str, Any]:
    """Read codebase graph + codewiki manifest freshness WITHOUT trusting counts.

    Compares each artifact's recorded git SHA to HEAD. An artifact with no git
    SHA (the codebase graph records none) is treated as unverifiable → stale.
    Counts are recorded as claims-only inputs, never as observations.
    """
    out: dict[str, Any] = {}

    graph_path = repo_root / "data" / "codebase_graph.json"
    manifest_path = repo_root / "docs" / "codewiki" / "_manifest.json"

    def _load(p: Path) -> Optional[dict[str, Any]]:
        try:
            if not p.is_file():
                return None
            with open(p, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else None
        except Exception as exc:
            logger.debug("artifact freshness read failed for %s: %s", p, exc)
            return None

    graph = _load(graph_path)
    if graph is None:
        out["codebase_graph"] = {"present": False}
    else:
        recorded = graph.get("git_sha") or graph.get("repository_commit")
        fresh = bool(recorded and head and recorded == head)
        out["codebase_graph"] = {
            "present": True,
            "recorded_sha": recorded,
            "head_sha": head,
            "fresh": fresh,
            "stale_reason": (
                None if fresh else ("no_recorded_sha" if not recorded else "sha_mismatch")
            ),
            # claims-only inputs — NOT observations
            "claimed_file_count": graph.get("stats", {}).get("files")
            if isinstance(graph.get("stats"), dict)
            else None,
        }

    manifest = _load(manifest_path)
    if manifest is None:
        out["codewiki_manifest"] = {"present": False}
    else:
        recorded = manifest.get("git_sha") or manifest.get("repository_commit")
        fresh = bool(recorded and head and recorded == head)
        out["codewiki_manifest"] = {
            "present": True,
            "recorded_sha": recorded,
            "head_sha": head,
            "fresh": fresh,
            "stale_reason": (
                None if fresh else ("no_recorded_sha" if not recorded else "sha_mismatch")
            ),
            "claimed_raw_total_files": manifest.get("raw_total_files"),
            "claimed_inventoried": manifest.get("inventoried"),
        }
    return out


def inventory_repository(
    repo_root: str | os.PathLike[str],
    run_id: str,
    activity_id: str,
    *,
    now: Optional[str] = None,
    max_hash_bytes: int = MAX_HASH_BYTES,
    max_paths: Optional[int] = None,
) -> InventoryResult:
    """Inventory a repository tree, accounting for every encountered file.

    FIXED SEAM: ``inventory_repository(repo_root, run_id, activity_id) ->
    InventoryResult``. The builder codes against this signature; keyword-only
    extras (now/max_hash_bytes/max_paths) are optional and default to production
    behavior.

    Args:
        repo_root: repository root to walk.
        run_id: run scope stamped onto every emitted record.
        activity_id: acquisition activity id stamped onto SourceRecords.
        now: fixed ISO timestamp for recorded_at/acquired_at (tests pass a value
            for determinism; production passes None → left unset/None).
        max_hash_bytes: files larger than this are not hashed (metadata + note).
        max_paths: hard cap on inventoried files (bounded real-repo probes).
            Excluded paths are always fully counted; the cap only limits how many
            files are hashed/emitted. When hit, accounting records a
            ``path_cap_reached`` note.

    Returns:
        InventoryResult with per-file SourceRecords, aggregated + surface
        ObservationRecords, and an accounting dict that sums to total_paths.
    """
    root = Path(repo_root).resolve()
    caller = "reconstruction.repository_inventory"

    head = _git_head(root, caller)
    tracked, git_note = _read_git_tracked(root, caller)

    total_paths = 0
    inventoried = 0
    sensitive_presence_only = 0
    excluded_by_category: dict[str, int] = {}
    by_language: dict[str, int] = {}
    git_tracked_count = 0
    git_untracked_count = 0
    notes: list[str] = []
    if git_note:
        notes.append(git_note)

    # Per top-level package: count of inventoried python files (aggregated obs).
    package_py_counts: dict[str, int] = {}

    sources: list[SourceRecord] = []
    surface_observations: list[ObservationRecord] = []

    cap_reached = False

    # Deterministic walk: sort dirs and files at every level.
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        filenames.sort()
        dp = Path(dirpath)
        for fname in filenames:
            total_paths += 1
            fpath = dp / fname
            try:
                rel = fpath.relative_to(root)
            except ValueError:
                rel = Path(fname)
            rel_parts = rel.parts
            rel_str = rel.as_posix()

            excl = _excluded_category(rel_parts)
            if excl is not None:
                excluded_by_category[excl] = excluded_by_category.get(excl, 0) + 1
                continue

            # Symlinks are counted but never hashed/followed.
            if fpath.is_symlink():
                excluded_by_category["symlink"] = excluded_by_category.get("symlink", 0) + 1
                continue

            # Sensitive classification BEFORE stat/hash — presence only, no
            # size/mtime/hash fingerprint of any kind.
            if _is_sensitive(rel_parts, fname):
                sources.append(
                    SourceRecord(
                        subject_path=rel_str,
                        source_kind="repository_file",
                        modality="config",
                        source_content_hash="",
                        activity_id=activity_id,
                        run_id=run_id,
                        repository_commit=head,
                        repository_commit_status=("resolved" if head else "unavailable"),
                        acquisition_context="repository_inventory",
                        redaction_status="redacted",
                        acquired_at=now,
                        recorded_at=now,
                        metadata={
                            "path_class": "sensitive_configuration",
                            "present": True,
                            "content_recorded": False,
                            "hash_recorded": False,
                        },
                    )
                )
                inventoried += 1
                sensitive_presence_only += 1
                continue

            if max_paths is not None and inventoried >= max_paths:
                # Count the path as inventory-eligible-but-capped so totals still
                # sum: record under a dedicated exclusion-like bucket.
                excluded_by_category["path_cap_skipped"] = (
                    excluded_by_category.get("path_cap_skipped", 0) + 1
                )
                cap_reached = True
                continue

            suffix = fpath.suffix
            category, modality = _classify_suffix(suffix)
            lang_key = (
                category
                if category not in ("config", "document", "binary_asset", "other")
                else category
            )
            by_language[lang_key] = by_language.get(lang_key, 0) + 1

            top_pkg = rel_parts[0] if len(rel_parts) > 1 else "<root>"

            try:
                st = fpath.stat()
                size = st.st_size
                mtime = int(st.st_mtime)
            except OSError:
                excluded_by_category["stat_error"] = excluded_by_category.get("stat_error", 0) + 1
                continue

            metadata: dict[str, Any] = {
                "size_bytes": size,
                "mtime": mtime,
                "category": category,
                "language": category if category in _CODE_SUFFIXES.values() else None,
                "top_level_package": top_pkg,
                "suffix": suffix.lower(),
            }

            is_tracked: Optional[bool]
            if tracked is None:
                is_tracked = None  # git unavailable — do not guess
            else:
                is_tracked = rel_str in tracked
                if is_tracked:
                    git_tracked_count += 1
                else:
                    git_untracked_count += 1
            metadata["git_tracked"] = is_tracked

            # Bounded hashing: only files <= max_hash_bytes and not binary.
            if size > max_hash_bytes:
                chash = ""
                metadata["hash_skipped"] = "oversized"
                metadata["note"] = (
                    f"size {size} > max_hash_bytes {max_hash_bytes}; metadata only, no hash"
                )
            else:
                try:
                    body = fpath.read_bytes()
                    chash = content_hash(body)
                except OSError:
                    chash = ""
                    metadata["hash_skipped"] = "read_error"
                    metadata["note"] = "unreadable; metadata only, no hash"

            if not chash:
                metadata["hash_recorded"] = False

            sources.append(
                SourceRecord(
                    subject_path=rel_str,
                    source_kind="repository_file",
                    modality=modality,  # code | config | document
                    source_content_hash=chash,
                    activity_id=activity_id,
                    run_id=run_id,
                    repository_commit=head,
                    repository_commit_status="resolved" if head else "unavailable",
                    acquisition_context="repository_inventory",
                    redaction_status="none",
                    acquired_at=now,
                    recorded_at=now,
                    metadata=metadata,
                )
            )
            inventoried += 1

            if suffix.lower() in (".py", ".pyi"):
                package_py_counts[top_pkg] = package_py_counts.get(top_pkg, 0) + 1
                # Per-file observation ONLY for the decision-relevant surface.
                if top_pkg in DECISION_SURFACE_DIRS and suffix.lower() == ".py":
                    surface_observations.append(
                        ObservationRecord(
                            subject=f"file:{rel_str}",
                            predicate="source_present",
                            value=True,
                            observation_kind="maturity",
                            maturity_facet="source_present",
                            source_id=sources[-1].id,
                            run_id=run_id,
                            scope=top_pkg,
                            valid_time=ValidTime(qualifier="unknown"),
                            recorded_at=now,
                            support={
                                "source_content_hash": chash,
                                "size_bytes": size,
                            },
                        )
                    )

    if cap_reached:
        notes.append(f"path_cap_reached:{max_paths}")

    # Aggregated per-package observations (python file counts). The aggregate
    # is a DERIVED artifact: extraction_hash is the hash of the actual derived
    # payload (the counts), and derivation lineage points at the inventory
    # activity — never a fabricated label hash posing as acquired content.
    agg_payload = {"package_py_counts": dict(sorted(package_py_counts.items()))}
    agg_extraction_hash = content_hash(agg_payload)
    agg_src = SourceRecord(
        subject_path="aggregate:repository_inventory",
        source_kind="derived_artifact",
        modality="derived",
        source_content_hash="",
        extraction_hash=agg_extraction_hash,
        derivation_key=agg_extraction_hash,
        derivation_activity_id=activity_id,
        activity_id=activity_id,
        run_id=run_id,
        repository_commit=head,
        repository_commit_status="resolved" if head else "unavailable",
        acquisition_context="aggregated per-package python file counts",
        acquired_at=now,
        recorded_at=now,
        metadata={
            "kind": "aggregate",
            "content_recorded": False,
            "input_lineage": (
                "inputs are the repository_file sources generated by the same "
                "inventory activity; complete lineage on the activity record"
            ),
        },
    )
    sources.append(agg_src)
    agg_source_id = agg_src.id
    aggregate_observations: list[ObservationRecord] = []
    for pkg in sorted(package_py_counts):
        aggregate_observations.append(
            ObservationRecord(
                subject=f"package:{pkg}",
                predicate="python_files_present",
                value=package_py_counts[pkg],
                observation_kind="aggregate_count",
                maturity_facet="source_present",
                source_id=agg_source_id,
                run_id=run_id,
                scope=pkg,
                valid_time=ValidTime(qualifier="unknown"),
                recorded_at=now,
                support={"kind": "aggregate_count"},
            )
        )

    observations = tuple(aggregate_observations + surface_observations)

    accounting: dict[str, Any] = {
        "total_encountered_files": total_paths,
        "inventoried": inventoried,
        "sensitive_presence_only": sensitive_presence_only,
        "excluded_by_category": dict(sorted(excluded_by_category.items())),
        "by_language": dict(sorted(by_language.items())),
        "git_tracked": git_tracked_count,
        "git_untracked": git_untracked_count,
        "head_sha": head,
        "git_available": tracked is not None,
        "artifact_freshness": _artifact_freshness(root, head),
        "notes": notes,
        "counts_reconcile": total_paths == inventoried + sum(excluded_by_category.values()),
    }

    return InventoryResult(
        sources=tuple(sources),
        observations=observations,
        accounting=accounting,
    )
