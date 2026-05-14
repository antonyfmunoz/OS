"""GWSSource — wraps GWSDocumentScanner as an ingestion Source."""

from __future__ import annotations

import hashlib
from typing import Any

from governance.policy.authority_tier import T5_DEFAULT, validate_tier
from understanding.perception.source import RawContent, Source


class GWSSource:
    """Reads a single Google Workspace document via GWSDocumentScanner.

    Wraps the scanner's read_doc() and list_all_docs() without
    duplicating any GWS API logic. The scanner handles CLI invocation,
    temp files, and error recovery.
    """

    source_type: str = "google_workspace"

    def __init__(
        self,
        doc_id: str,
        scanner: Any,
        doc_meta: dict[str, Any] | None = None,
        *,
        authority_tier: int = T5_DEFAULT,
    ) -> None:
        """Initialize with a GWS document ID and a GWSDocumentScanner instance.

        Args:
            doc_id: Google Docs document ID.
            scanner: A GWSDocumentScanner instance (or any object with
                read_doc(doc_id) -> str and list_all_docs() -> list[dict]).
            doc_meta: Optional pre-fetched metadata dict from list_all_docs().
                Keys: id, name, mimeType, modifiedTime, webViewLink.
            authority_tier: Authority tier (1-9). Default T5_DEFAULT.
        """
        self._doc_id = doc_id
        self._scanner = scanner
        self._doc_meta = doc_meta or {}
        self._cached_content: RawContent | None = None
        self.authority_tier: int = validate_tier(authority_tier)

    @property
    def source_id(self) -> str:
        return f"gws:{self._doc_id}"

    def exists(self) -> bool:
        """Check if the document is accessible via the scanner."""
        if self._doc_meta and self._doc_meta.get("id") == self._doc_id:
            return True
        docs = self._scanner.list_all_docs(limit=500)
        return any(d.get("id") == self._doc_id for d in docs)

    def read(self) -> RawContent:
        """Read document content via scanner.read_doc()."""
        if self._cached_content is not None:
            return self._cached_content

        text = self._scanner.read_doc(self._doc_id)
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self._cached_content = RawContent(
            content=text,
            content_type="text/plain",
            size_bytes=len(text.encode("utf-8")),
            sha256=sha,
        )
        return self._cached_content

    def metadata(self) -> dict[str, Any]:
        """Map GWS document metadata to standard ingestion metadata dict."""
        return {
            "path": self._doc_meta.get("webViewLink", f"gws://{self._doc_id}"),
            "filename": self._doc_meta.get("name", self._doc_id),
            "extension": ".gdoc",
            "size_bytes": self._cached_content.size_bytes if self._cached_content else 0,
            "mtime": self._doc_meta.get("modifiedTime", ""),
            "content_type": "text/plain",
            "doc_id": self._doc_id,
            "source_system": "google_workspace",
            "mime_type": self._doc_meta.get("mimeType", "application/vnd.google-apps.document"),
        }


assert isinstance(GWSSource, type)
_check: type[Source] = GWSSource  # type: ignore[assignment]  # protocol conformance
