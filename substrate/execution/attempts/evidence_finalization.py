"""One-way evidence finalization (R1 — CRITICAL SEC-C1).

The previous pipeline was self-invalidating in two ways:

1. It hashed every artifact, then rewrote those same files with a redaction pass,
   then wrote the manifest — so the recorded hashes described bytes that no
   longer existed on disk and could never re-verify.
2. Its redaction rule matched **any** bare 64-hex string, which destroyed the
   legitimate ``artifact_sha256`` / ``package_hash`` / ``scope_hash`` values and
   docker image IDs that the manifest's integrity claim depends on.

The order is now strictly one-way, and hashing happens LAST:

    collect  →  bounded extraction
             →  exact-value + typed-credential redaction
             →  second secret scan (fail closed on residue)
             →  FINALIZE (no file is ever rewritten again)
             →  per-file hashes
             →  manifest
             →  detached manifest hash

Redaction targets *known secret values* and *typed credential formats* — never
arbitrary hashes. A 40-hex git SHA, a 64-hex sha256 artifact hash, a package or
scope hash and a ``sha256:...`` image ID all survive verbatim, because the
evidence chain is built on them.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

# Typed credential formats. These are SHAPES that are always secret, never a
# hash. Deliberately does NOT include a bare-hex rule (see module docstring).
_TYPED_SECRET_PATTERNS: tuple[str, ...] = (
    r"sk-ant-[A-Za-z0-9_\-]{20,}",  # Anthropic API key
    r"sk-[A-Za-z0-9]{32,}",  # generic provider key
    r"eyJ[A-Za-z0-9._\-]{20,}",  # JWT
    r"bearer\s+[A-Za-z0-9._\-]{16,}",  # bearer token
    r"gh[pousr]_[A-Za-z0-9]{20,}",  # GitHub token
    r"\b(?:password|passwd|secret|token|api[_-]?key)\b\s*[=:]\s*\S+",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",  # private key block
    r"tskey-[A-Za-z0-9\-]{10,}",  # Tailscale auth key
)

# Case-insensitivity is a COMPILE flag: an inline (?i) inside a joined
# alternation raises "global flags not at the start of the expression".
_TYPED_SECRET_RE = re.compile("|".join(_TYPED_SECRET_PATTERNS), re.IGNORECASE)

_REDACTED = "<redacted>"

# Keys whose values are legitimate integrity hashes and must never be redacted.
_HASH_KEYS = frozenset(
    {
        "artifact_sha256",
        "dist_index_sha256",
        "manifest_sha256",
        "package_hash",
        "payload_hash",
        "authorized_scope_hash",
        "scope_hash",
        "container_image_id",
        "fixture_base_sha",
        "candidate_sha",
        "base_commit",
        "commit",
        "sha256",
    }
)


class EvidenceFinalizationError(RuntimeError):
    """Raised when evidence cannot be safely finalized (fail closed)."""


@dataclass
class FinalizedEvidence:
    """An immutable, hashed evidence package."""

    root: str
    files: dict[str, dict[str, Any]] = field(default_factory=dict)  # relpath -> {bytes, sha256}
    manifest_path: str = ""
    manifest_sha256: str = ""
    redacted_files: list[str] = field(default_factory=list)
    secret_scan_clean: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "file_count": len(self.files),
            "files": self.files,
            "manifest_path": self.manifest_path,
            "manifest_sha256": self.manifest_sha256,
            "redacted_files": list(self.redacted_files),
            "secret_scan_clean": self.secret_scan_clean,
        }


def redact_text(text: str, *, exact_values: Iterable[str] = ()) -> str:
    """Redact known exact secret values and typed credential formats.

    Legitimate hashes are preserved: this never matches a bare hex string.
    """
    out = text
    # Exact known values first (e.g. this run's dispatch secret) — longest first
    # so a value that contains another is not partially replaced.
    for value in sorted({v for v in exact_values if v and len(v) >= 8}, key=len, reverse=True):
        out = out.replace(value, _REDACTED)
    return _TYPED_SECRET_RE.sub(_REDACTED, out)


def scan_for_secrets(text: str, *, exact_values: Iterable[str] = ()) -> list[str]:
    """Return descriptions of any secret material still present (empty == clean)."""
    findings: list[str] = []
    for value in exact_values:
        if value and len(value) >= 8 and value in text:
            findings.append("exact known secret value present")
            break
    if _TYPED_SECRET_RE.search(text):
        findings.append("typed credential format present")
    return findings


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _iter_evidence_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and p.name != "manifest.json")


def finalize_evidence(
    root: str | Path,
    *,
    exact_values: Iterable[str] = (),
    extra_manifest: dict[str, Any] | None = None,
) -> FinalizedEvidence:
    """Run the one-way pipeline over an evidence tree and return the package.

    After this returns, NO file in the tree may be modified — the manifest's
    hashes describe the final bytes exactly.
    """
    root_path = Path(root)
    if not root_path.is_dir():
        raise EvidenceFinalizationError(f"evidence root does not exist: {root_path}")

    exact = list(exact_values)
    redacted_files: list[str] = []

    # 1. REDACT (text-like files only; binary artifacts such as screenshots are
    #    hashed as-is and never rewritten).
    for path in _iter_evidence_files(root_path):
        if path.suffix.lower() not in (".json", ".jsonl", ".txt", ".log", ".md", ".html"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        redacted = redact_text(text, exact_values=exact)
        if redacted != text:
            path.write_text(redacted, encoding="utf-8")
            redacted_files.append(str(path.relative_to(root_path)))

    # 2. SECOND SCAN — fail closed if any secret survived redaction.
    residue: list[str] = []
    for path in _iter_evidence_files(root_path):
        if path.suffix.lower() not in (".json", ".jsonl", ".txt", ".log", ".md", ".html"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        found = scan_for_secrets(text, exact_values=exact)
        if found:
            residue.append(f"{path.relative_to(root_path)}: {', '.join(found)}")
    if residue:
        raise EvidenceFinalizationError(
            "secret material survived redaction — refusing to finalize: " + "; ".join(residue[:5])
        )

    # 3. FINALIZE + HASH. From here the bytes are immutable; hashing happens
    #    AFTER every mutation so each recorded hash describes the final file.
    files: dict[str, dict[str, Any]] = {}
    for path in _iter_evidence_files(root_path):
        data = path.read_bytes()
        files[str(path.relative_to(root_path))] = {
            "bytes": len(data),
            "sha256": _sha256_bytes(data),
        }

    # 4. MANIFEST (never self-hashing: it is excluded from the file list).
    manifest: dict[str, Any] = dict(extra_manifest or {})
    manifest["files"] = files
    manifest["file_count"] = len(files)
    manifest["redacted_files"] = redacted_files
    manifest["secret_scan_clean"] = True
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    manifest_path = root_path / "manifest.json"
    manifest_path.write_bytes(manifest_bytes)

    # 5. DETACHED manifest hash — published in the qualification report so the
    #    package can be verified end to end without trusting the manifest itself.
    manifest_sha = _sha256_bytes(manifest_bytes)
    (root_path / "manifest.sha256").write_text(manifest_sha + "\n", encoding="utf-8")

    return FinalizedEvidence(
        root=str(root_path),
        files=files,
        manifest_path=str(manifest_path),
        manifest_sha256=manifest_sha,
        redacted_files=redacted_files,
        secret_scan_clean=True,
    )


def verify_evidence(root: str | Path) -> dict[str, Any]:
    """Re-verify a finalized package byte-for-byte. Deterministic and repeatable.

    Returns ``{"ok": bool, "mismatched": [...], "missing": [...], "extra": [...],
    "manifest_sha256_ok": bool}``. Used after transfer and after restart.
    """
    root_path = Path(root)
    manifest_path = root_path / "manifest.json"
    if not manifest_path.is_file():
        return {"ok": False, "error": "manifest.json missing"}

    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    recorded = manifest.get("files", {})

    mismatched: list[str] = []
    missing: list[str] = []
    for rel, meta in recorded.items():
        p = root_path / rel
        if not p.is_file():
            missing.append(rel)
            continue
        data = p.read_bytes()
        if _sha256_bytes(data) != meta.get("sha256") or len(data) != meta.get("bytes"):
            mismatched.append(rel)

    on_disk = {str(p.relative_to(root_path)) for p in _iter_evidence_files(root_path)}
    extra = sorted(on_disk - set(recorded) - {"manifest.sha256"})

    detached = root_path / "manifest.sha256"
    manifest_sha_ok = False
    if detached.is_file():
        manifest_sha_ok = detached.read_text(encoding="utf-8").strip() == _sha256_bytes(
            manifest_bytes
        )

    return {
        "ok": not mismatched and not missing and not extra and manifest_sha_ok,
        "mismatched": mismatched,
        "missing": missing,
        "extra": extra,
        "manifest_sha256_ok": manifest_sha_ok,
        "file_count": len(recorded),
    }


__all__ = [
    "EvidenceFinalizationError",
    "FinalizedEvidence",
    "finalize_evidence",
    "redact_text",
    "scan_for_secrets",
    "verify_evidence",
]
