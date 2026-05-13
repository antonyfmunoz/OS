"""LocalFileSource — reads a single local file as an ingestion source."""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Any

from runtime.ingestion.authority_tier import T5_DEFAULT, validate_tier
from runtime.ingestion.source import RawContent, Source


class LocalFileSource:
    """Wraps a single absolute file path as a Source."""

    source_type: str = "local_file"

    def __init__(self, path: Path | str, *, authority_tier: int = T5_DEFAULT) -> None:
        self._path = Path(path).resolve()
        self._cached_content: RawContent | None = None
        self.authority_tier: int = validate_tier(authority_tier)

    @property
    def source_id(self) -> str:
        if self._cached_content is not None:
            return self._cached_content.sha256
        return f"local:{self._path}"

    def exists(self) -> bool:
        return self._path.is_file()

    def read(self) -> RawContent:
        text = self._path.read_text(encoding="utf-8")
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        content_type = mimetypes.guess_type(str(self._path))[0] or "text/plain"
        self._cached_content = RawContent(
            content=text,
            content_type=content_type,
            size_bytes=len(text.encode("utf-8")),
            sha256=sha,
        )
        return self._cached_content

    def metadata(self) -> dict[str, Any]:
        stat = self._path.stat() if self._path.exists() else None
        return {
            "path": str(self._path),
            "filename": self._path.name,
            "extension": self._path.suffix,
            "size_bytes": stat.st_size if stat else 0,
            "mtime": stat.st_mtime if stat else 0,
            "content_type": mimetypes.guess_type(str(self._path))[0] or "text/plain",
        }


assert isinstance(LocalFileSource, type)
_check: type[Source] = LocalFileSource  # type: ignore[assignment]  # protocol conformance
