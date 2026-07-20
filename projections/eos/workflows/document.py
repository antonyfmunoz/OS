"""Document generation workflow — governed document creation.

Wraps existing doc_creator adapter functions so every document
generated goes through governed mutation and the organism learns.

Supported doc_types:
  briefing, board_update, investor_update, proposal,
  slides, announcement, crisis
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from projections.eos.workflows.types import WorkflowStep

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def _runtime_state_file(subsystem: str, filename: str) -> str:
    from substrate.state.runtime_paths import runtime_state_path

    return str(runtime_state_path(subsystem, filename, create_parent=False))


_DOCS_DIR = os.path.join(_REPO_ROOT, "data", "umh", "documents")

VALID_DOC_TYPES = {
    "briefing",
    "board_update",
    "investor_update",
    "proposal",
    "slides",
    "announcement",
    "crisis",
}


@dataclass
class DocumentContext:
    doc_type: str = "briefing"
    title: str = ""
    topic: str = ""
    context: str = ""
    audience: str = ""
    # announcement-specific
    key_message: str = ""
    announcement_type: str = "internal"
    # crisis-specific
    affected_parties: str = ""
    what_happened: str = ""
    what_we_are_doing: str = ""
    # slides-specific
    slide_count: int = 10


class DocumentWorkflow:
    """Document generation workflow through governed mutation."""

    def __init__(self, org_id: str = "", venture_id: str = "") -> None:
        self._org_id = org_id
        self._venture_id = venture_id
        self._doc_ctx: DocumentContext | None = None
        self._content: str = ""
        self._result: dict[str, Any] = {}

    def generate_steps(
        self, doc_type: str, context: dict[str, Any] | None = None
    ) -> list[WorkflowStep]:
        """Build governed steps for document generation."""
        if doc_type not in VALID_DOC_TYPES:
            doc_type = "briefing"

        ctx = context or {}
        self._doc_ctx = DocumentContext(
            doc_type=doc_type,
            title=ctx.get("title", ""),
            topic=ctx.get("topic", ""),
            context=ctx.get("context", ""),
            audience=ctx.get("audience", ""),
            key_message=ctx.get("key_message", ""),
            announcement_type=ctx.get("announcement_type", "internal"),
            affected_parties=ctx.get("affected_parties", ""),
            what_happened=ctx.get("what_happened", ""),
            what_we_are_doing=ctx.get("what_we_are_doing", ""),
            slide_count=ctx.get("slide_count", 10),
        )

        return [
            WorkflowStep(
                name="validate_request",
                mutation_name="command_submit",
                intent=f"Validate document request: {doc_type}",
                execute_fn=self._validate_request,
            ),
            WorkflowStep(
                name="generate_document",
                mutation_name="file_write",
                intent=f"Generate {doc_type} document",
                execute_fn=self._generate_document,
            ),
            WorkflowStep(
                name="store_document",
                mutation_name="file_write",
                intent=f"Store {doc_type} document locally",
                execute_fn=self._store_document,
            ),
        ]

    def _validate_request(self) -> tuple[str, bool]:
        if not self._doc_ctx:
            return ("no document context provided", False)

        dc = self._doc_ctx
        if dc.doc_type not in VALID_DOC_TYPES:
            return (f"invalid doc_type: {dc.doc_type}", False)

        if dc.doc_type in ("briefing", "board_update", "investor_update", "proposal"):
            if not dc.topic:
                dc.topic = dc.title or dc.doc_type.replace("_", " ").title()
            if not dc.title:
                dc.title = dc.topic

        if dc.doc_type == "slides":
            if not dc.topic:
                dc.topic = dc.title or "Presentation"
            if not dc.title:
                dc.title = dc.topic

        if dc.doc_type == "announcement":
            if not dc.topic:
                return ("announcement requires a topic", False)

        if dc.doc_type == "crisis":
            if not dc.what_happened:
                return ("crisis communication requires what_happened", False)

        return (
            f"Validated: {dc.doc_type} — {dc.title or dc.topic}",
            True,
        )

    def _generate_document(self) -> tuple[str, bool]:
        if not self._doc_ctx:
            return ("no document context", False)

        dc = self._doc_ctx

        if dc.doc_type in ("briefing", "board_update", "investor_update", "proposal"):
            return self._generate_briefing_doc(dc)
        elif dc.doc_type == "slides":
            return self._generate_slides(dc)
        elif dc.doc_type == "announcement":
            return self._generate_announcement(dc)
        elif dc.doc_type == "crisis":
            return self._generate_crisis(dc)
        else:
            return (f"unsupported doc_type: {dc.doc_type}", False)

    def _generate_briefing_doc(self, dc: DocumentContext) -> tuple[str, bool]:
        try:
            from adapters.google_workspace.doc_creator import create_briefing_doc

            result = create_briefing_doc(
                title=dc.title,
                topic=dc.topic,
                context=dc.context,
                audience=dc.audience or "Antony",
                doc_type=dc.doc_type,
            )
            if result.get("content"):
                self._content = result["content"]
                self._result = result
                return (f"Generated {dc.doc_type}: {dc.title}", True)
        except Exception as exc:
            logger.debug("briefing doc generation failed: %s", exc)

        self._content = self._deterministic_briefing(dc)
        return (f"Generated {dc.doc_type} (template fallback): {dc.title}", True)

    def _generate_slides(self, dc: DocumentContext) -> tuple[str, bool]:
        try:
            from adapters.google_workspace.doc_creator import create_presentation_outline

            result = create_presentation_outline(
                title=dc.title,
                topic=dc.topic,
                slides=dc.slide_count,
                audience=dc.audience,
            )
            slides_data = result.get("slides")
            if slides_data and isinstance(slides_data, dict) and slides_data.get("slides"):
                slide_list = slides_data["slides"]
                parts = [f"# {dc.title}\n"]
                for s in slide_list:
                    parts.append(
                        f"## Slide {s.get('number', '?')}: {s.get('title', '')}\n"
                        f"{s.get('key_message', '')}\n"
                    )
                self._content = "\n".join(parts)
                self._result = result
                return (f"Generated slides: {dc.title} ({dc.slide_count} slides)", True)
        except Exception as exc:
            logger.debug("slides generation failed: %s", exc)

        self._content = self._deterministic_slides(dc)
        return (f"Generated slides (template fallback): {dc.title}", True)

    def _generate_announcement(self, dc: DocumentContext) -> tuple[str, bool]:
        try:
            from adapters.google_workspace.doc_creator import draft_announcement

            content = draft_announcement(
                topic=dc.topic,
                audience=dc.audience or "team",
                key_message=dc.key_message or dc.topic,
                context=dc.context,
                announcement_type=dc.announcement_type,
            )
            if content and not content.startswith("Announcement draft unavailable"):
                self._content = content
                return (f"Generated announcement: {dc.topic}", True)
        except Exception as exc:
            logger.debug("announcement generation failed: %s", exc)

        self._content = self._deterministic_announcement(dc)
        return (f"Generated announcement (template fallback): {dc.topic}", True)

    def _generate_crisis(self, dc: DocumentContext) -> tuple[str, bool]:
        try:
            from adapters.google_workspace.doc_creator import draft_crisis_communication

            content = draft_crisis_communication(
                situation=dc.topic or "situation",
                affected_parties=dc.affected_parties or "stakeholders",
                what_happened=dc.what_happened,
                what_we_are_doing=dc.what_we_are_doing or "investigating",
            )
            if content and not content.startswith("Crisis communication unavailable"):
                self._content = content
                return (f"Generated crisis communication: {dc.topic}", True)
        except Exception as exc:
            logger.debug("crisis generation failed: %s", exc)

        self._content = self._deterministic_crisis(dc)
        return ("Generated crisis communication (template fallback)", True)

    def _store_document(self) -> tuple[str, bool]:
        if not self._content or not self._doc_ctx:
            return ("no content to store", False)

        dc = self._doc_ctx
        os.makedirs(_DOCS_DIR, exist_ok=True)

        now = datetime.now(timezone.utc)
        slug = (dc.title or dc.topic or dc.doc_type).lower()
        slug = "".join(c if c.isalnum() or c == "-" else "-" for c in slug)[:50]
        filename = f"{now.strftime('%Y-%m-%d')}_{dc.doc_type}_{slug}.md"
        filepath = os.path.join(_DOCS_DIR, filename)

        with open(filepath, "w") as f:
            f.write(self._content)

        meta = {
            "ts": now.isoformat(),
            "type": "document_generated",
            "doc_type": dc.doc_type,
            "title": dc.title or dc.topic,
            "filename": filename,
            "content_length": len(self._content),
        }
        journal_path = _runtime_state_file("organism", "execution_journal.jsonl")
        try:
            with open(journal_path, "a") as f:
                f.write(json.dumps(meta) + "\n")
        except OSError:
            pass

        return (f"Stored: {filename} ({len(self._content)} chars)", True)

    # --- Deterministic fallbacks ---

    def _deterministic_briefing(self, dc: DocumentContext) -> str:
        now = datetime.now(timezone.utc).strftime("%B %d, %Y")
        return (
            f"# {dc.title}\n"
            f"**Date:** {now}\n"
            f"**Type:** {dc.doc_type.replace('_', ' ').title()}\n\n"
            f"## Topic\n{dc.topic}\n\n"
            f"## Context\n{dc.context or 'No additional context provided.'}\n\n"
            f"## Next Steps\nAI generation unavailable. Complete manually.\n"
        )

    def _deterministic_slides(self, dc: DocumentContext) -> str:
        parts = [f"# {dc.title}\n"]
        for i in range(1, min(dc.slide_count + 1, 6)):
            parts.append(f"## Slide {i}\n[Content pending — AI unavailable]\n")
        return "\n".join(parts)

    def _deterministic_announcement(self, dc: DocumentContext) -> str:
        return (
            f"# Announcement: {dc.topic}\n\n"
            f"**Audience:** {dc.audience or 'team'}\n"
            f"**Key message:** {dc.key_message or dc.topic}\n\n"
            f"[Draft pending — AI generation unavailable]\n"
        )

    def _deterministic_crisis(self, dc: DocumentContext) -> str:
        return (
            f"# Crisis Communication\n\n"
            f"**What happened:** {dc.what_happened}\n"
            f"**Affected:** {dc.affected_parties or 'stakeholders'}\n"
            f"**Actions:** {dc.what_we_are_doing or 'investigating'}\n\n"
            f"[Full communication pending — AI generation unavailable]\n"
        )
