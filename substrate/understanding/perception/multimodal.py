"""Multi-modal understanding — turn operator-attached media into meaning.

This is the ONE canonical seam that lets the assistant understand the content of
an image, video, audio file, document, or link that an operator sends — on ANY
surface (cockpit browser, CLI, desktop, mobile). It is called from
``AdvisorConversation.converse()`` so every transport benefits through one path;
it is NEVER wired per-transport.

Layer: substrate/understanding/perception (universal perception — "perceives and
interprets, does NOT execute"). It calls DOWN into adapters (Gemini via the model
router) and execution (local Whisper STT), never up into transports.

Everything here is FREE:
  - image / video / pdf  → Gemini 2.5 Flash (GEMINI_API_KEY free tier) via
    ``call_with_fallback(images=[(bytes, mime)], task_type="multimodal")``.
  - audio                → local faster-whisper (``VoiceEngine.transcribe_fast``).
  - link (URL in text)   → stdlib fetch + Gemini summary of the page text.

Deterministic-first: every understander degrades to a short factual descriptor
(filename / type / "unavailable") if its provider is down, so converse() always
gets a usable string and the conversation never breaks.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Gemini accepts these inline mime prefixes directly (image, video, pdf, audio).
# We route image/video/pdf to the vision model; audio goes to local Whisper.
_MAX_UNDERSTAND_BYTES = 20 * 1024 * 1024  # 20 MB — Gemini inline ceiling headroom
_LINK_RE = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)
_LINK_FETCH_TIMEOUT = 8
_LINK_MAX_CHARS = 6000


@dataclass
class MediaUnderstanding:
    """One understood attachment (or link)."""

    media_type: str  # image | video | audio | file | link
    label: str  # short human label, e.g. "image chart.png" or the URL
    understanding: str  # the extracted meaning / transcript / description
    ok: bool = True  # False when the provider failed and this is a degraded stub


@dataclass
class PerceptionResult:
    """The full multi-modal perception for one converse turn."""

    items: list[MediaUnderstanding] = field(default_factory=list)

    def as_prompt_context(self) -> str:
        """Render the understandings as a text block to fold into the LLM prompt.

        Returns "" when there is nothing understood, so callers can append
        unconditionally.
        """
        if not self.items:
            return ""
        lines = ["\n\n[Attached content the operator shared — understood for you:]"]
        for it in self.items:
            lines.append(f"- {it.label} ({it.media_type}): {it.understanding}")
        return "\n".join(lines)


def _media_dir() -> Path:
    return Path(os.environ.get("UMH_ROOT", "/opt/OS")) / "data" / "chat_media"


def _read_media_bytes(media_id: str) -> bytes | None:
    """Read an uploaded artifact's bytes by id. Path-traversal safe."""
    if not media_id or "/" in media_id or ".." in media_id or media_id.startswith("."):
        return None
    p = _media_dir() / media_id
    try:
        if not p.is_file() or p.stat().st_size > _MAX_UNDERSTAND_BYTES:
            return None
        return p.read_bytes()
    except Exception as exc:  # never break converse on a read error
        logger.debug("media read failed for %s: %s", media_id, exc)
        return None


def _vision_understand(prompt: str, data: bytes, mime: str) -> str | None:
    """Free Gemini vision/video/pdf understanding via the model router."""
    try:
        from substrate.sockets.intelligence_port import call_with_fallback

        result = call_with_fallback(
            prompt=prompt,
            task_type="multimodal",
            images=[(data, mime)],
        )
        if result is None:
            return None
        out = getattr(result, "output", None) or getattr(result, "content", None)
        if not out and isinstance(result, str):
            out = result
        return (out or "").strip() or None
    except Exception as exc:
        logger.debug("vision understanding failed: %s", exc)
        return None


def _audio_transcribe(media_id: str) -> str | None:
    """Free local Whisper transcription of an uploaded audio file."""
    try:
        p = _media_dir() / media_id
        if not p.is_file():
            return None
        from substrate.execution.voice.warm_engine import get_warm_engine

        text = get_warm_engine().transcribe_fast(str(p))
        return (text or "").strip() or None
    except Exception as exc:
        logger.debug("audio transcription failed: %s", exc)
        return None


