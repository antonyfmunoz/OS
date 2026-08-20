#!/usr/bin/env python3
"""Build a slim immutable UMH mesh runtime release from an exact source tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

ALLOWLIST_PATHS = (
    "pyproject.toml",
    "requirements.txt",
    "scripts/op_run.sh",
    "services/mesh.env.tpl",
    "substrate",
    "transports/__init__.py",
    "transports/node_mesh",
)
REQUIRED_RELATIVE_PATHS = (
    "scripts/op_run.sh",
    "services/mesh.env.tpl",
    "transports/node_mesh/run.py",
    "transports/node_mesh/server.py",
    "substrate/execution/durable_remote_transport.py",
)
EXCLUDED_PARTS = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    ".ruff_cache",
    ".claude",
    ".codex",
    "cache",
    "caches",
    "credential",
    "credentials",
    "node_modules",
    "data",
    "evidence",
    "preservation",
}
MAX_RELEASE_BYTES = 512 * 1024 * 1024


def _excluded_path(rel_parts: tuple[str, ...]) -> bool:
    if any(part in EXCLUDED_PARTS for part in rel_parts):
        return True
    if rel_parts and rel_parts[0] in {"data", "evidence", "preservation", "runtime"}:
        return True
    # The mesh transport runtime package has no code directory named runtime.
    # If one appears there, treat it as node-local mutable state until explicitly
    # reviewed into the dependency closure.
    return len(rel_parts) >= 3 and rel_parts[:2] == ("transports", "node_mesh") and "runtime" in rel_parts


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_sha(source_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"could not resolve source git SHA: {exc}") from exc


def _tracked_files(source_root: Path) -> set[Path] | None:
    try:
        output = subprocess.check_output(
            ["git", "-C", str(source_root), "ls-files", "-z"],
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None
    tracked: set[Path] = set()
    for raw in output.split(b"\0"):
        if raw:
            tracked.add((source_root / raw.decode("utf-8")).resolve())
    return tracked


def _iter_included_files(source_root: Path) -> list[Path]:
    files: list[Path] = []
    tracked = _tracked_files(source_root)
    for rel in ALLOWLIST_PATHS:
        path = source_root / rel
        if not path.exists():
            continue
        if path.is_symlink():
            raise SystemExit(f"refusing symlink in mesh runtime release: {rel}")
        if path.is_file():
            if tracked is None or path.resolve() in tracked:
                files.append(path)
            continue
        for child in path.rglob("*"):
            rel_parts = child.relative_to(source_root).parts
            if _excluded_path(rel_parts):
                continue
            if child.is_symlink():
                raise SystemExit(
                    "refusing symlink in mesh runtime release: "
                    f"{child.relative_to(source_root)}"
                )
            if child.is_file():
                if tracked is not None and child.resolve() not in tracked:
                    continue
                files.append(child)
    return sorted(files)


def build_release(
    *,
    source_root: Path,
    output_root: Path,
    source_sha: str,
    max_bytes: int = MAX_RELEASE_BYTES,
) -> Path:
    source_root = source_root.resolve()
    output_root = output_root.resolve()
    included = _iter_included_files(source_root)
    rels = {str(path.relative_to(source_root)).replace("\\", "/") for path in included}
    missing = [rel for rel in REQUIRED_RELATIVE_PATHS if rel not in rels]
    if missing:
        raise SystemExit(f"missing required mesh runtime files: {missing}")

    total_bytes = sum(path.stat().st_size for path in included)
    if total_bytes > max_bytes:
        raise SystemExit(
            f"mesh runtime artifact would be {total_bytes} bytes, exceeding ceiling {max_bytes}"
        )

    content_digest = hashlib.sha256()
    file_manifest: list[dict[str, object]] = []
    for path in included:
        rel = str(path.relative_to(source_root)).replace("\\", "/")
        digest = _sha256_file(path)
        size = path.stat().st_size
        content_digest.update(rel.encode("utf-8"))
        content_digest.update(str(size).encode("ascii"))
        content_digest.update(digest.encode("ascii"))
        file_manifest.append({"path": rel, "size": size, "sha256": digest})

    artifact_digest = content_digest.hexdigest()
    release_dir = output_root / f"{source_sha}-{artifact_digest}"
    staging_dir = output_root / f".{release_dir.name}.staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)
    for path in included:
        rel = path.relative_to(source_root)
        dest = staging_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

    manifest = {
        "source_sha": source_sha,
        "artifact_digest": artifact_digest,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "entry_point": "transports/node_mesh/run.py",
        "max_release_bytes": max_bytes,
        "total_bytes": total_bytes,
        "allowlist": list(ALLOWLIST_PATHS),
        "excluded_parts": sorted(EXCLUDED_PARTS),
        "files": file_manifest,
    }
    (staging_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging_dir / "SOURCE_SHA").write_text(source_sha + "\n", encoding="ascii")
    sha_lines = [
        f"{entry['sha256']}  {entry['path']}"
        for entry in sorted(file_manifest, key=lambda item: str(item["path"]))
    ]
    (staging_dir / "SHA256SUMS").write_text("\n".join(sha_lines) + "\n", encoding="utf-8")
    if release_dir.exists():
        shutil.rmtree(staging_dir)
    else:
        staging_dir.rename(release_dir)
    return release_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", default=str(Path.cwd()))
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--source-sha", default="")
    parser.add_argument("--max-bytes", type=int, default=MAX_RELEASE_BYTES)
    args = parser.parse_args(argv)

    source_root = Path(args.source_root)
    source_sha = args.source_sha or _source_sha(source_root)
    release_dir = build_release(
        source_root=source_root,
        output_root=Path(args.output_root),
        source_sha=source_sha,
        max_bytes=args.max_bytes,
    )
    print(str(release_dir), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