def _fetch_link_text(url: str) -> str | None:
    """Fetch a URL and strip to readable text (stdlib only, bounded)."""
    try:
        import urllib.request

        req = urllib.request.Request(url, headers={"User-Agent": "UMH-Assistant/1.0"})
        with urllib.request.urlopen(req, timeout=_LINK_FETCH_TIMEOUT) as r:
            ctype = r.headers.get("Content-Type", "")
            raw = r.read(2 * 1024 * 1024)  # cap 2 MB
        if "html" in ctype or url.lower().endswith((".html", "/", ".htm")) or "text" in ctype:
            html = raw.decode("utf-8", errors="ignore")
            # crude readability: drop scripts/styles/tags, collapse whitespace
            html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
            text = re.sub(r"(?s)<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:_LINK_MAX_CHARS] or None
        return None
    except Exception as exc:
        logger.debug("link fetch failed for %s: %s", url, exc)
        return None


def _link_understand(url: str) -> str | None:
    """Fetch a link and summarize its content with the free LLM."""
    page = _fetch_link_text(url)
    if not page:
        return None
    try:
        from substrate.sockets.intelligence_port import call_with_fallback

        result = call_with_fallback(
            prompt=(
                "Summarize what this web page is about in 2-3 sentences so a "
                f"colleague understands it without opening it:\n\n{page}"
            ),
            task_type="summarize",
        )
        out = getattr(result, "output", None) or getattr(result, "content", None)
        if not out and isinstance(result, str):
            out = result
        return (out or "").strip() or None
    except Exception as exc:
        logger.debug("link summarize failed: %s", exc)
        return None


def understand_media(
    media: list[dict[str, Any]] | None,
    text: str = "",
) -> PerceptionResult:
    """Understand every attachment + any link in ``text``. FREE, best-effort.

    ``media`` items are MediaAttachment dicts: ``{id, filename, content_type,
    media_type, ...}``. ``text`` is the operator's message (scanned for URLs).
    Returns a PerceptionResult whose ``as_prompt_context()`` folds into the LLM
    prompt so the assistant reasons over the media content, not just the words.
    """
    result = PerceptionResult()

    for m in media or []:
        media_type = str(m.get("media_type", "file"))
        mime = str(m.get("content_type", "application/octet-stream")).split(";")[0].strip()
        media_id = str(m.get("id", ""))
        filename = str(m.get("filename", "") or media_id)
        label = f"{media_type} {filename}".strip()

        if media_type in ("image", "video"):
            data = _read_media_bytes(media_id)
            if data:
                verb = "video clip" if media_type == "video" else "image"
                desc = _vision_understand(
                    f"Describe this {verb} in detail — what it shows, any text, "
                    "and anything notable an assistant should know to help the operator.",
                    data,
                    mime,
                )
                if desc:
                    result.items.append(MediaUnderstanding(media_type, label, desc))
                    continue
            result.items.append(
                MediaUnderstanding(
                    media_type, label, f"({media_type} attached; could not be analyzed)", ok=False
                )
            )

        elif media_type == "audio":
            transcript = _audio_transcribe(media_id)
            if transcript:
                result.items.append(MediaUnderstanding("audio", label, f"transcript: {transcript}"))
            else:
                result.items.append(
                    MediaUnderstanding(
                        "audio", label, "(audio attached; could not be transcribed)", ok=False
                    )
                )

        else:  # file (pdf, doc, csv, arbitrary)
            data = _read_media_bytes(media_id)
            # PDFs go to Gemini inline (application/pdf is a supported vision mime);
            # other files without a text path get a factual stub.
            if data and mime == "application/pdf":
                desc = _vision_understand(
                    "Read this document and summarize its key content so an "
                    "assistant can help the operator discuss it.",
                    data,
                    mime,
                )
                if desc:
                    result.items.append(MediaUnderstanding("file", label, desc))
                    continue
            result.items.append(
                MediaUnderstanding("file", label, f"({filename} attached — {mime})", ok=False)
            )

    # Links in the operator's own text.
    seen: set[str] = set()
    for url in _LINK_RE.findall(text or ""):
        url = url.rstrip(".,);]")
        if url in seen:
            continue
        seen.add(url)
        summary = _link_understand(url)
        if summary:
            result.items.append(MediaUnderstanding("link", url, summary))
        # a dead/unfetchable link is silently skipped — the URL is still in `text`

    return result
